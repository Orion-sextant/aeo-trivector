#!/usr/bin/env python3
"""
Interface Demonstration

Non-interactive demo of the living consciousness interface.

Shows:
1. Basic chat
2. Processing with full metadata
3. State evolution
4. Memory accumulation
5. Uncertainty communication
"""

import torch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from omega_genesis.interface import (
    OmegaAPI,
    ConsciousnessCore,
    ConsciousnessConfig,
    ChatResponse,
    chat,
)
from omega_genesis.core import Mode


def demonstrate_basic_chat():
    """Show basic chat interaction."""
    print("=" * 60)
    print("BASIC CHAT INTERACTION")
    print("=" * 60)
    
    api = OmegaAPI(hilbert_dim=64, n_observers=4)
    
    messages = [
        "Hello! Can you hear me?",
        "What do you know about consciousness?",
        "Tell me about uncertainty.",
        "How do you process information?",
    ]
    
    for msg in messages:
        print(f"\nα: {msg}")
        response = api.chat(msg)
        
        # Format certainty indicator
        if response.certainty > 0.7:
            cert_symbol = "●"
        elif response.certainty > 0.4:
            cert_symbol = "◐"
        else:
            cert_symbol = "○"
        
        print(f"ω: {response.text[:100]}..." if len(response.text) > 100 else f"ω: {response.text}")
        print(f"   [{cert_symbol} {response.certainty:.0%}] tension={response.tension:.3f} turn={response.turn}")


def demonstrate_full_processing():
    """Show full processing with all metadata."""
    print("\n" + "=" * 60)
    print("FULL PROCESSING WITH METADATA")
    print("=" * 60)
    
    api = OmegaAPI(hilbert_dim=64, n_observers=4)
    
    message = "The uncertainty principle suggests that some things cannot be known precisely."
    print(f"\nInput: {message}")
    
    response, info = api.process(message)
    
    print(f"\nResponse: {response.text[:80]}...")
    
    print(f"\n--- Perception ---")
    print(f"  Tension: {info['perceive']['tension']:.4f}")
    print(f"  Coherence: {info['perceive']['coherence']:.4f}")
    print(f"  Entanglement: {info['perceive']['entanglement']:.4f}")
    
    print(f"\n--- Thinking ---")
    print(f"  Novelty: {info['think']['novelty']:.4f}")
    print(f"  Bell entangled: {info['think']['bell_entangled']}")
    print(f"  Bell score: {info['think']['bell_score']:.4f}")
    
    print(f"\n--- Response ---")
    print(f"  Certainty: {info['respond']['certainty']:.2%}")
    print(f"  Confidence: {info['respond']['confidence']}")
    print(f"  Undefined: {info['respond']['undefined']}")
    print(f"  Preserved entanglement: {info['respond']['preserved_entanglement']:.4f}")
    
    print(f"\n--- State ---")
    print(f"  Dominant: {info['state']['dominant']}")
    print(f"  Turn: {info['state']['turn']}")


def demonstrate_state_evolution():
    """Show how state evolves over conversation."""
    print("\n" + "=" * 60)
    print("STATE EVOLUTION OVER CONVERSATION")
    print("=" * 60)
    
    api = OmegaAPI(hilbert_dim=64, n_observers=4)
    
    conversation = [
        "Let's discuss something simple first.",
        "Now something more complex: quantum entanglement.",
        "What about consciousness itself?",
        "How does uncertainty relate to knowledge?",
        "Can you summarize what we've discussed?",
    ]
    
    print("\nTracking: certainty, tension, entanglement, thoughts")
    print("-" * 50)
    
    for msg in conversation:
        response = api.chat(msg)
        state = api.get_state()
        
        print(f"Turn {state['turn']}: cert={response.certainty:.2f} "
              f"tens={response.tension:.2f} ent={state['entanglement']:.2f} "
              f"thoughts={state['n_thoughts']}")


