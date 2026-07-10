"""
Jarvix - Dreaming Engine
=========================
Runs at low priority (called during idle / periodic maintenance).

What it does
------------
1. Compress episodic facts -> canonical concepts
   Walk recent episodes, re-extract triples, merge into semantic memory
   with boosted confidence if seen multiple times.

2. Infer reusable rules / patterns
   Find (A is_a B) repeated across many instances -> generate
   "things that are B tend to also have properties of B" rule.

3. Merge aliases / misspellings
   Find pairs of concept nodes with high string similarity ->
   register as synonyms, update edges to point to the canonical form.

4. Strengthen frequently co-occurring associations
   Count how often two topics appear in the same episode window ->
   boost the related_to edge confidence between them.

5. Decay weak / noisy links
   Edges with low confidence AND low times_seen AND old last_used
   are flagged for removal.

6. Update lightweight prototype embeddings in STM
   For each concept, build a bag-of-features vector from its edges
   and store it in working_memory.properties for fast similarity.
"""

from __future__ import annotations
import re
import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class DreamCycle:
    """Record of one dreaming cycle."""
    timestamp:        str   = field(default_factory=lambda: datetime.now().isoformat())
    episodes_scanned: int   = 0
    facts_compressed: int   = 0
    rules_found:      int   = 0
    aliases_merged:   int   = 0
    links_boosted:    int   = 0
    links_decayed:    int   = 0
    prototypes_built: int   = 0
    duration_ms:      int   = 0


