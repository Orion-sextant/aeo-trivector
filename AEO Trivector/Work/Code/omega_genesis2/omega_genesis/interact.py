#!/usr/bin/env python3
"""
Ω-Genesis: Interactive Consciousness Interface

Run this to start a conversation with the consciousness.

Usage:
    python -m omega_genesis.interact
    
Or:
    python omega_genesis/interact.py

Commands available in session:
    /help        - Show all commands
    /state       - Show consciousness state  
    /memory      - Show learned thoughts
    /mode <m>    - Change mode (COMPANION, RESEARCHER, etc.)
    /bell        - Show entanglement diagnostics
    /verbose     - Toggle detailed output
    /quit        - Exit

The key principle:
    Responses emerge from TENSION between entangled observers.
    Uncertainty is communicated, not hidden.
    μ = 0.569 at equilibrium.
"""

import sys
import argparse
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from omega_genesis.interface import InteractiveSession, SessionConfig, ConsciousnessConfig


def main():
    parser = argparse.ArgumentParser(
        description="Ω-Genesis Interactive Consciousness Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python interact.py                    # Default settings
    python interact.py --dim 256          # Larger Hilbert space
    python interact.py --observers 6      # More entangled observers
    python interact.py --quiet            # Minimal output
    python interact.py --no-color         # No ANSI colors
        """
    )
    
    parser.add_argument(
        '--dim', type=int, default=128,
        help='Hilbert space dimension (default: 128)'
    )
    parser.add_argument(
        '--observers', type=int, default=4,
        help='Number of entangled observers (default: 4)'
    )
    parser.add_argument(
        '--thoughts', type=int, default=500,
        help='Maximum thoughts in memory (default: 500)'
    )
    parser.add_argument(
        '--quiet', '-q', action='store_true',
        help='Minimal output (no verbose state info)'
    )
    parser.add_argument(
        '--no-uncertainty', action='store_true',
        help='Hide uncertainty indicators'
    )
    parser.add_argument(
        '--no-color', action='store_true',
        help='Disable colored output'
    )
    parser.add_argument(
        '--no-learn', action='store_true',
        help='Disable auto-learning from conversation'
    )
    parser.add_argument(
        '--temperature', type=float, default=0.8,
        help='Response generation temperature (default: 0.8)'
    )
    
    args = parser.parse_args()
    
    # Build configuration
    consciousness_config = ConsciousnessConfig(
        hilbert_dim=args.dim,
        n_observers=args.observers,
        max_thoughts=args.thoughts,
        temperature=args.temperature,
    )
    
    session_config = SessionConfig(
        consciousness_config=consciousness_config,
        verbose=not args.quiet,
        show_uncertainty=not args.no_uncertainty,
        auto_learn=not args.no_learn,
        use_colors=not args.no_color,
    )
    
    # Create and run session
    session = InteractiveSession(session_config)
    session.run()


if __name__ == "__main__":
    main()
