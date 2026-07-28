"""
Jarvix NoLLM
relations.py

Global ontology describing every relationship Jarvix understands.

Every module should import relations from this file instead of using
hard-coded strings.

Example:

from relations import *

memory.add_edge("dog", R_IS_A, "mammal")

instead of

memory.add_edge("dog", "is_a", "mammal")
"""

# ============================================================================
# Canonical Relations
# ============================================================================

R_IS = "is"
R_IS_A = "is_a"
R_INSTANCE_OF = "instance_of"

R_HAS = "has"
R_HAS_PROPERTY = "has_property"

R_CAN = "can"
R_DOES = "does"

R_MEANS = "means"
R_DEFINITION = "definition"

R_PART_OF = "part_of"
R_HAS_PART = "has_part"

R_CAUSES = "causes"
R_CAUSED_BY = "caused_by"

R_CREATED_BY = "created_by"
R_CREATES = "creates"

R_USED_FOR = "used_for"

R_LOCATED_IN = "located_in"

R_MEMBER_OF = "member_of"

R_RELATED_TO = "related_to"

R_OPPOSITE_OF = "opposite_of"

R_SIMILAR_TO = "similar_to"

R_BEFORE = "before"
R_AFTER = "after"

R_GREATER_THAN = "greater_than"
R_LESS_THAN = "less_than"

R_EQUALS = "equals"

R_EXAMPLE_OF = "example_of"

R_CATEGORY = "category"

R_FEELS = "feels"

R_WANTS = "wants"

R_LIKES = "likes"

R_DISLIKES = "dislikes"

R_BELIEVES = "believes"

R_KNOWS = "knows"

R_LEARNED_FROM = "learned_from"

R_SAID = "said"

R_ASKED = "asked"

R_ANSWERED = "answered"

R_REMEMBERS = "remembers"

# ============================================================================
# Aliases
# ============================================================================

RELATION_ALIASES = {

    "is": R_IS,

    "are": R_IS,

    "was": R_IS,

    "were": R_IS,

    "means": R_MEANS,

    "mean": R_MEANS,

    "defines": R_DEFINITION,

    "definition": R_DEFINITION,

    "has": R_HAS,

    "have": R_HAS,

    "contains": R_HAS,

    "owns": R_HAS,

    "can": R_CAN,

    "able_to": R_CAN,

    "does": R_DOES,

    "did": R_DOES,

    "part_of": R_PART_OF,

    "inside": R_PART_OF,

    "belongs_to": R_MEMBER_OF,

    "member_of": R_MEMBER_OF,

    "causes": R_CAUSES,

    "creates": R_CREATES,

    "produces": R_CREATES,

    "located_in": R_LOCATED_IN,

    "in": R_LOCATED_IN,

    "example_of": R_EXAMPLE_OF,

    "instance_of": R_INSTANCE_OF,

    "related": R_RELATED_TO,

    "related_to": R_RELATED_TO,

    "similar_to": R_SIMILAR_TO,

    "opposite": R_OPPOSITE_OF,

    "opposite_of": R_OPPOSITE_OF,

    "likes": R_LIKES,

    "dislikes": R_DISLIKES,

    "wants": R_WANTS,

    "believes": R_BELIEVES,

    "knows": R_KNOWS,

    "feels": R_FEELS,

    "before": R_BEFORE,

    "after": R_AFTER,

    "=": R_EQUALS,

    "equals": R_EQUALS,

    ">": R_GREATER_THAN,

    "<": R_LESS_THAN,
}

# ============================================================================
# Reverse Relations
# ============================================================================

INVERSE_RELATIONS = {

    R_PART_OF: R_HAS_PART,

    R_HAS_PART: R_PART_OF,

    R_CAUSES: R_CAUSED_BY,

    R_CAUSED_BY: R_CAUSES,

    R_CREATES: R_CREATED_BY,

    R_CREATED_BY: R_CREATES,

    R_BEFORE: R_AFTER,

    R_AFTER: R_BEFORE,

}

# ============================================================================
# Symmetric Relations
# ============================================================================

SYMMETRIC_RELATIONS = {

    R_RELATED_TO,

    R_SIMILAR_TO,

    R_OPPOSITE_OF,

    R_EQUALS,

}

# ============================================================================
# Transitive Relations
# ============================================================================

TRANSITIVE_RELATIONS = {

    R_IS_A,

    R_INSTANCE_OF,

    R_PART_OF,

    R_MEMBER_OF,

    R_LOCATED_IN,

    R_BEFORE,

    R_AFTER,

}

# ============================================================================
# Reasoning Priorities
# ============================================================================

RELATION_PRIORITY = {

    R_IS_A: 100,

    R_INSTANCE_OF: 95,

    R_DEFINITION: 95,

    R_MEANS: 90,

    R_HAS_PROPERTY: 85,

    R_HAS: 80,

    R_CAN: 75,

    R_DOES: 70,

    R_PART_OF: 70,

    R_USED_FOR: 70,

    R_CAUSES: 65,

    R_CREATES: 65,

    R_RELATED_TO: 40,

}

# ============================================================================
# Confidence Defaults
# ============================================================================

DEFAULT_CONFIDENCE = {

    R_IS_A: 0.95,

    R_INSTANCE_OF: 0.95,

    R_DEFINITION: 0.90,

    R_MEANS: 0.90,

    R_HAS_PROPERTY: 0.85,

    R_HAS: 0.85,

    R_CAN: 0.85,

    R_DOES: 0.80,

    R_PART_OF: 0.85,

    R_USED_FOR: 0.80,

    R_CAUSES: 0.75,

    R_CREATES: 0.75,

    R_RELATED_TO: 0.60,

    R_SIMILAR_TO: 0.55,

}

# ============================================================================
# Helpers
# ============================================================================

def normalize_relation(relation: str) -> str:
    """
    Convert any alias into the canonical relation.
    """
    if not relation:
        return R_RELATED_TO

    relation = relation.strip().lower().replace(" ", "_")

    return RELATION_ALIASES.get(relation, relation)


def inverse_relation(relation: str):
    """
    Return the inverse relation if one exists.
    """
    return INVERSE_RELATIONS.get(normalize_relation(relation))


def is_transitive(relation: str):
    """
    True if A→B and B→C implies A→C.
    """
    return normalize_relation(relation) in TRANSITIVE_RELATIONS


def is_symmetric(relation: str):
    """
    True if A→B implies B→A.
    """
    return normalize_relation(relation) in SYMMETRIC_RELATIONS


def default_confidence(relation: str):
    """
    Default confidence for a newly learned edge.
    """
    relation = normalize_relation(relation)
    return DEFAULT_CONFIDENCE.get(relation, 0.70)


def relation_priority(relation: str):
    """
    Importance of this relation during reasoning.
    """
    relation = normalize_relation(relation)
    return RELATION_PRIORITY.get(relation, 50)