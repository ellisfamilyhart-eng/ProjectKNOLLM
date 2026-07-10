const QUESTION_STARTERS = new Set([
  'what', 'who', 'which', 'where', 'when', 'why', 'how',
  'is', 'are', 'was', 'were', 'do', 'does', 'did', 'can',
  'could', 'would', 'should', 'will', 'has', 'have', 'am',
]);

const NEGATION_WORDS = new Set([
  'not', 'never', 'cannot', 'cant', 'isnt', 'arent', 'wasnt',
  'werent', 'dont', 'doesnt', 'didnt', 'wont', 'wouldnt',
  'couldnt', 'shouldnt', 'hasnt', 'havent',
]);

const ARTICLES = new Set(['a', 'an', 'the']);

const IMPERATIVE_VERBS = new Set([
  'tell', 'describe', 'explain', 'show', 'give', 'list', 'name',
  'define', 'teach', 'help', 'remember', 'forget', 'crawl',
]);

const KNOWN_VERBS = new Set([
  'is', 'are', 'was', 'were', 'am', 'be', 'being', 'been',
  'has', 'have', 'had', 'do', 'does', 'did',
  'can', 'could', 'will', 'would', 'should', 'shall', 'may', 'might', 'must',
  'tell', 'describe', 'explain', 'show', 'give', 'list', 'name', 'define', 'teach',
  'learn', 'know', 'think', 'use', 'make', 'create', 'build', 'run',
  'cause', 'produce', 'require', 'contain', 'include', 'involve',
  'become', 'form', 'consist', 'refer', 'mean', 'represent',
]);

const IS_A_MARKERS = new Set(['is', 'are', 'was', 'were', 'am']);
const PART_OF_MARKERS = new Set(['part', 'component', 'element', 'section', 'member', 'contains', 'includes']);
const CAUSES_MARKERS = new Set(['cause', 'causes', 'produces', 'leads', 'results', 'creates']);
const HAS_MARKERS = new Set(['has', 'have', 'had', 'possesses', 'contains', 'includes']);
const CAPABILITY_VERBS = new Set(['can', 'could', 'may', 'might']);
const ACTION_VERBS = new Set(['do', 'does', 'did', 'use', 'make', 'create', 'build', 'run', 'perform', 'execute']);

const WORD_TYPES = {
  big: 'adjective', small: 'adjective', large: 'adjective', tiny: 'adjective',
  fast: 'adjective', slow: 'adjective', hot: 'adjective', cold: 'adjective',
  good: 'adjective', bad: 'adjective', new: 'adjective', old: 'adjective',
  red: 'adjective', blue: 'adjective', green: 'adjective', yellow: 'adjective',
  important: 'adjective', useful: 'adjective', powerful: 'adjective', simple: 'adjective',
  complex: 'adjective', basic: 'adjective', advanced: 'adjective', digital: 'adjective',
  warm: 'adjective', cool: 'adjective', dark: 'adjective', bright: 'adjective',
  one: 'number', two: 'number', three: 'number', four: 'number', five: 'number',
  six: 'number', seven: 'number', eight: 'number', nine: 'number', ten: 'number',
  first: 'number', second: 'number', third: 'number',
};

