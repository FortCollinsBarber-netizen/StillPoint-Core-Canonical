import XCTest
@testable import CivicClockWatch

final class ClockGroundZeroAndLunarTests: XCTestCase {
    func testGroundZeroRequiresFreshPrecisionGradeObservationShape() {
        let precise = GroundZeroObservation(
            id: GroundZeroObservation.canonicalID,
            capturedAt: Date(timeIntervalSince1970: 1_795_433_529),
            latitude: 40.0,
            longitude: -105.0,
            altitudeMeters: 1500,
            horizontalAccuracyMeters: 8,
            verticalAccuracyMeters: 12,
            timeZoneIdentifier: "America/Denver",
            source: GroundZeroObservation.sourceID
        )
        XCTAssertTrue(precise.isValid)

        let coarse = GroundZeroObservation(
            id: GroundZeroObservation.canonicalID,
            capturedAt: precise.capturedAt,
            latitude: precise.latitude,
            longitude: precise.longitude,
            altitudeMeters: nil,
            horizontalAccuracyMeters: 100,
            verticalAccuracyMeters: nil,
            timeZoneIdentifier: precise.timeZoneIdentifier,
            source: GroundZeroObservation.sourceID
        )
        XCTAssertFalse(coarse.isValid)
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
