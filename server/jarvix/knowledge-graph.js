const SELF = 'jarvix';

const R_IS_A = 'is_a';
const R_HAS_PROP = 'has_property';
const R_HAS = 'has';
const R_CAN = 'can';
const R_DOES = 'does';
const R_PART_OF = 'part_of';
const R_CAUSES = 'causes';
const R_OPPOSITE = 'opposite_of';
const R_RELATED = 'related_to';
const R_INSTANCE_OF = 'instance_of';

const TRANSITIVE_RELATIONS = new Set([R_IS_A, R_PART_OF, R_INSTANCE_OF]);

function edgeKey(s, r, o) {
  return `${s}|${r}|${o}`;
}

class EdgeData {
  constructor({ confidence = 0.7, support = 1, inferred = false, source = 'user', added = null } = {}) {
    this.confidence = confidence;
    this.support = support;
    this.inferred = inferred;
    this.source = source;
    this.added = added || new Date().toISOString();
  }
  reinforce(boost = 0.1) {
    this.support += 1;
    this.confidence = Math.min(1.0, this.confidence + boost);
  }
}

class NodeData {
  constructor({ name, node_type = 'concept', properties = {}, aliases = [] } = {}) {
    this.name = name;
    this.node_type = node_type;
    this.properties = properties;
    this.aliases = aliases;
  }
}

const SEED_CAPABILITIES = [
  ['read text', 0.95],
  ['learn facts', 0.99],
  ['reason', 0.85],
  ['answer questions', 0.90],
  ['remember', 0.92],
  ['crawl web pages', 0.80],
];

const SEED_CANNOT = [
  ['see images', 0.90],
  ['hear audio', 0.90],
  ['access the internet directly', 0.95],
  ['run external code', 0.95],
];

export class KnowledgeGraph {
  constructor() {
    this.nodes = new Map();
    this.edges = new Map();
    this._seedSelf();
  }

  _seedSelf() {
    this._ensureNode(SELF, 'self');
    for (const [action, conf] of SEED_CAPABILITIES) {
      this._ensureNode(action);
      this.edges.set(edgeKey(SELF, R_CAN, action), new EdgeData({ confidence: conf, source: 'seed' }));
    }
    for (const [action, conf] of SEED_CANNOT) {
      this._ensureNode(action);
      this.edges.set(edgeKey(SELF, R_OPPOSITE, action), new EdgeData({ confidence: conf, source: 'seed' }));
    }
  }

  _ensureNode(name, type = 'concept') {
    const key = name.toLowerCase().trim();
    if (!this.nodes.has(key)) this.nodes.set(key, new NodeData({ name: key, node_type: type }));
    return this.nodes.get(key);
  }

  addEdge(subj, rel, obj, confidence = 0.7, inferred = false, source = 'user') {
    const s = subj.toLowerCase().trim();
    const r = rel.toLowerCase().trim();
    const o = obj.toLowerCase().trim();
    if (!s || !r || !o || s === 'unknown' || o === 'unknown') return null;
    this._ensureNode(s);
    this._ensureNode(o);
    const key = edgeKey(s, r, o);
    const existing = this.edges.get(key);
    if (existing) {
      existing.reinforce(0.05);
      return existing;
    }
    const edge = new EdgeData({ confidence, inferred, source });
    this.edges.set(key, edge);
    return edge;
  }

  edgeConfidence(subj, rel, obj) {
    const e = this.edges.get(edgeKey(subj.toLowerCase().trim(), rel.toLowerCase().trim(), obj.toLowerCase().trim()));
    return e ? e.confidence : 0.0;
  }

  hasEdge(subj, rel, obj) {
    return this.edges.has(edgeKey(subj.toLowerCase().trim(), rel.toLowerCase().trim(), obj.toLowerCase().trim()));
  }

