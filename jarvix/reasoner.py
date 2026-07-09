"""
Jarvix Reasoner
---------------
Operates over KnowledgeGraph to answer questions without LLMs.

Capabilities
  - Direct lookup           "Is X Y?"
  - Transitive inference    A->B, B->C => A->C  (is_a / part_of chains)
  - Property inheritance    subclass inherits parent's properties
  - Capability check        "Can X do Y?"  (self-awareness)
  - Path finding            How is X related to Z?
  - Contradiction detection X is_a Y vs X is_a NOT-Y

Confidence propagates multiplicatively along chains:
  conf(A->C) = conf(A->B) * conf(B->C) * CHAIN_DECAY
"""

from typing import Optional
from collections import deque
from .knowledge_graph import (
    KnowledgeGraph, EdgeData,
    R_IS_A, R_HAS_PROP, R_HAS, R_CAN, R_DOES,
    R_PART_OF, R_CAUSES, R_OPPOSITE, R_RELATED, R_INSTANCE_OF,
    TRANSITIVE_RELATIONS, SELF,
)

CHAIN_DECAY   = 0.90   # confidence penalty per inference hop
MAX_DEPTH     = 5      # maximum traversal depth
MIN_CONF      = 0.15   # prune paths below this confidence


# ── Result object ─────────────────────────────────────────────────────────────

class ReasonResult:
    """Holds the outcome of a reasoning query."""

    def __init__(self, query: str):
        self.query      = query
        self.answer     = None    # True / False / str / list / None
        self.confidence = 0.0
        self.path: list = []      # [(node, relation, node), …]
        self.explanation: str = ""
        self.found      = False

    def set(self, answer, confidence: float, path: list, explanation: str):
        self.answer     = answer
        self.confidence = round(confidence, 3)
        self.path       = path
        self.explanation = explanation
        self.found      = True
        return self

    def __repr__(self):
        return (f"ReasonResult(answer={self.answer!r}, "
                f"conf={self.confidence:.0%}, found={self.found})")


# ── Reasoner ──────────────────────────────────────────────────────────────────

