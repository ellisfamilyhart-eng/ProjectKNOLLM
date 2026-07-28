# Jarvix NoLLM v3.0 - Complete Module Reference

## Core Architecture

### Memory Systems (Three-Tier)

#### 1. `vocabulary.py` - Text Encoding
**Purpose**: Convert text to fixed-size numeric vectors

```python
from jarvix import Vocabulary

vocab = Vocabulary()
vector = vocab.encode("Python is great", size=64)
# → [0.1, 0.05, 0.2, ..., 0.15]  (64 dimensions)

vocab.get_vocabulary_size()  # How many unique words learned
vocab.export()              # Save vocabulary
vocab.import_vocab(data)    # Load vocabulary
```

**Use Cases**:
- Input to neural networks
- Encoding user input
- Enabling pattern learning

**Key Methods**:
- `encode(text, size=64)` - Text to vector
- `add_word(word)` - Add to vocabulary
- `export()` / `import_vocab()` - Persistence

---

#### 2. `episodic_memory.py` - Conversation Recording
**Purpose**: Record every conversation for replay and analysis

```python
from jarvix import EpisodicMemory

ep_mem = EpisodicMemory(max_episodes=1000)
ep_mem.record_episode(
    user_input="Python: is great",
    agent_response="Wow!",
    metadata={'topic': 'Python', 'surprise': 0.85}
)

ep_mem.get_recent_episodes(10)           # Last 10
ep_mem.get_episodes_by_topic("Python")   # All Python episodes
ep_mem.get_high_surprise_episodes(0.7)   # Important moments
ep_mem.get_statistics()                  # Stats
```

**Use Cases**:
- Replay for learning
- Pattern discovery
- Memory analysis
- Finding important moments

**Key Methods**:
- `record_episode()` - Save conversation
- `get_recent_episodes()` - Retrieve recent
- `get_episodes_by_topic()` - Filter by topic
- `get_episodes_by_emotion()` - Filter by emotion
- `get_high_surprise_episodes()` - Important moments
- `export()` / `import_episodes()` - Persistence

---

#### 3. `neural_learner.py` - Pattern Learning
**Purpose**: Learn patterns through tiny neural networks

```python
from jarvix import NeuralLearner

neural = NeuralLearner(memory, feature_size=64)

# Learn topic-specific pattern
loss = neural.learn_topic_pattern("Python", "is great", confidence=0.8)

# Predict using neural network
prediction, has_network = neural.predict_topic_pattern("Python", "is good")

# Batch learning
avg_loss = neural.batch_learn_topic("Python", facts_list, epochs=5)

# Statistics
neural.get_topic_network_stats("Python")
neural.get_all_topics_neural_performance()
```

**Use Cases**:
- Learning patterns from text
- Predicting confidence
- Per-topic specialization
- Neural + symbolic integration

**Key Methods**:
- `learn_topic_pattern()` - Single sample training
- `predict_topic_pattern()` - Get prediction
- `batch_learn_topic()` - Multiple samples
- `get_topic_network_stats()` - Network info
- `hybrid_predict_confidence()` - Symbolic + neural

---

#### 4. `memory_store.py` - Semantic Memory (Updated)
**Purpose**: Store facts, patterns, and associations

```python
from jarvix import MemoryStore

memory = MemoryStore()

# Add facts
memory.add_fact("Python", "is a language", confidence=0.9)

# Retrieve
facts = memory.get_facts_by_topic("Python")
confidence = memory.get_confidence("Python", "is a language")

# Associations
memory.add_association("Python", "Programming")
related = memory.get_associations("Python")

# Save everything (including neural data)
memory.save(
    neural_data=neural_state,
    episodic_data=episodes,
    reflection_data=reflections,
    vocab_data=vocabulary
)
```

**Updated Features** (v3.0):
- Now saves neural weights
- Saves episodic memory
- Saves vocabulary
- Saves reflection history

---

### Reflection System

#### 5. `reflection.py` - Self-Improvement Engine
**Purpose**: Review past episodes and improve continuously

