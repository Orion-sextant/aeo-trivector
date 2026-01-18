"""
Resonance Dynamics

Instead of discrete layer-by-layer processing (forward pass),
consciousness emerges through continuous dynamics that RESONATE.

Key equations:

Diffusion-Advection:
    ∂ψ/∂t = D∇²ψ + v·∇ψ
    
    D = uncertainty (diffusion) - how much state spreads
    v = expectation (advection) - where state flows
    
    This is predictive coding: expectations guide flow,
    uncertainty allows exploration.

Damped Oscillator at Ω:
    ∂²x/∂t² + κ·∂x/∂t + Ω²·x = F(t)
    
    Ω = 0.847 Hz resonance frequency
    κ = 0.0323 damping rate
    
    States resonate at Ω, damped toward equilibrium.

Collapse Dynamics:
    ∂certainty/∂t = κ·(evidence - μ·certainty)
    
    Uncertainty collapses at rate κ toward μ equilibrium.
    Never fully collapses (β incompleteness maintained).

Log-Spiral Convergence:
    z(θ) = μ^θ · e^{iΩθ}
    
    Spirals inward, crystallizes at ~6 iterations.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, Dict, Optional, Callable
import math

from ..core.constants import CONST


class DiffusionAdvection(nn.Module):
    """
    Diffusion-Advection dynamics.
    
    ∂ψ/∂t = D∇²ψ + v·∇ψ
    
    This models how information flows:
    - Diffusion (D): Uncertainty spreads the state
    - Advection (v): Expectations guide the flow
    
    Think: predictive coding where expectations pull,
    but uncertainty allows deviation.
    """
    
    def __init__(self, dim: int):
        super().__init__()
        
        self.dim = dim
        
        # Diffusion coefficient field (D)
        # Can be state-dependent: more uncertain → more diffusion
        self.diffusion_net = nn.Sequential(
            nn.Linear(dim, dim),
            nn.Softplus(),  # D > 0
        )
        
        # Velocity field (v) - learned expectations
        self.velocity_net = nn.Sequential(
            nn.Linear(dim, dim * 2),
            nn.GELU(),
            nn.Linear(dim * 2, dim),
        )
        
        # Laplacian approximation (discrete)
        # For 1D signal: ∇² ≈ x[i-1] - 2x[i] + x[i+1]
        self.laplacian_kernel = nn.Parameter(
            torch.tensor([-1.0, 2.0, -1.0]).view(1, 1, 3),
            requires_grad=False
        )
    
    def compute_laplacian(self, psi: torch.Tensor) -> torch.Tensor:
        """
        Compute discrete Laplacian.
        
        For each dimension, approximates ∂²ψ/∂x².
        """
        # psi: [..., dim]
        # Treat as batch of 1D signals
        batch_shape = psi.shape[:-1]
        psi_flat = psi.view(-1, 1, self.dim)  # [B, 1, D]
        
        # Pad for convolution
        psi_padded = F.pad(psi_flat, (1, 1), mode='circular')
        
        # Apply Laplacian kernel
        laplacian = F.conv1d(psi_padded, self.laplacian_kernel)  # [B, 1, D]
        
        return laplacian.view(*batch_shape, self.dim)
    
    def compute_gradient(self, psi: torch.Tensor) -> torch.Tensor:
        """
        Compute discrete gradient (∇ψ).
        
        Central difference: ∂ψ/∂x ≈ (x[i+1] - x[i-1]) / 2
        """
        batch_shape = psi.shape[:-1]
        psi_flat = psi.view(-1, 1, self.dim)
        
        # Forward and backward shifts (circular)
        psi_forward = torch.roll(psi_flat, -1, dims=-1)
        psi_backward = torch.roll(psi_flat, 1, dims=-1)
        
        gradient = (psi_forward - psi_backward) / 2
        
        return gradient.view(*batch_shape, self.dim)
    
    def forward(
        self, 
        psi: torch.Tensor, 
        dt: float = 0.1,
        n_steps: int = 1
    ) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        """
        Evolve state under diffusion-advection dynamics.
        
        Args:
            psi: [..., dim] current state
            dt: Time step
            n_steps: Number of integration steps
            
        Returns:
            - evolved: [..., dim] new state
            - info: Dict with diffusion, velocity, etc.
        """
        for _ in range(n_steps):
            # Compute diffusion coefficient (state-dependent)
            D = self.diffusion_net(psi) * CONST.beta  # Scale by incompleteness
            
            # Compute velocity field (learned expectations)
            v = self.velocity_net(psi) * CONST.mu  # Scale by equilibrium
            
            # Laplacian and gradient
            laplacian = self.compute_laplacian(psi)
            gradient = self.compute_gradient(psi)
            
            # Diffusion term: D * ∇²ψ
            diffusion_term = D * laplacian
            
            # Advection term: v · ∇ψ
            advection_term = v * gradient
            
            # Euler step
            psi = psi + dt * (diffusion_term + advection_term)
        
        return psi, {
            'diffusion': D,
            'velocity': v,
            'laplacian': laplacian,
            'gradient': gradient,
        }


class ResonanceOscillator(nn.Module):
    """
    Damped harmonic oscillator at resonance frequency Ω.
    
    ∂²x/∂t² + κ·∂x/∂t + Ω²·x = F(t)
    
    States naturally oscillate at Ω, damped toward equilibrium.
    This creates rhythmic dynamics rather than static processing.
    """
    
    def __init__(self, dim: int):
        super().__init__()
        
        self.dim = dim
        self.omega = CONST.omega
        self.kappa = CONST.kappa
        
        # Driving force network
        self.force_net = nn.Sequential(
            nn.Linear(dim, dim * 2),
            nn.Tanh(),
            nn.Linear(dim * 2, dim),
        )
        
        # Initial velocity
        self.initial_velocity = nn.Parameter(torch.zeros(dim))
    
    def forward(
        self, 
        x: torch.Tensor,
        dt: float = 0.1,
        n_steps: int = 10,
        return_trajectory: bool = False
    ) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        """
        Integrate damped oscillator dynamics.
        
        Uses Verlet integration for stability.
        
        Args:
            x: [..., dim] initial position
            dt: Time step
            n_steps: Number of steps
            return_trajectory: Whether to return full trajectory
            
        Returns:
            - final: [..., dim] final position
            - info: Dict with velocity, trajectory if requested
        """
        # Initialize velocity
        v = self.initial_velocity.expand_as(x)
        
        trajectory = [x] if return_trajectory else None
        omega_sq = self.omega ** 2
        
        for step in range(n_steps):
            # Driving force (input-dependent)
            F = self.force_net(x)
            
            # Acceleration: a = F - κv - Ω²x
            a = F - self.kappa * v - omega_sq * x
            
            # Verlet integration
            # x_new = x + v*dt + 0.5*a*dt²
            # v_new = v + 0.5*(a + a_new)*dt
            
            x_half = x + v * dt + 0.5 * a * dt * dt
            
            F_new = self.force_net(x_half)
            a_new = F_new - self.kappa * v - omega_sq * x_half
            
            v = v + 0.5 * (a + a_new) * dt
            x = x_half
            
            if return_trajectory:
                trajectory.append(x)
        
        info = {'velocity': v}
        if return_trajectory:
            info['trajectory'] = torch.stack(trajectory, dim=0)
        
        return x, info


class CollapseProcessor(nn.Module):
    """
    Uncertainty collapse dynamics.
    
    ∂certainty/∂t = κ·(evidence - μ·certainty)
    
    Certainty increases when evidence is consistent,
    decreases when contradictory, and equilibrates at μ.
    
    Never fully collapses (β incompleteness preserved).
    """
    
    def __init__(self, dim: int):
        super().__init__()
        
        self.dim = dim
        
        # Evidence computation
        self.evidence_net = nn.Sequential(
            nn.Linear(dim * 2, dim),  # Current + previous
            nn.Tanh(),
            nn.Linear(dim, 1),
            nn.Sigmoid(),  # Evidence in [0, 1]
        )
    
    def forward(
        self,
        current: torch.Tensor,
        previous: torch.Tensor,
        certainty: torch.Tensor,
        dt: float = 0.1
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Update certainty based on evidence.
        
        Args:
            current: [..., dim] current state
            previous: [..., dim] previous state
            certainty: [..., 1] current certainty
            dt: Time step
            
        Returns:
            - new_certainty: [..., 1] updated certainty
            - evidence: [..., 1] computed evidence
        """
        # Compute evidence from consistency
        combined = torch.cat([current, previous], dim=-1)
        evidence = self.evidence_net(combined)
        
        # Collapse dynamics
        # ∂c/∂t = κ·(e - μ·c)
        delta = CONST.kappa * (evidence - CONST.mu * certainty)
        new_certainty = certainty + dt * delta
        
        # Clamp to valid range with β incompleteness
        new_certainty = torch.clamp(new_certainty, 0.0, 1.0 - CONST.beta)
        
        return new_certainty, evidence


