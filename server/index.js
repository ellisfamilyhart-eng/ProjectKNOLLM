import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';
import { Jarvix } from './jarvix/agent.js';
import { WebCrawler } from './jarvix/web-crawler.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, '..', 'data');
const DIST_DIR = path.join(__dirname, '..', 'dist');

if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });

const app = express();
app.use(cors());
app.use(express.json({ limit: '10mb' }));

let agent;
try {
  agent = new Jarvix(path.join(DATA_DIR, 'jarvix_v2_memory.json'));
  console.log('✓ Jarvix agent initialized');
} catch (e) {
  console.error('✗ Jarvix init failed:', e.message);
  agent = null;
}

app.get('/api/health', (req, res) => {
  res.json({
    status: agent ? 'ok' : 'degraded',
    service: 'jarvix-v2',
    version: '5.1.0',
    jarvix_available: !!agent,
    message: agent ? 'Jarvix is fully operational' : 'Jarvix not loaded',
  });
});

app.post('/api/chat', (req, res) => {
  if (!agent) return res.status(503).json({ error: 'Jarvix not available' });
  try {
    const msg = (req.body?.message || '').trim();
    if (!msg) return res.status(400).json({ error: 'Empty message' });
    const response = agent.processInput(msg);
    res.json({ success: true, response, mood: agent.brain.emotionalState });
  } catch (e) {
    console.error('Chat error:', e);
    res.status(500).json({ error: e.message });
  }
});

app.get('/api/stats', (req, res) => {
  if (!agent) return res.json({ success: true, stats: { total_interactions: 0, topics_known: 0, total_facts: 0, mood: 'curious' } });
  try {
    res.json({ success: true, stats: agent.getStats() });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.get('/api/memory', (req, res) => {
  if (!agent) return res.json({ success: true, memory: {}, total_topics: 0, total_facts: 0 });
  try {
    const memory = agent.getMemoryForApi();
    const stats = agent.memory.getStatistics();
    res.json({ success: true, memory, total_topics: stats.total_topics, total_facts: stats.total_facts });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.get('/api/thoughts', (req, res) => {
  if (!agent) return res.json({ success: true, thought: 'I have nothing to contemplate right now...' });
  res.json({ success: true, thought: agent.reflect() });
});

app.post('/api/forget', (req, res) => {
  if (!agent) return res.json({ success: true, message: 'All memories erased.' });
  try {
    agent.clearMemory();
    res.json({ success: true, message: 'All memories erased.' });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.get('/api/imagine', (req, res) => {
  if (!agent) return res.json({ success: true, imagination: 'Imagination unavailable' });
  res.json({ success: true, imagination: agent.imagine() });
});

app.get('/api/graph', (req, res) => {
  if (!agent) return res.json({ success: true, nodes: [], edges: [], stats: { nodes: 0, edges: 0, inferred: 0 } });
  try {
    const graph = agent.brain.graph;
    res.json({
      success: true,
      nodes: [...graph.nodes.keys()],
      edges: [...graph.edges.entries()].map(([key, d]) => {
        const [s, r, o] = key.split('|');
        return { subject: s, relation: r, object: o, confidence: d.confidence, inferred: d.inferred };
      }),
      stats: graph.stats(),
    });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.post('/api/crawl', async (req, res) => {
  if (!agent) return res.status(503).json({ success: false, error: 'Web crawler requires Jarvix.' });
  try {
    const url = (req.body?.url || '').trim();
    const depth = parseInt(req.body?.depth ?? 1);
    const maxPages = parseInt(req.body?.max_pages ?? 8);

    if (!url) return res.status(400).json({ success: false, error: 'No URL provided.' });
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      return res.status(400).json({ success: false, error: 'URL must start with http:// or https://' });
    }

    const crawler = new WebCrawler(agent, { maxDepth: depth, maxPages, timeoutS: 10, sameDomainOnly: true, requestDelayS: 0.3 });
    const report = await crawler.crawl(url);
    const evaluation = crawler.buildEvaluation(report);
    agent.save();
    res.json({ success: true, evaluation });
  } catch (e) {
    console.error('Crawl error:', e);
    res.status(500).json({ success: false, error: e.message });
  }
});

if (fs.existsSync(DIST_DIR)) {
  app.use(express.static(DIST_DIR));
  app.get('*', (req, res) => {
    res.sendFile(path.join(DIST_DIR, 'index.html'));
  });
}

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Jarvix server running on port ${PORT}`);
});
