import Foundation

struct CalendarPopulation: Codable, Equatable {
    struct SacredYearProfile: Codable, Equatable {
        let id: String
        let selectionStatus: String
        let selectedBy: String
        let selectedOn: String
        let authorityScope: String
        let sourceCalendar: String
        let monthLengths: [Int]
        let anchorCommonMonth: Int
        let anchorCommonDay: Int
        let anchorWeekday: String
        let annualSolarReset: Bool
        let gridAuthority: Bool
    }

    struct LongCyclePolicy: Codable, Equatable {
        let id: String
        let selectionStatus: String
        let selectedBy: String
        let selectedOn: String
        let authorityScope: String
        let epochCommonYear: Int
        let epochCycle: Int
        let rolloverRule: String
        let cycleYears: Int
        let proclamationOrdinalYear: Int
        let year50OverlapsNextYear1: Bool
        let releaseObservanceId: String
        let gridAuthority: Bool
    }

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
        let sourceCalendar: String?
        let sourceMonth: Int?
        let sourceDay: Int?
        let sourceEndMonth: Int?
        let sourceEndDay: Int?
        let profileId: String?
    }

    let authorityStatus: String
    let distributedWitnesses: [Witness]
    let invariants: [String]
    let jurisdiction: Jurisdiction
    let observances: [Observance]
    let seasonalArchitecture: SeasonalArchitecture
    let version: String
    let sacredYearProfile: SacredYearProfile
    let longCyclePolicy: LongCyclePolicy
}

enum CalendarPopulationLoader {
    static let supportedVersion = "stillpoint-calendar-population-v2"

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
        let profile = population.sacredYearProfile
        let policy = population.longCyclePolicy
        let weekdays = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        guard (1...12).contains(profile.anchorCommonMonth),
              (1...spec.ordinaryCalendar.monthLengths[profile.anchorCommonMonth - 1]).contains(profile.anchorCommonDay),
              let firstWeekday = weekdays.firstIndex(of: spec.ordinaryCalendar.day001Weekday)
        else { return false }
        let anchorOrdinal = spec.ordinaryCalendar.monthLengths.prefix(profile.anchorCommonMonth - 1).reduce(0, +) + profile.anchorCommonDay
        guard
            population.version == supportedVersion,
            profile.id.isEmpty == false,
            profile.selectionStatus == "author-selected-working-rule-not-civil-enactment",
            policy.selectionStatus == "author-selected-working-rule-not-civil-enactment",
            profile.selectedBy == "Robert Emmanuel LaDay",
            policy.selectedBy == profile.selectedBy,
            profile.selectedOn == "2026-11-17",
            policy.selectedOn == profile.selectedOn,
            profile.sourceCalendar == "schematic-enochic-364",
            profile.authorityScope == "StillPoint-religious-overlay-only",
            profile.monthLengths == [30, 30, 31, 30, 30, 31, 30, 30, 31, 30, 30, 31],
            profile.anchorWeekday == "Wednesday",
            weekdays[(firstWeekday + anchorOrdinal - 1) % 7] == "Wednesday",
            profile.gridAuthority == false,
            profile.annualSolarReset == false,
            policy.rolloverRule == "overlap-49",
            policy.id.isEmpty == false,
            policy.authorityScope == "StillPoint-working-cycle-calculation-only",
            policy.cycleYears == 49,
            policy.proclamationOrdinalYear == 50,
            policy.year50OverlapsNextYear1 == true,
            policy.epochCommonYear > 0, policy.epochCycle > 0,
            policy.gridAuthority == false,
            policy.releaseObservanceId == "atonement",
            population.observances.contains(where: {
                $0.id == policy.releaseObservanceId && $0.profileId == profile.id
                    && $0.sourceMonth == 7 && $0.sourceDay == 10
            }),
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

                if let sourceCalendar = item.sourceCalendar {
                    guard sourceCalendar == profile.sourceCalendar,
                          item.profileId == profile.id,
                          let sourceMonth = item.sourceMonth, (1...12).contains(sourceMonth),
                          let sourceDay = item.sourceDay,
                          (1...profile.monthLengths[sourceMonth - 1]).contains(sourceDay)
                    else { return false }
                    let sourceOrdinal = profile.monthLengths.prefix(sourceMonth - 1).reduce(0, +) + sourceDay
                    let projectedOrdinal = (anchorOrdinal + sourceOrdinal - 2) % 364 + 1
                    let commonOrdinal = spec.ordinaryCalendar.monthLengths.prefix(item.month - 1).reduce(0, +) + item.day
                    guard projectedOrdinal == commonOrdinal else { return false }
                    if let endMonth = item.sourceEndMonth, let endDay = item.sourceEndDay {
                        guard (1...12).contains(endMonth), (1...profile.monthLengths[endMonth - 1]).contains(endDay),
                              let commonEndMonth = item.endMonth, let commonEndDay = item.endDay,
                              (1...12).contains(commonEndMonth)
                        else { return false }
                        let sourceEndOrdinal = profile.monthLengths.prefix(endMonth - 1).reduce(0, +) + endDay
                        let projectedEnd = (anchorOrdinal + sourceEndOrdinal - 2) % 364 + 1
                        let commonEnd = spec.ordinaryCalendar.monthLengths.prefix(commonEndMonth - 1).reduce(0, +) + commonEndDay
                        guard projectedEnd == commonEnd else { return false }
                    } else if item.sourceEndMonth != nil || item.sourceEndDay != nil
                                || item.endMonth != nil || item.endDay != nil {
                        return false
                    }
                } else if item.sourceMonth != nil || item.sourceDay != nil || item.profileId != nil
                            || item.sourceEndMonth != nil || item.sourceEndDay != nil {
                    return false
                }

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
