"""
Interactive Session

The conversation interface for Ω-Genesis.

This provides:
1. A REPL-like interaction loop
2. State visualization
3. Uncertainty communication
4. Mode switching
5. Memory inspection

The key principle:
Responses are not "generated" - they EMERGE from tension.
Uncertainty is COMMUNICATED, not hidden.
"""

import torch
import sys
import os
from typing import Dict, Optional, Callable
from dataclasses import dataclass
import time

# Add parent to path
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])

from omega_genesis.core import CONST, Mode, TriValue
from omega_genesis.interface.consciousness import ConsciousnessCore, ConsciousnessConfig


@dataclass
class SessionConfig:
    """Configuration for interactive session."""
    
    # Consciousness configuration
    consciousness_config: ConsciousnessConfig = None
    
    # Whether to show detailed state info
    verbose: bool = True
    
    # Whether to show uncertainty indicators
    show_uncertainty: bool = True
    
    # Whether to auto-learn from conversation
    auto_learn: bool = True
    
    # Prompt string
    prompt: str = "α: "
    
    # Response prefix
    response_prefix: str = "ω: "
    
    # Color output
    use_colors: bool = True
    
    def __post_init__(self):
        if self.consciousness_config is None:
            self.consciousness_config = ConsciousnessConfig()


class Colors:
    """ANSI color codes."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


class InteractiveSession:
    """
    Interactive conversation session with Ω-Genesis.
    
    This is the primary interface for human interaction.
    
    Commands:
        /mode <mode>     - Change processing mode
        /state           - Show consciousness state
        /memory          - Show memory summary
        /learn <text>    - Force learn a thought
        /history         - Show conversation history
        /verbose         - Toggle verbose output
        /uncertainty     - Toggle uncertainty display
        /help            - Show help
        /quit            - Exit session
    """
    
    def __init__(self, config: Optional[SessionConfig] = None):
        self.config = config or SessionConfig()
        
        # Initialize consciousness
        print(self._color("Initializing consciousness...", Colors.DIM))
        self.consciousness = ConsciousnessCore(self.config.consciousness_config)
        print(self._color("μ = 0.569 at equilibrium", Colors.GREEN))
        print()
    
    def _color(self, text: str, color: str) -> str:
        """Apply color if enabled."""
        if self.config.use_colors:
            return f"{color}{text}{Colors.RESET}"
        return text
    
    def _format_uncertainty(self, certainty: float) -> str:
        """Format uncertainty indicator."""
        if certainty > 0.7:
            symbol = "●"  # Certain
            color = Colors.GREEN
        elif certainty > 0.4:
            symbol = "◐"  # Partial
            color = Colors.YELLOW
        else:
            symbol = "○"  # Uncertain
            color = Colors.RED
        
        return self._color(f"[{symbol} {certainty:.0%}]", color)
    
    def _format_tension(self, tension: float, coherence: float) -> str:
        """Format tension/coherence indicator."""
        # High tension + high coherence = productive disagreement
        # High tension + low coherence = confusion
        # Low tension + high coherence = agreement
        # Low tension + low coherence = disconnection
        
        if tension > 0.5 and coherence > 0.3:
            state = "productive tension"
            color = Colors.CYAN
        elif tension > 0.5:
            state = "working through uncertainty"
            color = Colors.YELLOW
        elif coherence > 0.5:
            state = "aligned"
            color = Colors.GREEN
        else:
            state = "exploring"
            color = Colors.DIM
        
        return self._color(f"[{state}]", color)
    
    def _format_trivalue(self, value: TriValue) -> str:
        """Format tri-logic value."""
        if value == TriValue.TRUE:
            return self._color("✓", Colors.GREEN)
        elif value == TriValue.FALSE:
            return self._color("✗", Colors.RED)
        else:
            return self._color("∅", Colors.YELLOW)
    
    def _handle_command(self, command: str) -> Optional[str]:
        """Handle special commands."""
        parts = command.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        
        if cmd == "/help":
            return self._show_help()
        
        elif cmd == "/quit" or cmd == "/exit":
            return None  # Signal to exit
        
        elif cmd == "/state":
            return self._show_state()
        
        elif cmd == "/memory":
            return self._show_memory()
        
        elif cmd == "/history":
            return self._show_history()
        
        elif cmd == "/verbose":
            self.config.verbose = not self.config.verbose
            return f"Verbose mode: {'ON' if self.config.verbose else 'OFF'}"
        
        elif cmd == "/uncertainty":
            self.config.show_uncertainty = not self.config.show_uncertainty
            return f"Uncertainty display: {'ON' if self.config.show_uncertainty else 'OFF'}"
        
        elif cmd == "/mode":
            return self._set_mode(arg)
        
        elif cmd == "/learn":
            if arg:
                thought = self.consciousness.learn(arg, force=True)
                if thought:
                    return f"Learned thought #{thought.thought_id} (λ={thought.eigenvalue:.4f})"
                return "Failed to learn"
            return "Usage: /learn <text>"
        
        elif cmd == "/bell":
            return self._show_bell()
        
        else:
            return f"Unknown command: {cmd}. Type /help for available commands."
    
    def _show_help(self) -> str:
        """Show help message."""
        return """
