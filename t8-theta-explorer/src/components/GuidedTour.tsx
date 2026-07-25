import { useEffect } from 'react';
import { useStore, ModeId } from '../state/store';
import { BETA_CANONICAL, BETA_PYTHAGOREAN } from '../core/constants';

interface Stop {
  title: string;
  mode: ModeId;
  body: React.ReactNode;
  onEnter?: () => void;
}

const STOPS: Stop[] = [
  {
    title: 'Eight circles, one cube',
    mode: 'cube',
    body: (
      <>
        T⁸ is eight independent angles θ₀…θ₇. They are indexed by the subsets of {'{1,2,3}'}, so they sit
        naturally at the corners of a cube. Orbit the cube; each glowing ring is one live coordinate.
      </>
    ),
  },
  {
    title: 'Four diagonals and two triangles',
    mode: 'cube',
    body: (
      <>
        The whole deformation matrix Θ is pure cube geometry: the <b className="swatch-mu">μ</b> and three{' '}
        <b className="swatch-omega">Ω</b> couplings are the four space diagonals (each vertex to its
        antipode), and the two <b className="swatch-beta">β</b> triangles spin the grade-1 and grade-2 layers
        about the same diagonal. Toggle X-ray to isolate them; the energy bar reads 96.5 / 3.5.
      </>
    ),
  },
  {
    title: 'A loop that comes back different',
    mode: 'commutator',
    body: (
      <>
        The Weyl relation U_iU_j = e^(2πiΘ_ij)U_jU_i means a rectangular loop returns your position but not
        your phase. Trace the loop and watch the needle land on 2πΘ·(a·b). This — not Clifford multiplication
        — is where the noncommutativity lives.
      </>
    ),
  },
  {
    title: 'The map of all 28 phases',
    mode: 'commutator',
    body: (
      <>
        Every unordered pair carries a commutation phase. The 28-pair heatmap is the whole matrix at a glance:
        the bright cells reproduce exactly the four diagonals and two triangles. Click cells to compare a loud
        pair with a silent one.
      </>
    ),
  },
  {
    title: 'Turning on β: one line becomes three',
    mode: 'flow',
    body: (
      <>
        Slide β from 0. At β = 0 the middle block is threefold degenerate — one heavy line at Ω. Turning on β
        lifts it into the exact spin-1 triplet ν_m = Ω + mβ. It is a representation-theoretic splitting
        pattern; no magnetic field is asserted.
      </>
    ),
    onEnter: () => useStore.getState().setBeta(0),
  },
  {
    title: 'The 3:4:5 point — and the honest miss',
    mode: 'flow',
    body: (
      <>
        At β = Ω/4 the three frequencies stand in ratio 3:4:5 and the gauge G(β) = Ω(Ω−4β) reads exactly
        zero. At the <i>canonical</i> β it reads ≈ −3.5×10⁻⁴: a near-miss of about 5 parts in 10⁴. Zoom the
        gauge — it is never rounded to zero. Enable sound to hear the slow beat.
      </>
    ),
    onEnter: () => useStore.getState().setBeta(BETA_PYTHAGOREAN),
  },
  {
    title: 'The Lambert-W corner',
    mode: 'flow',
    body: (
      <>
        Restricted to span(e₀,e₇), D̂ = μ·I and D̂² = D̂·e^(−D̂); the plot of λ against e^(−λ) meets at μ =
        W(1), and the (0,7) plane spins at exactly that rate. This is a localization of the fixed-point
        equation to that block — not an independent derivation of W(1).
      </>
    ),
    onEnter: () => useStore.getState().setBeta(BETA_CANONICAL),
  },
];

export function GuidedTour() {
  const stop = useStore((s) => s.tourStop);
  const setStop = useStore((s) => s.setTourStop);
  const setMode = useStore((s) => s.setMode);

  useEffect(() => {
    if (stop === null) return;
    const s = STOPS[stop];
    setMode(s.mode);
    s.onEnter?.();
  }, [stop, setMode]);

  if (stop === null) return null;
  const s = STOPS[stop];
  const last = STOPS.length - 1;

  return (
    <div className="tour-scrim">
      <div className="tour-card">
        <div className="step">
          Guided tour · stop {stop + 1} of {STOPS.length}
        </div>
        <h2>{s.title}</h2>
        <p>{s.body}</p>
        <div className="tour-nav">
          <button className="btn" disabled={stop === 0} onClick={() => setStop(Math.max(0, stop - 1))}>
            ← back
          </button>
          {stop < last ? (
            <button className="btn" onClick={() => setStop(stop + 1)}>
              next →
            </button>
          ) : (
            <button className="btn" onClick={() => setStop(null)}>
              free exploration →
            </button>
          )}
          <div className="spacer" />
          <button className="btn" onClick={() => setStop(null)}>
            exit (Esc)
          </button>
        </div>
        <div className="small dim" style={{ marginTop: 8 }}>
          Free exploration is always one tap away.
        </div>
      </div>
    </div>
  );
}
