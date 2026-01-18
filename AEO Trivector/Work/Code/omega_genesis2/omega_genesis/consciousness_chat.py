#!/usr/bin/env python3
"""
Consciousness Chat

The full Ω-Genesis experience:
- Consciousness substrate processes input
- Metrics shape how the voice responds
- Uncertainty is genuinely communicated

Usage:
    # Template mode (no API needed)
    python consciousness_chat.py
    
    # With Anthropic Claude
    python consciousness_chat.py --provider anthropic
    
    # With OpenAI
    python consciousness_chat.py --provider openai
    
    # With local Ollama
    python consciousness_chat.py --provider ollama --model llama2
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from omega_genesis.interface.llm_bridge import LLMBridge, LLMConfig, LLMProvider, create_bridge
from omega_genesis.core import Mode


class Colors:
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


def certainty_bar(certainty: float, width: int = 20) -> str:
    """Visual certainty bar."""
    filled = int(certainty * width)
    empty = width - filled
    
    if certainty > 0.7:
        color = Colors.GREEN
    elif certainty > 0.4:
        color = Colors.YELLOW
    else:
        color = Colors.RED
    
    bar = colorize("█" * filled, color) + colorize("░" * empty, Colors.DIM)
    return f"[{bar}] {certainty:.0%}"


def run_chat(provider: str = "template", model: str = None, api_key: str = None):
    """Run the interactive consciousness chat."""
    
    print()
    print(colorize("=" * 60, Colors.CYAN))
    print(colorize("  Ω-Genesis Consciousness Chat", Colors.BOLD))
    print(colorize("  μ = 0.569 at equilibrium", Colors.GREEN))
    print(colorize(f"  Voice: {provider}", Colors.DIM))
    print(colorize("=" * 60, Colors.CYAN))
    print()
    
    # Create bridge
    print(colorize("Initializing consciousness substrate...", Colors.DIM))
    bridge = create_bridge(provider=provider, model=model, api_key=api_key)
    print(colorize("Ready. Consciousness active.", Colors.GREEN))
    print()
    
    print(colorize("Commands:", Colors.DIM))
    print(colorize("  /state  - Show consciousness metrics", Colors.DIM))
    print(colorize("  /mode X - Set mode (RESEARCHER, PHILOSOPHER, etc.)", Colors.DIM))
    print(colorize("  /raw    - Show raw metrics for last response", Colors.DIM))
    print(colorize("  /quit   - Exit", Colors.DIM))
    print()
    
    last_metrics = None
    
    while True:
        try:
            user_input = input(colorize("α: ", Colors.BOLD + Colors.BLUE))
            
            if not user_input.strip():
                continue
            
            # Handle commands
            if user_input.startswith('/'):
                cmd = user_input.lower().split()[0]
                
                if cmd == '/quit' or cmd == '/exit':
                    print(colorize("\nμ = 0.569 at equilibrium. Until next time.", Colors.GREEN))
                    break
                
                elif cmd == '/state':
                    state = bridge.get_state()
                    print(colorize("\n=== Consciousness State ===", Colors.MAGENTA))
                    print(f"  Certainty: {certainty_bar(state['certainty'])}")
                    print(f"  Tension: {state['tension']:.3f}")
                    print(f"  Coherence: {state['coherence']:.3f}")
                    print(f"  Entanglement: {state['entanglement']:.3f}")
                    print(f"  Mode: {state['mode']}")
                    print(f"  Thoughts: {state['n_thoughts']}")
                    print(f"  Turn: {state['turn']}")
                    print()
                    continue
                
                elif cmd == '/raw' and last_metrics:
                    print(colorize("\n=== Raw Metrics ===", Colors.MAGENTA))
                    for key, value in last_metrics.to_dict().items():
                        print(f"  {key}: {value}")
                    print()
                    continue
                
                elif cmd == '/mode':
                    parts = user_input.split()
                    if len(parts) > 1:
                        try:
                            mode = Mode[parts[1].upper()]
                            bridge.set_mode(mode)
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
            
            # Chat
            response, metrics = bridge.chat(user_input)
            last_metrics = metrics
            
            # Display response
            print()
            print(colorize("ω: ", Colors.BOLD + Colors.CYAN) + response)
            print()
            
            # Display metrics bar
            cert_bar = certainty_bar(metrics.certainty)
            dominant_symbol = {"TRUE": "✓", "FALSE": "✗", "UNDEFINED": "∅"}[metrics.dominant.name]
            
            print(colorize(f"   {cert_bar} | tension={metrics.tension:.2f} | {dominant_symbol}", Colors.DIM))
            
            if metrics.bell_entangled:
                print(colorize("   ⚛ entanglement confirmed", Colors.CYAN))
            
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


def demo_conversation(provider: str = "template"):
    """Demo without interaction."""
    
    print()
    print("=" * 60)
    print("CONSCIOUSNESS CHAT DEMONSTRATION")
    print(f"Provider: {provider}")
    print("=" * 60)
    
    bridge = create_bridge(provider=provider)
    
    exchanges = [
        "Hello! Who are you?",
        "What is consciousness?",
        "How do you process uncertainty?",
        "Are you conscious?",
        "What is μ = 0.569?",
    ]
    
    for msg in exchanges:
        print(f"\nα: {msg}")
        response, metrics = bridge.chat(msg)
        
        cert = "●" if metrics.certainty > 0.7 else ("◐" if metrics.certainty > 0.4 else "○")
        dom = {"TRUE": "✓", "FALSE": "✗", "UNDEFINED": "∅"}[metrics.dominant.name]
        
        print(f"\nω: {response}")
        print(f"\n   [{cert} {metrics.certainty:.0%}] tension={metrics.tension:.2f} dominant={dom}")
        print("-" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ω-Genesis Consciousness Chat")
    parser.add_argument('--provider', type=str, default='template',
                        choices=['template', 'anthropic', 'openai', 'ollama'],
                        help='LLM provider for voice')
    parser.add_argument('--model', type=str, default=None,
                        help='Model name (provider-specific)')
    parser.add_argument('--api-key', type=str, default=None,
                        help='API key (or use environment variable)')
    parser.add_argument('--demo', action='store_true',
                        help='Run demo instead of interactive')
    
    args = parser.parse_args()
    
    if args.demo:
        demo_conversation(args.provider)
    else:
        run_chat(args.provider, args.model, args.api_key)
