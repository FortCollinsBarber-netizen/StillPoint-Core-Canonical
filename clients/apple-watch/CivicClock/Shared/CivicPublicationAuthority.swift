import Foundation

private struct CivicPublicationPolicyDocument: Decodable {
    let version: String
    let authorityID: String
    let authorityStatus: String
    let referencePointID: String
    let referenceRuleVersion: String
    let ephemerisSource: String
    let ephemerisSHA256: String
    let publicationDigest: String
    let resourceSHA256: String
}

enum CivicPublicationAuthority {
    static let supportedPolicyVersion =
        "stillpoint-apple-publication-policy-v1"

    static func loadPolicy(
        bundle: Bundle = .main
    ) -> PublishedCalendarPolicy? {
        guard let url = bundle.url(
            forResource: "apple_publication_policy",
            withExtension: "json"
        ) else { return nil }

        return loadPolicy(url: url)
    }

    static func loadPolicy(
        url: URL
    ) -> PublishedCalendarPolicy? {
        guard
            let data = try? Data(contentsOf: url),
            let document = try? JSONDecoder().decode(
                CivicPublicationPolicyDocument.self,
                from: data
            ),
            document.version == supportedPolicyVersion
        else { return nil }

        let policy = PublishedCalendarPolicy(
            authorityID: document.authorityID,
            authorityStatus: document.authorityStatus,
            referencePointID: document.referencePointID,
            referenceRuleVersion: document.referenceRuleVersion,
            ephemerisSource: document.ephemerisSource,
            ephemerisSHA256: document.ephemerisSHA256,
            publicationDigest: document.publicationDigest,
            resourceSHA256: document.resourceSHA256
        )

        guard policy.isExplicitlyAuthorized else {
            return nil
        }

        return policy
    }

    static func loadPublishedCalendar(
        bundle: Bundle = .main,
        calendarCoreSpec: CalendarCoreSpec? = CalendarCoreSpecLoader.load()
    ) -> PublishedCivicCalendar? {
        guard
            let policy = loadPolicy(bundle: bundle),
            let calendarCoreSpec
        else { return nil }

        return PublishedCalendarLoader.load(
            bundle: bundle,
            policy: policy,
            calendarCoreSpec: calendarCoreSpec
        )
    }
}
