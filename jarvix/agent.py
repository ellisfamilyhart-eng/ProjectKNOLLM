"""
Jarvix Agent v6.0
Five new modules wired in:
  PredictiveEngine  — probabilistic next-turn predictor (event bus)
  DreamingEngine    — background compression + pattern mining
  InnerVoice        — pre/post prediction + generalisation hints
  canonical()       — concept normalisation throughout
"""

import json
import os

from .config            import STORAGE_CONFIG, BEHAVIOR_CONFIG, AGENT_METADATA
from .memory_store      import MemoryStore, STAGE_MASTERED
from .brain             import Brain, CURIOSITY_THRESHOLD, MAX_REASONING_DEPTH
from .working_memory    import WorkingMemory
from .semantic_memory   import SemanticMemory
from .logic_engine      import LogicEngine
from .contradiction_detector import ContradictionDetector
from .confidence_manager     import ConfidenceManager
from .curiosity_engine       import CuriosityEngine
from .executive_controller   import ExecutiveController
from .basic_conversation     import BasicConversationResponder
from .conversation_enhanced  import EnhancedConversationManager
from .recursive_learner      import RecursiveLearner
from .imagination            import Imagination
from .vocabulary             import Vocabulary
from .neural_learner         import NeuralLearner, TinyBrain
from .episodic_memory        import EpisodicMemory
from .reflection             import ReflectionEngine
from .personality_engine     import PersonalityEngine
from .core_knowledge         import seed_agent
from .canonical              import canonical
# New v6 modules
from .predictive_engine      import PredictiveEngine, PredictionError
from .dreaming_engine        import DreamingEngine
from .inner_voice            import InnerVoice
from .response_generator     import ResponseGenerator


