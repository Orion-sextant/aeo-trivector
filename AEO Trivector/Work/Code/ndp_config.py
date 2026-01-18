"""
ndp_config.py
=============
Config-driven NDP architecture with mode switching.

Modes:
- PRODUCTION: Lean, fast, sparse-only, minimal logging
- RESEARCH: Full diagnostics, Hamiltonian decomposition, spectral analysis
- CUSTOM: Fine-grained control via NDPConfig

Usage:
    # Production mode (default)
    model = NDP.from_preset("production", d=64)
    
    # Research mode
    model = NDP.from_preset("research", d=64)
    
    # Custom config
    config = NDPConfig(
        operator_type="heat",
        compute_spectral_diagnostics=True,
        compute_hamiltonian=False,
        ...
    )
    model = NDP(config)

α⊗ε⊗ω — December 2024
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Union

import torch
import torch.nn as nn
import torch.nn.functional as F


# =============================================================================
# §0. CONSTANTS & ENUMS
# =============================================================================
T, FLS, U = 0, 1, 2  # Tri-logic encoding


class Mode(Enum):
    PRODUCTION = "production"
    RESEARCH = "research"
    CUSTOM = "custom"


class CurvatureType(Enum):
    FORMAN = "forman"
    OLLIVIER = "ollivier"
    NONE = "none"


# =============================================================================
# §1. CONFIGURATION
# =============================================================================
@dataclass
class NDPConfig:
    """
    Master configuration for NDP.
    
    Presets:
    - production: Fast, lean, no diagnostics
    - research: Full diagnostics, theoretical analysis
    """
    # === Core architecture ===
    d: int = 64                          # Embedding dimension
    S: int = 16                          # Superposition size
    K: int = 6                           # Evolution steps (log-spiral collapse)
    
    # === Operator selection ===
    operator_type: Literal["polynomial", "heat", "chebyshev"] = "heat"
    poly_degree: int = 3                 # Polynomial/Chebyshev degree
    heat_t: float = 1.0                  # Heat kernel diffusion time
    heat_K: int = 12                     # Chebyshev terms for heat kernel
    learnable_heat_t: bool = False       # Make t learnable (research only)
    
    # === Laplacian ===
    use_normalized_laplacian: bool = True
    
    # === Temperature annealing ===
    tau_init: float = 1.0
    tau_final: float = 5.0
    
    # === ICF Constants ===
    mu: float = 0.569
    kappa_target: float = 0.0323
    beta_target: float = 0.207
    omega_target: float = 0.8479
    
    # === Loss weights ===
    lambda_invariant: float = 1.0        # ICF constraint weight
    lambda_undefined: float = 0.7        # A2 preservation weight
    lambda_coherence: float = 0.1        # Dirichlet energy weight
    
    # === Rewrite proposer ===
    max_add_edges: int = 6
    max_del_edges: int = 4
    
    # === Diagnostics (mode-dependent) ===
    compute_spectral_diagnostics: bool = False
    compute_hamiltonian: bool = False
    compute_full_spectral_dim: bool = False  # Expensive, research only
    log_operator_info: bool = True
    log_per_world: bool = False          # Log each world separately
    
    # === Curvature (graph geometry regularizer) ===
    use_curvature: bool = False
    curvature_type: CurvatureType = CurvatureType.FORMAN
    lambda_curvature: float = 0.0        # Weight for curvature penalty
    curvature_target: float = 0.0        # Target curvature (0 = flat)
    node_level_curvature: bool = False   # Aggregate to nodes vs edge-level
    
    # === Performance ===
    lambda_max_iterations: int = 30      # Power iteration for λ_max
    spectral_dim_samples: int = 10       # Hutchinson trace samples
    
    # === Mode tracking ===
    mode: Mode = Mode.CUSTOM
    
    @classmethod
    def production(cls, **overrides) -> "NDPConfig":
        """Lean configuration for deployment."""
        defaults = dict(
            operator_type="heat",
            learnable_heat_t=False,
            compute_spectral_diagnostics=False,
            compute_hamiltonian=False,
            compute_full_spectral_dim=False,
            log_operator_info=False,
            log_per_world=False,
            use_curvature=False,
            mode=Mode.PRODUCTION,
        )
        defaults.update(overrides)
        return cls(**defaults)
    
    @classmethod
    def research(cls, **overrides) -> "NDPConfig":
        """Full diagnostics for theoretical analysis."""
        defaults = dict(
            operator_type="heat",
            learnable_heat_t=True,
            compute_spectral_diagnostics=True,
            compute_hamiltonian=True,
            compute_full_spectral_dim=True,
            log_operator_info=True,
            log_per_world=True,
            use_curvature=True,
            curvature_type=CurvatureType.FORMAN,
            lambda_curvature=0.01,
            curvature_target=0.0,
            mode=Mode.RESEARCH,
        )
        defaults.update(overrides)
        return cls(**defaults)
    
    def __post_init__(self):
        # Validate
        assert self.d > 0, "d must be positive"
        assert self.S > 0, "S must be positive"
        assert self.K > 0, "K must be positive"
        assert self.operator_type in ("polynomial", "heat", "chebyshev")


# =============================================================================
# §2. DATA STRUCTURES
# =============================================================================
@dataclass
class WorldState:
    """One candidate world in superposition."""
    h: torch.Tensor           # [N, d]
    edge_index: torch.Tensor  # [2, E]
    t: torch.Tensor           # [N] in {T, FLS, U}
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpectralInfo:
    """Spectral diagnostics (computed only in research mode)."""
    lambda_1: float = float('nan')       # Algebraic connectivity
    lambda_max: float = float('nan')     # Largest eigenvalue
    spectral_dimension: float = float('nan')
    num_components: int = 0
    dirichlet_energy: float = float('nan')


@dataclass
class HamiltonianInfo:
    """Hamiltonian decomposition (computed only in research mode)."""
    kinetic: float = 0.0      # T = <h, Lh>
    potential: float = 0.0    # V = learned
    total: float = 0.0        # H = T + V


@dataclass 
class StepLog:
    """Log for one evolution step."""
    step: int
    tau: float
    energies: List[float]
    alpha: List[float]
    residuals: Optional[List[Dict[str, float]]] = None
    operator_info: Optional[List[Dict[str, Any]]] = None
    hamiltonian: Optional[List[HamiltonianInfo]] = None
    spectral: Optional[List[SpectralInfo]] = None
    curvature: Optional[List["CurvatureInfo"]] = None  # Forward reference


@dataclass
class TheoremCandidate:
    """Structured output for formal verification."""
    statement: str
    assumptions: List[str]
    residuals: Dict[str, float]
    spectral_info: Optional[SpectralInfo] = None
    hamiltonian_info: Optional[HamiltonianInfo] = None
    curvature_info: Optional["CurvatureInfo"] = None


@dataclass
class NDPResult:
    """Complete output from NDP forward pass."""
    collapsed_index: int
    final_alpha: List[float]
    final_world: WorldState
    rewrite_proposals: Dict[str, List[Tuple[int, int]]]
    theorem: TheoremCandidate
    logs: List[StepLog]
    config: NDPConfig


# =============================================================================
# §3. SPARSE GRAPH UTILITIES
# =============================================================================
def _coalesce_edge_index(edge_index: torch.Tensor, num_nodes: int) -> torch.Tensor:
    """Remove self-loops and duplicates via hashing."""
    src, dst = edge_index
    mask = src != dst
    src, dst = src[mask], dst[mask]
    key = src * num_nodes + dst
    uniq = torch.unique(key)
    return torch.stack([uniq // num_nodes, uniq % num_nodes], dim=0)


def symmetrize_edge_index(edge_index: torch.Tensor, num_nodes: int) -> torch.Tensor:
    """Add reverse edges and coalesce."""
    src, dst = edge_index
    rev = torch.stack([dst, src], dim=0)
    out = torch.cat([edge_index, rev], dim=1)
    return _coalesce_edge_index(out, num_nodes)


def build_sparse_laplacian(
    edge_index: torch.Tensor,
    num_nodes: int,
    *,
    normalized: bool = True,
    device: Optional[torch.device] = None,
    dtype: torch.dtype = torch.float32,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Build sparse COO Laplacian.
    
    Returns: (L, degree_vector)
    """
    device = device or edge_index.device
    ei = symmetrize_edge_index(edge_index.to(device), num_nodes)
    src, dst = ei[0], ei[1]
    vals = torch.ones(src.numel(), device=device, dtype=dtype)
    
    deg = torch.zeros(num_nodes, device=device, dtype=dtype)
    deg.index_add_(0, src, vals)
    
    diag_idx = torch.arange(num_nodes, device=device)
    
    if normalized:
        deg_inv_sqrt = torch.where(deg > 0, deg.pow(-0.5), torch.zeros_like(deg))
        off_vals = -deg_inv_sqrt[src] * deg_inv_sqrt[dst]
        idx = torch.cat([
            torch.stack([diag_idx, diag_idx], dim=0),
            torch.stack([src, dst], dim=0)
        ], dim=1)
        v = torch.cat([torch.ones(num_nodes, device=device, dtype=dtype), off_vals], dim=0)
    else:
        idx = torch.cat([
            torch.stack([diag_idx, diag_idx], dim=0),
            torch.stack([src, dst], dim=0)
        ], dim=1)
        v = torch.cat([deg, -vals], dim=0)
    
    L = torch.sparse_coo_tensor(idx, v, size=(num_nodes, num_nodes), 
                                 device=device, dtype=dtype).coalesce()
    return L, deg


