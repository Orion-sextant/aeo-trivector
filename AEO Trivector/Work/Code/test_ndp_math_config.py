"""test_ndp_math_config.py

Validation tests adapted from the Perplexity symmetry/correctness checklist,
implemented against the config-driven NDP in ndp_config.py.

Run:
  pytest -q

Covers:
- Permutation equivariance (operator-level)
- Rotation invariance (Dirichlet energy)
- Discrete calculus consistency: Lh == -div(grad(h)) for unnormalized Laplacian
- Spectral sanity: heat kernel Chebyshev approximation ~ exact exp(-tL) on small graphs
- Curvature sanity: Forman curvature homogeneous on a clique

These are deliberately small-N (fast) and aim to catch regressions.
"""

from __future__ import annotations

import math
import torch

from ndp_config import (
    T, FLS, U,
    NDPConfig,
    PolynomialOperator,
    HeatKernelOperator,
    GraphCurvature,
    CurvatureType,
    build_sparse_laplacian,
    dirichlet_energy,
)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _make_path_graph(N: int, device=None):
    src = torch.arange(N - 1, device=device)
    dst = src + 1
    return torch.stack([src, dst], dim=0)


def _permute_problem(edge_index: torch.Tensor, h: torch.Tensor, tri: torch.Tensor):
    """Reorder nodes by perm; return (edge_index_perm, h_perm, tri_perm, perm)."""
    N = h.size(0)
    device = h.device
    perm = torch.randperm(N, device=device)
    invperm = torch.empty_like(perm)
    invperm[perm] = torch.arange(N, device=device)

    h_perm = h[perm]
    tri_perm = tri[perm]
    edge_index_perm = invperm[edge_index]
    return edge_index_perm, h_perm, tri_perm, perm


def _grad_div_laplacian(h: torch.Tensor, edge_index: torch.Tensor, num_nodes: int) -> torch.Tensor:
    """Compute Lh via the identity Lh = -div(grad(h)) for the *unnormalized* Laplacian.

    For an undirected graph, we treat each undirected edge (u,v) as contributing:
      to u: (h_u - h_v)
      to v: (h_v - h_u)
    which equals (D - A)h.

    This avoids explicit sparse-matmul and is a good sanity check for Laplacian construction.
    """
    src, dst = edge_index
    out = torch.zeros((num_nodes, h.size(1)), device=h.device, dtype=h.dtype)

    diff = h[src] - h[dst]
    out.index_add_(0, src, diff)
    out.index_add_(0, dst, -diff)
    return out


def _exact_heat_dense(h: torch.Tensor, L_sparse: torch.Tensor, t: float) -> torch.Tensor:
    """Exact exp(-tL)h using dense eigendecomposition (small graphs only)."""
    N = h.size(0)
    L = L_sparse.to_dense()
    # Ensure symmetry (numerical hygiene)
    L = 0.5 * (L + L.T)
    evals, evecs = torch.linalg.eigh(L)
    g = torch.exp(-t * evals)
    # evecs @ diag(g) @ evecs^T @ h
    return evecs @ (g.unsqueeze(1) * (evecs.T @ h))


def _zero_module_params(module: torch.nn.Module) -> None:
    for p in module.parameters(recurse=True):
        p.data.zero_()


# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------

def test_dirichlet_energy_rotation_invariance():
    torch.manual_seed(0)
    device = torch.device("cpu")
    N, d = 16, 6

    edge_index = _make_path_graph(N, device=device)
    L, _ = build_sparse_laplacian(edge_index, N, normalized=False, device=device)

    h = torch.randn(N, d, device=device)

    A = torch.randn(d, d, device=device)
    Q, _ = torch.linalg.qr(A)
    h_rot = h @ Q

    E0 = dirichlet_energy(h, L)
    E1 = dirichlet_energy(h_rot, L)

    err = float((E0 - E1).abs().item())
    assert err < 1e-6, f"Dirichlet energy not rotation-invariant: {err}"


