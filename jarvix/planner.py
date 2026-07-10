"""
Jarvix Planner v2
-----------------
Decomposes a parsed Sentence into sub-queries for the Reasoner.

Routing table
  capability  sentence_type=="capability" OR verb=="can"
  describe    sentence_type=="question" + verb in IMPERATIVE_VERBS
              OR subject in (what, who, which)
  yesno       sentence_type=="question" + real subject + object
  path        verb in (related, connect, link)
  fallback    describe subject
"""

from .knowledge_graph import (
    KnowledgeGraph,
    R_IS_A, R_HAS_PROP, R_HAS, R_CAN,
    R_DOES, R_PART_OF, R_CAUSES, R_OPPOSITE, R_RELATED,
    SELF,
)
from .reasoner import Reasoner, ReasonResult
from .nlp_parser import Sentence, IMPERATIVE_VERBS


class Plan:
    def __init__(self, query_type: str, subject: str, relation: str, obj: str):
        self.query_type = query_type
        self.subject    = subject
        self.relation   = relation
        self.obj        = obj
        self.result: ReasonResult = None

    def __repr__(self):
        return f"Plan({self.query_type}: {self.subject!r} {self.relation!r} {self.obj!r})"


class Planner:
    """Translates a Sentence into Plans and executes them via the Reasoner."""

    def __init__(self, graph: KnowledgeGraph, reasoner: Reasoner):
        self.graph    = graph
        self.reasoner = reasoner

    # ── Main entry ────────────────────────────────────────────────────────────

    def plan_and_execute(self, sentence: Sentence) -> list:
        plans   = self._build_plans(sentence)
        results = [self._execute(p) for p in plans]
        # found first, then highest confidence
        results.sort(key=lambda r: (-int(r.found), -r.confidence))
        return results

    # ── Plan builder ──────────────────────────────────────────────────────────

    def _build_plans(self, s: Sentence) -> list:
        plans = []
        subj = s.subject.lower().strip()
        verb = s.verb.lower().strip()
        obj  = s.object_.lower().strip()

        # ── 1. Capability: "can X do Y?" ──────────────────────────
        if s.sentence_type == "capability" or verb == "can":
            actor = SELF if subj in ("you", "i", "me", "jarvix", SELF) else subj
            # obj may be a full phrase like "read sentences" — first word is enough
            action_core = obj.split()[0] if obj and obj != "unknown" else obj
            plans.append(Plan("capability", actor, R_CAN, action_core))
            if action_core != obj:
                plans.append(Plan("capability", actor, R_CAN, obj))  # full phrase too
            return plans

        # ── 2. Imperative description: "tell me about X" ──────────
        if verb in IMPERATIVE_VERBS and obj not in ("", "unknown"):
            plans.append(Plan("description", obj, "describe", obj))
            return plans

        # ── 3. "What / who / which is X?" ─────────────────────────
        if s.sentence_type == "question" and subj in ("what", "who", "which", "where"):
            concept = obj
            plans.extend(self._describe_plans(concept))
            return plans

        # ── 4. Yes/no question: "are cats animals?" ───────────────
        if s.sentence_type == "question" and subj not in (
                "what","who","which","where","when","why","how","unknown"):
            plans.extend(self._describe_plans(subj))
            if obj and obj != "unknown":
                plans.append(Plan("taxonomy", subj, R_IS_A,     obj))
                plans.append(Plan("property",  subj, R_HAS_PROP, obj))
            return plans

        # ── 5. Path: "how is X related to Y?" ────────────────────
        if verb in ("related", "connect", "link"):
            plans.append(Plan("path", subj, "path", obj))
            return plans

        # ── 6. Statement fallback: describe subject ───────────────
        if subj not in ("unknown",):
            plans.extend(self._describe_plans(subj))

        if not plans:
            plans.append(Plan("unknown", subj, verb, obj))

        return plans

    def _describe_plans(self, concept: str) -> list:
        """
        Build description plans for concept and its singular/plural variant.
        """
        plans = [Plan("description", concept, "describe", concept)]
        # singular/plural fallback
        alt = concept[:-1] if concept.endswith("s") else concept + "s"
        if alt != concept:
            plans.append(Plan("description", alt, "describe", alt))
        return plans

    # ── Plan executor ─────────────────────────────────────────────────────────

    def _execute(self, plan: Plan) -> ReasonResult:
        s, r, o = plan.subject, plan.relation, plan.obj

        if plan.query_type == "capability":
            if s == SELF:
                return self.reasoner.can_self(o)
            return self.reasoner.query(s, R_CAN, o)

        if plan.query_type == "description":
            facts  = self.reasoner.describe(s)
            result = ReasonResult(f"describe {s}")
            if facts:
                result.set(facts, max(f["confidence"] for f in facts),
                           [], f"I know {len(facts)} things about {s}.")
            else:
                result.explanation = f"I don't know anything about '{s}' yet."
            return result

        if plan.query_type == "path":
            path, conf = self.reasoner.find_path(s, o)
            result = ReasonResult(f"path {s} -> {o}")
            if path:
                result.set(path, conf, path,
                           " -> ".join(f"{a} {rel} {b}" for a, rel, b in path))
            else:
                result.explanation = f"I can't find a connection from '{s}' to '{o}'."
            return result

        if plan.query_type in ("taxonomy", "property"):
            return self.reasoner.query(s, r, o)

        return self.reasoner.query(s, r, o)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def check_contradictions(self) -> list:
        return self.reasoner.detect_contradictions()

    def infer_new_facts(self) -> list:
        return self.reasoner.run_forward_inference()
