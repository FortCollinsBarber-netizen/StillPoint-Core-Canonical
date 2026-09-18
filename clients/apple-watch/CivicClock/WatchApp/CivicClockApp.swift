import SwiftUI

@main
struct CivicClockApp: App {
    @StateObject private var locationService = LocationService()

    var body: some Scene {
        WindowGroup {
            CivicClockView()
                .environmentObject(locationService)
                .task {
                    locationService.start()
                }
        }
    }
}
