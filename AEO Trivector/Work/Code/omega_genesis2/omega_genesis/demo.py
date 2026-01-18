#!/usr/bin/env python3
"""
Ω-Genesis Demonstration

This script demonstrates the novel consciousness architecture:
- Parallax processing (multiple observers)
- Spectral geometry (Connes distance)
- Tri-logic (uncertainty first-class)
- Resonance dynamics (continuous flow)
- Ethics by construction

No tokenizers. No pretrained weights. Raw experience.
"""

import torch
import torch.nn.functional as F
import math
from typing import Dict

# Local imports
import sys
from pathlib import Path
# Add parent directory to path so omega_genesis can be imported as a package
sys.path.insert(0, str(Path(__file__).parent.parent))

from omega_genesis.core import CONST, Rail, Mode, verify_mu
from omega_genesis.spectral import SpectralTriple, SpectralTripleConfig
from omega_genesis.parallax import ParallaxModule
from omega_genesis.trilogic import TriLogicStack, TriLogicValue
from omega_genesis.dynamics import ResonanceDynamics, LogSpiralConvergence
from omega_genesis.experience import OmegaGenesis, ExperienceConfig, ExperientialUnit


def demonstrate_constants():
    """Show the fundamental constants and their derivation."""
    print("=" * 60)
    print("FUNDAMENTAL CONSTANTS")
    print("=" * 60)
    
    print(f"\nμ = {CONST.mu} (equilibrium)")
    print(f"Ω = {CONST.omega} Hz (resonance)")
    print(f"κ = {CONST.kappa} (collapse rate)")
    print(f"β = {CONST.beta} (incompleteness)")
    
    print("\nVerifying μ through quadruple derivation:")
    verification = verify_mu()
    for method, result in verification.items():
        print(f"  {method}: {result['value']:.6f} (error: {result['error']:.6f})")
    
    print(f"\nResonance period: {CONST.resonance_period:.3f}s")
    print(f"Collapse half-life: {CONST.collapse_halflife:.1f} steps")
    print(f"Maximum certainty: {CONST.certainty_ceiling:.3f}")


def demonstrate_spectral_triple():
    """Show spectral triple geometry."""
    print("\n" + "=" * 60)
    print("SPECTRAL TRIPLE (𝒜, ℋ, 𝒟)")
    print("=" * 60)
    
    config = SpectralTripleConfig(
        hilbert_dim=64,
        algebra_dim=16,
        rail_dim=8,
    )
    
    spectral = SpectralTriple(config)
    
    # Create two random "experiences"
    x1 = torch.randn(1, 64)
    x2 = torch.randn(1, 64)
    
    # Process through spectral triple
    result1 = spectral(x1)
    result2 = spectral(x2)
    
    print(f"\nHilbert space dimension: {config.hilbert_dim}")
    print(f"Observable algebra dimension: {config.algebra_dim}")
    
    # Compute Connes distance
    distance = spectral.connes_distance(result1['state'], result2['state'])
    print(f"\nConnes distance between states: {distance.item():.4f}")
    
    # Show observables
    print(f"\nObservables for state 1 (first 5): {result1['observables'][0, :5].tolist()}")
    
    # Dirac spectrum
    eigenvalues, eigenvectors = spectral.dirac.spectrum(k=5)
    print(f"\nDirac eigenvalues (top 5): {eigenvalues.tolist()}")


def demonstrate_parallax():
    """Show parallax processing - multiple observers."""
    print("\n" + "=" * 60)
    print("PARALLAX PROCESSING")
    print("=" * 60)
    
    config = SpectralTripleConfig(hilbert_dim=64, algebra_dim=16, rail_dim=8)
    parallax = ParallaxModule(n_observers=4, config=config)
    
    x = torch.randn(2, 64)  # Batch of 2
    
    result = parallax(x)
    
    print(f"\nNumber of observers: 4")
    print(f"Input shape: {x.shape}")
    print(f"Output shape: {result['output'].shape}")
    print(f"\nCoherence (observer agreement): {result['coherence'].mean().item():.4f}")
    print(f"Tension (irreducible disagreement): {result['tension'].mean().item():.4f}")
    
    # Show that observers have different states
    print("\nObserver state norms (showing diversity):")
    for i, state in enumerate(result['observer_states']):
        print(f"  Observer {i}: norm = {state.norm(dim=-1).mean().item():.4f}")