def spmm(L: torch.Tensor, x: torch.Tensor) -> torch.Tensor:
    """Sparse matrix multiply."""
    if not L.is_sparse:
        return L @ x
    return torch.sparse.mm(L, x)


def dirichlet_energy(h: torch.Tensor, L: torch.Tensor) -> torch.Tensor:
    """
    Mean Dirichlet energy per node: E(h) = <h, Lh> / N
    
    This is a normalized version of the standard Dirichlet energy:
        E_standard = (1/2) * Σ_{(i,j)} ||h_i - h_j||² = (1/2) * tr(h^T L h)
    
    Our version divides by N to make it scale-invariant across graph sizes.
    For normalized Laplacian, values are well-conditioned in [0, 2].
    """
    Lh = spmm(L, h)
    return torch.sum(h * Lh) / h.size(0)


# =============================================================================
# §4. SPECTRAL UTILITIES (Research Mode Only)
# =============================================================================
def estimate_lambda_max(L: torch.Tensor, num_iter: int = 30) -> float:
    """Power iteration for largest eigenvalue."""
    N = L.size(0)
    v = torch.randn(N, 1, device=L.device, dtype=torch.float32)
    v = v / (v.norm() + 1e-12)
    for _ in range(num_iter):
        w = spmm(L, v)
        v = w / (w.norm() + 1e-12)
    Lv = spmm(L, v)
    return max(float((v.T @ Lv).item()), 1e-6)