class Jarvix:
    """Jarvix v6.0 — Predictive + Dreaming + Inner Voice architecture."""

    def __init__(self, data_file=None):
        # ── Core memory ────────────────────────────────────────────
        self.memory = MemoryStore(data_file=data_file)
        self.brain  = Brain(self.memory)

        # ── Cognitive architecture ─────────────────────────────────
        self.working_memory  = WorkingMemory(max_turns=100)
        self.semantic_memory = SemanticMemory()
        self.logic_engine    = LogicEngine(self.semantic_memory)
        self.contradiction   = ContradictionDetector(self.semantic_memory)
        self.confidence_mgr  = ConfidenceManager()
        self.curiosity       = CuriosityEngine(self.semantic_memory)

        # ── New v6 modules ─────────────────────────────────────────
        self.predictive_engine = PredictiveEngine()
        self.dreaming_engine   = DreamingEngine(
            semantic_memory = self.semantic_memory,
            episodic_memory = None,    # set after episodic created below
            working_memory  = self.working_memory,
            confidence_mgr  = self.confidence_mgr,
            canonical_fn    = canonical,
        )
        self.inner_voice = InnerVoice(
            semantic_memory  = self.semantic_memory,
            confidence_mgr   = self.confidence_mgr,
            predictive_engine= self.predictive_engine,
            canonical_fn     = canonical,
        )

        # ── Wire PredictiveEngine error bus ────────────────────────
        # Subscribers receive PredictionError events decoupled
        self.predictive_engine.subscribe(self._on_prediction_error)

        # ── Conversation ───────────────────────────────────────────
        self.conversation       = EnhancedConversationManager(self.memory)
        self.basic_conversation = BasicConversationResponder(self.memory, self.conversation)

        # ── Executive controller ───────────────────────────────────
        self.ec = ExecutiveController(
            working_memory    = self.working_memory,
            semantic_memory   = self.semantic_memory,
            logic_engine      = self.logic_engine,
            contradiction     = self.contradiction,
            confidence        = self.confidence_mgr,
            curiosity         = self.curiosity,
            brain             = self.brain,
            basic_conversation= self.basic_conversation,
        )
        self.ec.set_agent(self)

        # ── Three-tier memory ──────────────────────────────────────
        self.episodic_memory   = EpisodicMemory()
        self.vocabulary        = Vocabulary()
        self.neural_learner    = NeuralLearner(self.memory, feature_size=64)
        self.reflection_engine = ReflectionEngine(
            self.memory, self.neural_learner,
            self.episodic_memory, self.vocabulary,
        )

        # Now wire episodic into dreaming
        self.dreaming_engine.epi = self.episodic_memory

        # ── Support ────────────────────────────────────────────────
        self.recursive_learner = RecursiveLearner(
            self.memory, self.brain, self.conversation)
        self.imagination = Imagination(self.memory)

        self.learning_queue    = []
        self.interaction_count = 0
        self.name              = AGENT_METADATA["name"]

        self._load_state()
        seed_agent(self)

    # ================================================================
    # PREDICTION ERROR HANDLER  (event bus subscriber)
    # ================================================================

    def _on_prediction_error(self, event: PredictionError):
        """
        React to prediction errors WITHOUT tight coupling.
        High-magnitude errors trigger targeted confidence updates.
        """
        if event.error_type == "CONFIRMED":
            # Prediction was correct — slight boost
            if event.topic:
                for edge in self.semantic_memory.outgoing(event.topic)[:3]:
                    edge.confidence = min(1.0, edge.confidence + 0.01)
            return

        mag = event.magnitude

        if mag > 0.7:
            # High surprise — new concept or topic shift
            # Reduce over-confidence on recently-added edges
            if event.topic:
                for edge in self.semantic_memory.outgoing(event.topic)[:3]:
                    if edge.confidence > 0.8:
                        edge.confidence = max(0.5, edge.confidence - 0.05)

        if event.error_type == "TOPIC_SHIFT" and event.actual:
            # User shifted topic — make sure we note the association
            prev = event.predicted
            curr = event.actual
            if prev and curr and prev != curr:
                existing = self.semantic_memory.edge_confidence(
                    prev, "related_to", curr)
                if existing < 0.3:
                    self.semantic_memory.add_edge(
                        prev, "related_to", curr,
                        confidence=0.30, source="prediction_error")

    # ================================================================
    # PRIMARY ENTRY POINT
    # ================================================================

    def process_input(self, raw: str) -> str:
        if not raw or not raw.strip():
            return "I'm listening — go ahead!"

        self.interaction_count         += 1
        self.memory.total_interactions += 1

        # ── InnerVoice pre-process: predict + find spelling variants ─
        ctx_topic    = self.working_memory.state.current_topic or ""
        last_intent  = -1
        if self.working_memory.turns:
            last_turn = self.working_memory.turns[-1]
            try:
                from .intent_classifier import Intent
                last_intent = next(
                    (v for k, v in Intent._NAMES.items()
                     if v == last_turn.intent), -1)
            except Exception:
                pass

        voice_ctx = self.inner_voice.pre_process(
            raw.strip(), ctx_topic=ctx_topic, last_intent=last_intent)

        # ── Executive controller: main pipeline ────────────────────
        response = self.ec.process(raw.strip(), _agent=self)

        # ── InnerVoice post-process: measure error + refine ────────
        actual_topic  = self.working_memory.state.current_topic or ""
        triples_learned = []
        if hasattr(self.ec, "_last_triples"):
            triples_learned = self.ec._last_triples

        voice_ctx = self.inner_voice.post_process(
            actual_topic  = actual_topic,
            actual_intent = last_intent,
            response_found= "don't know" not in response.lower(),
            triples_learned = triples_learned,
        )

        # ── Enrich response with InnerVoice insights ───────────────
        response = self.inner_voice.enrich_response(response, voice_ctx)

        # ── Episodic + neural ──────────────────────────────────────
        topic = actual_topic
        if topic:
            self.vocabulary.encode(raw)
            self.neural_learner.learn_topic_pattern(topic, raw[:50], 0.6)
            self.episodic_memory.record_episode(raw, response, {
                "topic":          topic,
                "pred_error":     round(voice_ctx.prediction_error, 3),
                "spelling_fixed": voice_ctx.spelling_corrected,
            })

        # ── Periodic maintenance ───────────────────────────────────
        n = self.memory.total_interactions
        if n % STORAGE_CONFIG["auto_save_interval"] == 0:
            self.memory.decay_confidence()
            self.semantic_memory.decay()
            self.confidence_mgr.run_decay()
            self.confidence_mgr.prune()
            self.save()

        # ── Dream every 25 turns (background maintenance) ──────────
        if n % 25 == 0 and n > 0:
            self._run_dream_cycle()

        return response

    # ================================================================
    # DREAMING (background)
    # ================================================================

    def _run_dream_cycle(self):
        """Run one dreaming cycle silently."""
        try:
            self.dreaming_engine.dream(max_episodes=40)
        except Exception as e:
            pass   # never crash the main loop

    def dream_now(self) -> str:
        """Trigger a dream cycle on demand and return a report."""
        try:
            cycle = self.dreaming_engine.dream(max_episodes=100)
            return (
                f"Dream cycle #{self.dreaming_engine.cycle_count} complete.\n"
                f"  Compressed  : {cycle.facts_compressed} facts\n"
                f"  Rules found : {cycle.rules_found}\n"
                f"  Aliases     : {cycle.aliases_merged}\n"
                f"  Boosted     : {cycle.links_boosted} links\n"
                f"  Decayed     : {cycle.links_decayed} links\n"
                f"  Prototypes  : {cycle.prototypes_built}\n"
                f"  Duration    : {cycle.duration_ms}ms"
            )
        except Exception as e:
            return f"Dream cycle failed: {e}"

    # ================================================================
    # WEB & TEXT LEARNING
    # ================================================================

    def learn_from_url(self, url: str) -> str:
        facts = self.recursive_learner.learn_from_url(url)
        for topic, fact in facts:
            ct = canonical(topic)
            self.semantic_memory.add_edge(ct, "related_to", fact,
                                          confidence=0.5, source="web")
            self.confidence_mgr.observe(ct, "related_to", fact,
                                        source="web", base_confidence=0.5)
        out = (f"[Web] {len(facts)} facts from {url}\n"
               + self.recursive_learner.get_extracted_facts_summary())
        self.save()
        return out

    def learn_from_text(self, text: str) -> str:
        facts = self.recursive_learner.extract_facts_from_text(text)
        added = []
        for t, f in facts:
            ct = canonical(t)
            is_dup, _ = self.conversation.is_duplicate_fact(ct, f)
            if not is_dup:
                self.memory.add_fact(ct, f, confidence=0.5)
                self.semantic_memory.add_edge(ct, "related_to", f,
                                              confidence=0.5, source="text")
                added.append((ct, f))
        out = f"[Text] {len(added)} new facts\n"
        for t, f in added[:5]:
            out += f"  {t}: {f}\n"
        self.save()
        return out

    # ================================================================
    # REFLECTION & AUTONOMY
    # ================================================================

    def reflect(self, topic=None):
        if topic:
            return self.reflection_engine.reflect_on_topic(topic)
        return self.reflection_engine.reflect_idle()

    def autonomous_thought(self) -> str:
        if not self.learning_queue:
            return self.imagination.get_imaginative_summary()
        thought = self.brain.generate_autonomous_thought(self.learning_queue)
        if thought:
            idx = self.learning_queue.index(
                max(self.learning_queue, key=lambda x: x.get("surprise", 0)))
            self.learning_queue.pop(idx)
        return thought

    def continuous_learning(self, duration=10):
        return self.reflection_engine.continuous_learning_session(duration)

    # ================================================================
    # IMAGINATION
    # ================================================================

    def imagine(self, topic=None) -> str:
        if topic:
            ct    = canonical(topic)
            facts = self.memory.get_facts_by_topic(ct)
            if not facts:
                return f"I haven't learned about '{topic}' yet."
            return "\n".join(
                self.imagination.generate_hypothetical(ct, facts[0][0])[:3])
        return self.imagination.get_imaginative_summary()

    def theorize(self, topic=None) -> str:
        if not topic:
            if not self.memory.facts:
                return "Need to learn more first."
            topic = list(self.memory.facts)[0]
        return self.imagination.generate_theory(canonical(topic))

    def concept_similarity(self, a: str, b: str) -> str:
        """Return similarity between two concepts using dream prototypes."""
        score = self.dreaming_engine.get_prototype_similarity(
            canonical(a), canonical(b))
        return (f"Similarity between '{a}' and '{b}': {score:.0%}\n"
                f"({'very similar' if score > 0.7 else 'somewhat similar' if score > 0.4 else 'different'})")

    # ================================================================
    # PERSISTENCE
    # ================================================================

    def save(self):
        self.memory.save(
            neural_data     = self._neural_data(),
            episodic_data   = self.episodic_memory.export(),
            reflection_data = self.reflection_engine.export(),
            vocab_data      = self.vocabulary.export(),
        )
        graph_path = self.memory.data_file.replace(".json", "_graph.json")
        try:
            with open(graph_path, "w") as f:
                json.dump(self.brain.graph.export(), f, indent=2)
        except Exception:
            pass

        sem_path = self.memory.data_file.replace(".json", "_semantic.json")
        try:
            ec_export = self.ec.export()
            ec_export["confidence_records"]  = self.confidence_mgr.export()
            ec_export["predictive_engine"]   = self.predictive_engine.export()
            ec_export["dreaming_cycles"]     = self.dreaming_engine.export()
            with open(sem_path, "w") as f:
                json.dump(ec_export, f, indent=2)
        except Exception:
            pass

    def _load_state(self):
        if not os.path.exists(self.memory.data_file):
            return
        try:
            with open(self.memory.data_file) as f:
                data = json.load(f)
            if "vocabulary"  in data: self.vocabulary.import_vocab(data["vocabulary"])
            if "episodic"    in data: self.episodic_memory.import_episodes(data["episodic"])
            if "reflection"  in data: self.reflection_engine.import_reflections(data["reflection"])
            if "neural" in data:
                for topic, wd in data["neural"].get("topic_networks", {}).items():
                    net = TinyBrain(input_size=64)
                    net.weights = wd.get("weights", net.weights)
                    net.bias    = wd.get("bias",    net.bias)
                    self.neural_learner.topic_networks[topic] = net
        except Exception as e:
            print(f"Note: could not load flat state: {e}")

        graph_path = self.memory.data_file.replace(".json", "_graph.json")
        if os.path.exists(graph_path):
            try:
                with open(graph_path) as f:
                    self.brain.graph.import_graph(json.load(f))
            except Exception:
                pass

        sem_path = self.memory.data_file.replace(".json", "_semantic.json")
        if os.path.exists(sem_path):
            try:
                with open(sem_path) as f:
                    sem_data = json.load(f)
                if "semantic_memory"   in sem_data:
                    self.semantic_memory.import_data(sem_data["semantic_memory"])
                if "working_memory"    in sem_data:
                    self.working_memory.import_state(sem_data["working_memory"])
                if "confidence_records" in sem_data:
                    self.confidence_mgr.import_data(sem_data["confidence_records"])
                if "predictive_engine" in sem_data:
                    self.predictive_engine.import_state(sem_data["predictive_engine"])
            except Exception as e:
                print(f"Note: could not load semantic state: {e}")

    def _neural_data(self) -> dict:
        return {
            "topic_networks": {
                topic: {"weights": n.weights, "bias": n.bias,
                        "training_samples": n.training_samples}
                for topic, n in self.neural_learner.topic_networks.items()
            },
            "global_network": {
                "weights": self.neural_learner.global_network.weights,
                "bias":    self.neural_learner.global_network.bias,
                "training_samples": self.neural_learner.global_network.training_samples,
            },
        }

    # ================================================================
    # STATS
    # ================================================================

    def get_stats(self) -> dict:
        mem  = self.memory.get_statistics()
        g    = self.brain.graph.stats()
        sem  = self.semantic_memory.stats()
        conf = self.confidence_mgr.stats()
        cont = self.contradiction.stats()
        cur  = self.curiosity.stats()
        pred = self.predictive_engine.stats()
        drm  = self.dreaming_engine.stats()
        iv   = self.inner_voice.stats()
        return {
            "name":               self.name,
            "birth_time":         self.memory.birth_time,
            "total_interactions": self.memory.total_interactions,
            "flat_topics":        mem["total_topics"],
            "flat_facts":         mem["total_facts"],
            "mastered_facts":     mem["mastered_facts"],
            "graph_nodes":        g["nodes"],
            "graph_edges":        g["edges"],
            "graph_inferred":     g["inferred_edges"],
            "semantic_nodes":     sem["nodes"],
            "semantic_edges":     sem["edges"],
            "confidence_avg":     conf["avg_confidence"],
            "contradictions":     cont["total_conflicts"],
            "curiosity_asked":    cur["total_asked"],
            "working_turns":      len(self.working_memory.turns),
            "episodic_episodes":  len(self.episodic_memory.episodes),
            "neural_networks":    len(self.neural_learner.topic_networks),
            "reflections":        self.reflection_engine.reflection_count,
            "current_topic":      self.working_memory.state.current_topic,
            "mood":               self.brain.emotional_state,
            # New v6
            "pred_accuracy":      pred["accuracy"],
            "pred_errors":        pred["errors"],
            "dream_cycles":       drm.get("cycles", 0),
            "last_pred_error":    iv["last_pred_error"],
            "vocab_size":         iv["vocab_size"],
        }

    def get_context(self) -> str:
        return self.working_memory.get_context_summary()

    def get_personality(self) -> str:
        return self.conversation.get_personality_summary()

    def get_memory_summary(self) -> str:
        lines = [ResponseGenerator.generate_memory_dump(self.memory)]
        sem  = self.semantic_memory.stats()
        conf = self.confidence_mgr.stats()
        cont = self.contradiction.stats()
        ep   = self.episodic_memory.get_statistics()
        rf   = self.reflection_engine.get_reflection_statistics()
        pred = self.predictive_engine.stats()
        drm  = self.dreaming_engine.stats()
        lines.append(
            f"\n[Semantic]    {sem['nodes']} nodes  {sem['edges']} edges  "
            f"avg_conf={sem['avg_confidence']}"
            f"\n[Confidence]  total={conf['total']}  mastered={conf['mastered']}"
            f"\n[Conflicts]   {cont['total_conflicts']} total"
            f"\n[Episodic]    {ep['total_episodes']} episodes"
            f"\n[Neural]      {len(self.neural_learner.topic_networks)} nets"
            f"\n[Reflection]  {rf['total_reflections']} runs"
            f"\n[Predictive]  accuracy={pred['accuracy']:.0%}  "
            f"errors={pred['errors']}"
            f"\n[Dreaming]    cycles={drm.get('cycles',0)}  "
            f"last_boosted={drm.get('last_boosted',0)}"
        )
        return "\n".join(lines)

    def analyze_topic(self, topic: str) -> dict:
        ct   = canonical(topic)
        base = self.brain.analyze_topic(ct)
        base["semantic_edges"] = [
            {"rel": e.relation, "obj": e.object_, "conf": e.confidence}
            for e in self.semantic_memory.outgoing(ct)
        ]
        base["gaps"] = [
            {"relation": g.relation, "question": g.hint, "score": g.score}
            for g in self.curiosity.find_gaps(ct)
        ]
        base["prototype_built"] = bool(
            self.semantic_memory.nodes.get(ct, None) and
            self.semantic_memory.nodes[ct].properties.get("_prototype")
        )
        return base

    def clear_memory(self):
        from .knowledge_graph import KnowledgeGraph
        from .reasoner        import Reasoner
        from .planner         import Planner

        self.memory.facts             = {}
        self.memory.associations.clear()
        self.memory.learning_log      = []
        self.memory.closed_topics     = set()
        self.learning_queue           = []
        self.episodic_memory.episodes = []
        self.reflection_engine.reflection_history = []
        self.brain._depth_counter     = {}
        self.brain.graph              = KnowledgeGraph()
        self.brain.reasoner           = Reasoner(self.brain.graph)
        self.brain.planner            = Planner(self.brain.graph, self.brain.reasoner)
        self.working_memory           = WorkingMemory()
        self.semantic_memory          = SemanticMemory()
        self.logic_engine             = LogicEngine(self.semantic_memory)
        self.contradiction            = ContradictionDetector(self.semantic_memory)
        self.confidence_mgr           = ConfidenceManager()
        self.curiosity                = CuriosityEngine(self.semantic_memory)
        self.predictive_engine        = PredictiveEngine()
        self.predictive_engine.subscribe(self._on_prediction_error)
        self.inner_voice              = InnerVoice(
            self.semantic_memory, self.confidence_mgr,
            self.predictive_engine, canonical)
        self.dreaming_engine          = DreamingEngine(
            self.semantic_memory, self.episodic_memory,
            self.working_memory, self.confidence_mgr, canonical)
        self.ec = ExecutiveController(
            working_memory    = self.working_memory,
            semantic_memory   = self.semantic_memory,
            logic_engine      = self.logic_engine,
            contradiction     = self.contradiction,
            confidence        = self.confidence_mgr,
            curiosity         = self.curiosity,
            brain             = self.brain,
            basic_conversation= self.basic_conversation,
        )
        self.ec.set_agent(self)
        self.save()

    def export_memory(self) -> dict:
        return {
            "facts":           self.memory.facts,
            "graph":           self.brain.graph.export(),
            "semantic":        self.semantic_memory.export(),
            "episodic":        self.episodic_memory.export(),
            "neural":          self._neural_data(),
            "reflection":      self.reflection_engine.export(),
            "vocabulary":      self.vocabulary.export(),
            "confidence":      self.confidence_mgr.export(),
            "predictive":      self.predictive_engine.export(),
            "dreaming":        self.dreaming_engine.export(),
            "metadata":        self.get_stats(),
        }
