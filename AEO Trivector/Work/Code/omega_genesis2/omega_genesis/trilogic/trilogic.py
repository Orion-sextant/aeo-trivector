"""
Tri-Logic Processing (K3 Logic)

Standard neural networks operate in continuous space that gets
discretized to binary at decision time. This loses crucial information
about UNCERTAINTY.

K3 tri-logic maintains three values:
- TRUE (✓): Evidence supports
- FALSE (✗): Evidence contradicts  
- UNDEFINED (∅): Genuine uncertainty

∅ is NOT failure. It's the honest answer when:
- Prerequisites aren't met
- Evidence is contradictory
- Information is genuinely missing

Maps to Riemann sphere:
- FALSE → 0 (south pole)
- TRUE → 1 (real axis)
- UNDEFINED → ∞ (north pole, the pole at infinity)

Möbius transformations preserve this structure.

Every computation maintains uncertainty explicitly.
The model can say "I don't know" at EVERY level.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, Dict, Optional, NamedTuple
import math

from ..core.constants import CONST, TriValue


class TriLogicValue(NamedTuple):
    """
    A value with tri-logic semantics.
    
    Contains:
    - value: The actual value tensor
    - certainty: How certain we are (0 = totally undefined, 1 = certain)
    - undefined_mask: Boolean mask where value is ∅
    """
    value: torch.Tensor
    certainty: torch.Tensor
    undefined_mask: torch.Tensor
    
    @classmethod
    def from_tensor(cls, x: torch.Tensor, initial_certainty: float = 1.0):
        """Create tri-logic value from regular tensor."""
        return cls(
            value=x,
            certainty=torch.full(x.shape[:-1] + (1,), initial_certainty, device=x.device),
            undefined_mask=torch.zeros(x.shape[:-1] + (1,), dtype=torch.bool, device=x.device)
        )
    
    @classmethod
    def undefined(cls, shape: Tuple, device: torch.device):
        """Create a purely undefined value."""
        return cls(
            value=torch.zeros(shape, device=device),
            certainty=torch.zeros(shape[:-1] + (1,), device=device),
            undefined_mask=torch.ones(shape[:-1] + (1,), dtype=torch.bool, device=device)
        )
    
    def collapse(self, threshold: float = 0.5) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Collapse to binary True/False where certain enough.
        
        Returns:
            - collapsed: Binary values (True where value > 0.5 AND certain)
            - mask: Where collapse was possible
        """
        can_collapse = (self.certainty > threshold) & (~self.undefined_mask)
        collapsed = self.value > 0.5
        return collapsed.float(), can_collapse.float()


