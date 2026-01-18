"""
API Interface

Programmatic interface to Ω-Genesis consciousness.

This provides:
1. Simple chat function
2. Full process with all metadata
3. Memory operations
4. State inspection
5. Batch processing

Use this when integrating Ω-Genesis into other systems.
"""

import torch
from typing import Dict, List, Optional, Union, Tuple
from dataclasses import dataclass, asdict
import json

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from omega_genesis.core import CONST, Mode, TriValue
from omega_genesis.interface.consciousness import (
    ConsciousnessCore,
    ConsciousnessConfig,
    ConsciousnessState,
)


@dataclass
class ChatResponse:
    """Response from a chat interaction."""
    
    # The response text
    text: str
    
    # Certainty level (0 to 1)
    certainty: float
    
    # Whether output is uncertain (∅)
    is_undefined: bool
    
    # Tension between observers
    tension: float
    
    # Coherence between observers
    coherence: float
    
    # Entanglement measure
    entanglement: float
    
    # Dominant tri-logic value
    dominant: str
    
    # Novelty of input (how new was this?)
    novelty: float
    
    # Turn number
    turn: int
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @property
    def confidence_level(self) -> str:
        """Human-readable confidence level."""
        if self.certainty > 0.7:
            return "high"
        elif self.certainty > 0.4:
            return "moderate"
        else:
            return "low"


class OmegaAPI:
    """
    High-level API for Ω-Genesis.
    
    Simple usage:
        api = OmegaAPI()
        response = api.chat("Hello!")
        print(response.text)
        print(f"Certainty: {response.certainty:.0%}")
    
    Full access:
        response, full_info = api.process("Deep question")
        print(f"Bell entangled: {full_info['think']['bell_entangled']}")
    """
    
    def __init__(
        self,
        hilbert_dim: int = 128,
        n_observers: int = 4,
        max_thoughts: int = 500,
        auto_learn: bool = True,
    ):
        """
        Initialize the API.
        
        Args:
            hilbert_dim: Dimension of Hilbert space
            n_observers: Number of entangled observers
            max_thoughts: Maximum thoughts in memory
            auto_learn: Whether to auto-learn from interactions
        """
        config = ConsciousnessConfig(
            hilbert_dim=hilbert_dim,
            n_observers=n_observers,
            max_thoughts=max_thoughts,
        )
        
        self.consciousness = ConsciousnessCore(config)
        self.auto_learn = auto_learn
    
    def chat(self, message: str) -> ChatResponse:
        """
        Simple chat interface.
        
        Args:
            message: Input message
            
        Returns:
            ChatResponse with text and metadata
        """
        response, info = self.consciousness.process(message, learn=self.auto_learn)
        
        return ChatResponse(
            text=response,
            certainty=info['respond']['certainty'],
            is_undefined=info['respond']['undefined'],
            tension=info['perceive']['tension'],
            coherence=info['perceive']['coherence'],
            entanglement=info['state']['entanglement'],
            dominant=info['state']['dominant'],
            novelty=info['think']['novelty'],
            turn=info['state']['turn'],
        )
    
    def process(self, message: str, learn: bool = None) -> Tuple[ChatResponse, Dict]:
        """
        Full processing with all metadata.
        
        Args:
            message: Input message
            learn: Whether to learn (None uses auto_learn setting)
            
        Returns:
            (ChatResponse, full_info_dict)
        """
        if learn is None:
            learn = self.auto_learn
        
        response, info = self.consciousness.process(message, learn=learn)
        
        chat_response = ChatResponse(
            text=response,
            certainty=info['respond']['certainty'],
            is_undefined=info['respond']['undefined'],
            tension=info['perceive']['tension'],
            coherence=info['perceive']['coherence'],
            entanglement=info['state']['entanglement'],
            dominant=info['state']['dominant'],
            novelty=info['think']['novelty'],
            turn=info['state']['turn'],
        )
        
        return chat_response, info
    
    def learn(self, text: str, force: bool = False) -> bool:
        """
        Learn a thought from text.
        
        Args:
            text: Text to learn
            force: Force learn even if not novel
            
        Returns:
            True if thought was learned
        """
        thought = self.consciousness.learn(text, force=force)
        return thought is not None
    
    def batch_chat(self, messages: List[str]) -> List[ChatResponse]:
        """
        Process multiple messages.
        
        Args:
            messages: List of input messages
            
        Returns:
            List of ChatResponses
        """
        return [self.chat(msg) for msg in messages]
    
    def set_mode(self, mode: Union[str, Mode]):
        """
        Set processing mode.
        
        Args:
            mode: Mode name (string) or Mode enum
        """
        if isinstance(mode, str):
            mode = Mode[mode.upper()]
        self.consciousness.set_mode(mode)
    
    def get_state(self) -> Dict:
        """Get current consciousness state."""
        return self.consciousness.get_state_summary()
    
    def get_memory_summary(self) -> Dict:
        """Get memory summary."""
        return self.consciousness.memory.get_spectral_summary()
    
    def get_history(self) -> List[Dict]:
        """Get conversation history."""
        return list(self.consciousness.history)
    
    def clear_history(self):
        """Clear conversation history."""
        self.consciousness.history.clear()
    
    def step(self):
        """Advance time (decay memories)."""
        self.consciousness.step()
    
    def save_state(self, path: str):
        """Save consciousness state to file."""
        torch.save({
            'model_state': self.consciousness.state_dict(),
            'consciousness_state': asdict(self.consciousness.state) if hasattr(self.consciousness.state, '__dict__') else {},
            'history': list(self.consciousness.history),
        }, path)
    
    def load_state(self, path: str):
        """Load consciousness state from file."""
        data = torch.load(path)
        self.consciousness.load_state_dict(data['model_state'])


class QuickChat:
    """
    Minimal chat interface.
    
    Usage:
        chat = QuickChat()
        print(chat("Hello!"))
        print(chat("What is consciousness?"))
    """
    
    def __init__(self, **kwargs):
        self.api = OmegaAPI(**kwargs)
    
    def __call__(self, message: str) -> str:
        """Chat and return just the text."""
        return self.api.chat(message).text
    
    def with_certainty(self, message: str) -> Tuple[str, float]:
        """Chat and return (text, certainty)."""
        response = self.api.chat(message)
        return response.text, response.certainty


def chat(message: str, **kwargs) -> str:
    """
    One-off chat function.
    
    Creates a new consciousness for each call.
    Use OmegaAPI for persistent conversations.
    """
    api = OmegaAPI(**kwargs)
    return api.chat(message).text


def chat_with_info(message: str, **kwargs) -> ChatResponse:
    """
    One-off chat with full response info.
    """
    api = OmegaAPI(**kwargs)
    return api.chat(message)
