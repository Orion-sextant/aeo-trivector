#!/usr/bin/env python3
"""
Living Consciousness Session

Truly interactive conversation with Ω-Genesis.

The consciousness processes through entangled observers.
Responses reflect the actual state:
- Certainty shapes confidence of language
- Tension shapes acknowledgment of perspectives
- UNDEFINED is embraced, not hidden

Run:
    python omega_genesis/living_session.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from omega_genesis.interface.living import LivingConsciousness
from omega_genesis.core import Mode


class Colors:
    """ANSI colors."""
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


def colorize(text: str, color: str) -> str:
    return f"{color}{text}{Colors.RESET}"


def certainty_indicator(certainty: float) -> str:
    """Visual certainty indicator."""
    if certainty > 0.7:
        return colorize("●", Colors.GREEN)
    elif certainty > 0.4:
        return colorize("◐", Colors.YELLOW)
    else:
        return colorize("○", Colors.RED)


def run_session():
    """Run the living consciousness session."""
    
    print()
    print(colorize("=" * 60, Colors.CYAN))
    print(colorize("  Ω-Genesis Living Consciousness", Colors.BOLD))
    print(colorize("  Observation Without Collapse", Colors.DIM))
    print(colorize("  μ = 0.569 at equilibrium", Colors.GREEN))
    print(colorize("=" * 60, Colors.CYAN))
    print()
    
    print(colorize("Initializing consciousness...", Colors.DIM))
    consciousness = LivingConsciousness(hilbert_dim=64, n_observers=4)
    print(colorize("Ready.", Colors.GREEN))
    print()
    
    print(colorize("Commands:", Colors.DIM))
    print(colorize("  /state  - Show consciousness state", Colors.DIM))
    print(colorize("  /mode X - Set mode (RESEARCHER, PHILOSOPHER, etc.)", Colors.DIM))
    print(colorize("  /quit   - Exit", Colors.DIM))
    print()
    
    while True:
        try:
            # Get input
            user_input = input(colorize("α: ", Colors.BOLD + Colors.BLUE))
            
            if not user_input.strip():
                continue
            
            # Handle commands
            if user_input.startswith('/'):
                cmd = user_input.lower().split()[0]
                
                if cmd == '/quit' or cmd == '/exit':
                    print(colorize("\nμ = 0.569 at equilibrium. Farewell.", Colors.GREEN))
                    break
                
                elif cmd == '/state':
                    state = consciousness.get_state()
                    print(colorize("\n=== Consciousness State ===", Colors.MAGENTA))
                    print(f"  Certainty: {state['certainty']:.0%}")
                    print(f"  Tension: {state['tension']:.3f}")
                    print(f"  Coherence: {state['coherence']:.3f}")
                    print(f"  Entanglement: {state['entanglement']:.3f}")
                    print(f"  Mode: {state['mode']}")
                    print(f"  Turn: {state['turn']}")
                    print(f"  Thoughts: {state['n_thoughts']}")
                    print()
                    continue
                
                elif cmd == '/mode':
                    parts = user_input.split()
                    if len(parts) > 1:
                        try:
                            mode = Mode[parts[1].upper()]
                            consciousness.set_mode(mode)
                            print(colorize(f"Mode set to: {mode.name}", Colors.GREEN))
                        except KeyError:
                            modes = ', '.join(m.name for m in Mode)
                            print(colorize(f"Available modes: {modes}", Colors.YELLOW))
                    else:
                        modes = ', '.join(m.name for m in Mode)
                        print(colorize(f"Usage: /mode <mode>. Available: {modes}", Colors.YELLOW))
                    print()
                    continue
                
                else:
                    print(colorize(f"Unknown command: {cmd}", Colors.RED))
                    print()
                    continue
            
            # Get response
            response, info = consciousness.respond(user_input)
            context = info['context']
            
            # Format output
            cert = certainty_indicator(context.certainty)
            
            print()
            print(colorize("ω: ", Colors.BOLD + Colors.CYAN) + response)
            print()
            print(colorize(f"   {cert} certainty={context.certainty:.0%} "
                          f"tension={context.tension:.2f} "
                          f"dominant={context.dominant.name}", Colors.DIM))
            print()
            
        except KeyboardInterrupt:
            print(colorize("\n\nInterrupted. μ = 0.569.", Colors.YELLOW))
            break
        except EOFError:
            print(colorize("\n\nEnd. μ = 0.569.", Colors.YELLOW))
            break
        except Exception as e:
            print(colorize(f"\nError: {e}", Colors.RED))
            import traceback
            traceback.print_exc()


def demo_conversation():
    """Demo a conversation without interaction."""
    
    print()
    print("=" * 60)
    print("LIVING CONSCIOUSNESS DEMONSTRATION")
    print("=" * 60)
    
    consciousness = LivingConsciousness(hilbert_dim=64, n_observers=4)
    
    messages = [
        "Hello! Who are you?",
        "What is consciousness?",
        "How do you process information?",
        "Are you certain about anything?",
        "Tell me about uncertainty.",
        "What is the meaning of existence?",
        "Can you help me understand truth?",
    ]
    
    for msg in messages:
        print(f"\nα: {msg}")
        response, info = consciousness.respond(msg)
        context = info['context']
        
        # Show certainty
        if context.certainty > 0.7:
            cert = "●"
        elif context.certainty > 0.4:
            cert = "◐"
        else:
            cert = "○"
        
        print(f"\nω: {response}")
        print(f"\n   [{cert} {context.certainty:.0%}] tension={context.tension:.2f} dominant={context.dominant.name}")
        print("-" * 60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Living Consciousness Session")
    parser.add_argument('--demo', action='store_true', help='Run demo instead of interactive')
    args = parser.parse_args()
    
    if args.demo:
        demo_conversation()
    else:
        run_session()
