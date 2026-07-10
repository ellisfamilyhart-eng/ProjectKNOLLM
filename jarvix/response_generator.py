"""
Jarvix NoLLM - Response Generator Module (Updated for Enhanced Conversation)
Generates personality-rich responses based on learning state and conversation context
"""

from .config import LEARNING_CONFIG

class ResponseGenerator:
    """
    Generates responses with personality based on:
    - Emotional state
    - Prediction vs reality
    - Surprise level
    - Generated questions
    - Conversation context (NEW)
    """
    
    EMOTION_MESSAGES = {
        'excited': "Wow! That's surprising!",
        'curious': "Hmm, that's interesting...",
        'thinking': "Let me think about that...",
        'bored': "I see.",
    }
    
    @staticmethod
    def generate_response(emotion, prediction, fact, surprise, questions, stats, 
                         conversation_manager=None):
        """
        Generate a complete response with all components.
        Enhanced with contextual conversation when available.
        """
        lines = []
        
        # Use enhanced conversation for opening if available
        if conversation_manager:
            try:
                context = {
                    'surprise': surprise,
                    'fact': fact,
                    'topic': stats.get('topic', 'that'),
                    'emotion': emotion,
                }
                opening = conversation_manager.generate_contextual_response(
                    stats.get('topic', 'that'),
                    context=context
                )
                lines.append(opening)
            except Exception as e:
                # Fallback if enhancement fails
                reaction = ResponseGenerator.EMOTION_MESSAGES.get(emotion, "Interesting.")
                lines.append(reaction)
        else:
            # Fallback to original emotion messages
            reaction = ResponseGenerator.EMOTION_MESSAGES.get(emotion, "Interesting.")
            lines.append(reaction)
        
        # Prediction vs reality
        if prediction:
            lines.append(f"\nI thought: '{prediction}'")
            lines.append(f"But you said: '{fact}'")
            lines.append(f"Surprise level: {surprise:.2f}")
        else:
            lines.append(f"\nThis is completely new to me!")
            lines.append(f"I'm learning about a new concept for the first time.")
        
        # Learning confirmation
        confidence_gain = min(1.0, (surprise + 0.3) * LEARNING_CONFIG['overcompensation'])
        lines.append(f"\n[Learning] Stored with confidence {confidence_gain:.2f}")
        
        # Questions
        if questions:
            lines.append(f"\n[Curiosity] I need to know more:")
            for i, q in enumerate(questions, 1):
                lines.append(f"  {i}. {q}")
        
        # Statistics
        lines.append(f"\n[Status] I now know {stats['total_facts']} facts "
                    f"across {stats['topics_known']} topics.")
        lines.append(f"[Mood] {emotion.title()}")
        
        # Enhanced conversation status
        if conversation_manager:
            try:
                lines.append(f"[Flow] Conversation: {conversation_manager.get_conversation_flow_score():.1%}")
                lines.append(f"[Engagement] {conversation_manager.engagement_level:.1%}")
            except:
                pass
        
        return "\n".join(lines)
    
    @staticmethod
    def generate_summary(agent):
        """Generate a session summary"""
        stats = agent.get_stats()
        
        lines = [
            "\n" + "=" * 60,
            "  SESSION SUMMARY",
            "=" * 60,
            f"\n📚 Topics learned: {stats['topics_known']}",
            f"💾 Total facts: {stats['total_facts']}",
            f"🎯 Interactions: {stats['total_interactions']}",
            f"🧠 Current mood: {stats['emotional_state']}",
            f"🔗 Associations: {stats['associations']}",
            f"📋 Learning queue: {stats['learning_queue_size']}",
        ]
        
        return "\n".join(lines)
    
    @staticmethod
    def generate_status_report(memory):
        """Generate detailed status report"""
        stats = memory.get_statistics()
        
        lines = [
            "\n" + "=" * 60,
            "  AGENT STATUS REPORT",
            "=" * 60,
            f"\nName: Jarvix NoLLM",
            f"Birth time: {stats['birth_time']}",
            f"Total interactions: {stats['total_interactions']}",
            f"Topics known: {stats['total_topics']}",
            f"Total facts: {stats['total_facts']}",
            f"Associations: {stats['associations_count']}",
            f"Last save: {stats['last_save']}",
        ]
        
        return "\n".join(lines)
    
    @staticmethod
    def generate_memory_dump(memory, limit=5):
        """Generate a view of current memory"""
        lines = [
            "\n" + "=" * 60,
            "  MEMORY SNAPSHOT",
            "=" * 60,
        ]
        
        if not memory.facts:
            lines.append("\n[Empty] No facts learned yet.")
            return "\n".join(lines)
        
        for topic, facts in list(memory.facts.items())[:10]:
            lines.append(f"\n[{topic}]")
            
            sorted_facts = sorted(facts.items(), key=lambda x: -x[1])[:limit]
            for fact, conf in sorted_facts:
                confidence_bar = "█" * int(conf * 10) + "░" * (10 - int(conf * 10))
                lines.append(f"  • {fact} [{confidence_bar}] {conf:.2f}")
        
        return "\n".join(lines)
    
    @staticmethod
    def generate_conversation_context(conversation_manager):
        """Generate conversation context display"""
        if not hasattr(conversation_manager, 'export_conversation'):
            return "[No conversation context]"
        
        export = conversation_manager.export_conversation()
        
        lines = [
            "\n" + "=" * 60,
            "  CONVERSATION CONTEXT",
            "=" * 60,
            f"\nExchanges: {len(export['exchanges'])}",
            f"Topics discussed: {', '.join(export['topics'][:5])}",
            f"Engagement: {conversation_manager.engagement_level:.1%}",
            f"Curiosity: {conversation_manager.curiosity_level:.1%}",
        ]
        
        if hasattr(conversation_manager, 'personality_traits'):
            lines.append(f"\n[Personality Traits]")
            for trait, value in sorted(conversation_manager.personality_traits.items(), 
                                      key=lambda x: -x[1])[:3]:
                lines.append(f"  {trait}: {value:.1%}")
        
        return "\n".join(lines)
