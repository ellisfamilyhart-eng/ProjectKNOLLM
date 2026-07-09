"""
Jarvix NLP Parser v3
Fixed: "what is a dog" -> object_=dog (not subject=what)
       "what is an apple" -> object_=apple
       alias expansion before parse
"""

from dataclasses import dataclass, field
import re


@dataclass
class Sentence:
    subject:       str
    verb:          str
    object_:       str
    relation_type: str
    modifiers:     list = field(default_factory=list)
    negated:       bool = False
    sentence_type: str  = "statement"
    raw:           str  = ""

    def __repr__(self):
        neg = " NOT" if self.negated else ""
        return (f"Sentence({self.subject!r} --[{self.relation_type}{neg}]--> "
                f"{self.object_!r}  [{self.sentence_type}])")


# ── Vocabulary ────────────────────────────────────────────────────────────────

QUESTION_STARTERS = {
    "what", "who", "where", "when", "why", "which",
    "is", "are", "do", "does", "did",
    "would", "should", "have", "has", "may", "might",
}

NEGATION_WORDS = {
    "not", "no", "never",
    "cannot", "can't", "isn't", "aren't",
    "doesn't", "don't", "didn't", "won't", "wont",
}

ARTICLES = {"a", "an", "the"}

IMPERATIVE_VERBS = {"tell", "describe", "explain", "show", "give", "list", "name"}

KNOWN_VERBS = {
    "is", "are", "was", "were", "be", "been", "being",
    "has", "have", "had",
    "does", "do", "did",
    "can", "could", "will", "would", "should", "may", "might", "must",
    "goes", "go", "comes", "come", "makes", "make", "takes", "take",
    "gives", "give", "puts", "put", "gets", "get",
    "says", "say", "sees", "see", "knows", "know",
    "thinks", "think", "feels", "feel",
    "reads", "read", "writes", "write", "runs", "run",
    "eats", "eat", "moves", "move", "lives", "live",
    "works", "work", "flies", "fly", "swims", "swim",
    "causes", "cause", "leads", "produces", "creates",
    "contains", "include", "includes",
    "belongs", "belong",
    "orbits", "orbit", "powers", "power", "stores", "store",
    "gains", "gain", "expects", "expect", "responds", "respond",
    "identifies", "identify", "measures", "measure",
} | IMPERATIVE_VERBS

IS_A_MARKERS    = {"is a", "is an", "are a", "are an", "was a", "is one of", "are one of"}
PART_OF_MARKERS = {"is part of", "are part of", "belongs to", "belong to"}
CAUSES_MARKERS  = {"causes", "cause", "leads to", "results in", "produces", "creates"}
HAS_MARKERS     = {"has", "have", "had", "contains", "include", "includes"}
CAPABILITY_VERBS= {"can", "could", "able to"}
ACTION_VERBS    = {"does", "do", "did", "runs", "run", "eats", "eat",
                   "moves", "move", "lives", "live", "works", "work",
                   "reads", "read", "writes", "write", "flies", "fly",
                   "swims", "swim", "orbits", "orbit", "powers", "power",
                   "stores", "store", "gains", "gain", "expects", "expect",
                   "responds", "respond", "identifies", "identify",
                   "measures", "measure"}

WORD_TYPES = {
    "read":"verb","write":"verb","learn":"verb","teach":"verb",
    "run":"verb","eat":"verb","think":"verb","see":"verb",
    "hear":"verb","speak":"verb","understand":"verb","process":"verb",
    "fly":"verb","swim":"verb","move":"verb","live":"verb",
    "cat":"noun","dog":"noun","mammal":"noun","animal":"noun",
    "earth":"noun","planet":"noun","human":"noun","person":"noun",
    "sentence":"noun","word":"noun","language":"noun","text":"noun",
    "gravity":"noun","force":"noun","energy":"noun","matter":"noun",
    "bird":"noun","fish":"noun","tree":"noun","water":"noun",
    "red":"adjective","blue":"adjective","fast":"adjective",
    "slow":"adjective","big":"adjective","small":"adjective",
    "round":"adjective","flat":"adjective","hot":"adjective",
    "cold":"adjective","alive":"adjective","dead":"adjective",
    "one":"number","two":"number","three":"number","four":"number",
}

# ── Alias / contraction normalisation ────────────────────────────────────────

