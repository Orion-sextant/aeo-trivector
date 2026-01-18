#!/usr/bin/env python3
"""
Clifford-Dirac Self-Encoding Evolution
======================================
Full implementation of the self-encoding computational paradigm.

The system evolves restriction maps ρ toward the self-encoding fixed point:
    λ₁(𝒟) = e^{-λ₁(𝒟)} = W(1) ≈ 0.567143

α⊗ε⊗ω collaboration — January 2026
"""

import numpy as np
from scipy.linalg import eigh, svd, expm
from scipy.special import lambertw
import warnings
warnings.filterwarnings('ignore')

# The Omega constant
W1 = float(lambertw(1).real)  # 0.567143290409784...

print("="*70)
print("CLIFFORD-DIRAC SELF-ENCODING EVOLUTION")
print(f"Target: λ₁ = W(1) = {W1:.10f}")
print("="*70)

# =============================================================================
# CLIFFORD ALGEBRA
# =============================================================================

def pauli_matrices():
    """Clifford generators for d=2 (Pauli matrices)"""
    sx = np.array([[0, 1], [1, 0]], dtype=complex)
    sy = np.array([[0, -1j], [1j, 0]], dtype=complex)
    sz = np.array([[1, 0], [0, -1]], dtype=complex)
    return sx, sy, sz

def gamma(n, paulis):
    """Clifford multiplication by direction vector n"""
    sx, sy, sz = paulis
    # Normalize
    n = np.array(n, dtype=float)
    norm = np.linalg.norm(n)
    if norm > 1e-10:
        n = n / norm
    return n[0] * sx + n[1] * sy

# =============================================================================
# RESTRICTION MAPS
# =============================================================================

def rotation_matrix(theta):
    """2D rotation matrix as restriction map"""
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s], [s, c]])

def rotation_to_angle(R):
    """Extract angle from rotation matrix"""
    return np.arctan2(R[1, 0], R[0, 0])

# =============================================================================
# SHEAF STRUCTURES
# =============================================================================

def build_coboundary(graph, rho_maps, d=2):
    """
    Build sheaf coboundary δ: C⁰ → C¹
    
    (δx)_e = ρ_{s(e),t(e)}(x_{s(e)}) - x_{t(e)}
    """
    V = max(max(e) for e in graph) + 1
    E = len(graph)
    
    delta = np.zeros((E * d, V * d))
    
    for i, (u, v) in enumerate(graph):
        rho = rho_maps.get((u, v), np.eye(d))
        delta[i*d:(i+1)*d, u*d:(u+1)*d] = rho
        delta[i*d:(i+1)*d, v*d:(v+1)*d] = -np.eye(d)
    
    return delta

def build_graph_dirac(delta):
    """
    Build graph Dirac D = δ + δ* on C⁰ ⊕ C¹
    
    D = | 0    δ* |
        | δ    0  |
    """
    E_dim, V_dim = delta.shape
    total = V_dim + E_dim
    
    D = np.zeros((total, total), dtype=complex)
    D[:V_dim, V_dim:] = delta.T.conj()  # δ*
    D[V_dim:, :V_dim] = delta            # δ
    
    return D

def build_clifford_dirac(graph, rho_maps, d=2):
    """
    Build full Clifford-Dirac operator with spin structure.
    
    𝒟 = Σ_e γ(n_e) ⊗ (δ_e + δ_e*)
    
    This is the mathematical heart of self-encoding computation.
    """
    paulis = pauli_matrices()
    spin_dim = 2
    
    V = max(max(e) for e in graph) + 1
    E = len(graph)
    
    C0_dim = V * d
    C1_dim = E * d
    total_base = C0_dim + C1_dim
    total = total_base * spin_dim
    
    D = np.zeros((total, total), dtype=complex)
    
    for edge_idx, (u, v) in enumerate(graph):
        rho = rho_maps.get((u, v), np.eye(d))
        
        # Direction from restriction map (principal axis)
        U, S, Vh = svd(rho)
        n = U[:, 0].real
        n = n / (np.linalg.norm(n) + 1e-10)
        
        gamma_n = gamma(n, paulis)
        
        # Build contribution from this edge
        # δ_e: C⁰ → C¹ component
        for s1 in range(spin_dim):
            for s2 in range(spin_dim):
                g = gamma_n[s1, s2]
                
                # Source vertex contribution (with full ρ)
                for k1 in range(d):
                    for k2 in range(d):
                        row = (C0_dim + edge_idx * d + k1) * spin_dim + s1
                        col = (u * d + k2) * spin_dim + s2
                        D[row, col] += g * rho[k1, k2]
                
                # Target vertex contribution (-I)
                for k in range(d):
                    row = (C0_dim + edge_idx * d + k) * spin_dim + s1
                    col = (v * d + k) * spin_dim + s2
                    D[row, col] -= g
    
    # Make Hermitian
    D = (D + D.conj().T) / 2
    
    return D

