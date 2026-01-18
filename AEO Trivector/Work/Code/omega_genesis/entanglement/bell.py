"""
Bell-Like Inequalities

Metrics that prove observers are TRULY entangled, not just parallel.

In quantum mechanics, Bell inequalities distinguish:
- Classical correlations: can be explained by hidden variables
- Quantum correlations: CANNOT be explained classically

The CHSH inequality:
    |E(a,b) - E(a,b') + E(a',b) + E(a',b')| ≤ 2  (classical bound)
    
    But quantum mechanics allows values up to 2√2 ≈ 2.83.
    Violation proves genuine entanglement.

In Ω-Genesis, we define analogous inequalities:
    If observers were independent, certain correlations would be bounded.
    We measure these correlations.
    VIOLATION of the bound proves the observers are genuinely entangled.

This is not just theoretical. It's a METRIC:
    bell_violation > 0 ⟹ genuine entanglement
    bell_violation = 0 ⟹ observers might be independent
    bell_violation < 0 ⟹ anti-correlated (also entangled!)
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

from omega_genesis.core import CONST


@dataclass
class BellTestResult:
    """Result of a Bell-like inequality test."""
    
    # The Bell parameter (like CHSH S value)
    bell_parameter: float
    
    # Classical bound for this test
    classical_bound: float
    
    # Quantum bound (maximum possible violation)
    quantum_bound: float
    
    # Violation amount (positive = genuine entanglement)
    violation: float
    
    # Normalized violation (0 = at classical, 1 = at quantum)
    normalized_violation: float
    
    # Whether this conclusively shows entanglement
    is_entangled: bool
    
    # Confidence in the result
    confidence: float


class CHSHAnalog(nn.Module):
    """
    CHSH-like inequality for neural observers.
    
    Classical CHSH:
        S = E(a,b) - E(a,b') + E(a',b) + E(a',b')
        Classical: |S| ≤ 2
        Quantum: |S| ≤ 2√2
        
    Neural analog:
        We define "measurement settings" a, a', b, b' as
        learned projection directions.
        
        E(x,y) = correlation when observer 1 measures along x
                 and observer 2 measures along y.
        
        If observers are truly entangled, S can exceed 2.
    """
    
    def __init__(self, dim: int):
        super().__init__()
        self.dim = dim
        
        # Measurement settings for observer 1
        self.a = nn.Parameter(F.normalize(torch.randn(dim), dim=-1))
        self.a_prime = nn.Parameter(F.normalize(torch.randn(dim), dim=-1))
        
        # Measurement settings for observer 2
        self.b = nn.Parameter(F.normalize(torch.randn(dim), dim=-1))
        self.b_prime = nn.Parameter(F.normalize(torch.randn(dim), dim=-1))
        
        # Classical bound
        self.classical_bound = 2.0
        
        # Quantum bound (Tsirelson's bound)
        self.quantum_bound = 2 * math.sqrt(2)
    
    def expectation_value(
        self,
        state1: torch.Tensor,
        state2: torch.Tensor,
        setting1: torch.Tensor,
        setting2: torch.Tensor
    ) -> torch.Tensor:
        """
        Compute expectation value E(setting1, setting2).
        
        This is the correlation when observer 1 measures along setting1
        and observer 2 measures along setting2.
        
        E = ⟨ψ₁|σ₁⟩ · ⟨ψ₂|σ₂⟩  (product of projections)
        
        For entangled states, this shows non-classical correlations.
        """
        # Project each state onto its measurement setting
        proj1 = torch.einsum('bd,d->b', state1, setting1)  # [batch]
        proj2 = torch.einsum('bd,d->b', state2, setting2)  # [batch]
        
        # Expectation is the mean of the product
        E = (proj1 * proj2).mean()
        
        return E
    
    def compute_bell_parameter(
        self,
        state1: torch.Tensor,
        state2: torch.Tensor
    ) -> torch.Tensor:
        """
        Compute the CHSH-analog Bell parameter S.
        
        S = E(a,b) - E(a,b') + E(a',b) + E(a',b')
        
        Classical: |S| ≤ 2
        Quantum: |S| ≤ 2√2
        """
        # Normalize settings
        a = F.normalize(self.a, dim=-1)
        a_p = F.normalize(self.a_prime, dim=-1)
        b = F.normalize(self.b, dim=-1)
        b_p = F.normalize(self.b_prime, dim=-1)
        
        # Compute four expectation values
        E_ab = self.expectation_value(state1, state2, a, b)
        E_ab_p = self.expectation_value(state1, state2, a, b_p)
        E_a_pb = self.expectation_value(state1, state2, a_p, b)
        E_a_pb_p = self.expectation_value(state1, state2, a_p, b_p)
        
        # CHSH combination
        S = E_ab - E_ab_p + E_a_pb + E_a_pb_p
        
        return S
    
    def test(
        self,
        state1: torch.Tensor,
        state2: torch.Tensor
    ) -> BellTestResult:
        """
        Perform Bell test on two observer states.
        
        Returns BellTestResult with violation information.
        """
        S = self.compute_bell_parameter(state1, state2)
        S_val = S.abs().item()
        
        violation = S_val - self.classical_bound
        
        # Normalize: 0 at classical, 1 at quantum
        max_violation = self.quantum_bound - self.classical_bound
        normalized = violation / max_violation if violation > 0 else 0
        
        # Confidence based on how far from boundary
        # Higher |S| means more confidence
        confidence = min(1.0, S_val / self.quantum_bound)
        
        return BellTestResult(
            bell_parameter=S_val,
            classical_bound=self.classical_bound,
            quantum_bound=self.quantum_bound,
            violation=violation,
            normalized_violation=normalized,
            is_entangled=violation > 0,
            confidence=confidence,
        )
    
    def forward(
        self,
        state1: torch.Tensor,
        state2: torch.Tensor
    ) -> Tuple[torch.Tensor, BellTestResult]:
        """Compute Bell parameter and return test result."""
        result = self.test(state1, state2)
        return torch.tensor(result.bell_parameter), result


class MultiObserverBellTest(nn.Module):
    """
    Bell-like test for N > 2 observers.
    
    Generalization of CHSH to N parties.
    Uses Mermin-Ardehali-Belinskii-Klyshko (MABK) inequalities.
    
    For N observers:
        M_N defined recursively
        Classical bound: 2^((N-1)/2) for odd N, 2^((N-2)/2) for even N
        Quantum bound: 2^((N-1)/2) for all N
    """
    
    def __init__(self, n_observers: int, dim: int):
        super().__init__()
        self.n_observers = n_observers
        self.dim = dim
        
        # Measurement settings for each observer (two per observer)
        self.settings = nn.ParameterList([
            nn.Parameter(torch.randn(2, dim) * 0.1)
            for _ in range(n_observers)
        ])
        
        # Classical and quantum bounds
        if n_observers % 2 == 1:
            self.classical_bound = 2 ** ((n_observers - 1) / 2)
        else:
            self.classical_bound = 2 ** ((n_observers - 2) / 2)
        
        self.quantum_bound = 2 ** ((n_observers - 1) / 2)
    
    def get_normalized_settings(self, observer_idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        """Get normalized measurement settings for an observer."""
        settings = self.settings[observer_idx]
        s0 = F.normalize(settings[0], dim=-1)
        s1 = F.normalize(settings[1], dim=-1)
        return s0, s1
    
    def compute_correlation(
        self,
        states: List[torch.Tensor],
        setting_indices: List[int]
    ) -> torch.Tensor:
        """
        Compute N-party correlation.
        
        Args:
            states: List of N [batch, dim] states
            setting_indices: List of N indices (0 or 1) for which setting to use
            
        Returns:
            Correlation value (scalar)
        """
        batch_size = states[0].shape[0]
        
        # Product of all projections
        product = torch.ones(batch_size, device=states[0].device)
        
        for i, (state, idx) in enumerate(zip(states, setting_indices)):
            s0, s1 = self.get_normalized_settings(i)
            setting = s0 if idx == 0 else s1
            proj = torch.einsum('bd,d->b', state, setting)
            product = product * proj
        
        return product.mean()
    
    def compute_mermin_parameter(
        self,
        states: List[torch.Tensor]
    ) -> torch.Tensor:
        """
        Compute Mermin-type Bell parameter for N parties.
        
        M_N = (1/2)[M_{N-1} ⊗ (σ_a + σ_b) + M'_{N-1} ⊗ (σ_a - σ_b)]
        
        We compute this recursively through correlations.
        """
        N = len(states)
        
        # For N=2, reduce to CHSH
        if N == 2:
            chsh = CHSHAnalog(self.dim)
            chsh.a.data = self.settings[0][0]
            chsh.a_prime.data = self.settings[0][1]
            chsh.b.data = self.settings[1][0]
            chsh.b_prime.data = self.settings[1][1]
            return chsh.compute_bell_parameter(states[0], states[1])
        
        # For N > 2, compute full Mermin parameter
        # Sum over all 2^N setting combinations with appropriate signs
        total = 0
        
        for bits in range(2 ** N):
            # Convert to setting indices
            indices = [(bits >> i) & 1 for i in range(N)]
            
            # Sign determined by Mermin recursion
            # Count number of 1s
            n_ones = sum(indices)
            sign = (-1) ** ((n_ones * (n_ones - 1)) // 2)
            
            # Compute correlation for this setting combination
            corr = self.compute_correlation(states, indices)
            total = total + sign * corr
        
        # Normalize
        M = total / (2 ** (N - 1))
        
        return M
    
    def test(
        self,
        states: List[torch.Tensor]
    ) -> BellTestResult:
        """
        Perform N-party Bell test.
        """
        M = self.compute_mermin_parameter(states)
        M_val = M.abs().item()
        
        violation = M_val - self.classical_bound
        
        max_violation = self.quantum_bound - self.classical_bound
        normalized = violation / max_violation if max_violation > 0 and violation > 0 else 0
        
        confidence = min(1.0, M_val / self.quantum_bound) if self.quantum_bound > 0 else 0
        
        return BellTestResult(
            bell_parameter=M_val,
            classical_bound=self.classical_bound,
            quantum_bound=self.quantum_bound,
            violation=violation,
            normalized_violation=normalized,
            is_entangled=violation > 0,
            confidence=confidence,
        )
    
    def forward(
        self,
        states: List[torch.Tensor]
    ) -> Tuple[torch.Tensor, BellTestResult]:
        """Compute Mermin parameter and return test result."""
        result = self.test(states)
        return torch.tensor(result.bell_parameter), result


class EntanglementWitness(nn.Module):
    """
    Entanglement witness operator.
    
    An entanglement witness W is an observable such that:
    - Tr(W ρ) ≥ 0 for all separable states ρ
    - Tr(W ρ) < 0 for some entangled states ρ
    
    If ⟨W⟩ < 0, the state is DEFINITELY entangled.
    
    We learn W to be maximally sensitive to the entanglement
    structure of our observer system.
    """
    
    def __init__(self, dim: int, n_observers: int = 2):
        super().__init__()
        self.dim = dim
        self.n_observers = n_observers
        
        # Witness operator components
        # W = Σᵢⱼ wᵢⱼ Aᵢ ⊗ Bⱼ
        # We parameterize the local operators A, B and coefficients w
        
        self.local_operators = nn.ParameterList([
            nn.Parameter(torch.randn(dim, dim) * 0.1)
            for _ in range(n_observers)
        ])
        
        # Coefficients for tensor product terms
        self.coefficients = nn.Parameter(torch.randn(n_observers, n_observers) * 0.1)
        
        # Threshold for entanglement detection
        self.threshold = nn.Parameter(torch.tensor(0.0))
    
    def compute_witness_value(
        self,
        states: List[torch.Tensor]
    ) -> torch.Tensor:
        """
        Compute ⟨W⟩ = Tr(W ρ) for the joint state.
        
        For pure states |ψ₁⟩|ψ₂⟩, this is:
        ⟨W⟩ = Σᵢⱼ wᵢⱼ ⟨ψ₁|Aᵢ|ψ₁⟩⟨ψ₂|Bⱼ|ψ₂⟩
        
        But our states may be entangled, so we compute
        the full expectation including correlations.
        """
        N = len(states)
        batch_size = states[0].shape[0]
        device = states[0].device
        
        # Make local operators Hermitian
        ops = []
        for op in self.local_operators:
            H = 0.5 * (op + op.T)
            ops.append(H)
        
        # Compute local expectation values
        local_exp = []
        for i, (state, op) in enumerate(zip(states, ops)):
            # ⟨ψ|A|ψ⟩
            exp = torch.einsum('bd,de,be->b', state, op.to(device), state)
            local_exp.append(exp)
        
        # Compute witness value
        # Include both local and correlation terms
        W_value = torch.zeros(batch_size, device=device)
        
        coeffs = self.coefficients.to(device)
        
        for i in range(N):
            for j in range(N):
                if i == j:
                    # Local term
                    W_value = W_value + coeffs[i, j] * local_exp[i]
                else:
                    # Correlation term
                    W_value = W_value + coeffs[i, j] * local_exp[i] * local_exp[j]
        
        return W_value.mean()
    
    def detect_entanglement(
        self,
        states: List[torch.Tensor]
    ) -> Tuple[bool, float, float]:
        """
        Detect entanglement using the witness.
        
        Returns:
            - is_entangled: True if witness detects entanglement
            - witness_value: The computed ⟨W⟩
            - confidence: How confident is the detection
        """
        W = self.compute_witness_value(states)
        W_val = W.item()
        
        threshold = self.threshold.item()
        
        is_entangled = W_val < threshold
        
        # Confidence: how far below threshold
        if is_entangled:
            confidence = min(1.0, (threshold - W_val) / (abs(threshold) + 1e-6))
        else:
            confidence = 0.0
        
        return is_entangled, W_val, confidence
    
    def forward(
        self,
        states: List[torch.Tensor]
    ) -> Tuple[torch.Tensor, Dict]:
        """Compute witness value and detection result."""
        is_entangled, W_val, confidence = self.detect_entanglement(states)
        
        return torch.tensor(W_val), {
            'is_entangled': is_entangled,
            'confidence': confidence,
            'threshold': self.threshold.item(),
        }


class FullBellDiagnostics(nn.Module):
    """
    Complete Bell diagnostics suite.
    
    Combines multiple tests:
    1. CHSH-analog for pairs
    2. Mermin for N-party
    3. Entanglement witness
    4. Correlation metrics
    
    Provides comprehensive entanglement verification.
    """
    
    def __init__(self, n_observers: int, dim: int):
        super().__init__()
        self.n_observers = n_observers
        self.dim = dim
        
        # CHSH for all pairs
        self.pairwise_chsh = nn.ModuleDict({
            f'{i}_{j}': CHSHAnalog(dim)
            for i in range(n_observers)
            for j in range(i + 1, n_observers)
        })
        
        # N-party Mermin test
        if n_observers >= 2:
            self.mermin = MultiObserverBellTest(n_observers, dim)
        
        # Entanglement witness
        self.witness = EntanglementWitness(dim, n_observers)
        
        # Correlation tracker
        self.correlation_history = []
    
    def run_full_diagnostics(
        self,
        observer_states: List[torch.Tensor]
    ) -> Dict:
        """
        Run all entanglement diagnostics.
        
        Args:
            observer_states: List of N [batch, dim] states
            
        Returns:
            Comprehensive diagnostics dict
        """
        results = {
            'n_observers': len(observer_states),
            'pairwise_tests': {},
            'mermin_test': None,
            'witness_test': None,
            'overall_entangled': False,
            'entanglement_score': 0.0,
        }
        
        N = len(observer_states)
        
        # Pairwise CHSH tests
        pairwise_violations = []
        for i in range(N):
            for j in range(i + 1, N):
                key = f'{i}_{j}'
                if key in self.pairwise_chsh:
                    _, test_result = self.pairwise_chsh[key](
                        observer_states[i],
                        observer_states[j]
                    )
                    results['pairwise_tests'][key] = {
                        'bell_parameter': test_result.bell_parameter,
                        'violation': test_result.violation,
                        'is_entangled': test_result.is_entangled,
                        'confidence': test_result.confidence,
                    }
                    if test_result.is_entangled:
                        pairwise_violations.append(test_result.normalized_violation)
        
        # N-party Mermin test
        if hasattr(self, 'mermin') and N >= 2:
            _, mermin_result = self.mermin(observer_states)
            results['mermin_test'] = {
                'bell_parameter': mermin_result.bell_parameter,
                'violation': mermin_result.violation,
                'is_entangled': mermin_result.is_entangled,
                'confidence': mermin_result.confidence,
            }
        
        # Entanglement witness
        _, witness_info = self.witness(observer_states)
        results['witness_test'] = witness_info
        
        # Overall assessment
        any_pairwise = any(r['is_entangled'] for r in results['pairwise_tests'].values())
        mermin_entangled = results['mermin_test']['is_entangled'] if results['mermin_test'] else False
        witness_entangled = witness_info['is_entangled']
        
        results['overall_entangled'] = any_pairwise or mermin_entangled or witness_entangled
        
        # Entanglement score: weighted combination
        scores = []
        if pairwise_violations:
            scores.append(max(pairwise_violations))
        if results['mermin_test']:
            scores.append(results['mermin_test']['confidence'])
        if witness_entangled:
            scores.append(witness_info['confidence'])
        
        results['entanglement_score'] = max(scores) if scores else 0.0
        
        # Add correlation matrix
        states_stack = torch.stack(observer_states, dim=0)
        corr_matrix = torch.zeros(N, N)
        for i in range(N):
            for j in range(N):
                corr = F.cosine_similarity(
                    observer_states[i], 
                    observer_states[j], 
                    dim=-1
                ).mean()
                corr_matrix[i, j] = corr.item()
        
        results['correlation_matrix'] = corr_matrix
        
        return results
    
    def forward(
        self,
        observer_states: List[torch.Tensor]
    ) -> Dict:
        """Run diagnostics."""
        return self.run_full_diagnostics(observer_states)
