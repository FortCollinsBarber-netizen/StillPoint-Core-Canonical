import XCTest
@testable import CivicClockWatch

final class CivicCalendarTests: XCTestCase {
    func testNamedSaturdayBeginsAtFridaySunset() throws {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(identifier: "America/Denver")!

        // Loveland-area coordinate is used only as a deterministic test point.
        let latitude = 40.3978
        let longitude = -105.0749

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

    func testExampleAnnualDayMathIsBoundedTo364() throws {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(identifier: "America/Denver")!

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
            latitude: 40.3978,
            longitude: -105.0749,
            publishedCalendar: published,
            calendar: calendar
        )

        XCTAssertTrue(snapshot.commonCalendarLabel.contains("YEAR 7"))
    }
}
