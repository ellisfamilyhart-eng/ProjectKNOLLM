"""
Jarvix NoLLM - Episodic Memory Module
Stores every conversation exchange with full context
"""

from datetime import datetime
from typing import List, Dict

class EpisodicMemory:
    """
    Episodic Memory: Records every conversation episode with full context.
    Used for replay and reflection learning.
    """
    
    def __init__(self, max_episodes: int = 1000):
        """
        Initialize episodic memory.
        
        Args:
            max_episodes: Maximum number of episodes to keep
        """
        self.episodes = []  # List of full conversations
        self.max_episodes = max_episodes
        self.episode_index = 0
    
    def record_episode(self, 
                      user_input: str,
                      agent_response: str,
                      metadata: dict = None) -> dict:
        """
        Record a single conversation episode.
        
        Args:
            user_input: What user said
            agent_response: How agent responded
            metadata: Additional context (topic, emotion, surprise, etc.)
        
        Returns:
            Episode dict with timestamp and ID
        """
        episode = {
            'id': self.episode_index,
            'timestamp': datetime.now().isoformat(),
            'user_input': user_input,
            'agent_response': agent_response,
            'metadata': metadata or {},
        }
        
        self.episodes.append(episode)
        self.episode_index += 1
        
        # Trim if over limit
        if len(self.episodes) > self.max_episodes:
            self.episodes.pop(0)
        
        return episode
    
    def get_episode(self, episode_id: int) -> dict:
        """Get a specific episode by ID"""
        for episode in self.episodes:
            if episode['id'] == episode_id:
                return episode
        return None
    
    def get_recent_episodes(self, limit: int = 10) -> List[dict]:
        """Get most recent episodes"""
        return self.episodes[-limit:]
    
    def get_episodes_by_topic(self, topic: str) -> List[dict]:
        """Get all episodes related to a topic"""
        matching = []
        for episode in self.episodes:
            if topic.lower() in episode['user_input'].lower() or \
               topic.lower() in episode['agent_response'].lower():
                matching.append(episode)
        return matching
    
    def get_episodes_by_emotion(self, emotion: str) -> List[dict]:
        """Get episodes from a specific emotional state"""
        return [ep for ep in self.episodes 
                if ep['metadata'].get('emotion') == emotion]
    
    def get_high_surprise_episodes(self, threshold: float = 0.7) -> List[dict]:
        """Get episodes with high surprise (important learning moments)"""
        return [ep for ep in self.episodes 
                if ep['metadata'].get('surprise', 0) > threshold]
    
    def get_statistics(self) -> dict:
        """Get episodic memory statistics"""
        if not self.episodes:
            return {
                'total_episodes': 0,
                'avg_response_length': 0,
                'unique_topics': 0,
            }
        
        # Extract topics from metadata
        topics = set()
        for ep in self.episodes:
            if 'topic' in ep['metadata']:
                topics.add(ep['metadata']['topic'])
        
        avg_response = sum(len(ep['agent_response']) for ep in self.episodes) / len(self.episodes)
        
        return {
            'total_episodes': len(self.episodes),
            'avg_response_length': int(avg_response),
            'unique_topics': len(topics),
            'oldest_episode': self.episodes[0]['timestamp'] if self.episodes else None,
            'newest_episode': self.episodes[-1]['timestamp'] if self.episodes else None,
        }
    
    def export(self) -> List[dict]:
        """Export episodic memory"""
        return self.episodes
    
    def import_episodes(self, episodes: List[dict]):
        """Import episodic memory"""
        self.episodes = episodes
        self.episode_index = len(episodes)
