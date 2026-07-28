"""
Jarvix Memory Classifier v1

Determines what kind of memory an input represents.

Later this can be replaced or enhanced
by NeuralLearner.
"""


from .memory_models import MemoryType



class MemoryClassification:


    def __init__(
        self,
        memory_type: MemoryType,
        confidence: float,
        importance: float
    ):

        self.memory_type = memory_type

        self.confidence = confidence

        self.importance = importance



    def to_dict(self):

        return {

            "type":
                self.memory_type.value,

            "confidence":
                self.confidence,

            "importance":
                self.importance

        }




class MemoryClassifier:



    def classify(
        self,
        text: str
    ) -> MemoryClassification:


        text_lower = text.lower()



        # Personal information
        if any(
            word in text_lower
            for word in [
                "my name is",
                "i like",
                "i love",
                "my favourite",
                "my favorite"
            ]
        ):

            return MemoryClassification(
                MemoryType.FACT,
                0.9,
                0.8
            )



        # Learning experiences
        if any(
            word in text_lower
            for word in [
                "i learned",
                "i fixed",
                "i discovered",
                "i found",
                "the problem was"
            ]
        ):

            return MemoryClassification(
                MemoryType.EXPERIENCE,
                0.85,
                0.7
            )



        # Definitions
        if any(
            word in text_lower
            for word in [
                "is a",
                "is an",
                "means",
                "defined as"
            ]
        ):

            return MemoryClassification(
                MemoryType.FACT,
                0.8,
                0.6
            )



        # Current tasks
        if any(
            word in text_lower
            for word in [
                "need to",
                "working on",
                "building",
                "creating"
            ]
        ):

            return MemoryClassification(
                MemoryType.WORKING,
                0.75,
                0.7
            )



        # Default
        return MemoryClassification(
            MemoryType.SHORT_TERM,
            0.4,
            0.3
        )