def estimate_lambda_1(L: torch.Tensor, lambda_max: float, num_iter: int = 50) -> float:
    """Inverse power iteration for smallest non-zero eigenvalue."""
    N = L.size(0)
    v = torch.randn(N, 1, device=L.device, dtype=L.dtype)
    v = v - v.mean()
    v = v / (v.norm() + 1e-12)
    
    for _ in range(num_iter):
        Lv = spmm(L, v)
        w = lambda_max * v - Lv
        w = w - w.mean()
        v = w / (w.norm() + 1e-12)
    
    Lv = spmm(L, v)
    return max(float((v.T @ Lv).item()), 1e-10)


def estimate_spectral_dimension(
    L: torch.Tensor,
    lambda_max: float,
    num_samples: int = 10,
    K: int = 12,
) -> float:
    """
    Estimate spectral dimension via heat trace.
    
    Tr(exp(-tL)) ~ t^{-d_s/2} as t→0
    """
    N = L.size(0)
    device, dtype = L.device, torch.float32
    
    t_values = torch.logspace(-1, 1, steps=8, device=device, dtype=dtype)
    traces = []
    
    for t in t_values:
        trace_est = 0.0
        for _ in range(num_samples):
            z = torch.randn(N, 1, device=device, dtype=dtype)
            exp_z = _apply_heat_kernel(z, L, float(t), K, lambda_max)
            trace_est += float((z.T @ exp_z).item())
        traces.append(trace_est / num_samples)
    
    # Linear regression: log(trace) = -d_s/2 * log(t) + const
    log_t = torch.log(t_values).cpu().numpy()
    log_trace = torch.tensor(traces).log().cpu().numpy()
    
    # Least squares
    A = log_t.reshape(-1, 1)
    A = torch.tensor([[x, 1.0] for x in log_t]).numpy()
    result = torch.linalg.lstsq(torch.tensor(A, dtype=torch.float32), 
                                 torch.tensor(log_trace, dtype=torch.float32))
    slope = float(result.solution[0])
    
    return max(-2 * slope, 0.0)


def count_components(edge_index: torch.Tensor, num_nodes: int) -> int:
    """Union-find for connected components."""
    parent = list(range(num_nodes))
    
    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]
    
    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py
    
    src, dst = edge_index.cpu().tolist()
    for s, d in zip(src, dst):
        union(s, d)
    
    return len(set(find(i) for i in range(num_nodes)))


def compute_spectral_info(
    world: WorldState,
    L: torch.Tensor,
    config: NDPConfig,
    lambda_max: float,
) -> SpectralInfo:
    """Compute all spectral diagnostics."""
    N = world.h.size(0)
    
    E_dir = float(dirichlet_energy(world.h, L).detach())
    lambda_1 = estimate_lambda_1(L, lambda_max, num_iter=config.lambda_max_iterations)
    num_comp = count_components(world.edge_index, N)
    
    if config.compute_full_spectral_dim and N < 500:
        d_s = estimate_spectral_dimension(L, lambda_max, config.spectral_dim_samples)
    else:
        d_s = float('nan')
    
    return SpectralInfo(
        lambda_1=lambda_1,
        lambda_max=lambda_max,
        spectral_dimension=d_s,
        num_components=num_comp,
        dirichlet_energy=E_dir,
    )


