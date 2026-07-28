"""
Jarvix NoLLM
Response Generator v3

Creates final user-facing responses with improved natural language and variability.

It does not reason or search memory.
It receives:
- reasoning result
- plan
- knowledge (facts)
- personality hints

and turns them into language.
"""


import random
from typing import List, Optional, Union, Dict, Any


class ResponseGenerator:

    def __init__(self):
        self.responses_generated = 0

        # Templates for different actions when facts are present
        self.lookup_templates = [
            "Based on what I know: {facts}",
            "Here's what I found: {facts}",
            "According to my knowledge: {facts}",
            "From my memory: {facts}",
            "This is what I recall: {facts}",
        ]

        self.store_templates = [
            "Got it! I've learned that {facts}",
            "Okay, I'll remember that {facts}",
            "Thanks for teaching me: {facts}",
            "I've stored this information: {facts}",
            "Noted: {facts}",
        ]

        self.respond_templates = [
            "{facts}",
            "Here's what I think: {facts}",
            "Based on my understanding: {facts}",
            "Let me share what I know: {facts}",
        ]

        self.greet_templates = [
            "Hello! {facts}",
            "Hi there! {facts}",
            "Hey! {facts}",
            "Greetings! {facts}",
        ]

        self.empathize_templates = [
            "I understand how you feel. {facts}",
            "That sounds tough. {facts}",
            "I'm here for you. {facts}",
            "I hear you. {facts}",
        ]

        # Templates for when no facts are available
        self.unknown_templates = [
            "I'm not sure about that yet. Could you teach me?",
            "I don't have information on that topic. Would you like to share what you know?",
            "I'm still learning about this. Can you help me understand?",
            "I haven't learned about this yet. Please explain?",
            "I don't know the answer, but I'm eager to learn from you.",
        ]

        # Fallback templates
        self.fallback_templates = [
            "I'm not sure how to respond to that.",
            "Let me think about that...",
            "That's interesting. Tell me more?",
            "I'm still processing that. Can you clarify?",
        ]

    def _format_facts(self, facts: List[Any]) -> str:
        """Convert a list of facts into a natural language string."""
        if not facts:
            return ""

        # Convert facts to strings if they aren't already
        fact_strings = []
        for fact in facts:
            if isinstance(fact, dict):
                # Expecting keys: subject, relation, object
                subj = fact.get('subject', '')
                rel = fact.get('relation', '')
                obj = fact.get('object', '')
                if subj and rel and obj:
                    # Make the relation more natural
                    rel_phrase = self._relation_to_phrase(rel)
                    if rel_phrase:
                        fact_strings.append(f"{subj} {rel_phrase} {obj}")
                    else:
                        fact_strings.append(f"{subj} {rel} {obj}")
                else:
                    fact_strings.append(str(fact))
            else:
                fact_strings.append(str(fact))

        # Remove duplicates while preserving order
        seen = set()
        unique_facts = []
        for f in fact_strings:
            if f not in seen:
                seen.add(f)
                unique_facts.append(f)

        # Format the list naturally
        if len(unique_facts) == 1:
            return unique_facts[0]
        elif len(unique_facts) == 2:
            return f"{unique_facts[0]} and {unique_facts[1]}"
        else:
            # Oxford comma
            return ", ".join(unique_facts[:-1]) + f", and {unique_facts[-1]}"

    def _relation_to_phrase(self, relation: str) -> str:
        """Convert a relation token to a natural language phrase."""
        # Map relations to more natural phrases
        relation_map = {
            "is_a": "is a",
            "instance_of": "is an example of",
            "has_property": "has the property",
            "has": "has",
            "can": "can",
            "causes": "causes",
            "part_of": "is part of",
            "definition": "means",
            "named": "is named",
            "located_in": "is located in",
            "produced_by": "is produced by",
            "synonym_of": "is the same as",
            "opposite_of": "is the opposite of",
            "related_to": "is related to",
            "does": "does",
        }
        return relation_map.get(relation, relation)

    def _select_template(self, templates: List[str]) -> str:
        """Select a random template from a list."""
        return random.choice(templates) if templates else "{}"

    def generate(
        self,
        reasoning=None,
        plan=None,
        facts=None,
        personality=None
    ) -> str:
        self.responses_generated += 1

        facts = facts or []
        personality_suffix = personality() if callable(personality) else (personality or "")

        # Format facts into a natural language string
        facts_str = self._format_facts(facts)

        # Determine the action from reasoning
        action = "RESPOND"  # default
        if reasoning and hasattr(reasoning, 'action'):
            action = reasoning.action

        # Choose template set based on action
        if action == "LOOKUP":
            templates = self.lookup_templates
        elif action == "STORE_FACT":
            templates = self.store_templates
        elif action == "GREET":
            templates = self.greet_templates
        elif action == "EMPATHIZE":
            templates = self.empathize_templates
        elif action == "RESPOND":
            templates = self.respond_templates
        else:
            # For any other action, use respond templates as fallback
            templates = self.respond_templates

        # If we have facts, use the selected template set
        if facts_str:
            template = self._select_template(templates)
            response = template.format(facts=facts_str)
        else:
            # No facts: use unknown or fallback templates
            if action in ["LOOKUP", "RESPOND"]:
                response = self._select_template(self.unknown_templates)
            else:
                response = self._select_template(self.fallback_templates)

        # Append personality suffix if available
        if personality_suffix:
            # Ensure proper spacing
            if not response.endswith((' ', '\n')):
                response += " "
            response += personality_suffix

        return response

    # Static helper for memory dump (unchanged)
    @staticmethod
    def generate_memory_dump(memory):
        return (
            f"Memory contains "
            f"{len(memory.facts)} topics.\n"
        )