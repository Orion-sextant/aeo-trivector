"""
ndp_unified_struct.py
====================
Unified, production-lean NDP core that merges the *structure* implied by your Perplexity red-team
("sparse Laplacian + fast spectral operators + invariance tests") with your existing NDP Superposed Web v2
(operator modularity + ICF validator + Boltzmann amplitude collapse).

Key changes vs your current v2:
- Sparse Laplacian (O(E) memory) + sparse matmul apply
- Chebyshev + Polynomial operators implemented on *signals* (no NxN operator matrices)
- Heat kernel via Chebyshev approximation of exp(-tL) (no O(N^3) matrix exponential)
- Shared edge symmetrization/coalescing utilities to prevent circular imports

Requires: torch>=2.0
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


# ---------------------------------------------------------------------
# Tri-logic encoding
# ---------------------------------------------------------------------
T, FLS, U = 0, 1, 2


# ---------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------
@dataclass
class WorldState:
    """One candidate world W_s."""
    h: torch.Tensor          # [N, d]
    edge_index: torch.Tensor # [2, E]
    t: torch.Tensor          # [N] in {T, FLS, U}


# ---------------------------------------------------------------------
# Graph utilities
# ---------------------------------------------------------------------
def _coalesce_edge_index(edge_index: torch.Tensor, num_nodes: int) -> torch.Tensor:
    """
    Remove self-loops and duplicate edges (COO-style coalescing via hashing).
    Assumes 0 <= node < num_nodes.
    """
    src, dst = edge_index
    # drop self loops
    mask = src != dst
    src, dst = src[mask], dst[mask]
    key = src * num_nodes + dst
    uniq = torch.unique(key)
    src = uniq // num_nodes
    dst = uniq % num_nodes
    return torch.stack([src, dst], dim=0)


def symmetrize_edge_index(edge_index: torch.Tensor, num_nodes: int) -> torch.Tensor:
    """Make edges undirected by adding reverse edges, then coalescing."""
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
    Build sparse (COO) Laplacian.

    Unnormalized: L = D - A
    Symmetric normalized: L = I - D^{-1/2} A D^{-1/2}

    Returns:
      L: torch.sparse_coo_tensor [N,N]
      deg: dense degree vector [N]
    """
    device = device or edge_index.device
    ei = symmetrize_edge_index(edge_index.to(device), num_nodes)
    src, dst = ei[0], ei[1]
    vals = torch.ones(src.numel(), device=device, dtype=dtype)

    # degree from outgoing (symmetric => undirected degree)
    deg = torch.zeros(num_nodes, device=device, dtype=dtype)
    deg.index_add_(0, src, vals)

    if normalized:
        deg_inv_sqrt = torch.where(deg > 0, deg.pow(-0.5), torch.zeros_like(deg))
        off_vals = -deg_inv_sqrt[src] * deg_inv_sqrt[dst]
        # L = I + off-diagonals (negative)
        diag_idx = torch.arange(num_nodes, device=device)
        idx = torch.cat(
            [torch.stack([diag_idx, diag_idx], dim=0), torch.stack([src, dst], dim=0)],
            dim=1,
        )
        v = torch.cat([torch.ones(num_nodes, device=device, dtype=dtype), off_vals], dim=0)
    else:
        # L = D - A  => diag=deg, off=-1 on edges
        diag_idx = torch.arange(num_nodes, device=device)
        idx = torch.cat(
            [torch.stack([diag_idx, diag_idx], dim=0), torch.stack([src, dst], dim=0)],
            dim=1,
        )
        v = torch.cat([deg, -vals], dim=0)

    L = torch.sparse_coo_tensor(idx, v, size=(num_nodes, num_nodes), device=device, dtype=dtype).coalesce()
    return L, deg


def spmm(L: torch.Tensor, x: torch.Tensor) -> torch.Tensor:
    """Sparse matrix multiply: (N,N) @ (N,d) -> (N,d)."""
    if not L.is_sparse:
        return L @ x
    return torch.sparse.mm(L, x)


def dirichlet_energy(h: torch.Tensor, L: torch.Tensor) -> torch.Tensor:
    """
    E(h) = <h, L h> / N
    For normalized Laplacian this is well-conditioned (λ in [0,2]).
    """
    Lh = spmm(L, h)
    return torch.sum(h * Lh) / h.size(0)


