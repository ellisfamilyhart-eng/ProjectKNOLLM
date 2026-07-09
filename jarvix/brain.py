"""
Jarvix Brain v3 -- five-layer cognitive pipeline
--------------------------------------------------
Layer 1  NLPParser        raw text  -> Sentence(SVO)
Layer 2  KnowledgeGraph   Sentence  -> store triple
Layer 3  Reasoner         query     -> ReasonResult
Layer 4  Planner          question  -> Plan[] -> ReasonResult[]
Layer 5  AnswerGenerator  results   -> natural language

The Brain owns all five layers and exposes:
  process_statement(text)  -> stores + returns confirmation string
  process_question(text)   -> answers from graph + string
  compute_curiosity(...)   -> float (termination-aware)
  is_topic_understood(...) -> bool
"""

import math
from .config import LEARNING_CONFIG, BEHAVIOR_CONFIG
from .memory_store import (
    MemoryStore, STAGE_MASTERED, MASTERY_CONFIDENCE, MASTERY_SUPPORT,
)
from .nlp_parser import NLPParser, Sentence
from .knowledge_graph import (
    KnowledgeGraph, R_IS_A, R_HAS_PROP, R_HAS,
    R_CAN, R_DOES, R_PART_OF, R_CAUSES, R_OPPOSITE, R_RELATED,
    SELF,
)
from .reasoner import Reasoner
from .planner import Planner
from .answer_generator import AnswerGenerator

# Tuning
CURIOSITY_THRESHOLD = 0.25
MAX_REASONING_DEPTH = 2
CHAIN_DECAY         = 0.90


