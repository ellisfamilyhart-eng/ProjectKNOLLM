"""
Jarvix - Contradiction Detector
Per-fact multi-belief store with conflict detection, alert generation,
and merge policy.

Design
------
For every (subject, relation) pair we keep ALL known objects with their
own confidence scores.  When a new fact arrives:

  1. Compute semantic similarity to existing objects.
  2. If similarity is LOW and existing confidence is HIGH -> contradiction.
  3. Don't overwrite — store both, flag the conflict.
  4. Generate a natural-language alert asking the user to clarify.

Merge policies
  KEEP_BOTH   : store both, lower new fact's confidence (default)
  TRUST_USER  : always accept new, reduce old
  TRUST_HIGHEST: keep whichever has higher confidence
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from .semantic_memory import SemanticMemory, SemanticEdge


# ── Tunables ──────────────────────────────────────────────────────────────────

SIMILARITY_THRESHOLD   = 0.35   # word-overlap below this = potential contradiction
CONFLICT_CONF_FLOOR    = 0.55   # existing confidence must be above this to trigger alert
NEW_FACT_PENALTY       = 0.15   # reduce new fact confidence when conflict detected


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class Conflict:
    subject:         str
    relation:        str
    existing_object: str
    existing_conf:   float
    new_object:      str
    new_conf:        float
    similarity:      float
    timestamp:       str = field(default_factory=lambda: datetime.now().isoformat())
    resolved:        bool = False
    resolution:      str  = ""   # "user_confirmed_new" | "user_kept_old" | "both_valid"

    def alert_message(self) -> str:
        return (
            f"I already know that '{self.subject}' {self.relation} "
            f"'{self.existing_object}' ({self.existing_conf:.0%} confident).\n"
            f"Now you're saying it {self.relation} '{self.new_object}'.\n"
            f"Has something changed, or are both true?"
        )


@dataclass
class BeliefSet:
    """All beliefs about a single (subject, relation) pair."""
    subject:  str
    relation: str
    beliefs:  dict = field(default_factory=dict)   # object -> confidence

    def add(self, object_: str, confidence: float):
        # Always take the higher confidence if already known
        old = self.beliefs.get(object_, 0.0)
        self.beliefs[object_] = max(old, confidence)

    def strongest(self) -> tuple:
        if not self.beliefs:
            return "", 0.0
        best = max(self.beliefs.items(), key=lambda kv: kv[1])
        return best

    def all_sorted(self) -> list:
        return sorted(self.beliefs.items(), key=lambda kv: -kv[1])


# ── Contradiction Detector ────────────────────────────────────────────────────

class ContradictionDetector:
    """
    Watches every new edge being added to SemanticMemory.
    Detects conflicts, stores them, and produces alert messages.
    """

    def __init__(self, semantic_memory: SemanticMemory):
        self.memory     = semantic_memory
        self.beliefs:  dict[tuple, BeliefSet] = {}   # (subj, rel) -> BeliefSet
        self.conflicts: list[Conflict] = []
        self.merge_policy = "KEEP_BOTH"

    # ── Main check ────────────────────────────────────────────────────────────

    def check_and_store(self, subject: str, relation: str,
                        object_: str, confidence: float,
                        source: str = "user") -> Optional[Conflict]:
        """
        Called before adding a new edge.
        Returns a Conflict if one is detected, else None.
        Always stores the belief regardless.
        """
        s = subject.lower().strip()
        r = relation.lower().strip()
        o = object_.lower().strip()

        key = (s, r)
        if key not in self.beliefs:
            self.beliefs[key] = BeliefSet(subject=s, relation=r)

        bs = self.beliefs[key]

        # Check for conflict with each existing belief
        conflict = None
        for existing_obj, existing_conf in bs.beliefs.items():
            if existing_obj == o:
                break   # same fact — just reinforce, no conflict
            sim = self._word_overlap(set(o.split()), set(existing_obj.split()))
            if sim < SIMILARITY_THRESHOLD and existing_conf >= CONFLICT_CONF_FLOOR:
                conflict = Conflict(
                    subject         = s,
                    relation        = r,
                    existing_object = existing_obj,
                    existing_conf   = existing_conf,
                    new_object      = o,
                    new_conf        = confidence,
                    similarity      = sim,
                )
                self.conflicts.append(conflict)
                # Apply merge policy
                confidence = self._apply_merge(bs, o, confidence, conflict)
                break

        bs.add(o, confidence)
        return conflict

    # ── Merge policies ────────────────────────────────────────────────────────

    def _apply_merge(self, belief_set: BeliefSet, new_obj: str,
                     new_conf: float, conflict: Conflict) -> float:
        if self.merge_policy == "KEEP_BOTH":
            # Reduce new fact slightly to signal uncertainty
            return max(0.1, new_conf - NEW_FACT_PENALTY)

        if self.merge_policy == "TRUST_USER":
            # Reduce existing
            belief_set.beliefs[conflict.existing_object] = max(
                0.1, conflict.existing_conf - NEW_FACT_PENALTY
            )
            return new_conf

        if self.merge_policy == "TRUST_HIGHEST":
            return new_conf   # both kept, no penalty

        return new_conf

    # ── Resolution ────────────────────────────────────────────────────────────

    def resolve_conflict(self, conflict: Conflict, decision: str):
        """
        Record user decision.
        decision: "keep_new" | "keep_old" | "both_valid"
        """
        conflict.resolved   = True
        conflict.resolution = decision

        s = conflict.subject
        r = conflict.relation
        key = (s, r)

        if key not in self.beliefs:
            return

        bs = self.beliefs[key]

        if decision == "keep_new":
            # Drop old belief
            bs.beliefs.pop(conflict.existing_object, None)
            # Boost new
            if conflict.new_object in bs.beliefs:
                bs.beliefs[conflict.new_object] = min(
                    1.0, bs.beliefs[conflict.new_object] + NEW_FACT_PENALTY
                )
        elif decision == "keep_old":
            bs.beliefs.pop(conflict.new_object, None)
        # "both_valid" -> do nothing, keep both as-is

    # ── Pending conflicts ─────────────────────────────────────────────────────

    def pending_conflicts(self) -> list[Conflict]:
        return [c for c in self.conflicts if not c.resolved]

    def has_pending(self) -> bool:
        return bool(self.pending_conflicts())

    def oldest_pending(self) -> Optional[Conflict]:
        pending = self.pending_conflicts()
        return pending[0] if pending else None

    # ── Scan existing memory for conflicts ────────────────────────────────────

    def scan_memory(self) -> list[Conflict]:
        """
        One-time scan of all edges in SemanticMemory to detect
        pre-existing contradictions.
        """
        from collections import defaultdict
        bucket: dict = defaultdict(list)   # (subj, rel) -> [(obj, conf)]

        for (s, r, o), edge in self.memory.edges.items():
            bucket[(s, r)].append((o, edge.confidence))

        found = []
        for (s, r), items in bucket.items():
            for i, (o1, c1) in enumerate(items):
                for o2, c2 in items[i+1:]:
                    sim = self._word_overlap(set(o1.split()), set(o2.split()))
                    if sim < SIMILARITY_THRESHOLD and c1 >= CONFLICT_CONF_FLOOR:
                        found.append(Conflict(
                            subject=s, relation=r,
                            existing_object=o1, existing_conf=c1,
                            new_object=o2, new_conf=c2,
                            similarity=sim,
                        ))
        return found

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _word_overlap(self, w1: set, w2: set) -> float:
        union = len(w1 | w2)
        return len(w1 & w2) / union if union else 0.0

    def get_all_beliefs(self, subject: str, relation: str) -> list:
        key = (subject.lower(), relation.lower())
        bs  = self.beliefs.get(key)
        return bs.all_sorted() if bs else []

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        return {
            "total_belief_sets":  len(self.beliefs),
            "total_conflicts":    len(self.conflicts),
            "pending_conflicts":  len(self.pending_conflicts()),
            "resolved_conflicts": sum(1 for c in self.conflicts if c.resolved),
        }
