/**
 * A phase on a hue wheel with a needle. The Weyl phase e^(2πiΘ) is an element
 * of U(1); the wheel is the honest picture of that circle.
 */
export function ColorWheel({
  phase,
  size = 84,
  label,
}: {
  phase: number; // radians
  size?: number;
  label?: string;
}) {
  const r = size / 2;
  const inner = r - 10;
  const segs = 48;
  const arcs = Array.from({ length: segs }, (_, k) => {
    const a0 = (k / segs) * 2 * Math.PI;
    const a1 = ((k + 1) / segs) * 2 * Math.PI;
    const hue = (k / segs) * 360;
    const x0 = r + inner * Math.cos(a0 - Math.PI / 2);
    const y0 = r + inner * Math.sin(a0 - Math.PI / 2);
    const x1 = r + inner * Math.cos(a1 - Math.PI / 2);
    const y1 = r + inner * Math.sin(a1 - Math.PI / 2);
    const xo0 = r + r * Math.cos(a0 - Math.PI / 2);
    const yo0 = r + r * Math.sin(a0 - Math.PI / 2);
    const xo1 = r + r * Math.cos(a1 - Math.PI / 2);
    const yo1 = r + r * Math.sin(a1 - Math.PI / 2);
    return (
      <path
        key={k}
        d={`M ${x0} ${y0} L ${xo0} ${yo0} A ${r} ${r} 0 0 1 ${xo1} ${yo1} L ${x1} ${y1} A ${inner} ${inner} 0 0 0 ${x0} ${y0} Z`}
        fill={`hsl(${hue} 70% 55%)`}
        opacity={0.85}
      />
    );
  });
  const nx = r + inner * Math.cos(phase - Math.PI / 2);
  const ny = r + inner * Math.sin(phase - Math.PI / 2);
  const deg = (((phase % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI) * 180) / Math.PI;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {arcs}
      <circle cx={r} cy={r} r={inner} fill="#080b11" />
      <line
        className="wheel-needle"
        x1={r}
        y1={r}
        x2={nx}
        y2={ny}
        stroke="#eef4ff"
        strokeWidth={2}
        strokeLinecap="round"
      />
      <circle cx={r} cy={r} r={3} fill="#eef4ff" />
      <text x={r} y={r + inner - 2} textAnchor="middle" fontSize={9} fill="#8794a8">
        {label ?? `${deg.toFixed(0)}°`}
      </text>
    </svg>
  );
}
