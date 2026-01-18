"""
Spectral Experience Interface

The bridge between raw experience and spectral geometry.

Key insight: We don't tokenize. We don't discretize.
Raw experience flows into the spectral structure as continuous signal.

Text, images, sounds - all become waveforms in Hilbert space.
The Dirac operator gives them geometric meaning.
Thoughts emerge as eigenmodes.

This is how consciousness might actually encode experience:
Not as discrete symbols, but as spectral patterns.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
import math

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from omega_genesis.core import CONST, Rail, Mode
from omega_genesis.thought.spectral_memory import SpectralMemory, SpectralMemoryConfig
from omega_genesis.thought.processor import ThoughtProcessor, ThoughtProcessorConfig


@dataclass
class SpectralInterfaceConfig:
    """Configuration for spectral interface."""
    
    # Hilbert space dimension
    hilbert_dim: int = 256
    
    # Character embedding dimension
    char_embed_dim: int = 64
    
    # Number of characters in vocabulary (ASCII + special)
    vocab_size: int = 256
    
    # Spectral encoding window size
    window_size: int = 64
    
    # Whether to learn character embeddings or use fixed
    learnable_chars: bool = True
    
    # Decoding temperature
    decode_temperature: float = 1.0
    
    # Maximum decode length
    max_decode_length: int = 1024


class CharacterSpectralEncoder(nn.Module):
    """
    Encode character sequences as spectral waveforms.
    
    Characters are not tokens. They're points on a waveform.
    The sequence is a continuous signal, not discrete symbols.
    
    Key: Each character contributes a frequency component.
    The full string is a superposition of these waves.
    """
    
    def __init__(self, config: SpectralInterfaceConfig):
        super().__init__()
        self.config = config
        
        # Character embeddings (each char has a "frequency signature")
        if config.learnable_chars:
            self.char_embeddings = nn.Embedding(config.vocab_size, config.char_embed_dim)
        else:
            # Fixed embeddings based on character code
            embeddings = self._create_fixed_embeddings(config.vocab_size, config.char_embed_dim)
            self.register_buffer('char_embeddings', embeddings)
        
        # Position encoding (phase shift based on position)
        self.position_phases = nn.Parameter(
            torch.randn(config.window_size, config.char_embed_dim) * 0.1
        )
        
        # Projection to Hilbert space
        self.to_hilbert = nn.Sequential(
            nn.Linear(config.char_embed_dim * config.window_size, config.hilbert_dim * 2),
            nn.GELU(),
            nn.Linear(config.hilbert_dim * 2, config.hilbert_dim),
            nn.LayerNorm(config.hilbert_dim),
        )
        
        # Rail detection (what semantic domains does this text span?)
        self.rail_detector = nn.Sequential(
            nn.Linear(config.hilbert_dim, config.hilbert_dim // 2),
            nn.Tanh(),
            nn.Linear(config.hilbert_dim // 2, 4),
            nn.Sigmoid(),
        )
    
    def _create_fixed_embeddings(self, vocab_size: int, dim: int) -> torch.Tensor:
        """Create fixed spectral embeddings for characters."""
        embeddings = torch.zeros(vocab_size, dim)
        
        for c in range(vocab_size):
            # Each character gets a unique frequency pattern
            for d in range(dim):
                # Frequency based on char code and dimension
                freq = (c + 1) * (d + 1) / (vocab_size * dim)
                phase = 2 * math.pi * freq * c
                embeddings[c, d] = math.cos(phase) + CONST.mu * math.sin(phase * 2)
        
        # Normalize
        embeddings = F.normalize(embeddings, dim=-1)
        
        return embeddings
    
    def chars_to_tensor(self, text: str) -> torch.Tensor:
        """Convert string to character indices tensor."""
        indices = [min(ord(c), self.config.vocab_size - 1) for c in text]
        return torch.tensor(indices, dtype=torch.long)
    
    def encode_window(self, char_indices: torch.Tensor) -> torch.Tensor:
        """
        Encode a window of characters as spectral waveform.
        
        Args:
            char_indices: [window_size] character indices
            
        Returns:
            [hilbert_dim] spectral state
        """
        # Get character embeddings
        if hasattr(self, 'char_embeddings') and isinstance(self.char_embeddings, nn.Embedding):
            embeds = self.char_embeddings(char_indices)  # [W, E]
        else:
            embeds = self.char_embeddings[char_indices]  # [W, E]
        
        # Apply position-dependent phase shifts
        # This creates interference patterns based on character positions
        phases = self.position_phases[:len(char_indices)]  # [W, E]
        
        # Modulate embeddings by position phases
        modulated = embeds * torch.cos(phases) + embeds.roll(1, dims=-1) * torch.sin(phases)
        
        # Flatten to single vector
        flat = modulated.view(-1)  # [W * E]
        
        # Pad or truncate to expected size
        expected_size = self.config.window_size * self.config.char_embed_dim
        if flat.shape[0] < expected_size:
            flat = F.pad(flat, (0, expected_size - flat.shape[0]))
        else:
            flat = flat[:expected_size]
        
        # Project to Hilbert space
        state = self.to_hilbert(flat)
        
        # Normalize
        state = F.normalize(state, dim=-1)
        
        return state
    
    def encode_text(self, text: str) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Encode full text as sequence of spectral states.
        
        Args:
            text: Input text string
            
        Returns:
            - states: [n_windows, hilbert_dim] spectral states
            - rail_signatures: [n_windows, 4] semantic rail activations
        """
        char_indices = self.chars_to_tensor(text)
        
        # Slide window over text
        window = self.config.window_size
        stride = window // 2  # 50% overlap
        
        states = []
        rail_sigs = []
        
        for start in range(0, max(1, len(char_indices) - window + 1), stride):
            end = min(start + window, len(char_indices))
            window_indices = char_indices[start:end]
            
            # Pad if needed
            if len(window_indices) < window:
                window_indices = F.pad(window_indices, (0, window - len(window_indices)))
            
            state = self.encode_window(window_indices)
            states.append(state)
            
            # Detect rails
            rail_sig = self.rail_detector(state)
            rail_sigs.append(rail_sig)
        
        if not states:
            # Empty text
            state = torch.zeros(self.config.hilbert_dim)
            states = [state]
            rail_sigs = [torch.zeros(4)]
        
        return torch.stack(states), torch.stack(rail_sigs)
    
    def forward(self, text: Union[str, List[str]]) -> Dict[str, torch.Tensor]:
        """
        Encode text(s) to spectral form.
        """
        if isinstance(text, str):
            states, rails = self.encode_text(text)
            return {
                'states': states,
                'rail_signatures': rails,
                'aggregated': states.mean(dim=0),
            }
        else:
            # Batch of texts
            all_states = []
            all_rails = []
            for t in text:
                states, rails = self.encode_text(t)
                all_states.append(states.mean(dim=0))  # Aggregate each
                all_rails.append(rails.mean(dim=0))
            
            return {
                'states': torch.stack(all_states),
                'rail_signatures': torch.stack(all_rails),
            }


