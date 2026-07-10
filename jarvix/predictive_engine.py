"""
Jarvix - Predictive Engine
===========================
Asynchronous probabilistic predictor that:

1. Maintains probability distributions over next intent, topic, entities,
   emotions, and expected world-state BEFORE each user turn.

2. After each turn, compares prediction against reality, generates a
   PredictionError signal with magnitude and type.

3. Publishes PredictionError events to any registered subscribers
   (Executive Controller, ConfidenceManager, etc.) — fully decoupled.

4. Updates its own internal frequency tables and Bayesian priors so
   predictions improve over time without any external input.

Design principles
-----------------
- Zero tight coupling: other modules subscribe via callback, never imported here.
- Synchronous-safe: runs inline but designed so it can be moved to a thread.
- No LLM: pure frequency counting + Bayesian update + simple Markov chains.
- Exposes only events, never internal state directly.

Prediction targets
------------------
  intent       : next likely Intent code (0-10)
  topic        : next likely concept string
  entity       : next likely named entity
  emotion      : expected emotional tone of input
  world_state  : expected facts the user is about to assert

Error types
-----------
  INTENT_ERROR   : predicted wrong intent
  TOPIC_SHIFT    : unexpected topic change
  ENTITY_NOVEL   : unknown entity appeared
  EMOTION_SHIFT  : emotional tone changed unexpectedly
  FACT_CONFLICT  : fact contradicts a predicted world-state
  SEQUENCE_BREAK : input breaks expected conversational sequence
"""

from __future__ import annotations
import math
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional


# ── Event types ───────────────────────────────────────────────────────────────

ERROR_INTENT_WRONG   = "INTENT_ERROR"
ERROR_TOPIC_SHIFT    = "TOPIC_SHIFT"
ERROR_ENTITY_NOVEL   = "ENTITY_NOVEL"
ERROR_EMOTION_SHIFT  = "EMOTION_SHIFT"
ERROR_FACT_CONFLICT  = "FACT_CONFLICT"
ERROR_SEQUENCE_BREAK = "SEQUENCE_BREAK"
ERROR_CONFIRMED      = "CONFIRMED"        # prediction was correct


@dataclass
class PredictionState:
    """What the engine predicted BEFORE a turn."""
    intent:      int   = -1          # Intent code, -1 = no prediction
    topic:       str   = ""
    entity:      str   = ""
    emotion:     str   = "neutral"
    world_facts: list  = field(default_factory=list)   # [(s, r, o)] expected
    confidence:  float = 0.0
    timestamp:   str   = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PredictionError:
    """Published after each turn to all subscribers."""
    error_type:      str
    magnitude:       float     # 0.0 = perfect, 1.0 = total surprise
    predicted:       str       = ""
    actual:          str       = ""
    topic:           str       = ""
    intent_code:     int       = -1
    confidence_was:  float     = 0.0
    timestamp:       str       = field(default_factory=lambda: datetime.now().isoformat())

    def __repr__(self):
        return (f"PredictionError({self.error_type}, "
                f"mag={self.magnitude:.2f}, "
                f"pred={self.predicted!r} vs actual={self.actual!r})")


# ── Predictive Engine ─────────────────────────────────────────────────────────

