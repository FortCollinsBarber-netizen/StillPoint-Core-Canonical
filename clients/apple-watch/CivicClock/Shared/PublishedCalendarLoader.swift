import CryptoKit
import Foundation

struct PublishedCivicYear: Equatable {
    let year: Int
    let openingCivilDate: String
    let reconciliationDaysAfterCompletion: Int
}

struct PublishedCalendarValidationReceipt: Equatable {
    let authorityID: String
    let authorityStatus: String
    let referencePointID: String
    let referenceRuleVersion: String
    let ephemerisSource: String
    let ephemerisSHA256: String
    let publicationDigest: String
    let resourceSHA256: String
    let source: String
}

struct PublishedCivicCalendar: Equatable {
    let version: String
    let years: [PublishedCivicYear]
    let validationReceipt: PublishedCalendarValidationReceipt?

    var isValidatedForProjection: Bool {
        validationReceipt != nil
    }

    static func conformanceFixture(
        years: [PublishedCivicYear]
    ) -> PublishedCivicCalendar {
        PublishedCivicCalendar(
            version: "CONFORMANCE-ONLY",
            years: years,
            validationReceipt: PublishedCalendarValidationReceipt(
                authorityID: "CONFORMANCE_ONLY",
                authorityStatus: "conformance-only",
                referencePointID: "CONFORMANCE_ONLY",
                referenceRuleVersion: "CONFORMANCE_ONLY",
                ephemerisSource: "CONFORMANCE_ONLY",
                ephemerisSHA256: String(repeating: "0", count: 64),
                publicationDigest: String(repeating: "0", count: 64),
                resourceSHA256: String(repeating: "0", count: 64),
                source: "unit-test-conformance"
            )
        )
    }
}

struct PublishedCalendarPolicy: Equatable {
    let authorityID: String?
    let authorityStatus: String?
    let referencePointID: String?
    let referenceRuleVersion: String?
    let ephemerisSource: String?
    let ephemerisSHA256: String?
    let publicationDigest: String?
    let resourceSHA256: String?

    static let unratified = PublishedCalendarPolicy(
        authorityID: nil,
        authorityStatus: nil,
        referencePointID: nil,
        referenceRuleVersion: nil,
        ephemerisSource: nil,
        ephemerisSHA256: nil,
        publicationDigest: nil,
        resourceSHA256: nil
    )

    var isExplicitlyAuthorized: Bool {
        guard
            let authorityID, !authorityID.isEmpty,
            let authorityStatus,
            ["pilot", "enacted"].contains(authorityStatus),
            let referencePointID, !referencePointID.isEmpty,
            let referenceRuleVersion, !referenceRuleVersion.isEmpty,
            let ephemerisSource, !ephemerisSource.isEmpty,
            let ephemerisSHA256,
            PublishedCalendarLoader.isSHA256(ephemerisSHA256),
            let publicationDigest,
            PublishedCalendarLoader.isSHA256(publicationDigest),
            let resourceSHA256,
            PublishedCalendarLoader.isSHA256(resourceSHA256)
        else { return false }

        return true
    }
}

private struct PublishedCalendarEnvelope: Decodable {
    struct Authority: Decodable {
        let id: String
        let status: String
    }

    struct ReferencePoint: Decodable {
        let id: String
        let coordinateCustodyDigest: String
    }

    struct DuskProtocol: Decodable {
        let id: String
        let sunCenterAltitudeDegrees: Double
    }

    struct SeasonalAnchor: Decodable {
        let event: String
        let commonMonth: Int
        let commonDay: Int
        let ordinal: Int
    }

    struct EphemerisEvidence: Decodable {
        let source: String
        let sha256: String
    }

    struct YearRow: Decodable {
        let year: Int
        let openingCivilDate: String
        let reconciliationDaysAfterCompletion: Int
        let reconciliationReasonCode: String
        let governingMarchEquinoxYear: Int
        let governingMarchEquinoxUTC: String
        let immediateCandidateOpeningCivilDate: String
        let delayedCandidateOpeningCivilDate: String
        let immediateSpringGateCivilDate: String
        let delayedSpringGateCivilDate: String
        let immediateErrorSeconds: Double
        let delayedErrorSeconds: Double
        let nextYearSpringGateCivilDate: String
    }

    let publicationVersion: String
    let calendarCoreSpecVersion: String
    let version: String
    let authority: Authority
    let referenceRuleVersion: String
    let referencePoint: ReferencePoint
    let duskProtocol: DuskProtocol
    let seasonalAnchor: SeasonalAnchor
    let snapOperator: String
    let ephemerisEvidence: EphemerisEvidence
    let years: [YearRow]
    let publicationDigest: String
}

enum PublishedCalendarLoader {
    static let supportedPublicationVersion =
        "stillpoint-calendar-publication-v1"
    static let supportedTemporalVersion =
        "stillpoint-temporal-v3.3"

    static func load(
        bundle: Bundle = .main,
        policy: PublishedCalendarPolicy = .unratified,
        calendarCoreSpec: CalendarCoreSpec? = CalendarCoreSpecLoader.load()
    ) -> PublishedCivicCalendar? {
        guard
            policy.isExplicitlyAuthorized,
            let calendarCoreSpec,
            let url = bundle.url(
                forResource: "published_calendar",
                withExtension: "json"
            )
        else { return nil }

        return load(
            url: url,
            policy: policy,
            calendarCoreSpec: calendarCoreSpec
        )
    }

