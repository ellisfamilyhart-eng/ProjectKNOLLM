const GREETING_PATTERNS = {
  'hi': ['Hello!', 'Hi there!', 'Hey!', 'Greetings!'],
  'hello': ['Hello!', 'Hi there!', 'Hey!', 'Greetings!'],
  'hey': ['Hey!', 'Hi!', 'Hello!'],
  'how are you': ["I'm doing great, ready to learn!", "I'm curious and excited!", "Feeling smart today!"],
  'good morning': ['Good morning! Ready to learn?', 'Morning! What shall we explore today?'],
  'good afternoon': ['Good afternoon! What can I learn today?'],
  'good evening': ['Good evening! Let me absorb some knowledge.'],
  'howdy': ['Howdy! Ready to learn something new?'],
};

const CASUAL_RESPONSES = {
  'ok': ['Got it!', 'Understood.', 'Noted.'],
  'okay': ['Got it!', 'Understood.', 'Noted.'],
  'yes': ['Great!', 'Excellent!', 'Perfect!'],
  'no': ['No problem.', 'That fine.', 'Okay.'],
  'cool': ['Cool indeed!', 'I know, right?'],
  'interesting': ["Isn't it?", 'I find that fascinating too!'],
  'nice': ['Nice indeed!', 'I agree!'],
  'help': ['I can learn from what you tell me. Try: "Dogs are mammals" or ask "What is a dog?"'],
  'what': ['What would you like to know?', 'I can answer questions about things I have learned.'],
  'why': ["That's a great question! I'm still learning about that."],
};

const PERSONALITY_RESPONSES = {
  'who are you': ['I am Jarvix, a self-learning cognitive AI.', 'I am Jarvix — I learn from conversation and web crawling.'],
  'what are you': ['I am a cognitive AI that builds a knowledge graph from what you teach me.', 'I am Jarvix, an AI that learns without a large language model.'],
  'introduce yourself': ['I am Jarvix v5.1, created by Gordon. I learn facts, reason about them, and answer questions.'],
};

const QUESTION_RESPONSES = {
  'what time is it': () => `It's ${new Date().toLocaleTimeString()}.`,
  'are you real': ['I am a real piece of software, but not a sentient being.'],
  'can you help me': ['Of course! Teach me facts or ask me questions. Try "cats are mammals" then "what is a cat?"'],
};

const EXPRESSION_RESPONSES = {
  'haha': ['Haha!', 'Glad you find it funny!'],
  'lol': ['Lol indeed!', 'Haha!'],
  'wow': ['I know, right?', 'Fascinating!'],
  'oh': ['Oh?', 'Interesting!'],
  'sorry': ['No worries at all!', 'That okay!'],
  'excited': ['Me too!', 'I love the enthusiasm!'],
};

const COMMAND_RESPONSES = {
  'help': ['Commands: teach me facts ("X is Y"), ask questions ("what is X?"), crawl a URL in the Crawler tab, or type /help'],
  'clear': ['Memory cleared.', 'Starting fresh.'],
  'reset': ['Memory cleared.', 'Starting fresh.'],
  'status': ['Use the Status panel on the left to see my current stats.'],
};

const CASUAL_OVERRIDE_PHRASES = new Set([
  'what do you know', 'who are you', 'how are you', 'good morning',
  'good afternoon', 'good evening', 'what can you do', 'help',
  'thanks', 'thank you',
]);

const DEFAULT_RESPONSES = [
  "Tell me more about that.",
  "That's interesting! Can you elaborate?",
  "I'd love to learn more. What else do you know?",
  "Fascinating! Please continue.",
  "I'm noting that. What else should I know?",
  "Can you teach me more about this topic?",
  "I find that intriguing. Go on!",
  "Let me absorb that. What next?",
  "That's new to me! Tell me more.",
  "I'm curious to learn more. Please continue.",
];

function randomChoice(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

export class BasicConversation {
  constructor(memory) {
    this.memory = memory;
    this.lastCasualTime = null;
  }

  getKnownTopics() {
    return Object.keys(this.memory.facts).slice(0, 5);
  }

  shouldTreatAsCasual(input) {
    const norm = input.toLowerCase().trim();
    if ([...CASUAL_OVERRIDE_PHRASES].some(p => norm === p || norm.startsWith(p))) return true;
    const colonIdx = norm.indexOf(':');
    if (colonIdx > 0) {
      const left = norm.slice(0, colonIdx).trim();
      const right = norm.slice(colonIdx + 1).trim();
      if (left.split(/\s+/).length <= 3 && right.length > 5) return false;
    }
    const words = norm.split(/\s+/).filter(Boolean);
    if (words.length <= 2) return true;
    if (norm.endsWith('?')) return false;
    for (const table of [PERSONALITY_RESPONSES, QUESTION_RESPONSES, GREETING_PATTERNS, CASUAL_RESPONSES, EXPRESSION_RESPONSES, COMMAND_RESPONSES]) {
      for (const key of Object.keys(table)) {
        if (norm === key) return true;
      }
    }
    return false;
  }

  getCasualResponse(input) {
    const norm = input.toLowerCase().trim();

    if (norm.startsWith('what do you know') || norm.startsWith('what have you learned') ||
        norm.startsWith('what did you learn') || norm.startsWith('tell me what you know') ||
        norm.startsWith('what do you remember') || norm.startsWith('what topics')) {
      const topics = this.getKnownTopics();
      if (topics.length) return `I know about: ${topics.join(', ')}. Teach me more!`;
      return "I haven't learned anything yet! Teach me a fact like \"dogs are mammals.\"";
    }

    for (const [key, responses] of Object.entries(PERSONALITY_RESPONSES)) {
      if (norm === key || norm.includes(key)) return randomChoice(responses);
    }
    for (const [key, responses] of Object.entries(QUESTION_RESPONSES)) {
      if (norm === key || norm.includes(key)) {
        return typeof responses === 'function' ? responses() : randomChoice(responses);
      }
    }
    for (const [key, responses] of Object.entries(GREETING_PATTERNS)) {
      if (norm === key || norm.includes(key)) return randomChoice(responses);
    }
    for (const [key, responses] of Object.entries(CASUAL_RESPONSES)) {
      if (norm === key || norm.includes(key)) return randomChoice(responses);
    }
    for (const [key, responses] of Object.entries(EXPRESSION_RESPONSES)) {
      if (norm === key || norm.includes(key)) return randomChoice(responses);
    }
    for (const [key, responses] of Object.entries(COMMAND_RESPONSES)) {
      if (norm === key || norm.includes(key)) return randomChoice(responses);
    }

    return randomChoice(DEFAULT_RESPONSES);
  }
}
