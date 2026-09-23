import Foundation

struct CalendarPopulation: Codable, Equatable {
    struct Jurisdiction: Codable, Equatable {
        let gridAuthority: Bool
        let mayAlterWeekday: Bool
        let mayInsertDays: Bool
        let mayMoveYearOpening: Bool
    }

    struct Witness: Codable, Equatable {
        let id: String
        let sourceRefs: [String]
        let role: String?
    }

    struct SeasonalArchitecture: Codable, Equatable {
        let authorityRole: String
        let gateSequence: [Int]
        let motions: [String]
        let phaseLengths: [Int]
        let quarterDays: Int
        let sourceRefs: [String]
    }

    struct Observance: Codable, Equatable {
        let assembly: Bool
        let day: Int
        let endDay: Int?
        let endMonth: Int?
        let id: String
        let jurisdiction: String
        let month: Int
        let name: String
        let note: String?
        let rule: String
        let sourceRefs: [String]
    }

    let authorityStatus: String
    let distributedWitnesses: [Witness]
    let invariants: [String]
    let jurisdiction: Jurisdiction
    let observances: [Observance]
    let seasonalArchitecture: SeasonalArchitecture
    let version: String
}

enum CalendarPopulationLoader {
    static let supportedVersion = "stillpoint-calendar-population-v1"

    static func load(
        bundle: Bundle = .main,
        calendarCoreSpec: CalendarCoreSpec? = CalendarCoreSpecLoader.load()
    ) -> CalendarPopulation? {
        guard let spec = calendarCoreSpec else { return nil }

        if let url = bundle.url(
            forResource: "calendar_population_v1",
            withExtension: "json"
        ), let population = load(url: url, calendarCoreSpec: spec) {
            return population
        }

        #if DEBUG
        let sourceURL = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("Resources")
            .appendingPathComponent("calendar_population_v1.json")
        return load(url: sourceURL, calendarCoreSpec: spec)
        #else
        return nil
        #endif
    }

    static func load(
        url: URL,
        calendarCoreSpec spec: CalendarCoreSpec
    ) -> CalendarPopulation? {
        guard
            let data = try? Data(contentsOf: url),
            let population = try? JSONDecoder().decode(
                CalendarPopulation.self,
                from: data
            ),
            validate(population, spec: spec)
        else { return nil }
        return population
    }

    private static func validate(
        _ population: CalendarPopulation,
        spec: CalendarCoreSpec
    ) -> Bool {
        let jurisdiction = population.jurisdiction
        let seasonal = population.seasonalArchitecture
        guard
            population.version == supportedVersion,
            population.authorityStatus == "population-layer-no-grid-authority",
            jurisdiction.gridAuthority == false,
            jurisdiction.mayInsertDays == false,
            jurisdiction.mayMoveYearOpening == false,
            jurisdiction.mayAlterWeekday == false,
            seasonal.authorityRole == "witness-metadata-no-grid-mutation",
            seasonal.phaseLengths.reduce(0, +) == 364,
            seasonal.phaseLengths.count == seasonal.gateSequence.count,
            seasonal.phaseLengths.count == seasonal.motions.count,
            seasonal.quarterDays == 91,
            Set(seasonal.gateSequence) == Set(1...6),
            population.observances.allSatisfy({ item in
                guard
                    (1...12).contains(item.month),
                    (1...spec.ordinaryCalendar.monthLengths[item.month - 1])
                        .contains(item.day)
                else { return false }

                if let endMonth = item.endMonth,
                   let endDay = item.endDay {
                    guard (1...12).contains(endMonth) else { return false }
                    return (1...spec.ordinaryCalendar.monthLengths[endMonth - 1])
                        .contains(endDay)
                }

                return item.endMonth == nil && item.endDay == nil
            })
        else { return false }

        return true
    }
}
