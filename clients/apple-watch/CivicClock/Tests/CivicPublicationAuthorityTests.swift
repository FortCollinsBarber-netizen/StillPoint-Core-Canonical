import XCTest
@testable import CivicClockWatch

final class CivicPublicationAuthorityTests: XCTestCase {
    private func resourceURL(_ name: String) -> URL {
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("Resources")
            .appendingPathComponent(name)
    }

    func testBundledCivicPolicyAuthorizesFinitePublication() throws {
        let policy = try XCTUnwrap(
            CivicPublicationAuthority.loadPolicy(
                url: resourceURL("apple_publication_policy.json")
            )
        )
        let spec = try XCTUnwrap(
            CalendarCoreSpecLoader.load(
                url: resourceURL("calendar_core_spec.json")
            )
        )
        let calendar = try XCTUnwrap(
            PublishedCalendarLoader.load(
                url: resourceURL("published_calendar.json"),
                policy: policy,
                calendarCoreSpec: spec
            )
        )

        XCTAssertTrue(calendar.isValidatedForProjection)
        XCTAssertEqual(calendar.years.count, 1)
        XCTAssertEqual(calendar.years[0].year, 2026)
        XCTAssertEqual(calendar.years[0].openingCivilDate, "2026-01-01")
        XCTAssertEqual(
            calendar.years[0].reconciliationDaysAfterCompletion,
            0
        )

        let receipt = try XCTUnwrap(calendar.validationReceipt)
        XCTAssertEqual(
            receipt.authorityID,
            "STILLPOINT_CIVIC_PILOT_AUTHORITY_V1"
        )
        XCTAssertEqual(receipt.authorityStatus, "pilot")
        XCTAssertEqual(receipt.referencePointID, "GROUND_ZERO")
        XCTAssertEqual(receipt.ephemerisSource, "USNO_AA_SEASONS_API")
        XCTAssertEqual(
            receipt.publicationDigest,
            "44beb06f964d0b88bb74fbea317745d26f7ff2f25661fcbb6bb8eba7d20ccb77"
        )
    }
}
