# Jarvix NoLLM - Modular Architecture Documentation

## Overview

**Jarvix NoLLM** is a complete refactor of CuriousMind into a modular, production-grade self-learning AI system. It requires no LLM and learns purely through prediction error and curiosity-driven generalization.

**Version:** 1.0  
**Backup Location:** `backups/curious_mind_v0.1_backup.py`

---

## Architecture

### Module Breakdown

```
jarvix/
├── __init__.py              # Public API
├── config.py               # Configuration & parameters
├── memory_store.py         # Persistent memory (facts, patterns, history)
├── brain.py                # Prediction engine & learning logic
├── parser.py               # Input parsing & NLP
├── response_generator.py   # Response generation
└── agent.py                # Main orchestrator (Jarvix class)

jarvix_cli.py              # Command-line interface
app.py                     # Flask web server
```

---

## Module Specifications

### 1. **config.py** - Configuration
Centralized parameter management for the entire system.

**Key Configurations:**
- `LEARNING_CONFIG`: Learning rate, overcompensation, curiosity thresholds
- `BEHAVIOR_CONFIG`: Max associations, learning queue size
- `EMOTIONAL_STATES`: Emotion thresholds (excited > 0.8, curious > 0.15)
- `STORAGE_CONFIG`: File paths, history limits, save intervals
- `AGENT_METADATA`: Name, version, description

**Usage:**
```python
from jarvix.config import LEARNING_CONFIG
learning_rate = LEARNING_CONFIG['learning_rate']
```

**Customization:**
Edit `config.py` to tune agent personality without touching core logic.

---

### 2. **memory_store.py** - Memory Management
Handles all persistent memory and learning history.

**Core Structures:**
- `facts`: `{topic: {fact: confidence_score}}`
- `patterns`: Extracted rule patterns
- `associations`: Graph of topic relationships
- `conversation_history`: User/agent exchanges
- `learning_log`: Timestamped learning events

**Key Methods:**
```python
store = MemoryStore()

# Learning
store.add_fact(topic, fact, confidence=0.5)

# Retrieval
facts = store.get_facts_by_topic(topic)
confidence = store.get_confidence(topic, fact)

# Relationships
store.add_association(topic1, topic2)
related = store.get_associations(topic)

# Maintenance
store.decay_confidence()  # Simulate forgetting
store.save()              # Persist to disk
```

**Persistence:**
- Auto-saves every N interactions (configurable)
- JSON format for human readability
- Supports import/export

---

### 3. **brain.py** - Prediction Engine
The core learning and prediction logic.

**Core Responsibilities:**
1. **Prediction**: Forecasts facts about topics
2. **Surprise Calculation**: Measures how unexpected information is
3. **Emotion Management**: Updates emotional state
4. **Generalization**: Extracts patterns and creates associations
5. **Question Generation**: Formulates curiosity-driven questions
6. **Thought Generation**: Autonomous reasoning

**Key Methods:**
```python
brain = Brain(memory)

# Prediction
fact, confidence = brain.predict(topic)

# Learning
surprise = brain.calculate_surprise(topic, new_fact)
brain.update_emotion(surprise)

# Generalization
patterns = brain.generalize(topic, fact)

# Curiosity
questions = brain.generate_questions(topic, fact, surprise)

# Autonomy
thought = brain.generate_autonomous_thought(learning_queue)
```

**Learning Formula:**
```
new_confidence = min(1.0, old_confidence + (surprise * learning_rate * overcompensation))
```

---

### 4. **parser.py** - Input Parser
Natural language processing for user input.

**Supported Formats:**
```python
parser = InputParser()

# Format 1: "Topic: Fact" (recommended)
topic, fact = parser.parse("Python: is a programming language")

# Format 2: Natural language
topic, fact = parser.parse("Python is a programming language")

# Validation
valid = parser.validate_fact(topic, fact)

# Command detection
is_cmd = parser.is_command("/stats")
cmd, args = parser.parse_command("/analyze Python")

# Keyword extraction
keywords = parser.extract_keywords("Python is a popular language")
```

---

### 5. **response_generator.py** - Response Generation
Generates personality-rich responses.

**Response Components:**
1. Emotional reaction (Excited, Curious, Thinking, Bored)
2. Prediction vs. reality comparison
3. Learning confirmation
4. Generated questions
5. Statistics update
6. Mood display

**Methods:**
```python
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

### 6. **agent.py** - Main Orchestrator (Jarvix)
Coordinates all modules into a coherent agent.

**Main Responsibilities:**
1. Process user input end-to-end
2. Coordinate learning loop
3. Manage learning queue
4. Provide introspection/statistics
5. Handle memory operations

**Key Methods:**
```python
agent = Jarvix()

