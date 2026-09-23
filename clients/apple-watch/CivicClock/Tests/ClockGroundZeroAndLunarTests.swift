import XCTest
@testable import CivicClockWatch

final class ClockGroundZeroAndLunarTests: XCTestCase {
    private func observation(
        horizontalAccuracy: Double = 8,
        fullAccuracyAuthorized: Bool = true,
        simulatedBySoftware: Bool? = false
    ) -> GroundZeroObservation {
        GroundZeroObservation(
            id: GroundZeroObservation.canonicalID,
            capturedAt: Date(timeIntervalSince1970: 1_795_433_529),
            latitude: 40.0,
            longitude: -105.0,
            altitudeMeters: 1500,
            horizontalAccuracyMeters: horizontalAccuracy,
            verticalAccuracyMeters: 12,
            timeZoneIdentifier: "America/Denver",
            source: GroundZeroObservation.sourceID,
            coordinateSystem: GroundZeroObservation.coordinateReferenceSystem,
            fullAccuracyAuthorized: fullAccuracyAuthorized,
            simulatedBySoftware: simulatedBySoftware,
            producedByAccessory: false
        )
    }

    func testGroundZeroRequiresPrecisionGradeObservationShape() {
        XCTAssertTrue(observation().isValid)
        XCTAssertFalse(observation(horizontalAccuracy: 100).isValid)
    }

    func testGroundZeroRejectsReducedAccuracyAndSoftwareSimulation() {
        XCTAssertFalse(
            observation(fullAccuracyAuthorized: false).isValid
        )
        XCTAssertFalse(
            observation(simulatedBySoftware: true).isValid
        )
    }

    func testGroundZeroBindingPayloadMatchesRobertOSContract() throws {
        let payload = observation().bindingPayload()

        XCTAssertEqual(
            payload.schema,
            GroundZeroBindingPayload.schemaID
        )
        XCTAssertEqual(
            payload.groundZeroID,
            GroundZeroObservation.canonicalID
        )
        XCTAssertEqual(payload.source, "apple-core-location")
        XCTAssertEqual(payload.coordinateSystem, "WGS84")
        XCTAssertEqual(payload.latitude, 40.0)
        XCTAssertEqual(payload.longitude, -105.0)
        XCTAssertEqual(payload.horizontalAccuracyMeters, 8)
        XCTAssertTrue(payload.fullAccuracyAuthorized)
        XCTAssertEqual(payload.simulatedBySoftware, false)
        let parser = ISO8601DateFormatter()
        parser.formatOptions = [
            .withInternetDateTime,
            .withFractionalSeconds,
        ]
        XCTAssertNotNil(parser.date(from: payload.capturedAt))

        let encoded = try JSONEncoder().encode(payload)
        let object = try XCTUnwrap(
            JSONSerialization.jsonObject(with: encoded)
                as? [String: Any]
        )
        XCTAssertEqual(
            object["schema"] as? String,
            "stillpoint.ground-zero-measurement.v1"
        )
        XCTAssertEqual(
            object["groundZeroID"] as? String,
            GroundZeroObservation.canonicalID
        )
        XCTAssertNil(object["id"])
    }

    func testSeptember23ObservationIsWaxingGibbous() throws {
        let parser = ISO8601DateFormatter()
        let instant = try XCTUnwrap(
            parser.date(from: "2026-09-23T11:32:09Z")
        )

        let state = LunarPhaseCalculator.state(at: instant)

        XCTAssertTrue(state.isWaxing)
        XCTAssertEqual(state.phaseName, "WAXING GIBBOUS")
        XCTAssertGreaterThan(state.illuminationFraction, 0.85)
        XCTAssertLessThan(state.illuminationFraction, 0.95)
        XCTAssertGreaterThan(state.ageDays, 11.0)
        XCTAssertLessThan(state.ageDays, 12.5)
    }

    func testMeanLunationTracksUSNOSeptember2026PrimaryPhases() throws {
        let parser = ISO8601DateFormatter()
        let newMoon = try XCTUnwrap(
            parser.date(from: "2026-09-11T03:27:00Z")
        )
        let fullMoon = try XCTUnwrap(
            parser.date(from: "2026-09-26T16:49:00Z")
        )

        let newState = LunarPhaseCalculator.state(at: newMoon)
        let fullState = LunarPhaseCalculator.state(at: fullMoon)

        XCTAssertEqual(newState.phaseName, "NEW MOON")
        XCTAssertLessThan(newState.illuminationFraction, 0.02)

        XCTAssertEqual(fullState.phaseName, "FULL MOON")
        XCTAssertGreaterThan(fullState.illuminationFraction, 0.99)
    }
}
