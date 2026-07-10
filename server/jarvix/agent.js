import { MemoryStore } from './memory-store.js';
import { Brain } from './brain.js';
import { SemanticMemory } from './semantic-memory.js';
import { BasicConversation } from './basic-conversation.js';
import { tryBuiltinAnswer, seedAgent } from './core-knowledge.js';
import fs from 'fs';
import { STORAGE_CONFIG, AGENT_METADATA, LEARNING_CONFIG } from './config.js';

export class Jarvix {
  constructor(dataFile = null) {
    this.memory = new MemoryStore(dataFile);
    this.brain = new Brain(this.memory);
    this.semanticMemory = new SemanticMemory();
    this.basicConversation = new BasicConversation(this.memory);
    this.interactionCount = 0;
    this.name = AGENT_METADATA.name;
    this.learningQueue = [];
    this._loadState();
    seedAgent(this);
  }

  processInput(raw) {
    if (!raw || !raw.trim()) return "I'm listening — go ahead!";

    this.interactionCount++;
    this.memory.totalInteractions++;

    const text = raw.trim();
    const builtin = tryBuiltinAnswer(text);
    if (builtin) {
      this.memory.addConversation('user', text);
      this.memory.addConversation('agent', builtin);
      return builtin;
    }

    if (this.basicConversation.shouldTreatAsCasual(text)) {
      const response = this.basicConversation.getCasualResponse(text);
      this.memory.addConversation('user', text);
      this.memory.addConversation('agent', response);
      return response;
    }

    const sentence = this.brain.parse(text);

    if (sentence.sentence_type === 'question') {
      const answer = this.brain.answerQuestion(text);
      this.memory.addConversation('user', text);
      this.memory.addConversation('agent', answer);
      return answer;
    }

    const result = this.brain.storeSentence(sentence, 0.65);
    if (result.stored) {
      const curiosity = this.brain.computeCuriosity(sentence.subject, sentence.object_);
      this.brain.updateEmotion(curiosity);
      const questions = this.brain.generateQuestions(sentence.subject, sentence.object_, curiosity);
      this.learningQueue.push({ topic: sentence.subject, surprise: curiosity });
      if (this.learningQueue.length > 100) this.learningQueue.shift();

      const relDisplay = {
        'is_a': 'is',
        'has_property': 'is',
        'has': 'has',
        'can': 'can',
        'does': 'does',
        'part_of': 'is part of',
        'causes': 'causes',
        'opposite_of': 'is opposite of',
        'related_to': 'relates to',
        'instance_of': 'is an instance of',
      };
      const verb = relDisplay[sentence.relation_type] || sentence.relation_type.replace(/_/g, ' ');
      const isPlural = sentence.subject.endsWith('s') && !sentence.subject.endsWith('is');
      const verbForm = (verb === 'is' && isPlural) ? 'are' : verb;
      let response = `Got it! I learned that ${sentence.subject} ${verbForm} ${sentence.object_}.`;
      if (result.inferred_count > 0) {
        response += `\n[Inference] I also inferred ${result.inferred_count} new fact(s) through transitive reasoning.`;
      }
      if (questions.length) {
        response += `\n[Curiosity] ${questions[0]}`;
      }
      response += `\n[Status] I now know ${this.memory.getStatistics().total_facts} facts across ${this.memory.getStatistics().total_topics} topics.`;
      response += `\n[Mood] ${this.brain.emotionalState}`;

      this.memory.addConversation('user', text);
      this.memory.addConversation('agent', response);

      if (this.interactionCount % STORAGE_CONFIG.auto_save_interval === 0) {
        this.memory.decayConfidence();
        this.save();
      }
      return response;
    }

    const fallback = `I tried to learn from that but couldn't extract a clear fact. Try teaching me in the format "X is Y" or "X can Y".`;
    this.memory.addConversation('user', text);
    this.memory.addConversation('agent', fallback);
    return fallback;
  }

  getStats() {
    const mem = this.memory.getStatistics();
    const g = this.brain.graph.stats();
    const sem = this.semanticMemory.stats();
    return {
      name: this.name,
      birth_time: this.memory.birthTime,
      total_interactions: this.memory.totalInteractions,
      flat_topics: mem.total_topics,
      flat_facts: mem.total_facts,
      mastered_facts: mem.mastered_facts,
      graph_nodes: g.nodes,
      graph_edges: g.edges,
      graph_inferred: g.inferred_edges,
      semantic_nodes: sem.nodes,
      semantic_edges: sem.edges,
      confidence_avg: sem.avg_confidence,
      contradictions: 0,
      curiosity_asked: 0,
      working_turns: 0,
      episodic_episodes: 0,
      neural_networks: 0,
      reflections: 0,
      current_topic: '',
      mood: this.brain.emotionalState,
      pred_accuracy: 0,
      pred_errors: 0,
      dream_cycles: 0,
      last_pred_error: 0,
      vocab_size: 0,
    };
  }

  getMemorySummary() {
    const stats = this.memory.getStatistics();
    const topics = Object.entries(this.memory.facts).map(([topic, facts]) => {
      const factList = Object.entries(facts).slice(0, 3).map(([f, s]) => `  → ${f} (${Math.round(s.confidence * 100)}%)`);
      return `📚 ${topic}:\n${factList.join('\n')}`;
    });
    return topics.length ? topics.join('\n\n') : 'No memories yet.';
  }

  getMemoryForApi() {
    const result = {};
    for (const [topic, facts] of Object.entries(this.memory.facts)) {
      result[topic] = Object.entries(facts).map(([f, s]) => ({ fact: f, confidence: s.confidence }));
    }
    return result;
  }

  reflect() {
    const thoughts = [
      "I wonder about the connections between the things I've learned.",
      "Every new fact changes how I see the world.",
      "I'm curious about what I don't know yet.",
      "Patterns are emerging in my knowledge graph.",
    ];
    return thoughts[Math.floor(Math.random() * thoughts.length)];
  }

  imagine(topic = null) {
    if (topic) {
      const facts = this.memory.getFactsByTopic(topic);
      if (!facts.length) return `I haven't learned about '${topic}' yet, so I can only imagine it's something fascinating.`;
      return `Imagine if ${topic} could do more than what I've learned. What if ${facts[0][0]} had hidden properties we haven't discovered yet?`;
    }
    return "I imagine a world where every question has a beautiful, verifiable answer.";
  }

  clearMemory() {
    this.memory.clear();
    this.semanticMemory.clear();
    this.brain = new Brain(this.memory);
    this.learningQueue = [];
    this.interactionCount = 0;
    seedAgent(this);
    this.save();
  }

  save() {
    this.memory.save({
      semantic: this.semanticMemory.export(),
      graph: this.brain.graph.export(),
    });
  }

  _loadState() {
    try {
      if (!fs.existsSync(this.memory.dataFile)) return;
      const data = JSON.parse(fs.readFileSync(this.memory.dataFile, 'utf-8'));
      if (data.semantic) this.semanticMemory.importData(data.semantic);
      if (data.graph) this.brain.graph.importGraph(data.graph);
    } catch (e) {
      console.error('State load error:', e.message);
    }
  }
}
