"""
Jarvix NoLLM
Knowledge Validator v2

Checks information before it enters memory.

Responsibilities:
- Reject empty data
- Detect suspicious inputs
- Score knowledge quality
- Prepare confidence level

It does NOT store memory.
It does NOT resolve contradictions.
"""

from dataclasses import dataclass


@dataclass
class ValidationResult:

    valid: bool

    confidence: float = 0.0

    reason: str = ""



class KnowledgeValidator:
    def __init__(self, semantic_memory):
        self.semantic_memory = semantic_memory

        self.checked = 0
        self.accepted = 0
        self.rejected = 0



    ############################################################
    # Main validation
    ############################################################

    def validate(
        self,
        subject,
        relation,
        object_
    ):

        self.checked += 1


        subject = self.clean(subject)
        relation = self.clean(relation)
        object_ = self.clean(object_)
        
        # Check if this knowledge already exists
        try:
            existing = self.semantic_memory.edge_confidence(
                subject,
                relation,
                object_
            )

            if existing >= 0.9:
                return self.reject(
                    "Knowledge already exists"
                )

        except Exception:
            # Semantic memory may not have the lookup method yet
            pass


        # Missing information

        if not subject:

            return self.reject(
                "Missing subject"
            )


        if not relation:

            return self.reject(
                "Missing relation"
            )


        if not object_:

            return self.reject(
                "Missing object"
            )



        ########################################################
        # Basic quality checks
        ########################################################


        confidence = 0.7



        # Very short concepts are suspicious

        if len(subject) < 2:

            confidence -= 0.2


        if len(object_) < 2:

            confidence -= 0.2



        # Self contradictions

        if subject == object_:

            return self.reject(
                "Subject and object are identical"
            )



        ########################################################
        # Accept
        ########################################################


        self.accepted += 1


        return ValidationResult(

            valid=True,

            confidence=max(
                0.1,
                confidence
            ),

            reason="Knowledge accepted"

        )



    ############################################################
    # Helpers
    ############################################################

    def clean(self, value):

        if not value:

            return ""


        return str(value).strip().lower()



    def reject(self, reason):

        self.rejected += 1


        return ValidationResult(

            valid=False,

            confidence=0.0,

            reason=reason

        )



    ############################################################
    # Stats
    ############################################################

    def stats(self):

        return {

            "checked": self.checked,

            "accepted": self.accepted,

            "rejected": self.rejected

        }