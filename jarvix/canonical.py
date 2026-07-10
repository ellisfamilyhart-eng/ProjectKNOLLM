"""
Jarvix - Canonical Concept Normaliser
Phase 1: Every concept gets one canonical node before any lookup/insert/query.

canonical("a Dog")       -> "dog"
canonical("the Planets") -> "planet"
canonical("AI")          -> "artificial intelligence"
canonical("colours")     -> "color"
"""

import re
from typing import Optional

# ── Alias table: variant -> canonical ────────────────────────────────────────
# Add entries freely — lowercase on both sides.

ALIASES: dict[str, str] = {
    # self-referential
    "jarvix":             "jarvix",
    "curiousmind":        "jarvix",
    "curious mind":       "jarvix",
    "the ai":             "jarvix",
    "you":                "jarvix",

    # common abbreviations
    "ai":                 "artificial intelligence",
    "ml":                 "machine learning",
    "dl":                 "deep learning",
    "nlp":                "natural language processing",
    "cpu":                "processor",
    "gpu":                "graphics processor",
    "os":                 "operating system",
    "pc":                 "computer",
    "www":                "internet",
    "url":                "web address",
    "ui":                 "user interface",
    "api":                "application programming interface",
    "db":                 "database",
    "sql":                "structured query language",
    "html":               "html",
    "css":                "css",
    "js":                 "javascript",
    "py":                 "python",

    # British/American spelling
    "colour":             "color",
    "colours":            "color",
    "flavour":            "flavor",
    "behaviour":          "behavior",
    "organisation":       "organization",
    "recognised":         "recognized",
    "grey":               "gray",

    # plurals that don't singularise cleanly
    "mathematics":        "math",
    "maths":              "math",
    "physics":            "physics",
    "economics":          "economics",
    "linguistics":        "language",
    "sciences":           "science",
    "humanities":         "humanities",
    "countries":          "country",
    "cities":             "city",
    "languages":          "language",
    "animals":            "animal",
    "mammals":            "mammal",
    "planets":            "planet",
    "stars":              "star",
    "colors":             "color",
    "colours":            "color",
    "fruits":             "fruit",
    "vegetables":         "vegetable",
    "programming languages": "programming language",

    # common synonyms
    "means":              "definition",
    "definition":         "definition",
    "example":            "instance",
    "instances":          "instance",
    "kind":               "type",
    "kinds":              "type",
    "sorts":              "type",
    "sort":               "type",
    "category":           "type",
    "categories":         "type",
}

# ── Articles to strip ─────────────────────────────────────────────────────────
_ARTICLES = re.compile(r"^(a|an|the)\s+", re.I)

# ── Simple singulariser (rule-based, English only) ───────────────────────────
# Covers the most common cases without nltk.

_IRREGULAR_PLURAL = {
    "children": "child", "people": "person", "men": "man",
    "women": "woman", "teeth": "tooth", "feet": "foot",
    "mice": "mouse", "geese": "goose", "oxen": "ox",
    "phenomena": "phenomenon", "criteria": "criterion",
    "data": "datum", "media": "medium",
    "indices": "index", "matrices": "matrix",
    "vertices": "vertex", "axes": "axis",
    "analyses": "analysis", "crises": "crisis",
    "theses": "thesis", "bases": "base",
}

def _singularise(word: str) -> str:
    """
    Convert an English plural word to singular.
    Single word only — call per token if needed.
    """
    w = word.lower()
    if w in _IRREGULAR_PLURAL:
        return _IRREGULAR_PLURAL[w]
    # Don't singularise short words or already-singular-looking words
    if len(w) <= 3:
        return w
    # -ies -> -y  (flies -> fly, but NOT series -> sery)
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    # -ses / -xes / -zes / -ches / -shes -> strip -es
    if re.search(r"(s|x|z|ch|sh)es$", w):
        return w[:-2]
    # -ves -> -f / -fe  (leaves -> leaf, knives -> knife)
    if w.endswith("ves"):
        stem = w[:-3]
        if stem + "f" in ("leaf", "wolf", "shelf", "loaf", "calf"):
            return stem + "f"
        return stem + "fe"
    # plain -s (not -ss)
    if w.endswith("s") and not w.endswith("ss") and len(w) > 2:
        return w[:-1]
    return w


def _singularise_phrase(phrase: str) -> str:
    """Singularise only the LAST word of a multi-word phrase."""
    words = phrase.split()
    if not words:
        return phrase
    words[-1] = _singularise(words[-1])
    return " ".join(words)


# ── Public API ────────────────────────────────────────────────────────────────

def canonical(text: str) -> str:
    """
    Return the canonical form of a concept string.
    Steps: lowercase -> strip punctuation -> strip articles
           -> singularise last word -> alias lookup
    """
    if not text:
        return text

    # 1. lowercase + strip surrounding punctuation/whitespace
    t = text.lower().strip().strip(".,!?;:'\"")

    # 2. strip leading articles
    t = _ARTICLES.sub("", t).strip()

    # 3. normalise internal whitespace
    t = re.sub(r"\s+", " ", t)

    # 4. alias lookup (before singularising, in case alias is plural)
    if t in ALIASES:
        return ALIASES[t]

    # 5. singularise last word
    t = _singularise_phrase(t)

    # 6. alias lookup again (after singularising)
    if t in ALIASES:
        return ALIASES[t]

    return t


def canonical_pair(subject: str, object_: str) -> tuple[str, str]:
    """Canonicalise both sides of a triple."""
    return canonical(subject), canonical(object_)


def add_alias(variant: str, canonical_form: str):
    """Register a new alias at runtime."""
    ALIASES[variant.lower().strip()] = canonical_form.lower().strip()
