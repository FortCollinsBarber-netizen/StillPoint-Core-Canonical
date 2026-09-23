import XCTest
@testable import CivicClockWatch

final class ExternalCalendarWitnessTests: XCTestCase {
    func testSharedWitnessCatalogLoadsAndHasNoGridAuthority() throws {
        let catalog = try XCTUnwrap(
            ExternalCalendarWitnessLoader.load()
        )

        XCTAssertEqual(
            catalog.version,
            "stillpoint-external-calendar-witnesses-v1"
        )
        XCTAssertEqual(
            catalog.authorityStatus,
            "witness-layer-no-grid-authority"
        )
        XCTAssertFalse(catalog.jurisdiction.gridAuthority)
        XCTAssertFalse(catalog.jurisdiction.mayInsertDays)
        XCTAssertFalse(catalog.jurisdiction.mayAlterWeekday)
        XCTAssertFalse(catalog.scope.repeatIntoLaterCommonYears)
        XCTAssertEqual(catalog.scope.externalProjectionYear, 2026)
        XCTAssertTrue(
            catalog.events.allSatisfy {
                !$0.grid_authority && $0.calendar_effect == "none"
            }
        )
    }

    func testPassoverAndRamadanSeedWitnessesRemainExternal() throws {
        let catalog = try XCTUnwrap(
            ExternalCalendarWitnessLoader.load()
        )

        let passover = catalog.events(
            onExternalDate: "2026-04-01"
        )
        XCTAssertTrue(
            passover.contains {
                $0.id == "jewish-passover-2026"
                    && $0.begins_at == "sunset"
            }
        )

        let ramadan = catalog.events(
            onExternalDate: "2026-02-17"
        )
        let witness = try XCTUnwrap(
            ramadan.first {
                $0.id == "islamic-ramadan-begins-2026"
            }
        )
        XCTAssertEqual(witness.begins_at, "sunset")
        XCTAssertTrue(
            witness.qualification?.lowercased().contains("sighting")
                == true
        )
    }

    func testExternalWitnessesDoNotCreateARepeatingAppleCalendarRule() throws {
        let catalog = try XCTUnwrap(
            ExternalCalendarWitnessLoader.load()
        )

        XCTAssertEqual(
            catalog.scope.role,
            "comparison-and-observation-only"
        )
        XCTAssertFalse(
            catalog.scope.repeatIntoLaterCommonYears
        )
    }
}
