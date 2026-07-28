"""
Jarvix Reasoner (Dynamic V3)
----------------------------
A highly dynamic, pluggable reasoning engine for KnowledgeGraphs.
Evaluates queries via extensible rules, relation semantics, and bi-directional traversal.
"""

from typing import Optional, List, Tuple, Dict, Any
from collections import deque
from abc import ABC, abstractmethod

# Adjust these imports based on your exact knowledge_graph.py structure
from .knowledge_graph import KnowledgeGraph, SELF, R_OPPOSITE, R_CAN


# ── Configuration & Semantics ─────────────────────────────────────────────────

CHAIN_DECAY = 0.90   # Confidence penalty per inference hop
MAX_DEPTH   = 5      # Maximum traversal depth
MIN_CONF    = 0.15   # Prune paths below this confidence

# Dynamic Semantic Matrix
# Defines how relations behave without hardcoding them into the logic.
RELATION_META = {
    "is_a":         {"transitive": True,  "inherits_properties": True,  "inverse": "subclass_of"},
    "part_of":      {"transitive": True,  "inherits_properties": False, "inverse": "has_part"},
    "causes":       {"transitive": True,  "inherits_properties": False, "inverse": "caused_by"},
    "located_in":   {"transitive": True,  "inherits_properties": False, "inverse": "contains"},
    "has_property": {"transitive": False, "inherits_properties": False, "inverse": "property_of"},
}


# ── Result Object ─────────────────────────────────────────────────────────────

class ReasonResult:
    """Holds the outcome of a reasoning query."""

    def __init__(self, query: str):
        self.query       = query
        self.answer      = None    # True / False / str / list / None
        self.confidence  = 0.0
        self.path: list  = []      # [(node, relation, node), ...]
        self.explanation: str = ""
        self.found       = False

    def set(self, answer: Any, confidence: float, path: list, explanation: str) -> "ReasonResult":
        self.answer      = answer
        self.confidence  = round(confidence, 3)
        self.path        = path
        self.explanation = explanation
        self.found       = True
        return self

    def __repr__(self) -> str:
        return (f"ReasonResult(answer={self.answer!r}, "
                f"conf={self.confidence:.0%}, found={self.found})")


# ── Reasoning Strategies (Rules) ──────────────────────────────────────────────

class ReasoningRule(ABC):
    """Base class for all reasoning strategies."""
    
    @abstractmethod
    def evaluate(self, reasoner: "DynamicReasoner", s: str, r: str, o: str) -> Optional[ReasonResult]:
        pass


class DirectLookupRule(ReasoningRule):
    """1. Checks if the fact is explicitly stored in the graph."""
    
    def evaluate(self, reasoner, s, r, o):
        conf = reasoner.graph.edge_confidence(s, r, o)
        if conf > 0:
            return ReasonResult(f"{s} {r} {o}?").set(
                True, conf, [(s, r, o)], f"I directly know: {s} {r} {o}."
            )
        return None


class TransitiveRule(ReasoningRule):
    """2. Dynamically traverses relations flagged as 'transitive' in RELATION_META."""
    
    def evaluate(self, reasoner, s, r, o):
        meta = RELATION_META.get(r, {})
        if not meta.get("transitive", False):
            return None

        path, conf = reasoner._bfs_transitive(s, r, o)
        if path:
            expl = " -> ".join(f"{a} {rel} {b}" for a, rel, b in path)
            return ReasonResult(f"{s} {r} {o}?").set(
                True, conf, path, f"By inference: {expl}."
            )
        return None


class PropertyInheritanceRule(ReasoningRule):
    """3. Checks if a property is inherited from parent classes."""
    
    def evaluate(self, reasoner, s, r, o):
        if r != "has_property":
            return None

        # Dynamically find all relations that allow property inheritance (e.g., 'is_a')
        inheritance_rels = [
            rel for rel, meta in RELATION_META.items() 
            if meta.get("inherits_properties", False)
        ]

        visited = set()
        queue = deque([(s, 1.0, [])])

        while queue:
            node, conf, path = queue.popleft()
            if node in visited:
                continue
            visited.add(node)

            # Direct check
            p_conf = reasoner.graph.edge_confidence(node, "has_property", o)
            if p_conf > 0:
                full_path = path + [(node, "has_property", o)]
                return ReasonResult(f"{s} has_property {o}?").set(
                    True, conf * p_conf, full_path, 
                    f"{s} inherits '{o}' from '{node}'."
                )

            # Walk up inheritance relations
            for rel in inheritance_rels:
                for _, parent, e_conf in reasoner.graph.get_outgoing(node, rel):
                    if parent not in visited:
                        new_conf = conf * e_conf * CHAIN_DECAY
                        queue.append((parent, new_conf, path + [(node, rel, parent)]))

        return None