_ALIAS_PATTERNS = [
    (re.compile(r"\bwhat's\b",  re.I), "what is"),
    (re.compile(r"\bwho's\b",   re.I), "who is"),
    (re.compile(r"\bwhere's\b", re.I), "where is"),
    (re.compile(r"\bhow's\b",   re.I), "how is"),
    (re.compile(r"\bcan't\b",   re.I), "cannot"),
    (re.compile(r"\bdon't\b",   re.I), "do not"),
    (re.compile(r"\bdoesn't\b", re.I), "does not"),
    (re.compile(r"\bisn't\b",   re.I), "is not"),
    (re.compile(r"\baren't\b",  re.I), "are not"),
]

def _expand_aliases(text: str) -> str:
    for pat, rep in _ALIAS_PATTERNS:
        text = pat.sub(rep, text)
    return text


# ── "what is X" extractor ────────────────────────────────────────────────────
# Handles: "what is a dog", "what is an apple", "what is the sun", "what are cats"
_WHAT_IS_RE = re.compile(
    r"^what\s+(?:is|are)\s+(?:a\s+|an\s+|the\s+)?(.+?)[\s?]*$",
    re.I
)


class NLPParser:
    """Rule-based SVO parser v3. No external dependencies."""

    def parse(self, text: str) -> Sentence:
        raw     = text.strip()
        aliased = _expand_aliases(raw)
        clean   = self._clean(aliased)
        words   = clean.split()

        if not words:
            return Sentence("unknown", "unknown", "unknown", "related_to", raw=raw)

        negated = self._is_negated(words)

        # ── "can [subject] [verb]?" ───────────────────────────────
        if words[0] == "can":
            return self._parse_capability(words, negated, raw)

        # ── Imperative "tell/describe/…" ──────────────────────────
        if words[0] in IMPERATIVE_VERBS:
            return self._parse_imperative(words, negated, raw)

        stype = self._detect_type(words)

        if stype == "question":
            return self._parse_question(words, negated, raw, clean)
        else:
            return self._parse_statement(words, negated, raw)

    def parse_bulk(self, text: str) -> list:
        sentences = re.split(r"[.!?]\s+", text.strip())
        return [self.parse(s) for s in sentences if s.strip()]

    # ── Sentence parsers ──────────────────────────────────────────────────────

    def _parse_capability(self, words, negated, raw):
        if len(words) < 3:
            subj   = words[1] if len(words) > 1 else "unknown"
            action = "unknown"
        else:
            subj   = words[1]
            action_words = [w for w in words[2:] if w not in ARTICLES]
            action = action_words[0] if action_words else "unknown"
        subj = self._strip_articles(subj)
        rel  = "opposite_of" if negated else "can"
        return Sentence(subject=subj, verb="can", object_=action,
                        relation_type=rel, negated=negated,
                        sentence_type="capability", raw=raw)

    def _parse_imperative(self, words, negated, raw):
        skip    = {"me", "about", "us"}
        content = [w for w in words[1:] if w not in skip and w not in ARTICLES]
        obj     = " ".join(content) if content else "unknown"
        return Sentence(subject="unknown", verb=words[0], object_=obj,
                        relation_type="related_to", negated=negated,
                        sentence_type="question", raw=raw)

    def _parse_question(self, words, negated, raw, clean):
        q_word = words[0]

        # ── KEY FIX: "what is a/an/the X" → object_=X, subject=X ─
        # The QuestionBrain handles answering; the parser just extracts the noun.
        if q_word in ("what", "who", "which"):
            m = _WHAT_IS_RE.match(clean)
            if m:
                noun = m.group(1).strip()
                return Sentence(subject=noun, verb="is", object_=noun,
                                relation_type="has_property", negated=negated,
                                sentence_type="question", raw=raw)
            # Fallback: skip q-word + is/are/article
            remainder = [w for w in words[1:]
                         if w not in ("is", "are", "was") and w not in ARTICLES]
            obj = " ".join(remainder) if remainder else "unknown"
            return Sentence(subject=obj, verb="is", object_=obj,
                            relation_type="has_property", negated=negated,
                            sentence_type="question", raw=raw)

        # "is/are/do/does [subject] [predicate]?"
        if q_word in ("is", "are", "do", "does") and len(words) >= 3:
            subj       = self._strip_articles(words[1])
            pred       = self._strip_articles(" ".join(words[2:]))
            pred_clean = " ".join(w for w in pred.split() if w not in NEGATION_WORDS)
            rel        = "opposite_of" if negated else self._classify_relation(
                             q_word, pred_clean, negated=False)
            return Sentence(subject=subj, verb=q_word,
                            object_=pred_clean or "unknown",
                            relation_type=rel, negated=negated,
                            sentence_type="question", raw=raw)

        # Generic fallback
        subj, verb, obj = self._extract_svo(
            words[1:] if len(words) > 1 else words, "question")
        return Sentence(subject=subj if subj != "unknown" else q_word,
                        verb=verb, object_=obj,
                        relation_type=self._classify_relation(verb, obj, negated),
                        negated=negated, sentence_type="question", raw=raw)

    def _parse_statement(self, words, negated, raw):
        # Expand "cannot"
        expanded = []
        for w in words:
            if w == "cannot":
                expanded += ["can", "not"]
            else:
                expanded.append(w)
        words = expanded
        subj, verb, obj = self._extract_svo(words, "statement")
        rel = self._classify_relation(verb, obj, negated)
        return Sentence(subject=subj, verb=verb, object_=obj,
                        relation_type=rel,
                        modifiers=self._extract_modifiers(words, subj, verb, obj),
                        negated=negated, sentence_type="statement", raw=raw)

    # ── SVO extraction ────────────────────────────────────────────────────────

    def _extract_svo(self, words, stype):
        if not words:
            return "unknown", "unknown", "unknown"
        words_l  = [w.lower() for w in words]
        verb_idx = None
        for i, w in enumerate(words_l):
            if i == 0 and w not in KNOWN_VERBS:
                continue
            if w in KNOWN_VERBS:
                verb_idx = i
                break
        if verb_idx is None:
            mid = max(1, len(words_l) // 2)
            return (self._strip_articles(" ".join(words_l[:mid])),
                    "is",
                    self._strip_articles(" ".join(words_l[mid:])))
        subj    = self._strip_articles(" ".join(words_l[:verb_idx]).strip()) or "unknown"
        verb    = words_l[verb_idx]
        raw_obj = " ".join(words_l[verb_idx + 1:]).strip()
        obj_words = [w for w in raw_obj.split() if w not in NEGATION_WORDS]
        obj     = self._strip_articles(" ".join(obj_words)) or "unknown"
        return subj, verb, obj

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _detect_type(self, words):
        if not words:
            return "statement"
        first = words[0].lower()
        if first == "can":
            return "capability"
        if first in QUESTION_STARTERS:
            return "question"
        if words[-1].endswith("?"):
            return "question"
        return "statement"

    def _is_negated(self, words):
        return any(w.lower() in NEGATION_WORDS for w in words)

    def _strip_articles(self, phrase):
        words = phrase.strip().split()
        while words and words[0] in ARTICLES:
            words = words[1:]
        return " ".join(words) or phrase.strip()

    def _classify_relation(self, verb, obj, negated):
        if negated:
            return "opposite_of"
        v      = verb.lower()
        phrase = f"{v} {obj}".lower()
        if v in ("is", "are", "was", "were", "be", "been"):
            obj_words = obj.split()
            if obj_words and obj_words[0] in ("a", "an"):
                return "is_a"
            if obj_words and obj_words[0] not in ARTICLES:
                return "is_a"
            return "has_property"
        for m in IS_A_MARKERS:
            if phrase.startswith(m):
                return "is_a"
        for m in PART_OF_MARKERS:
            if m in phrase:
                return "part_of"
        for m in CAUSES_MARKERS:
            if v in m or phrase.startswith(v):
                return "causes"
        if v in CAPABILITY_VERBS:
            return "can"
        if v in HAS_MARKERS:
            return "has"
        if v in ACTION_VERBS:
            return "does"
        if v in IMPERATIVE_VERBS:
            return "related_to"
        return "related_to"

    def _extract_modifiers(self, words, subj, verb, obj):
        content = set((subj + " " + obj).split())
        return [w.lower() for w in words
                if w.lower() in WORD_TYPES
                and WORD_TYPES[w.lower()] == "adjective"
                and w.lower() not in content]

    def _clean(self, text):
        text = text.lower()
        text = re.sub(r"[^\w\s\-]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def classify_word(self, word):
        wl = word.lower()
        if wl in WORD_TYPES:  return WORD_TYPES[wl]
        if wl in KNOWN_VERBS: return "verb"
        return "noun"
