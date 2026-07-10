# Jarvix NoLLM v2.0 - Complete Feature Guide

## 🎯 Overview

**Jarvix v2.0** adds four powerful new capabilities to the self-learning AI:

1. **Imagination Module** - Creative thinking, hypotheticals, theories
2. **Conversation Module** - Tracks context, prevents duplicate learning, builds personality
3. **Recursive Learner** - Learns from web pages and text, follows links recursively
4. **Question Answerer** - Answers questions based on learned knowledge

---

## 🧠 Module Details

### 1. Imagination Module (`imagination.py`)

Generates creative and speculative thoughts based on learned facts.

**Features:**
- **Hypothetical Reasoning**: "What if..." questions
- **Analogies**: Finds connections between different concepts
- **Pattern Extrapolation**: Predicts new properties based on learned facts
- **Theory Generation**: Creates speculative theories
- **Concept Combinations**: Creatively merges learned concepts
- **Philosophical Questions**: Deeper "why" questions

**Usage:**

```python
agent = Jarvix()
agent.process_input("Python: is a programming language")
agent.process_input("Java: is also a programming language")

# Generate hypothetical questions
hypotheticals = agent.imagination.generate_hypothetical("Python", "is a programming language")
# Output: ["What if the opposite were true...", "Could it apply to Java...", ...]

# Generate theories
theory = agent.theorize("Python")
# Output: "[Emerging Theory] Based on what I know about Python..."

# Find analogies
analogies = agent.get_analogies("Python", "Java")
# Output: ["Like Java is also a programming language, similarly Python is..."]

# Get imagination summary
summary = agent.imagine()
# Output: Creative synthesis of current learning
```

**API Endpoints:**
- `GET /api/imagine?topic=Python` - Imagination about a topic
- `GET /api/theorize?topic=Python` - Generate theory
- `GET /api/analogies?topic1=Python&topic2=Java` - Find analogies

---

### 2. Conversation Module (`conversation.py`)

Manages conversation context and prevents duplicate learning.

**Features:**
- **Duplicate Detection**: Won't learn the same fact twice
- **Conversation Threads**: Tracks past conversations
- **User Preference Learning**: Learns user's favorite topics
- **Interaction Patterns**: Tracks how often topics are discussed
- **Personality Development**: Builds agent personality based on interactions
- **Response Tone Adjustment**: Adapts tone based on conversation flow

**Usage:**

```python
agent = Jarvix()

# Add an exchange
agent.conversation.add_exchange(
    user_input="Python: is a programming language",
    agent_response="That's interesting...",
    metadata={'topic': 'Python'}
)

# Check for duplicates
is_dup, confidence = agent.conversation.is_duplicate_fact("Python", "is a programming language")
# Output: (True, 0.85) - Already learned

# Get user interests
interests = agent.conversation.get_user_interests(top_n=3)
# Output: ['Python', 'Programming', 'Languages']

# Get personality summary
personality = agent.get_personality()
# Output: "[Personality Profile]\nI find these topics most engaging..."

# Get conversation statistics
stats = agent.conversation.get_conversation_statistics()
# Output: {'current_exchanges': 5, 'total_past_conversations': 2, ...}
```

**API Endpoints:**
- `GET /api/personality` - Get agent personality
- `GET /api/history?limit=10` - Get conversation history

---

### 3. Recursive Learner (`recursive_learner.py`)

Learns from web pages and text, can recursively follow links.

**Features:**
- **Web Scraping**: Fetches and processes web pages
- **Text Extraction**: Extracts facts from raw text
- **Recursive Learning**: Follows links and learns recursively (depth-limited)
- **Duplicate Detection**: Integrates with conversation module
- **Fact Extraction**: Uses pattern matching ("X is Y", "X has Y", "X does Y")
- **URL Tracking**: Remembers visited URLs

**Installation (requires requests):**
```bash
pip install requests beautifulsoup4
```

**Usage:**

```python
agent = Jarvix()

# Learn from a URL
response = agent.learn_from_url("https://example.com/article")
# Output: "[Learning from Web] 15 facts extracted from..."

# Learn from raw text
text = "Python is a programming language. Java is also a programming language."
response = agent.learn_from_text(text)
# Output: "[Learning from Text] 2 new facts learned"

# Analyze text for facts (without learning)
analysis = agent.recursive_learner.analyze_text(text)
# Output: {'paragraph_count': 1, 'sentence_count': 2, 'fact_count': 2, ...}

# Learn from multiple URLs
urls = ["https://example.com/1", "https://example.com/2"]
response = agent.learn_from_urls(urls)

# Get learning statistics
stats = agent.recursive_learner.get_learning_statistics()
# Output: {'urls_visited': 5, 'facts_extracted': 42, 'current_depth': 2}
```

