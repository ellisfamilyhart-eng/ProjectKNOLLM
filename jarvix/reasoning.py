"""
Jarvix NoLLM
Reasoning Engine V2

Evaluates thoughts and chooses the best course of action.
Updated with dynamic capability checking & self-evolution hooks.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from .thought import Thought


@dataclass
class ReasoningResult:
    action: str = "RESPOND"
    confidence: float = 0.0
    explanation: str = ""
    selected_thought: Optional[Thought] = None
    plan: list = field(default_factory=list)

    def set(self, action: str, confidence: float, explanation: str, plan: Optional[list] = None) -> "ReasoningResult":
        self.action = action
        self.confidence = round(confidence, 3)
        self.explanation = explanation
        if plan is not None:
            self.plan = plan
        return self


class ReasoningEngine:
    # Action plans keyed by goal
    PLANS = {
        "LOOKUP": ["search_memory", "evaluate_facts", "generate_answer"],
        "STORE_FACT": ["validate_fact", "check_conflicts", "store_memory"],
        "GREET": ["create_social_response"],
        "EMPATHIZE": ["recognize_emotion", "create_supportive_response"],
        "SELF_UPDATE": ["validate_syntax", "persist_code", "inject_module", "register_ability"],
    }

    DEFAULT_PLAN = ["understand", "respond"]

    def __init__(self, dynamic_engine: Optional[Any] = None):
        self.last_result: Optional[ReasoningResult] = None
        self.reasoning_history: List[ReasoningResult] = []
        self.dynamic_engine = dynamic_engine  # Reference to DynamicAbilityEngine if present

    # ── Self-Awareness & Capability Checks ─────────────────────────────────────

    def can_self(self, query: str) -> ReasoningResult:
        """
        Evaluates whether the engine or an injected ability can handle a self-task.
        Prevents 'AttributeError: ReasoningEngine object has no attribute can_self'.
        """
        query_str = query.lower().strip()
        result = ReasoningResult(action="CHECK_CAPABILITY")

        # 1. Check statically registered plans
        for goal in self.PLANS:
            if goal.lower() in query_str or query_str in goal.lower():
                return result.set(
                    action=goal,
                    confidence=0.9,
                    explanation=f"Built-in capability match found for plan: '{goal}'.",
                    plan=self.PLANS[goal]
                )

        # 2. Check dynamic self-written capabilities if available
        if self.dynamic_engine and hasattr(self.dynamic_engine, "brain"):
            abilities = getattr(self.dynamic_engine.brain, "abilities", {})
            for name, ability in abilities.items():
                if name.lower() in query_str or query_str in name.lower():
                    return result.set(
                        action=f"EXECUTE_{name.upper()}",
                        confidence=0.85,
                        explanation=f"Dynamic ability '{name}' is compiled and available.",
                        plan=["load_dynamic_ability", "execute_handler"]
                    )

        # Fallback
        return result.set(
            action="UNSUPPORTED",
            confidence=0.0,
            explanation=f"No direct reasoning strategy or learned ability found for '{query}'.",
            plan=self.DEFAULT_PLAN
        )

    def can_handle(self, text: str) -> bool:
        """Boolean check used by dispatchers before invoking a full reasoning cycle."""
        res = self.can_self(text)
        return res.confidence > 0.0

    # ── Core Reasoning Pipeline ───────────────────────────────────────────────

    def reason(self, thoughts: List[Thought]) -> ReasoningResult:
        result = ReasoningResult()

        if not thoughts:
            result.explanation = "No thoughts available."
            self.last_result = result
            self.reasoning_history.append(result)
            return result

        # 1. Sort thoughts by priority, then confidence
        ordered = sorted(
            thoughts,
            key=lambda t: (getattr(t, "priority", 0), getattr(t, "confidence", 0.0)),
            reverse=True
        )

        # 2. Select top thought
        best = ordered[0]
        result.selected_thought = best
        result.action = getattr(best, "goal", "RESPOND")
        result.plan = self.create_plan(best)
        result.confidence = getattr(best, "confidence", 0.5)
        result.explanation = getattr(best, "text", "Processing thought.")

        # 3. Save state & history
        self.last_result = result
        self.reasoning_history.append(result)

        return result

    def create_plan(self, thought: Thought) -> list:
        goal = getattr(thought, "goal", "")
        return self.PLANS.get(goal, self.DEFAULT_PLAN)

    def register_plan(self, goal: str, steps: List[str]):
        """Dynamically add new action plans when Jarvix learns new skills."""
        self.PLANS[goal.upper()] = steps

    def explain(self) -> str:
        if self.last_result is None:
            return "No reasoning performed."

        return (
            f"Action: {self.last_result.action}\n"
            f"Reason: {self.last_result.explanation}\n"
            f"Confidence: {self.last_result.confidence:.2f}\n"
            f"Plan: {' -> '.join(self.last_result.plan)}"
        )


# ── Export Aliases ─────────────────────────────────────────────────────────────
ReasonEngine = ReasoningEngine