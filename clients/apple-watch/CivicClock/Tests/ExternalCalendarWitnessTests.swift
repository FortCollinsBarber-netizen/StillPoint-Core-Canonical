import XCTest
@testable import CivicClockWatch

final class ExternalCalendarWitnessTests: XCTestCase {
    private func fiftyYearFixture() -> PublishedCivicCalendar {
        var calendar = Calendar(identifier: .gregorian)
        calendar.locale = Locale(identifier: "en_US_POSIX")
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!

        let formatter = DateFormatter()
        formatter.calendar = calendar
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = calendar.timeZone
        formatter.dateFormat = "yyyy-MM-dd"
        formatter.isLenient = false

        let first = formatter.date(from: "2026-01-01")!
        let years = (0..<50).map { index -> PublishedCivicYear in
            let opening = calendar.date(
                byAdding: .day,
                value: 364 * index,
                to: first
            )!
            return PublishedCivicYear(
                year: 2026 + index,
                openingCivilDate: formatter.string(from: opening)
            )
        }
        return .conformanceFixture(years: years)
    }

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

    func testClockSnapshotSurfacesWitnessAndLocalLight() throws {
        var calendar = Calendar(identifier: .gregorian)
        calendar.locale = Locale(identifier: "en_US_POSIX")
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!

        let now = try XCTUnwrap(
            ISO8601DateFormatter().date(
                from: "2026-04-01T18:00:00Z"
            )
        )
        let catalog = try XCTUnwrap(
            ExternalCalendarWitnessLoader.load()
        )
        let population = try XCTUnwrap(
            CalendarPopulationLoader.load()
        )

        let snapshot = CivicCalendarEngine.snapshot(
            now: now,
            latitude: 40.0,
            longitude: -105.0,
            publishedCalendar: fiftyYearFixture(),
            population: population,
            externalWitnesses: catalog,
            calendar: calendar
        )

        XCTAssertTrue(
            snapshot.externalWitnessLabel?.contains(
                "Passover begins"
            ) == true
        )
        XCTAssertTrue(
            snapshot.sourceRefs.contains(
                "Hebcal Jewish Holidays 2026 (Diaspora)"
            )
        )
        XCTAssertNotNil(snapshot.localLightPhase)
        XCTAssertNotNil(snapshot.civilDawn)
        XCTAssertNotNil(snapshot.sunrise)
        XCTAssertNotNil(snapshot.sunset)
        XCTAssertNotNil(snapshot.civilDusk)
        XCTAssertNotNil(snapshot.nextLightEvent)
        XCTAssertNotNil(snapshot.nextLightEventAt)

        let dawn = try XCTUnwrap(snapshot.civilDawn)
        let sunrise = try XCTUnwrap(snapshot.sunrise)
        let sunset = try XCTUnwrap(snapshot.sunset)
        let dusk = try XCTUnwrap(snapshot.civilDusk)
        XCTAssertLessThan(dawn, sunrise)
        XCTAssertLessThan(sunrise, sunset)
        XCTAssertLessThan(sunset, dusk)
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
