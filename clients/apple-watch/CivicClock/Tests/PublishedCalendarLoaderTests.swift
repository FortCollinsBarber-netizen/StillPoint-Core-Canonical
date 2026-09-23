import CryptoKit
import XCTest
@testable import CivicClockWatch

final class PublishedCalendarLoaderTests: XCTestCase {
    private var spec: CalendarCoreSpec {
        get throws {
            let resourceRoot = URL(fileURLWithPath: #filePath)
                .deletingLastPathComponent()
                .deletingLastPathComponent()
                .appendingPathComponent("Resources")
            return try XCTUnwrap(
                CalendarCoreSpecLoader.load(
                    url: resourceRoot.appendingPathComponent(
                        "calendar_core_spec.json"
                    )
                )
            )
        }
    }

    private let publicationDigest =
        "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"

    private func fixtureData(
        secondOpening: String = "2026-12-31"
    ) -> Data {
        Data(
            """
            {
              "publicationVersion": "stillpoint-calendar-publication-v2",
              "calendarCoreSpecVersion": "stillpoint-calendar-core-spec-v2",
              "authority": {
                "id": "TEST_PILOT_AUTHORITY",
                "status": "pilot"
              },
              "years": [
                {
                  "year": 7,
                  "openingCivilDate": "2026-01-01"
                },
                {
                  "year": 8,
                  "openingCivilDate": "\(secondOpening)"
                }
              ],
              "publicationDigest": "\(publicationDigest)"
            }
            """.utf8
        )
    }

    private func rawSHA256(_ data: Data) -> String {
        SHA256.hash(data: data)
            .map { String(format: "%02x", $0) }
            .joined()
    }

    private func writeFixture(_ data: Data) throws -> URL {
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
            .appendingPathExtension("json")
        try data.write(to: url)
        return url
    }

    private func policy(for data: Data) -> PublishedCalendarPolicy {
        PublishedCalendarPolicy(
            authorityID: "TEST_PILOT_AUTHORITY",
            authorityStatus: "pilot",
            publicationDigest: publicationDigest,
            resourceSHA256: rawSHA256(data)
        )
    }

    func testUnratifiedDefaultPolicyFailsClosed() throws {
        let data = fixtureData()
        let url = try writeFixture(data)

        XCTAssertNil(
            PublishedCalendarLoader.load(
                url: url,
                policy: .unratified,
                calendarCoreSpec: try spec
            )
        )
    }

    func testExplicitFinitePolicyLoadsExactAuthorizedBytes() throws {
        let data = fixtureData()
        let url = try writeFixture(data)

        let publication = try XCTUnwrap(
            PublishedCalendarLoader.load(
                url: url,
                policy: policy(for: data),
                calendarCoreSpec: try spec
            )
        )

        XCTAssertTrue(publication.isValidatedForProjection)
        XCTAssertEqual(publication.years.count, 2)
        XCTAssertEqual(publication.years[0].year, 7)
        XCTAssertEqual(
            publication.years[1].openingCivilDate,
            "2026-12-31"
        )
        XCTAssertEqual(
            publication.validationReceipt?.authorityID,
            "TEST_PILOT_AUTHORITY"
        )
    }

    func testRawResourceTamperingFailsClosed() throws {
        let data = fixtureData()
        var tampered = data
        tampered.append(0x20)
        let url = try writeFixture(tampered)

        XCTAssertNil(
            PublishedCalendarLoader.load(
                url: url,
                policy: policy(for: data),
                calendarCoreSpec: try spec
            )
        )
    }

    func testWrongAuthorityPolicyFailsClosed() throws {
        let data = fixtureData()
        let url = try writeFixture(data)
        let base = policy(for: data)
        let wrong = PublishedCalendarPolicy(
            authorityID: "OTHER_AUTHORITY",
            authorityStatus: base.authorityStatus,
            publicationDigest: base.publicationDigest,
            resourceSHA256: base.resourceSHA256
        )

        XCTAssertNil(
            PublishedCalendarLoader.load(
                url: url,
                policy: wrong,
                calendarCoreSpec: try spec
            )
        )
    }

    func testWrongPublicationDigestPolicyFailsClosed() throws {
        let data = fixtureData()
        let url = try writeFixture(data)
        let base = policy(for: data)
        let wrong = PublishedCalendarPolicy(
            authorityID: base.authorityID,
            authorityStatus: base.authorityStatus,
            publicationDigest:
                "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
            resourceSHA256: base.resourceSHA256
        )

        XCTAssertNil(
            PublishedCalendarLoader.load(
                url: url,
                policy: wrong,
                calendarCoreSpec: try spec
            )
        )
    }

    func testProjectionRejectsNon364OpeningSpan() throws {
        let data = fixtureData(secondOpening: "2027-01-01")
        let url = try writeFixture(data)

        XCTAssertNil(
            PublishedCalendarLoader.load(
                url: url,
                policy: policy(for: data),
                calendarCoreSpec: try spec
            )
        )
    }

    func testUnvalidatedSyntheticPublicationCannotProject() throws {
        let unvalidated = PublishedCivicCalendar(
            version: "test",
            years: [
                PublishedCivicYear(
                    year: 7,
                    openingCivilDate: "2026-01-01"
                )
            ],
            validationReceipt: nil
        )

        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(
            identifier: "America/Denver"
        )!

        let now = calendar.date(
            from: DateComponents(
                year: 2026,
                month: 1,
                day: 10,
                hour: 12
            )
        )!

        let snapshot = CivicCalendarEngine.snapshot(
            now: now,
            latitude: 40.3978,
            longitude: -105.0749,
            publishedCalendar: unvalidated,
            calendarCoreSpec: try spec,
            calendar: calendar
        )

        XCTAssertEqual(
            snapshot.commonCalendarDetail,
            "PUBLICATION NOT AUTHORIZED"
        )
    }
}
