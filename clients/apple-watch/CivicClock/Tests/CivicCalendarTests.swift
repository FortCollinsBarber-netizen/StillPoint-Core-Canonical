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

    private var resourceRoot: URL {
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("Resources")
    }

    private func spec() throws -> CalendarCoreSpec {
        try XCTUnwrap(
            CalendarCoreSpecLoader.load(
                url: resourceRoot.appendingPathComponent(
                    "calendar_core_spec.json"
                )
            )
        )
    }

    private func publication(
        _ spec: CalendarCoreSpec
    ) throws -> PublishedCivicCalendar {
        try XCTUnwrap(
            PublishedCalendarLoader.load(
                url: resourceRoot.appendingPathComponent(
                    "published_calendar.json"
                ),
                calendarCoreSpec: spec
            )
        )
    }

    private func population(
        _ spec: CalendarCoreSpec
    ) throws -> CalendarPopulation {
        try XCTUnwrap(
            CalendarPopulationLoader.load(
                url: resourceRoot.appendingPathComponent(
                    "calendar_population_v1.json"
                ),
                calendarCoreSpec: spec
            )
        )
    }

    private func snapshot(
        _ now: Date
    ) throws -> CivicClockSnapshot {
        let core = try spec()
        return CivicCalendarEngine.snapshot(
            now: now,
            latitude: latitude,
            longitude: longitude,
            publishedCalendar: try publication(core),
            population: try population(core),
            calendarCoreSpec: core,
            calendar: denverCalendar
        )
    }

    func testFridaySunsetOpensSabbathAndStillPoint() throws {
        let calendar = denverCalendar
        let friday = calendar.date(from: DateComponents(
            year: 2026, month: 9, day: 18, hour: 12
        ))!
        let boundary = try XCTUnwrap(
            SolarBoundaryCalculator.sunset(
                on: friday,
                latitude: latitude,
                longitude: longitude,
                calendar: calendar,
                spec: try spec()
            )
        )

        let state = try snapshot(
            boundary.addingTimeInterval(1)
        )
        XCTAssertEqual(state.namedDay, "SATURDAY")
        XCTAssertTrue(state.isSabbath)
        XCTAssertTrue(state.isStillPoint)
        XCTAssertFalse(state.isLordsDay)
    }

    func testSaturdaySunsetOpensLordsDayAndStillPointContinues() throws {
        let calendar = denverCalendar
        let saturday = calendar.date(from: DateComponents(
            year: 2026, month: 9, day: 19, hour: 12
        ))!
        let boundary = try XCTUnwrap(
            SolarBoundaryCalculator.sunset(
                on: saturday,
                latitude: latitude,
                longitude: longitude,
                calendar: calendar,
                spec: try spec()
            )
        )

        let state = try snapshot(
            boundary.addingTimeInterval(1)
        )
        XCTAssertEqual(state.namedDay, "SUNDAY")
        XCTAssertFalse(state.isSabbath)
        XCTAssertTrue(state.isLordsDay)
        XCTAssertTrue(state.isStillPoint)
    }

    func testCommonClockUsesPermanentStandardOffsetDuringDST() throws {
        let parser = ISO8601DateFormatter()
        let now = try XCTUnwrap(
            parser.date(from: "2026-09-18T19:00:00Z")
        )
        let state = try snapshot(now)
        XCTAssertEqual(state.commonClockLabel, "12:00")
    }

    func testFixedMapProjectsRealCommonAddressFromEnactedPublication() throws {
        let parser = ISO8601DateFormatter()
        let now = try XCTUnwrap(
            parser.date(from: "2026-09-18T19:28:57Z")
        )
        let state = try snapshot(now)

        XCTAssertTrue(state.commonCalendarLabel.contains("Y2026"))
        XCTAssertTrue(state.commonCalendarLabel.contains("SEP 17"))
        XCTAssertTrue(state.commonCalendarLabel.contains("DAY 260"))
        XCTAssertTrue(state.commonCalendarDetail.contains("THURSDAY"))
        XCTAssertTrue(state.commonCalendarDetail.contains("W38 D1"))
        XCTAssertTrue(state.commonCalendarDetail.contains("S3.78"))
        XCTAssertTrue(state.commonCalendarDetail.contains("G1 · P9"))
        XCTAssertEqual(state.jubileeLabel, "JUBILEE Y1/50")
    }

    func testDecember30RollsDirectlyToNextJanuary1AtNextSunset() throws {
        let calendar = denverCalendar
        let dec30 = calendar.date(from: DateComponents(
            year: 2026, month: 12, day: 30, hour: 12
        ))!
        let dec31 = calendar.date(from: DateComponents(
            year: 2026, month: 12, day: 31, hour: 12
        ))!
        let day364Opening = try XCTUnwrap(
            SolarBoundaryCalculator.sunset(
                on: dec30,
                latitude: latitude,
                longitude: longitude,
                calendar: calendar,
                spec: try spec()
            )
        )
        let nextOpening = try XCTUnwrap(
            SolarBoundaryCalculator.sunset(
                on: dec31,
                latitude: latitude,
                longitude: longitude,
                calendar: calendar,
                spec: try spec()
            )
        )

        let last = try snapshot(
            day364Opening.addingTimeInterval(1)
        )
        let next = try snapshot(
            nextOpening.addingTimeInterval(1)
        )

        XCTAssertTrue(last.commonCalendarLabel.contains("Y2026"))
        XCTAssertTrue(last.commonCalendarLabel.contains("DEC 30"))
        XCTAssertTrue(last.commonCalendarLabel.contains("DAY 364"))
        XCTAssertTrue(next.commonCalendarLabel.contains("Y2027"))
        XCTAssertTrue(next.commonCalendarLabel.contains("JAN 01"))
        XCTAssertTrue(next.commonCalendarLabel.contains("DAY 001"))
        XCTAssertFalse(
            next.commonCalendarLabel.contains("RECONCILIATION")
        )
    }

    func testChristmasObservanceIsPopulatedOnFixedAddress() throws {
        let calendar = denverCalendar
        let day = calendar.date(from: DateComponents(
            year: 2026, month: 12, day: 25, hour: 12
        ))!
        let opening = try XCTUnwrap(
            SolarBoundaryCalculator.sunset(
                on: day,
                latitude: latitude,
                longitude: longitude,
                calendar: calendar,
                spec: try spec()
            )
        )
        let state = try snapshot(
            opening.addingTimeInterval(1)
        )

        XCTAssertTrue(
            state.observanceLabel.contains("Christmas Day")
        )
        XCTAssertTrue(
            state.commonCalendarDetail.contains("FRIDAY")
        )
    }

    func testAtonementCarriesSourceProvenance() throws {
        let calendar = denverCalendar
        let civil = calendar.date(from: DateComponents(
            year: 2026, month: 7, day: 10, hour: 12
        ))!
        let opening = try XCTUnwrap(
            SolarBoundaryCalculator.sunset(
                on: civil,
                latitude: latitude,
                longitude: longitude,
                calendar: calendar,
                spec: try spec()
            )
        )
        let state = try snapshot(
            opening.addingTimeInterval(1)
        )

        XCTAssertTrue(
            state.observanceLabel.contains("Day of Atonement")
        )
        XCTAssertTrue(
            state.sourceRefs.contains("Leviticus 23:26-32")
        )
        XCTAssertTrue(
            state.sourceRefs.contains("1 Enoch 72-82")
        )
    }

    func testYear50AndReleaseSurfaceWithoutChangingGrid() throws {
        let calendar = denverCalendar
        let year50 = calendar.date(from: DateComponents(
            year: 2074, month: 11, day: 1, hour: 12
        ))!
        let opening = try XCTUnwrap(
            SolarBoundaryCalculator.sunset(
                on: year50,
                latitude: latitude,
                longitude: longitude,
                calendar: calendar,
                spec: try spec()
            )
        )
        let state = try snapshot(
            opening.addingTimeInterval(1)
        )

        XCTAssertTrue(state.commonCalendarLabel.contains("Y2075"))
        XCTAssertTrue(state.commonCalendarLabel.contains("JAN 01"))
        XCTAssertEqual(state.jubileeLabel, "JUBILEE YEAR 50")
    }
}
