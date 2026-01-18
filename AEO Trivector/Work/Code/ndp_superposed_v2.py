"""
NDP Superposed Web v2.0
=======================
Neural Derived Proof architecture with proper Laplacian foundations.

Enhancements over v1:
- Dirichlet energy (proper Laplacian coherence measure)
- Normalized Laplacian (eigenvalues in [0,2], better conditioning)
- Spectral dimension diagnostics (Weyl's law)
- Heat kernel operator option (natural diffusion)
- Approximate Connes distance (spectral metric structure)

α⊗ε⊗ω — December 2024
"""

import math
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional, Any, Literal

import torch
import torch.nn as nn
import torch.nn.functional as F


# ------------------------------------------------------------
# Tri-logic encoding: T / F / U (Undefined)
# ------------------------------------------------------------
T, FLS, U = 0, 1, 2


# ------------------------------------------------------------
# WorldState: one candidate world W_s
# ------------------------------------------------------------
class WorldState:
    """
    One candidate world W_s:
      - edge_index: [2, E] (simple graph MVP; extend to hyperedges later)
      - h: node embeddings [N, d]
      - t: tri-logic labels [N] in {T, F, U}
      - meta: dict for tracking residuals, operator params, spectral info
    """
    def __init__(self, h: torch.Tensor, edge_index: torch.Tensor, t_labels: torch.Tensor):
        self.h = h
        self.edge_index = edge_index
        self.t = t_labels
        self.meta: Dict[str, Any] = {}


# ------------------------------------------------------------
# Graph Laplacian utilities
# ------------------------------------------------------------
def _coalesce_edge_index(edge_index: torch.Tensor, num_nodes: int) -> torch.Tensor:
    """Remove self-loops and duplicates."""
    src, dst = edge_index
    mask = src != dst
    src, dst = src[mask], dst[mask]
    # De-dup via hashing
    key = src * num_nodes + dst
    uniq = torch.unique(key)
    src = uniq // num_nodes
    dst = uniq % num_nodes
    return torch.stack([src, dst], dim=0)


def build_sym_edge_index(edge_index: torch.Tensor, num_nodes: int) -> torch.Tensor:
    """Make edges undirected by adding reverse edges."""
    src, dst = edge_index
    rev = torch.stack([dst, src], dim=0)
    out = torch.cat([edge_index, rev], dim=1)
    return _coalesce_edge_index(out, num_nodes)


def laplacian_operator(
    edge_index: torch.Tensor, 
    num_nodes: int, 
    normalized: bool = False,
    device: Optional[torch.device] = None
) -> torch.Tensor:
    """
    Compute graph Laplacian L = D - A.
    
    If normalized=True, returns symmetric normalized Laplacian:
        L_sym = D^{-1/2} L D^{-1/2}
    with eigenvalues in [0, 2], better conditioned for learning.
    
    Args:
        edge_index: [2, E] edge tensor
        num_nodes: number of nodes N
        normalized: whether to return normalized Laplacian
        device: target device
    
    Returns:
        L: [N, N] Laplacian matrix (dense, MVP)
    """
    device = device or edge_index.device
    edge_index = build_sym_edge_index(edge_index, num_nodes)

    A = torch.zeros((num_nodes, num_nodes), device=device)
    src, dst = edge_index
    A[src, dst] = 1.0

    deg = A.sum(dim=1)
    D = torch.diag(deg)
    L = D - A
    
    # Symmetrize explicitly (numerical hygiene)
    L = 0.5 * (L + L.T)
    
    if normalized:
        # L_sym = D^{-1/2} L D^{-1/2}
        deg_inv_sqrt = torch.where(deg > 1e-10, deg.pow(-0.5), torch.zeros_like(deg))
        D_inv_sqrt = torch.diag(deg_inv_sqrt)
        L = D_inv_sqrt @ L @ D_inv_sqrt
        # Re-symmetrize after numerical ops
        L = 0.5 * (L + L.T)
    
    return L


