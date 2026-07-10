"""
Jarvix - Curiosity Engine
Identifies gaps in knowledge and generates ranked questions.

Gap detection strategy
    After learning "Cat eats Fish" the engine notices:
        - What kind of thing is Cat?      (missing is_a)
        - Where does Cat live?            (missing has_property:location)
        - Is Cat an animal?               (unverified taxonomy)
        - What does Fish is_a?            (unknown object type)

Question ranking
    Score = gap_importance * (1 - existing_coverage) * recency_boost

    gap_importance by relation:
        is_a          : 0.9   (taxonomy is critical)
        has_property  : 0.7
        can           : 0.6
        causes        : 0.6
        part_of       : 0.5
        related_to    : 0.3

    existing_coverage: fraction of gap slots already filled (0 = all unknown)
    recency_boost    : 1.5 if topic seen in last 3 turns, else 1.0

Deduplication
    Questions already asked (stored per concept) are never re-asked.
"""

from dataclasses import dataclass, field
from typing import Optional
from .semantic_memory import (
    SemanticMemory, SemanticEdge,
    R_IS_A, R_HAS_PROP, R_HAS, R_CAN, R_DOES,
    R_PART_OF, R_CAUSES, R_OPPOSITE, R_RELATED,
)


# ── Gap importance weights ────────────────────────────────────────────────────

GAP_IMPORTANCE = {
    R_IS_A:     0.9,
    R_HAS_PROP: 0.7,
    R_CAN:      0.6,
    R_CAUSES:   0.6,
    R_PART_OF:  0.5,
    R_HAS:      0.5,
    R_RELATED:  0.3,
}

# Expected relations for a "complete" concept
EXPECTED_RELATIONS = [R_IS_A, R_HAS_PROP, R_CAN]

MAX_QUESTIONS_PER_CONCEPT = 3
MAX_TOTAL_QUESTIONS       = 5


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class KnowledgeGap:
    concept:    str
    relation:   str          # what relation is missing
    hint:       str          # suggested question text
    score:      float        # higher = more useful to ask
    asked:      bool = False

    def __lt__(self, other):
        return self.score > other.score   # sort descending


# ── Curiosity Engine ──────────────────────────────────────────────────────────

class CuriosityEngine:
    """
    Identifies what Jarvix doesn't know and formulates useful questions.
    Never re-asks the same question. Ranks by usefulness.
    """

    def __init__(self, semantic_memory: SemanticMemory):
        self.memory  = semantic_memory
        self._asked: dict[str, set] = {}   # concept -> set of asked question strings

    # ── Main entry ────────────────────────────────────────────────────────────

    def find_gaps(self, concept: str,
                  recent_topics: list = None) -> list[KnowledgeGap]:
        """
        Return a ranked list of KnowledgeGap for a single concept.
        """
        concept = concept.lower().strip()
        recent_topics = [t.lower() for t in (recent_topics or [])]
        recency_boost = 1.5 if concept in recent_topics else 1.0

        known_rels = {e.relation for e in self.memory.outgoing(concept)}
        gaps = []

        for rel in EXPECTED_RELATIONS:
            if rel in known_rels:
                continue   # already covered

            importance   = GAP_IMPORTANCE.get(rel, 0.3)
            coverage     = self._coverage(concept, rel)
            score        = importance * (1.0 - coverage) * recency_boost

            question = self._formulate_question(concept, rel)
            if not question:
                continue
            if self._already_asked(concept, question):
                continue

            gaps.append(KnowledgeGap(
                concept  = concept,
                relation = rel,
                hint     = question,
                score    = score,
            ))

        # Also check objects we know about: do we know what they ARE?
        for edge in self.memory.outgoing(concept):
            obj = edge.object_
            if obj == "unknown":
                continue
            if not self.memory.outgoing(obj, R_IS_A):
                q = f"What kind of thing is '{obj}'?"
                if not self._already_asked(concept, q):
                    score = 0.5 * recency_boost
                    gaps.append(KnowledgeGap(
                        concept  = concept,
                        relation = R_IS_A,
                        hint     = q,
                        score    = score,
                    ))

        gaps.sort()   # descending by score (see __lt__)
        return gaps[:MAX_QUESTIONS_PER_CONCEPT]

    def find_gaps_multi(self, concepts: list,
                        recent_topics: list = None) -> list[KnowledgeGap]:
        """Collect gaps across multiple concepts and return top N."""
        all_gaps = []
        for c in concepts:
            all_gaps.extend(self.find_gaps(c, recent_topics))
        all_gaps.sort()
        return all_gaps[:MAX_TOTAL_QUESTIONS]

    # ── Pick next question ────────────────────────────────────────────────────

    def next_question(self, concept: str,
                      recent_topics: list = None) -> Optional[str]:
        """
        Return the single most useful question to ask right now, or None.
        Marks the question as asked to prevent repetition.
        """
        gaps = self.find_gaps(concept, recent_topics)
        if not gaps:
            return None

        best = gaps[0]
        self._mark_asked(concept, best.hint)
        best.asked = True
        return best.hint

    # ── Coverage ──────────────────────────────────────────────────────────────

    def _coverage(self, concept: str, relation: str) -> float:
        """
        How well covered is this relation for the concept?
        0.0 = completely unknown, 1.0 = fully known.
        """
        edges = self.memory.outgoing(concept, relation)
        if not edges:
            return 0.0
        # Coverage = max confidence of any edge of this relation
        return max(e.confidence for e in edges)

    # ── Question formulation ──────────────────────────────────────────────────

    def _formulate_question(self, concept: str, relation: str) -> Optional[str]:
        templates = {
            R_IS_A:     f"What type of thing is '{concept}'?",
            R_HAS_PROP: f"What are the main properties of '{concept}'?",
            R_CAN:      f"What can '{concept}' do?",
            R_CAUSES:   f"What does '{concept}' cause or lead to?",
            R_PART_OF:  f"Is '{concept}' part of something larger?",
            R_HAS:      f"What does '{concept}' have or contain?",
            R_RELATED:  f"What is '{concept}' related to?",
        }
        return templates.get(relation)

    # ── Deduplication ─────────────────────────────────────────────────────────

    def _already_asked(self, concept: str, question: str) -> bool:
        return question in self._asked.get(concept, set())

    def _mark_asked(self, concept: str, question: str):
        if concept not in self._asked:
            self._asked[concept] = set()
        self._asked[concept].add(question)

    def reset_asked(self, concept: str = None):
        """Clear asked history for a concept, or all concepts."""
        if concept:
            self._asked.pop(concept, None)
        else:
            self._asked.clear()

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        total_asked = sum(len(v) for v in self._asked.values())
        return {
            "concepts_tracked": len(self._asked),
            "total_asked":      total_asked,
        }
