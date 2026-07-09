"""
Jarvix NoLLM - Parser Module
Natural language processing and input parsing
"""

class InputParser:
    """
    Simple NLP for extracting topic and fact from user input.
    Supports multiple formats.
    """
    
    @staticmethod
    def parse(user_input):
        """
        Parse user input to extract topic and fact.
        Supports formats:
        - "Topic: Fact" (preferred)
        - "Natural language input" (extracts heuristically)
        """
        if not user_input or not user_input.strip():
            return None, None
        
        # Format 1: "Topic: Fact"
        if ":" in user_input:
            parts = user_input.split(":", 1)
            topic = parts[0].strip()
            fact = parts[1].strip()
            
            if topic and fact:
                return topic, fact
        
        # Format 2: Natural language (heuristic)
        words = user_input.split()
        
        if len(words) >= 3:
            # First 2 words = topic, rest = fact
            topic = " ".join(words[:2])
            fact = " ".join(words[2:])
            return topic, fact
        elif len(words) == 2:
            # Assume "Topic Fact"
            return words[0], words[1]
        else:
            # Single word - use as both
            return user_input, user_input
        
        return None, None
    
    @staticmethod
    def is_command(user_input):
        """Check if input is a command (starts with /)"""
        return user_input.strip().startswith('/')
    
    @staticmethod
    def parse_command(user_input):
        """Extract command and arguments"""
        parts = user_input.strip().split()
        if not parts:
            return None, []
        
        cmd = parts[0].lstrip('/').lower()
        args = parts[1:]
        
        return cmd, args
    
    @staticmethod
    def validate_fact(topic, fact):
        """Validate that topic and fact are meaningful"""
        if not topic or not fact:
            return False
        
        min_length = 2
        if len(topic) < min_length or len(fact) < min_length:
            return False
        
        return True
    
    @staticmethod
    def extract_keywords(text):
        """Extract key concepts from text"""
        # Simple keyword extraction
        stop_words = {
            'is', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
            'to', 'for', 'of', 'by', 'with', 'from', 'be', 'are', 'was',
            'were', 'been', 'have', 'has', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'can'
        }
        
        words = text.lower().split()
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return list(set(keywords))
