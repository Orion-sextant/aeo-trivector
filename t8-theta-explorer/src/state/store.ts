import { create } from 'zustand';
import { BETA_CANONICAL } from '../core/constants';

export type ModeId = 'cube' | 'commutator' | 'projection' | 'flow';
export type XRay = 'off' | 'swap' | 'pres';

export interface AppState {
  mode: ModeId;
  setMode: (m: ModeId) => void;

  /** The 8 torus angles θ₀…θ₇ (radians). Independent coordinates. */
  phases: number[];
  setPhase: (i: number, v: number) => void;
  resetPhases: () => void;

  /** β for the Θ family. Canonical by default; Mode D sweeps it. */
  beta: number;
  setBeta: (b: number) => void;

  /** Grade-cube view controls. */
  xray: XRay;
  setXray: (x: XRay) => void;
  explode: number; // 0..1 grade-layer separation
  setExplode: (e: number) => void;

  /** Commutator lab: ordered pair (i,j). */
  pair: [number, number];
  setPair: (p: [number, number]) => void;

  /** Diagnostics panel visibility. */
  showDiag: boolean;
  toggleDiag: () => void;

  /** Guided tour. */
  tourStop: number | null; // null = not in tour
  setTourStop: (n: number | null) => void;

  /** Audio on/off (muted by default). */
  audio: boolean;
  setAudio: (a: boolean) => void;
}

export const useStore = create<AppState>((set) => ({
  mode: 'cube',
  setMode: (mode) => set({ mode }),

  phases: new Array(8).fill(0),
  setPhase: (i, v) =>
    set((s) => {
      const phases = s.phases.slice();
      phases[i] = ((v % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
      return { phases };
    }),
  resetPhases: () => set({ phases: new Array(8).fill(0) }),

  beta: BETA_CANONICAL,
  setBeta: (beta) => set({ beta }),

  xray: 'off',
  setXray: (xray) => set({ xray }),
  explode: 0,
  setExplode: (explode) => set({ explode }),

  pair: [0, 7],
  setPair: (pair) => set({ pair }),

  showDiag: false,
  toggleDiag: () => set((s) => ({ showDiag: !s.showDiag })),

  tourStop: null,
  setTourStop: (tourStop) => set({ tourStop }),

  audio: false,
  setAudio: (audio) => set({ audio }),
}));
