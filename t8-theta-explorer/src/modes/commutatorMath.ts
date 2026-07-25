/**
 * Loop holonomy on the (θ_i, θ_j) 2-torus.
 *
 * The Weyl relation U_iU_j = e^(2πiΘ_ij) U_jU_i says a rectangular loop —
 * forward a in direction i, forward b in direction j, back a, back b — returns
 * the position to start but multiplies the state by e^(2πiΘ_ij·ab). We render
 * the phase accumulating along the path using the symmetric gauge
 * A = πΘ(x_i dx_j − x_j dx_i), so the needle turns on two of the four legs and
 * lands exactly on 2πΘ·a·b after one full loop.
 */

export interface LoopState {
  /** Position in the unit cell, each component in [0,1]. */
  pos: [number, number];
  /** Accumulated phase in radians. */
  phase: number;
  /** Which leg (0..3). */
  leg: number;
}

/**
 * @param t traversal parameter in [0,4] (one leg per unit)
 * @param a loop side in direction i, fraction of the cell [0,1]
 * @param b loop side in direction j, fraction of the cell [0,1]
 * @param theta Θ_ij
 */
export function loopAt(t: number, a: number, b: number, theta: number): LoopState {
  const tc = Math.max(0, Math.min(4, t));
  const leg = Math.min(3, Math.floor(tc));
  const f = tc - leg;
  const k = Math.PI * theta; // symmetric-gauge constant
  let pos: [number, number];
  let phase: number;
  switch (leg) {
    case 0: // → a along i, x_j = 0
      pos = [a * f, 0];
      phase = 0; // ∫ −πΘ x_j dx_i = 0
      break;
    case 1: // ↑ b along j, x_i = a
      pos = [a, b * f];
      phase = k * a * (b * f); // ∫ πΘ x_i dx_j = πΘ a (b f)
      break;
    case 2: // ← a along i, x_j = b
      pos = [a * (1 - f), b];
      phase = k * a * b + k * b * (a * f); // add ∫ −πΘ x_j dx_i from a→0
      break;
    case 3: // ↓ b along j, x_i = 0
    default:
      pos = [0, b * (1 - f)];
      phase = 2 * k * a * b; // total, x_i = 0 contributes nothing
      break;
  }
  return { pos, phase, leg };
}

/** Final loop phase (radians): 2πΘ·a·b. */
export function loopPhase(a: number, b: number, theta: number): number {
  return 2 * Math.PI * theta * a * b;
}
