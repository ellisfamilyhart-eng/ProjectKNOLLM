"""
Jarvix - Logic Engine
Forward-chaining symbolic inference over SemanticMemory.

Rules implemented
  1. Transitivity (is_a)   A is_a B, B is_a C  =>  A is_a C
  2. Transitivity (part_of) A part_of B, B part_of C  =>  A part_of C
  3. Property inheritance   A is_a B, B has_property P  =>  A has_property P
  4. Capability inheritance A is_a B, B can V  =>  A can V
  5. Cause chain            A causes B, B causes C  =>  A causes C (weaker)
  6. Custom user rules      if-then rules stored at runtime

Confidence propagation
  inferred_conf = conf(A->B) * conf(B->C) * CHAIN_DECAY
  Never infer if result would be below MIN_INFER_CONF.
"""

from dataclasses import dataclass, field
from typing import Callable
from .semantic_memory import (
    SemanticMemory, SemanticEdge,
    R_IS_A, R_HAS_PROP, R_HAS, R_CAN, R_DOES,
    R_PART_OF, R_CAUSES, R_OPPOSITE, R_RELATED,
)

CHAIN_DECAY     = 0.90   # confidence penalty per inference hop
MIN_INFER_CONF  = 0.20   # don't store inferences weaker than this
MAX_DEPTH       = 5      # maximum inference chain length


# ── Rule model ────────────────────────────────────────────────────────────────

@dataclass
class InferenceRule:
    """
    A single symbolic rule.
    premise_relation  : relation that must hold on the left
    conclusion_relation: relation to derive on the right
    decay             : extra confidence multiplier for this rule
    description       : human-readable rule label
    """
    name:                 str
    premise_relation:     str
    link_relation:        str    # relation connecting premise to conclusion chain
    conclusion_relation:  str
    decay:                float = CHAIN_DECAY
    description:          str   = ""


@dataclass
class InferenceResult:
    subject:    str
    relation:   str
    object_:    str
    confidence: float
    path:       list   # list of SemanticEdge that produced this result
    rule_name:  str

    def __repr__(self):
        return (f"Infer({self.subject} {self.relation} {self.object_}  "
                f"{self.confidence:.0%} via {self.rule_name})")


# ── Logic Engine ──────────────────────────────────────────────────────────────

