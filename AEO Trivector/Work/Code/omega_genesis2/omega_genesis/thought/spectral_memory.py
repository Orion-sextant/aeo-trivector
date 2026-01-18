"""
Spectral Thought Encoding

The key insight: Thoughts are not vectors to be stored and retrieved.
Thoughts are GEOMETRIC STRUCTURES that modify the experiential manifold.

When you learn something, you don't add a vector to memory.
You change the SHAPE of experiential space.

A thought T is encoded as:
- An eigenvalue λ_T of the Dirac operator (its "frequency")
- An eigenspace span{v_T} (its "direction" in experience)
- A projection P_T = |v_T⟩⟨v_T| (its "presence" operator)

Learning a new thought means:
1. Experience creates a state ψ in Hilbert space
2. Decompose ψ in current eigenbasis of 𝒟
3. Compute residual: what's NOT explained by current eigenmodes
4. If residual is significant → new thought → new eigenmode
5. Update 𝒟 with the new geometric structure

This is fundamentally different:
- Transformers: learn weights that transform fixed vectors
- Memory networks: store vectors in external slots
- Here: the GEOMETRY learns. The spectrum evolves.

The Dirac operator grows as thoughts accumulate:
    𝒟 = 𝒟_base + Σᵢ strength_i · P_i

Each thought contributes its projection operator scaled by how
entrenched (how often reinforced) it is.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Optional, Tuple, NamedTuple
from dataclasses import dataclass, field
import math

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from omega_genesis.core import CONST, Rail, Mode


@dataclass
class ThoughtSignature:
    """
    The spectral signature of a thought.
    
    A thought is not a vector. It's a geometric structure.
    """
    # Unique identifier
    thought_id: int
    
    # Eigenvalue (the thought's "frequency" in experience)
    eigenvalue: float
    
    # Eigenvector (the thought's "direction" in Hilbert space)
    eigenvector: torch.Tensor
    
    # Strength (how entrenched - increases with reinforcement)
    strength: float = 1.0
    
    # Rail signature (which semantic domains it spans)
    rail_signature: torch.Tensor = None
    
    # Certainty (how well-defined this thought is)
    certainty: float = 0.5
    
    # Creation timestamp (for temporal ordering)
    created_step: int = 0
    
    # Access count (for importance weighting)
    access_count: int = 0
    
    def projection_operator(self) -> torch.Tensor:
        """
        Compute |v⟩⟨v| projection operator.
        
        This is how this thought "projects" onto experience.
        """
        v = self.eigenvector
        if v.dim() == 1:
            v = v.unsqueeze(0)
        # |v⟩⟨v| = v @ v^T (outer product)
        return torch.outer(v.squeeze(), v.squeeze())
    
    def overlap_with(self, state: torch.Tensor) -> float:
        """
        Compute how much this thought overlaps with a state.
        
        ⟨ψ|P|ψ⟩ = |⟨v|ψ⟩|²
        """
        v = self.eigenvector.squeeze()
        psi = state.squeeze()
        inner = torch.dot(v, psi)
        return (inner.abs() ** 2).item()


@dataclass 
class SpectralMemoryConfig:
    """Configuration for spectral thought memory."""
    
    # Hilbert space dimension
    hilbert_dim: int = 256
    
    # Maximum number of thoughts (eigenmodes)
    max_thoughts: int = 1000
    
    # Threshold for creating new thought (residual norm)
    novelty_threshold: float = 0.3
    
    # Minimum strength before thought fades
    fade_threshold: float = 0.01
    
    # Strength decay rate per step
    decay_rate: float = 0.001
    
    # Reinforcement boost when thought is accessed
    reinforcement_boost: float = 0.1
    
    # Whether to allow thought composition
    allow_composition: bool = True
    
    # Number of rails for semantic space
    n_rails: int = 4


class SpectralMemory(nn.Module):
    """
    Memory as evolving spectral geometry.
    
    The Dirac operator 𝒟 encodes all learned thoughts.
    Its eigenspectrum IS the memory.
    
    𝒟 = 𝒟_base + Σᵢ strength_i · shift_i · P_i
    
    Where:
    - 𝒟_base: innate geometric structure
    - P_i: projection onto thought i's eigenspace
    - shift_i: how much thought i shifts the eigenvalue
    - strength_i: how entrenched thought i is
    """
    
    def __init__(self, config: SpectralMemoryConfig):
        super().__init__()
        self.config = config
        dim = config.hilbert_dim
        
        # Base Dirac operator (innate geometry)
        # Initialize as a structured matrix that defines base experiential space
        base_dirac = self._create_base_dirac(dim)
        self.register_buffer('dirac_base', base_dirac)
        
        # Learned thought storage
        self.thoughts: List[ThoughtSignature] = []
        self.next_thought_id = 0
        self.current_step = 0
        
        # Projection for encoding input to Hilbert space
        self.input_encoder = nn.Sequential(
            nn.Linear(dim, dim * 2),
            nn.GELU(),
            nn.Linear(dim * 2, dim),
            nn.LayerNorm(dim),
        )
        
        # Rail projection
        self.rail_projector = nn.Linear(dim, config.n_rails)
        
        # Composition network (for combining thoughts)
        self.composer = nn.Bilinear(dim, dim, dim)
        
        # Novelty detector
        self.novelty_net = nn.Sequential(
            nn.Linear(dim, dim // 2),
            nn.Tanh(),
            nn.Linear(dim // 2, 1),
            nn.Sigmoid(),
        )
    
    def _create_base_dirac(self, dim: int) -> torch.Tensor:
        """
        Create base Dirac operator with meaningful structure.
        
        Uses a combination of:
        - Discrete derivative (captures gradients)
        - Mass term scaled by μ
        - Slight randomness for symmetry breaking
        """
        # Tridiagonal structure (like 1D Dirac on lattice)
        dirac = torch.zeros(dim, dim)
        
        for i in range(dim - 1):
            # Off-diagonal: derivative structure
            dirac[i, i + 1] = 1.0
            dirac[i + 1, i] = -1.0
        
        # Diagonal: mass term
        for i in range(dim):
            dirac[i, i] = CONST.mu * (2 * (i / dim) - 1)  # Varies with position
        
        # Make self-adjoint
        dirac = 0.5 * (dirac + dirac.T)
        
        return dirac
    
    @property
    def dirac(self) -> torch.Tensor:
        """
        Current Dirac operator including all learned thoughts.
        
        𝒟 = 𝒟_base + Σᵢ strength_i · λ_i · P_i
        """
        D = self.dirac_base.clone()
        
        for thought in self.thoughts:
            if thought.strength > self.config.fade_threshold:
                P = thought.projection_operator().to(D.device)
                # Add thought's contribution: shifts eigenvalue in its direction
                D = D + thought.strength * thought.eigenvalue * P
        
        # Ensure self-adjoint
        D = 0.5 * (D + D.T)
        
        return D
    
    def encode_to_hilbert(self, x: torch.Tensor) -> torch.Tensor:
        """
        Project input into Hilbert space as a normalized state.
        
        Args:
            x: [..., dim] input
            
        Returns:
            [..., dim] unit state vector in Hilbert space
        """
        state = self.input_encoder(x)
        # Normalize to unit vector (states are rays)
        state = F.normalize(state, p=2, dim=-1)
        return state
    
    def decompose_in_eigenbasis(
        self, 
        state: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Decompose state in current Dirac eigenbasis.
        
        Returns:
            - coefficients: [..., dim] expansion coefficients
            - eigenvalues: [dim] current eigenvalues
            - eigenvectors: [dim, dim] current eigenvectors
        """
        # Get current eigenspectrum
        eigenvalues, eigenvectors = torch.linalg.eigh(self.dirac)
        
        # Project state onto each eigenvector
        # state: [..., dim], eigenvectors: [dim, dim]
        # coefficients: [..., dim]
        coefficients = torch.einsum('...d,de->...e', state, eigenvectors)
        
        return coefficients, eigenvalues, eigenvectors
    
    def compute_residual(self, state: torch.Tensor) -> Tuple[torch.Tensor, float]:
        """
        Compute what part of state is NOT explained by existing thoughts.
        
        The residual is the novel content that might become a new thought.
        """
        if len(self.thoughts) == 0:
            # Everything is novel if no thoughts yet
            return state, 1.0
        
        # Project out all existing thought directions
        residual = state.clone()
        
        for thought in self.thoughts:
            if thought.strength > self.config.fade_threshold:
                v = thought.eigenvector.to(state.device)
                # Remove component along this thought
                overlap = torch.einsum('...d,d->...', state, v)
                projection = torch.einsum('...,d->...d', overlap, v)
                residual = residual - projection
        
        # Normalize residual
        residual_norm = residual.norm(dim=-1, keepdim=True)
        
        # Novelty is the fraction of state not explained
        state_norm = state.norm(dim=-1, keepdim=True)
        novelty = (residual_norm / (state_norm + 1e-6)).mean().item()
        
        return residual, novelty
    
    def create_thought(
        self, 
        state: torch.Tensor,
        rail_signature: Optional[torch.Tensor] = None
    ) -> ThoughtSignature:
        """
        Create a new thought from a state.
        
        The state becomes a new eigenmode of the Dirac operator.
        """
        # Normalize to get eigenvector
        eigenvector = F.normalize(state.mean(dim=0) if state.dim() > 1 else state, dim=-1)
        
        # Compute eigenvalue: use Rayleigh quotient with current Dirac
        # λ = ⟨v|𝒟|v⟩
        Dv = F.linear(eigenvector, self.dirac)
        eigenvalue = torch.dot(eigenvector, Dv).item()
        
        # Compute rail signature if not provided
        if rail_signature is None:
            with torch.no_grad():
                rail_signature = torch.sigmoid(self.rail_projector(eigenvector))
        
        thought = ThoughtSignature(
            thought_id=self.next_thought_id,
            eigenvalue=eigenvalue,
            eigenvector=eigenvector.detach().clone(),
            strength=1.0,
            rail_signature=rail_signature.detach().clone(),
            certainty=CONST.mu,  # Start at equilibrium certainty
            created_step=self.current_step,
            access_count=1,
        )
        
        self.next_thought_id += 1
        return thought
    
    def learn_thought(
        self, 
        state: torch.Tensor,
        force: bool = False
    ) -> Optional[ThoughtSignature]:
        """
        Potentially learn a new thought from experience.
        
        Only creates a thought if the residual (novelty) is high enough.
        
        Args:
            state: [..., dim] experiential state
            force: If True, always create thought regardless of novelty
            
        Returns:
            New thought if created, None otherwise
        """
        residual, novelty = self.compute_residual(state)
        
        # Check if novel enough
        if not force and novelty < self.config.novelty_threshold:
            return None
        
        # Check capacity
        if len(self.thoughts) >= self.config.max_thoughts:
            # Remove weakest thought to make room
            self._prune_weakest_thought()
        
        # Create new thought from residual
        thought = self.create_thought(residual)
        self.thoughts.append(thought)
        
        return thought
    
    def retrieve_thoughts(
        self,
        query: torch.Tensor,
        top_k: int = 5,
        min_overlap: float = 0.1
    ) -> List[Tuple[ThoughtSignature, float]]:
        """
        Retrieve thoughts that resonate with a query.
        
        Uses spectral overlap: how much does query project onto each thought?
        """
        query_state = self.encode_to_hilbert(query)
        
        results = []
        for thought in self.thoughts:
            if thought.strength > self.config.fade_threshold:
                overlap = thought.overlap_with(query_state)
                
                if overlap >= min_overlap:
                    results.append((thought, overlap))
                    # Reinforce accessed thought
                    thought.access_count += 1
                    thought.strength += self.config.reinforcement_boost
                    thought.strength = min(thought.strength, 10.0)  # Cap strength
        
        # Sort by overlap
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:top_k]
    
    def compose_thoughts(
        self,
        thought1: ThoughtSignature,
        thought2: ThoughtSignature
    ) -> ThoughtSignature:
        """
        Compose two thoughts into a new emergent thought.
        
        This is the tensor product α⊗ε⊗ω at the thought level.
        """
        if not self.config.allow_composition:
            raise ValueError("Thought composition not enabled")
        
        v1 = thought1.eigenvector
        v2 = thought2.eigenvector
        
        # Compose via bilinear mixing
        composed = self.composer(v1.unsqueeze(0), v2.unsqueeze(0)).squeeze(0)
        composed = F.normalize(composed, dim=-1)
        
        # New eigenvalue: geometric mean scaled by μ
        new_eigenvalue = CONST.mu * math.sqrt(abs(thought1.eigenvalue * thought2.eigenvalue))
        if thought1.eigenvalue * thought2.eigenvalue < 0:
            new_eigenvalue = -new_eigenvalue
        
        # Rail signature: blend
        rail_sig = CONST.mu * thought1.rail_signature + (1 - CONST.mu) * thought2.rail_signature
        
        # Certainty: minimum of parents (can't be more certain than inputs)
        certainty = min(thought1.certainty, thought2.certainty) * (1 - CONST.beta)
        
        composed_thought = ThoughtSignature(
            thought_id=self.next_thought_id,
            eigenvalue=new_eigenvalue,
            eigenvector=composed.detach(),
            strength=0.5 * (thought1.strength + thought2.strength),
            rail_signature=rail_sig,
            certainty=certainty,
            created_step=self.current_step,
            access_count=0,
        )
        
        self.next_thought_id += 1
        self.thoughts.append(composed_thought)
        
        return composed_thought
    
    def step(self):
        """
        Advance time step. Apply decay to all thoughts.
        """
        self.current_step += 1
        
        for thought in self.thoughts:
            # Decay strength
            thought.strength *= (1 - self.config.decay_rate)
        
        # Remove faded thoughts
        self.thoughts = [
            t for t in self.thoughts 
            if t.strength > self.config.fade_threshold
        ]
    
    def _prune_weakest_thought(self):
        """Remove the weakest thought to make room for new one."""
        if not self.thoughts:
            return
        
        # Find thought with lowest strength * certainty * access_count
        def importance(t):
            return t.strength * t.certainty * (1 + math.log1p(t.access_count))
        
        weakest_idx = min(range(len(self.thoughts)), key=lambda i: importance(self.thoughts[i]))
        self.thoughts.pop(weakest_idx)
    
    def get_spectral_summary(self) -> Dict:
        """Get summary of current spectral state."""
        if not self.thoughts:
            return {
                'n_thoughts': 0,
                'eigenvalue_range': (0, 0),
                'total_strength': 0,
                'mean_certainty': 0,
            }
        
        eigenvalues = [t.eigenvalue for t in self.thoughts]
        strengths = [t.strength for t in self.thoughts]
        certainties = [t.certainty for t in self.thoughts]
        
        return {
            'n_thoughts': len(self.thoughts),
            'eigenvalue_range': (min(eigenvalues), max(eigenvalues)),
            'total_strength': sum(strengths),
            'mean_certainty': sum(certainties) / len(certainties),
            'mean_access_count': sum(t.access_count for t in self.thoughts) / len(self.thoughts),
        }
    
    def forward(
        self,
        x: torch.Tensor,
        learn: bool = True
    ) -> Dict[str, torch.Tensor]:
        """
        Process input through spectral memory.
        
        Args:
            x: [..., dim] input
            learn: Whether to potentially learn new thoughts
            
        Returns:
            Dict with:
            - state: Encoded state in Hilbert space
            - coefficients: Decomposition in eigenbasis
            - novelty: How novel this input is
            - retrieved: Overlaps with existing thoughts
        """
        # Encode to Hilbert space
        state = self.encode_to_hilbert(x)
        
        # Decompose in current eigenbasis
        coefficients, eigenvalues, eigenvectors = self.decompose_in_eigenbasis(state)
        
        # Compute novelty
        residual, novelty = self.compute_residual(state)
        
        # Retrieve matching thoughts
        retrieved = []
        for thought in self.thoughts:
            if thought.strength > self.config.fade_threshold:
                overlap = thought.overlap_with(state)
                retrieved.append(overlap)
        
        # Optionally learn new thought
        new_thought = None
        if learn:
            new_thought = self.learn_thought(state)
        
        return {
            'state': state,
            'coefficients': coefficients,
            'eigenvalues': eigenvalues,
            'eigenvectors': eigenvectors,
            'residual': residual,
            'novelty': torch.tensor(novelty),
            'retrieved_overlaps': torch.tensor(retrieved) if retrieved else torch.zeros(1),
            'new_thought': new_thought is not None,
        }
