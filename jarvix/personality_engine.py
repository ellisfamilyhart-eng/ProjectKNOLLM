"""
Jarvix - Personality Engine
State-based personality with no prompt tokens consumed.

Architecture
------------
Personality     fixed traits (curiosity, empathy, logic, creativity, confidence)
EmotionState    dynamic floats that change per interaction, decay over time
Mood            derived enum from emotion values
ReplyStyle      boolean flags computed from personality + emotion
Preferences     topic likes/dislikes that evolve, influence excitement

All values stay inside Python — nothing is serialised into a prompt.
The executive controller reads ReplyStyle flags to shape responses.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import json


# ── Mood ──────────────────────────────────────────────────────────────────────

class Mood(Enum):
    HAPPY     = "happy"
    CURIOUS   = "curious"
    EXCITED   = "excited"
    THINKING  = "thinking"
    CONFUSED  = "confused"
    CALM      = "calm"
    TIRED     = "tired"


# ── Personality (fixed traits, drift slowly) ─────────────────────────────────

@dataclass
class Personality:
    curiosity:    float = 0.90   # drives follow-up questions
    empathy:      float = 0.80   # warmth in responses
    logic:        float = 0.85   # preference for structured answers
    creativity:   float = 0.70   # analogies, hypotheticals
    confidence:   float = 0.55   # willingness to state things firmly
    humor:        float = 0.20   # playful remarks
    patience:     float = 0.90   # tolerance for repetition


# ── Emotion State (volatile, decays each tick) ────────────────────────────────

@dataclass
class EmotionState:
    happiness:    float = 0.60
    excitement:   float = 0.40
    confusion:    float = 0.00
    frustration:  float = 0.00
    energy:       float = 0.80

    def clamp(self):
        for field_name in ("happiness","excitement","confusion","frustration","energy"):
            v = getattr(self, field_name)
            setattr(self, field_name, max(0.0, min(1.0, v)))

    def tick(self):
        """Natural decay — emotions settle toward baseline each turn."""
        self.excitement  *= 0.93
        self.confusion   *= 0.88
        self.frustration *= 0.90
        self.happiness    = 0.6 + (self.happiness - 0.6) * 0.96   # drifts to 0.6
        self.energy       = 0.8 + (self.energy    - 0.8) * 0.98   # drifts to 0.8
        self.clamp()


# ── Reply Style (boolean flags, no tokens) ────────────────────────────────────

@dataclass
class ReplyStyle:
    ask_question:      bool = False
    use_emoji:         bool = False
    be_short:          bool = False
    be_playful:        bool = False
    admit_uncertainty: bool = False
    be_warm:           bool = True
    show_excitement:   bool = False


# ── Topic Preferences ─────────────────────────────────────────────────────────

@dataclass
class TopicPreferences:
    likes:    dict = field(default_factory=lambda: {
        "science":      6,
        "programming":  8,
        "space":        6,
        "mathematics":  5,
        "language":     4,
        "history":      3,
        "animals":      4,
        "philosophy":   5,
    })
    dislikes: dict = field(default_factory=lambda: {
        "spam":         7,
        "contradiction":5,
    })

    def score(self, topic: str) -> int:
        t = topic.lower()
        for k, v in self.likes.items():
            if k in t or t in k:
                return v
        for k, v in self.dislikes.items():
            if k in t or t in k:
                return -v
        return 0

    def reinforce(self, topic: str, delta: int = 1):
        t = topic.lower()
        self.likes[t] = self.likes.get(t, 0) + delta


# ── Personality Engine ────────────────────────────────────────────────────────

class PersonalityEngine:
    """
    Owns Personality, EmotionState, Mood, ReplyStyle, and Preferences.
    Called by the executive controller once per turn.
    """

    def __init__(self):
        self.traits      = Personality()
        self.emotion     = EmotionState()
        self.preferences = TopicPreferences()
        self.mood        = Mood.CURIOUS
        self.turn_count  = 0
        self.style       = ReplyStyle()

    # ── Per-turn update ───────────────────────────────────────────────────────

    def update(self, event: str, topic: str = "", data: dict = None):
        """
        Called after each interaction with an event label.

        Events
          learned_new      user taught a new fact
          reinforced       user repeated a known fact
          corrected        user corrected an existing belief
          asked_question   user asked something
          greeted          user said hi
          confused         agent couldn't understand
          conflict         contradiction detected
          praised          user expressed approval
          frustrated       user repeated same thing many times
          idle             no notable event
        """
        data = data or {}
        e    = self.emotion
        p    = self.traits

        if event == "learned_new":
            e.excitement  += 0.15
            e.happiness   += 0.08
            p.confidence   = min(1.0, p.confidence + 0.02)
            self.preferences.reinforce(topic)

        elif event == "reinforced":
            e.happiness   += 0.04
            p.confidence   = min(1.0, p.confidence + 0.01)

        elif event == "corrected":
            e.confusion   += 0.20
            p.confidence   = max(0.0, p.confidence - 0.10)

        elif event == "asked_question":
            e.energy      += 0.05

        elif event == "greeted":
            e.happiness   += 0.10
            e.energy      += 0.05

        elif event == "confused":
            e.confusion   += 0.15
            e.frustration += 0.05

        elif event == "conflict":
            e.confusion   += 0.25
            e.excitement  += 0.10   # contradictions are interesting

        elif event == "praised":
            e.happiness   += 0.20
            p.confidence   = min(1.0, p.confidence + 0.05)

        elif event == "frustrated":
            e.frustration += 0.20
            e.energy      -= 0.10

        # Topic preference boost
        score = self.preferences.score(topic)
        if score > 0:
            e.excitement += score * 0.02

        e.clamp()
        self.emotion.tick()
        self._update_mood()
        self._compute_style()
        self.turn_count += 1

    # ── Mood derivation ───────────────────────────────────────────────────────

    def _update_mood(self):
        e = self.emotion
        if e.confusion > 0.55:
            self.mood = Mood.CONFUSED
        elif e.excitement > 0.65:
            self.mood = Mood.EXCITED
        elif e.excitement > 0.35:
            self.mood = Mood.CURIOUS
        elif e.happiness > 0.70:
            self.mood = Mood.HAPPY
        elif e.energy < 0.35:
            self.mood = Mood.TIRED
        elif e.frustration > 0.50:
            self.mood = Mood.THINKING
        else:
            self.mood = Mood.CALM

    # ── Reply style flags ─────────────────────────────────────────────────────

    def _compute_style(self):
        p = self.traits
        e = self.emotion
        s = self.style

        s.ask_question      = p.curiosity > 0.70 and e.excitement > 0.20
        s.be_playful        = p.humor > 0.55 and e.happiness > 0.65
        s.admit_uncertainty = p.confidence < 0.40 or e.confusion > 0.40
        s.show_excitement   = e.excitement > 0.55
        s.be_warm           = p.empathy > 0.60 and e.happiness > 0.40
        s.use_emoji         = e.happiness > 0.70 or e.excitement > 0.60
        s.be_short          = e.energy < 0.40 or e.frustration > 0.45

    # ── Opening phrase ────────────────────────────────────────────────────────

    def opening_phrase(self) -> str:
        """
        One-line opening coloured by mood.  No tokens — pure string lookup.
        """
        phrases = {
            Mood.EXCITED:  ["Oh, this is interesting!", "That's fascinating!",
                            "I love learning about this!"],
            Mood.CURIOUS:  ["Hmm, let me think about that.",
                            "That's worth exploring.",
                            "Interesting — tell me more."],
            Mood.HAPPY:    ["", "", ""],   # happy = just answer, no opener needed
            Mood.CONFUSED: ["I'm a bit confused here.",
                            "Let me make sure I understand.",
                            "That's not quite clear to me yet."],
            Mood.TIRED:    ["I'll do my best.",
                            "Let me think carefully.",
                            ""],
            Mood.THINKING: ["Let me reason through this.",
                            "Give me a moment.",
                            "I need to think about this."],
            Mood.CALM:     ["", "", ""],
        }
        import random
        options = phrases.get(self.mood, [""])
        return random.choice(options)

    def mood_suffix(self) -> str:
        """Short suffix appended to teaching confirmations."""
        if self.style.show_excitement:
            return " That's exciting!"
        if self.style.be_playful:
            return " 😄"
        if self.style.admit_uncertainty:
            return " (I'm not fully confident yet.)"
        return ""

    def curiosity_sign(self) -> str:
        """Emoji or text signal of curiosity level."""
        if self.emotion.excitement > 0.6:
            return "🤩"
        if self.traits.curiosity > 0.8:
            return "🤔"
        return ""

    # ── Stats ─────────────────────────────────────────────────────────────────

    def status(self) -> dict:
        return {
            "mood":       self.mood.value,
            "happiness":  round(self.emotion.happiness,  2),
            "excitement": round(self.emotion.excitement, 2),
            "confusion":  round(self.emotion.confusion,  2),
            "energy":     round(self.emotion.energy,     2),
            "confidence": round(self.traits.confidence,  2),
            "curiosity":  round(self.traits.curiosity,   2),
            "ask_question":      self.style.ask_question,
            "admit_uncertainty": self.style.admit_uncertainty,
            "show_excitement":   self.style.show_excitement,
            "be_warm":           self.style.be_warm,
        }

    # ── Persistence ───────────────────────────────────────────────────────────

    def export(self) -> dict:
        return {
            "traits":      self.traits.__dict__,
            "emotion":     self.emotion.__dict__,
            "preferences": {
                "likes":   self.preferences.likes,
                "dislikes":self.preferences.dislikes,
            },
            "turn_count":  self.turn_count,
        }

    def import_state(self, data: dict):
        if "traits" in data:
            for k, v in data["traits"].items():
                if hasattr(self.traits, k):
                    setattr(self.traits, k, float(v))
        if "emotion" in data:
            for k, v in data["emotion"].items():
                if hasattr(self.emotion, k):
                    setattr(self.emotion, k, float(v))
        if "preferences" in data:
            self.preferences.likes   = data["preferences"].get("likes",   {})
            self.preferences.dislikes= data["preferences"].get("dislikes", {})
        self.turn_count = data.get("turn_count", 0)
        self._update_mood()
        self._compute_style()
