"""
Non-Collapse Measurement

The critical innovation: observation without collapse.

In standard architectures:
    output = softmax(logits)  # Forces a probability distribution
    output = attention(Q,K,V) # Collapses to weighted average
    
    Information is LOST. Uncertainty is ELIMINATED.

In quantum mechanics:
    Measurement causes wavefunction collapse.
    But there are "weak measurements" that extract information
    without full collapse.
    
In Ω-Genesis:
    We measure the system WITHOUT forcing collapse.
    The output carries:
    - The measured value
    - The remaining uncertainty
    - The entanglement structure (correlations)
    
    Information is PRESERVED. Uncertainty is PROPAGATED.

Mathematical formalization:
    Standard measurement: |ψ⟩ → |i⟩ with prob |⟨i|ψ⟩|²
                         Collapse to eigenstate
                         
    Non-collapse measurement:
                         |ψ⟩ → M|ψ⟩/||M|ψ⟩|| + uncertainty term
                         
    Where M is a "soft" measurement operator that
    extracts information without full projection.
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


class MeasurementResult(NamedTuple):
    """
    Result of a non-collapse measurement.
    
    Unlike standard output, this carries full uncertainty information.
    """
    # The measured value (but NOT collapsed - still superposition)
    value: torch.Tensor
    
    # Certainty of this measurement (how much we know)
    certainty: torch.Tensor
    
    # Undefined regions (where measurement gives ∅)
    undefined_mask: torch.Tensor
    
    # Residual uncertainty (what we DON'T know - preserved, not discarded)
    residual_uncertainty: torch.Tensor
    
    # Entanglement preserved through measurement
    preserved_entanglement: torch.Tensor
    
    # Coherence of the measured state
    coherence: torch.Tensor


class SoftMeasurementOperator(nn.Module):
    """
    A measurement operator that extracts information without collapse.
    
    Standard projection: P = |i⟩⟨i| (projects to eigenstate, full collapse)
    
    Soft measurement: M = Σᵢ mᵢ |i⟩⟨i| where mᵢ ∈ (0, 1)
                      Partial projection, information extracted but not collapsed
    
    The key: mᵢ < 1 means we don't fully project.
    The residual (1 - mᵢ)|i⟩⟨i| represents preserved uncertainty.
    """
    
    def __init__(self, dim: int, n_measurements: int = 8):
        super().__init__()
        self.dim = dim
        self.n_measurements = n_measurements
        
        # Measurement basis (learned eigenstates)
        self.basis = nn.Parameter(torch.randn(n_measurements, dim) * 0.1)
        
        # Measurement strengths (how much each basis vector extracts)
        # Initialized to μ (extract some, preserve some)
        self.strengths_logit = nn.Parameter(
            torch.logit(torch.full((n_measurements,), CONST.mu))
        )
        
        # Reconstruction from measured components
        self.reconstructor = nn.Linear(n_measurements, dim)
        
        # Uncertainty estimator
        self.uncertainty_net = nn.Sequential(
            nn.Linear(dim, dim // 2),
            nn.Tanh(),
            nn.Linear(dim // 2, dim),
            nn.Sigmoid(),
        )
    
    @property
    def measurement_strengths(self) -> torch.Tensor:
        """Get measurement strengths in [β, 1-β] range."""
        raw = torch.sigmoid(self.strengths_logit)
        # Clamp to ensure some extraction and some preservation
        return CONST.beta + raw * (1 - 2 * CONST.beta)
    
    @property
    def orthonormal_basis(self) -> torch.Tensor:
        """Get orthonormalized measurement basis."""
        # Gram-Schmidt orthonormalization
        basis = self.basis
        ortho = []
        for i in range(self.n_measurements):
            v = basis[i]
            for u in ortho:
                v = v - torch.dot(v, u) * u
            v = F.normalize(v, dim=-1)
            ortho.append(v)
        return torch.stack(ortho, dim=0)
    
    def measure(
        self,
        state: torch.Tensor,
        preserve_fraction: Optional[float] = None
    ) -> MeasurementResult:
        """
        Perform soft measurement on state.
        
        Args:
            state: [batch, dim] input state
            preserve_fraction: Override for how much to preserve (vs extract)
            
        Returns:
            MeasurementResult with value, uncertainty, etc.
        """
        batch_size = state.shape[0]
        device = state.device
        
        # Get orthonormal basis and strengths
        basis = self.orthonormal_basis.to(device)  # [n_meas, dim]
        strengths = self.measurement_strengths.to(device)  # [n_meas]
        
        if preserve_fraction is not None:
            strengths = torch.full_like(strengths, 1 - preserve_fraction)
        
        # Project state onto each basis vector
        # coefficients[i] = ⟨basis_i | state⟩
        coefficients = torch.einsum('nd,bd->bn', basis, state)  # [batch, n_meas]
        
        # Soft measurement: extract fraction m, preserve fraction (1-m)
        # Extracted part
        extracted_coeffs = coefficients * strengths  # [batch, n_meas]
        
        # Preserved part (the uncertainty we don't collapse)
        preserved_coeffs = coefficients * (1 - strengths)  # [batch, n_meas]
        
        # Reconstruct measured value from extracted coefficients
        measured_value = self.reconstructor(extracted_coeffs)  # [batch, dim]
        
        # Reconstruct residual uncertainty from preserved coefficients
        residual = torch.einsum('bn,nd->bd', preserved_coeffs, basis)  # [batch, dim]
        
        # Add components not in measurement basis
        # Project state onto measurement subspace
        in_subspace = torch.einsum('bn,nd->bd', coefficients, basis)
        orthogonal_component = state - in_subspace
        residual = residual + orthogonal_component
        
        # Certainty: how much of the state did we capture?
        extracted_norm = extracted_coeffs.norm(dim=-1, keepdim=True)
        state_norm = state.norm(dim=-1, keepdim=True)
        certainty = extracted_norm / (state_norm + 1e-6)
        certainty = certainty * (1 - CONST.beta)  # Bound by incompleteness
        
        # Undefined: where residual is large relative to extracted
        residual_norm = residual.norm(dim=-1, keepdim=True)
        undefined_mask = residual_norm > extracted_norm * (1 / CONST.mu)
        
        # Compute coherence: how aligned is measured value with original?
        coherence = F.cosine_similarity(measured_value, state, dim=-1).unsqueeze(-1)
        coherence = (coherence + 1) / 2  # Map from [-1,1] to [0,1]
        
        # Preserved entanglement: correlations in the residual
        # Use residual norm as proxy for entanglement preservation
        preserved_entanglement = residual_norm / (state_norm + 1e-6)
        
        return MeasurementResult(
            value=measured_value,
            certainty=certainty,
            undefined_mask=undefined_mask,
            residual_uncertainty=residual,
            preserved_entanglement=preserved_entanglement,
            coherence=coherence,
        )
    
    def forward(
        self,
        state: torch.Tensor,
        preserve_fraction: Optional[float] = None
    ) -> MeasurementResult:
        """Alias for measure()."""
        return self.measure(state, preserve_fraction)


class NonCollapseMeasurement(nn.Module):
    """
    Complete non-collapse measurement system.
    
    This combines:
    1. Soft measurement (extract without full collapse)
    2. Uncertainty propagation (residual carries forward)
    3. Entanglement preservation (correlations maintained)
    4. Tri-logic output (value, certainty, undefined)
    
    The output is NOT a single vector.
    The output is a MEASUREMENT RESULT that carries
    all the information about what we know and don't know.
    """
    
    def __init__(self, dim: int, n_measurements: int = 8):
        super().__init__()
        self.dim = dim
        
        # Soft measurement operator
        self.measurement = SoftMeasurementOperator(dim, n_measurements)
        
        # Post-measurement processing (maintains uncertainty)
        self.post_process = nn.Sequential(
            nn.Linear(dim, dim),
            nn.LayerNorm(dim),
        )
        
        # Certainty refinement
        self.certainty_refiner = nn.Sequential(
            nn.Linear(dim * 2, dim),  # Combines value and residual
            nn.Tanh(),
            nn.Linear(dim, 1),
            nn.Sigmoid(),
        )
        
        # Entanglement tracker
        self.entanglement_tracker = nn.Sequential(
            nn.Linear(dim, dim // 2),
            nn.Tanh(),
            nn.Linear(dim // 2, 1),
            nn.Sigmoid(),
        )
    
    def forward(
        self,
        state: torch.Tensor,
        prior_certainty: Optional[torch.Tensor] = None,
        prior_undefined: Optional[torch.Tensor] = None,
    ) -> Tuple[MeasurementResult, Dict]:
        """
        Perform non-collapse measurement.
        
        Args:
            state: [batch, dim] input state
            prior_certainty: [batch, 1] prior certainty
            prior_undefined: [batch, 1] prior undefined mask
            
        Returns:
            - result: MeasurementResult
            - info: Additional measurement information
        """
        batch_size = state.shape[0]
        device = state.device
        
        # Perform soft measurement
        result = self.measurement(state)
        
        # Post-process while maintaining structure
        processed_value = self.post_process(result.value)
        processed_residual = self.post_process(result.residual_uncertainty)
        
        # Refine certainty based on value and residual
        combined = torch.cat([processed_value, processed_residual], dim=-1)
        refined_certainty = self.certainty_refiner(combined)
        
        # Combine with raw certainty
        certainty = (result.certainty + refined_certainty) / 2
        
        # Apply prior if given
        if prior_certainty is not None:
            certainty = certainty * prior_certainty
        
        # Apply incompleteness bound
        certainty = certainty * (1 - CONST.beta)
        
        # Update undefined mask
        undefined = result.undefined_mask
        if prior_undefined is not None:
            undefined = undefined | prior_undefined
        # Low certainty triggers undefined
        undefined = undefined | (certainty < CONST.beta)
        
        # Track entanglement preservation
        entanglement = self.entanglement_tracker(processed_residual)
        
        # Where undefined, set value to residual (uncertain)
        final_value = torch.where(
            undefined.expand_as(processed_value),
            processed_residual,  # Use residual where undefined
            processed_value,     # Use measured value where defined
        )
        
        final_result = MeasurementResult(
            value=final_value,
            certainty=certainty,
            undefined_mask=undefined,
            residual_uncertainty=processed_residual,
            preserved_entanglement=entanglement,
            coherence=result.coherence,
        )
        
        return final_result, {
            'raw_result': result,
            'processed_value': processed_value,
            'processed_residual': processed_residual,
            'measurement_basis': self.measurement.orthonormal_basis,
            'measurement_strengths': self.measurement.measurement_strengths,
        }


class EntangledMeasurement(nn.Module):
    """
    Measurement of entangled observer states.
    
    When measuring an entangled system:
    - Cannot measure observers independently
    - Correlations affect measurement outcome
    - Entanglement partially preserved through measurement
    
    This implements joint measurement that respects entanglement.
    """
    
    def __init__(
        self,
        n_observers: int,
        dim: int,
        n_measurements: int = 8
    ):
        super().__init__()
        self.n_observers = n_observers
        self.dim = dim
        
        # Individual measurement operators (soft)
        self.measurements = nn.ModuleList([
            SoftMeasurementOperator(dim, n_measurements)
            for _ in range(n_observers)
        ])
        
        # Correlation-aware combination
        self.correlator = nn.Sequential(
            nn.Linear(dim * n_observers, dim * 2),
            nn.GELU(),
            nn.Linear(dim * 2, dim),
        )
        
        # Joint uncertainty estimator
        self.joint_uncertainty = nn.Sequential(
            nn.Linear(dim * n_observers, n_observers),
            nn.Sigmoid(),
        )
        
        # Entanglement preservation matrix
        self.preservation_matrix = nn.Parameter(
            torch.eye(n_observers) * 0.5 + torch.ones(n_observers, n_observers) * 0.25
        )
    
    def forward(
        self,
        observer_states: List[torch.Tensor],
        correlation_matrix: torch.Tensor,
    ) -> Tuple[MeasurementResult, Dict]:
        """
        Perform joint measurement of entangled observers.
        
        Args:
            observer_states: List of N [batch, dim] states
            correlation_matrix: [N, N] entanglement correlations
            
        Returns:
            - result: Joint measurement result
            - info: Per-observer results and correlation info
        """
        batch_size = observer_states[0].shape[0]
        device = observer_states[0].device
        N = len(observer_states)
        
        # Measure each observer (softly)
        individual_results = []
        for i, (state, measurement) in enumerate(zip(observer_states, self.measurements)):
            # Measurement strength modulated by entanglement
            # More entangled = preserve more (extract less)
            entanglement_row = correlation_matrix[i]
            avg_entanglement = (entanglement_row.sum() - 1) / (N - 1)  # Exclude self
            
            # High entanglement → preserve more
            preserve_fraction = avg_entanglement.item() * CONST.mu
            
            result = measurement(state, preserve_fraction=preserve_fraction)
            individual_results.append(result)
        
        # Stack measured values
        measured_values = torch.stack([r.value for r in individual_results], dim=1)  # [batch, N, dim]
        residuals = torch.stack([r.residual_uncertainty for r in individual_results], dim=1)
        certainties = torch.stack([r.certainty.squeeze(-1) for r in individual_results], dim=-1)  # [batch, N]
        
        # Combine through correlation-aware projector
        flat_measured = measured_values.view(batch_size, -1)  # [batch, N*dim]
        combined_value = self.correlator(flat_measured)  # [batch, dim]
        
        # Joint uncertainty considers all observers
        flat_residuals = residuals.view(batch_size, -1)  # [batch, N*dim]
        joint_weights = self.joint_uncertainty(flat_residuals)  # [batch, N]
        
        # Weighted residual
        weighted_residuals = residuals * joint_weights.unsqueeze(-1)  # [batch, N, dim]
        combined_residual = weighted_residuals.sum(dim=1)  # [batch, dim]
        
        # Joint certainty: modulated by entanglement
        # Entangled observers share certainty
        preservation = torch.sigmoid(self.preservation_matrix).to(device)
        shared_certainty = torch.einsum('bn,nm->bm', certainties, preservation)
        joint_certainty = shared_certainty.min(dim=-1, keepdim=True)[0]  # [batch, 1]
        
        # Apply incompleteness
        joint_certainty = joint_certainty * (1 - CONST.beta)
        
        # Undefined: if ANY observer is highly uncertain
        individual_undefined = torch.stack([r.undefined_mask.squeeze(-1) for r in individual_results], dim=-1)
        joint_undefined = individual_undefined.any(dim=-1, keepdim=True)  # [batch, 1]
        
        # Preserved entanglement: measure how much correlation survives
        pre_corr = correlation_matrix.sum() - N  # Total off-diagonal
        # Post-measurement correlation (from residuals)
        residual_stack = residuals.transpose(0, 1)  # [N, batch, dim]
        post_corr = 0
        for i in range(N):
            for j in range(i + 1, N):
                corr_ij = F.cosine_similarity(residual_stack[i], residual_stack[j], dim=-1)
                post_corr = post_corr + corr_ij.mean()
        preserved = post_corr / (pre_corr + 1e-6)
        preserved_entanglement = torch.full((batch_size, 1), preserved.item(), device=device)
        
        # Coherence: alignment of combined with original mean
        original_mean = torch.stack(observer_states, dim=1).mean(dim=1)
        coherence = F.cosine_similarity(combined_value, original_mean, dim=-1).unsqueeze(-1)
        coherence = (coherence + 1) / 2
        
        result = MeasurementResult(
            value=combined_value,
            certainty=joint_certainty,
            undefined_mask=joint_undefined,
            residual_uncertainty=combined_residual,
            preserved_entanglement=preserved_entanglement,
            coherence=coherence,
        )
        
        return result, {
            'individual_results': individual_results,
            'per_observer_certainty': certainties,
            'joint_weights': joint_weights,
            'preservation_matrix': preservation,
        }