  getOutgoing(subj, rel = null) {
    const s = subj.toLowerCase().trim();
    const results = [];
    for (const [key, data] of this.edges) {
      const [ekS, ekR, ekO] = key.split('|');
      if (ekS === s && (!rel || ekR === rel)) {
        results.push([ekR, ekO, data.confidence]);
      }
    }
    return results.sort((a, b) => b[2] - a[2]);
  }

  getIncoming(obj, rel = null) {
    const o = obj.toLowerCase().trim();
    const results = [];
    for (const [key, data] of this.edges) {
      const [ekS, ekR, ekO] = key.split('|');
      if (ekO === o && (!rel || ekR === rel)) {
        results.push([ekS, ekR, data.confidence]);
      }
    }
    return results.sort((a, b) => b[2] - a[2]);
  }

  neighbours(concept) {
    const c = concept.toLowerCase().trim();
    const result = new Set();
    for (const [key] of this.edges) {
      const [s, , o] = key.split('|');
      if (s === c) result.add(o);
      if (o === c) result.add(s);
    }
    return [...result];
  }

  allFactsAbout(concept) {
    return this.getOutgoing(concept);
  }

  getParents(concept) {
    return this.getOutgoing(concept, R_IS_A)
      .concat(this.getOutgoing(concept, R_INSTANCE_OF))
      .concat(this.getOutgoing(concept, R_PART_OF));
  }

  getChildren(concept) {
    return this.getIncoming(concept, R_IS_A).concat(this.getIncoming(concept, R_INSTANCE_OF));
  }

  getCapabilities(concept) {
    return this.getOutgoing(concept, R_CAN);
  }

  getProperties(concept) {
    return this.getOutgoing(concept, R_HAS_PROP);
  }

  selfCan(action) {
    const a = action.toLowerCase().trim();
    const direct = this.edges.get(edgeKey(SELF, R_CAN, a));
    if (direct) return direct.confidence;
    for (const [key, data] of this.edges) {
      const [s, r, o] = key.split('|');
      if (s === SELF && r === R_CAN && o.includes(a)) return data.confidence;
    }
    return null;
  }

  selfCannot(action) {
    const a = action.toLowerCase().trim();
    const direct = this.edges.get(edgeKey(SELF, R_OPPOSITE, a));
    if (direct) return direct.confidence;
    for (const [key, data] of this.edges) {
      const [s, r, o] = key.split('|');
      if (s === SELF && r === R_OPPOSITE && o.includes(a)) return data.confidence;
    }
    return null;
  }

  stats() {
    let inferred = 0;
    for (const d of this.edges.values()) if (d.inferred) inferred++;
    return {
      nodes: this.nodes.size,
      edges: this.edges.size,
      inferred_edges: inferred,
      user_edges: this.edges.size - inferred,
    };
  }

  export() {
    return {
      nodes: Object.fromEntries(
        [...this.nodes.entries()].map(([k, v]) => [k, { node_type: v.node_type, properties: v.properties, aliases: v.aliases }])
      ),
      edges: [...this.edges.entries()].map(([key, d]) => {
        const [s, r, o] = key.split('|');
        return { subject: s, relation: r, object: o, confidence: d.confidence, support: d.support, inferred: d.inferred, source: d.source };
      }),
    };
  }

  importGraph(data) {
    if (data.nodes) {
      for (const [name, nd] of Object.entries(data.nodes)) {
        this.nodes.set(name, new NodeData({ name, node_type: nd.node_type, properties: nd.properties || {}, aliases: nd.aliases || [] }));
      }
    }
    if (data.edges) {
      for (const e of data.edges) {
        this.addEdge(e.subject, e.relation, e.object, e.confidence, e.inferred || false, e.source || 'user');
      }
    }
  }
}

export {
  SELF, R_IS_A, R_HAS_PROP, R_HAS, R_CAN, R_DOES,
  R_PART_OF, R_CAUSES, R_OPPOSITE, R_RELATED, R_INSTANCE_OF,
  TRANSITIVE_RELATIONS, EdgeData, NodeData,
};