# Interaction
response = agent.process_input("Topic: Fact")

# Statistics
stats = agent.get_stats()
analysis = agent.analyze_topic("Python")

# Memory
agent.clear_memory()
exported = agent.export_memory()
agent.import_facts({...})

# Autonomy
thought = agent.autonomous_thought()

# Reporting
summary = agent.get_session_summary()
memory_view = agent.get_memory_summary()
status = agent.get_status_report()
```

**Interaction Pipeline:**
```
1. parse_input(user_input) → (topic, fact)
2. predict(topic) → (prediction, confidence)
3. calculate_surprise(topic, fact) → surprise_score
4. update_emotion(surprise)
5. learn(topic, fact, surprise)
6. generate_questions(topic, fact, surprise)
7. generate_response(...) → response_text
8. save_memory() [periodic]
```

---

## Usage Examples

### CLI Usage
```bash
# Start Jarvix
python jarvix_cli.py

# Example interaction
You > Grammar: is the system of rules for language
Jarvix > Wow! That's surprising!
         I'm learning about a new concept...
         [Curiosity] I need to know more:
           1. Why is this true about Grammar?
           2. How does it relate to what I know?

# Commands
/stats      # Show statistics
/memory     # Show current memory
/summary    # Session summary
/analyze Python
/thought    # Get autonomous thought
/forget     # Clear all memory
/quit       # Exit
```

### Programmatic Usage
```python
from jarvix import Jarvix

# Create agent
agent = Jarvix()

# Teach it
response1 = agent.process_input("Python: is a programming language")
response2 = agent.process_input("Python: supports multiple paradigms")

# Get stats
stats = agent.get_stats()
print(f"Topics: {stats['topics_known']}")
print(f"Mood: {stats['emotional_state']}")

# Analyze
analysis = agent.analyze_topic("Python")
print(f"Facts about Python: {len(analysis['known_facts'])}")

# Export
exported = agent.export_memory()

# Clear
agent.clear_memory()
```

### Web API Usage (Flask)
```bash
# Chat
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Python: is a programming language"}'

# Stats
curl http://localhost:5000/api/stats

# Bulk teach
curl -X POST http://localhost:5000/api/bulk-teach \
  -H "Content-Type: application/json" \
  -d '{"facts": ["Topic1: Fact1", "Topic2: Fact2"]}'

# Analyze
curl http://localhost:5000/api/analyze/Python

# Report
curl http://localhost:5000/api/report?type=memory
```

---

## Extending the System

### Adding New Features

#### 1. New Learning Strategy
Edit `brain.py`, extend `Brain` class:
```python
def learn_with_context(self, topic, fact, context_facts):
    """Learn with contextual information"""
    # Implementation
```

#### 2. New Emotion State
Edit `config.py`:
```python
EMOTIONAL_STATES = {
    ...
    'overwhelmed': 0.95,  # New state
}
```

#### 3. New Response Type
Edit `response_generator.py`:
```python
def generate_poetic_response(self, topic, fact):
    """Generate responses in verse"""
    # Implementation
```

#### 4. New Storage Backend
Create `storage.py`:
```python
class SQLiteStore:
    """Alternative storage backend"""
    def save(self): pass
    def load(self): pass
```

---

## Performance & Optimization

### Memory Management
- Facts decay in confidence over time (configurable)
- Low-confidence facts are pruned
- Conversation history capped to last N entries
- Learning log capped to last N events

### Learning Efficiency
- Over-compensation (3x learning) makes patterns stand out
- Associations link related concepts
- Generalization extracts rules from facts
- Learning queue prioritizes surprising topics

### Scaling
- Suitable for: single-user, interactive learning
- Not suitable for: distributed systems, real-time streaming
- Estimated max topics: 10,000+ (limited by JSON serialization)

---

## Testing Checklist

```
[✓] Module imports work
[✓] Memory saves/loads correctly
[✓] Prediction accuracy improves over time
[✓] Emotions update correctly
[✓] Questions are generated appropriately
[✓] Associations form correctly
[✓] Web API endpoints work
[✓] Bulk teaching works
[✓] Statistics are accurate
[✓] Forgetting mechanism works
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Memory not persisting | Check file permissions, path in `config.py` |
| Agent seems to forget facts | Check `confidence_decay` setting |
| Too many questions generated | Adjust `question_batch_size` in config |
| Learning too slow | Increase `learning_rate` in config |
| Web server won't start | Check port 5000 availability |

---

## Version History

- **v1.0 (Current)**: Complete modular refactor from CuriousMind v0.1
- **v0.1 (Backup)**: Original monolithic implementation

---

## License & Attribution

Jarvix NoLLM is a modularized version of CuriousMind AI.  
Built with Python, Flask, and Docker.
