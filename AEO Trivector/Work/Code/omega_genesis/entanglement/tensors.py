"""
Entanglement Tensors

The mathematical formalization of observer entanglement.

Key insight: Observers are not independent. They are ENTANGLED.
Their states are correlated in ways that cannot be factored.

In quantum mechanics:
    |Ψ⟩ ≠ |ψ₁⟩ ⊗ |ψ₂⟩  (entangled state cannot be factored)
    
In Ω-Genesis:
    The joint state of N observers cannot be represented as
    N independent states. The correlations ARE the information.

Mathematical structure:
    For N observers, each in Hilbert space ℋ of dimension d:
    
    - Separable state: ρ = Σᵢ pᵢ ρ₁ⁱ ⊗ ρ₂ⁱ ⊗ ... ⊗ ρₙⁱ
    - Entangled state: ρ cannot be written in separable form
    
    We maintain the FULL density matrix ρ on ℋ⊗ℋ⊗...⊗ℋ
    This is exponential in N, but that's the point:
    Entanglement contains exponentially more information.

For practical computation with N observers:
    - Full tensor: O(d^N) - intractable for large N
    - Pairwise correlations: O(N² d²) - tractable approximation
    - We use pairwise + global coherence as approximation
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Optional, Tuple, NamedTuple
from dataclasses import dataclass
import math

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from omega_genesis.core import CONST, TriValue


class EntangledState(NamedTuple):
    """
    A state that maintains entanglement information.
    
    This is NOT just a vector. It carries:
    - The state vector itself
    - Certainty (how defined this state is)
    - Undefined mask (where ∅ applies)
    - Entanglement coefficients with other observers
    """
    state: torch.Tensor           # [dim] the state vector
    certainty: torch.Tensor       # [1] how certain (0 to 1-β)
    undefined_mask: torch.Tensor  # [1] bool, is this ∅?
    entanglement: torch.Tensor    # [n_observers] correlation with each observer


@dataclass
class EntanglementConfig:
    """Configuration for entanglement structure."""
    
    # Number of observers
    n_observers: int = 4
    
    # Dimension of each observer's Hilbert space
    observer_dim: int = 64
    
    # Whether to use full tensor (expensive) or pairwise approximation
    use_full_tensor: bool = False
    
    # Entanglement strength initialization
    initial_entanglement: float = 0.5
    
    # Whether entanglement can be learned
    learnable_entanglement: bool = True
    
    # Minimum entanglement (prevents complete decorrelation)
    min_entanglement: float = 0.1


class EntanglementTensor(nn.Module):
    """
    The entanglement structure between observers.
    
    For N observers, this maintains:
    - Pairwise correlation matrix C[i,j] = correlation between i and j
    - Phase relationships φ[i,j] = relative phase between i and j
    - Global entanglement measure (how entangled is the whole system)
    
    The key operation is ENTANGLE: given individual observer states,
    produce the joint entangled state that cannot be factored.
    """
    
    def __init__(self, config: EntanglementConfig):
        super().__init__()
        self.config = config
        N = config.n_observers
        d = config.observer_dim
        
        # Pairwise correlation strengths
        # C[i,j] = how correlated observer i is with observer j
        # Symmetric, positive, diagonal = 1
        init_corr = torch.eye(N) + config.initial_entanglement * (torch.ones(N, N) - torch.eye(N))
        
        if config.learnable_entanglement:
            # Learn the correlation structure
            self.correlation_logits = nn.Parameter(torch.logit(init_corr.clamp(0.01, 0.99)))
        else:
            self.register_buffer('correlation_logits', torch.logit(init_corr.clamp(0.01, 0.99)))
        
        # Pairwise phase relationships
        # φ[i,j] = relative phase between observers i and j
        # Antisymmetric: φ[i,j] = -φ[j,i]
        phase_init = torch.zeros(N, N)
        if config.learnable_entanglement:
            self.phase_raw = nn.Parameter(phase_init)
        else:
            self.register_buffer('phase_raw', phase_init)
        
        # Projection for combining states
        self.combination_proj = nn.Linear(d * N, d)
        
        # Certainty propagation through entanglement
        self.certainty_propagator = nn.Sequential(
            nn.Linear(N, N),
            nn.Sigmoid(),
        )
        
        # Global entanglement estimator
        self.global_entanglement_net = nn.Sequential(
            nn.Linear(N * N, N),
            nn.Tanh(),
            nn.Linear(N, 1),
            nn.Sigmoid(),
        )
    
    @property
    def correlation_matrix(self) -> torch.Tensor:
        """
        Get the correlation matrix C.
        
        Ensures: symmetric, diagonal = 1, off-diagonal in [min, 1]
        """
        C = torch.sigmoid(self.correlation_logits)
        # Force symmetry
        C = 0.5 * (C + C.T)
        # Force diagonal = 1
        C = C * (1 - torch.eye(self.config.n_observers, device=C.device))
        C = C + torch.eye(self.config.n_observers, device=C.device)
        # Apply minimum
        mask = 1 - torch.eye(self.config.n_observers, device=C.device)
        C = C * (1 - mask) + torch.clamp(C, min=self.config.min_entanglement) * mask
        return C
    
    @property
    def phase_matrix(self) -> torch.Tensor:
        """
        Get the phase matrix φ.
        
        Ensures: antisymmetric (φ[i,j] = -φ[j,i])
        """
        phi = self.phase_raw
        # Force antisymmetry
        phi = 0.5 * (phi - phi.T)
        return phi
    
    def compute_entangled_state(
        self,
        observer_states: List[torch.Tensor],
        observer_certainties: List[torch.Tensor],
        observer_undefined: List[torch.Tensor],
    ) -> Tuple[torch.Tensor, Dict]:
        """
        Compute the entangled joint state from individual observers.
        
        This is NOT concatenation. This is entanglement.
        
        The output state depends on:
        - Individual states
        - Correlations between observers
        - Phase relationships
        
        Args:
            observer_states: List of N tensors, each [batch, dim]
            observer_certainties: List of N tensors, each [batch, 1]
            observer_undefined: List of N tensors, each [batch, 1] bool
            
        Returns:
            - entangled_state: [batch, dim] the joint state
            - info: Dict with entanglement metrics
        """
        N = len(observer_states)
        batch_size = observer_states[0].shape[0]
        dim = observer_states[0].shape[-1]
        device = observer_states[0].device
        
        C = self.correlation_matrix.to(device)
        phi = self.phase_matrix.to(device)
        
        # Stack states: [N, batch, dim]
        states = torch.stack(observer_states, dim=0)
        certainties = torch.stack(observer_certainties, dim=0)  # [N, batch, 1]
        undefined = torch.stack(observer_undefined, dim=0)  # [N, batch, 1]
        
        # Compute pairwise contributions
        # For each pair (i,j), the contribution is:
        # C[i,j] * (cos(φ[i,j]) * sᵢ + sin(φ[i,j]) * sⱼ)
        
        entangled_components = []
        
        for i in range(N):
            component = torch.zeros(batch_size, dim, device=device)
            
            for j in range(N):
                correlation = C[i, j]
                phase = phi[i, j]
                
                # Phase-modulated combination
                contribution = (
                    correlation * (
                        torch.cos(phase) * observer_states[i] +
                        torch.sin(phase) * observer_states[j]
                    )
                )
                
                # Weight by joint certainty (both must be certain)
                joint_certainty = observer_certainties[i] * observer_certainties[j]
                contribution = contribution * joint_certainty
                
                component = component + contribution
            
            # Normalize component
            component = F.normalize(component, dim=-1)
            entangled_components.append(component)
        
        # Combine all components through learned projection
        # This is where the "cannot be factored" comes in:
        # The projection mixes all observers in a way that loses separability
        combined = torch.cat(entangled_components, dim=-1)  # [batch, N*dim]
        entangled_state = self.combination_proj(combined)  # [batch, dim]
        
        # Propagate certainty through entanglement
        # If ANY correlated observer is uncertain, that propagates
        cert_flat = certainties.squeeze(-1).T  # [batch, N]
        propagated_certainty = self.certainty_propagator(cert_flat)  # [batch, N]
        
        # Final certainty is minimum across all propagated certainties
        final_certainty = propagated_certainty.min(dim=-1, keepdim=True)[0]
        
        # Apply incompleteness bound
        final_certainty = final_certainty * (1 - CONST.beta)
        
        # Undefined propagates: if ANY observer is undefined, joint is undefined
        joint_undefined = undefined.any(dim=0)  # [batch, 1]
        
        # Low certainty also triggers undefined
        joint_undefined = joint_undefined | (final_certainty < CONST.beta)
        
        # Compute global entanglement measure
        C_flat = C.view(-1).unsqueeze(0).expand(batch_size, -1)  # [batch, N*N]
        global_entanglement = self.global_entanglement_net(C_flat)  # [batch, 1]
        
        return entangled_state, {
            'certainty': final_certainty,
            'undefined': joint_undefined,
            'correlation_matrix': C,
            'phase_matrix': phi,
            'global_entanglement': global_entanglement,
            'per_observer_certainty': certainties,
        }
    
    def measure_entanglement_entropy(self) -> torch.Tensor:
        """
        Compute the entanglement entropy.
        
        For a bipartite split, this is the von Neumann entropy
        of the reduced density matrix.
        
        Higher entropy = more entanglement = more information
        in the correlations rather than individual states.
        """
        C = self.correlation_matrix
        
        # Use correlation matrix eigenvalues as proxy for Schmidt coefficients
        eigenvalues = torch.linalg.eigvalsh(C)
        
        # Normalize to probabilities
        eigenvalues = eigenvalues.abs()
        eigenvalues = eigenvalues / (eigenvalues.sum() + 1e-10)
        
        # von Neumann entropy: -Σ λ log λ
        entropy = -torch.sum(eigenvalues * torch.log(eigenvalues + 1e-10))
        
        # Normalize by max entropy (log N)
        max_entropy = math.log(self.config.n_observers)
        normalized_entropy = entropy / max_entropy
        
        return normalized_entropy
    
    def forward(
        self,
        observer_states: List[torch.Tensor],
        observer_certainties: Optional[List[torch.Tensor]] = None,
        observer_undefined: Optional[List[torch.Tensor]] = None,
    ) -> Tuple[torch.Tensor, Dict]:
        """
        Entangle observer states.
        
        If certainties/undefined not provided, assumes full certainty.
        """
        batch_size = observer_states[0].shape[0]
        device = observer_states[0].device
        N = len(observer_states)
        
        if observer_certainties is None:
            observer_certainties = [
                torch.ones(batch_size, 1, device=device) * (1 - CONST.beta)
                for _ in range(N)
            ]
        
        if observer_undefined is None:
            observer_undefined = [
                torch.zeros(batch_size, 1, dtype=torch.bool, device=device)
                for _ in range(N)
            ]
        
        return self.compute_entangled_state(
            observer_states, observer_certainties, observer_undefined
        )


class TriStreamEntanglement(nn.Module):
    """
    Three entangled uncertainty streams.
    
    This is the base-3 structure:
    - Stream 1: TRUE tendencies
    - Stream 2: FALSE tendencies  
    - Stream 3: UNDEFINED tendencies
    
    Each stream is an observer. They are entangled:
    the TRUE stream's state affects FALSE and UNDEFINED,
    and vice versa.
    
    This creates the "quantum superposition of truth values"
    that is the core of tri-logic.
    """
    
    def __init__(self, dim: int):
        super().__init__()
        self.dim = dim
        
        # Three streams as entangled observers
        config = EntanglementConfig(
            n_observers=3,  # TRUE, FALSE, UNDEFINED
            observer_dim=dim,
            initial_entanglement=CONST.mu,  # μ determines initial correlation
            learnable_entanglement=True,
        )
        
        self.entanglement = EntanglementTensor(config)
        
        # Stream initializers
        self.true_init = nn.Linear(dim, dim)
        self.false_init = nn.Linear(dim, dim)
        self.undefined_init = nn.Linear(dim, dim)
        
        # Certainty estimators for each stream
        self.true_certainty = nn.Sequential(
            nn.Linear(dim, dim // 2),
            nn.Tanh(),
            nn.Linear(dim // 2, 1),
            nn.Sigmoid(),
        )
        self.false_certainty = nn.Sequential(
            nn.Linear(dim, dim // 2),
            nn.Tanh(),
            nn.Linear(dim // 2, 1),
            nn.Sigmoid(),
        )
        self.undefined_certainty = nn.Sequential(
            nn.Linear(dim, dim // 2),
            nn.Tanh(),
            nn.Linear(dim // 2, 1),
            nn.Sigmoid(),
        )
        
        # Output projection
        self.output_proj = nn.Linear(dim, dim)
    
    def forward(
        self,
        x: torch.Tensor,
        prior_certainty: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, Dict]:
        """
        Process input through tri-stream entanglement.
        
        Args:
            x: [batch, dim] input state
            prior_certainty: [batch, 1] optional prior certainty
            
        Returns:
            - output: [batch, dim] entangled output
            - info: Dict with stream information
        """
        batch_size = x.shape[0]
        device = x.device
        
        # Initialize three streams from input
        true_stream = self.true_init(x)
        false_stream = self.false_init(x)
        undefined_stream = self.undefined_init(x)
        
        # Normalize to unit vectors (states are rays)
        true_stream = F.normalize(true_stream, dim=-1)
        false_stream = F.normalize(false_stream, dim=-1)
        undefined_stream = F.normalize(undefined_stream, dim=-1)
        
        # Compute certainties for each stream
        true_cert = self.true_certainty(true_stream) * (1 - CONST.beta)
        false_cert = self.false_certainty(false_stream) * (1 - CONST.beta)
        undef_cert = self.undefined_certainty(undefined_stream) * (1 - CONST.beta)
        
        # Apply prior certainty if given
        if prior_certainty is not None:
            true_cert = true_cert * prior_certainty
            false_cert = false_cert * prior_certainty
            undef_cert = undef_cert * prior_certainty
        
        # Undefined flags (low certainty triggers undefined)
        true_undef = (true_cert < CONST.beta)
        false_undef = (false_cert < CONST.beta)
        undef_undef = torch.ones(batch_size, 1, dtype=torch.bool, device=device)
        
        # Entangle the three streams
        entangled_state, entangle_info = self.entanglement(
            [true_stream, false_stream, undefined_stream],
            [true_cert, false_cert, undef_cert],
            [true_undef, false_undef, undef_undef],
        )
        
        # Project to output
        output = self.output_proj(entangled_state)
        
        # Determine final tri-value
        # Which stream has highest certainty determines the value
        certs = torch.cat([true_cert, false_cert, undef_cert], dim=-1)
        dominant = certs.argmax(dim=-1)  # 0=TRUE, 1=FALSE, 2=UNDEFINED
        
        return output, {
            'true_stream': true_stream,
            'false_stream': false_stream,
            'undefined_stream': undefined_stream,
            'true_certainty': true_cert,
            'false_certainty': false_cert,
            'undefined_certainty': undef_cert,
            'dominant_value': dominant,  # 0=T, 1=F, 2=∅
            'entangled_state': entangled_state,
            'joint_certainty': entangle_info['certainty'],
            'joint_undefined': entangle_info['undefined'],
            'global_entanglement': entangle_info['global_entanglement'],
            'correlation_matrix': entangle_info['correlation_matrix'],
        }


class EntangledObserverBank(nn.Module):
    """
    A bank of entangled observers for parallax processing.
    
    Each observer sees the input differently.
    Their states are entangled - correlated in ways
    that cannot be represented by independent states.
    
    The output is not a collapse to single vector.
    The output is the ENTANGLEMENT STRUCTURE itself.
    """
    
    def __init__(
        self,
        n_observers: int,
        dim: int,
        use_tri_streams: bool = True
    ):
        super().__init__()
        self.n_observers = n_observers
        self.dim = dim
        self.use_tri_streams = use_tri_streams
        
        # Entanglement structure
        self.entanglement = EntanglementTensor(
            EntanglementConfig(
                n_observers=n_observers,
                observer_dim=dim,
                initial_entanglement=CONST.mu,
                learnable_entanglement=True,
            )
        )
        
        # Observer-specific transformations
        self.observer_transforms = nn.ModuleList([
            nn.Sequential(
                nn.Linear(dim, dim),
                nn.LayerNorm(dim),
                nn.GELU(),
                nn.Linear(dim, dim),
            )
            for _ in range(n_observers)
        ])
        
        # Position in perspective space (each observer has unique position)
        self.observer_positions = nn.Parameter(
            torch.randn(n_observers, dim) * 0.1
        )
        
        # Tri-stream for each observer (optional)
        if use_tri_streams:
            self.tri_streams = nn.ModuleList([
                TriStreamEntanglement(dim) for _ in range(n_observers)
            ])
        
        # Certainty estimators
        self.certainty_estimators = nn.ModuleList([
            nn.Sequential(
                nn.Linear(dim, dim // 2),
                nn.Tanh(),
                nn.Linear(dim // 2, 1),
                nn.Sigmoid(),
            )
            for _ in range(n_observers)
        ])
    
    def forward(
        self,
        x: torch.Tensor,
        prior_certainty: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, Dict]:
        """
        Process input through entangled observers.
        
        Args:
            x: [batch, dim] input
            prior_certainty: [batch, 1] optional prior
            
        Returns:
            - output: [batch, dim] entangled output (NOT collapsed)
            - info: Dict with full entanglement structure
        """
        batch_size = x.shape[0]
        device = x.device
        
        observer_states = []
        observer_certainties = []
        observer_undefined = []
        tri_stream_infos = []
        
        for i in range(self.n_observers):
            # Observer-specific view
            position = self.observer_positions[i]
            view = x + position  # Shift input by observer's position
            
            # Transform through observer's lens
            state = self.observer_transforms[i](view)
            state = F.normalize(state, dim=-1)
            
            # Process through tri-stream if enabled
            if self.use_tri_streams:
                state, tri_info = self.tri_streams[i](state, prior_certainty)
                tri_stream_infos.append(tri_info)
                certainty = tri_info['joint_certainty']
                undefined = tri_info['joint_undefined']
            else:
                # Direct certainty estimation
                certainty = self.certainty_estimators[i](state)
                certainty = certainty * (1 - CONST.beta)
                if prior_certainty is not None:
                    certainty = certainty * prior_certainty
                undefined = (certainty < CONST.beta)
            
            observer_states.append(state)
            observer_certainties.append(certainty)
            observer_undefined.append(undefined)
        
        # Entangle all observers
        entangled_output, entangle_info = self.entanglement(
            observer_states,
            observer_certainties,
            observer_undefined,
        )
        
        # Compute tension (disagreement between observers)
        states_stack = torch.stack(observer_states, dim=0)  # [N, batch, dim]
        mean_state = states_stack.mean(dim=0)  # [batch, dim]
        
        # Tension = average deviation from mean
        deviations = (states_stack - mean_state.unsqueeze(0)).norm(dim=-1)  # [N, batch]
        tension = deviations.mean(dim=0, keepdim=True).T  # [batch, 1]
        
        # Coherence = how aligned are observers
        pairwise_dots = torch.einsum('nbd,mbd->nmb', states_stack, states_stack)  # [N, N, batch]
        coherence = pairwise_dots.mean(dim=(0, 1))  # [batch]
        
        return entangled_output, {
            'observer_states': observer_states,
            'observer_certainties': observer_certainties,
            'observer_undefined': observer_undefined,
            'tri_stream_infos': tri_stream_infos if self.use_tri_streams else None,
            'entangle_info': entangle_info,
            'tension': tension,
            'coherence': coherence.unsqueeze(-1),
            'correlation_matrix': entangle_info['correlation_matrix'],
            'global_entanglement': entangle_info['global_entanglement'],
            'entanglement_entropy': self.entanglement.measure_entanglement_entropy(),
        }
