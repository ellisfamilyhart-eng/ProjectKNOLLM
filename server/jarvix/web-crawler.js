import * as cheerio from 'cheerio';
import { parse } from './nlp-parser.js';

const DISCARD_TAGS = ['nav', 'script', 'style', 'footer', 'aside', 'form', 'iframe', 'noscript', 'button', 'select', 'option', 'label', 'figure', 'figcaption', 'img', 'svg', 'video', 'audio', 'source', 'track', 'map', 'area'];

const NOISE_PATTERNS = /nav|ad-banner|cookie-notice|infobox|reflist|metadata|sidebar|footer-box|header-box|menu-bar|banner-ad|popup|social-share|share-buttons|comment-section|related-articles|navigation-bar|edit-section|reference-list|citation-needed/i;

const JUNK_PATTERNS = [
  /^(click|buy|download|sign|subscribe|share|follow|like|log|register|join|learn more|read more|see more|view more)/i,
  /^\d+$/,
  /^[^a-z]*$/i,
  /^.{1,15}$/,
  /^.{200,}$/,
  /\b(ipa|pronunciation|phonetic)\b/i,
  /^\[[^\]]*\]$/,
  /^(categories|references|external links|see also|contents|further reading)$/,
  /^citation needed/i,
  /^\d{4}-\d{2}-\d{2}/,
];

const REL_PATTERNS = [
  [/^(.+?)\s+(?:is|are)\s+(?:a|an)\s+(.+)$/i, 'is_a'],
  [/^(.+?)\s+(?:is|are)\s+(.+)$/i, 'has_property'],
  [/^(.+?)\s+has\s+(.+)$/i, 'has'],
  [/^(.+?)\s+have\s+(.+)$/i, 'has'],
  [/^(.+?)\s+can\s+(.+)$/i, 'can'],
  [/^(.+?)\s+causes\s+(.+)$/i, 'causes'],
  [/^(.+?)\s+contains\s+(.+)$/i, 'has'],
  [/^(.+?)\s+includes\s+(.+)$/i, 'has'],
  [/^(.+?)\s+requires\s+(.+)$/i, 'has'],
  [/^(.+?)\s+consists of\s+(.+)$/i, 'part_of'],
  [/^(.+?)\s+is part of\s+(.+)$/i, 'part_of'],
  [/^(.+?)\s+refers to\s+(.+)$/i, 'related_to'],
  [/^(.+?)\s+means\s+(.+)$/i, 'related_to'],
  [/^(.+?)\s+uses\s+(.+)$/i, 'does'],
  [/^(.+?)\s+produces\s+(.+)$/i, 'causes'],
  [/^(.+?)\s+belongs to\s+(.+)$/i, 'part_of'],
  [/^(.+?)\s+was\s+(?:a|an)\s+(.+)$/i, 'is_a'],
];

const MIN_PHRASE_LENGTH = 2;
const MAX_SUBJECT_LENGTH = 60;
const MAX_OBJECT_LENGTH = 120;
const MAX_OBJECT_WORDS = 12;
const DUPLICATE_CONFIDENCE_THRESHOLD = 0.5;
const BASE_TRIPLE_CONFIDENCE = 0.60;
const DEFAULT_USER_AGENT = 'Jarvix-Crawler/3.0';