**API Endpoints:**
- `POST /api/learn-url` - Learn from a URL
- `POST /api/learn-text` - Learn from text
- `POST /api/analyze-text` - Analyze text for facts

**Request Bodies:**
```json
# Learn from URL
{
  "url": "https://example.com/article"
}

# Learn from text
{
  "text": "Python is a programming language..."
}

# Analyze text
{
  "text": "Python is a programming language..."
}
```

---

### 4. Question Answerer (`question_answerer.py`)

Answers user questions based on learned knowledge.

**Features:**
- **Question Detection**: Identifies questions vs. statements
- **Question Type Classification**: What, Why, How, When, Where, Who
- **Knowledge Search**: Finds relevant facts
- **Answer Formatting**: Generates coherent answers
- **Confidence Reporting**: Indicates how confident in answers
- **Graceful Fallback**: Admits when it doesn't know

**Usage:**

```python
agent = Jarvix()

# Teach first
agent.process_input("Python: is a programming language")
agent.process_input("Python: supports object-oriented programming")

# Answer questions
answer = agent.question_answerer.answer_question("What is Python?")
# Output: "[About Python]\n1. Python is a programming language..."

# Check question type
q_type = agent.question_answerer.get_question_type("Why is Python popular?")
# Output: "causal"

# Get answer confidence
confidence = agent.question_answerer.get_answer_confidence("Python")
# Output: 0.85

# Via agent (simpler)
response = agent.process_input("What is Python?")
```

**Question Types & Answers:**
- **Factual ("What...")**: Lists known facts with confidence
- **Causal ("Why...")**: Explains underlying reasons
- **Procedural ("How...")**: Provides steps or method
- **General**: Best-effort answer from learned facts

**API Endpoints:**
- `POST /api/ask` - Ask a question

**Request Body:**
```json
{
  "question": "What is Python?"
}
```

**Response:**
```json
{
  "success": true,
  "question": "What is Python?",
  "answer": "[About Python]\n1. Python is a programming language ✓\n...",
  "confidence": 0.85
}
```

---

## 📚 Complete Interaction Examples

### Example 1: Teaching and Answering

```python
agent = Jarvix()

# Teach
agent.process_input("Photosynthesis: is the process by which plants make food")
agent.process_input("Photosynthesis: uses sunlight and chlorophyll")

# Ask
answer = agent.question_answerer.answer_question("What is photosynthesis?")
print(answer)
# Output:
# [About Photosynthesis]
# 1. Photosynthesis is the process by which plants make food ✓ (very confident)
# 2. Photosynthesis uses sunlight and chlorophyll ~ (fairly confident)
```

### Example 2: Web Learning & Q&A

```python
agent = Jarvix()

# Learn from Wikipedia
agent.learn_from_url("https://en.wikipedia.org/wiki/Machine_Learning")

# Now answer questions
answer = agent.question_answerer.answer_question("What is machine learning?")
print(answer)

# Get imagination
theory = agent.theorize("Machine Learning")
print(theory)
```

### Example 3: Deduplication & Personality

```python
agent = Jarvix()

# First teaching
response1 = agent.process_input("Python: is a language")
print(response1)  # [Excited] "Wow! That's surprising!"

# Duplicate attempt
response2 = agent.process_input("Python: is a programming language")
print(response2)  # "I already know that python is..."

# User preferences tracked
interests = agent.conversation.get_user_interests()
print(interests)  # ['Python', 'Programming', ...]

# Personality emerges
print(agent.get_personality())
```

### Example 4: Recursive Learning from Text

```python
agent = Jarvix()

article_text = """
Artificial Intelligence is transforming the world.
AI systems learn from data and improve over time.
Machine Learning is a subset of AI.
Deep Learning uses neural networks.
"""

# Extract and learn
agent.learn_from_text(article_text)

# Now it knows facts from that text
analysis = agent.question_answerer.answer_question("What is Machine Learning?")
print(analysis)
```

---

## 🔗 Web API Reference (v2.0)

### Teaching & Learning

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/chat` | POST | Send message (teach or ask) |
| `/api/bulk-teach` | POST | Teach multiple facts |
| `/api/learn-url` | POST | Learn from webpage |
| `/api/learn-text` | POST | Learn from text |
| `/api/analyze-text` | POST | Analyze text (no learning) |

### Question Answering

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/ask` | POST | Answer a question |

