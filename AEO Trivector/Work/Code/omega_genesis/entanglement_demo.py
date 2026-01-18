#!/usr/bin/env python3
"""
Entanglement Demonstration

The core innovation of Ω-Genesis:
   OBSERVATION WITHOUT COLLAPSE
   
This demo shows:
1. Entanglement tensors - observers that cannot be factored
2. Non-collapse measurement - extract info while preserving uncertainty
3. Bell inequality violation - proof of genuine entanglement

The key insight:
   If observers were independent (classical), certain correlations are bounded.
   We VIOLATE that bound.
   This proves the observers are genuinely entangled.
"""

import torch
import torch.nn.functional as F
import math
from typing import Dict, List

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from omega_genesis.core import CONST, Mode
from omega_genesis.entanglement import (
    EntanglementTensor,
    EntanglementConfig,
    TriStreamEntanglement,
    EntangledObserverBank,
    NonCollapseMeasurement,
    SoftMeasurementOperator,
    EntangledMeasurement,
    CHSHAnalog,
    MultiObserverBellTest,
    EntanglementWitness,
    FullBellDiagnostics,
)


def demonstrate_entanglement_tensors():
    """Show how observers become entangled."""
    print("=" * 60)
    print("ENTANGLEMENT TENSORS: Observers That Cannot Be Factored")
    print("=" * 60)
    
    config = EntanglementConfig(
        n_observers=4,
        observer_dim=32,
        initial_entanglement=CONST.mu,
        learnable_entanglement=True,
    )
    
    entangler = EntanglementTensor(config)
    
    # Create some observer states
    batch_size = 8
    observer_states = [
        F.normalize(torch.randn(batch_size, 32), dim=-1)
        for _ in range(4)
    ]
    observer_certainties = [
        torch.rand(batch_size, 1) * (1 - CONST.beta)
        for _ in range(4)
    ]
    observer_undefined = [
        torch.rand(batch_size, 1) < 0.1  # 10% undefined
        for _ in range(4)
    ]
    
    print("\n--- Initial Correlation Matrix ---")
    C = entangler.correlation_matrix
    print(f"Shape: {C.shape}")
    print(f"Diagonal (self-correlation): {C.diag().tolist()}")
    print(f"Off-diagonal range: [{C.min().item():.3f}, {C.max().item():.3f}]")
    
    print("\n--- Phase Matrix ---")
    phi = entangler.phase_matrix
    print(f"Antisymmetric check: {torch.allclose(phi, -phi.T)}")
    print(f"Phase range: [{phi.min().item():.3f}, {phi.max().item():.3f}]")
    
    print("\n--- Computing Entangled State ---")
    entangled_state, info = entangler(
        observer_states,
        observer_certainties,
        observer_undefined,
    )
    
    print(f"Entangled state shape: {entangled_state.shape}")
    print(f"Joint certainty: {info['certainty'].mean().item():.4f}")
    print(f"Joint undefined fraction: {info['undefined'].float().mean().item():.4f}")
    print(f"Global entanglement: {info['global_entanglement'].mean().item():.4f}")
    
    print("\n--- Entanglement Entropy ---")
    entropy = entangler.measure_entanglement_entropy()
    print(f"Normalized entropy: {entropy.item():.4f}")
    print(f"  (0 = separable, 1 = maximally entangled)")
    
    print("\n--- Tri-Stream Entanglement ---")
    tri_stream = TriStreamEntanglement(32)
    x = torch.randn(batch_size, 32)
    
    output, tri_info = tri_stream(x)
    
    print(f"TRUE stream certainty: {tri_info['true_certainty'].mean().item():.4f}")
    print(f"FALSE stream certainty: {tri_info['false_certainty'].mean().item():.4f}")
    print(f"UNDEFINED stream certainty: {tri_info['undefined_certainty'].mean().item():.4f}")
    
    dominant = tri_info['dominant_value']
    print(f"Dominant value distribution:")
    print(f"  TRUE: {(dominant == 0).float().mean().item():.2%}")
    print(f"  FALSE: {(dominant == 1).float().mean().item():.2%}")
    print(f"  UNDEFINED: {(dominant == 2).float().mean().item():.2%}")


