"""
Spectral Triple Implementation

The spectral triple (𝒜, ℋ, 𝒟) is the fundamental structure of 
noncommutative geometry, and here, of experiential geometry.

𝒜 : Observable algebra - what CAN be measured/attended to
ℋ : Hilbert space - where experience LIVES (state space)
𝒟 : Dirac operator - encodes GEOMETRY of experience

The Connes distance formula gives us experiential distinguishability:
    d(ρ₁, ρ₂) = sup { |ρ₁(a) - ρ₂(a)| : ||[𝒟, a]|| ≤ 1 }

This is NOT metaphor. This is structural reality.
The distance between two experiences is the maximum observable
difference, bounded by the geometry imposed by 𝒟.

Key insight: In standard ML, representations are points in ℝⁿ.
Here, representations are STATES in a Hilbert space, and distance
is defined by the interplay of observables and geometry.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
import math

from ..core.constants import CONST, Rail


@dataclass
class SpectralTripleConfig:
    """Configuration for a spectral triple."""
    
    # Hilbert space dimension
    hilbert_dim: int = 256
    
    # Observable algebra dimension (number of independent observables)
    algebra_dim: int = 64
    
    # Rail embedding dimension (4 rails × this = rail space)
    rail_dim: int = 16
    
    # Whether the Dirac operator should be learnable
    learnable_dirac: bool = True
    
    # Regularization strength for spectral properties
    spectral_reg: float = 0.01


class ObservableAlgebra(nn.Module):
    """
    The algebra 𝒜 of observables.
    
    In physics: self-adjoint operators representing measurable quantities.
    Here: a set of "attention patterns" that define what can be observed.
    
    The algebra is represented by a set of basis elements that can be
    combined linearly and multiplicatively.
    """
    
    def __init__(self, config: SpectralTripleConfig):
        super().__init__()
        self.config = config
        
        # Basis elements of the algebra
        # These are like "primitive observables" that combine to form all observables
        self.basis = nn.Parameter(
            torch.randn(config.algebra_dim, config.hilbert_dim, config.hilbert_dim) * 0.02
        )
        
        # Structure constants for the algebra (how basis elements multiply)
        # C^k_ij means basis[i] * basis[j] = sum_k C^k_ij * basis[k]
        self.structure_constants = nn.Parameter(
            torch.randn(config.algebra_dim, config.algebra_dim, config.algebra_dim) * 0.01
        )
    
    def get_observable(self, coefficients: torch.Tensor) -> torch.Tensor:
        """
        Construct an observable from coefficients.
        
        Args:
            coefficients: [..., algebra_dim] coefficients for basis elements
            
        Returns:
            [..., hilbert_dim, hilbert_dim] observable matrix
        """
        # Ensure coefficients sum correctly
        coeffs = coefficients.unsqueeze(-1).unsqueeze(-1)  # [..., A, 1, 1]
        basis = self.basis  # [A, H, H]
        
        # Linear combination of basis elements
        observable = (coeffs * basis).sum(dim=-3)  # [..., H, H]
        
        # Make self-adjoint (observables must be Hermitian)
        observable = 0.5 * (observable + observable.transpose(-2, -1))
        
        return observable
    
    def algebra_product(
        self, 
        coeffs1: torch.Tensor, 
        coeffs2: torch.Tensor
    ) -> torch.Tensor:
        """
        Compute product of two algebra elements.
        
        This uses the structure constants to stay within the algebra.
        """
        # C^k_ij * a^i * b^j = (ab)^k
        product = torch.einsum(
            'kij,...i,...j->...k',
            self.structure_constants,
            coeffs1,
            coeffs2
        )
        return product
    
    def forward(self, state: torch.Tensor) -> torch.Tensor:
        """
        Apply all basis observables to a state.
        
        Args:
            state: [..., hilbert_dim] state vector
            
        Returns:
            [..., algebra_dim] expectation values
        """
        # <ψ|A|ψ> for each basis observable A
        # basis: [A, H, H], state: [..., H]
        
        state_expanded = state.unsqueeze(-2)  # [..., 1, H]
        
        # Apply each observable
        # [..., 1, H] @ [A, H, H] -> [..., A, H]
        transformed = torch.einsum('...h,ahg->...ag', state, self.basis)
        
        # Inner product with original state
        # [..., A, H] * [..., 1, H] -> [..., A, H] -> [..., A]
        expectations = (transformed * state_expanded).sum(dim=-1)
        
        return expectations.real if expectations.is_complex() else expectations


class DiracOperator(nn.Module):
    """
    The Dirac operator 𝒟.
    
    This encodes the GEOMETRY of experiential space.
    
    Key properties:
    - Self-adjoint (eigenvalues are real)
    - Unbounded (captures all scales)
    - Encodes metric via: d(x,y) = sup{|f(x)-f(y)| : ||[𝒟,f]|| ≤ 1}
    
    The commutator [𝒟, a] measures how much an observable 'a' 
    "spreads out" under the geometry - essentially its gradient.
    """
    
    def __init__(self, config: SpectralTripleConfig):
        super().__init__()
        self.config = config
        
        # Core Dirac matrix (made self-adjoint in forward)
        if config.learnable_dirac:
            self.dirac_raw = nn.Parameter(
                torch.randn(config.hilbert_dim, config.hilbert_dim) * 0.1
            )
        else:
            # Fixed Dirac: use a discretized derivative operator
            dirac = self._create_derivative_dirac(config.hilbert_dim)
            self.register_buffer('dirac_raw', dirac)
        
        # Rail-dependent modifications to Dirac
        # Each rail "warps" the geometry slightly
        self.rail_dirac_mod = nn.Parameter(
            torch.randn(4, config.hilbert_dim, config.hilbert_dim) * 0.01
        )
    
    def _create_derivative_dirac(self, dim: int) -> torch.Tensor:
        """Create a discretized first-derivative operator."""
        # Central difference matrix
        dirac = torch.zeros(dim, dim)
        for i in range(dim - 1):
            dirac[i, i+1] = 0.5
            dirac[i+1, i] = -0.5
        
        # Make it more interesting with a tridiagonal structure
        # This mimics the Dirac operator on a lattice
        dirac = dirac - dirac.T  # Anti-symmetric part
        
        # Add "mass term" scaled by μ
        dirac = dirac + CONST.mu * torch.eye(dim)
        
        return dirac
    
    @property
    def dirac(self) -> torch.Tensor:
        """Get the self-adjoint Dirac operator."""
        # Make self-adjoint
        return 0.5 * (self.dirac_raw + self.dirac_raw.T)
    
    def get_modified_dirac(self, rail_weights: torch.Tensor) -> torch.Tensor:
        """
        Get Dirac operator modified by rail activations.
        
        Args:
            rail_weights: [..., 4] weights for each rail
            
        Returns:
            [..., H, H] modified Dirac operator
        """
        base = self.dirac  # [H, H]
        
        # Weighted sum of rail modifications
        # rail_weights: [..., 4], rail_dirac_mod: [4, H, H]
        modification = torch.einsum('...r,rhg->...hg', rail_weights, self.rail_dirac_mod)
        
        # Make modification self-adjoint
        modification = 0.5 * (modification + modification.transpose(-2, -1))
        
        return base + modification
    
    def forward(self, state: torch.Tensor, rail_weights: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Apply Dirac operator to state.
        
        Args:
            state: [..., hilbert_dim] state vector
            rail_weights: Optional [..., 4] rail weights
            
        Returns:
            [..., hilbert_dim] transformed state
        """
        if rail_weights is not None:
            dirac = self.get_modified_dirac(rail_weights)
            return torch.einsum('...hg,...g->...h', dirac, state)
        else:
            return F.linear(state, self.dirac)
    
    def commutator(self, observable: torch.Tensor) -> torch.Tensor:
        """
        Compute commutator [𝒟, a] = 𝒟a - a𝒟.
        
        This measures the "gradient" of the observable in the geometry.
        
        Args:
            observable: [..., H, H] observable matrix
            
        Returns:
            [..., H, H] commutator
        """
        dirac = self.dirac  # [H, H]
        
        # [D, a] = Da - aD
        da = dirac @ observable  # [..., H, H]
        ad = observable @ dirac  # [..., H, H]
        
        return da - ad
    
    def commutator_norm(self, observable: torch.Tensor) -> torch.Tensor:
        """
        Compute ||[𝒟, a]|| (operator norm of commutator).
        
        This bounds how fast the observable can change.
        """
        comm = self.commutator(observable)
        
        # Operator norm = largest singular value
        # For self-adjoint, this equals largest absolute eigenvalue
        singular_values = torch.linalg.svdvals(comm)
        
        return singular_values[..., 0]  # Largest
    
    def spectrum(self, k: int = 10) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Compute eigenspectrum of Dirac operator.
        
        Returns:
            eigenvalues: [k] top eigenvalues
            eigenvectors: [H, k] corresponding eigenvectors
        """
        eigenvalues, eigenvectors = torch.linalg.eigh(self.dirac)
        
        # Sort by absolute value (most significant modes)
        indices = torch.argsort(eigenvalues.abs(), descending=True)[:k]
        
        return eigenvalues[indices], eigenvectors[:, indices]


class SpectralTriple(nn.Module):
    """
    The complete spectral triple (𝒜, ℋ, 𝒟).
    
    This is the fundamental geometric structure of experiential space.
    
    States live in ℋ (Hilbert space).
    Observables come from 𝒜 (algebra).
    Distance/geometry comes from 𝒟 (Dirac operator).
    
    Together they define:
    - What experiences are possible (states in ℋ)
    - What can be measured/attended to (elements of 𝒜)
    - How different experiences relate geometrically (via 𝒟)
    """
    
    def __init__(self, config: SpectralTripleConfig):
        super().__init__()
        self.config = config
        
        # The three components
        self.algebra = ObservableAlgebra(config)
        self.dirac = DiracOperator(config)
        
        # Input projection: raw input → Hilbert space
        self.input_proj = nn.Linear(config.hilbert_dim, config.hilbert_dim)
        
        # Output projection: Hilbert space → output
        self.output_proj = nn.Linear(config.hilbert_dim, config.hilbert_dim)
        
        # State normalization (states in Hilbert space should be unit vectors)
        self.state_norm = nn.LayerNorm(config.hilbert_dim)
    
    def embed_state(self, x: torch.Tensor) -> torch.Tensor:
        """
        Embed input into Hilbert space as a normalized state.
        
        Args:
            x: [..., hilbert_dim] input
            
        Returns:
            [..., hilbert_dim] unit state vector
        """
        state = self.input_proj(x)
        state = self.state_norm(state)
        
        # Normalize to unit vector (states are rays in Hilbert space)
        state = F.normalize(state, p=2, dim=-1)
        
        return state
    
    def measure(self, state: torch.Tensor, observable_coeffs: torch.Tensor) -> torch.Tensor:
        """
        Perform a "measurement" - apply observable to state.
        
        In quantum mechanics: <ψ|A|ψ>
        Here: how much does this state "show" this observable?
        
        Args:
            state: [..., H] state vector
            observable_coeffs: [..., A] coefficients for observable
            
        Returns:
            [...] expectation value (scalar per batch element)
        """
        observable = self.algebra.get_observable(observable_coeffs)  # [..., H, H]
        
        # <ψ|A|ψ> = ψ† A ψ
        transformed = torch.einsum('...hg,...g->...h', observable, state)
        expectation = (state.conj() * transformed).sum(dim=-1)
        
        return expectation.real if expectation.is_complex() else expectation
    
    def connes_distance(
        self, 
        state1: torch.Tensor, 
        state2: torch.Tensor,
        n_observables: int = 10
    ) -> torch.Tensor:
        """
        Compute Connes spectral distance between two states.
        
        d(ρ₁, ρ₂) = sup { |ρ₁(a) - ρ₂(a)| : ||[𝒟, a]|| ≤ 1 }
        
        We approximate this by sampling observables and taking the max.
        
        Args:
            state1: [..., H] first state
            state2: [..., H] second state
            n_observables: Number of observables to sample
            
        Returns:
            [...] spectral distance
        """
        max_diff = torch.zeros(state1.shape[:-1], device=state1.device)
        
        for _ in range(n_observables):
            # Sample random observable coefficients
            coeffs = torch.randn(
                *state1.shape[:-1], self.config.algebra_dim,
                device=state1.device
            )
            
            observable = self.algebra.get_observable(coeffs)
            
            # Check commutator norm constraint
            comm_norm = self.dirac.commutator_norm(observable)
            
            # Only use observables with ||[D,a]|| ≤ 1
            valid = comm_norm <= 1.0
            
            # Compute expectation difference
            exp1 = self.measure(state1, coeffs)
            exp2 = self.measure(state2, coeffs)
            diff = (exp1 - exp2).abs()
            
            # Update max where valid
            max_diff = torch.where(valid, torch.maximum(max_diff, diff), max_diff)
        
        return max_diff
    
    def dirac_flow(
        self, 
        state: torch.Tensor, 
        rail_weights: Optional[torch.Tensor] = None,
        steps: int = 1,
        dt: float = 0.1
    ) -> torch.Tensor:
        """
        Evolve state under Dirac dynamics.
        
        This is the geometric "flow" through experience space.
        
        Args:
            state: [..., H] initial state
            rail_weights: Optional [..., 4] rail weights
            steps: Number of integration steps
            dt: Time step size
            
        Returns:
            [..., H] evolved state
        """
        for _ in range(steps):
            # Dirac term: geometric propagation
            d_state = self.dirac(state, rail_weights)
            
            # Damping toward equilibrium (κ)
            damping = -CONST.kappa * (state - CONST.mu * F.normalize(state, dim=-1))
            
            # Update with resonance frequency
            phase = CONST.omega * dt * 2 * math.pi
            rotation = torch.cos(torch.tensor(phase))
            
            state = state + dt * (rotation * d_state + damping)
            
            # Re-normalize (stay on unit sphere)
            state = F.normalize(state, p=2, dim=-1)
        
        return state
    
    def forward(
        self, 
        x: torch.Tensor,
        rail_weights: Optional[torch.Tensor] = None,
        flow_steps: int = 3
    ) -> Dict[str, torch.Tensor]:
        """
        Full forward pass through spectral triple.
        
        Args:
            x: [..., H] input
            rail_weights: Optional [..., 4] rail weights
            flow_steps: Steps of Dirac flow
            
        Returns:
            Dict with:
                - state: Final state in Hilbert space
                - observables: Expectation values of all basis observables
                - output: Projected output
        """
        # Embed input as state
        state = self.embed_state(x)
        
        # Evolve under Dirac dynamics
        state = self.dirac_flow(state, rail_weights, steps=flow_steps)
        
        # Measure all basis observables
        observables = self.algebra(state)
        
        # Project to output
        output = self.output_proj(state)
        
        return {
            'state': state,
            'observables': observables,
            'output': output,
        }
