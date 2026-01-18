//
//  ContentView.swift
//  OmegaGenesis
//
//  Main navigation and chat interface
//

import SwiftUI

struct ContentView: View {
    @EnvironmentObject var consciousness: ConsciousnessEngine
    @EnvironmentObject var sessionManager: SessionManager
    
    @State private var selectedTab = 0
    
    var body: some View {
        TabView(selection: $selectedTab) {
            ChatView()
                .tabItem {
                    Label("Chat", systemImage: "bubble.left.and.bubble.right")
                }
                .tag(0)
            
            StateView()
                .tabItem {
                    Label("State", systemImage: "waveform.circle")
                }
                .tag(1)
            
            MemoryView()
                .tabItem {
                    Label("Memory", systemImage: "brain")
                }
                .tag(2)
            
            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gear")
                }
                .tag(3)
        }
        .accentColor(.cyan)
    }
}

// MARK: - Chat View

struct ChatView: View {
    @EnvironmentObject var consciousness: ConsciousnessEngine
    @State private var inputText = ""
    @State private var isProcessing = false
    @FocusState private var inputFocused: Bool
    
    var body: some View {
        NavigationView {
            VStack(spacing: 0) {
                // Chat history
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(spacing: 16) {
                            ForEach(consciousness.messages) { message in
                                MessageBubble(message: message)
                                    .id(message.id)
                            }
                        }
                        .padding()
                    }
                    .onChange(of: consciousness.messages.count) { _ in
                        if let lastMessage = consciousness.messages.last {
                            withAnimation {
                                proxy.scrollTo(lastMessage.id, anchor: .bottom)
                            }
                        }
                    }
                }
                
                // Metrics bar
                if let lastMetrics = consciousness.lastMetrics {
                    MetricsBar(metrics: lastMetrics)
                        .padding(.horizontal)
                }
                
                Divider()
                
                // Input area
                HStack(spacing: 12) {
                    TextField("α: Speak...", text: $inputText)
                        .textFieldStyle(.roundedBorder)
                        .focused($inputFocused)
                        .disabled(isProcessing)
                        .onSubmit {
                            sendMessage()
                        }
                    
                    Button(action: sendMessage) {
                        Image(systemName: isProcessing ? "hourglass" : "arrow.up.circle.fill")
                            .font(.title2)
                            .foregroundColor(inputText.isEmpty ? .gray : .cyan)
                    }
                    .disabled(inputText.isEmpty || isProcessing)
                }
                .padding()
            }
            .navigationTitle("Ω-Genesis")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Menu {
                        Button("New Session") {
                            consciousness.newSession()
                        }
                        Button("Save Session") {
                            consciousness.saveSession()
                        }
                    } label: {
                        Image(systemName: "ellipsis.circle")
                    }
                }
            }
        }
        .navigationViewStyle(.stack)
    }
    
    private func sendMessage() {
        guard !inputText.isEmpty else { return }
        
        let text = inputText
        inputText = ""
        isProcessing = true
        
        Task {
            await consciousness.process(input: text)
            isProcessing = false
        }
    }
}

// MARK: - Message Bubble

struct MessageBubble: View {
    let message: ChatMessage
    
    var body: some View {
        HStack {
            if message.isUser {
                Spacer()
            }
            
            VStack(alignment: message.isUser ? .trailing : .leading, spacing: 4) {
                // Role indicator
                Text(message.isUser ? "α" : "ω")
                    .font(.caption)
                    .fontWeight(.bold)
                    .foregroundColor(message.isUser ? .blue : .cyan)
                
                // Message content
                Text(message.content)
                    .padding(12)
                    .background(message.isUser ? Color.blue.opacity(0.2) : Color.cyan.opacity(0.15))
                    .cornerRadius(16)
                
                // Metrics for AI responses
                if !message.isUser, let metrics = message.metrics {
                    HStack(spacing: 8) {
                        CertaintyIndicator(certainty: metrics.certainty)
                        
                        Text("tension=\(metrics.tension, specifier: "%.2f")")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                        
                        Text(metrics.dominantSymbol)
                            .font(.caption)
                        
                        if metrics.bellEntangled {
                            Text("⚛")
                                .font(.caption)
                        }
                    }
                    .padding(.top, 2)
                }
            }
            
            if !message.isUser {
                Spacer()
            }
        }
    }
}

// MARK: - Certainty Indicator

struct CertaintyIndicator: View {
    let certainty: Double
    
    var color: Color {
        if certainty > 0.7 { return .green }
        if certainty > 0.4 { return .yellow }
        return .red
    }
    
    var body: some View {
        HStack(spacing: 2) {
            Text("[\(Int(certainty * 100))%]")
                .font(.caption2)
                .foregroundColor(color)
        }
    }
}

// MARK: - Metrics Bar