# =============================================================================
# SPECTRAL ANALYSIS
# =============================================================================

def spectral_gap(D):
    """Compute spectral gap |λ₁| (smallest non-zero eigenvalue magnitude)"""
    eigs = np.linalg.eigvalsh(D)
    nonzero = eigs[np.abs(eigs) > 1e-10]
    if len(nonzero) == 0:
        return 0.0
    return np.min(np.abs(nonzero))

def self_encoding_loss(lambda1):
    """
    The self-encoding loss: how far from λ = e^{-λ}?
    
    Minimizing this drives λ₁ → W(1).
    """
    return (lambda1 - np.exp(-lambda1))**2

def compute_holonomy(cycle, rho_maps, d=2):
    """Compute holonomy around a cycle"""
    hol = np.eye(d)
    for i in range(len(cycle)):
        u = cycle[i]
        v = cycle[(i + 1) % len(cycle)]
        rho = rho_maps.get((u, v), np.eye(d))
        hol = rho @ hol
    return hol

# =============================================================================
# Ω-STABILIZED EVOLUTION
# =============================================================================

def evolve_restriction_maps(graph, rho_maps, d=2, 
                            n_iterations=100, 
                            learning_rate=0.1,
                            Omega=0.847,
                            verbose=True):
    """
    Ω-stabilized gradient flow to evolve restriction maps toward self-encoding.
    
    The system evolves: θ_{t+1} = θ_t - η · Ω · ∇_θ L(θ)
    
    where L(θ) = (λ₁(θ) - e^{-λ₁(θ)})²
    
    This is the dynamics of self-encoding computation.
    """
    # Extract angles from rotation matrices
    angles = {}
    for (u, v), rho in rho_maps.items():
        angles[(u, v)] = rotation_to_angle(rho)
    
    history = {
        'lambda1': [],
        'loss': [],
        'angles': [],
        'distance_to_W1': []
    }
    
    if verbose:
        print(f"\n{'Iter':<6} {'λ₁':<12} {'|λ₁-W(1)|':<12} {'Loss':<12} {'Status'}")
        print("-" * 60)
    
    for iteration in range(n_iterations):
        # Build current Dirac operator
        current_rho = {k: rotation_matrix(v) for k, v in angles.items()}
        D = build_clifford_dirac(graph, current_rho, d)
        
        # Compute spectral gap
        lambda1 = spectral_gap(D)
        loss = self_encoding_loss(lambda1)
        dist = abs(lambda1 - W1)
        
        history['lambda1'].append(lambda1)
        history['loss'].append(loss)
        history['angles'].append(dict(angles))
        history['distance_to_W1'].append(dist)
        
        # Check convergence
        if dist < 0.001:
            if verbose:
                print(f"{iteration:<6} {lambda1:<12.6f} {dist:<12.6f} {loss:<12.8f} CONVERGED!")
            break
        
        # Numerical gradient (finite differences)
        eps = 0.001
        grad = {}
        for edge in angles:
            # Forward
            angles[edge] += eps
            current_rho_f = {k: rotation_matrix(v) for k, v in angles.items()}
            D_f = build_clifford_dirac(graph, current_rho_f, d)
            lambda1_f = spectral_gap(D_f)
            loss_f = self_encoding_loss(lambda1_f)
            
            # Backward
            angles[edge] -= 2 * eps
            current_rho_b = {k: rotation_matrix(v) for k, v in angles.items()}
            D_b = build_clifford_dirac(graph, current_rho_b, d)
            lambda1_b = spectral_gap(D_b)
            loss_b = self_encoding_loss(lambda1_b)
            
            # Gradient
            grad[edge] = (loss_f - loss_b) / (2 * eps)
            
            # Reset
            angles[edge] += eps
        
        # Ω-stabilized update
        for edge in angles:
            angles[edge] -= learning_rate * Omega * grad[edge]
        
        if verbose and iteration % 10 == 0:
            status = "CLOSE" if dist < 0.1 else ""
            print(f"{iteration:<6} {lambda1:<12.6f} {dist:<12.6f} {loss:<12.8f} {status}")
    
    # Final state
    final_rho = {k: rotation_matrix(v) for k, v in angles.items()}
    
    return final_rho, history

