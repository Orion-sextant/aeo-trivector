import { useEffect, useMemo, useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Line } from '@react-three/drei';
import * as THREE from 'three';
import { useStore } from '../state/store';
import { eigenPlanes } from '../core/theta';
import { FlowEngine } from '../core/flow';
import {
  MU,
  OMEGA,
  BETA_CANONICAL,
  BETA_PYTHAGOREAN,
  pythagoreanGauge,
  frequencies,
  COLORS,
} from '../core/constants';
import { SpectrumAudio } from '../core/audio';

/** Live 8-D flow projected to 3-D, plus a Lissajous of two chosen planes. */
function FlowScene({ speed, planePair, lissRef }: { speed: number; planePair: [number, number]; lissRef: React.MutableRefObject<[number, number][]> }) {
  const beta = useStore((s) => s.beta);
  const planes = useMemo(() => eigenPlanes(beta), [beta]);
  const engine = useRef(new FlowEngine(planes));
  engine.current.setPlanes(planes);
  const lineRef = useRef<any>(null);
  const headRef = useRef<THREE.Mesh>(null);
  const trail = useRef<THREE.Vector3[]>([]);
  // fixed projection frame onto first three coords for a stable view
  const P = [
    [1, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 1, 0, 0, 0],
  ];
  useFrame((_, dt) => {
    engine.current.step(Math.min(dt, 0.05), speed);
    const x = engine.current.state();
    const v = P.map((row) => row.reduce((s, w, k) => s + w * x[k], 0));
    const p = new THREE.Vector3(v[0], v[1], v[2]).multiplyScalar(1.5);
    trail.current.push(p);
    if (trail.current.length > 1000) trail.current.shift();
    if (lineRef.current && trail.current.length > 1) lineRef.current.geometry.setFromPoints(trail.current);
    if (headRef.current) headRef.current.position.copy(p);
    // Lissajous: cos of the two chosen plane phases
    const ph = engine.current.phases;
    lissRef.current.push([Math.cos(ph[planePair[0]]), Math.cos(ph[planePair[1]])]);
    if (lissRef.current.length > 400) lissRef.current.shift();
  });
  return (
    <>
      <line ref={lineRef as any}>
        <bufferGeometry />
        <lineBasicMaterial color={COLORS.omega} transparent opacity={0.6} />
      </line>
      <mesh ref={headRef}>
        <sphereGeometry args={[0.12, 16, 16]} />
        <meshBasicMaterial color="#ffffff" />
      </mesh>
    </>
  );
}

function LissajousInset({ lissRef, labels }: { lissRef: React.MutableRefObject<[number, number][]>; labels: [string, string] }) {
  const [, force] = useState(0);
  useEffect(() => {
    const id = setInterval(() => force((n) => n + 1), 60);
    return () => clearInterval(id);
  }, []);
  const S = 120;
  const pts = lissRef.current.map(([x, y]) => `${S / 2 + (x * S) / 2.4},${S / 2 - (y * S) / 2.4}`).join(' ');
  return (
    <svg width={S} height={S}>
      <rect x={0} y={0} width={S} height={S} fill="#0a0e15" stroke="#1c2434" rx={6} />
      <polyline points={pts} fill="none" stroke={COLORS.beta} strokeWidth={1.2} opacity={0.85} />
      <text x={S / 2} y={S - 4} textAnchor="middle" fontSize={9} fill="#8794a8">
        {labels[0]} × {labels[1]}
      </text>
    </svg>
  );
}

