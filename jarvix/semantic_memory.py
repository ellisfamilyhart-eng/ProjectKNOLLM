"""
Jarvix - Semantic Memory
Rich property graph: typed relations, confidence, source, times_seen, last_used.

Structure
---------
Node  : a concept (dog, mammal, gravity, ...)
Edge  : (subject, relation, object) triple with full provenance metadata
Relation types mirror knowledge_graph.py but this layer owns confidence
tracking and provenance — the knowledge_graph handles traversal/inference.

Every edge carries:
    confidence  : float   0-1
    sources     : list    who taught this
    times_seen  : int     reinforcement count
    last_used   : str     ISO timestamp
    inferred    : bool    derived by logic engine, not direct user input
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# ── Relation vocabulary (mirrors knowledge_graph constants) ───────────────────

R_IS_A        = "is_a"
R_HAS_PROP    = "has_property"
R_IS_PROP_OF  = "is_property_of"
R_HAS         = "has"
R_CAN         = "can"
R_DOES        = "does"
R_PART_OF     = "part_of"
R_CAUSES      = "causes"
R_OPPOSITE    = "opposite_of"
R_RELATED     = "related_to"
R_PERCEIVED_BY = "perceived_by"
R_PRODUCED_BY  = "produced_by"
R_ABSORBS      = "absorbs"
R_REFLECTS     = "reflects"


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class SemanticEdge:
    subject:    str
    relation:   str
    object_:    str
    confidence: float = 0.70
    sources:    list  = field(default_factory=list)   # ["user", "inference", ...]
    times_seen: int   = 1
    last_used:  str   = field(default_factory=lambda: datetime.now().isoformat())
    inferred:   bool  = False

    @property
    def key(self) -> tuple:
        return (self.subject, self.relation, self.object_)

    def reinforce(self, source: str = "user", boost: float = 0.05):
        self.confidence  = min(1.0, self.confidence + boost)
        self.times_seen += 1
        self.last_used   = datetime.now().isoformat()
        if source not in self.sources:
            self.sources.append(source)

    def touch(self):
        self.last_used = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "subject":    self.subject,
            "relation":   self.relation,
            "object_":    self.object_,
            "confidence": self.confidence,
            "sources":    self.sources,
            "times_seen": self.times_seen,
            "last_used":  self.last_used,
            "inferred":   self.inferred,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SemanticEdge":
        return cls(**d)


@dataclass
class SemanticNode:
    name:       str
    node_type:  str  = "concept"    # concept | entity | action | property
    properties: dict = field(default_factory=dict)
    aliases:    list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name":       self.name,
            "node_type":  self.node_type,
            "properties": self.properties,
            "aliases":    self.aliases,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SemanticNode":
        return cls(**d)


# ── Semantic Memory ────────────────────────────────────────────────────────────

class SemanticMemory:
    """
    Property graph store with full provenance on every edge.
    Supplements the KnowledgeGraph (which handles traversal);
    this layer owns the rich metadata.
    """

    def __init__(self):
        self.nodes: dict[str, SemanticNode] = {}
        self.edges: dict[tuple, SemanticEdge] = {}   # key -> SemanticEdge

    # ── Node management ───────────────────────────────────────────────────────

    def ensure_node(self, name: str,
                    node_type: str = "concept") -> SemanticNode:
        n = name.lower().strip()
        if n not in self.nodes:
            self.nodes[n] = SemanticNode(name=n, node_type=node_type)
        return self.nodes[n]

    def set_node_property(self, concept: str, key: str, value):
        self.ensure_node(concept).properties[key] = value

    # ── Edge management ───────────────────────────────────────────────────────

    def add_edge(self, subject: str, relation: str, object_: str,
                 confidence: float = 0.70,
                 source: str = "user",
                 inferred: bool = False) -> SemanticEdge:
        s  = subject.lower().strip()
        o  = object_.lower().strip()
        r  = relation.lower().strip()

        if not s or not o or s == "unknown" or o == "unknown":
            return None

        self.ensure_node(s)
        self.ensure_node(o)

        key = (s, r, o)
        if key in self.edges:
            self.edges[key].reinforce(source)
        else:
            self.edges[key] = SemanticEdge(
                subject    = s,
                relation   = r,
                object_    = o,
                confidence = confidence,
                sources    = [source],
                inferred   = inferred,
            )
        return self.edges[key]

    def get_edge(self, subject: str, relation: str, object_: str
                 ) -> Optional[SemanticEdge]:
        key = (subject.lower(), relation.lower(), object_.lower())
        return self.edges.get(key)

    def edge_confidence(self, subject: str, relation: str,
                        object_: str) -> float:
        e = self.get_edge(subject, relation, object_)
        return e.confidence if e else 0.0

    # ── Queries ───────────────────────────────────────────────────────────────

    def outgoing(self, subject: str,
                 relation: str = None) -> list[SemanticEdge]:
        s = subject.lower()
        result = [
            e for (su, r, _), e in self.edges.items()
            if su == s and (relation is None or r == relation)
        ]
        return sorted(result, key=lambda e: -e.confidence)

    def incoming(self, object_: str,
                 relation: str = None) -> list[SemanticEdge]:
        o = object_.lower()
        result = [
            e for (_, r, ob), e in self.edges.items()
            if ob == o and (relation is None or r == relation)
        ]
        return sorted(result, key=lambda e: -e.confidence)

    def all_about(self, concept: str) -> list[SemanticEdge]:
        """All edges where concept is subject or object."""
        c = concept.lower()
        result = []
        for (s, r, o), e in self.edges.items():
            if s == c or o == c:
                result.append(e)
        return sorted(result, key=lambda e: -e.confidence)

    def high_confidence_topics(self, threshold: float = 0.85) -> set:
        """Set of subjects that have at least one edge above threshold."""
        return {
            s for (s, _, _), e in self.edges.items()
            if e.confidence >= threshold
        }

    # ── Decay ─────────────────────────────────────────────────────────────────

    def decay(self, rate: float = 0.02, min_conf: float = 0.05):
        """
        Reduce confidence of infrequently-used, non-inferred edges.
        Remove edges that fall below min_conf.
        """
        to_remove = []
        for key, edge in self.edges.items():
            if edge.inferred:
                continue   # inferred edges don't decay (re-derived as needed)
            edge.confidence = max(0.0, edge.confidence - rate)
            if edge.confidence < min_conf:
                to_remove.append(key)
        for k in to_remove:
            del self.edges[k]

    # ── Serialisation ─────────────────────────────────────────────────────────

    def export(self) -> dict:
        return {
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "edges": [e.to_dict() for e in self.edges.values()],
        }

    def import_data(self, data: dict):
        for k, nd in data.get("nodes", {}).items():
            self.nodes[k] = SemanticNode.from_dict(nd)
        for ed in data.get("edges", []):
            e = SemanticEdge.from_dict(ed)
            self.edges[e.key] = e

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        inferred = sum(1 for e in self.edges.values() if e.inferred)
        conf_avg = (
            sum(e.confidence for e in self.edges.values()) / len(self.edges)
            if self.edges else 0.0
        )
        return {
            "nodes":          len(self.nodes),
            "edges":          len(self.edges),
            "inferred_edges": inferred,
            "avg_confidence": round(conf_avg, 3),
        }