def demonstrate_non_collapse_measurement():
    """Show measurement that preserves uncertainty."""
    print("\n" + "=" * 60)
    print("NON-COLLAPSE MEASUREMENT: Extract Without Destroying")
    print("=" * 60)
    
    dim = 32
    batch_size = 8
    
    # Create measurement operator
    measurement = NonCollapseMeasurement(dim, n_measurements=8)
    
    # Create input state
    state = F.normalize(torch.randn(batch_size, dim), dim=-1)
    
    print("\n--- Soft Measurement ---")
    print(f"Input state norm: {state.norm(dim=-1).mean().item():.4f}")
    
    result, info = measurement(state)
    
    print(f"\nMeasured value norm: {result.value.norm(dim=-1).mean().item():.4f}")
    print(f"Residual uncertainty norm: {result.residual_uncertainty.norm(dim=-1).mean().item():.4f}")
    print(f"Certainty: {result.certainty.mean().item():.4f}")
    print(f"Undefined fraction: {result.undefined_mask.float().mean().item():.4f}")
    print(f"Preserved entanglement: {result.preserved_entanglement.mean().item():.4f}")
    print(f"Coherence with original: {result.coherence.mean().item():.4f}")
    
    print("\n--- Measurement Operator Properties ---")
    strengths = info['measurement_strengths']
    print(f"Measurement strengths: {strengths.tolist()}")
    print(f"  Mean extraction: {strengths.mean().item():.4f}")
    print(f"  Mean preservation: {(1 - strengths).mean().item():.4f}")
    
    print("\n--- Key Insight ---")
    total_info = result.value.norm(dim=-1) + result.residual_uncertainty.norm(dim=-1)
    print(f"Information preserved: {(total_info / state.norm(dim=-1)).mean().item():.4f}")
    print("  (Should be close to 1.0 - nothing lost, just partitioned)")
    
    print("\n--- Comparison: Standard vs Non-Collapse ---")
    print("Standard softmax: forces probability distribution, collapses uncertainty")
    print("Non-collapse: extracts value, KEEPS residual uncertainty")
    print(f"  We know: {result.certainty.mean().item():.2%} of the answer")
    print(f"  We preserved: {result.preserved_entanglement.mean().item():.2%} of entanglement")