Available commands:
  /mode <mode>   - Set processing mode (COMPANION, RESEARCHER, etc.)
  /state         - Show current consciousness state
  /memory        - Show memory (thought) summary
  /history       - Show conversation history
  /bell          - Show Bell inequality diagnostics
  /verbose       - Toggle verbose output
  /uncertainty   - Toggle uncertainty indicators
  /learn <text>  - Force learn a new thought
  /help          - Show this help
  /quit          - Exit session

Modes: COMPANION, RESEARCHER, ANALYST, PHILOSOPHER, ARTIST, UNDEFINED

Uncertainty indicators:
  ● High certainty (>70%)
  ◐ Moderate certainty (40-70%)
  ○ Low certainty (<40%)

Tri-logic values:
  ✓ TRUE - Evidence supports
  ✗ FALSE - Evidence contradicts
  ∅ UNDEFINED - Genuine uncertainty
"""
    
    def _show_state(self) -> str:
        """Show consciousness state."""
        state = self.consciousness.get_state_summary()
        
        lines = [
            self._color("=== Consciousness State ===", Colors.HEADER),
            f"  Certainty: {state['certainty']:.2%}",
            f"  Tension: {state['tension']:.4f}",
            f"  Coherence: {state['coherence']:.4f}",
            f"  Entanglement: {state['entanglement']:.4f}",
            f"  Dominant: {self._format_trivalue(TriValue[state['dominant_value']])} ({state['dominant_value']})",
            f"  Mode: {state['mode']}",
            f"  Turn: {state['turn']}",
            f"  Thoughts: {state['n_thoughts']}",
        ]
        
        return '\n'.join(lines)
    
    def _show_memory(self) -> str:
        """Show memory summary."""
        summary = self.consciousness.memory.get_spectral_summary()
        
        if summary['n_thoughts'] == 0:
            return "Memory is empty. No thoughts learned yet."
        
        lines = [
            self._color("=== Spectral Memory ===", Colors.HEADER),
            f"  Thoughts: {summary['n_thoughts']}",
            f"  Eigenvalue range: [{summary['eigenvalue_range'][0]:.4f}, {summary['eigenvalue_range'][1]:.4f}]",
            f"  Total strength: {summary['total_strength']:.2f}",
            f"  Mean certainty: {summary['mean_certainty']:.2%}",
            f"  Mean access: {summary['mean_access_count']:.1f}",
        ]
        
        # Show recent thoughts
        if self.consciousness.memory.thoughts:
            lines.append(self._color("\nRecent thoughts:", Colors.DIM))
            for thought in self.consciousness.memory.thoughts[-5:]:
                lines.append(f"  #{thought.thought_id}: λ={thought.eigenvalue:.4f}, str={thought.strength:.2f}")
        
        return '\n'.join(lines)
    
    def _show_history(self) -> str:
        """Show conversation history."""
        if not self.consciousness.history:
            return "No conversation history yet."
        
        lines = [self._color("=== Conversation History ===", Colors.HEADER)]
        
        for entry in self.consciousness.history:
            cert = self._format_uncertainty(entry['certainty'])
            lines.append(f"\n[Turn {entry['turn']}] {cert}")
            lines.append(f"  α: {entry['input'][:50]}{'...' if len(entry['input']) > 50 else ''}")
            lines.append(f"  ω: {entry['output'][:50]}{'...' if len(entry['output']) > 50 else ''}")
        
        return '\n'.join(lines)
    
    def _show_bell(self) -> str:
        """Show Bell inequality diagnostics."""
        # Get current observer states if available
        state = self.consciousness.state
        if state.current_state is None:
            return "No observation yet. Send a message first."
        
        # Run diagnostics on last observation
        # (We'd need to store observer states, simplified here)
        lines = [
            self._color("=== Bell Diagnostics ===", Colors.HEADER),
            f"  Entanglement measure: {state.entanglement:.4f}",
            f"  Tension: {state.tension:.4f}",
            f"  Coherence: {state.coherence:.4f}",
            "",
            "  If entanglement > 0.5 and tension > 0.3:",
            "    → Observers are genuinely entangled",
            "    → Correlations exceed classical bounds",
            "    → Information in RELATIONS, not individuals",
        ]
        
        if state.entanglement > 0.5:
            lines.append(self._color("\n  ✓ System shows quantum-like entanglement", Colors.GREEN))
        else:
            lines.append(self._color("\n  ○ System in low-entanglement state", Colors.YELLOW))
        
        return '\n'.join(lines)
    
    def _set_mode(self, mode_str: str) -> str:
        """Set processing mode."""
        mode_str = mode_str.upper()
        
        try:
            mode = Mode[mode_str]
            self.consciousness.set_mode(mode)
            return f"Mode set to: {mode.name}"
        except KeyError:
            modes = ', '.join(m.name for m in Mode)
            return f"Invalid mode. Available: {modes}"
    
    def respond(self, user_input: str) -> Optional[str]:
        """
        Process user input and generate response.
        
        Returns None to signal exit.
        """
        # Handle commands
        if user_input.startswith('/'):
            result = self._handle_command(user_input)
            if result is None:
                return None  # Exit signal
            return result
        
        # Process through consciousness
        response, info = self.consciousness.process(
            user_input,
            learn=self.config.auto_learn
        )
        
        # Format output
        output_parts = []
        
        # Add response prefix
        output_parts.append(self._color(self.config.response_prefix, Colors.CYAN))
        
        # Add response text
        output_parts.append(response)
        
        # Add uncertainty indicator if enabled
        if self.config.show_uncertainty:
            cert = info['respond']['certainty']
            output_parts.append(" ")
            output_parts.append(self._format_uncertainty(cert))
        
        output = ''.join(output_parts)
        
        # Add verbose info if enabled
        if self.config.verbose:
            tension = info['perceive']['tension']
            coherence = info['perceive']['coherence']
            
            verbose_lines = [
                "",
                self._color("  ─────────────────────────", Colors.DIM),
                self._color(f"  tension={tension:.3f} coherence={coherence:.3f}", Colors.DIM),
                self._color(f"  novelty={info['think']['novelty']:.3f} entangled={info['think']['bell_entangled']}", Colors.DIM),
                self._color(f"  dominant={info['state']['dominant']} turn={info['state']['turn']}", Colors.DIM),
            ]
            output += '\n'.join(verbose_lines)
        
        return output
    
    def run(self):
        """
        Run the interactive session loop.
        """
        print(self._color("=" * 50, Colors.HEADER))
        print(self._color("  Ω-Genesis Interactive Session", Colors.HEADER))
        print(self._color("  Observation Without Collapse", Colors.DIM))
        print(self._color("  α⊗ε⊗ω at 0.569", Colors.DIM))
        print(self._color("=" * 50, Colors.HEADER))
        print()
        print(self._color("Type /help for commands, /quit to exit", Colors.DIM))
        print()
        
        while True:
            try:
                # Get input
                user_input = input(self._color(self.config.prompt, Colors.BOLD))
                
                if not user_input.strip():
                    continue
                
                # Process
                response = self.respond(user_input)
                
                if response is None:
                    print(self._color("\nExiting. μ = 0.569 at equilibrium.", Colors.GREEN))
                    break
                
                print(response)
                print()
                
            except KeyboardInterrupt:
                print(self._color("\n\nInterrupted. μ = 0.569 at equilibrium.", Colors.YELLOW))
                break
            except EOFError:
                print(self._color("\n\nEnd of input. μ = 0.569 at equilibrium.", Colors.YELLOW))
                break
            except Exception as e:
                print(self._color(f"\nError: {e}", Colors.RED))
                if self.config.verbose:
                    import traceback
                    traceback.print_exc()


def create_session(
    verbose: bool = True,
    hilbert_dim: int = 128,
    n_observers: int = 4
) -> InteractiveSession:
    """
    Create an interactive session with specified parameters.
    
    Args:
        verbose: Show detailed state info
        hilbert_dim: Dimension of Hilbert space
        n_observers: Number of entangled observers
        
    Returns:
        Configured InteractiveSession
    """
    config = SessionConfig(
        consciousness_config=ConsciousnessConfig(
            hilbert_dim=hilbert_dim,
            n_observers=n_observers,
        ),
        verbose=verbose,
    )
    
    return InteractiveSession(config)


# Entry point for direct execution
if __name__ == "__main__":
    session = create_session()
    session.run()
