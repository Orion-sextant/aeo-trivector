/**
 * The deformation matrix Θ ∈ so(8) and everything read off from it.
 *
 * Θ is real antisymmetric, built ENTIRELY from the entry rules below — no
 * decimals are hardcoded. Its spectrum, Pfaffian, Frobenius norm and invariant
 * 2-planes are all consequences of these rules, and the diagnostics panel
 * confirms the closed forms against direct numerical measurement.
 */

import { MU, OMEGA } from './constants';
import { Mat, Vec, zeros, matvec, dot } from './linalg';

/** J = (1/√3)·[[0,−1,1],[1,0,−1],[−1,1,0]] — spectrum {0,±i}, rotates ℝ³ about (1,1,1)/√3. */
export function buildJ(): Mat {
  const s = 1 / Math.sqrt(3);
  return [
    [0, -s, s],
    [s, 0, -s],
    [-s, s, 0],
  ];
}

/** n̂ = (1,1,1)/√3 — the cube's main diagonal and J's rotation axis. */
export const N_HAT: Vec = [1, 1, 1].map((x) => x / Math.sqrt(3));

/**
 * Build Θ(β) from the entry rules:
 *   Θ[0,7] = μ                       (scalar ↔ pseudoscalar)
 *   Θ[i,i+3] = Ω,  i = 1,2,3         (grade-1 ↔ complementary grade-2)
 *   βJ on index blocks {1,2,3} and {4,5,6}
 *   antisymmetry Θ[j,i] = −Θ[i,j]
 */
export function buildTheta(beta: number): Mat {
  const T = zeros(8);
  const J = buildJ();
  // (0,7) coupling
  T[0][7] = MU;
  T[7][0] = -MU;
  // Ω cross-pairings (i, i+3)
  for (const i of [1, 2, 3]) {
    T[i][i + 3] = OMEGA;
    T[i + 3][i] = -OMEGA;
  }
  // βJ blocks on {1,2,3} and {4,5,6}
  for (let a = 0; a < 3; a++) {
    for (let b = 0; b < 3; b++) {
      T[1 + a][1 + b] += beta * J[a][b];
      T[4 + a][4 + b] += beta * J[a][b];
    }
  }
  return T;
}

/**
 * Even/odd split Θ = Θ_swap + Θ_pres.
 * Θ_swap: the (0,7) entry and the three Ω cross-pairings (the four cube diagonals).
 * Θ_pres: the two βJ blocks (the two spinning grade triangles).
 */
export function splitTheta(beta: number): { swap: Mat; pres: Mat; full: Mat } {
  const swap = zeros(8);
  swap[0][7] = MU;
  swap[7][0] = -MU;
  for (const i of [1, 2, 3]) {
    swap[i][i + 3] = OMEGA;
    swap[i + 3][i] = -OMEGA;
  }
  const pres = zeros(8);
  const J = buildJ();
  for (let a = 0; a < 3; a++) {
    for (let b = 0; b < 3; b++) {
      pres[1 + a][1 + b] += beta * J[a][b];
      pres[4 + a][4 + b] += beta * J[a][b];
    }
  }
  const full = buildTheta(beta);
  return { swap, pres, full };
}

/** Closed-form eigenvalue magnitudes of Θ: {μ, Ω−β, Ω, Ω+β} each with multiplicity 2. */
export function spectrumMagnitudes(beta: number): number[] {
  return [MU, MU, OMEGA - beta, OMEGA - beta, OMEGA, OMEGA, OMEGA + beta, OMEGA + beta];
}

/** Dirac magnitude D̂ = |iΘ| spectrum: {μ, Ω−β, Ω, Ω+β}, each multiplicity 2. */
export function diracMagnitudes(beta: number): number[] {
  return [MU, OMEGA - beta, OMEGA, OMEGA + beta];
}

