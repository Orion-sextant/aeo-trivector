import { useEffect, useMemo, useRef, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Line } from '@react-three/drei';
import { useStore } from '../state/store';
import { buildTheta } from '../core/theta';
import { absMatrix } from '../core/couplings';
import { COORDS } from '../core/coords';
import { COLORS } from '../core/constants';
import { ColorWheel } from '../components/ColorWheel';
import { Formula } from '../components/Formula';
import { loopAt, loopPhase } from './commutatorMath';

interface Preset {
  name: string;
  pair: [number, number];
  note: string;
}
const PRESETS: Preset[] = [
  { name: '(0,7) — loud', pair: [0, 7], note: 'μ coupling: ≈204° per unit cell' },
  { name: 'grade-1 internal — quiet', pair: [1, 2], note: 'phase from β/√3' },
  { name: 'uncoupled — silent', pair: [0, 1], note: 'Θ = 0, phase 0' },
];

/** The donut view: 2-torus with the loop path and a phase-twist marker. */
function Donut({ a, b, t, theta }: { a: number; b: number; t: number; theta: number }) {
  const R = 1.6;
  const r = 0.55;
  const toXYZ = (u: number, v: number): [number, number, number] => {
    const au = u * 2 * Math.PI;
    const av = v * 2 * Math.PI;
    return [(R + r * Math.cos(av)) * Math.cos(au), r * Math.sin(av), (R + r * Math.cos(av)) * Math.sin(au)];
  };
  const pathPts = useMemo(() => {
    const pts: [number, number, number][] = [];
    for (let s = 0; s <= 4; s += 0.02) {
      const { pos } = loopAt(s, a, b, theta);
      pts.push(toXYZ(pos[0], pos[1]));
    }
    return pts;
  }, [a, b, theta]);
  const cur = loopAt(t, a, b, theta);
  const marker = toXYZ(cur.pos[0], cur.pos[1]);
  // twist tick: a short segment whose orientation encodes accumulated phase
  const tickLen = 0.32;
  const tick: [number, number, number][] = [
    [marker[0], marker[1] - (tickLen / 2) * Math.cos(cur.phase), marker[2]],
    [marker[0], marker[1] + (tickLen / 2) * Math.cos(cur.phase), marker[2]],
  ];

  return (
    <Canvas camera={{ position: [0, 3.2, 4.2], fov: 45 }}>
      <ambientLight intensity={0.7} />
      <pointLight position={[4, 6, 4]} intensity={30} />
      <mesh rotation={[0, 0, 0]}>
        <torusGeometry args={[R, r, 24, 80]} />
        <meshStandardMaterial color="#141c2a" wireframe opacity={0.5} transparent />
      </mesh>
      <Line points={pathPts} color={COLORS.omega} lineWidth={2} />
      <Line points={tick} color={`hsl(${((cur.phase % (2 * Math.PI)) / (2 * Math.PI)) * 360} 80% 60%)`} lineWidth={4} />
      <mesh position={marker}>
        <sphereGeometry args={[0.09, 16, 16]} />
        <meshBasicMaterial color="#ffffff" />
      </mesh>
      <OrbitControls enablePan={false} makeDefault />
    </Canvas>
  );
}