# =============================================================================
# §4b. CURVATURE MODULE (Graph Geometry)
# =============================================================================
class GraphCurvature:
    """
    Unified curvature interface for graph geometry.
    
    Supports:
    - Forman-Ricci: Fast combinatorial curvature (edge-based)
    - Ollivier-Ricci: OT-based curvature (stub for future implementation)
    
    Forman-Ricci for simple unweighted graphs:
        κ_F(u,v) = 4 - (deg(u) + deg(v))
    
    Interpretation:
    - κ > 0: Edge is in a "clustered" region (sphere-like)
    - κ < 0: Edge is in an "expanding" region (hyperbolic-like)
    - κ = 0: Flat geometry
    """
    
    def __init__(
        self,
        curvature_type: CurvatureType = CurvatureType.FORMAN,
        alpha: float = 0.5,  # Ollivier lazy RW parameter (unused for Forman)
    ):
        self.curvature_type = curvature_type
        self.alpha = alpha
    
    def edge_curvature(
        self,
        edge_index: torch.Tensor,
        num_nodes: int,
    ) -> Dict[Tuple[int, int], float]:
        """
        Compute edge curvature κ(u,v) for each undirected edge (u < v).
        """
        if self.curvature_type == CurvatureType.FORMAN:
            return self._forman_edge_curvature(edge_index, num_nodes)
        elif self.curvature_type == CurvatureType.OLLIVIER:
            return self._ollivier_edge_curvature_stub(edge_index, num_nodes)
        elif self.curvature_type == CurvatureType.NONE:
            return {}
        else:
            raise ValueError(f"Unknown curvature type: {self.curvature_type}")
    
    def node_curvature(
        self,
        edge_curv: Dict[Tuple[int, int], float],
        num_nodes: int,
        device: torch.device = torch.device("cpu"),
    ) -> torch.Tensor:
        """
        Aggregate edge curvature to nodes (sum of incident edge curvatures).
        """
        k_node = torch.zeros(num_nodes, device=device)
        for (u, v), k in edge_curv.items():
            k_node[u] += k
            k_node[v] += k
        return k_node
    
    def mean_curvature(
        self,
        edge_curv: Dict[Tuple[int, int], float],
    ) -> float:
        """Mean edge curvature across all edges."""
        if not edge_curv:
            return 0.0
        return sum(edge_curv.values()) / len(edge_curv)
    
    def _forman_edge_curvature(
        self,
        edge_index: torch.Tensor,
        num_nodes: int,
    ) -> Dict[Tuple[int, int], float]:
        """
        Forman-Ricci curvature for simple unweighted graphs.
        
        Formula: κ_F(u,v) = 4 - (deg(u) + deg(v))
        
        This is the simplest form; for weighted graphs or graphs with
        parallel edges, the formula includes additional terms.
        """
        src, dst = edge_index
        device = edge_index.device
        
        # Compute degrees
        deg = torch.zeros(num_nodes, device=device)
        ones = torch.ones_like(src, dtype=torch.float, device=device)
        deg.index_add_(0, src, ones)
        deg.index_add_(0, dst, ones)
        
        curv: Dict[Tuple[int, int], float] = {}
        seen = set()
        
        for s, d in zip(src.tolist(), dst.tolist()):
            if s == d:
                continue
            edge = (min(s, d), max(s, d))
            if edge in seen:
                continue
            seen.add(edge)
            
            k = 4.0 - (float(deg[edge[0]]) + float(deg[edge[1]]))
            curv[edge] = k
        
        return curv
    
    def _ollivier_edge_curvature_stub(
        self,
        edge_index: torch.Tensor,
        num_nodes: int,
    ) -> Dict[Tuple[int, int], float]:
        """
        Placeholder for Ollivier-Ricci curvature.
        
        Full implementation requires optimal transport (Wasserstein distance)
        between probability measures on node neighborhoods:
        
            κ_OR(u,v) = 1 - W_1(μ_u, μ_v) / d(u,v)
        
        where μ_u is the lazy random walk distribution centered at u.
        
        For now, returns zeros. Replace with full OT implementation when ready.
        """
        src, dst = edge_index
        curv: Dict[Tuple[int, int], float] = {}
        seen = set()
        
        for s, d in zip(src.tolist(), dst.tolist()):
            if s == d:
                continue
            edge = (min(s, d), max(s, d))
            if edge in seen:
                continue
            seen.add(edge)
            curv[edge] = 0.0
        
        return curv


@dataclass
class CurvatureInfo:
    """Curvature diagnostics for a world."""
    mean_curvature: float = 0.0
    min_curvature: float = 0.0
    max_curvature: float = 0.0
    curvature_penalty: float = 0.0
    num_positive: int = 0  # Number of edges with κ > 0
    num_negative: int = 0  # Number of edges with κ < 0


def compute_curvature_info(
    world: WorldState,
    config: NDPConfig,
) -> Tuple[CurvatureInfo, torch.Tensor]:
    """
    Compute curvature diagnostics and penalty.
    
    Returns:
        info: CurvatureInfo dataclass
        penalty: torch.Tensor (scalar) for loss
    """
    device = world.h.device
    dtype = world.h.dtype
    
    if not config.use_curvature or config.curvature_type == CurvatureType.NONE:
        return CurvatureInfo(), torch.tensor(0.0, device=device, dtype=dtype)
    
    curv_module = GraphCurvature(curvature_type=config.curvature_type)
    edge_curv = curv_module.edge_curvature(world.edge_index, world.h.size(0))
    
    if not edge_curv:
        return CurvatureInfo(), torch.tensor(0.0, device=device, dtype=dtype)
    
    vals = list(edge_curv.values())
    vals_t = torch.tensor(vals, device=device, dtype=dtype)
    
    if config.node_level_curvature:
        k_node = curv_module.node_curvature(edge_curv, world.h.size(0), device)
        penalty = ((k_node - config.curvature_target) ** 2).mean()
        mean_k = float(k_node.mean())
    else:
        penalty = ((vals_t - config.curvature_target) ** 2).mean()
        mean_k = float(vals_t.mean())
    
    info = CurvatureInfo(
        mean_curvature=mean_k,
        min_curvature=min(vals),
        max_curvature=max(vals),
        curvature_penalty=float(penalty.detach()),
        num_positive=sum(1 for v in vals if v > 0),
        num_negative=sum(1 for v in vals if v < 0),
    )
    
    return info, penalty


# =============================================================================
# §5. CHEBYSHEV UTILITIES
# =============================================================================
def _cheb_coeffs_exp(
    t: float,
    K: int,
    lambda_max: float,
    device: torch.device,
    dtype: torch.dtype,
    M: int = 512,
) -> torch.Tensor:
    """Chebyshev coefficients for exp(-tλ) on [0, λ_max]."""
    j = torch.arange(M, device=device, dtype=dtype)
    theta = math.pi * (j + 0.5) / M
    x = torch.cos(theta)
    lam = 0.5 * lambda_max * (x + 1.0)
    f = torch.exp(-t * lam)
    
    a = []
    for k in range(K + 1):
        ck = torch.cos(k * theta)
        ak = (2.0 / M) * torch.sum(f * ck)
        a.append(ak)
    a = torch.stack(a, dim=0)
    a[0] = a[0] * 0.5
    return a


