"""
Jarvix NoLLM
Parser Result Object

Every sentence parsed by InputParser returns one ParseResult.

This allows every module (ConversationBrain, QuestionBrain,
TeachBrain, SocialBrain, ReasoningEngine, etc.) to speak the
same language.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParseResult:
    """
    Standard parser output.

    Every user message is converted into one of these.
    """

    # Original user text
    raw: str = ""

    # Lowercase / cleaned version
    normalized: str = ""

    # Main intent
    # UNKNOWN
    # GREETING
    # FAREWELL
    # SMALL_TALK
    # QUESTION
    # TEACH
    # COMMAND
    # OPINION
    # CORRECTION
    # THANKS
    # MATH
    # MEMORY
    # SEARCH
    # REASONING
    intent: str = "UNKNOWN"

    # Question subtype
    question_type: str = ""

    # Parsed knowledge
    subject: str = ""
    relation: str = ""
    object: str = ""

    # Optional secondary subject
    secondary_subject: str = ""

    # Named entities
    entities: list[str] = field(default_factory=list)

    # Keywords
    keywords: list[str] = field(default_factory=list)

    # Emotion detected
    emotion: str = "neutral"

    # User sentiment
    sentiment: str = "neutral"

    # Confidence of parser
    confidence: float = 1.0

    # Is the user expecting an answer?
    expects_reply: bool = True

    # Is the user teaching new information?
    teaches_fact: bool = False

    # Does this replace existing knowledge?
    correction: bool = False

    # Is this likely a social interaction?
    social: bool = False

    # Is this mathematical?
    mathematical: bool = False

    # Is this a memory recall request?
    memory_query: bool = False

    # Is the parser uncertain?
    uncertain: bool = False

    # Additional extracted values
    metadata: dict = field(default_factory=dict)

    # Parser notes for debugging
    notes: list[str] = field(default_factory=list)

    # ---------------------------------------------------------

    def add_note(self, text: str):
        """Attach parser debugging note."""
        self.notes.append(text)

    def add_entity(self, entity: str):
        """Add unique entity."""
        entity = entity.strip().lower()

        if entity and entity not in self.entities:
            self.entities.append(entity)

    def add_keyword(self, keyword: str):
        """Add unique keyword."""
        keyword = keyword.strip().lower()

        if keyword and keyword not in self.keywords:
            self.keywords.append(keyword)

    def set_relation(self, subject: str, relation: str, object_: str):
        """Populate a knowledge triple."""
        self.subject = subject.strip().lower()
        self.relation = relation.strip().lower()
        self.object = object_.strip().lower()

    def as_tuple(self):
        """
        Backwards compatibility.

        Allows old code expecting:

            topic, fact = parser.parse(...)

        to continue working while migrating.
        """
        return self.subject, self.object

    def is_valid_fact(self):
        """
        Returns True if parser found a complete knowledge statement.
        """
        return (
            self.subject != ""
            and self.relation != ""
            and self.object != ""
        )

    def summary(self):
        """
        Human-readable debug output.
        """
        return (
            f"Intent={self.intent} | "
            f"Subject='{self.subject}' | "
            f"Relation='{self.relation}' | "
            f"Object='{self.object}' | "
            f"Confidence={self.confidence:.2f}"
        )

    def to_dict(self):
        """Serialize."""
        return {
            "raw": self.raw,
            "normalized": self.normalized,
            "intent": self.intent,
            "question_type": self.question_type,
            "subject": self.subject,
            "relation": self.relation,
            "object": self.object,
            "secondary_subject": self.secondary_subject,
            "entities": self.entities,
            "keywords": self.keywords,
            "emotion": self.emotion,
            "sentiment": self.sentiment,
            "confidence": self.confidence,
            "expects_reply": self.expects_reply,
            "teaches_fact": self.teaches_fact,
            "correction": self.correction,
            "social": self.social,
            "mathematical": self.mathematical,
            "memory_query": self.memory_query,
            "uncertain": self.uncertain,
            "metadata": self.metadata,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data):
        """Deserialize."""
        obj = cls()

        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)

        return obj

    def __repr__(self):
        return (
            f"<ParseResult "
            f"intent={self.intent} "
            f"subject='{self.subject}' "
            f"relation='{self.relation}' "
            f"object='{self.object}' "
            f"confidence={self.confidence:.2f}>"
        )