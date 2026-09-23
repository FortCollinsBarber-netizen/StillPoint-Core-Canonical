import XCTest
@testable import CivicClockWatch

private struct CalendarProjectionVectorDocument: Decodable {
    struct Fixture: Decodable {
        let latitude: Double
        let longitude: Double
        let legalCivilZone: String
    }

    struct Vector: Decodable {
        struct Expected: Decodable {
            struct CommonDate: Decodable {
                let ordinal: Int
                let quarter: Int
                let week: Int
                let dayInWeek: Int
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

    func testSaturdaySunsetOpensLordsDayWhileStillPointContinues() throws {
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

    func testFixedCalendarProjectsWithoutPublicationTable() throws {
        let calendar = denverCalendar
        let day = calendar.date(from: DateComponents(
            year: 2026, month: 9, day: 18, hour: 12
        ))!

        let snapshot = CivicCalendarEngine.snapshot(
            now: day,
            latitude: latitude,
            longitude: longitude,
            publishedCalendar: nil,
            calendar: calendar
        )

        XCTAssertTrue(snapshot.commonCalendarLabel.contains("Y2026"))
        XCTAssertTrue(snapshot.commonCalendarLabel.contains("DAY 260"))
        XCTAssertNotEqual(
            snapshot.commonCalendarDetail,
            "ANNUAL TABLE PENDING"
        )
    }

    func testAnnualDayChangesAtSunsetNotMidnight() throws {
        let calendar = denverCalendar
        let secondCivilDay = calendar.date(from: DateComponents(
            year: 2026, month: 1, day: 2, hour: 12
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
            calendar: calendar
        )
        let after = CivicCalendarEngine.snapshot(
            now: secondSunset.addingTimeInterval(60),
            latitude: latitude,
            longitude: longitude,
            calendar: calendar
        )

        XCTAssertTrue(before.commonCalendarLabel.contains("DAY 001"))
        XCTAssertTrue(after.commonCalendarLabel.contains("DAY 002"))
    }

    func testDecember30RollsDirectlyToNextJanuary1() throws {
        let calendar = denverCalendar
        let rolloverCivilDay = calendar.date(from: DateComponents(
            year: 2026, month: 12, day: 31, hour: 12
        ))!
        let rollover = try XCTUnwrap(SolarBoundaryCalculator.sunset(
            on: rolloverCivilDay,
            latitude: latitude,
            longitude: longitude,
            calendar: calendar
        ))

        let before = CivicCalendarEngine.snapshot(
            now: rollover.addingTimeInterval(-60),
            latitude: latitude,
            longitude: longitude,
            calendar: calendar
        )
        let after = CivicCalendarEngine.snapshot(
            now: rollover.addingTimeInterval(60),
            latitude: latitude,
            longitude: longitude,
            calendar: calendar
        )

        XCTAssertTrue(before.commonCalendarLabel.contains("Y2026"))
        XCTAssertTrue(before.commonCalendarLabel.contains("DEC 30"))
        XCTAssertTrue(before.commonCalendarLabel.contains("DAY 364"))
        XCTAssertTrue(after.commonCalendarLabel.contains("Y2027"))
        XCTAssertTrue(after.commonCalendarLabel.contains("JAN 01"))
        XCTAssertTrue(after.commonCalendarLabel.contains("DAY 001"))
    }

    func testCommonClockRemovesDaylightSavingOffset() throws {
        let parser = ISO8601DateFormatter()
        let now = try XCTUnwrap(
            parser.date(from: "2026-09-18T19:00:00Z")
        )
        let snapshot = CivicCalendarEngine.snapshot(
            now: now,
            latitude: latitude,
            longitude: longitude,
            calendar: denverCalendar
        )

        XCTAssertEqual(snapshot.commonClockLabel, "12:00")
    }

    func testChristmasAndJubileeContextComeFromSharedLaw() throws {
        let calendar = denverCalendar
        let christmasCivilDay = calendar.date(from: DateComponents(
            year: 2026, month: 12, day: 25, hour: 20
        ))!
        let christmasSunset = try XCTUnwrap(SolarBoundaryCalculator.sunset(
            on: christmasCivilDay,
            latitude: latitude,
            longitude: longitude,
            calendar: calendar
        ))
        let christmas = CivicCalendarEngine.snapshot(
            now: christmasSunset.addingTimeInterval(60),
            latitude: latitude,
            longitude: longitude,
            calendar: calendar
        )
        XCTAssertTrue(
            christmas.observanceLabel.contains("Christmas Day")
        )
        XCTAssertEqual(christmas.jubileeLabel, "JUBILEE Y1/50")

        let year50CivilOpening = calendar.date(from: DateComponents(
            year: 2074, month: 11, day: 1, hour: 20
        ))!
        let year50Sunset = try XCTUnwrap(SolarBoundaryCalculator.sunset(
            on: year50CivilOpening,
            latitude: latitude,
            longitude: longitude,
            calendar: calendar
        ))
        let year50 = CivicCalendarEngine.snapshot(
            now: year50Sunset.addingTimeInterval(60),
            latitude: latitude,
            longitude: longitude,
            calendar: calendar
        )
        XCTAssertEqual(year50.jubileeLabel, "JUBILEE YEAR 50")
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

        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = try XCTUnwrap(TimeZone(
            identifier: document.fixture.legalCivilZone
        ))
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
                publishedCalendar: nil,
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
            } else {
                XCTAssertEqual(
                    expected.state,
                    "OUTSIDE_RANGE",
                    vector.id
                )
            }
        }
    }
}