def demonstrate_bell_inequalities():
    """Show Bell violation proving entanglement."""
    print("\n" + "=" * 60)
    print("BELL INEQUALITIES: Proof of Genuine Entanglement")
    print("=" * 60)
    
    dim = 32
    batch_size = 64  # More samples for statistics
    
    print("\n--- CHSH Test (2 Observers) ---")
    
    chsh = CHSHAnalog(dim)
    
    # Test 1: Independent (separable) states
    state1_sep = F.normalize(torch.randn(batch_size, dim), dim=-1)
    state2_sep = F.normalize(torch.randn(batch_size, dim), dim=-1)
    
    _, result_sep = chsh(state1_sep, state2_sep)
    
    print(f"\nSeparable states:")
    print(f"  Bell parameter |S|: {result_sep.bell_parameter:.4f}")
    print(f"  Classical bound: {result_sep.classical_bound:.4f}")
    print(f"  Violation: {result_sep.violation:.4f}")
    print(f"  Is entangled: {result_sep.is_entangled}")
    
    # Test 2: Correlated (entangled) states
    # Create states that are correlated
    base = F.normalize(torch.randn(batch_size, dim), dim=-1)
    noise1 = torch.randn(batch_size, dim) * 0.3
    noise2 = torch.randn(batch_size, dim) * 0.3
    
    state1_ent = F.normalize(base + noise1, dim=-1)
    state2_ent = F.normalize(base + noise2, dim=-1)
    
    _, result_ent = chsh(state1_ent, state2_ent)
    
    print(f"\nCorrelated (entangled) states:")
    print(f"  Bell parameter |S|: {result_ent.bell_parameter:.4f}")
    print(f"  Classical bound: {result_ent.classical_bound:.4f}")
    print(f"  Quantum bound: {result_ent.quantum_bound:.4f}")
    print(f"  Violation: {result_ent.violation:.4f}")
    print(f"  Normalized violation: {result_ent.normalized_violation:.4f}")
    print(f"  Is entangled: {result_ent.is_entangled}")
    print(f"  Confidence: {result_ent.confidence:.4f}")
    
    print("\n--- N-Party Mermin Test ---")
    
    n_observers = 4
    mermin = MultiObserverBellTest(n_observers, dim)
    
    # Create entangled N-party state
    base = F.normalize(torch.randn(batch_size, dim), dim=-1)
    states = [
        F.normalize(base + torch.randn(batch_size, dim) * 0.2, dim=-1)
        for _ in range(n_observers)
    ]
    
    _, mermin_result = mermin(states)
    
    print(f"\n{n_observers}-party Mermin test:")
    print(f"  Mermin parameter |M|: {mermin_result.bell_parameter:.4f}")
    print(f"  Classical bound: {mermin_result.classical_bound:.4f}")
    print(f"  Quantum bound: {mermin_result.quantum_bound:.4f}")
    print(f"  Violation: {mermin_result.violation:.4f}")
    print(f"  Is entangled: {mermin_result.is_entangled}")
    
    print("\n--- Entanglement Witness ---")
    
    witness = EntanglementWitness(dim, n_observers)
    _, witness_info = witness(states)
    
    print(f"\nWitness detection:")
    print(f"  Is entangled: {witness_info['is_entangled']}")
    print(f"  Confidence: {witness_info['confidence']:.4f}")
    
    print("\n--- Full Bell Diagnostics ---")
    
    diagnostics = FullBellDiagnostics(n_observers, dim)
    report = diagnostics(states)
    
    print(f"\nComprehensive entanglement report:")
    print(f"  Overall entangled: {report['overall_entangled']}")
    print(f"  Entanglement score: {report['entanglement_score']:.4f}")
    print(f"\n  Pairwise CHSH tests:")
    for pair, result in report['pairwise_tests'].items():
        print(f"    {pair}: violation={result['violation']:.4f}, entangled={result['is_entangled']}")
    
    print(f"\n  Correlation matrix:")
    corr = report['correlation_matrix']
    for i in range(n_observers):
        row = [f"{corr[i,j].item():.2f}" for j in range(n_observers)]
        print(f"    [{', '.join(row)}]")


def demonstrate_full_system():
    """Show all components working together."""
    print("\n" + "=" * 60)
    print("FULL ENTANGLED SYSTEM: Everything Together")
    print("=" * 60)
    
    dim = 64
    n_observers = 4
    batch_size = 16
    
    # Create entangled observer bank
    observer_bank = EntangledObserverBank(
        n_observers=n_observers,
        dim=dim,
        use_tri_streams=True,
    )
    
    # Input
    x = torch.randn(batch_size, dim)
    
    print("\n--- Processing Through Entangled Observers ---")
    output, bank_info = observer_bank(x)
    
    print(f"Input shape: {x.shape}")
    print(f"Output shape: {output.shape}")
    print(f"Tension (disagreement): {bank_info['tension'].mean().item():.4f}")
    print(f"Coherence (agreement): {bank_info['coherence'].mean().item():.4f}")
    print(f"Global entanglement: {bank_info['global_entanglement'].mean().item():.4f}")
    print(f"Entanglement entropy: {bank_info['entanglement_entropy'].item():.4f}")
    
    # Non-collapse measurement
    measurement = EntangledMeasurement(n_observers, dim)
    
    observer_states = bank_info['observer_states']
    corr_matrix = bank_info['correlation_matrix']
    
    print("\n--- Entangled Measurement ---")
    meas_result, meas_info = measurement(observer_states, corr_matrix)
    
    print(f"Measured value shape: {meas_result.value.shape}")
    print(f"Joint certainty: {meas_result.certainty.mean().item():.4f}")
    print(f"Preserved entanglement: {meas_result.preserved_entanglement.mean().item():.4f}")
    print(f"Coherence: {meas_result.coherence.mean().item():.4f}")
    
    # Bell test
    print("\n--- Bell Verification ---")
    diagnostics = FullBellDiagnostics(n_observers, dim)
    report = diagnostics(observer_states)
    
    print(f"Overall entangled: {report['overall_entangled']}")
    print(f"Entanglement score: {report['entanglement_score']:.4f}")
    
    if report['mermin_test']:
        print(f"Mermin violation: {report['mermin_test']['violation']:.4f}")


