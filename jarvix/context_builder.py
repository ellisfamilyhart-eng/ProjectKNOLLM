"""
Jarvix - Context Builder + Knowledge Summary
Two utilities:

ContextBuilder
  Builds a compact BrainState for the response generator.
  Uses intern IDs so the same string is never repeated.
  Only retrieves facts relevant to the current topic.
  Keeps the token footprint tiny.

KnowledgeSummary
  Formats memory for "what do you know?" / "list topics" queries.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ══════════════════════════════════════════════════════════════════
# CONTEXT BUILDER
# ══════════════════════════════════════════════════════════════════

@dataclass
class BrainState:
    """
    Minimal structured context — what the response generator receives.
    All string IDs are interned so repeated names cost 1 entry.
    """
    intent:         int   = 0        # Intent code
    intent_name:    str   = "CHAT"
    topic:          str   = ""
    mood:           str   = "curious"
    goal:           str   = ""       # what the response should accomplish

    # Compact fact list: [(relation, object_, confidence)]
    facts:          list  = field(default_factory=list)

    # Inference results from this turn
    inferred:       list  = field(default_factory=list)

    # Contradiction info if present
    conflict:       Optional[dict] = None

    # Working memory context
    last_topic:     str   = ""
    last_question:  str   = ""
    pending_q:      str   = ""

    # Intern map: id -> real string (kept outside the prompt)
    _intern:        dict  = field(default_factory=dict, repr=False)
    _rev_intern:    dict  = field(default_factory=dict, repr=False)
    _next_id:       int   = 0

    def intern(self, s: str) -> int:
        """Return numeric ID for a string, creating if needed."""
        if s not in self._rev_intern:
            self._rev_intern[s] = self._next_id
            self._intern[self._next_id] = s
            self._next_id += 1
        return self._rev_intern[s]

    def resolve(self, id_: int) -> str:
        return self._intern.get(id_, str(id_))

    def compact_facts(self) -> list:
        """
        Return facts as (rel, obj_str, conf) using already-interned objects.
        Sorted by confidence descending.
        """
        return sorted(self.facts, key=lambda x: -x[2])

    def to_prompt_context(self, max_facts: int = 8) -> str:
        """
        Minimal text representation for response generation.
        Designed to be small — only what the response generator needs.
        """
        lines = []

        if self.topic:
            lines.append(f"Topic: {self.topic}")

        if self.conflict:
            c = self.conflict
            lines.append(
                f"Conflict: '{c.get('existing_obj')}' vs '{c.get('new_obj')}'"
                f" on {c.get('relation')}"
            )

        facts = self.compact_facts()[:max_facts]
        if facts:
            lines.append("Known:")
            for rel, obj, conf in facts:
                lines.append(f"  {rel} {obj}  [{conf:.0%}]")

        if self.inferred:
            lines.append(f"Inferred: {len(self.inferred)} new fact(s)")

        if self.pending_q:
            lines.append(f"Waiting for answer to: {self.pending_q}")

        return "\n".join(lines)


class ContextBuilder:
    """Builds a BrainState for one turn from the agent's current state."""

    def __init__(self, agent):
        self.agent = agent

    def build(self, intent_result, triple=None,
              conflict=None, inferred=None) -> BrainState:
        wm    = self.agent.working_memory
        state = BrainState(
            intent       = intent_result.code,
            intent_name  = intent_result.name,
            topic        = self._topic(intent_result, triple),
            mood         = self.agent.brain.emotional_state,
            goal         = self._goal(intent_result.code),
            conflict     = self._pack_conflict(conflict),
            inferred     = inferred or [],
            last_topic   = wm.state.current_topic,
            last_question = "",
            pending_q    = wm.state.pending_question or "",
        )

        # Load topic-scoped facts from semantic memory
        if state.topic:
            for edge in self.agent.semantic_memory.outgoing(state.topic)[:10]:
                oid = state.intern(edge.object_)
                state.facts.append((edge.relation, edge.object_, edge.confidence))
            # Also singular/plural variant
            alt = state.topic[:-1] if state.topic.endswith("s") else state.topic + "s"
            if alt != state.topic:
                for edge in self.agent.semantic_memory.outgoing(alt)[:5]:
                    state.facts.append((edge.relation, edge.object_, edge.confidence))

        return state

    def _topic(self, intent_result, triple) -> str:
        if triple and triple.subject not in ("unknown", ""):
            return triple.subject
        if intent_result.subject:
            return intent_result.subject
        return self.agent.working_memory.state.current_topic or ""

    def _goal(self, intent_code: int) -> str:
        from .intent_classifier import Intent
        goals = {
            Intent.CHAT:         "acknowledge",
            Intent.QUESTION:     "answer",
            Intent.TEACH:        "confirm_and_learn",
            Intent.MEMORY_QUERY: "show_memory",
            Intent.IDENTITY:     "acknowledge_identity",
            Intent.COMMAND:      "execute_command",
            Intent.WEB_REQUEST:  "fetch_and_learn",
            Intent.CLARIFY:      "resolve",
            Intent.DEFINITION:   "store_definition",
            Intent.EXAMPLE:      "store_example",
        }
        return goals.get(intent_code, "respond")

    def _pack_conflict(self, conflict) -> Optional[dict]:
        if conflict is None:
            return None
        return {
            "subject":      conflict.subject,
            "relation":     conflict.relation,
            "existing_obj": conflict.existing_object,
            "existing_conf":conflict.existing_conf,
            "new_obj":      conflict.new_object,
        }


