"""
Jarvix NoLLM
Reasoning Engine V3

Evaluates thoughts and chooses the best course of action using goal aggregation.
Updated with dynamic capability checking & self-evolution hooks.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from collections import defaultdict

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
    # Mapping of goals to executable plan steps
    PLANS: Dict[str, list] = {
        "LOOKUP": ["search_memory", "evaluate_facts", "generate_answer"],
        "STORE_FACT": ["validate_fact", "check_conflicts", "store_memory"],
        "GREET": ["create_social_response"],
        "EMPATHIZE": ["recognize_emotion", "create_supportive_response"],
        "RESPOND": ["understand", "respond"],
        "SELF_UPDATE": ["validate_syntax", "persist_code", "inject_module", "register_ability"],
    }

    DEFAULT_PLAN = ["understand", "respond"]

    def __init__(self, dynamic_engine: Optional[Any] = None):
        self.last_result: Optional[ReasoningResult] = None
        self.reasoning_history: List[ReasoningResult] = []
        self.dynamic_engine = dynamic_engine  # Optional reference to DynamicAbilityEngine

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
                res = result.set(
                    action=goal,
                    confidence=0.9,
                    explanation=f"Built-in capability match found for plan: '{goal}'.",
                    plan=self.PLANS[goal]
                )
                self._commit_result(res)
                return res

        # 2. Check dynamic self-written capabilities if available
        if self.dynamic_engine and hasattr(self.dynamic_engine, "brain"):
            abilities = getattr(self.dynamic_engine.brain, "abilities", {})
            for name, ability in abilities.items():
                if name.lower() in query_str or query_str in name.lower():
                    res = result.set(
                        action=f"EXECUTE_{name.upper()}",
                        confidence=0.85,
                        explanation=f"Dynamic ability '{name}' is compiled and available.",
                        plan=["load_dynamic_ability", "execute_handler"]
                    )
                    self._commit_result(res)
                    return res

        # Fallback
        res = result.set(
            action="UNSUPPORTED",
            confidence=0.0,
            explanation=f"No direct reasoning strategy or learned ability found for '{query}'.",
            plan=self.DEFAULT_PLAN
        )
        self._commit_result(res)
        return res

    def can_handle(self, text: str) -> bool:
        """Boolean check used by dispatchers before invoking a full reasoning cycle."""
        res = self.can_self(text)
        return res.confidence > 0.0

    # ── Core Reasoning Pipeline ───────────────────────────────────────────────

    def reason(self, thoughts: List[Thought]) -> ReasoningResult:
        result = ReasoningResult()

        if not thoughts:
            result.explanation = "No thoughts available."
            self._commit_result(result)
            return result

        # 1. Group thoughts by goal and calculate individual composite scores
        goal_groups = defaultdict(list)
        goal_scores = defaultdict(float)
        
        # Cache score per thought to avoid duplicate multiplications
        thought_scores = {}

        for t in thoughts:
            score = t.priority * t.confidence
            thought_scores[t] = score
            goal_groups[t.goal].append(t)
            goal_scores[t.goal] += score

        # 2. Select the goal with the highest aggregate score
        best_goal = max(goal_scores, key=goal_scores.get)
        best_thoughts = goal_groups[best_goal]

        # 3. Select the best individual thought within that winning goal
        best_thought = max(best_thoughts, key=lambda t: thought_scores[t])

        # 4. Populate result attributes
        result.selected_thought = best_thought
        result.action = best_thought.goal
        result.confidence = best_thought.confidence
        result.plan = self.create_plan(best_thought)

        # 5. Build explanation string
        explanation_parts = [f"Primary intention: {best_thought.text}"]

        # Find the highest-scoring secondary thought overall (if any exist)
        other_thoughts = [t for t in thoughts if t != best_thought]
        if other_thoughts:
            secondary_thought = max(other_thoughts, key=lambda t: thought_scores[t])
            explanation_parts.append(f"Also considering: {secondary_thought.text}")

        result.explanation = " ".join(explanation_parts)

        # 6. Save state and history
        self._commit_result(result)
        return result

    def create_plan(self, thought: Thought) -> list:
        """Generate a plan step list based on the thought's goal."""
        return self.PLANS.get(thought.goal, self.DEFAULT_PLAN)

    def register_plan(self, goal: str, steps: List[str]):
        """Dynamically register new action plans when Jarvix self-modifies or learns a skill."""
        self.PLANS[goal.upper()] = steps

    def explain(self) -> str:
        if self.last_result is None:
            return "No reasoning performed."

        plan_str = " -> ".join(self.last_result.plan) if self.last_result.plan else "N/A"
        return (
            f"Action: {self.last_result.action}\n"
            f"Reason: {self.last_result.explanation}\n"
            f"Confidence: {self.last_result.confidence:.2f}\n"
            f"Plan: {plan_str}"
        )

    def _commit_result(self, result: ReasoningResult):
        """Helper to maintain state consistency across evaluations."""
        self.last_result = result
        self.reasoning_history.append(result)


# ── Export Aliases ─────────────────────────────────────────────────────────────
ReasonEngine = ReasoningEngine