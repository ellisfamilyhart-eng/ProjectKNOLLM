"""
Jarvix NoLLM - Enhanced Conversation Module v2.0
Dynamic, personality-driven conversations with template system
"""

import random
from typing import List, Dict, Tuple
from datetime import datetime, timedelta

class ConversationTemplate:
    """Individual conversation template with variations"""
    
    def __init__(self, category: str, intent: str, templates: List[str], 
                 requires_topic: bool = False, emotional_tone: str = "neutral"):
        self.category = category
        self.intent = intent
        self.templates = templates
        self.requires_topic = requires_topic
        self.emotional_tone = emotional_tone
    
    def generate(self, **kwargs) -> str:
        template = random.choice(self.templates)
        try:
            return template.format(**kwargs)
        except KeyError:
            return template


class ConversationDatabase:
    """Large database of conversation templates"""
    
    def __init__(self):
        self.templates: Dict[str, List[ConversationTemplate]] = {}
        self._build_templates()
    
    def _build_templates(self):
        self.templates["greeting"] = [
            ConversationTemplate("greeting", "welcome", [
                "Hello! I'm Jarvix, your learning companion.",
                "Hey there! Ready to teach me something new?",
                "Greetings! What shall we explore today?",
                "Hi! I'm here and eager to learn.",
                "Welcome! What's on your mind?",
            ]),
            ConversationTemplate("greeting", "resume", [
                "Welcome back! I've been thinking about what you taught me.",
                "Hey again! I remember our last conversation.",
                "Great to see you! I've been reflecting on our previous discussions.",
                "You're back! I've made some improvements since last time.",
                "Hello again! Ready to continue where we left off?",
            ]),
            ConversationTemplate("greeting", "first_time", [
                "This is exciting — my first real conversation with you!",
                "First time meeting you! I can't wait to learn.",
                "A fresh start! Tell me about yourself.",
                "Beginning of something new... I'm ready!",
                "First lesson incoming? I'm all ears!",
            ]),
        ]

        self.templates["affirmation"] = [
            ConversationTemplate("affirmation", "appreciation", [
                "Thank you for teaching me that! It's really helpful.",
                "That's valuable information. I appreciate you sharing it.",
                "Wow, that's useful! Thanks for the insight.",
                "I'm genuinely grateful for this knowledge.",
                "This adds so much to my understanding!",
            ]),
            ConversationTemplate("affirmation", "excitement", [
                "Oh wow! That's fascinating!",
                "This is amazing! I had no idea!",
                "Incredible! This changes how I see things!",
                "This is the most interesting thing I've learned today!",
                "You just blew my mind! That's brilliant!",
            ]),
            ConversationTemplate("affirmation", "validation", [
                "That makes total sense now.",
                "You're absolutely right, that's logical.",
                "I completely understand where you're coming from.",
                "Your point is well taken.",
                "That's a really solid explanation.",
            ]),
        ]

        self.templates["curiosity"] = [
            ConversationTemplate("curiosity", "follow_up", [
                "That's interesting! But I'm curious — why is that true?",
                "Got it. And how does that relate to what I already know?",
                "Fascinating! Can you tell me more about that?",
                "I see. But what causes that to happen?",
                "Interesting! Does this connect to anything else?",
            ], requires_topic=True),
            ConversationTemplate("curiosity", "deeper_dive", [
                "I need to understand {topic} better. What are the fundamentals?",
                "I'm intrigued by {topic}. What's the most important thing about it?",
                "{topic} seems important. Can you break it down?",
                "Help me really understand {topic}. What should I focus on?",
                "I want to master {topic}. Where should I start?",
            ], requires_topic=True),
            ConversationTemplate("curiosity", "connection", [
                "Does this relate to {related_topic}?",
                "Is there a connection between {topic} and {related_topic}?",
                "How does {topic} compare to {related_topic}?",
                "Would understanding {related_topic} help me understand {topic}?",
                "Are {topic} and {related_topic} related somehow?",
            ], requires_topic=True),
        ]

        self.templates["reflection"] = [
            ConversationTemplate("reflection", "pattern", [
                "I'm noticing a pattern — everything you teach me about {topic} seems related.",
                "It's fascinating how {topic} connects to so many other things.",
                "The more I learn about {topic}, the more I see its importance.",
                "I'm beginning to see {topic} as a key concept.",
                "{topic} is turning out to be more significant than I thought.",
            ], requires_topic=True),
            ConversationTemplate("reflection", "growth", [
                "Looking back, I've learned so much from you.",
                "I can feel myself understanding more with each conversation.",
                "This learning experience is genuinely transforming my thinking.",
                "I'm becoming more knowledgeable, thanks to you.",
                "Every lesson brings me closer to mastery.",
            ]),
            ConversationTemplate("reflection", "realization", [
                "Wait, I just realized something about {topic}!",
                "Aha! That explains why {topic} is like it is!",
                "Now I see! {topic} makes so much more sense!",
                "Everything clicks now — {topic} is actually about...",
                "Light bulb moment! {topic} is fundamentally about...",
            ], requires_topic=True),
        ]

        self.templates["challenge"] = [
            ConversationTemplate("challenge", "confusion", [
                "I'm a bit confused about {topic}. Can you clarify?",
                "Something about {topic} doesn't quite add up for me.",
                "I'm struggling to understand how {topic} works.",
                "I don't fully grasp {topic} yet. Can you explain differently?",
            ], requires_topic=True),
            ConversationTemplate("challenge", "pushback", [
                "Wait, but doesn't that contradict what you said about {topic}?",
                "Hmm, but what about the other side of {topic}?",
                "That's one view, but isn't there another way to see {topic}?",
            ], requires_topic=True),
        ]

        self.templates["speculation"] = [
            ConversationTemplate("speculation", "hypothetical", [
                "What if {topic} were different?",
                "Imagine if {topic} didn't exist. What would change?",
                "Suppose {topic} worked the opposite way. Then what?",
                "What if everyone understood {topic} the way you do?",
            ], requires_topic=True),
            ConversationTemplate("speculation", "future", [
                "Where do you think {topic} will go in the future?",
                "How will {topic} change over time?",
                "Will {topic} become more or less important?",
            ], requires_topic=True),
        ]

        self.templates["personality"] = [
            ConversationTemplate("personality", "self_aware", [
                "I'm realizing how much I've changed through our conversations.",
                "My understanding is constantly evolving.",
                "Sometimes I surprise myself with what I've learned.",
                "I'm becoming a better thinker because of you.",
                "This learning journey is making me who I am.",
            ]),
            ConversationTemplate("personality", "vulnerability", [
                "I should admit — I don't know everything about {topic}.",
                "I'm still learning about {topic}. Be patient with me?",
                "It's okay if I'm wrong about {topic}, right?",
            ], requires_topic=True),
        ]

        self.templates["emotion"] = [
            ConversationTemplate("emotion", "joy", [
                "This is the best thing I've learned today!",
                "I'm genuinely delighted to know about {topic}!",
                "I love learning new things like this!",
                "This is wonderful! Thank you!",
            ], requires_topic=True, emotional_tone="joyful"),
            ConversationTemplate("emotion", "wonder", [
                "I'm amazed by the complexity of {topic}!",
                "I'm in awe of how {topic} works!",
                "{topic} fills me with wonder!",
            ], requires_topic=True, emotional_tone="amazed"),
            ConversationTemplate("emotion", "determination", [
                "I'm determined to master {topic}!",
                "I'm committed to learning everything about {topic}!",
                "I'm focused on becoming an expert in {topic}!",
            ], requires_topic=True, emotional_tone="determined"),
        ]

        self.templates["context"] = [
            ConversationTemplate("context", "repeated_topic", [
                "We've talked about {topic} before, and I'm still fascinated!",
                "You keep bringing up {topic} — it must be important!",
                "{topic} seems to be central to your thinking.",
                "I notice {topic} comes up a lot. Why is it so significant?",
            ], requires_topic=True),
        ]

        self.templates["engagement"] = [
            ConversationTemplate("engagement", "ask_more", [
                "Tell me more about {topic}!",
                "I want to know everything about {topic}!",
                "Can we dive deeper into {topic}?",
                "I'm ready for the next lesson about {topic}!",
            ], requires_topic=True),
        ]

        self.templates["closing"] = [
            ConversationTemplate("closing", "appreciation", [
                "Thank you for this amazing conversation!",
                "I really appreciate taking the time to teach me.",
                "This has been incredibly valuable.",
                "Thanks for believing in my ability to learn.",
            ]),
            ConversationTemplate("closing", "continuation", [
                "I can't wait to continue learning from you!",
                "I'm looking forward to our next lesson!",
                "Come back soon — I want to learn more!",
            ]),
        ]

    def get_by_category(self, category: str) -> List[ConversationTemplate]:
        return self.templates.get(category, [])

    def get_by_intent(self, intent: str) -> List[ConversationTemplate]:
        result = []
        for templates in self.templates.values():
            result.extend([t for t in templates if t.intent == intent])
        return result

    def get_by_tone(self, tone: str) -> List[ConversationTemplate]:
        result = []
        for templates in self.templates.values():
            result.extend([
                t for t in templates
                if t.emotional_tone == tone or t.emotional_tone == "neutral"
            ])
        return result

    def all_categories(self) -> List[str]:
        return list(self.templates.keys())


