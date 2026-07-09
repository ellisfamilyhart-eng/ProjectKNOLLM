"""
Jarvix NoLLM - Memory Store v2
Each fact carries full state: confidence, support count, lifecycle stage,
asked questions, and reasoning depth.  Topics can be "closed" once mastered.
"""

import json
import os
from datetime import datetime
from collections import defaultdict
from .config import STORAGE_CONFIG, LEARNING_CONFIG

# -- Lifecycle stages ----------------------------------------------------------
STAGE_NEW        = "new"
STAGE_QUESTIONED = "questioned"
STAGE_ANSWERED   = "answered"
STAGE_CONFIRMED  = "confirmed"
STAGE_MASTERED   = "mastered"

MASTERY_CONFIDENCE = 0.85   # minimum confidence to consider mastery
MASTERY_SUPPORT    = 3      # minimum corroborating facts needed
CLOSURE_RATIO      = 0.90   # fraction of facts mastered to close a topic


def _blank_fact(confidence: float = 0.5) -> dict:
    """Return a fresh fact-state dict."""
    return {
        "confidence":     confidence,
        "support":        1,
        "stage":          STAGE_NEW,
        "questions_asked": [],      # list of question strings already asked
        "depth":          0,        # reasoning depth when this fact was stored
        "added":          datetime.now().isoformat(),
        "last_updated":   datetime.now().isoformat(),
    }


