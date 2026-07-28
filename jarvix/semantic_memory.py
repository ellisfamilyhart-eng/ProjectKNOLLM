"""
Jarvix Advanced Cognitive Memory
Next-Gen Neuro-Symbolic Property Graph with Spreading Activation & Memory Plasticity.
"""

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Set, Any


# ── Full Relation Vocabulary (Mirrors KnowledgeGraph) ─────────────────────────

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
R_PRODUCED_BY = "produced_by"
R_ABSORBS     = "absorbs"
R_REFLECTS    = "reflects"


# ── Node & Edge Data Structures ───────────────────────────────────────────────

@dataclass
class SemanticEdge:
    subject: str
    relation: str
    object_: str

    # Cognitive Properties
    confidence: float = 0.70
    strength: float = 1.0  # Memory stability (S in Ebbinghaus curve)
    sources: List[str] = field(default_factory=list)
    times_seen: int = 1
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    last_accessed: float = field(default_factory=lambda: datetime.now().timestamp())
    last_used: str = field(default_factory=lambda: datetime.now().isoformat())
    inferred: bool = False

    @property
    def key(self) -> Tuple[str, str, str]:
        return (self.subject.lower().strip(), self.relation.lower().strip(), self.object_.lower().strip())

    def __hash__(self) -> int:
        return hash(self.key)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, SemanticEdge):
            return self.key == other.key
        return False

    def access(self, boost: float = 0.1):
        """Reinforces memory stability based on usage frequency."""
        now = datetime.now().timestamp()
        self.times_seen += 1
        self.last_accessed = now
        self.last_used = datetime.now().isoformat()
        self.strength += boost * (1.0 + math.log(self.times_seen))
        self.confidence = min(1.0, self.confidence + 0.02)

    def reinforce(self, source: str = "user", boost: float = 0.05):
        """Backwards compatible reinforce method."""
        self.access(boost=boost)
        if source not in self.sources:
            self.sources.append(source)

    def touch(self):
        """Updates last_used timestamp."""
        self.last_used = datetime.now().isoformat()
        self.last_accessed = datetime.now().timestamp()

    def calculate_retention(self, half_life_factor: float = 86400.0) -> float:
        """Ebbinghaus Forgetting Curve: Retain(t) = exp(-delta_t / S)"""
        now = datetime.now().timestamp()
        elapsed_time = max(0.0, now - self.last_accessed)
        effective_decay = elapsed_time / (self.strength * half_life_factor)
        return self.confidence * math.exp(-effective_decay)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject": self.subject,
            "relation": self.relation,
            "object_": self.object_,
            "confidence": self.confidence,
            "strength": self.strength,
            "sources": self.sources,
            "times_seen": self.times_seen,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "last_used": self.last_used,
            "inferred": self.inferred,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SemanticEdge":
        # Handle dicts missing new fields smoothly
        d_clean = {
            "subject": d.get("subject", ""),
            "relation": d.get("relation", ""),
            "object_": d.get("object_", ""),
            "confidence": d.get("confidence", 0.70),
            "strength": d.get("strength", 1.0),
            "sources": d.get("sources", []),
            "times_seen": d.get("times_seen", 1),
            "created_at": d.get("created_at", datetime.now().timestamp()),
            "last_accessed": d.get("last_accessed", datetime.now().timestamp()),
            "last_used": d.get("last_used", datetime.now().isoformat()),
            "inferred": d.get("inferred", False),
        }
        return cls(**d_clean)


@dataclass
class SemanticNode:
    name: str
    node_type: str = "concept"  # concept | entity | action | property
    activation_energy: float = 0.0  # Dynamic working memory energy
    vector_embedding: Optional[List[float]] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    aliases: List[str] = field(default_factory=list)

    def __hash__(self) -> int:
        return hash(self.name.lower().strip())

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, SemanticNode):
            return self.name.lower().strip() == other.name.lower().strip()
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "node_type": self.node_type,
            "properties": self.properties,
            "aliases": self.aliases,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SemanticNode":
        return cls(
            name=d.get("name", ""),
            node_type=d.get("node_type", "concept"),
            properties=d.get("properties", {}),
            aliases=d.get("aliases", []),
        )


