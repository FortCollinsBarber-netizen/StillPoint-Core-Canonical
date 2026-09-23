import Foundation

struct GroundZeroObservation: Codable, Equatable {
    static let canonicalID = "STILLPOINT-GROUND-ZERO-001"
    static let sourceID = "apple-core-location"
    static let maximumLockAccuracyMeters = 25.0

    let id: String
    let capturedAt: Date
    let latitude: Double
    let longitude: Double
    let altitudeMeters: Double?
    let horizontalAccuracyMeters: Double
    let verticalAccuracyMeters: Double?
    let timeZoneIdentifier: String
    let source: String

    var isValid: Bool {
        (-90.0...90.0).contains(latitude)
            && (-180.0...180.0).contains(longitude)
            && horizontalAccuracyMeters >= 0
            && horizontalAccuracyMeters <= Self.maximumLockAccuracyMeters
            && !timeZoneIdentifier.isEmpty
            && source == Self.sourceID
    }
}

extension CivicClockSharedStore {
    static let groundZeroKey = "civic-clock.ground-zero.v1"

    static func saveGroundZeroIfAbsent(_ observation: GroundZeroObservation) -> Bool {
        guard observation.isValid, defaults?.data(forKey: groundZeroKey) == nil else {
            return false
        }
        guard let data = try? JSONEncoder().encode(observation) else {
            return false
        }
        defaults?.set(data, forKey: groundZeroKey)
        return true
    }

    static func loadGroundZero() -> GroundZeroObservation? {
        guard let data = defaults?.data(forKey: groundZeroKey) else { return nil }
        return try? JSONDecoder().decode(GroundZeroObservation.self, from: data)
    }
}