/** The little λ vs e^(−λ) plot with the intersection at μ. */
function LambertCorner() {
  const W = 180;
  const H = 120;
  const x0 = 0;
  const x1 = 1.2;
  const X = (x: number) => ((x - x0) / (x1 - x0)) * W;
  const Y = (y: number) => H - y * H;
  const line = (fn: (x: number) => number) => {
    let d = '';
    for (let i = 0; i <= 60; i++) {
      const x = x0 + (i / 60) * (x1 - x0);
      d += `${i === 0 ? 'M' : 'L'} ${X(x)} ${Y(fn(x))} `;
    }
    return d;
  };
  return (
    <svg width={W} height={H}>
      <rect x={0} y={0} width={W} height={H} fill="#0a0e15" stroke="#1c2434" rx={6} />
      <path d={line((x) => x)} fill="none" stroke={COLORS.omega} strokeWidth={1.5} />
      <path d={line((x) => Math.exp(-x))} fill="none" stroke={COLORS.mu} strokeWidth={1.5} />
      <circle cx={X(MU)} cy={Y(MU)} r={4} fill="#fff" />
      <text x={X(MU) + 6} y={Y(MU) - 4} fontSize={10} fill="#dbe5f2" className="mono">
        μ = {MU.toFixed(4)}
      </text>
      <text x={6} y={14} fontSize={9} fill={COLORS.omega}>
        λ
      </text>
      <text x={W - 42} y={Y(Math.exp(-x1)) - 4} fontSize={9} fill={COLORS.mu}>
        e^(−λ)
      </text>
    </svg>
  );
}

/** Spectrum: four frequency lines, live; middle triplet splits from Ω as β grows. */
function SpectrumBars({ beta }: { beta: number }) {
  const W = 300;
  const H = 90;
  const fmax = 1.15;
  const X = (f: number) => (f / fmax) * W;
  const { minus, zero, plus } = frequencies(beta);
  const lines = [
    { f: MU, c: COLORS.mu, label: 'μ' },
    { f: minus, c: COLORS.beta, label: 'Ω−β' },
    { f: zero, c: COLORS.omega, label: 'Ω' },
    { f: plus, c: COLORS.beta, label: 'Ω+β' },
  ];
  return (
    <svg width={W} height={H}>
      <line x1={0} y1={H - 20} x2={W} y2={H - 20} stroke="#1c2434" />
      {[0, 0.25, 0.5, 0.75, 1].map((t) => (
        <text key={t} x={X(t * fmax)} y={H - 6} fontSize={8} fill="#5a6578" textAnchor="middle">
          {(t * fmax).toFixed(2)}
        </text>
      ))}
      {lines.map((l, i) => (
        <g key={i}>
          <line x1={X(l.f)} y1={10} x2={X(l.f)} y2={H - 20} stroke={l.c} strokeWidth={2} />
          <text x={X(l.f)} y={8} fontSize={9} fill={l.c} textAnchor="middle">
            {l.label}
          </text>
        </g>
      ))}
    </svg>
  );
}

/** Right-triangle inset with legs ν₋, ν₀ and hypotenuse ν₊. */
function PythTriangle({ beta }: { beta: number }) {
  const { minus, zero, plus } = frequencies(beta);
  const S = 120;
  const scale = S / (OMEGA * 1.3);
  const a = minus * scale;
  const b = zero * scale;
  // right angle at origin; legs along axes; hypotenuse would be sqrt(a²+b²); actual ν₊ drawn
  const ox = 14;
  const oy = S - 14;
  const closes = Math.abs(minus * minus + zero * zero - plus * plus) < 1e-6;
  return (
    <svg width={S} height={S}>
      <rect x={0} y={0} width={S} height={S} fill="#0a0e15" stroke="#1c2434" rx={6} />
      {/* legs */}
      <line x1={ox} y1={oy} x2={ox + a} y2={oy} stroke={COLORS.beta} strokeWidth={2} />
      <line x1={ox} y1={oy} x2={ox} y2={oy - b} stroke={COLORS.omega} strokeWidth={2} />
      {/* actual hypotenuse ν₊ (from end of ν₀ leg to end of ν₋ leg) */}
      <line x1={ox} y1={oy - b} x2={ox + a} y2={oy} stroke="#fff" strokeWidth={1} strokeDasharray="3 2" />
      {/* the ν₊-length hypotenuse, drawn from apex at the true angle to show the gap */}
      <line x1={ox + a} y1={oy} x2={ox + a - (plus * scale) * (a / Math.hypot(a, b))} y2={oy - (plus * scale) * (b / Math.hypot(a, b))} stroke={COLORS.beta} strokeWidth={2} opacity={0.5} />
      <text x={ox + a / 2} y={oy + 11} fontSize={8} fill={COLORS.beta} textAnchor="middle">ν₋</text>
      <text x={ox - 11} y={oy - b / 2} fontSize={8} fill={COLORS.omega}>ν₀</text>
      <text x={S - 30} y={14} fontSize={8} fill={closes ? COLORS.ok : '#8794a8'}>
        {closes ? '3:4:5 ✓' : 'near-miss'}
      </text>
    </svg>
  );
}

