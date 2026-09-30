import Foundation

struct ExternalCalendarWitnessCatalog: Codable, Equatable {
    struct Jurisdiction: Codable, Equatable {
        let gridAuthority: Bool
        let mayAlterWeekday: Bool
        let mayInsertDays: Bool
        let mayMoveYearOpening: Bool
        let mayPromoteExternalCalendarToCommonLaw: Bool
    }

    struct Scope: Codable, Equatable {
        let externalProjectionYear: Int
        let repeatIntoLaterCommonYears: Bool
        let role: String
    }

    struct Event: Codable, Equatable {
        let authority: String
        let begins_at: String
        let calendar_effect: String
        let external_date: String
        let grid_authority: Bool
        let id: String
        let name: String
        let qualification: String?
        let schema: String
        let source_calendar: String
        let source_refs: [String]
    }

    let authorityStatus: String
    let events: [Event]
    let invariants: [String]
    let jurisdiction: Jurisdiction
    let scope: Scope
    let version: String

    func events(onExternalDate value: String) -> [Event] {
        events.filter { $0.external_date == value }
    }
}

enum ExternalCalendarWitnessLoader {
    static let supportedVersion =
        "stillpoint-external-calendar-witnesses-v1"

    static func load(
        bundle: Bundle = .main
    ) -> ExternalCalendarWitnessCatalog? {
        if let url = bundle.url(
            forResource: "calendar_external_witnesses_2026",
            withExtension: "json"
        ), let catalog = load(url: url) {
            return catalog
        }

        #if DEBUG
        let sourceURL = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("Resources")
            .appendingPathComponent(
                "calendar_external_witnesses_2026.json"
            )
        return load(url: sourceURL)
        #else
        return nil
        #endif
    }

    static func load(
        url: URL
    ) -> ExternalCalendarWitnessCatalog? {
        guard
            let data = try? Data(contentsOf: url),
            let catalog = try? JSONDecoder().decode(
                ExternalCalendarWitnessCatalog.self,
                from: data
            ),
            validate(catalog)
        else { return nil }
        return catalog
    }

    private static func validate(
        _ catalog: ExternalCalendarWitnessCatalog
    ) -> Bool {
        guard
            catalog.version == supportedVersion,
            catalog.authorityStatus
                == "witness-layer-no-grid-authority",
            catalog.jurisdiction.gridAuthority == false,
            catalog.jurisdiction.mayAlterWeekday == false,
            catalog.jurisdiction.mayInsertDays == false,
            catalog.jurisdiction.mayMoveYearOpening == false,
            catalog.jurisdiction.mayPromoteExternalCalendarToCommonLaw
                == false,
            catalog.scope.externalProjectionYear == 2026,
            catalog.scope.repeatIntoLaterCommonYears == false,
            catalog.scope.role
                == "comparison-and-observation-only",
            !catalog.events.isEmpty,
            catalog.events.allSatisfy({
                $0.authority == "witness-only"
                    && $0.grid_authority == false
                    && $0.calendar_effect == "none"
                    && [
                        "jewish",
                        "islamic"
                    ].contains($0.source_calendar)
                    && !$0.external_date.isEmpty
                    && !$0.id.isEmpty
                    && !$0.name.isEmpty
            })
        else { return false }

        return true
    }
}