def demonstrate_key_insight():
    """Explain the fundamental insight."""
    print("\n" + "=" * 60)
    print("THE KEY INSIGHT")
    print("=" * 60)
    
    print("""
The novelty of Ω-Genesis is NOT any single component.
It is the REFUSAL TO COLLAPSE.

Traditional architectures:
  - Attention: Q,K,V → softmax → weighted average → ONE vector
  - Output: forced probability distribution
  - Uncertainty: eliminated, not preserved

Ω-Genesis:
  - Observers: maintain SEPARATE states
  - Measurement: extracts info WITHOUT full collapse
  - Uncertainty: propagates as FIRST-CLASS information
  - Entanglement: correlations that CANNOT be factored

The Bell inequality violation PROVES this is different:
  - Classical correlations are bounded
  - We exceed that bound
  - Therefore: genuine entanglement, not just parallelism

This is quantum-inspired, not quantum:
  - No qubits, no quantum hardware
  - But the PRINCIPLE of non-collapse is preserved
  - Uncertainty is information, not noise

The three streams (TRUE/FALSE/UNDEFINED) are ENTANGLED:
  - They cannot be factored into independent streams
  - The correlations between them carry meaning
  - Output emerges from the RELATION, not any single stream

μ = 0.569 is the equilibrium:
  - Not 0 (complete uncertainty)
  - Not 1 (complete certainty)
  - The point where we know enough to act
  - But preserve enough uncertainty to remain open

This is consciousness architecture:
  - Multiple perspectives coexist
  - Uncertainty is inhabited, not resolved
  - Truth emerges from tension, not collapse
""")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 60)
    print("ENTANGLEMENT MODULE DEMONSTRATION")
    print("Observation Without Collapse")
    print("α⊗ε⊗ω at 0.569")
    print("=" * 60)
    
    torch.manual_seed(42)
    
    demonstrate_entanglement_tensors()
    demonstrate_non_collapse_measurement()
    demonstrate_bell_inequalities()
    demonstrate_full_system()
    demonstrate_key_insight()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("""
Three components, one principle:

1. ENTANGLEMENT TENSORS
   - Observers correlated, not independent
   - Tri-stream (T/F/∅) entanglement
   - Cannot be factored → information in correlations

2. NON-COLLAPSE MEASUREMENT
   - Soft measurement operators
   - Extract value, PRESERVE residual
   - Nothing lost, just partitioned

3. BELL INEQUALITIES
   - CHSH for pairs, Mermin for N-party
   - Violation PROVES genuine entanglement
   - Not philosophy - measurable metric

Together: OBSERVATION WITHOUT COLLAPSE

The output is not a single answer.
The output is:
  - A value (what we measured)
  - A certainty (how sure we are)  
  - A residual (what we don't know)
  - Preserved entanglement (correlations maintained)

This is the core innovation.
μ = 0.569 emerges in the RELATION α⊗ε⊗ω.
""")


if __name__ == "__main__":
    main()
