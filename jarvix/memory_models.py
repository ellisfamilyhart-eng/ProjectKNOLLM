"""
Jarvix Memory Models v2

Defines the structures used by MemoryManager.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, List
import uuid


class MemoryType(Enum):
    """
    Different kinds of memory Jarvix can store.
    """

    SHORT_TERM = "short_term"

    WORKING = "working"

    FACT = "fact"

    EXPERIENCE = "experience"

    CONCEPT = "concept"



@dataclass
class Memory:
    """
    Base memory object.

    Every memory in Jarvix uses this structure.
    """

    content: Any

    memory_type: MemoryType

    confidence: float = 0.5

    importance: float = 0.5

    created: datetime = field(
        default_factory=datetime.now
    )

    last_accessed: datetime = field(
        default_factory=datetime.now
    )

    id: str = field(
        default_factory=lambda:
        str(uuid.uuid4())
    )

    tags: List[str] = field(
        default_factory=list
    )

    links: List[str] = field(
        default_factory=list
    )


    def touch(self):
        """
        Update memory access time.
        """

        self.last_accessed = datetime.now()


    def strengthen(
        self,
        amount: float = 0.05
    ):
        """
        Increase confidence when recalled.
        """

        self.confidence = min(
            1.0,
            self.confidence + amount
        )


    def weaken(
        self,
        amount: float = 0.05
    ):
        """
        Reduce confidence over time.
        """

        self.confidence = max(
            0.0,
            self.confidence - amount
        )