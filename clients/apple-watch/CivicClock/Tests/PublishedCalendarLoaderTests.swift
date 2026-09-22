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

    private func fixtureData() -> Data {
        Data(
            """
            {
              "publicationVersion": "stillpoint-calendar-publication-v1",
              "calendarCoreSpecVersion": "stillpoint-calendar-core-spec-v1",
              "version": "stillpoint-temporal-v3.3",
              "authority": {
                "id": "TEST_PILOT_AUTHORITY",
                "status": "pilot"
              },
              "referenceRuleVersion": "v3.3-candidate",
              "referencePoint": {
                "id": "REFERENCE_TEST",
                "coordinateCustodyDigest": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
              },
              "duskProtocol": {
                "id": "apparent-sunset-0.8333",
                "sunCenterAltitudeDegrees": -0.8333
              },
              "seasonalAnchor": {
                "event": "march_equinox",
                "commonMonth": 3,
                "commonDay": 20,
                "ordinal": 80
              },
              "snapOperator": "NearestLegalSpringGate",
              "ephemerisEvidence": {
                "source": "TEST_EPHEMERIS",
                "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
              },
              "years": [
                {
                  "year": 7,
                  "openingCivilDate": "2026-01-01",
                  "reconciliationDaysAfterCompletion": 0,
                  "reconciliationReasonCode": "IMMEDIATE_CLOSER_OR_TIE",
                  "governingMarchEquinoxYear": 2027,
                  "governingMarchEquinoxUTC": "2027-03-20T12:00:00Z",
                  "immediateCandidateOpeningCivilDate": "2026-12-31",
                  "delayedCandidateOpeningCivilDate": "2027-01-07",
                  "immediateSpringGateCivilDate": "2027-03-20",
                  "delayedSpringGateCivilDate": "2027-03-27",
                  "immediateErrorSeconds": 0,
                  "delayedErrorSeconds": 604800,
                  "nextYearSpringGateCivilDate": "2027-03-20"
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
            referenceRuleVersion: "v3.3-candidate",
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
        XCTAssertEqual(publication.years.count, 1)
        XCTAssertEqual(publication.years[0].year, 7)
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
        var expected = policy(for: data)
        expected = PublishedCalendarPolicy(
            authorityID: "OTHER_AUTHORITY",
            authorityStatus: expected.authorityStatus,
            referencePointID: expected.referencePointID,
            referenceRuleVersion: expected.referenceRuleVersion,
            ephemerisSource: expected.ephemerisSource,
            ephemerisSHA256: expected.ephemerisSHA256,
            publicationDigest: expected.publicationDigest,
            resourceSHA256: expected.resourceSHA256
        )

        XCTAssertNil(
            PublishedCalendarLoader.load(
                url: url,
                policy: expected,
                calendarCoreSpec: try spec
            )
        )
    }

    func testWrongReferencePointFailsClosed() throws {
        let data = fixtureData()
        let url = try writeFixture(data)
        let base = policy(for: data)
        let wrong = PublishedCalendarPolicy(
            authorityID: base.authorityID,
            authorityStatus: base.authorityStatus,
            referencePointID: "OTHER_REFERENCE",
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

    func testUnvalidatedSyntheticPublicationCannotProject() {
        let unvalidated = PublishedCivicCalendar(
            version: "test",
            years: [
                PublishedCivicYear(
                    year: 7,
                    openingCivilDate: "2026-01-01",
                    reconciliationDaysAfterCompletion: 0
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
            calendarCoreSpec: try? spec,
            calendar: calendar
        )

        XCTAssertEqual(
            snapshot.commonCalendarDetail,
            "PUBLICATION NOT AUTHORIZED"
        )
    }
}
