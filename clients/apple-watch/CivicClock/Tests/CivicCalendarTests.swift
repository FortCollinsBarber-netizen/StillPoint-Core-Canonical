import XCTest
@testable import CivicClockWatch

private struct CalendarProjectionVectorDocument: Decodable {
    struct Fixture: Decodable {
        let latitude: Double
        let longitude: Double
        let legalCivilZone: String
        let commonYear: Int
        let openingCivilDate: String
        let day001Weekday: String
    }

    struct Vector: Decodable {
        struct Expected: Decodable {
            struct CommonDate: Decodable {
                let year: Int
                let ordinal: Int
                let quarter: Int
                let week: Int
                let dayInWeek: Int
                let weekday: String
            }

            let commonDate: CommonDate?
            let namedDay: String
            let sabbath: Bool
            let lordsDay: Bool
            let stillPoint: Bool
            let state: String
            let nextProtectedBoundaryLabel: String?
        }

        let id: String
        let instantUTC: String
        let expected: Expected
    }

    let authorityStatus: String
    let fixture: Fixture
    let vectors: [Vector]
}

final class CivicCalendarTests: XCTestCase {
    private var denverCalendar: Calendar {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(identifier: "America/Denver")!
        return calendar
    }

    private let latitude = 40.3978
    private let longitude = -105.0749


    private func fiftyYearFixture(
        startYear: Int = 7,
        openingCivilDate: String = "2026-03-20",
        overrideSecondOpening: String? = nil
    ) -> PublishedCivicCalendar {
        var calendar = Calendar(identifier: .gregorian)
        calendar.locale = Locale(identifier: "en_US_POSIX")
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!

        let formatter = DateFormatter()
        formatter.calendar = calendar
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = calendar.timeZone
        formatter.dateFormat = "yyyy-MM-dd"
        formatter.isLenient = false

        let first = formatter.date(from: openingCivilDate)!
        let years = (0..<50).map { index -> PublishedCivicYear in
            let opening: String
            if index == 1, let overrideSecondOpening {
                opening = overrideSecondOpening
            } else {
                let date = calendar.date(
                    byAdding: .day,
                    value: 364 * index,
                    to: first
                )!
                opening = formatter.string(from: date)
            }
            return PublishedCivicYear(
                year: startYear + index,
                openingCivilDate: opening
            )
        }
        return .conformanceFixture(years: years)
    }