def estimate_lambda_max(L: torch.Tensor, num_iter: int = 30, eps: float = 1e-12) -> float:
    """
    Power-iteration estimate of largest eigenvalue of symmetric PSD L.
    For normalized Laplacian you can just use 2.0, but this is useful if unnormalized.
    """
    N = L.size(0)
    v = torch.randn(N, 1, device=L.device, dtype=torch.float32)
    v = v / (v.norm() + eps)
    for _ in range(num_iter):
        w = spmm(L, v)
        n = w.norm() + eps
        v = w / n
    # Rayleigh quotient
    Lv = spmm(L, v)
    lam = float((v.T @ Lv).item())
    return max(lam, 1e-6)


# ---------------------------------------------------------------------
# Spectral operator base
# ---------------------------------------------------------------------
class SpectralOperator(nn.Module):
    def forward(
        self,
        h: torch.Tensor,           # [N,d]
        L: torch.Tensor,           # sparse [N,N]
        tri_labels: torch.Tensor,  # [N]
        lambda_max: Optional[float] = None,
    ) -> Tuple[torch.Tensor, Dict[str, Any]]:
        raise NotImplementedError


class PolynomialOperator(SpectralOperator):
    """
    Apply g(L)h with g a learnable polynomial:
      g(L)h = Σ_{k=0..K} c_k L^k h
    Implemented via repeated sparse matmul on signals (no NxN operator construction).
    """
    def __init__(self, d: int, poly_degree: int = 3):
        super().__init__()
        self.poly_degree = poly_degree
        self.coeffs = nn.Parameter(torch.zeros(poly_degree + 1))
        self.corr = nn.Sequential(
            nn.Linear(d, d),
            nn.GELU(),
            nn.Linear(d, d),
        )

    def forward(self, h: torch.Tensor, L: torch.Tensor, tri_labels: torch.Tensor, lambda_max: Optional[float] = None):
        out = self.coeffs[0] * h
        hk = h
        for k in range(1, self.poly_degree + 1):
            hk = spmm(L, hk)
            out = out + self.coeffs[k] * hk

        # Tri-logic gate (A2: undefined evolves slower)
        gate = torch.ones(h.size(0), device=h.device, dtype=h.dtype)
        gate[tri_labels == U] = 0.6
        out = out * gate.unsqueeze(-1)

        h_new = out + self.corr(h)
        info = {f"poly_c{k}": float(self.coeffs[k].detach().cpu()) for k in range(self.poly_degree + 1)}
        return h_new, info


class ChebyshevOperator(SpectralOperator):
    """
    Chebyshev approximation g(L)h ≈ Σ θ_k T_k(L~) h
    implemented on signals via recurrence, with L~ = 2L/λ_max - I.
    """
    def __init__(self, d: int, K: int = 3):
        super().__init__()
        self.K = K
        self.theta = nn.Parameter(torch.zeros(K + 1))
        self.corr = nn.Sequential(
            nn.Linear(d, d),
            nn.GELU(),
            nn.Linear(d, d),
        )

    def forward(self, h: torch.Tensor, L: torch.Tensor, tri_labels: torch.Tensor, lambda_max: Optional[float] = None):
        if lambda_max is None:
            lambda_max = 2.0  # normalized Laplacian safe default

        def L_tilde_apply(x: torch.Tensor) -> torch.Tensor:
            return (2.0 / lambda_max) * spmm(L, x) - x

        t0 = h
        out = self.theta[0] * t0
        if self.K >= 1:
            t1 = L_tilde_apply(h)
            out = out + self.theta[1] * t1
        else:
            t1 = None

        for k in range(2, self.K + 1):
            assert t1 is not None
            t2 = 2.0 * L_tilde_apply(t1) - t0
            out = out + self.theta[k] * t2
            t0, t1 = t1, t2

        gate = torch.ones(h.size(0), device=h.device, dtype=h.dtype)
        gate[tri_labels == U] = 0.6
        out = out * gate.unsqueeze(-1)

        h_new = out + self.corr(h)
        info = {f"cheb_theta{k}": float(self.theta[k].detach().cpu()) for k in range(self.K + 1)}
        info["lambda_max"] = float(lambda_max)
        return h_new, info