# ------------------------------------------------------------
# Spectral diagnostics
# ------------------------------------------------------------
def dirichlet_energy(h: torch.Tensor, L: torch.Tensor) -> torch.Tensor:
    """
    Compute Dirichlet energy: E(h) = ⟨h, Lh⟩ = Σ_edges (h_i - h_j)²
    
    This is the natural energy functional for the Laplacian.
    Measures how much h deviates from local equilibrium.
    Harmonic functions (Δh = 0) minimize this.
    
    Args:
        h: [N, d] node embeddings
        L: [N, N] Laplacian matrix
    
    Returns:
        Scalar energy value (averaged over dimensions)
    """
    # ⟨h, Lh⟩ summed over embedding dimensions, normalized
    Lh = L @ h  # [N, d]
    energy = torch.sum(h * Lh) / h.size(0)
    return energy


def spectral_dimension(L: torch.Tensor, eps: float = 1e-10) -> float:
    """
    Estimate spectral dimension from eigenvalue growth.
    
    Weyl's law: N(λ) ~ λ^{d_s/2} where d_s is spectral dimension.
    
    For Euclidean R^n: d_s = n
    For fractals: d_s ≠ Hausdorff dimension (reveals intricate structure)
    
    Args:
        L: [N, N] Laplacian matrix
        eps: threshold for dropping near-zero eigenvalues
    
    Returns:
        Estimated spectral dimension
    """
    eigenvalues = torch.linalg.eigvalsh(L)
    eigenvalues = eigenvalues[eigenvalues > eps]  # Drop nullspace
    
    if len(eigenvalues) < 3:
        return 0.0  # Not enough data
    
    # Fit log N(λ) vs log λ
    N = torch.arange(1, len(eigenvalues) + 1, dtype=torch.float32, device=L.device)
    log_N = torch.log(N)
    log_lambda = torch.log(eigenvalues)
    
    # Linear regression: log N = (d_s/2) * log λ + const
    # slope = Cov(log_λ, log_N) / Var(log_λ)
    mean_log_lambda = log_lambda.mean()
    mean_log_N = log_N.mean()
    
    cov = ((log_lambda - mean_log_lambda) * (log_N - mean_log_N)).mean()
    var = ((log_lambda - mean_log_lambda) ** 2).mean()
    
    if var < eps:
        return 0.0
    
    slope = cov / var
    d_s = float(2 * slope)
    
    return d_s