const DETENTS = [
  { v: 0, label: '0' },
  { v: BETA_CANONICAL, label: 'β canonical' },
  { v: BETA_PYTHAGOREAN, label: 'Ω/4 (3:4:5)' },
  { v: 0.3, label: '0.3' },
];

export function FlowSpectrum() {
  const beta = useStore((s) => s.beta);
  const setBeta = useStore((s) => s.setBeta);
  const audio = useStore((s) => s.audio);
  const setAudio = useStore((s) => s.setAudio);
  const [speed, setSpeed] = useState(1);
  const [planePair, setPlanePair] = useState<[number, number]>([0, 2]);
  const [zoom, setZoom] = useState(1);
  const lissRef = useRef<[number, number][]>([]);
  const audioRef = useRef<SpectrumAudio | null>(null);

  const G = pythagoreanGauge(beta);
  const beat = SpectrumAudio.beat(beta);
  const planeLabels = ['μ', 'Ω−β', 'Ω', 'Ω+β'];

  useEffect(() => {
    if (audio) {
      if (!audioRef.current) audioRef.current = new SpectrumAudio();
      audioRef.current.start(beta);
    } else {
      audioRef.current?.stop();
      audioRef.current = null;
    }
    return () => {
      audioRef.current?.stop();
      audioRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [audio]);

  useEffect(() => {
    audioRef.current?.update(beta);
  }, [beta]);

  // Gauge needle: G ranges roughly [-0.02, +0.02] near canonical; zoomed.
  const gaugeMax = 0.02 / zoom;
  const needleX = Math.max(-1, Math.min(1, G / gaugeMax));

  return (
    <div className="canvas-wrap" style={{ display: 'grid', gridTemplateColumns: '1fr 360px' }}>
      <div style={{ position: 'relative' }}>
        <Canvas camera={{ position: [3.5, 2.5, 4.5], fov: 45 }}>
          <ambientLight intensity={0.7} />
          <Line points={[[-3, 0, 0], [3, 0, 0]]} color="#141b28" lineWidth={1} />
          <FlowScene speed={speed} planePair={planePair} lissRef={lissRef} />
          <OrbitControls enablePan={false} makeDefault />
        </Canvas>
        <div className="overlay tl panel" style={{ maxWidth: 300 }}>
          <span className="tag projection">natural dynamics · projection of ℝ⁸</span>
          <h3 style={{ marginTop: 10 }}>Flow &amp; Spectrum</h3>
          <p className="hint">
            Each invariant 2-plane rotates at its own frequency (μ, Ω−β, Ω, Ω+β). Incommensurate rates ⇒
            quasi-periodic motion that never exactly repeats.
          </p>
          <div className="row">
            <label>speed</label>
            <input type="range" min={0} max={3} step={0.01} value={speed} onChange={(e) => setSpeed(+e.target.value)} />
          </div>
        </div>
        <div className="overlay bl panel">
          <div className="small dim" style={{ marginBottom: 6 }}>Lissajous — pick two planes</div>
          <div style={{ display: 'flex', gap: 10 }}>
            <LissajousInset lissRef={lissRef} labels={[planeLabels[planePair[0]], planeLabels[planePair[1]]]} />
            <div>
              {[0, 1].map((slot) => (
                <div className="row" key={slot}>
                  <label>{slot === 0 ? 'plane A' : 'plane B'}</label>
                  <select
                    value={planePair[slot]}
                    onChange={(e) => {
                      const np = [...planePair] as [number, number];
                      np[slot] = +e.target.value;
                      setPlanePair(np);
                    }}
                  >
                    {planeLabels.map((l, i) => (
                      <option key={i} value={i}>
                        {l}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Right rail */}
      <div className="panel" style={{ borderRadius: 0, borderTop: 'none', borderRight: 'none', borderBottom: 'none', overflow: 'auto' }}>
        <h3>Spectrum (live)</h3>
        <SpectrumBars beta={beta} />
        <div className="small dim">
          At β = 0 the three middle lines coincide at Ω (threefold degenerate). Turning on β lifts the
          degeneracy into the exact spin-1 triplet ν_m = Ω + mβ — a representation-theoretic pattern, not a
          magnetic field.
        </div>

        <div style={{ borderTop: '1px solid #1a2130', margin: '12px 0', paddingTop: 10 }}>
          <h3>β slider</h3>
          <input type="range" min={0} max={0.3} step={0.0002} value={beta} onChange={(e) => setBeta(+e.target.value)} style={{ width: '100%' }} />
          <div style={{ display: 'flex', gap: 4, marginTop: 8, flexWrap: 'wrap' }}>
            {DETENTS.map((d) => (
              <button key={d.label} className={Math.abs(beta - d.v) < 1e-6 ? 'btn active' : 'btn'} style={{ fontSize: 11, padding: '4px 8px' }} onClick={() => setBeta(d.v)}>
                {d.label}
              </button>
            ))}
          </div>
          <div className="mono small" style={{ marginTop: 6 }}>
            β = <span className="value">{beta.toFixed(6)}</span>
          </div>
        </div>

        <div style={{ borderTop: '1px solid #1a2130', margin: '12px 0', paddingTop: 10 }}>
          <h3>Pythagorean gauge — G(β) = Ω(Ω − 4β)</h3>
          <div style={{ display: 'flex', gap: 12 }}>
            <PythTriangle beta={beta} />
            <div style={{ flex: 1 }}>
              {/* gauge */}
              <svg width={160} height={40}>
                <line x1={10} y1={20} x2={150} y2={20} stroke="#1c2434" />
                <line x1={80} y1={10} x2={80} y2={30} stroke={COLORS.ok} strokeWidth={1.5} />
                <text x={80} y={40} fontSize={8} fill={COLORS.ok} textAnchor="middle">0</text>
                <circle cx={80 + needleX * 70} cy={20} r={5} fill="#fff" />
              </svg>
              <div className="mono small" style={{ marginTop: 4 }}>
                G(β) = <span className="value">{G.toExponential(3)}</span>
              </div>
              <div className="row">
                <label>zoom</label>
                <input type="range" min={1} max={200} step={1} value={zoom} onChange={(e) => setZoom(+e.target.value)} />
              </div>
              <div className="small dim">
                Zero only at β = Ω/4. At the canonical β the residual is ≈ −3.5×10⁻⁴ — about 5 parts in 10⁴, a
                near-miss, never rounded to zero.
              </div>
            </div>
          </div>
        </div>

        <div style={{ borderTop: '1px solid #1a2130', margin: '12px 0', paddingTop: 10 }}>
          <h3>Lambert-W corner</h3>
          <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
            <LambertCorner />
            <div className="small dim">
              On span(e₀,e₇), D̂ = μ·I and D̂² = D̂·e^(−D̂): the (0,7) plane spins at exactly μ. This is a{' '}
              <i>localization</i> of the fixed-point equation to that block, not an independent derivation of
              W(1).
            </div>
          </div>
        </div>

        <div style={{ borderTop: '1px solid #1a2130', margin: '12px 0', paddingTop: 10 }}>
          <h3>Sonification</h3>
          <button className={audio ? 'btn active' : 'btn'} onClick={() => setAudio(!audio)}>
            {audio ? '🔊 sound on' : '🔈 muted — enable'}
          </button>
          <div className="mono small" style={{ marginTop: 6 }}>
            Ω → 800 Hz · tones {SpectrumAudio.freqs(beta).map((f) => f.toFixed(0)).join(', ')} Hz
          </div>
          <div className="small dim" style={{ marginTop: 4 }}>
            Beat period vs exact 3:4:5:{' '}
            <span className="value mono">
              {beat.periodSec === Infinity ? '∞ (locked)' : `${beat.periodSec.toFixed(2)} s`}
            </span>
            . At β = Ω/4 the chord locks; at the canonical β you hear slow beating.
          </div>
        </div>
      </div>
    </div>
  );
}
