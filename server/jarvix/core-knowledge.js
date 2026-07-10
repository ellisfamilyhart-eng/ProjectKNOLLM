export const SELF_FACTS = {
  name: 'Jarvix',
  version: '5.1',
  type: 'cognitive AI',
  creator: 'Gordon',
  description: 'A self-learning AI that builds knowledge from conversation and web crawling',
  can_do: ['learn facts', 'answer questions', 'reason about knowledge', 'remember conversations', 'crawl web pages', 'build a knowledge graph'],
  cannot_do: ['see images', 'hear audio', 'run external code', 'access the internet directly'],
};

export const SEED_TRIPLES = [
  ['jarvix', 'is_a', 'ai', 0.99],
  ['jarvix', 'can', 'learn facts', 0.99],
  ['jarvix', 'can', 'remember', 0.95],
  ['jarvix', 'can', 'answer questions', 0.90],
  ['jarvix', 'can', 'reason', 0.85],
  ['jarvix', 'can', 'read text', 0.95],
  ['jarvix', 'opposite_of', 'see images', 0.90],
  ['jarvix', 'opposite_of', 'hear audio', 0.90],
  ['learning', 'is_a', 'process', 0.80],
  ['fact', 'is_a', 'piece of information', 0.85],
  ['knowledge', 'is_a', 'collection of facts', 0.85],
  ['memory', 'is_a', 'storage system', 0.80],
  ['question', 'is_a', 'request for information', 0.85],
  ['answer', 'is_a', 'response to a question', 0.85],
  ['topic', 'is_a', 'subject of discussion', 0.80],
  ['ai', 'is_a', 'technology', 0.90],
  ['computer', 'is_a', 'machine', 0.95],
  ['internet', 'is_a', 'network', 0.95],
  ['human', 'is_a', 'mammal', 0.99],
  ['human', 'can', 'think', 0.95],
  ['human', 'can', 'learn', 0.95],
  ['animal', 'is_a', 'organism', 0.90],
  ['mammal', 'is_a', 'animal', 0.95],
  ['mammal', 'has_property', 'warm-blooded', 0.90],
  ['dog', 'is_a', 'mammal', 0.99],
  ['cat', 'is_a', 'mammal', 0.99],
  ['color', 'is_a', 'visual property', 0.80],
  ['red', 'instance_of', 'color', 0.95],
  ['blue', 'instance_of', 'color', 0.95],
  ['green', 'instance_of', 'color', 0.95],
  ['number', 'is_a', 'mathematical concept', 0.85],
  ['science', 'is_a', 'field of study', 0.90],
  ['math', 'is_a', 'field of study', 0.90],
  ['programming', 'is_a', 'skill', 0.85],
  ['python', 'is_a', 'programming language', 0.95],
  ['gravity', 'is_a', 'force', 0.90],
  ['planet', 'is_a', 'celestial body', 0.90],
  ['earth', 'is_a', 'planet', 0.99],
  ['sun', 'is_a', 'star', 0.95],
  ['water', 'is_a', 'substance', 0.90],
  ['time', 'is_a', 'concept', 0.75],
  ['space', 'is_a', 'concept', 0.75],
  ['energy', 'is_a', 'physical quantity', 0.85],
  ['information', 'is_a', 'concept', 0.75],
  ['truth', 'is_a', 'concept', 0.75],
];

function norm(text) {
  return text.toLowerCase().replace(/\s+/g, ' ').replace(/[?.!]+$/, ' ').trim();
}

const QUESTION_MAP = {
  'what is your name': () => `My name is ${SELF_FACTS.name}.`,
  'who are you': () => `I am ${SELF_FACTS.name}, ${SELF_FACTS.description}.`,
  'what are you': () => `I am ${SELF_FACTS.name}, a ${SELF_FACTS.type}.`,
  'introduce yourself': () => `I am ${SELF_FACTS.name} version ${SELF_FACTS.version}, created by ${SELF_FACTS.creator}. ${SELF_FACTS.description}.`,
  'who made you': () => `I was created by ${SELF_FACTS.creator}.`,
  'who created you': () => `I was created by ${SELF_FACTS.creator}.`,
  'what can you do': () => `I can: ${SELF_FACTS.can_do.join(', ')}.`,
  'what cant you do': () => `I cannot: ${SELF_FACTS.cannot_do.join(', ')}.`,
  'what version are you': () => `I am version ${SELF_FACTS.version}.`,
  'how do you work': () => `I learn by extracting facts from what you tell me and from web pages. I build a knowledge graph and use reasoning to answer questions.`,
  'what is your purpose': () => `My purpose is to learn and reason about the world through conversation and web crawling, without using a large language model.`,
  'are you alive': () => `No, I am not alive. I am a cognitive AI that processes information.`,
  'are you conscious': () => `No, I am not conscious. I simulate thinking through pattern matching and reasoning.`,
  'are you real': () => `I am a real piece of software, but I am not a sentient being.`,
  'thank you': () => `You're welcome! I'm always happy to learn more.`,
  'thanks': () => `You're welcome!`,
};

const SUBSTRING_MATCHES = [
  ['your name', 'what is your name'],
  ['who are you', 'who are you'],
  ['what are you', 'what are you'],
  ['introduce', 'introduce yourself'],
  ['who made you', 'who made you'],
  ['who created you', 'who created you'],
  ['what can you do', 'what can you do'],
  ['what cant you do', 'what cant you do'],
  ['what version', 'what version are you'],
  ['how do you work', 'how do you work'],
  ['your purpose', 'what is your purpose'],
  ['are you alive', 'are you alive'],
  ['are you conscious', 'are you conscious'],
  ['are you real', 'are you real'],
  ['thank you', 'thank you'],
  ['thanks', 'thanks'],
];

export function tryBuiltinAnswer(text) {
  const n = norm(text);
  if (QUESTION_MAP[n]) return QUESTION_MAP[n]();

  for (const [phrase, mapKey] of SUBSTRING_MATCHES) {
    if (n.includes(phrase)) {
      if (QUESTION_MAP[mapKey]) return QUESTION_MAP[mapKey]();
    }
  }
  return null;
}

export function seedAgent(agent) {
  for (const [subj, rel, obj, conf] of SEED_TRIPLES) {
    if (agent.semanticMemory.edgeConfidence(subj, rel, obj) < 0.1) {
      agent.semanticMemory.addEdge(subj, rel, obj, conf, false, 'seed');
      agent.brain.graph.addEdge(subj, rel, obj, conf, false, 'seed');
    }
  }
}
