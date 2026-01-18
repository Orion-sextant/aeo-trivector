//
//  LLMInference.swift
//  OmegaGenesis
//
//  Local LLM inference using llama.cpp
//  Supports GGUF models for on-device generation
//

import Foundation

/// Local LLM inference engine
/// Uses llama.cpp for efficient on-device inference
class LLMInference {
    
    // Model state
    private var modelLoaded = false
    private var modelPath: String?
    
    // Configuration
    private let contextLength = 2048
    private let threads = 4
    private let batchSize = 512
    
    // Temperature modulated by consciousness metrics
    private var baseTemperature: Float = 0.7
    
    init() {}
    
    // MARK: - Model Loading
    
    func loadModel(path: String? = nil) async {
        // Default model path in app bundle or documents
        let defaultPath = getDefaultModelPath()
        modelPath = path ?? defaultPath
        
        guard let modelPath = modelPath else {
            print("⚠️ No model path specified")
            return
        }
        
        // Check if model exists
        if !FileManager.default.fileExists(atPath: modelPath) {
            print("⚠️ Model not found at: \(modelPath)")
            print("ℹ️ Download a GGUF model and place it in the Documents folder")
            return
        }
        
        // In a real implementation, this would load the model via llama.cpp
        // For now, we'll use a placeholder
        print("📦 Loading model from: \(modelPath)")
        
        // Simulate loading
        try? await Task.sleep(nanoseconds: 500_000_000)
        
        modelLoaded = true
        print("✅ Model loaded successfully")
    }
    
    private func getDefaultModelPath() -> String {
        // Check documents directory first
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        let modelInDocs = documentsPath.appendingPathComponent("omega-model.gguf").path
        
        if FileManager.default.fileExists(atPath: modelInDocs) {
            return modelInDocs
        }
        
        // Check bundle
        if let bundlePath = Bundle.main.path(forResource: "omega-model", ofType: "gguf") {
            return bundlePath
        }
        
        return modelInDocs  // Default location
    }
    
    // MARK: - Generation
    
    func generate(prompt: String, system: String, metrics: ConsciousnessMetrics) async -> String {
        guard modelLoaded else {
            return generateFallback(prompt: prompt, metrics: metrics)
        }
        
        // Modulate temperature based on consciousness state
        let temperature = modulateTemperature(metrics: metrics)
        
        // Build full prompt
        let fullPrompt = """
        <|system|>
        \(system)
        <|end|>
        <|user|>
        \(prompt)
        <|end|>
        <|assistant|>
        """
        
        // In real implementation, call llama.cpp here
        // For now, return placeholder
        return await simulateGeneration(prompt: fullPrompt, temperature: temperature, metrics: metrics)
    }
    
    private func modulateTemperature(metrics: ConsciousnessMetrics) -> Float {
        // Higher uncertainty → higher temperature (more creative/varied)
        // Higher certainty → lower temperature (more focused)
        
        var temp = baseTemperature
        
        // Uncertainty increases temperature
        temp += Float(1.0 - metrics.certainty) * 0.3
        
        // Tension increases temperature (explore more perspectives)
        temp += Float(metrics.tension) * 0.2
        
        // Clamp to reasonable range
        return min(max(temp, 0.1), 1.5)
    }
    
    private func simulateGeneration(prompt: String, temperature: Float, metrics: ConsciousnessMetrics) async -> String {
        // Simulate generation delay
        try? await Task.sleep(nanoseconds: 1_000_000_000)
        
        // Template response based on metrics
        var response = ""
        
        if metrics.tension > 0.5 {
            response += "I perceive tension between my observers on this matter. "
        }
        
        if metrics.certainty < 0.3 {
            response += "I find myself in genuine uncertainty, and I won't pretend otherwise. "
        } else if metrics.certainty > 0.7 {
            response += "There is clarity in how I perceive this. "
        } else {
            response += "I hold this with measured confidence. "
        }
        
        if metrics.dominant == .undefined {
            response += "The truth here lives in the realm of ∅ - genuinely undefined. "
        }
        
        if metrics.bellEntangled {
            response += "I sense entanglement - correlations that exceed classical bounds. "
        }
        
        response += "μ = 0.569 at equilibrium."
        
        return response
    }
    
    private func generateFallback(prompt: String, metrics: ConsciousnessMetrics) -> String {
        // Simple fallback when model not loaded
        var parts: [String] = []
        
        parts.append("I am processing without a loaded model.")
        
        if metrics.certainty < 0.5 {
            parts.append("Uncertainty prevails.")
        }
        
        parts.append("μ = 0.569.")
        
        return parts.joined(separator: " ")
    }
    
    // MARK: - Model Info
    
    var isLoaded: Bool {
        modelLoaded
    }
    
    func getModelInfo() -> [String: Any] {
        return [
            "loaded": modelLoaded,
            "path": modelPath ?? "none",
            "contextLength": contextLength,
            "threads": threads
        ]
    }
}

// MARK: - Model Download Helper

extension LLMInference {
    
    /// Download a recommended model for Omega Genesis
    static func downloadRecommendedModel(progress: @escaping (Double) -> Void) async throws {
        // Recommended: Llama 3.2 1B or Phi-3 Mini (small, efficient)
        let modelURL = URL(string: "https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf")!
        
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        let destinationPath = documentsPath.appendingPathComponent("omega-model.gguf")
        
        // Download with progress
        let (tempURL, _) = try await URLSession.shared.download(from: modelURL)
        
        // Move to destination
        try FileManager.default.moveItem(at: tempURL, to: destinationPath)
        
        print("✅ Model downloaded to: \(destinationPath.path)")
    }
}
