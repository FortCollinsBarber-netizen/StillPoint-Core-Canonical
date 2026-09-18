import Foundation

struct CalendarCoreContract: Codable, Equatable {
    struct Constants: Codable, Equatable {
        let apparentHorizonZenithDegrees: Double
        let baseYearDays: Int
        let gateSequence: [Int]
        let monthLengths: [Int]
        let phaseLengths: [Int]
        let reconciliationDaysAllowed: [Int]
        let springGateOrdinalV33Candidate: Int
    }

    struct Jurisdiction: Codable, Equatable {
        let authorityNamespace: String
        let calendarNamespace: String
        let referenceStatus: String
    }

    struct ConformanceContext: Codable, Equatable {
        let commonStandardOffsetSeconds: Int
        let commonYear: Int
        let day001Weekday: String
        let jubileeEpochCommonYear: Int
        let jubileeEpochCycle: Int
        let latitude: Double
        let legalCivilZone: String
        let locationId: String
        let longitude: Double
        let openingCivilDate: String
    }

    struct GoldenVector: Codable, Equatable {
        struct Expected: Codable, Equatable {
            struct CommonDate: Codable, Equatable {
                let day: Int
                let dayInWeek: Int
                let month: Int
                let ordinal: Int
                let quarter: Int
                let week: Int
                let weekday: String
                let year: Int
            }

            struct Jubilee: Codable, Equatable {
                let cycle: Int
                let cycleYear: Int
                let isJubileeYear: Bool
                let isSabbaticalThreshold: Bool
                let sevenYearBlock: Int?
                let yearWithinBlock: Int?
            }

            let annualPhase: Int?
            let civilOffsetSeconds: Int
            let commonDate: CommonDate?
            let commonStandardOffsetSeconds: Int
            let jubilee: Jubilee?
            let lordsDay: Bool
            let namedDay: String
            let nextProtectedBoundaryLabel: String?
            let sabbath: Bool
            let solarGate: Int?
            let stillPoint: Bool
        }

        let expected: Expected
        let id: String
        let instantUTC: String
    }

    let conformanceContext: ConformanceContext
    let constants: Constants
    let goldenVectors: [GoldenVector]
    let jurisdiction: Jurisdiction
    let version: String
}

enum CalendarCoreContractLoader {
    static func load(bundle: Bundle = .main) -> CalendarCoreContract? {
        guard let url = bundle.url(
            forResource: "calendar_core_contract",
            withExtension: "json"
        ) else { return nil }
        return load(url: url)
    }

    static func load(url: URL) -> CalendarCoreContract? {
        guard
            let data = try? Data(contentsOf: url),
            let contract = try? JSONDecoder().decode(
                CalendarCoreContract.self,
                from: data
            )
        else { return nil }

        guard
            contract.version == "stillpoint-calendar-core-contract-v1",
            contract.jurisdiction.calendarNamespace == "stillpoint.calendar_core",
            contract.jurisdiction.authorityNamespace == "stillpoint.temporal",
            contract.constants.baseYearDays == 364,
            contract.constants.reconciliationDaysAllowed == [0, 7],
            contract.constants.monthLengths.reduce(0, +) == 364,
            contract.constants.phaseLengths.reduce(0, +) == 364,
            contract.constants.gateSequence.count == 12
        else { return nil }

        return contract
    }
}
