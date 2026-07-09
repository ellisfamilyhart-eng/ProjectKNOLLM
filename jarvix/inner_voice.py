"""
Jarvix - Inner Voice
====================
Continuously predicts the next likely fact/intent BEFORE responding,
measures prediction error against what actually arrived, and uses that
error signal to refine concept weights before the response is generated.

The response engine receives enriched context (predicted facts, confidence
adjustments, analogy hints) rather than raw triples, enabling:
  - Spelling-variant generalisation  ("colur" -> "color")
  - Analogy completion               ("X is to Y as A is to ?")
  - Arithmetic rules                 ("three + two = five")
  - Incomplete knowledge handling    (partial match -> hedged answer)

Architecture
------------
  InnerVoice sits between IntentClassifier and ResponseEngine.
  It does NOT replace the pipeline — it enriches the PipelineContext
  with a VoiceContext that every downstream module can optionally use.

  Input  -> [Classifier] -> [InnerVoice.pre_process()] -> [Pipeline]
  Output <- [InnerVoice.post_process()] <- [Pipeline result]

Prediction error drives learning
---------------------------------
  high error   -> concept is novel    -> lower confidence on related edges
  low error    -> concept is familiar -> boost confidence on related edges
  zero error   -> perfect prediction  -> slight boost, mark as stable
"""

from __future__ import annotations
import re
import math
from dataclasses import dataclass, field
from collections import defaultdict
from typing import Optional


# ── Voice Context ─────────────────────────────────────────────────────────────

@dataclass
class VoiceContext:
    """
    Enriched context produced by InnerVoice and consumed by ResponseEngine.
    Attached to PipelineContext before response generation.
    """
    # Predicted values (what InnerVoice expected)
    predicted_topic:    str   = ""
    predicted_intent:   int   = -1
    predicted_facts:    list  = field(default_factory=list)   # [(s,r,o,conf)]

    # Error signal
    prediction_error:   float = 0.0    # 0 = perfect, 1 = total surprise
    error_type:         str   = ""     # from PredictiveEngine error types

    # Generalisation hints for ResponseEngine
    spelling_corrected: str   = ""     # if input had a near-match concept
    analogy_hint:       str   = ""     # "X is to Y as A is to ?" completion
    partial_match:      list  = field(default_factory=list)   # near-miss facts
    confidence_boost:   float = 0.0    # amount added to relevant edges this turn
    hedged:             bool  = False  # True = answer should be qualified
    novel_concept:      bool  = False  # True = concept never seen before


# ── Fuzzy concept matcher ─────────────────────────────────────────────────────

def _trigrams(s: str) -> set:
    s = s.lower()
    return {s[i:i+3] for i in range(len(s) - 2)} if len(s) >= 3 else {s}

def _similarity(a: str, b: str) -> float:
    ta, tb = _trigrams(a), _trigrams(b)
    union  = len(ta | tb)
    return len(ta & tb) / union if union else 0.0

def fuzzy_match(query: str, candidates: list[str],
                threshold: float = 0.60) -> Optional[str]:
    """Return the best-matching candidate or None."""
    best, best_sim = None, 0.0
    for c in candidates:
        s = _similarity(query, c)
        if s > best_sim:
            best_sim, best = s, c
    return best if best_sim >= threshold else None


# ── Arithmetic evaluator ──────────────────────────────────────────────────────

_NUMBER_WORDS = {
    "zero":0,"one":1,"two":2,"three":3,"four":4,"five":5,
    "six":6,"seven":7,"eight":8,"nine":9,"ten":10,
    "eleven":11,"twelve":12,"thirteen":13,"fourteen":14,"fifteen":15,
    "sixteen":16,"seventeen":17,"eighteen":18,"nineteen":19,"twenty":20,
}
_NUM_RE = re.compile(
    r"(\w+)\s*(\+|plus|minus|-|times|multiplied by|\*|divided by|/)\s*(\w+)"
    r"\s*(?:=|equals|is)?\s*(\w+)?", re.I)

def _to_num(s: str) -> Optional[float]:
    s = s.strip().lower()
    if s in _NUMBER_WORDS:
        return float(_NUMBER_WORDS[s])
    try:
        return float(s)
    except ValueError:
        return None

def _from_num(n: float) -> str:
    if n == int(n):
        i = int(n)
        rev = {v: k for k, v in _NUMBER_WORDS.items()}
        return rev.get(i, str(i))
    return str(n)

