import fs from 'fs';
import { STORAGE_CONFIG, LEARNING_CONFIG } from './config.js';

const STAGE_NEW = 'new';
const STAGE_QUESTIONED = 'questioned';
const STAGE_ANSWERED = 'answered';
const STAGE_CONFIRMED = 'confirmed';
const STAGE_MASTERED = 'mastered';

export const MASTERY_CONFIDENCE = 0.85;
export const MASTERY_SUPPORT = 3;
export const CLOSURE_RATIO = 0.90;

function blankFact(confidence = 0.5) {
  const now = new Date().toISOString();
  return {
    confidence,
    support: 1,
    stage: STAGE_NEW,
    questions_asked: [],
    depth: 0,
    added: now,
    last_updated: now,
  };
}

export class MemoryStore {
  constructor(dataFile = null) {
    this.dataFile = dataFile || STORAGE_CONFIG.data_file;
    this.facts = {};
    this.patterns = [];
    this.associations = {};
    this.conversationHistory = [];
    this.learningLog = [];
    this.closedTopics = new Set();
    this.birthTime = new Date().toISOString();
    this.totalInteractions = 0;
    this.lastSaveTime = new Date().toISOString();
    this.load();
  }

  load() {
    try {
      if (!fs.existsSync(this.dataFile)) return;
      const data = JSON.parse(fs.readFileSync(this.dataFile, 'utf-8'));
      this.facts = data.facts || {};
      this.patterns = data.patterns || [];
      this.associations = data.associations || {};
      this.conversationHistory = data.conversation_history || [];
      this.learningLog = data.learning_log || [];
      this.closedTopics = new Set(data.closed_topics || []);
      this.birthTime = data.birth_time || this.birthTime;
      this.totalInteractions = data.total_interactions || 0;
    } catch {}
  }

  save(extra = {}) {
    try {
      const payload = {
        facts: this.facts,
        patterns: this.patterns,
        associations: this.associations,
        conversation_history: this.conversationHistory.slice(-STORAGE_CONFIG.max_conversation_history),
        learning_log: this.learningLog.slice(-STORAGE_CONFIG.max_learning_log),
        closed_topics: [...this.closedTopics],
        birth_time: this.birthTime,
        total_interactions: this.totalInteractions,
        ...extra,
      };
      fs.writeFileSync(this.dataFile, JSON.stringify(payload, null, 2));
      this.lastSaveTime = new Date().toISOString();
    } catch (e) {
      console.error('Memory save failed:', e.message);
    }
  }

  addFact(topic, fact, confidence = 0.5, depth = 0) {
    if (!this.facts[topic]) this.facts[topic] = {};
    const existing = this.facts[topic][fact];
    let state;
    if (!existing) {
      state = blankFact(confidence);
      state.depth = depth;
      this.facts[topic][fact] = state;
    } else {
      const boost = LEARNING_CONFIG.learning_rate * LEARNING_CONFIG.overcompensation;
      existing.confidence = Math.min(1.0, existing.confidence + confidence * boost);
      existing.support = (existing.support || 1) + 1;
      existing.last_updated = new Date().toISOString();
      if (existing.stage === STAGE_NEW || existing.stage === STAGE_QUESTIONED) {
        existing.stage = STAGE_ANSWERED;
      }
      state = existing;
    }
    if (this._qualifiesMastered(state)) state.stage = STAGE_MASTERED;
    this.learningLog.push({
      time: new Date().toISOString(),
      type: 'fact_learned',
      topic, fact,
      confidence: state.confidence,
      stage: state.stage,
    });
    this._maybeCloseTopic(topic);
    return state;
  }

  _qualifiesMastered(state) {
    return state.confidence >= MASTERY_CONFIDENCE && (state.support || 0) >= MASTERY_SUPPORT;
  }

  _maybeCloseTopic(topic) {
    const factStates = Object.values(this.facts[topic] || {});
    if (!factStates.length) return;
    const mastered = factStates.filter(s => s.stage === STAGE_MASTERED).length;
    if (mastered / factStates.length >= CLOSURE_RATIO && factStates.length >= 2) {
      this.closedTopics.add(topic);
    }
  }

  getFactsByTopic(topic) {
    return Object.entries(this.facts[topic] || {})
      .map(([f, s]) => [f, s.confidence])
      .sort((a, b) => b[1] - a[1]);
  }

  getConfidence(topic, fact) {
    const s = this.facts[topic]?.[fact];
    return s ? s.confidence : 0.0;
  }

  isFactMastered(topic, fact) {
    return this.facts[topic]?.[fact]?.stage === STAGE_MASTERED;
  }

  isTopicClosed(topic) {
    return this.closedTopics.has(topic);
  }

  hasAsked(topic, fact, question) {
    const s = this.facts[topic]?.[fact];
    return s ? s.questions_asked?.includes(question) : false;
  }

  recordQuestion(topic, fact, question) {
    const s = this.facts[topic]?.[fact];
    if (s) {
      if (!s.questions_asked) s.questions_asked = [];
      if (!s.questions_asked.includes(question)) s.questions_asked.push(question);
      if (s.stage === STAGE_NEW) s.stage = STAGE_QUESTIONED;
    }
  }

  addAssociation(t1, t2) {
    if (t1 !== t2) {
      if (!this.associations[t1]) this.associations[t1] = [];
      if (!this.associations[t2]) this.associations[t2] = [];
      if (!this.associations[t1].includes(t2)) this.associations[t1].push(t2);
      if (!this.associations[t2].includes(t1)) this.associations[t2].push(t1);
    }
  }

  addConversation(role, content) {
    this.conversationHistory.push({ role, content, time: new Date().toISOString() });
  }

  decayConfidence() {
    for (const topic of Object.keys(this.facts)) {
      for (const fact of Object.keys(this.facts[topic])) {
        const s = this.facts[topic][fact];
        if (s.stage === STAGE_MASTERED) continue;
        s.confidence *= LEARNING_CONFIG.confidence_decay;
        if (s.confidence < 0.05) delete this.facts[topic][fact];
      }
      if (Object.keys(this.facts[topic]).length === 0) {
        delete this.facts[topic];
        this.closedTopics.delete(topic);
      }
    }
  }

  getStatistics() {
    const allFacts = Object.values(this.facts).flatMap(t => Object.values(t));
    const mastered = allFacts.filter(s => s.stage === STAGE_MASTERED).length;
    return {
      total_topics: Object.keys(this.facts).length,
      total_facts: allFacts.length,
      mastered_facts: mastered,
      closed_topics: this.closedTopics.size,
      total_interactions: this.totalInteractions,
      birth_time: this.birthTime,
      associations_count: Math.floor(Object.values(this.associations).reduce((a, v) => a + v.length, 0) / 2),
      last_save: this.lastSaveTime,
    };
  }

  clear() {
    this.facts = {};
    this.associations = {};
    this.learningLog = [];
    this.closedTopics = new Set();
    this.conversationHistory = [];
    this.totalInteractions = 0;
  }
}
