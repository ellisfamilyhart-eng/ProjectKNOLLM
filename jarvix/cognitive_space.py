import math
import time
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field


# =====================================================================
# 1. DATA STRUCTURES FOR THE 3D COGNITIVE SPACE
# =====================================================================

@dataclass
class Vector3D:
    """Coordinates in the 3D Cognitive Field.
    
    X = Semantic / Concept Axis (-1.0 Abstract <-> +1.0 Concrete)
    Y = Context / Experience Axis (-1.0 Emotional <-> +1.0 Factual)
    Z = Temporal Axis (-1.0 Far Past <-> 0.0 Present <-> +1.0 Future)
    """
    x: float
    y: float
    z: float

    def distance_to(self, other: "Vector3D") -> float:
        """Euclidean distance in 3D cognitive space."""
        return math.sqrt(
            (self.x - other.x) ** 2 +
            (self.y - other.y) ** 2 +
            (self.z - other.z) ** 2
        )


@dataclass
class Edge:
    """Weighted relationship between two nodes in the space."""
    target_id: str
    relation_type: str  # e.g., 'semantic', 'temporal', 'emotional', 'causal'
    weight: float = 1.0  # Strength of link [0.0, 1.0]


class ThoughtNode:
    """A single point/concept in the 3D Cognitive Field."""

    def __init__(
        self,
        node_id: str,
        label: str,
        position: Vector3D,
        node_type: str = "concept",  # concept, memory, emotion, belief, goal, prediction
        metadata: Optional[Dict] = None
    ):
        self.node_id = node_id
        self.label = label
        self.position = position
        self.node_type = node_type
        self.metadata = metadata or {}

        # Dynamic Field Properties
        self.activation_energy: float = 0.0  # Current activation level [0.0, +inf)
        self.base_level_activation: float = 0.1  # Recency/frequency baseline
        self.edges: List[Edge] = []
        self.last_activated: float = time.time()

    def add_edge(self, target_id: str, relation_type: str, weight: float = 1.0):
        # Prevent duplicate identical edges
        for e in self.edges:
            if e.target_id == target_id and e.relation_type == relation_type:
                e.weight = max(e.weight, weight)
                return
        self.edges.append(Edge(target_id, relation_type, weight))


# =====================================================================
# 2. CORE COGNITIVE SPACE 3D ENGINE
# =====================================================================

class CognitiveSpace3D:
    """Dynamic, non-linear 3D Cognitive Graph representation for Jarvix.
    
    Subsystems (Semantic, Episodic, Prediction, InnerVoice) communicate 
    by perturbing energy in this space and reading activated neighborhoods.
    """

    def __init__(self, decay_rate: float = 0.15, activation_threshold: float = 0.2):
        self.nodes: Dict[str, ThoughtNode] = {}
        self.decay_rate = decay_rate
        self.activation_threshold = activation_threshold
        self._initialize_seed_space()

    def _initialize_seed_space(self):
        """Seeds the space with foundational anchor concepts across X, Y, Z."""
        anchors = [
            # ID, Label, X (Concept), Y (Experience), Z (Time), Type
            ("self", "Self / Core Identity", Vector3D(0.0, -0.8, 0.0), "belief"),
            ("home", "Home / Belonging", Vector3D(0.4, -0.7, -0.3), "memory"),
            ("wind_in_the_willows", "The Wind in the Willows", Vector3D(0.8, 0.2, 0.0), "concept"),
            ("nostalgia", "Nostalgia / Longing", Vector3D(-0.3, -0.9, -0.5), "emotion"),
            ("nature", "Nature / Environment", Vector3D(0.7, 0.5, 0.0), "concept"),
            ("childhood", "Childhood / Early Years", Vector3D(0.2, -0.6, -0.9), "memory"),
        ]

        for nid, label, pos, ntype in anchors:
            self.add_node(ThoughtNode(nid, label, pos, ntype))

        # Seed initial relations
        self.connect("wind_in_the_willows", "nature", "semantic", 0.9)
        self.connect("wind_in_the_willows", "home", "experiential", 0.6)
        self.connect("home", "nostalgia", "emotional", 0.95)
        self.connect("home", "childhood", "temporal", 0.85)
        self.connect("nostalgia", "self", "experiential", 0.9)

    def add_node(self, node: ThoughtNode):
        self.nodes[node.node_id] = node

    def connect(self, source_id: str, target_id: str, relation_type: str, weight: float = 1.0, bidirectional: bool = True):
        if source_id in self.nodes and target_id in self.nodes:
            self.nodes[source_id].add_edge(target_id, relation_type, weight)
            if bidirectional:
                self.nodes[target_id].add_edge(source_id, relation_type, weight)

    # -----------------------------------------------------------------
    # FIELD DYNAMICS: PERTURBATION & SPREADING ACTIVATION
    # -----------------------------------------------------------------

    def inject_energy(self, node_id: str, energy: float):
        """Stimulates a specific node (e.g. from raw input recognition)."""
        if node_id in self.nodes:
            node = self.nodes[node_id]
            node.activation_energy += energy
            node.last_activated = time.time()

    def spread_activation(self, steps: int = 2, damping: float = 0.5):
        """Spreads energy outwards along graph edges and 3D spatial proximity.
        
        Energy flow formula: 
        E_target += E_source * Edge_Weight * Damping * Spatial_Proximity_Factor
        """
        for _ in range(steps):
            energy_delta: Dict[str, float] = {nid: 0.0 for nid in self.nodes}

            for source_id, node in self.nodes.items():
                if node.activation_energy < 0.05:
                    continue

                # 1. Spread through graph connections
                for edge in node.edges:
                    if edge.target_id in self.nodes:
                        target = self.nodes[edge.target_id]
                        
                        # Distance penalizes energy spread slightly
                        dist = node.position.distance_to(target.position)
                        spatial_factor = 1.0 / (1.0 + dist)
                        
                        transferred = node.activation_energy * edge.weight * damping * spatial_factor
                        energy_delta[edge.target_id] += transferred

                # 2. Field Effect: Radiate energy to unlinked nearby nodes in 3D Space
                for target_id, target in self.nodes.items():
                    if target_id == source_id:
                        continue
                    dist = node.position.distance_to(target.position)
                    if dist < 0.5:  # Spatial resonance threshold
                        field_transfer = (node.activation_energy * damping * 0.2) / (1.0 + dist**2)
                        energy_delta[target_id] += field_transfer

            # Apply collected energy deltas
            for nid, delta in energy_delta.items():
                self.nodes[nid].activation_energy += delta

    def decay_space(self):
        """Applies natural decay to all node activations across time cycles."""
        for node in self.nodes.values():
            node.activation_energy = max(
                node.base_level_activation,
                node.activation_energy * (1.0 - self.decay_rate)
            )

    # -----------------------------------------------------------------
    # READ/INSPECT THE ACTIVE FIELD
    # -----------------------------------------------------------------

    def get_active_neighborhood(self) -> List[Tuple[ThoughtNode, float]]:
        """Returns all nodes operating above the awareness threshold, sorted by energy."""
        active = [
            (node, node.activation_energy)
            for node in self.nodes.values()
            if node.activation_energy >= self.activation_threshold
        ]
        return sorted(active, key=lambda item: item[1], reverse=True)

    def detect_conflicts(self) -> List[Tuple[str, str]]:
        """Finds active concepts that occupy contradictory or opposing 3D vector spaces."""
        conflicts = []
        active = [n for n, energy in self.get_active_neighborhood()]
        
        for i in range(len(active)):
            for j in range(i + 1, len(active)):
                n1, n2 = active[i], active[j]
                # High distance in X (Concept) but high connection strength indicates cognitive dissonance
                dist = n1.position.distance_to(n2.position)
                has_direct_edge = any(e.target_id == n2.node_id for e in n1.edges)
                
                if dist > 1.2 and has_direct_edge:
                    conflicts.append((n1.label, n2.label))
        return conflicts


