"""
Jarvix - Executive Controller v4
QuestionBrain wired into _run_question.
Bulk paste handled. Natural confused responses.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional
from .response_generator     import ResponseGenerator
from .input_parser           import InputParser
from .knowledge_validator    import KnowledgeValidator
from .thought                import ThoughtEngine
from .reasoning_engine       import ReasoningEngine
from .cognitive_planner      import CognitivePlanner
from .intent_classifier      import IntentClassifier, IntentResult, Intent
from .relation_detector      import RelationDetector, Triple
from .command_engine         import CommandEngine, CommandResult
from .context_builder        import ContextBuilder, BrainState
from .working_memory         import WorkingMemory
from .semantic_memory        import SemanticMemory
from .logic_engine           import LogicEngine
from .contradiction_detector import ContradictionDetector, Conflict
from .confidence_manager     import ConfidenceManager
from .curiosity_engine       import CuriosityEngine
from .personality_engine     import PersonalityEngine
from .core_knowledge         import try_builtin_answer, SELF_FACTS
from .knowledge_graph        import SELF
from .question_brain         import QuestionBrain

# ── Bulk-paste detector ───────────────────────────────────────────────────────
_TEACH_LINE = re.compile(r'^([^:?!\n]{1,60}):\s*(.{2,120})$')

def _split_bulk(text: str) -> list:
    lines   = [l.strip() for l in text.strip().splitlines() if l.strip()]
    if len(lines) < 2:
        return []
    matched = [l for l in lines if _TEACH_LINE.match(l)]
    return matched if len(matched) >= 2 else []


@dataclass
class PipelineContext:
    raw:            str          = ""
    resolved:       str          = ""
    intent:         Optional[IntentResult]  = None
    triple:         Optional[Triple]        = None
    conflict:       Optional[Conflict]      = None
    inferred:       list         = field(default_factory=list)
    brain_state:    Optional[BrainState]    = None
    command_result: Optional[CommandResult] = None
    response:       str          = ""
    topic:          str          = ""


class ExecutiveController:

    def __init__(self, working_memory, semantic_memory, logic_engine,
                 contradiction, confidence, curiosity, brain, basic_conversation):

        self.thought_engine = ThoughtEngine()
        self.reasoning_engine = ReasoningEngine()
        self.response_generator = ResponseGenerator()
        self.cognitive_planner = CognitivePlanner()

        self.wm         = working_memory
        self.sem        = semantic_memory
        self.logic      = logic_engine
        self.contra     = contradiction
        self.conf       = confidence
        self.curiosity  = curiosity
        self.brain      = brain
        self.basic_conv = basic_conversation

        self.intent_clf  = IntentClassifier()
        self.rel_det     = RelationDetector()
        self.personality = PersonalityEngine()
        self.qbrain      = None
        self.validator = KnowledgeValidator(
             self.sem
        )

        self._agent      = None
        self.cmd_engine  = None
        self.ctx_builder = None
        self._ks         = None

        # Cognitive architecture

        self.parser = InputParser()

        self.last_plan = []

    def set_agent(self, agent):
        self._agent      = agent
        self.cmd_engine  = CommandEngine(agent)
        self.ctx_builder = ContextBuilder(agent)
        self.qbrain      = QuestionBrain(agent.brain.graph,
                                         agent.semantic_memory)
        # lazy-import KnowledgeSummary here to avoid circular import
        from .context_builder import KnowledgeSummary
        self._ks = KnowledgeSummary(agent)

    # ================================================================
    # ENTRY
    # ================================================================

    def process(self, raw: str, _agent=None) -> str:
        if _agent and not self._agent:
            self.set_agent(_agent)

        # Multi-line bulk paste
        bulk = _split_bulk(raw)
        if bulk:
            return self._run_bulk(bulk)

        ctx = PipelineContext(raw=raw)


        # Resolve references

        ctx.resolved = self.wm.resolve_coreference(raw)



        ################################################
        # New cognitive pipeline
        ################################################


        parsed = self.parser.parse(
            ctx.resolved
        )
        

        thoughts = self.thought_engine.think(
            parsed
        )


        reasoning = self.reasoning_engine.reason(
            thoughts
        )


        if reasoning.selected_thought:

            self.last_plan = self.cognitive_planner.create_plan(
                reasoning.selected_thought
            )

        else:

            self.last_plan = []



        ################################################
        # Existing intent system continues
        ################################################

        ctx.intent = self.intent_clf.classify(
            ctx.resolved
        )

        ctx.topic = (
            ctx.intent.subject
            or self.wm.state.current_topic
            or ""
        )

        code = ctx.intent.code

        if code in (Intent.COMMAND, Intent.WEB_REQUEST):
            return self._run_command(ctx)

        if code == Intent.MEMORY_QUERY:
            return self._run_memory_query(ctx)

        if code == Intent.IDENTITY:
            return self._run_identity(ctx)

        if code == Intent.CHAT:
            return self._run_chat(ctx)

        if code == Intent.QUESTION:
            return self._run_question(ctx)

        if code == Intent.DEFINITION:
            return self._run_definition(ctx)

        if code == Intent.EXAMPLE:
            return self._run_example(ctx)

        resolved_exp = ctx.resolved.replace("cannot", "can not")
        ctx.triple = self.rel_det.detect(resolved_exp)

        return self._run_teach(ctx)

    # ================================================================
    # BULK LEARNING
    # ================================================================

    def _run_bulk(self, lines: list) -> str:
        stored, skipped, topics = 0, 0, []

        for line in lines:
            m = _TEACH_LINE.match(line)
            if not m:
                continue
            raw_subj = m.group(1).strip().rstrip(":").lower()
            raw_fact = m.group(2).strip()
            full     = f"{raw_subj} {raw_fact}".replace("cannot", "can not")

            triple = self.rel_det.detect(full)
            if triple and triple.subject not in ("unknown", ""):
                s, r, o = triple.subject.rstrip(":"), triple.relation, triple.object_
            else:
                s, r, o = raw_subj, "has_property", raw_fact

            if self.sem.edge_confidence(s, r, o) > 0.5:
                skipped += 1
                continue

            self.sem.add_edge(s, r, o, confidence=0.70, source="user")
            self.brain.graph.add_edge(s, r, o, confidence=0.70, source="user")
            self.conf.observe(s, r, o, source="user", base_confidence=0.70)
            if self._agent:
                self._agent.memory.add_fact(s, f"{r} {o}", confidence=0.70)

            stored += 1
            if s not in topics:
                topics.append(s)
            self.personality.update("learned_new", topic=s)

        new_inferred = self.logic.run()

        lines_out = [
            f"Bulk learning complete.",
            f"  Stored   : {stored} fact(s)",
            f"  Skipped  : {skipped} (already known)",
            f"  Topics   : {len(topics)}",
            f"  Inferred : {len(new_inferred)} new fact(s) automatically",
        ]
        if topics[:8]:
            lines_out.append(f"  Learned  : {', '.join(topics[:8])}")
        for inf in new_inferred[:3]:
            lines_out.append(
                f"    e.g. {inf.subject} {inf.relation} "
                f"{inf.object_} ({inf.confidence:.0%})")
        return "\n".join(lines_out)

    # ================================================================
    # HANDLERS
    # ================================================================

    def _run_command(self, ctx: PipelineContext) -> str:
        self.personality.update("asked_question")
        result = self.cmd_engine.execute(
            ctx.intent.command, arg=ctx.intent.object_,
            url=ctx.intent.url, raw=ctx.resolved)
        self._record(ctx, result.response)
        return result.response

    def _run_memory_query(self, ctx: PipelineContext) -> str:
        self.personality.update("asked_question")
        response = self._ks.full_summary()
        self._record(ctx, response)
        return response

    def _run_identity(self, ctx: PipelineContext) -> str:
        value = ctx.intent.object_
        if value:
            self.sem.add_edge(SELF, "named", value.lower(), confidence=0.99, source="user")
            self.brain.graph.add_edge(SELF, "named", value.lower(), confidence=0.99, source="user")
            self.personality.update("praised")
            response = f"Got it — I'll remember that my name is '{value}'."
        else:
            self.personality.update("asked_question")
            caps    = self.brain.graph.get_capabilities(SELF)
            cap_str = ", ".join(o for o, _ in caps[:4]) if caps else "learn and remember"
            response = (f"I'm {SELF_FACTS['name']}, a self-learning AI.\n"
                        f"I can {cap_str}.\n"
                        f"I know about {len(self.brain.graph.nodes)} concepts so far.")
        self._record(ctx, response)
        return response

    def _split_compound_sentence(self, text: str) -> list[str]:
        """Splits compound statements connected by 'and' or 'or' into simple sentences."""
        # Simple split on conjunctions flanked by spaces to avoid splitting inside words
        segments = re.split(r'\s+(?:and|or)\s+', text, flags=re.IGNORECASE)
        # Clean up fragments and filter out empty strings
        return [seg.strip() for seg in segments if seg.strip()]

    def _run_chat(self, ctx: PipelineContext) -> str:
        # If the user is trying to teach a fact using a colon, don't throw it 
        # away to say hello. Force it to run through the learning pipeline!
        if ":" in ctx.resolved:
            resolved_exp = ctx.resolved.replace("cannot", "can not")
            ctx.triple = self.rel_det.detect(resolved_exp)
            return self._run_teach(ctx)

        # Intercept compound learning statements (e.g., contains 'and' / 'or') 
        # and parse them into individual simple facts before teaching.
        if any(conj in ctx.resolved.lower() for conj in (" and ", " or ")):
            sub_sentences = self._split_compound_sentence(ctx.resolved)
            
            # Verify if these split segments actually look like facts 
            # (i.e. we can successfully detect a valid triple in at least one)
            valid_triples = []
            for sub in sub_sentences:
                clean_sub = sub.replace("cannot", "can not")
                triple = self.rel_det.detect(clean_sub)
                if triple and triple.subject not in ("unknown", ""):
                    valid_triples.append((sub, triple))
            
            # If we successfully isolated individual facts, teach them sequentially
            if valid_triples:
                responses = []
                for sub_text, triple in valid_triples:
                    # Create a mini pipeline context for each clean, simple sentence
                    sub_ctx = PipelineContext(raw=sub_text, resolved=sub_text)
                    sub_ctx.triple = triple
                    sub_ctx.intent = ctx.intent
                    responses.append(self._run_teach(sub_ctx))
                
                # Merge the sequential learning responses
                combined_response = "\n\n".join(responses)
                self._record(ctx, combined_response)
                return combined_response

        self.personality.update("greeted")
        response = self.basic_conv.get_casual_response(ctx.resolved)
        self._record(ctx, response)
        return response

    def _run_question(self, ctx: PipelineContext) -> str:
        self.personality.update("asked_question")

        # 1. Built-in answers (identity, capabilities, etc.)
        builtin = try_builtin_answer(ctx.resolved)
        if builtin:
            prefix   = self.personality.opening_phrase()
            response = (prefix + "\n" + builtin).strip()
            self._record(ctx, response)
            return response

        # 2. QuestionBrain — pattern-matched + reverse graph lookup
        if self.qbrain:
            qa = self.qbrain.answer(ctx.resolved)
            if qa and qa.found:
                prefix   = self.personality.opening_phrase()
                response = (prefix + "\n" + qa.answer).strip()
                self._record(ctx, response, topic=qa.topic)
                return response

        # 3. Five-layer brain pipeline (graph traversal)
            sentence = self.brain.parse(ctx.resolved)

        if sentence.subject in ("you", "i", "me"):
            sentence.subject = SELF

        results = self.brain.planner.plan_and_execute(sentence)

        facts = []

        for result in results:
            if result.found:
                facts.extend(result.facts)

        response = self.response_generator.generate(
            reasoning=self.reasoning_engine.last_result,
            plan=self.last_plan,
            facts=facts,
            personality=self.personality.mood_suffix
        )


        # 4. Nothing found — ask to be taught
        if not (results and results[0].found):
            # Extract topic from the parsed sentence (now fixed to be the noun)
            topic = (sentence.subject
                     if sentence.subject not in ("unknown", "", "what", "who")
                     else sentence.object_)
            if topic and topic not in ("unknown", ""):
                response = (
                    f"I don't know about '{topic}' yet.\n"
                    f"Could you teach me?  For example:\n"
                    f"  \"{topic}: [what it is]\""
                )
            else:
                response = (
                    "I'm not sure how to answer that yet.\n"
                    "You can teach me by saying:  \"Topic: what it means\""
                )

        prefix   = self.personality.opening_phrase()
        response = (prefix + "\n" + response).strip() if prefix else response
        topic    = getattr(sentence, "subject", "")
        self._record(ctx, response, topic=topic)
        return response

    def _run_definition(self, ctx: PipelineContext) -> str:
        triple = self.rel_det.detect(ctx.resolved)
        subj   = ctx.intent.subject or (triple.subject if triple else "unknown")
        obj    = ctx.intent.object_  or (triple.object_ if triple else "")
        if subj != "unknown" and obj:
            self.sem.add_edge(subj, "definition", obj, confidence=0.85, source="user")
            self.brain.graph.add_edge(subj, "definition", obj, confidence=0.85)
            self.conf.observe(subj, "definition", obj, source="user")
            self.personality.update("learned_new", topic=subj)
        response = f"Stored: '{subj}' means '{obj}'.{self.personality.mood_suffix()}"
        self._record(ctx, response, topic=subj)
        return response

    def _run_example(self, ctx: PipelineContext) -> str:
        triple = self.rel_det.detect(ctx.resolved)
        subj   = ctx.intent.subject or (triple.subject if triple else "unknown")
        obj    = ctx.intent.object_  or (triple.object_ if triple else "")
        if subj != "unknown" and obj:
            self.sem.add_edge(subj, "instance_of", obj, confidence=0.80, source="user")
            self.brain.graph.add_edge(subj, "instance_of", obj, confidence=0.80)
            self.conf.observe(subj, "instance_of", obj, source="user")
            self.personality.update("learned_new", topic=obj)
        response = f"Got it — '{subj}' is an example of '{obj}'."
        self._record(ctx, response, topic=obj)
        return response

    def _run_teach(self, ctx: PipelineContext) -> str:
        triple = ctx.triple
        if triple is None or triple.subject in ("unknown", ""):
            self.personality.update("confused")
            response = self._confused_response(ctx.resolved)
            self._record(ctx, response)
            return response

        s = triple.subject.rstrip(":")
        r = triple.relation
        o = triple.object_

        validation = self.validator.validate(
            s,
            r,
            o
        )

        if not validation.valid:

            response = (
                f"I couldn't store that information.\n"
                f"Reason: {validation.reason}"
            )

            self._record(ctx, response)

            return response
        ctx.topic = s

        conflict = self.contra.check_and_store(s, r, o,
                       confidence=triple.confidence, source="user")
        ctx.conflict = conflict

        self.sem.add_edge(s, r, o, confidence=triple.confidence, source="user")
        self.brain.graph.add_edge(s, r, o, confidence=triple.confidence, source="user")
        self.conf.observe(s, r, o, source="user", base_confidence=triple.confidence)
        if self._agent:
            self._agent.memory.add_fact(s, f"{r} {o}", confidence=triple.confidence)

        ctx.inferred   = self.logic.run_focused(s)
        event          = "conflict" if conflict else "learned_new"
        self.personality.update(event, topic=s)
        ctx.brain_state = self.ctx_builder.build(ctx.intent, triple, conflict, ctx.inferred)
        response        = self._teach_response(ctx)

        if not conflict and not self.wm.state.pending_question:
            q = self.curiosity.next_question(s, recent_topics=self.wm.recent_topics(3))
            if q and self.personality.style.ask_question:
                response += f"\n\n{q}"
                self.wm.set_pending_question(q)

        self.wm.record_entities(s, o)
        self._record(ctx, response, topic=s)
        return response

    # ================================================================
    # RESPONSE BUILDERS
    # ================================================================

    _REL_PHRASE = {
        "is_a": "is a type of", "instance_of": "is an example of",
        "has_property": "has the property", "has": "has",
        "can": "can", "causes": "causes", "part_of": "is part of",
        "definition": "means", "named": "is named",
        "located_in": "is located in", "produced_by": "is produced by",
        "synonym_of": "is the same as", "opposite_of": "is NOT",
        "related_to": "is related to", "does": "does",
    }

    def _teach_response(self, ctx: PipelineContext) -> str:
        s, r, o = ctx.triple.subject, ctx.triple.relation, ctx.triple.object_
        if ctx.conflict:
            c = ctx.conflict
            return (f"I already thought '{s}' {c.relation} '{c.existing_object}' "
                    f"({c.existing_conf:.0%}).\n"
                    f"Now you say it {r} '{o}'.\nHas something changed, or are both true?")
        rel    = self._REL_PHRASE.get(r, r)
        suffix = self.personality.mood_suffix()
        lines  = [f"Got it — {s} {rel} {o}.{suffix}"]
        if ctx.inferred:
            lines.append(f"  Inferred {len(ctx.inferred)} more fact(s) from this.")
            for inf in ctx.inferred[:2]:
                lines.append(f"  e.g. {inf.subject} {inf.relation} "
                             f"{inf.object_} ({inf.confidence:.0%})")
        bs = ctx.brain_state
        if bs and len(bs.facts) > 1:
            lines.append(f"  I now know {len(bs.facts)} thing(s) about '{s}'.")
        return "\n".join(lines)

    def _confused_response(self, raw: str) -> str:
        words = [w for w in raw.lower().split()
                 if len(w) > 3 and w not in {
                     "what","when","where","why","how","does","that",
                     "this","with","from","have","will","your","tell",
                     "about","much","ways","many","also",
                 }]
        topic = words[0] if words else "that"
        if self.personality.style.admit_uncertainty:
            return (f"I'm not sure I understood that.\n"
                    f"Try:  \"{topic}: [what it means]\"")
        return (f"I didn't quite catch that.\n"
                f"Try the format:  \"Topic: what it is\"\n"
                f"Example:  \"gravity: pulls objects toward each other\"")

    # ================================================================
    # HELPERS
    # ================================================================

    def _record(self, ctx: PipelineContext, response: str, topic: str = ""):
        t = topic or ctx.topic or ""
        n = Intent.name(ctx.intent.code) if ctx.intent else ""
        self.wm.add_turn("user",  ctx.raw,    topic=t, intent=n)
        self.wm.add_turn("agent", response,   topic=t)

    def export(self) -> dict:
        return {
            "working_memory": self.wm.export(),
            "semantic_memory": self.sem.export(),
            "contradiction_stats": self.contra.stats(),
            "curiosity_stats": self.curiosity.stats(),
            "personality": self.personality.export(),
        }

    def cognitive_status(self):
        thought = self.reasoning_engine.last_result

        if not thought:
            return "No reasoning performed."

        return {
            "thought": thought.explanation,
            "goal": thought.action,
            "confidence": thought.confidence,
            "plan": self.last_plan,
        }
