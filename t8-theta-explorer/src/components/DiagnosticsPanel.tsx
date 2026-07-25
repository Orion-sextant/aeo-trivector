import { useMemo } from 'react';
import { runDiagnostics, allPass } from '../core/diagnostics';
import { useStore } from '../state/store';

export function DiagnosticsBanner() {
  const beta = useStore((s) => s.beta);
  const checks = useMemo(() => runDiagnostics(beta), [beta]);
  if (allPass(checks)) return null;
  const failing = checks.filter((c) => !c.pass).map((c) => c.name).join(', ');
  return <div className="banner bad">DIAGNOSTIC FAILURE — {failing}. Numbers on screen are not trustworthy.</div>;
}

export function DiagnosticsPanel() {
  const show = useStore((s) => s.showDiag);
  const toggle = useStore((s) => s.toggleDiag);
  const beta = useStore((s) => s.beta);
  const checks = useMemo(() => runDiagnostics(beta), [beta]);
  if (!show) return null;
  const pass = allPass(checks);
  return (
    <div className="overlay tr panel diag" style={{ zIndex: 35 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <h3 style={{ margin: 0 }}>
          Diagnostics — measure, don't estimate{' '}
          <span className="dot" style={{ marginLeft: 6, verticalAlign: 'middle' }} />
          <span className={pass ? 'swatch-omega' : 'swatch-beta'} style={{ marginLeft: 6, fontSize: 12 }}>
            {pass ? 'ALL GREEN' : 'FAILURE'}
          </span>
        </h3>
        <button className="btn" onClick={toggle}>
          close
        </button>
      </div>
      <p className="hint" style={{ maxWidth: 480, marginTop: 0 }}>
        Every row is a direct numerical measurement compared against a closed form. Recomputed live at the
        current β = {beta.toFixed(6)}.
      </p>
      <table>
        <tbody>
          {checks.map((c) => (
            <tr key={c.id}>
              <td className="st">
                <span className={`dot ${c.pass ? 'ok' : 'bad'}`} />
              </td>
              <td>
                <div className="value">{c.name}</div>
                <div className="dim small">{c.detail}</div>
              </td>
              <td className="mono small" style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                {c.residual.toExponential(1)}
                <div className="dim">≤ {c.tol.toExponential(0)}</div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
