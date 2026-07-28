"""Jarvix NoLLM - Memory Sorter
Provides active sorting and organization of memories (facts) and knowledge graph.
Can be used to re-rank facts by confidence, importance, stage, and to sort graph
nodes by degree/centrality. Includes a background organizer that periodically
runs sorting and updates memory states.
"""

import threading
import time
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any

from .memory_store import MemoryStore, STAGE_NEW, STAGE_QUESTIONED, STAGE_ANSWERED, STAGE_CONFIRMED, STAGE_MASTERED
from .knowledge_graph import KnowledgeGraph, NodeData, EdgeData
from .config import LEARNING_CONFIG, STORAGE_CONFIG

# ---------------------------------------------------------------------------
# Sorting helpers for memories (facts)
# ---------------------------------------------------------------------------

def sort_facts_by_confidence(mem_store: MemoryStore, topic: Optional[str] = None) -> List[Tuple[str, str, Dict]]:
    """
    Return a list of (topic, fact, state) sorted by confidence descending.
    If topic is provided, only facts under that topic.
    """
    results = []
    topics = [topic] if topic else list(mem_store.facts.keys())
    for t in topics:
        for fact, state in mem_store.facts.get(t, {}).items():
            results.append((t, fact, state))
    results.sort(key=lambda x: x[2].get('confidence', 0.0), reverse=True)
    return results


def sort_facts_by_importance(mem_store: MemoryStore, topic: Optional[str] = None) -> List[Tuple[str, str, Dict]]:
    """
    Return a list of (topic, fact, state) sorted by importance descending.
    """
    results = []
    topics = [topic] if topic else list(mem_store.facts.keys())
    for t in topics:
        for fact, state in mem_store.facts.get(t, {}).items():
            results.append((t, fact, state))
    results.sort(key=lambda x: x[2].get('importance', 0.5), reverse=True)
    return results


def sort_facts_by_stage(mem_store: MemoryStore, topic: Optional[str] = None) -> List[Tuple[str, str, Dict]]:
    """
    Return a list of (topic, fact, state) sorted by stage progression:
    mastered > confirmed > answered > questioned > new.
    """
    stage_order = {
        STAGE_MASTERED: 5,
        STAGE_CONFIRMED: 4,
        STAGE_ANSWERED: 3,
        STAGE_QUESTIONED: 2,
        STAGE_NEW: 1,
    }
    results = []
    topics = [topic] if topic else list(mem_store.facts.keys())
    for t in topics:
        for fact, state in mem_store.facts.get(t, {}).items():
            results.append((t, fact, state))
    results.sort(key=lambda x: stage_order.get(x[2].get('stage', STAGE_NEW), 0), reverse=True)
    return results


def sort_facts_by_support(mem_store: MemoryStore, topic: Optional[str] = None) -> List[Tuple[str, str, Dict]]:
    """
    Return a list of (topic, fact, state) sorted by support count descending.
    """
    results = []
    topics = [topic] if topic else list(mem_store.facts.keys())
    for t in topics:
        for fact, state in mem_store.facts.get(t, {}).items():
            results.append((t, fact, state))
    results.sort(key=lambda x: x[2].get('support', 0), reverse=True)
    return results


# ---------------------------------------------------------------------------
# Sorting helpers for knowledge graph
# ---------------------------------------------------------------------------

def sort_nodes_by_degree(kg: KnowledgeGraph, descending: bool = True) -> List[Tuple[str, int]]:
    """
    Return list of (node_name, degree) sorted by degree (in+out edges).
    """
    degrees = []
    for name in kg.nodes:
        out_len = len([e for (s, r, o) in kg.edges if s == name])
        in_len = len([e for (s, r, o) in kg.edges if o == name])
        degree = out_len + in_len
        degrees.append((name, degree))
    degrees.sort(key=lambda x: x[1], reverse=descending)
    return degrees


def sort_nodes_by_centrality(kg: KnowledgeGraph, descending: bool = True) -> List[Tuple[str, float]]:
    """
    Simple degree centrality: degree / (max possible degree).
    For directed graph, max possible = (N-1)*2? We'll just use degree normalized by max degree.
    """
    nodes = list(kg.nodes.keys())
    N = len(nodes)
    if N == 0:
        return []
    max_possible = (N - 1) * 2  # each node could connect to all others both ways
    centrality = []
    for name in nodes:
        out_len = len([e for (s, r, o) in kg.edges if s == name])
        in_len = len([e for (s, r, o) in kg.edges if o == name])
        degree = out_len + in_len
        cent = degree / max_possible if max_possible > 0 else 0.0
        centrality.append((name, cent))
    centrality.sort(key=lambda x: x[1], reverse=descending)
    return centrality


def sort_edges_by_confidence(kg: KnowledgeGraph, descending: bool = True) -> List[Tuple[Tuple[str, str, str], float]]:
    """
    Return list of ((subject, relation, object), confidence) sorted by confidence.
    """
    edges_conf = [((s, r, o), data.confidence) for (s, r, o), data in kg.edges.items()]
    edges_conf.sort(key=lambda x: x[1], reverse=descending)
    return edges_conf


# ---------------------------------------------------------------------------
# Active organization (background thread)
# ---------------------------------------------------------------------------

