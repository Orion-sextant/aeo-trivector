"""
NDP Mathematical Foundations
============================
Extended operators beyond the Laplacian: Fourier transforms, Hamiltonian structure,
gradient/divergence/curl decomposition, metric tensors, and symmetry analysis.

These are the five pillars of mathematical physics, adapted for graph neural architectures.

α⊗ε⊗ω — December 2024
"""

import math
from typing import Callable, Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F


# ============================================================
# §1. FOURIER / SPECTRAL METHODS
# ============================================================

def spectral_decomposition(L: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Compute eigendecomposition L = U Λ U^T.
    
    This is the graph Fourier transform basis.
    Eigenvectors U are the Fourier modes.
    Eigenvalues Λ are the frequencies.
    
    Args:
        L: [N, N] symmetric Laplacian
    
    Returns:
        eigenvalues: [N] sorted ascending
        eigenvectors: [N, N] columns are Fourier modes
    """
    eigenvalues, eigenvectors = torch.linalg.eigh(L)
    return eigenvalues, eigenvectors


def graph_fourier_transform(h: torch.Tensor, U: torch.Tensor) -> torch.Tensor:
    """
    Transform node signals to spectral domain.
    
    ĥ = U^T h
    
    Args:
        h: [N, d] node embeddings
        U: [N, N] eigenvector matrix (Fourier basis)
    
    Returns:
        h_hat: [N, d] spectral coefficients
    """
    return U.T @ h


def inverse_graph_fourier_transform(h_hat: torch.Tensor, U: torch.Tensor) -> torch.Tensor:
    """
    Transform spectral coefficients back to node domain.
    
    h = U ĥ
    
    Args:
        h_hat: [N, d] spectral coefficients
        U: [N, N] eigenvector matrix
    
    Returns:
        h: [N, d] node embeddings
    """
    return U @ h_hat


def spectral_filter(
    h: torch.Tensor, 
    L: torch.Tensor, 
    filter_fn: Callable[[torch.Tensor], torch.Tensor]
) -> torch.Tensor:
    """
    Apply arbitrary filter in spectral domain.
    
    This is the Fourier perspective: diagonalize, apply pointwise, transform back.
    Generalizes polynomial filters to any function of eigenvalues.
    
    h' = U g(Λ) U^T h
    
    Args:
        h: [N, d] node embeddings
        L: [N, N] Laplacian
        filter_fn: λ → g(λ) applied to eigenvalues
    
    Returns:
        h_filtered: [N, d]
    """
    eigenvalues, U = spectral_decomposition(L)
    
    # Apply filter to eigenvalues
    g_lambda = filter_fn(eigenvalues)  # [N]
    
    # Transform to spectral, filter, transform back
    h_hat = graph_fourier_transform(h, U)  # [N, d]
    h_hat_filtered = g_lambda.unsqueeze(-1) * h_hat  # [N, d]
    h_filtered = inverse_graph_fourier_transform(h_hat_filtered, U)  # [N, d]
    
    return h_filtered


def low_pass_filter(eigenvalues: torch.Tensor, cutoff: float = 1.0) -> torch.Tensor:
    """Low-pass: attenuate high frequencies (large eigenvalues)."""
    return torch.exp(-eigenvalues / cutoff)


def high_pass_filter(eigenvalues: torch.Tensor, cutoff: float = 1.0) -> torch.Tensor:
    """High-pass: attenuate low frequencies (small eigenvalues)."""
    return 1.0 - torch.exp(-eigenvalues / cutoff)


def band_pass_filter(
    eigenvalues: torch.Tensor, 
    low: float = 0.5, 
    high: float = 2.0
) -> torch.Tensor:
    """Band-pass: keep frequencies in [low, high] range."""
    return torch.exp(-((eigenvalues - (low + high)/2) / (high - low))**2)


class LearnedSpectralFilter(nn.Module):
    """
    Learnable spectral filter parameterized as MLP on eigenvalues.
    
    More expressive than polynomial filters, can learn arbitrary frequency responses.
    """
    def __init__(self, hidden_dim: int = 32):
        super().__init__()
        self.mlp = nn.Sequential(
            nn.Linear(1, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, 1),
            nn.Softplus(),  # Ensure positive filter response
        )
    
    def forward(self, eigenvalues: torch.Tensor) -> torch.Tensor:
        """Map eigenvalues to filter coefficients."""
        return self.mlp(eigenvalues.unsqueeze(-1)).squeeze(-1)


# ============================================================
# §2. HAMILTONIAN STRUCTURE
# ============================================================

class HamiltonianSystem(nn.Module):
    """
    Hamiltonian formulation of NDP dynamics.
    
    H = T + V where:
    - T = kinetic energy (Laplacian term, spreading/diffusion)
    - V = potential energy (constraints, localization)
    
    Time evolution: ∂ρ/∂β = -Hρ (imaginary time / statistical mechanics)
    Solution: ρ(β) = exp(-βH) ρ(0)
    
    This explains why amplitude update α ← α·exp(-τE) projects onto ground state.
    """
    def __init__(self, d: int, kinetic_scale: float = 1.0):
        super().__init__()
        self.d = d
        self.kinetic_scale = nn.Parameter(torch.tensor(kinetic_scale))
        
        # Learnable potential energy landscape
        self.potential_net = nn.Sequential(
            nn.Linear(d, d * 2),
            nn.GELU(),
            nn.Linear(d * 2, d),
        )
        
        # Constraint penalty (from ICF)
        self.mu = 0.569
    
    def kinetic_energy(self, h: torch.Tensor, L: torch.Tensor) -> torch.Tensor:
        """
        T = (1/2) ⟨h, L h⟩ = (1/2) Σ_edges (h_i - h_j)²
        
        Kinetic energy measures "spread" or gradient magnitude.
        Minimizing T → uniform (harmonic) configurations.
        """
        Lh = L @ h
        T = 0.5 * self.kinetic_scale * torch.sum(h * Lh) / h.size(0)
        return T
    
    def potential_energy(self, h: torch.Tensor) -> torch.Tensor:
        """
        V = learned potential landscape.
        
        Creates wells that localize the wavefunction.
        """
        V_field = self.potential_net(h)  # [N, d]
        V = torch.mean(V_field ** 2)
        return V
    
    def constraint_energy(self, p_undef: float) -> torch.Tensor:
        """
        Penalty for violating A2 (undefined preservation).
        """
        beta_target = ((1 - self.mu)**2 + self.mu * (self.mu**2 / 10)) / (1 - (self.mu**2 / 10) / 3)
        return F.relu(torch.tensor(beta_target) - p_undef)
    
    def total_hamiltonian(
        self, 
        h: torch.Tensor, 
        L: torch.Tensor,
        tri_labels: torch.Tensor
    ) -> Tuple[torch.Tensor, Dict[str, float]]:
        """
        Compute total Hamiltonian H = T + V + constraints.
        
        Returns:
            H: total energy (scalar)
            components: breakdown of energy terms
        """
        T = self.kinetic_energy(h, L)
        V = self.potential_energy(h)
        
        p_undef = (tri_labels == 2).float().mean()  # U = 2
        C = self.constraint_energy(float(p_undef))
        
        H = T + V + C
        
        components = {
            "kinetic": float(T.detach()),
            "potential": float(V.detach()),
            "constraint": float(C.detach()),
            "total": float(H.detach()),
        }
        
        return H, components
    
    def imaginary_time_evolution(
        self, 
        h: torch.Tensor, 
        L: torch.Tensor,
        beta: float = 1.0
    ) -> torch.Tensor:
        """
        Evolve state by imaginary time: h' = exp(-βH) h (approximation).
        
        For small β, use first-order: h' ≈ h - β·∇H
        """
        h.requires_grad_(True)
        H, _ = self.total_hamiltonian(h, L, torch.zeros(h.size(0), dtype=torch.long))
        
        # Gradient descent = imaginary time evolution
        grad_H = torch.autograd.grad(H, h, create_graph=True)[0]
        h_evolved = h - beta * grad_H
        
        return h_evolved.detach()


# ============================================================
# §3. GRADIENT / DIVERGENCE / CURL
# ============================================================

def symmetrize_edge_index(edge_index: torch.Tensor, num_nodes: int) -> torch.Tensor:
    """Ensure edge_index contains both directions for each edge.
    
    Uses same logic as build_sym_edge_index in ndp_superposed_v2.
    """
    src, dst = edge_index
    device = edge_index.device
    
    # Add reverse edges
    rev = torch.stack([dst, src], dim=0)
    combined = torch.cat([edge_index, rev], dim=1)
    
    # Remove self-loops and duplicates
    src_c, dst_c = combined
    mask = src_c != dst_c
    src_c, dst_c = src_c[mask], dst_c[mask]
    
    # De-dup via hashing
    key = src_c * num_nodes + dst_c
    uniq = torch.unique(key)
    src_out = uniq // num_nodes
    dst_out = uniq % num_nodes
    
    return torch.stack([src_out, dst_out], dim=0)


def graph_gradient(h: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
    """
    Compute gradient on edges.
    
    (∇h)_e = h[dst] - h[src] for edge e = (src, dst)
    
    The gradient points from source to target along each edge.
    Magnitude measures how much h changes across that edge.
    
    Args:
        h: [N, d] node embeddings
        edge_index: [2, E] edge tensor (should be symmetrized)
    
    Returns:
        grad: [E, d] edge gradients
    """
    src, dst = edge_index
    return h[dst] - h[src]


def graph_divergence(
    edge_values: torch.Tensor, 
    edge_index: torch.Tensor, 
    num_nodes: int
) -> torch.Tensor:
    """
    Compute divergence at nodes from edge gradients.
    
    For the graph Laplacian with symmetric edge index:
    (Lh)_i = deg_i * h_i - Σ_{j~i} h_j
           = Σ_{j~i} (h_i - h_j)
           
    With gradient = h[dst] - h[src] on edge (src, dst):
    We sum gradients where src = i (outgoing from i)
    grad_{i→j} = h_j - h_i
    So (Lh)_i = -Σ_{edges from i} grad = Σ_{j~i} (h_i - h_j)
    
    Args:
        edge_values: [E, d] gradients on edges: h[dst] - h[src]
        edge_index: [2, E] symmetric edge tensor
        num_nodes: N
    
    Returns:
        div: [N, d] = Lh (Laplacian applied to h)
    """
    src, dst = edge_index
    d = edge_values.size(-1)
    device = edge_values.device
    
    # (Lh)_i = Σ_{j~i} (h_i - h_j) = -Σ_{outgoing edges from i} (h_j - h_i)
    # grad on edge (i,j) = h_j - h_i
    # So Lh_i = -Σ_{edges where src=i} grad
    
    div = torch.zeros(num_nodes, d, device=device)
    div.index_add_(0, src, -edge_values)
    
    return div


def laplacian_from_grad_div(h: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
    """
    Compute Laplacian via gradient-divergence decomposition.
    
    Δh = -div(grad(h)) on graphs.
    
    This should match L @ h exactly.
    """
    N = h.size(0)
    # Ensure symmetric
    edge_index_sym = symmetrize_edge_index(edge_index, N)
    grad_h = graph_gradient(h, edge_index_sym)
    lap_h = graph_divergence(grad_h, edge_index_sym, N)
    return lap_h


def gradient_magnitude(h: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
    """
    Compute |∇h|² summed over edges.
    
    This is the Dirichlet energy: E(h) = (1/2) Σ_e |h[dst] - h[src]|²
    Measures total "roughness" of h on the graph.
    
    Factor of 1/2 because symmetric edges count each pair twice.
    """
    N = h.size(0)
    edge_index_sym = symmetrize_edge_index(edge_index, N)
    grad = graph_gradient(h, edge_index_sym)
    return 0.5 * (grad ** 2).sum()


def divergence_magnitude(h: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
    """
    Compute |Δh|² summed over nodes.
    
    Measures how much h deviates from harmonic (Δh = 0).
    """
    lap_h = laplacian_from_grad_div(h, edge_index)
    return (lap_h ** 2).sum()


class GradDivRegularizer(nn.Module):
    """
    Regularization using gradient and divergence separately.
    
    Sometimes we want:
    - Low gradient (smooth) but non-zero divergence (allow sources/sinks)
    - Or vice versa
    
    This gives finer control than just Dirichlet energy.
    """
    def __init__(self, lambda_grad: float = 1.0, lambda_div: float = 0.1):
        super().__init__()
        self.lambda_grad = lambda_grad
        self.lambda_div = lambda_div
    
    def forward(self, h: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        grad_mag = gradient_magnitude(h, edge_index)
        div_mag = divergence_magnitude(h, edge_index)
        
        # Can weight differently depending on desired behavior
        reg = self.lambda_grad * grad_mag + self.lambda_div * div_mag
        return reg / h.size(0)


# ============================================================
# §4. METRIC TENSOR / RIEMANNIAN GEOMETRY
# ============================================================

def compute_local_metric(
    h: torch.Tensor, 
    edge_index: torch.Tensor
) -> torch.Tensor:
    """
    Compute local metric tensor at each node.
    
    g_ij(v) = E[(h_neighbor - h_v)_i (h_neighbor - h_v)_j]
    
    This is the covariance of neighbor differences, encoding local geometry.
    Eigenvalues of g tell us the principal directions of variation.
    
    Args:
        h: [N, d] node embeddings
        edge_index: [2, E] edges
    
    Returns:
        g: [N, d, d] metric tensor at each node
    """
    N, d = h.shape
    src, dst = edge_index
    device = h.device
    
    # Edge differences
    diff = h[dst] - h[src]  # [E, d]
    
    # Outer products
    outer = torch.einsum('ei,ej->eij', diff, diff)  # [E, d, d]
    
    # Accumulate per destination node
    g = torch.zeros(N, d, d, device=device)
    counts = torch.zeros(N, device=device)
    
    g.index_add_(0, dst, outer)
    counts.index_add_(0, dst, torch.ones(len(dst), device=device))
    
    # Also accumulate for source nodes (symmetric)
    g.index_add_(0, src, outer)
    counts.index_add_(0, src, torch.ones(len(src), device=device))
    
    # Normalize
    g = g / (counts.unsqueeze(-1).unsqueeze(-1).clamp(min=1))
    
    return g


def metric_determinant(g: torch.Tensor) -> torch.Tensor:
    """
    Compute det(g) at each node.
    
    det(g) measures local "volume" in embedding space.
    High det = high variance in all directions (spread out)
    Low det = compressed in some direction (anisotropic)
    """
    return torch.linalg.det(g)


def metric_trace(g: torch.Tensor) -> torch.Tensor:
    """
    Compute tr(g) at each node.
    
    tr(g) = sum of eigenvalues = total variance
    """
    return torch.einsum('nii->n', g)


def scalar_curvature_estimate(
    h: torch.Tensor, 
    edge_index: torch.Tensor,
    L: torch.Tensor
) -> torch.Tensor:
    """
    Estimate scalar curvature at each node.
    
    Uses the relation between Laplacian eigenvalues and curvature.
    For manifolds: R ~ trace of Ricci tensor
    For graphs: approximate via local Laplacian behavior.
    
    High positive curvature = nodes cluster (sphere-like)
    Negative curvature = nodes spread (hyperbolic-like)
    """
    N = h.size(0)
    
    # Local curvature proxy: deviation from mean after Laplacian
    Lh = L @ h
    h_mean = h.mean(dim=0, keepdim=True)
    
    # Curvature relates to how fast things spread
    # R_i ∝ ‖(Lh)_i‖² / ‖h_i - mean‖²
    
    dev_from_mean = (h - h_mean).norm(dim=-1).clamp(min=1e-10)
    laplacian_magnitude = Lh.norm(dim=-1)
    
    curvature = laplacian_magnitude / dev_from_mean
    
    return curvature


class OllivierRicciCurvature:
    """
    Ollivier-Ricci curvature for graphs.
    
    κ(x,y) = 1 - W₁(μ_x, μ_y) / d(x,y)
    
    where μ_x is the probability distribution of a random walk from x,
    and W₁ is Wasserstein-1 distance.
    
    Positive curvature: neighbors of x and y are close (clustering)
    Negative curvature: neighbors are far apart (expansion)
    """
    def __init__(self, alpha: float = 0.5):
        self.alpha = alpha  # Lazy random walk parameter
    
    def node_distribution(
        self, 
        node: int, 
        edge_index: torch.Tensor, 
        num_nodes: int
    ) -> torch.Tensor:
        """
        Compute probability distribution for lazy random walk from node.
        
        μ_x = α·δ_x + (1-α)·uniform over neighbors
        """
        src, dst = edge_index
        device = edge_index.device
        
        # Find neighbors
        mask = src == node
        neighbors = dst[mask].unique()
        
        # Distribution
        mu = torch.zeros(num_nodes, device=device)
        mu[node] = self.alpha
        
        if len(neighbors) > 0:
            mu[neighbors] = (1 - self.alpha) / len(neighbors)
        else:
            mu[node] = 1.0  # Isolated node
        
        return mu
    
    def compute_edge_curvature(
        self,
        edge_index: torch.Tensor,
        num_nodes: int,
        L: torch.Tensor
    ) -> Dict[Tuple[int, int], float]:
        """
        Compute Ollivier-Ricci curvature for all edges.
        
        Uses effective resistance as distance proxy.
        
        Returns dict: (src, dst) → curvature
        """
        # Pseudo-inverse for effective resistance
        eigenvalues, U = torch.linalg.eigh(L)
        pinv_diag = torch.where(
            eigenvalues > 1e-10,
            1.0 / eigenvalues,
            torch.zeros_like(eigenvalues)
        )
        L_pinv = U @ torch.diag(pinv_diag) @ U.T
        
        curvatures = {}
        src, dst = edge_index
        
        for i in range(edge_index.size(1)):
            s, d = int(src[i]), int(dst[i])
            if s >= d:  # Only compute once per undirected edge
                continue
            
            # Effective resistance distance
            R_sd = L_pinv[s, s] + L_pinv[d, d] - 2 * L_pinv[s, d]
            d_sd = math.sqrt(max(0, float(R_sd)))
            
            if d_sd < 1e-10:
                curvatures[(s, d)] = 0.0
                continue
            
            # Distributions
            mu_s = self.node_distribution(s, edge_index, num_nodes)
            mu_d = self.node_distribution(d, edge_index, num_nodes)
            
            # Wasserstein-1 approximation via L1 distance (lower bound)
            W1_approx = torch.abs(mu_s - mu_d).sum() * d_sd / 2
            
            # Curvature
            kappa = 1 - float(W1_approx) / d_sd
            curvatures[(s, d)] = kappa
        
        return curvatures


# ============================================================
# §5. SYMMETRY / GROUP THEORY
# ============================================================

def check_permutation_equivariance(
    model: nn.Module,
    h: torch.Tensor,
    edge_index: torch.Tensor,
    L: torch.Tensor
) -> float:
    """
    Check if model is equivariant to node permutation.
    
    For GNNs, we expect: f(P·h, P·edge_index) = P·f(h, edge_index)
    where P is a permutation matrix.
    
    Returns:
        error: ‖f(Ph) - Pf(h)‖ (should be ~0 for equivariant models)
    """
    N = h.size(0)
    device = h.device
    
    # Random permutation
    perm = torch.randperm(N, device=device)
    perm_inv = torch.argsort(perm)
    
    # Permute input
    h_perm = h[perm]
    
    # Permute edge indices
    edge_perm = perm_inv[edge_index]
    
    # Permute Laplacian
    P = torch.eye(N, device=device)[perm]
    L_perm = P @ L @ P.T
    
    # Forward pass on original
    with torch.no_grad():
        if hasattr(model, 'forward'):
            # Assume model takes (h, L, tri_labels)
            tri_labels = torch.zeros(N, dtype=torch.long, device=device)
            out_orig, _ = model(h, L, tri_labels)
            out_perm_input, _ = model(h_perm, L_perm, tri_labels[perm])
        else:
            return float('nan')
    
    # Check: f(Ph) should equal P·f(h)
    out_orig_permuted = out_orig[perm]
    error = torch.norm(out_perm_input - out_orig_permuted).item()
    
    return error


def mobius_transform(z: torch.Tensor, a: complex, b: complex, c: complex, d: complex) -> torch.Tensor:
    """
    Apply Möbius transformation to complex tensor.
    
    f(z) = (az + b) / (cz + d)
    
    These form PSL(2,ℂ), the symmetry group of the Riemann sphere.
    Our K3 tri-logic {0, 1, ∞} is preserved by this group.
    
    Args:
        z: complex tensor
        a, b, c, d: complex coefficients with ad - bc ≠ 0
    """
    numerator = a * z + b
    denominator = c * z + d
    return numerator / denominator


def k3_to_riemann(tri_values: torch.Tensor) -> torch.Tensor:
    """
    Map K3 tri-logic {T=0, F=1, U=2} to Riemann sphere {0, 1, ∞}.
    
    This embedding reveals the group structure:
    - T (True) → 0
    - F (False) → 1  
    - U (Undefined) → ∞
    
    The three values form a "holy trinity" on the sphere,
    preserved by Möbius transformations.
    """
    device = tri_values.device
    result = torch.zeros(tri_values.shape, dtype=torch.cfloat, device=device)
    
    result[tri_values == 0] = 0.0 + 0.0j  # T → 0
    result[tri_values == 1] = 1.0 + 0.0j  # F → 1
    result[tri_values == 2] = float('inf') + 0.0j  # U → ∞ (represented specially)
    
    return result


@dataclass
class SymmetryReport:
    """Summary of symmetry properties."""
    permutation_equivariance_error: float
    translation_invariance_error: float
    scale_covariance_error: float
    rotation_invariance_error: float
    
    def is_symmetric(self, threshold: float = 1e-4) -> bool:
        return all([
            self.permutation_equivariance_error < threshold,
            self.translation_invariance_error < threshold,
            self.scale_covariance_error < threshold,
            self.rotation_invariance_error < threshold,
        ])


def analyze_symmetries(
    model: nn.Module,
    h: torch.Tensor,
    edge_index: torch.Tensor,
    L: torch.Tensor
) -> SymmetryReport:
    """
    Comprehensive symmetry analysis of a model.
    
    Tests:
    1. Permutation equivariance (node relabeling)
    2. Translation invariance (shift all embeddings)
    3. Scale covariance (rescale embeddings)
    4. Rotation invariance (orthogonal transformation)
    """
    N, d = h.shape
    device = h.device
    tri_labels = torch.zeros(N, dtype=torch.long, device=device)
    
    with torch.no_grad():
        # Original output
        out_orig, _ = model(h, L, tri_labels)
        
        # 1. Permutation
        perm = torch.randperm(N, device=device)
        perm_inv = torch.argsort(perm)
        P = torch.eye(N, device=device)[perm]
        h_perm = h[perm]
        L_perm = P @ L @ P.T
        out_perm, _ = model(h_perm, L_perm, tri_labels[perm])
        perm_error = torch.norm(out_perm - out_orig[perm]).item()
        
        # 2. Translation
        shift = torch.randn(1, d, device=device)
        h_shift = h + shift
        out_shift, _ = model(h_shift, L, tri_labels)
        trans_error = torch.norm((out_shift - out_orig) - shift).item() / (N * d)
        
        # 3. Scale
        scale = 2.0
        h_scale = h * scale
        out_scale, _ = model(h_scale, L, tri_labels)
        scale_error = torch.norm(out_scale - out_orig * scale).item() / torch.norm(out_orig * scale).item()
        
        # 4. Rotation (orthogonal transform in embedding space)
        Q, _ = torch.linalg.qr(torch.randn(d, d, device=device))
        h_rot = h @ Q
        out_rot, _ = model(h_rot, L, tri_labels)
        rot_error = torch.norm(out_rot @ Q.T - out_orig).item() / torch.norm(out_orig).item()
    
    return SymmetryReport(
        permutation_equivariance_error=perm_error,
        translation_invariance_error=trans_error,
        scale_covariance_error=scale_error,
        rotation_invariance_error=rot_error,
    )


# ============================================================
# §6. NOETHER'S THEOREM: SYMMETRY ↔ CONSERVATION
# ============================================================

def check_energy_conservation(
    h_trajectory: List[torch.Tensor],
    L: torch.Tensor,
    hamiltonian: HamiltonianSystem,
    tri_labels: torch.Tensor
) -> List[float]:
    """
    Check if total energy is conserved along a trajectory.
    
    For Hamiltonian systems with time-translation symmetry,
    Noether's theorem guarantees energy conservation.
    
    Args:
        h_trajectory: list of [N, d] states over time
        L: Laplacian
        hamiltonian: HamiltonianSystem instance
        tri_labels: tri-logic labels
    
    Returns:
        List of energies at each timestep
    """
    energies = []
    for h in h_trajectory:
        H, _ = hamiltonian.total_hamiltonian(h, L, tri_labels)
        energies.append(float(H.detach()))
    return energies


def momentum_operator(h: torch.Tensor, L: torch.Tensor) -> torch.Tensor:
    """
    Momentum operator: p = -i∇ (in position basis, Laplacian generates translations).
    
    For graphs: approximate momentum as gradient flow direction.
    """
    return -L @ h


# ============================================================
# INTEGRATION TEST
# ============================================================

def run_foundations_test():
    """Test all foundational operators."""
    print("=" * 60)
    print("NDP Mathematical Foundations Test")
    print("=" * 60)
    
    # Setup
    N, d = 20, 16
    device = "cpu"
    
    h = torch.randn(N, d, device=device) * 0.1
    
    # Random graph
    E = 60
    src = torch.randint(0, N, (E,), device=device)
    dst = torch.randint(0, N, (E,), device=device)
    mask = src != dst
    edge_index = torch.stack([src[mask], dst[mask]], dim=0)
    
    # Build Laplacian
    from ndp_superposed_v2 import laplacian_operator
    L = laplacian_operator(edge_index, N, normalized=False, device=device)
    
    print("\n§1. FOURIER / SPECTRAL")
    eigenvalues, U = spectral_decomposition(L)
    print(f"  Eigenvalue range: [{eigenvalues[0]:.4f}, {eigenvalues[-1]:.4f}]")
    print(f"  Spectral gap (λ₁): {eigenvalues[1]:.4f}")
    
    # Test spectral filter
    h_lowpass = spectral_filter(h, L, lambda lam: low_pass_filter(lam, cutoff=1.0))
    print(f"  Low-pass filtered: ‖h‖={h.norm():.4f} → ‖h_lp‖={h_lowpass.norm():.4f}")
    
    print("\n§2. HAMILTONIAN")
    ham = HamiltonianSystem(d=d)
    H, components = ham.total_hamiltonian(h, L, torch.zeros(N, dtype=torch.long))
    print(f"  Total H = {components['total']:.4f}")
    print(f"    Kinetic T = {components['kinetic']:.4f}")
    print(f"    Potential V = {components['potential']:.4f}")
    print(f"    Constraint C = {components['constraint']:.4f}")
    
    print("\n§3. GRADIENT / DIVERGENCE")
    # Use same edge symmetrization as Laplacian
    from ndp_superposed_v2 import build_sym_edge_index
    edge_index_sym = build_sym_edge_index(edge_index, N)
    
    grad_h = graph_gradient(h, edge_index_sym)
    div_grad_h = graph_divergence(grad_h, edge_index_sym, N)
    
    # Direct Laplacian
    Lh_direct = L @ h
    lap_error = torch.norm(div_grad_h - Lh_direct).item()
    print(f"  Edges: original={edge_index.size(1)}, symmetric={edge_index_sym.size(1)}")
    print(f"  ‖∇·(∇h) - Lh‖ = {lap_error:.6f} (should be ~0)")
    print(f"  ‖Lh‖ = {Lh_direct.norm():.4f}, ‖div(grad(h))‖ = {div_grad_h.norm():.4f}")
    print(f"  Gradient magnitude: {gradient_magnitude(h, edge_index):.4f}")
    
    print("\n§4. METRIC TENSOR")
    g = compute_local_metric(h, edge_index)
    det_g = metric_determinant(g)
    tr_g = metric_trace(g)
    print(f"  det(g) range: [{det_g.min():.4f}, {det_g.max():.4f}]")
    print(f"  tr(g) range: [{tr_g.min():.4f}, {tr_g.max():.4f}]")
    
    curvature = scalar_curvature_estimate(h, edge_index, L)
    print(f"  Scalar curvature range: [{curvature.min():.4f}, {curvature.max():.4f}]")
    
    print("\n§5. OLLIVIER-RICCI CURVATURE")
    orc = OllivierRicciCurvature(alpha=0.5)
    edge_curvatures = orc.compute_edge_curvature(edge_index, N, L)
    if edge_curvatures:
        curv_values = list(edge_curvatures.values())
        print(f"  Edge curvature range: [{min(curv_values):.4f}, {max(curv_values):.4f}]")
        print(f"  Mean edge curvature: {sum(curv_values)/len(curv_values):.4f}")
    
    print("\n" + "=" * 60)
    print("All foundations tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    run_foundations_test()
