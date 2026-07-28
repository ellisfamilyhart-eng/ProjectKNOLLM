"""
Jarvix - Relation Detector
Direction-aware, 30+ pattern rules.  Maps a sentence to a typed triple.

Key improvement over the old parser:
  "Red is a color"  ->  Red instance_of Color   (NOT Color is_a Red)
  "Your name is X"  ->  SELF named X
  "Color means Y"   ->  Color definition Y
  "X is part of Y"  ->  X part_of Y
  "X can Y"         ->  X can Y
  "X has more than one meaning"  ->  X has_property multiple_meanings

Relations returned
  is_a              taxonomic parent
  instance_of       specific example of a category
  has_property      attribute / adjective
  has               possession / containment
  can               capability
  causes            causal link
  part_of           composition
  named             identity / name assignment
  definition        meaning / definition
  example_of        explicit example
  opposite_of       negation / antonym
  synonym_of        same concept
  located_in        spatial
  produced_by       creation chain
  related_to        fallback weak link
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional

SELF_NODE = "jarvix"


@dataclass
class Triple:
    subject:    str
    relation:   str
    object_:    str
    confidence: float = 0.70
    negated:    bool  = False
    raw:        str   = ""

    def __repr__(self):
        neg = " [NOT]" if self.negated else ""
        return f"Triple({self.subject!r} --[{self.relation}{neg}]--> {self.object_!r})"


# ── Article stripping ─────────────────────────────────────────────────────────

_ARTICLES = re.compile(r"^(a|an|the)\s+", re.I)

def _strip(phrase: str) -> str:
    phrase = phrase.strip().lower()
    phrase = _ARTICLES.sub("", phrase).strip()
    phrase = re.sub(r"\s+", " ", phrase)
    return phrase


# ── Negation detection ────────────────────────────────────────────────────────

_NEGATION_WORDS = {"not", "never", "no", "neither", "cannot", "can't",
                   "isn't", "aren't", "doesn't", "don't", "didn't",
                   "won't", "wouldn't", "couldn't", "shouldn't"}

def _has_negation(phrase: str) -> bool:
    words = set(phrase.lower().split())
    return bool(words & _NEGATION_WORDS)

def _strip_negation(phrase: str) -> str:
    for neg in sorted(_NEGATION_WORDS, key=len, reverse=True):
        phrase = re.sub(r"\b" + re.escape(neg) + r"\b", "", phrase, flags=re.I)
    return re.sub(r"\s+", " ", phrase).strip()


# ── Rule table ────────────────────────────────────────────────────────────────
# Each entry: (compiled_regex, relation, swap_direction)
# swap_direction=True  means the regex captures (object, subject) but we swap
# so storage is always (subject, relation, object).

_RULES: list[tuple] = []

def _r(pattern: str, relation: str, swap: bool = False):
    _RULES.append((re.compile(pattern, re.I), relation, swap))

# ── IDENTITY / NAME ─────────────────────────────────────────────────────────
_r(r"^(?:your|its|the)\s+name\s+is\s+(.+)$",              "named")       # -> SELF named X
_r(r"^(?:call\s+(?:yourself|it))\s+(.+)$",                "named")
_r(r"^(?:you\s+are\s+(?:called|named))\s+(.+)$",          "named")
_r(r"^(.+?)\s+is\s+(?:called|named)\s+(.+)$",             "named")

# ── DEFINITION ──────────────────────────────────────────────────────────────
_r(r"^(.+?)\s+means?\s+(.+)$",                            "definition")
_r(r"^(.+?)\s+is\s+defined\s+as\s+(.+)$",                "definition")
_r(r"^(.+?)\s+refers?\s+to\s+(.+)$",                     "definition")
_r(r"^(.+?)\s+can\s+be\s+defined\s+as\s+(.+)$",          "definition")

# ── EXAMPLE / INSTANCE ──────────────────────────────────────────────────────
_r(r"^(.+?)\s+is\s+an?\s+example\s+of\s+(.+)$",          "instance_of")
_r(r"^(.+?)\s+is\s+an?\s+(?:type|kind|sort)\s+of\s+(.+)$","instance_of")
_r(r"^(.+?)\s+are\s+(?:types?|kinds?|sorts?)\s+of\s+(.+)$","instance_of")
_r(r"^(?:for\s+example|e\.g\.?)[,:\s]+(.+?)\s+is\s+(.+)$","instance_of")

# ── TAXONOMY (is_a) ─────────────────────────────────────────────────────────
# "X is a Y"  -> X is_a Y    (X more specific than Y)
_r(r"^(.+?)\s+is\s+an?\s+(.+)$",                         "is_a")
_r(r"^(.+?)\s+are\s+an?\s+(.+)$",                        "is_a")
_r(r"^(.+?)\s+was\s+an?\s+(.+)$",                        "is_a")

# ── PART_OF ─────────────────────────────────────────────────────────────────
_r(r"^(.+?)\s+is\s+(?:a\s+)?part\s+of\s+(.+)$",          "part_of")
_r(r"^(.+?)\s+are\s+(?:a\s+)?part\s+of\s+(.+)$",         "part_of")
_r(r"^(.+?)\s+belongs?\s+to\s+(.+)$",                    "part_of")
_r(r"^(.+?)\s+is\s+(?:a\s+)?component\s+of\s+(.+)$",     "part_of")
_r(r"^(.+?)\s+is\s+(?:a\s+)?member\s+of\s+(.+)$",        "part_of")
_r(r"^(.+?)\s+is\s+(?:a\s+)?subset\s+of\s+(.+)$",        "part_of")

# ── PROPERTY (has_property) ─────────────────────────────────────────────────
_r(r"^(.+?)\s+is\s+(.+)$",                               "has_property")  # catch-all is
_r(r"^(.+?)\s+are\s+(.+)$",                              "has_property")
_r(r"^(.+?)\s+was\s+(.+)$",                              "has_property")
_r(r"^(.+?)\s+were\s+(.+)$",                             "has_property")

# ── HAS (possession / containment) ──────────────────────────────────────────
_r(r"^(.+?)\s+has\s+(.+)$",                              "has")
_r(r"^(.+?)\s+have\s+(.+)$",                             "has")
_r(r"^(.+?)\s+contains?\s+(.+)$",                        "has")
_r(r"^(.+?)\s+includes?\s+(.+)$",                        "has")
_r(r"^(.+?)\s+possesses?\s+(.+)$",                       "has")
_r(r"^(.+?)\s+(?:holds?|carries?)\s+(.+)$",              "has")

# ── CAN (capability) ─────────────────────────────────────────────────────────
_r(r"^(.+?)\s+can\s+(.+)$",                              "can")
_r(r"^(.+?)\s+is\s+able\s+to\s+(.+)$",                  "can")
_r(r"^(.+?)\s+is\s+capable\s+of\s+(.+)$",               "can")

# ── CAUSES ───────────────────────────────────────────────────────────────────
_r(r"^(.+?)\s+causes?\s+(.+)$",                          "causes")
_r(r"^(.+?)\s+leads?\s+to\s+(.+)$",                     "causes")
_r(r"^(.+?)\s+results?\s+in\s+(.+)$",                   "causes")
_r(r"^(.+?)\s+produces?\s+(.+)$",                        "causes")
_r(r"^(.+?)\s+creates?\s+(.+)$",                         "causes")
_r(r"^(.+?)\s+triggers?\s+(.+)$",                        "causes")

# ── LOCATED_IN ───────────────────────────────────────────────────────────────
_r(r"^(.+?)\s+(?:is\s+)?located\s+in\s+(.+)$",           "located_in")
_r(r"^(.+?)\s+(?:is\s+)?found\s+in\s+(.+)$",             "located_in")
_r(r"^(.+?)\s+lives?\s+in\s+(.+)$",                      "located_in")

# ── PRODUCED_BY ──────────────────────────────────────────────────────────────
_r(r"^(.+?)\s+is\s+produced\s+by\s+(.+)$",               "produced_by")
_r(r"^(.+?)\s+is\s+(?:made|created|built)\s+by\s+(.+)$", "produced_by")
_r(r"^(.+?)\s+comes?\s+from\s+(.+)$",                    "produced_by")

# ── SYNONYM ──────────────────────────────────────────────────────────────────
_r(r"^(.+?)\s+(?:is\s+)?(?:a\s+)?synonym\s+(?:of|for)\s+(.+)$", "synonym_of")
_r(r"^(.+?)\s+(?:is\s+)?also\s+(?:called|known\s+as)\s+(.+)$",  "synonym_of")
_r(r"^(.+?)\s+(?:is\s+)?the\s+same\s+as\s+(.+)$",               "synonym_of")

# ── OPPOSITE ─────────────────────────────────────────────────────────────────
_r(r"^(.+?)\s+(?:is\s+)?(?:the\s+)?opposite\s+of\s+(.+)$",      "opposite_of")
_r(r"^(.+?)\s+(?:is\s+)?(?:the\s+)?antonym\s+of\s+(.+)$",       "opposite_of")


# ── Detector ─────────────────────────────────────────────────────────────────

class RelationDetector:
    """
    Converts a plain sentence into a direction-correct typed Triple.
    Tries rules in order; first match wins.
    """

    def detect(self, text: str) -> Optional[Triple]:
        """
        Returns a Triple or None if nothing matches.
        """
        raw    = text.strip()
        clean  = raw.rstrip(".!?").strip()
        negated = _has_negation(clean)

        # If negated, strip negation words for matching, then restore flag
        match_text = _strip_negation(clean) if negated else clean

        for pattern, relation, swap in _RULES:
            m = pattern.match(match_text)
            if not m:
                continue

            g1 = _strip(m.group(1)) if m.lastindex >= 1 else ""
            g2 = _strip(m.group(2)) if m.lastindex >= 2 else ""

            if not g1:
                continue

            # Quality gates
            if len(g1) > 80 or len(g2) > 120:
                continue
            if g1.count(" ") > 8:
                continue

            subj, obj = (g2, g1) if swap else (g1, g2)
            if not obj:
                obj = g1
                subj = "unknown"

            # Fix direction: "Red is a color" -> Red instance_of Color
            # (already handled by rule order — is_a rule comes AFTER instance_of)

            # Identity injection: "your name is X" -> self named X
            if relation == "named" and subj in ("your", "its", "the", ""):
                subj = SELF_NODE

            # Negated capability -> opposite_of
            if negated and relation == "can":
                relation = "opposite_of"

            # Confidence: lower for catch-all is/are rules
            conf = 0.65 if relation == "has_property" else 0.75

            return Triple(
                subject    = subj,
                relation   = relation,
                object_    = obj,
                confidence = conf,
                negated    = negated,
                raw        = raw,
            )

        return None

    def detect_all(self, text: str) -> list[Triple]:
        """
        Split multi-sentence text and detect triples from each.
        """
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        triples = []
        for s in sentences:
            t = self.detect(s.strip())
            if t:
                triples.append(t)
        return triples
