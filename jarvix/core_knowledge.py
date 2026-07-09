"""
Jarvix - Core Knowledge
50 built-in concepts seeded at startup so Jarvix can hold a basic
conversation without needing to be taught elementary vocabulary.

Also contains built-in identity facts and common-question handlers
that return deterministic answers without touching the knowledge graph.
"""

from __future__ import annotations

# ── Self-knowledge ─────────────────────────────────────────────────────────

SELF_FACTS = {
    "name":        "Jarvix",
    "version":     "5.1",
    "type":        "self-learning AI",
    "creator":     "built with Python, no LLMs",
    "description": (
        "I am Jarvix, a self-learning AI. "
        "I learn from what you teach me, remember facts, "
        "reason about connections, and ask questions when curious."
    ),
    "can_do": [
        "learn facts from conversation",
        "remember everything you teach me",
        "answer questions based on what I know",
        "detect contradictions in what I learn",
        "infer new facts from existing knowledge",
        "crawl web pages and learn from them",
        "ask follow-up questions to fill gaps",
    ],
    "cannot_do": [
        "access the internet on my own",
        "see images",
        "hear audio",
        "generate creative text without facts to draw from",
    ],
}

# ── Built-in seed triples (subject, relation, object_, confidence) ──────────

SEED_TRIPLES = [
    # Meta / self
    ("jarvix",       "is_a",        "ai",                     0.99),
    ("jarvix",       "can",         "learn facts",            0.99),
    ("jarvix",       "can",         "remember",               0.99),
    ("jarvix",       "can",         "answer questions",       0.95),
    ("jarvix",       "can",         "reason about knowledge", 0.90),
    ("jarvix",       "can",         "read text",              0.95),
    ("jarvix",       "opposite_of", "see images",             0.95),
    ("jarvix",       "opposite_of", "hear audio",             0.95),
    # Learning concepts
    ("learning",     "definition",  "acquiring new knowledge or skills",   0.90),
    ("learning",     "is_a",        "cognitive process",                   0.85),
    ("fact",         "definition",  "a piece of true information",         0.90),
    ("knowledge",    "definition",  "facts and information acquired",      0.90),
    ("memory",       "definition",  "stored information from the past",    0.90),
    ("question",     "definition",  "a request for information",           0.90),
    ("answer",       "definition",  "a response to a question",            0.90),
    ("topic",        "definition",  "a subject being discussed",           0.90),
    ("name",         "definition",  "a label used to identify something",  0.95),
    ("word",         "definition",  "a unit of language with meaning",     0.90),
    ("language",     "definition",  "a system of communication",           0.90),
    ("sentence",     "definition",  "a complete unit of written or spoken language", 0.90),
    # Common concepts
    ("ai",           "definition",  "artificial intelligence — machines that simulate thinking", 0.90),
    ("computer",     "definition",  "a machine that processes information", 0.90),
    ("internet",     "definition",  "a global network of computers",       0.85),
    ("human",        "is_a",        "mammal",                              0.90),
    ("human",        "can",         "think",                               0.90),
    ("human",        "can",         "learn",                               0.90),
    ("animal",       "definition",  "a living organism that is not a plant", 0.85),
    ("mammal",       "is_a",        "animal",                              0.90),
    ("mammal",       "has_property","warm-blooded",                        0.90),
    ("dog",          "is_a",        "mammal",                              0.90),
    ("cat",          "is_a",        "mammal",                              0.90),
    ("color",        "definition",  "a property of light perceived by the eye", 0.90),
    ("red",          "instance_of", "color",                               0.95),
    ("blue",         "instance_of", "color",                               0.95),
    ("green",        "instance_of", "color",                               0.95),
    ("number",       "definition",  "a mathematical value used to count",  0.90),
    ("science",      "definition",  "systematic study of the natural world", 0.90),
    ("math",         "definition",  "the study of numbers and patterns",   0.90),
    ("programming",  "definition",  "writing instructions for a computer", 0.90),
    ("python",       "is_a",        "programming language",                0.95),
    ("gravity",      "definition",  "a force that pulls objects together", 0.90),
    ("planet",       "definition",  "a large body orbiting a star",        0.90),
    ("earth",        "is_a",        "planet",                              0.95),
    ("sun",          "definition",  "the star at the center of our solar system", 0.95),
    ("water",        "definition",  "a molecule of hydrogen and oxygen",   0.90),
    ("time",         "definition",  "the progression of events from past to future", 0.85),
    ("space",        "definition",  "the vast expanse beyond Earth's atmosphere", 0.85),
    ("energy",       "definition",  "the capacity to do work",             0.90),
    ("information",  "definition",  "data that has meaning and context",   0.90),
    ("truth",        "definition",  "a statement that corresponds to reality", 0.85),
]