# ══════════════════════════════════════════════════════════════════
# KNOWLEDGE SUMMARY
# ══════════════════════════════════════════════════════════════════

class KnowledgeSummary:
    """Formats memory for display — never used as LLM input."""

    def __init__(self, agent):
        self.agent = agent

    def full_summary(self) -> str:
        """High-level overview of everything Jarvix knows."""
        mem    = self.agent.memory
        sem    = self.agent.semantic_memory
        conf   = self.agent.confidence_mgr

        topics = sorted(mem.facts.keys())
        stats  = conf.stats()

        total_facts  = sum(len(v) for v in mem.facts.values())
        avg_conf     = stats.get("avg_confidence", 0.0)
        mastered     = stats.get("mastered", 0)

        lines = [
            "Knowledge Summary",
            "=" * 40,
            f"Topics  : {len(topics)}",
            f"Facts   : {total_facts}",
            f"Mastered: {mastered}",
            f"Avg conf: {avg_conf:.0%}",
            "",
            "Topics:",
            "-" * 20,
        ]

        for topic in topics[:20]:
            facts = sorted(mem.facts[topic].items(),
                           key=lambda kv: -(kv[1].get("confidence", kv[1])
                                            if isinstance(kv[1], dict)
                                            else kv[1]))
            top = facts[0][0] if facts else ""
            n   = len(facts)
            lines.append(f"  {topic}  ({n} fact{'s' if n != 1 else ''})  — {top[:50]}")

        if len(topics) > 20:
            lines.append(f"  ... and {len(topics) - 20} more")

        # Graph summary
        g = self.agent.brain.graph.stats()
        lines += [
            "",
            f"Graph: {g['nodes']} nodes  {g['edges']} edges  "
            f"{g['inferred_edges']} inferred",
        ]

        return "\n".join(lines)

    def topic_summary(self, topic: str) -> str:
        """Everything known about one topic."""
        t     = topic.lower().strip()
        facts = self.agent.memory.facts.get(t, {})

        # Try singular/plural
        if not facts:
            alt = t[:-1] if t.endswith("s") else t + "s"
            facts = self.agent.memory.facts.get(alt, {})
            if facts:
                t = alt

        sem_edges = self.agent.semantic_memory.outgoing(t)

        if not facts and not sem_edges:
            return f"I haven't learned anything about '{topic}' yet."

        lines = [f"About '{t}':", "-" * 30]

        # Semantic edges (rich)
        if sem_edges:
            for edge in sem_edges[:10]:
                lines.append(f"  {edge.relation:15} {edge.object_}  "
                              f"[{edge.confidence:.0%}]")
        else:
            # Flat facts fallback
            sorted_facts = sorted(
                facts.items(),
                key=lambda kv: -(kv[1].get("confidence", kv[1])
                                  if isinstance(kv[1], dict) else kv[1]),
            )
            for fact, state in sorted_facts[:10]:
                conf = state.get("confidence", state) if isinstance(state, dict) else state
                lines.append(f"  {fact[:60]}  [{conf:.0%}]")

        # Check for inference
        all_edges = self.agent.semantic_memory.outgoing(t)
        inferred  = [e for e in all_edges if e.inferred]
        if inferred:
            lines.append(f"\n  (+ {len(inferred)} inferred fact(s))")

        return "\n".join(lines)

    def facts_dump(self, limit: int = 30) -> str:
        """Raw fact dump, limited rows."""
        lines = ["Facts (most confident first):"]
        count = 0
        for topic, facts in sorted(self.agent.memory.facts.items()):
            for fact, state in sorted(
                facts.items(),
                key=lambda kv: -(kv[1].get("confidence", kv[1])
                                  if isinstance(kv[1], dict) else kv[1]),
            )[:3]:
                conf = state.get("confidence", state) if isinstance(state, dict) else state
                lines.append(f"  {topic}: {fact[:55]}  [{conf:.0%}]")
                count += 1
                if count >= limit:
                    lines.append(f"  ... ({sum(len(v) for v in self.agent.memory.facts.values()) - limit} more)")
                    return "\n".join(lines)
        return "\n".join(lines) if len(lines) > 1 else "No facts stored yet."