const ALIAS_PATTERNS = [
  [/what's/g, 'what is'],
  [/can't/g, 'cannot'],
  [/won't/g, 'will not'],
  [/don't/g, 'do not'],
  [/doesn't/g, 'does not'],
  [/didn't/g, 'did not'],
  [/isn't/g, 'is not'],
  [/aren't/g, 'are not'],
  [/it's/g, 'it is'],
  [/that's/g, 'that is'],
  [/there's/g, 'there is'],
];

const WHAT_IS_RE = /^what\s+(?:is|are)\s+(?:a|an|the\s)?(.+?)[\s?]*$/;

export class Sentence {
  constructor({ subject = 'unknown', verb = 'is', object_ = '', relation_type = 'related_to', modifiers = [], negated = false, sentence_type = 'statement', raw = '' } = {}) {
    this.subject = subject;
    this.verb = verb;
    this.object_ = object_;
    this.relation_type = relation_type;
    this.modifiers = modifiers;
    this.negated = negated;
    this.sentence_type = sentence_type;
    this.raw = raw;
  }
}

function expandAliases(text) {
  let result = text;
  for (const [pattern, replacement] of ALIAS_PATTERNS) {
    result = result.replace(pattern, replacement);
  }
  return result;
}

function clean(text) {
  return text.toLowerCase().replace(/[^a-z0-9\s\-]/g, ' ').replace(/\s+/g, ' ').trim();
}

function stripArticles(words) {
  return words.filter(w => !ARTICLES.has(w));
}

function isNegated(words) {
  return words.some(w => NEGATION_WORDS.has(w));
}

function classifyRelation(verb, obj, negated) {
  if (negated) return 'opposite_of';
  const objWords = obj.split(/\s+/);
  if (IS_A_MARKERS.has(verb)) {
    if (ARTICLES.has(objWords[0])) return 'is_a';
    if (objWords.length === 1) return 'has_property';
    return 'is_a';
  }
  if (PART_OF_MARKERS.has(verb)) return 'part_of';
  if (CAUSES_MARKERS.has(verb)) return 'causes';
  if (CAPABILITY_VERBS.has(verb)) return 'can';
  if (HAS_MARKERS.has(verb)) return 'has';
  if (ACTION_VERBS.has(verb)) return 'does';
  return 'related_to';
}

function extractSVO(words, stype = 'statement') {
  const filtered = stripArticles(words.filter(w => !NEGATION_WORDS.has(w)));
  if (!filtered.length) return new Sentence({ raw: words.join(' '), sentence_type: stype });

  let verbIdx = -1;
  for (let i = 0; i < filtered.length; i++) {
    if (KNOWN_VERBS.has(filtered[i]) && i > 0) { verbIdx = i; break; }
  }

  if (verbIdx === -1) {
    if (filtered.length === 1) return new Sentence({ subject: filtered[0], verb: 'is', object_: '', relation_type: 'has_property', raw: words.join(' '), sentence_type: stype });
    const mid = Math.floor(filtered.length / 2);
    const subj = filtered.slice(0, mid).join(' ');
    const obj = filtered.slice(mid).join(' ');
    return new Sentence({ subject: subj, verb: 'is', object_: obj, relation_type: classifyRelation('is', obj, false), raw: words.join(' '), sentence_type: stype });
  }

  const subj = filtered.slice(0, verbIdx).join(' ');
  const verb = filtered[verbIdx];
  const obj = filtered.slice(verbIdx + 1).join(' ');
  return new Sentence({
    subject: subj, verb, object_: obj,
    relation_type: classifyRelation(verb, obj, false),
    raw: words.join(' '), sentence_type: stype,
  });
}

function extractModifiers(words, subj, obj) {
  const result = [];
  const usedWords = new Set([...subj.split(/\s+/), ...obj.split(/\s+/)]);
  for (const w of words) {
    if (WORD_TYPES[w] === 'adjective' && !usedWords.has(w)) result.push(w);
  }
  return result;
}

function parseStatement(text) {
  const words = clean(text).split(/\s+/).filter(Boolean);
  if (!words.length) return new Sentence({ raw: text });
  const neg = isNegated(words);
  const sentence = extractSVO(words, 'statement');
  sentence.negated = neg;
  if (neg) sentence.relation_type = 'opposite_of';
  sentence.modifiers = extractModifiers(words, sentence.subject, sentence.object_);
  return sentence;
}

function parseQuestion(text) {
  const cleanText = clean(text);
  const words = cleanText.split(/\s+/).filter(Boolean);
  if (!words.length) return new Sentence({ sentence_type: 'question', raw: text });

  const m = text.toLowerCase().match(WHAT_IS_RE);
  if (m) {
    const noun = clean(m[1]);
    return new Sentence({ subject: noun, verb: 'is', object_: noun, relation_type: 'has_property', sentence_type: 'question', raw: text });
  }

  if (QUESTION_STARTERS.has(words[0]) && words[0] !== 'what' && words[0] !== 'who' && words[0] !== 'which') {
    const filtered = stripArticles(words.slice(1).filter(w => !NEGATION_WORDS.has(w)));
    if (filtered.length >= 2) {
      const s = extractSVO(filtered, 'question');
      s.raw = text;
      s.sentence_type = 'question';
      return s;
    }
  }

  const s = extractSVO(words, 'question');
  s.sentence_type = 'question';
  s.raw = text;
  return s;
}

function parseCapability(text) {
  const words = clean(text).split(/\s+/).filter(Boolean);
  if (words.length < 2) return new Sentence({ raw: text, relation_type: 'can' });
  const subj = words[1];
  const rest = stripArticles(words.slice(2).filter(w => !NEGATION_WORDS.has(w)));
  const obj = rest.join(' ');
  const neg = isNegated(words);
  return new Sentence({
    subject: subj, verb: 'can', object_: obj,
    relation_type: neg ? 'opposite_of' : 'can',
    negated: neg, sentence_type: 'capability', raw: text,
  });
}

function parseImperative(text) {
  const words = clean(text).split(/\s+/).filter(Boolean);
  const filler = new Set(['me', 'about', 'us', 'more', 'the', 'a', 'an', 'of', 'to', 'please']);
  const obj = words.slice(1).filter(w => !filler.has(w)).join(' ');
  return new Sentence({
    subject: 'unknown', verb: words[0], object_: obj,
    relation_type: 'related_to', sentence_type: 'statement', raw: text,
  });
}

export function parse(text) {
  if (!text || !text.trim()) return new Sentence({ raw: text || '' });
  const expanded = expandAliases(text.trim().toLowerCase());
  const words = expanded.split(/\s+/).filter(Boolean);
  if (!words.length) return new Sentence({ raw: text });

  if (words[0] === 'can' && words.length >= 2 && !QUESTION_STARTERS.has(words[1])) {
    return parseCapability(expanded);
  }
  if (IMPERATIVE_VERBS.has(words[0])) {
    return parseImperative(expanded);
  }
  if (QUESTION_STARTERS.has(words[0]) || expanded.includes('?')) {
    return parseQuestion(expanded);
  }
  return parseStatement(expanded);
}

export function parseBulk(text) {
  return text.split(/[.!?]\s+/).map(s => s.trim()).filter(Boolean).map(parse);
}

export function classifyWord(word) {
  if (WORD_TYPES[word]) return WORD_TYPES[word];
  if (KNOWN_VERBS.has(word)) return 'verb';
  return 'noun';
}
