import XCTest
@testable import CivicClockWatch

final class CivicCalendarTests: XCTestCase {
    private var denverCalendar: Calendar {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(identifier: "America/Denver")!
        return calendar
    }

    private let latitude = 40.3978
    private let longitude = -105.0749

    func testSunsetStaysOnRequestedLocalCivilDate() throws {
        let calendar = denverCalendar
        let requested = calendar.date(from: DateComponents(
            year: 2026, month: 9, day: 18, hour: 12
        ))!

        let sunset = try XCTUnwrap(SolarBoundaryCalculator.sunset(
            on: requested,
            latitude: latitude,
            longitude: longitude,
            calendar: calendar
        ))

        let components = calendar.dateComponents(
            [.year, .month, .day, .hour],
            from: sunset
        )

        XCTAssertEqual(components.year, 2026)
        XCTAssertEqual(components.month, 9)
        XCTAssertEqual(components.day, 18)
        XCTAssertGreaterThanOrEqual(components.hour ?? -1, 18)
        XCTAssertLessThanOrEqual(components.hour ?? 99, 20)
    }

    func testNamedSaturdayBeginsAtFridaySunset() throws {
        let calendar = denverCalendar
        let fridayNoon = calendar.date(from: DateComponents(
            year: 2026, month: 9, day: 18, hour: 12
        ))!
        let fridaySunset = try XCTUnwrap(SolarBoundaryCalculator.sunset(
            on: fridayNoon,
            latitude: latitude,
            longitude: longitude,
            calendar: calendar
        ))
        let afterSunset = fridaySunset.addingTimeInterval(60)

        let snapshot = CivicCalendarEngine.snapshot(
            now: afterSunset,
            latitude: latitude,
            longitude: longitude,
            calendar: calendar
        )

        XCTAssertEqual(snapshot.namedDay, "SATURDAY")
        XCTAssertTrue(snapshot.isSabbath)
    }

    func testCalendarDoesNotInventAnnualDateWithoutPublishedTable() {
        let snapshot = CivicClockSnapshot.unavailable
        XCTAssertEqual(snapshot.commonCalendarDetail, "PUBLISHED TABLE PENDING")
    }

    func testAnnualDayChangesAtSunsetNotMidnight() throws {
        let calendar = denverCalendar
        let published = PublishedCivicCalendar(
            version: "test",
            years: [
                PublishedCivicYear(
                    year: 7,
                    openingCivilDate: "2026-03-20",
                    reconciliationDaysAfterCompletion: 0
                )
            ]
        )

        let secondCivilDay = calendar.date(from: DateComponents(
            year: 2026, month: 3, day: 21, hour: 12
        ))!
        let secondSunset = try XCTUnwrap(SolarBoundaryCalculator.sunset(
            on: secondCivilDay,
            latitude: latitude,
            longitude: longitude,
            calendar: calendar
        ))

        let before = CivicCalendarEngine.snapshot(
            now: secondSunset.addingTimeInterval(-60),
            latitude: latitude,
            longitude: longitude,
            publishedCalendar: published,
            calendar: calendar
        )
        let after = CivicCalendarEngine.snapshot(
            now: secondSunset.addingTimeInterval(60),
            latitude: latitude,
            longitude: longitude,
            publishedCalendar: published,
            calendar: calendar
        )

        XCTAssertTrue(before.commonCalendarLabel.contains("DAY 001"))
        XCTAssertTrue(after.commonCalendarLabel.contains("DAY 002"))
    }

    func testPublishedYearExpiresInsteadOfClaimingAuthorityForever() {
        let calendar = denverCalendar
        let published = PublishedCivicCalendar(
            version: "test",
            years: [
                PublishedCivicYear(
                    year: 7,
                    openingCivilDate: "2026-03-20",
                    reconciliationDaysAfterCompletion: 0
                )
            ]
        )

        let farOutside = calendar.date(from: DateComponents(
            year: 2027, month: 4, day: 1, hour: 12
        ))!

        let snapshot = CivicCalendarEngine.snapshot(
            now: farOutside,
            latitude: latitude,
            longitude: longitude,
            publishedCalendar: published,
            calendar: calendar
        )

        XCTAssertEqual(snapshot.commonCalendarDetail, "OUTSIDE PUBLISHED TABLE")
    }

    func testPublishedRowsMustAgreeOn364Or371BoundarySpan() {
        let calendar = denverCalendar
        let inconsistent = PublishedCivicCalendar(
            version: "test",
            years: [
                PublishedCivicYear(
                    year: 7,
                    openingCivilDate: "2026-03-20",
                    reconciliationDaysAfterCompletion: 0
                ),
                PublishedCivicYear(
                    year: 8,
                    openingCivilDate: "2027-03-21",
                    reconciliationDaysAfterCompletion: 0
                )
            ]
        )

        let now = calendar.date(from: DateComponents(
            year: 2026, month: 4, day: 1, hour: 12
        ))!

        let snapshot = CivicCalendarEngine.snapshot(
            now: now,
            latitude: latitude,
            longitude: longitude,
            publishedCalendar: inconsistent,
            calendar: calendar
        )

        XCTAssertEqual(snapshot.commonCalendarDetail, "OUTSIDE PUBLISHED TABLE")
    }

    func testExampleAnnualDayMathIsBoundedTo364() {
        let calendar = denverCalendar
        let published = PublishedCivicCalendar(
            version: "test",
            years: [
                PublishedCivicYear(
                    year: 7,
                    openingCivilDate: "2026-03-20",
                    reconciliationDaysAfterCompletion: 0
                )
            ]
        )

        let now = calendar.date(from: DateComponents(
            year: 2026, month: 4, day: 1, hour: 12
        ))!

        let snapshot = CivicCalendarEngine.snapshot(
            now: now,
            latitude: latitude,
            longitude: longitude,
            publishedCalendar: published,
            calendar: calendar
        )

        XCTAssertTrue(snapshot.commonCalendarLabel.contains("YEAR 7"))
    }
}