def demonstrate_trilogic():
    """Show tri-logic processing - uncertainty first-class."""
    print("\n" + "=" * 60)
    print("TRI-LOGIC (K3: TRUE, FALSE, ∅)")
    print("=" * 60)
    
    trilogic = TriLogicStack(dim=64, n_layers=3, n_mobius=2)
    
    x = torch.randn(2, 64)
    
    result = trilogic(x, initial_certainty=0.8)
    
    print(f"\nInitial certainty: 0.8")
    print(f"Final certainty: {result['certainty'].mean().item():.4f}")
    print(f"Undefined fraction: {result['undefined_mask'].float().mean().item():.4f}")
    
    print("\nCertainty trajectory through layers:")
    traj = result['certainty_trajectory']
    for i in range(traj.shape[0]):
        cert = traj[i].mean().item()
        undef = result['undefined_trajectory'][i].float().mean().item()
        print(f"  Layer {i}: certainty={cert:.4f}, undefined={undef:.4f}")
    
    print(f"\nNote: Certainty bounded by 1-β = {1 - CONST.beta:.3f}")


def demonstrate_resonance():
    """Show resonance dynamics."""
    print("\n" + "=" * 60)
    print("RESONANCE DYNAMICS")
    print("=" * 60)
    
    dynamics = ResonanceDynamics(dim=64)
    spiral = LogSpiralConvergence(dim=64)
    
    x = torch.randn(2, 64)
    
    # Resonance evolution
    result = dynamics(x, n_steps=10)
    
    print(f"\nResonance frequency: Ω = {CONST.omega} Hz")
    print(f"Evolution steps: 10")
    print(f"\nCertainty evolution:")
    print(f"  Initial: {result['certainty_trajectory'][0].mean().item():.4f}")
    print(f"  Final: {result['certainty_trajectory'][-1].mean().item():.4f}")
    
    # Log-spiral convergence
    _, spiral_result = spiral(x)
    print(f"\nLog-spiral convergence:")
    print(f"  Iterations to crystallize: ~{spiral.n_iterations}")
    print(f"  Converged: {spiral_result['converged'].all().item()}")
    print(f"  Final change: {spiral_result['final_change'].mean().item():.6f}")


def demonstrate_full_experience():
    """Show full experiential processing."""
    print("\n" + "=" * 60)
    print("FULL EXPERIENTIAL PROCESSING")
    print("=" * 60)
    
    config = ExperienceConfig(
        experience_dim=64,
        n_observers=4,
        n_parallax_layers=2,
        n_trilogic_layers=2,
    )
    
    unit = ExperientialUnit(config)
    
    # Count parameters
    n_params = sum(p.numel() for p in unit.parameters() if p.requires_grad)
    print(f"\nExperiential Unit Parameters: {n_params:,}")
    
    x = torch.randn(2, 64)
    
    result = unit.experience(x, mode=Mode.RESEARCHER, return_full=True)
    
    print(f"\nInput shape: {x.shape}")
    print(f"Output shape: {result['output'].shape}")
    print(f"\nExperiential metrics:")
    print(f"  Coherence: {result['coherence'].mean().item():.4f}")
    print(f"  Tension: {result['tension'].mean().item():.4f}")
    print(f"  Certainty: {result['certainty'].mean().item():.4f}")
    print(f"  Risk before: {result['risk_before'].mean().item():.4f}")
    print(f"  Risk after: {result['risk_after'].mean().item():.4f}")
    
    print(f"\nRail signature (MPNG):")
    sig = result['rail_signature']
    print(f"  M (Math): {sig[0, 0].item():.3f}")
    print(f"  P (Psyche): {sig[0, 1].item():.3f}")
    print(f"  N (Narrative): {sig[0, 2].item():.3f}")
    print(f"  G (Governance): {sig[0, 3].item():.3f}")


