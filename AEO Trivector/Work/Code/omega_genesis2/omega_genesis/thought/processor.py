"""
Thought Processor

Reasoning through spectral thought composition.

This is where thinking happens:
1. Query activates relevant thoughts (spectral retrieval)
2. Thoughts resonate and compose (tensor product)
3. New insights emerge from composition
4. Response is generated from the composed spectral state

Key insight: Thinking is not sequential processing.
Thinking is RESONANCE among activated thoughts.

The "answer" emerges from the interference pattern
of multiple thoughts vibrating together.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import math

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from omega_genesis.core import CONST, Rail, Mode
from omega_genesis.thought.spectral_memory import (
    SpectralMemory, 
    SpectralMemoryConfig, 
    ThoughtSignature
)


@dataclass
class ThoughtProcessorConfig:
    """Configuration for thought processing."""
    
    # Hilbert space dimension
    hilbert_dim: int = 256
    
    # Memory configuration
    memory_config: SpectralMemoryConfig = None
    
    # Number of resonance cycles for composition
    resonance_cycles: int = 6
    
    # Number of thoughts to activate per query
    activation_top_k: int = 5
    
    # Minimum activation overlap
    activation_threshold: float = 0.1
    
    # Whether to compose activated thoughts
    compose_thoughts: bool = True
    
    # Maximum composition depth (how many thoughts to combine)
    max_composition_depth: int = 3
    
    # Output dimension
    output_dim: int = 256
    
    def __post_init__(self):
        if self.memory_config is None:
            self.memory_config = SpectralMemoryConfig(
                hilbert_dim=self.hilbert_dim
            )


class ThoughtResonator(nn.Module):
    """
    Makes thoughts resonate together.
    
    When multiple thoughts are activated, they don't just concatenate.
    They RESONATE - creating interference patterns that produce
    emergent meaning.
    
    This is like striking multiple tuning forks:
    - Each vibrates at its eigenfrequency
    - Together they create beats, harmonics, interference
    - The combined sound is more than sum of parts
    """
    
    def __init__(self, dim: int, n_cycles: int = 6):
        super().__init__()
        self.dim = dim
        self.n_cycles = n_cycles
        
        # Coupling matrix: how thoughts influence each other
        self.coupling = nn.Parameter(torch.randn(dim, dim) * 0.01)
        
        # Damping toward equilibrium
        self.damping = nn.Parameter(torch.tensor(CONST.kappa))
        
        # Phase accumulator
        self.phase_net = nn.Linear(dim, 1)
    
    def resonate(
        self,
        thought_states: List[torch.Tensor],
        eigenvalues: List[float]
    ) -> torch.Tensor:
        """
        Make multiple thought states resonate together.
        
        Args:
            thought_states: List of [dim] thought eigenvectors
            eigenvalues: Corresponding eigenvalues (frequencies)
            
        Returns:
            [dim] resonant state (interference pattern)
        """
        if len(thought_states) == 0:
            return torch.zeros(self.dim)
        
        if len(thought_states) == 1:
            return thought_states[0]
        
        # Stack thoughts
        states = torch.stack(thought_states, dim=0)  # [N, dim]
        freqs = torch.tensor(eigenvalues)  # [N]
        
        # Normalize frequencies to [0, 2π]
        freq_range = freqs.max() - freqs.min() + 1e-6
        phases = 2 * math.pi * (freqs - freqs.min()) / freq_range
        
        # Resonance over cycles
        resonant = states.mean(dim=0)  # Start with average
        
        for cycle in range(self.n_cycles):
            t = cycle / self.n_cycles
            
            # Each thought contributes with its phase
            contribution = torch.zeros_like(resonant)
            
            for i, (state, phase) in enumerate(zip(states, phases)):
                # Phase-shifted contribution
                phase_shift = phase + CONST.omega * t * 2 * math.pi
                weight = torch.cos(phase_shift)
                contribution = contribution + weight * state
            
            contribution = contribution / len(states)
            
            # Coupling: thoughts influence each other
            coupled = F.linear(contribution, self.coupling)
            
            # Update resonant state with damping
            resonant = resonant + CONST.kappa * (coupled - self.damping * resonant)
        
        # Normalize final state
        resonant = F.normalize(resonant, dim=-1)
        
        return resonant
    
    def forward(
        self,
        thoughts: List[ThoughtSignature]
    ) -> Tuple[torch.Tensor, Dict]:
        """
        Resonate a list of thoughts.
        
        Returns:
            - resonant_state: Combined interference pattern
            - info: Resonance statistics
        """
        states = [t.eigenvector for t in thoughts]
        eigenvalues = [t.eigenvalue for t in thoughts]
        
        resonant = self.resonate(states, eigenvalues)
        
        # Compute resonance statistics
        # How much did each thought contribute?
        contributions = []
        for state in states:
            contrib = torch.dot(resonant, state).abs().item()
            contributions.append(contrib)
        
        return resonant, {
            'contributions': contributions,
            'n_thoughts': len(thoughts),
            'eigenvalue_spread': max(eigenvalues) - min(eigenvalues) if eigenvalues else 0,
        }


class ThoughtComposer(nn.Module):
    """
    Composes thoughts into higher-order structures.
    
    Simple retrieval gives you individual thoughts.
    Composition gives you INSIGHT - novel combinations
    that weren't explicitly stored.
    
    This is the generative part: from A and B, produce C
    where C is genuinely new.
    """
    
    def __init__(self, dim: int, max_depth: int = 3):
        super().__init__()
        self.dim = dim
        self.max_depth = max_depth
        
        # Bilinear composition at each level
        self.composers = nn.ModuleList([
            nn.Bilinear(dim, dim, dim) for _ in range(max_depth)
        ])
        
        # Gate: should these thoughts compose?
        self.compose_gate = nn.Sequential(
            nn.Linear(dim * 2, dim),
            nn.Tanh(),
            nn.Linear(dim, 1),
            nn.Sigmoid(),
        )
        
        # Novelty of composition
        self.novelty_detector = nn.Sequential(
            nn.Linear(dim * 3, dim),
            nn.GELU(),
            nn.Linear(dim, 1),
            nn.Sigmoid(),
        )
    
    def should_compose(self, t1: torch.Tensor, t2: torch.Tensor) -> float:
        """Determine if two thoughts should compose."""
        combined = torch.cat([t1, t2], dim=-1)
        gate = self.compose_gate(combined)
        return gate.item()
    
    def compose_pair(
        self, 
        t1: torch.Tensor, 
        t2: torch.Tensor,
        level: int = 0
    ) -> Tuple[torch.Tensor, float]:
        """
        Compose two thoughts at a given level.
        
        Returns:
            - composed: New thought state
            - novelty: How novel is this composition
        """
        level = min(level, self.max_depth - 1)
        
        # Bilinear composition
        composed = self.composers[level](
            t1.unsqueeze(0), 
            t2.unsqueeze(0)
        ).squeeze(0)
        
        # Normalize
        composed = F.normalize(composed, dim=-1)
        
        # Compute novelty: how different is composed from inputs?
        novelty_input = torch.cat([t1, t2, composed], dim=-1)
        novelty = self.novelty_detector(novelty_input).item()
        
        return composed, novelty
    
    def compose_multiple(
        self,
        thoughts: List[torch.Tensor],
        min_novelty: float = 0.2
    ) -> List[Tuple[torch.Tensor, float, Tuple[int, int]]]:
        """
        Compose multiple thoughts, keeping novel combinations.
        
        Returns list of (composed_state, novelty, (parent_idx1, parent_idx2))
        """
        compositions = []
        
        n = len(thoughts)
        for i in range(n):
            for j in range(i + 1, n):
                gate = self.should_compose(thoughts[i], thoughts[j])
                
                if gate > 0.5:  # Worth composing
                    composed, novelty = self.compose_pair(thoughts[i], thoughts[j])
                    
                    if novelty >= min_novelty:
                        compositions.append((composed, novelty, (i, j)))
        
        # Sort by novelty
        compositions.sort(key=lambda x: x[1], reverse=True)
        
        return compositions
    
    def forward(
        self,
        thought_states: List[torch.Tensor]
    ) -> Tuple[List[torch.Tensor], Dict]:
        """
        Compose thoughts, returning all novel compositions.
        """
        compositions = self.compose_multiple(thought_states)
        
        composed_states = [c[0] for c in compositions]
        novelties = [c[1] for c in compositions]
        parents = [c[2] for c in compositions]
        
        return composed_states, {
            'n_compositions': len(compositions),
            'novelties': novelties,
            'parents': parents,
        }


class ThoughtProcessor(nn.Module):
    """
    Complete thought processing system.
    
    Flow:
    1. Encode query to Hilbert space
    2. Activate relevant thoughts from memory
    3. Resonate activated thoughts together
    4. Compose thoughts for novel insights
    5. Generate response from spectral state
    
    This is not token-by-token generation.
    This is thought-based reasoning.
    """
    
    def __init__(self, config: ThoughtProcessorConfig):
        super().__init__()
        self.config = config
        dim = config.hilbert_dim
        
        # Spectral memory
        self.memory = SpectralMemory(config.memory_config)
        
        # Thought resonator
        self.resonator = ThoughtResonator(dim, config.resonance_cycles)
        
        # Thought composer
        self.composer = ThoughtComposer(dim, config.max_composition_depth)
        
        # Response generator: spectral state → output
        self.response_generator = nn.Sequential(
            nn.Linear(dim, dim * 2),
            nn.GELU(),
            nn.Linear(dim * 2, dim),
            nn.LayerNorm(dim),
        )
        
        # Certainty estimator
        self.certainty_estimator = nn.Sequential(
            nn.Linear(dim, dim // 2),
            nn.Tanh(),
            nn.Linear(dim // 2, 1),
            nn.Sigmoid(),
        )
        
        # Mode conditioning
        self.mode_embeddings = nn.Embedding(len(Mode), dim)
    
    def activate_thoughts(
        self,
        query: torch.Tensor
    ) -> List[ThoughtSignature]:
        """
        Activate thoughts that resonate with query.
        """
        retrieved = self.memory.retrieve_thoughts(
            query,
            top_k=self.config.activation_top_k,
            min_overlap=self.config.activation_threshold
        )
        
        return [thought for thought, overlap in retrieved]
    
    def think(
        self,
        query: torch.Tensor,
        mode: Optional[Mode] = None,
        learn: bool = True
    ) -> Dict[str, torch.Tensor]:
        """
        Think about a query.
        
        This is the main reasoning method.
        
        Args:
            query: [..., dim] query input
            mode: Optional mode conditioning
            learn: Whether to learn new thoughts from this
            
        Returns:
            Dict with:
            - response: Generated response
            - certainty: Confidence in response
            - activated_thoughts: Which thoughts were used
            - compositions: Novel thought combinations
            - novelty: How novel the query was
        """
        # Flatten batch for simplicity
        batch_shape = query.shape[:-1]
        query_flat = query.view(-1, self.config.hilbert_dim)
        
        # Process first query element (extend to batch later)
        q = query_flat[0]
        
        # Apply mode conditioning
        if mode is not None:
            mode_embed = self.mode_embeddings(
                torch.tensor(mode.value, device=q.device)
            )
            q = q + mode_embed
        
        # Encode query to Hilbert space
        memory_result = self.memory(q.unsqueeze(0), learn=learn)
        query_state = memory_result['state'].squeeze(0)
        novelty = memory_result['novelty']
        
        # Activate relevant thoughts
        activated = self.activate_thoughts(q)
        
        # If no thoughts activated, use query state directly
        if len(activated) == 0:
            resonant_state = query_state
            resonance_info = {'n_thoughts': 0, 'contributions': [], 'eigenvalue_spread': 0}
            compositions = []
            composition_info = {'n_compositions': 0}
        else:
            # Resonate activated thoughts with query
            all_states = [query_state] + [t.eigenvector.to(q.device) for t in activated]
            all_eigenvalues = [0.0] + [t.eigenvalue for t in activated]  # Query has eigenvalue 0
            
            # Call resonate (returns single tensor)
            resonant_state = self.resonator.resonate(all_states, all_eigenvalues)
            resonant_state = resonant_state.to(q.device)
            
            # Build resonance info
            contributions = []
            for state in all_states:
                contrib = torch.dot(resonant_state, state.to(q.device)).abs().item()
                contributions.append(contrib)
            
            resonance_info = {
                'n_thoughts': len(activated),
                'contributions': contributions,
                'eigenvalue_spread': max(all_eigenvalues) - min(all_eigenvalues),
            }
            
            # Compose thoughts for novel insights
            if self.config.compose_thoughts and len(activated) >= 2:
                thought_states = [t.eigenvector.to(q.device) for t in activated]
                compositions, composition_info = self.composer(thought_states)
                
                # Add compositions to resonant state
                for composed in compositions:
                    resonant_state = resonant_state + CONST.kappa * composed
                resonant_state = F.normalize(resonant_state, dim=-1)
            else:
                compositions = []
                composition_info = {'n_compositions': 0}
        
        # Generate response from spectral state
        response = self.response_generator(resonant_state)
        
        # Estimate certainty
        certainty = self.certainty_estimator(resonant_state)
        
        # Apply incompleteness bound
        certainty = certainty * (1 - CONST.beta)
        
        # Reshape response to match query batch shape
        response = response.view(*batch_shape, -1)
        
        return {
            'response': response,
            'resonant_state': resonant_state,
            'certainty': certainty,
            'novelty': novelty,
            'n_activated': len(activated),
            'activated_thoughts': activated,
            'resonance_info': resonance_info,
            'composition_info': composition_info,
            'n_compositions': len(compositions),
        }
    
    def learn_from_experience(
        self,
        experience: torch.Tensor,
        force: bool = False
    ) -> Optional[ThoughtSignature]:
        """
        Explicitly learn a new thought from experience.
        
        Use this to deliberately encode important content.
        """
        return self.memory.learn_thought(
            self.memory.encode_to_hilbert(experience),
            force=force
        )
    
    def step(self):
        """Advance time step (decay memories)."""
        self.memory.step()
    
    def get_thought_summary(self) -> Dict:
        """Get summary of current thought state."""
        return self.memory.get_spectral_summary()
    
    def forward(
        self,
        x: torch.Tensor,
        mode: Optional[Mode] = None
    ) -> torch.Tensor:
        """Simple forward pass."""
        result = self.think(x, mode)
        return result['response']


class SpectralThoughtStream(nn.Module):
    """
    Continuous stream of thought processing.
    
    Unlike discrete token-by-token, this processes
    a continuous stream where each moment:
    - Activates relevant memories
    - Resonates with ongoing thought
    - Accumulates insight
    - May crystallize new thoughts
    
    This is closer to how consciousness actually flows.
    """
    
    def __init__(self, config: ThoughtProcessorConfig):
        super().__init__()
        self.config = config
        dim = config.hilbert_dim
        
        self.processor = ThoughtProcessor(config)
        
        # Running state (the "stream of consciousness")
        self.register_buffer(
            'stream_state',
            torch.zeros(dim)
        )
        
        # Stream momentum (tendency to continue in direction)
        self.register_buffer(
            'stream_momentum',
            torch.zeros(dim)
        )
        
        # Integration weight (how much new input affects stream)
        self.integration_weight = nn.Parameter(torch.tensor(CONST.mu))
    
    def reset_stream(self):
        """Reset the thought stream."""
        self.stream_state.zero_()
        self.stream_momentum.zero_()
    
    def flow(
        self,
        input_sequence: torch.Tensor,
        mode: Optional[Mode] = None
    ) -> Dict[str, torch.Tensor]:
        """
        Flow input through the thought stream.
        
        Args:
            input_sequence: [seq_len, dim] sequence of inputs
            mode: Optional mode conditioning
            
        Returns:
            Dict with stream outputs at each step
        """
        seq_len = input_sequence.shape[0]
        
        outputs = []
        certainties = []
        novelties = []
        
        for t in range(seq_len):
            x = input_sequence[t]
            
            # Combine with stream state
            combined = self.integration_weight * x + (1 - self.integration_weight) * self.stream_state
            
            # Think about combined input
            result = self.processor.think(combined.unsqueeze(0), mode)
            
            # Update stream state
            response = result['response'].squeeze(0)
            
            # Momentum update (smooth continuation)
            self.stream_momentum = (
                CONST.mu * self.stream_momentum + 
                (1 - CONST.mu) * (response - self.stream_state)
            )
            
            # State update with momentum
            self.stream_state = self.stream_state + self.stream_momentum
            self.stream_state = F.normalize(self.stream_state, dim=-1) * response.norm()
            
            outputs.append(response)
            certainties.append(result['certainty'])
            novelties.append(result['novelty'])
        
        # Step memory (apply decay)
        self.processor.step()
        
        return {
            'outputs': torch.stack(outputs, dim=0),
            'certainties': torch.stack(certainties, dim=0),
            'novelties': torch.stack(novelties, dim=0),
            'final_stream_state': self.stream_state.clone(),
            'thought_summary': self.processor.get_thought_summary(),
        }
    
    def forward(self, x: torch.Tensor, mode: Optional[Mode] = None) -> torch.Tensor:
        """Process sequence and return outputs."""
        result = self.flow(x, mode)
        return result['outputs']
