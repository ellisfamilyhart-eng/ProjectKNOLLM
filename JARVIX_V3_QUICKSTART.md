# Jarvix v3.0 - Quick Start Guide

## What's New in v3.0?

Jarvix now has **three types of memory** that work together:

1. **Episodic** - Records every conversation
2. **Semantic** - Stores facts (like before)
3. **Neural** - Learns patterns from text encoding

Plus a **Reflection Engine** that:
- Reviews past episodes
- Replays them to improve
- Discovers patterns
- Gets better over time

---

## Installation & Setup

```bash
# Docker (simplest)
docker compose up

# Or local
pip install -r requirements.txt
python jarvix_cli.py
```

---

## How It Works Now

### Teaching (Same as Before)
```
You > Python: is a programming language
Jarvix > Wow! That's surprising!
         This is completely new to me...
         [Learning] Stored with confidence 1.00
```

### What Happens Behind the Scenes (NEW)

1. **Vocabulary** encodes "Python: is a programming language" → vector
2. **Neural network** learns this pattern
3. **Semantic memory** stores the fact
4. **Episodic memory** records the episode
5. **Weights saved** for next time

### Reflection (NEW - Happens Automatically)

While idle (or call `agent.reflect()`):
1. Picks a random past conversation
2. Re-encodes with vocabulary
3. Retrains neural network
4. Sees if it improved
5. Tries new facts it might learn from

---

## Key Features

### 1. Ask Questions (New Capabilities)

```
You > What is Python?
Jarvix > [About Python]
         1. Python is a programming language ✓ (very confident)
         
You > Why do people use Python?
Jarvix > [Why about Python]
         Based on what I know:
         - is a programming language
         - is widely used
```

### 2. Everything Persists

- Close Jarvix, come back later
- **All facts** still there (were before)
- **All episodes** still there (NEW)
- **Neural weights** still there (NEW)
- **Vocabulary** still learned (NEW)

### 3. Self-Improvement

```
You > Tell me you're better than yesterday
Jarvix > [Reflection Statistics]
         - Total reflections: 127
         - Average improvement per reflection: 0.0124
         - Total improvement: 1.57
```

### 4. Pattern Discovery

```
You > Show me what you've learned
Jarvix > [Pattern Analysis]
         - Most discussed topics: Programming, AI, Learning
         - Emotional states: Excited (40%), Curious (35%), Thinking (25%)
         - High-learning moments: 23 (topics: Python, AI, Patterns)
```

---

## Simple Commands

### CLI Commands
```bash
/stats              # Show statistics (now includes neural info)
/memory             # Show learned facts
/personality        # Show who you are
/reflect            # Reflect on memories
/analyze TOPIC      # Deep dive into a topic
/imagine TOPIC      # Generate creative thoughts
/forget             # Clear everything
/quit               # Exit
```

### Web Interface
Just use the chat box as normal. Behind the scenes:
- `POST /api/chat` - Teach or ask
- `GET /api/stats` - See all memory stats
- `GET /api/reflection` - See reflection progress
- `POST /api/reflect` - Force reflection

---

## Three Memory Systems Explained

### Semantic Memory (Symbolic Facts)
```python
# What it stores
agent.memory.facts = {
    "Python": {
        "is a programming language": 0.95,
        "is popular for AI": 0.87,
        ...
    }
}

# How to access
facts = agent.memory.get_facts_by_topic("Python")
confidence = agent.memory.get_confidence("Python", "is popular for AI")
```

### Episodic Memory (Episodes)
```python
# What it stores
[
    {
        "id": 1,
        "timestamp": "2026-07-06T21:50:00",
        "user_input": "Python: is a programming language",
        "agent_response": "Wow! That's surprising...",
        "metadata": {"topic": "Python", "surprise": 0.85, "emotion": "excited"}
    },
    ...
]

# How to access
episodes = agent.episodic_memory.get_recent_episodes(10)
python_eps = agent.episodic_memory.get_episodes_by_topic("Python")
important = agent.episodic_memory.get_high_surprise_episodes(0.7)
```

### Neural Memory (Learned Patterns)
```python
# Vocabulary encodes text
vector = agent.vocabulary.encode("Python is great")
# → [0.1, 0.05, 0.2, ..., 0.15]  (64 dimensions)

# Tiny neural network learns
agent.neural_learner.learn_topic_pattern("Python", "is great", 0.8)

# Predictions use neural weights
prediction = agent.neural_learner.predict_topic_pattern("Python", "is good")
# → 0.76  (predicted confidence)

# Weights saved automatically
agent.save()  # Saves weights to disk
```

---

## Reflection Engine

Runs on its own or you can trigger it:

```python
# Automatic (every N interactions)
# Manual trigger
agent.reflect()
# Output: "[Reflection #45] I replayed episode #23..."

# Deep reflection on topic
result = agent.reflection_engine.reflect_on_topic("Python")
# {
#   "episodes_found": 8,
#   "facts_learned": 6,
#   "total_retraining_improvement": 0.0567,
#   "insight": "I've learned..."
# }

# Continuous learning session
reflections = agent.continuous_learning(duration=20)
# Replays 20 episodes and improves

# Check progress
stats = agent.reflection_engine.get_reflection_statistics()
# {
#   "total_reflections": 127,
#   "avg_improvement": 0.0124,
#   "total_improvement": 1.57
# }
```

