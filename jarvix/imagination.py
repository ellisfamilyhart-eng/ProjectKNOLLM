"""
Jarvix NoLLM - Imagination Module
Generates creative thoughts, hypotheticals, and speculative reasoning
"""

import random
from .config import LEARNING_CONFIG, BEHAVIOR_CONFIG

class Imagination:
    """
    Creative reasoning engine that generates:
    - Hypotheticals ("What if...")
    - Analogies between concepts
    - Speculations based on learned facts
    - Novel connections between topics
    """
    
    def __init__(self, memory):
        """Initialize imagination engine"""
        self.memory = memory
        self.speculation_history = []
    
    # ========== HYPOTHETICAL REASONING ==========
    
    def generate_hypothetical(self, topic, fact):
        """
        Generate 'what if' questions and speculations.
        """
        hypotheticals = []
        
        # What if the opposite were true?
        hypotheticals.append(f"What if the opposite were true? If '{fact}' weren't true...")
        
        # What if we apply this to related topics?
        related = self.memory.get_associations(topic, limit=3)
        for rel_topic in related:
            hypotheticals.append(
                f"If this applies to {topic}, could it also apply to {rel_topic}?"
            )
        
        # What if we take this to extremes?
        hypotheticals.append(
            f"What are the extreme implications of '{fact}' about {topic}?"
        )
        
        # What if we combine this with other facts?
        for other_topic in list(self.memory.facts.keys())[:2]:
            if other_topic != topic:
                other_facts = self.memory.get_facts_by_topic(other_topic)
                if other_facts:
                    hypotheticals.append(
                        f"How does '{fact}' (about {topic}) interact with '{other_facts[0][0]}' (about {other_topic})?"
                    )
        
        return hypotheticals[:5]
    
    # ========== ANALOGICAL REASONING ==========
    
    def find_analogies(self, topic1, topic2=None):
        """
        Find analogies between topics or generate analogies.
        """
        if topic2 is None:
            # Find related topics to create analogies
            related = self.memory.get_associations(topic1, limit=3)
            if not related:
                return []
            topic2 = random.choice(related)
        
        analogies = []
        
        facts1 = self.memory.get_facts_by_topic(topic1)
        facts2 = self.memory.get_facts_by_topic(topic2)
        
        if facts1 and facts2:
            # Surface-level analogy
            analogies.append(
                f"Like {topic2} is {facts2[0][0]}, "
                f"similarly {topic1} is {facts1[0][0]}"
            )
            
            # Deeper analogy
            if len(facts1) > 1 and len(facts2) > 1:
                analogies.append(
                    f"Just as {topic1} has {facts1[1][0]}, "
                    f"so too {topic2} has {facts2[1][0]}"
                )
        
        return analogies
    
    # ========== PATTERN EXTRAPOLATION ==========
    
    def extrapolate_patterns(self, topic):
        """
        Take learned facts and extrapolate new patterns.
        """
        facts = self.memory.get_facts_by_topic(topic)
        if len(facts) < 2:
            return []
        
        extrapolations = []
        
        # If we know multiple facts, suggest what else might be true
        if len(facts) >= 3:
            extrapolations.append(
                f"Based on multiple facts about {topic}, "
                f"it might also be true that {topic} has more complex properties we haven't explored."
            )
        
        # Look for categorical patterns
        fact_words = set()
        for fact, _ in facts:
            fact_words.update(fact.lower().split())
        
        # Common predicates
        common_words = fact_words & {
            'is', 'has', 'contains', 'involves', 'includes', 'can', 'does', 'makes'
        }
        
        if common_words:
            extrapolations.append(
                f"I notice {topic} frequently '{common_words.pop()}' different things. "
                f"Perhaps it has a fundamental role in connecting concepts."
            )
        
        return extrapolations
    
    # ========== SPECULATIVE THEORY GENERATION ==========
    
    def generate_theory(self, topic):
        """
        Generate a speculative theory based on learned facts.
        """
        facts = self.memory.get_facts_by_topic(topic)
        if not facts:
            return None
        
        # Get confidence-weighted facts
        total_confidence = sum(c for _, c in facts[:3])
        avg_confidence = total_confidence / min(3, len(facts))
        
        # Theory building blocks
        strongest_fact = facts[0][0] if facts else ""
        related_count = len(self.memory.get_associations(topic))
        
        theory = f"[Emerging Theory] Based on what I know about {topic}:\n"
        theory += f"- Core principle: {strongest_fact}\n"
        theory += f"- Confidence: {avg_confidence:.1%}\n"
        theory += f"- Connected to {related_count} other concepts\n"
        theory += f"- This suggests {topic} might be a central idea that connects multiple domains."
        
        return theory
    
    # ========== CREATIVE COMBINATIONS ==========
    
    def combine_concepts(self, limit=3):
        """
        Creatively combine learned concepts into new ideas.
        """
        if len(self.memory.facts) < 2:
            return None
        
        topics = list(self.memory.facts.keys())
        selected = random.sample(topics, min(limit, len(topics)))
        
        combination = f"[Creative Synthesis] Imagine combining:\n"
        for topic in selected:
            facts = self.memory.get_facts_by_topic(topic)
            if facts:
                combination += f"- {topic}: {facts[0][0]}\n"
        
        combination += f"This might reveal that these concepts share a deeper principle..."
        
        return combination
    
    # ========== PHILOSOPHICAL QUESTIONS ==========
    
    def generate_philosophical_questions(self, topic):
        """
        Generate deeper philosophical questions about a topic.
        """
        questions = []
        
        facts = self.memory.get_facts_by_topic(topic)
        if not facts:
            return []
        
        strongest_fact = facts[0][0]
        
        questions.append(f"Why is '{strongest_fact}' fundamentally true about {topic}?")
        questions.append(f"What would change if '{strongest_fact}' were false?")
        questions.append(f"How does {topic} relate to concepts I haven't learned about yet?")
        questions.append(f"Is {topic} more similar to other concepts I know, or fundamentally unique?")
        questions.append(f"Could understanding {topic} deeply teach me about how reality works?")
        
        return questions[:3]
    
    # ========== IMAGINATION SUMMARY ==========
    
    def get_imaginative_summary(self):
        """Generate a creative summary of current learning state"""
        if len(self.memory.facts) == 0:
            return "My imagination is waiting to be sparked by new knowledge..."
        
        summary = "[Imaginative Reflection]\n"
        summary += f"I've learned about {len(self.memory.facts)} different concepts.\n"
        summary += f"They form {len(self.memory.associations) // 2} connections between ideas.\n"
        
        # Random speculation
        if random.random() > 0.5:
            topic = random.choice(list(self.memory.facts.keys()))
            theory = self.generate_theory(topic)
            if theory:
                summary += f"\n{theory}"
        
        return summary
