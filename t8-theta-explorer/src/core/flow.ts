/**
 * The natural dynamics of Θ: rotate each invariant 2-plane at its eigenfrequency.
 *
 * The state is the lift x(t) ∈ ℝ⁸ of a point on T⁸, given by
 *   x(t) = Σ_j [ cos(φ_j) f_j + sin(φ_j) g_j ],   φ_j(t) = φ_j(0) + ν_j t.
 * This is exactly e^{tΘ} applied to Σ_j f_j: each plane rotates rigidly at its
 * own frequency ν_j ∈ {μ, Ω−β, Ω, Ω+β}. Because the frequencies are mutually
 * incommensurate the motion is quasi-periodic and never exactly repeats.
 */

import { EigenPlane } from './theta';

export class FlowEngine {
  phases: number[];
  planes: EigenPlane[];

  constructor(planes: EigenPlane[]) {
    this.planes = planes;
    this.phases = planes.map(() => 0);
  }

  setPlanes(planes: EigenPlane[]) {
    // Preserve current phases (per-plane) when β changes.
    const old = this.phases;
    this.planes = planes;
    this.phases = planes.map((_, i) => old[i] ?? 0);
  }

  /** Advance all plane phases by dt·speed. */
  step(dt: number, speed = 1) {
    for (let j = 0; j < this.planes.length; j++) {
      this.phases[j] += this.planes[j].freq * dt * speed;
    }
  }

  /** Current 8-D lift x(t). */
  state(): number[] {
    const x = new Array(8).fill(0);
    for (let j = 0; j < this.planes.length; j++) {
      const c = Math.cos(this.phases[j]);
      const s = Math.sin(this.phases[j]);
      const { f, g } = this.planes[j];
      for (let k = 0; k < 8; k++) x[k] += c * f[k] + s * g[k];
    }
    return x;
  }

  /** The four winding plane-phases (a genuine point on T⁴), wrapped to [0,2π). */
  planePhases(): number[] {
    return this.phases.map((p) => ((p % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI));
  }
}

/** Smallest common beat period between two frequencies (for sonification display). */
export function beatPeriod(f1: number, f2: number): number {
  const d = Math.abs(f1 - f2);
  return d < 1e-12 ? Infinity : 1 / d;
}
