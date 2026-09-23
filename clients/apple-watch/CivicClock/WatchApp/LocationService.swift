import CoreLocation
import Foundation

@MainActor
final class LocationService: NSObject, ObservableObject, CLLocationManagerDelegate {
    @Published private(set) var coordinate: CLLocationCoordinate2D?
    @Published private(set) var authorization: CLAuthorizationStatus
    @Published private(set) var accuracyAuthorization: CLAccuracyAuthorization
    @Published private(set) var groundZero: GroundZeroObservation?

    private let manager = CLLocationManager()

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
            break
        }
    }

    private func beginMeasurement() {
        manager.desiredAccuracy = kCLLocationAccuracyBest
        manager.distanceFilter = kCLDistanceFilterNone

        if groundZero == nil {
            // Keep sampling until the first precise, fresh, non-simulated
            // observation is locked.
            manager.startUpdatingLocation()
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
        }
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
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
            manager.stopUpdatingLocation()
        }
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        // Cached current location and the immutable Ground Zero observation remain
        // available. The UI owns the visible degraded state.
    }
}
