"""
Jarvix NoLLM
Thought Engine

Produces internal thoughts before a response.
The Thought Engine never talks directly to the user.
It creates ideas for the Executive Controller.
"""

import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class Thought:
    """
    A complete internal representation of one thought.
    Every subsystem receives this object instead of raw strings.
    """

    # Original user text
    text: str

    # Unique identity (ensures hashability for dicts/sets)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Basic properties
    priority: float = 0.5
    source: str = "general"
    confidence: float = 0.7
    goal: str = "RESPOND"

    # Parsed knowledge
    intent: str = ""
    entities: List[str] = field(default_factory=list)
    triples: List[Any] = field(default_factory=list)

    # Reasoning
    conclusions: List[str] = field(default_factory=list)
    questions: List[str] = field(default_factory=list)

    # Memory
    consolidated: bool = False
    importance: float = 0.5

    # Extra information
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ── Hash & Equality ────────────────────────────────────────────────────────
    # Prevents "unhashable type: 'Thought'" errors when used as dict keys or in sets
    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Thought):
            return self.id == other.id
        return self is other


class ThoughtEngine:

    def __init__(self):
        self.active_thoughts: List[Thought] = []

    # ── Utility Methods ────────────────────────────────────────────────────────

    def clear(self) -> None:
        """Clears all active thoughts."""
        self.active_thoughts.clear()

    def add(
        self,
        text: str,
        priority: float = 0.5,
        source: str = "general",
        confidence: float = 0.7,
        goal: str = "RESPOND",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Thought:
        """Constructs and registers a new Thought object."""
        thought = Thought(
            text=text,
            priority=priority,
            source=source,
            confidence=confidence,
            goal=goal,
            metadata=metadata or {}
        )
        self.active_thoughts.append(thought)
        return thought

    def _decorate_thought(self, thought: Thought, parse_result: Any) -> None:
        """Enriches a Thought instance with intent, entities, and graph triples."""
        thought.intent = getattr(parse_result, "intent", "")
        thought.entities = getattr(parse_result, "entities", [])
        thought.triples = getattr(parse_result, "triples", [])
        thought.metadata["parse_result"] = parse_result

    # ── Main Engine Loop ───────────────────────────────────────────────────────

    def think(self, parse_result: Any) -> List[Thought]:
        """
        Generates internal thoughts from structured parse inputs.
        """
        self.clear()

        intent = getattr(parse_result, "intent", "")
        entities = getattr(parse_result, "entities", [])

        # 1. GREETING
        if intent == "GREETING":
            thought = self.add(
                "The user is greeting me.",
                priority=1.0,
                source="conversation",
                goal="GREET"
            )
            self._decorate_thought(thought, parse_result)

        # 2. QUESTION
        elif intent == "QUESTION":
            thought = self.add(
                "The user is asking a question.",
                priority=1.0,
                source="conversation",
                goal="RESPOND"
            )
            self._decorate_thought(thought, parse_result)

            if entities:
                joined_entities = ", ".join(f"'{e}'" for e in entities)
                self.add(
                    f"Search memory for relationships involving: {joined_entities}.",
                    priority=0.9,
                    source="memory",
                    goal="RETRIEVE_FACT"
                )

        # 3. TEACH
        elif intent == "TEACH":
            thought = self.add(
                "The user is teaching me something.",
                priority=1.0,
                source="learning",
                goal="STORE_FACT"
            )
            self._decorate_thought(thought, parse_result)

            if hasattr(parse_result, "subject"):
                self.add(
                    f"Remember information about '{parse_result.subject}'.",
                    priority=0.95,
                    source="memory",
                    goal="STORE_FACT"
                )

        # 4. CORRECTION
        elif intent == "CORRECTION":
            thought = self.add(
                "The user is correcting existing knowledge.",
                priority=0.95,
                source="learning",
                goal="UPDATE_FACT"
            )
            self._decorate_thought(thought, parse_result)

        # 5. THANKS
        elif intent == "THANKS":
            thought = self.add(
                "The user is thanking me.",
                priority=0.80,
                source="conversation",
                goal="THANK"
            )
            self._decorate_thought(thought, parse_result)

        # 6. FAREWELL
        elif intent == "FAREWELL":
            thought = self.add(
                "The conversation is ending.",
                priority=0.80,
                source="conversation",
                goal="FAREWELL"
            )
            self._decorate_thought(thought, parse_result)

        # 7. EMOTION
        elif intent == "EMOTION":
            thought = self.add(
                "The user expressed an emotion.",
                priority=0.90,
                source="social",
                goal="EMPATHIZE"
            )
            self._decorate_thought(thought, parse_result)

        # 8. OPINION
        elif intent == "OPINION":
            thought = self.add(
                "The user expressed an opinion.",
                priority=0.75,
                source="reasoning",
                goal="DISCUSS"
            )
            self._decorate_thought(thought, parse_result)

        # 9. DEFAULT
        else:
            thought = self.add(
                "Understand the user's statement.",
                priority=0.60,
                source="general",
                goal="RESPOND"
            )
            self._decorate_thought(thought, parse_result)

        return self.active_thoughts

    # ── Thought Queries & Analytics ────────────────────────────────────────────

    def highest_priority(self) -> Optional[Thought]:
        """Returns the active thought with the highest priority score."""
        if not self.active_thoughts:
            return None
        return max(self.active_thoughts, key=lambda t: t.priority)

    def thoughts_by_goal(self, goal: str) -> List[Thought]:
        """Filters active thoughts by target goal."""
        return [t for t in self.active_thoughts if t.goal == goal]

    def thoughts_by_source(self, source: str) -> List[Thought]:
        """Filters active thoughts by subsystem origin."""
        return [t for t in self.active_thoughts if t.source == source]

    def summary(self) -> List[Dict[str, Any]]:
        """Returns a simplified serializable state of all active thoughts."""
        return [
            {
                "id": t.id,
                "text": t.text,
                "goal": t.goal,
                "source": t.source,
                "priority": t.priority,
                "confidence": t.confidence
            }
            for t in self.active_thoughts
        ]