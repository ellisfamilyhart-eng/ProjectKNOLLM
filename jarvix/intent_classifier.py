"""
Jarvix - Intent Classifier
Deterministic rule-based classification.  Zero tokens consumed.
Returns an IntentResult with a numeric code and extracted metadata.

Intent codes (numeric, used internally — never sent to an LLM)
  0  CHAT          hi / thanks / casual
  1  QUESTION      what/who/how/why/where/when + ?
  2  TEACH         declarative statement with a fact
  3  MEMORY_QUERY  what do you know / list topics / show memory
  4  IDENTITY      your name is X / call yourself X / who are you
  5  COMMAND       read / learn from / forget / show / summarize / open
  6  WEB_REQUEST   URL present + learn/read/fetch/open verb or bare URL
  7  CLARIFY       yes/no/both as answer to a pending question
  8  DEFINITION    X means / X is defined as / definition of X
  9  EXAMPLE       for example / e.g. / such as / X is an example
  10 UNKNOWN       fallback
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional

# ── Intent codes ──────────────────────────────────────────────────────────────

class Intent:
    CHAT         = 0
    QUESTION     = 1
    TEACH        = 2
    MEMORY_QUERY = 3
    IDENTITY     = 4
    COMMAND      = 5
    WEB_REQUEST  = 6
    CLARIFY      = 7
    DEFINITION   = 8
    EXAMPLE      = 9
    UNKNOWN      = 10

    _NAMES = {
        0: "CHAT", 1: "QUESTION", 2: "TEACH", 3: "MEMORY_QUERY",
        4: "IDENTITY", 5: "COMMAND", 6: "WEB_REQUEST", 7: "CLARIFY",
        8: "DEFINITION", 9: "EXAMPLE", 10: "UNKNOWN",
    }

    @classmethod
    def name(cls, code: int) -> str:
        return cls._NAMES.get(code, "UNKNOWN")


@dataclass
class IntentResult:
    code:       int             # Intent.* constant
    confidence: float = 1.0    # how certain we are (rule-based = always 1.0)
    subject:    str   = ""     # extracted subject if present
    predicate:  str   = ""     # extracted verb/relation phrase
    object_:    str   = ""     # extracted object / value
    url:        str   = ""     # URL if detected
    command:    str   = ""     # command keyword if code==COMMAND or WEB_REQUEST
    raw:        str   = ""     # original text

    @property
    def name(self) -> str:
        return Intent.name(self.code)

    def __repr__(self):
        return (f"IntentResult({self.name}, subj={self.subject!r}, "
                f"pred={self.predicate!r}, obj={self.object_!r})")


# ── Patterns (compiled once at import) ───────────────────────────────────────

_URL_RE = re.compile(
    r"https?://[^\s\)\]>\"']+", re.IGNORECASE
)

_QUESTION_STARTERS = frozenset([
    "what","who","where","when","why","how","which","whose","whom",
    "is","are","do","does","did","can","could","will","would",
    "should","have","has","may","might",
])

# --- Memory queries (checked before generic question) ---
_MEMORY_EXACT = frozenset([
    "what do you know", "what do you know?",
    "what have you learned", "what have you learned?",
    "what did you learn", "what did you learn?",
    "show memory", "show what you know", "list topics",
    "list everything", "list all topics", "list facts",
    "tell me what you know", "summarize knowledge",
    "knowledge summary", "what topics do you know",
    "what have you stored", "show knowledge",
    "what facts do you have",
])

_MEMORY_STARTS = (
    "what do you know",
    "what have you learned",
    "what did you learn",
    "tell me everything you know",
    "show me what you know",
    "list what you know",
    "what topics",
    "what facts",
    "show your memory",
    "memory summary",
    "knowledge summary",
)

# --- Identity ---
_IDENTITY_PATTERNS = [
    re.compile(r"^(?:your|my)\s+name\s+is\s+(.+)$", re.I),
    re.compile(r"^call\s+(?:yourself|me)\s+(.+)$", re.I),
    re.compile(r"^(?:you\s+are|you're)\s+(?:called|named)\s+(.+)$", re.I),
    re.compile(r"^(?:i\s+am|i'm)\s+(.+)$", re.I),
    re.compile(r"^who\s+are\s+you\??$", re.I),
    re.compile(r"^what\s+(?:is\s+your\s+name|are\s+you\s+called)\??$", re.I),
]

# --- Definition ---
_DEFINITION_PATTERNS = [
    re.compile(r"^(.+?)\s+means?\s+(.+)$", re.I),
    re.compile(r"^(.+?)\s+is\s+defined\s+as\s+(.+)$", re.I),
    re.compile(r"^definition\s+of\s+(.+?)\s*[:\-]\s*(.+)$", re.I),
    re.compile(r"^meaning\s+of\s+(.+?)\s*[:\-]\s*(.+)$", re.I),
    re.compile(r"^meaning\s*[:\-]\s*(.+)$", re.I),
    re.compile(r"^define\s+(.+?)\s+as\s+(.+)$", re.I),
    re.compile(r"^(.+?)\s+refers?\s+to\s+(.+)$", re.I),
]

# --- Example ---
_EXAMPLE_PATTERNS = [
    re.compile(r"^(?:for\s+example|e\.g\.?|such\s+as|for\s+instance)[,:\s]+(.+)$", re.I),
    re.compile(r"^(.+?)\s+is\s+an?\s+example\s+of\s+(.+)$", re.I),
    re.compile(r"^(?:an?\s+example\s+(?:of|is))\s+(.+)$", re.I),
    re.compile(r"^(.+?)\s+for\s+example[:\s]+(.+)$", re.I),
    re.compile(r"^a\s+(?:color|colour)\s+is[:\s]+(.+)$", re.I),
]

# --- Commands (reserved keywords that BYPASS the fact parser) ---
# Format: (pattern, command_name)
_COMMAND_PATTERNS = [
    (re.compile(r"^(?:learn\s+from|read\s+(?:page|url|link|from)?)\s*[:\-]?\s*(.+)$", re.I), "learn_url"),
    (re.compile(r"^(?:open|fetch|crawl|scrape)\s+(.+)$", re.I),                               "learn_url"),
    (re.compile(r"^(?:forget|clear|reset|wipe)\s+(?:everything|all|memory)?$", re.I),         "forget"),
    (re.compile(r"^(?:forget|clear)\s+(.+)$", re.I),                                          "forget_topic"),
    (re.compile(r"^(?:show|display|print)\s+(?:memory|facts|knowledge|topics)$", re.I),       "show_memory"),
    (re.compile(r"^(?:summarize|summarise)(?:\s+(.+))?$", re.I),                              "summarize"),
    (re.compile(r"^(?:remember|save)\s+(.+)$", re.I),                                         "remember"),
    (re.compile(r"^(?:list|show)\s+(?:all\s+)?topics$", re.I),                                "list_topics"),
    (re.compile(r"^(?:list|show)\s+(?:all\s+)?facts(?:\s+about\s+(.+))?$", re.I),            "list_facts"),
    (re.compile(r"^/\w+", re.I),                                                               "slash_command"),
]

# --- Clarification (yes/no/both following a pending question) ---
_CLARIFY_EXACT = frozenset([
    "yes","no","both","neither","correct","wrong","right","incorrect",
    "true","false","maybe","not sure","both are true","both are correct",
    "yes both","nope","yep","yeah","nah","exactly","precisely",
])

# --- Casual chat ---
_CASUAL_EXACT = frozenset([
    "hi","hello","hey","thanks","thank you","ok","okay","cool","bye",
    "goodbye","good morning","good afternoon","good evening","good night",
    "lol","haha","wow","hmm","yep","nope","sure","great","awesome",
    "nice","interesting","good","bad","fine","alright","welcome",
    "how are you","how are you doing","what's up","sup",
])

_CASUAL_STARTS = (
    "haha","lol","omg","oh wow","oh my","oh no",
)


# ── Classifier ────────────────────────────────────────────────────────────────

class IntentClassifier:
    """
    Fully deterministic, zero-token intent classifier.
    Checked in strict priority order so high-confidence patterns
    always win before ambiguous ones.
    """

    def classify(self, text: str) -> IntentResult:
        raw   = text.strip()
        clean = raw.lower().strip().rstrip("?.,!")
        words = clean.split()

        if not words:
            return IntentResult(Intent.CHAT, raw=raw)

        # ── 1. Bare URL → WEB_REQUEST ──────────────────────────────
        if _URL_RE.match(raw.strip()):
            return IntentResult(Intent.WEB_REQUEST, url=raw.strip(),
                                command="learn_url", raw=raw)

        # ── 2. Commands (reserved keywords, bypass parser) ─────────
        for pattern, cmd_name in _COMMAND_PATTERNS:
            m = pattern.match(clean)
            if m:
                arg = m.group(1).strip() if m.lastindex and m.group(1) else ""
                url = _URL_RE.search(arg).group(0) if _URL_RE.search(arg) else ""
                return IntentResult(Intent.COMMAND, command=cmd_name,
                                    object_=arg, url=url, raw=raw)

        # ── 3. URL anywhere in text → WEB_REQUEST ──────────────────
        url_match = _URL_RE.search(raw)
        if url_match:
            return IntentResult(Intent.WEB_REQUEST, url=url_match.group(0),
                                command="learn_url", raw=raw)

        # ── 4. Memory query (before generic question) ───────────────
        if clean in _MEMORY_EXACT:
            return IntentResult(Intent.MEMORY_QUERY, raw=raw)
        for prefix in _MEMORY_STARTS:
            if clean.startswith(prefix):
                return IntentResult(Intent.MEMORY_QUERY, raw=raw)

        # ── 5. Identity ─────────────────────────────────────────────
        for pattern in _IDENTITY_PATTERNS:
            m = pattern.match(raw.strip())
            if m:
                value = m.group(1).strip() if m.lastindex else ""
                return IntentResult(Intent.IDENTITY, object_=value, raw=raw)

        # ── 6. Definition ────────────────────────────────────────────
        for pattern in _DEFINITION_PATTERNS:
            m = pattern.match(raw.strip())
            if m:
                subj = m.group(1).strip() if m.lastindex >= 1 else ""
                obj  = m.group(2).strip() if m.lastindex >= 2 else raw
                return IntentResult(Intent.DEFINITION, subject=subj,
                                    object_=obj, raw=raw)

        # ── 7. Example ───────────────────────────────────────────────
        for pattern in _EXAMPLE_PATTERNS:
            m = pattern.match(raw.strip())
            if m:
                subj = m.group(1).strip() if m.lastindex >= 1 else ""
                obj  = m.group(2).strip() if m.lastindex >= 2 else subj
                return IntentResult(Intent.EXAMPLE, subject=subj,
                                    object_=obj, raw=raw)

        # ── 8. Casual chat ───────────────────────────────────────────
        if clean in _CASUAL_EXACT or len(words) <= 2 and ":" not in raw:
            for prefix in _CASUAL_STARTS:
                if clean.startswith(prefix):
                    return IntentResult(Intent.CHAT, raw=raw)
            if clean in _CASUAL_EXACT:
                return IntentResult(Intent.CHAT, raw=raw)
            if len(words) == 1:
                return IntentResult(Intent.CHAT, raw=raw)

        # ── 9. Clarification ─────────────────────────────────────────
        if clean in _CLARIFY_EXACT:
            return IntentResult(Intent.CLARIFY, object_=clean, raw=raw)

        # ── 10. Question ─────────────────────────────────────────────
        if raw.strip().endswith("?") or words[0] in _QUESTION_STARTERS:
            subj, obj = self._extract_question_focus(words)
            return IntentResult(Intent.QUESTION, subject=subj,
                                object_=obj, raw=raw)

        # ── 11. Teach (default for declarative statements) ───────────
        return IntentResult(Intent.TEACH, raw=raw)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _extract_question_focus(self, words: list) -> tuple:
        """Best-effort: strip question words, return (topic, detail)."""
        stop = {
            "what","who","where","when","why","how","which",
            "is","are","do","does","did","can","could","will","would",
            "should","have","has","the","a","an","you","i",
        }
        focus = [w for w in words if w not in stop and len(w) > 1]
        if not focus:
            return "", ""
        mid = max(1, len(focus) // 2)
        return " ".join(focus[:mid]), " ".join(focus[mid:])