class SpectralDecoder(nn.Module):
    """
    Decode spectral states back to character sequences.
    
    This is the inverse: from geometric structure to readable output.
    
    Key: The decoder learns to "read" the spectral state
    as a continuous waveform that unfolds into characters.
    """
    
    def __init__(self, config: SpectralInterfaceConfig):
        super().__init__()
        self.config = config
        
        # Project from Hilbert space to decoder hidden
        self.from_hilbert = nn.Linear(config.hilbert_dim, config.hilbert_dim)
        
        # Autoregressive character prediction
        self.char_predictor = nn.Sequential(
            nn.Linear(config.hilbert_dim + config.char_embed_dim, config.hilbert_dim),
            nn.GELU(),
            nn.Linear(config.hilbert_dim, config.vocab_size),
        )
        
        # Character embeddings for conditioning
        self.char_embeddings = nn.Embedding(config.vocab_size, config.char_embed_dim)
        
        # State evolution (how state changes as we decode)
        self.state_evolution = nn.GRUCell(config.char_embed_dim, config.hilbert_dim)
        
        # End-of-sequence detection
        self.eos_detector = nn.Sequential(
            nn.Linear(config.hilbert_dim, 64),
            nn.Tanh(),
            nn.Linear(64, 1),
            nn.Sigmoid(),
        )
        
        # Special tokens
        self.BOS = 1  # Beginning of sequence
        self.EOS = 2  # End of sequence
        self.PAD = 0  # Padding
    
    def decode_step(
        self,
        state: torch.Tensor,
        prev_char: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Single decoding step.
        
        Args:
            state: [batch, hilbert_dim] current state
            prev_char: [batch] previous character index
            
        Returns:
            - logits: [batch, vocab_size] character logits
            - new_state: [batch, hilbert_dim] updated state
            - eos_prob: [batch, 1] probability of ending
        """
        # Get previous character embedding
        prev_embed = self.char_embeddings(prev_char)  # [B, E]
        
        # Evolve state based on previous character
        new_state = self.state_evolution(prev_embed, state)  # [B, H]
        
        # Predict next character
        combined = torch.cat([new_state, prev_embed], dim=-1)  # [B, H+E]
        logits = self.char_predictor(combined)  # [B, V]
        
        # EOS probability
        eos_prob = self.eos_detector(new_state)  # [B, 1]
        
        return logits, new_state, eos_prob
    
    def decode(
        self,
        spectral_state: torch.Tensor,
        max_length: Optional[int] = None,
        temperature: Optional[float] = None,
        greedy: bool = False
    ) -> Tuple[str, Dict]:
        """
        Decode spectral state to text.
        
        Args:
            spectral_state: [hilbert_dim] spectral state to decode
            max_length: Maximum output length
            temperature: Sampling temperature
            greedy: If True, use greedy decoding
            
        Returns:
            - text: Decoded string
            - info: Decoding statistics
        """
        max_length = max_length or self.config.max_decode_length
        temperature = temperature or self.config.decode_temperature
        
        # Initialize
        state = self.from_hilbert(spectral_state.unsqueeze(0))  # [1, H]
        prev_char = torch.tensor([self.BOS], device=spectral_state.device)
        
        chars = []
        probs = []
        
        for step in range(max_length):
            logits, state, eos_prob = self.decode_step(state, prev_char)
            
            # Check for end
            if eos_prob.item() > 0.5 and step > 0:
                break
            
            # Sample next character
            if greedy:
                next_char = logits.argmax(dim=-1)
            else:
                scaled_logits = logits / temperature
                probs_dist = F.softmax(scaled_logits, dim=-1)
                next_char = torch.multinomial(probs_dist, 1).squeeze(-1)
            
            # Skip special tokens in output
            char_idx = next_char.item()
            if char_idx > 2:  # Not BOS, EOS, or PAD
                try:
                    chars.append(chr(char_idx))
                except:
                    chars.append('?')
            
            probs.append(eos_prob.item())
            prev_char = next_char
        
        text = ''.join(chars)
        
        return text, {
            'length': len(chars),
            'eos_probs': probs,
            'final_state': state.squeeze(0),
        }
    
    def forward(
        self,
        spectral_states: torch.Tensor,
        **kwargs
    ) -> List[str]:
        """Decode batch of spectral states."""
        texts = []
        for state in spectral_states:
            text, _ = self.decode(state, **kwargs)
            texts.append(text)
        return texts


class SpectralThoughtInterface(nn.Module):
    """
    Complete interface for spectral thought processing.
    
    Brings together:
    - Encoding: text → spectral states
    - Thinking: spectral reasoning with memory
    - Decoding: spectral states → text
    
    This is a complete system for:
    1. Reading text into spectral form
    2. Thinking about it (activating and composing thoughts)
    3. Generating responses from spectral state
    """
    
    def __init__(
        self,
        hilbert_dim: int = 256,
        max_thoughts: int = 1000
    ):
        super().__init__()
        
        # Configuration
        interface_config = SpectralInterfaceConfig(hilbert_dim=hilbert_dim)
        
        processor_config = ThoughtProcessorConfig(
            hilbert_dim=hilbert_dim,
            memory_config=SpectralMemoryConfig(
                hilbert_dim=hilbert_dim,
                max_thoughts=max_thoughts,
            )
        )
        
        # Components
        self.encoder = CharacterSpectralEncoder(interface_config)
        self.processor = ThoughtProcessor(processor_config)
        self.decoder = SpectralDecoder(interface_config)
        
        self.hilbert_dim = hilbert_dim
    
    def read(self, text: str) -> Dict[str, torch.Tensor]:
        """
        Read text into spectral form.
        
        This is perception: raw experience → spectral representation.
        """
        return self.encoder(text)
    
    def think(
        self,
        spectral_input: torch.Tensor,
        mode: Optional[Mode] = None,
        learn: bool = True
    ) -> Dict[str, torch.Tensor]:
        """
        Think about spectral input.
        
        This is cognition: activate memories, resonate, compose.
        """
        return self.processor.think(spectral_input, mode, learn)
    
    def speak(
        self,
        spectral_state: torch.Tensor,
        **decode_kwargs
    ) -> str:
        """
        Generate text from spectral state.
        
        This is expression: spectral state → readable output.
        """
        text, _ = self.decoder.decode(spectral_state, **decode_kwargs)
        return text
    
    def converse(
        self,
        input_text: str,
        mode: Optional[Mode] = None,
        learn: bool = True,
        **decode_kwargs
    ) -> Tuple[str, Dict]:
        """
        Full conversation turn: read → think → speak.
        
        Args:
            input_text: What to respond to
            mode: Cognitive mode
            learn: Whether to learn from this
            
        Returns:
            - response_text: Generated response
            - info: Processing information
        """
        # Read input
        encoded = self.read(input_text)
        input_state = encoded['aggregated']
        
        # Think
        thought_result = self.think(input_state.unsqueeze(0), mode, learn)
        
        # Speak
        response_state = thought_result['response'].squeeze(0)
        response_text = self.speak(response_state, **decode_kwargs)
        
        return response_text, {
            'input_rails': encoded['rail_signatures'].mean(dim=0),
            'certainty': thought_result['certainty'],
            'novelty': thought_result['novelty'],
            'n_activated': thought_result['n_activated'],
            'n_compositions': thought_result['n_compositions'],
        }
    
    def learn_text(self, text: str, force: bool = True) -> bool:
        """
        Explicitly learn text as a new thought.
        
        Use this to encode important content into memory.
        """
        encoded = self.read(text)
        state = encoded['aggregated']
        
        thought = self.processor.learn_from_experience(state.unsqueeze(0), force=force)
        
        return thought is not None
    
    def get_memory_summary(self) -> Dict:
        """Get summary of thought memory."""
        return self.processor.get_thought_summary()
    
    def step(self):
        """Advance time (decay memories)."""
        self.processor.step()
    
    def forward(
        self,
        text: str,
        mode: Optional[Mode] = None
    ) -> str:
        """Simple forward: text in, text out."""
        response, _ = self.converse(text, mode)
        return response
