import XCTest
@testable import CivicClockWatch

final class PublishedCalendarLoaderTests: XCTestCase {
    private var resourceRoot: URL {
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("Resources")
    }

    private var spec: CalendarCoreSpec {
        get throws {
            try XCTUnwrap(
                CalendarCoreSpecLoader.load(
                    url: resourceRoot.appendingPathComponent(
                        "calendar_core_spec.json"
                    )
                )
            )
        }
    }

    func testBundledEnactedPublicationLoadsFiftyExactYears() throws {
        let publication = try XCTUnwrap(
            PublishedCalendarLoader.load(
                url: resourceRoot.appendingPathComponent(
                    "published_calendar.json"
                ),
                calendarCoreSpec: try spec
            )
        )

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
            publication.validationReceipt?.authorityStatus,
            "enacted"
        )
    }

    func testRawPublicationTamperingFailsDigestValidation() throws {
        let source = resourceRoot.appendingPathComponent(
            "published_calendar.json"
        )
        let original = try String(
            contentsOf: source,
            encoding: .utf8
        )
        let tampered = original.replacingOccurrences(
            of: "2074-11-01",
            with: "2074-11-02"
        )
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
            .appendingPathExtension("json")
        try tampered.write(
            to: url,
            atomically: true,
            encoding: .utf8
        )

        XCTAssertNil(
            PublishedCalendarLoader.load(
                url: url,
                calendarCoreSpec: try spec
            )
        )
    }

    func testCalendarPopulationArtifactLoadsWithoutGridAuthority() throws {
        let population = try XCTUnwrap(
            CalendarPopulationLoader.load(
                url: resourceRoot.appendingPathComponent(
                    "calendar_population_v1.json"
                ),
                calendarCoreSpec: try spec
            )
        )

        XCTAssertFalse(population.jurisdiction.gridAuthority)
        XCTAssertFalse(population.jurisdiction.mayInsertDays)
        XCTAssertEqual(
            population.seasonalArchitecture.phaseLengths.reduce(0, +),
            364
        )
        XCTAssertEqual(
            Set(population.seasonalArchitecture.gateSequence),
            Set(1...6)
        )
        XCTAssertTrue(
            population.observances.contains {
                $0.id == "atonement"
            }
        )
        XCTAssertTrue(
            population.observances.contains {
                $0.id == "christmas"
            }
        )
    }
}
