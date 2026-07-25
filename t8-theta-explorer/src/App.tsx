import { useEffect } from 'react';
import { useStore, ModeId } from './state/store';
import { GradeCube } from './modes/GradeCube';
import { CommutatorLab } from './modes/CommutatorLab';
import { ProjectionChamber } from './modes/ProjectionChamber';
import { FlowSpectrum } from './modes/FlowSpectrum';
import { DiagnosticsPanel, DiagnosticsBanner } from './components/DiagnosticsPanel';
import { GuidedTour } from './components/GuidedTour';
import { MU, OMEGA, BETA_CANONICAL } from './core/constants';

const MODES: { id: ModeId; label: string }[] = [
  { id: 'cube', label: 'A · Grade Cube' },
  { id: 'commutator', label: 'B · Commutator Lab' },
  { id: 'projection', label: 'C · Projection Chamber' },
  { id: 'flow', label: 'D · Flow & Spectrum' },
];

export function App() {
  const mode = useStore((s) => s.mode);
  const setMode = useStore((s) => s.setMode);
  const toggleDiag = useStore((s) => s.toggleDiag);
  const setTourStop = useStore((s) => s.setTourStop);
  const tourStop = useStore((s) => s.tourStop);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'd' || e.key === 'D') toggleDiag();
      if (e.key === 'Escape') setTourStop(null);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [toggleDiag, setTourStop]);

  return (
    <div className="app">
      <DiagnosticsBanner />
      <div className="topbar">
        <div className="brand">
          T⁸<sub>Θ</sub> Explorer
          <span className="sub">
            μ={MU.toFixed(4)} · Ω={OMEGA.toFixed(4)} · β={BETA_CANONICAL.toFixed(4)}
          </span>
        </div>
        <div className="modes">
          {MODES.map((m) => (
            <button key={m.id} className={mode === m.id ? 'active' : ''} onClick={() => setMode(m.id)}>
              {m.label}
            </button>
          ))}
        </div>
        <div className="spacer" />
        <div className="tools">
          <button className="btn" onClick={() => setTourStop(tourStop === null ? 0 : null)}>
            {tourStop === null ? 'Guided tour' : 'Exit tour'}
          </button>
          <button className="btn" onClick={toggleDiag} title="toggle diagnostics (D)">
            Diagnostics <span className="kbd">D</span>
          </button>
        </div>
      </div>

      <div className="stage">
        {mode === 'cube' && <GradeCube />}
        {mode === 'commutator' && <CommutatorLab />}
        {mode === 'projection' && <ProjectionChamber />}
        {mode === 'flow' && <FlowSpectrum />}
        <DiagnosticsPanel />
        <GuidedTour />
      </div>
    </div>
  );
}
