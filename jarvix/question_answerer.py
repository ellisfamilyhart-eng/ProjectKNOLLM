"""
Jarvix NoLLM - Question Answerer v2
Answers from memory; never recurse infinitely; uses lifecycle stages.
"""

from .memory_store import MemoryStore, STAGE_MASTERED


class QuestionAnswerer:
    """
    Answers questions from stored knowledge.
    Key differences from v1:
      - Searches across topics for keyword overlap, not just exact topic match
      - Returns confidence-annotated answers
      - Never triggers more learning/questioning (that is the brain's job)
    """

    # Question-word -> intent mapping
    _Q_TYPE = {
        "what": "factual", "which": "factual",
        "why":  "causal",
        "how":  "procedural",
        "when": "temporal",
        "where":"spatial",
        "who":  "entity",
        "is":   "yesno",  "are": "yesno",
        "do":   "yesno",  "does":"yesno",
        "can":  "yesno",  "could":"yesno",
    }

    _STOP_WORDS = {
        "what","why","how","when","where","who","which","is","are","do",
        "does","can","could","will","would","should","have","has","may",
        "might","about","the","a","an","tell","me","you","i",
    }

    def __init__(self, memory: MemoryStore, brain):
        self.memory = memory
        self.brain  = brain

    # -- Public: is this text a question? -------------------------------------

    def is_question(self, text: str) -> bool:
        t = text.strip()
        if t.endswith("?"):
            return True
        first = t.lower().split()[0] if t.split() else ""
        return first in self._Q_TYPE

    # -- Public: extract the keyword focus of a question -----------------------

    def extract_question_focus(self, question: str) -> str:
        words = question.replace("?", "").lower().split()
        focus = [w for w in words if w not in self._STOP_WORDS and len(w) > 1]
        return " ".join(focus[:4])

    # -- Public: answer --------------------------------------------------------

    def answer_question(self, question: str) -> str | None:
        if not self.is_question(question):
            return None

        focus  = self.extract_question_focus(question)
        q_type = self._Q_TYPE.get(question.lower().split()[0], "factual")

        if not focus:
            return None

        # 1. Try direct topic match
        facts = self.memory.get_facts_by_topic(focus)

        # 2. Fall back: search across all topics by keyword overlap
        if not facts:
            focus_words = set(focus.lower().split())
            best_topic  = None
            best_score  = 0
            for topic in self.memory.facts:
                t_words = set(topic.lower().split())
                score   = len(focus_words & t_words) / max(len(focus_words | t_words), 1)
                if score > best_score:
                    best_score = score
                    best_topic = topic
            if best_topic and best_score > 0.3:
                facts = self.memory.get_facts_by_topic(best_topic)
                focus = best_topic

        if not facts:
            return self._unknown(focus)

        # Dispatch by question type
        if q_type == "causal":
            return self._answer_causal(focus, facts)
        if q_type == "procedural":
            return self._answer_procedural(focus, facts)
        return self._answer_factual(focus, facts)

    # -- Answer builders -------------------------------------------------------

    def _answer_factual(self, topic: str, facts: list) -> str:
        lines = [f"Here's what I know about {topic}:"]
        for fact, conf in facts[:4]:
            marker = "✓" if conf >= 0.85 else ("~" if conf >= 0.6 else "?")
            lines.append(f"  {marker} {fact}  ({conf:.0%})")
        conf_avg = sum(c for _, c in facts[:4]) / min(4, len(facts))
        lines.append(f"\n  Overall confidence: {conf_avg:.0%}")
        return "\n".join(lines)

    def _answer_causal(self, topic: str, facts: list) -> str:
        lines = [f"Why {topic}? Based on what I know:"]
        for fact, conf in facts[:3]:
            lines.append(f"  - {fact}  ({conf:.0%})")
        return "\n".join(lines)

    def _answer_procedural(self, topic: str, facts: list) -> str:
        lines = [f"How {topic} works, as far as I know:"]
        for i, (fact, conf) in enumerate(facts[:4], 1):
            lines.append(f"  {i}. {fact}  ({conf:.0%})")
        return "\n".join(lines)

    def _unknown(self, focus: str) -> str:
        return (
            f"I don't know enough about '{focus}' yet.\n"
            f"Teach me with:  {focus}: [what it is]"
        )

    # -- Confidence helper -----------------------------------------------------

    def get_answer_confidence(self, topic: str) -> float:
        facts = self.memory.get_facts_by_topic(topic)
        if not facts:
            return 0.0
        avg = sum(c for _, c in facts) / len(facts)
        bonus = 0.1 if len(facts) >= 3 else 0.0
        return min(1.0, avg + bonus)
