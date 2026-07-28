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

# New system relations
R_TRIGGERS    = "triggers_function"  # Links a keyword to a python function name
R_THEN        = "then"               # Chaining sequence: Step A -> then -> Step B
R_STEP_OF     = "step_of"            # Grouping sequences: Step A -> step_of -> "clean_house"

# Relations that support transitivity (A->B, B->C => A->C)
TRANSITIVE_RELATIONS = {R_IS_A, R_PART_OF, R_INSTANCE_OF}

# Self node — the agent's own identity
SELF = "jarvix"


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class EdgeData:
    confidence: float = 0.7
    support:    int   = 1
    inferred:   bool  = False
    source:     str   = "user"
    last_used:  str   = field(default_factory=lambda: datetime.now().isoformat())
    added:      str   = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def times_seen(self):
        return self.support

    def reinforce(self, conf_boost: float = 0.05):
        self.support += 1
        self.confidence = min(
            1.0,
            self.confidence + conf_boost
        )
        self.last_used = datetime.now().isoformat()


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
        """
        Jarvix's known capabilities — seeded once at startup.
        Long strings have been consolidated into clean noun concepts.
        """
        # (relation, consolidated_node, confidence)
        caps = [
            (R_CAN, "reading", 0.95),
            (R_CAN, "text_comprehension", 0.90),
            (R_CAN, "learning", 0.99),
            (R_CAN, "memory", 0.99),
            (R_CAN, "reasoning", 0.85),
            (R_CAN, "interaction", 0.80),
            (R_CAN, "error_generation", 0.70),
        ]
        cannot = [
            ("vision", 0.90),
            ("hearing", 0.90),
            ("emotion", 0.60),
            ("internet_access", 0.95),
        ]
        for relation, cap, conf in caps:
            self.add_edge(SELF, relation, cap, confidence=conf, source="seed")
        for cap, conf in cannot:
            self.add_edge(SELF, R_OPPOSITE, cap, confidence=conf, source="seed")

    def self_can(self, action: str) -> Optional[float]:
        """Return confidence that jarvix can do action, or None."""
        a = action.lower().strip()
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

    # ── DreamingEngine compatibility layer ────────────────────────────────────

    @property
    def nodes_map(self):
        return self.nodes

    def get_edge(self, subject, relation, obj):
        return self.edges.get(
            (
                subject.lower(),
                relation.lower(),
                obj.lower()
            )
        )

    def outgoing(self, subject, relation=None):
        results = []
        for (s, r, o), edge in self.edges.items():
            if s == subject.lower():
                if relation is None or relation == r:
                    results.append(edge)
                    edge.object_ = o
                    edge.relation = r
        return results

    def replay_memory(self):
        """
        Sleep replay:
        1. Automatically breaks down "long string" nodes into atomic concepts.
        2. Strengthens old important memories.
        3. Creates associative links.
        """
        strengthened = 0
        long_node_limit = 20  # Character length threshold to trigger a breakdown
        
        # 1. Identify "long string" nodes currently in the graph
        long_nodes = [name for name in list(self.nodes.keys()) if len(name) > long_node_limit]
        
        for long_node in long_nodes:
            # Decompose a long node like "feel emotions" or "understand text"
            words = long_node.split()
            if len(words) >= 2:
                verb = words[0]
                noun = "_".join(words[1:])
                
                # Migrate incoming/outgoing edges from the old bulky node to the new atomic nodes
                for (s, r, o), edge in list(self.edges.items()):
                    if o == long_node:
                        # Add a clean, atomic object node
                        self.add_edge(s, r, noun, confidence=edge.confidence, inferred=True, source="dream_decomposer")
                        # Add a functional link between the action verb and the concept noun
                        self.add_edge(noun, R_IS_A, verb, confidence=0.7, inferred=True, source="dream_decomposer")
                        # Clean up the old, bulky edge
                        self.edges.pop((s, r, o), None)
                        
                    if s == long_node:
                        self.add_edge(noun, r, o, confidence=edge.confidence, inferred=True, source="dream_decomposer")
                        self.edges.pop((s, r, o), None)
                
                # Safely delete the orphaned bulky node
                self.nodes.pop(long_node, None)

        # 2. Standard reinforcement and association loop
        for (s, r, o), edge in list(self.edges.items()):
            if edge.confidence < 0.3:
                continue

            # Reinforce repeated knowledge
            if edge.support >= 3:
                edge.reinforce(0.01)
                strengthened += 1

            # Concepts connected by facts become associated
            if r in (R_IS_A, R_HAS_PROP, R_CAN, R_HAS):
                if not self.has_edge(s, R_RELATED, o):
                    self.add_edge(
                        s,
                        R_RELATED,
                        o,
                        confidence=0.25,
                        inferred=True,
                        source="memory_replay"
                    )
        return strengthened

    def infer_properties(self):
        created = 0
        for child, parent_data in list(self.edges.items()):
            child_name, rel, parent = child
            if rel != R_IS_A:
                continue

            for prop, conf in self.get_properties(parent):
                if not self.has_edge(child_name, R_HAS_PROP, prop):
                    self.add_edge(
                        child_name,
                        R_HAS_PROP,
                        prop,
                        confidence=conf * 0.8,
                        inferred=True,
                        source="ontology_reasoner"
                    )
                    created += 1
        return created

    # --- MOVED INSIDE CLASS ---
    def execute_sequence(self, sequence_name: str, registry: dict):
        """
        Locates steps grouped under sequence_name, orders them using R_THEN, 
        and executes their registered functions.
        """
        print(f"\n--- Initiating Sequence: {sequence_name} ---")
        
        # 1. Gather all steps belonging to this routine
        steps = []
        for s, r, o in self.edges:
            if r == R_STEP_OF and o == sequence_name:
                steps.append(s)
                
        if not steps:
            print(f"No steps found for sequence: '{sequence_name}'")
            return

        # 2. Find the starting step (the one that has no incoming 'then' edges)
        start_step = None
        for step in steps:
            has_incoming_then = any(r == R_THEN and o == step for (s, r, o) in self.edges)
            if not has_incoming_then:
                start_step = step
                break
                
        if not start_step:
            start_step = steps[0]  # Fallback if circular or unlinked

        # 3. Traverse and execute steps sequentially
        current_step = start_step
        visited = set()
        
        while current_step and current_step not in visited:
            visited.add(current_step)
            
            # Find associated function for this step
            trigger_edges = self.get_outgoing(current_step, R_TRIGGERS)
            if trigger_edges:
                func_name = trigger_edges[0][1] # Get target object
                func = registry.get(func_name)
                if func:
                    result = func()
                    print(f"[{current_step}] executed '{func_name}' -> Result: {result}")
                else:
                    print(f"[{current_step}] Failed: '{func_name}' not in registry.")
            
            # Find the next step in the sequence chain
            then_edges = self.get_outgoing(current_step, R_THEN)
            if then_edges:
                current_step = then_edges[0][1] # Next node
            else:
                current_step = None  # End of sequence
                
        print(f"--- Sequence {sequence_name} Complete ---\n")