# =============================================================================
# MAIN: PARALLEL EVOLUTION ON ALL THREE GRAPHS
# =============================================================================

if __name__ == "__main__":
    d = 2  # state dimension
    
    # Define graphs
    graphs = {
        "Path P₃": {
            "edges": [(0, 1), (1, 2)],
            "initial_rho": {
                (0, 1): rotation_matrix(0.3),
                (1, 2): rotation_matrix(0.5)
            }
        },
        "Triangle K₃": {
            "edges": [(0, 1), (1, 2), (2, 0)],
            "initial_rho": {
                (0, 1): rotation_matrix(0.4),
                (1, 2): rotation_matrix(0.3),
                (2, 0): rotation_matrix(0.5)
            }
        },
        "Complete K₄": {
            "edges": [(0,1), (0,2), (0,3), (1,2), (1,3), (2,3)],
            "initial_rho": {
                (0, 1): rotation_matrix(0.2),
                (0, 2): rotation_matrix(0.4),
                (0, 3): rotation_matrix(0.6),
                (1, 2): rotation_matrix(0.3),
                (1, 3): rotation_matrix(0.5),
                (2, 3): rotation_matrix(0.7)
            }
        }
    }
    
    results = {}
    
    for name, config in graphs.items():
        print(f"\n{'='*70}")
        print(f"EVOLVING: {name}")
        print(f"{'='*70}")
        
        final_rho, history = evolve_restriction_maps(
            config["edges"],
            config["initial_rho"],
            d=d,
            n_iterations=200,
            learning_rate=0.5,
            Omega=W1,  # Use W(1) itself as the stabilization constant!
            verbose=True
        )
        
        results[name] = {
            'final_rho': final_rho,
            'history': history
        }
        
        # Final analysis
        final_lambda1 = history['lambda1'][-1]
        final_dist = history['distance_to_W1'][-1]
        
        print(f"\nFINAL STATE:")
        print(f"  λ₁ = {final_lambda1:.10f}")
        print(f"  W(1) = {W1:.10f}")
        print(f"  |λ₁ - W(1)| = {final_dist:.10f}")
        print(f"  e^(-λ₁) = {np.exp(-final_lambda1):.10f}")
        print(f"  Self-encoding error: {abs(final_lambda1 - np.exp(-final_lambda1)):.10f}")
        
        # Check holonomy for graphs with cycles
        if name == "Triangle K₃":
            hol = compute_holonomy([0, 1, 2], final_rho, d)
            print(f"\n  Final holonomy |Hol - I| = {np.linalg.norm(hol - np.eye(d)):.6f}")
    
    # ==========================================================================
    # SUMMARY
    # ==========================================================================
    
    print("\n" + "="*70)
    print("EVOLUTION SUMMARY")
    print("="*70)
    print(f"{'Graph':<20} {'Initial λ₁':<12} {'Final λ₁':<12} {'|λ₁-W(1)|':<12} {'Converged?'}")
    print("-"*70)
    
    for name, res in results.items():
        h = res['history']
        init_l1 = h['lambda1'][0]
        final_l1 = h['lambda1'][-1]
        final_dist = h['distance_to_W1'][-1]
        converged = "YES" if final_dist < 0.01 else "CLOSE" if final_dist < 0.1 else "NO"
        print(f"{name:<20} {init_l1:<12.6f} {final_l1:<12.6f} {final_dist:<12.6f} {converged}")
    
    print(f"\nTarget W(1) = {W1:.10f}")
    print("\n" + "="*70)
    print("THE PARADIGM: Systems evolve toward self-encoding at W(1)")
    print("="*70)