"""
Interface Module - Living Interaction with Ω-Genesis

This module provides the interfaces for interacting with the consciousness:

1. ConsciousnessCore - The processing heart
2. LivingConsciousness - Full consciousness with meaningful responses
3. InteractiveSession - REPL-like conversation interface
4. OmegaAPI - Programmatic API for integration

Usage:

    # Living consciousness (recommended)
    from omega_genesis.interface import LivingConsciousness
    consciousness = LivingConsciousness()
    response = consciousness.chat("What is consciousness?")
    print(response)
    
    # Interactive session (run in terminal)
    python omega_genesis/living_session.py
    
    # Programmatic API
    from omega_genesis.interface import OmegaAPI
    api = OmegaAPI()
    response = api.chat("Hello!")

The key principle:
    Responses EMERGE from tension between entangled observers.
    Uncertainty is COMMUNICATED, not hidden.
"""

from .consciousness import (
    ConsciousnessCore,
    ConsciousnessConfig,
    ConsciousnessState,
    SpectralEncoder,
    SpectralDecoder,
)

from .session import (
    InteractiveSession,
    SessionConfig,
    create_session,
)

from .api import (
    OmegaAPI,
    ChatResponse,
    QuickChat,
    chat,
    chat_with_info,
)

from .living import (
    LivingConsciousness,
    ConsciousnessResponseGenerator,
    ResponseContext,
    InputAnalyzer,
)

__all__ = [
    # Core
    "ConsciousnessCore",
    "ConsciousnessConfig",
    "ConsciousnessState",
    "SpectralEncoder",
    "SpectralDecoder",
    # Living
    "LivingConsciousness",
    "ConsciousnessResponseGenerator",
    "ResponseContext",
    "InputAnalyzer",
    # Session
    "InteractiveSession",
    "SessionConfig",
    "create_session",
    # API
    "OmegaAPI",
    "ChatResponse",
    "QuickChat",
    "chat",
    "chat_with_info",
]