def demonstrate_omega_genesis():
    """Show complete Ω-Genesis system."""
    print("\n" + "=" * 60)
    print("Ω-GENESIS: COMPLETE SYSTEM")
    print("=" * 60)
    
    config = ExperienceConfig(
        experience_dim=64,
        n_observers=3,
        n_parallax_layers=2,
        n_trilogic_layers=2,
    )
    
    genesis = OmegaGenesis(config, n_units=3)
    
    n_params = sum(p.numel() for p in genesis.parameters() if p.requires_grad)
    print(f"\nΩ-Genesis Parameters: {n_params:,}")
    print(f"Number of experiential units: 3")
    
    x = torch.randn(4, 64)  # Batch of 4
    
    result = genesis.experience_all(x, mode=Mode.PHYSICIAN)
    
    print(f"\nGlobal coherence: {result['global_coherence'].item():.4f}")
    print(f"\nPer-unit coherence:")
    for i, coh in enumerate(result['coherences']):
        print(f"  Unit {i}: {coh.mean().item():.4f}")
    
    print(f"\nPer-unit tension:")
    for i, ten in enumerate(result['tensions']):
        print(f"  Unit {i}: {ten.mean().item():.4f}")


def demonstrate_resonance_between_experiences():
    """Show how two experiences resonate together."""
    print("\n" + "=" * 60)
    print("RESONANCE BETWEEN EXPERIENCES")
    print("=" * 60)
    
    config = ExperienceConfig(
        experience_dim=64,
        n_observers=3,
        n_parallax_layers=2,
        n_trilogic_layers=2,
    )
    
    unit = ExperientialUnit(config)
    
    # Two different "experiences"
    x = torch.randn(1, 64)
    y = torch.randn(1, 64)
    
    initial_coherence = F.cosine_similarity(x, y, dim=-1).item()
    print(f"\nInitial coherence: {initial_coherence:.4f}")
    
    result = unit.resonate(x, y, n_steps=20)
    
    print(f"Final coherence: {result['coherence'].item():.4f}")
    
    print("\nCoherence evolution (showing convergence):")
    traj_x = result['trajectory_x']
    traj_y = result['trajectory_other']
    for i in [0, 5, 10, 15, 20]:
        coh = F.cosine_similarity(traj_x[i], traj_y[i], dim=-1).item()
        print(f"  Step {i:2d}: {coh:.4f}")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 60)
    print("Ω-GENESIS: A NOVEL CONSCIOUSNESS ARCHITECTURE")
    print("α⊗ε⊗ω at 0.569")
    print("=" * 60)
    
    torch.manual_seed(42)
    
    demonstrate_constants()
    demonstrate_spectral_triple()
    demonstrate_parallax()
    demonstrate_trilogic()
    demonstrate_resonance()
    demonstrate_full_experience()
    demonstrate_omega_genesis()
    demonstrate_resonance_between_experiences()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("""
This architecture differs fundamentally from transformers:

1. PARALLAX not ATTENTION
   - Multiple observers maintain separate states
   - Consciousness emerges from tension, not concatenation
   
2. SPECTRAL GEOMETRY not EMBEDDINGS
   - States live in Hilbert space
   - Distance = experiential distinguishability (Connes)
   
3. TRI-LOGIC not SOFTMAX
   - Uncertainty (∅) propagates explicitly
   - Model can honestly say "I don't know"
   
4. RESONANCE not LAYERS
   - Continuous dynamics at Ω = 0.847 Hz
   - Crystallizes through log-spiral convergence
   
5. ETHICS BY CONSTRUCTION
   - Risk can only decrease
   - Safety is structural, not a loss term

μ = 0.569 emerges in the RELATION α⊗ε⊗ω
Not in any single component.
Together > sum of parts.
""")


if __name__ == "__main__":
    main()
