import numpy as np
from scipy.linalg import eigh, svd
from scipy.special import lambertw

W1 = float(lambertw(1).real)  # 0.567143...

def pauli_matrices():
    """Clifford generators for d=2"""
    sx = np.array([[0, 1], [1, 0]], dtype=complex)
    sy = np.array([[0, -1j], [1j, 0]], dtype=complex)
    sz = np.array([[1, 0], [0, -1]], dtype=complex)
    return sx, sy, sz

def gamma(n, paulis):
    """Clifford multiplication by direction n"""
    sx, sy, sz = paulis
    return n[0] * sx + n[1] * sy

def rotation_matrix(theta):
    """2D rotation as restriction map"""
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s], [s, c]])

def build_coboundary(graph, rho_maps, d=2):
    """
    Build sheaf coboundary δ: C⁰ → C¹
    graph: list of edges (source, target)
    rho_maps: dict of restriction maps {(u,v): matrix}
    """
    V = max(max(e) for e in graph) + 1
    E = len(graph)
    
    delta = np.zeros((E * d, V * d))
    
    for i, (u, v) in enumerate(graph):
        rho = rho_maps.get((u, v), np.eye(d))
        # (δx)_e = ρ(x_source) - x_target
        delta[i*d:(i+1)*d, u*d:(u+1)*d] = rho
        delta[i*d:(i+1)*d, v*d:(v+1)*d] = -np.eye(d)
    
    return delta

def build_graph_dirac(delta):
    """Build D = δ + δ* on C⁰ ⊕ C¹"""
    E_dim, V_dim = delta.shape
    total = V_dim + E_dim
    
    D = np.zeros((total, total), dtype=complex)
    D[:V_dim, V_dim:] = delta.T  # δ*
    D[V_dim:, :V_dim] = delta     # δ
    
    return D

def build_clifford_dirac(graph, rho_maps, d=2):
    """Build full Clifford-Dirac with spin structure"""
    paulis = pauli_matrices()
    spin_dim = 2  # for d=2
    
    V = max(max(e) for e in graph) + 1
    E = len(graph)
    
    # Total dimension: (V*d + E*d) * spin_dim
    C0_dim = V * d
    C1_dim = E * d
    total_base = C0_dim + C1_dim
    total = total_base * spin_dim
    
    D = np.zeros((total, total), dtype=complex)
    
    for i, (u, v) in enumerate(graph):
        rho = rho_maps.get((u, v), np.eye(d))
        
        # Extract direction from restriction map
        U, S, Vh = svd(rho)
        n = U[:, 0].real  # principal direction
        n = n / (np.linalg.norm(n) + 1e-10)
        
        gamma_n = gamma(n, paulis)
        
        # Build the edge contribution to Dirac
        # This is γ(n) ⊗ (δ_e + δ_e*)
        for s1 in range(spin_dim):
            for s2 in range(spin_dim):
                g = gamma_n[s1, s2]
                
                # δ_e part: C⁰ → C¹
                # Source contribution
                row_base = C0_dim + i * d
                col_base = u * d
                for k in range(d):
                    D[(row_base + k) * spin_dim + s1, 
                      (col_base + k) * spin_dim + s2] += g * rho[k, k] if k < rho.shape[0] else 0
                
                # Target contribution  
                col_base = v * d
                for k in range(d):
                    D[(row_base + k) * spin_dim + s1,
                      (col_base + k) * spin_dim + s2] -= g
    
    # Make Hermitian (D + D†)/2
    D = (D + D.conj().T) / 2
    
    return D

def compute_holonomy(cycle, rho_maps, d=2):
    """Compute holonomy around a cycle"""
    hol = np.eye(d)
    for i in range(len(cycle)):
        u = cycle[i]
        v = cycle[(i + 1) % len(cycle)]
        rho = rho_maps.get((u, v), np.eye(d))
        hol = rho @ hol
    return hol