class MemoryStore:
    """
    Semantic memory with full per-fact state.

    facts layout:
        {
          topic: {
            fact_text: {
              confidence, support, stage,
              questions_asked, depth, added, last_updated
            }
          }
        }
    """

    def __init__(self, data_file=None):
        self.data_file = data_file or STORAGE_CONFIG["data_file"]

        self.facts: dict             = {}
        self.patterns: list          = []
        self.associations            = defaultdict(set)
        self.conversation_history    = []
        self.learning_log            = []
        self.closed_topics: set      = set()   # topics with nothing left to learn

        self.birth_time              = datetime.now().isoformat()
        self.total_interactions      = 0
        self.last_save_time          = datetime.now().isoformat()

        self.load()

    # -- Persistence ----------------------------------------------------------

    def load(self):
        if not os.path.exists(self.data_file):
            return
        try:
            with open(self.data_file, "r") as f:
                data = json.load(f)
            self.facts               = data.get("facts", {})
            self.patterns            = data.get("patterns", [])
            self.associations        = defaultdict(set, {
                k: set(v) for k, v in data.get("associations", {}).items()
            })
            self.conversation_history = data.get("conversation_history", [])
            self.learning_log         = data.get("learning_log", [])
            self.closed_topics        = set(data.get("closed_topics", []))
            self.birth_time           = data.get("birth_time", self.birth_time)
            self.total_interactions   = data.get("total_interactions", 0)
        except Exception as e:
            print(f"Warning: could not load memory: {e}")

    def save(self, neural_data=None, episodic_data=None,
             reflection_data=None, vocab_data=None):
        try:
            payload = {
                "facts":        self.facts,
                "patterns":     self.patterns,
                "associations": {k: list(v) for k, v in self.associations.items()},
                "conversation_history": self.conversation_history[
                    -STORAGE_CONFIG["max_conversation_history"]:],
                "learning_log": self.learning_log[
                    -STORAGE_CONFIG["max_learning_log"]:],
                "closed_topics":       list(self.closed_topics),
                "birth_time":          self.birth_time,
                "total_interactions":  self.total_interactions,
            }
            if neural_data    is not None: payload["neural"]     = neural_data
            if episodic_data  is not None: payload["episodic"]   = episodic_data
            if reflection_data is not None: payload["reflection"] = reflection_data
            if vocab_data     is not None: payload["vocabulary"] = vocab_data

            with open(self.data_file, "w") as f:
                json.dump(payload, f, indent=2)
            self.last_save_time = datetime.now().isoformat()
        except Exception as e:
            print(f"Warning: could not save memory: {e}")

    # -- Fact CRUD -------------------------------------------------------------

    def add_fact(self, topic: str, fact: str,
                 confidence: float = 0.5, depth: int = 0) -> dict:
        """
        Store or reinforce a fact.  Returns the updated fact-state dict.
        Existing facts get their confidence boosted and support incremented.
        """
        if topic not in self.facts:
            self.facts[topic] = {}

        existing = self.facts[topic].get(fact)

        if existing is None:
            # Brand-new fact
            state = _blank_fact(confidence)
            state["depth"] = depth
            self.facts[topic][fact] = state
        else:
            # Reinforce
            boost = LEARNING_CONFIG["learning_rate"] * LEARNING_CONFIG["overcompensation"]
            old_conf = existing["confidence"]
            existing["confidence"]   = min(1.0, old_conf + confidence * boost)
            existing["support"]      = existing.get("support", 1) + 1
            existing["last_updated"] = datetime.now().isoformat()
            # Advance lifecycle if warranted
            if existing["stage"] in (STAGE_NEW, STAGE_QUESTIONED):
                existing["stage"] = STAGE_ANSWERED
            state = existing

        # Check for automatic mastery
        if self._qualifies_mastered(state):
            state["stage"] = STAGE_MASTERED

        self.learning_log.append({
            "time":       datetime.now().isoformat(),
            "type":       "fact_learned",
            "topic":      topic,
            "fact":       fact,
            "confidence": state["confidence"],
            "stage":      state["stage"],
        })

        # Re-evaluate topic closure
        self._maybe_close_topic(topic)

        return state

    def get_fact_state(self, topic: str, fact: str) -> dict | None:
        """Return the full state dict for a fact, or None."""
        return self.facts.get(topic, {}).get(fact)

    def get_confidence(self, topic: str, fact: str) -> float:
        s = self.get_fact_state(topic, fact)
        return s["confidence"] if s else 0.0

    def get_facts_by_topic(self, topic: str) -> list:
        """Return [(fact, confidence), ...] sorted by confidence desc."""
        return sorted(
            ((f, s["confidence"]) for f, s in self.facts.get(topic, {}).items()),
            key=lambda x: -x[1],
        )

    # -- Mastery & closure ----------------------------------------------------

    def _qualifies_mastered(self, state: dict) -> bool:
        return (
            state["confidence"] >= MASTERY_CONFIDENCE
            and state.get("support", 0) >= MASTERY_SUPPORT
        )

    def is_fact_mastered(self, topic: str, fact: str) -> bool:
        s = self.get_fact_state(topic, fact)
        return s is not None and s.get("stage") == STAGE_MASTERED

    def is_topic_closed(self, topic: str) -> bool:
        return topic in self.closed_topics

    def _maybe_close_topic(self, topic: str):
        """Close a topic when enough of its facts are mastered."""
        fact_states = list(self.facts.get(topic, {}).values())
        if not fact_states:
            return
        mastered = sum(1 for s in fact_states if s.get("stage") == STAGE_MASTERED)
        ratio = mastered / len(fact_states)
        if ratio >= CLOSURE_RATIO and len(fact_states) >= 2:
            self.closed_topics.add(topic)

    def mastery_ratio(self, topic: str) -> float:
        fact_states = list(self.facts.get(topic, {}).values())
        if not fact_states:
            return 0.0
        return sum(1 for s in fact_states if s.get("stage") == STAGE_MASTERED) / len(fact_states)

    # -- Question deduplication -----------------------------------------------

    def has_asked(self, topic: str, fact: str, question: str) -> bool:
        s = self.get_fact_state(topic, fact)
        if s is None:
            return False
        return question in s.get("questions_asked", [])

    def record_question(self, topic: str, fact: str, question: str):
        s = self.get_fact_state(topic, fact)
        if s is not None:
            if "questions_asked" not in s:
                s["questions_asked"] = []
            if question not in s["questions_asked"]:
                s["questions_asked"].append(question)
            # Advance lifecycle
            if s["stage"] == STAGE_NEW:
                s["stage"] = STAGE_QUESTIONED

    def advance_stage(self, topic: str, fact: str, new_stage: str):
        s = self.get_fact_state(topic, fact)
        if s:
            s["stage"] = new_stage
            s["last_updated"] = datetime.now().isoformat()

    # -- Association helpers --------------------------------------------------

    def add_association(self, t1: str, t2: str):
        if t1 != t2:
            self.associations[t1].add(t2)
            self.associations[t2].add(t1)

    def get_associations(self, topic: str, limit=None) -> list:
        assocs = list(self.associations.get(topic, set()))
        return assocs[:limit] if limit else assocs

    # -- Conversation log -----------------------------------------------------

    def add_conversation(self, role: str, content: str):
        self.conversation_history.append({
            "role":    role,
            "content": content,
            "time":    datetime.now().isoformat(),
        })

    # -- Forgetting -----------------------------------------------------------

    def decay_confidence(self):
        """Gently decay non-mastered facts; remove very stale ones."""
        for topic in list(self.facts):
            for fact in list(self.facts[topic]):
                s = self.facts[topic][fact]
                if s.get("stage") == STAGE_MASTERED:
                    continue           # mastered facts don't decay
                s["confidence"] *= LEARNING_CONFIG["confidence_decay"]
                if s["confidence"] < 0.05:
                    del self.facts[topic][fact]
            if not self.facts[topic]:
                del self.facts[topic]
                self.closed_topics.discard(topic)

    # -- Stats ----------------------------------------------------------------

    def get_statistics(self) -> dict:
        all_facts   = [s for t in self.facts.values() for s in t.values()]
        mastered    = sum(1 for s in all_facts if s.get("stage") == STAGE_MASTERED)
        return {
            "total_topics":        len(self.facts),
            "total_facts":         len(all_facts),
            "mastered_facts":      mastered,
            "closed_topics":       len(self.closed_topics),
            "total_interactions":  self.total_interactions,
            "birth_time":          self.birth_time,
            "associations_count":  sum(len(v) for v in self.associations.values()) // 2,
            "last_save":           self.last_save_time,
        }
