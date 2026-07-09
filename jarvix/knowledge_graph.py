"""
Jarvix Knowledge Graph
-----------------------
Stores structured triples:

    (subject, relation_type, object_)

plus per-node properties and an ontology layer.

Graph layout
  nodes: { name -> NodeData }
  edges: { (subject, relation, object_) -> EdgeData }

NodeData  : { type, properties, aliases }
EdgeData  : { confidence, support, inferred, source }
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import json


# ── Relation constants ────────────────────────────────────────────────────────

R_IS_A        = "is_a"
R_HAS_PROP    = "has_property"
R_HAS         = "has"
R_CAN         = "can"
R_DOES        = "does"
R_PART_OF     = "part_of"
R_CAUSES      = "causes"
R_OPPOSITE    = "opposite_of"
R_RELATED     = "related_to"
R_INSTANCE_OF = "instance_of"

# Relations that support transitivity (A->B, B->C => A->C)
TRANSITIVE_RELATIONS = {R_IS_A, R_PART_OF, R_INSTANCE_OF}

# Self node — the agent's own identity
SELF = "jarvix"


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class EdgeData:
    confidence: float = 0.7
    support:    int   = 1
    inferred:   bool  = False   # True = derived by reasoner, not taught
    source:     str   = "user"
    added:      str   = field(default_factory=lambda: datetime.now().isoformat())

    def reinforce(self, conf_boost: float = 0.1):
        self.support    += 1
        self.confidence  = min(1.0, self.confidence + conf_boost)


@dataclass
class NodeData:
    name:       str
    node_type:  str = "concept"   # concept | entity | action | property | self
    properties: dict = field(default_factory=dict)   # free-form key:value
    aliases:    list = field(default_factory=list)


# ── Graph ─────────────────────────────────────────────────────────────────────

class KnowledgeGraph:
    """
    Directed, typed, confidence-weighted knowledge graph.
    """

    def __init__(self):
        self.nodes: dict[str, NodeData] = {}
        self.edges: dict[tuple, EdgeData] = {}   # (subj, rel, obj) -> EdgeData

        # Seed the self-node
        self._ensure_node(SELF, "self")
        self._seed_self_capabilities()

    # ── Node management ───────────────────────────────────────────────────────

    def _ensure_node(self, name: str, node_type: str = "concept") -> NodeData:
        if name not in self.nodes:
            self.nodes[name] = NodeData(name=name, node_type=node_type)
        return self.nodes[name]

    def set_property(self, concept: str, key: str, value):
        n = self._ensure_node(concept)
        n.properties[key] = value

    def get_property(self, concept: str, key: str):
        return self.nodes.get(concept, NodeData("")).properties.get(key)

    # ── Edge management ───────────────────────────────────────────────────────

    def add_edge(self, subject: str, relation: str, obj: str,
                 confidence: float = 0.7, inferred: bool = False,
                 source: str = "user") -> EdgeData:
        subject = subject.lower().strip()
        obj     = obj.lower().strip()
        relation = relation.lower().strip()

        if not subject or not obj or subject == "unknown" or obj == "unknown":
            return EdgeData()

        self._ensure_node(subject)
        self._ensure_node(obj)

        key = (subject, relation, obj)
        if key in self.edges:
            self.edges[key].reinforce(0.05)
        else:
            self.edges[key] = EdgeData(
                confidence=confidence,
                inferred=inferred,
                source=source,
            )
        return self.edges[key]

    def edge_confidence(self, subject: str, relation: str, obj: str) -> float:
        return self.edges.get(
            (subject.lower(), relation, obj.lower()),
            EdgeData(confidence=0.0)
        ).confidence

    def has_edge(self, subject: str, relation: str, obj: str) -> bool:
        return (subject.lower(), relation, obj.lower()) in self.edges

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_outgoing(self, subject: str, relation: str = None) -> list:
        """All (relation, obj, confidence) triples from subject."""
        subj = subject.lower()
        result = []
        for (s, r, o), data in self.edges.items():
            if s == subj and (relation is None or r == relation):
                result.append((r, o, data.confidence))
        return sorted(result, key=lambda x: -x[2])

    def get_incoming(self, obj: str, relation: str = None) -> list:
        """All (subject, relation, confidence) that point TO obj."""
        ob = obj.lower()
        result = []
        for (s, r, o), data in self.edges.items():
            if o == ob and (relation is None or r == relation):
                result.append((s, r, data.confidence))
        return sorted(result, key=lambda x: -x[2])

    def neighbours(self, concept: str) -> list:
        """All directly connected concepts."""
        concept = concept.lower()
        seen = set()
        for (s, r, o) in self.edges:
            if s == concept: seen.add(o)
            if o == concept: seen.add(s)
        return list(seen)

    def all_facts_about(self, concept: str) -> list:
        """Return every (relation, obj, conf) edge from this concept."""
        return self.get_outgoing(concept)

    # ── Ontology helpers ──────────────────────────────────────────────────────

    def get_parents(self, concept: str) -> list:
        """Direct is_a / instance_of / part_of parents."""
        parents = []
        for rel in (R_IS_A, R_INSTANCE_OF, R_PART_OF):
            for _, obj, conf in self.get_outgoing(concept, rel):
                parents.append((obj, conf))
        return parents

    def get_children(self, concept: str) -> list:
        """Concepts that are_a this concept."""
        children = []
        for rel in (R_IS_A, R_INSTANCE_OF):
            for subj, _, conf in self.get_incoming(concept, rel):
                children.append((subj, conf))
        return children

    def get_capabilities(self, concept: str) -> list:
        """What concept can do."""
        return [(obj, conf)
                for _, obj, conf in self.get_outgoing(concept, R_CAN)]

    def get_properties(self, concept: str) -> list:
        """All has_property edges."""
        return [(obj, conf)
                for _, obj, conf in self.get_outgoing(concept, R_HAS_PROP)]

    # ── Self capability model ─────────────────────────────────────────────────

    def _seed_self_capabilities(self):
        """Jarvix's known capabilities — seeded once at startup."""
        caps = [
            ("read",           0.95),
            ("understand text",0.90),
            ("learn facts",    0.99),
            ("remember",       0.99),
            ("reason",         0.85),
            ("answer questions",0.80),
            ("make mistakes",  0.70),
        ]
        cannot = [
            ("see images",     0.90),
            ("hear audio",     0.90),
            ("feel emotions",  0.60),
            ("access internet",0.95),
        ]
        for cap, conf in caps:
            self.add_edge(SELF, R_CAN, cap, confidence=conf, source="seed")
        for cap, conf in cannot:
            self.add_edge(SELF, R_OPPOSITE, cap, confidence=conf, source="seed")

    def self_can(self, action: str) -> Optional[float]:
        """Return confidence that jarvix can do action, or None."""
        a = action.lower().strip()
        # Direct
        e = self.edges.get((SELF, R_CAN, a))
        if e:
            return e.confidence
        # Partial match
        for (s, r, o), data in self.edges.items():
            if s == SELF and r == R_CAN and a in o:
                return data.confidence
        return None

    def self_cannot(self, action: str) -> Optional[float]:
        """Return confidence that jarvix cannot do action, or None."""
        a = action.lower().strip()
        e = self.edges.get((SELF, R_OPPOSITE, a))
        if e:
            return e.confidence
        for (s, r, o), data in self.edges.items():
            if s == SELF and r == R_OPPOSITE and a in o:
                return data.confidence
        return None

    # ── Serialisation ─────────────────────────────────────────────────────────

    def export(self) -> dict:
        return {
            "nodes": {
                k: {
                    "node_type":  v.node_type,
                    "properties": v.properties,
                    "aliases":    v.aliases,
                }
                for k, v in self.nodes.items()
            },
            "edges": [
                {
                    "subject":    s,
                    "relation":   r,
                    "object":     o,
                    "confidence": data.confidence,
                    "support":    data.support,
                    "inferred":   data.inferred,
                    "source":     data.source,
                }
                for (s, r, o), data in self.edges.items()
            ],
        }

    def import_graph(self, data: dict):
        for name, nd in data.get("nodes", {}).items():
            node = self._ensure_node(name, nd.get("node_type", "concept"))
            node.properties = nd.get("properties", {})
            node.aliases     = nd.get("aliases", [])

        for ed in data.get("edges", []):
            self.add_edge(
                ed["subject"], ed["relation"], ed["object"],
                confidence=ed.get("confidence", 0.7),
                inferred=ed.get("inferred", False),
                source=ed.get("source", "user"),
            )

    def stats(self) -> dict:
        inferred = sum(1 for d in self.edges.values() if d.inferred)
        return {
            "nodes":           len(self.nodes),
            "edges":           len(self.edges),
            "inferred_edges":  inferred,
            "user_edges":      len(self.edges) - inferred,
        }