# ── Advanced Cognitive Graph Engine ───────────────────────────────────────────

class SemanticMemory:
    """
    Next-Generation Neuro-Symbolic Property Graph with Spreading Activation,
    Memory Plasticity, and Full Systems Compatibility.
    """

    def __init__(self, activation_decay: float = 0.85, energy_threshold: float = 0.15):
        self.nodes: Dict[str, SemanticNode] = {}
        self.edges: Dict[Tuple[str, str, str], SemanticEdge] = {}
        self.activation_decay = activation_decay
        self.energy_threshold = energy_threshold

    # ── Node Management ───────────────────────────────────────────────────────

    def ensure_node(self, name: str, node_type: str = "concept", embedding: Optional[List[float]] = None) -> SemanticNode:
        key = name.lower().strip()
        if key not in self.nodes:
            self.nodes[key] = SemanticNode(name=key, node_type=node_type, vector_embedding=embedding)
        return self.nodes[key]

    def set_node_property(self, concept: str, key: str, value: Any):
        self.ensure_node(concept).properties[key] = value

    # ── Edge Management ───────────────────────────────────────────────────────

    def add_edge(
        self,
        subject: str,
        relation: str,
        object_: str,
        confidence: float = 0.70,
        source: str = "user",
        inferred: bool = False
    ) -> Optional[SemanticEdge]:
        s = subject.lower().strip()
        o = object_.lower().strip()
        r = relation.lower().strip()

        if not s or not o or s == "unknown" or o == "unknown":
            return None

        self.ensure_node(s)
        self.ensure_node(o)

        key = (s, r, o)
        if key in self.edges:
            self.edges[key].reinforce(source=source)
        else:
            self.edges[key] = SemanticEdge(
                subject=s,
                relation=r,
                object_=o,
                confidence=confidence,
                sources=[source],
                inferred=inferred
            )
        return self.edges[key]

    def get_edge(self, subject: str, relation: str, object_: str) -> Optional[SemanticEdge]:
        key = (subject.lower().strip(), relation.lower().strip(), object_.lower().strip())
        return self.edges.get(key)

    def edge_confidence(self, subject: str, relation: str, object_: str) -> float:
        e = self.get_edge(subject, relation, object_)
        return e.confidence if e else 0.0

    # ── Traversal Queries ─────────────────────────────────────────────────────

    def outgoing(self, subject: str, relation: Optional[str] = None) -> List[SemanticEdge]:
        s = subject.lower().strip()
        r_target = relation.lower().strip() if relation else None
        result = [
            e for (su, r, _), e in self.edges.items()
            if su == s and (r_target is None or r == r_target)
        ]
        return sorted(result, key=lambda e: -e.confidence)

    def incoming(self, object_: str, relation: Optional[str] = None) -> List[SemanticEdge]:
        o = object_.lower().strip()
        r_target = relation.lower().strip() if relation else None
        result = [
            e for (_, r, ob), e in self.edges.items()
            if ob == o and (r_target is None or r == r_target)
        ]
        return sorted(result, key=lambda e: -e.confidence)

    def all_about(self, concept: str) -> List[SemanticEdge]:
        c = concept.lower().strip()
        result = [
            e for (s, _, o), e in self.edges.items()
            if s == c or o == c
        ]
        return sorted(result, key=lambda e: -e.confidence)

    def high_confidence_topics(self, threshold: float = 0.85) -> Set[str]:
        return {
            s for (s, _, _), e in self.edges.items()
            if e.confidence >= threshold
        }

    # ── Spreading Activation Engine (Working Memory) ───────────────────────────

    def pulse_activation(self, seed_concepts: List[str], initial_energy: float = 1.0, max_hops: int = 3) -> Dict[str, float]:
        """
        Simulates neural spreading activation.
        Energy flows outward from seed nodes along edge weights to surface contextual concepts.
        """
        for node in self.nodes.values():
            node.activation_energy = 0.0

        frontier: Dict[str, float] = {}
        for seed in seed_concepts:
            s_key = seed.lower().strip()
            if s_key in self.nodes:
                self.nodes[s_key].activation_energy = initial_energy
                frontier[s_key] = initial_energy

        for _ in range(max_hops):
            next_frontier: Dict[str, float] = {}
            for node_name, energy in frontier.items():
                if energy < self.energy_threshold:
                    continue

                connected_edges = [
                    e for e in self.edges.values()
                    if e.subject == node_name or e.object_ == node_name
                ]

                for edge in connected_edges:
                    target = edge.object_ if edge.subject == node_name else edge.subject
                    target_node = self.nodes.get(target)

                    if target_node:
                        transmitted = energy * edge.calculate_retention() * self.activation_decay
                        if transmitted > target_node.activation_energy:
                            target_node.activation_energy += transmitted
                            next_frontier[target] = transmitted
                            edge.access(boost=0.01)

            frontier = next_frontier

        return {
            name: round(node.activation_energy, 4)
            for name, node in self.nodes.items()
            if node.activation_energy >= self.energy_threshold
        }

    # ── Cognitive Consolidation & Reasoning ───────────────────────────────────

    def replay_memory(self) -> int:
        strengthened = 0
        for edge in list(self.edges.values()):
            if edge.confidence < 0.3:
                continue

            if edge.times_seen >= 3:
                edge.reinforce(source="memory_replay", boost=0.01)
                strengthened += 1

            if edge.relation in (R_IS_A, R_HAS_PROP, R_HAS, R_CAN):
                if not self.get_edge(edge.subject, R_RELATED, edge.object_):
                    self.add_edge(
                        edge.subject,
                        R_RELATED,
                        edge.object_,
                        confidence=0.25,
                        source="memory_replay",
                        inferred=True
                    )
        return strengthened

    def infer_properties(self) -> int:
        created = 0
        for (child, relation, parent), edge in list(self.edges.items()):
            if relation != R_IS_A:
                continue

            parent_properties = self.outgoing(parent, R_HAS_PROP)

            for prop_edge in parent_properties:
                if not self.get_edge(child, R_HAS_PROP, prop_edge.object_):
                    self.add_edge(
                        child,
                        R_HAS_PROP,
                        prop_edge.object_,
                        confidence=prop_edge.confidence * 0.8,
                        source="ontology_reasoner",
                        inferred=True
                    )
                    created += 1

        return created

    # ── Memory Maintenance & Decay ───────────────────────────────────────────

    def decay(self, rate: float = 0.02, min_conf: float = 0.05):
        to_remove = []
        for key, edge in list(self.edges.items()):
            if edge.inferred:
                continue
            edge.confidence = max(0.0, edge.confidence - rate)
            if edge.confidence < min_conf:
                to_remove.append(key)

        for k in to_remove:
            del self.edges[k]

    def apply_ebbinghaus_decay(self, prune_threshold: float = 0.05) -> int:
        pruned_keys = []
        for key, edge in list(self.edges.items()):
            if edge.inferred:
                continue
            if edge.calculate_retention() < prune_threshold:
                pruned_keys.append(key)

        for k in pruned_keys:
            del self.edges[k]

        return len(pruned_keys)

    # ── Serialization & Analytics ─────────────────────────────────────────────

    def export(self) -> Dict[str, Any]:
        return {
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "edges": [e.to_dict() for e in self.edges.values()],
        }

    def import_data(self, data: Dict[str, Any]):
        for k, nd in data.get("nodes", {}).items():
            self.nodes[k.lower().strip()] = SemanticNode.from_dict(nd)
        for ed in data.get("edges", []):
            e = SemanticEdge.from_dict(ed)
            self.edges[e.key] = e

    def stats(self) -> Dict[str, Any]:
        inferred = sum(1 for e in self.edges.values() if e.inferred)
        conf_avg = (
            sum(e.confidence for e in self.edges.values()) / len(self.edges)
            if self.edges else 0.0
        )
        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "inferred_edges": inferred,
            "avg_confidence": round(conf_avg, 3),
        }


# ── Future Class Aliases ─────────────────────────────────────────────────────

CognitiveMemoryNetwork = SemanticMemory
HyperEdge = SemanticEdge
CognitiveNode = SemanticNode