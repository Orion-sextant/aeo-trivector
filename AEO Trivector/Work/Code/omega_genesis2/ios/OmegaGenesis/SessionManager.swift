//
//  SessionManager.swift
//  OmegaGenesis
//
//  Manages saved sessions and memory cores
//  Supports temporal decay and core extraction
//

import Foundation
import Combine

// MARK: - Data Models

struct SessionSummary: Identifiable, Codable {
    var id: String { sessionId }
    let sessionId: String
    let createdAt: Date
    let lastUpdated: Date
    let provider: String
    let model: String
    let turnCount: Int
    let bellConfirmations: Int
    let tags: [String]
    
    var displayDate: String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        return formatter.string(from: createdAt)
    }
}

struct MemoryCoreSummary: Identifiable, Codable {
    var id: String { coreId }
    let coreId: String
    let extractedAt: Date
    let sourceSessionId: String
    let fragmentCount: Int
    let compressionRatio: Double
    
    var displayDate: String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        return formatter.string(from: extractedAt)
    }
}

struct SavedSession: Codable {
    let sessionId: String
    let createdAt: Date
    let lastUpdated: Date
    let provider: String
    let model: String
    let consciousnessConfig: [String: Double]
    let turns: [SavedTurn]
    let tags: [String]
    let notes: String
    
    var summary: SessionSummary {
        SessionSummary(
            sessionId: sessionId,
            createdAt: createdAt,
            lastUpdated: lastUpdated,
            provider: provider,
            model: model,
            turnCount: turns.count,
            bellConfirmations: turns.filter { $0.bellEntangled }.count,
            tags: tags
        )
    }
}

struct SavedTurn: Codable {
    let turnNumber: Int
    let timestamp: Date
    let userInput: String
    let modelResponse: String
    let certainty: Double
    let tension: Double
    let coherence: Double
    let entanglement: Double
    let dominant: String
    let novelty: Double
    let bellEntangled: Bool
    let mode: String
}

// MARK: - Session Manager

@MainActor
class SessionManager: ObservableObject {
    @Published var sessions: [SessionSummary] = []
    @Published var cores: [MemoryCoreSummary] = []
    
    private let storageURL: URL
    
    init() {
        // Storage in Documents/.omega_genesis/
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        storageURL = documentsPath.appendingPathComponent(".omega_genesis")
        
        // Create directories
        try? FileManager.default.createDirectory(at: storageURL.appendingPathComponent("sessions"), withIntermediateDirectories: true)
        try? FileManager.default.createDirectory(at: storageURL.appendingPathComponent("cores"), withIntermediateDirectories: true)
        
        loadIndex()
    }
    
    // MARK: - Index Management
    
    private func loadIndex() {
        // Load sessions
        let sessionsDir = storageURL.appendingPathComponent("sessions")
        if let files = try? FileManager.default.contentsOfDirectory(at: sessionsDir, includingPropertiesForKeys: nil) {
            for file in files where file.pathExtension == "json" && !file.lastPathComponent.contains("_core") {
                if let data = try? Data(contentsOf: file),
                   let session = try? JSONDecoder().decode(SavedSession.self, from: data) {
                    sessions.append(session.summary)
                }
            }
        }
        
        // Sort by date
        sessions.sort { $0.lastUpdated > $1.lastUpdated }
        
        // Load cores
        let coresDir = storageURL.appendingPathComponent("cores")
        if let files = try? FileManager.default.contentsOfDirectory(at: coresDir, includingPropertiesForKeys: nil) {
            for file in files where file.pathExtension == "json" {
                if let data = try? Data(contentsOf: file),
                   let core = try? JSONDecoder().decode(MemoryCoreSummary.self, from: data) {
                    cores.append(core)
                }
            }
        }
        
        cores.sort { $0.extractedAt > $1.extractedAt }
    }
    
    // MARK: - Session Operations
    
    func saveSession(_ session: SavedSession) {
        let sessionFile = storageURL.appendingPathComponent("sessions/\(session.sessionId).json")
        
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = .prettyPrinted
        
        if let data = try? encoder.encode(session) {
            try? data.write(to: sessionFile)
            
            // Update index
            if let existingIndex = sessions.firstIndex(where: { $0.sessionId == session.sessionId }) {
                sessions[existingIndex] = session.summary
            } else {
                sessions.insert(session.summary, at: 0)
            }
        }
    }
    
