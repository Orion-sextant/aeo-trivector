import { useMemo, useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Line } from '@react-three/drei';
import * as THREE from 'three';
import { useStore } from '../state/store';
import { eigenPlanes } from '../core/theta';
import { FlowEngine } from '../core/flow';
import { COORDS } from '../core/coords';
import { COLORS } from '../core/constants';

type ViewFamily = 'slice' | 'morph';

const TRAIL = 900;

/** A 3×8 orthonormal projection frame, steerable via Givens rotations (Stiefel path). */
function makeFrame(sliceIdx: [number, number, number]): number[][] {
  const P = [new Array(8).fill(0), new Array(8).fill(0), new Array(8).fill(0)];
  P[0][sliceIdx[0]] = 1;
  P[1][sliceIdx[1]] = 1;
  P[2][sliceIdx[2]] = 1;
  return P;
}

function givensRight(P: number[][], p: number, q: number, angle: number): number[][] {
  const c = Math.cos(angle);
  const s = Math.sin(angle);
  return P.map((row) => {
    const out = row.slice();
    out[p] = row[p] * c + row[q] * s;
    out[q] = -row[p] * s + row[q] * c;
    return out;
  });
}

function FlowPoints({
  family,
  sliceIdx,
  frame,
  hueCoord,
  sizeCoord,
  speed,
}: {
  family: ViewFamily;
  sliceIdx: [number, number, number];
  frame: number[][];
  hueCoord: number;
  sizeCoord: number;
  speed: number;
}) {
  const beta = useStore((s) => s.beta);
  const planes = useMemo(() => eigenPlanes(beta), [beta]);
  const engine = useRef(new FlowEngine(planes));
  engine.current.setPlanes(planes);

  const lineRef = useRef<any>(null);
  const headRef = useRef<THREE.Mesh>(null);
  const trail = useRef<THREE.Vector3[]>([]);

  const project = (x: number[]): THREE.Vector3 => {
    if (family === 'slice') {
      return new THREE.Vector3(x[sliceIdx[0]], x[sliceIdx[1]], x[sliceIdx[2]]).multiplyScalar(1.4);
    }
    const v = frame.map((row) => row.reduce((s, w, k) => s + w * x[k], 0));
    return new THREE.Vector3(v[0], v[1], v[2]).multiplyScalar(1.4);
  };

  useFrame((_, dt) => {
    engine.current.step(Math.min(dt, 0.05), speed);
    const x = engine.current.state();
    const p = project(x);
    trail.current.push(p);
    if (trail.current.length > TRAIL) trail.current.shift();
    if (lineRef.current && trail.current.length > 1) {
      lineRef.current.geometry.setFromPoints(trail.current);
    }
    if (headRef.current) {
      headRef.current.position.copy(p);
      const hue = (((x[hueCoord] + 2) / 4) * 360) % 360;
      const sz = 0.08 + Math.max(0, (x[sizeCoord] + 2) / 4) * 0.14;
      headRef.current.scale.setScalar(sz / 0.1);
      (headRef.current.material as THREE.MeshBasicMaterial).color.setHSL(hue / 360, 0.8, 0.6);
    }
  });

  return (
    <>
      <line ref={lineRef as any}>
        <bufferGeometry />
        <lineBasicMaterial color={COLORS.omega} transparent opacity={0.55} />
      </line>
      <mesh ref={headRef}>
        <sphereGeometry args={[0.1, 16, 16]} />
        <meshBasicMaterial color="#ffffff" />
      </mesh>
    </>
  );
}

function CubeFrame() {
  const R = 2.0;
  const corners: [number, number, number][] = [];
  for (let i = 0; i < 8; i++) corners.push([(i & 1 ? 1 : -1) * R, (i & 2 ? 1 : -1) * R, (i & 4 ? 1 : -1) * R]);
  const edges = [
    [0, 1], [0, 2], [0, 4], [1, 3], [1, 5], [2, 3], [2, 6], [3, 7], [4, 5], [4, 6], [5, 7], [6, 7],
  ];
  return (
    <>
      {edges.map(([a, b], k) => (
        <Line key={k} points={[corners[a], corners[b]]} color="#1c2636" lineWidth={1} />
      ))}
    </>
  );
}

