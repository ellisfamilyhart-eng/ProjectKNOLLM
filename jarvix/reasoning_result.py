"""
Jarvix NoLLM
Pipeline Reasoning Engine V4

Processes parsed input through a strictly ordered reasoning pipeline:
Goal -> Memory -> Logic -> Conflicts -> Confidence -> Plan
Updated with dynamic capability checking & self-evolution hooks.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ReasoningResult:
    goal: str = "UNKNOWN"
    memory_facts: List[Dict[str, Any]] = field(default_factory=list)
    inferred_facts: List[Dict[str, Any]] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 1.0
    action: str = "RESPOND"
    plan: List[str] = field(default_factory=list)
    explanation: str = ""

    def set(
        self,
        action: str,
        confidence: float,
        explanation: str,
        plan: Optional[List[str]] = None,
        goal: Optional[str] = None,
    ) -> "ReasoningResult":
        self.action = action
        if goal:
            self.goal = goal
        self.confidence = round(confidence, 3)
        self.explanation = explanation
        if plan is not None:
            self.plan = plan
        return self


class ReasoningEngine:

    PLAN_TEMPLATES: Dict[str, List[str]] = {
        "LOOKUP": ["search_memory", "evaluate_facts", "generate_answer"],
        "STORE_FACT": ["validate_fact", "check_conflicts", "store_memory"],
        "GREET": ["create_social_response"],
        "EMPATHIZE": ["recognize_emotion", "create_supportive_response"],
        "RESPOND": ["understand", "respond"],
        "SELF_UPDATE": ["validate_syntax", "persist_code", "inject_module", "register_ability"],
    }

    def __init__(self, memory_system=None, logic_reasoner=None, dynamic_engine: Optional[Any] = None):
        self.memory = memory_system
        self.reasoner = logic_reasoner
        self.dynamic_engine = dynamic_engine  # Optional reference to DynamicAbilityEngine
        self.last_result: Optional[ReasoningResult] = None
        self.history: List[ReasoningResult] = []

    # ── Self-Awareness & Capability Checks ─────────────────────────────────────

    def can_self(self, query: str) -> ReasoningResult:
        """
        Evaluates whether the engine or an injected ability can handle a self-task.
        Prevents 'AttributeError: ReasoningEngine object has no attribute can_self'.
        """
        query_str = query.lower().strip()
        result = ReasoningResult(goal="CHECK_CAPABILITY")

        # 1. Check statically registered plans
        for goal, steps in self.PLAN_TEMPLATES.items():
            if goal.lower() in query_str or query_str in goal.lower():
                res = result.set(
                    action=goal,
                    confidence=0.9,
                    explanation=f"Built-in capability match found for plan: '{goal}'.",
                    plan=steps,
                    goal=goal
                )
                self._commit_result(res)
                return res

        # 2. Check dynamic self-written capabilities if available
        if self.dynamic_engine and hasattr(self.dynamic_engine, "brain"):
            abilities = getattr(self.dynamic_engine.brain, "abilities", {})
            for name, _ in abilities.items():
                if name.lower() in query_str or query_str in name.lower():
                    res = result.set(
                        action=f"EXECUTE_{name.upper()}",
                        confidence=0.85,
                        explanation=f"Dynamic ability '{name}' is compiled and available.",
                        plan=["load_dynamic_ability", "execute_handler"],
                        goal=f"DYNAMIC_{name.upper()}"
                    )
                    self._commit_result(res)
                    return res

        # Fallback
        res = result.set(
            action="UNSUPPORTED",
            confidence=0.0,
            explanation=f"No direct reasoning strategy or learned ability found for '{query}'.",
            plan=self.PLAN_TEMPLATES["RESPOND"],
            goal="UNSUPPORTED"
        )
        self._commit_result(res)
        return res

    def can_handle(self, text: str) -> bool:
        """Boolean check used by dispatchers before invoking a full reasoning cycle."""
        res = self.can_self(text)
        return res.confidence > 0.0

    def register_plan(self, goal: str, steps: List[str]):
        """Dynamically register new action plans when Jarvix self-modifies or learns a skill."""
        self.PLAN_TEMPLATES[goal.upper()] = steps

    # ── Main Entry Point ──────────────────────────────────────────────────────

    def reason(self, parse_result: Dict[str, Any]) -> ReasoningResult:
        result = ReasoningResult()

        self.determine_goal(parse_result, result)
        self.collect_memory(parse_result, result)
        self.apply_logic(result)
        self.detect_conflicts(result)
        self.evaluate_confidence(result)
        self.plan_action(result)

        # Commit to history
        self._commit_result(result)

        return result

    # ── Pipeline Stages ───────────────────────────────────────────────────────

    def determine_goal(self, parse_result: Dict[str, Any], result: ReasoningResult):
        """Extract or infer the primary user goal from the parsed input."""
        intent = parse_result.get("intent", "RESPOND")
        result.goal = intent.upper()

    def collect_memory(self, parse_result: Dict[str, Any], result: ReasoningResult):
        """Query memory graph or store based on subjects/entities found in input."""
        entities = parse_result.get("entities", [])
        if self.memory and entities:
            facts = []
            for entity in entities:
                if hasattr(self.memory, "get_facts"):
                    facts.extend(self.memory.get_facts(entity))
            result.memory_facts = facts

    def apply_logic(self, result: ReasoningResult):
        """Derive transitive facts or run graph inferences on gathered memory."""
        if self.reasoner and result.memory_facts:
            if hasattr(self.reasoner, "run_forward_inference"):
                inferred = self.reasoner.run_forward_inference()
                result.inferred_facts = inferred

    def detect_conflicts(self, result: ReasoningResult):
        """Identify contradicting facts (e.g., A is_a B vs A opposite_of B)."""
        if self.reasoner and hasattr(self.reasoner, "detect_contradictions"):
            conflicts = self.reasoner.detect_contradictions()
            result.conflicts = conflicts

    def evaluate_confidence(self, result: ReasoningResult):
        """Adjust overall confidence based on evidence chain and conflicts."""
        base_confidence = 1.0

        # Penalize confidence if logical contradictions exist
        if result.conflicts:
            base_confidence *= 0.5 ** len(result.conflicts)

        # Reward confidence if supporting facts exist
        if result.memory_facts:
            base_confidence = min(1.0, base_confidence * 1.1)

        result.confidence = round(base_confidence, 2)

    def plan_action(self, result: ReasoningResult):
        """Assign the final execution plan based on goal and confidence."""
        if result.confidence < 0.3:
            result.action = "CLARIFY"
            result.plan = ["ask_clarification"]
            result.explanation = "Low confidence due to conflicting or missing facts."
            return

        result.action = result.goal
        result.plan = self.PLAN_TEMPLATES.get(
            result.goal, self.PLAN_TEMPLATES["RESPOND"]
        )
        result.explanation = f"Executing plan for goal '{result.goal}' with confidence {result.confidence}."

    # ── Diagnostics & History ─────────────────────────────────────────────────

    def explain(self) -> str:
        if self.last_result is None:
            return "No reasoning performed yet."

        r = self.last_result
        return (
            f"Goal: {r.goal}\n"
            f"Action: {r.action}\n"
            f"Confidence: {r.confidence:.2f}\n"
            f"Conflicts Found: {len(r.conflicts)}\n"
            f"Plan Steps: {' -> '.join(r.plan)}\n"
            f"Explanation: {r.explanation}"
        )

    def _commit_result(self, result: ReasoningResult):
        """Helper to maintain state consistency across evaluations."""
        self.last_result = result
        self.history.append(result)


# ── Export Aliases ─────────────────────────────────────────────────────────────
ReasonEngine = ReasoningEngine