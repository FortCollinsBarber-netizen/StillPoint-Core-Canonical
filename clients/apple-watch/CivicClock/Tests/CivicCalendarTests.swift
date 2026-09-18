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

    func testSunriseAndSunsetStayOnRequestedLocalCivilDate() throws {
        let calendar = denverCalendar
        let requested = calendar.date(from: DateComponents(
            year: 2026, month: 9, day: 20, hour: 12
        ))!

        let sunrise = try XCTUnwrap(SolarBoundaryCalculator.sunrise(
            on: requested,
            latitude: latitude,
            longitude: longitude,
            calendar: calendar
        ))
        let sunset = try XCTUnwrap(SolarBoundaryCalculator.sunset(
            on: requested,
            latitude: latitude,
            longitude: longitude,
            calendar: calendar
        ))

        XCTAssertTrue(calendar.isDate(sunrise, inSameDayAs: requested))
        XCTAssertTrue(calendar.isDate(sunset, inSameDayAs: requested))
        XCTAssertLessThan(sunrise, sunset)
    }

    func testFridaySunsetOpensSabbathAndStillPoint() throws {
        let calendar = denverCalendar
        let friday = calendar.date(from: DateComponents(
            year: 2026, month: 9, day: 18, hour: 12
        ))!
        let boundary = try XCTUnwrap(SolarBoundaryCalculator.sunset(
            on: friday,
            latitude: latitude,
            longitude: longitude,
            calendar: calendar
        ))

        let snapshot = CivicCalendarEngine.snapshot(
            now: boundary,
            latitude: latitude,
            longitude: longitude,
            calendar: calendar
        )

        XCTAssertEqual(snapshot.namedDay, "SATURDAY")
        XCTAssertTrue(snapshot.isSabbath)
        XCTAssertTrue(snapshot.isStillPoint)
        XCTAssertFalse(snapshot.isLordsDay)
    }

    func testSaturdaySunsetClosesSabbathAndOpensLordsDayWhileStillPointContinues() throws {
        let calendar = denverCalendar
        let saturday = calendar.date(from: DateComponents(
            year: 2026, month: 9, day: 19, hour: 12
        ))!
        let boundary = try XCTUnwrap(SolarBoundaryCalculator.sunset(
            on: saturday,
            latitude: latitude,
            longitude: longitude,
            calendar: calendar
        ))

        let snapshot = CivicCalendarEngine.snapshot(
            now: boundary,
            latitude: latitude,
            longitude: longitude,
            calendar: calendar
        )

        XCTAssertEqual(snapshot.namedDay, "SUNDAY")
        XCTAssertFalse(snapshot.isSabbath)
        XCTAssertTrue(snapshot.isLordsDay)
        XCTAssertTrue(snapshot.isStillPoint)
        XCTAssertEqual(
            snapshot.nextProtectedBoundaryLabel,
            "STILLPOINT RELEASE · SUNDAY SUNRISE"
        )
    }

    func testSundaySunriseReleasesStillPointButLordsDayContinues() throws {
        let calendar = denverCalendar
        let sunday = calendar.date(from: DateComponents(
            year: 2026, month: 9, day: 20, hour: 12
        ))!
        let sunrise = try XCTUnwrap(SolarBoundaryCalculator.sunrise(
            on: sunday,
            latitude: latitude,
            longitude: longitude,
            calendar: calendar
        ))

        let before = CivicCalendarEngine.snapshot(
            now: sunrise.addingTimeInterval(-1),
            latitude: latitude,
            longitude: longitude,
            calendar: calendar
        )
        let at = CivicCalendarEngine.snapshot(
            now: sunrise,
            latitude: latitude,
            longitude: longitude,
            calendar: calendar
        )

        XCTAssertTrue(before.isStillPoint)
        XCTAssertTrue(before.isLordsDay)
        XCTAssertFalse(at.isStillPoint)
        XCTAssertTrue(at.isLordsDay)
        XCTAssertEqual(
            at.nextProtectedBoundaryLabel,
            "LORD'S DAY ENDS · SUNDAY SUNSET"
        )
    }

    func testSundaySunsetEndsLordsDay() throws {
        let calendar = denverCalendar
        let sunday = calendar.date(from: DateComponents(
            year: 2026, month: 9, day: 20, hour: 12
        ))!
        let sunset = try XCTUnwrap(SolarBoundaryCalculator.sunset(
            on: sunday,
            latitude: latitude,
            longitude: longitude,
            calendar: calendar
        ))

        let at = CivicCalendarEngine.snapshot(
            now: sunset,
            latitude: latitude,
            longitude: longitude,
            calendar: calendar
        )

        XCTAssertFalse(at.isSabbath)
        XCTAssertFalse(at.isLordsDay)
        XCTAssertFalse(at.isStillPoint)
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

    func testPublishedRowsMustAgreeOnDeclaredBoundarySpan() {
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