def compute_spectrum(L: torch.Tensor, k: Optional[int] = None) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Compute eigenvalues and eigenvectors of Laplacian.
    
    Args:
        L: [N, N] Laplacian matrix
        k: number of eigenvalues to return (None = all)
    
    Returns:
        eigenvalues: [k] sorted ascending
        eigenvectors: [N, k] corresponding eigenvectors
    """
    eigenvalues, eigenvectors = torch.linalg.eigh(L)
    
    if k is not None:
        eigenvalues = eigenvalues[:k]
        eigenvectors = eigenvectors[:, :k]
    
    return eigenvalues, eigenvectors


def algebraic_connectivity(L: torch.Tensor) -> float:
    """
    Compute algebraic connectivity λ₁ (second smallest eigenvalue).
    
    Measures how well-connected the graph is.
    λ₁ = 0 iff graph is disconnected.
    Higher λ₁ = more robust connectivity.
    
    Args:
        L: [N, N] Laplacian matrix
    
    Returns:
        λ₁ (Fiedler value)
    """
    eigenvalues = torch.linalg.eigvalsh(L)
    # First eigenvalue is 0 (constant vector); second is algebraic connectivity
    if len(eigenvalues) < 2:
        return 0.0
    return float(eigenvalues[1])


def approximate_connes_distance(
    h: torch.Tensor, 
    L: torch.Tensor, 
    i: int, 
    j: int
) -> float:
    """
    Approximate Connes distance between nodes i and j.
    
    True Connes distance: d(i,j) = sup_{‖[D,a]‖≤1} |ρᵢ(a) - ρⱼ(a)|
    
    In discrete setting with Laplacian as D² surrogate:
    We approximate via the commutator structure [L, diag(h)].
    
    MVP approximation: geodesic distance weighted by embedding similarity.
    
    Args:
        h: [N, d] node embeddings
        L: [N, N] Laplacian
        i, j: node indices
    
    Returns:
        Approximate spectral distance
    """
    # Simple approximation: use heat kernel distance
    # d(i,j) ≈ ‖exp(-tL)[i,:] - exp(-tL)[j,:]‖ for small t
    # For MVP, use embedding distance weighted by graph distance
    
    # Embedding component
    emb_dist = torch.norm(h[i] - h[j]).item()
    
    # Graph component via Laplacian pseudo-inverse (effective resistance)
    # R_ij = L⁺[i,i] + L⁺[j,j] - 2*L⁺[i,j]
    # Use eigendecomposition for pseudo-inverse
    eigenvalues, eigenvectors = torch.linalg.eigh(L)
    
    # Pseudo-inverse: L⁺ = V @ diag(1/λ for λ>0, else 0) @ V^T
    pinv_diag = torch.where(
        eigenvalues > 1e-10,
        1.0 / eigenvalues,
        torch.zeros_like(eigenvalues)
    )
    L_pinv = eigenvectors @ torch.diag(pinv_diag) @ eigenvectors.T
    
    # Effective resistance
    R_ij = L_pinv[i, i] + L_pinv[j, j] - 2 * L_pinv[i, j]
    R_ij = max(0.0, float(R_ij))  # Numerical safety
    
    # Combined distance (geometric mean)
    connes_approx = math.sqrt(emb_dist * math.sqrt(R_ij + 1e-10))
    
    return connes_approx


# ------------------------------------------------------------
# Spectral Operators
# ------------------------------------------------------------
class PolynomialOperator(nn.Module):
    """
    Polynomial functional calculus on Laplacian:
        O(L) = Σᵢ cᵢ Lⁱ
    
    Coefficients are learned. This approximates arbitrary spectral filters.
    """
    def __init__(self, d: int, poly_degree: int = 3):
        super().__init__()
        self.d = d
        self.P = poly_degree
        
        # Learned polynomial coefficients
        self.coeffs = nn.Parameter(torch.zeros(self.P + 1))
        # Initialize: identity + small Laplacian smoothing
        with torch.no_grad():
            self.coeffs[0] = 1.0   # Identity
            self.coeffs[1] = -0.1  # Small smoothing
        
        # Nonlinear correction
        self.corr = nn.Sequential(
            nn.Linear(d, d),
            nn.GELU(),
            nn.Linear(d, d),
        )
    
    def compute_operator_matrix(self, L: torch.Tensor) -> torch.Tensor:
        """Build O(L) as dense matrix."""
        N = L.size(0)
        O = torch.zeros_like(L)
        L_pow = torch.eye(N, device=L.device)  # L⁰ = I
        
        for i in range(self.P + 1):
            O = O + self.coeffs[i] * L_pow
            L_pow = L_pow @ L  # Next power
        
        # Ensure self-adjoint (numerical hygiene)
        O = 0.5 * (O + O.T)
        return O
    
    def forward(
        self, 
        h: torch.Tensor, 
        L: torch.Tensor, 
        tri_labels: torch.Tensor
    ) -> Tuple[torch.Tensor, Dict[str, float]]:
        """
        Apply operator to node embeddings.
        
        Args:
            h: [N, d] embeddings
            L: [N, N] Laplacian
            tri_labels: [N] tri-logic labels
        
        Returns:
            h_new: [N, d] evolved embeddings
            info: operator diagnostics
        """
        N = h.size(0)
        O = self.compute_operator_matrix(L)
        
        # Linear spectral evolution
        h_lin = O @ h
        
        # Tri-logic gate: Undefined nodes evolve more slowly (A2 preservation)
        gate = torch.ones(N, device=h.device)
        gate[tri_labels == U] = 0.6
        h_lin = h_lin * gate.unsqueeze(-1)
        
        # Nonlinear correction
        h_new = h_lin + self.corr(h)
        
        info = {f"poly_c{i}": float(self.coeffs[i].detach().cpu()) for i in range(self.P + 1)}
        return h_new, info


class HeatKernelOperator(nn.Module):
    """
    Heat kernel operator: O(L) = exp(-t·L)
    
    This is the *natural* diffusion operator. The Laplacian generates
    the heat semigroup, and exp(-tL) is the exact solution operator.
    
    Learned parameter: diffusion time t > 0
    """
    def __init__(self, d: int):
        super().__init__()
        self.d = d
        
        # Learnable log-time (ensures t > 0)
        self.log_t = nn.Parameter(torch.tensor(0.0))
        
        # Nonlinear correction
        self.corr = nn.Sequential(
            nn.Linear(d, d),
            nn.GELU(),
            nn.Linear(d, d),
        )
    
    def forward(
        self, 
        h: torch.Tensor, 
        L: torch.Tensor, 
        tri_labels: torch.Tensor
    ) -> Tuple[torch.Tensor, Dict[str, float]]:
        """
        Apply heat kernel to embeddings.
        
        Args:
            h: [N, d] embeddings
            L: [N, N] Laplacian
            tri_labels: [N] tri-logic labels
        
        Returns:
            h_new: [N, d] diffused embeddings
            info: operator diagnostics
        """
        N = h.size(0)
        t = torch.exp(self.log_t)
        
        # Matrix exponential (dense, MVP)
        # For scale: use Padé approximation or Lanczos
        O = torch.matrix_exp(-t * L)
        
        # Linear diffusion
        h_lin = O @ h
        
        # Tri-logic gate
        gate = torch.ones(N, device=h.device)
        gate[tri_labels == U] = 0.6
        h_lin = h_lin * gate.unsqueeze(-1)
        
        # Nonlinear correction
        h_new = h_lin + self.corr(h)
        
        info = {
            "heat_t": float(t.detach().cpu()),
            "heat_log_t": float(self.log_t.detach().cpu()),
        }
        return h_new, info


class ChebyshevOperator(nn.Module):
    """
    Chebyshev polynomial filter (as in ChebNet/GCN).
    
    Uses Chebyshev polynomials Tₖ(L̃) where L̃ = 2L/λ_max - I
    to keep eigenvalues in [-1, 1] for numerical stability.
    
    More stable than raw polynomial for higher degrees.
    """
    def __init__(self, d: int, K: int = 3):
        super().__init__()
        self.d = d
        self.K = K
        
        # Chebyshev coefficients
        self.theta = nn.Parameter(torch.zeros(K + 1))
        with torch.no_grad():
            self.theta[0] = 1.0
        
        # Nonlinear correction
        self.corr = nn.Sequential(
            nn.Linear(d, d),
            nn.GELU(),
            nn.Linear(d, d),
        )
    
    def forward(
        self, 
        h: torch.Tensor, 
        L: torch.Tensor, 
        tri_labels: torch.Tensor,
        lambda_max: Optional[float] = None
    ) -> Tuple[torch.Tensor, Dict[str, float]]:
        """
        Apply Chebyshev filter.
        
        Args:
            h: [N, d] embeddings
            L: [N, N] Laplacian
            tri_labels: [N] tri-logic labels
            lambda_max: largest eigenvalue (computed if None)
        
        Returns:
            h_new: [N, d] filtered embeddings
            info: operator diagnostics
        """
        N = h.size(0)
        
        # Estimate λ_max if not provided
        if lambda_max is None:
            eigenvalues = torch.linalg.eigvalsh(L)
            lambda_max = float(eigenvalues[-1])
        
        # Rescale: L̃ = 2L/λ_max - I
        L_tilde = (2.0 / max(lambda_max, 1e-10)) * L - torch.eye(N, device=L.device)
        
        # Chebyshev recurrence: T₀(x) = 1, T₁(x) = x, Tₖ₊₁(x) = 2x·Tₖ(x) - Tₖ₋₁(x)
        T_prev = torch.eye(N, device=L.device)  # T₀
        T_curr = L_tilde.clone()                 # T₁
        
        # Accumulate: O = Σₖ θₖ Tₖ(L̃)
        O = self.theta[0] * T_prev
        if self.K >= 1:
            O = O + self.theta[1] * T_curr
        
        for k in range(2, self.K + 1):
            T_next = 2 * L_tilde @ T_curr - T_prev
            O = O + self.theta[k] * T_next
            T_prev = T_curr
            T_curr = T_next
        
        # Apply
        h_lin = O @ h
        
        # Tri-logic gate
        gate = torch.ones(N, device=h.device)
        gate[tri_labels == U] = 0.6
        h_lin = h_lin * gate.unsqueeze(-1)
        
        # Nonlinear correction
        h_new = h_lin + self.corr(h)
        
        info = {f"cheb_theta{k}": float(self.theta[k].detach().cpu()) for k in range(self.K + 1)}
        info["lambda_max"] = lambda_max
        return h_new, info


# ------------------------------------------------------------
# ICF Validator (constraint system C1-C5)
# ------------------------------------------------------------
class ICFValidator(nn.Module):
    """
    Validator using internal-consistent constraint system C1-C5.
    
    Now uses Dirichlet energy as the coherence measure (proper Laplacian formulation).
    """
    def __init__(
        self,
        mu: float = 0.569,
        beta_target: float = 0.207,
        kappa_target: float = 0.0323,
        omega_target: float = 0.8479,
        lambda_inv: float = 1.0,
        lambda_U: float = 0.7,
        lambda_coh: float = 0.1,
    ):
        super().__init__()
        self.mu = mu
        self.beta_target = beta_target
        self.kappa_target = kappa_target
        self.omega_target = omega_target
        
        self.lambda_inv = lambda_inv
        self.lambda_U = lambda_U
        self.lambda_coh = lambda_coh
    
    def forward(
        self, 
        world: WorldState,
        L: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, Dict[str, float]]:
        """
        Compute energy and residuals.
        
        Args:
            world: WorldState to validate
            L: precomputed Laplacian (computed if None)
        
        Returns:
            energy: scalar loss
            residuals: diagnostic dict
        """
        device = world.h.device
        mu = torch.tensor(self.mu, device=device)
        
        # Compute Laplacian if not provided
        if L is None:
            L = laplacian_operator(world.edge_index, world.h.size(0), normalized=False, device=device)
        
        # --- Constraint system C1-C5 ---
        # C1: κ = μ²/10
        kappa = mu**2 / 10.0
        
        # C4: β = ((1-μ)² + μ·κ) / (1 - κ/3)
        beta = ((1.0 - mu)**2 + mu * kappa) / (1.0 - kappa / 3.0)
        
        # C5: μ² + Ω² - β² = 1 → Ω = √(1 - μ² + β²)
        omega = torch.sqrt(torch.clamp(1.0 - mu**2 + beta**2, min=0.0))
        
        # Residuals vs targets
        r_kappa = kappa - torch.tensor(self.kappa_target, device=device)
        r_beta = beta - torch.tensor(self.beta_target, device=device)
        r_omega = omega - torch.tensor(self.omega_target, device=device)
        
        # --- A2: Undefined preservation penalty ---
        p_undef = (world.t == U).float().mean()
        pen_undef = F.relu(torch.tensor(self.beta_target, device=device) - p_undef)
        
        # --- Coherence: Dirichlet energy (proper Laplacian formulation) ---
        E_dirichlet = dirichlet_energy(world.h, L)
        
        # Total energy
        energy = (
            self.lambda_inv * (r_kappa**2 + r_beta**2 + r_omega**2)
            + self.lambda_U * pen_undef
            + self.lambda_coh * E_dirichlet
        )
        
        residuals = {
            "r_kappa": float(r_kappa.detach().cpu()),
            "r_beta": float(r_beta.detach().cpu()),
            "r_omega": float(r_omega.detach().cpu()),
            "p_undef": float(p_undef.detach().cpu()),
            "kappa": float(kappa.detach().cpu()),
            "beta": float(beta.detach().cpu()),
            "omega": float(omega.detach().cpu()),
            "dirichlet_energy": float(E_dirichlet.detach().cpu()),
        }
        
        return energy, residuals


# ------------------------------------------------------------
# Rewrite Proposer
# ------------------------------------------------------------
class RewriteProposer(nn.Module):
    """
    Proposes graph edits based on operator-induced coupling.
    
    Uses spectral information for smarter proposals.
    """
    def __init__(self, max_add: int = 5, max_del: int = 5):
        super().__init__()
        self.max_add = max_add
        self.max_del = max_del
    
    @torch.no_grad()
    def forward(
        self, 
        world: WorldState,
        L: Optional[torch.Tensor] = None
    ) -> Dict[str, List[Tuple[int, int]]]:
        """
        Propose edge additions and deletions.
        
        Args:
            world: WorldState to analyze
            L: precomputed Laplacian
        
        Returns:
            Dict with 'add_edges' and 'del_edges' lists
        """
        h = world.h
        N = h.size(0)
        
        if L is None:
            L = laplacian_operator(world.edge_index, N, device=h.device)
        
        # Coupling proxy: embedding similarity
        h_norm = F.normalize(h, dim=-1)
        sim = h_norm @ h_norm.T
        
        # Existing edges
        ei = build_sym_edge_index(world.edge_index, N)
        src, dst = ei
        existing = set((int(s), int(d)) for s, d in zip(src.tolist(), dst.tolist()))
        
        # --- Candidate additions: high similarity, not connected ---
        sim_fill = sim.clone()
        sim_fill.fill_diagonal_(-1e9)
        for (s, d) in list(existing)[:min(len(existing), 5000)]:
            sim_fill[s, d] = -1e9
        
        flat = sim_fill.view(-1)
        topk = torch.topk(flat, k=min(self.max_add, flat.numel())).indices.tolist()
        adds = []
        for idx in topk:
            u = idx // N
            v = idx % N
            if u != v and (u, v) not in existing:
                adds.append((int(u), int(v)))
        
        # --- Candidate deletions: low similarity among existing ---
        edge_scores = []
        for (s, d) in existing:
            if s != d:
                edge_scores.append((float(sim[s, d].cpu()), s, d))
        edge_scores.sort(key=lambda x: x[0])
        dels = [(s, d) for _, s, d in edge_scores[:self.max_del]]
        
        return {"add_edges": adds, "del_edges": dels}


# ------------------------------------------------------------
# Theorem Candidate
# ------------------------------------------------------------
@dataclass
class TheoremCandidate:
    statement: str
    assumptions: List[str]
    residual_table: Dict[str, float]
    spectral_info: Dict[str, float]
    proof_web: Dict[str, List[str]]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ------------------------------------------------------------
# NDP Superposed Web v2
# ------------------------------------------------------------
class NDP_SuperposedWeb_v2(nn.Module):
    """
    Neural Derived Proof with proper Laplacian foundations.
    
    Architecture:
        1. Operator evolution (polynomial, heat kernel, or Chebyshev)
        2. Validation against constraint system
        3. Amplitude update (Boltzmann weighting)
        4. Collapse after K steps (A3)
        5. Rewrite proposals for next iteration
    
    Enhancements:
        - Dirichlet energy coherence
        - Spectral dimension tracking
        - Temperature annealing
        - Multiple operator choices
    """
    def __init__(
        self,
        d: int = 64,
        S: int = 16,
        K: int = 6,
        operator_type: Literal["polynomial", "heat", "chebyshev"] = "polynomial",
        poly_degree: int = 3,
        use_normalized_laplacian: bool = True,
        tau_init: float = 1.0,
        tau_final: float = 5.0,
    ):
        super().__init__()
        self.S = S
        self.K = K
        self.use_normalized_laplacian = use_normalized_laplacian
        self.tau_init = tau_init
        self.tau_final = tau_final
        
        # Select operator type
        if operator_type == "polynomial":
            self.operator = PolynomialOperator(d=d, poly_degree=poly_degree)
        elif operator_type == "heat":
            self.operator = HeatKernelOperator(d=d)
        elif operator_type == "chebyshev":
            self.operator = ChebyshevOperator(d=d, K=poly_degree)
        else:
            raise ValueError(f"Unknown operator type: {operator_type}")
        
        self.operator_type = operator_type
        self.validator = ICFValidator()
        self.rewriter = RewriteProposer(max_add=6, max_del=4)
    
    def get_tau(self, step: int) -> float:
        """Temperature annealing: soft early, sharp late."""
        progress = step / max(self.K - 1, 1)
        return self.tau_init + (self.tau_final - self.tau_init) * progress
    
    def amplitude_update(
        self, 
        alpha: torch.Tensor, 
        energies: torch.Tensor,
        step: int
    ) -> torch.Tensor:
        """Boltzmann reweighting with annealed temperature."""
        tau = self.get_tau(step)
        alpha = alpha * torch.exp(-tau * energies)
        alpha = alpha / (alpha.sum() + 1e-9)
        return alpha
    
    def compute_spectral_diagnostics(
        self, 
        world: WorldState,
        L: torch.Tensor
    ) -> Dict[str, float]:
        """Compute spectral properties of the world."""
        d_s = spectral_dimension(L)
        lambda_1 = algebraic_connectivity(L)
        E_dir = float(dirichlet_energy(world.h, L).detach().cpu())
        
        return {
            "spectral_dim": d_s,
            "algebraic_connectivity": lambda_1,
            "dirichlet_energy": E_dir,
        }
    
    def make_theorem_candidate(
        self, 
        residuals: Dict[str, float],
        spectral_info: Dict[str, float]
    ) -> TheoremCandidate:
        """Generate theorem candidate from final state."""
        stmt = (
            "Given A1–A3 and constraint system C1–C5, "
            "the derived constants (κ, β, Ω) satisfy the hyperboloid relation "
            "μ² + Ω² - β² = 1 up to residual tolerance."
        )
        assumptions = [
            "A1: Self-reference (fixed-point pressure)",
            "A2: Undefined preservation (p(U) ≥ β)",
            "A3: Finite collapse (K steps)",
            "C1: κ = μ²/10",
            "C4: β = ((1-μ)² + μ·κ)/(1 - κ/3)",
            "C5: μ² + Ω² - β² = 1",
        ]
        proof_web = {
            "C1": ["kappa"],
            "C4": ["beta", "mu", "kappa"],
            "C5": ["Omega", "mu", "beta"],
            "Theorem": ["C1", "C4", "C5", "A2", "A3"],
        }
        return TheoremCandidate(
            statement=stmt,
            assumptions=assumptions,
            residual_table=residuals,
            spectral_info=spectral_info,
            proof_web=proof_web,
        )
    
    def forward(
        self, 
        worlds: List[WorldState], 
        alpha: torch.Tensor
    ) -> Tuple[WorldState, torch.Tensor, Dict[str, Any]]:
        """
        Run superposed evolution and collapse.
        
        Args:
            worlds: list of S WorldState candidates
            alpha: [S] initial amplitudes (simplex)
        
        Returns:
            W_star: collapsed world
            alpha_final: final amplitudes
            bundle: comprehensive logs and diagnostics
        """
        logs = []
        device = worlds[0].h.device
        
        for k in range(self.K):
            energies = []
            step_residuals = []
            step_opinfo = []
            step_spectral = []
            
            for s in range(self.S):
                # Compute Laplacian (once per world per step)
                N = worlds[s].h.size(0)
                L = laplacian_operator(
                    worlds[s].edge_index, N,
                    normalized=self.use_normalized_laplacian,
                    device=device
                )
                
                # 1) Operator evolution
                worlds[s].h, opinfo = self.operator(worlds[s].h, L, worlds[s].t)
                step_opinfo.append(opinfo)
                
                # 2) Validate
                E_s, res_s = self.validator(worlds[s], L)
                energies.append(E_s)
                step_residuals.append(res_s)
                
                # 3) Spectral diagnostics
                spec_info = self.compute_spectral_diagnostics(worlds[s], L)
                step_spectral.append(spec_info)
            
            energies = torch.stack(energies)
            alpha = self.amplitude_update(alpha, energies, k)
            
            logs.append({
                "step": k,
                "tau": self.get_tau(k),
                "alpha": alpha.detach().cpu().tolist(),
                "energies": energies.detach().cpu().tolist(),
                "residuals": step_residuals,
                "opinfo": step_opinfo,
                "spectral": step_spectral,
            })
        
        # Collapse to MAP world
        s_star = int(torch.argmax(alpha).item())
        W_star = worlds[s_star]
        
        # Final Laplacian for diagnostics
        L_final = laplacian_operator(
            W_star.edge_index, W_star.h.size(0),
            normalized=self.use_normalized_laplacian,
            device=device
        )
        
        # Rewrite proposals
        rewrite_props = self.rewriter(W_star, L_final)
        
        # Final spectral info
        final_spectral = self.compute_spectral_diagnostics(W_star, L_final)
        
        # Theorem candidate
        _, final_res = self.validator(W_star, L_final)
        theorem = self.make_theorem_candidate(final_res, final_spectral)
        
        bundle = {
            "logs": logs,
            "collapsed_index": s_star,
            "rewrite_proposals": rewrite_props,
            "theorem_candidate": theorem.to_dict(),
            "final_spectral": final_spectral,
            "operator_type": self.operator_type,
        }
        
        return W_star, alpha, bundle


# ------------------------------------------------------------
# Initialization helper
# ------------------------------------------------------------
def init_worlds(
    S: int, 
    N: int, 
    d: int, 
    E: int, 
    device: str = "cpu",
    p_undefined: float = 0.25
) -> Tuple[List[WorldState], torch.Tensor]:
    """
    Initialize S worlds with random graphs and embeddings.
    
    Args:
        S: number of worlds
        N: nodes per world
        d: embedding dimension
        E: approximate edges per world
        device: torch device
        p_undefined: probability of Undefined label (A2 support)
    
    Returns:
        worlds: list of WorldState
        alpha: [S] uniform initial amplitudes
    """
    worlds = []
    for _ in range(S):
        h = torch.randn(N, d, device=device) * 0.1
        
        # Random edges
        src = torch.randint(0, N, (E,), device=device)
        dst = torch.randint(0, N, (E,), device=device)
        edge_index = torch.stack([src, dst], dim=0)
        edge_index = _coalesce_edge_index(edge_index, N)
        
        # Tri-logic labels with controlled Undefined mass
        t = torch.zeros(N, dtype=torch.long, device=device)
        n_undef = int(N * p_undefined)
        n_true = (N - n_undef) // 2
        n_false = N - n_undef - n_true
        
        perm = torch.randperm(N, device=device)
        t[perm[:n_true]] = T
        t[perm[n_true:n_true + n_false]] = FLS
        t[perm[n_true + n_false:]] = U
        
        worlds.append(WorldState(h=h, edge_index=edge_index, t_labels=t))
    
    alpha = torch.ones(S, device=device) / S
    return worlds, alpha


# ------------------------------------------------------------
# Diagnostic runner
# ------------------------------------------------------------
def run_diagnostics(bundle: Dict[str, Any]) -> None:
    """Print comprehensive diagnostics from a run."""
    print("=" * 60)
    print(f"NDP Run Diagnostics (operator: {bundle['operator_type']})")
    print("=" * 60)
    
    print(f"\nCollapsed to world {bundle['collapsed_index']}")
    
    print("\n--- Evolution over K steps ---")
    for log in bundle["logs"]:
        k = log["step"]
        tau = log["tau"]
        E_mean = sum(log["energies"]) / len(log["energies"])
        alpha_max = max(log["alpha"])
        
        # Average spectral dim across worlds
        d_s_mean = sum(s["spectral_dim"] for s in log["spectral"]) / len(log["spectral"])
        dir_mean = sum(s["dirichlet_energy"] for s in log["spectral"]) / len(log["spectral"])
        
        # p_undef from first world (representative)
        p_undef = log["residuals"][0]["p_undef"]
        
        print(f"  Step {k}: τ={tau:.2f}, E_mean={E_mean:.4f}, α_max={alpha_max:.4f}, "
              f"d_s={d_s_mean:.2f}, E_dir={dir_mean:.4f}, p(U)={p_undef:.3f}")
    
    print("\n--- Final Spectral Info ---")
    fs = bundle["final_spectral"]
    print(f"  Spectral dimension: {fs['spectral_dim']:.3f}")
    print(f"  Algebraic connectivity (λ₁): {fs['algebraic_connectivity']:.4f}")
    print(f"  Dirichlet energy: {fs['dirichlet_energy']:.4f}")
    
    print("\n--- Theorem Candidate ---")
    tc = bundle["theorem_candidate"]
    print(f"  Statement: {tc['statement'][:80]}...")
    print(f"  Residuals: κ={tc['residual_table']['r_kappa']:.6f}, "
          f"β={tc['residual_table']['r_beta']:.6f}, "
          f"Ω={tc['residual_table']['r_omega']:.6f}")
    
    print("\n--- Rewrite Proposals ---")
    rp = bundle["rewrite_proposals"]
    print(f"  Add edges: {rp['add_edges'][:3]}{'...' if len(rp['add_edges']) > 3 else ''}")
    print(f"  Del edges: {rp['del_edges'][:3]}{'...' if len(rp['del_edges']) > 3 else ''}")
    
    print("=" * 60)


# ------------------------------------------------------------
# Main: test all operator types
# ------------------------------------------------------------
if __name__ == "__main__":
    device = "cpu"
    S, N, d, E = 8, 24, 32, 80
    
    print("Testing NDP Superposed Web v2.0")
    print("-" * 40)
    
    for op_type in ["polynomial", "heat", "chebyshev"]:
        print(f"\n>>> Operator: {op_type}")
        
        worlds, alpha = init_worlds(S, N, d, E, device=device, p_undefined=0.25)
        
        model = NDP_SuperposedWeb_v2(
            d=d, S=S, K=6,
            operator_type=op_type,
            poly_degree=3,
            use_normalized_laplacian=True,
        ).to(device)
        
        W_star, alpha_final, bundle = model(worlds, alpha)
        
        run_diagnostics(bundle)
