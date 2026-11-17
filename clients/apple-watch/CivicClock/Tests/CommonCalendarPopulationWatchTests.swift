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
            "49847804cc86fc2858aed019deaa0f702fd03bc6acc3b01f7036def7e51db2c8"
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
        XCTAssertTrue(state.jubileeLabel.hasPrefix("JUBILEE COUNT NOT STARTED"))
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
            try XCTUnwrap(parser.date(from: "2026-10-02 12:00"))
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

    func testLastPublishedYearIsYear49WithoutChangingGrid() throws {
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
        XCTAssertTrue(state.jubileeLabel.hasPrefix("JUBILEE C1 Y49/49 · SABBATICAL"))
    }

    func testExplicitSacredProfileKeepsSourceAndCommonCoordinatesDistinct() throws {
        let spec = try coreSpec()
        let population = try population(spec: spec)
        let profile = population.sacredYearProfile
        XCTAssertEqual(profile.anchorCommonMonth, 3)
        XCTAssertEqual(profile.anchorCommonDay, 25)
        XCTAssertEqual(profile.anchorWeekday, "Wednesday")
        XCTAssertFalse(profile.annualSolarReset)
        XCTAssertFalse(profile.gridAuthority)
        let atonement = try XCTUnwrap(population.observances.first { $0.id == "atonement" })
        XCTAssertEqual(atonement.sourceMonth, 7)
        XCTAssertEqual(atonement.sourceDay, 10)
        XCTAssertEqual(atonement.month, 10)
        XCTAssertEqual(atonement.day, 2)
        XCTAssertEqual(atonement.profileId, profile.id)
    }

    func testFiftiethProclamationOverlapsNextCycleFirstYearWithoutExtendingPublication() throws {
        let spec = try coreSpec()
        let population = try population(spec: spec)
        let policy = population.longCyclePolicy
        XCTAssertNil(CivicCalendarEngine.longCyclePosition(commonYear: 2026, policy: policy))
        let year49 = try XCTUnwrap(CivicCalendarEngine.longCyclePosition(commonYear: 2075, policy: policy))
        XCTAssertEqual(year49.year, 49)
        XCTAssertTrue(year49.isSabbatical)
        XCTAssertFalse(year49.isJubilee)
        let release = try XCTUnwrap(CivicCalendarEngine.longCyclePosition(commonYear: 2076, policy: policy))
        XCTAssertEqual(release.cycle, 2)
        XCTAssertEqual(release.year, 1)
        XCTAssertEqual(release.proclamationOrdinalYear, 50)
        XCTAssertTrue(release.isJubilee)
        let next = try XCTUnwrap(CivicCalendarEngine.longCyclePosition(commonYear: 2125, policy: policy))
        XCTAssertEqual(next.cycle, 3)
        XCTAssertTrue(next.isJubilee)
        XCTAssertFalse(try publication(spec: spec).years.contains { $0.year == 2076 })
    }

    func testFirstfruitsAndWeeksUseSourcePatternAndInclusiveFiftiethDay() throws {
        let spec = try coreSpec()
        let population = try population(spec: spec)
        let first = try XCTUnwrap(population.observances.first { $0.id == "firstfruits" })
        let weeks = try XCTUnwrap(population.observances.first { $0.id == "weeks" })
        XCTAssertEqual(first.sourceMonth, 1)
        XCTAssertEqual(first.sourceDay, 26)
        XCTAssertEqual(first.month, 4)
        XCTAssertEqual(first.day, 19)
        XCTAssertEqual(weeks.sourceMonth, 3)
        XCTAssertEqual(weeks.sourceDay, 15)
        let lengths = spec.ordinaryCalendar.monthLengths
        let firstOrdinal = lengths.prefix(first.month - 1).reduce(0, +) + first.day
        let weeksOrdinal = lengths.prefix(weeks.month - 1).reduce(0, +) + weeks.day
        XCTAssertEqual(weeksOrdinal - firstOrdinal + 1, 50)
    }

    func testLoaderRejectsAnAnchorWhoseDeclaredWeekdayIsFalse() throws {
        let spec = try coreSpec()
        let data = try Data(contentsOf: resources.appendingPathComponent("calendar_population_v1.json"))
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        var profile = try XCTUnwrap(object["sacredYearProfile"] as? [String: Any])
        profile["anchorCommonDay"] = 24
        object["sacredYearProfile"] = profile
        let temporary = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString + ".json")
        defer { try? FileManager.default.removeItem(at: temporary) }
        try JSONSerialization.data(withJSONObject: object).write(to: temporary)
        XCTAssertNil(CalendarPopulationLoader.load(url: temporary, calendarCoreSpec: spec))
    }
    func testAuthorSelectedWorkingRuleHasVisibleProvenanceAndNoCivilAuthority() throws {
        let loaded = try population(spec: coreSpec())
        XCTAssertEqual(loaded.sacredYearProfile.selectionStatus, "author-selected-working-rule-not-civil-enactment")
        XCTAssertEqual(loaded.longCyclePolicy.selectionStatus, "author-selected-working-rule-not-civil-enactment")
        XCTAssertEqual(loaded.sacredYearProfile.selectedBy, "Robert Emmanuel LaDay")
        XCTAssertEqual(loaded.longCyclePolicy.selectedBy, "Robert Emmanuel LaDay")
        XCTAssertEqual(loaded.sacredYearProfile.selectedOn, "2026-11-17")
        XCTAssertEqual(loaded.longCyclePolicy.selectedOn, "2026-11-17")
        XCTAssertEqual(loaded.sacredYearProfile.anchorCommonMonth, 3)
        XCTAssertEqual(loaded.sacredYearProfile.anchorCommonDay, 25)
        XCTAssertEqual(loaded.longCyclePolicy.epochCommonYear, 2027)
        XCTAssertTrue(loaded.longCyclePolicy.year50OverlapsNextYear1)
        XCTAssertFalse(loaded.sacredYearProfile.gridAuthority)
        XCTAssertFalse(loaded.longCyclePolicy.gridAuthority)
    }

}
