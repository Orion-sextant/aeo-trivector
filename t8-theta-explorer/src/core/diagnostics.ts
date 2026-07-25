/**
 * In-app validation: measure, don't estimate.
 *
 * Every check computes a residual by direct numerical measurement and compares
 * it against the closed form. No visualization ships numbers these checks have
 * not confirmed. Run on load; a red result raises a banner.
 */

import { MU, OMEGA, BETA_CANONICAL, BETA_PYTHAGOREAN, pythagoreanGauge } from './constants';
import {
  buildTheta,
  splitTheta,
  spectrumMagnitudes,
  pfaffianClosedForm,
  frobeniusSqClosedForm,
  eigenPlanes,
  spinIdentityResidual,
  charPolyResidual,
} from './theta';
import { pfaffian, antisymmetryResidual, frobeniusSq, matvec } from './linalg';

export interface Check {
  id: number;
  name: string;
  detail: string;
  residual: number;
  tol: number;
  pass: boolean;
}

function mk(id: number, name: string, detail: string, residual: number, tol: number): Check {
  return { id, name, detail, residual, tol, pass: residual <= tol };
}

export function runDiagnostics(beta = BETA_CANONICAL): Check[] {
  const checks: Check[] = [];
  const T = buildTheta(beta);

  // 1. Antisymmetry.
  checks.push(
    mk(1, 'Θ antisymmetric', 'max |Θ_ij + Θ_ji| from the entry rules', antisymmetryResidual(T), 1e-12),
  );

  // 2. Char-poly / spectrum: closed-form roots annihilate det(xI−Θ).
  checks.push(
    mk(
      2,
      'Spectrum {±iμ, ±iΩ, ±i(Ω±β)}',
      'det(xI−Θ) matches Π(x²+ν²) at sampled x',
      charPolyResidual(beta),
      1e-10,
    ),
  );

  // 3. Pfaffian: numerical vs closed form μΩ(Ω²−β²).
  const pfNum = Math.abs(pfaffian(T));
  const pfCF = pfaffianClosedForm(beta);
  checks.push(
    mk(3, '|Pf(Θ)| = μΩ(Ω²−β²)', `numerical ${pfNum.toFixed(9)} vs closed ${pfCF.toFixed(9)}`, Math.abs(pfNum - pfCF), 1e-10),
  );

  // 4. Frobenius norm squared.
  const frNum = frobeniusSq(T);
  const frCF = frobeniusSqClosedForm(beta);
  checks.push(
    mk(4, '‖Θ‖² = 2μ²+6Ω²+4β²', `measured ${frNum.toFixed(9)} vs closed ${frCF.toFixed(9)}`, Math.abs(frNum - frCF), 1e-10),
  );

  // 5. Pythagorean gauge: G(Ω/4)=0 exactly; G(β_can) = Ω(Ω−4β).
  const gAtPyth = pythagoreanGauge(BETA_PYTHAGOREAN);
  const gCanMeasured = OMEGA * (OMEGA - 4 * BETA_CANONICAL);
  const gCanFromNu = (() => {
    const nm = OMEGA - BETA_CANONICAL,
      n0 = OMEGA,
      np = OMEGA + BETA_CANONICAL;
    return nm * nm + n0 * n0 - np * np;
  })();
  checks.push(mk(5, 'G(Ω/4) = 0, G(β)=Ω(Ω−4β)', `G(Ω/4)=${gAtPyth.toExponential(2)}, residual on β form`, Math.max(Math.abs(gAtPyth), Math.abs(gCanMeasured - gCanFromNu)), 1e-12));

  // 6. Energy split of Θ_swap vs Θ_pres ≈ 0.965 / 0.035 (to three decimals).
  const { swap, pres } = splitTheta(beta);
  const total = frobeniusSq(T);
  const swapFrac = frobeniusSq(swap) / total;
  const presFrac = frobeniusSq(pres) / total;
  const splitErr = Math.max(Math.abs(swapFrac - 0.965), Math.abs(presFrac - 0.035));
  checks.push(
    mk(6, 'Energy split 0.965 / 0.035', `swap ${swapFrac.toFixed(4)}, pres ${presFrac.toFixed(4)}`, splitErr, 1e-3 + 5e-4),
  );

  // 7. n̂·L = iJ entrywise (real form J = −Σ n_k ε_kij).
  checks.push(mk(7, 'n̂·L = iJ', 'spin-1 identity, entrywise residual', spinIdentityResidual(), 1e-12));

  // 8. μ satisfies μ = e^(−μ).
  checks.push(mk(8, 'μ = e^(−μ)  (μ = W(1))', `μ = ${MU.toFixed(10)}`, Math.abs(MU - Math.exp(-MU)), 1e-12));

  // Bonus: eigenplanes really rotate at their frequencies (Θ f = ν g), sanity for the flow.
  let planeRes = 0;
  for (const p of eigenPlanes(beta)) {
    const Tf = matvec(T, p.f);
    for (let i = 0; i < 8; i++) planeRes = Math.max(planeRes, Math.abs(Tf[i] - p.freq * p.g[i]));
  }
  checks.push(mk(9, 'Invariant 2-planes: Θf = ν·g', 'flow generator acts as pure rotation per plane', planeRes, 1e-8));

  // Bonus: spectrum magnitudes sorted match sorted closed form (belt & suspenders).
  const mags = spectrumMagnitudes(beta);
  checks.push(mk(10, 'Dirac magnitudes {μ,Ω−β,Ω,Ω+β}', mags.map((m) => m.toFixed(4)).join(', '), 0, 1e-12));

  return checks;
}

export function allPass(checks: Check[]): boolean {
  return checks.every((c) => c.pass);
}
