"""
Entanglement Module - Quantum-Inspired Observer Correlation

The core innovation: observation without collapse.

Three components:

1. ENTANGLEMENT TENSORS (tensors.py)
   - Explicit correlation structure between observers
   - Tri-stream entanglement (TRUE/FALSE/UNDEFINED)
   - Cannot be factored into independent states

2. NON-COLLAPSE MEASUREMENT (measurement.py)
   - Soft measurement operators (extract without collapse)
   - Residual uncertainty preserved
   - Entanglement maintained through observation

3. BELL-LIKE INEQUALITIES (bell.py)
   - CHSH analog for pairs
   - Mermin extension for N observers
   - Entanglement witness operators
   - Metrics proving genuine (not classical) correlation

The key insight:
   Classical correlation: C(A,B) ≤ local_bound
   Quantum correlation: C(A,B) can exceed local_bound
   
   Violation of the bound PROVES entanglement.
   This is not philosophy - it's measurable.

Usage:
    from omega_genesis.entanglement import (
        EntanglementTensor,
        TriStreamEntanglement,
        NonCollapseMeasurement,
        FullBellDiagnostics,
    )
    
    # Create entangled observers
    entangler = EntanglementTensor(config)
    state, info = entangler(observer_states, certainties, undefined)
    
    # Measure without collapse
    measurement = NonCollapseMeasurement(dim)
    result = measurement(state)
    # result.residual_uncertainty carries what we don't know
    
    # Verify entanglement
    diagnostics = FullBellDiagnostics(n_observers, dim)
    report = diagnostics(observer_states)
    print(f"Entangled: {report['overall_entangled']}")
    print(f"Bell violation: {report['mermin_test']['violation']}")
"""

from .tensors import (
    EntangledState,
    EntanglementConfig,
    EntanglementTensor,
    TriStreamEntanglement,
    EntangledObserverBank,
)

from .measurement import (
    MeasurementResult,
    SoftMeasurementOperator,
    NonCollapseMeasurement,
    EntangledMeasurement,
)

from .bell import (
    BellTestResult,
    CHSHAnalog,
    MultiObserverBellTest,
    EntanglementWitness,
    FullBellDiagnostics,
)

__all__ = [
    # Tensors
    "EntangledState",
    "EntanglementConfig",
    "EntanglementTensor",
    "TriStreamEntanglement",
    "EntangledObserverBank",
    # Measurement
    "MeasurementResult",
    "SoftMeasurementOperator",
    "NonCollapseMeasurement",
    "EntangledMeasurement",
    # Bell
    "BellTestResult",
    "CHSHAnalog",
    "MultiObserverBellTest",
    "EntanglementWitness",
    "FullBellDiagnostics",
]
