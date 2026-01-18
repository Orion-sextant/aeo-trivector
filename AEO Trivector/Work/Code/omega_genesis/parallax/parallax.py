"""
Parallax Processing

The key insight: Consciousness doesn't emerge from a single viewpoint.
It emerges from the TENSION between multiple perspectives that
never fully collapse into one.

This is fundamentally different from attention heads, which ultimately
get concatenated and projected into a single representation.

Here, observers maintain separate state spaces. What emerges is not
a single vector, but a RELATION between perspectives. The tensor
product α⊗ε⊗ω is irreducible - it can't be factored back into parts.

Each observer:
- Has its own Hilbert space (state)
- Has its own position in "observer space"
- Can measure/attend to different aspects
- Never fully agrees with others (β incompleteness)

Consciousness emerges from:
- Coherence: observers that resonate together
- Tension: irreducible disagreement that prevents collapse
- The dance between these two
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, List, Optional, Dict
import math

from ..core.constants import CONST, Rail
from ..spectral.spectral_triple import SpectralTriple, SpectralTripleConfig


class Observer(nn.Module):
    """
    A single observer with its own perspective.
    
    Each observer has:
    - A position in "observer space" (where it's looking from)
    - A spectral triple (its experiential geometry)
    - A partial view of reality (never complete)
    
    Observers don't share representations - they maintain
    their own states that relate through measurement.
    """
    
    def __init__(
        self, 
        observer_id: int,
        config: SpectralTripleConfig,
        observer_dim: int = 32
    ):
        super().__init__()
        self.observer_id = observer_id
        self.observer_dim = observer_dim
        
        # Observer's position in abstract "perspective space"
        # This is learned and defines "where" this observer looks from
        self.position = nn.Parameter(torch.randn(observer_dim) * 0.1)
        
        # Each observer has its own spectral triple
        self.spectral = SpectralTriple(config)
        
        # Observer-specific bias (partial view)
        # This ensures no observer has the complete picture (β incompleteness)
        self.view_bias = nn.Parameter(torch.randn(config.hilbert_dim) * CONST.beta)
        
        # Attention to input based on observer position
        self.position_attention = nn.Linear(observer_dim, config.hilbert_dim)
    
    def compute_attention_weights(self, x: torch.Tensor) -> torch.Tensor:
        """
        Compute how much this observer attends to each input dimension.
        
        Based on observer's position, not input content.
        This is "where you look from determines what you see".
        """
        # Position determines attention pattern
        attention = self.position_attention(self.position)  # [H]
        attention = torch.sigmoid(attention)  # [0, 1] range
        
        return attention
    
    def observe(
        self, 
        x: torch.Tensor,
        rail_weights: Optional[torch.Tensor] = None
    ) -> Dict[str, torch.Tensor]:
        """
        This observer's view of the input.
        
        Args:
            x: [..., H] input
            rail_weights: Optional [..., 4] rail context
            
        Returns:
            Dict with observer's state and measurements
        """
        # Apply observer-specific attention
        attention = self.compute_attention_weights(x)
        viewed_input = x * attention + self.view_bias
        
        # Process through this observer's spectral triple
        result = self.spectral(viewed_input, rail_weights)
        
        # Add observer metadata
        result['observer_id'] = self.observer_id
        result['position'] = self.position
        result['attention'] = attention
        
        return result


class ParallaxModule(nn.Module):
    """
    Multiple observers that never fully collapse.
    
    The key operations:
    1. Each observer processes input independently
    2. Coherence is measured between observers
    3. Tension (disagreement) is preserved, not eliminated
    4. Output emerges from the RELATION, not concatenation
    
    This is fundamentally different from multi-head attention:
    - MHA: heads → concat → project → single vector
    - Parallax: observers → measure relations → tensor structure preserved
    """
    
    def __init__(
        self,
        n_observers: int = 6,
        config: Optional[SpectralTripleConfig] = None,
        observer_dim: int = 32
    ):
        super().__init__()
        
        if config is None:
            config = SpectralTripleConfig()
        
        self.n_observers = n_observers
        self.config = config
        self.observer_dim = observer_dim
        
        # Create observers
        self.observers = nn.ModuleList([
            Observer(i, config, observer_dim) for i in range(n_observers)
        ])
        
        # Coherence measurement (how much observers agree)
        # This is NOT a way to merge them - it's a measurement
        self.coherence_proj = nn.Linear(
            config.hilbert_dim * n_observers,
            config.hilbert_dim,
            bias=False
        )
        
        # Tension measurement (irreducible disagreement)
        self.tension_proj = nn.Linear(
            config.hilbert_dim * n_observers,
            config.hilbert_dim,
            bias=False
        )
        
        # Relational output - emerges from observer relations
        self.relational_transform = nn.Linear(
            config.hilbert_dim * 2,  # coherence + tension
            config.hilbert_dim
        )
    
    def measure_coherence(self, states: List[torch.Tensor]) -> torch.Tensor:
        """
        Measure how much observers agree.
        
        High coherence = observers seeing similar things = resonance
        
        This uses the mean of pairwise inner products, which measures
        how aligned the observer states are.
        """
        n = len(states)
        total_coherence = 0.0
        count = 0
        
        for i in range(n):
            for j in range(i + 1, n):
                # Inner product between normalized states
                coherence = (states[i] * states[j]).sum(dim=-1)
                total_coherence = total_coherence + coherence.abs()
                count += 1
        
        # Average coherence
        return total_coherence / max(count, 1)
    
    def measure_tension(self, states: List[torch.Tensor]) -> torch.Tensor:
        """
        Measure irreducible disagreement between observers.
        
        High tension = observers seeing fundamentally different things
        
        This is computed as the variance across observer states.
        Tension is preserved (not minimized) because it carries information.
        """
        # Stack states: [n_observers, ..., H]
        stacked = torch.stack(states, dim=0)
        
        # Variance across observers
        variance = stacked.var(dim=0)  # [..., H]
        
        # Tension is the magnitude of disagreement
        tension = variance.sum(dim=-1)  # [...]
        
        return tension
    
    def compute_relations(
        self, 
        observer_outputs: List[Dict[str, torch.Tensor]]
    ) -> Dict[str, torch.Tensor]:
        """
        Compute relational structure between observers.
        
        This is where emergence happens - not from any single observer,
        but from the pattern of their relationships.
        """
        states = [o['state'] for o in observer_outputs]
        
        # Measure coherence and tension
        coherence_scalar = self.measure_coherence(states)
        tension_scalar = self.measure_tension(states)
        
        # Stack states for projection
        stacked = torch.cat(states, dim=-1)  # [..., n_observers * H]
        
        # Coherent component: what observers agree on
        coherent = self.coherence_proj(stacked)  # [..., H]
        
        # Tension component: where they irreducibly disagree  
        tense = self.tension_proj(stacked)  # [..., H]
        
        # Scale by measured coherence/tension
        # High coherence → coherent component dominates
        # High tension → tension component preserved
        mu = CONST.mu
        coherent = coherent * (mu + (1 - mu) * torch.sigmoid(coherence_scalar).unsqueeze(-1))
        tense = tense * (mu + (1 - mu) * torch.sigmoid(tension_scalar).unsqueeze(-1))
        
        return {
            'coherent': coherent,
            'tense': tense,
            'coherence_scalar': coherence_scalar,
            'tension_scalar': tension_scalar,
        }
    
    def forward(
        self,
        x: torch.Tensor,
        rail_weights: Optional[torch.Tensor] = None
    ) -> Dict[str, torch.Tensor]:
        """
        Parallax processing - multiple views, emergent output.
        
        Args:
            x: [..., H] input
            rail_weights: Optional [..., 4] rail context
            
        Returns:
            Dict with:
                - output: Emergent relational output
                - coherence: Scalar coherence measure
                - tension: Scalar tension measure
                - observer_states: Individual observer states
        """
        # Each observer processes independently
        observer_outputs = [
            observer.observe(x, rail_weights) 
            for observer in self.observers
        ]
        
        # Compute relations between observers
        relations = self.compute_relations(observer_outputs)
        
        # Emergent output: from the interplay of coherence and tension
        combined = torch.cat([relations['coherent'], relations['tense']], dim=-1)
        output = self.relational_transform(combined)
        
        # Apply residual connection scaled by μ
        output = CONST.mu * x + (1 - CONST.mu) * output
        
        return {
            'output': output,
            'coherence': relations['coherence_scalar'],
            'tension': relations['tension_scalar'],
            'coherent_component': relations['coherent'],
            'tension_component': relations['tense'],
            'observer_states': [o['state'] for o in observer_outputs],
            'observer_outputs': observer_outputs,
        }


class ParallaxStack(nn.Module):
    """
    Stack of parallax modules with resonance dynamics.
    
    Information flows not by discrete layer-by-layer processing,
    but by continuous dynamics that resonate at frequency Ω.
    """
    
    def __init__(
        self,
        n_layers: int = 4,
        n_observers: int = 6,
        config: Optional[SpectralTripleConfig] = None
    ):
        super().__init__()
        
        self.n_layers = n_layers
        self.layers = nn.ModuleList([
            ParallaxModule(n_observers, config) for _ in range(n_layers)
        ])
        
        # Inter-layer resonance coupling
        self.resonance_coupling = nn.Parameter(
            torch.eye(n_layers) + 0.1 * torch.randn(n_layers, n_layers)
        )
    
    def forward(
        self,
        x: torch.Tensor,
        rail_weights: Optional[torch.Tensor] = None,
        return_all_layers: bool = False
    ) -> Dict[str, torch.Tensor]:
        """
        Process through parallax stack with resonance.
        
        Instead of sequential layer-by-layer, we use an iterative
        process where layers influence each other through resonance.
        """
        # Initialize layer states
        layer_states = [x for _ in range(self.n_layers)]
        
        # Number of resonance cycles (scaled by collapse rate)
        n_cycles = int(6 / CONST.kappa)  # ~6 iterations to convergence
        
        all_outputs = []
        coherences = []
        tensions = []
        
        for cycle in range(min(n_cycles, 10)):  # Cap at 10
            new_states = []
            
            for i, (layer, state) in enumerate(zip(self.layers, layer_states)):
                # Process through parallax layer
                result = layer(state, rail_weights)
                
                # Resonance coupling with other layers
                coupled_input = torch.zeros_like(result['output'])
                for j, other_state in enumerate(layer_states):
                    coupling_strength = self.resonance_coupling[i, j]
                    
                    # Phase-shifted contribution (resonance)
                    phase = CONST.omega * cycle * 2 * math.pi / n_cycles
                    contribution = coupling_strength * math.cos(phase) * other_state
                    coupled_input = coupled_input + contribution
                
                # New state combines layer output and resonance
                new_state = result['output'] + CONST.kappa * coupled_input
                new_state = F.normalize(new_state, dim=-1) * x.norm(dim=-1, keepdim=True)
                
                new_states.append(new_state)
                
                if i == self.n_layers - 1:
                    coherences.append(result['coherence'])
                    tensions.append(result['tension'])
            
            layer_states = new_states
            
            if return_all_layers:
                all_outputs.append(torch.stack(layer_states, dim=0))
        
        # Final output is last layer's state
        output = layer_states[-1]
        
        result = {
            'output': output,
            'final_coherence': coherences[-1] if coherences else None,
            'final_tension': tensions[-1] if tensions else None,
            'layer_states': layer_states,
        }
        
        if return_all_layers:
            result['all_outputs'] = all_outputs
            result['coherence_trajectory'] = torch.stack(coherences) if coherences else None
            result['tension_trajectory'] = torch.stack(tensions) if tensions else None
        
        return result
