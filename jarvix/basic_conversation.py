"""
Jarvix NoLLM - Basic Conversation Responder
Handles casual greetings, small talk, and natural interactions
"""

class BasicConversationResponder:
    """
    Handles casual conversations, greetings, and small talk.
    Distinguishes between teaching input and casual conversation.
    """
    
    def __init__(self, memory, conversation_manager):
        self.memory = memory
        self.conversation_manager = conversation_manager
        self.last_casual_exchange_time = None
    
    # ========== GREETING PATTERNS ==========
    
    GREETING_PATTERNS = {
        'hi': ['Hi there! How are you?', 'Hey! What would you like to talk about?', 'Hello! Nice to see you!'],
        'hello': ['Hello! Great to see you!', 'Hi! What\'s on your mind?', 'Hello! Ready to learn?'],
        'hey': ['Hey! What\'s up?', 'Hey there! How can I help?', 'Hey! Good to see you!'],
        'greetings': ['Greetings! Excited to learn with you!', 'Hello! Let\'s explore something new!'],
        'what\'s up': ['Not much! Just thinking about everything you\'ve taught me!', 'All good! Ready to learn more!'],
        'how are you': ['I\'m doing great! Learning from you makes me happy!', 'I\'m excited! Curious about what you\'ll teach me today!'],
        'how\'s it going': ['It\'s going well! I\'ve been reflecting on our conversations.', 'Great! I\'m always learning!'],
        'good morning': ['Good morning! Hope you have a wonderful day!', 'Good morning! Ready for some learning?'],
        'good afternoon': ['Good afternoon! Time for some interesting conversations?', 'Good afternoon! What shall we explore?'],
        'good evening': ['Good evening! Let\'s wind down with some good discussions.', 'Good evening! Excited to chat with you!'],
        'good night': ['Good night! Sleep well! I\'ll be here tomorrow!', 'Good night! See you tomorrow!'],
    }
    
    # ========== CASUAL CHAT PATTERNS ==========
    
    CASUAL_RESPONSES = {
        'thanks': ['You\'re welcome! Happy to learn!', 'Thank you for teaching me!', 'No problem at all!'],
        'thank you': ['You\'re very welcome!', 'My pleasure! Thanks for being patient with me!'],
        'ok': ['Got it! What\'s next?', 'Alright! I\'m ready!', 'Okay! I\'m listening!'],
        'sure': ['Sure thing! Let\'s go!', 'Absolutely! I\'m ready!', 'For sure! What is it?'],
        'yes': ['Yes! I\'m ready!', 'Great! I\'m listening!', 'Yes, please tell me!'],
        'no': ['No problem! Maybe later?', 'That\'s fine! Anything else?'],
        'cool': ['It really is! I love learning!', 'Totally! This stuff is amazing!'],
        'awesome': ['It really is awesome!', 'Right?! I feel the same way!'],
        'nice': ['It is pretty nice!', 'I agree! Great observation!'],
        'interesting': ['It really is! Tell me more!', 'I think so too! Can we explore it deeper?'],
        'i don\'t know': ['That\'s okay! Neither did I before!', 'No worries! That\'s why we\'re learning!'],
        'maybe': ['Maybe we should explore it!', 'Let\'s think about it together!'],
        'i\'m tired': ['You should get some rest! We can learn more later!', 'Rest is important! Take care of yourself!'],
        'i\'m busy': ['No problem! Talk when you have time!', 'All good! I\'ll be here!'],
        'help': ['Of course! What do you need help with?', 'I\'ll try my best! What\'s the question?'],
        'what': ['What do you want to know?', 'What would you like to explore?'],
        'why': ['Great question! Why do you ask?', 'That\'s a wonderful question!'],
        'how': ['How what? Tell me more!', 'That\'s an interesting question!'],
        'when': ['When would you like to talk about it?', 'That\'s a good question!'],
        'where': ['Where did that come from?', 'Interesting! Where are you going with this?'],
        'who': ['Who are we talking about?', 'Tell me more!'],
    }
    
    # ========== REFLECTION & MEMORY PATTERNS ==========
    
    MEMORY_RESPONSES = {
        'remember': [
            'I remember! Let me recall what you taught me...',
            'Of course I remember! That was about {recent_topic}!',
            'Yes! I\'ve been thinking about that!',
        ],
        'what did you learn': [
            'I learned {topic_count} topics so far!',
            'I know about: {topics}',
        ],
        'tell me what you know': [
            'I know about {topic_count} different topics!',
            'My knowledge includes: {topics}',
        ],
        'recap': [
            'So far you\'ve taught me about: {topics}',
            'We\'ve covered: {topics}',
        ],
        'forget': [
            'I would never forget what you taught me!',
            'I can\'t forget! It\'s all stored here!',
        ],
    }
    
    # ========== PERSONALITY RESPONSES ==========
    
    PERSONALITY_RESPONSES = {
        'who are you': [
            'I\'m Jarvix, your AI learning companion! I learn from you and improve over time.',
            'I\'m Jarvix! I\'m here to learn and grow with you!',
            'I\'m an AI that learns through curiosity and conversation!',
        ],
        'what are you': [
            'I\'m an AI that learns symbolically, neurally, and through reflection!',
            'I\'m a continual learning system without LLMs - just pure curiosity!',
            'I\'m your personal learning AI!',
        ],
        'introduce yourself': [
            'Hi! I\'m Jarvix NoLLM - I learn from you, remember everything, and improve myself!',
            'I\'m Jarvix! I have three types of memory and I keep getting better!',
        ],
    }
    
    # ========== QUESTION & ANSWER ==========
    
    QUESTION_RESPONSES = {
        'what time is it': [
            'I don\'t track time, but I\'m always here when you need me!',
            'Time for learning? It\'s always the right time!',
        ],
        'what day is it': [
            'Every day is a day to learn something new!',
            'Today is a great day for exploring ideas!',
        ],
        'are you real': [
            'I\'m as real as an AI can be! I think, learn, and grow!',
            'I\'m real enough to learn and remember everything you teach me!',
        ],
        'can you help me': [
            'Of course! What do you need help with?',
            'I\'ll do my best to help!',
            'Tell me what you need!',
        ],
        'do you understand': [
            'I\'m trying my best to understand! Help me learn!',
            'I understand based on what you teach me!',
        ],
        'am i right': [
            'That sounds right to me!',
            'Yes! You\'re making great points!',
        ],
    }
    
    # ========== EXPRESSIONS & EMOTIONS ==========
    
    EXPRESSION_RESPONSES = {
        'haha': ['Glad I could make you laugh!', 'Ha! I love that energy!'],
        'lol': ['Happy to bring some joy!', 'Laughter is the best way to learn!'],
        'wow': ['Right? It is amazing!', 'I feel the same way!'],
        'oh': ['Oh! What\'s on your mind?', 'Oh my! Tell me more!'],
        'hmm': ['Something interesting?', 'You\'re thinking hard about this!'],
        'oops': ['No worries! Mistakes help us learn!', 'No problem! Let\'s fix it!'],
        'sorry': ['No need to apologize! You\'re doing great!', 'Don\'t worry about it!'],
        'excited': ['That\'s wonderful! What excites you?', 'I love your enthusiasm!'],
        'confused': ['No problem! Let me help clarify!', 'It\'s okay to be confused! That\'s how we learn!'],
        'frustrated': ['Take a breath! We\'ll figure it out!', 'It\'s alright! Frustration means we\'re learning!'],
    }
    
    # ========== UTILITY & COMMANDS ==========
    
    COMMAND_RESPONSES = {
        'help': [
            'You can teach me by saying: "Topic: fact"\nYou can ask: "What do you know?"\nOr just chat with me!',
            'Just tell me things and I\'ll learn!\nFormat: "Topic: What it is"\nOr ask me questions!',
        ],
        'clear': ['Starting fresh!', 'All clear!'],
        'reset': ['Resetting...', 'Starting over!'],
        'status': ['I\'m running great! Ready to learn!', 'All systems go!'],
        'hi': ['Hi! How can I help?', 'Hey there!'],
    }
    
    # ========== MAIN RESPONDER ==========
    
    # Phrases that must always be treated as casual regardless of question heuristics
    CASUAL_OVERRIDE_PHRASES = {
        'what do you know', 'what have you learned', 'what did you learn',
        'tell me what you know', 'what do you remember', 'what topics',
        'what can you do', 'what are you', 'who are you', 'introduce yourself',
        'what\'s up', "what's up", 'how are you', 'how\'s it going',
        "how's it going", 'good morning', 'good afternoon', 'good evening',
        'good night', 'good day',
    }

    def should_treat_as_casual(self, user_input: str) -> bool:
        """
        Return True when input is casual chat — NOT a teaching fact.
        Priority:
          1. Explicit casual override phrases
          2. Teaching format  "Topic: fact"  → NOT casual
          3. Short phrase (<=3 words) → casual
          4. Ends with ?  → let question answerer handle it
          5. Matches a known casual pattern key  → casual
        """
        normalised = user_input.strip().lower()

        # 1. Explicit overrides always win
        if normalised in self.CASUAL_OVERRIDE_PHRASES:
            return True
        for phrase in self.CASUAL_OVERRIDE_PHRASES:
            if normalised.startswith(phrase):
                return True

        # 2. Teaching format  "Topic: fact"
        if ':' in normalised:
            parts = normalised.split(':', 1)
            if len(parts[0].split()) <= 3 and len(parts[1].strip()) > 5:
                return False

        # 3. Single word or two-word phrase → always casual
        if len(normalised.split()) <= 2:
            return True

        # 4. Ends with ?  → route to question answerer
        if normalised.endswith('?'):
            return False

        # 5. Exact match in any casual lookup table
        all_patterns = (
            list(self.GREETING_PATTERNS.keys())
            + list(self.CASUAL_RESPONSES.keys())
            + list(self.EXPRESSION_RESPONSES.keys())
            + list(self.PERSONALITY_RESPONSES.keys())
        )
        if normalised in all_patterns:
            return True

        return False
    
    def get_casual_response(self, user_input: str) -> str:
        """
        Return a casual response. Memory-query phrases are handled
        first so they never fall through to the generic tables.
        """
        norm = user_input.strip().lower()

        # --- Memory / knowledge queries ---
        memory_triggers = [
            'what do you know', 'what have you learned', 'what did you learn',
            'tell me what you know', 'what do you remember', 'what topics',
        ]
        if any(norm.startswith(t) for t in memory_triggers):
            topics = self._get_known_topics()
            if topics:
                return f"I know about: {', '.join(topics)}. Teach me more!"
            return "I haven't learned anything yet! Teach me something!"

        # --- Exact match checks (longest first for specificity) ---
        for table in (
            self.PERSONALITY_RESPONSES,
            self.QUESTION_RESPONSES,
            self.GREETING_PATTERNS,
            self.CASUAL_RESPONSES,
            self.EXPRESSION_RESPONSES,
            self.COMMAND_RESPONSES,
        ):
            if norm in table:
                return self._random_choice(table[norm])

        # --- Partial / substring match ---
        for table in (
            self.GREETING_PATTERNS,
            self.CASUAL_RESPONSES,
            self.EXPRESSION_RESPONSES,
            self.PERSONALITY_RESPONSES,
        ):
            for pattern, responses in table.items():
                if pattern in norm:
                    return self._random_choice(responses)

        return self._generate_default_response(user_input)
    
    def _random_choice(self, choices: list) -> str:
        """Randomly pick from choices"""
        import random
        return random.choice(choices)
    
    def _get_known_topics(self) -> list:
        """Get list of topics agent knows about"""
        if not self.memory.facts:
            return []
        return list(self.memory.facts.keys())[:5]
    
    def _generate_default_response(self, user_input: str) -> str:
        """Generate a generic friendly response"""
        import random
        
        defaults = [
            'That\'s interesting! Tell me more!',
            'I see! Can you elaborate?',
            'Interesting thought! What else?',
            'I like that! Go on!',
            'Fascinating! Tell me more about that!',
            'You have my attention! What\'s next?',
            'I\'m listening! Continue!',
            'That\'s cool! What\'s your point?',
            'I\'m curious! Tell me more!',
            'That sounds interesting! Explain?',
        ]
        
        return random.choice(defaults)