```python
from jarvix import ReflectionEngine

reflection = ReflectionEngine(memory, neural_learner, 
                             episodic_memory, vocabulary)

# Random reflection
reflection_note = reflection.reflect_idle()

# Deep reflection on topic
result = reflection.reflect_on_topic("Python")

# Continuous learning session
reflections = reflection.continuous_learning_session(duration=20)

# Discover patterns
patterns = reflection.discover_patterns()

# Statistics
stats = reflection.get_reflection_statistics()
trajectory = reflection.get_learning_trajectory()
```

**How It Works**:
1. Pick random episode from episodic memory
2. Re-encode with vocabulary
3. Retrain neural network
4. Compare loss before/after
5. Track improvement

**Key Methods**:
- `replay_episode()` - Replay single episode
- `reflect_on_topic()` - Deep reflection
- `reflect_idle()` - Random reflection
- `discover_patterns()` - Find patterns
- `reinforce_important_facts()` - Strengthen knowledge
- `get_learning_trajectory()` - See improvements

---

### AI Components

#### 6. `brain.py` - Prediction & Learning Engine
**Purpose**: Core prediction and learning logic

```python
from jarvix import Brain

brain = Brain(memory)

# Predict
fact, confidence = brain.predict("Python")

# Surprise calculation
surprise = brain.calculate_surprise("Python", new_fact)

# Update emotion
brain.update_emotion(surprise)

# Generalization
generalizations = brain.generalize("Python", fact)

# Questions
questions = brain.generate_questions("Python", fact, surprise)

# Analysis
analysis = brain.analyze_topic("Python")
```

**No Changes in v3.0** - Still works as before, now benefits from neural memory

---

#### 7. `agent.py` - Main Orchestrator (Updated)
**Purpose**: Coordinate all systems

```python
from jarvix import Jarvix

agent = Jarvix()

# Main interaction
response = agent.process_input("Python: is a language")

# Statistics
stats = agent.get_stats()

# Reflection
agent.reflect()
patterns = agent.discover_patterns()

# Learning
agent.learn_from_url("https://...")
agent.learn_from_text("Text here...")

# Persistence
agent.save()

# Export
exported = agent.export_memory()
```

**Key Updates** (v3.0):
- Integrates all three memory systems
- Auto-saves neural weights
- Loads saved weights on startup
- Coordinates reflection engine

---

### Supporting Modules

#### 8. `parser.py` - Natural Language Parsing
Parse user input into topic and fact

```python
from jarvix import InputParser

topic, fact = InputParser.parse("Python: is a language")
# → ("Python", "is a language")

is_q = InputParser.is_question("What is Python?")
# → True

q_type = InputParser.get_question_type("Why is Python popular?")
# → "causal"

keywords = InputParser.extract_keywords("Python is great for AI")
# → ["python", "great", "artificial", "intelligence"]
```

---

#### 9. `imagination.py` - Creative Thinking
Generate creative and speculative thoughts

```python
from jarvix import Imagination

imagination = Imagination(memory)

# Hypotheticals
hypotheticals = imagination.generate_hypothetical("Python", fact)

# Analogies
analogies = imagination.find_analogies("Python", "Java")

# Theories
theory = imagination.generate_theory("Python")

# Combinations
combo = imagination.combine_concepts(limit=3)

# Philosophical questions
questions = imagination.generate_philosophical_questions("Python")
```

---

#### 10. `conversation.py` - Conversation Management
Manage context and prevent duplicate learning

```python
from jarvix import ConversationManager

conversation = ConversationManager(memory)

# Add exchange
conversation.add_exchange(user_input, agent_response, metadata)

# Check duplicates
is_dup, confidence = conversation.is_duplicate_fact("Python", "is a language")

# User preferences
conversation.update_user_preferences({'topic': 'Python'})
interests = conversation.get_user_interests(top_n=5)

# Statistics
stats = conversation.get_conversation_statistics()

# Personality
personality = conversation.get_personality_summary()
```

---

#### 11. `question_answerer.py` - Q&A Engine
Answer user questions

