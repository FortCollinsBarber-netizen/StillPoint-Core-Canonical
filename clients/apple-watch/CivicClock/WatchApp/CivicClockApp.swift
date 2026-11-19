import SwiftUI

@main
struct CivicClockApp: App {
    @Environment(\.scenePhase) private var scenePhase
    @StateObject private var locationService = LocationService()

    var body: some Scene {
        WindowGroup {
            CivicClockView()
                .environmentObject(locationService)
                .task {
                    if scenePhase == .active {
                        locationService.start()
                    }
                }
                .onChange(of: scenePhase) { _, newPhase in
                    if newPhase == .active {
                        locationService.start()
                    } else {
                        locationService.stop()
                    }
                }
        }
    }
}
