import Foundation

struct GroundZeroBindingPayload: Codable, Equatable {
    static let schemaID = "stillpoint.ground-zero-measurement.v1"

    let schema: String
    let groundZeroID: String
    let source: String
    let coordinateSystem: String
    let latitude: Double
    let longitude: Double
    let altitudeMeters: Double?
    let horizontalAccuracyMeters: Double
    let verticalAccuracyMeters: Double?
    let capturedAt: String
    let timeZoneIdentifier: String
    let fullAccuracyAuthorized: Bool
    let simulatedBySoftware: Bool?
    let producedByAccessory: Bool?
}

struct GroundZeroObservation: Codable, Equatable {
    static let canonicalID = "STILLPOINT-GROUND-ZERO-001"
    static let sourceID = "apple-core-location"
    static let coordinateReferenceSystem = "WGS84"
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
    let coordinateSystem: String
    let fullAccuracyAuthorized: Bool
    let simulatedBySoftware: Bool?
    let producedByAccessory: Bool?

    var isValid: Bool {
        (-90.0...90.0).contains(latitude)
            && (-180.0...180.0).contains(longitude)
            && horizontalAccuracyMeters >= 0
            && horizontalAccuracyMeters <= Self.maximumLockAccuracyMeters
            && !timeZoneIdentifier.isEmpty
            && source == Self.sourceID
            && coordinateSystem == Self.coordinateReferenceSystem
            && fullAccuracyAuthorized
            && simulatedBySoftware != true
    }

    func bindingPayload() -> GroundZeroBindingPayload {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [
            .withInternetDateTime,
            .withFractionalSeconds,
        ]
        return GroundZeroBindingPayload(
            schema: GroundZeroBindingPayload.schemaID,
            groundZeroID: id,
            source: source,
            coordinateSystem: coordinateSystem,
            latitude: latitude,
            longitude: longitude,
            altitudeMeters: altitudeMeters,
            horizontalAccuracyMeters: horizontalAccuracyMeters,
            verticalAccuracyMeters: verticalAccuracyMeters,
            capturedAt: formatter.string(from: capturedAt),
            timeZoneIdentifier: timeZoneIdentifier,
            fullAccuracyAuthorized: fullAccuracyAuthorized,
            simulatedBySoftware: simulatedBySoftware,
            producedByAccessory: producedByAccessory
        )
    }
}

extension CivicClockSharedStore {
    static let groundZeroKey = "civic-clock.ground-zero.v2"
    static let groundZeroBindingPayloadKey =
        "civic-clock.ground-zero-binding-payload.v1"

    static func saveGroundZeroIfAbsent(_ observation: GroundZeroObservation) -> Bool {
        guard observation.isValid, defaults?.data(forKey: groundZeroKey) == nil else {
            return false
        }
        guard
            let data = try? JSONEncoder().encode(observation),
            let bindingData = try? JSONEncoder().encode(
                observation.bindingPayload()
            )
        else {
            return false
        }
        defaults?.set(data, forKey: groundZeroKey)
        defaults?.set(bindingData, forKey: groundZeroBindingPayloadKey)
        return true
    }

    static func loadGroundZero() -> GroundZeroObservation? {
        guard
            let data = defaults?.data(forKey: groundZeroKey),
            let observation = try? JSONDecoder().decode(
                GroundZeroObservation.self,
                from: data
            ),
            observation.isValid
        else { return nil }

        return observation
    }

    static func loadGroundZeroBindingPayload() -> GroundZeroBindingPayload? {
        guard
            let data = defaults?.data(forKey: groundZeroBindingPayloadKey)
        else { return nil }

        return try? JSONDecoder().decode(
            GroundZeroBindingPayload.self,
            from: data
        )
    }
}