# ── Common question handler (deterministic, no graph lookup needed) ──────────

QUESTION_MAP = {
    # Identity
    "what is your name":          lambda: f"My name is {SELF_FACTS['name']}.",
    "what are you":               lambda: SELF_FACTS["description"],
    "who are you":                lambda: SELF_FACTS["description"],
    "introduce yourself":         lambda: SELF_FACTS["description"],
    "what can you do":            lambda: "I can:\n" + "\n".join(f"  - {c}" for c in SELF_FACTS["can_do"]),
    "what do you do":             lambda: SELF_FACTS["description"],
    "how do you learn":           lambda: (
        "You teach me by stating facts — like 'Dogs are mammals' or "
        "'Python: is a programming language'. I store them, reason about "
        "connections, and ask questions when I want to know more."
    ),
    "how much can you learn":     lambda: (
        "There's no hard limit — I grow with every conversation. "
        "The more you teach me, the more connections I can find."
    ),
    "what ways can you learn":    lambda: (
        "I learn in several ways:\n"
        "  - You teach me directly ('Topic: fact')\n"
        "  - I infer new facts from existing ones\n"
        "  - I crawl web pages when given a URL\n"
        "  - I ask follow-up questions to fill gaps\n"
        "  - I reinforce facts when I see them repeated"
    ),
    "can you learn":              lambda: "Yes! That's what I'm here for. Teach me something.",
    "what is learn":              lambda: QUESTION_MAP["what ways can you learn"](),
    "what is learning":           lambda: "Learning is the process of acquiring new knowledge or skills.",
    "what is your version":       lambda: f"I am Jarvix version {SELF_FACTS['version']}.",
    "what version are you":       lambda: f"I am Jarvix version {SELF_FACTS['version']}.",
}

# Normalisation helper
def _norm(text: str) -> str:
    import re
    t = text.lower().strip().rstrip("?.!")
    t = re.sub(r"\s+", " ", t)
    return t

def try_builtin_answer(text: str) -> str | None:
    """
    Check if the question matches a built-in answer.
    Returns the answer string, or None if not matched.
    """
    key = _norm(text)
    if key in QUESTION_MAP:
        return QUESTION_MAP[key]()

    # Partial match on key phrases
    matches = {
        "what is your name":       "what is your name",
        "what are you":            "what are you",
        "who are you":             "who are you",
        "what can you do":         "what can you do",
        "how do you learn":        "how do you learn",
        "how much can you learn":  "how much can you learn",
        "what ways can you learn": "what ways can you learn",
        "what have you learned":   None,   # handled by memory summary
        "what do you know":        None,   # handled by memory summary
        "can you learn":           "can you learn",
        "what is learning":        "what is learning",
    }
    for phrase, map_key in matches.items():
        if phrase in key:
            if map_key:
                return QUESTION_MAP[map_key]()
            return None   # caller handles via memory summary

    return None


def seed_agent(agent):
    """
    Seed the agent's graph and semantic memory with built-in triples.
    Called once at agent startup.  Skips triples already present.
    """
    for subj, rel, obj, conf in SEED_TRIPLES:
        # Only add if not already known
        existing = agent.semantic_memory.edge_confidence(subj, rel, obj)
        if existing < 0.1:
            agent.semantic_memory.add_edge(subj, rel, obj,
                                           confidence=conf, source="seed")
            agent.brain.graph.add_edge(subj, rel, obj,
                                       confidence=conf, source="seed")