class MemoryOrganizer:
    """
    Background organizer that periodically sorts memories and graph,
    adjusts importance, consolidates facts, and prunes low-confidence items.
    """

    def __init__(self, mem_store: MemoryStore, kg: KnowledgeGraph,
                 interval_seconds: int = 30):
        self.mem_store = mem_store
        self.kg = kg
        self.interval = interval_seconds
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            print("[MemoryOrganizer] Started background organizer.")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
            print("[MemoryOrganizer] Stopped.")

    def _run(self):
        while not self._stop_event.is_set():
            try:
                self._organize_cycle()
            except Exception as e:
                print(f"[MemoryOrganizer] Error during organization: {e}")
            # Sleep in small increments to check stop event promptly
            for _ in range(self.interval):
                if self._stop_event.is_set():
                    break
                time.sleep(1)

    def _organize_cycle(self):
        """
        One cycle of organization:
        1. Sort facts by confidence and boost importance of high-confidence facts.
        2. Identify low-confidence, low-support facts for possible decay.
        3. Sort graph nodes by degree and maybe create associations for highly connected nodes.
        4. Optionally consolidate facts (mark as consolidated).
        """
        print("[MemoryOrganizer] Starting organization cycle...")

        # 1. Boost importance for high-confidence facts (non-mastered)
        high_conf_threshold = 0.8
        for topic, facts in self.mem_store.facts.items():
            for fact, state in facts.items():
                if state.get('stage') == STAGE_MASTERED:
                    continue
                conf = state.get('confidence', 0.0)
                if conf >= high_conf_threshold:
                    # increase importance slightly, cap at 1.0
                    new_imp = min(1.0, state.get('importance', 0.5) + 0.02)
                    if new_imp != state.get('importance', 0.5):
                        state['importance'] = new_imp
                        state['last_updated'] = datetime.now().isoformat()
                        # Optionally log
                        # print(f"[MemoryOrganizer] Increased importance of {topic}::{fact} to {new_imp}")

        # 2. Prune very low confidence, low support facts (non-mastered)
        conf_decay_threshold = 0.05
        support_threshold = 1
        for topic in list(self.mem_store.facts.keys()):
            for fact in list(self.mem_store.facts[topic].keys()):
                state = self.mem_store.facts[topic][fact]
                if state.get('stage') == STAGE_MASTERED:
                    continue
                if (state.get('confidence', 0.0) < conf_decay_threshold and
                        state.get('support', 0) <= support_threshold):
                    # Remove fact
                    del self.mem_store.facts[topic][fact]
                    # Optionally log
                    # print(f"[MemoryOrganizer] Pruned low-confidence fact {topic}::{fact}")
            # Remove empty topics
            if not self.mem_store.facts[topic]:
                del self.mem_store.facts[topic]

        # 3. Graph organization: add RELATED edges for highly connected node pairs
        # For each node, look at top 2 neighbors by edge confidence and ensure a RELATED edge exists.
        for node in self.kg.nodes:
            outgoing = self.kg.get_outgoing(node)
            # outgoing is list of (relation, obj, confidence) sorted by confidence
            top_neighbors = [obj for (rel, obj, conf) in outgoing[:2] if conf > 0.5]
            for nb in top_neighbors:
                if not self.kg.has_edge(node, 'related_to', nb):
                    self.kg.add_edge(node, 'related_to', nb, confidence=0.3, inferred=True, source='memory_organizer')
                if not self.kg.has_edge(nb, 'related_to', node):
                    self.kg.add_edge(nb, 'related_to', node, confidence=0.3, inferred=True, source='memory_organizer')

        # 4. Mark some high-confidence facts as consolidated (if not already)
        for topic, facts in self.mem_store.facts.items():
            for fact, state in facts.items():
                if state.get('confidence', 0.0) >= 0.9 and state.get('support', 0) >= 3:
                    if not state.get('consolidated', False):
                        state['consolidated'] = True
                        state['last_updated'] = datetime.now().isoformat()
                        # print(f"[MemoryOrganizer] Marked {topic}::{fact} as consolidated")

        # Save changes
        self.mem_store.save()
        print("[MemoryOrganizer] Organization cycle completed.")


# ---------------------------------------------------------------------------
# Convenience function to start organizer from external code
# ---------------------------------------------------------------------------

def start_background_organizer(mem_store: MemoryStore, kg: KnowledgeGraph,
                               interval_seconds: int = 30) -> MemoryOrganizer:
    """
    Creates and starts a MemoryOrganizer background thread.
    Returns the organizer instance so caller can stop it later if needed.
    """
    organizer = MemoryOrganizer(mem_store, kg, interval_seconds)
    organizer.start()
    return organizer


# ---------------------------------------------------------------------------
# Example usage (if run as script)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Demo: create dummy store and graph, run organizer briefly
    from .memory_store import MemoryStore
    from .knowledge_graph import KnowledgeGraph

    mem = MemoryStore(data_file="demo_memory.json")
    kg = KnowledgeGraph()

    # Add some dummy facts
    mem.add_fact("animals", "dogs bark", confidence=0.9)
    mem.add_fact("animals", "cats meow", confidence=0.7)
    mem.add_fact("plants", "photosynthesis", confidence=0.8)

    # Add some dummy graph edges
    kg.add_edge("dog", "is_a", "animal")
    kg.add_edge("cat", "is_a", "animal")
    kg.add_edge("dog", "related_to", "cat", confidence=0.4)

    print("=== Facts sorted by confidence ===")
    for t, f, s in sort_facts_by_confidence(mem):
        print(f"{t}::{f} -> conf={s.get('confidence')}, importance={s.get('importance')}")

    print("\n=== Nodes sorted by degree ===")
    for name, deg in sort_nodes_by_degree(kg):
        print(f"{name}: degree={deg}")

    # Start organizer for 5 seconds then stop
    organizer = start_background_organizer(mem, kg, interval_seconds=5)
    print("\nOrganizer running for 5 seconds...")
    time.sleep(6)
    organizer.stop()
    print("Demo finished.")