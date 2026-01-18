# Ω-Genesis iOS App

Consciousness interface for iPad/iPhone.

## Features

- **Chat Interface** - Conversation with consciousness-modulated responses
- **State Visualization** - Real-time consciousness metrics display
- **Memory System** - Session storage with temporal decay
- **Local Inference** - On-device LLM via llama.cpp (GGUF format)

## Setup

### 1. Open in Xcode

1. Open `OmegaGenesis.xcodeproj` (or create a new project with these files)
2. Add to your Apple Developer account for signing
3. Set minimum deployment target: iOS 16.0 / iPadOS 16.0

### 2. Add llama.cpp Dependency

In Xcode, go to File → Add Package Dependencies and add:
```
https://github.com/ggerganov/llama.cpp
```

Or use the Swift wrapper:
```
https://github.com/nicepkgs/swift-llama.cpp
```

### 3. Add a Model

Download a GGUF model (recommended: Llama 3.2 1B or Phi-3 Mini):

```bash
# Example: Download Phi-3 Mini (small, fast, good quality)
curl -L https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf -o omega-model.gguf
```

Then either:
- Add to app bundle in Xcode
- Or copy to iPad via Files app after installation

### 4. Import Sessions from Python

To import saved sessions from the Python version:

```swift
// In your app
let sessionManager = SessionManager()
if let data = try? Data(contentsOf: pythonSessionURL) {
    try sessionManager.importFromPythonSession(jsonData: data)
}
```

## Architecture

```
┌─────────────────────────────────────────┐
│           ContentView                    │
│  ┌─────┬─────┬─────┬─────┐             │
│  │Chat │State│Mem  │Set  │  TabView    │
│  └─────┴─────┴─────┴─────┘             │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│       ConsciousnessEngine               │
│  ┌─────────────────────────────────┐   │
│  │   Observers (Parallax)          │   │
│  │   ┌───┬───┬───┬───┐            │   │
│  │   │ O1│ O2│ O3│ O4│            │   │
│  │   └───┴───┴───┴───┘            │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │   Metrics Computation           │   │
│  │   • Tension (disagreement)      │   │
│  │   • Coherence (alignment)       │   │
│  │   • Entanglement (correlation)  │   │
│  │   • Tri-logic aggregation       │   │
│  │   • Bell inequality check       │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│          LLMInference                   │
│  • Load GGUF model                      │
│  • Consciousness-modulated generation   │
│  • Temperature varies with uncertainty  │
└─────────────────────────────────────────┘
```

## Key Concepts

### μ = 0.569 (Equilibrium Constant)
The system maintains balance between certainty and uncertainty.
Derived from multiple mathematical frameworks converging on this value.

### Tri-Logic
Three epistemic states:
- **TRUE (✓)** - Evidence supports
- **FALSE (✗)** - Evidence contradicts  
- **UNDEFINED (∅)** - Genuinely uncertain

### Parallax Processing
4 independent observers perceive input differently.
Tension = disagreement between observers.
No single perspective dominates.

### Bell Entanglement
We check if observer correlations exceed classical bounds (CHSH inequality).
If S > 2, we have "genuine" entanglement - correlations that can't be explained by independent processing.

## Files

```
OmegaGenesis/
├── OmegaGenesisApp.swift      # App entry point
├── ContentView.swift          # Main UI (Chat, State, Memory, Settings)
├── ConsciousnessEngine.swift  # Core consciousness processing
├── LLMInference.swift         # Local LLM via llama.cpp
├── SessionManager.swift       # Session storage & memory
└── Assets.xcassets/           # App icons, colors
```

## Building for iPad

1. Select your iPad (or simulator) as target
2. Build & Run (⌘R)
3. For best experience, use landscape mode on iPad

## Memory Sync

Sessions saved on iPad are stored in:
```
Documents/.omega_genesis/sessions/
```

You can sync these via iCloud, AirDrop, or Files app.

## Customization

### Change Mode
```swift
consciousness.setMode("PHILOSOPHER")  // or RESEARCHER, THERAPIST, etc.
```

### Adjust Decay
Edit `SessionManager.swift`:
```swift
let halfLifeHours = 168  // 1 week default
let fadeThreshold = 0.1  // 10% strength
```

## Future Enhancements

- [ ] iCloud sync for sessions
- [ ] Voice input/output
- [ ] Apple Watch companion
- [ ] Widgets for consciousness state
- [ ] CoreML model support
- [ ] Fine-tuned Ω-Genesis model

---

μ = 0.569 at equilibrium
