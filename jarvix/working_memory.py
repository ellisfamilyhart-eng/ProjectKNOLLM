"""
Jarvix - Working Memory
Short-term conversation context with attention scoring.

Stores the last N turns, tracks current topic, resolves coreferences
("it", "that", "they"), and scores each memory item for relevance.

Attention score formula:
    recency      : +5  (last 3 turns)
    current_topic: +8  (matches active topic)
    frequent     : +3  (seen 3+ times in session)
    high_conf    : +4  (confidence >= 0.85 in knowledge graph)
    old/irrelevant: -6 (>20 turns ago, off-topic)
"""

from dataclasses import dataclass, field
from datetime import datetime
from collections import Counter
from typing import Optional


MAX_TURNS = 100          # hard cap on stored turns
RECENCY_WINDOW = 3       # turns considered "recent"
ATTENTION_RECENCY   = +5
ATTENTION_TOPIC     = +8
ATTENTION_FREQUENT  = +3
ATTENTION_HIGH_CONF = +4
ATTENTION_OLD       = -6


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class Turn:
    role:       str          # "user" | "agent"
    text:       str
    topic:      str  = ""
    intent:     str  = ""    # "teach" | "question" | "casual" | "command"
    timestamp:  str  = field(default_factory=lambda: datetime.now().isoformat())
    turn_index: int  = 0


@dataclass
class WorkingMemoryState:
    """Snapshot of the current short-term context."""
    current_topic:   str  = ""
    previous_topics: list = field(default_factory=list)
    user_goal:       str  = ""
    mood:            str  = "curious"
    last_subject:    str  = ""   # most recent named entity (for coreference)
    last_object:     str  = ""
    pending_question: Optional[str] = None   # question agent asked, awaiting answer


# ── Working Memory ────────────────────────────────────────────────────────────

