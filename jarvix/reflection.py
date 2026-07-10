"""
Jarvix NoLLM - Reflection Module
Reviews and replays past episodes to improve continuously
Self-directed learning through reflection
"""

from typing import List, Dict, Tuple
import random

class ReflectionEngine:
    """
    Reflection Engine: Reviews past episodes to improve learning.
    Replays conversations, identifies patterns, reinforces knowledge.
    """
    
    def __init__(self, memory, neural_learner, episodic_memory, vocabulary):
        """
        Initialize reflection engine.
        
        Args:
            memory: Semantic memory (facts)
            neural_learner: Neural network learner
            episodic_memory: Episodic memory (conversations)
            vocabulary: Vocabulary encoder
        """
        self.memory = memory
        self.neural_learner = neural_learner
        self.episodic_memory = episodic_memory
        self.vocabulary = vocabulary
        
        self.reflection_count = 0
        self.reflection_history = []
    
    # ========== EPISODE REPLAY & LEARNING ==========
    
    def replay_episode(self, episode: dict) -> Tuple[float, str]:
        """
        Replay an episode by re-encoding and re-training the neural network.
        Returns (learning_improvement, reflection_note).
        """
        user_input = episode['user_input']
        metadata = episode.get('metadata', {})
        
        # Extract topic and confidence
        topic = metadata.get('topic', 'unknown')
        surprise = metadata.get('surprise', 0.5)
        
        # Re-encode
        vector = self.vocabulary.encode(user_input)
        
        # Target: high surprise = should learn well
        target = min(1.0, surprise * 1.5)
        
        # Retrain neural network
        loss_before = None
        if topic in self.neural_learner.topic_networks:
            losses = self.neural_learner.topic_networks[topic].get_loss_history(1)
            if losses:
                loss_before = losses[0]
        
        new_loss = self.neural_learner.learn_global_pattern(user_input, target)
        
        # Calculate improvement
        improvement = 0.0
        note = f"Replayed episode on topic '{topic}'"
        
        if loss_before is not None:
            improvement = loss_before - new_loss
            if improvement > 0:
                note += f" (improved by {improvement:.4f})"
            else:
                note += f" (loss increased by {-improvement:.4f})"
        
        return improvement, note
    
    def reflect_on_topic(self, topic: str) -> Dict[str, any]:
        """
        Deep reflection on a specific topic.
        Replays all episodes about that topic and identifies patterns.
        """
        episodes = self.episodic_memory.get_episodes_by_topic(topic)
        
        if not episodes:
            return {
                'topic': topic,
                'episodes_found': 0,
                'reflection': f"No episodes found for '{topic}'",
            }
        
        # Extract insights
        total_surprise = sum(ep['metadata'].get('surprise', 0.5) for ep in episodes)
        avg_surprise = total_surprise / len(episodes)
        
        # Find most surprising episode
        most_surprising = max(episodes, key=lambda e: e['metadata'].get('surprise', 0))
        
        # Retrain on all episodes
        total_improvement = 0.0
        for episode in episodes:
            improvement, _ = self.replay_episode(episode)
            total_improvement += improvement
        
        # Get current knowledge about topic
        facts = self.memory.get_facts_by_topic(topic)
        
        reflection = {
            'topic': topic,
            'episodes_found': len(episodes),
            'average_surprise': avg_surprise,
            'facts_learned': len(facts),
            'total_retraining_improvement': total_improvement,
            'insight': f"I've learned {len(facts)} facts about {topic} through {len(episodes)} interactions.",
        }
        
        if avg_surprise > 0.7:
            reflection['insight'] += f" This topic surprised me significantly on average ({avg_surprise:.2f})."
        
        return reflection
    
    # ========== PATTERN DISCOVERY ==========
    
    def discover_patterns(self) -> List[Dict]:
        """
        Analyze episodic memory to discover new patterns.
        Looks for recurring topics, emotions, and sequences.
        """
        patterns = []
        
        if len(self.episodic_memory.episodes) < 5:
            return patterns
        
        # Find most discussed topics
        topic_counts = {}
        for ep in self.episodic_memory.episodes:
            topic = ep['metadata'].get('topic', 'unknown')
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        top_topics = sorted(topic_counts.items(), key=lambda x: -x[1])[:5]
        
        patterns.append({
            'pattern_type': 'topic_distribution',
            'insights': f"Most discussed topics: {[t for t, _ in top_topics]}",
        })
        
        # Find emotion patterns
        emotion_counts = {}
        for ep in self.episodic_memory.episodes:
            emotion = ep['metadata'].get('emotion', 'neutral')
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        patterns.append({
            'pattern_type': 'emotional_distribution',
            'insights': f"Emotional states: {emotion_counts}",
        })
        
        # Find high-learning moments (high surprise)
        high_surprise = self.episodic_memory.get_high_surprise_episodes(threshold=0.7)
        if high_surprise:
            topics_in_high_surprise = [ep['metadata'].get('topic') for ep in high_surprise]
            patterns.append({
                'pattern_type': 'high_learning_moments',
                'count': len(high_surprise),
                'topics': list(set(topics_in_high_surprise)),
            })
        
        return patterns
    
    # ========== CONTINUOUS IMPROVEMENT ==========
    
    def reflect_idle(self) -> str:
        """
        Called when agent is idle. Reviews memories and improves.
        """
        if len(self.episodic_memory.episodes) == 0:
            return "Nothing to reflect on yet."
        
        self.reflection_count += 1
        
        # Pick a random episode to replay
        episode = random.choice(self.episodic_memory.episodes)
        improvement, note = self.replay_episode(episode)
        
        # Record reflection
        self.reflection_history.append({
            'reflection_id': self.reflection_count,
            'timestamp': episode['timestamp'],
            'episode_id': episode['id'],
            'improvement': improvement,
            'note': note,
        })
        
        # Generate reflection summary
        reflection = f"[Reflection #{self.reflection_count}] "
        reflection += f"I replayed episode #{episode['id']}: '{episode['user_input'][:50]}...' "
        reflection += f"({note})"
        
        return reflection
    
    def continuous_learning_session(self, duration_episodes: int = 10) -> List[str]:
        """
        Run a continuous learning session by replaying episodes.
        """
        reflections = []
        
        for i in range(min(duration_episodes, len(self.episodic_memory.episodes))):
            reflection = self.reflect_idle()
            reflections.append(reflection)
        
        return reflections
    
    # ========== REINFORCEMENT ==========
    
    def reinforce_important_facts(self):
        """
        Strengthen important facts by re-training on them multiple times.
        """
        if not self.memory.facts:
            return []
        
        reinforcements = []
        
        # Get high-confidence facts
        important_facts = []
        for topic, facts_dict in self.memory.facts.items():
            for fact, confidence in facts_dict.items():
                if confidence > 0.8:
                    important_facts.append((topic, fact, confidence))
        
        # Retrain on these facts
        for topic, fact, confidence in important_facts[:5]:
            vector = self.vocabulary.encode(fact)
            loss = self.neural_learner.learn_topic_pattern(topic, fact, confidence)
            
            reinforcements.append({
                'topic': topic,
                'fact': fact,
                'loss': loss,
            })
        
        return reinforcements
    
    # ========== ANALYSIS ==========
    
    def get_learning_trajectory(self, limit: int = 20) -> List[Dict]:
        """
        Get the trajectory of learning improvements over time.
        """
        recent_reflections = self.reflection_history[-limit:]
        
        return [
            {
                'reflection_id': r['reflection_id'],
                'improvement': r['improvement'],
                'note': r['note'],
            }
            for r in recent_reflections
        ]
    
    def get_reflection_statistics(self) -> Dict:
        """Get reflection engine statistics"""
        if not self.reflection_history:
            return {
                'total_reflections': 0,
                'avg_improvement': 0.0,
            }
        
        total_improvement = sum(r['improvement'] for r in self.reflection_history)
        avg_improvement = total_improvement / len(self.reflection_history)
        
        return {
            'total_reflections': len(self.reflection_history),
            'avg_improvement': avg_improvement,
            'total_improvement': total_improvement,
        }
    
    def export(self) -> Dict:
        """Export reflection data"""
        return {
            'reflection_count': self.reflection_count,
            'reflection_history': self.reflection_history,
        }
    
    def import_reflections(self, data: Dict):
        """Import reflection data"""
        self.reflection_count = data.get('reflection_count', 0)
        self.reflection_history = data.get('reflection_history', [])
