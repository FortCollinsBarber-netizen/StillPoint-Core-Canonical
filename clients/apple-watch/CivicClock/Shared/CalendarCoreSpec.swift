import Foundation

struct CalendarCoreSpec: Codable, Equatable {
    struct Boundary: Codable, Equatable {
        let apparentHorizonZenithDegrees: Double
        let failurePolicy: String
        let protocolId: String
    }

    struct EnactmentBoundary: Codable, Equatable {
        let lawDoesNotSupplyEpoch: Bool
        let requiredForFiniteProjection: [String]
        let status: String
    }

    struct MonthDay: Codable, Equatable {
        let day: Int
        let month: Int
    }

    struct OrdinaryCalendar: Codable, Equatable {
        let baseYearDays: Int
        let day001Weekday: String
        let hasDecember31: Bool
        let hasFebruary29: Bool
        let monthLengths: [Int]
        let quarterDays: Int
        let quarterRelation: String
        let quarters: Int
        let weekDays: Int
        let weeksPerYear: Int
        let yearClosing: MonthDay
        let yearOpening: MonthDay
    }

    struct AnnualTransition: Codable, Equatable {
        let interannualDays: Int
        let reconciliationAllowed: Bool
        let rule: String
    }

    struct WitnessPolicy: Codable, Equatable {
        let astronomy: String
        let enochicGates: String
        let lunar: String
        let seasonal: String
    }

    struct HistoricalModels: Codable, Equatable {
        let nearestLegalSpringGateV33: String
        let nearestLegalV32: String
    }

    struct Jurisdiction: Codable, Equatable {
        let authorityNamespace: String
        let calendarNamespace: String
        let translationAuthority: String
    }

    let annualTransition: AnnualTransition
    let boundary: Boundary
    let enactmentBoundary: EnactmentBoundary
    let historicalModels: HistoricalModels
    let invariants: [String]
    let jurisdiction: Jurisdiction
    let ordinaryCalendar: OrdinaryCalendar
    let version: String
    let witnessPolicy: WitnessPolicy
}

enum CalendarCoreSpecLoader {
    static let supportedVersion = "stillpoint-calendar-core-spec-v2"

    static func load(bundle: Bundle = .main) -> CalendarCoreSpec? {
        if let url = bundle.url(
            forResource: "calendar_core_spec",
            withExtension: "json"
        ), let spec = load(url: url) {
            return spec
        }

        #if DEBUG
        let sourceURL = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("Resources")
            .appendingPathComponent("calendar_core_spec.json")
        return load(url: sourceURL)
        #else
        return nil
        #endif
    }

    static func load(url: URL) -> CalendarCoreSpec? {
        guard
            let data = try? Data(contentsOf: url),
            let spec = try? JSONDecoder().decode(
                CalendarCoreSpec.self,
                from: data
            ),
            validate(spec)
        else { return nil }
        return spec
    }

    private static func validate(_ spec: CalendarCoreSpec) -> Bool {
        let calendar = spec.ordinaryCalendar
        let enactment = spec.enactmentBoundary

        guard
            spec.version == supportedVersion,
            spec.boundary.apparentHorizonZenithDegrees.isFinite,
            enactment.status == "annual-law-ratified-epoch-external",
            enactment.lawDoesNotSupplyEpoch,
            Set(enactment.requiredForFiniteProjection) == Set([
                "firstOpening",
                "publicationAuthority"
            ]),
            calendar.baseYearDays == 364,
            calendar.weekDays == 7,
            calendar.weeksPerYear == 52,
            calendar.day001Weekday == "Thursday",
            calendar.monthLengths == [
                31, 28, 31, 30, 31, 30,
                31, 31, 30, 31, 30, 30
            ],
            calendar.monthLengths.reduce(0, +) == 364,
            calendar.quarterDays == 91,
            calendar.quarters == 4,
            calendar.quarterDays * calendar.quarters == 364,
            calendar.yearOpening == MonthDay(day: 1, month: 1),
            calendar.yearClosing == MonthDay(day: 30, month: 12),
            calendar.hasFebruary29 == false,
            calendar.hasDecember31 == false,
            spec.annualTransition.interannualDays == 0,
            spec.annualTransition.reconciliationAllowed == false,
            spec.annualTransition.rule == "DAY_364_TO_NEXT_YEAR_DAY_001",
            spec.witnessPolicy.astronomy == "witness-only-no-grid-mutation",
            spec.witnessPolicy.lunar == "witness-only-no-grid-mutation",
            spec.witnessPolicy.seasonal == "witness-only-no-grid-mutation",
            spec.witnessPolicy.enochicGates == "witness-metadata-no-grid-mutation",
            spec.historicalModels.nearestLegalV32 == "superseded-non-operative",
            spec.historicalModels.nearestLegalSpringGateV33 == "superseded-non-operative"
        else { return false }

        return true
    }
}