class DreamingEngine:
    """
    Background cognitive maintenance.
    Call dream() during idle time.  Each call runs one full cycle.
    """

    # Thresholds
    ALIAS_SIMILARITY_THRESHOLD = 0.80   # string similarity to consider merging
    CO_OCCUR_BOOST_THRESHOLD   = 3      # times co-occurring before boosting
    DECAY_AGE_DAYS             = 7      # edges older than this are candidates
    DECAY_CONF_MAX             = 0.40   # only decay edges below this confidence
    DECAY_TIMES_MAX            = 2      # only decay edges seen this few times
    COMPRESS_MIN_EPISODES      = 2      # need this many episodes to compress

    def __init__(self, semantic_memory, episodic_memory,
                 working_memory, confidence_mgr, canonical_fn=None):
        """
        semantic_memory  : SemanticMemory
        episodic_memory  : EpisodicMemory
        working_memory   : WorkingMemory
        confidence_mgr   : ConfidenceManager
        canonical_fn     : callable(str) -> str  (from canonical.py)
        """
        self.sem        = semantic_memory
        self.epi        = episodic_memory
        self.wm         = working_memory
        self.conf       = confidence_mgr
        self._canonical = canonical_fn or (lambda x: x.lower().strip())

        self.cycle_count   = 0
        self.cycle_history: list[DreamCycle] = []

    # ================================================================
    # PUBLIC
    # ================================================================

    def dream(self, max_episodes: int = 50) -> DreamCycle:
        """Run one full dreaming cycle. Returns a DreamCycle report."""
        import time as _t
        t0    = _t.time()
        cycle = DreamCycle()

        cycle.facts_compressed = self._compress_episodes(max_episodes)
        cycle.episodes_scanned = min(max_episodes, len(self.epi.episodes))
        cycle.rules_found      = self._infer_rules()
        cycle.aliases_merged   = self._merge_aliases()
        cycle.links_boosted    = self._boost_co_occurrences()
        cycle.links_decayed    = self._decay_weak_links()
        cycle.prototypes_built = self._build_prototypes()

        cycle.duration_ms  = int((_t.time() - t0) * 1000)
        self.cycle_count  += 1
        self.cycle_history.append(cycle)
        if len(self.cycle_history) > 100:
            self.cycle_history = self.cycle_history[-100:]

        return cycle

    # ================================================================
    # STEP 1: Compress episodic facts
    # ================================================================

    def _compress_episodes(self, max_episodes: int) -> int:
        """
        Re-extract triples from recent episodes.
        If the same (s, r, o) appears in 2+ episodes, boost its confidence.
        """
        triple_counts: dict = defaultdict(int)
        episodes = self.epi.episodes[-max_episodes:]

        for ep in episodes:
            text = ep.get("user_input", "")
            if not text:
                continue
            # Simple "X is Y" / "X has Y" extraction
            for s, r, o in self._extract_triples_from_text(text):
                cs = self._canonical(s)
                co = self._canonical(o)
                if cs and co and cs != "unknown" and co != "unknown":
                    triple_counts[(cs, r, co)] += 1

        boosted = 0
        for (s, r, o), count in triple_counts.items():
            if count >= self.COMPRESS_MIN_EPISODES:
                existing = self.sem.edge_confidence(s, r, o)
                if existing > 0:
                    # Boost confidence proportional to repetition
                    boost = min(0.05 * count, 0.20)
                    edge  = self.sem.get_edge(s, r, o)
                    if edge:
                        edge.confidence = min(1.0, edge.confidence + boost)
                        boosted += 1
                else:
                    # New compressed fact
                    self.sem.add_edge(s, r, o,
                                      confidence=0.50 + 0.05 * count,
                                      source="dream")
                    boosted += 1
        return boosted

    # ================================================================
    # STEP 2: Infer reusable rules
    # ================================================================

    def _infer_rules(self) -> int:
        """
        Find patterns like: many instances of B share property P
        -> strengthen B has_property P.
        """
        # Group: for each parent B, collect all children and their properties
        parent_props: dict = defaultdict(lambda: defaultdict(int))

        for (s, r, o), edge in self.sem.edges.items():
            if r == "is_a":
                # s is a child of o; collect s's properties
                for child_edge in self.sem.outgoing(s, "has_property"):
                    parent_props[o][child_edge.object_] += 1

        rules_added = 0
        for parent, prop_counts in parent_props.items():
            total_children = sum(
                1 for (s, r, _) in self.sem.edges
                if r == "is_a" and _ == parent
            ) or 1
            for prop, count in prop_counts.items():
                ratio = count / total_children
                if ratio >= 0.6:   # 60%+ of children share this property
                    existing = self.sem.edge_confidence(parent, "has_property", prop)
                    if existing < ratio * 0.8:
                        self.sem.add_edge(parent, "has_property", prop,
                                          confidence=ratio * 0.75,
                                          source="dream_rule",
                                          inferred=True)
                        rules_added += 1
        return rules_added

    # ================================================================
    # STEP 3: Merge aliases / misspellings
    # ================================================================

    def _merge_aliases(self) -> int:
        """
        Find pairs of concept nodes with high string similarity.
        Register as synonyms; redirect edges to canonical form.
        """
        nodes  = list(self.sem.nodes.keys())
        merged = 0

        for i, a in enumerate(nodes):
            for b in nodes[i + 1:]:
                if a == b:
                    continue
                sim = self._string_similarity(a, b)
                if sim >= self.ALIAS_SIMILARITY_THRESHOLD:
                    # Keep shorter/more common as canonical
                    canon = a if len(a) <= len(b) else b
                    alias = b if canon == a else a
                    # Add synonym edge if not already present
                    if not self.sem.get_edge(alias, "synonym_of", canon):
                        self.sem.add_edge(alias, "synonym_of", canon,
                                          confidence=sim,
                                          source="dream_alias",
                                          inferred=True)
                        merged += 1
        return merged

    # ================================================================
    # STEP 4: Boost co-occurring associations
    # ================================================================

    def _boost_co_occurrences(self) -> int:
        """
        Count topic pairs that appear in the same episode window (±2 turns).
        If co-occurrence >= threshold, boost the related_to edge.
        """
        co_counts: dict = defaultdict(int)
        window = 2

        topics_per_ep = []
        for ep in self.epi.episodes[-100:]:
            t = ep.get("metadata", {}).get("topic", "")
            if t:
                topics_per_ep.append(t)

        for i, t1 in enumerate(topics_per_ep):
            start = max(0, i - window)
            end   = min(len(topics_per_ep), i + window + 1)
            for t2 in topics_per_ep[start:end]:
                if t1 != t2:
                    key = tuple(sorted([t1, t2]))
                    co_counts[key] += 1

        boosted = 0
        for (t1, t2), count in co_counts.items():
            if count >= self.CO_OCCUR_BOOST_THRESHOLD:
                existing = self.sem.edge_confidence(t1, "related_to", t2)
                boost    = min(0.03 * count, 0.15)
                if existing > 0:
                    edge = self.sem.get_edge(t1, "related_to", t2)
                    if edge:
                        edge.confidence = min(1.0, edge.confidence + boost)
                        boosted += 1
                else:
                    self.sem.add_edge(t1, "related_to", t2,
                                      confidence=0.30 + boost,
                                      source="dream_cooccur",
                                      inferred=True)
                    boosted += 1
        return boosted

    # ================================================================
    # STEP 5: Decay weak / noisy links
    # ================================================================

    def _decay_weak_links(self) -> int:
        """
        Flag and remove edges that are weak, infrequently seen, and old.
        """
        cutoff = (datetime.now() - timedelta(days=self.DECAY_AGE_DAYS)).isoformat()
        to_remove = []

        for key, edge in list(self.sem.edges.items()):
            if (edge.confidence <= self.DECAY_CONF_MAX and
                    edge.times_seen <= self.DECAY_TIMES_MAX and
                    edge.last_used < cutoff and
                    edge.inferred):   # only remove inferred, never user-taught
                to_remove.append(key)

        for k in to_remove:
            del self.sem.edges[k]

        return len(to_remove)

    # ================================================================
    # STEP 6: Build prototype embeddings
    # ================================================================

    def _build_prototypes(self) -> int:
        """
        For each concept with >= 2 edges, build a bag-of-features vector
        and store it in working_memory state for fast similarity lookup.
        """
        built = 0
        for concept, node in list(self.sem.nodes.items()):
            edges = self.sem.outgoing(concept)
            if len(edges) < 2:
                continue
            # Feature vector: {relation_object: confidence}
            prototype = {}
            for edge in edges:
                feat_key = f"{edge.relation}:{edge.object_}"
                prototype[feat_key] = round(edge.confidence, 3)
            node.properties["_prototype"] = prototype
            built += 1
        return built

    # ================================================================
    # HELPERS
    # ================================================================

    def _extract_triples_from_text(self, text: str) -> list:
        """Quick triple extraction for compression."""
        triples = []
        patterns = [
            (re.compile(r"^(.+?)\s+is\s+an?\s+(.+)$",  re.I), "is_a"),
            (re.compile(r"^(.+?)\s+is\s+(.+)$",        re.I), "has_property"),
            (re.compile(r"^(.+?)\s+has\s+(.+)$",       re.I), "has"),
            (re.compile(r"^(.+?)\s+can\s+(.+)$",       re.I), "can"),
        ]
        for sentence in re.split(r"[.!?\n]+", text):
            s = sentence.strip().rstrip(".")
            for pattern, rel in patterns:
                m = pattern.match(s)
                if m:
                    subj = m.group(1).strip().lower()
                    obj  = m.group(2).strip().lower()
                    # strip articles
                    for art in ("a ", "an ", "the "):
                        if obj.startswith(art):
                            obj = obj[len(art):]
                        if subj.startswith(art):
                            subj = subj[len(art):]
                    if 2 <= len(subj) <= 60 and 2 <= len(obj) <= 80:
                        triples.append((subj, rel, obj))
                    break
        return triples

    def _string_similarity(self, a: str, b: str) -> float:
        """Jaccard similarity on character trigrams."""
        def trigrams(s):
            return {s[i:i+3] for i in range(len(s) - 2)} if len(s) >= 3 else {s}
        ta, tb = trigrams(a), trigrams(b)
        union  = len(ta | tb)
        return len(ta & tb) / union if union else 0.0

    def get_prototype_similarity(self, concept_a: str,
                                  concept_b: str) -> float:
        """
        Cosine-like similarity between two concept prototypes.
        Returns 0.0-1.0.
        """
        pa = self.sem.nodes.get(concept_a, None)
        pb = self.sem.nodes.get(concept_b, None)
        if not pa or not pb:
            return 0.0
        va = pa.properties.get("_prototype", {})
        vb = pb.properties.get("_prototype", {})
        if not va or not vb:
            return 0.0
        keys   = set(va) | set(vb)
        dot    = sum(va.get(k, 0) * vb.get(k, 0) for k in keys)
        norm_a = math.sqrt(sum(v**2 for v in va.values())) or 1.0
        norm_b = math.sqrt(sum(v**2 for v in vb.values())) or 1.0
        return round(dot / (norm_a * norm_b), 3)

    # ================================================================
    # STATS / EXPORT
    # ================================================================

    def stats(self) -> dict:
        if not self.cycle_history:
            return {"cycles": 0}
        last = self.cycle_history[-1]
        return {
            "cycles":           self.cycle_count,
            "last_compressed":  last.facts_compressed,
            "last_rules":       last.rules_found,
            "last_aliases":     last.aliases_merged,
            "last_boosted":     last.links_boosted,
            "last_decayed":     last.links_decayed,
            "last_prototypes":  last.prototypes_built,
            "last_ms":          last.duration_ms,
        }

    def export(self) -> list:
        return [
            {"timestamp": c.timestamp, "compressed": c.facts_compressed,
             "rules": c.rules_found, "aliases": c.aliases_merged,
             "boosted": c.links_boosted, "decayed": c.links_decayed,
             "ms": c.duration_ms}
            for c in self.cycle_history[-20:]
        ]