# =====================================================================
# 3. JARVIX AGENT INTEGRATION (SUBSYSTEMS INTERACTION)
# =====================================================================

class IntegratedJarvixAgent:
    """Jarvix agent interacting directly with the shared 3D Cognitive Space."""

    def __init__(self):
        self.cognitive_space = CognitiveSpace3D()

    def process_stimulus(self, raw_input: str) -> str:
        print(f"\n--- [INPUT STIMULUS]: \"{raw_input}\" ---")

        # Step 1: Input Perturbation (Subsystems inject energy into matching nodes)
        if "wind" in raw_input.lower() or "willows" in raw_input.lower():
            self.cognitive_space.inject_energy("wind_in_the_willows", energy=2.5)
            self.cognitive_space.inject_energy("nature", energy=1.0)

        if "home" in raw_input.lower() or "reminds" in raw_input.lower():
            self.cognitive_space.inject_energy("home", energy=2.0)

        # Step 2: Non-linear Spreading Activation across 3D graph
        print(">> Spreading activation across Knowledge, Temporal, and Self axes...")
        self.cognitive_space.spread_activation(steps=2, damping=0.6)

        # Step 3: Inspect active neighborhood (Cognitive state emergence)
        active_nodes = self.cognitive_space.get_active_neighborhood()

        print("\n[ACTIVE COGNITIVE FIELD STATE]:")
        print(f"{'Node Label':<25} | {'Type':<10} | {'Energy':<6} | {'3D Position (X,Y,Z)'}")
        print("-" * 65)
        for node, energy in active_nodes:
            pos = f"({node.position.x:.1f}, {node.position.y:.1f}, {node.position.z:.1f})"
            print(f"{node.label:<25} | {node.node_type:<10} | {energy:<6.2f} | {pos}")

        # Step 4: Executive synthesis based on activated regions
        response = self._synthesize_response(active_nodes)

        # Step 5: System Decay for next turn
        self.cognitive_space.decay_space()

        return response

    def _synthesize_response(self, active_nodes: List[Tuple[ThoughtNode, float]]) -> str:
        node_ids = {node.node_id for node, _ in active_nodes}

        # Check activated dimensions
        has_nostalgia = "nostalgia" in node_ids
        has_childhood = "childhood" in node_ids
        has_home = "home" in node_ids

        if has_nostalgia and has_home:
            return (
                "I sense a deep personal connection here. 'The Wind in the Willows' isn't just "
                "a reference to a book for you—it triggers a nostalgic pull back toward home and past memories."
            )
        elif has_home:
            return "That brings up thoughts of home and familiar spaces."
        else:
            return "I am processing the semantic elements of your input."


# =====================================================================
# 4. EXECUTION DEMO
# =====================================================================

if __name__ == "__main__":
    jarvix = IntegratedJarvixAgent()

    # Pass the stimulus phrase
    statement = "The wind in the willows reminds me of home."
    output = jarvix.process_stimulus(statement)

    print("\n[JARVIX RESPONSE]:")
    print(output)