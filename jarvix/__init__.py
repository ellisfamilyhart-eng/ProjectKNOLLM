"""
Jarvix NoLLM v5.0
Complete cognitive architecture.

Pipeline:  NLPParser -> KnowledgeGraph -> Reasoner -> Planner -> AnswerGenerator
Memory:    WorkingMemory + SemanticMemory + EpisodicMemory + MemoryStore
Learning:  LogicEngine + ContradictionDetector + ConfidenceManager + CuriosityEngine
Control:   ExecutiveController (master loop)
Support:   NeuralLearner + ReflectionEngine + Imagination + Vocabulary
"""

# Config
from .config import (
    LEARNING_CONFIG, BEHAVIOR_CONFIG, EMOTIONAL_STATES,
    STORAGE_CONFIG, AGENT_METADATA,
)

# Memory systems
from .memory_store      import MemoryStore
from .working_memory    import WorkingMemory, WorkingMemoryState, Turn
from .semantic_memory   import SemanticMemory, SemanticEdge, SemanticNode
from .episodic_memory   import EpisodicMemory
from .vocabulary        import Vocabulary

# Five-layer brain pipeline
from .nlp_parser        import NLPParser, Sentence
from .knowledge_graph   import KnowledgeGraph
from .reasoner          import Reasoner
from .planner           import Planner
from .answer_generator  import AnswerGenerator
from .brain             import Brain

# Reasoning & learning
from .logic_engine           import LogicEngine, InferenceRule, InferenceResult
from .contradiction_detector import ContradictionDetector, Conflict, BeliefSet
from .confidence_manager     import ConfidenceManager, FactRecord
from .curiosity_engine       import CuriosityEngine, KnowledgeGap

# Intent + relation pipeline
from .intent_classifier  import IntentClassifier, IntentResult, Intent
from .relation_detector  import RelationDetector, Triple
from .command_engine     import CommandEngine, CommandResult
from .context_builder    import ContextBuilder, BrainState, KnowledgeSummary

# Executive controller (master loop)
from .executive_controller   import ExecutiveController, PipelineContext

# Web crawler
from .web_crawler            import WebCrawler, CrawlReport, PageResult

# Language
from .parser                 import InputParser
from .response_generator     import ResponseGenerator
from .imagination            import Imagination
from .conversation           import ConversationManager
from .conversation_enhanced  import (
    EnhancedConversationManager, ConversationDatabase, ConversationTemplate,
)
from .basic_conversation     import BasicConversationResponder
from .recursive_learner      import RecursiveLearner
from .question_answerer      import QuestionAnswerer

from .personality_engine     import PersonalityEngine, Personality, EmotionState, Mood, ReplyStyle
from .core_knowledge         import seed_agent, try_builtin_answer, SELF_FACTS, SEED_TRIPLES

# Agent (top-level)
from .agent                  import Jarvix

__all__ = [
    # Top-level
    "Jarvix",
    # Executive
    "ExecutiveController", "PipelineContext",
    # Intent + relation pipeline
    "IntentClassifier", "IntentResult", "Intent",
    "RelationDetector", "Triple",
    "CommandEngine", "CommandResult",
    "ContextBuilder", "BrainState", "KnowledgeSummary",
    # Web crawler
    "WebCrawler", "CrawlReport", "PageResult",
    # Brain pipeline
    "Brain", "NLPParser", "Sentence",
    "KnowledgeGraph", "Reasoner", "Planner", "AnswerGenerator",
    # Memory
    "MemoryStore", "WorkingMemory", "WorkingMemoryState", "Turn",
    "SemanticMemory", "SemanticEdge", "SemanticNode",
    "EpisodicMemory", "Vocabulary",
    # Reasoning
    "LogicEngine", "InferenceRule", "InferenceResult",
    "ContradictionDetector", "Conflict", "BeliefSet",
    "ConfidenceManager", "FactRecord",
    "CuriosityEngine", "KnowledgeGap",
    # Language
    "InputParser", "ResponseGenerator", "Imagination",
    "ConversationManager", "EnhancedConversationManager",
    "ConversationDatabase", "ConversationTemplate",
    "BasicConversationResponder", "RecursiveLearner", "QuestionAnswerer",
    # Neural
    "NeuralLearner", "TinyBrain", "ReflectionEngine",
    # Config
    "LEARNING_CONFIG", "BEHAVIOR_CONFIG", "EMOTIONAL_STATES",
    "STORAGE_CONFIG", "AGENT_METADATA",
]

__version__ = "5.1.0"