export function ProjectionChamber() {
  const [family, setFamily] = useState<ViewFamily>('morph');
  const [sliceIdx, setSliceIdx] = useState<[number, number, number]>([0, 7, 3]);
  const [angles, setAngles] = useState<[number, number, number]>([0.6, 0.9, 0.3]);
  const [hueCoord, setHueCoord] = useState(4);
  const [sizeCoord, setSizeCoord] = useState(6);
  const [speed, setSpeed] = useState(1);

  const frame = useMemo(() => {
    let P = makeFrame(sliceIdx);
    P = givensRight(P, sliceIdx[0], 4, angles[0]);
    P = givensRight(P, sliceIdx[1], 5, angles[1]);
    P = givensRight(P, sliceIdx[2], 1, angles[2]);
    return P;
  }, [sliceIdx, angles]);

  const axisLabels = ['X', 'Y', 'Z'];

  return (
    <div className="canvas-wrap">
      <Canvas camera={{ position: [4.5, 3.5, 5.5], fov: 45 }}>
        <ambientLight intensity={0.7} />
        <CubeFrame />
        <FlowPoints
          family={family}
          sliceIdx={sliceIdx}
          frame={frame}
          hueCoord={hueCoord}
          sizeCoord={sizeCoord}
          speed={speed}
        />
        <OrbitControls enablePan={false} makeDefault />
      </Canvas>

      <div className="overlay tl panel" style={{ maxWidth: 330 }}>
        <span className={`tag ${family === 'slice' ? 'slice' : 'projection'}`}>
          {family === 'slice' ? 'coordinate slice' : 'orthogonal projection ℝ⁸→ℝ³'}
        </span>
        <h3 style={{ marginTop: 10 }}>Projection Chamber</h3>
        <p className="hint">
          The state is the 8-D lift x(t) = e<sup>tΘ</sup>x₀ of a point on T⁸, rotating each invariant plane
          at its own frequency. Everything on screen is a projection of that 8-D curve — never more than 3
          spatial dimensions.
        </p>
        <div className="modes" style={{ marginTop: 8 }}>
          <button className={family === 'morph' ? 'active' : ''} onClick={() => setFamily('morph')}>
            frame morph
          </button>
          <button className={family === 'slice' ? 'active' : ''} onClick={() => setFamily('slice')}>
            coordinate slice
          </button>
        </div>
      </div>

      <div className="overlay br panel" style={{ minWidth: 300, maxHeight: '84vh', overflow: 'auto' }}>
        {family === 'slice' ? (
          <>
            <h3>Slice — 3 of 8 coordinates</h3>
            {(['X', 'Y', 'Z'] as const).map((ax, a) => (
              <div className="row" key={ax}>
                <label>{ax} axis</label>
                <select
                  value={sliceIdx[a]}
                  onChange={(e) => {
                    const ni = [...sliceIdx] as [number, number, number];
                    ni[a] = +e.target.value;
                    setSliceIdx(ni);
                  }}
                >
                  {COORDS.map((c) => (
                    <option key={c.index} value={c.index}>
                      θ{c.index} · {c.plain}
                    </option>
                  ))}
                </select>
              </div>
            ))}
            <div className="small dim">Plots three components of the projected 8-D state inside the wire cube.</div>
          </>
        ) : (
          <>
            <h3>Steer the frame (Stiefel path)</h3>
            {angles.map((ang, k) => (
              <div className="row" key={k}>
                <label>rot {k + 1}</label>
                <input
                  type="range"
                  min={-Math.PI}
                  max={Math.PI}
                  step={0.01}
                  value={ang}
                  onChange={(e) => {
                    const na = [...angles] as [number, number, number];
                    na[k] = +e.target.value;
                    setAngles(na);
                  }}
                />
              </div>
            ))}
            <div className="small dim" style={{ margin: '8px 0 4px' }}>
              axis mixture — |weight| on each of the 8 coordinates
            </div>
            {frame.map((row, a) => (
              <div key={a} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <span className="mono small" style={{ width: 14 }}>
                  {axisLabels[a]}
                </span>
                <div className="legend-bars">
                  {row.map((w, k) => (
                    <i
                      key={k}
                      style={{
                        height: `${Math.abs(w) * 20}px`,
                        background:
                          COORDS[k].grade === 0 || COORDS[k].grade === 3
                            ? COLORS.mu
                            : COORDS[k].grade === 1
                            ? COLORS.omega
                            : COLORS.beta,
                        opacity: 0.4 + Math.abs(w) * 0.6,
                      }}
                      title={`${COORDS[k].plain}: ${w.toFixed(2)}`}
                    />
                  ))}
                </div>
              </div>
            ))}
          </>
        )}

        <div style={{ borderTop: '1px solid #1a2130', margin: '12px 0 8px', paddingTop: 8 }}>
          <h3>Channel map — dimensions beyond 3</h3>
          <div className="row">
            <label>hue ←</label>
            <select value={hueCoord} onChange={(e) => setHueCoord(+e.target.value)}>
              {COORDS.map((c) => (
                <option key={c.index} value={c.index}>
                  θ{c.index} · {c.plain}
                </option>
              ))}
            </select>
          </div>
          <div className="row">
            <label>size ←</label>
            <select value={sizeCoord} onChange={(e) => setSizeCoord(+e.target.value)}>
              {COORDS.map((c) => (
                <option key={c.index} value={c.index}>
                  θ{c.index} · {c.plain}
                </option>
              ))}
            </select>
          </div>
          <div className="small dim">
            Spectral content → audio lives in Mode D. The app encodes extra dimensions; it never claims more
            than 3 spatial ones.
          </div>
          <div className="row">
            <label>speed</label>
            <input type="range" min={0} max={3} step={0.01} value={speed} onChange={(e) => setSpeed(+e.target.value)} />
          </div>
        </div>
      </div>
    </div>
  );
}
