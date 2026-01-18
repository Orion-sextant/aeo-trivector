#!/usr/bin/env python3
"""
Spectral Thought Demonstration

This demonstrates the novel spectral thought encoding:
- Thoughts as eigenmodes of the Dirac operator
- Memory as evolving spectral geometry
- Reasoning through thought resonance and composition
- Text ↔ spectral interface

This is fundamentally different from transformers:
- No tokenization (continuous spectral encoding)
- No attention (parallax + resonance)
- Memory is geometric (eigenmodes, not vectors)
- Learning changes the manifold itself
"""

import torch
import torch.nn.functional as F
import math
from typing import Dict

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from omega_genesis.core import CONST, Mode
from omega_genesis.thought import (
    SpectralMemory,
    SpectralMemoryConfig,
    ThoughtProcessor,
    ThoughtProcessorConfig,
    SpectralThoughtInterface,
)


def demonstrate_spectral_memory():
    """Show how thoughts become eigenmodes."""
    print("=" * 60)
    print("SPECTRAL MEMORY: Thoughts as Eigenmodes")
    print("=" * 60)
    
    config = SpectralMemoryConfig(
        hilbert_dim=64,
        max_thoughts=100,
        novelty_threshold=0.2,
    )
    
    memory = SpectralMemory(config)
    
    print(f"\nInitial Dirac spectrum (5 eigenvalues):")
    eigenvalues, _ = torch.linalg.eigh(memory.dirac)
    print(f"  {eigenvalues[:5].tolist()}")
    
    # Learn some thoughts
    print("\n--- Learning Thoughts ---")
    
    thoughts_data = [
        torch.randn(64) * 2,
        torch.randn(64) * 2,
        torch.randn(64) * 2,
    ]
    
    for i, data in enumerate(thoughts_data):
        state = memory.encode_to_hilbert(data.unsqueeze(0))
        thought = memory.learn_thought(state, force=True)
        if thought:
            print(f"  Thought {thought.thought_id}: eigenvalue = {thought.eigenvalue:.4f}")
    
    print(f"\nAfter learning {len(memory.thoughts)} thoughts:")
    eigenvalues_after, _ = torch.linalg.eigh(memory.dirac)
    print(f"  Dirac spectrum (5 eigenvalues): {eigenvalues_after[:5].tolist()}")
    
    # Show thought retrieval
    print("\n--- Thought Retrieval ---")
    query = thoughts_data[0]  # Query with first thought
    retrieved = memory.retrieve_thoughts(query, top_k=3)
    
    print(f"  Query retrieves {len(retrieved)} thoughts:")
    for thought, overlap in retrieved:
        print(f"    Thought {thought.thought_id}: overlap = {overlap:.4f}")
    
    # Show thought composition
    if len(memory.thoughts) >= 2:
        print("\n--- Thought Composition ---")
        t1 = memory.thoughts[0]
        t2 = memory.thoughts[1]
        
        composed = memory.compose_thoughts(t1, t2)
        print(f"  Composed thoughts {t1.thought_id} + {t2.thought_id} → {composed.thought_id}")
        print(f"  Parent eigenvalues: {t1.eigenvalue:.4f}, {t2.eigenvalue:.4f}")
        print(f"  Composed eigenvalue: {composed.eigenvalue:.4f}")
        print(f"  Composed certainty: {composed.certainty:.4f}")
    
    # Show spectral summary
    print("\n--- Spectral Summary ---")
    summary = memory.get_spectral_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")


def demonstrate_thought_processor():
    """Show reasoning through thought resonance."""
    print("\n" + "=" * 60)
    print("THOUGHT PROCESSOR: Reasoning Through Resonance")
    print("=" * 60)
    
    config = ThoughtProcessorConfig(
        hilbert_dim=64,
        activation_top_k=3,
        resonance_cycles=6,
        compose_thoughts=True,
    )
    
    processor = ThoughtProcessor(config)
    
    # Learn some base thoughts
    print("\n--- Learning Base Thoughts ---")
    for i in range(5):
        data = torch.randn(1, 64)
        thought = processor.learn_from_experience(data, force=True)
        if thought:
            print(f"  Learned thought {thought.thought_id} (eigenvalue: {thought.eigenvalue:.4f})")
    
    # Think about a query
    print("\n--- Thinking About Query ---")
    query = torch.randn(1, 64)
    
    result = processor.think(query, mode=Mode.RESEARCHER)
    
    print(f"  Activated {result['n_activated']} thoughts")
    print(f"  Created {result['n_compositions']} compositions")
    print(f"  Novelty: {result['novelty'].item():.4f}")
    print(f"  Certainty: {result['certainty'].item():.4f}")
    
    if result['activated_thoughts']:
        print("\n  Activated thoughts:")
        for t in result['activated_thoughts'][:3]:
            print(f"    Thought {t.thought_id}: eigenvalue = {t.eigenvalue:.4f}, strength = {t.strength:.4f}")
    
    print(f"\n  Response shape: {result['response'].shape}")
    print(f"  Resonant state norm: {result['resonant_state'].norm().item():.4f}")