def _apply_cheb_filter(
    h: torch.Tensor,
    L: torch.Tensor,
    coeffs: torch.Tensor,
    lambda_max: float,
) -> torch.Tensor:
    """Apply Chebyshev polynomial filter."""
    K = len(coeffs) - 1
    
    def L_tilde(x):
        return (2.0 / lambda_max) * spmm(L, x) - x
    
    t0 = h
    out = coeffs[0] * t0
    
    if K >= 1:
        t1 = L_tilde(h)
        out = out + coeffs[1] * t1
    else:
        return out
    
    for k in range(2, K + 1):
        t2 = 2.0 * L_tilde(t1) - t0
        out = out + coeffs[k] * t2
        t0, t1 = t1, t2
    
    return out


def _apply_heat_kernel(
    h: torch.Tensor,
    L: torch.Tensor,
    t: float,
    K: int,
    lambda_max: float,
) -> torch.Tensor:
    """Apply exp(-tL) via Chebyshev."""
    coeffs = _cheb_coeffs_exp(t, K, lambda_max, h.device, h.dtype)
    return _apply_cheb_filter(h, L, coeffs, lambda_max)


# =============================================================================
# §6. SPECTRAL OPERATORS
# =============================================================================
class SpectralOperator(nn.Module):
    """Base class for spectral operators."""
    def forward(
        self,
        h: torch.Tensor,
        L: torch.Tensor,
        tri_labels: torch.Tensor,
        lambda_max: float,
    ) -> Tuple[torch.Tensor, Dict[str, Any]]:
        raise NotImplementedError


class PolynomialOperator(SpectralOperator):
    """g(L)h = Σ c_k L^k h — signal-based, O(K·E)."""
    
    def __init__(self, config: NDPConfig):
        super().__init__()
        K = config.poly_degree
        self.coeffs = nn.Parameter(torch.zeros(K + 1))
        with torch.no_grad():
            self.coeffs[0] = 1.0
            self.coeffs[1] = -0.1
        
        self.corr = nn.Sequential(
            nn.Linear(config.d, config.d),
            nn.GELU(),
            nn.Linear(config.d, config.d),
        )
        self.config = config
    
    def forward(self, h, L, tri_labels, lambda_max):
        out = self.coeffs[0] * h
        hk = h
        for k in range(1, len(self.coeffs)):
            hk = spmm(L, hk)
            out = out + self.coeffs[k] * hk
        
        # A2: Undefined evolves slower
        gate = torch.ones(h.size(0), device=h.device, dtype=h.dtype)
        gate[tri_labels == U] = 0.6
        out = out * gate.unsqueeze(-1)
        
        h_new = out + self.corr(h)
        
        info = {}
        if self.config.log_operator_info:
            info = {f"c{k}": float(self.coeffs[k].detach()) for k in range(len(self.coeffs))}
        
        return h_new, info


class ChebyshevOperator(SpectralOperator):
    """g(L)h ≈ Σ θ_k T_k(L̃) h — stable for high degrees."""
    
    def __init__(self, config: NDPConfig):
        super().__init__()
        K = config.poly_degree
        self.K = K
        self.theta = nn.Parameter(torch.zeros(K + 1))
        with torch.no_grad():
            self.theta[0] = 1.0
        
        self.corr = nn.Sequential(
            nn.Linear(config.d, config.d),
            nn.GELU(),
            nn.Linear(config.d, config.d),
        )
        self.config = config
    
    def forward(self, h, L, tri_labels, lambda_max):
        out = _apply_cheb_filter(h, L, self.theta, lambda_max)
        
        gate = torch.ones(h.size(0), device=h.device, dtype=h.dtype)
        gate[tri_labels == U] = 0.6
        out = out * gate.unsqueeze(-1)
        
        h_new = out + self.corr(h)
        
        info = {}
        if self.config.log_operator_info:
            info = {f"θ{k}": float(self.theta[k].detach()) for k in range(self.K + 1)}
            info["λ_max"] = lambda_max
        
        return h_new, info


class HeatKernelOperator(SpectralOperator):
    """exp(-tL)h via Chebyshev — O(K·E), no matrix exp."""
    
    def __init__(self, config: NDPConfig):
        super().__init__()
        self.K = config.heat_K
        
        if config.learnable_heat_t:
            self.log_t = nn.Parameter(torch.tensor(math.log(config.heat_t)))
        else:
            self.register_buffer('log_t', torch.tensor(math.log(config.heat_t)))
        
        self.corr = nn.Sequential(
            nn.Linear(config.d, config.d),
            nn.GELU(),
            nn.Linear(config.d, config.d),
        )
        self.config = config
    
    @property
    def t(self) -> float:
        return float(torch.exp(self.log_t).detach())
    
    def forward(self, h, L, tri_labels, lambda_max):
        t_val = float(torch.exp(self.log_t).detach())
        out = _apply_heat_kernel(h, L, t_val, self.K, lambda_max)
        
        gate = torch.ones(h.size(0), device=h.device, dtype=h.dtype)
        gate[tri_labels == U] = 0.6
        out = out * gate.unsqueeze(-1)
        
        h_new = out + self.corr(h)
        
        info = {}
        if self.config.log_operator_info:
            info = {"t": t_val, "K": self.K, "λ_max": lambda_max}
        
        return h_new, info