/** Closed form |Pf(Θ)| = μ Ω (Ω² − β²). */
export function pfaffianClosedForm(beta: number): number {
  return MU * OMEGA * (OMEGA * OMEGA - beta * beta);
}

/** Closed form ‖Θ‖² = 2μ² + 6Ω² + 4β². */
export function frobeniusSqClosedForm(beta: number): number {
  return 2 * MU * MU + 6 * OMEGA * OMEGA + 4 * beta * beta;
}

export interface EigenPlane {
  /** Rotation frequency of this invariant 2-plane. */
  freq: number;
  /** Orthonormal basis {f,g} with Θ f = freq·g, Θ g = −freq·f. */
  f: Vec;
  g: Vec;
  /** Short label for legends. */
  label: string;
}

/**
 * The four invariant 2-planes of Θ, with their rotation frequencies.
 *
 * Each real 2-plane rotating at ω is exactly the kernel of (Θ² + ω²I) — the
 * frequencies come from the closed-form spectrum, not a general eigensolver.
 * We then orient an orthonormal basis so Θ acts as a pure rotation by ω.
 */
export function eigenPlanes(beta: number): EigenPlane[] {
  const T = buildTheta(beta);
  const T2 = zeros(8);
  for (let i = 0; i < 8; i++)
    for (let j = 0; j < 8; j++) {
      let s = 0;
      for (let k = 0; k < 8; k++) s += T[i][k] * T[k][j];
      T2[i][j] = s;
    }
  const specs: { freq: number; label: string }[] = [
    { freq: MU, label: 'μ' },
    { freq: OMEGA - beta, label: 'Ω−β' },
    { freq: OMEGA, label: 'Ω' },
    { freq: OMEGA + beta, label: 'Ω+β' },
  ];
  const planes: EigenPlane[] = [];
  for (const { freq, label } of specs) {
    // Kernel of (Θ² + freq²·I): the 2-plane rotating at `freq`.
    const M = T2.map((row, i) => row.map((v, j) => v + (i === j ? freq * freq : 0)));
    const basis = kernelBasis(M, 2);
    // Orient: f = first kernel vector; g = Θf / freq (guaranteed ⊥ f, unit).
    const f = basis[0];
    const gf = matvec(T, f).map((x) => x / freq);
    // Re-orthonormalize g against f defensively.
    const proj = dot(gf, f);
    const g = gf.map((x, i) => x - proj * f[i]);
    const gn = Math.hypot(...g);
    const gu = g.map((x) => x / gn);
    planes.push({ freq, label, f, g: gu });
  }
  return planes;
}

/**
 * Find `want` orthonormal kernel vectors of a symmetric singular matrix by
 * Gaussian elimination with partial pivoting, collecting free-column directions.
 */
function kernelBasis(Ain: Mat, want: number): Vec[] {
  const n = Ain.length;
  const A = Ain.map((r) => r.slice());
  const pivotCols: number[] = [];
  const pivotRowOf: number[] = new Array(n).fill(-1);
  let row = 0;
  for (let col = 0; col < n && row < n; col++) {
    // Find pivot.
    let piv = row;
    let best = Math.abs(A[row][col]);
    for (let r = row + 1; r < n; r++) {
      const v = Math.abs(A[r][col]);
      if (v > best) {
        best = v;
        piv = r;
      }
    }
    if (best < 1e-9) continue; // free column
    [A[row], A[piv]] = [A[piv], A[row]];
    const pv = A[row][col];
    for (let j = 0; j < n; j++) A[row][j] /= pv;
    for (let r = 0; r < n; r++) {
      if (r === row) continue;
      const f = A[r][col];
      if (f === 0) continue;
      for (let j = 0; j < n; j++) A[r][j] -= f * A[row][j];
    }
    pivotCols.push(col);
    pivotRowOf[col] = row;
    row++;
  }
  const isPivot = new Set(pivotCols);
  const freeCols: number[] = [];
  for (let c = 0; c < n; c++) if (!isPivot.has(c)) freeCols.push(c);
  const vecs: Vec[] = [];
  for (const fc of freeCols) {
    const v = new Array(n).fill(0);
    v[fc] = 1;
    for (const pc of pivotCols) {
      v[pc] = -A[pivotRowOf[pc]][fc];
    }
    vecs.push(v);
  }
  // Orthonormalize (Gram–Schmidt) and return the first `want`.
  const out: Vec[] = [];
  for (const v of vecs) {
    const w = v.slice();
    for (const u of out) {
      const d = dot(w, u);
      for (let i = 0; i < n; i++) w[i] -= d * u[i];
    }
    const nn = Math.hypot(...w);
    if (nn > 1e-9) out.push(w.map((x) => x / nn));
    if (out.length === want) break;
  }
  return out;
}