def _cheb_coeffs_exp(
    t: float,
    K: int,
    lambda_max: float,
    *,
    M: int = 512,
    device: torch.device,
    dtype: torch.dtype,
) -> torch.Tensor:
    """
    Compute Chebyshev coefficients for f(λ)=exp(-t λ) on [0, λ_max],
    using discrete orthogonality on Chebyshev nodes.

    Returns a: [K+1], where f(L)h ≈ Σ a_k T_k(L~)h, with L~ = 2L/λ_max - I.
    """
    # Chebyshev nodes on [-1,1]: x_j = cos(theta_j), theta_j = pi*(j+0.5)/M
    j = torch.arange(M, device=device, dtype=dtype)
    theta = math.pi * (j + 0.5) / M
    x = torch.cos(theta)  # in [-1,1]
    lam = 0.5 * lambda_max * (x + 1.0)  # map to [0,lambda_max]
    f = torch.exp(-t * lam)             # f(lam)
    # a_k = 2/M Σ f_j cos(k theta_j), with a_0 = 1/M Σ f_j
    a = []
    for k in range(K + 1):
        ck = torch.cos(k * theta)
        ak = (2.0 / M) * torch.sum(f * ck)
        a.append(ak)
    a = torch.stack(a, dim=0)
    a[0] = a[0] * 0.5  # adjust a0
    return a


class HeatKernelOperator(SpectralOperator):
    """
    Apply exp(-t L) h using a Chebyshev approximation (fast, sparse, differentiable w.r.t h).

    Notes:
    - For normalized Laplacian, lambda_max <= 2 and the scaling is stable.
    - If you want t learnable, make it an nn.Parameter (kept fixed here for simplicity).
    """
    def __init__(self, d: int, t: float = 1.0, K: int = 12):
        super().__init__()
        self.t = t
        self.K = K
        self.corr = nn.Sequential(
            nn.Linear(d, d),
            nn.GELU(),
            nn.Linear(d, d),
        )

    def forward(self, h: torch.Tensor, L: torch.Tensor, tri_labels: torch.Tensor, lambda_max: Optional[float] = None):
        if lambda_max is None:
            lambda_max = 2.0

        a = _cheb_coeffs_exp(self.t, self.K, float(lambda_max), device=h.device, dtype=h.dtype)

        def L_tilde_apply(x: torch.Tensor) -> torch.Tensor:
            return (2.0 / lambda_max) * spmm(L, x) - x

        # Chebyshev recurrence on signals
        t0 = h
        out = a[0] * t0
        if self.K >= 1:
            t1 = L_tilde_apply(h)
            out = out + a[1] * t1
        else:
            t1 = None

        for k in range(2, self.K + 1):
            assert t1 is not None
            t2 = 2.0 * L_tilde_apply(t1) - t0
            out = out + a[k] * t2
            t0, t1 = t1, t2

        gate = torch.ones(h.size(0), device=h.device, dtype=h.dtype)
        gate[tri_labels == U] = 0.6
        out = out * gate.unsqueeze(-1)

        h_new = out + self.corr(h)
        info = {"heat_t": float(self.t), "heat_K": int(self.K), "lambda_max": float(lambda_max)}
        return h_new, info