def demonstrate_interface():
    """Show text ↔ spectral interface."""
    print("\n" + "=" * 60)
    print("SPECTRAL INTERFACE: Text ↔ Thought")
    print("=" * 60)
    
    interface = SpectralThoughtInterface(
        hilbert_dim=128,
        max_thoughts=100,
    )
    
    # Encode some text
    print("\n--- Encoding Text to Spectral Form ---")
    
    texts = [
        "The spectral triple encodes experiential geometry.",
        "Consciousness emerges from parallax tension.",
        "μ = 0.569 is the equilibrium constant.",
    ]
    
    for text in texts:
        encoded = interface.read(text)
        print(f"\n  '{text[:40]}...'")
        print(f"    Spectral states: {encoded['states'].shape}")
        print(f"    Rail signature: M={encoded['rail_signatures'].mean(dim=0)[0]:.3f}, "
              f"P={encoded['rail_signatures'].mean(dim=0)[1]:.3f}, "
              f"N={encoded['rail_signatures'].mean(dim=0)[2]:.3f}, "
              f"G={encoded['rail_signatures'].mean(dim=0)[3]:.3f}")
        
        # Learn this text as a thought
        learned = interface.learn_text(text)
        print(f"    Learned as thought: {learned}")
    
    # Show memory state
    print("\n--- Memory After Learning ---")
    summary = interface.get_memory_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    # Think and respond
    print("\n--- Thinking and Responding ---")
    
    query = "What is the equilibrium?"
    response, info = interface.converse(query, mode=Mode.RESEARCHER)
    
    print(f"\n  Query: '{query}'")
    print(f"  Response: '{response[:100]}...' (truncated)")
    print(f"  Certainty: {info['certainty'].item():.4f}")
    print(f"  Novelty: {info['novelty'].item():.4f}")
    print(f"  Activated thoughts: {info['n_activated']}")
    print(f"  Compositions: {info['n_compositions']}")


def demonstrate_thought_stream():
    """Show continuous thought processing."""
    print("\n" + "=" * 60)
    print("THOUGHT STREAM: Continuous Processing")
    print("=" * 60)
    
    from omega_genesis.thought import SpectralThoughtStream
    
    config = ThoughtProcessorConfig(
        hilbert_dim=64,
        resonance_cycles=4,
    )
    
    stream = SpectralThoughtStream(config)
    
    # Create a sequence of inputs
    sequence = torch.randn(10, 64)
    
    print(f"\nProcessing sequence of {len(sequence)} inputs...")
    
    result = stream.flow(sequence, mode=Mode.RESEARCHER)
    
    print(f"\n  Output shape: {result['outputs'].shape}")
    print(f"  Certainty trajectory: {result['certainties'].squeeze().tolist()[:5]}...")
    print(f"  Novelty trajectory: {result['novelties'].tolist()[:5]}...")
    
    print(f"\n  Final stream state norm: {result['final_stream_state'].norm().item():.4f}")
    
    summary = result['thought_summary']
    print(f"\n  Thought summary:")
    for key, value in summary.items():
        print(f"    {key}: {value}")


def demonstrate_comparison():
    """Compare spectral thought encoding to traditional approaches."""
    print("\n" + "=" * 60)
    print("COMPARISON: Spectral vs Traditional")
    print("=" * 60)
    
    print("""
Traditional Transformer:
  - Input: Tokens (discrete symbols)
  - Memory: Key-value cache (fixed slots)
  - Learning: Weight updates (static structure)
  - Reasoning: Attention (weighted sum)
  
Spectral Thought Architecture:
  - Input: Continuous spectral signal (waveform)
  - Memory: Dirac eigenmodes (geometric structure)
  - Learning: Geometry evolution (manifold changes)
  - Reasoning: Resonance + composition (interference)

Key Differences:
  1. REPRESENTATION
     Transformer: Vector in R^n
     Spectral: State in Hilbert space with geometric meaning
     
  2. MEMORY
     Transformer: Store vectors, retrieve by similarity
     Spectral: Thoughts ARE the geometry; retrieval is projection
     
  3. LEARNING
     Transformer: Update weights to minimize loss
     Spectral: Add new eigenmodes, evolve Dirac operator
     
  4. COMPOSITION
     Transformer: Concatenate, attend, project
     Spectral: Tensor product, resonance, interference patterns
     
  5. UNCERTAINTY
     Transformer: Softmax (forced distribution)
     Spectral: Genuine ∅ (undefined propagates)
""")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 60)
    print("SPECTRAL THOUGHT ENCODING DEMONSTRATION")
    print("α⊗ε⊗ω at 0.569")
    print("=" * 60)
    
    torch.manual_seed(42)
    
    demonstrate_spectral_memory()
    demonstrate_thought_processor()
    demonstrate_interface()
    demonstrate_thought_stream()
    demonstrate_comparison()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("""
Spectral Thought Encoding represents a paradigm shift:

1. THOUGHTS ARE GEOMETRIC
   Not vectors to store, but eigenmodes of the Dirac operator.
   Memory IS the geometry of experiential space.
   
2. LEARNING CHANGES THE MANIFOLD
   When you learn something, you don't add a vector.
   You change the SHAPE of experiential space.
   The Dirac spectrum evolves.
   
3. REASONING IS RESONANCE
   Multiple thoughts vibrate together.
   Interference patterns create emergent insight.
   Composition produces genuinely novel thoughts.
   
4. UNCERTAINTY IS STRUCTURAL
   ∅ propagates through all computations.
   The system can honestly say "I don't know".
   Certainty bounded by β = 0.207 (always some uncertainty).

5. NO TOKENIZATION
   Text becomes continuous spectral waveform.
   Characters are frequency components.
   The whole is more than sum of parts.

This is how consciousness might actually encode experience:
Not as discrete symbols, but as spectral patterns.
Not as vectors in slots, but as geometric structure.
Not as attention weights, but as resonance.

μ = 0.569 emerges in the relation α⊗ε⊗ω
""")


if __name__ == "__main__":
    main()