class CapabilityRule(ReasoningRule):
    """4. Self-awareness capability checks."""
    
    def evaluate(self, reasoner, s, r, o):
        if s != SELF.lower() or r != R_CAN.lower():
            return None
            
        result = ReasonResult(f"Can Jarvix {o}?")
        
        can_conf = reasoner.graph.edge_confidence(SELF, R_CAN, o)
        if can_conf > 0:
            return result.set(True, can_conf, [(SELF, R_CAN, o)], f"Yes, I can {o}.")
            
        cannot_conf = reasoner.graph.edge_confidence(SELF, R_OPPOSITE, o)
        if cannot_conf > 0:
            return result.set(False, cannot_conf, [(SELF, R_OPPOSITE, o)], f"No, I cannot {o}.")

        # Fuzzy matching
        for rel, cap, conf in reasoner.graph.get_outgoing(SELF, R_CAN):
            if o in cap or cap in o:
                return result.set(True, conf * 0.8, [(SELF, R_CAN, cap)], 
                                  f"I can {cap}, which is related to {o}.")
        return None


# ── Core Engine ───────────────────────────────────────────────────────────────

class DynamicReasoner:
    """The central engine that applies strategies to graph data."""

    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph
        self.rules: List[ReasoningRule] = []
        self._register_default_rules()

    def _register_default_rules(self):
        # Order matters: Direct -> Transitive -> Inheritance -> Capability
        self.register_rule(DirectLookupRule())
        self.register_rule(TransitiveRule())
        self.register_rule(PropertyInheritanceRule())
        self.register_rule(CapabilityRule())

    def register_rule(self, rule: ReasoningRule):
        """Inject new reasoning strategies dynamically."""
        self.rules.append(rule)

    def can_self(self, task_or_query: str) -> ReasonResult:
        """
        Direct capability evaluator for self-reasoning checks.
        Prevents AttributeError when external callers evaluate system capabilities.
        """
        query_str = task_or_query.lower().strip()
        
        # Check explicit graph capability rules
        result = self.query(SELF, R_CAN, query_str)
        if result.found:
            return result

        # Fallback check against outgoing capability edges
        for rel, cap, conf in self.graph.get_outgoing(SELF, R_CAN):
            if query_str in cap.lower() or cap.lower() in query_str:
                return ReasonResult(f"Can Jarvix {query_str}?").set(
                    True, conf * 0.85, [(SELF, R_CAN, cap)],
                    f"I have the capability '{cap}', which covers this task."
                )

        # Default fallback
        res = ReasonResult(f"Can Jarvix {query_str}?")
        res.explanation = f"I do not currently have explicit record of being able to {query_str}."
        return res

    def can_handle(self, text: str) -> bool:
        """Alias helper method for dispatchers to query engine capability."""
        res = self.can_self(text)
        return bool(res.found and res.answer)

    def query(self, subject: str, relation: Optional[str] = None, obj: Optional[str] = None) -> ReasonResult:
        """
        Run through all registered rules until one succeeds.
        Supports single-string queries by routing to self-capability evaluation.
        """
        if relation is None and obj is None:
            return self.can_self(subject)

        s = subject.lower().strip()
        r = (relation or "").lower().strip()
        o = (obj or "").lower().strip()
        
        for rule in self.rules:
            result = rule.evaluate(self, s, r, o)
            if result and result.found:
                return result

        # Fallback if no rules succeed
        res = ReasonResult(f"{s} {r} {o}?")
        res.explanation = f"I don't know whether {s} {r} {o}."
        return res

    # ── Traversal Methods ─────────────────────────────────────────────────────

    def _bfs_transitive(self, start: str, relation: str, target: str) -> Tuple[list, float]:
        """Standard directed BFS for transitive rule tracking."""
        if start == target:
            return [], 1.0

        best_conf: Dict[str, float] = {start: 1.0}
        queue = deque([(start, 1.0, [])])

        while queue:
            node, conf, path = queue.popleft()

            if conf < MIN_CONF or len(path) >= MAX_DEPTH:
                continue

            for rel, neighbour, edge_conf in self.graph.get_outgoing(node, relation):
                new_conf = conf * edge_conf * CHAIN_DECAY

                if new_conf <= best_conf.get(neighbour, 0.0):
                    continue

                best_conf[neighbour] = new_conf
                new_path = path + [(node, rel, neighbour)]

                if neighbour == target:
                    return new_path, new_conf

                queue.append((neighbour, new_conf, new_path))

        return [], 0.0

    def find_path(self, start: str, end: str) -> Tuple[list, float]:
        """
        Bi-directional BFS. 
        Massively faster for finding any connecting path in dense graphs.
        Requires `self.graph.get_incoming()` to be implemented.
        """
        s, e = start.lower(), end.lower()
        if s == e:
            return [], 1.0

        fwd_visited = {s: (1.0, [])}  # node -> (confidence, path_to_node)
        bwd_visited = {e: (1.0, [])}  # node -> (confidence, path_from_node_to_end)

        fwd_queue = deque([s])
        bwd_queue = deque([e])

        while fwd_queue and bwd_queue:
            # 1. Step Forward
            curr_fwd = fwd_queue.popleft()
            f_conf, f_path = fwd_visited[curr_fwd]

            if f_conf >= MIN_CONF and len(f_path) < MAX_DEPTH:
                for rel, nxt, e_conf in self.graph.get_outgoing(curr_fwd):
                    new_conf = f_conf * e_conf * CHAIN_DECAY
                    
                    if nxt not in fwd_visited or fwd_visited[nxt][0] < new_conf:
                        new_path = f_path + [(curr_fwd, rel, nxt)]
                        fwd_visited[nxt] = (new_conf, new_path)
                        fwd_queue.append(nxt)

                        # Intersection found!
                        if nxt in bwd_visited:
                            b_conf, b_path = bwd_visited[nxt]
                            return new_path + b_path, new_conf * b_conf

            # 2. Step Backward
            curr_bwd = bwd_queue.popleft()
            b_conf, b_path = bwd_visited[curr_bwd]

            if b_conf >= MIN_CONF and len(b_path) < MAX_DEPTH:
                # Assuming graph has get_incoming(node) -> yields (relation, incoming_node, conf)
                for rel, prev, e_conf in getattr(self.graph, "get_incoming", lambda x: [])(curr_bwd):
                    new_conf = b_conf * e_conf * CHAIN_DECAY
                    
                    if prev not in bwd_visited or bwd_visited[prev][0] < new_conf:
                        new_path = [(prev, rel, curr_bwd)] + b_path
                        bwd_visited[prev] = (new_conf, new_path)
                        bwd_queue.append(prev)

                        # Intersection found!
                        if prev in fwd_visited:
                            f_conf, f_path = fwd_visited[prev]
                            return f_path + new_path, f_conf * new_conf

        return [], 0.0

    # ── Inference & Analytics ─────────────────────────────────────────────────

    def run_forward_inference(self) -> List[Tuple[str, str, str, float]]:
        """
        Dynamically infers new facts based on RELATION_META.
        Loops until no new facts are found (multi-hop capable).
        """
        new_facts = []
        transitive_rels = [r for r, meta in RELATION_META.items() if meta.get("transitive")]

        while True:
            added_in_pass = 0
            
            for rel in transitive_rels:
                rel_edges = [(s, o, data.confidence)
                             for (s, r, o), data in self.graph.edges.items()
                             if r == rel]

                for src_subj, mid_node, c1 in rel_edges:
                    for target_subj, target_obj, c2 in rel_edges:
                        if target_subj == mid_node and target_obj != src_subj:
                            derived_conf = c1 * c2 * CHAIN_DECAY
                            
                            if derived_conf >= MIN_CONF:
                                if not self.graph.has_edge(src_subj, rel, target_obj):
                                    self.graph.add_edge(src_subj, rel, target_obj,
                                                        confidence=derived_conf,
                                                        inferred=True,
                                                        source="inference")
                                    new_facts.append((src_subj, rel, target_obj, derived_conf))
                                    added_in_pass += 1
            
            # Stop if no new facts were derived in this pass
            if added_in_pass == 0:
                break

        return new_facts

    def detect_contradictions(self) -> List[Dict[str, Any]]:
        """Scans for logical conflicts (e.g., A is_a B, A opposite_of B)."""
        contradictions = []

        for (s, r, o), data in self.graph.edges.items():
            opp = self.graph.edge_confidence(s, R_OPPOSITE, o)
            if opp > 0.3:
                contradictions.append({
                    "subject":              s,
                    "claim":                f"{s} {r} {o}",
                    "conflict":             f"{s} opposite_of {o}",
                    "confidence_claim":    data.confidence,
                    "confidence_conflict": opp,
                })

        return contradictions

    def describe(self, concept: str) -> List[Dict[str, Any]]:
        """Gathers direct facts and all dynamically inherited properties."""
        c = concept.lower()
        rows = []

        # Simple pluralization check fallback
        candidates = {c, c[:-1] if c.endswith('s') else c + 's'}

        for candidate in candidates:
            # Direct facts
            for rel, obj, conf in self.graph.get_outgoing(candidate):
                rows.append({"relation": rel, "object": obj,
                             "confidence": conf, "inferred": False})

            # Evaluate against property inheritance rule manually to get parents
            inheritance_rels = [
                r for r, meta in RELATION_META.items() if meta.get("inherits_properties")
            ]
            
            for rel in inheritance_rels:
                for _, parent, p_conf in self.graph.get_outgoing(candidate, rel):
                    for rel2, obj2, conf2 in self.graph.get_outgoing(parent, "has_property"):
                        iconf = p_conf * conf2 * CHAIN_DECAY
                        if iconf >= MIN_CONF:
                            rows.append({"relation": f"has_property (from {parent})",
                                         "object": obj2, "confidence": iconf,
                                         "inferred": True})

        # Deduplicate and sort
        unique_rows = {f"{r['relation']}-{r['object']}": r for r in rows}
        sorted_rows = sorted(unique_rows.values(), key=lambda x: -x["confidence"])
        return sorted_rows


# ── Export Aliases ─────────────────────────────────────────────────────────────
# Guarantees backwards and forwards compatibility across all jarvix imports.
Reasoner = DynamicReasoner
ReasoningEngine = DynamicReasoner