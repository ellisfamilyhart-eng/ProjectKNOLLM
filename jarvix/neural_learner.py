"""
Jarvix NoLLM - Neural Learning Module
Integrates a tiny neural network for pattern learning alongside symbolic facts
Hybrid approach: Facts + Neural Patterns
"""

import random
import math
from typing import List, Tuple

class TinyBrain:
    """
    Minimal neural network for learning patterns from numeric inputs.
    Single layer perceptron with sigmoid activation.
    """
    
    def __init__(self, input_size=64):
        """Initialize neural network"""
        self.input_size = input_size
        
        # Random weights
        self.weights = [random.uniform(-0.1, 0.1) for _ in range(input_size)]
        self.bias = 0.0
        self.lr = 0.1  # Learning rate
        
        # Training history
        self.loss_history = []
        self.training_samples = 0
    
    def sigmoid(self, x):
        """Sigmoid activation function"""
        try:
            return 1 / (1 + math.exp(-x))
        except OverflowError:
            return 1.0 if x > 0 else 0.0
    
    def sigmoid_derivative(self, sigmoid_output):
        """Derivative of sigmoid"""
        return sigmoid_output * (1 - sigmoid_output)
    
    def predict(self, x: List[float]) -> float:
        """
        Predict output for input vector.
        Returns probability between 0 and 1.
        """
        if len(x) != self.input_size:
            raise ValueError(f"Expected {self.input_size} inputs, got {len(x)}")
        
        z = self.bias
        for w, v in zip(self.weights, x):
            z += w * v
        
        return self.sigmoid(z)
    
    def train(self, x: List[float], target: float) -> float:
        """
        Train on single sample using backpropagation.
        Returns absolute error.
        """
        if len(x) != self.input_size:
            raise ValueError(f"Expected {self.input_size} inputs, got {len(x)}")
        
        target = max(0.0, min(1.0, target))  # Clamp target to [0, 1]
        
        # Forward pass
        pred = self.predict(x)
        
        # Backprop
        error = target - pred
        gradient = error * self.sigmoid_derivative(pred)
        
        # Update bias
        self.bias += self.lr * gradient
        
        # Update weights
        for i in range(self.input_size):
            self.weights[i] += self.lr * gradient * x[i]
        
        abs_error = abs(error)
        self.loss_history.append(abs_error)
        self.training_samples += 1
        
        return abs_error
    
    def batch_train(self, inputs: List[List[float]], targets: List[float], epochs=1) -> float:
        """
        Train on batch of samples for multiple epochs.
        Returns average loss.
        """
        total_loss = 0.0
        
        for _ in range(epochs):
            epoch_loss = 0.0
            for x, target in zip(inputs, targets):
                loss = self.train(x, target)
                epoch_loss += loss
            total_loss = epoch_loss / len(inputs)
        
        return total_loss
    
    def get_weights_summary(self) -> dict:
        """Get summary of network weights"""
        return {
            'bias': self.bias,
            'weights_mean': sum(self.weights) / len(self.weights),
            'weights_max': max(self.weights),
            'weights_min': min(self.weights),
            'training_samples': self.training_samples,
        }
    
    def get_loss_history(self, last_n=10):
        """Get recent loss history"""
        return self.loss_history[-last_n:]
    
    def reset(self):
        """Reset network to random state"""
        self.weights = [random.uniform(-0.1, 0.1) for _ in range(self.input_size)]
        self.bias = 0.0
        self.loss_history = []
        self.training_samples = 0


