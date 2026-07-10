"""
Jarvix - Question Brain
-----------------------
Classifies questions into 8 types, routes each to a dedicated handler,
and performs reverse graph lookup.  No LLM tokens consumed.

Question types
  DEFINITION      "What is a cat?"
  EXAMPLES        "What fruits do you know?"  /  "Give me examples of colors"
  CAPABILITY      "What can you do?"  /  "Can you read?"
  MEMORY          "What have you learned?"  /  "What do you know?"
  IDENTITY        "Who are you?"  /  "What is your name?"
  COMPARISON      "How is a cat different from a dog?"
  COUNT           "How many topics?"  /  "How many facts?"
  RELATIONSHIP    "What is part of a computer?"  /  "What causes rain?"
  TOPIC_QUERY     "What do you know about gravity?"
  UNKNOWN         fallback

Alias normalisation
  Expands contractions and synonym phrases before classification:
    "what's" -> "what is"
    "who's"  -> "who is"
    "can you" / "could you" -> question about capability
    "tell me about" -> topic query
    "give me examples of" -> examples query
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional


# ── Answer result ─────────────────────────────────────────────────────────────

@dataclass
class QuestionAnswer:
    question_type: str
    topic:         str
    answer:        str
    confidence:    float = 1.0
    found:         bool  = True

    def __repr__(self):
        return f"QA({self.question_type}, topic={self.topic!r}, found={self.found})"


# ── Alias / contraction table ─────────────────────────────────────────────────

_ALIASES = [
    (r"\bwhat's\b",           "what is"),
    (r"\bwho's\b",            "who is"),
    (r"\bwhere's\b",          "where is"),
    (r"\bhow's\b",            "how is"),
    (r"\bthat's\b",           "that is"),
    (r"\bit's\b",             "it is"),
    (r"\bcan't\b",            "cannot"),
    (r"\bdon't\b",            "do not"),
    (r"\bdoesn't\b",          "does not"),
    (r"\bisn't\b",            "is not"),
    (r"\baren't\b",           "are not"),
    (r"\bgive me examples of\b", "what are examples of"),
    (r"\btell me about\b",    "what do you know about"),
    (r"\blist\s+(?:all\s+)?", "what are examples of "),
    (r"\bshow me\b",          "what do you know about"),
    (r"\bdo you know about\b","what do you know about"),
]
_ALIAS_RE = [(re.compile(p, re.I), r) for p, r in _ALIASES]

def _normalise(text: str) -> str:
    t = text.strip()
    for pattern, replacement in _ALIAS_RE:
        t = pattern.sub(replacement, t)
    return re.sub(r"\s+", " ", t).strip()


# ── Question patterns ─────────────────────────────────────────────────────────
# Each: (compiled_regex, question_type, group_for_topic)

_Q_PATTERNS = [
    # IDENTITY
    (re.compile(r"^(?:who|what)\s+are\s+you\??$", re.I),
     "IDENTITY", None),
    (re.compile(r"^what\s+is\s+your\s+name\??$", re.I),
     "IDENTITY", None),

    # CAPABILITY
    (re.compile(r"^(?:what\s+can\s+(?:you|i)\s+do|what\s+are\s+your\s+(?:abilities|capabilities))\??$", re.I),
     "CAPABILITY", None),
    (re.compile(r"^can\s+you\s+(.+?)\??$", re.I),
     "CAPABILITY", 1),

    # MEMORY
    (re.compile(r"^(?:what\s+(?:do|have)\s+you\s+(?:know|learned|remember)|what\s+did\s+you\s+learn)\??$", re.I),
     "MEMORY", None),

    # COUNT
    (re.compile(r"^how\s+many\s+(.+?)\??$", re.I),
     "COUNT", 1),

    # COMPARISON
    (re.compile(r"^how\s+(?:is|are)\s+(.+?)\s+different\s+from\s+(.+?)\??$", re.I),
     "COMPARISON", 1),
    (re.compile(r"^(?:what(?:'s|\s+is)\s+the\s+difference\s+between)\s+(.+?)\s+and\s+(.+?)\??$", re.I),
     "COMPARISON", 1),

    # EXAMPLES  (must come before DEFINITION to catch "what is an example of X")
    (re.compile(r"^what\s+(?:are\s+)?examples?\s+of\s+(.+?)\??$", re.I),
     "EXAMPLES", 1),
    (re.compile(r"^what\s+is\s+an?\s+example\s+of\s+(.+?)\??$", re.I),
     "EXAMPLES", 1),
    (re.compile(r"^(?:name|list|give)\s+(?:some\s+)?(.+?)s?\??$", re.I),
     "EXAMPLES", 1),
    (re.compile(r"^what\s+(.+?)s?\s+do\s+you\s+know\??$", re.I),
     "EXAMPLES", 1),

    # RELATIONSHIP
    (re.compile(r"^what\s+is\s+part\s+of\s+(.+?)\??$", re.I),
     "RELATIONSHIP", 1),
    (re.compile(r"^what\s+(?:causes?|produces?|creates?)\s+(.+?)\??$", re.I),
     "RELATIONSHIP", 1),
    (re.compile(r"^what\s+(?:does|do)\s+(.+?)\s+(?:cause|produce|create)\??$", re.I),
     "RELATIONSHIP", 1),
    (re.compile(r"^(?:what|which)\s+(?:things?\s+)?(?:are|is)\s+(?:part\s+of|inside|in)\s+(.+?)\??$", re.I),
     "RELATIONSHIP", 1),

    # TOPIC QUERY  "what do you know about X"
    (re.compile(r"^what\s+do\s+you\s+know\s+about\s+(.+?)\??$", re.I),
     "TOPIC_QUERY", 1),
    (re.compile(r"^(?:tell\s+me\s+about|describe)\s+(.+?)\??$", re.I),
     "TOPIC_QUERY", 1),

    # DEFINITION  (catch-all "what is X" — after all the more-specific patterns)
    (re.compile(r"^what\s+(?:is|are)\s+(?:a\s+|an\s+|the\s+)?(.+?)\??$", re.I),
     "DEFINITION", 1),
    (re.compile(r"^(?:define|explain)\s+(.+?)\??$", re.I),
     "DEFINITION", 1),
    (re.compile(r"^who\s+is\s+(.+?)\??$", re.I),
     "DEFINITION", 1),
]


# ── Question Brain ────────────────────────────────────────────────────────────

class QuestionBrain:
    """
    Routes questions to dedicated handlers using graph + semantic memory.
    No LLM involved.
    """

    def __init__(self, graph, semantic_memory):
        self.graph = graph
        self.sem   = semantic_memory

    # ── Public entry ─────────────────────────────────────────────────────────

    def answer(self, raw_question: str) -> Optional[QuestionAnswer]:
        """
        Try to answer a question.  Returns QuestionAnswer or None if unknown.
        """
        norm  = _normalise(raw_question)
        qtype, topic = self._classify(norm)

        if qtype == "IDENTITY":
            return self._answer_identity()
        if qtype == "CAPABILITY":
            return self._answer_capability(topic)
        if qtype == "MEMORY":
            return self._answer_memory()
        if qtype == "COUNT":
            return self._answer_count(topic)
        if qtype == "EXAMPLES":
            return self._answer_examples(topic)
        if qtype == "RELATIONSHIP":
            return self._answer_relationship(topic, norm)
        if qtype == "COMPARISON":
            return self._answer_comparison(topic, norm)
        if qtype == "TOPIC_QUERY":
            return self._answer_topic(topic)
        if qtype == "DEFINITION":
            return self._answer_definition(topic)

        return None

    # ── Classification ────────────────────────────────────────────────────────

    def _classify(self, norm: str) -> tuple[str, str]:
        """Return (question_type, topic_string)."""
        for pattern, qtype, group in _Q_PATTERNS:
            m = pattern.match(norm.rstrip("?").strip())
            if m:
                topic = m.group(group).strip().lower() if group else ""
                topic = re.sub(r"^(a|an|the)\s+", "", topic)
                return qtype, topic
        return "UNKNOWN", ""

    # ── Handlers ─────────────────────────────────────────────────────────────

    def _answer_identity(self) -> QuestionAnswer:
        from .knowledge_graph import SELF
        named = self.graph.get_outgoing(SELF, "named")
        name  = named[0][1] if named else "Jarvix"
        caps  = self.graph.get_capabilities(SELF)
        cap_str = ", ".join(o for o, _ in caps[:4]) if caps else "learn and remember"
        answer = (
            f"I'm {name.title()}, a self-learning AI.\n"
            f"I can {cap_str}.\n"
            f"I know about {len(self.graph.nodes)} concepts so far."
        )
        return QuestionAnswer("IDENTITY", "self", answer)

    def _answer_capability(self, action: str) -> QuestionAnswer:
        from .knowledge_graph import SELF
        if not action:
            caps = self.graph.get_capabilities(SELF)
            if caps:
                lines = ["I can:"]
                for obj, conf in caps[:8]:
                    lines.append(f"  - {obj}  ({conf:.0%})")
                return QuestionAnswer("CAPABILITY", "self", "\n".join(lines))
            return QuestionAnswer("CAPABILITY", "self",
                                  "I can learn, remember, and reason about facts.")

        # Check specific capability
        result = self.graph.self_can(action)
        if result is not None:
            yn = "Yes" if result > 0.5 else "No"
            return QuestionAnswer("CAPABILITY", action,
                                  f"{yn}, I can {action}  ({result:.0%})")
        return QuestionAnswer("CAPABILITY", action,
                              f"I'm not sure whether I can {action}.",
                              confidence=0.3, found=False)

    def _answer_memory(self) -> QuestionAnswer:
        topics = sorted(self.sem.nodes.keys())
        total_edges = len(self.sem.edges)
        if not topics:
            return QuestionAnswer("MEMORY", "", "I haven't learned anything yet.")
        lines = [
            f"I know {total_edges} facts across {len(topics)} topics.",
            "",
            "Topics I know about:",
        ]
        for t in sorted(topics)[:20]:
            edges = self.sem.outgoing(t)
            if edges:
                lines.append(f"  - {t}  ({len(edges)} fact(s))")
        if len(topics) > 20:
            lines.append(f"  ... and {len(topics) - 20} more")
        return QuestionAnswer("MEMORY", "", "\n".join(lines))

    def _answer_count(self, subject: str) -> QuestionAnswer:
        s = subject.lower()
        n_topics = len(self.sem.nodes)
        n_edges  = len(self.sem.edges)
        if "topic" in s or "concept" in s:
            return QuestionAnswer("COUNT", "topics",
                                  f"I know about {n_topics} topics.")
        if "fact" in s or "thing" in s or "edge" in s:
            return QuestionAnswer("COUNT", "facts",
                                  f"I know {n_edges} facts in total.")
        if subject:
            # Count instances of this category
            instances = self._reverse_lookup(subject, ["is_a", "instance_of"])
            if instances:
                return QuestionAnswer("COUNT", subject,
                                      f"I know {len(instances)} type(s) of {subject}: "
                                      f"{', '.join(instances[:6])}.")
        return QuestionAnswer("COUNT", subject,
                              f"I know {n_topics} topics and {n_edges} facts.")

    def _answer_examples(self, category: str) -> QuestionAnswer:
        """Reverse lookup: find everything that is_a / instance_of category."""
        if not category:
            return QuestionAnswer("EXAMPLES", "", "Examples of what?", found=False)

        # Try both singular and plural
        instances = self._reverse_lookup(category,
                                         ["is_a", "instance_of", "has_property"])
        # Also try stripping trailing 's'
        if not instances and category.endswith("s"):
            instances = self._reverse_lookup(category[:-1],
                                             ["is_a", "instance_of"])

        if instances:
            lines = [f"Examples of '{category}' I know:"]
            for inst in sorted(set(instances))[:12]:
                lines.append(f"  - {inst}")
            return QuestionAnswer("EXAMPLES", category, "\n".join(lines))

        return QuestionAnswer("EXAMPLES", category,
                              f"I don't know any examples of '{category}' yet.",
                              found=False)

    def _answer_relationship(self, topic: str, norm: str) -> QuestionAnswer:
        """Find things related to topic by a specific relation."""
        # Detect relation type from the question
        rel = "related_to"
        if "part of" in norm:
            # "What is part of X?" -> reverse part_of lookup
            parts = self._reverse_lookup(topic, ["part_of"])
            if parts:
                return QuestionAnswer(
                    "RELATIONSHIP", topic,
                    f"Things that are part of '{topic}':\n" +
                    "\n".join(f"  - {p}" for p in parts[:10])
                )
        elif "cause" in norm or "produce" in norm or "create" in norm:
            # "What causes X?" -> reverse causes lookup
            causes = self._reverse_lookup(topic, ["causes"])
            if causes:
                return QuestionAnswer(
                    "RELATIONSHIP", topic,
                    f"Things that cause '{topic}':\n" +
                    "\n".join(f"  - {c}" for c in causes[:10])
                )
            # "What does X cause?" -> forward causes lookup
            effects = [(r, o, c) for r, o, c in
                       self.sem.outgoing(topic) if r == "causes"]
            if effects:
                return QuestionAnswer(
                    "RELATIONSHIP", topic,
                    f"'{topic}' causes:\n" +
                    "\n".join(f"  - {o}  ({c:.0%})" for _, o, c in effects[:8])
                )

        # Generic relationship query
        edges = self.sem.outgoing(topic)
        if edges:
            lines = [f"What I know about '{topic}':"]
            for edge in edges[:8]:
                lines.append(f"  - {edge.relation}: {edge.object_}  ({edge.confidence:.0%})")
            return QuestionAnswer("RELATIONSHIP", topic, "\n".join(lines))

        return QuestionAnswer("RELATIONSHIP", topic,
                              f"I don't know relationships for '{topic}' yet.",
                              found=False)

    def _answer_comparison(self, topic1: str, norm: str) -> QuestionAnswer:
        """Compare two topics by their known properties."""
        # Extract second topic from norm
        m = re.search(r"\bfrom\s+(.+?)(?:\?|$)", norm, re.I) or \
            re.search(r"\band\s+(.+?)(?:\?|$)", norm, re.I)
        topic2 = m.group(1).strip().lower() if m else ""

        t1_edges = {e.relation + " " + e.object_: e.confidence
                    for e in self.sem.outgoing(topic1)}
        t2_edges = {e.relation + " " + e.object_: e.confidence
                    for e in self.sem.outgoing(topic2)} if topic2 else {}

        if not t1_edges and not t2_edges:
            return QuestionAnswer("COMPARISON", topic1,
                                  f"I don't know enough about '{topic1}' or "
                                  f"'{topic2}' to compare them yet.",
                                  found=False)

        only_t1 = set(t1_edges) - set(t2_edges)
        only_t2 = set(t2_edges) - set(t1_edges)
        shared  = set(t1_edges) & set(t2_edges)

        lines = [f"Comparing '{topic1}' and '{topic2}':"]
        if shared:
            lines.append(f"\nBoth have in common:")
            for s in list(shared)[:4]:
                lines.append(f"  - {s}")
        if only_t1:
            lines.append(f"\nOnly '{topic1}':")
            for s in list(only_t1)[:4]:
                lines.append(f"  - {s}")
        if only_t2:
            lines.append(f"\nOnly '{topic2}':")
            for s in list(only_t2)[:4]:
                lines.append(f"  - {s}")

        return QuestionAnswer("COMPARISON", topic1, "\n".join(lines))

    def _answer_topic(self, topic: str) -> QuestionAnswer:
        """Everything known about a topic."""
        edges = self.sem.outgoing(topic)
        # Also try singular/plural
        if not edges and topic.endswith("s"):
            edges = self.sem.outgoing(topic[:-1])
            if edges:
                topic = topic[:-1]
        if not edges and not topic.endswith("s"):
            edges = self.sem.outgoing(topic + "s")
            if edges:
                topic = topic + "s"

        if not edges:
            return QuestionAnswer("TOPIC_QUERY", topic,
                                  f"I haven't learned about '{topic}' yet.",
                                  found=False)

        lines = [f"Here's what I know about '{topic}':"]
        for edge in edges[:10]:
            conf_label = ("(very sure)" if edge.confidence >= 0.85 else
                          "(fairly sure)" if edge.confidence >= 0.65 else
                          "(uncertain)")
            lines.append(f"  - {edge.relation}: {edge.object_}  {conf_label}")

        # Check for instances
        instances = self._reverse_lookup(topic, ["is_a", "instance_of"])
        if instances:
            lines.append(f"\nExamples / members I know:")
            for inst in sorted(instances)[:6]:
                lines.append(f"  - {inst}")

        return QuestionAnswer("TOPIC_QUERY", topic, "\n".join(lines))

    def _answer_definition(self, topic: str) -> QuestionAnswer:
        """Look up definition / main description of a concept."""
        if not topic:
            return QuestionAnswer("DEFINITION", "", "Definition of what?", found=False)

        # Try in order: definition edge, then is_a, then has_property
        for rel in ("definition", "is_a", "has_property", "instance_of"):
            edges = [e for e in self.sem.outgoing(topic) if e.relation == rel]
            if not edges and topic.endswith("s"):
                edges = [e for e in self.sem.outgoing(topic[:-1]) if e.relation == rel]
            if edges:
                best = max(edges, key=lambda e: e.confidence)
                verb = {"is_a": "is a type of",
                        "has_property": "is",
                        "instance_of": "is an example of",
                        "definition": "means"}.get(rel, rel)
                lines = [f"'{topic.title()}' {verb} {best.object_}  ({best.confidence:.0%})"]
                # Add extra facts
                extra = [e for e in self.sem.outgoing(topic) if e != best][:3]
                for e in extra:
                    lines.append(f"  Also: {e.relation} {e.object_}  ({e.confidence:.0%})")
                return QuestionAnswer("DEFINITION", topic, "\n".join(lines))

        return QuestionAnswer("DEFINITION", topic,
                              f"I don't know what '{topic}' means yet.",
                              found=False)

    # ── Reverse graph lookup ──────────────────────────────────────────────────

    def _reverse_lookup(self, target: str, relations: list[str]) -> list[str]:
        """
        Find all subjects X where (X, rel, target) exists in semantic memory.
        This enables "what fruits do you know?" by looking up instance_of=fruit.
        """
        t       = target.lower().strip()
        results = []
        for (s, r, o), edge in self.sem.edges.items():
            if r in relations and (o == t or o == t + "s" or
                                   (t.endswith("s") and o == t[:-1])):
                results.append(s)
        return results
