import { useMemo, useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Line, Html } from '@react-three/drei';
import * as THREE from 'three';
import { COORDS, cornerPosition } from '../core/coords';
import { couplings, Coupling, weylPhase, wrapPi } from '../core/couplings';
import { splitTheta } from '../core/theta';
import { frobeniusSq } from '../core/linalg';
import { useStore } from '../state/store';
import { COLORS } from '../core/constants';
import { ColorWheel } from '../components/ColorWheel';
import { Formula } from '../components/Formula';

const CUBE = 1.7; // half-extent

function vertexPos(index: number, explode: number): [number, number, number] {
  const c = COORDS[index];
  const base = cornerPosition(c.corner, CUBE);
  // Explode by grade: lift each grade layer vertically (grade as height).
  const gradeLift = (c.grade - 1.5) * explode * 2.2;
  return [base[0], base[1] + gradeLift, base[2]];
}

/** A live phase ring at a vertex: glowing ring + marker at θ_k. */
function PhaseRing({ index, explode }: { index: number; explode: number }) {
  const phase = useStore((s) => s.phases[index]);
  const setPhase = useStore((s) => s.setPhase);
  const coord = COORDS[index];
  const pos = vertexPos(index, explode);
  const groupRef = useRef<THREE.Group>(null);
  const [hover, setHover] = useState(false);
  const [dragging, setDragging] = useState(false);
  const color = coord.grade === 0 ? COLORS.mu : coord.grade === 3 ? COLORS.mu : coord.grade === 1 ? COLORS.omega : COLORS.beta;

  const ringGeo = useMemo(() => new THREE.TorusGeometry(0.26, 0.02, 8, 40), []);
  const markerAngle = phase;
  const mx = 0.26 * Math.cos(markerAngle);
  const my = 0.26 * Math.sin(markerAngle);

  return (
    <group
      ref={groupRef}
      position={pos}
      onPointerOver={(e) => {
        e.stopPropagation();
        setHover(true);
      }}
      onPointerOut={() => setHover(false)}
      onPointerDown={(e) => {
        e.stopPropagation();
        (e.target as Element).setPointerCapture?.(e.pointerId);
        setDragging(true);
      }}
      onPointerUp={(e) => {
        e.stopPropagation();
        setDragging(false);
      }}
      onPointerMove={(e) => {
        if (!dragging) return;
        e.stopPropagation();
        // Advance phase from horizontal drag.
        setPhase(index, phase + e.movementX * 0.04);
      }}
    >
      <mesh geometry={ringGeo}>
        <meshBasicMaterial color={color} transparent opacity={hover || dragging ? 1 : 0.7} />
      </mesh>
      {/* marker */}
      <mesh position={[mx, my, 0]}>
        <sphereGeometry args={[0.05, 12, 12]} />
        <meshBasicMaterial color="#ffffff" />
      </mesh>
      {/* vertex core */}
      <mesh>
        <sphereGeometry args={[0.06, 12, 12]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.6} />
      </mesh>
      <Html center distanceFactor={9} position={[0, 0.42, 0]} style={{ pointerEvents: 'none' }}>
        <div style={{ fontSize: 12, color: '#dbe5f2', whiteSpace: 'nowrap', textShadow: '0 1px 3px #000' }}>
          <span className="mono">θ{sub(index)}</span> <span dangerouslySetInnerHTML={{ __html: renderLabel(coord.label) }} />
        </div>
      </Html>
    </group>
  );
}

function sub(n: number) {
  return String(n).replace(/[0-9]/g, (d) => '₀₁₂₃₄₅₆₇₈₉'[+d]);
}
function renderLabel(label: string) {
  // e_{23} -> e<sub>23</sub>
  return label.replace(/_\{([^}]+)\}/g, '<sub>$1</sub>');
}

function CouplingBridge({
  c,
  explode,
  onHover,
}: {
  c: Coupling;
  explode: number;
  onHover: (c: Coupling | null, x: number, y: number) => void;
}) {
  const a = vertexPos(c.i, explode);
  const b = vertexPos(c.j, explode);
  const mag = Math.abs(c.value);
  const width = 1 + mag * 6;
  return (
    <Line
      points={[a, b]}
      color={c.color}
      lineWidth={width}
      transparent
      opacity={0.35 + Math.min(0.6, mag)}
      onPointerOver={(e) => {
        e.stopPropagation();
        onHover(c, e.clientX, e.clientY);
      }}
      onPointerMove={(e) => onHover(c, e.clientX, e.clientY)}
      onPointerOut={() => onHover(null, 0, 0)}
    />
  );
}

function Scene({ onHover }: { onHover: (c: Coupling | null, x: number, y: number) => void }) {
  const beta = useStore((s) => s.beta);
  const xray = useStore((s) => s.xray);
  const explode = useStore((s) => s.explode);
  const cps = useMemo(() => couplings(beta), [beta]);
  const visible = cps.filter((c) => (xray === 'off' ? true : xray === 'swap' ? c.kind !== 'beta' : c.kind === 'beta'));

  return (
    <>
      <ambientLight intensity={0.6} />
      <pointLight position={[5, 6, 5]} intensity={40} />
      {visible.map((c) => (
        <CouplingBridge key={`${c.i}-${c.j}`} c={c} explode={explode} onHover={onHover} />
      ))}
      {COORDS.map((c) => (
        <PhaseRing key={c.index} index={c.index} explode={explode} />
      ))}
      <OrbitControls enablePan={false} minDistance={3.5} maxDistance={12} makeDefault />
    </>
  );
}