# ── Executable Script Block ───────────────────────────────────────────────────

if __name__ == "__main__":
    # 1. Define your python functions
    def fetch_weather_report():
        print("[Executing Function] Fetching local weather...")
        return "Weather is sunny, 22°C."

    def send_alert_email():
        print("[Executing Function] Sending out alert email...")
        return "Email sent successfully."

    def log_to_file():
        print("[Executing Function] Writing data to local system log...")
        return "System log updated."

    # 2. Maintain a registry map in your main script
    FUNCTION_REGISTRY = {
        "fetch_weather_report": fetch_weather_report,
        "send_alert_email": send_alert_email,
        "log_to_file": log_to_file
    }

    # 3. Instantiate the Knowledge Graph
    graph = KnowledgeGraph()

    # 4. Associate words/terms in the graph with those functions
    graph.add_edge("rain_alert", R_TRIGGERS, "send_alert_email")
    graph.add_edge("morning_routine", R_TRIGGERS, "fetch_weather_report")

    # 5. Define the parent thought pattern
    graph._ensure_node("emergency_routine", node_type="action")

    # Define individual steps
    graph._ensure_node("step_one", node_type="action")
    graph._ensure_node("step_two", node_type="action")
    graph._ensure_node("step_three", node_type="action")

    # Group steps under the parent routine
    graph.add_edge("step_one", R_STEP_OF, "emergency_routine")
    graph.add_edge("step_two", R_STEP_OF, "emergency_routine")
    graph.add_edge("step_three", R_STEP_OF, "emergency_routine")

    # Bind functional triggers to the steps
    graph.add_edge("step_one", R_TRIGGERS, "fetch_weather_report")
    graph.add_edge("step_two", R_TRIGGERS, "send_alert_email")
    graph.add_edge("step_three", R_TRIGGERS, "log_to_file")

    # Chain the timeline order (Sequence)
    graph.add_edge("step_one", R_THEN, "step_two")
    graph.add_edge("step_two", R_THEN, "step_three")

    # 6. Run it!
    graph.execute_sequence("emergency_routine", FUNCTION_REGISTRY)