def test_laplacian_equals_grad_div_identity():
    torch.manual_seed(1)
    device = torch.device("cpu")
    N, d = 20, 5

    # Random sparse graph, then symmetrize via Laplacian builder
    E = 60
    src = torch.randint(0, N, (E,), device=device)
    dst = torch.randint(0, N, (E,), device=device)
    edge_index = torch.stack([src, dst], dim=0)

    h = torch.randn(N, d, device=device)

    L, _ = build_sparse_laplacian(edge_index, N, normalized=False, device=device)
    Lh_sparse = torch.sparse.mm(L, h)

    # IMPORTANT: the grad/div identity expects an *undirected* edge set.
    # We reconstruct an undirected edge list from L's indices to ensure symmetry.
    ii = L.indices()
    mask_offdiag = ii[0] != ii[1]
    undirected_edges = ii[:, mask_offdiag]

    # undirected_edges here includes both (u,v) and (v,u). That's okay: our formula
    # uses each pair once if passed as an undirected list. So we coalesce by forcing u<v.
    u, v = undirected_edges
    lo = torch.minimum(u, v)
    hi = torch.maximum(u, v)
    e = torch.stack([lo, hi], dim=0)
    e = torch.unique(e, dim=1)

    Lh_gd = _grad_div_laplacian(h, e, N)

    err = torch.norm(Lh_sparse - Lh_gd).item() / (torch.norm(Lh_sparse).item() + 1e-9)
    assert err < 1e-6, f"Lh != -div(grad(h)) relerr={err}"


def test_operator_permutation_equivariance_polynomial():
    torch.manual_seed(2)
    device = torch.device("cpu")
    N, d = 12, 4

    edge_index = _make_path_graph(N, device=device)
    h = torch.randn(N, d, device=device)
    tri = torch.randint(0, 3, (N,), device=device)

    cfg = NDPConfig(d=d, operator_type="polynomial", poly_degree=3, use_normalized_laplacian=True)
    op = PolynomialOperator(cfg)

    # Permute
    edge_p, h_p, tri_p, perm = _permute_problem(edge_index, h, tri)

    L, _ = build_sparse_laplacian(edge_index, N, normalized=True, device=device)
    Lp, _ = build_sparse_laplacian(edge_p, N, normalized=True, device=device)

    out, _ = op(h, L, tri, lambda_max=2.0)
    out_p, _ = op(h_p, Lp, tri_p, lambda_max=2.0)

    err = torch.norm(out_p - out[perm]).item()
    assert err < 1e-5, f"Polynomial operator not permutation-equivariant, err={err}"


def test_heat_kernel_chebyshev_matches_exact_small_graph():
    torch.manual_seed(3)
    device = torch.device("cpu")

    N, d = 14, 3
    edge_index = _make_path_graph(N, device=device)
    L, _ = build_sparse_laplacian(edge_index, N, normalized=True, device=device)

    h = torch.randn(N, d, device=device)
    tri = torch.full((N,), T, dtype=torch.long, device=device)

    # Chebyshev approximation params
    t = 0.7
    K = 40
    cfg = NDPConfig(d=d, operator_type="heat", heat_t=t, heat_K=K, use_normalized_laplacian=True)
    op = HeatKernelOperator(cfg)

    # Make the correction term identically zero so we're testing the spectral filter
    _zero_module_params(op.corr)

    approx, _ = op(h, L, tri, lambda_max=2.0)
    exact = _exact_heat_dense(h, L, t)

    relerr = torch.norm(approx - exact).item() / (torch.norm(exact).item() + 1e-9)
    assert relerr < 2e-3, f"Heat Chebyshev approx too far from exact: relerr={relerr}"


def test_forman_curvature_homogeneous_on_clique():
    device = torch.device("cpu")
    frc = GraphCurvature(curvature_type=CurvatureType.FORMAN)

    N = 6
    src, dst = [], []
    for i in range(N):
        for j in range(i + 1, N):
            src.append(i)
            dst.append(j)
    edge_index = torch.tensor([src, dst], device=device)

    curv = frc.edge_curvature(edge_index, N)
    vals = torch.tensor(list(curv.values()), device=device)

    assert float((vals - vals.mean()).abs().max().item()) < 1e-6
