"""
Jarvix - Command Engine
Dispatches reserved-keyword commands that bypass the fact parser entirely.
Returns a CommandResult with a plain-text response and optional metadata.

Commands
  learn_url      fetch URL, crawl, store facts
  forget         clear all memory
  forget_topic   clear one topic
  show_memory    dump current knowledge
  summarize      summarize a topic or all knowledge
  remember       explicit store reminder
  list_topics    list known topics
  list_facts     list facts (optionally filtered by topic)
  slash_command  /stats /memory /clear /reflect /help
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CommandResult:
    command:  str
    response: str
    metadata: dict = field(default_factory=dict)
    success:  bool = True


class CommandEngine:
    """
    Executes commands without touching the fact-learning pipeline.
    Receives the agent instance so it can call any method it needs.
    """

    def __init__(self, agent):
        self.agent = agent

    def execute(self, command: str, arg: str = "",
                url: str = "", raw: str = "") -> CommandResult:
        """Route to the right handler based on command name."""
        dispatch = {
            "learn_url":     self._learn_url,
            "forget":        self._forget,
            "forget_topic":  self._forget_topic,
            "show_memory":   self._show_memory,
            "summarize":     self._summarize,
            "remember":      self._remember,
            "list_topics":   self._list_topics,
            "list_facts":    self._list_facts,
            "slash_command": self._slash,
        }
        handler = dispatch.get(command, self._unknown)
        return handler(arg=arg.strip(), url=url.strip(), raw=raw.strip())

    # ── Handlers ─────────────────────────────────────────────────────────────

    def _learn_url(self, arg: str = "", url: str = "") -> CommandResult:
        target = url or arg
        if not target:
            return CommandResult(
                "learn_url",
                "No URL found. Paste a full URL starting with http:// or https://",
                success=False,
            )
        try:
            from .web_crawler import WebCrawler
            crawler = WebCrawler(self.agent, max_depth=1, max_pages=8)
            report  = crawler.crawl(target)
            eval_   = crawler.build_evaluation(report)

            lines = [
                f"Crawled: {target}",
                f"Pages: {report.pages_visited}  "
                f"Facts stored: {report.stored_facts}  "
                f"Duplicates: {report.duplicate_facts}",
                f"Knowledge gain: +{report.knowledge_gain:.1f}%",
                f"Quality: {eval_['summary']['quality_score']}",
            ]
            if report.top_topics:
                lines.append(f"Top topics: {', '.join(report.top_topics[:5])}")
            if eval_["inference_note"]:
                lines.append(eval_["inference_note"])

            return CommandResult(
                "learn_url",
                "\n".join(lines),
                metadata=eval_,
            )
        except Exception as e:
            return CommandResult("learn_url", f"Error crawling {target}: {e}",
                                 success=False)

    def _forget(self, arg: str = "", **_) -> CommandResult:
        self.agent.clear_memory()
        return CommandResult("forget",
                             "All memories cleared. Starting fresh.")

    def _forget_topic(self, arg: str = "", **_) -> CommandResult:
        if not arg:
            return CommandResult("forget_topic", "Which topic should I forget?",
                                 success=False)
        topic = arg.lower().strip()
        removed = 0
        if topic in self.agent.memory.facts:
            removed = len(self.agent.memory.facts[topic])
            del self.agent.memory.facts[topic]
        # Also from semantic memory
        keys = [(s, r, o) for (s, r, o) in self.agent.semantic_memory.edges
                if s == topic or o == topic]
        for k in keys:
            self.agent.semantic_memory.edges.pop(k, None)
        self.agent.memory.closed_topics.discard(topic)
        return CommandResult(
            "forget_topic",
            f"Forgotten '{topic}' ({removed} facts removed).",
        )

    def _show_memory(self, **_) -> CommandResult:
        from .knowledge_summary import KnowledgeSummary
        ks   = KnowledgeSummary(self.agent)
        text = ks.full_summary()
        return CommandResult("show_memory", text,
                             metadata={"summary": text})

    def _summarize(self, arg: str = "", **_) -> CommandResult:
        from .knowledge_summary import KnowledgeSummary
        ks = KnowledgeSummary(self.agent)
        if arg:
            text = ks.topic_summary(arg.strip())
        else:
            text = ks.full_summary()
        return CommandResult("summarize", text)

    def _remember(self, arg: str = "", **_) -> CommandResult:
        # Explicit reminder: "remember X" -> teach it
        if not arg:
            return CommandResult("remember", "Remember what?", success=False)
        response = self.agent.process_input(arg)
        return CommandResult("remember",
                             f"Noted: {arg}\n{response}")

    def _list_topics(self, **_) -> CommandResult:
        topics = sorted(self.agent.memory.facts.keys())
        if not topics:
            return CommandResult("list_topics",
                                 "I haven't learned any topics yet.")
        lines = [f"I know about {len(topics)} topic(s):"]
        for t in topics:
            n = len(self.agent.memory.facts[t])
            lines.append(f"  {t}  ({n} fact{'s' if n != 1 else ''})")
        return CommandResult("list_topics", "\n".join(lines),
                             metadata={"topics": topics})

    def _list_facts(self, arg: str = "", **_) -> CommandResult:
        from .knowledge_summary import KnowledgeSummary
        ks = KnowledgeSummary(self.agent)
        if arg:
            text = ks.topic_summary(arg.strip())
        else:
            text = ks.facts_dump(limit=30)
        return CommandResult("list_facts", text)

    def _slash(self, arg: str = "", raw: str = "", **_) -> CommandResult:
        """Handle /word slash commands. Uses raw input to extract command word."""
        import re as _re
        m   = _re.match(r'^/([\w]+)', raw)
        cmd = m.group(1).lower() if m else (arg.lstrip("/").split()[0].lower() if arg else "")
        if cmd in ("stats", "status"):
            stats = self.agent.get_stats()
            lines = ["--- Stats ---"]
            for k, v in stats.items():
                lines.append(f"  {k}: {v}")
            return CommandResult("slash", "\n".join(lines),
                                 metadata=stats)
        if cmd in ("memory", "mem"):
            return self._show_memory()
        if cmd in ("clear", "forget", "reset"):
            return self._forget()
        if cmd in ("reflect",):
            result = self.agent.reflect()
            return CommandResult("slash", str(result))
        if cmd in ("topics",):
            return self._list_topics()
        if cmd in ("help", "?"):
            help_text = (
                "Commands:\n"
                "  /stats          Agent statistics\n"
                "  /memory         Show all knowledge\n"
                "  /topics         List known topics\n"
                "  /clear          Erase all memory\n"
                "  /reflect        Run reflection cycle\n"
                "  /help           This help\n\n"
                "Natural commands:\n"
                "  learn from: <url>    Crawl and learn from a URL\n"
                "  forget <topic>       Remove a topic\n"
                "  summarize <topic>    Summarize a topic\n"
                "  list topics          List all topics\n"
                "  what do you know?    Knowledge summary"
            )
            return CommandResult("slash", help_text)
        return CommandResult("slash",
                             f"Unknown command: /{cmd}. Try /help.",
                             success=False)

    def _unknown(self, **_) -> CommandResult:
        return CommandResult("unknown",
                             "I don't know that command. Try /help.",
                             success=False)