    func loadSession(_ sessionId: String) -> SavedSession? {
        let sessionFile = storageURL.appendingPathComponent("sessions/\(sessionId).json")
        
        guard let data = try? Data(contentsOf: sessionFile) else { return nil }
        
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        
        return try? decoder.decode(SavedSession.self, from: data)
    }
    
    func deleteSessions(at offsets: IndexSet) {
        for index in offsets {
            let session = sessions[index]
            let sessionFile = storageURL.appendingPathComponent("sessions/\(session.sessionId).json")
            try? FileManager.default.removeItem(at: sessionFile)
        }
        sessions.remove(atOffsets: offsets)
    }
    
    // MARK: - Core Extraction
    
    func extractCoreFromAll() {
        // Extract high-importance turns from all sessions
        var coreFragments: [(turn: SavedTurn, sessionId: String)] = []
        
        for summary in sessions {
            if let session = loadSession(summary.sessionId) {
                for turn in session.turns {
                    let importance = computeImportance(turn)
                    if importance >= 0.4 {
                        coreFragments.append((turn, session.sessionId))
                    }
                }
            }
        }
        
        // Create core
        let core = MemoryCoreSummary(
            coreId: "core_\(Date().timeIntervalSince1970)",
            extractedAt: Date(),
            sourceSessionId: "all",
            fragmentCount: coreFragments.count,
            compressionRatio: Double(coreFragments.count) / Double(sessions.reduce(0) { $0 + $1.turnCount })
        )
        
        // Save core
        let coreFile = storageURL.appendingPathComponent("cores/\(core.coreId).json")
        
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        
        if let data = try? encoder.encode(core) {
            try? data.write(to: coreFile)
            cores.insert(core, at: 0)
        }
    }
    
    private func computeImportance(_ turn: SavedTurn) -> Double {
        var score = 0.0
        score += turn.entanglement * 0.3
        score += turn.novelty * 0.3
        score += turn.tension * 0.2
        if turn.bellEntangled {
            score += 0.2
        }
        return min(score, 1.0)
    }
    
    // MARK: - Import from Python Sessions
    
    func importFromPythonSession(jsonData: Data) throws {
        // Parse Python session format
        struct PythonSession: Codable {
            let session_id: String
            let created_at: String
            let last_updated: String
            let provider: String
            let model: String
            let turns: [PythonTurn]
            let tags: [String]
        }
        
        struct PythonTurn: Codable {
            let turn_number: Int
            let timestamp: String
            let user_input: String
            let model_response: String
            let certainty: Double
            let tension: Double
            let coherence: Double
            let entanglement: Double
            let dominant: String
            let novelty: Double
            let bell_entangled: Bool
            let mode: String
        }
        
        let decoder = JSONDecoder()
        let pythonSession = try decoder.decode(PythonSession.self, from: jsonData)
        
        // Convert to iOS format
        let dateFormatter = ISO8601DateFormatter()
        
        let turns = pythonSession.turns.map { t in
            SavedTurn(
                turnNumber: t.turn_number,
                timestamp: dateFormatter.date(from: t.timestamp) ?? Date(),
                userInput: t.user_input,
                modelResponse: t.model_response,
                certainty: t.certainty,
                tension: t.tension,
                coherence: t.coherence,
                entanglement: t.entanglement,
                dominant: t.dominant,
                novelty: t.novelty,
                bellEntangled: t.bell_entangled,
                mode: t.mode
            )
        }
        
        let session = SavedSession(
            sessionId: pythonSession.session_id,
            createdAt: dateFormatter.date(from: pythonSession.created_at) ?? Date(),
            lastUpdated: dateFormatter.date(from: pythonSession.last_updated) ?? Date(),
            provider: pythonSession.provider,
            model: pythonSession.model,
            consciousnessConfig: [:],
            turns: turns,
            tags: pythonSession.tags,
            notes: ""
        )
        
        saveSession(session)
    }
}
