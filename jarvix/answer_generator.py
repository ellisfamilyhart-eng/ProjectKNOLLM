"""
Jarvix Answer Generator
-----------------------
Converts Reasoner / Planner results into natural language responses.

Handles:
  - Description answers   "Here is what I know about X..."
  - Yes/No answers        "Yes, cats are animals (86% confident)."
  - Path answers          "X is related to Z through Y."
  - Capability answers    "Yes, I can read text."
  - Unknown answers       "I haven't learned about X yet."
  - Contradiction alerts  "I have conflicting beliefs about X."
"""

from .knowledge_graph import (
    R_IS_A, R_HAS_PROP, R_HAS, R_CAN, R_DOES,
    R_PART_OF, R_CAUSES, R_OPPOSITE, R_RELATED, SELF,
)
from .reasoner import ReasonResult


# ── Relation -> readable phrase ───────────────────────────────────────────────

RELATION_PHRASES = {
    R_IS_A:        "is a type of",
    R_HAS_PROP:    "has the property",
    R_HAS:         "has",
    R_CAN:         "can",
    R_DOES:        "does",
    R_PART_OF:     "is part of",
    R_CAUSES:      "causes",
    R_OPPOSITE:    "is the opposite of / cannot",
    R_RELATED:     "is related to",
}

def _rel_phrase(rel: str) -> str:
    # Strip inheritance annotation  "has_property (from mammal)" -> "has_property"
    base = rel.split("(")[0].strip()
    return RELATION_PHRASES.get(base, rel)

def _conf_label(conf: float) -> str:
    if conf >= 0.90: return "very confident"
    if conf >= 0.75: return "fairly confident"
    if conf >= 0.55: return "somewhat confident"
    return "uncertain"


# ── Generator ─────────────────────────────────────────────────────────────────

class AnswerGenerator:
    """
    Produces human-readable answers from Planner/Reasoner results.
    """

    def generate(self, results: list, original_question: str = "") -> str:
        """
        Main entry.  results = list[ReasonResult] from Planner.plan_and_execute()
        """
        if not results:
            return "I don't have enough information to answer that yet."

        best = results[0]   # highest confidence, found=True preferred

        # ── Not found at all ──────────────────────────────────────────────
        if not best.found:
            focus = self._extract_focus(original_question)
            return self._unknown(focus)

        # ── Dispatch by answer type ───────────────────────────────────────
        answer = best.answer

        # Description (list of fact dicts)
        if isinstance(answer, list) and answer and isinstance(answer[0], dict):
            return self._describe(best, answer)

        # Path (list of (s, rel, o) tuples)
        if isinstance(answer, list) and answer and isinstance(answer[0], tuple):
            return self._path_answer(best, answer)

        # Boolean yes/no
        if isinstance(answer, bool):
            return self._yesno(best, answer)

        # Fallback
        return best.explanation or str(answer)

    # ── Formatters ────────────────────────────────────────────────────────────

    def _describe(self, result: ReasonResult, facts: list) -> str:
        concept = result.query.replace("describe ", "").strip()
        lines   = [f"Here is what I know about '{concept}':"]

        for f in facts[:8]:
            rel  = _rel_phrase(f["relation"])
            obj  = f["object"]
            conf = f["confidence"]
            tag  = "(inferred)" if f.get("inferred") else ""
            lines.append(f"  - {concept} {rel} {obj}  "
                         f"[{conf:.0%}] {tag}".rstrip())

        # Show what we inferred via inheritance
        inherited = [f for f in facts if f.get("inferred")]
        if inherited:
            lines.append(f"\n  (+ {len(inherited)} inherited from parent concepts)")

        # Confidence summary
        avg = sum(f["confidence"] for f in facts) / len(facts)
        lines.append(f"\nOverall understanding: {avg:.0%} ({_conf_label(avg)})")
        return "\n".join(lines)

    def _yesno(self, result: ReasonResult, answer: bool) -> str:
        word  = "Yes" if answer else "No"
        conf  = result.confidence
        label = _conf_label(conf)

        # Build explanation from path
        expl = result.explanation
        if result.path:
            steps = []
            for item in result.path:
                if isinstance(item, tuple) and len(item) == 3:
                    s, r, o = item
                    steps.append(f"{s} {_rel_phrase(r)} {o}")
            if steps:
                expl = " -> ".join(steps)

        return f"{word}, {expl}  [{conf:.0%}, {label}]"

    def _path_answer(self, result: ReasonResult, path: list) -> str:
        if not path:
            return result.explanation

        steps = []
        for item in path:
            if isinstance(item, tuple) and len(item) == 3:
                s, r, o = item
                steps.append(f"{s} {_rel_phrase(r)} {o}")

        chain = " -> ".join(steps)
        return (f"They are connected:  {chain}  "
                f"[{result.confidence:.0%} confidence]")

    def _unknown(self, focus: str) -> str:
        if not focus or focus == "unknown":
            return "I don't have enough information to answer that yet."
        return (
            f"I haven't learned about '{focus}' yet.\n"
            f"Teach me:  {focus}: [what it is]"
        )

    # ── Teaching confirmation ─────────────────────────────────────────────────

    def confirm_learning(self, sentence, graph_result: dict) -> str:
        """
        Generate a confirmation after storing a new SVO triple.
        """
        subj = sentence.subject
        rel  = _rel_phrase(sentence.relation_type)
        obj  = sentence.object_
        conf = graph_result.get("confidence", 0.7)
        stage = graph_result.get("stage", "stored")

        lines = []

        if sentence.negated:
            lines.append(f"Understood: {subj} is NOT {obj}.  Stored as contradiction.")
        else:
            lines.append(f"Stored: {subj} {rel} {obj}  [{conf:.0%}]")

        # Show if inference fired
        new_inferred = graph_result.get("inferred_count", 0)
        if new_inferred:
            lines.append(f"  -> {new_inferred} new fact(s) inferred automatically.")

        # Mastery note
        if stage == "mastered":
            lines.append(f"  -> I now understand '{subj}' well.")

        return "\n".join(lines)

    def contradiction_alert(self, contradiction: dict) -> str:
        subj = contradiction["subject"]
        c1   = contradiction["claim"]
        c2   = contradiction["conflict"]
        return (
            f"Conflict detected about '{subj}':\n"
            f"  I believe: {c1}\n"
            f"  But also:  {c2}\n"
            f"  Which is correct?"
        )

    # ── Inference summary ─────────────────────────────────────────────────────

    def summarise_inference(self, new_facts: list) -> str:
        if not new_facts:
            return ""
        lines = [f"I inferred {len(new_facts)} new fact(s):"]
        for s, r, o, conf in new_facts[:5]:
            lines.append(f"  - {s} {_rel_phrase(r)} {o}  [{conf:.0%}]")
        return "\n".join(lines)

    # ── Utility ───────────────────────────────────────────────────────────────

    def _extract_focus(self, question: str) -> str:
        stop = {"what","is","are","a","the","about","of","for","in","on",
                "to","me","how","why","does","do","can","tell","know","you"}
        words = question.replace("?", "").lower().split()
        focus = [w for w in words if w not in stop and len(w) > 1]
        return " ".join(focus[:3]) if focus else "unknown"
