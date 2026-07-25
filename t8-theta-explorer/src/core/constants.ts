/**
 * Fundamental constants of the T^8_Theta ansatz.
 *
 * Everything here is computed at runtime from closed forms. The literal
 * decimals in comments are validation targets only (see core/diagnostics.ts),
 * never sources of truth.
 */

/** Golden ratio  φ = (1 + √5) / 2 ≈ 1.6180339887 */
export const PHI = (1 + Math.sqrt(5)) / 2;

/**
 * μ = W(1): the unique positive real solution of  λ = e^(−λ).
 * Found by Newton iteration on f(λ) = λ − e^(−λ), f'(λ) = 1 + e^(−λ).
 * Reference value 0.5671432904.
 */
export function computeMu(): number {
  let lambda = 0.5;
  for (let k = 0; k < 100; k++) {
    const e = Math.exp(-lambda);
    const f = lambda - e;
    const fp = 1 + e;
    const next = lambda - f / fp;
    if (Math.abs(next - lambda) < 1e-16) {
      lambda = next;
      break;
    }
    lambda = next;
  }
  return lambda;
}

export const MU = computeMu();

/** Ω = √(1 − μ²).  Reference value 0.8236191. */
export const OMEGA = Math.sqrt(1 - MU * MU);

/**
 * β = φ⁻¹ / 3 = (√5 − 1) / 6.  Reference value 0.2060113296.
 * NOTE: this is one third of the INVERSE golden ratio, NOT φ^(−1/3).
 */
export const BETA_CANONICAL = (Math.sqrt(5) - 1) / 6;

/** The three grade-triplet frequencies at a given β. */
export function frequencies(beta: number) {
  return {
    minus: OMEGA - beta,
    zero: OMEGA,
    plus: OMEGA + beta,
  };
}

/**
 * Pythagorean gauge:  G(β) = ν₋² + ν₀² − ν₊² = Ω(Ω − 4β).
 * Vanishes exactly at β = Ω/4, where ν₋ : ν₀ : ν₊ = 3 : 4 : 5.
 * At the canonical β it reads ≈ −3.5×10⁻⁴ — a near-miss, not an identity.
 */
export function pythagoreanGauge(beta: number): number {
  return OMEGA * (OMEGA - 4 * beta);
}

/** β value at which the 3:4:5 relation is exact. */
export const BETA_PYTHAGOREAN = OMEGA / 4;

/** Palette — dark laboratory. gold=μ, cyan=Ω, magenta=β. */
export const COLORS = {
  mu: '#f4c14b',
  omega: '#3fd8e0',
  beta: '#e05cc8',
  bg: '#05070c',
  panel: '#0c1018',
  ink: '#c8d2e0',
  inkDim: '#6b7688',
  grid: '#1a2130',
  ok: '#4fd18b',
  bad: '#ff5c6c',
} as const;