class NeuralLearner:
    """
    Bridges symbolic facts and neural patterns.
    Uses neural networks to learn patterns across topics and facts.
    """
    
    def __init__(self, memory, feature_size=64):
        """Initialize neural learner"""
        self.memory = memory
        self.feature_size = feature_size
        
        # Per-topic neural networks
        self.topic_networks = {}  # {topic: TinyBrain}
        
        # Global pattern network
        self.global_network = TinyBrain(input_size=feature_size)
        
        # Feature extraction history
        self.feature_cache = {}  # Cache for efficiency
    
    # ========== FEATURE EXTRACTION ==========
    
    def text_to_features(self, text: str, max_len=64) -> List[float]:
        """
        Convert text to feature vector for neural network.
        Uses character-level encoding + statistics.
        """
        # Normalize
        text = text.lower()[:max_len]
        
        # Character encoding (ASCII normalized)
        features = []
        for char in text:
            features.append((ord(char) - 32) / 96.0)  # Normalize to [0, 1]
        
        # Pad to max_len
        while len(features) < max_len:
            features.append(0.0)
        
        return features[:max_len]
    
    def confidence_to_target(self, confidence: float) -> float:
        """Convert confidence score to neural target"""
        return max(0.0, min(1.0, confidence))
    
    def features_to_confidence(self, prediction: float) -> float:
        """Convert neural prediction to confidence score"""
        return prediction
    
    # ========== TOPIC-SPECIFIC LEARNING ==========
    
    def learn_topic_pattern(self, topic: str, fact: str, confidence: float):
        """
        Learn a pattern for a specific topic using its neural network.
        """
        # Get or create topic network
        if topic not in self.topic_networks:
            self.topic_networks[topic] = TinyBrain(input_size=self.feature_size)
        
        network = self.topic_networks[topic]
        
        # Convert to features and target
        features = self.text_to_features(fact)
        target = self.confidence_to_target(confidence)
        
        # Train
        loss = network.train(features, target)
        
        return loss
    
    def predict_topic_pattern(self, topic: str, fact: str) -> Tuple[float, bool]:
        """
        Predict confidence for a fact using topic's neural network.
        Returns (prediction, has_network).
        """
        if topic not in self.topic_networks:
            return 0.5, False
        
        network = self.topic_networks[topic]
        features = self.text_to_features(fact)
        prediction = network.predict(features)
        
        return prediction, True
    
    # ========== GLOBAL PATTERN LEARNING ==========
    
    def learn_global_pattern(self, text: str, importance: float):
        """
        Learn a global pattern that applies across topics.
        """
        features = self.text_to_features(text)
        target = self.confidence_to_target(importance)
        
        loss = self.global_network.train(features, target)
        
        return loss
    
    def predict_global_pattern(self, text: str) -> float:
        """Predict importance of text using global network"""
        features = self.text_to_features(text)
        return self.global_network.predict(features)
    
    # ========== BATCH LEARNING ==========
    
    def batch_learn_topic(self, topic: str, facts: List[Tuple[str, float]], epochs=5):
        """
        Batch train a topic network on multiple fact-confidence pairs.
        """
        if topic not in self.topic_networks:
            self.topic_networks[topic] = TinyBrain(input_size=self.feature_size)
        
        network = self.topic_networks[topic]
        
        # Convert to features and targets
        inputs = [self.text_to_features(fact) for fact, _ in facts]
        targets = [self.confidence_to_target(conf) for _, conf in facts]
        
        # Train
        avg_loss = network.batch_train(inputs, targets, epochs=epochs)
        
        return avg_loss
    
    # ========== NEURAL STATISTICS ==========
    
    def get_topic_network_stats(self, topic: str) -> dict:
        """Get statistics for a topic's neural network"""
        if topic not in self.topic_networks:
            return {'exists': False}
        
        network = self.topic_networks[topic]
        
        return {
            'exists': True,
            'training_samples': network.training_samples,
            'weights': network.get_weights_summary(),
            'recent_losses': network.get_loss_history(5),
        }
    
    def get_global_network_stats(self) -> dict:
        """Get statistics for global network"""
        return {
            'training_samples': self.global_network.training_samples,
            'weights': self.global_network.get_weights_summary(),
            'recent_losses': self.global_network.get_loss_history(5),
        }
    
    def get_all_topics_neural_performance(self) -> dict:
        """Get performance across all topic networks"""
        performance = {}
        
        for topic, network in self.topic_networks.items():
            if network.loss_history:
                avg_loss = sum(network.loss_history) / len(network.loss_history)
                recent_loss = network.get_loss_history(1)[0]
            else:
                avg_loss = 0.0
                recent_loss = 0.0
            
            performance[topic] = {
                'samples': network.training_samples,
                'avg_loss': avg_loss,
                'recent_loss': recent_loss,
            }
        
        return performance
    
    # ========== NEURAL-SYMBOLIC INTEGRATION ==========
    
    def hybrid_predict_confidence(self, topic: str, fact: str) -> dict:
        """
        Combine symbolic (memory-based) and neural predictions.
        Returns both and a hybrid score.
        """
        # Symbolic prediction
        symbolic_conf = self.memory.get_confidence(topic, fact)
        
        # Neural prediction
        neural_conf, has_network = self.predict_topic_pattern(topic, fact)
        
        # Hybrid: weighted average
        if has_network and symbolic_conf > 0:
            hybrid_conf = 0.6 * symbolic_conf + 0.4 * neural_conf
        elif has_network:
            hybrid_conf = neural_conf
        else:
            hybrid_conf = symbolic_conf
        
        return {
            'symbolic': symbolic_conf,
            'neural': neural_conf,
            'hybrid': hybrid_conf,
            'has_neural_network': has_network,
        }
    
    def learn_symbolic_and_neural(self, topic: str, fact: str, confidence: float):
        """
        Learn both symbolically (facts) and neurally (patterns).
        """
        # Symbolic learning (done in memory)
        # self.memory.add_fact(topic, fact, confidence)
        
        # Neural learning
        self.learn_topic_pattern(topic, fact, confidence)
        self.learn_global_pattern(fact, confidence)
    
    # ========== ANALYSIS ==========
    
    def analyze_learning_convergence(self, topic: str) -> dict:
        """
        Analyze if a topic network is converging in training.
        """
        if topic not in self.topic_networks:
            return {'converged': False, 'reason': 'No network'}
        
        losses = self.topic_networks[topic].get_loss_history(20)
        
        if len(losses) < 5:
            return {'converged': False, 'reason': 'Too few samples'}
        
        # Check if losses are decreasing
        recent = losses[-5:]
        trend = sum(losses[-10:-5]) - sum(recent)
        
        converged = trend > 0.01  # Improving if positive
        
        return {
            'converged': converged,
            'recent_losses': recent,
            'trend': trend,
            'samples': self.topic_networks[topic].training_samples,
        }
