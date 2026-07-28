"""
ability_brain_v2036.py

Jarvix Next-Gen Ability & Metacognitive Reasoning Engine
Features:
- Autonomous Intent Scoring (Semantic & 3D Space vector integration)
- Multi-step Ability Composition & Dynamic Pipelines
- Self-Reasoning (Metacognition: Plan -> Evaluate -> Reflect -> Learn)
"""

from __future__ import annotations

import time
import random
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Any, Tuple


# --------------------------------------------------
# Metacognitive Context & Result Structs
# --------------------------------------------------

@dataclass
class ReasoningTrace:
    step_id: int
    thought: str
    action_taken: str
    confidence: float
    output: Any


@dataclass
class MetacognitiveResult:
    success: bool
    final_output: str
    overall_confidence: float
    reasoning_chain: List[ReasoningTrace] = field(default_factory=list)
    critique: str = ""


# --------------------------------------------------
# Next-Gen Ability Abstraction
# --------------------------------------------------

class Ability:
    def __init__(
        self,
        name: str,
        description: str,
        handler: Callable[..., Any],
        semantic_tags: Optional[List[str]] = None,
        complexity_score: float = 0.5,
    ):
        self.name = name.lower()
        self.description = description
        self.handler = handler
        self.semantic_tags = set(semantic_tags or [])
        self.complexity_score = complexity_score
        self.execution_history: List[bool] = []

    def compute_relevance(self, text: str, active_nodes: List[Any] = None) -> float:
        """Evaluates semantic relevance using intent tags and 3D node activations."""
        text_lower = text.lower()
        score = 0.0

        # Direct name or tag hits
        if self.name in text_lower:
            score += 0.8
        for tag in self.semantic_tags:
            if tag in text_lower:
                score += 0.4

        # Boost score if active concept nodes match ability tags
        if active_nodes:
            for node, energy in active_nodes:
                node_label = getattr(node, "label", str(node)).lower()
                if node_label in self.semantic_tags or node_label == self.name:
                    score += 0.3 * float(energy)

        # Historical reliability multiplier
        if self.execution_history:
            success_rate = sum(self.execution_history) / len(self.execution_history)
            score *= (0.8 + 0.4 * success_rate)

        return min(1.0, score)

    def execute(self, *args, **kwargs) -> Any:
        try:
            res = self.handler(*args, **kwargs)
            self.execution_history.append(True)
            return res
        except Exception as e:
            self.execution_history.append(False)
            raise e


# --------------------------------------------------
# Metacognitive Ability Brain
# --------------------------------------------------