/** Flat fundamental square with the rectangular loop and a running marker. */
function FlatSquare({
  a,
  b,
  t,
  onSet,
}: {
  a: number;
  b: number;
  t: number;
  theta: number;
  onSet: (a: number, b: number) => void;
}) {
  const size = 240;
  const pad = 24;
  const inner = size - pad * 2;
  const X = (u: number) => pad + u * inner;
  const Y = (v: number) => size - pad - v * inner;
  const cur = loopAt(t, a, b, 0).pos;
  const ref = useRef<SVGSVGElement>(null);
  const [drag, setDrag] = useState(false);

  const set = (e: React.PointerEvent) => {
    const rect = ref.current!.getBoundingClientRect();
    const u = (e.clientX - rect.left - pad) / inner;
    const v = (size - (e.clientY - rect.top) - pad) / inner;
    onSet(Math.max(0.05, Math.min(1, u)), Math.max(0.05, Math.min(1, v)));
  };

  return (
    <svg
      ref={ref}
      width={size}
      height={size}
      style={{ touchAction: 'none', cursor: 'crosshair' }}
      onPointerDown={(e) => {
        setDrag(true);
        set(e);
      }}
      onPointerMove={(e) => drag && set(e)}
      onPointerUp={() => setDrag(false)}
      onPointerLeave={() => setDrag(false)}
    >
      {/* cell */}
      <rect x={pad} y={pad} width={inner} height={inner} fill="#0a0e15" stroke="#1c2434" />
      {/* wraparound hint edges */}
      {[0.25, 0.5, 0.75].map((g) => (
        <g key={g} stroke="#141b28">
          <line x1={X(g)} y1={pad} x2={X(g)} y2={size - pad} />
          <line x1={pad} y1={Y(g)} x2={size - pad} y2={Y(g)} />
        </g>
      ))}
      {/* loop rectangle */}
      <rect x={X(0)} y={Y(b)} width={X(a) - X(0)} height={Y(0) - Y(b)} fill="rgba(63,216,224,0.10)" stroke={COLORS.omega} strokeWidth={1.5} />
      {/* handle */}
      <circle cx={X(a)} cy={Y(b)} r={6} fill={COLORS.omega} />
      {/* running marker */}
      <circle cx={X(cur[0])} cy={Y(cur[1])} r={5} fill="#fff" />
      {/* axis labels */}
      <text x={X(1)} y={size - 6} textAnchor="end" fontSize={10} fill="#8794a8">
        θ_i →
      </text>
      <text x={6} y={Y(1) + 4} fontSize={10} fill="#8794a8">
        θ_j ↑
      </text>
    </svg>
  );
}

/** 28-pair triangular heatmap doubling as the pair selector. */
function Heatmap() {
  const beta = useStore((s) => s.beta);
  const pair = useStore((s) => s.pair);
  const setPair = useStore((s) => s.setPair);
  const M = useMemo(() => absMatrix(beta), [beta]);
  const maxV = Math.max(...M.flat());
  const cell = 26;
  return (
    <svg width={cell * 8 + 30} height={cell * 8 + 30}>
      {COORDS.map((c, i) => (
        <text key={`r${i}`} x={4} y={30 + i * cell + cell / 2 + 3} fontSize={9} fill="#8794a8" className="mono">
          {c.plain}
        </text>
      ))}
      {COORDS.map((c, j) => (
        <text key={`c${j}`} x={30 + j * cell + cell / 2} y={16} fontSize={9} fill="#8794a8" textAnchor="middle" className="mono">
          {c.plain}
        </text>
      ))}
      {M.map((row, i) =>
        row.map((v, j) => {
          if (j <= i) return null;
          const on = v / maxV;
          const sel = (pair[0] === i && pair[1] === j) || (pair[0] === j && pair[1] === i);
          return (
            <rect
              key={`${i}-${j}`}
              x={30 + j * cell}
              y={30 + i * cell}
              width={cell - 2}
              height={cell - 2}
              rx={3}
              fill={v < 1e-9 ? '#0c1119' : `rgba(63,216,224,${0.12 + 0.85 * on})`}
              stroke={sel ? '#fff' : '#111722'}
              strokeWidth={sel ? 2 : 1}
              style={{ cursor: 'pointer' }}
              onClick={() => setPair([i, j])}
            >
              <title>
                Θ[{i},{j}] = {buildTheta(beta)[i][j].toFixed(4)}
              </title>
            </rect>
          );
        }),
      )}
    </svg>
  );
}