class PredictiveEngine:
    """
    Probabilistic next-turn predictor.
    Completely decoupled from all other modules via subscriber callbacks.
    """

    HISTORY_WINDOW = 20     # turns kept in the Markov history
    MIN_PRIOR      = 0.01   # Laplace smoothing constant

    def __init__(self):
        # ── Frequency tables ──────────────────────────────────────
        # intent_transitions[prev_intent][next_intent] = count
        self._intent_trans: dict = defaultdict(lambda: defaultdict(float))
        # topic_transitions[prev_topic][next_topic] = count
        self._topic_trans:  dict = defaultdict(lambda: defaultdict(float))
        # entity_freq[entity] = count
        self._entity_freq:  dict = defaultdict(float)
        # emotion_seq[(prev_emotion, intent)] = {next_emotion: count}
        self._emotion_seq:  dict = defaultdict(lambda: defaultdict(float))
        # world_state: {(s,r,o): probability}
        self._world_probs:  dict = defaultdict(float)

        # ── Markov history ────────────────────────────────────────
        self._history: deque = deque(maxlen=self.HISTORY_WINDOW)
        # Each entry: {"intent": int, "topic": str, "emotion": str, "entities": list}

        # ── Current prediction (set before each turn) ─────────────
        self._pending: Optional[PredictionState] = None

        # ── Subscribers: list of Callable[[PredictionError], None] ─
        self._subscribers: list[Callable] = []

        # ── Stats ─────────────────────────────────────────────────
        self.total_predictions = 0
        self.total_errors      = 0
        self.total_confirmed   = 0
        self.cumulative_error  = 0.0

    # ================================================================
    # SUBSCRIPTION (decoupled event bus)
    # ================================================================

    def subscribe(self, callback: Callable[[PredictionError], None]):
        """Register a callback to receive PredictionError events."""
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable):
        self._subscribers = [c for c in self._subscribers if c != callback]

    def _publish(self, event: PredictionError):
        for cb in self._subscribers:
            try:
                cb(event)
            except Exception:
                pass   # never let a bad subscriber crash the pipeline

    # ================================================================
    # PREDICT  (call BEFORE processing user input)
    # ================================================================

    def predict(self, context: dict) -> PredictionState:
        """
        Generate a prediction for the next turn.

        context keys used:
          current_topic  : str
          last_intent    : int
          last_emotion   : str
          recent_entities: list[str]
        """
        last_intent = context.get("last_intent", -1)
        last_topic  = context.get("current_topic", "")
        last_emotion= context.get("last_emotion", "neutral")

        # Predict next intent via Markov
        intent_pred, intent_conf = self._predict_intent(last_intent)

        # Predict next topic via Markov
        topic_pred = self._predict_topic(last_topic)

        # Predict next emotion
        emotion_pred = self._predict_emotion(last_emotion, last_intent)

        # Predict likely entity
        entity_pred = self._predict_entity()

        confidence = intent_conf * 0.4 + (0.5 if topic_pred == last_topic else 0.2)
        confidence = min(1.0, confidence)

        self._pending = PredictionState(
            intent    = intent_pred,
            topic     = topic_pred,
            entity    = entity_pred,
            emotion   = emotion_pred,
            confidence= confidence,
        )
        self.total_predictions += 1
        return self._pending

    # ================================================================
    # OBSERVE  (call AFTER processing, with actual values)
    # ================================================================

    def observe(self, actual: dict):
        """
        Compare actual turn data against pending prediction.
        Generates and publishes PredictionError events.
        Updates internal frequency tables.

        actual keys:
          intent      : int
          topic       : str
          entities    : list[str]
          emotion     : str
          triples     : list[(s, r, o)]   facts learned this turn
        """
        a_intent  = actual.get("intent",  -1)
        a_topic   = actual.get("topic",   "")
        a_emotion = actual.get("emotion", "neutral")
        a_entities= actual.get("entities", [])
        a_triples = actual.get("triples",  [])

        p = self._pending

        # ── Generate error signals ────────────────────────────────
        if p is not None:
            self._check_intent(p, a_intent, a_topic)
            self._check_topic(p, a_topic)
            self._check_entities(p, a_entities, a_topic)
            self._check_emotion(p, a_emotion, a_topic)
            self._check_sequence(a_topic)

        # ── Update Markov tables ──────────────────────────────────
        if self._history:
            last = self._history[-1]
            self._intent_trans[last["intent"]][a_intent]  += 1.0
            self._topic_trans[last["topic"]][a_topic]     += 1.0
            key = (last["emotion"], last["intent"])
            self._emotion_seq[key][a_emotion]             += 1.0

        for ent in a_entities:
            self._entity_freq[ent.lower()] += 1.0

        for s, r, o in a_triples:
            self._world_probs[(s, r, o)] = min(
                1.0, self._world_probs[(s, r, o)] + 0.15)

        # Record turn in history
        self._history.append({
            "intent":   a_intent,
            "topic":    a_topic,
            "emotion":  a_emotion,
            "entities": a_entities,
        })

        self._pending = None

    # ================================================================
    # ERROR CHECKERS
    # ================================================================

    def _check_intent(self, p: PredictionState, actual_intent: int,
                      actual_topic: str):
        if p.intent == -1 or actual_intent == -1:
            return
        if p.intent != actual_intent:
            magnitude = 1.0 - self._transition_prob(
                self._intent_trans, p.intent, actual_intent)
            err = PredictionError(
                error_type     = ERROR_INTENT_WRONG,
                magnitude      = magnitude,
                predicted      = str(p.intent),
                actual         = str(actual_intent),
                topic          = actual_topic,
                intent_code    = actual_intent,
                confidence_was = p.confidence,
            )
            self.total_errors   += 1
            self.cumulative_error += magnitude
            self._publish(err)
        else:
            self.total_confirmed += 1
            self._publish(PredictionError(
                error_type  = ERROR_CONFIRMED,
                magnitude   = 0.0,
                predicted   = str(p.intent),
                actual      = str(actual_intent),
                topic       = actual_topic,
                intent_code = actual_intent,
            ))

    def _check_topic(self, p: PredictionState, actual_topic: str):
        if not actual_topic or not p.topic:
            return
        if p.topic != actual_topic:
            magnitude = 1.0 - self._transition_prob(
                self._topic_trans, p.topic, actual_topic)
            err = PredictionError(
                error_type     = ERROR_TOPIC_SHIFT,
                magnitude      = max(0.1, magnitude),
                predicted      = p.topic,
                actual         = actual_topic,
                topic          = actual_topic,
                confidence_was = p.confidence,
            )
            self.total_errors   += 1
            self.cumulative_error += err.magnitude
            self._publish(err)

    def _check_entities(self, p: PredictionState,
                         entities: list, topic: str):
        for ent in entities:
            if self._entity_freq[ent.lower()] < 1.0:
                err = PredictionError(
                    error_type  = ERROR_ENTITY_NOVEL,
                    magnitude   = 0.8,
                    predicted   = p.entity,
                    actual      = ent,
                    topic       = topic,
                )
                self.total_errors   += 1
                self.cumulative_error += 0.8
                self._publish(err)

    def _check_emotion(self, p: PredictionState,
                       actual_emotion: str, topic: str):
        if p.emotion and actual_emotion and p.emotion != actual_emotion:
            err = PredictionError(
                error_type     = ERROR_EMOTION_SHIFT,
                magnitude      = 0.4,
                predicted      = p.emotion,
                actual         = actual_emotion,
                topic          = topic,
                confidence_was = p.confidence,
            )
            self.total_errors   += 1
            self.cumulative_error += 0.4
            self._publish(err)

    def _check_sequence(self, actual_topic: str):
        """Detect abrupt topic breaks (3+ turns on same topic then sudden change)."""
        if len(self._history) < 3:
            return
        recent_topics = [h["topic"] for h in list(self._history)[-3:]]
        if (len(set(recent_topics)) == 1 and
                recent_topics[0] and
                actual_topic and
                actual_topic != recent_topics[0]):
            err = PredictionError(
                error_type = ERROR_SEQUENCE_BREAK,
                magnitude  = 0.5,
                predicted  = recent_topics[0],
                actual     = actual_topic,
                topic      = actual_topic,
            )
            self.total_errors   += 1
            self.cumulative_error += 0.5
            self._publish(err)

    # ================================================================
    # PROBABILITY HELPERS
    # ================================================================

    def _predict_intent(self, last_intent: int) -> tuple[int, float]:
        """Return (most_likely_intent, confidence) via Markov."""
        trans = self._intent_trans.get(last_intent, {})
        if not trans:
            return last_intent if last_intent != -1 else 2, 0.3   # default: TEACH
        best = max(trans, key=lambda k: trans[k])
        total = sum(trans.values()) + self.MIN_PRIOR * 11
        conf  = (trans[best] + self.MIN_PRIOR) / total
        return best, conf

    def _predict_topic(self, last_topic: str) -> str:
        """Predict next topic: continuation is most likely."""
        if not last_topic:
            return ""
        trans = self._topic_trans.get(last_topic, {})
        if not trans:
            return last_topic   # continue on same topic
        best = max(trans, key=lambda k: trans[k])
        return best

    def _predict_emotion(self, last_emotion: str, last_intent: int) -> str:
        """Predict next emotional tone."""
        key  = (last_emotion, last_intent)
        seq  = self._emotion_seq.get(key, {})
        if not seq:
            return last_emotion or "neutral"
        return max(seq, key=lambda k: seq[k])

    def _predict_entity(self) -> str:
        """Predict most likely upcoming entity by frequency."""
        if not self._entity_freq:
            return ""
        return max(self._entity_freq, key=lambda k: self._entity_freq[k])

    def _transition_prob(self, table: dict, src, dst) -> float:
        """Compute transition probability with Laplace smoothing."""
        row   = table.get(src, {})
        total = sum(row.values()) + self.MIN_PRIOR
        return (row.get(dst, 0) + self.MIN_PRIOR) / total

    # ================================================================
    # STATS
    # ================================================================

    def accuracy(self) -> float:
        """Fraction of confirmed vs total predictions."""
        total = self.total_confirmed + self.total_errors
        return self.total_confirmed / total if total else 0.0

    def avg_error(self) -> float:
        return self.cumulative_error / max(self.total_errors, 1)

    def stats(self) -> dict:
        return {
            "total_predictions": self.total_predictions,
            "confirmed":         self.total_confirmed,
            "errors":            self.total_errors,
            "accuracy":          round(self.accuracy(), 3),
            "avg_error_mag":     round(self.avg_error(), 3),
            "topics_tracked":    len(self._topic_trans),
            "entities_tracked":  len(self._entity_freq),
        }

    # ================================================================
    # PERSISTENCE
    # ================================================================

    def export(self) -> dict:
        return {
            "intent_trans":  {str(k): dict(v) for k, v in self._intent_trans.items()},
            "topic_trans":   {k: dict(v) for k, v in self._topic_trans.items()},
            "entity_freq":   dict(self._entity_freq),
            "world_probs":   {str(k): v for k, v in self._world_probs.items()},
            "stats": {
                "total_predictions": self.total_predictions,
                "total_errors":      self.total_errors,
                "total_confirmed":   self.total_confirmed,
                "cumulative_error":  self.cumulative_error,
            },
        }

    def import_state(self, data: dict):
        for k, v in data.get("intent_trans", {}).items():
            self._intent_trans[int(k)] = defaultdict(float, {int(i): f for i, f in v.items()})
        for k, v in data.get("topic_trans", {}).items():
            self._topic_trans[k] = defaultdict(float, v)
        self._entity_freq = defaultdict(float, data.get("entity_freq", {}))
        s = data.get("stats", {})
        self.total_predictions = s.get("total_predictions", 0)
        self.total_errors      = s.get("total_errors",      0)
        self.total_confirmed   = s.get("total_confirmed",   0)
        self.cumulative_error  = s.get("cumulative_error",  0.0)