class LogicEngine:
    """
    Symbolic forward-chaining inference engine.
    Operates over SemanticMemory; adds inferred edges back into it.
    """

    # Built-in rule library
    BUILTIN_RULES: list[InferenceRule] = [
        InferenceRule(
            name="is_a_transitivity",
            premise_relation=R_IS_A,
            link_relation=R_IS_A,
            conclusion_relation=R_IS_A,
            decay=CHAIN_DECAY,
            description="A is_a B, B is_a C => A is_a C",
        ),
        InferenceRule(
            name="part_of_transitivity",
            premise_relation=R_PART_OF,
            link_relation=R_PART_OF,
            conclusion_relation=R_PART_OF,
            decay=CHAIN_DECAY,
            description="A part_of B, B part_of C => A part_of C",
        ),
        InferenceRule(
            name="property_inheritance",
            premise_relation=R_IS_A,
            link_relation=R_HAS_PROP,
            conclusion_relation=R_HAS_PROP,
            decay=CHAIN_DECAY * 0.95,
            description="A is_a B, B has_property P => A has_property P",
        ),
        InferenceRule(
            name="capability_inheritance",
            premise_relation=R_IS_A,
            link_relation=R_CAN,
            conclusion_relation=R_CAN,
            decay=CHAIN_DECAY * 0.90,
            description="A is_a B, B can V => A can V",
        ),
        InferenceRule(
            name="cause_chain",
            premise_relation=R_CAUSES,
            link_relation=R_CAUSES,
            conclusion_relation=R_CAUSES,
            decay=CHAIN_DECAY * 0.80,
            description="A causes B, B causes C => A causes C (weakened)",
        ),
    ]

    def __init__(self, semantic_memory: SemanticMemory):
        self.memory     = semantic_memory
        self.rules      = list(self.BUILTIN_RULES)
        self._user_rules: list = []   # user-added if-then rules

    # ── Forward inference pass ────────────────────────────────────────────────

    def run(self) -> list[InferenceResult]:
        """
        One complete forward-chaining pass over all rules.
        Returns list of newly derived InferenceResults.
        All new facts are written back into semantic_memory as inferred edges.
        """
        new_facts: list[InferenceResult] = []

        for rule in self.rules:
            new_facts.extend(self._apply_rule(rule))

        # Apply custom user rules
        for rule_fn in self._user_rules:
            try:
                results = rule_fn(self.memory)
                if results:
                    new_facts.extend(results)
            except Exception:
                pass

        return new_facts

    def run_focused(self, concept: str) -> list[InferenceResult]:
        """
        Run inference only on edges involving a specific concept.
        Faster for incremental updates after teaching.
        """
        new_facts = []
        for rule in self.rules:
            new_facts.extend(self._apply_rule(rule, focus=concept))
        return new_facts

    # ── Rule application ──────────────────────────────────────────────────────

    def _apply_rule(self, rule: InferenceRule,
                    focus: str = None) -> list[InferenceResult]:
        """
        For a rule  (P_rel, L_rel, C_rel):
          Find all (A, P_rel, B)
          For each, find all (B, L_rel, C)
          Derive  (A, C_rel, C)  with  conf(A->B) * conf(B->C) * rule.decay
        """
        results = []
        edges = self.memory.edges

        # Step 1: gather premise edges
        premise_edges = [
            e for e in edges.values()
            if e.relation == rule.premise_relation
            and (focus is None or e.subject == focus or e.object_ == focus)
            and not e.inferred   # only chain from user-taught facts
        ]

        for p_edge in premise_edges:
            A = p_edge.subject
            B = p_edge.object_

            # Step 2: find link edges from B
            link_edges = [
                e for e in edges.values()
                if e.subject == B and e.relation == rule.link_relation
            ]

            for l_edge in link_edges:
                C = l_edge.object_
                if C == A:
                    continue   # no self-loops

                derived_conf = p_edge.confidence * l_edge.confidence * rule.decay

                if derived_conf < MIN_INFER_CONF:
                    continue

                key = (A, rule.conclusion_relation, C)

                # Already known (user-taught) with higher confidence?
                existing = edges.get(key)
                if existing and not existing.inferred:
                    continue   # don't overwrite user facts
                if existing and existing.confidence >= derived_conf:
                    continue   # already have a better inferred version

                # Write to semantic memory
                self.memory.add_edge(
                    A, rule.conclusion_relation, C,
                    confidence=derived_conf,
                    source="inference",
                    inferred=True,
                )

                result = InferenceResult(
                    subject    = A,
                    relation   = rule.conclusion_relation,
                    object_    = C,
                    confidence = derived_conf,
                    path       = [p_edge, l_edge],
                    rule_name  = rule.name,
                )
                results.append(result)

        return results

    # ── Direct query ──────────────────────────────────────────────────────────

    def can_derive(self, subject: str, relation: str,
                   object_: str) -> tuple[bool, float, list]:
        """
        Check if (subject, relation, object_) is derivable — directly or via chain.
        Returns (found, confidence, path).
        """
        s = subject.lower()
        o = object_.lower()
        r = relation.lower()

        # Direct
        e = self.memory.get_edge(s, r, o)
        if e:
            return True, e.confidence, [e]

        # BFS through transitive relations
        if r in (R_IS_A, R_PART_OF, R_HAS_PROP, R_CAN):
            found, conf, path = self._bfs_derive(s, r, o)
            if found:
                return True, conf, path

        return False, 0.0, []

    def _bfs_derive(self, start: str, target_rel: str,
                    target: str, max_depth: int = MAX_DEPTH
                    ) -> tuple[bool, float, list]:
        from collections import deque
        visited = {start}
        queue   = deque([(start, 1.0, [])])

        # Determine which relation(s) to traverse
        traverse_rels = {target_rel}
        # is_a chains also support property/capability inheritance
        if target_rel == R_HAS_PROP:
            traverse_rels = {R_IS_A}
        elif target_rel == R_CAN:
            traverse_rels = {R_IS_A}

        while queue:
            node, conf, path = queue.popleft()
            if len(path) >= max_depth:
                continue

            for edge in self.memory.outgoing(node):
                if edge.relation not in traverse_rels:
                    continue
                mid = edge.object_
                if mid in visited:
                    continue
                visited.add(mid)
                new_conf = conf * edge.confidence * CHAIN_DECAY
                new_path = path + [edge]

                # Check: does mid have the target relation to target?
                link = self.memory.get_edge(mid, target_rel, target)
                if link:
                    final_conf = new_conf * link.confidence * CHAIN_DECAY
                    if final_conf >= MIN_INFER_CONF:
                        return True, final_conf, new_path + [link]

                if new_conf >= MIN_INFER_CONF:
                    queue.append((mid, new_conf, new_path))

        return False, 0.0, []

    # ── User-defined rules ────────────────────────────────────────────────────

    def add_rule(self, rule_fn: Callable):
        """
        Add a custom rule function.
        Signature: rule_fn(semantic_memory: SemanticMemory) -> list[InferenceResult]
        """
        self._user_rules.append(rule_fn)

    # ── Explanation ───────────────────────────────────────────────────────────

    def explain(self, subject: str, relation: str, object_: str) -> str:
        """Human-readable explanation of how a fact was derived."""
        found, conf, path = self.can_derive(subject, relation, object_)
        if not found:
            return f"I cannot derive '{subject} {relation} {object_}'."

        if not path:
            return f"I know directly: {subject} {relation} {object_} ({conf:.0%})."

        steps = []
        for e in path:
            steps.append(f"{e.subject} {e.relation} {e.object_} ({e.confidence:.0%})")
        chain = " -> ".join(steps)
        return (f"Because: {chain}\n"
                f"Therefore: {subject} {relation} {object_} ({conf:.0%})")

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        return {
            "builtin_rules":  len(self.rules),
            "custom_rules":   len(self._user_rules),
        }
