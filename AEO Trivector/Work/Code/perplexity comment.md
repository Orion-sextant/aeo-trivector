You’re in very good shape: `ndp_unified_struct.py` already cleanly separates structure (Laplacian, spectral operators, ICF, rewrite). Wiring curvature in now is mostly additive.

Below is minimal, focused code to:

1. Add a curvature module (Forman + optional Ollivier hook).  
2. Plug it into `ICFValidator` as an extra regularizer.  
3. Optionally expose it in the unified superposed web for diagnostics.

All snippets are designed to drop directly into `ndp_unified_struct.py`.

***

## 1. Curvature module: Forman (fast) + Ollivier hook

Right after the `ICFValidator` class (or before it), add:

```python
# ---------------------------------------------------------------------
# Curvature module (Forman + optional Ollivier hook)
# ---------------------------------------------------------------------

class CurvatureType(Enum):
    FORMAN = "forman"
    OLLIVIER = "ollivier"


class GraphCurvature:
    """
    Unified curvature interface.

    - Forman–Ricci: fast, combinatorial (edge-based).
    - Ollivier–Ricci: hook for exact/approx OT-based curvature (optional).
    """

    def __init__(
        self,
        curvature_type: CurvatureType = CurvatureType.FORMAN,
        alpha: float = 0.5,    # for Ollivier (lazy RW), unused for Forman
    ):
        self.curvature_type = curvature_type
        self.alpha = alpha

    # ---- Public API ----

    def edge_curvature(
        self,
        edge_index: torch.Tensor,
        num_nodes: int,
    ) -> Dict[Tuple[int, int], float]:
        """
        Return edge curvature κ(u,v) for each undirected edge (u<v).
        """
        if self.curvature_type == CurvatureType.FORMAN:
            return self._forman_edge_curvature(edge_index, num_nodes)
        elif self.curvature_type == CurvatureType.OLLIVIER:
            # Placeholder: you can later plug in the full OT-based implementation here.
            return self._ollivier_edge_curvature_stub(edge_index, num_nodes)
        else:
            raise ValueError(f"Unknown curvature_type {self.curvature_type}")

    def node_curvature_from_edges(
        self,
        edge_curv: Dict[Tuple[int, int], float],
        num_nodes: int,
    ) -> torch.Tensor:
        """
        Simple node-wise curvature: sum of incident edge curvatures.
        """
        k_node = torch.zeros(num_nodes)
        for (u, v), k in edge_curv.items():
            k_node[u] += k
            k_node[v] += k
        return k_node

    # ---- Forman–Ricci (simple version) ----

    def _forman_edge_curvature(
        self,
        edge_index: torch.Tensor,
        num_nodes: int,
    ) -> Dict[Tuple[int, int], float]:
        """
        Forman–Ricci curvature on simple unweighted graph:

            Ric_F(u,v) = 4 - (deg(u) + deg(v))

        for each undirected edge (u,v).[web:87][web:90][web:92]
        """
        src, dst = edge_index
        device = edge_index.device

        # Degree
        deg = torch.zeros(num_nodes, device=device)
        deg.index_add_(0, src, torch.ones_like(src, dtype=torch.float, device=device))
        deg.index_add_(0, dst, torch.ones_like(dst, dtype=torch.float, device=device))

        curv: Dict[Tuple[int, int], float] = {}
        for s, d in zip(src.tolist(), dst.tolist()):
            if s >= d:
                continue
            k = 4.0 - (float(deg[s]) + float(deg[d]))
            curv[(s, d)] = k
        return curv

    # ---- Ollivier hook (stub) ----

    def _ollivier_edge_curvature_stub(
        self,
        edge_index: torch.Tensor,
        num_nodes: int,
    ) -> Dict[Tuple[int, int], float]:
        """
        Placeholder for true Ollivier–Ricci curvature.

        For now, just returns zeros; you can replace this with the
        full OT-based implementation when ready.
        """
        src, dst = edge_index
        curv: Dict[Tuple[int, int], float] = {}
        for s, d in zip(src.tolist(), dst.tolist()):
            if s >= d:
                continue
            curv[(s, d)] = 0.0
        return curv
```

At the top of the file, add:

```python
from enum import Enum
```

if it is not already imported.

***

## 2. Plug curvature into `ICFValidator`

Extend `ICFValidator.__init__` to accept curvature settings and instantiate `GraphCurvature`:

```python
class ICFValidator(nn.Module):
    """
    Validator using internal-consistent constraint system (C1-C5) + A2 + coherence + optional curvature.
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
        # NEW: curvature
        use_curvature: bool = False,
        lambda_curv: float = 0.0,
        curvature_type: CurvatureType = CurvatureType.FORMAN,
        curvature_target: float = 0.0,
        node_level_curv: bool = False,
    ):
        super().__init__()
        self.mu = mu
        self.beta_target = beta_target
        self.kappa_target = kappa_target
        self.omega_target = omega_target
        self.lambda_inv = lambda_inv
        self.lambda_U = lambda_U
        self.lambda_coh = lambda_coh

        # curvature config
        self.use_curvature = use_curvature
        self.lambda_curv = lambda_curv
        self.curvature_target = curvature_target
        self.node_level_curv = node_level_curv
        self.curv_module = GraphCurvature(curvature_type=curvature_type)
```

