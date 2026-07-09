"""
Jarvix NoLLM - Recursive Learner Module
Learns from web pages, extracts text, and processes recursively
"""

import re
from urllib.parse import urlparse, urljoin
from typing import List, Tuple

class RecursiveLearner:
    """
    Learns from external sources:
    - Scrapes web pages
    - Extracts key facts from text
    - Learns recursively from links
    - Processes and deduplicates information
    """
    
    def __init__(self, memory, brain, conversation_manager):
        """Initialize recursive learner"""
        self.memory = memory
        self.brain = brain
        self.conversation = conversation_manager
        self.visited_urls = set()
        self.learning_depth = 0
        self.max_depth = 2  # Prevent infinite recursion
        self.extracted_facts = []
    
    # ========== TEXT EXTRACTION ==========
    
    def extract_facts_from_text(self, text: str, source_topic: str = None) -> List[Tuple[str, str]]:
        """
        Extract key facts from raw text using simple heuristics.
        Returns list of (topic, fact) tuples.
        """
        facts = []
        
        # Clean text
        text = text.strip()
        
        # Split into sentences
        sentences = re.split(r'[.!?]\s+', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
            
            # Look for "X is Y" patterns
            if ' is ' in sentence.lower():
                parts = sentence.split(' is ', 1)
                if len(parts) == 2:
                    topic = parts[0].strip()
                    fact = f"is {parts[1].strip()}"
                    
                    # Filter out low-quality extractions
                    if len(topic) > 2 and len(fact) > 5:
                        facts.append((topic, fact))
            
            # Look for "X has Y" patterns
            elif ' has ' in sentence.lower():
                parts = sentence.split(' has ', 1)
                if len(parts) == 2:
                    topic = parts[0].strip()
                    fact = f"has {parts[1].strip()}"
                    
                    if len(topic) > 2 and len(fact) > 5:
                        facts.append((topic, fact))
            
            # Look for "X does Y" patterns
            elif ' does ' in sentence.lower():
                parts = sentence.split(' does ', 1)
                if len(parts) == 2:
                    topic = parts[0].strip()
                    fact = f"does {parts[1].strip()}"
                    
                    if len(topic) > 2 and len(fact) > 5:
                        facts.append((topic, fact))
        
        return facts
    
    # ========== SENTENCE EXTRACTION ==========
    
    def extract_sentences(self, text: str) -> List[str]:
        """Extract individual sentences from text"""
        sentences = re.split(r'[.!?]\s+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 10]
    
    def extract_paragraphs(self, text: str) -> List[str]:
        """Extract paragraphs from text"""
        paragraphs = re.split(r'\n\n+', text)
        return [p.strip() for p in paragraphs if len(p.strip()) > 20]
    
    # ========== WEB SCRAPING ==========
    
    def learn_from_url(self, url: str, depth: int = 0):
        """
        Learn from a URL by scraping and processing the content.
        Recursively follows links if depth allows.
        """
        if depth > self.max_depth or url in self.visited_urls:
            return []
        
        self.visited_urls.add(url)
        self.learning_depth = depth
        learned_facts = []
        
        try:
            # Try to fetch the URL
            text = self._fetch_url(url)
            if not text:
                return []
            
            # Extract facts from the page
            facts = self.extract_facts_from_text(text)
            
            # Learn the facts
            for topic, fact in facts:
                # Check for duplicates
                is_dup, _ = self.conversation.is_duplicate_fact(topic, fact)
                if not is_dup:
                    self.memory.add_fact(topic, fact, confidence=0.6)
                    learned_facts.append((topic, fact))
                    self.extracted_facts.append({
                        'source': url,
                        'topic': topic,
                        'fact': fact,
                    })
            
            # Recursive learning: extract links and learn from them
            if depth < self.max_depth:
                links = self._extract_links(text, url)
                for link in links[:3]:  # Limit to 3 links
                    recursive_facts = self.learn_from_url(link, depth + 1)
                    learned_facts.extend(recursive_facts)
        
        except Exception as e:
            print(f"Error learning from {url}: {e}")
        
        return learned_facts
    
    def _fetch_url(self, url: str) -> str:
        """
        Fetch content from URL.
        In production, use requests library. For now, return placeholder.
        """
        try:
            import requests
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response.text
        except ImportError:
            print("Note: requests library not installed. Skipping URL fetch.")
            print(f"To enable web scraping, install: pip install requests beautifulsoup4")
            return ""
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
        
        return ""
    
    def _extract_links(self, text: str, base_url: str) -> List[str]:
        """Extract links from text"""
        # Simple regex for URLs
        url_pattern = r'https?://[^\s\)\]]*'
        links = re.findall(url_pattern, text)
        
        # Normalize links
        normalized = []
        for link in links:
            try:
                parsed = urlparse(link)
                if parsed.scheme in ['http', 'https']:
                    normalized.append(link)
            except:
                pass
        
        return list(set(normalized))  # Remove duplicates
    
    # ========== TEXT ANALYSIS ==========
    
    def analyze_text(self, text: str) -> dict:
        """
        Analyze text for key information.
        """
        paragraphs = self.extract_paragraphs(text)
        sentences = self.extract_sentences(text)
        facts = self.extract_facts_from_text(text)
        
        # Extract keywords
        words = text.lower().split()
        keywords = [w for w in words if len(w) > 4 and w.isalpha()]
        keyword_freq = {}
        for kw in keywords:
            keyword_freq[kw] = keyword_freq.get(kw, 0) + 1
        
        top_keywords = sorted(
            keyword_freq.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            'paragraph_count': len(paragraphs),
            'sentence_count': len(sentences),
            'fact_count': len(facts),
            'top_keywords': [kw for kw, _ in top_keywords],
            'facts': facts,
        }
    
    # ========== LEARNING STATISTICS ==========
    
    def get_learning_statistics(self):
        """Get statistics about recursive learning"""
        return {
            'urls_visited': len(self.visited_urls),
            'facts_extracted': len(self.extracted_facts),
            'current_depth': self.learning_depth,
            'max_depth': self.max_depth,
            'visited_urls': list(self.visited_urls),
        }
    
    def get_extracted_facts_summary(self):
        """Get summary of extracted facts"""
        if not self.extracted_facts:
            return "No facts extracted yet."
        
        summary = f"[Extracted {len(self.extracted_facts)} facts from web]\n"
        
        # Group by topic
        topics = {}
        for fact_entry in self.extracted_facts:
            topic = fact_entry['topic']
            if topic not in topics:
                topics[topic] = []
            topics[topic].append(fact_entry['fact'])
        
        for topic, facts in list(topics.items())[:5]:
            summary += f"\n{topic}:\n"
            for fact in facts[:2]:
                summary += f"  • {fact}\n"
        
        return summary
    
    # ========== BULK LEARNING ==========
    
    def learn_from_urls(self, urls: List[str]):
        """
        Learn from multiple URLs.
        """
        all_facts = []
        
        for url in urls:
            facts = self.learn_from_url(url)
            all_facts.extend(facts)
        
        return all_facts
    
    def learn_from_text_file(self, file_path: str):
        """
        Learn from a local text file.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            facts = self.extract_facts_from_text(text)
            
            for topic, fact in facts:
                is_dup, _ = self.conversation.is_duplicate_fact(topic, fact)
                if not is_dup:
                    self.memory.add_fact(topic, fact, confidence=0.6)
            
            return facts
        
        except Exception as e:
            print(f"Error learning from file {file_path}: {e}")
            return []
    
    # ========== RESET ==========
    
    def reset_learning(self):
        """Reset learning state"""
        self.visited_urls.clear()
        self.learning_depth = 0
        self.extracted_facts.clear()