/**
 * Diagnostic identity: n̂·L = iJ, where (L_k)_ij = −i ε_kij (spin-1 generators).
 * Comparing imaginary parts, this is the real statement  J_ij = −Σ_k n_k ε_kij.
 * Returns the max entrywise residual.
 */
export function spinIdentityResidual(): number {
  const J = buildJ();
  const eps = leviCivita3();
  let res = 0;
  for (let i = 0; i < 3; i++)
    for (let j = 0; j < 3; j++) {
      let s = 0;
      for (let k = 0; k < 3; k++) s += N_HAT[k] * eps(k, i, j);
      res = Math.max(res, Math.abs(J[i][j] - -s));
    }
  return res;
}

function leviCivita3() {
  return (a: number, b: number, c: number): number => {
    if (a === b || b === c || a === c) return 0;
    // sign of permutation (a,b,c) of (0,1,2)
    const perm = [a, b, c];
    let sign = 1;
    for (let i = 0; i < 3; i++)
      for (let j = i + 1; j < 3; j++) if (perm[i] > perm[j]) sign = -sign;
    return sign;
  };
}

/**
 * Characteristic polynomial residual: evaluate det(Θ − iλ... ) — more simply,
 * confirm each closed-form root λ (as ±iν) annihilates the factored char poly
 * p(x) = (x²+μ²)(x²+Ω²)(x²+(Ω−β)²)(x²+(Ω+β)²), and that this p equals det(xI−Θ).
 * We check numerically that p(x) matches det(xI−Θ) at several sample x.
 */
export function charPolyResidual(beta: number): number {
  const T = buildTheta(beta);
  const roots2 = [MU * MU, OMEGA * OMEGA, (OMEGA - beta) ** 2, (OMEGA + beta) ** 2];
  const samples = [0.13, 0.5, 1.1, 2.0, -0.7];
  let res = 0;
  for (const x of samples) {
    // p(x) = Π (x² + ν²)
    let p = 1;
    for (const r of roots2) p *= x * x + r;
    // det(xI − Θ)
    const M = T.map((rw, i) => rw.map((v, j) => (i === j ? x : 0) - v));
    const d = det(M);
    res = Math.max(res, Math.abs(p - d) / (Math.abs(p) + 1));
  }
  return res;
}

/** Plain LU determinant with partial pivoting (diagnostics only). */
export function det(Ain: Mat): number {
  const n = Ain.length;
  const A = Ain.map((r) => r.slice());
  let d = 1;
  for (let col = 0; col < n; col++) {
    let piv = col;
    let best = Math.abs(A[col][col]);
    for (let r = col + 1; r < n; r++) {
      const v = Math.abs(A[r][col]);
      if (v > best) {
        best = v;
        piv = r;
      }
    }
    if (best < 1e-300) return 0;
    if (piv !== col) {
      [A[col], A[piv]] = [A[piv], A[col]];
      d = -d;
    }
    d *= A[col][col];
    for (let r = col + 1; r < n; r++) {
      const f = A[r][col] / A[col][col];
      for (let j = col; j < n; j++) A[r][j] -= f * A[col][j];
    }
  }
  return d;
}
