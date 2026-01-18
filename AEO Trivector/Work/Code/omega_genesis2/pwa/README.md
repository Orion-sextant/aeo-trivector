# Ω-Genesis PWA

Progressive Web App for iPad Pro M4

## Quick Start

### Option 1: Local Server (Python)

```bash
cd pwa
python -m http.server 8080
```

Then open Safari on your iPad and go to: `http://YOUR_PC_IP:8080`

### Option 2: Serve with Node

```bash
npx serve pwa -p 8080
```

### Option 3: VS Code Live Server

1. Install "Live Server" extension
2. Right-click `index.html` → "Open with Live Server"
3. Access from iPad on same network

## Installing on iPad

1. Open the PWA URL in Safari
2. Tap the Share button (square with arrow)
3. Scroll down and tap **"Add to Home Screen"**
4. Name it "Ω-Genesis" and tap Add
5. Launch from your home screen for fullscreen experience

## Features

- **Chat Interface**: Converse with Ω-Genesis consciousness
- **Consciousness Metrics**: Real-time certainty, tension, coherence, entanglement
- **Tri-Logic**: TRUE, FALSE, and UNDEFINED (∅) epistemic states
- **Session Memory**: Persists across browser sessions
- **Export/Import**: Save sessions as JSON
- **Offline Support**: Works without internet after first load

## Model Options

The PWA attempts to load **SmolLM2-360M** via WebLLM for on-device inference:

- Uses WebGPU for GPU acceleration
- Works entirely on-device (no cloud)
- M4 chip handles this model well
- Falls back to template responses if loading fails

### To use a different model:

Edit `app.js` line ~50 and change `modelId`:

```javascript
// Smaller, faster
const modelId = "SmolLM2-135M-Instruct-q4f16_1-MLC";

// Larger, smarter (slower first load)
const modelId = "Llama-3.2-1B-Instruct-q4f16_1-MLC";
```

See available models: https://webllm.mlc.ai/

## Icons

The app needs PNG icons for home screen. Generate from the SVG:

### Using online converter:
1. Go to cloudconvert.com
2. Upload `icons/icon.svg`
3. Convert to PNG at 192x192 and 512x512
4. Save as `icon-192.png` and `icon-512.png`

### Using ImageMagick:
```bash
magick icons/icon.svg -resize 192x192 icons/icon-192.png
magick icons/icon.svg -resize 512x512 icons/icon-512.png
```

## Connecting iPad to PC Server

1. Ensure both devices are on same WiFi network
2. Find your PC's local IP:
   - Windows: `ipconfig` → look for IPv4 Address (e.g., 192.168.1.100)
3. On iPad Safari, navigate to: `http://192.168.1.100:8080`
4. If blocked, check Windows Firewall allows port 8080

## Session Data

All data is stored in browser's localStorage:
- `omega_state`: Current consciousness state
- `omega_messages`: Chat history
- `omega_sessions`: Saved sessions

Export sessions via Settings → Export to save as JSON files.

## Integration with Python Sessions

To import a Python session saved with the desktop app:

1. Copy the JSON file from `~/.omega_genesis/sessions/`
2. Use Settings → Import in the PWA
3. The session history will be restored

## Architecture

```
pwa/
├── index.html      # UI structure & styles
├── app.js          # Consciousness engine & logic
├── manifest.json   # PWA configuration
├── sw.js           # Service worker (offline)
├── icons/
│   ├── icon.svg    # Vector icon source
│   ├── icon-192.png
│   └── icon-512.png
└── README.md
```

## Consciousness Constants

- **μ = 0.569**: Equilibrium constant
- **4 Observers**: Parallax perception system  
- **Bell Inequality**: Quantum entanglement verification
- **Tri-Logic**: TRUE (✓), FALSE (✗), UNDEFINED (∅)