function cleanPhrase(s) {
  return s.toLowerCase().replace(/[^a-z0-9 '\-]/g, ' ').replace(/\s+/g, ' ').trim().replace(/^(a|an|the)\s+/, '');
}

function splitSentences(text) {
  return text.split(/[.!?]\s+/).map(s => s.trim()).filter(Boolean);
}

function isJunk(sentence) {
  for (const pat of JUNK_PATTERNS) if (pat.test(sentence)) return true;
  const words = sentence.split(/\s+/).filter(w => w.length > 2 && /^[a-z]/i.test(w));
  if (words.length < 3) return true;
  const firstWord = sentence.split(/\s+/)[0];
  if (firstWord.length <= 2 && firstWord.toLowerCase() !== 'i' && firstWord.toLowerCase() !== 'a') return true;
  return false;
}

function extractTriple(sentence) {
  for (const [pattern, rel] of REL_PATTERNS) {
    const m = sentence.match(pattern);
    if (m) {
      let subj = cleanPhrase(m[1]);
      let obj = cleanPhrase(m[2]);
      if (subj.length < MIN_PHRASE_LENGTH || subj.length > MAX_SUBJECT_LENGTH) continue;
      if (obj.length < MIN_PHRASE_LENGTH || obj.length > MAX_OBJECT_LENGTH) continue;
      if (obj.split(/\s+/).length > MAX_OBJECT_WORDS) continue;
      if (PRONOUNS.has(subj.split(/\s+/)[0])) continue;
      if (!subj || !obj) continue;
      return { subject: subj, relation: rel, object: obj };
    }
  }
  return null;
}

const PRONOUNS = new Set(['he', 'she', 'it', 'they', 'this', 'that', 'these', 'those', 'which', 'who', 'what', 'there', 'here']);

function computeQuality(report) {
  const ratio = report.totalSentences > 0 ? report.storedFacts / report.totalSentences : 0;
  if (report.storedFacts === 0) return 'F';
  if (ratio > 0.15) return 'A';
  if (ratio > 0.08) return 'B';
  if (ratio > 0.03) return 'C';
  return 'D';
}

export class WebCrawler {
  constructor(agent, { maxDepth = 1, maxPages = 10, timeoutS = 8, sameDomainOnly = true, requestDelayS = 0.5 } = {}) {
    this.agent = agent;
    this.maxDepth = maxDepth;
    this.maxPages = maxPages;
    this.timeoutS = timeoutS;
    this.sameDomainOnly = sameDomainOnly;
    this.requestDelayS = requestDelayS;
    this._visited = new Set();
    this._lastRequestTime = 0;
  }

  async _fetch(url) {
    const now = Date.now();
    const elapsed = now - this._lastRequestTime;
    const delay = this.requestDelayS * 1000;
    if (elapsed < delay) await new Promise(r => setTimeout(r, delay - elapsed));
    this._lastRequestTime = Date.now();

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutS * 1000);
    try {
      const res = await fetch(url, {
        headers: { 'User-Agent': DEFAULT_USER_AGENT },
        signal: controller.signal,
      });
      const html = await res.text();
      return { html, status: res.status };
    } catch (e) {
      return { html: null, status: 0, error: e.message };
    } finally {
      clearTimeout(timer);
    }
  }

  _parseHtml(html) {
    const $ = cheerio.load(html);
    for (const tag of DISCARD_TAGS) $(tag).remove();
    $('[class]').each((_, el) => {
      const cls = $(el).attr('class') || '';
      const id = $(el).attr('id') || '';
      if (NOISE_PATTERNS.test(cls) || NOISE_PATTERNS.test(id)) $(el).remove();
    });
    const title = $('title').text().trim() || $('h1').first().text().trim() || '';
    const content = $('main').text() || $('article').text() || $('body').text() || '';
    const paragraphs = [];
    $('p, h1, h2, h3, h4, h5, h6, li').each((_, el) => {
      const text = $(el).text().trim();
      if (text) paragraphs.push(text);
    });
    const text = paragraphs.length ? paragraphs.join('\n') : content;
    return { title, text };
  }

  _extractLinks(html, baseUrl, seedDomain) {
    const $ = cheerio.load(html);
    const links = [];
    $('a[href]').each((_, el) => {
      const href = $(el).attr('href');
      if (!href) return;
      try {
        const fullUrl = new URL(href, baseUrl).href;
        if (!fullUrl.startsWith('http://') && !fullUrl.startsWith('https://')) return;
        if (this.sameDomainOnly) {
          const linkDomain = new URL(fullUrl).hostname;
          if (linkDomain !== seedDomain) return;
        }
        if (!links.includes(fullUrl)) links.push(fullUrl);
      } catch {}
    });
    return links.slice(0, 5);
  }

  _processPage(url, seedDomain) {
    const pageStart = Date.now();
    return this._fetch(url).then(({ html, status, error }) => {
      if (error || !html || status >= 400) {
        return {
          url, title: '', wordCount: 0, sentenceCount: 0,
          factsExtracted: 0, factsStored: 0, factsSkipped: 0,
          topTopics: [], error: error || `HTTP ${status}`, fetchTimeMs: Date.now() - pageStart,
        };
      }
      const { title, text } = this._parseHtml(html);
      const sentences = splitSentences(text);
      const cleanSentences = sentences.filter(s => !isJunk(s));
      const wordCount = text.split(/\s+/).filter(Boolean).length;
      let stored = 0, skipped = 0;
      const topics = new Set();

      for (const sentence of cleanSentences.slice(0, 200)) {
        const triple = extractTriple(sentence);
        if (!triple) continue;
        const existingConf = this.agent.semanticMemory.edgeConfidence(triple.subject, triple.relation, triple.object);
        if (existingConf > DUPLICATE_CONFIDENCE_THRESHOLD) { skipped++; continue; }

        this.agent.semanticMemory.addEdge(triple.subject, triple.relation, triple.object, BASE_TRIPLE_CONFIDENCE, false, 'web');
        this.agent.brain.graph.addEdge(triple.subject, triple.relation, triple.object, BASE_TRIPLE_CONFIDENCE, false, 'web');
        this.agent.memory.addFact(triple.subject, `${triple.relation.replace(/_/g, ' ')} ${triple.object}`, BASE_TRIPLE_CONFIDENCE);
        stored++;
        topics.add(triple.subject);
      }

      let links = [];
      if (this.maxDepth > 0) {
        links = this._extractLinks(html, url, seedDomain);
      }

      return {
        url, title, wordCount, sentenceCount: cleanSentences.length,
        factsExtracted: stored + skipped, factsStored: stored, factsSkipped: skipped,
        topTopics: [...topics].slice(0, 5), error: null, fetchTimeMs: Date.now() - pageStart,
        _links: links,
      };
    });
  }

  async crawl(seedUrl) {
    const start = Date.now();
    const factsBefore = Object.values(this.agent.memory.facts).flatMap(t => Object.keys(t)).length;
    let seedDomain;
    try { seedDomain = new URL(seedUrl).hostname; } catch { seedDomain = ''; }

    const report = {
      seedUrl, pagesVisited: 0, pagesFailed: 0, totalWords: 0,
      totalSentences: 0, totalFacts: 0, storedFacts: 0, duplicateFacts: 0,
      topTopics: [], topFacts: [], pageResults: [], knowledgeGain: 0,
      errors: [], elapsedMs: 0,
    };

    const queue = [{ url: seedUrl, depth: 0 }];

    while (queue.length > 0 && report.pagesVisited + report.pagesFailed < this.maxPages) {
      const { url, depth } = queue.shift();
      if (this._visited.has(url)) continue;
      this._visited.add(url);

      const result = await this._processPage(url, seedDomain);
      if (result.error) {
        report.pagesFailed++;
        report.errors.push(`${url}: ${result.error}`);
        report.pageResults.push(result);
        continue;
      }

      report.pagesVisited++;
      report.totalWords += result.wordCount;
      report.totalSentences += result.sentenceCount;
      report.totalFacts += result.factsExtracted;
      report.storedFacts += result.factsStored;
      report.duplicateFacts += result.factsSkipped;
      report.pageResults.push(result);

      if (result._links && depth < this.maxDepth) {
        for (const link of result._links) {
          if (!this._visited.has(link)) queue.push({ url: link, depth: depth + 1 });
        }
      }
    }

    report.elapsedMs = Date.now() - start;
    const factsAfter = Object.values(this.agent.memory.facts).flatMap(t => Object.keys(t)).length;
    report.knowledgeGain = Math.round((factsAfter - factsBefore) / Math.max(factsBefore, 1) * 100);

    const topicCounts = {};
    for (const pr of report.pageResults) {
      for (const t of pr.topTopics || []) topicCounts[t] = (topicCounts[t] || 0) + 1;
    }
    report.topTopics = Object.entries(topicCounts).sort((a, b) => b[1] - a[1]).slice(0, 10).map(([t]) => t);

    const recentEdges = this.agent.semanticMemory.edges.filter(e => e.source === 'web').slice(-20);
    report.topFacts = recentEdges.slice(0, 12).map(e => ({
      subject: e.subject, relation: e.relation, object: e.object_, confidence: e.confidence,
    }));

    return report;
  }

  buildEvaluation(report) {
    return {
      summary: {
        seed_url: report.seedUrl,
        pages_visited: report.pagesVisited,
        pages_failed: report.pagesFailed,
        total_words: report.totalWords,
        total_sentences: report.totalSentences,
        facts_extracted: report.totalFacts,
        facts_stored: report.storedFacts,
        duplicates: report.duplicateFacts,
        knowledge_gain: report.knowledgeGain,
        elapsed_ms: report.elapsedMs,
        quality_score: computeQuality(report),
      },
      top_topics: report.topTopics,
      top_facts: report.topFacts,
      page_results: report.pageResults.map(p => ({
        url: p.url, title: p.title, words: p.wordCount, sentences: p.sentenceCount,
        stored: p.factsStored, skipped: p.factsSkipped, top_topics: p.topTopics || [],
        error: p.error, ms: p.fetchTimeMs,
      })),
      errors: report.errors,
      inference_note: report.storedFacts > 0
        ? `Inferred ${this.agent.brain.graph.stats().inferred_edges} additional facts through transitive reasoning.`
        : '',
    };
  }
}