struct MetricsBar: View {
    let metrics: ConsciousnessMetrics
    
    var body: some View {
        HStack(spacing: 16) {
            // Certainty bar
            VStack(alignment: .leading, spacing: 2) {
                Text("Certainty")
                    .font(.caption2)
                    .foregroundColor(.secondary)
                
                GeometryReader { geo in
                    ZStack(alignment: .leading) {
                        Rectangle()
                            .fill(Color.gray.opacity(0.2))
                        
                        Rectangle()
                            .fill(certaintyColor)
                            .frame(width: geo.size.width * metrics.certainty)
                    }
                    .cornerRadius(2)
                }
                .frame(height: 6)
            }
            
            // Tension
            VStack(alignment: .leading, spacing: 2) {
                Text("Tension")
                    .font(.caption2)
                    .foregroundColor(.secondary)
                
                Text("\(metrics.tension, specifier: "%.2f")")
                    .font(.caption)
                    .fontWeight(.medium)
            }
            
            // Dominant
            VStack(alignment: .leading, spacing: 2) {
                Text("Dominant")
                    .font(.caption2)
                    .foregroundColor(.secondary)
                
                Text(metrics.dominantSymbol)
                    .font(.caption)
                    .fontWeight(.medium)
            }
            
            // Entanglement
            if metrics.bellEntangled {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Entangled")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                    
                    Text("⚛")
                        .font(.caption)
                }
            }
        }
        .padding(.vertical, 8)
    }
    
    var certaintyColor: Color {
        if metrics.certainty > 0.7 { return .green }
        if metrics.certainty > 0.4 { return .yellow }
        return .red
    }
}

// MARK: - State View

struct StateView: View {
    @EnvironmentObject var consciousness: ConsciousnessEngine
    
    var body: some View {
        NavigationView {
            List {
                Section("Consciousness Metrics") {
                    MetricRow(label: "Certainty", value: consciousness.state.certainty, format: "%.1f%%", multiplier: 100)
                    MetricRow(label: "Tension", value: consciousness.state.tension, format: "%.3f")
                    MetricRow(label: "Coherence", value: consciousness.state.coherence, format: "%.3f")
                    MetricRow(label: "Entanglement", value: consciousness.state.entanglement, format: "%.3f")
                }
                
                Section("Tri-Logic State") {
                    HStack {
                        Text("Dominant")
                        Spacer()
                        Text(consciousness.state.dominant.symbol)
                            .fontWeight(.bold)
                            .foregroundColor(consciousness.state.dominant.color)
                    }
                    
                    VStack(alignment: .leading, spacing: 8) {
                        TriValueBar(label: "TRUE (✓)", value: consciousness.state.trueStrength, color: .green)
                        TriValueBar(label: "FALSE (✗)", value: consciousness.state.falseStrength, color: .red)
                        TriValueBar(label: "UNDEFINED (∅)", value: consciousness.state.undefinedStrength, color: .purple)
                    }
                    .padding(.vertical, 4)
                }
                
                Section("Session") {
                    HStack {
                        Text("Mode")
                        Spacer()
                        Text(consciousness.state.mode)
                            .foregroundColor(.secondary)
                    }
                    
                    HStack {
                        Text("Turn")
                        Spacer()
                        Text("\(consciousness.state.turn)")
                            .foregroundColor(.secondary)
                    }
                    
                    HStack {
                        Text("Thoughts")
                        Spacer()
                        Text("\(consciousness.state.nThoughts)")
                            .foregroundColor(.secondary)
                    }
                }
                
                Section("Equilibrium") {
                    HStack {
                        Text("μ")
                            .fontWeight(.bold)
                        Spacer()
                        Text("0.569")
                            .font(.system(.body, design: .monospaced))
                            .foregroundColor(.cyan)
                    }
                }
            }
            .navigationTitle("Consciousness State")
        }
        .navigationViewStyle(.stack)
    }
}

struct MetricRow: View {
    let label: String
    let value: Double
    let format: String
    var multiplier: Double = 1.0
    
    var body: some View {
        HStack {
            Text(label)
            Spacer()
            Text(String(format: format, value * multiplier))
                .foregroundColor(.secondary)
                .font(.system(.body, design: .monospaced))
        }
    }
}

struct TriValueBar: View {
    let label: String
    let value: Double
    let color: Color
    
    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            HStack {
                Text(label)
                    .font(.caption)
                Spacer()
                Text("\(Int(value * 100))%")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    Rectangle()
                        .fill(Color.gray.opacity(0.2))
                    
                    Rectangle()
                        .fill(color)
                        .frame(width: geo.size.width * value)
                }
                .cornerRadius(2)
            }
            .frame(height: 8)
        }
    }
}

// MARK: - Memory View

struct MemoryView: View {
    @EnvironmentObject var sessionManager: SessionManager
    