class Brain:
    """
    Five-layer cognitive pipeline.
    """

    def __init__(self, memory: MemoryStore):
        self.memory = memory

        # Layer 1
        self.parser = NLPParser()

        # Layer 2
        self.graph = KnowledgeGraph()

        # Layer 3
        self.reasoner = Reasoner(self.graph)

        # Layer 4
        self.planner = Planner(self.graph, self.reasoner)

        # Layer 5
        self.answer_gen = AnswerGenerator()

        # Agent-level state
        self.emotional_state  = "curious"
        self._depth_counter: dict = {}

    # ================================================================
    # LAYER 1 -- Parse
    # ================================================================

    def parse(self, text: str) -> Sentence:
        return self.parser.parse(text)

    # ================================================================
    # LAYER 2 -- Store into graph
    # ================================================================

    def store_sentence(self, sentence: Sentence, confidence: float = 0.65) -> dict:
        """
        Add an SVO triple to the knowledge graph.
        Also adds to the flat MemoryStore for backward compat.
        Runs one forward-inference pass.
        Returns a dict with storage metadata.
        """
        subj = sentence.subject
        rel  = sentence.relation_type
        obj  = sentence.object_

        if subj == "unknown" or obj == "unknown":
            return {"stored": False, "reason": "could not parse"}

        # Add to graph
        edge_data = self.graph.add_edge(subj, rel, obj, confidence=confidence,
                                        source="user")

        # Mirror into flat MemoryStore (keeps v3.2 compatibility)
        fact_text = f"{rel} {obj}" if rel not in ("is", "are") else obj
        state     = self.memory.add_fact(subj, fact_text, confidence=confidence)

        # Forward inference
        new_facts = self.planner.infer_new_facts()

        return {
            "stored":          True,
            "subject":         subj,
            "relation":        rel,
            "object":          obj,
            "confidence":      edge_data.confidence,
            "stage":           state.get("stage", "new"),
            "inferred_count":  len(new_facts),
            "new_inferences":  new_facts,
        }

    # ================================================================
    # LAYER 3+4 -- Reason & Plan
    # ================================================================

    def answer_question(self, text: str) -> str:
        """Full pipeline for a question: parse -> plan -> reason -> generate."""
        sentence = self.parser.parse(text)
        results  = self.planner.plan_and_execute(sentence)
        return self.answer_gen.generate(results, text)

    def query_graph(self, subject: str, relation: str, obj: str):
        """Direct reasoner query (used internally and by tests)."""
        return self.reasoner.query(subject, relation, obj)

    def describe(self, concept: str) -> str:
        """Natural language description of a concept."""
        facts = self.reasoner.describe(concept)
        if not facts:
            return f"I haven't learned about '{concept}' yet."
        # Synthesise via answer generator
        from .reasoner import ReasonResult
        r = ReasonResult(f"describe {concept}")
        r.set(facts, max(f["confidence"] for f in facts), [], "")
        return self.answer_gen._describe(r, facts)

    # ================================================================
    # LAYER 5 -- Generate
    # ================================================================

    def confirm_teaching(self, sentence: Sentence, store_result: dict) -> str:
        return self.answer_gen.confirm_learning(sentence, store_result)

    # ================================================================
    # CURIOSITY (termination-aware)
    # ================================================================

    def compute_curiosity(self, topic: str, new_fact: str) -> float:
        """
        curiosity = base * (1 - avg_confidence) * (1 - support_saturation)
        Approaches 0 as topic is mastered.
        """
        _, pred_conf = self.predict(topic)
        contradicts, conflict_degree = self.is_contradiction(topic, new_fact)

        base = conflict_degree if contradicts else max(0.0, 1.0 - pred_conf)

        facts = self.memory.facts.get(topic, {})
        if facts:
            avg_support = sum(s.get("support", 1) for s in facts.values()) / len(facts)
        else:
            avg_support = 0
        support_sat = min(1.0, avg_support / MASTERY_SUPPORT)

        curiosity = base * (1.0 - pred_conf) * (1.0 - support_sat * 0.7)
        return max(0.0, curiosity)

    def generate_questions(self, topic: str, new_fact: str,
                           curiosity: float, depth: int = 0) -> list:
        """Return at most ONE novel question; never repeat."""
        if curiosity < CURIOSITY_THRESHOLD:
            return []
        if depth >= MAX_REASONING_DEPTH:
            return []
        if self.memory.is_topic_closed(topic):
            return []
        if self.memory.is_fact_mastered(topic, new_fact):
            return []

        contradicts, _ = self.is_contradiction(topic, new_fact)

        candidates = []
        if contradicts:
            candidates.append(
                f"I thought I knew something different about {topic} -- "
                f"can you help me reconcile '{new_fact}'?"
            )
        else:
            candidates.append(
                f"Can you give me a real example of '{new_fact}'?")
            candidates.append(
                f"What is the most important thing about {topic}?")
            candidates.append(
                f"How does {topic} connect to something else I know?")

        related = self.memory.get_associations(topic, limit=2)
        for rel in related:
            if not self.memory.is_topic_closed(rel):
                candidates.append(
                    f"Does knowing about {rel} change how I understand {topic}?")

        for q in candidates:
            if self.memory.has_asked(topic, new_fact, q):
                continue
            if self._answer_already_exists(topic, q):
                continue
            self.memory.record_question(topic, new_fact, q)
            return [q]

        return []

    def _answer_already_exists(self, topic: str, question: str) -> bool:
        stop = {"what","is","are","a","the","about","of","for","in","on","it",
                "to","me","my","how","why","does","do","can","tell","know"}
        q_words = {w.lower().strip("'?") for w in question.split()} - stop
        if not q_words:
            return False
        # Check graph first
        for (s, r, o) in self.graph.edges:
            if s == topic.lower():
                obj_words = set(o.split())
                if q_words & obj_words:
                    return True
        # Then flat memory
        for fact_text in self.memory.facts.get(topic, {}):
            fact_words = set(fact_text.lower().split())
            if q_words & fact_words:
                return True
        return False

    # ================================================================
    # COMPAT HELPERS (used by agent / legacy code)
    # ================================================================

    def predict(self, topic: str):
        """Return (best_fact_text, confidence) from flat memory."""
        facts = self.memory.facts.get(topic, {})
        if not facts:
            return None, 0.0
        best = max(facts.items(),
                   key=lambda kv: kv[1]["confidence"]
                       if isinstance(kv[1], dict) else kv[1])
        conf = best[1]["confidence"] if isinstance(best[1], dict) else best[1]
        return best[0], conf

    def is_contradiction(self, topic: str, new_fact: str) -> tuple:
        """Check contradiction using graph + flat memory."""
        # Graph-level: check opposite_of edges
        graph_contras = self.reasoner.detect_contradictions()
        for c in graph_contras:
            if c["subject"] == topic.lower():
                return True, c["confidence_conflict"]

        # Flat memory word-overlap fallback
        facts = self.memory.facts.get(topic, {})
        new_words = set(new_fact.lower().split())
        for stored_fact, state in facts.items():
            conf = state["confidence"] if isinstance(state, dict) else state
            stored_words = set(stored_fact.lower().split())
            similarity   = len(new_words & stored_words) / max(len(new_words | stored_words), 1)
            if similarity < 0.30 and conf > 0.6:
                conflict = conf * (1.0 - similarity)
                if conflict > 0.3:
                    return True, conflict

        return False, 0.0

    def update_emotion(self, curiosity: float):
        if curiosity > 0.7:
            self.emotional_state = "excited"
        elif curiosity > CURIOSITY_THRESHOLD:
            self.emotional_state = "curious"
        elif curiosity > 0.05:
            self.emotional_state = "thinking"
        else:
            self.emotional_state = "satisfied"

    def generalize(self, topic: str, new_fact: str) -> list:
        """Pattern extraction (minimal, no cascade)."""
        out = []
        if " is " in new_fact.lower():
            parts = new_fact.lower().split(" is ", 1)
            if len(parts) == 2 and parts[1].strip():
                out.append(f"Pattern: [X] is {parts[1].strip()}")
        topic_words = set(topic.lower().split())
        for known in list(self.memory.facts):
            if known == topic:
                continue
            if topic_words & set(known.lower().split()):
                self.memory.add_association(topic, known)
        return out

    def is_topic_understood(self, topic: str) -> bool:
        if self.memory.is_topic_closed(topic):
            return True
        return self.memory.mastery_ratio(topic) >= 0.9

    def analyze_topic(self, topic: str) -> dict:
        facts  = self.memory.get_facts_by_topic(topic)
        assocs = self.memory.get_associations(topic)
        confs  = [c for _, c in facts]
        graph_facts = self.reasoner.describe(topic)
        return {
            "topic":             topic,
            "known_facts":       facts,
            "graph_facts":       graph_facts,
            "avg_confidence":    sum(confs) / len(confs) if confs else 0.0,
            "associated_topics": assocs,
            "mastery_ratio":     self.memory.mastery_ratio(topic),
            "closed":            self.memory.is_topic_closed(topic),
            "emotional_state":   self.emotional_state,
        }

    # ================================================================
    # DEPTH TRACKING
    # ================================================================

    def get_depth(self, topic: str) -> int:
        return self._depth_counter.get(topic, 0)

    def increment_depth(self, topic: str):
        self._depth_counter[topic] = self.get_depth(topic) + 1

    def reset_depth(self, topic: str):
        self._depth_counter.pop(topic, None)

    # ================================================================
    # AUTONOMOUS THOUGHT
    # ================================================================

    def generate_autonomous_thought(self, learning_queue: list):
        if not learning_queue:
            return None
        item  = max(learning_queue, key=lambda x: x.get("surprise", 0))
        topic = item["topic"]
        related = self.memory.get_associations(topic)
        thought = f"[Thinking about '{topic}'...]"
        graph_facts = self.reasoner.describe(topic)
        if graph_facts:
            top = graph_facts[0]
            thought += (f"\n  Strongest: {topic} {top['relation']} "
                        f"{top['object']} ({top['confidence']:.0%})")
        if related:
            thought += f"\n  Connected to: {', '.join(related[:3])}"
        ratio = self.memory.mastery_ratio(topic)
        thought += f"\n  Mastery: {ratio:.0%}"
        if ratio >= 0.9:
            thought += " -- I think I understand this well."

        # Forward inference on this topic
        new_facts = self.planner.infer_new_facts()
        if new_facts:
            thought += f"\n  Inferred {len(new_facts)} new facts from what I know."
        return thought