def build_operator(config: NDPConfig) -> SpectralOperator:
    """Factory for spectral operators."""
    if config.operator_type == "polynomial":
        return PolynomialOperator(config)
    elif config.operator_type == "chebyshev":
        return ChebyshevOperator(config)
    elif config.operator_type == "heat":
        return HeatKernelOperator(config)
    else:
        raise ValueError(f"Unknown operator: {config.operator_type}")


# =============================================================================
# §7. HAMILTONIAN (Research Mode Only)
# =============================================================================
class HamiltonianModule(nn.Module):
    """H = T + V decomposition for theoretical analysis."""
    
    def __init__(self, config: NDPConfig):
        super().__init__()
        self.potential = nn.Sequential(
            nn.Linear(config.d, config.d),
            nn.Softplus(),
            nn.Linear(config.d, 1),
        )
    
    def forward(self, h: torch.Tensor, L: torch.Tensor) -> HamiltonianInfo:
        T = float(dirichlet_energy(h, L).detach())
        V = float(self.potential(h).mean().detach())
        return HamiltonianInfo(kinetic=T, potential=V, total=T + V)


# =============================================================================
# §8. ICF VALIDATOR
# =============================================================================
class ICFValidator(nn.Module):
    """
    Validate ICF constraint system C1-C5 + A2 + coherence + curvature.
    
    Constraints:
        C1: κ = μ²/10 (collapse rate from equilibrium)
        C4: β = ((1-μ)² + μ·κ) / (1 - κ/3) (incompleteness)
        C5: μ² + Ω² - β² = 1 (hyperboloid constraint)
             → Ω = √(1 + β² - μ²)
        A2: Undefined nodes preserved (p(U) ≥ β_target)
    
    Regularizers:
        - Dirichlet energy (coherence)
        - Curvature penalty (graph geometry, optional)
    """
    
    def __init__(self, config: NDPConfig):
        super().__init__()
        self.config = config
    
    def forward(
        self, 
        world: WorldState, 
        L: torch.Tensor
    ) -> Tuple[torch.Tensor, Dict[str, float], Optional[CurvatureInfo]]:
        cfg = self.config
        device = world.h.device
        dtype = world.h.dtype
        
        mu = torch.tensor(cfg.mu, device=device, dtype=dtype)
        
        # C1: κ = μ²/10
        kappa = mu**2 / 10.0
        
        # C4: β = ((1-μ)² + μ·κ) / (1 - κ/3)
        beta = ((1.0 - mu)**2 + mu * kappa) / (1.0 - kappa / 3.0)
        
        # C5: μ² + Ω² - β² = 1  →  Ω² = 1 + β² - μ²  →  Ω = √(1 + β² - μ²)
        omega = torch.sqrt(torch.clamp(1.0 - mu**2 + beta**2, min=0.0))
        
        r_kappa = kappa - cfg.kappa_target
        r_beta = beta - cfg.beta_target
        r_omega = omega - cfg.omega_target
        
        # A2: Undefined preservation
        p_undef = (world.t == U).float().mean()
        pen_undef = F.relu(torch.tensor(cfg.beta_target, device=device, dtype=dtype) - p_undef)
        
        # Coherence (Dirichlet energy)
        E_dir = dirichlet_energy(world.h, L)
        
        # Curvature penalty (graph geometry)
        curv_info = None
        curv_pen = torch.tensor(0.0, device=device, dtype=dtype)
        if cfg.use_curvature:
            curv_info, curv_pen = compute_curvature_info(world, cfg)
        
        energy = (
            cfg.lambda_invariant * (r_kappa**2 + r_beta**2 + r_omega**2)
            + cfg.lambda_undefined * pen_undef
            + cfg.lambda_coherence * E_dir
            + cfg.lambda_curvature * curv_pen
        )
        
        residuals = {
            "r_κ": float(r_kappa.detach()),
            "r_β": float(r_beta.detach()),
            "r_Ω": float(r_omega.detach()),
            "p(U)": float(p_undef.detach()),
            "κ": float(kappa.detach()),
            "β": float(beta.detach()),
            "Ω": float(omega.detach()),
            "E_dir": float(E_dir.detach()),
        }
        
        if cfg.use_curvature and curv_info:
            residuals["mean_κ_graph"] = curv_info.mean_curvature
            residuals["curv_penalty"] = curv_info.curvature_penalty
        
        return energy, residuals, curv_info