class RiemannProjection(nn.Module):
    """
    Project between plane and Riemann sphere.
    
    The Riemann sphere compactifies the complex plane by adding
    a point at infinity (∞). This is where ∅ lives.
    
    Stereographic projection:
    - Plane point z maps to sphere point (X, Y, Z)
    - ∞ maps to north pole (0, 0, 1)
    - 0 maps to south pole (0, 0, -1)
    """
    
    def __init__(self, epsilon: float = 1e-6):
        super().__init__()
        self.epsilon = epsilon
    
    def to_sphere(self, z: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Stereographic projection from plane to sphere.
        
        For real z:
            X = 2z / (1 + z²)
            Y = 0  
            Z = (z² - 1) / (z² + 1)
        
        Args:
            z: [...] real values (extended reals with ∞)
            
        Returns:
            X, Y, Z coordinates on unit sphere
        """
        z_sq = z ** 2
        denom = 1 + z_sq + self.epsilon
        
        X = 2 * z / denom
        Y = torch.zeros_like(z)
        Z = (z_sq - 1) / denom
        
        return X, Y, Z
    
    def from_sphere(self, X: torch.Tensor, Y: torch.Tensor, Z: torch.Tensor) -> torch.Tensor:
        """
        Inverse stereographic projection from sphere to plane.
        
        z = X / (1 - Z)  (for Z ≠ 1)
        z = ∞            (for Z = 1, the north pole)
        """
        # Handle north pole (Z ≈ 1) → infinity
        is_north_pole = (1 - Z).abs() < self.epsilon
        
        z = X / (1 - Z + self.epsilon)
        
        # Set infinity for north pole
        z = torch.where(is_north_pole, torch.tensor(float('inf'), device=z.device), z)
        
        return z
    
    def get_undefined_region(self, Z: torch.Tensor, threshold: float = 0.8) -> torch.Tensor:
        """
        Identify points near north pole (undefined region).
        
        Returns boolean mask where Z > threshold.
        """
        return Z > threshold


class MobiusTransform(nn.Module):
    """
    Möbius transformation: (az + b) / (cz + d)
    
    These are the conformal maps of the Riemann sphere.
    They preserve the tri-logic structure:
    - Circles and lines map to circles and lines
    - The point at infinity is handled naturally
    - Cross-ratios are preserved
    
    A Möbius transformation is determined by 4 complex numbers
    (a, b, c, d) with ad - bc ≠ 0.
    
    For real-valued processing, we use real Möbius transforms.
    """
    
    def __init__(self, dim: int, n_transforms: int = 4):
        super().__init__()
        
        self.dim = dim
        self.n_transforms = n_transforms
        
        # Learnable parameters for Möbius transforms
        # Initialize near identity: (z + 0) / (0 + 1) = z
        self.a = nn.Parameter(torch.eye(n_transforms, dim) + 0.01 * torch.randn(n_transforms, dim))
        self.b = nn.Parameter(0.01 * torch.randn(n_transforms, dim))
        self.c = nn.Parameter(0.01 * torch.randn(n_transforms, dim))
        self.d = nn.Parameter(torch.ones(n_transforms, dim) + 0.01 * torch.randn(n_transforms, dim))
    
    def forward(self, z: torch.Tensor, transform_idx: int = 0) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Apply Möbius transformation.
        
        Args:
            z: [..., dim] input values
            transform_idx: Which transform to use
            
        Returns:
            - transformed: [..., dim] transformed values
            - poles: [..., dim] boolean mask where denominator is near zero
        """
        a = self.a[transform_idx]  # [dim]
        b = self.b[transform_idx]
        c = self.c[transform_idx]
        d = self.d[transform_idx]
        
        numerator = a * z + b  # [..., dim]
        denominator = c * z + d  # [..., dim]
        
        # Detect poles (where denominator ≈ 0)
        poles = denominator.abs() < 1e-6
        
        # Safe division
        result = numerator / (denominator + 1e-6 * poles.float())
        
        # At poles, the result is ∞ (undefined)
        result = torch.where(poles, torch.tensor(float('inf'), device=z.device), result)
        
        return result, poles


class TriLogicGate(nn.Module):
    """
    A computation gate that maintains tri-logic semantics.
    
    Every gate outputs:
    - value: The computed result
    - certainty: Confidence in the result
    - undefined_mask: Where result is ∅
    
    Certainty propagates: uncertain inputs → more uncertain outputs
    Undefined propagates: ∅ in prerequisites → ∅ in result
    """
    
    def __init__(self, in_dim: int, out_dim: int):
        super().__init__()
        
        self.in_dim = in_dim
        self.out_dim = out_dim
        
        self.value_transform = nn.Linear(in_dim, out_dim)
        self.certainty_transform = nn.Linear(2, 1)  # mean value + input certainty
        
        # Riemann sphere projection
        self.riemann = RiemannProjection()
        
        # Threshold for undefined detection
        self.undefined_threshold = nn.Parameter(torch.tensor(CONST.beta))
    
    def forward(self, input: TriLogicValue) -> TriLogicValue:
        """
        Process input maintaining tri-logic semantics.
        """
        # Transform value
        new_value = self.value_transform(input.value)
        
        # Compute new certainty (certainty propagates and can only decrease)
        cert_input = torch.cat([input.value.mean(dim=-1, keepdim=True), input.certainty], dim=-1)
        certainty_raw = self.certainty_transform(cert_input)
        
        # Certainty can only decrease: use sigmoid and multiply by input certainty
        new_certainty = torch.sigmoid(certainty_raw) * input.certainty
        
        # Apply incompleteness bound (never 100% certain)
        new_certainty = new_certainty * (1 - CONST.beta)
        
        # Detect undefined: low certainty OR propagated undefined
        is_undefined = (new_certainty < self.undefined_threshold) | input.undefined_mask
        
        # Project to Riemann sphere to detect ∅ region
        X, Y, Z = self.riemann.to_sphere(new_value.mean(dim=-1))
        riemann_undefined = self.riemann.get_undefined_region(Z)
        is_undefined = is_undefined | riemann_undefined.unsqueeze(-1)
        
        # Where undefined, set certainty to 0
        new_certainty = new_certainty * (~is_undefined).float()
        
        return TriLogicValue(
            value=new_value,
            certainty=new_certainty,
            undefined_mask=is_undefined
        )


class TriLogicLayer(nn.Module):
    """
    A full processing layer with tri-logic semantics.
    
    Combines:
    - Value transformation (what)
    - Certainty propagation (how sure)
    - Undefined detection (when to say "I don't know")
    
    Uses Möbius transforms on Riemann sphere for structure preservation.
    """
    
    def __init__(self, dim: int, n_mobius: int = 4):
        super().__init__()
        
        self.dim = dim
        
        # Möbius transforms for structure-preserving processing
        self.mobius = MobiusTransform(dim, n_mobius)
        self.n_mobius = n_mobius
        
        # Tri-logic gate for certainty management
        self.gate = TriLogicGate(dim, dim)
        
        # Layer normalization (but aware of certainty)
        self.norm_scale = nn.Parameter(torch.ones(dim))
        self.norm_bias = nn.Parameter(torch.zeros(dim))
        
        # Undefined handling: what to output when uncertain
        self.undefined_output = nn.Parameter(torch.zeros(dim))
    
    def certainty_aware_norm(
        self, 
        x: torch.Tensor, 
        certainty: torch.Tensor
    ) -> torch.Tensor:
        """
        Normalize considering certainty.
        
        Less certain values are normalized toward neutral.
        """
        # Standard normalization
        mean = x.mean(dim=-1, keepdim=True)
        std = x.std(dim=-1, keepdim=True) + 1e-6
        normalized = (x - mean) / std
        
        # Scale by certainty: less certain → closer to 0
        # But maintain β incompleteness: never fully certain
        effective_certainty = certainty * (1 - CONST.beta)
        normalized = normalized * effective_certainty
        
        return normalized * self.norm_scale + self.norm_bias
    
    def forward(self, input: TriLogicValue) -> TriLogicValue:
        """
        Process through tri-logic layer.
        """
        x = input.value
        certainty = input.certainty
        undefined = input.undefined_mask
        
        # Apply each Möbius transform and track poles
        transformed = x
        total_poles = torch.zeros_like(undefined)
        
        for i in range(self.n_mobius):
            transformed, poles = self.mobius(transformed, i)
            total_poles = total_poles | poles.any(dim=-1, keepdim=True)
        
        # Handle infinities from poles
        is_inf = torch.isinf(transformed)
        transformed = torch.where(is_inf, torch.zeros_like(transformed), transformed)
        new_undefined = undefined | total_poles | is_inf.any(dim=-1, keepdim=True)
        
        # Certainty-aware normalization
        normalized = self.certainty_aware_norm(transformed, certainty)
        
        # Process through tri-logic gate
        intermediate = TriLogicValue(normalized, certainty, new_undefined)
        result = self.gate(intermediate)
        
        # Where undefined, use special undefined output
        final_value = torch.where(
            result.undefined_mask.expand_as(result.value),
            self.undefined_output.expand_as(result.value),
            result.value
        )
        
        return TriLogicValue(
            value=final_value,
            certainty=result.certainty,
            undefined_mask=result.undefined_mask
        )


class TriLogicStack(nn.Module):
    """
    Stack of tri-logic layers with uncertainty propagation.
    
    Uncertainty compounds through layers but can also RESOLVE
    when evidence accumulates (at rate κ).
    """
    
    def __init__(self, dim: int, n_layers: int = 4, n_mobius: int = 4):
        super().__init__()
        
        self.layers = nn.ModuleList([
            TriLogicLayer(dim, n_mobius) for _ in range(n_layers)
        ])
        
        # Evidence accumulation (can resolve uncertainty)
        self.evidence_gate = nn.Linear(2, 1)  # Two scalar means concatenated
    
    def forward(
        self, 
        x: torch.Tensor,
        initial_certainty: float = 0.8
    ) -> Dict[str, torch.Tensor]:
        """
        Process through tri-logic stack.
        
        Returns dict with:
        - output: Final values
        - certainty: Final certainty
        - undefined_mask: Where output is ∅
        - certainty_trajectory: How certainty evolved
        - undefined_trajectory: How undefined regions evolved
        """
        # Initialize tri-logic value
        current = TriLogicValue.from_tensor(x, initial_certainty)
        
        certainty_trajectory = [current.certainty]
        undefined_trajectory = [current.undefined_mask]
        
        for i, layer in enumerate(self.layers):
            # Process through layer
            result = layer(current)
            
            # Evidence accumulation: can RESOLVE uncertainty
            # Compare current and previous to detect consistency
            if i > 0:
                evidence_input = torch.cat([
                    current.value.mean(dim=-1, keepdim=True),
                    result.value.mean(dim=-1, keepdim=True)
                ], dim=-1)
                evidence_strength = torch.sigmoid(self.evidence_gate(evidence_input))
                
                # Consistent evidence increases certainty (at rate κ)
                certainty_boost = CONST.kappa * evidence_strength
                new_certainty = result.certainty + certainty_boost * (1 - result.certainty)
                new_certainty = new_certainty * (1 - CONST.beta)  # Always some uncertainty
                
                # Update undefined mask: resolved if certainty increased enough
                resolved = (new_certainty > CONST.mu) & result.undefined_mask
                new_undefined = result.undefined_mask & (~resolved)
                
                result = TriLogicValue(result.value, new_certainty, new_undefined)
            
            current = result
            certainty_trajectory.append(current.certainty)
            undefined_trajectory.append(current.undefined_mask)
        
        return {
            'output': current.value,
            'certainty': current.certainty,
            'undefined_mask': current.undefined_mask,
            'certainty_trajectory': torch.stack(certainty_trajectory, dim=0),
            'undefined_trajectory': torch.stack(undefined_trajectory, dim=0),
        }
