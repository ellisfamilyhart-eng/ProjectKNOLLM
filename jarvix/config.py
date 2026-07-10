"""
Jarvix NoLLM - Configuration Module
Centralized settings for the self-learning AI
"""

# ============================================================
# LEARNING PARAMETERS
# ============================================================
LEARNING_CONFIG = {
    "learning_rate": 0.9,           # How fast it learns (0.9 = aggressive)
    "overcompensation": 3.0,        # Multiplier: learns X times more than needed
    "curiosity_threshold": 0.15,    # Prediction error that triggers curiosity
    "novelty_bonus": 2.0,           # Extra learning for completely new topics
    "confidence_decay": 0.95,       # Confidence drops if not reinforced (per interaction)
}

# ============================================================
# BEHAVIORAL PARAMETERS
# ============================================================
BEHAVIOR_CONFIG = {
    "max_associations": 5,          # How many related concepts to explore
    "forgetting_rate": 0.02,        # How much it forgets per day
    "learning_queue_max": 100,      # Maximum items in learning queue
    "question_batch_size": 5,       # Max questions to ask at once
}

# ============================================================
# EMOTIONAL STATES & TRIGGERS
# ============================================================
EMOTIONAL_STATES = {
    "excited": 0.8,                 # Threshold for excitement (surprise > 0.8)
    "curious": 0.15,                # Threshold for curiosity (surprise > 0.15)
    "thinking": 0.0,                # Default when processing
    "bored": -1.0,                  # When no surprise
}

# ============================================================
# STORAGE CONFIGURATION
# ============================================================
STORAGE_CONFIG = {
    "data_file": "curious_mind_memory.json",
    "max_conversation_history": 100,  # Keep last N messages
    "max_learning_log": 500,           # Keep last N learning events
    "auto_save_interval": 10,          # Save every N interactions
}

# ============================================================
# AGENT METADATA
# ============================================================
AGENT_METADATA = {
    "name": "Jarvix",
    "version": "1.0",
    "description": "A modular self-learning AI (NoLLM - No Large Language Model)",
    "author": "Gordon",
}
