"""
Jarvix - Confidence Manager
Multi-source confidence tracking, reinforcement, decay, and pruning.

Every fact carries:
    confidence  : float  0-1   current belief strength
    sources     : set    who contributed ("user", "inference", "web", ...)
    times_seen  : int    total reinforcement count
    last_used   : str    ISO timestamp
    first_seen  : str    ISO timestamp

Confidence rules
    New fact from user            : base = 0.65
    Same fact seen again          : += 0.08 per repeat, cap 1.0
    Inferred fact                 : base = source_conf * chain_decay
    High source count (>= 3)     : +0.10 bonus (crowd wisdom)
    Decay per idle cycle          : -= 0.02 (configurable, skips mastered)
    Prune below                   : 0.05
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# ── Tunables ──────────────────────────────────────────────────────────────────

BASE_USER_CONF      = 0.65
REINFORCE_BOOST     = 0.08
MULTI_SOURCE_BONUS  = 0.10
MIN_SOURCE_FOR_BONUS = 3
DECAY_RATE          = 0.02
PRUNE_THRESHOLD     = 0.05
MASTERY_THRESHOLD   = 0.88   # facts above this don't decay


# ── Per-fact record ───────────────────────────────────────────────────────────

@dataclass
class FactRecord:
    subject:    str
    relation:   str
    object_:    str
    confidence: float      = BASE_USER_CONF
    sources:    set        = field(default_factory=set)
    times_seen: int        = 1
    first_seen: str        = field(default_factory=lambda: datetime.now().isoformat())
    last_used:  str        = field(default_factory=lambda: datetime.now().isoformat())
    inferred:   bool       = False

    @property
    def key(self) -> tuple:
        return (self.subject, self.relation, self.object_)

    def reinforce(self, source: str = "user"):
        self.sources.add(source)
        self.times_seen += 1
        self.last_used   = datetime.now().isoformat()
        boost = REINFORCE_BOOST
        # Extra bonus when many independent sources agree
        if len(self.sources) >= MIN_SOURCE_FOR_BONUS:
            boost += MULTI_SOURCE_BONUS
        self.confidence = min(1.0, self.confidence + boost)

    def decay(self):
        if self.confidence >= MASTERY_THRESHOLD:
            return   # mastered facts don't decay
        self.confidence = max(0.0, self.confidence - DECAY_RATE)

    def to_dict(self) -> dict:
        return {
            "subject":    self.subject,
            "relation":   self.relation,
            "object_":    self.object_,
            "confidence": self.confidence,
            "sources":    list(self.sources),
            "times_seen": self.times_seen,
            "first_seen": self.first_seen,
            "last_used":  self.last_used,
            "inferred":   self.inferred,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "FactRecord":
        d = dict(d)
        d["sources"] = set(d.get("sources", []))
        return cls(**d)


# ── Confidence Manager ────────────────────────────────────────────────────────

class ConfidenceManager:
    """
    Central authority for fact confidence.
    All modules should call this instead of writing confidences directly.
    """

    def __init__(self):
        self.records: dict[tuple, FactRecord] = {}

    # ── Write ─────────────────────────────────────────────────────────────────

    def observe(self, subject: str, relation: str, object_: str,
                source: str = "user",
                base_confidence: float = BASE_USER_CONF,
                inferred: bool = False) -> FactRecord:
        """
        Record or reinforce a fact.
        Returns the updated FactRecord.
        """
        s = subject.lower().strip()
        r = relation.lower().strip()
        o = object_.lower().strip()
        key = (s, r, o)

        if key in self.records:
            self.records[key].reinforce(source)
        else:
            self.records[key] = FactRecord(
                subject    = s,
                relation   = r,
                object_    = o,
                confidence = base_confidence,
                sources    = {source},
                inferred   = inferred,
            )
        return self.records[key]

    def reinforce(self, subject: str, relation: str, object_: str,
                  source: str = "user") -> Optional[FactRecord]:
        """Reinforce an existing fact. No-op if not known."""
        key = (subject.lower(), relation.lower(), object_.lower())
        if key in self.records:
            self.records[key].reinforce(source)
            return self.records[key]
        return None

    # ── Read ──────────────────────────────────────────────────────────────────

    def get(self, subject: str, relation: str,
            object_: str) -> Optional[FactRecord]:
        key = (subject.lower(), relation.lower(), object_.lower())
        return self.records.get(key)

    def confidence(self, subject: str, relation: str, object_: str) -> float:
        rec = self.get(subject, relation, object_)
        return rec.confidence if rec else 0.0

    def all_about(self, subject: str) -> list[FactRecord]:
        s = subject.lower()
        return sorted(
            [r for (su, _, _), r in self.records.items() if su == s],
            key=lambda r: -r.confidence,
        )

    def strongest(self, subject: str, relation: str) -> Optional[FactRecord]:
        """Best known object for (subject, relation)."""
        candidates = [
            r for (su, re, _), r in self.records.items()
            if su == subject.lower() and re == relation.lower()
        ]
        return max(candidates, key=lambda r: r.confidence) if candidates else None

    def high_confidence_topics(self, threshold: float = 0.85) -> set:
        return {r.subject for r in self.records.values()
                if r.confidence >= threshold}

    # ── Maintenance ───────────────────────────────────────────────────────────

    def run_decay(self):
        """Apply decay to all non-mastered, non-inferred facts."""
        for rec in self.records.values():
            if not rec.inferred:
                rec.decay()

    def prune(self) -> list:
        """Remove facts below PRUNE_THRESHOLD. Returns removed keys."""
        to_remove = [k for k, r in self.records.items()
                     if r.confidence < PRUNE_THRESHOLD]
        for k in to_remove:
            del self.records[k]
        return to_remove

    def sync_from_semantic(self, sem_memory) -> int:
        """
        Import edge data from a SemanticMemory into this manager.
        Returns count of records synced.
        """
        count = 0
        for (s, r, o), edge in sem_memory.edges.items():
            key = (s, r, o)
            if key not in self.records:
                rec = FactRecord(
                    subject    = s,
                    relation   = r,
                    object_    = o,
                    confidence = edge.confidence,
                    sources    = set(edge.sources),
                    times_seen = edge.times_seen,
                    first_seen = edge.last_used,
                    last_used  = edge.last_used,
                    inferred   = edge.inferred,
                )
                self.records[key] = rec
                count += 1
            else:
                # Sync confidence upward only
                if edge.confidence > self.records[key].confidence:
                    self.records[key].confidence = edge.confidence
        return count

    # ── Serialisation ─────────────────────────────────────────────────────────

    def export(self) -> list:
        return [r.to_dict() for r in self.records.values()]

    def import_data(self, data: list):
        for d in data:
            rec = FactRecord.from_dict(d)
            self.records[rec.key] = rec

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        if not self.records:
            return {"total": 0, "avg_confidence": 0.0,
                    "mastered": 0, "multi_source": 0}
        confs   = [r.confidence for r in self.records.values()]
        return {
            "total":          len(self.records),
            "avg_confidence": round(sum(confs) / len(confs), 3),
            "mastered":       sum(1 for c in confs if c >= MASTERY_THRESHOLD),
            "multi_source":   sum(1 for r in self.records.values()
                                  if len(r.sources) >= MIN_SOURCE_FOR_BONUS),
        }