```python
from jarvix import QuestionAnswerer

qa = QuestionAnswerer(memory, brain)

# Answer
answer = qa.answer_question("What is Python?")

# Confidence
confidence = qa.get_answer_confidence("Python")

# Question analysis
q_type = qa.get_question_type("Why?")
focus = qa.extract_question_focus("What is Python?")
```

---

#### 12. `recursive_learner.py` - Web & Text Learning
Learn from external sources

```python
from jarvix import RecursiveLearner

learner = RecursiveLearner(memory, brain, conversation)

# Learn from web
facts = learner.learn_from_url("https://...")

# Learn from text
facts = learner.extract_facts_from_text("Text here")

# Analyze text
analysis = learner.analyze_text("Text")

# Statistics
stats = learner.get_learning_statistics()
```

---

#### 13. `response_generator.py` - Response Generation
Generate personality-rich responses

```python
from jarvix import ResponseGenerator

gen = ResponseGenerator()

# Generate response
response = gen.generate_response(
    emotion='excited',
    prediction='old belief',
    fact='new fact',
    surprise=0.85,
    questions=[...],
    stats={...}
)

# Summaries
summary = gen.generate_summary(agent)
memory_dump = gen.generate_memory_dump(memory)
status = gen.generate_status_report(memory)
```

---

### Configuration

#### 14. `config.py` - All Settings
All tunable parameters

```python
from jarvix import (
    LEARNING_CONFIG,
    BEHAVIOR_CONFIG,
    EMOTIONAL_STATES,
    STORAGE_CONFIG,
    AGENT_METADATA,
)

# Tune these to change behavior
LEARNING_CONFIG['learning_rate'] = 0.9
BEHAVIOR_CONFIG['max_associations'] = 5
STORAGE_CONFIG['auto_save_interval'] = 10
```

---

## File Dependencies

```
agent.py (main orchestrator)
├── memory_store.py (semantic memory)
├── brain.py
├── imagination.py
├── conversation.py
├── recursive_learner.py
├── question_answerer.py
├── parser.py
├── response_generator.py
├── episodic_memory.py (NEW)
├── neural_learner.py (NEW)
│   └── vocabulary.py (NEW)
└── reflection.py (NEW)
    ├── episodic_memory.py
    ├── neural_learner.py
    └── vocabulary.py
```

---

## Data Flow

```
User Input
    ↓
parser.py → topic, fact
    ↓
conversation.py → check duplicates
    ↓
vocabulary.py → encode to vector
    ↓
neural_learner.py → predict & train
    ↓
brain.py → surprise calculation
    ↓
imagination.py → creative ideas
    ↓
response_generator.py → generate response
    ↓
episodic_memory.py → record episode
    ↓
memory_store.py → save facts
    ↓
(Automatic) → reflection.py → improve
    ↓
(Automatic) → save all data to disk
```

---

## Quick Reference

| Module | Purpose | Key Input | Key Output |
|--------|---------|-----------|-----------|
| vocabulary | Text → Vector | String | [float] |
| episodic_memory | Record episodes | user_input, response | episode dict |
| neural_learner | Learn patterns | vector, target | loss, weights |
| memory_store | Store facts | topic, fact | confidence |
| reflection | Self-improve | episodic_memory | improvement |
| brain | Predict | topic | (fact, confidence) |
| parser | Parse input | user_input | (topic, fact) |
| imagination | Create ideas | topic | hypotheticals |
| conversation | Manage context | exchange | personality |
| question_answerer | Answer Q's | question | answer |
| recursive_learner | Web learning | URL/text | facts |
| response_generator | Generate text | emotion, facts | response |
| agent | Orchestrate | anything | everything |

---

## Summary

**v3.0 adds 4 new core modules:**
1. `vocabulary.py` - Text encoding
2. `episodic_memory.py` - Conversation recording
3. `neural_learner.py` - Pattern learning
4. `reflection.py` - Self-improvement

**That enable:**
- Persistent neural learning
- Complete memory of conversations
- Continuous self-improvement
- True continual learning

**Everything else** (agent, brain, imagination, etc.) still works, now benefits from neural enhancement.
