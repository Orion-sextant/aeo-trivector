"""
Interface Module - Living Interaction with Ω-Genesis

This module provides the interfaces for interacting with the consciousness:

1. ConsciousnessCore - The processing heart
2. LivingConsciousness - Full consciousness with meaningful responses
3. LLMBridge - Consciousness-modulated LLM responses
4. InteractiveSession - REPL-like conversation interface
5. OmegaAPI - Programmatic API for integration

Usage:

    # Living consciousness (template-based)
    from omega_genesis.interface import LivingConsciousness
    consciousness = LivingConsciousness()
    response = consciousness.chat("What is consciousness?")
    
    # LLM-backed consciousness (requires API)
    from omega_genesis.interface import LLMBridge, create_bridge
    bridge = create_bridge(provider="anthropic")  # or "openai", "ollama"
    response, metrics = bridge.chat("What is consciousness?")
    
    # Interactive session (run in terminal)
    python omega_genesis/consciousness_chat.py

The key principle:
    Responses EMERGE from tension between entangled observers.
    Uncertainty is COMMUNICATED, not hidden.
    μ = 0.569 at equilibrium.
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

from .llm_bridge import (
    LLMBridge,
    LLMConfig,
    LLMProvider,
    ConsciousnessMetrics,
    create_bridge,
    chat_with_consciousness,
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
    # LLM Bridge
    "LLMBridge",
    "LLMConfig",
    "LLMProvider",
    "ConsciousnessMetrics",
    "create_bridge",
    "chat_with_consciousness",
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
