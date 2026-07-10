import { parse } from './nlp-parser.js';
import { KnowledgeGraph, R_IS_A, R_HAS_PROP, R_CAN, R_RELATED, SELF } from './knowledge-graph.js';
import { MASTERY_CONFIDENCE, MASTERY_SUPPORT } from './memory-store.js';

const CURIOSITY_THRESHOLD = 0.25;
const MAX_REASONING_DEPTH = 2;

export class Brain {
  constructor(memory) {
    this.memory = memory;
    this.graph = new KnowledgeGraph();
    this.emotionalState = 'curious';
    this._depthCounter = {};
  }

  parse(text) {
    return parse(text);
  }

  storeSentence(sentence, confidence = 0.65) {
    if (sentence.subject === 'unknown' || !sentence.object_ || sentence.subject === sentence.object_) {
      return { stored: false };
    }
    const edge = this.graph.addEdge(
      sentence.subject, sentence.relation_type, sentence.object_,
      confidence, false, 'user'
    );
    const factText = sentence.relation_type === 'is_a' || sentence.relation_type === 'has_property'
      ? sentence.object_
      : `${sentence.relation_type} ${sentence.object_}`;
    this.memory.addFact(sentence.subject, factText, confidence);

    const inferred = this._inferNewFacts(sentence);
    return {
      stored: true,
      subject: sentence.subject,
      relation: sentence.relation_type,
      object: sentence.object_,
      confidence,
      inferred_count: inferred.length,
      new_inferences: inferred,
    };
  }

  _inferNewFacts(sentence) {
    const inferred = [];
    if (sentence.relation_type === 'is_a') {
      const parents = this.graph.getParents(sentence.object_);
      for (const [obj, conf] of parents) {
        const newConf = conf * 0.85;
        if (!this.graph.hasEdge(sentence.subject, 'is_a', obj)) {
          this.graph.addEdge(sentence.subject, 'is_a', obj, newConf, true, 'inference');
          inferred.push({ subject: sentence.subject, relation: 'is_a', object: obj, confidence: newConf });
        }
      }
    }
    return inferred;
  }

  answerQuestion(text) {
    const sentence = this.parse(text);
    if (sentence.subject === 'unknown' || !sentence.subject) {
      return "I'm not sure what you're asking about. Could you rephrase?";
    }

    const facts = this.graph.allFactsAbout(sentence.subject);
    if (!facts.length) {
      const parents = this.graph.getParents(sentence.subject);
      if (parents.length) {
        const [rel, obj, conf] = parents[0];
        return `${sentence.subject} is ${obj}. (confidence: ${Math.round(conf * 100)}%)`;
      }
      return `I don't know about "${sentence.subject}" yet. Could you teach me?`;
    }

    if (sentence.sentence_type === 'question') {
      const m = text.toLowerCase().match(/^what\s+(?:is|are)\s+(?:a|an|the\s)?(.+?)[\s?]*$/);
      if (m) {
        const concept = m[1].trim();
        const is_a = facts.filter(([r]) => r === 'is_a');
        if (is_a.length) {
          return `${concept} is ${is_a[0][1]}.`;
        }
        const props = facts.filter(([r]) => r === 'has_property');
        if (props.length) {
          return `${concept} has the property of being ${props[0][1]}.`;
        }
      }
    }

    const lines = facts.slice(0, 8).map(([rel, obj, conf]) => {
      return `  ${sentence.subject} ${rel.replace(/_/g, ' ')} ${obj} (${Math.round(conf * 100)}%)`;
    });
    return `Here's what I know about ${sentence.subject}:\n${lines.join('\n')}`;
  }

  describe(concept) {
    const facts = this.graph.allFactsAbout(concept);
    if (!facts.length) return `I don't know about "${concept}" yet.`;
    const lines = facts.slice(0, 10).map(([rel, obj, conf]) => {
      return `  ${concept} ${rel.replace(/_/g, ' ')} ${obj} (${Math.round(conf * 100)}%)`;
    });
    return `What I know about ${concept}:\n${lines.join('\n')}`;
  }

  isContradiction(topic, newFact) {
    const existing = this.memory.getFactsByTopic(topic);
    for (const [fact, conf] of existing) {
      if (conf > 0.6) {
        const words1 = new Set(newFact.toLowerCase().split(/\s+/));
        const words2 = new Set(fact.toLowerCase().split(/\s+/));
        const intersection = [...words1].filter(w => words2.has(w)).length;
        const union = new Set([...words1, ...words2]).size;
        const similarity = intersection / union;
        if (similarity < 0.30 && similarity > 0) {
          return [true, conf * (1 - similarity)];
        }
      }
    }
    return [false, 0];
  }

  computeCuriosity(topic, newFact) {
    const facts = this.memory.getFactsByTopic(topic);
    if (!facts.length) return 1.0;
    const [isContr, conflictDeg] = this.isContradiction(topic, newFact);
    const avgSupport = facts.reduce((a, [, c]) => a + c, 0) / facts.length;
    const supportSat = Math.min(1, avgSupport / MASTERY_SUPPORT);
    if (isContr) return Math.min(1, conflictDeg * (1 - avgSupport));
    const predConf = facts[0][1];
    return Math.max(0, (1 - predConf) * (1 - supportSat * 0.7));
  }

  generateQuestions(topic, newFact, curiosity, depth = 0) {
    if (curiosity < CURIOSITY_THRESHOLD) return [];
    if (depth >= MAX_REASONING_DEPTH) return [];
    if (this.memory.isTopicClosed(topic)) return [];

    const candidates = [];
    const [isContr] = this.isContradiction(topic, newFact);
    if (isContr) {
      candidates.push(`Wait, I thought something different about ${topic}. Can you clarify?`);
    } else {
      candidates.push(`Can you give me an example of ${topic}?`);
      candidates.push(`Why is ${newFact} important?`);
      candidates.push(`How does ${topic} relate to other things you know?`);
    }

    for (const q of candidates) {
      if (!this.memory.hasAsked(topic, newFact, q)) {
        this.memory.recordQuestion(topic, newFact, q);
        return [q];
      }
    }
    return [];
  }

  updateEmotion(curiosity) {
    if (curiosity > 0.7) this.emotionalState = 'excited';
    else if (curiosity > 0.25) this.emotionalState = 'curious';
    else if (curiosity > 0.05) this.emotionalState = 'thinking';
    else this.emotionalState = 'satisfied';
  }

  generateAutonomousThought(learningQueue) {
    if (!learningQueue || !learningQueue.length) return null;
    const top = learningQueue.reduce((a, b) => (a.surprise || 0) > (b.surprise || 0) ? a : b);
    return `I was surprised to learn about ${top.topic || 'something new'}. I wonder what else is connected to it.`;
  }
}
