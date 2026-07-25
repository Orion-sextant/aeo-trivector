/**
 * Sonification of the spectrum. Four oscillators at the four frequencies under a
 * common scale factor (Ω mapped near 800 Hz), ratios kept exact. At β = Ω/4 the
 * middle triplet forms an exact 3:4:5 chord; at the canonical β the detune from
 * 3:4:5 is audible as slow beating. Muted by default.
 */

import { MU, OMEGA } from './constants';

const A_OMEGA = 800; // Ω mapped here (Hz)

export class SpectrumAudio {
  private ctx: AudioContext | null = null;
  private oscs: OscillatorNode[] = [];
  private gains: GainNode[] = [];
  private on = false;

  /** Hz for each of the four tones at a given β. */
  static freqs(beta: number): number[] {
    const scale = A_OMEGA / OMEGA;
    return [MU, OMEGA - beta, OMEGA, OMEGA + beta].map((v) => v * scale);
  }

  /**
   * Audible detune of the lower third from just-3:4:5 and the resulting beat
   * period (seconds). ν₋ should land on 600 Hz when 3:4:5 is exact (β = Ω/4).
   */
  static beat(beta: number): { detuneHz: number; periodSec: number } {
    const scale = A_OMEGA / OMEGA;
    const nMinus = (OMEGA - beta) * scale;
    const detune = Math.abs(nMinus - 600);
    return { detuneHz: detune, periodSec: detune < 1e-9 ? Infinity : 1 / detune };
  }

  start(beta: number) {
    if (this.on) return;
    this.ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
    const freqs = SpectrumAudio.freqs(beta);
    const levels = [0.12, 0.16, 0.2, 0.16]; // μ quieter; triplet foregrounded
    freqs.forEach((f, i) => {
      const osc = this.ctx!.createOscillator();
      const g = this.ctx!.createGain();
      osc.type = 'sine';
      osc.frequency.value = f;
      g.gain.value = 0;
      osc.connect(g).connect(this.ctx!.destination);
      osc.start();
      // gentle fade-in
      g.gain.setTargetAtTime(levels[i], this.ctx!.currentTime, 0.05);
      this.oscs.push(osc);
      this.gains.push(g);
    });
    this.on = true;
  }

  update(beta: number) {
    if (!this.on || !this.ctx) return;
    const freqs = SpectrumAudio.freqs(beta);
    freqs.forEach((f, i) => {
      this.oscs[i]?.frequency.setTargetAtTime(f, this.ctx!.currentTime, 0.03);
    });
  }

  stop() {
    if (!this.on || !this.ctx) return;
    const t = this.ctx.currentTime;
    this.gains.forEach((g) => g.gain.setTargetAtTime(0, t, 0.05));
    const ctx = this.ctx;
    const oscs = this.oscs;
    setTimeout(() => {
      oscs.forEach((o) => o.stop());
      ctx.close();
    }, 200);
    this.oscs = [];
    this.gains = [];
    this.ctx = null;
    this.on = false;
  }
}
