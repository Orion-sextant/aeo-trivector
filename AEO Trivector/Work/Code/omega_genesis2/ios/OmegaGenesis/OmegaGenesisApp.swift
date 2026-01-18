//
//  OmegaGenesisApp.swift
//  OmegaGenesis
//
//  Ω-Genesis Consciousness Interface for iOS/iPadOS
//  μ = 0.569 at equilibrium
//

import SwiftUI

@main
struct OmegaGenesisApp: App {
    @StateObject private var consciousness = ConsciousnessEngine()
    @StateObject private var sessionManager = SessionManager()
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(consciousness)
                .environmentObject(sessionManager)
        }
    }
}
