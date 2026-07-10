"""
Jarvix NoLLM - Vocabulary Module
Bag-of-Words encoder for converting text to numeric vectors
"""

class Vocabulary:
    """
    Simple bag-of-words vocabulary for encoding text to vectors.
    Supports building vocabulary incrementally and encoding to fixed-size vectors.
    """
    
    def __init__(self):
        """Initialize empty vocabulary"""
        self.words = {}  # {word: index}
        self.word_count = 0
    
    def add_word(self, word: str) -> int:
        """
        Add a word to vocabulary if not already present.
        Returns the word's index.
        """
        word = word.lower().strip()
        
        if word not in self.words:
            self.words[word] = self.word_count
            self.word_count += 1
        
        return self.words[word]
    
    def encode(self, text: str, size: int = 64) -> list:
        """
        Encode text to fixed-size vector using bag-of-words.
        
        Args:
            text: Text to encode
            size: Vector size (default 64)
        
        Returns:
            Vector of floats representing word frequencies
        """
        vector = [0.0] * size
        
        if not text:
            return vector
        
        # Split and encode words
        words = text.lower().split()
        word_count = len(words)
        
        for word in words:
            # Add word to vocabulary if new
            if word not in self.words:
                self.add_word(word)
            
            # Map to vector index (modulo size)
            idx = self.words[word] % size
            vector[idx] += 1.0
        
        # Normalize by word count
        if word_count > 0:
            vector = [v / word_count for v in vector]
        
        return vector
    
    def decode(self, vector: list, top_n: int = 5) -> list:
        """
        Approximate decoding: find most active dimensions.
        Returns top N words by approximate activation.
        """
        # Find top indices
        indexed = [(i, v) for i, v in enumerate(vector)]
        top_indices = sorted(indexed, key=lambda x: -x[1])[:top_n]
        
        # Find words for these indices
        result = []
        index_to_word = {v: k for k, v in self.words.items()}
        
        for idx, activation in top_indices:
            if activation > 0:
                # Find word(s) that hash to this index
                for word, word_idx in self.words.items():
                    if word_idx % len(vector) == idx:
                        result.append((word, activation))
                        break
        
        return result
    
    def get_vocabulary_size(self) -> int:
        """Get total number of unique words learned"""
        return len(self.words)
    
    def export(self) -> dict:
        """Export vocabulary for saving"""
        return {
            'words': self.words,
            'word_count': self.word_count,
        }
    
    def import_vocab(self, data: dict):
        """Import vocabulary from saved data"""
        self.words = data.get('words', {})
        self.word_count = data.get('word_count', 0)
    
    def get_stats(self) -> dict:
        """Get vocabulary statistics"""
        return {
            'unique_words': len(self.words),
            'word_count': self.word_count,
        }
