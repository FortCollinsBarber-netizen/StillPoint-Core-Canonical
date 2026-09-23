import XCTest
@testable import CivicClockWatch

final class CommonCalendarPopulationWatchTests: XCTestCase {
    private var calendar: Calendar {
        var value = Calendar(identifier: .gregorian)
        value.timeZone = TimeZone(identifier: "America/Denver")!
        return value
    }

    private var resources: URL {
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("Resources")
    }

    private func coreSpec() throws -> CalendarCoreSpec {
        try XCTUnwrap(
            CalendarCoreSpecLoader.load(
                url: resources.appendingPathComponent(
                    "calendar_core_spec.json"
                )
            )
        )
    }

    private func publication(
        spec: CalendarCoreSpec
    ) throws -> PublishedCivicCalendar {
        try XCTUnwrap(
            PublishedCalendarLoader.load(
                url: resources.appendingPathComponent(
                    "published_calendar.json"
                ),
                policy: .enactedStillPoint,
                calendarCoreSpec: spec
            )
        )
    }

    private func population(
        spec: CalendarCoreSpec
    ) throws -> CalendarPopulation {
        try XCTUnwrap(
            CalendarPopulationLoader.load(
                url: resources.appendingPathComponent(
                    "calendar_population_v1.json"
                ),
                calendarCoreSpec: spec
            )
        )
    }

    private func snapshot(
        _ instant: Date
    ) throws -> CivicClockSnapshot {
        let spec = try coreSpec()
        return CivicCalendarEngine.snapshot(
            now: instant,
            latitude: 40.3978,
            longitude: -105.0749,
            publishedCalendar: try publication(spec: spec),
            population: try population(spec: spec),
            calendarCoreSpec: spec,
            calendar: calendar
        )
    }

    func testExactEnactedPublicationIsFiftyYears() throws {
        let spec = try coreSpec()
        let publication = try publication(spec: spec)

        XCTAssertTrue(publication.isValidatedForProjection)
        XCTAssertEqual(publication.years.count, 50)
        XCTAssertEqual(publication.years.first?.year, 2026)
        XCTAssertEqual(
            publication.years.first?.openingCivilDate,
            "2026-01-01"
        )
        XCTAssertEqual(publication.years.last?.year, 2075)
        XCTAssertEqual(
            publication.years.last?.openingCivilDate,
            "2074-11-01"
        )
        XCTAssertEqual(
            publication.validationReceipt?.authorityID,
            "ROBERT_EMMANUEL_LADAY"
        )
        XCTAssertEqual(
            publication.validationReceipt?.publicationDigest,
            "e06b9181fdf4122e71a6645911dcf1024b39e9e20aef7f0a2c1eca086267294a"
        )
    }

    func testCommonClockUsesPermanentStandardTimeDuringDST() throws {
        let instant = try XCTUnwrap(
            ISO8601DateFormatter().date(
                from: "2026-09-18T19:00:00Z"
            )
        )
        let state = try snapshot(instant)
        XCTAssertEqual(state.commonClockLabel, "12:00")
    }

    func testPopulatedAddressContainsFullFixedGridContext() throws {
        let instant = try XCTUnwrap(
            ISO8601DateFormatter().date(
                from: "2026-09-18T19:28:57Z"
            )
        )
        let state = try snapshot(instant)

        XCTAssertTrue(state.commonCalendarLabel.contains("Y2026"))
        XCTAssertTrue(state.commonCalendarLabel.contains("SEP 18"))
        XCTAssertTrue(state.commonCalendarLabel.contains("DAY 261"))
        XCTAssertTrue(state.commonCalendarDetail.contains("FRIDAY"))
        XCTAssertTrue(state.commonCalendarDetail.contains("W38 D2"))
        XCTAssertTrue(state.commonCalendarDetail.contains("S3.79"))
        XCTAssertTrue(state.commonCalendarDetail.contains("G1 · P9"))
        XCTAssertEqual(state.jubileeLabel, "JUBILEE Y1/50")
    }

    func testDecember30TransitionsDirectlyToNextJanuary1() throws {
        let parser = DateFormatter()
        parser.calendar = calendar
        parser.locale = Locale(identifier: "en_US_POSIX")
        parser.timeZone = calendar.timeZone
        parser.dateFormat = "yyyy-MM-dd HH:mm"

        let last = try snapshot(
            try XCTUnwrap(parser.date(from: "2026-12-30 20:00"))
        )
        let next = try snapshot(
            try XCTUnwrap(parser.date(from: "2026-12-31 20:00"))
        )

        XCTAssertTrue(last.commonCalendarLabel.contains("Y2026"))
        XCTAssertTrue(last.commonCalendarLabel.contains("DEC 30"))
        XCTAssertTrue(last.commonCalendarLabel.contains("DAY 364"))
        XCTAssertTrue(next.commonCalendarLabel.contains("Y2027"))
        XCTAssertTrue(next.commonCalendarLabel.contains("JAN 01"))
        XCTAssertTrue(next.commonCalendarLabel.contains("DAY 001"))
    }

    func testChristmasAndAtonementComeFromPopulationArtifact() throws {
        let parser = DateFormatter()
        parser.calendar = calendar
        parser.locale = Locale(identifier: "en_US_POSIX")
        parser.timeZone = calendar.timeZone
        parser.dateFormat = "yyyy-MM-dd HH:mm"

        let christmas = try snapshot(
            try XCTUnwrap(parser.date(from: "2026-12-25 20:00"))
        )
        XCTAssertTrue(
            christmas.observanceLabel.contains("Christmas Day")
        )
        XCTAssertTrue(
            christmas.commonCalendarDetail.contains("FRIDAY")
        )

        let atonement = try snapshot(
            try XCTUnwrap(parser.date(from: "2026-07-10 22:00"))
        )
        XCTAssertTrue(
            atonement.observanceLabel.contains("Day of Atonement")
        )
        XCTAssertTrue(
            atonement.sourceRefs.contains("Leviticus 23:26-32")
        )
        XCTAssertTrue(
            atonement.sourceRefs.contains("1 Enoch 72-82")
        )
    }

    func testYearFiftySurfacesAsJubileeWithoutChangingGrid() throws {
        let parser = DateFormatter()
        parser.calendar = calendar
        parser.locale = Locale(identifier: "en_US_POSIX")
        parser.timeZone = calendar.timeZone
        parser.dateFormat = "yyyy-MM-dd HH:mm"

        let state = try snapshot(
            try XCTUnwrap(parser.date(from: "2074-11-01 20:00"))
        )
        XCTAssertTrue(state.commonCalendarLabel.contains("Y2075"))
        XCTAssertTrue(state.commonCalendarLabel.contains("JAN 01"))
        XCTAssertEqual(state.jubileeLabel, "JUBILEE YEAR 50")
    }
}