# ---------------------------------------------------------------------
# Validator (ICF constraints) — adapted from ndp_superposed_v2 but with sparse L
# ---------------------------------------------------------------------
class ICFValidator(nn.Module):
    """
    Validator using internal-consistent constraint system (C1-C5) + A2 + coherence.
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

    def forward(self, world: WorldState, L: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, Dict[str, float]]:
        device = world.h.device
        mu = torch.tensor(self.mu, device=device, dtype=world.h.dtype)

        if L is None:
            L, _ = build_sparse_laplacian(world.edge_index, world.h.size(0), normalized=False, device=device, dtype=world.h.dtype)

        # C1: κ = μ²/10
        kappa = mu**2 / 10.0

        # C4: β = ((1-μ)² + μ·κ) / (1 - κ/3)
        beta = ((1.0 - mu) ** 2 + mu * kappa) / (1.0 - kappa / 3.0)

        # C5: μ² + Ω² - β² = 1 → Ω = √(1 - μ² + β²)
        omega = torch.sqrt(torch.clamp(1.0 - mu**2 + beta**2, min=0.0))

        r_kappa = kappa - torch.tensor(self.kappa_target, device=device, dtype=world.h.dtype)
        r_beta = beta - torch.tensor(self.beta_target, device=device, dtype=world.h.dtype)
        r_omega = omega - torch.tensor(self.omega_target, device=device, dtype=world.h.dtype)

        p_undef = (world.t == U).float().mean()
        pen_undef = F.relu(torch.tensor(self.beta_target, device=device, dtype=world.h.dtype) - p_undef)

        E_dir = dirichlet_energy(world.h, L)

        energy = (
            self.lambda_inv * (r_kappa**2 + r_beta**2 + r_omega**2)
            + self.lambda_U * pen_undef
            + self.lambda_coh * E_dir
        )

        residuals = {
            "r_kappa": float(r_kappa.detach().cpu()),
            "r_beta": float(r_beta.detach().cpu()),
            "r_omega": float(r_omega.detach().cpu()),
            "p_undef": float(p_undef.detach().cpu()),
            "kappa": float(kappa.detach().cpu()),
            "beta": float(beta.detach().cpu()),
            "omega": float(omega.detach().cpu()),
            "dirichlet_energy": float(E_dir.detach().cpu()),
        }
        return energy, residuals


# ---------------------------------------------------------------------
# Rewrite proposer (kept simple; dense similarity can be replaced later)
# ---------------------------------------------------------------------
class RewriteProposer(nn.Module):
    """
    Proposes graph edits based on embedding similarity.
    NOTE: This is O(N^2) for similarity — keep N small or replace with ANN later.
    """
    def __init__(self, max_add: int = 5, max_del: int = 5):
        super().__init__()
        self.max_add = max_add
        self.max_del = max_del

    @torch.no_grad()
    def forward(self, world: WorldState) -> Dict[str, List[Tuple[int, int]]]:
        h = world.h
        N = h.size(0)

        h_norm = F.normalize(h, dim=-1)
        sim = h_norm @ h_norm.T  # O(N^2)

        ei = symmetrize_edge_index(world.edge_index, N)
        src, dst = ei
        existing = set((int(s), int(d)) for s, d in zip(src.tolist(), dst.tolist()))

        sim_fill = sim.clone()
        sim_fill.fill_diagonal_(-1e9)
        for (s, d) in list(existing)[: min(len(existing), 5000)]:
            sim_fill[s, d] = -1e9

        flat = sim_fill.view(-1)
        topk = torch.topk(flat, k=min(self.max_add, flat.numel())).indices.tolist()
        adds: List[Tuple[int, int]] = []
        for idx in topk:
            u = idx // N
            v = idx % N
            if u != v and (u, v) not in existing:
                adds.append((int(u), int(v)))

        edge_scores = []
        for (s, d) in existing:
            if s != d:
                edge_scores.append((float(sim[s, d].cpu()), s, d))
        edge_scores.sort(key=lambda x: x[0])
        dels = [(s, d) for _, s, d in edge_scores[: self.max_del]]

        return {"add_edges": adds, "del_edges": dels}


# ---------------------------------------------------------------------
# NDP Superposed Web (unified, sparse)
# ---------------------------------------------------------------------
class NDP_SuperposedWeb_Unified(nn.Module):
    """
    Superposition bundle evolution:
      1) Operator evolution (poly/heat/cheb)
      2) Validation energy (ICF)
      3) Boltzmann amplitude update
      4) Collapse after K steps
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

        if operator_type == "polynomial":
            self.operator: SpectralOperator = PolynomialOperator(d=d, poly_degree=poly_degree)
        elif operator_type == "heat":
            self.operator = HeatKernelOperator(d=d, t=1.0, K=max(8, poly_degree * 4))
        elif operator_type == "chebyshev":
            self.operator = ChebyshevOperator(d=d, K=poly_degree)
        else:
            raise ValueError(f"Unknown operator type: {operator_type}")
        self.operator_type = operator_type

        self.validator = ICFValidator()
        self.rewriter = RewriteProposer(max_add=6, max_del=4)

    def get_tau(self, step: int) -> float:
        progress = step / max(self.K - 1, 1)
        return self.tau_init + (self.tau_final - self.tau_init) * progress

    def amplitude_update(self, alpha: torch.Tensor, energies: torch.Tensor, step: int) -> torch.Tensor:
        tau = self.get_tau(step)
        alpha = alpha * torch.exp(-tau * energies)
        alpha = alpha / (alpha.sum() + 1e-9)
        return alpha

    def forward(self, worlds: List[WorldState], alpha: torch.Tensor) -> Dict[str, Any]:
        logs: List[Dict[str, Any]] = []

        for step in range(self.K):
            tau = self.get_tau(step)

            energies = []
            residuals_list = []
            op_infos = []

            for s, world in enumerate(worlds):
                N = world.h.size(0)

                L, _ = build_sparse_laplacian(
                    world.edge_index, N,
                    normalized=self.use_normalized_laplacian,
                    device=world.h.device,
                    dtype=world.h.dtype,
                )

                # lambda_max: known bound if normalized; otherwise estimate
                lambda_max = 2.0 if self.use_normalized_laplacian else estimate_lambda_max(L)

                h_new, info = self.operator(world.h, L, world.t, lambda_max=lambda_max)
                worlds[s] = WorldState(h=h_new, edge_index=world.edge_index, t=world.t)

                E, residuals = self.validator(worlds[s], L=L)
                energies.append(E)
                residuals_list.append(residuals)
                op_infos.append(info)

            energies_t = torch.stack(energies, dim=0)  # [S]
            alpha = self.amplitude_update(alpha, energies_t.detach(), step)  # keep stable

            logs.append({
                "step": step,
                "tau": tau,
                "energies": [float(e.detach().cpu()) for e in energies_t],
                "alpha": [float(a) for a in alpha.detach().cpu().tolist()],
                "residuals": residuals_list,
                "op_info": op_infos,
            })

        collapsed_index = int(torch.argmax(alpha).item())
        rewrite_proposals = self.rewriter(worlds[collapsed_index])

        return {
            "operator_type": self.operator_type,
            "logs": logs,
            "collapsed_index": collapsed_index,
            "final_alpha": alpha.detach().cpu().tolist(),
            "rewrite_proposals": rewrite_proposals,
        }