export function CommutatorLab() {
  const pair = useStore((s) => s.pair);
  const setPair = useStore((s) => s.setPair);
  const beta = useStore((s) => s.beta);
  const [a, setA] = useState(1);
  const [b, setB] = useState(1);
  const [t, setT] = useState(4);
  const [playing, setPlaying] = useState(false);
  const raf = useRef<number>();

  const [i, j] = pair;
  const theta = buildTheta(beta)[i][j];
  const finalPhase = loopPhase(a, b, theta);
  const cur = loopAt(t, a, b, theta);

  useEffect(() => {
    if (!playing) return;
    let last = performance.now();
    const tick = (now: number) => {
      const dt = (now - last) / 1000;
      last = now;
      setT((prev) => {
        const nx = prev + dt * 1.1;
        if (nx >= 4) {
          setPlaying(false);
          return 4;
        }
        return nx;
      });
      raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current!);
  }, [playing]);

  const play = () => {
    setT(0);
    setPlaying(true);
  };

  return (
    <div className="canvas-wrap" style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 0 }}>
      {/* Left: donut + square + needle */}
      <div style={{ position: 'relative' }}>
        <Donut a={a} b={b} t={t} theta={theta} />
        <div className="overlay tl panel" style={{ maxWidth: 300 }}>
          <span className="tag slice">2-torus (θ_i, θ_j)</span>
          <h3 style={{ marginTop: 10 }}>Commutator Lab</h3>
          <p className="hint">
            A rectangular loop returns your <i>position</i> to the start — but not your <i>phase</i>. Drag the
            handle in the flat cell to size the loop, then press play.
          </p>
          <div style={{ marginTop: 8 }}>
            <Formula tex={`U_iU_j = e^{2\\pi i\\,\\Theta_{ij}}\\,U_jU_i`} block />
          </div>
        </div>

        {/* Flat square + needle bottom-left */}
        <div className="overlay bl panel" style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
          <div>
            <div className="small dim" style={{ marginBottom: 6 }}>
              flat fundamental cell · drag to size loop
            </div>
            <FlatSquare a={a} b={b} t={t} theta={theta} onSet={(na, nb) => { setA(na); setB(nb); }} />
          </div>
          <div style={{ textAlign: 'center' }}>
            <div className="small dim" style={{ marginBottom: 6 }}>
              accumulated phase
            </div>
            <ColorWheel phase={cur.phase} size={120} />
            <div className="mono" style={{ marginTop: 8, fontSize: 15 }}>
              {((cur.phase * 180) / Math.PI).toFixed(1)}°
            </div>
            <div className="small dim">
              lands at {((finalPhase * 180) / Math.PI).toFixed(1)}°
            </div>
            <button className="btn" style={{ marginTop: 8 }} onClick={play}>
              {playing ? 'tracing…' : '▶ trace loop'}
            </button>
          </div>
        </div>
      </div>

      {/* Right rail: controls, presets, heatmap */}
      <div className="panel" style={{ borderRadius: 0, borderTop: 'none', borderRight: 'none', borderBottom: 'none', overflow: 'auto' }}>
        <h3>
          Pair (θ<sub>{i}</sub>, θ<sub>{j}</sub>) — {COORDS[i].plain} · {COORDS[j].plain}
        </h3>
        <div className="mono" style={{ marginBottom: 10 }}>
          Θ[{i},{j}] = <span className="value">{theta.toFixed(6)}</span>
          <br />
          full-cell phase 2πΘ = <span className="value">{((2 * Math.PI * theta * 180) / Math.PI).toFixed(1)}°</span>
        </div>

        <div className="row">
          <label>area a·b</label>
          <input type="range" min={0.0025} max={1} step={0.0025} value={a * b}
            onChange={(e) => { const A = +e.target.value; const s = Math.sqrt(A); setA(s); setB(s); }} />
        </div>
        <div className="row small mono dim">
          a={a.toFixed(2)} · b={b.toFixed(2)} · area={(a * b).toFixed(3)} → phase {((finalPhase * 180) / Math.PI).toFixed(1)}°
        </div>
        <div className="small dim" style={{ marginBottom: 12 }}>
          Phase is exactly linear in enclosed area: 2πΘ·(a·b).
        </div>

        <h3>Contrast presets</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 14 }}>
          {PRESETS.map((p) => (
            <button key={p.name} className="btn" style={{ textAlign: 'left' }} onClick={() => { setPair(p.pair); setA(1); setB(1); setT(4); }}>
              <b>{p.name}</b>
              <div className="small dim">{p.note}</div>
            </button>
          ))}
        </div>

        <h3>All 28 pairs — |Θ_ij|</h3>
        <div className="small dim" style={{ marginBottom: 6 }}>
          Click to select. The four diagonals + two triangles are visible as the bright structure.
        </div>
        <Heatmap />
      </div>
    </div>
  );
}