def try_arithmetic(text: str) -> Optional[str]:
    """
    Try to evaluate a simple arithmetic expression in the text.
    Returns answer string or None.
    """
    m = _NUM_RE.search(text)
    if not m:
        return None
    a_str, op, b_str, given = m.group(1), m.group(2), m.group(3), m.group(4)
    a = _to_num(a_str)
    b = _to_num(b_str)
    if a is None or b is None:
        return None
    op = op.lower().strip()
    try:
        if op in ("+", "plus"):             result = a + b
        elif op in ("-", "minus"):          result = a - b
        elif op in ("*", "times", "multiplied by"): result = a * b
        elif op in ("/", "divided by"):
            if b == 0: return "undefined (division by zero)"
            result = a / b
        else:
            return None
    except Exception:
        return None
    answer = _from_num(result)
    # Verify if given answer is present
    if given:
        g = _to_num(given)
        if g is not None and g != result:
            return f"{_from_num(a)} {op} {_from_num(b)} = {answer} (not {_from_num(g)})"
    return f"{_from_num(a)} {op} {_from_num(b)} = {answer}"


# ── Inner Voice ───────────────────────────────────────────────────────────────

class InnerVoice:
    """
    Pre- and post-processes each turn to:
      1. Predict what's coming (before pipeline runs)
      2. Spot spelling variants / fuzzy concept matches
      3. Try arithmetic completion
      4. Detect analogy patterns
      5. Measure prediction error (after pipeline runs)
      6. Update edge confidence based on error magnitude
      7. Return VoiceContext for ResponseEngine
    """

    FUZZY_THRESHOLD  = 0.62   # minimum similarity for spelling correction
    ERROR_DECAY      = 0.03   # confidence penalty on high-error turns
    ERROR_BOOST      = 0.02   # confidence bonus on confirmed-prediction turns

    def __init__(self, semantic_memory, confidence_mgr,
                 predictive_engine=None, canonical_fn=None):
        self.sem        = semantic_memory
        self.conf       = confidence_mgr
        self.pred_eng   = predictive_engine   # optional; enriches predictions
        self._canonical = canonical_fn or (lambda x: x.lower().strip())

        # Concept vocabulary for fuzzy matching
        self._concept_vocab: list = []
        self._vocab_dirty = True   # rebuild on next use

        # Turn state
        self._last_vc:  Optional[VoiceContext] = None
        self.turn_count = 0

    # ================================================================
    # PRE-PROCESS  (run before pipeline, enriches PipelineContext)
    # ================================================================

    def pre_process(self, raw: str, ctx_topic: str = "",
                    last_intent: int = -1) -> VoiceContext:
        """
        Called BEFORE the pipeline processes user input.
        Returns VoiceContext with predictions and generalisation hints.
        """
        self.turn_count += 1
        vc = VoiceContext()

        # ── 1. Arithmetic check ───────────────────────────────────
        arith = try_arithmetic(raw)
        if arith:
            vc.analogy_hint = arith

        # ── 2. Spelling / fuzzy concept correction ────────────────
        words = re.findall(r"\b[a-zA-Z]{3,}\b", raw.lower())
        vocab = self._get_vocab()
        for word in words:
            if word not in vocab:
                match = fuzzy_match(word, vocab, self.FUZZY_THRESHOLD)
                if match and match != word:
                    vc.spelling_corrected = f"{word} -> {match}"
                    break

        # ── 3. Predict from predictive engine ────────────────────
        if self.pred_eng:
            pred_ctx = {
                "current_topic": ctx_topic,
                "last_intent":   last_intent,
                "last_emotion":  "neutral",
            }
            pred_state = self.pred_eng.predict(pred_ctx)
            vc.predicted_topic  = pred_state.topic
            vc.predicted_intent = pred_state.intent

        # ── 4. Partial match / incomplete knowledge ───────────────
        canon_words = [self._canonical(w) for w in words
                       if len(w) > 3]
        for cw in canon_words[:3]:
            edges = self.sem.outgoing(cw)
            if not edges:
                # Unknown concept
                vc.novel_concept = True
            else:
                for e in edges[:2]:
                    vc.partial_match.append(
                        (e.subject, e.relation, e.object_, e.confidence))

        # ── 5. Analogy detection: "X is to Y as A is to ?" ────────
        analogy_re = re.compile(
            r"(\w+)\s+is\s+to\s+(\w+)\s+as\s+(\w+)\s+is\s+to\s+\?", re.I)
        m = analogy_re.search(raw)
        if m:
            hint = self._complete_analogy(m.group(1), m.group(2), m.group(3))
            if hint:
                vc.analogy_hint = hint

        self._last_vc = vc
        return vc

    # ================================================================
    # POST-PROCESS  (run after pipeline, refines confidence)
    # ================================================================

    def post_process(self, actual_topic: str, actual_intent: int,
                      response_found: bool, triples_learned: list) -> VoiceContext:
        """
        Called AFTER the pipeline has produced a response.
        Measures prediction error and updates edge confidence.
        Returns the updated VoiceContext.
        """
        vc = self._last_vc or VoiceContext()

        # ── Measure prediction error ──────────────────────────────
        topic_error  = 0.0 if vc.predicted_topic == actual_topic else 0.5
        intent_error = 0.0 if vc.predicted_intent == actual_intent else 0.4
        novel_error  = 0.6 if vc.novel_concept else 0.0
        vc.prediction_error = min(1.0,
            topic_error * 0.4 + intent_error * 0.3 + novel_error * 0.3)

        # ── Notify predictive engine ──────────────────────────────
        if self.pred_eng:
            entities = [t[0] for t in triples_learned] + \
                       [t[2] for t in triples_learned]
            self.pred_eng.observe({
                "intent":   actual_intent,
                "topic":    actual_topic,
                "emotion":  "neutral",
                "entities": entities[:6],
                "triples":  triples_learned,
            })

        # ── Update confidence based on error ──────────────────────
        if actual_topic:
            edges = self.sem.outgoing(actual_topic)
            if vc.prediction_error > 0.5:
                # High error -> slight decay on related edges
                for edge in edges[:5]:
                    edge.confidence = max(0.1,
                        edge.confidence - self.ERROR_DECAY * vc.prediction_error)
                vc.hedged = True
            elif vc.prediction_error < 0.2:
                # Low error -> boost edges (familiar territory)
                for edge in edges[:5]:
                    edge.confidence = min(1.0,
                        edge.confidence + self.ERROR_BOOST)
                vc.confidence_boost = self.ERROR_BOOST * len(edges[:5])

        self._vocab_dirty = True   # new concepts may have been added
        self._last_vc = vc
        return vc

    # ================================================================
    # ANALOGY COMPLETION
    # ================================================================

    def _complete_analogy(self, x: str, y: str, a: str) -> str:
        """
        X is to Y as A is to ?
        Find the relation(s) X has to Y, then apply to A.
        """
        cx, cy, ca = (self._canonical(v) for v in (x, y, a))
        # Find relation(s) between X and Y
        xy_edges = [e for e in self.sem.outgoing(cx) if e.object_ == cy]
        if not xy_edges:
            xy_edges = [e for e in self.sem.incoming(cy) if e.subject == cx]
        if not xy_edges:
            return ""
        rel = xy_edges[0].relation
        # Apply same relation from A
        a_edges = [e for e in self.sem.outgoing(ca) if e.relation == rel]
        if a_edges:
            best = max(a_edges, key=lambda e: e.confidence)
            return (f"Analogy: {x} {rel} {y}, so {a} {rel} {best.object_}  "
                    f"({best.confidence:.0%} confident)")
        return f"I know {a} but can't find what {a} {rel} (like {x} {rel} {y})."

    # ================================================================
    # VOCABULARY MANAGEMENT
    # ================================================================

    def _get_vocab(self) -> list:
        if self._vocab_dirty:
            self._concept_vocab = list(self.sem.nodes.keys())
            self._vocab_dirty   = False
        return self._concept_vocab

    # ================================================================
    # RESPONSE ENRICHMENT
    # ================================================================

    def enrich_response(self, response: str, vc: VoiceContext) -> str:
        """
        Optionally prefix/suffix the response with InnerVoice insights.
        Only adds content when genuinely useful.
        """
        prefixes = []
        suffixes = []

        # Arithmetic result
        if vc.analogy_hint and re.search(r"=\s*\w+", vc.analogy_hint):
            prefixes.append(f"{vc.analogy_hint}")

        # Analogy completion (non-arithmetic)
        elif vc.analogy_hint:
            suffixes.append(f"\n{vc.analogy_hint}")

        # Spelling correction hint
        if vc.spelling_corrected:
            old, new = vc.spelling_corrected.split(" -> ")
            suffixes.append(f"\n(Did you mean '{new}' instead of '{old}'?)")

        # Hedge if prediction error was high
        if vc.hedged and "I don't" not in response:
            suffixes.append("\n(I'm less certain than usual — "
                            "this is a newer concept for me.)")

        if prefixes:
            response = "\n".join(prefixes) + "\n\n" + response
        if suffixes:
            response = response + "".join(suffixes)

        return response

    # ================================================================
    # STATS
    # ================================================================

    def stats(self) -> dict:
        last_error = self._last_vc.prediction_error if self._last_vc else 0.0
        return {
            "turn_count":       self.turn_count,
            "last_pred_error":  round(last_error, 3),
            "vocab_size":       len(self._concept_vocab),
        }