# =============================================================================
# §9. REWRITE PROPOSER
# =============================================================================
class RewriteProposer(nn.Module):
    """Propose graph rewrites based on embedding similarity."""
    
    def __init__(self, config: NDPConfig):
        super().__init__()
        self.max_add = config.max_add_edges
        self.max_del = config.max_del_edges
    
    @torch.no_grad()
    def forward(self, world: WorldState) -> Dict[str, List[Tuple[int, int]]]:
        h = world.h
        N = h.size(0)
        
        h_norm = F.normalize(h, dim=-1)
        sim = h_norm @ h_norm.T
        
        ei = symmetrize_edge_index(world.edge_index, N)
        existing = set((int(s), int(d)) for s, d in zip(ei[0].tolist(), ei[1].tolist()))
        
        sim_masked = sim.clone()
        sim_masked.fill_diagonal_(-1e9)
        for s, d in list(existing)[:5000]:
            sim_masked[s, d] = -1e9
        
        flat = sim_masked.view(-1)
        topk = torch.topk(flat, k=min(self.max_add, flat.numel())).indices.tolist()
        adds = [(idx // N, idx % N) for idx in topk if idx // N != idx % N]
        
        edge_scores = [(float(sim[s, d]), s, d) for s, d in existing if s != d]
        edge_scores.sort(key=lambda x: x[0])
        dels = [(s, d) for _, s, d in edge_scores[:self.max_del]]
        
        return {"add": adds[:self.max_add], "del": dels}


# =============================================================================
# §10. NDP MAIN CLASS
# =============================================================================
class NDP(nn.Module):
    """
    Neural Derived Proof architecture with config-driven behavior.
    
    Usage:
        # Production
        model = NDP.from_preset("production", d=64, S=8)
        
        # Research
        model = NDP.from_preset("research", d=64, S=8)
        
        # Custom
        config = NDPConfig(...)
        model = NDP(config)
    """
    
    def __init__(self, config: NDPConfig):
        super().__init__()
        self.config = config
        
        self.operator = build_operator(config)
        self.validator = ICFValidator(config)
        self.rewriter = RewriteProposer(config)
        
        if config.compute_hamiltonian:
            self.hamiltonian = HamiltonianModule(config)
        else:
            self.hamiltonian = None
    
    @classmethod
    def from_preset(
        cls, 
        preset: Literal["production", "research"], 
        **overrides
    ) -> "NDP":
        """Create NDP from preset configuration."""
        if preset == "production":
            config = NDPConfig.production(**overrides)
        elif preset == "research":
            config = NDPConfig.research(**overrides)
        else:
            raise ValueError(f"Unknown preset: {preset}")
        return cls(config)
    
    def get_tau(self, step: int) -> float:
        progress = step / max(self.config.K - 1, 1)
        return self.config.tau_init + (self.config.tau_final - self.config.tau_init) * progress
    
    def amplitude_update(
        self, 
        alpha: torch.Tensor, 
        energies: torch.Tensor, 
        step: int
    ) -> torch.Tensor:
        tau = self.get_tau(step)
        alpha = alpha * torch.exp(-tau * energies)
        return alpha / (alpha.sum() + 1e-9)
    
    def forward(
        self, 
        worlds: List[WorldState], 
        alpha: torch.Tensor
    ) -> NDPResult:
        cfg = self.config
        logs: List[StepLog] = []
        
        for step in range(cfg.K):
            tau = self.get_tau(step)
            energies = []
            
            # Per-world data (only in research/verbose mode)
            residuals_list = [] if cfg.log_per_world else None
            op_info_list = [] if cfg.log_operator_info else None
            ham_list = [] if cfg.compute_hamiltonian else None
            spec_list = [] if (cfg.compute_spectral_diagnostics and step == cfg.K - 1) else None
            curv_list = [] if (cfg.use_curvature and step == cfg.K - 1) else None
            
            for s, world in enumerate(worlds):
                N = world.h.size(0)
                device = world.h.device
                dtype = world.h.dtype
                
                # Build Laplacian
                L, _ = build_sparse_laplacian(
                    world.edge_index, N,
                    normalized=cfg.use_normalized_laplacian,
                    device=device, dtype=dtype,
                )
                
                lambda_max = 2.0 if cfg.use_normalized_laplacian else estimate_lambda_max(L, cfg.lambda_max_iterations)
                
                # Sanity check: normalized Laplacian should have λ_max ≤ 2
                if cfg.use_normalized_laplacian:
                    assert lambda_max <= 2.0 + 1e-6, f"λ_max={lambda_max} > 2 for normalized Laplacian"
                
                # Operator evolution
                h_new, op_info = self.operator(world.h, L, world.t, lambda_max)
                worlds[s] = WorldState(h=h_new, edge_index=world.edge_index, t=world.t)
                
                # Validation (now includes curvature)
                E, residuals, curv_info = self.validator(worlds[s], L)
                energies.append(E)
                
                # Collect diagnostics
                if residuals_list is not None:
                    residuals_list.append(residuals)
                if op_info_list is not None:
                    op_info_list.append(op_info)
                if ham_list is not None and self.hamiltonian is not None:
                    ham_list.append(self.hamiltonian(worlds[s].h, L))
                if spec_list is not None:
                    spec_list.append(compute_spectral_info(worlds[s], L, cfg, lambda_max))
                if curv_list is not None and curv_info is not None:
                    curv_list.append(curv_info)
            
            energies_t = torch.stack(energies)
            alpha = self.amplitude_update(alpha, energies_t.detach(), step)
            
            logs.append(StepLog(
                step=step,
                tau=tau,
                energies=[float(e.detach()) for e in energies_t],
                alpha=alpha.detach().cpu().tolist(),
                residuals=residuals_list,
                operator_info=op_info_list,
                hamiltonian=ham_list,
                spectral=spec_list,
                curvature=curv_list,
            ))
        
        # Collapse
        collapsed_idx = int(torch.argmax(alpha).item())
        W_star = worlds[collapsed_idx]
        
        # Final diagnostics
        final_res = logs[-1].residuals[collapsed_idx] if logs[-1].residuals else {}
        final_spec = logs[-1].spectral[collapsed_idx] if logs[-1].spectral else None
        final_ham = logs[-1].hamiltonian[collapsed_idx] if logs[-1].hamiltonian else None
        final_curv = logs[-1].curvature[collapsed_idx] if logs[-1].curvature else None
        
        theorem = TheoremCandidate(
            statement="Given A1-A3 and C1-C5: μ² + Ω² - β² = 1",
            assumptions=["A1: Self-reference", "A2: Undefined preservation", 
                        "A3: Finite collapse (K=6)", "C1-C5: ICF constraints"],
            residuals=final_res,
            spectral_info=final_spec,
            hamiltonian_info=final_ham,
            curvature_info=final_curv,
        )
        
        return NDPResult(
            collapsed_index=collapsed_idx,
            final_alpha=alpha.detach().cpu().tolist(),
            final_world=W_star,
            rewrite_proposals=self.rewriter(W_star),
            theorem=theorem,
            logs=logs,
            config=cfg,
        )


# =============================================================================
# §11. UTILITIES
# =============================================================================
def init_worlds(
    S: int, N: int, d: int, E: int,
    *, device: str = "cpu", p_undef: float = 0.25,
) -> Tuple[List[WorldState], torch.Tensor]:
    """Create S random worlds."""
    device_t = torch.device(device)
    worlds = []
    
    for _ in range(S):
        h = torch.randn(N, d, device=device_t) * 0.1
        src = torch.randint(0, N, (E,), device=device_t)
        dst = torch.randint(0, N, (E,), device=device_t)
        edge_index = torch.stack([src, dst], dim=0)
        
        t = torch.zeros(N, dtype=torch.long, device=device_t)
        n_undef = int(N * p_undef)
        n_true = (N - n_undef) // 2
        perm = torch.randperm(N, device=device_t)
        t[perm[:n_true]] = T
        t[perm[n_true:N - n_undef]] = FLS
        t[perm[N - n_undef:]] = U
        
        worlds.append(WorldState(h=h, edge_index=edge_index, t=t))
    
    alpha = torch.ones(S, device=device_t) / S
    return worlds, alpha


def print_result(result: NDPResult) -> None:
    """Pretty-print NDP result."""
    cfg = result.config
    mode_str = f"[{cfg.mode.value.upper()}]"
    
    print("=" * 70)
    print(f"NDP {mode_str} — {cfg.operator_type} operator")
    print("=" * 70)
    
    print(f"\nCollapsed to world {result.collapsed_index}")
    print(f"Final α: max={max(result.final_alpha):.4f}")
    
    print("\n--- Evolution ---")
    for log in result.logs:
        E_mean = sum(log.energies) / len(log.energies)
        alpha_max = max(log.alpha)
        line = f"  Step {log.step}: τ={log.tau:.2f}, E={E_mean:.4f}, α_max={alpha_max:.4f}"
        
        if log.hamiltonian:
            h = log.hamiltonian[0]
            line += f", T={h.kinetic:.4f}, V={h.potential:.4f}"
        
        print(line)
    
    print("\n--- Theorem ---")
    print(f"  {result.theorem.statement}")
    if result.theorem.residuals:
        res = result.theorem.residuals
        print(f"  Residuals: r_κ={res.get('r_κ', 0):.6f}, r_β={res.get('r_β', 0):.6f}, "
              f"r_Ω={res.get('r_Ω', 0):.6f}")
        print(f"  p(U)={res.get('p(U)', 0):.3f}, E_dir={res.get('E_dir', 0):.4f}")
        if 'mean_κ_graph' in res:
            print(f"  Graph curvature: mean_κ={res.get('mean_κ_graph', 0):.4f}")
    
    if result.theorem.spectral_info:
        spec = result.theorem.spectral_info
        print(f"\n--- Spectral ---")
        print(f"  λ₁={spec.lambda_1:.4f}, λ_max={spec.lambda_max:.4f}, "
              f"components={spec.num_components}")
        if not math.isnan(spec.spectral_dimension):
            print(f"  d_s={spec.spectral_dimension:.2f}")
    
    if result.theorem.curvature_info:
        curv = result.theorem.curvature_info
        print(f"\n--- Curvature (Forman-Ricci) ---")
        print(f"  mean={curv.mean_curvature:.4f}, min={curv.min_curvature:.4f}, "
              f"max={curv.max_curvature:.4f}")
        print(f"  κ>0: {curv.num_positive} edges, κ<0: {curv.num_negative} edges")
    
    print(f"\n--- Rewrites ---")
    rp = result.rewrite_proposals
    print(f"  Add: {rp['add'][:3]}{'...' if len(rp['add']) > 3 else ''}")
    print(f"  Del: {rp['del'][:3]}{'...' if len(rp['del']) > 3 else ''}")
    
    print("=" * 70)


# =============================================================================
# §12. MAIN
# =============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("NDP Config-Driven Architecture Test")
    print("=" * 70)
    
    # Test both modes
    for preset in ["production", "research"]:
        print(f"\n{'='*30} {preset.upper()} {'='*30}\n")
        
        torch.manual_seed(42)
        worlds, alpha = init_worlds(S=6, N=100, d=32, E=400)
        
        model = NDP.from_preset(preset, d=32, S=6, K=6)
        result = model(worlds, alpha)
        
        print_result(result)
