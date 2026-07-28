"""
Jarvix Memory Manager v2.1

Controls memory creation,
classification and storage.
"""

from typing import List

from .memory_linker import MemoryLinker
from .memory_models import (
    Memory,
    MemoryType
)
from .memory_classifier import (
    MemoryClassifier
)


class MemoryManager:

    def __init__(self):
        self.linker = MemoryLinker()
        self.short_term: List[Memory] = []
        self.working_memory: List[Memory] = []
        self.long_term: List[Memory] = []
        self.experiences: List[Memory] = []
        self.concepts: List[Memory] = []

        # Memory brain
        self.classifier = MemoryClassifier()

    def learn(self, text: str) -> Memory:
        # Decide memory type
        result = self.classifier.classify(text)

        # Create memory object
        memory = Memory(
            content=text,
            memory_type=result.memory_type,
            confidence=result.confidence,
            importance=result.importance
        )

        # Store it
        self.remember(memory)

        # Get all memories for linking
        all_memories = (
            self.short_term
            + self.working_memory
            + self.long_term
            + self.experiences
            + self.concepts
        )

        # Link related memories
        self.linker.link(
            memory,
            all_memories
        )

        return memory

    def remember(self, memory: Memory):
        if memory.memory_type == MemoryType.SHORT_TERM:
            self.short_term.append(memory)

        elif memory.memory_type == MemoryType.WORKING:
            self.working_memory.append(memory)

        elif memory.memory_type == MemoryType.FACT:
            self.long_term.append(memory)

        elif memory.memory_type == MemoryType.EXPERIENCE:
            self.experiences.append(memory)

        elif memory.memory_type == MemoryType.CONCEPT:
            self.concepts.append(memory)

    def recall(self, query: str):
        results = []
        all_memory = (
            self.short_term
            + self.working_memory
            + self.long_term
            + self.experiences
            + self.concepts
        )

        for memory in all_memory:
            if query.lower() in str(memory.content).lower():
                memory.touch()
                memory.strengthen()
                results.append(memory)

        return results

    def forget(self, threshold=0.2):
        groups = [
            self.short_term,
            self.working_memory,
            self.long_term,
            self.experiences,
            self.concepts
        ]

        for group in groups:
            group[:] = [
                memory
                for memory in group
                if memory.confidence > threshold
            ]

    def stats(self):
        return {
            "short_term": len(self.short_term),
            "working": len(self.working_memory),
            "facts": len(self.long_term),
            "experiences": len(self.experiences),
            "concepts": len(self.concepts)
        }