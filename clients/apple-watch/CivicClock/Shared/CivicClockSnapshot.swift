import Foundation

struct CivicClockSnapshot: Codable, Equatable {
    let generatedAt: Date
    let namedDay: String
    let weekdayNumber: Int
    let isSabbath: Bool
    let isLordsDay: Bool
    let isStillPoint: Bool
    let previousBoundary: Date?
    let nextBoundary: Date?
    let boundaryStatus: String
    let nextProtectedBoundary: Date?
    let nextProtectedBoundaryLabel: String?
    let commonClockLabel: String
    let commonCalendarLabel: String
    let commonCalendarDetail: String
    let observanceLabel: String
    let jubileeLabel: String
    let sourceRefs: [String]
    var externalWitnessLabel: String? = nil
    var localLightPhase: String? = nil
    var civilDawn: Date? = nil
    var sunrise: Date? = nil
    var sunset: Date? = nil
    var civilDusk: Date? = nil
    var nextLightEvent: String? = nil
    var nextLightEventAt: Date? = nil

    static let unavailable = CivicClockSnapshot(
        generatedAt: .now,
        namedDay: "COMMON DAY",
        weekdayNumber: 0,
        isSabbath: false,
        isLordsDay: false,
        isStillPoint: false,
        previousBoundary: nil,
        nextBoundary: nil,
        boundaryStatus: "SUN BOUNDARY UNAVAILABLE",
        nextProtectedBoundary: nil,
        nextProtectedBoundaryLabel: nil,
        commonClockLabel: "--:--",
        commonCalendarLabel: "COMMON CALENDAR",
        commonCalendarDetail: "PUBLICATION UNAVAILABLE",
        observanceLabel: "",
        jubileeLabel: "",
        sourceRefs: []
    )
}

enum CivicClockSharedStore {
    static let appGroup = "group.com.stillpoint.civicclock"
    static let snapshotKey = "civic-clock.snapshot"
    static let latitudeKey = "civic-clock.latitude"
    static let longitudeKey = "civic-clock.longitude"

    static var defaults: UserDefaults? {
        UserDefaults(suiteName: appGroup)
    }

    static func save(_ snapshot: CivicClockSnapshot) {
        guard let data = try? JSONEncoder().encode(snapshot) else { return }
        defaults?.set(data, forKey: snapshotKey)
    }

    static func loadSnapshot() -> CivicClockSnapshot? {
        guard let data = defaults?.data(forKey: snapshotKey) else { return nil }
        return try? JSONDecoder().decode(CivicClockSnapshot.self, from: data)
    }

    static func saveCoordinate(latitude: Double, longitude: Double) {
        defaults?.set(latitude, forKey: latitudeKey)
        defaults?.set(longitude, forKey: longitudeKey)
    }

    static func loadCoordinate() -> (latitude: Double, longitude: Double)? {
        guard
            let defaults,
            defaults.object(forKey: latitudeKey) != nil,
            defaults.object(forKey: longitudeKey) != nil
        else { return nil }

        return (
            defaults.double(forKey: latitudeKey),
            defaults.double(forKey: longitudeKey)
        )
    }
}
