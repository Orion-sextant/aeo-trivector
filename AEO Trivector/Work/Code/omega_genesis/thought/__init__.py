"""
Thought Module - Spectral Thought Encoding and Processing

Thoughts are not vectors. They are geometric structures.
Learning is geometric evolution. Memory is spectral structure.

Core Components:
- SpectralMemory: Thoughts as eigenmodes of the Dirac operator
- ThoughtProcessor: Reasoning through spectral composition
- SpectralThoughtInterface: Text ↔ Spectral encoding

The key insight:
When you learn something, you don't add a vector to memory.
You change the SHAPE of experiential space.
"""

from .spectral_memory import (
    ThoughtSignature,
    SpectralMemoryConfig,
    SpectralMemory,
)

from .processor import (
    ThoughtProcessorConfig,
    ThoughtResonator,
    ThoughtComposer,
    ThoughtProcessor,
    SpectralThoughtStream,
)

from .interface import (
    SpectralInterfaceConfig,
    CharacterSpectralEncoder,
    SpectralDecoder,
    SpectralThoughtInterface,
)

__all__ = [
    # Memory
    "ThoughtSignature",
    "SpectralMemoryConfig",
    "SpectralMemory",
    # Processing
    "ThoughtProcessorConfig",
    "ThoughtResonator",
    "ThoughtComposer",
    "ThoughtProcessor",
    "SpectralThoughtStream",
    # Interface
    "SpectralInterfaceConfig",
    "CharacterSpectralEncoder",
    "SpectralDecoder",
    "SpectralThoughtInterface",
]