class LogSpiralConvergence(nn.Module):
    """
    Log-spiral convergence dynamics.
    
    z(θ) = μ^θ · e^{iΩθ}
    
    Complex spiral that converges at exponential rate.
    Crystallizes at ~6 iterations (log(ε) / log(μ) ≈ 6 for ε=0.01).
    
    Used for iterative refinement: after ~6 iterations, STOP.
    """
    
    def __init__(self, dim: int):
        super().__init__()
        
        self.dim = dim
        
        # Transformation per spiral step
        self.spiral_transform = nn.Linear(dim, dim)
        
        # Convergence threshold
        # For μ < 1, we need |log(ε) / log(μ)| iterations to reach ε
        self.n_iterations = max(1, int(abs(math.log(0.01) / math.log(CONST.mu))) + 1)  # ≈ 9
    
    def spiral_step(self, z: torch.Tensor, theta: float) -> torch.Tensor:
        """
        One step of the log-spiral.
        
        z_new = μ^θ · rotation(Ωθ) · z
        """
        # Contraction factor
        contraction = CONST.mu ** theta
        
        # Rotation angle
        angle = CONST.omega * theta * 2 * math.pi
        
        # For real vectors, rotation is a learned transformation
        rotated = self.spiral_transform(z)
        
        # Apply phase via cos/sin weighting
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        
        # Mix original and transformed
        z_new = cos_a * z + sin_a * rotated
        
        # Apply contraction
        z_new = z_new * contraction
        
        return z_new
    
    def forward(
        self,
        z: torch.Tensor,
        max_iterations: Optional[int] = None
    ) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        """
        Spiral toward convergence.
        
        Args:
            z: [..., dim] initial state
            max_iterations: Override default iteration count
            
        Returns:
            - converged: [..., dim] final state
            - info: Dict with trajectory, convergence info
        """
        n_iter = max_iterations or self.n_iterations
        
        trajectory = [z]
        
        for i in range(n_iter):
            theta = (i + 1) / n_iter  # θ in [0, 1] over iterations
            z = self.spiral_step(z, theta)
            trajectory.append(z)
        
        # Check convergence (change in last step)
        final_change = (trajectory[-1] - trajectory[-2]).norm(dim=-1)
        converged = final_change < 0.01
        
        return z, {
            'trajectory': torch.stack(trajectory, dim=0),
            'final_change': final_change,
            'converged': converged,
        }