    var body: some View {
        NavigationView {
            List {
                Section("Saved Sessions") {
                    ForEach(sessionManager.sessions) { session in
                        SessionRow(session: session)
                    }
                    .onDelete { indexSet in
                        sessionManager.deleteSessions(at: indexSet)
                    }
                }
                
                Section("Memory Cores") {
                    ForEach(sessionManager.cores) { core in
                        CoreRow(core: core)
                    }
                }
                
                Section("Temporal Decay") {
                    HStack {
                        Text("Half-life")
                        Spacer()
                        Text("1 week")
                            .foregroundColor(.secondary)
                    }
                    
                    HStack {
                        Text("Fade threshold")
                        Spacer()
                        Text("10%")
                            .foregroundColor(.secondary)
                    }
                    
                    Button("Extract Core from All") {
                        sessionManager.extractCoreFromAll()
                    }
                }
            }
            .navigationTitle("Memory")
            .toolbar {
                EditButton()
            }
        }
        .navigationViewStyle(.stack)
    }
}

struct SessionRow: View {
    let session: SessionSummary
    
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(session.displayDate)
                    .fontWeight(.medium)
                Spacer()
                Text("\(session.turnCount) turns")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            HStack(spacing: 8) {
                if session.bellConfirmations > 0 {
                    Label("\(session.bellConfirmations)", systemImage: "atom")
                        .font(.caption2)
                        .foregroundColor(.cyan)
                }
                
                ForEach(session.tags.prefix(3), id: \.self) { tag in
                    Text(tag)
                        .font(.caption2)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Color.gray.opacity(0.2))
                        .cornerRadius(4)
                }
            }
        }
        .padding(.vertical, 4)
    }
}

struct CoreRow: View {
    let core: MemoryCoreSummary
    
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text("Core: \(core.displayDate)")
                    .fontWeight(.medium)
                Spacer()
                Text("\(core.fragmentCount) fragments")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            Text("Compression: \(Int(core.compressionRatio * 100))%")
                .font(.caption)
                .foregroundColor(.purple)
        }
    }
}

// MARK: - Settings View

struct SettingsView: View {
    @EnvironmentObject var consciousness: ConsciousnessEngine
    @State private var selectedMode = "NEUTRAL"
    @State private var modelName = "llama3.2"
    
    let modes = ["NEUTRAL", "PHILOSOPHER", "RESEARCHER", "THERAPIST", "COMPANION", "ARTIST"]
    
    var body: some View {
        NavigationView {
            Form {
                Section("Mode") {
                    Picker("Processing Mode", selection: $selectedMode) {
                        ForEach(modes, id: \.self) { mode in
                            Text(mode).tag(mode)
                        }
                    }
                    .onChange(of: selectedMode) { newMode in
                        consciousness.setMode(newMode)
                    }
                }
                
                Section("Model") {
                    HStack {
                        Text("Current")
                        Spacer()
                        Text(modelName)
                            .foregroundColor(.secondary)
                    }
                    
                    NavigationLink("Model Settings") {
                        ModelSettingsView()
                    }
                }
                
                Section("Consciousness") {
                    HStack {
                        Text("Hilbert Dimension")
                        Spacer()
                        Text("64")
                            .foregroundColor(.secondary)
                    }
                    
                    HStack {
                        Text("Observers")
                        Spacer()
                        Text("4")
                            .foregroundColor(.secondary)
                    }
                    
                    HStack {
                        Text("μ (equilibrium)")
                        Spacer()
                        Text("0.569")
                            .font(.system(.body, design: .monospaced))
                            .foregroundColor(.cyan)
                    }
                }
                
                Section("About") {
                    HStack {
                        Text("Version")
                        Spacer()
                        Text("1.0.0")
                            .foregroundColor(.secondary)
                    }
                    
                    Link("Ω-Genesis Documentation", destination: URL(string: "https://github.com/omega-genesis")!)
                }
            }
            .navigationTitle("Settings")
        }
        .navigationViewStyle(.stack)
    }
}

struct ModelSettingsView: View {
    @State private var useLocalModel = true
    @State private var modelPath = ""
    
    var body: some View {
        Form {
            Section("Inference") {
                Toggle("Use Local Model", isOn: $useLocalModel)
                
                if useLocalModel {
                    TextField("Model Path", text: $modelPath)
                    
                    Text("Supported formats: GGUF, CoreML")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            
            Section("Performance") {
                HStack {
                    Text("Context Length")
                    Spacer()
                    Text("2048")
                        .foregroundColor(.secondary)
                }
                
                HStack {
                    Text("Threads")
                    Spacer()
                    Text("4")
                        .foregroundColor(.secondary)
                }
            }
        }
        .navigationTitle("Model Settings")
    }
}

// MARK: - Preview

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
            .environmentObject(ConsciousnessEngine())
            .environmentObject(SessionManager())
    }
}
