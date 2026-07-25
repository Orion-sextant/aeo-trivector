/**
 * The nonzero couplings of Θ, tagged by kind for rendering and tooltips.
 *
 * Under the subset→cube layout the whole matrix is four space diagonals
 * (Θ_swap) plus two spinning grade triangles (Θ_pres):
 *   - μ  diagonal (gold):    ∅ ↔ {1,2,3}
 *   - Ω  diagonals (cyan):   {1}↔{2,3}, {2}↔{1,3}, {3}↔{1,2}
 *   - β  triangles (magenta): cyclic βJ on the grade-1 and grade-2 layers
 */

import { buildTheta } from './theta';
import { COORDS } from './coords';
import { COLORS } from './constants';

export type CouplingKind = 'mu' | 'omega' | 'beta';

export interface Coupling {
  i: number;
  j: number;
  value: number; // Θ_ij (signed, i<j convention where meaningful)
  kind: CouplingKind;
  color: string;
  role: string;
}

export function couplings(beta: number): Coupling[] {
  const T = buildTheta(beta);
  const out: Coupling[] = [];
  for (let i = 0; i < 8; i++) {
    for (let j = i + 1; j < 8; j++) {
      const v = T[i][j];
      if (Math.abs(v) < 1e-12) continue;
      let kind: CouplingKind;
      if ((i === 0 && j === 7)) kind = 'mu';
      else if (j === i + 3 && i >= 1 && i <= 3) kind = 'omega';
      else kind = 'beta';
      out.push({
        i,
        j,
        value: v,
        kind,
        color: kind === 'mu' ? COLORS.mu : kind === 'omega' ? COLORS.omega : COLORS.beta,
        role: role(i, j, kind),
      });
    }
  }
  return out;
}

function role(i: number, j: number, kind: CouplingKind): string {
  const ci = COORDS[i].plain;
  const cj = COORDS[j].plain;
  if (kind === 'mu') return `scalar ↔ pseudoscalar (${ci} ↔ ${cj})`;
  if (kind === 'omega') return `grade-1 ↔ complementary grade-2 (${ci} ↔ ${cj})`;
  return `βJ triangle coupling (${ci} ↔ ${cj})`;
}

/** The signed Weyl commutation phase in radians: arg = 2π·Θ_ij. */
export function weylPhase(thetaIJ: number): number {
  return 2 * Math.PI * thetaIJ;
}

/** Wrap radians into (−π, π]. */
export function wrapPi(x: number): number {
  let a = x % (2 * Math.PI);
  if (a > Math.PI) a -= 2 * Math.PI;
  if (a <= -Math.PI) a += 2 * Math.PI;
  return a;
}

/** Full 8×8 |Θ_ij| matrix for the heatmap. */
export function absMatrix(beta: number): number[][] {
  const T = buildTheta(beta);
  return T.map((row) => row.map((v) => Math.abs(v)));
}
