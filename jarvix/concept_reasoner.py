"""
Jarvix Concept Reasoner
=======================

The ConceptReasoner is Jarvix's executive reasoning layer.
It sits above the Planner and Reasoner.

Pipeline:
User -> ConceptReasoner -> Execution Plan -> Abilities -> Reasoner/KG/Memory -> Final Answer
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import re
import math
from abc import ABC, abstractmethod

from .knowledge_graph import (
    KnowledgeGraph,
    R_IS_A,
    R_HAS_PROP,
    R_CAN,
)

from .reasoner import Reasoner

# ---------------------------------------------------------
# Problem categories
# ---------------------------------------------------------

PROBLEM_UNKNOWN = "unknown"
PROBLEM_FACT = "fact"
PROBLEM_GRAPH = "graph"
PROBLEM_ARITHMETIC = "arithmetic"
PROBLEM_COUNTING = "counting"
PROBLEM_COMPARISON = "comparison"
PROBLEM_TEXT = "text"
PROBLEM_PIPELINE = "pipeline"
PROBLEM_ONTOLOGY = "ontology"
PROBLEM_EXPLANATION = "explanation"

# ---------------------------------------------------------
# Ability identifiers
# ---------------------------------------------------------

ABILITY_ARITHMETIC = "arithmetic"
ABILITY_COUNTING = "counting"
ABILITY_ONTOLOGY = "ontology"
ABILITY_GRAPH = "graph"
ABILITY_TEXT = "text"
ABILITY_COMPARE = "comparison"
ABILITY_REASONER = "reasoner"

@dataclass
class AbilityResult:
    success: bool = False
    answer: Any = None
    confidence: float = 0.0
    explanation: str = ""
    produced_concepts: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    
@dataclass
class ExecutionStep:
    ability: str
    instruction: str
    inputs: Any = None
    output: Any = None
    completed: bool = False
    confidence: float = 0.0
    
@dataclass
class ExecutionPlan:
    original_query: str
    problem_type: str
    steps: list[ExecutionStep] = field(default_factory=list)
    current_value: Any = None
    explanation: list[str] = field(default_factory=list)
    confidence: float = 1.0

    def add_step(
        self,
        ability,
        instruction,
        inputs=None
    ):
        self.steps.append(
            ExecutionStep(
                ability=ability,
                instruction=instruction,
                inputs=inputs
            )
        )

    @property
    def finished(self):
        return all(
            step.completed
            for step in self.steps
        )

# ---------------------------------------------------------
# Ability Base Class
# ---------------------------------------------------------

class Ability(ABC):
    """
    Base class for every Jarvix capability.
    Abilities are plugins.
    """
    name = "unknown"
    description = ""

    @abstractmethod
    def can_handle(
        self,
        problem_type: str,
        query: str,
        context: dict | None = None
    ) -> bool:
        """Decide if this ability applies."""
        pass

    @abstractmethod
    def execute(
        self,
        instruction: str,
        inputs=None,
        context: dict | None = None
    ) -> AbilityResult:
        """Perform the ability."""
        pass

    def info(self):
        return {
            "name": self.name,
            "description": self.description
        }

# ---------------------------------------------------------
# Ability Registry
# ---------------------------------------------------------

class AbilityRegistry:
    """Stores and routes Jarvix abilities."""
    def __init__(self):
        self.abilities = []

    def register(self, ability: Ability):
        if not isinstance(ability, Ability):
            raise TypeError("Ability must inherit from Ability")
        self.abilities.append(ability)

    def find(self, problem_type, query, context=None):
        matches = []
        for ability in self.abilities:
            if ability.can_handle(problem_type, query, context):
                matches.append(ability)
        return matches

    def get(self, name):
        for ability in self.abilities:
            if ability.name == name:
                return ability
        return None

    def list(self):
        return [ability.info() for ability in self.abilities]

# ---------------------------------------------------------
# Concept Reasoner
# ---------------------------------------------------------

class ConceptReasoner:
    def __init__(
        self,
        graph: KnowledgeGraph,
        reasoner: Reasoner,
        memory=None
    ):
        self.graph = graph
        self.reasoner = reasoner
        self.memory = memory
        self.registry = AbilityRegistry()
        self.load_default_abilities()

    def register_ability(self, ability: Ability):
        self.registry.register(ability)

    def load_default_abilities(self):
        self.register_ability(ArithmeticAbility())
        self.register_ability(CountingAbility())

    def understand_request(self, query: str) -> AbilityResult:
        """Main entry point. Executive reasoning pipeline."""
        plan = self.build_plan(query)
        self.choose_abilities(plan)
        self.execute_plan(plan)
        return self.combine_results(plan)
    
    def classify_problem(self, query: str) -> str:
        """Determines what kind of reasoning the request requires."""
        text = query.lower()

        concepts = self.extract_concepts(query)

        if len(concepts) >= 2:
            return PROBLEM_COUNTING
        
        text = query.lower()

        # Multi-step pipeline detection
        pipeline_words = ["then", "after", "next", "followed by", "and then"]
        if any(word in text for word in pipeline_words):
            return PROBLEM_PIPELINE

        # Arithmetic detection
        arithmetic_symbols = ["+", "-", "*", "/", "multiply", "divide", "add", "subtract", "calculate"]
        if any(symbol in text for symbol in arithmetic_symbols):
            return PROBLEM_ARITHMETIC

        # Counting detection
        counting_words = ["how many", "how much", "count", "number of"]
        if any(word in text for word in counting_words):
            return PROBLEM_COUNTING

        # Comparison detection
        comparison_words = ["greater", "smaller", "larger", "taller", "shorter", "highest", "lowest", "best", "worst"]
        if any(word in text for word in comparison_words):
            return PROBLEM_COMPARISON

        # Knowledge graph style questions
        graph_words = ["is", "has", "can", "does", "where", "who"]
        if any(word in text.split() for word in graph_words):
            return PROBLEM_GRAPH

        return PROBLEM_UNKNOWN
    
    def extract_concepts(self, query: str) -> list:
        """Extract basic concepts."""
        concepts = []
        numbers = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
        }
        words = query.lower().split()

        for index, word in enumerate(words):
            quantity = None
            if word.isdigit():
                quantity = int(word)
            elif word in numbers:
                quantity = numbers[word]

            if quantity is not None:
                if index + 1 < len(words):
                    # Clean punctuation from concepts
                    concept = re.sub(r"[^\w]", "", words[index+1])
                    concepts.append({
                        "quantity": quantity,
                        "concept": concept
                    })
        return concepts
    
    def build_plan(self, query: str) -> ExecutionPlan:
        """Converts user request into an execution plan."""
        problem_type = self.classify_problem(query)
        plan = ExecutionPlan(
            original_query=query,
            problem_type=problem_type
        )

        concepts = self.extract_concepts(query)

        if concepts:
            plan.explanation.append(
                f"Detected concepts: {concepts}"
            )


        # Pipeline
        if problem_type == PROBLEM_PIPELINE:

            parts = re.split(
                r"\bthen\b|\band then\b",
                query,
                flags=re.IGNORECASE
            )

            for part in parts:

                part = part.strip()

                if not part:
                    continue

                sub_problem = self.classify_problem(part)

                if sub_problem == PROBLEM_ARITHMETIC:

                    ability = ABILITY_ARITHMETIC

                elif sub_problem == PROBLEM_COUNTING:

                    ability = ABILITY_COUNTING

                else:

                    ability = None

                plan.add_step(
                    ability=ability,
                    instruction=part
                )
        # Arithmetic
        elif problem_type == PROBLEM_ARITHMETIC:
            plan.add_step(
                ability=ABILITY_ARITHMETIC,
                instruction=query
            )
        # Counting
        elif problem_type == PROBLEM_COUNTING:
            plan.add_step(
                ability=ABILITY_COUNTING,
                instruction=query,
                inputs=concepts
            )
        # Comparison
        elif problem_type == PROBLEM_COMPARISON:
            plan.add_step(
                ability=ABILITY_COMPARE,
                instruction=query
            )
        # Graph / Knowledge
        elif problem_type == PROBLEM_GRAPH:
            plan.add_step(
                ability=ABILITY_GRAPH,
                instruction=query
            )
        # Unknown
        else:
            plan.add_step(
                ability=None,
                instruction=query
            )

        return plan
    
    def choose_abilities(self, plan: ExecutionPlan):
        """Matches execution steps with registered abilities."""
        for step in plan.steps:
            if step.ability:
                continue

            matches = self.registry.find(
                plan.problem_type,
                step.instruction,
                {"plan": plan}
            )

            if matches:
                step.ability = matches[0].name
            else:
                step.ability = ABILITY_REASONER

    def execute_plan(self, plan: ExecutionPlan):
        """Execute every step, feeding current state forward."""
        for step in plan.steps:
            ability = self.registry.get(step.ability)

            if ability is None:
                step.output = AbilityResult(
                    success=False,
                    answer=None,
                    confidence=0,
                    explanation="No ability available."
                )
                step.completed = True
                continue

            result = ability.execute(
                instruction=step.instruction,
                inputs=plan.current_value,
                context={
                    "graph": self.graph,
                    "reasoner": self.reasoner,
                    "memory": self.memory,
                    "plan": plan
                }
            )

            step.output = result.answer
            step.completed = result.success
            step.confidence = result.confidence

            plan.current_value = result.answer
            plan.confidence *= result.confidence
            plan.explanation.append(result.explanation)
    
    def combine_results(self, plan: ExecutionPlan) -> AbilityResult:
        """Merge all completed reasoning steps into a final Answer."""
        if not plan.steps:
            return AbilityResult(
                success=False,
                explanation="No reasoning steps created."
            )

        final_step = plan.steps[-1]
        successful = [step for step in plan.steps if step.completed]

        confidence = 0.0
        if successful:
            confidence = sum(step.confidence for step in successful) / len(successful)

        return AbilityResult(
            success=len(successful) == len(plan.steps),
            answer=final_step.output,
            confidence=confidence,
            explanation="\n".join(plan.explanation),
            metadata={
                "problem_type": plan.problem_type,
                "steps": len(plan.steps)
            }
        )

# ---------------------------------------------------------
# Arithmetic Ability
# ---------------------------------------------------------

class ArithmeticAbility(Ability):
    name = ABILITY_ARITHMETIC
    description = "Performs mathematical calculations while preserving context."

    def can_handle(self, problem_type, query, context=None):
        if problem_type == PROBLEM_ARITHMETIC:
            return True
        operators = ["+", "-", "*", "/", "add", "subtract", "multiply", "divide", "calculate"]
        query = query.lower()
        return any(op in query for op in operators)

    def extract_number(self, text):
        numbers = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
        }
        for word, value in numbers.items():
            if word in text:
                return value
        found = re.findall(r"\d+", text)
        if found:
            return int(found[0])
        return None

    def extract_expression(self, text):
        # Match sequences of numbers and operators, allowing spaces inside them
        # but demanding at least some actual mathematical characters
        matches = re.findall(r"[0-9]+(?:\s*[\+\-\*\/\.]+\s*[0-9]+)+|[0-9]+", text)
        if not matches:
            return None
        
        # Return the longest match (or the first one) that contains actual digits
        expression = matches[0].strip()
        return expression if expression else None

    def calculate(self, expression):
        allowed = {
            "abs": abs,
            "round": round,
            "math": math
        }
        return eval(expression, {"__builtins__": {}}, allowed)

    def execute(self, instruction, inputs=None, context=None) -> AbilityResult:
        text = instruction.lower()

        # Chain logic (prioritising sequential operations)
        if inputs is not None:
            number = self.extract_number(text)
            if number is not None:
                if "add" in text or "plus" in text or "+" in text:
                    result = inputs + number
                    return AbilityResult(
                        success=True,
                        answer=result,
                        confidence=0.95,
                        explanation=f"{inputs} + {number} = {result}"
                    )
                if "multiply" in text or "times" in text or "*" in text:
                    result = inputs * number
                    return AbilityResult(
                        success=True,
                        answer=result,
                        confidence=0.95,
                        explanation=f"{inputs} * {number} = {result}"
                    )

        # Baseline single expression calculation
        expression = self.extract_expression(instruction)
        if expression is None:
            return AbilityResult(
                success=False,
                explanation="No arithmetic expression found."
            )

        try:
            result = self.calculate(expression)
            return AbilityResult(
                success=True,
                answer=result,
                confidence=0.95,
                explanation=f"Calculated {expression} = {result}"
            )
        except Exception as e:
            return AbilityResult(
                success=False,
                explanation=f"Arithmetic error: {e}"
            )

# ---------------------------------------------------------
# Counting Ability
# ---------------------------------------------------------

class CountingAbility(Ability):
    name = ABILITY_COUNTING
    description = "Detects entities, extracts their counts, and prepares them for conceptual reasoning."

    def can_handle(self, problem_type, query, context=None):
        if problem_type == PROBLEM_COUNTING:
            return True
        counting_words = ["count", "how many", "number of"]
        return any(word in query.lower() for word in counting_words)

    def execute(self, instruction, inputs=None, context=None) -> AbilityResult:
        # Pull concepts extracted from the execution plan context if available
        concepts = None
        if context and "plan" in context:
            plan = context["plan"]
            concepts = plan.steps[0].inputs if plan.steps else None

        if not concepts:
            # Fall back to trying to extract manually
            reasoner = context.get("reasoner") if context else None
            # Basic manual regex parsing of quantity to nouns if no extraction was pre-computed
            matches = re.findall(r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+([a-zA-Z]+)", instruction.lower())
            numbers = {
                "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
            }
            concepts = []
            for num, noun in matches:
                qty = int(num) if num.isdigit() else numbers.get(num, 1)
                concepts.append({"quantity": qty, "concept": noun})

        if not concepts:
            return AbilityResult(
                success=False,
                explanation="Could not identify any entities to count."
            )

        # Map entities into a dict structure for downstream processing (e.g., OntologyAbility)
        counts = {}

        for item in concepts:

            counts[item["concept"]] = (
                counts.get(item["concept"], 0)
                + item["quantity"]
            )
        
        return AbilityResult(
            success=True,
            answer=counts,
            confidence=0.90,
            explanation=f"Identified counts: {', '.join([f'{v} {k}' for k, v in counts.items()])}",
            produced_concepts=list(counts.keys())
        )