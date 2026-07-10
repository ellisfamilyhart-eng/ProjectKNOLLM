"""
Jarvix NoLLM - Conversation Module
Manages conversation context, deduplication, and personality building
"""

from datetime import datetime, timedelta
from collections import defaultdict

class ConversationManager:
    """
    Manages ongoing conversations:
    - Tracks conversation context and threads
    - Prevents duplicate information learning
    - Builds personality through interaction patterns
    - Remembers conversation history with metadata
    """
    
    def __init__(self, memory):
        """Initialize conversation manager"""
        self.memory = memory
        self.current_conversation = []
        self.conversation_threads = []  # Past conversations
        self.user_preferences = {}  # User's teaching style
        self.interaction_patterns = defaultdict(int)  # How often topics discussed
        self.duplicate_cache = {}  # Cache to prevent re-learning
    
    # ========== CONVERSATION CONTEXT ==========
    
    def start_new_conversation(self):
        """Mark the beginning of a new conversation thread"""
        if self.current_conversation:
            # Save current conversation as thread
            self.conversation_threads.append({
                'exchanges': self.current_conversation,
                'started': self.current_conversation[0].get('time') if self.current_conversation else datetime.now().isoformat(),
                'ended': datetime.now().isoformat(),
            })
        
        self.current_conversation = []
    
    def add_exchange(self, user_input, agent_response, metadata=None):
        """
        Add a user-agent exchange to current conversation.
        """
        exchange = {
            'user_input': user_input,
            'agent_response': agent_response,
            'time': datetime.now().isoformat(),
            'metadata': metadata or {},
        }
        
        self.current_conversation.append(exchange)
        
        # Track topic interaction
        if 'topic' in metadata or {}:
            topic = metadata.get('topic', '')
            self.interaction_patterns[topic] += 1
    
    def get_conversation_context(self, depth=5):
        """
        Get recent conversation context for generating coherent responses.
        """
        if len(self.current_conversation) == 0:
            return []
        
        return self.current_conversation[-depth:]
    
    # ========== DUPLICATE DETECTION ==========
    
    def is_duplicate_fact(self, topic, fact):
        """
        Check if we've already learned this fact or something very similar.
        Prevents re-learning the same information.
        """
        existing_facts = self.memory.get_facts_by_topic(topic)
        
        # Exact match
        for existing_fact, confidence in existing_facts:
            if existing_fact.lower() == fact.lower():
                return True, confidence
            
            # Similarity check (fuzzy)
            if self._similarity(existing_fact, fact) > 0.8:
                return True, confidence
        
        return False, 0.0
    
    def _similarity(self, text1, text2):
        """
        Calculate text similarity (0-1).
        Simple approach: word overlap.
        """
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        overlap = len(words1 & words2)
        union = len(words1 | words2)
        
        return overlap / union if union > 0 else 0.0
    
    # ========== USER PERSONALITY MODELING ==========
    
    def update_user_preferences(self, interaction_data):
        """
        Learn user's teaching style and preferences.
        """
        # Track user's favorite topics
        if 'topic' in interaction_data:
            topic = interaction_data['topic']
            self.user_preferences[topic] = self.user_preferences.get(topic, 0) + 1
    
    def get_user_interests(self, top_n=5):
        """Get user's most frequently discussed topics"""
        sorted_prefs = sorted(
            self.user_preferences.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return [topic for topic, _ in sorted_prefs[:top_n]]
    
    def should_ask_follow_up(self, topic, fact, confidence):
        """
        Decide whether to ask follow-up questions based on conversation pattern.
        """
        # Ask more if we're uncertain
        if confidence < 0.5:
            return True
        
        # Ask less if we've already discussed this topic extensively
        times_discussed = self.interaction_patterns.get(topic, 0)
        if times_discussed > 5:
            return random.random() > 0.7  # Less frequent
        
        return True
    
    # ========== CONVERSATION ANALYTICS ==========
    
    def get_conversation_statistics(self):
        """Get statistics about conversations"""
        total_exchanges = len(self.current_conversation)
        total_threads = len(self.conversation_threads)
        
        all_exchanges = total_exchanges
        for thread in self.conversation_threads:
            all_exchanges += len(thread['exchanges'])
        
        return {
            'current_exchanges': total_exchanges,
            'total_past_conversations': total_threads,
            'total_exchanges_ever': all_exchanges,
            'unique_topics': len(self.interaction_patterns),
            'most_discussed': self.get_user_interests(1),
        }
    
    # ========== PERSONALITY DEVELOPMENT ==========
    
    def get_personality_summary(self):
        """
        Generate a summary of the agent's personality based on conversation patterns.
        """
        interests = self.get_user_interests(3)
        
        summary = "[Personality Profile]\n"
        summary += f"I find these topics most engaging: {', '.join(interests) if interests else 'Still discovering...'}\n"
        summary += f"Over {len(self.conversation_threads)} conversations, "
        summary += f"I've had {sum(len(t['exchanges']) for t in self.conversation_threads)} exchanges.\n"
        
        # Learning style
        if len(self.interaction_patterns) > 10:
            summary += "I enjoy broad, exploratory learning across many domains.\n"
        elif len(self.interaction_patterns) < 3:
            summary += "I prefer focused learning within specific domains.\n"
        else:
            summary += "I enjoy balanced exploration across multiple areas.\n"
        
        return summary
    
    # ========== RESPONSE CONSISTENCY ==========
    
    def should_expand_response(self, topic):
        """
        Decide if response should be expanded with examples or concise.
        Based on user interaction patterns.
        """
        times_discussed = self.interaction_patterns.get(topic, 0)
        
        # First time: give full response
        if times_discussed == 0:
            return True
        
        # Repeated: be more concise
        return times_discussed < 3
    
    def get_response_tone(self):
        """
        Determine appropriate response tone based on conversation flow.
        """
        recent = self.get_conversation_context(3)
        
        if not recent:
            return "curious"
        
        # If many rapid exchanges, be more concise and direct
        if len(recent) >= 3:
            time_diffs = []
            for i in range(1, len(recent)):
                try:
                    t1 = datetime.fromisoformat(recent[i-1]['time'])
                    t2 = datetime.fromisoformat(recent[i]['time'])
                    time_diffs.append((t2 - t1).total_seconds())
                except:
                    pass
            
            if time_diffs and sum(time_diffs) / len(time_diffs) < 5:
                return "concise"
        
        return "normal"
    
    # ========== CONVERSATION EXPORT ==========
    
    def export_conversation(self):
        """Export current conversation for analysis or saving"""
        return {
            'current': self.current_conversation,
            'threads': self.conversation_threads,
            'interaction_patterns': dict(self.interaction_patterns),
            'user_preferences': self.user_preferences,
        }
    
    def get_conversation_summary(self):
        """Get a textual summary of the conversation"""
        if not self.current_conversation:
            return "No conversation yet."
        
        summary = f"[Conversation Summary - {len(self.current_conversation)} exchanges]\n"
        
        for i, exchange in enumerate(self.current_conversation[-3:], 1):
            user_input = exchange['user_input'][:50]
            summary += f"{i}. You: {user_input}...\n"
        
        return summary
