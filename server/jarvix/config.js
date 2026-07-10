export const LEARNING_CONFIG = {
  learning_rate: 0.9,
  overcompensation: 3.0,
  curiosity_threshold: 0.15,
  novelty_bonus: 2.0,
  confidence_decay: 0.95,
};

export const BEHAVIOR_CONFIG = {
  max_associations: 5,
  forgetting_rate: 0.02,
  learning_queue_max: 100,
  question_batch_size: 5,
};

export const EMOTIONAL_STATES = {
  excited: 0.8,
  curious: 0.15,
  thinking: 0.0,
  bored: -1.0,
};

export const STORAGE_CONFIG = {
  data_file: 'curious_mind_memory.json',
  max_conversation_history: 100,
  max_learning_log: 500,
  auto_save_interval: 10,
};

export const AGENT_METADATA = {
  name: 'Jarvix',
  version: '5.1.0',
  description: 'A self-learning cognitive AI without LLM dependencies',
  author: 'Gordon',
};