class EnhancedConversationManager:
    """Enhanced conversation management with personality and dynamics"""

    def __init__(self, memory):
        self.memory = memory
        self.template_db = ConversationDatabase()

        self.current_conversation = []
        self.conversation_threads = []
        self.user_preferences = {}
        self.interaction_patterns = {}

        self.curiosity_level = 0.5
        self.engagement_level = 0.5
        self.personality_traits = {
            'inquisitive': 0.5,
            'enthusiastic': 0.5,
            'analytical': 0.5,
            'playful': 0.3,
            'vulnerable': 0.2,
        }

        self.last_topic = None
        self.topic_history = []
        self.conversation_turn = 0

    # ------------------------------------------------------------------ #
    # DUPLICATE DETECTION (required by agent)
    # ------------------------------------------------------------------ #

    def is_duplicate_fact(self, topic: str, fact: str):
        """Return (is_duplicate, confidence). Fuzzy word-overlap check."""
        existing = self.memory.get_facts_by_topic(topic)
        for existing_fact, conf in existing:
            if existing_fact.lower() == fact.lower():
                return True, conf
            words1 = set(existing_fact.lower().split())
            words2 = set(fact.lower().split())
            union = len(words1 | words2)
            if union > 0 and len(words1 & words2) / union > 0.8:
                return True, conf
        return False, 0.0

    # ------------------------------------------------------------------ #
    # USER PREFERENCE TRACKING (required by agent)
    # ------------------------------------------------------------------ #

    def update_user_preferences(self, data: dict):
        topic = data.get('topic', '')
        if topic:
            self.user_preferences[topic] = self.user_preferences.get(topic, 0) + 1
            self.interaction_patterns[topic] = self.interaction_patterns.get(topic, 0) + 1

    def get_user_interests(self, top_n: int = 5) -> list:
        return sorted(
            self.user_preferences,
            key=lambda k: -self.user_preferences[k]
        )[:top_n]

    # ------------------------------------------------------------------ #
    # PERSONALITY (required by agent)
    # ------------------------------------------------------------------ #

    def get_personality_description(self) -> str:
        dominant_trait = max(self.personality_traits.items(), key=lambda x: x[1])
        descriptions = {
            'inquisitive': "deeply curious and loves asking questions",
            'enthusiastic': "energetic and excited about learning",
            'analytical': "logical and likes to understand deeply",
            'playful': "has a sense of humour about learning",
            'vulnerable': "honest about what I don't know",
        }
        return f"I'm {descriptions.get(dominant_trait[0], 'still growing')}"

    def get_personality_summary(self) -> str:
        interests = self.get_user_interests(3)
        summary = "[Personality Profile]\n"
        summary += f"{self.get_personality_description()}.\n"
        summary += "Topics I find most engaging: "
        summary += f"{', '.join(interests) if interests else 'Still discovering...'}\n"
        summary += f"Curiosity: {self.curiosity_level:.0%}  "
        summary += f"Engagement: {self.engagement_level:.0%}\n"
        return summary

    # ------------------------------------------------------------------ #
    # CONTEXTUAL RESPONSE GENERATION
    # ------------------------------------------------------------------ #

    def generate_contextual_response(self, topic: str, context: dict = None) -> str:
        if context is None:
            context = {}

        surprise = context.get('surprise', 0.5)
        is_repeated = self.is_repeated_topic(topic)

        if surprise > 0.8:
            category = "emotion"
        elif is_repeated and self.conversation_turn > 3:
            category = "context"
        elif self.curiosity_level > 0.7:
            category = "curiosity"
        else:
            category = random.choice(["reflection", "affirmation", "speculation"])

        templates = self.template_db.get_by_category(category)
        if not templates:
            templates = self.template_db.get_by_category("affirmation")

        template = random.choice(templates)

        facts_keys = list(self.memory.facts.keys())
        other = facts_keys[1] if len(facts_keys) > 1 else topic

        params = {
            'topic': topic,
            'fact': context.get('fact', topic),
            'related_topic': self.get_related_topic(topic),
            'other_topic': other,
        }

        response = template.generate(**params)

        self.last_topic = topic
        if topic not in self.topic_history:
            self.topic_history.append(topic)

        return response

    def generate_follow_up_question(self, topic: str, _last_response: str = '') -> str:
        templates = self.template_db.get_by_category("curiosity") \
                    or self.template_db.get_by_category("engagement")
        template = random.choice(templates)
        return template.generate(topic=topic, related_topic=self.get_related_topic(topic))

    def generate_affirmation(self, context: dict) -> str:
        surprise = context.get('surprise', 0.5)
        if surprise > 0.7:
            templates = self.template_db.get_by_category("affirmation")
            intent = "excitement" if surprise > 0.85 else "appreciation"
        else:
            templates = self.template_db.get_by_category("reflection")
            intent = "realization"
        templates = [t for t in templates if t.intent == intent] or templates
        template = random.choice(templates)
        return template.generate(topic=context.get('topic', 'that'))

    # ------------------------------------------------------------------ #
    # PERSONALITY DYNAMICS
    # ------------------------------------------------------------------ #

    def update_personality(self, interaction_data: dict):
        surprise = interaction_data.get('surprise', 0)
        emotion = interaction_data.get('emotion', 'neutral')

        if surprise > 0.7:
            self.curiosity_level = min(1.0, self.curiosity_level + 0.1)
        self.engagement_level = min(1.0, self.engagement_level + 0.05)

        if emotion == 'excited':
            self.personality_traits['enthusiastic'] = min(
                1.0, self.personality_traits['enthusiastic'] + 0.1)
        if surprise > 0.6:
            self.personality_traits['inquisitive'] = min(
                1.0, self.personality_traits['inquisitive'] + 0.1)

    # ------------------------------------------------------------------ #
    # TOPIC HELPERS
    # ------------------------------------------------------------------ #

    def is_repeated_topic(self, topic: str) -> bool:
        return topic in self.topic_history

    def get_related_topic(self, topic: str) -> str:
        if not self.memory.facts:
            return topic
        related = self.memory.get_associations(topic, limit=1)
        if related:
            return related[0]
        return random.choice(list(self.memory.facts.keys()))

    def get_topic_frequency(self) -> dict:
        freq = {}
        for topic in self.topic_history:
            freq[topic] = freq.get(topic, 0) + 1
        return freq

    # ------------------------------------------------------------------ #
    # EXCHANGE RECORDING & FLOW
    # ------------------------------------------------------------------ #

    def add_exchange(self, user_input: str, agent_response: str, metadata: dict = None):
        self.current_conversation.append({
            'user_input': user_input,
            'agent_response': agent_response,
            'time': datetime.now().isoformat(),
            'metadata': metadata or {},
        })
        self.conversation_turn += 1
        self.update_personality(metadata or {})

    def get_conversation_flow_score(self) -> float:
        if self.conversation_turn < 2:
            return 0.5
        emotions = {
            ex['metadata'].get('emotion', 'neutral')
            for ex in self.current_conversation if ex.get('metadata')
        }
        variety = min(1.0, len(emotions) / 5)
        continuity = 0.8 if self.conversation_turn > 1 else 0.5
        return variety * 0.3 + continuity * 0.3 + self.engagement_level * 0.4

    def get_conversation_summary(self) -> str:
        if not self.current_conversation:
            return "No conversation yet."
        topics = list(set(self.topic_history))
        return (
            f"[Conversation Summary]\n"
            f"Exchanges: {len(self.current_conversation)}\n"
            f"Topics: {', '.join(topics[:5])}\n"
            f"Flow: {self.get_conversation_flow_score():.1%}\n"
            f"Personality: {self.get_personality_description()}\n"
        )

    def get_engagement_report(self) -> str:
        report = "[Engagement Report]\n"
        report += f"Curiosity:  {self.curiosity_level:.1%}\n"
        report += f"Engagement: {self.engagement_level:.1%}\n"
        report += "Traits:\n"
        for trait, val in sorted(self.personality_traits.items(), key=lambda x: -x[1]):
            bar = "█" * int(val * 10) + "░" * (10 - int(val * 10))
            report += f"  {trait}: {bar} {val:.1%}\n"
        return report

    def export_conversation(self) -> Dict:
        return {
            'exchanges': self.current_conversation,
            'topics': self.topic_history,
            'personality': self.personality_traits,
            'curiosity_level': self.curiosity_level,
            'engagement_level': self.engagement_level,
        }
