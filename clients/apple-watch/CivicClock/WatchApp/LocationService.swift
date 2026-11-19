import CoreLocation
import Foundation

@MainActor
final class LocationService: NSObject, ObservableObject, CLLocationManagerDelegate {
    @Published private(set) var coordinate: CLLocationCoordinate2D?
    @Published private(set) var authorization: CLAuthorizationStatus
    @Published private(set) var accuracyAuthorization: CLAccuracyAuthorization
    @Published private(set) var groundZero: GroundZeroObservation?
    @Published private(set) var isMeasuringGroundZero = false

    private let manager = CLLocationManager()
    private var acquisitionStartedAt: Date?
    private var acquisitionTimeout: Task<Void, Never>?

    override init() {
        authorization = manager.authorizationStatus
        accuracyAuthorization = manager.accuracyAuthorization
        groundZero = CivicClockSharedStore.loadGroundZero()
        super.init()
        manager.delegate = self

        if let cached = CivicClockSharedStore.loadCoordinate() {
            coordinate = CLLocationCoordinate2D(
                latitude: cached.latitude,
                longitude: cached.longitude
            )
        }
    }

    func start() {
        authorization = manager.authorizationStatus
        accuracyAuthorization = manager.accuracyAuthorization

        switch authorization {
        case .notDetermined:
            manager.requestWhenInUseAuthorization()
        case .authorizedAlways, .authorizedWhenInUse:
            beginMeasurement()
        default:
            stop()
        }
    }

    // End Core Location's high-accuracy sampling when the app is inactive,
    // authorization is withdrawn, an error occurs, or the attempt times out.
    // A later foreground activation may start a new bounded attempt.
    func stop() {
        acquisitionTimeout?.cancel()
        acquisitionTimeout = nil
        if isMeasuringGroundZero {
            manager.stopUpdatingLocation()
        }
        isMeasuringGroundZero = false
        acquisitionStartedAt = nil
    }

    private func beginMeasurement() {
        manager.desiredAccuracy = kCLLocationAccuracyBest
        manager.distanceFilter = kCLDistanceFilterNone

        if groundZero == nil {
            // One bounded high-accuracy attempt. A poor GPS fix must not keep
            // continuous location sampling running indefinitely.
            guard !isMeasuringGroundZero else { return }
            acquisitionStartedAt = Date()
            isMeasuringGroundZero = true
            manager.startUpdatingLocation()
            acquisitionTimeout?.cancel()
            acquisitionTimeout = Task { [weak self] in
                do {
                    try await Task.sleep(
                        nanoseconds: UInt64(
                            GroundZeroSamplingPolicy.maximumDurationSeconds * 1_000_000_000
                        )
                    )
                } catch {
                    return
                }
                self?.stop()
            }
        } else {
            // Ground Zero is immutable. Later measurements are current-location
            // inputs for local horizon calculations only.
            manager.requestLocation()
        }
    }

    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        authorization = manager.authorizationStatus
        accuracyAuthorization = manager.accuracyAuthorization
        if authorization == .authorizedAlways || authorization == .authorizedWhenInUse {
            beginMeasurement()
        } else {
            stop()
        }
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard authorization == .authorizedAlways || authorization == .authorizedWhenInUse else {
            return
        }
        guard
            let location = locations
                .filter({ $0.horizontalAccuracy >= 0 })
                .max(by: { $0.timestamp < $1.timestamp })
        else { return }

        coordinate = location.coordinate
        CivicClockSharedStore.saveCoordinate(
            latitude: location.coordinate.latitude,
            longitude: location.coordinate.longitude
        )

        guard groundZero == nil else { return }

        guard
            let acquisitionStartedAt,
            GroundZeroSamplingPolicy.shouldContinue(
                startedAt: acquisitionStartedAt,
                now: Date(),
                authorized: authorization == .authorizedAlways
                    || authorization == .authorizedWhenInUse,
                hasGroundZero: groundZero != nil
            )
        else {
            stop()
            return
        }

        accuracyAuthorization = manager.accuracyAuthorization
        let fullAccuracy = accuracyAuthorization == .fullAccuracy
        let sourceInformation = location.sourceInformation
        let simulated = sourceInformation?.isSimulatedBySoftware

        let age = abs(location.timestamp.timeIntervalSinceNow)
        guard
            fullAccuracy,
            simulated != true,
            age <= 30,
            location.horizontalAccuracy <= GroundZeroObservation.maximumLockAccuracyMeters
        else { return }

        let verticalAccuracy: Double? =
            location.verticalAccuracy >= 0 ? location.verticalAccuracy : nil
        let altitude: Double? =
            location.verticalAccuracy >= 0 ? location.altitude : nil

        let observation = GroundZeroObservation(
            id: GroundZeroObservation.canonicalID,
            capturedAt: location.timestamp,
            latitude: location.coordinate.latitude,
            longitude: location.coordinate.longitude,
            altitudeMeters: altitude,
            horizontalAccuracyMeters: location.horizontalAccuracy,
            verticalAccuracyMeters: verticalAccuracy,
            timeZoneIdentifier: TimeZone.current.identifier,
            source: GroundZeroObservation.sourceID,
            coordinateSystem: GroundZeroObservation.coordinateReferenceSystem,
            fullAccuracyAuthorized: fullAccuracy,
            simulatedBySoftware: simulated,
            producedByAccessory: sourceInformation?.isProducedByAccessory
        )

        if CivicClockSharedStore.saveGroundZeroIfAbsent(observation) {
            groundZero = observation
            stop()
        } else if let existing = CivicClockSharedStore.loadGroundZero() {
            // Another consumer may have already saved the immutable value.
            groundZero = existing
            stop()
        }
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        // Stop a failed acquisition instead of draining battery indefinitely.
        // Preserve the last good coordinate and any immutable Ground Zero.
        stop()
    }
}