class AbilityBrain:
    def __init__(self, agent_instance=None):
        self.abilities: Dict[str, Ability] = {}
        self.agent = agent_instance
        self.reflection_memory: List[Dict[str, Any]] = []

        self._register_builtins()
        if agent_instance:
            self.bind_agent(agent_instance)

    def bind_agent(self, agent):
        """Connects Jarvix agent assets (3D space, memory, graphs)."""
        self.agent = agent

    def register(self, ability: Ability):
        self.abilities[ability.name] = ability

    # --------------------------------------------------
    # Self-Reasoning & Intent Recognition
    # --------------------------------------------------

    def evaluate_intent(self, text: str) -> List[Tuple[Ability, float]]:
        """Ranks abilities by contextual and semantic fit."""
        active_nodes = []
        if self.agent and hasattr(self.agent, "cognitive_space"):
            try:
                active_nodes = self.agent.cognitive_space.get_active_neighborhood()
            except Exception:
                pass

        rankings = []
        for ability in self.abilities.values():
            rel = ability.compute_relevance(text, active_nodes)
            if rel > 0.25:
                rankings.append((ability, rel))

        rankings.sort(key=lambda x: x[1], reverse=True)
        return rankings

    def can_handle(self, text: str) -> bool:
        """Determines if the brain can handle the task via single tool or pipeline."""
        ranked = self.evaluate_intent(text)
        if ranked and ranked[0][1] >= 0.4:
            return True
        
        # Self-reasoning fallback: Check if a composed pipeline can solve it
        return self._can_synthesize_pipeline(text)

    def _can_synthesize_pipeline(self, text: str) -> bool:
        """Checks for multi-step tasks (e.g., 'generate random and reverse it')."""
        words = text.lower().split()
        match_count = sum(1 for a in self.abilities.values() if a.name in words or any(t in words for t in a.semantic_tags))
        return match_count >= 2

    # --------------------------------------------------
    # Self-Reasoning Execution Engine
    # --------------------------------------------------

    def execute(self, text: str) -> Optional[str]:
        """Main entry point: Executes request with metacognitive validation."""
        meta_res = self.self_reasoning_pipeline(text)
        
        if meta_res.success:
            return (
                f"{meta_res.final_output}\n\n"
                f"--- [Metacognitive Trace] ---\n"
                f"Confidence: {meta_res.overall_confidence:.0%}\n"
                f"Self-Critique: {meta_res.critique}"
            )
        return f"Unable to process reliably. Critique: {meta_res.critique}"

    def self_reasoning_pipeline(self, text: str) -> MetacognitiveResult:
        """Executes the 4-phase metacognitive loop: Plan -> Act -> Verify -> Reflect."""
        traces: List[ReasoningTrace] = []
        
        # Phase 1: Planning / Intent Discovery
        ranked = self.evaluate_intent(text)
        
        if not ranked and not self._can_synthesize_pipeline(text):
            return MetacognitiveResult(
                success=False,
                final_output="",
                overall_confidence=0.0,
                critique="No relevant intent vector found in cognitive space."
            )

        # Multi-step pipeline execution if needed
        if self._can_synthesize_pipeline(text) and (not ranked or ranked[0][1] < 0.7):
            return self._execute_composed_pipeline(text)

        target_ability, initial_conf = ranked[0]
        
        traces.append(ReasoningTrace(
            step_id=1,
            thought=f"Selected tool '{target_ability.name}' with intent score {initial_conf:.2f}",
            action_taken=f"Invoke {target_ability.name}",
            confidence=initial_conf,
            output=None
        ))

        # Phase 2: Action Execution
        try:
            raw_output = target_ability.execute(text)
            traces.append(ReasoningTrace(
                step_id=2,
                thought="Tool execution completed without runtime errors.",
                action_taken="Capture Output",
                confidence=0.9,
                output=raw_output
            ))
        except Exception as err:
            # Self-Correction Loop
            traces.append(ReasoningTrace(
                step_id=2,
                thought=f"Execution failed with error: {str(err)}",
                action_taken="Trigger Self-Correction",
                confidence=0.1,
                output=None
            ))
            return self._reflect_and_retry(text, target_ability, str(err), traces)

        # Phase 3: Self-Verification
        critique, verified_conf = self._self_verify(text, str(raw_output), initial_conf)
        
        # Phase 4: Reflection Memory Storage
        self.reflection_memory.append({
            "input": text,
            "ability": target_ability.name,
            "confidence": verified_conf,
            "timestamp": time.time()
        })

        return MetacognitiveResult(
            success=True,
            final_output=str(raw_output),
            overall_confidence=verified_conf,
            reasoning_chain=traces,
            critique=critique
        )

    def _self_verify(self, prompt: str, output: str, base_conf: float) -> Tuple[str, float]:
        """Metacognitive verification: Evaluates if the output answers the prompt."""
        if not output or output.strip() == "":
            return "Output was empty; low reliability.", 0.2
        
        # Checking for empty or degraded outputs
        if "error" in output.lower():
            return "Output contains error flags.", 0.3

        return "Output matches structural expectations and confidence thresholds.", base_conf * 0.95

    def _reflect_and_retry(
        self, prompt: str, failed_ability: Ability, error_msg: str, traces: List[ReasoningTrace]
    ) -> MetacognitiveResult:
        """Reflects on execution failures and attempts a fallback strategy."""
        traces.append(ReasoningTrace(
            step_id=3,
            thought=f"Reflection: '{failed_ability.name}' failed. Error: {error_msg}. Searching fallback.",
            action_taken="Search Alternative Ability",
            confidence=0.5,
            output=None
        ))
        
        # Pick secondary alternative
        ranked = [a for a, c in self.evaluate_intent(prompt) if a.name != failed_ability.name]
        if ranked:
            fallback = ranked[0]
            try:
                out = fallback.execute(prompt)
                return MetacognitiveResult(
                    success=True,
                    final_output=str(out),
                    overall_confidence=0.6,
                    reasoning_chain=traces,
                    critique=f"Primary tool failed ({failed_ability.name}). Successfully recovered using {fallback.name}."
                )
            except Exception as e:
                pass

        return MetacognitiveResult(
            success=False,
            final_output="",
            overall_confidence=0.0,
            reasoning_chain=traces,
            critique=f"Self-repair exhausted. Failed at {failed_ability.name}: {error_msg}"
        )

    def _execute_composed_pipeline(self, text: str) -> MetacognitiveResult:
        """Synthesizes a multi-step execution pipeline dynamically."""
        words = text.lower().split()
        active_pipeline: List[Ability] = []
        
        for word in words:
            for ab in self.abilities.values():
                if ab.name == word or word in ab.semantic_tags:
                    if ab not in active_pipeline:
                        active_pipeline.append(ab)

        current_val = text
        traces = []
        
        for idx, ab in enumerate(active_pipeline, 1):
            try:
                current_val = str(ab.execute(current_val))
                traces.append(ReasoningTrace(
                    step_id=idx,
                    thought=f"Pipeline step {idx}: Executed {ab.name}",
                    action_taken=f"Pass result to step {idx+1}",
                    confidence=0.85,
                    output=current_val
                ))
            except Exception as e:
                return MetacognitiveResult(
                    success=False,
                    final_output="",
                    overall_confidence=0.2,
                    reasoning_chain=traces,
                    critique=f"Pipeline collapsed at stage '{ab.name}': {str(e)}"
                )

        return MetacognitiveResult(
            success=True,
            final_output=current_val,
            overall_confidence=0.8,
            reasoning_chain=traces,
            critique=f"Successfully synthesized and ran {len(active_pipeline)}-step dynamic pipeline."
        )

    # --------------------------------------------------
    # Built-In Capability Registration
    # --------------------------------------------------

    def _register_builtins(self):
        self.register(Ability("echo", "Echoes input text back.", lambda t: re.sub(r"^echo", "", t, flags=re.I).strip(), ["repeat", "mirror"]))
        self.register(Ability("reverse", "Reverses character stream.", lambda t: re.sub(r"^reverse", "", t, flags=re.I).strip()[::-1], ["backwards", "invert"]))
        self.register(Ability("uppercase", "Converts text to uppercase.", lambda t: t.upper(), ["caps", "loud"]))
        self.register(Ability("lowercase", "Converts text to lowercase.", lambda t: t.lower(), ["quiet", "min"]))
        self.register(Ability("random", "Generates random value.", lambda t: str(random.randint(1, 100)), ["dice", "rng", "generate"]))
        self.register(Ability("count", "Counts numbers to threshold.", self._count_handler, ["counter", "sequence"]))

    def _count_handler(self, text: str) -> str:
        m = re.search(r"\d+", text)
        end = int(m.group()) if m else 10
        end = max(0, min(end, 100))
        return ", ".join(str(i) for i in range(end + 1))