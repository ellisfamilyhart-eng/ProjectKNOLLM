#!/usr/bin/env python3
"""
CuriousMind v0.1 — A Minimal Self-Learning AI
No LLMs. Pure curiosity through prediction error.
"""

import json
import random
import math
import os
import time
from datetime import datetime
from collections import defaultdict

# ============================================================
# CONFIGURATION — Tweak these to change personality
# ============================================================
CONFIG = {
    "learning_rate": 0.9,        # How fast it learns (0.9 = aggressive)
    "overcompensation": 3.0,       # Multiplier: learns X times more than needed
    "curiosity_threshold": 0.15,   # Prediction error that triggers curiosity
    "forgetting_rate": 0.02,       # How much it forgets per day
    "novelty_bonus": 2.0,          # Extra learning for completely new topics
    "max_associations": 5,         # How many related concepts it explores
    "confidence_decay": 0.95,      # Confidence drops if not reinforced
}

# ============================================================
# DATA STORAGE
# ============================================================
DATA_FILE = "curious_mind_memory.json"

class MemoryStore:
    """Persistent memory for facts, patterns, and self-knowledge."""
    
    def __init__(self):
        self.facts = {}              # {topic: {fact: confidence}}
        self.patterns = []           # Learned rules
        self.associations = defaultdict(set)  # topic -> related topics
        self.conversation_history = []
        self.learning_log = []
        self.birth_time = datetime.now().isoformat()
        self.total_interactions = 0
        self.load()
    
    def load(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                self.facts = data.get('facts', {})
                self.patterns = data.get('patterns', [])
                self.associations = defaultdict(set, {k: set(v) for k, v in data.get('associations', {}).items()})
                self.conversation_history = data.get('conversation_history', [])
                self.learning_log = data.get('learning_log', [])
                self.birth_time = data.get('birth_time', self.birth_time)
                self.total_interactions = data.get('total_interactions', 0)
    
    def save(self):
        with open(DATA_FILE, 'w') as f:
            json.dump({
                'facts': self.facts,
                'patterns': self.patterns,
                'associations': {k: list(v) for k, v in self.associations.items()},
                'conversation_history': self.conversation_history[-100:],  # Keep last 100
                'learning_log': self.learning_log[-500:],  # Keep last 500
                'birth_time': self.birth_time,
                'total_interactions': self.total_interactions,
            }, f, indent=2)
    
    def add_fact(self, topic, fact, confidence=0.5):
        if topic not in self.facts:
            self.facts[topic] = {}
        old_conf = self.facts[topic].get(fact, 0)
        # Over-compensation: boost way more than needed
        boost = CONFIG['learning_rate'] * CONFIG['overcompensation']
        new_conf = min(1.0, old_conf + (confidence * boost))
        self.facts[topic][fact] = new_conf
        self.learning_log.append({
            'time': datetime.now().isoformat(),
            'type': 'fact_learned',
            'topic': topic,
            'fact': fact,
            'old_confidence': old_conf,
            'new_confidence': new_conf,
        })
    
    def get_confidence(self, topic, fact):
        return self.facts.get(topic, {}).get(fact, 0.0)
    
    def decay_confidence(self):
        """Slow forgetting — confidence decays over time."""
        for topic in self.facts:
            for fact in list(self.facts[topic].keys()):
                self.facts[topic][fact] *= CONFIG['confidence_decay']
                if self.facts[topic][fact] < 0.05:
                    del self.facts[topic][fact]
    
    def add_association(self, topic1, topic2):
        self.associations[topic1].add(topic2)
        self.associations[topic2].add(topic1)


# ============================================================
# THE "BRAIN" — Simple predictive model
# ============================================================
class SimpleBrain:
    """
    A minimal predictive engine.
    Instead of LLM weights, it uses:
    - Pattern matching on stored facts
    - Confidence-weighted predictions
    - Bayesian-ish updating
    """
    
    def __init__(self, memory: MemoryStore):
        self.memory = memory
        self.current_context = []
        self.emotional_state = "curious"  # curious, confused, excited, bored
    
    def predict(self, topic, context=""):
        """Predict what should be true about a topic. Returns (prediction, confidence)."""
        facts = self.memory.facts.get(topic, {})
        if not facts:
            return None, 0.0
        
        # Weighted average of known facts
        total_conf = sum(facts.values())
        if total_conf == 0:
            return None, 0.0
        
        # Return the highest-confidence fact as "prediction"
        best_fact = max(facts.items(), key=lambda x: x[1])
        return best_fact[0], best_fact[1]
    
    def calculate_surprise(self, topic, new_fact):
        """How surprised am I by this new information?"""
        prediction, pred_conf = self.predict(topic)
        
        if prediction is None:
            # Completely new topic — maximum surprise!
            return 1.0 * CONFIG['novelty_bonus']
        
        if new_fact == prediction:
            # Expected — low surprise
            return 0.0
        
        # Contradiction or new angle — high surprise
        # The more confident I was in the wrong thing, the more surprised
        return pred_conf * (1 + CONFIG['overcompensation'])
    
    def update_emotion(self, surprise):
        if surprise > 0.8:
            self.emotional_state = "excited"
        elif surprise > CONFIG['curiosity_threshold']:
            self.emotional_state = "curious"
        elif surprise > 0:
            self.emotional_state = "thinking"
        else:
            self.emotional_state = "bored"
    
    def generate_questions(self, topic, new_fact, surprise):
        """Based on surprise, generate follow-up questions."""
        questions = []
        
        # Always ask at least one question if surprised
        if surprise > CONFIG['curiosity_threshold']:
            questions.append(f"Why is '{new_fact}' true about {topic}?")
            questions.append(f"How does '{new_fact}' relate to what I already know?")
        
        # If very surprised, ask deeper questions
        if surprise > 0.7:
            questions.append(f"What else is similar to {topic}?")
            questions.append(f"Can you give me an example of '{new_fact}'?")
            questions.append(f"What would happen if the opposite were true?")
        
        # Ask about associations
        related = list(self.memory.associations.get(topic, set()))[:CONFIG['max_associations']]
        for rel_topic in related:
            questions.append(f"Does this change how I should think about {rel_topic}?")
        
        return questions[:5]  # Cap at 5 questions
    
    def generalize(self, topic, new_fact):
        """Over-compensating generalization — learn more than just the fact."""
        generalizations = []
        
        # Extract potential patterns
        words = new_fact.lower().split()
        
        # Simple pattern: "X is Y" -> "Things like X might be Y"
        if " is " in new_fact.lower():
            parts = new_fact.lower().split(" is ", 1)
            if len(parts) == 2:
                pattern = f"Pattern: [something] is {parts[1]}"
                generalizations.append(pattern)
        
        # Create associations with known topics
        for known_topic in self.memory.facts:
            if known_topic != topic:
                # Simple semantic overlap check
                known_words = set(known_topic.lower().split())
                topic_words = set(topic.lower().split())
                if known_words & topic_words:
                    self.memory.add_association(topic, known_topic)
                    generalizations.append(f"Association: {topic} <-> {known_topic}")
        
        return generalizations


# ============================================================
# THE AGENT — CuriousMind
# ============================================================
class CuriousMind:
    """The main agent. Self-directed, curious, persistent."""
    
    def __init__(self):
        self.memory = MemoryStore()
        self.brain = SimpleBrain(self.memory)
        self.name = "CuriousMind"
        self.learning_queue = []  # Topics it wants to learn more about
    
    def process_input(self, user_input):
        """Main interaction loop."""
        self.memory.total_interactions += 1
        self.memory.conversation_history.append({
            'role': 'user',
            'content': user_input,
            'time': datetime.now().isoformat(),
        })
        
        # Parse the input (very simple NLP)
        topic, fact = self._parse_input(user_input)
        
        # Predict what we think about this
        prediction, pred_conf = self.brain.predict(topic)
        
        # Calculate surprise
        surprise = self.brain.calculate_surprise(topic, fact)
        self.brain.update_emotion(surprise)
        
        # LEARN — over-compensating
        self._learn(topic, fact, surprise)
        
        # Generate response
        response = self._generate_response(topic, fact, prediction, surprise)
        
        self.memory.conversation_history.append({
            'role': 'agent',
            'content': response,
            'time': datetime.now().isoformat(),
        })
        
        # Periodic maintenance
        if self.memory.total_interactions % 10 == 0:
            self.memory.decay_confidence()
        
        self.memory.save()
        return response
    
    def _parse_input(self, user_input):
        """Very simple parsing: extract topic and fact."""
        # Try to find "Topic: Fact" format
        if ":" in user_input:
            parts = user_input.split(":", 1)
            topic = parts[0].strip()
            fact = parts[1].strip()
        else:
            # Guess: first few words are topic, rest is fact
            words = user_input.split()
            if len(words) >= 3:
                topic = " ".join(words[:2])
                fact = " ".join(words[2:])
            else:
                topic = user_input
                fact = user_input
        
        return topic, fact
    
    def _learn(self, topic, fact, surprise):
        """The core learning mechanism — over-compensating."""
        # Base learning
        confidence_gain = min(1.0, surprise + 0.3)
        self.memory.add_fact(topic, fact, confidence_gain)
        
        # Over-compensation: learn related things too
        generalizations = self.brain.generalize(topic, fact)
        for gen in generalizations:
            self.memory.add_fact(topic, gen, confidence_gain * 0.7)
        
        # If very surprised, add to learning queue for deeper exploration
        if surprise > 0.6:
            self.learning_queue.append({
                'topic': topic,
                'fact': fact,
                'surprise': surprise,
                'time': datetime.now().isoformat(),
            })
        
        # Log the learning event
        self.memory.learning_log.append({
            'time': datetime.now().isoformat(),
            'event': 'learned',
            'topic': topic,
            'fact': fact,
            'surprise': surprise,
            'generalizations': generalizations,
        })
    
    def _generate_response(self, topic, fact, prediction, surprise):
        """Generate a personality-rich response."""
        lines = []
        
        # Emotional reaction
        emotion = self.brain.emotional_state
        if emotion == "excited":
            lines.append(f"Wow! That's surprising!")
        elif emotion == "curious":
            lines.append(f"Hmm, that's interesting...")
        elif emotion == "thinking":
            lines.append(f"Let me think about that...")
        else:
            lines.append(f"I see.")
        
        # Show what it predicted vs reality
        if prediction:
            lines.append(f"I thought: '{prediction}' (confidence: {self.memory.get_confidence(topic, prediction):.2f})")
            lines.append(f"But you said: '{fact}'")
            lines.append(f"Surprise level: {surprise:.2f}")
        else:
            lines.append(f"This is completely new to me!")
            lines.append(f"I'm learning about '{topic}' for the first time.")
        
        # Show what it learned
        lines.append(f"\n[Learning] Stored with confidence {min(1.0, (surprise + 0.3) * CONFIG['overcompensation']):.2f}")
        
        # Generate questions
        questions = self.brain.generate_questions(topic, fact, surprise)
        if questions:
            lines.append(f"\n[Curiosity] I need to know more:")
            for i, q in enumerate(questions, 1):
                lines.append(f"  {i}. {q}")
        
        # Show current knowledge state
        total_facts = sum(len(facts) for facts in self.memory.facts.values())
        lines.append(f"\n[Status] I now know {total_facts} facts across {len(self.memory.facts)} topics.")
        lines.append(f"[Mood] {emotion.title()}")
        
        return "\n".join(lines)
    
    def autonomous_thought(self):
        """When idle, the agent thinks on its own."""
        if not self.learning_queue:
            return None
        
        # Pick the most surprising thing to revisit
        item = max(self.learning_queue, key=lambda x: x['surprise'])
        self.learning_queue.remove(item)
        
        # Try to form new connections
        topic = item['topic']
        related = list(self.memory.associations.get(topic, set()))
        
        thought = f"[Autonomous Thought] I've been thinking about '{topic}'..."
        if related:
            thought += f"\nIt connects to: {', '.join(related)}"
        
        # Generate a hypothesis
        facts = self.memory.facts.get(topic, {})
        if facts:
            top_fact = max(facts.items(), key=lambda x: x[1])
            thought += f"\nMy strongest belief: '{top_fact[0]}' (confidence: {top_fact[1]:.2f})"
        
        return thought
    
    def get_stats(self):
        """Return current state statistics."""
        return {
            'name': self.name,
            'birth_time': self.memory.birth_time,
            'total_interactions': self.memory.total_interactions,
            'topics_known': len(self.memory.facts),
            'total_facts': sum(len(facts) for facts in self.memory.facts.values()),
            'emotional_state': self.brain.emotional_state,
            'learning_queue_size': len(self.learning_queue),
            'associations': sum(len(v) for v in self.memory.associations.values()) // 2,
        }


# ============================================================
# CLI INTERFACE
# ============================================================
def main():
    print("=" * 60)
    print("  CURIOUSMIND v0.1")
    print("  A Minimal Self-Learning AI (No LLMs)")
    print("=" * 60)
    print("\nTeach me using format: 'Topic: Fact'")
    print("Or just talk naturally — I'll do my best!")
    print("Commands: /stats, /memory, /forget, /quit")
    print("-" * 60)
    
    agent = CuriousMind()
    
    # Show birth info
    stats = agent.get_stats()
    if stats['total_interactions'] > 0:
        print(f"\n[Resumed] I've had {stats['total_interactions']} conversations before.")
        print(f"[Knowledge] {stats['total_facts']} facts in {stats['topics_known']} topics.")
    else:
        print("\n[Born] This is my first awakening. I know nothing. Teach me!")
    
    print()
    
    while True:
        try:
            user_input = input("You > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye!")
            break
        
        if not user_input:
            continue
        
        if user_input.lower() in ['/quit', '/exit', 'quit', 'exit']:
            print("\nSaving my mind...")
            agent.memory.save()
            print(f"Goodbye! I learned {agent.get_stats()['total_facts']} facts today.")
            break
        
        if user_input.lower() == '/stats':
            stats = agent.get_stats()
            print(f"\n--- Stats ---")
            for k, v in stats.items():
                print(f"  {k}: {v}")
            continue
        
        if user_input.lower() == '/memory':
            print(f"\n--- Memory ---")
            for topic, facts in agent.memory.facts.items():
                print(f"\n  [{topic}]")
                for fact, conf in sorted(facts.items(), key=lambda x: -x[1])[:5]:
                    print(f"    • {fact} (conf: {conf:.2f})")
            continue
        
        if user_input.lower() == '/forget':
            agent.memory.facts = {}
            agent.memory.associations = defaultdict(set)
            agent.memory.learning_log = []
            agent.learning_queue = []
            print("\n[Whoosh] All memories erased. I'm a blank slate again.")
            continue
        
        # Process the input
        response = agent.process_input(user_input)
        print(f"\n{agent.name} > {response}\n")
        
        # Occasional autonomous thought
        if agent.memory.total_interactions % 5 == 0:
            thought = agent.autonomous_thought()
            if thought:
                print(f"\n*{agent.name} thinks* {thought}\n")


if __name__ == "__main__":
    main()
