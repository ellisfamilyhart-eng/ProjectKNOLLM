"""
Jarvix NoLLM - Parser Module
Natural language processing and input parsing
"""

import re


class InputParser:
    """
    Lightweight NLP parser.

    Supports:
    - Topic: Fact
    - X is Y
    - X are Y
    - X means Y
    - X has Y

    Also detects commands and questions.
    """

    QUESTION_WORDS = (
        "what", "who", "where", "when", "why", "how",
        "can", "could", "would", "should",
        "do", "does", "did",
        "is", "are", "am",
        "will", "shall"
    )

    @staticmethod
    def normalize(text):
        """Normalize text for comparisons."""
        if not text:
            return ""

        text = text.lower().strip()

        # Remove punctuation except apostrophes
        text = re.sub(r"[^\w\s']", " ", text)

        # Collapse whitespace
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    @staticmethod
    def parse(user_input):
        """
        Parse user input into (topic, fact).

        Returns:
            (topic, fact)
            (None, None) if the input is not teaching.
        """

        if not user_input:
            return None, None

        text = user_input.strip()

        if not text:
            return None, None

        # Ignore commands
        if InputParser.is_command(text):
            return None, None

        # Ignore questions
        if InputParser.is_question(text):
            return None, None

        # Topic: Fact
        if ":" in text:
            topic, fact = text.split(":", 1)

            topic = topic.strip()
            fact = fact.strip()

            if topic and fact:
                return topic, fact

        # X means Y
        m = re.match(r"^(.+?)\s+means\s+(.+)$", text, re.I)
        if m:
            return m.group(1).strip(), m.group(2).strip()

        # X is Y
        m = re.match(r"^(.+?)\s+is\s+(.+)$", text, re.I)
        if m:
            return m.group(1).strip(), m.group(2).strip()

        # X are Y
        m = re.match(r"^(.+?)\s+are\s+(.+)$", text, re.I)
        if m:
            return m.group(1).strip(), m.group(2).strip()

        # X has Y
        m = re.match(r"^(.+?)\s+has\s+(.+)$", text, re.I)
        if m:
            return m.group(1).strip(), m.group(2).strip()

        # X have Y
        m = re.match(r"^(.+?)\s+have\s+(.+)$", text, re.I)
        if m:
            return m.group(1).strip(), m.group(2).strip()

        return None, None

    @staticmethod
    def is_question(user_input):
        """Return True if the input looks like a question."""

        if not user_input:
            return False

        text = user_input.strip().lower()

        if text.endswith("?"):
            return True

        return text.startswith(InputParser.QUESTION_WORDS)

    @staticmethod
    def is_command(user_input):
        """Check if input is a command."""

        return bool(user_input and user_input.strip().startswith("/"))

    @staticmethod
    def parse_command(user_input):
        """Extract command and arguments."""

        if not user_input:
            return None, []

        parts = user_input.strip().split()

        if not parts:
            return None, []

        cmd = parts[0].lstrip("/").lower()
        args = parts[1:]

        return cmd, args

    @staticmethod
    def validate_fact(topic, fact):
        """Validate a topic/fact pair."""

        if not topic or not fact:
            return False

        topic = topic.strip()
        fact = fact.strip()

        if len(topic) < 2:
            return False

        if len(fact) < 2:
            return False

        return True

    @staticmethod
    def extract_keywords(text):
        """Extract keywords from text."""

        if not text:
            return []

        stop_words = {
            "is", "the", "a", "an", "and", "or", "but",
            "in", "on", "at", "to", "for", "of", "by",
            "with", "from", "be", "are", "was", "were",
            "been", "have", "has", "do", "does", "did",
            "will", "would", "could", "should", "may",
            "might", "must", "can", "am"
        }

        words = re.findall(r"[a-zA-Z']+", text.lower())

        keywords = []

        for word in words:
            if len(word) <= 2:
                continue

            if word in stop_words:
                continue

            if word not in keywords:
                keywords.append(word)

        return keywords