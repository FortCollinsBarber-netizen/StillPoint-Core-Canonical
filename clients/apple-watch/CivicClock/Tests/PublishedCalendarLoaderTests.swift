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
        reconciliation: Int = 0
    ) -> Data {
        Data(
            """
            {
              "publicationVersion": "stillpoint-calendar-publication-v1",
              "calendarCoreSpecVersion": "stillpoint-calendar-core-spec-v2",
              "version": "stillpoint-fixed-364-v1",
              "authority": {
                "id": "TEST_PILOT_AUTHORITY",
                "status": "pilot"
              },
              "referenceRuleVersion": "fixed-364-v1",
              "referencePoint": {
                "id": "REFERENCE_TEST",
                "coordinateCustodyDigest": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
              },
              "gridRule": {
                "yearDays": 364,
                "weekDays": 7,
                "yearCount": 2,
                "reconciliationDays": 0
              },
              "ephemerisEvidence": {
                "source": "TEST_EPHEMERIS",
                "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "role": "witness-only-no-grid-authority"
              },
              "years": [
                {
                  "year": 2026,
                  "openingCivilDate": "2026-01-01",
                  "reconciliationDaysAfterCompletion": (reconciliation)
                },
                {
                  "year": 2027,
                  "openingCivilDate": "2026-12-31",
                  "reconciliationDaysAfterCompletion": 0
                }
              ],
              "publicationDigest": "(publicationDigest)"
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
            referencePointID: "REFERENCE_TEST",
            referenceRuleVersion: "fixed-364-v1",
            ephemerisSource: "TEST_EPHEMERIS",
            ephemerisSHA256:
                "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
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

    func testExplicitFinitePolicyLoadsFixed364Publication() throws {
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
        XCTAssertEqual(publication.years[0].year, 2026)
        XCTAssertEqual(
            publication.years[1].openingCivilDate,
            "2026-12-31"
        )
        XCTAssertEqual(
            publication.validationReceipt?.referenceRuleVersion,
            "fixed-364-v1"
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
            referencePointID: base.referencePointID,
            referenceRuleVersion: base.referenceRuleVersion,
            ephemerisSource: base.ephemerisSource,
            ephemerisSHA256: base.ephemerisSHA256,
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

    func testAnyReconciliationFailsClosed() throws {
        let data = fixtureData(reconciliation: 7)
        let url = try writeFixture(data)

        XCTAssertNil(
            PublishedCalendarLoader.load(
                url: url,
                policy: policy(for: data),
                calendarCoreSpec: try spec
            )
        )
    }
}
