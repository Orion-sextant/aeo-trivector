/**
 * A small, self-contained real-matrix module — only what the app needs.
 *
 * We never run a general eigensolver on the hot path: the spectrum of Θ is
 * known in closed form (see theta.ts). The routines here exist for the
 * diagnostics cross-checks (numerical Pfaffian, antisymmetry, char-poly
 * evaluation) and for building projection frames.
 */

export type Mat = number[][];
export type Vec = number[];

export function zeros(n: number, m = n): Mat {
  return Array.from({ length: n }, () => new Array(m).fill(0));
}

export function identity(n: number): Mat {
  const M = zeros(n);
  for (let i = 0; i < n; i++) M[i][i] = 1;
  return M;
}

export function clone(A: Mat): Mat {
  return A.map((r) => r.slice());
}

export function transpose(A: Mat): Mat {
  const n = A.length;
  const m = A[0].length;
  const T = zeros(m, n);
  for (let i = 0; i < n; i++) for (let j = 0; j < m; j++) T[j][i] = A[i][j];
  return T;
}

export function matmul(A: Mat, B: Mat): Mat {
  const n = A.length;
  const k = B.length;
  const m = B[0].length;
  const C = zeros(n, m);
  for (let i = 0; i < n; i++) {
    for (let t = 0; t < k; t++) {
      const a = A[i][t];
      if (a === 0) continue;
      const Bt = B[t];
      const Ci = C[i];
      for (let j = 0; j < m; j++) Ci[j] += a * Bt[j];
    }
  }
  return C;
}

export function matvec(A: Mat, x: Vec): Vec {
  return A.map((row) => row.reduce((s, a, j) => s + a * x[j], 0));
}

export function frobeniusSq(A: Mat): number {
  let s = 0;
  for (const row of A) for (const v of row) s += v * v;
  return s;
}

export function maxAbsDiff(A: Mat, B: Mat): number {
  let d = 0;
  for (let i = 0; i < A.length; i++)
    for (let j = 0; j < A[0].length; j++) d = Math.max(d, Math.abs(A[i][j] - B[i][j]));
  return d;
}

/** Antisymmetry residual max_{i,j} |A_ij + A_ji|. */
export function antisymmetryResidual(A: Mat): number {
  const n = A.length;
  let d = 0;
  for (let i = 0; i < n; i++)
    for (let j = 0; j < n; j++) d = Math.max(d, Math.abs(A[i][j] + A[j][i]));
  return d;
}

/**
 * Pfaffian of a real antisymmetric matrix of even order, computed numerically
 * via Parlett–Reid tridiagonalization (the PFAPACK "LTL" Gauss method). Returns
 * the signed Pfaffian — an independent cross-check against the closed form.
 */
export function pfaffian(Ain: Mat): number {
  const n = Ain.length;
  if (n % 2 !== 0) return 0;
  const A = clone(Ain);
  let pf = 1;
  for (let k = 0; k < n - 1; k += 2) {
    // Pivot: permute the largest |A[i][k]| (i>k) into row/col k+1.
    let piv = k + 1;
    let best = Math.abs(A[k + 1][k]);
    for (let i = k + 2; i < n; i++) {
      const v = Math.abs(A[i][k]);
      if (v > best) {
        best = v;
        piv = i;
      }
    }
    if (piv !== k + 1) {
      swapRows(A, k + 1, piv);
      swapCols(A, k + 1, piv);
      pf = -pf;
    }
    if (A[k + 1][k] === 0) return 0;
    pf *= A[k][k + 1];
    if (k + 2 < n) {
      // tau = A[k][k+2:] / A[k][k+1]; rank-2 skew update of trailing block.
      const inv = 1 / A[k][k + 1];
      for (let i = k + 2; i < n; i++) {
        const taui = A[k][i] * inv;
        const viK1 = A[i][k + 1];
        if (taui === 0 && viK1 === 0) continue;
        for (let j = k + 2; j < n; j++) {
          A[i][j] += taui * A[j][k + 1] - viK1 * (A[k][j] * inv);
        }
      }
    }
  }
  return pf;
}

function swapRows(A: Mat, i: number, j: number) {
  const t = A[i];
  A[i] = A[j];
  A[j] = t;
}
function swapCols(A: Mat, i: number, j: number) {
  for (const row of A) {
    const t = row[i];
    row[i] = row[j];
    row[j] = t;
  }
}

/** Evaluate a monic-ish polynomial given as coefficient array (highest first). */
export function polyval(coeffs: number[], x: number): number {
  return coeffs.reduce((acc, c) => acc * x + c, 0);
}

/** Gram–Schmidt orthonormalization of the ROWS of A (each row a vector in R^m). */
export function orthonormalizeRows(A: Mat): Mat {
  const rows = A.map((r) => r.slice());
  const out: Vec[] = [];
  for (const v of rows) {
    const w = v.slice();
    for (const u of out) {
      const d = dot(w, u);
      for (let i = 0; i < w.length; i++) w[i] -= d * u[i];
    }
    const n = Math.hypot(...w);
    if (n > 1e-12) out.push(w.map((x) => x / n));
    else out.push(w);
  }
  return out;
}

export function dot(a: Vec, b: Vec): number {
  let s = 0;
  for (let i = 0; i < a.length; i++) s += a[i] * b[i];
  return s;
}
