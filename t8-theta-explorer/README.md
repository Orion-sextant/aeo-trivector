# T⁸_Θ Explorer

An interactive laboratory instrument for building genuine geometric intuition
about the **noncommutative 8-torus T⁸_Θ**. Every quantity on screen is computed
live from the deformation matrix Θ; every view is labeled as exactly what it is
(coordinate slice, orthogonal projection, or visualization metaphor); and the
math is presented with strict honesty about what is exact, what is approximate,
and what is a rendering choice.

## Run

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # typecheck + production bundle to dist/
```

## The mathematics (all computed from closed forms at runtime)

- **μ = W(1)** — the positive solution of λ = e^(−λ), by Newton iteration (≈0.5671432904).
- **Ω = √(1 − μ²)** (≈0.8236191).
- **β = φ⁻¹/3 = (√5 − 1)/6** (≈0.2060113296) — one third of the *inverse* golden ratio, not φ^(−1/3).

Θ ∈ so(8) is built from entry rules only: Θ[0,7] = μ, Θ[i,i+3] = Ω for i∈{1,2,3},
and βJ on the index blocks {1,2,3} and {4,5,6}, where J = (1/√3)[[0,−1,1],[1,0,−1],[−1,1,0]].
Under the subset→cube layout this is **four space diagonals (Θ_swap) plus two
spinning grade triangles (Θ_pres)**.

Closed forms exercised and verified live: spectrum {±iμ, ±iΩ, ±i(Ω±β)},
|Pf(Θ)| = μΩ(Ω²−β²), ‖Θ‖² = 2μ²+6Ω²+4β², energy split 0.965/0.035, the spin-1
identity n̂·L = iJ, the invariant 2-planes of the flow, and the Pythagorean gauge
G(β) = Ω(Ω−4β) with its **near-miss** at the canonical β (≈−3.5×10⁻⁴, ~5 parts in
10⁴ — never rounded to zero).

## Modes

- **A · Grade Cube** — the home map. Live phase rings at the cube corners, colored
  coupling bridges (μ gold, Ω cyan, β magenta), X-ray of Θ_swap/Θ_pres with a live
  energy bar, explode-by-grade into the subset Hasse diagram.
- **B · Commutator Lab** — the Weyl relation U_iU_j = e^(2πiΘ_ij)U_jU_i made
  tangible: trace a rectangular loop on the (θ_i,θ_j) 2-torus and watch the phase
  needle land on 2πΘ·(a·b); the 28-pair heatmap doubles as a navigator.
- **C · Projection Chamber** — the 8-D state x(t) = e^{tΘ}x₀ rendered as a
  coordinate slice or a steerable orthogonal projection ℝ⁸→ℝ³ (a smooth Stiefel
  path) with a per-axis mixture legend and a hue/size channel map.
- **D · Flow & Spectrum** — eigenplane dynamics, live spectrum, the β slider
  (0 → canonical → Ω/4 → 0.3) lifting the Ω degeneracy into the spin-1 triplet,
  the Pythagorean gauge with zoom and 3:4:5 triangle, the Lambert-W corner, and
  Web-Audio sonification (Ω→800 Hz, exact ratios, live beat period).

## Diagnostics

Press **D** (or the toolbar button) to open the diagnostics panel: ten checks
that *measure* rather than estimate, each comparing a direct numerical result
against its closed form. A failure raises a red banner; no visualization ships
numbers the diagnostics have not confirmed.

## Guided tour

Seven stops (**Guided tour** in the toolbar) walk from "eight circles, one cube"
to the Lambert-W corner. Free exploration is always one tap away (Esc).

## Stack

Vite + React + TypeScript, Three.js via @react-three/fiber + drei, zustand for
state, KaTeX for formulas, Web Audio for sonification. The numeric core
(`src/core/`) is a small self-contained module with no external linear-algebra
dependency.