### Creativity & Imagination

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/imagine` | GET | Generate imagination |
| `/api/theorize` | GET | Generate theories |
| `/api/analogies` | GET | Find analogies |
| `/api/thoughts` | GET | Autonomous thoughts |

### Introspection

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/stats` | GET | Agent statistics |
| `/api/memory` | GET | Current memory |
| `/api/history` | GET | Conversation history |
| `/api/personality` | GET | Agent personality |
| `/api/analyze/<topic>` | GET | Analyze a topic |
| `/api/export` | GET | Export all knowledge |

### Admin

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/forget` | POST | Clear all memories |
| `/api/health` | GET | Health check |

---

## 🚀 Quick Start

### Local CLI

```bash
# Using updated CLI
python jarvix_cli.py

# Then type:
You > Python: is a programming language
You > What is Python?
You > /imagine
You > /theorize
You > /personality
```

### Web Interface

```bash
# Start server
docker compose up

# Open browser
# http://localhost:5000

# In chat box:
# - Type: "Python: is a programming language"
# - Ask: "What is Python?"
# - Try: "[weblearn] https://example.com"
```

### Programmatic

```python
from jarvix import Jarvix

agent = Jarvix()

# Teach
agent.process_input("Concept: is a definition")

# Ask
answer = agent.question_answerer.answer_question("What is Concept?")

# Imagine
imagination = agent.imagine("Concept")

# Web learning
agent.learn_from_url("https://example.com/article")

# Get personality
print(agent.get_personality())
```

---

## ⚙️ Configuration & Customization

All parameters in `jarvix/config.py`:

```python
LEARNING_CONFIG = {
    "learning_rate": 0.9,           # Increase for faster learning
    "overcompensation": 3.0,        # Higher = learns more patterns
    "curiosity_threshold": 0.15,    # Lower = more curious
    "novelty_bonus": 2.0,           # Bonus for new topics
    "confidence_decay": 0.95,       # Forgetting rate
}

BEHAVIOR_CONFIG = {
    "max_associations": 5,          # More = more connections
    "learning_queue_max": 100,      # Larger = longer memory
    "question_batch_size": 5,       # Questions per response
}
```

**Tweak for:**
- **Faster Learning**: Increase `learning_rate` and `overcompensation`
- **More Curious**: Decrease `curiosity_threshold`
- **More Forgetting**: Decrease `confidence_decay`
- **More Creative**: Increase `max_associations`

---

## 🧪 Testing New Features

```python
# Test all v2.0 features
from jarvix import Jarvix

agent = Jarvix()

# 1. Teaching
print("\n=== TEACHING ===")
agent.process_input("Neural Networks: are computational models")
agent.process_input("Deep Learning: uses neural networks")

# 2. Conversation deduplication
print("\n=== DEDUPLICATION ===")
response = agent.process_input("Neural Networks: are computational models")
print("Duplicate detected:", "already know" in response.lower())

# 3. Q&A
print("\n=== Q&A ===")
answer = agent.question_answerer.answer_question("What are neural networks?")
print(answer)

# 4. Imagination
print("\n=== IMAGINATION ===")
print(agent.imagine("Neural Networks"))

# 5. Text learning
print("\n=== TEXT LEARNING ===")
text = "Neurons are the building blocks of brains. Artificial neurons model biological neurons."
agent.learn_from_text(text)
print("Learned from text")

# 6. Personality
print("\n=== PERSONALITY ===")
print(agent.get_personality())

# 7. Stats
print("\n=== STATS ===")
print(agent.get_stats())
```

---

## 📝 Changelog (v0.1 → v2.0)

### v0.1 (Original)
- Basic learning from user input
- CLI interface
- Emotional states
- Simple conversation

### v1.0 (Modularization)
- Broke monolithic code into 6 modules
- Added configuration system
- Added response generator
- Added parser

### v2.0 (Enhanced)
- ✅ Imagination module (creative thinking)
- ✅ Conversation module (deduplication + personality)
- ✅ Recursive Learner (web scraping + text analysis)
- ✅ Question Answerer (Q&A engine)
- ✅ Web API for all new features
- ✅ Prevents duplicate learning
- ✅ Personality development

---

## 🎯 Future Enhancements

- Semantic similarity (use embeddings)
- Knowledge graph visualization
- Multi-language support
- Advanced NLP (dependency parsing, NER)
- Reasoning with uncertainty
- Collaborative learning (multiple agents)
- Export to knowledge graphs (RDF, Neo4j)

---

## 📞 Support

For issues or questions, check:
1. `JARVIX_ARCHITECTURE.md` - Architecture details
2. Module docstrings - Function documentation
3. Web API examples above - Usage patterns
4. CLI help - `python jarvix_cli.py` and try `/help`

---

**Jarvix NoLLM v2.0 is ready to learn, create, and answer!** 🚀