class Reasoner:
    """
    All reasoning operates over KnowledgeGraph.
    No string matching—pure graph traversal.
    """

    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph

    # ── Main entry ────────────────────────────────────────────────────────────

    def query(self, subject: str, relation: str, obj: str) -> ReasonResult:
        """
        Ask: does (subject, relation, obj) hold?
        Tries in order:
          1. Direct edge lookup
          2. Transitive chain (for is_a / part_of)
          3. Property inheritance from parent classes
        """
        s = subject.lower().strip()
        r = relation.lower().strip()
        o = obj.lower().strip()
        result = ReasonResult(f"{s} {r} {o}?")

        # 1. Direct
        direct = self._direct(s, r, o)
        if direct is not None:
            return result.set(True, direct, [(s, r, o)],
                              f"I directly know: {s} {r} {o}.")

        # 2. Transitive chain (only for transitive relation types)
        if r in TRANSITIVE_RELATIONS:
            path, conf = self._transitive(s, r, o)
            if path:
                expl = " -> ".join(f"{a} {rel} {b}"
                                   for a, rel, b in path)
                return result.set(True, conf, path,
                                  f"By inference: {expl}.")

        # 3. Inherited property
        if r == R_HAS_PROP:
            inherited = self._inherit_property(s, o)
            if inherited:
                path, conf = inherited
                return result.set(True, conf, path,
                                  f"{s} inherits '{o}' from its parent class.")

        # Not found
        result.explanation = f"I don't know whether {s} {r} {o}."
        return result

    # ── Direct lookup ─────────────────────────────────────────────────────────

    def _direct(self, s: str, r: str, o: str) -> Optional[float]:
        """Return confidence if edge exists, else None."""
        conf = self.graph.edge_confidence(s, r, o)
        return conf if conf > 0 else None

    # ── Transitive BFS ────────────────────────────────────────────────────────

    def _transitive(self, start: str, relation: str, target: str
                    ) -> tuple[list, float]:
        """
        BFS from start following `relation` edges.
        Returns (path_list, confidence) or ([], 0).

        path_list: [(s, rel, o), ...]
        """
        if start == target:
            return [], 1.0

        visited = {start}
        # queue items: (current_node, running_conf, path)
        queue = deque([(start, 1.0, [])])

        while queue:
            node, conf, path = queue.popleft()

            if conf < MIN_CONF or len(path) >= MAX_DEPTH:
                continue

            for rel, neighbour, edge_conf in self.graph.get_outgoing(node, relation):
                if neighbour in visited:
                    continue
                visited.add(neighbour)

                new_conf = conf * edge_conf * CHAIN_DECAY
                new_path = path + [(node, rel, neighbour)]

                if neighbour == target:
                    return new_path, new_conf

                queue.append((neighbour, new_conf, new_path))

        return [], 0.0

    # ── Property inheritance ──────────────────────────────────────────────────

    def _inherit_property(self, concept: str, prop: str
                          ) -> Optional[tuple[list, float]]:
        """
        Walk up the is_a hierarchy; return (path, conf) if any ancestor
        has the property, else None.
        """
        visited = set()
        queue   = deque([(concept, 1.0, [])])

        while queue:
            node, conf, path = queue.popleft()
            if node in visited:
                continue
            visited.add(node)

            # Does this node have the property directly?
            p_conf = self.graph.edge_confidence(node, R_HAS_PROP, prop)
            if p_conf > 0:
                full_path = path + [(node, R_HAS_PROP, prop)]
                return full_path, conf * p_conf

            # Walk up
            for parent, p_conf2 in self.graph.get_parents(node):
                if parent not in visited:
                    queue.append((parent, conf * p_conf2 * CHAIN_DECAY,
                                  path + [(node, R_IS_A, parent)]))

        return None

    # ── Path finding ──────────────────────────────────────────────────────────

    def find_path(self, start: str, end: str) -> tuple[list, float]:
        """
        Find any path between start and end, regardless of relation type.
        Returns (path, confidence).
        """
        if start == end:
            return [], 1.0

        visited = {start.lower()}
        queue   = deque([(start.lower(), 1.0, [])])

        while queue:
            node, conf, path = queue.popleft()
            if conf < MIN_CONF or len(path) >= MAX_DEPTH:
                continue

            for rel, neighbour, edge_conf in self.graph.get_outgoing(node):
                if neighbour in visited:
                    continue
                visited.add(neighbour)

                new_conf = conf * edge_conf * CHAIN_DECAY
                new_path = path + [(node, rel, neighbour)]

                if neighbour == end.lower():
                    return new_path, new_conf

                queue.append((neighbour, new_conf, new_path))

        return [], 0.0

    # ── Capability check ─────────────────────────────────────────────────────

    def can_self(self, action: str) -> ReasonResult:
        """Answer 'Can Jarvix do X?'"""
        result = ReasonResult(f"Can Jarvix {action}?")

        can_conf    = self.graph.self_can(action)
        cannot_conf = self.graph.self_cannot(action)

        if can_conf is not None:
            return result.set(True, can_conf,
                              [(SELF, R_CAN, action)],
                              f"Yes, I can {action}.")
        if cannot_conf is not None:
            return result.set(False, cannot_conf,
                              [(SELF, R_OPPOSITE, action)],
                              f"No, I cannot {action}.")

        # General capability inference: can I do anything like this?
        all_caps = self.graph.get_capabilities(SELF)
        for cap, conf in all_caps:
            if action.lower() in cap or cap in action.lower():
                return result.set(True, conf * 0.8,
                                  [(SELF, R_CAN, cap)],
                                  f"I can {cap}, which is related to {action}.")

        result.explanation = f"I'm not sure whether I can {action}."
        return result

    # ── Inference: run all transitive rules ──────────────────────────────────

    def run_forward_inference(self) -> list:
        """
        One pass of forward chaining over transitive relations.
        Returns list of newly inferred (subj, rel, obj, conf) tuples.
        """
        new_facts = []

        for rel in TRANSITIVE_RELATIONS:
            # Collect all edges of this relation type
            rel_edges = [(s, o, data.confidence)
                         for (s, r, o), data in self.graph.edges.items()
                         if r == rel and not data.inferred]

            for s, mid, c1 in rel_edges:
                for s2, o, c2 in rel_edges:
                    if s2 == mid and o != s:
                        derived_conf = c1 * c2 * CHAIN_DECAY
                        if derived_conf >= MIN_CONF:
                            if not self.graph.has_edge(s, rel, o):
                                self.graph.add_edge(s, rel, o,
                                                    confidence=derived_conf,
                                                    inferred=True,
                                                    source="inference")
                                new_facts.append((s, rel, o, derived_conf))

        return new_facts

    # ── Contradiction detection ───────────────────────────────────────────────

    def detect_contradictions(self) -> list:
        """
        Find pairs of edges where one directly contradicts the other.
        Currently checks: (X is_a Y) and (X opposite_of Y).
        """
        contradictions = []

        for (s, r, o), data in self.graph.edges.items():
            if r == R_IS_A:
                opp = self.graph.edge_confidence(s, R_OPPOSITE, o)
                if opp > 0.3:
                    contradictions.append({
                        "subject":    s,
                        "claim":      f"{s} is_a {o}",
                        "conflict":   f"{s} opposite_of {o}",
                        "confidence_claim":    data.confidence,
                        "confidence_conflict": opp,
                    })

        return contradictions

    # ── What do we know about X? ──────────────────────────────────────────────

    def describe(self, concept: str) -> list:
        """Return all directly known and inherited facts about a concept."""
        c = concept.lower()
        rows = []

        # Try exact, then strip/add trailing 's' for singular/plural
        candidates = {c}
        if c.endswith('s'):  candidates.add(c[:-1])   # dogs -> dog
        else:                candidates.add(c + 's')   # dog  -> dogs

        for candidate in candidates:
            # Direct outgoing
            for rel, obj, conf in self.graph.get_outgoing(candidate):
                rows.append({"relation": rel, "object": obj,
                             "confidence": conf, "inferred": False})

            # Inherited properties
            for parent, p_conf in self.graph.get_parents(candidate):
                for rel2, obj2, conf2 in self.graph.get_outgoing(parent, R_HAS_PROP):
                    iconf = p_conf * conf2 * CHAIN_DECAY
                    if iconf >= MIN_CONF:
                        rows.append({"relation": f"{R_HAS_PROP} (from {parent})",
                                     "object": obj2, "confidence": iconf,
                                     "inferred": True})

        rows.sort(key=lambda x: -x["confidence"])
        return rows
