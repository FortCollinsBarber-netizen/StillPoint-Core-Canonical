import CryptoKit
import Foundation

struct PublishedCivicYear: Codable, Equatable {
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
    let publicationVersion: String
    let calendarCoreSpecVersion: String
    let years: [PublishedCivicYear]
    let validationReceipt: PublishedCalendarValidationReceipt?

    var isValidatedForProjection: Bool {
        validationReceipt != nil
    }

    static func conformanceFixture(
        years: [PublishedCivicYear]
    ) -> PublishedCivicCalendar {
        PublishedCivicCalendar(
            publicationVersion: "CONFORMANCE-ONLY",
            calendarCoreSpecVersion: "stillpoint-calendar-core-spec-v2",
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

private struct PublishedCalendarEnvelope: Decodable {
    struct Authority: Decodable {
        let id: String
        let status: String
    }

    let publicationVersion: String
    let calendarCoreSpecVersion: String
    let authority: Authority
    let years: [PublishedCivicYear]
    let publicationDigest: String
}

enum PublishedCalendarLoader {
    static let supportedPublicationVersion =
        "stillpoint-calendar-publication-v2"

    static func load(
        bundle: Bundle = .main,
        calendarCoreSpec: CalendarCoreSpec? = CalendarCoreSpecLoader.load()
    ) -> PublishedCivicCalendar? {
        guard let spec = calendarCoreSpec else { return nil }

        if let url = bundle.url(
            forResource: "published_calendar",
            withExtension: "json"
        ), let publication = load(url: url, calendarCoreSpec: spec) {
            return publication
        }

        #if DEBUG
        let sourceURL = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("Resources")
            .appendingPathComponent("published_calendar.json")
        return load(url: sourceURL, calendarCoreSpec: spec)
        #else
        return nil
        #endif
    }

    static func load(
        url: URL,
        calendarCoreSpec spec: CalendarCoreSpec
    ) -> PublishedCivicCalendar? {
        guard
            let data = try? Data(contentsOf: url),
            let envelope = try? JSONDecoder().decode(
                PublishedCalendarEnvelope.self,
                from: data
            ),
            validate(
                envelope,
                rawData: data,
                spec: spec
            )
        else { return nil }

        let receipt = PublishedCalendarValidationReceipt(
            authorityID: envelope.authority.id,
            authorityStatus: envelope.authority.status,
            publicationDigest: envelope.publicationDigest.lowercased(),
            resourceSHA256: sha256(data),
            source: "validated-enacted-v2-publication"
        )

        return PublishedCivicCalendar(
            publicationVersion: envelope.publicationVersion,
            calendarCoreSpecVersion: envelope.calendarCoreSpecVersion,
            years: envelope.years,
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

    private static func computedPublicationDigest(
        _ data: Data
    ) -> String? {
        guard
            var object = try? JSONSerialization.jsonObject(
                with: data
            ) as? [String: Any]
        else { return nil }

        object.removeValue(forKey: "publicationDigest")
        guard
            let canonical = try? JSONSerialization.data(
                withJSONObject: object,
                options: [.sortedKeys]
            )
        else { return nil }

        return sha256(canonical)
    }

    private static func validate(
        _ envelope: PublishedCalendarEnvelope,
        rawData: Data,
        spec: CalendarCoreSpec
    ) -> Bool {
        guard
            envelope.publicationVersion == supportedPublicationVersion,
            envelope.calendarCoreSpecVersion == spec.version,
            envelope.authority.status == "enacted",
            !envelope.authority.id.isEmpty,
            isSHA256(envelope.publicationDigest),
            computedPublicationDigest(rawData)
                == envelope.publicationDigest.lowercased(),
            envelope.years.count == 50,
            validateRows(
                envelope.years,
                baseYearDays: spec.ordinaryCalendar.baseYearDays
            )
        else { return false }

        return true
    }

    private static func validateRows(
        _ rows: [PublishedCivicYear],
        baseYearDays: Int
    ) -> Bool {
        guard !rows.isEmpty else { return false }

        var calendar = Calendar(identifier: .gregorian)
        calendar.locale = Locale(identifier: "en_US_POSIX")
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!

        let formatter = DateFormatter()
        formatter.calendar = calendar
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = calendar.timeZone
        formatter.dateFormat = "yyyy-MM-dd"
        formatter.isLenient = false

        for index in rows.indices {
            let row = rows[index]
            guard formatter.date(from: row.openingCivilDate) != nil else {
                return false
            }

            if rows.indices.contains(index + 1) {
                let next = rows[index + 1]
                guard
                    next.year == row.year + 1,
                    let opening = formatter.date(from: row.openingCivilDate),
                    let nextOpening = formatter.date(from: next.openingCivilDate),
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