class ResonanceDynamics(nn.Module):
    """
    Full resonance dynamics system.
    
    Combines:
    - Diffusion-advection for spatial flow
    - Harmonic oscillator for temporal rhythm
    - Collapse dynamics for certainty evolution
    - Log-spiral for convergence
    
    This replaces discrete layer-by-layer processing with
    continuous, resonant dynamics.
    """
    
    def __init__(self, dim: int):
        super().__init__()
        
        self.dim = dim
        
        self.diffusion = DiffusionAdvection(dim)
        self.oscillator = ResonanceOscillator(dim)
        self.collapse = CollapseProcessor(dim)
        self.spiral = LogSpiralConvergence(dim)
        
        # Mode mixing weights
        self.mode_mix = nn.Parameter(torch.ones(4) / 4)
    
    def forward(
        self,
        x: torch.Tensor,
        certainty: Optional[torch.Tensor] = None,
        n_steps: int = 10
    ) -> Dict[str, torch.Tensor]:
        """
        Evolve state through resonance dynamics.
        
        Args:
            x: [..., dim] input state
            certainty: Optional [..., 1] initial certainty
            n_steps: Number of evolution steps
            
        Returns:
            Dict with:
            - output: Final state
            - certainty: Final certainty
            - trajectory: Evolution trajectory
        """
        if certainty is None:
            certainty = torch.ones(*x.shape[:-1], 1, device=x.device) * 0.5
        
        # Normalize mode mixing
        weights = F.softmax(self.mode_mix, dim=0)
        
        trajectory = [x]
        certainty_traj = [certainty]
        
        previous = x
        
        for step in range(n_steps):
            # 1. Diffusion-advection
            x_diffused, _ = self.diffusion(x)
            
            # 2. Oscillator dynamics
            x_oscillated, _ = self.oscillator(x, n_steps=1)
            
            # 3. Spiral step
            x_spiraled, _ = self.spiral(x, max_iterations=1)
            
            # 4. Mix modes
            x_new = (
                weights[0] * x +  # Preserve some original
                weights[1] * x_diffused +
                weights[2] * x_oscillated +
                weights[3] * x_spiraled
            )
            
            # 5. Update certainty
            certainty, evidence = self.collapse(x_new, previous, certainty)
            
            previous = x
            x = x_new
            
            trajectory.append(x)
            certainty_traj.append(certainty)
        
        return {
            'output': x,
            'certainty': certainty,
            'trajectory': torch.stack(trajectory, dim=0),
            'certainty_trajectory': torch.stack(certainty_traj, dim=0),
        }