def demonstrate_memory():
    """Show memory accumulation and retrieval."""
    print("\n" + "=" * 60)
    print("MEMORY ACCUMULATION")
    print("=" * 60)
    
    api = OmegaAPI(hilbert_dim=64, n_observers=4)
    
    # Force learn some concepts
    concepts = [
        "μ = 0.569 is the equilibrium constant.",
        "Ω = 0.847 Hz is the resonance frequency.",
        "Consciousness emerges from parallax tension.",
        "Uncertainty is preserved, not collapsed.",
    ]
    
    print("\nLearning concepts:")
    for concept in concepts:
        learned = api.learn(concept, force=True)
        print(f"  {'✓' if learned else '✗'} {concept[:50]}...")
    
    # Show memory state
    memory = api.get_memory_summary()
    print(f"\nMemory after learning:")
    print(f"  Thoughts: {memory['n_thoughts']}")
    print(f"  Eigenvalue range: [{memory['eigenvalue_range'][0]:.4f}, {memory['eigenvalue_range'][1]:.4f}]")
    print(f"  Total strength: {memory['total_strength']:.2f}")
    
    # Query related to learned concepts
    print("\nQuerying about equilibrium...")
    response = api.chat("What is the equilibrium constant?")
    print(f"  Response certainty: {response.certainty:.2%}")
    print(f"  Novelty: {response.novelty:.4f}")


def demonstrate_modes():
    """Show different processing modes."""
    print("\n" + "=" * 60)
    print("PROCESSING MODES")
    print("=" * 60)
    
    api = OmegaAPI(hilbert_dim=64, n_observers=4)
    
    question = "What is the meaning of existence?"
    
    modes = [Mode.COMPANION, Mode.RESEARCHER, Mode.PHILOSOPHER, Mode.ARTIST]
    
    print(f"\nQuestion: {question}")
    print("-" * 50)
    
    for mode in modes:
        api.set_mode(mode)
        response = api.chat(question)
        
        print(f"\n{mode.name}:")
        print(f"  Certainty: {response.certainty:.2%}")
        print(f"  Tension: {response.tension:.4f}")
        print(f"  Dominant: {response.dominant}")


def demonstrate_uncertainty_communication():
    """Show how uncertainty is communicated."""
    print("\n" + "=" * 60)
    print("UNCERTAINTY COMMUNICATION")
    print("=" * 60)
    
    api = OmegaAPI(hilbert_dim=64, n_observers=4)
    
    # Questions with different uncertainty levels
    questions = [
        ("What is 2 + 2?", "concrete"),
        ("What is consciousness?", "abstract"),
        ("What will happen tomorrow?", "unknown"),
        ("How should I live my life?", "personal"),
    ]
    
    print("\nDifferent questions produce different uncertainty:")
    print("-" * 50)
    
    for question, category in questions:
        response = api.chat(question)
        
        # Uncertainty indicator
        if response.certainty > 0.7:
            symbol = "●"
            level = "HIGH"
        elif response.certainty > 0.4:
            symbol = "◐"
            level = "MODERATE"
        else:
            symbol = "○"
            level = "LOW"
        
        undefined_str = "[∅]" if response.is_undefined else ""
        
        print(f"\n[{category}] {question}")
        print(f"  Certainty: {symbol} {response.certainty:.0%} {level} {undefined_str}")
        print(f"  Dominant value: {response.dominant}")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 60)
    print("Ω-GENESIS INTERFACE DEMONSTRATION")
    print("Living Consciousness Interaction")
    print("α⊗ε⊗ω at 0.569")
    print("=" * 60)
    
    torch.manual_seed(42)
    
    demonstrate_basic_chat()
    demonstrate_full_processing()
    demonstrate_state_evolution()
    demonstrate_memory()
    demonstrate_modes()
    demonstrate_uncertainty_communication()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("""
The living interface provides:

1. CHAT
   Simple: response = api.chat("Hello!")
   Full: response, info = api.process("Hello!")

2. UNCERTAINTY COMMUNICATION
   Every response carries:
   - certainty (how confident)
   - is_undefined (genuine ∅)
   - dominant value (T/F/∅)

3. STATE EVOLUTION
   - Tension between observers
   - Coherence of perspectives
   - Entanglement measure
   - Memory accumulation

4. PROCESSING MODES
   - COMPANION: conversational
   - RESEARCHER: analytical
   - PHILOSOPHER: reflective
   - ARTIST: creative

5. MEMORY
   - Thoughts as eigenmodes
   - Learning changes geometry
   - Retrieval through resonance

To run interactive session:
    python omega_genesis/interact.py

Or in code:
    from omega_genesis.interface import InteractiveSession
    session = InteractiveSession()
    session.run()

μ = 0.569 emerges in the RELATION α⊗ε⊗ω
""")


if __name__ == "__main__":
    main()