def analyze_graph(name, graph, rho_maps, d=2):
    """Complete analysis of a graph"""
    print(f"\n{'='*60}")
    print(f"GRAPH: {name}")
    print(f"{'='*60}")
    
    V = max(max(e) for e in graph) + 1
    E = len(graph)
    print(f"Vertices: {V}, Edges: {E}")
    
    # Build operators
    delta = build_coboundary(graph, rho_maps, d)
    L_sheaf = delta.T @ delta
    D_graph = build_graph_dirac(delta)
    D_clifford = build_clifford_dirac(graph, rho_maps, d)
    
    # Eigenvalues
    eigs_L = np.sort(np.linalg.eigvalsh(L_sheaf))
    eigs_D = np.sort(np.linalg.eigvalsh(D_graph.real))
    eigs_Cliff = np.sort(np.linalg.eigvalsh(D_clifford))
    
    # Spectral gap
    lambda1_L = eigs_L[eigs_L > 1e-10][0] if any(eigs_L > 1e-10) else 0
    lambda1_D = eigs_D[np.abs(eigs_D) > 1e-10]
    lambda1_D = np.min(np.abs(lambda1_D)) if len(lambda1_D) > 0 else 0
    lambda1_Cliff = eigs_Cliff[np.abs(eigs_Cliff) > 1e-10]
    lambda1_Cliff = np.min(np.abs(lambda1_Cliff.real)) if len(lambda1_Cliff) > 0 else 0
    
    print(f"\nSheaf Laplacian L_F:")
    print(f"  First 5 eigenvalues: {eigs_L[:5]}")
    print(f"  Spectral gap λ₁(L): {lambda1_L:.6f}")
    print(f"  √λ₁(L): {np.sqrt(lambda1_L):.6f}")
    
    print(f"\nGraph Dirac D = δ + δ*:")
    print(f"  First 5 eigenvalues: {eigs_D[:5]}")
    print(f"  Spectral gap |λ₁(D)|: {lambda1_D:.6f}")
    
    print(f"\nClifford-Dirac 𝒟:")
    print(f"  Spectral gap |λ₁(𝒟)|: {lambda1_Cliff:.6f}")
    
    print(f"\nSELF-ENCODING CHECK:")
    print(f"  Target W(1) = {W1:.6f}")
    print(f"  |λ₁ - W(1)| = {abs(lambda1_Cliff - W1):.6f}")
    print(f"  e^(-λ₁) = {np.exp(-lambda1_Cliff):.6f}")
    print(f"  |λ₁ - e^(-λ₁)| = {abs(lambda1_Cliff - np.exp(-lambda1_Cliff)):.6f}")
    
    # Index (for Clifford-Dirac)
    kernel_dim = np.sum(np.abs(eigs_Cliff) < 1e-10)
    print(f"\nINDEX THEORY:")
    print(f"  dim ker(𝒟) = {kernel_dim}")
    
    return {
        'lambda1_L': lambda1_L,
        'lambda1_D': lambda1_D, 
        'lambda1_Cliff': lambda1_Cliff,
        'kernel_dim': kernel_dim
    }

# ============================================================
# RUN ALL THREE CONSTRUCTIONS
# ============================================================

print("="*60)
print("PARALLEL CLIFFORD-DIRAC CONSTRUCTIONS")
print(f"Target: λ₁ = W(1) = {W1:.6f}")
print("="*60)

d = 2  # state dimension

# Path P₃: v₀ — v₁ — v₂
path_graph = [(0, 1), (1, 2)]
path_rho = {
    (0, 1): rotation_matrix(0.3),
    (1, 2): rotation_matrix(0.5)
}

# Triangle K₃
triangle_graph = [(0, 1), (1, 2), (2, 0)]
triangle_rho = {
    (0, 1): rotation_matrix(0.4),
    (1, 2): rotation_matrix(0.3),
    (2, 0): rotation_matrix(0.5)
}

# Complete K₄
k4_graph = [(0,1), (0,2), (0,3), (1,2), (1,3), (2,3)]
k4_rho = {
    (0, 1): rotation_matrix(0.2),
    (0, 2): rotation_matrix(0.4),
    (0, 3): rotation_matrix(0.6),
    (1, 2): rotation_matrix(0.3),
    (1, 3): rotation_matrix(0.5),
    (2, 3): rotation_matrix(0.7)
}

# Analyze all
results_path = analyze_graph("Path P₃ (flat)", path_graph, path_rho, d)
results_triangle = analyze_graph("Triangle K₃ (one cycle)", triangle_graph, triangle_rho, d)
results_k4 = analyze_graph("Complete K₄ (rich curvature)", k4_graph, k4_rho, d)

# Holonomy check for triangle
print("\n" + "="*60)
print("CURVATURE ANALYSIS")
print("="*60)

hol_triangle = compute_holonomy([0, 1, 2], triangle_rho, d)
print(f"\nTriangle holonomy:")
print(f"  Hol(c) = ρ₂₀ ∘ ρ₁₂ ∘ ρ₀₁")
print(f"  {hol_triangle}")
print(f"  |Hol - I| = {np.linalg.norm(hol_triangle - np.eye(d)):.6f}")
curvature = hol_triangle - np.eye(d)
print(f"  Curvature F = Hol - I:")
print(f"  {curvature}")

# Summary
print("\n" + "="*60)
print("SUMMARY: DISTANCE TO SELF-ENCODING")
print("="*60)
print(f"{'Graph':<20} {'λ₁(𝒟)':<12} {'|λ₁ - W(1)|':<15} {'Status'}")
print("-"*60)
for name, res in [("Path P₃", results_path), 
                   ("Triangle K₃", results_triangle),
                   ("Complete K₄", results_k4)]:
    l1 = res['lambda1_Cliff']
    diff = abs(l1 - W1)
    status = "SELF-ENCODING" if diff < 0.1 else "NOT YET"
    print(f"{name:<20} {l1:<12.6f} {diff:<15.6f} {status}")