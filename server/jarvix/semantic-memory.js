function nowISO() { return new Date().toISOString(); }

export class SemanticEdge {
  constructor({ subject, relation, object_, confidence = 0.7, source = 'user', added = null } = {}) {
    this.subject = subject;
    this.relation = relation;
    this.object_ = object_;
    this.confidence = confidence;
    this.source = source;
    this.added = added || nowISO();
  }
}

export class SemanticNode {
  constructor({ name, properties = {} } = {}) {
    this.name = name;
    this.properties = properties;
  }
}

export class SemanticMemory {
  constructor() {
    this.nodes = new Map();
    this.edges = [];
    this._edgeIndex = new Map();
  }

  _ensureNode(name) {
    const key = name.toLowerCase().trim();
    if (!this.nodes.has(key)) this.nodes.set(key, new SemanticNode({ name: key }));
    return this.nodes.get(key);
  }

  addEdge(subject, relation, object_, confidence = 0.7, source = 'user') {
    const s = subject.toLowerCase().trim();
    const r = relation.toLowerCase().trim();
    const o = object_.toLowerCase().trim();
    if (!s || !r || !o) return null;

    this._ensureNode(s);
    this._ensureNode(o);

    const idxKey = `${s}|${r}|${o}`;
    const existingIdx = this._edgeIndex.get(idxKey);
    if (existingIdx !== undefined) {
      const edge = this.edges[existingIdx];
      edge.confidence = Math.min(1.0, edge.confidence + 0.05);
      return edge;
    }

    const edge = new SemanticEdge({ subject: s, relation: r, object_: o, confidence, source });
    this.edges.push(edge);
    this._edgeIndex.set(idxKey, this.edges.length - 1);
    return edge;
  }

  edgeConfidence(subject, relation, object_) {
    const key = `${subject.toLowerCase().trim()}|${relation.toLowerCase().trim()}|${object_.toLowerCase().trim()}`;
    const idx = this._edgeIndex.get(key);
    return idx !== undefined ? this.edges[idx].confidence : 0.0;
  }

  outgoing(concept) {
    const c = concept.toLowerCase().trim();
    return this.edges.filter(e => e.subject === c).sort((a, b) => b.confidence - a.confidence);
  }

  incoming(concept) {
    const c = concept.toLowerCase().trim();
    return this.edges.filter(e => e.object_ === c).sort((a, b) => b.confidence - a.confidence);
  }

  decay() {
    for (const edge of this.edges) {
      if (edge.source !== 'seed') edge.confidence *= 0.97;
    }
    this.edges = this.edges.filter(e => e.confidence >= 0.05 || e.source === 'seed');
    this._rebuildIndex();
  }

  _rebuildIndex() {
    this._edgeIndex.clear();
    for (let i = 0; i < this.edges.length; i++) {
      const e = this.edges[i];
      this._edgeIndex.set(`${e.subject}|${e.relation}|${e.object_}`, i);
    }
  }

  stats() {
    const avgConf = this.edges.length ? this.edges.reduce((a, e) => a + e.confidence, 0) / this.edges.length : 0;
    return { nodes: this.nodes.size, edges: this.edges.length, avg_confidence: avgConf };
  }

  export() {
    return {
      nodes: [...this.nodes.keys()],
      edges: this.edges.map(e => ({ subject: e.subject, relation: e.relation, object_: e.object_, confidence: e.confidence, source: e.source })),
    };
  }

  importData(data) {
    if (!data) return;
    if (data.nodes) for (const n of data.nodes) this._ensureNode(n);
    if (data.edges) for (const e of data.edges) this.addEdge(e.subject, e.relation, e.object_, e.confidence, e.source);
  }

  clear() {
    this.nodes.clear();
    this.edges = [];
    this._edgeIndex.clear();
  }
}