/** Slow auto-tumble for the idle home scene. */
function Rig() {
  useFrame(({ camera, clock }) => {
    if (!(window as any).__cubeUserInteracting) {
      const t = clock.getElapsedTime() * 0.08;
      const r = 6.5;
      camera.position.x = Math.sin(t) * r;
      camera.position.z = Math.cos(t) * r;
      camera.position.y = 2.4;
      camera.lookAt(0, 0, 0);
    }
  });
  return null;
}

export function GradeCube() {
  const xray = useStore((s) => s.xray);
  const setXray = useStore((s) => s.setXray);
  const explode = useStore((s) => s.explode);
  const setExplode = useStore((s) => s.setExplode);
  const beta = useStore((s) => s.beta);
  const [tip, setTip] = useState<{ c: Coupling; x: number; y: number } | null>(null);

  const { swap, pres } = useMemo(() => splitTheta(beta), [beta]);
  const swapE = frobeniusSq(swap);
  const presE = frobeniusSq(pres);
  const total = swapE + presE;
  const swapPct = (100 * swapE) / total;
  const presPct = (100 * presE) / total;

  const onHover = (c: Coupling | null, x: number, y: number) => {
    setTip(c ? { c, x, y } : null);
    (window as any).__cubeUserInteracting = !!c || (window as any).__cubeUserInteracting;
  };

  return (
    <div className="canvas-wrap">
      <Canvas
        camera={{ position: [6.5, 2.4, 0], fov: 45 }}
        onPointerDown={() => ((window as any).__cubeUserInteracting = true)}
      >
        <Rig />
        <Scene onHover={onHover} />
      </Canvas>

      {/* Left: what this is */}
      <div className="overlay tl panel" style={{ maxWidth: 340 }}>
        <span className="tag metaphor">visualization metaphor</span>
        <h3 style={{ marginTop: 10 }}>Grade Cube</h3>
        <p className="hint">
          The 8 coordinates are the subsets of {'{1,2,3}'}, so they sit at the cube's corners. The whole
          deformation matrix is then <b className="swatch-mu">four space diagonals</b> plus{' '}
          <b className="swatch-beta">two spinning triangles</b>.
        </p>
        <div style={{ margin: '10px 0', fontSize: 12, lineHeight: 1.7 }}>
          <div>
            <span style={{ color: COLORS.mu }}>●</span> μ diagonal — scalar ↔ pseudoscalar
          </div>
          <div>
            <span style={{ color: COLORS.omega }}>●</span> Ω diagonals — grade-1 ↔ complementary grade-2
          </div>
          <div>
            <span style={{ color: COLORS.beta }}>●</span> β triangles — cyclic βJ on each grade layer
          </div>
        </div>
        <p className="hint" style={{ borderTop: '1px solid #1a2130', paddingTop: 8 }}>
          Drag a vertex ring to advance its phase θ<sub>k</sub> — nothing else moves. The θ's are{' '}
          <i>independent coordinates</i>; the coupling lives in the algebra of translations, which the
          Commutator Lab makes tangible.
        </p>
        <p className="small dim" style={{ borderTop: '1px solid #1a2130', paddingTop: 8, marginBottom: 0 }}>
          Honesty: the Ω cross-pairing is uniform along basis-aligned indices — it is <i>not</i> the Hodge
          star (which carries alternating signs). "Canonical" names this specific ansatz (grade-ordered basis
          + the triple μ, Ω, β); no uniqueness is claimed. The (0,7) block decouples only in this privileged
          grade basis — the spectrum is basis-invariant, the block structure is not.
        </p>
      </div>

      {/* Right: controls */}
      <div className="overlay br panel" style={{ minWidth: 280 }}>
        <h3>X-ray the matrix</h3>
        <div className="modes" style={{ marginBottom: 10 }}>
          {(['off', 'swap', 'pres'] as const).map((x) => (
            <button key={x} className={xray === x ? 'active' : ''} onClick={() => setXray(x)}>
              {x === 'off' ? 'all' : x === 'swap' ? 'Θ_swap' : 'Θ_pres'}
            </button>
          ))}
        </div>
        <div className="small dim" style={{ marginBottom: 4 }}>
          energy split ‖·‖² (live)
        </div>
        <div className="energybar">
          <div className="swap" style={{ width: `${swapPct}%` }} />
          <div className="pres" style={{ width: `${presPct}%` }} />
        </div>
        <div className="row small mono" style={{ justifyContent: 'space-between' }}>
          <span>
            swap <span className="value">{swapPct.toFixed(1)}%</span>
          </span>
          <span>
            pres <span className="value">{presPct.toFixed(1)}%</span>
          </span>
        </div>
        <div className="row">
          <label>explode</label>
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={explode}
            onChange={(e) => setExplode(+e.target.value)}
          />
        </div>
        <div className="small dim">grade as height → the Hasse diagram of subsets (grades 0,1,2,3)</div>
      </div>

      {tip && (
        <div className="tooltip" style={{ left: tip.x + 14, top: tip.y + 14 }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <ColorWheel phase={weylPhase(tip.c.value)} size={64} />
            <div>
              <div className="mono">
                Θ[{tip.c.i},{tip.c.j}] = <span className="value">{tip.c.value.toFixed(6)}</span>
              </div>
              <div className="mono small">
                Weyl phase e<sup>2πiΘ</sup> = {((wrapPi(weylPhase(tip.c.value)) * 180) / Math.PI).toFixed(1)}°
              </div>
              <div className="small dim" style={{ marginTop: 4, maxWidth: 150 }}>
                {tip.c.role}
              </div>
            </div>
          </div>
          <div className="small" style={{ marginTop: 6 }}>
            <Formula tex={`U_iU_j = e^{2\\pi i\\,\\Theta_{ij}}\\,U_jU_i`} />
          </div>
        </div>
      )}
    </div>
  );
}