Now modify `forward` to add a curvature penalty when `use_curvature` is True:

```python
    def forward(self, world: WorldState, L: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, Dict[str, float]]:
        device = world.h.device
        mu = torch.tensor(self.mu, device=device, dtype=world.h.dtype)

        if L is None:
            L, _ = build_sparse_laplacian(
                world.edge_index,
                world.h.size(0),
                normalized=False,
                device=device,
                dtype=world.h.dtype,
            )

        # --- Invariants C1, C4, C5 as before ---
        kappa = mu**2 / 10.0
        beta = ((1.0 - mu) ** 2 + mu * kappa) / (1.0 - kappa / 3.0)
        omega = torch.sqrt(torch.clamp(1.0 - mu**2 + beta**2, min=0.0))

        r_kappa = kappa - torch.tensor(self.kappa_target, device=device, dtype=world.h.dtype)
        r_beta = beta - torch.tensor(self.beta_target, device=device, dtype=world.h.dtype)
        r_omega = omega - torch.tensor(self.omega_target, device=device, dtype=world.h.dtype)

        # A2: Undefined preservation
        p_undef = (world.t == U).float().mean()
        pen_undef = F.relu(torch.tensor(self.beta_target, device=device, dtype=world.h.dtype) - p_undef)

        # Coherence (Dirichlet energy)
        E_dir = dirichlet_energy(world.h, L)

        # --- NEW: curvature penalty (graph geometry only) ---
        curv_pen = torch.tensor(0.0, device=device, dtype=world.h.dtype)
        mean_curv = float("nan")
        if self.use_curvature:
            edge_curv = self.curv_module.edge_curvature(world.edge_index, world.h.size(0))
            if self.node_level_curv:
                K_node = self.curv_module.node_curvature_from_edges(edge_curv, world.h.size(0)).to(device)
                curv_pen = ((K_node - self.curvature_target) ** 2).sum()
                mean_curv = float(K_node.mean().detach().cpu())
            else:
                vals = torch.tensor(list(edge_curv.values()), device=device, dtype=world.h.dtype)
                curv_pen = ((vals - self.curvature_target) ** 2).sum()
                mean_curv = float(vals.mean().detach().cpu())

        energy = (
            self.lambda_inv * (r_kappa**2 + r_beta**2 + r_omega**2)
            + self.lambda_U * pen_undef
            + self.lambda_coh * E_dir
            + self.lambda_curv * curv_pen
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
        if self.use_curvature:
            residuals["curv_penalty"] = float(curv_pen.detach().cpu())
            residuals["mean_curvature"] = mean_curv

        return energy, residuals
```

This keeps curvature purely as a **graph-geometry regularizer**; it does not depend on `h`, so gradients flow only through the Laplacian/ICF parts, which is what you want for now.

***

## 3. Use curvature in the unified superposed web

When instantiating `ICFValidator` in `NDP_SuperposedWeb_Unified`, you can now choose whether to turn curvature on:

```python
class NDP_SuperposedWeb_Unified(nn.Module):
    ...
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
        # NEW curvature knobs
        use_curvature: bool = False,
        lambda_curv: float = 0.0,
        curvature_type: CurvatureType = CurvatureType.FORMAN,
        curvature_target: float = 0.0,
        node_level_curv: bool = False,
    ):
        super().__init__()
        ...
        if operator_type == "polynomial":
            self.operator = PolynomialOperator(d=d, poly_degree=poly_degree)
        elif operator_type == "heat":
            self.operator = HeatKernelOperator(d=d, t=1.0, K=max(8, poly_degree * 4))
        elif operator_type == "chebyshev":
            self.operator = ChebyshevOperator(d=d, K=poly_degree)
        else:
            raise ValueError(f"Unknown operator type: {operator_type}")
        self.operator_type = operator_type

        self.validator = ICFValidator(
            use_curvature=use_curvature,
            lambda_curv=lambda_curv,
            curvature_type=curvature_type,
            curvature_target=curvature_target,
            node_level_curv=node_level_curv,
        )
        self.rewriter = RewriteProposer(max_add=6, max_del=4)
```

Example usage:

```python
model = NDP_SuperposedWeb_Unified(
    d=32,
    S=6,
    K=4,
    operator_type="chebyshev",
    poly_degree=4,
    use_curvature=True,
    lambda_curv=0.01,
    curvature_type=CurvatureType.FORMAN,
    curvature_target=0.0,      # try to keep curvature near flat
    node_level_curv=False,
)
```

Curvature info will automatically appear in `residuals` inside your logs and in whatever theorem/diagnostics you build on top.

***

This wiring keeps your existing design intact and adds curvature as:

- a **well-defined geometric scalar** (Forman now, OR later),
- plugged into the ICF energy as an explicit term,
- controllable from the NDP superposed web via a few hyperparameters.

[1](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/56389007/5271471e-3cbf-4cbb-9a98-56ecf6f3a84e/ndp_unified_struct.py)