    func testV2SpecFreezesImmutableCalendarIdentity() throws {
        let spec = try XCTUnwrap(CalendarCoreSpecLoader.load())
        XCTAssertEqual(spec.version, "stillpoint-calendar-core-spec-v2")
        XCTAssertEqual(spec.ordinaryCalendar.baseYearDays, 364)
        XCTAssertEqual(spec.ordinaryCalendar.weeksPerYear, 52)
        XCTAssertEqual(spec.ordinaryCalendar.day001Weekday, "Thursday")
        XCTAssertEqual(spec.ordinaryCalendar.yearClosing.month, 12)
        XCTAssertEqual(spec.ordinaryCalendar.yearClosing.day, 30)
        XCTAssertFalse(spec.ordinaryCalendar.hasDecember31)
        XCTAssertFalse(spec.ordinaryCalendar.hasFebruary29)
        XCTAssertEqual(spec.annualTransition.interannualDays, 0)
        XCTAssertFalse(spec.annualTransition.reconciliationAllowed)
    }

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
        XCTAssertEqual(snapshot.commonCalendarDetail, "PUBLICATION UNAVAILABLE")
    }

    func testCommonCivilDateChangesAtStandardMidnightWhileSacredDayChangesAtSunset() throws {
        let calendar = denverCalendar
        let published = fiftyYearFixture()

        var standard = Calendar(identifier: .gregorian)
        standard.timeZone = try XCTUnwrap(TimeZone(secondsFromGMT: -7 * 3600))

        let dayOneNoon = try XCTUnwrap(standard.date(from: DateComponents(
            year: 2026, month: 3, day: 20, hour: 12
        )))
        let sunset = try XCTUnwrap(SolarBoundaryCalculator.sunset(
            on: dayOneNoon,
            latitude: latitude,
            longitude: longitude,
            calendar: standard
        ))

        let beforeSunset = CivicCalendarEngine.snapshot(
            now: sunset.addingTimeInterval(-60),
            latitude: latitude,
            longitude: longitude,
            publishedCalendar: published,
            calendar: calendar
        )
        let afterSunset = CivicCalendarEngine.snapshot(
            now: sunset.addingTimeInterval(60),
            latitude: latitude,
            longitude: longitude,
            publishedCalendar: published,
            calendar: calendar
        )

        XCTAssertTrue(beforeSunset.commonCalendarLabel.contains("DAY 001"))
        XCTAssertTrue(afterSunset.commonCalendarLabel.contains("DAY 001"))
        XCTAssertEqual(beforeSunset.namedDay, "THURSDAY")
        XCTAssertEqual(afterSunset.namedDay, "FRIDAY")

        let beforeMidnight = try XCTUnwrap(standard.date(from: DateComponents(
            year: 2026, month: 3, day: 20, hour: 23, minute: 59
        )))
        let afterMidnight = try XCTUnwrap(standard.date(from: DateComponents(
            year: 2026, month: 3, day: 21, hour: 0, minute: 1
        )))

        let before = CivicCalendarEngine.snapshot(
            now: beforeMidnight,
            latitude: latitude,
            longitude: longitude,
            publishedCalendar: published,
            calendar: calendar
        )
        let after = CivicCalendarEngine.snapshot(
            now: afterMidnight,
            latitude: latitude,
            longitude: longitude,
            publishedCalendar: published,
            calendar: calendar
        )

        XCTAssertTrue(before.commonCalendarLabel.contains("DAY 001"))
        XCTAssertTrue(after.commonCalendarLabel.contains("DAY 002"))
        XCTAssertTrue(after.commonCalendarDetail.contains("FRIDAY"))
        XCTAssertEqual(after.namedDay, "FRIDAY")
    }

    func testPublishedYearExpiresInsteadOfClaimingAuthorityForever() {
        let calendar = denverCalendar
        let published = fiftyYearFixture()

        let farOutside = calendar.date(from: DateComponents(
            year: 2080, month: 4, day: 1, hour: 12
        ))!

        let snapshot = CivicCalendarEngine.snapshot(
            now: farOutside,
            latitude: latitude,
            longitude: longitude,
            publishedCalendar: published,
            calendar: calendar
        )

        XCTAssertEqual(
            snapshot.commonCalendarDetail,
            "OUTSIDE PUBLISHED 50-YEAR MAP"
        )
    }

    func testPublishedRowsMustBeExactly364DaysApart() {
        let calendar = denverCalendar
        let inconsistent = fiftyYearFixture(
            overrideSecondOpening: "2027-03-21"
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

        XCTAssertEqual(
            snapshot.commonCalendarDetail,
            "OUTSIDE PUBLISHED 50-YEAR MAP"
        )
    }

    func testExampleAnnualDayMathIsBoundedTo364() {
        let calendar = denverCalendar
        let published = fiftyYearFixture()

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

        XCTAssertTrue(snapshot.commonCalendarLabel.contains("Y7"))
    }

    func testNativeProjectionConsumesGeneratedCalendarCoreSpecAndVectors() throws {
        let resourceRoot = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("Resources")

        let spec = try XCTUnwrap(CalendarCoreSpecLoader.load(
            url: resourceRoot.appendingPathComponent("calendar_core_spec.json")
        ))
        let vectorData = try Data(contentsOf:
            resourceRoot.appendingPathComponent("calendar_projection_vectors.json")
        )
        let document = try JSONDecoder().decode(
            CalendarProjectionVectorDocument.self,
            from: vectorData
        )

        XCTAssertEqual(document.authorityStatus, "conformance-only")
        XCTAssertEqual(document.fixture.day001Weekday, "Thursday")

        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = try XCTUnwrap(TimeZone(
            identifier: document.fixture.legalCivilZone
        ))

        let published = fiftyYearFixture(
            startYear: document.fixture.commonYear,
            openingCivilDate: document.fixture.openingCivilDate
        )

        let parser = ISO8601DateFormatter()

        for vector in document.vectors {
            let now = try XCTUnwrap(
                parser.date(from: vector.instantUTC),
                "Could not parse \(vector.id)"
            )
            let snapshot = CivicCalendarEngine.snapshot(
                now: now,
                latitude: document.fixture.latitude,
                longitude: document.fixture.longitude,
                publishedCalendar: published,
                calendarCoreSpec: spec,
                calendar: calendar
            )
            let expected = vector.expected

            XCTAssertEqual(
                snapshot.namedDay,
                expected.namedDay.uppercased(),
                vector.id
            )
            XCTAssertEqual(snapshot.isSabbath, expected.sabbath, vector.id)
            XCTAssertEqual(snapshot.isLordsDay, expected.lordsDay, vector.id)
            XCTAssertEqual(snapshot.isStillPoint, expected.stillPoint, vector.id)
            XCTAssertEqual(
                snapshot.nextProtectedBoundaryLabel,
                expected.nextProtectedBoundaryLabel,
                vector.id
            )

            if let common = expected.commonDate {
                XCTAssertTrue(
                    snapshot.commonCalendarLabel.contains(
                        "Y\(common.year)"
                    ),
                    vector.id
                )
                XCTAssertTrue(
                    snapshot.commonCalendarLabel.contains(
                        "DAY \(String(format: "%03d", common.ordinal))"
                    ),
                    vector.id
                )
                XCTAssertTrue(
                    snapshot.commonCalendarDetail.contains(
                        "S\(common.quarter)"
                    ),
                    vector.id
                )
                XCTAssertTrue(
                    snapshot.commonCalendarDetail.contains(
                        "W\(String(format: "%02d", common.week))"
                    ),
                    vector.id
                )
                XCTAssertTrue(
                    snapshot.commonCalendarDetail.contains(
                        "D\(common.dayInWeek)"
                    ),
                    vector.id
                )
                let weekdays = [
                    "Sunday", "Monday", "Tuesday", "Wednesday",
                    "Thursday", "Friday", "Saturday"
                ]
                let thursdayIndex = 4
                let expectedWeekday = weekdays[
                    (thursdayIndex + common.ordinal - 1) % 7
                ]
                XCTAssertEqual(
                    common.weekday,
                    expectedWeekday,
                    vector.id
                )
            }
        }
    }
}