---

## Data Persistence

Your memory file now contains:

```json
{
  "facts": {...},                    // Semantic (facts)
  "episodic": [...],                 // Episodic (episodes)
  "neural": {                        // Neural (weights)
    "topic_networks": {
      "Python": {
        "weights": [0.1, 0.05, ...],
        "bias": 0.02,
        "training_samples": 42
      },
      ...
    }
  },
  "vocabulary": {                    // Vocabulary (encoding)
    "words": {
      "python": 0,
      "programming": 1,
      ...
    }
  },
  "reflection": {...}                // Reflection history
}
```

All this loads automatically on startup!

---

## Memory Statistics

After using Jarvix, check:

```python
stats = agent.get_stats()

print(f"Semantic facts: {stats['total_facts']}")
print(f"Episodic episodes: {stats['episodic_episodes']}")
print(f"Neural networks: {stats['neural_topic_networks']}")
print(f"Reflections: {stats['reflections_performed']}")

# See full summary
print(agent.get_memory_summary())
```

---

## Practical Example: Complete Session

```python
from jarvix import Jarvix

agent = Jarvix()

# --- TEACHING ---
print("Teaching phase...")
agent.process_input("Python: is a programming language")
agent.process_input("Python: is popular for AI")
agent.process_input("Machine Learning: is part of AI")
agent.process_input("Python: is used for machine learning")

# --- QUESTIONING ---
print("\nQuestion phase...")
answer = agent.question_answerer.answer_question("What is Python?")
print(answer)

# --- REFLECTION ---
print("\nReflection phase...")
for i in range(5):
    reflection = agent.reflect()
    print(reflection)

# --- STATISTICS ---
print("\nStatistics...")
stats = agent.get_stats()
print(f"Episodes recorded: {stats['episodic_episodes']}")
print(f"Neural networks: {stats['neural_topic_networks']}")

reflection_stats = agent.reflection_engine.get_reflection_statistics()
print(f"Reflections performed: {reflection_stats['total_reflections']}")
print(f"Average improvement: {reflection_stats['avg_improvement']:.4f}")

# --- SAVE ---
print("\nSaving...")
agent.save()
print("All systems saved!")

# --- LATER ---
# Restart Jarvix - it remembers everything!
agent2 = Jarvix()
stats2 = agent2.get_stats()
print(f"Reloaded: {stats2['episodic_episodes']} episodes")  # Still there!
```

---

## What Improves Over Time

1. **Confidence Scores**: Facts get higher confidence after reinforcement
2. **Neural Weights**: Get better at predicting confidence for new facts
3. **Associations**: Creates more connections between topics
4. **Pattern Recognition**: Discovers patterns in how you teach
5. **Personality**: Becomes more "you"

---

## Advanced: Continuous Learning

Make Jarvix learn while you sleep:

```python
agent = Jarvix()

# Teach it lots
for i in range(100):
    agent.process_input(f"Topic{i}: is interesting concept {i}")

# Let it reflect continuously
for round in range(10):
    reflections = agent.continuous_learning(duration=50)
    print(f"Round {round}: {len(reflections)} reflections")
    
    # Check progress
    trajectory = agent.reflection_engine.get_learning_trajectory()
    total_improvement = sum(r['improvement'] for r in trajectory)
    print(f"  Total improvement so far: {total_improvement:.4f}")

# See how much better it got
agent.save()
```

---

## Troubleshooting

**Q: Is it actually learning?**
```python
trajectory = agent.reflection_engine.get_learning_trajectory()
if sum(r['improvement'] for r in trajectory) > 0:
    print("Yes, it's improving!")
```

**Q: Where's my data saved?**
```
curious_mind_v2_memory.json  (or jarvix_memory.json)
```

**Q: Can I export everything?**
```python
export = agent.export_memory()
import json
json.dump(export, open("backup.json", "w"))
```

---

## Key Differences from v2.0

| Feature | v2.0 | v3.0 |
|---------|------|------|
| Remembers facts | ✅ | ✅ |
| Remembers conversations | ❌ | ✅ (Episodic) |
| Neural learning | ❌ | ✅ (Neural + Weights) |
| Self-improvement | ❌ | ✅ (Reflection) |
| Pattern discovery | ❌ | ✅ |
| Persistence | Facts only | All data |
| Answer questions | ✅ | ✅ (+ neural-enhanced) |

---

## Summary

**Jarvix v3.0 = Memory + Learning + Self-Improvement**

- **Episodic**: Remembers every conversation
- **Semantic**: Stores facts you teach
- **Neural**: Learns patterns from encoding
- **Reflection**: Gets better by replaying memories

It's like you have a student who:
1. Pays attention (episodic)
2. Takes notes (semantic)
3. Studies patterns (neural)
4. Does homework on their own (reflection)

And they get better every day! 🚀
