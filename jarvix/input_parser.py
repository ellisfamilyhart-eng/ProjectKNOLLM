"""
Jarvix NoLLM
Input Parser v3

Converts human language into structured information.

Does not reason.
Does not answer.
Only understands the shape of input.
"""


from dataclasses import dataclass
import re



@dataclass
class ParseResult:

    text: str

    intent: str = "UNKNOWN"

    subject: str = ""

    relation: str = ""

    object_: str = ""

    confidence: float = 0.0



class InputParser:



    QUESTION_WORDS = {
        "what",
        "who",
        "where",
        "when",
        "why",
        "how",
        "can",
        "could",
        "would",
        "should",
        "is",
        "are",
        "do",
        "does"
    }



    TEACH_WORDS = {
        "remember",
        "learn",
        "teach",
        "know"
    }



    CORRECTION_WORDS = {
        "no",
        "wrong",
        "actually",
        "correct"
    }

    ############################################################
    # Text normalization
    ############################################################

    def normalize(self, text):
        if not text:
            return ""

        text = str(text).lower().strip()

        # Keep apostrophes AND colons, but remove other punctuation
        text = re.sub(r"[^\w\s':]", " ", text)

        # Collapse spaces
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    ############################################################
    # Main parser
    ############################################################

    def parse(self, text):

        clean = self.normalize(text)


        result = ParseResult(
            text=clean
        )


        if not clean:

            return result



        ########################################################
        # Detect intent
        ########################################################


        words = clean.split()

        first = words[0]



        if first in self.QUESTION_WORDS:

            result.intent = "QUESTION"
            result.confidence = 0.9



        elif any(
            word in clean
            for word in self.CORRECTION_WORDS
        ):

            result.intent = "CORRECTION"
            result.confidence = 0.8



        elif any(
            word in clean
            for word in self.TEACH_WORDS
        ):

            result.intent = "TEACH"
            result.confidence = 0.8



        elif ":" in clean:

            result.intent = "TEACH"
            result.confidence = 0.9



        else:

            result.intent = "STATEMENT"
            result.confidence = 0.5



        ########################################################
        # Extract relationships
        ########################################################


        self.extract_relation(result)



        return result



    ############################################################
    # Relationship extraction
    ############################################################


    def extract_relation(self, result):

        text = result.text



        patterns = [

            (
                r"(.+?)\s+is\s+(.+)",
                "is_a"
            ),

            (
                r"(.+?)\s+are\s+(.+)",
                "is_a"
            ),

            (
                r"(.+?)\s+has\s+(.+)",
                "has"
            ),

            (
                r"(.+?)\s+have\s+(.+)",
                "has"
            ),

            (
                r"(.+?):\s*(.+)",
                "definition"
            ),

        ]



        for pattern, relation in patterns:

            match = re.match(
                pattern,
                text,
                re.I
            )


            if match:

                result.subject = (
                    match.group(1)
                    .strip()
                )

                result.relation = relation

                result.object_ = (
                    match.group(2)
                    .strip()
                )

                return



        ########################################################
        # Questions
        ########################################################


        if result.intent == "QUESTION":

            words = text.split()


            if len(words) > 1:

                result.subject = words[-1]