class WorkingMemory:
    """
    Short-term conversation memory.
    Tracks recent turns, current context, and produces attention-weighted
    retrieval so the reasoning engine focuses on what matters.
    """

    PRONOUNS = {"it", "its", "they", "them", "their", "that", "this",
                "he", "she", "his", "her", "those", "these"}

    def __init__(self, max_turns: int = MAX_TURNS):
        self.max_turns   = max_turns
        self.turns: list[Turn] = []
        self.state       = WorkingMemoryState()
        self._topic_freq = Counter()   # topic -> times mentioned this session
        self._turn_idx   = 0

    # ── Add turns ─────────────────────────────────────────────────────────────

    def add_turn(self, role: str, text: str,
                 topic: str = "", intent: str = ""):
        turn = Turn(
            role       = role,
            text       = text,
            topic      = topic or self.state.current_topic,
            intent     = intent,
            turn_index = self._turn_idx,
        )
        self.turns.append(turn)
        self._turn_idx += 1

        # Trim to max
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]

        # Update state
        if topic:
            if self.state.current_topic and self.state.current_topic != topic:
                if self.state.current_topic not in self.state.previous_topics:
                    self.state.previous_topics.append(self.state.current_topic)
                    self.state.previous_topics = self.state.previous_topics[-10:]
            self.state.current_topic = topic
            self._topic_freq[topic] += 1

    def record_entities(self, subject: str, obj: str):
        """Record the most recent subject/object for coreference resolution."""
        if subject and subject not in ("unknown", ""):
            self.state.last_subject = subject
        if obj and obj not in ("unknown", ""):
            self.state.last_object = obj

    def set_pending_question(self, question: str):
        self.state.pending_question = question

    def clear_pending_question(self):
        self.state.pending_question = None

    # ── Coreference resolution ────────────────────────────────────────────────

    def resolve_coreference(self, text: str) -> str:
        """
        Replace pronouns with the most recent named entity.
        "it eats fish" -> "cat eats fish"  (if last subject was "cat")
        """
        words = text.lower().split()
        if not any(w in self.PRONOUNS for w in words):
            return text

        resolved = []
        for w in words:
            if w in ("it", "its", "this", "that"):
                replacement = self.state.last_subject or self.state.current_topic or w
                resolved.append(replacement)
            elif w in ("they", "them", "their", "those", "these"):
                replacement = self.state.current_topic or self.state.last_subject or w
                resolved.append(replacement)
            else:
                resolved.append(w)

        result = " ".join(resolved)
        return result if result != text.lower() else text

    # ── Attention scoring ─────────────────────────────────────────────────────

    def attention_score(self, turn: Turn,
                        topic: str = "",
                        high_conf_topics: set = None) -> float:
        """Compute attention relevance score for a single turn."""
        score = 0.0
        high_conf_topics = high_conf_topics or set()
        active_topic = topic or self.state.current_topic

        # Recency
        age = self._turn_idx - turn.turn_index
        if age <= RECENCY_WINDOW:
            score += ATTENTION_RECENCY
        elif age > 20:
            score += ATTENTION_OLD

        # Topic match
        if active_topic and turn.topic == active_topic:
            score += ATTENTION_TOPIC

        # Frequent topic
        if self._topic_freq.get(turn.topic, 0) >= 3:
            score += ATTENTION_FREQUENT

        # High-confidence topic in knowledge graph
        if turn.topic in high_conf_topics:
            score += ATTENTION_HIGH_CONF

        return score

    def get_relevant_turns(self, topic: str = "",
                           high_conf_topics: set = None,
                           top_n: int = 10) -> list:
        """Return top_n turns sorted by attention score."""
        scored = [
            (t, self.attention_score(t, topic, high_conf_topics))
            for t in self.turns
        ]
        scored.sort(key=lambda x: -x[1])
        return [t for t, _ in scored[:top_n]]

    # ── Context summary ───────────────────────────────────────────────────────

    def recent_user_turns(self, n: int = 5) -> list:
        return [t for t in self.turns[-n:] if t.role == "user"]

    def recent_topics(self, n: int = 5) -> list:
        seen = []
        for t in reversed(self.turns):
            if t.topic and t.topic not in seen:
                seen.append(t.topic)
            if len(seen) >= n:
                break
        return seen

    def get_context_summary(self) -> str:
        lines = [
            f"[Working Memory]",
            f"  Current topic  : {self.state.current_topic or '(none)'}",
            f"  Previous topics: {', '.join(self.state.previous_topics[-3:]) or '(none)'}",
            f"  Last subject   : {self.state.last_subject or '(none)'}",
            f"  User goal      : {self.state.user_goal or 'unknown'}",
            f"  Mood           : {self.state.mood}",
            f"  Turns stored   : {len(self.turns)}",
        ]
        if self.state.pending_question:
            lines.append(f"  Pending Q      : {self.state.pending_question}")
        return "\n".join(lines)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def export(self) -> dict:
        return {
            "turns": [
                {"role": t.role, "text": t.text,
                 "topic": t.topic, "intent": t.intent,
                 "timestamp": t.timestamp, "turn_index": t.turn_index}
                for t in self.turns
            ],
            "state": {
                "current_topic":   self.state.current_topic,
                "previous_topics": self.state.previous_topics,
                "user_goal":       self.state.user_goal,
                "mood":            self.state.mood,
                "last_subject":    self.state.last_subject,
                "last_object":     self.state.last_object,
            },
            "topic_freq": dict(self._topic_freq),
        }

    def import_state(self, data: dict):
        self.turns = []
        for td in data.get("turns", []):
            self.turns.append(Turn(**td))
        if self.turns:
            self._turn_idx = max(t.turn_index for t in self.turns) + 1

        sd = data.get("state", {})
        self.state.current_topic    = sd.get("current_topic", "")
        self.state.previous_topics  = sd.get("previous_topics", [])
        self.state.user_goal        = sd.get("user_goal", "")
        self.state.mood             = sd.get("mood", "curious")
        self.state.last_subject     = sd.get("last_subject", "")
        self.state.last_object      = sd.get("last_object", "")

        self._topic_freq = Counter(data.get("topic_freq", {}))
