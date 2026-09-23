import CryptoKit
import Foundation

struct PublishedCivicYear: Equatable {
    let year: Int
    let openingCivilDate: String
}

struct PublishedCalendarValidationReceipt: Equatable {
    let authorityID: String
    let authorityStatus: String
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
    let publicationDigest: String?
    let resourceSHA256: String?

    static let unratified = PublishedCalendarPolicy(
        authorityID: nil,
        authorityStatus: nil,
        publicationDigest: nil,
        resourceSHA256: nil
    )

    var isExplicitlyAuthorized: Bool {
        guard
            let authorityID, !authorityID.isEmpty,
            let authorityStatus,
            ["pilot", "enacted"].contains(authorityStatus),
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

    struct YearRow: Decodable {
        let year: Int
        let openingCivilDate: String
    }

    let publicationVersion: String
    let calendarCoreSpecVersion: String
    let authority: Authority
    let years: [YearRow]
    let publicationDigest: String
}

enum PublishedCalendarLoader {
    static let supportedPublicationVersion =
        "stillpoint-calendar-publication-v2"

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
            publicationDigest: envelope.publicationDigest.lowercased(),
            resourceSHA256: sha256(data),
            source: "validated-finite-immutable-projection"
        )

        return PublishedCivicCalendar(
            version: envelope.publicationVersion,
            years: envelope.years.map {
                PublishedCivicYear(
                    year: $0.year,
                    openingCivilDate: $0.openingCivilDate
                )
            },
            validationReceipt: receipt
        )
    }

    static func isSHA256(_ value: String) -> Bool {
        value.count == 64
            && value.allSatisfy { $0.isHexDigit }
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
        guard
            envelope.publicationVersion == supportedPublicationVersion,
            envelope.calendarCoreSpecVersion == spec.version,
            envelope.authority.id == policy.authorityID,
            envelope.authority.status == policy.authorityStatus,
            envelope.publicationDigest.lowercased()
                == policy.publicationDigest?.lowercased(),
            isSHA256(envelope.publicationDigest),
            !envelope.years.isEmpty,
            validateRows(
                envelope.years,
                baseYearDays: spec.ordinaryCalendar.baseYearDays
            )
        else { return false }

        return true
    }

    private static func parseCivilDate(
        _ value: String,
        calendar: Calendar
    ) -> Date? {
        let parts = value.split(separator: "-", omittingEmptySubsequences: false)
        guard
            parts.count == 3,
            parts[0].count == 4,
            parts[1].count == 2,
            parts[2].count == 2,
            let year = Int(parts[0]),
            let month = Int(parts[1]),
            let day = Int(parts[2]),
            (1...12).contains(month),
            (1...31).contains(day),
            let parsed = calendar.date(
                from: DateComponents(
                    timeZone: calendar.timeZone,
                    year: year,
                    month: month,
                    day: day
                )
            )
        else { return nil }

        let components = calendar.dateComponents(
            [.year, .month, .day],
            from: parsed
        )
        guard
            components.year == year,
            components.month == month,
            components.day == day
        else { return nil }

        return parsed
    }

    private static func validateRows(
        _ rows: [PublishedCalendarEnvelope.YearRow],
        baseYearDays: Int
    ) -> Bool {
        var calendar = Calendar(identifier: .gregorian)
        calendar.locale = Locale(identifier: "en_US_POSIX")
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!

        for index in rows.indices {
            let row = rows[index]
            guard
                let opening = parseCivilDate(
                    row.openingCivilDate,
                    calendar: calendar
                )
            else { return false }

            if rows.indices.contains(index + 1) {
                let next = rows[index + 1]
                guard
                    next.year == row.year + 1,
                    let nextOpening = parseCivilDate(
                        next.openingCivilDate,
                        calendar: calendar
                    ),
                    let span = calendar.dateComponents(
                        [.day],
                        from: opening,
                        to: nextOpening
                    ).day,
                    span == baseYearDays
                else { return false }
            }
        }

        return true
    }
}