    static func load(
        url: URL,
        policy: PublishedCalendarPolicy,
        calendarCoreSpec spec: CalendarCoreSpec
    ) -> PublishedCivicCalendar? {
        guard
            policy.isExplicitlyAuthorized,
            let data = try? Data(contentsOf: url),
            sha256(data) == policy.resourceSHA256?.lowercased(),
            let envelope = try? JSONDecoder().decode(
                PublishedCalendarEnvelope.self,
                from: data
            ),
            validate(
                envelope,
                policy: policy,
                spec: spec
            )
        else { return nil }

        let receipt = PublishedCalendarValidationReceipt(
            authorityID: envelope.authority.id,
            authorityStatus: envelope.authority.status,
            referencePointID: envelope.referencePoint.id,
            referenceRuleVersion: envelope.referenceRuleVersion,
            ephemerisSource: envelope.ephemerisEvidence.source,
            ephemerisSHA256: envelope.ephemerisEvidence.sha256.lowercased(),
            publicationDigest: envelope.publicationDigest.lowercased(),
            resourceSHA256: sha256(data),
            source: "validated-finite-publication"
        )

        return PublishedCivicCalendar(
            version: envelope.version,
            years: envelope.years.map {
                PublishedCivicYear(
                    year: $0.year,
                    openingCivilDate: $0.openingCivilDate,
                    reconciliationDaysAfterCompletion:
                        $0.reconciliationDaysAfterCompletion
                )
            },
            validationReceipt: receipt
        )
    }

    static func isSHA256(_ value: String) -> Bool {
        value.count == 64
            && value.allSatisfy {
                $0.isHexDigit
            }
    }

    private static func sha256(_ data: Data) -> String {
        SHA256.hash(data: data)
            .map { String(format: "%02x", $0) }
            .joined()
    }

    private static func validate(
        _ envelope: PublishedCalendarEnvelope,
        policy: PublishedCalendarPolicy,
        spec: CalendarCoreSpec
    ) -> Bool {
        let v33 = spec.referenceRules.v33Candidate
        let geometryAltitude =
            -(spec.boundary.apparentHorizonZenithDegrees - 90.0)

        guard
            envelope.publicationVersion == supportedPublicationVersion,
            envelope.calendarCoreSpecVersion == spec.version,
            envelope.version == supportedTemporalVersion,
            envelope.authority.id == policy.authorityID,
            envelope.authority.status == policy.authorityStatus,
            envelope.referenceRuleVersion == policy.referenceRuleVersion,
            envelope.referenceRuleVersion == "v3.3-candidate",
            envelope.referencePoint.id == policy.referencePointID,
            isSHA256(envelope.referencePoint.coordinateCustodyDigest),
            envelope.ephemerisEvidence.source == policy.ephemerisSource,
            envelope.ephemerisEvidence.sha256.lowercased()
                == policy.ephemerisSHA256?.lowercased(),
            isSHA256(envelope.ephemerisEvidence.sha256),
            envelope.publicationDigest.lowercased()
                == policy.publicationDigest?.lowercased(),
            isSHA256(envelope.publicationDigest),
            envelope.snapOperator == v33.operator,
            envelope.seasonalAnchor.event == "march_equinox",
            envelope.seasonalAnchor.commonMonth == v33.springGateMonth,
            envelope.seasonalAnchor.commonDay == v33.springGateDay,
            envelope.seasonalAnchor.ordinal == v33.springGateOrdinal,
            envelope.duskProtocol.sunCenterAltitudeDegrees.isFinite,
            abs(
                envelope.duskProtocol.sunCenterAltitudeDegrees
                    - geometryAltitude
            ) < 0.0000001,
            !envelope.years.isEmpty,
            validateRows(
                envelope.years,
                spec: spec
            )
        else { return false }

        return true
    }

    private static func validateRows(
        _ rows: [PublishedCalendarEnvelope.YearRow],
        spec: CalendarCoreSpec
    ) -> Bool {
        var calendar = Calendar(identifier: .gregorian)
        calendar.locale = Locale(identifier: "en_US_POSIX")
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!

        let formatter = DateFormatter()
        formatter.calendar = calendar
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = calendar.timeZone
        formatter.dateFormat = "yyyy-MM-dd"
        formatter.isLenient = false

        let allowed = Set(spec.reconciliation.allowedDays)

        for index in rows.indices {
            let row = rows[index]

            guard
                allowed.contains(
                    row.reconciliationDaysAfterCompletion
                ),
                [
                    "IMMEDIATE_CLOSER_OR_TIE",
                    "RECONCILIATION_WEEK_CLOSER"
                ].contains(row.reconciliationReasonCode),
                row.immediateErrorSeconds >= 0,
                row.delayedErrorSeconds >= 0,
                formatter.date(from: row.openingCivilDate) != nil,
                formatter.date(
                    from: row.immediateCandidateOpeningCivilDate
                ) != nil,
                formatter.date(
                    from: row.delayedCandidateOpeningCivilDate
                ) != nil,
                formatter.date(
                    from: row.immediateSpringGateCivilDate
                ) != nil,
                formatter.date(
                    from: row.delayedSpringGateCivilDate
                ) != nil,
                formatter.date(
                    from: row.nextYearSpringGateCivilDate
                ) != nil,
                ISO8601DateFormatter().date(
                    from: row.governingMarchEquinoxUTC
                ) != nil
            else { return false }

            if rows.indices.contains(index + 1) {
                let next = rows[index + 1]

                guard
                    next.year == row.year + 1,
                    let opening = formatter.date(
                        from: row.openingCivilDate
                    ),
                    let nextOpening = formatter.date(
                        from: next.openingCivilDate
                    ),
                    let span = calendar.dateComponents(
                        [.day],
                        from: opening,
                        to: nextOpening
                    ).day,
                    span
                        == spec.ordinaryCalendar.baseYearDays
                        + row.reconciliationDaysAfterCompletion
                else { return false }
            }
        }

        return true
    }
}