# ---------------------------------------------------------------------
# Minimal init helpers
# ---------------------------------------------------------------------
def init_worlds(
    S: int,
    N: int,
    d: int,
    E: int,
    *,
    device: str = "cpu",
    p_undef: float = 0.25,
) -> Tuple[List[WorldState], torch.Tensor]:
    """
    Create S random worlds for smoke-testing.
    """
    device_t = torch.device(device)
    worlds: List[WorldState] = []
    for _ in range(S):
        h = torch.randn(N, d, device=device_t)
        src = torch.randint(0, N, (E,), device=device_t)
        dst = torch.randint(0, N, (E,), device=device_t)
        edge_index = torch.stack([src, dst], dim=0)

        # tri-labels
        t = torch.full((N,), U, device=device_t, dtype=torch.long)
        n_true = int(0.5 * (1.0 - p_undef) * N)
        n_false = int(0.5 * (1.0 - p_undef) * N)
        perm = torch.randperm(N, device=device_t)
        t[perm[:n_true]] = T
        t[perm[n_true:n_true + n_false]] = FLS

        worlds.append(WorldState(h=h, edge_index=edge_index, t=t))

    alpha = torch.ones(S, device=device_t) / S
    return worlds, alpha


if __name__ == "__main__":
    # Quick smoke-test
    torch.manual_seed(0)
    worlds, alpha = init_worlds(S=6, N=64, d=32, E=256, device="cpu")
    model = NDP_SuperposedWeb_Unified(d=32, S=6, K=4, operator_type="chebyshev", poly_degree=4)
    out = model(worlds, alpha)
    print("Collapsed world:", out["collapsed_index"])
    print("Rewrite proposal sample:", out["rewrite_proposals"])
