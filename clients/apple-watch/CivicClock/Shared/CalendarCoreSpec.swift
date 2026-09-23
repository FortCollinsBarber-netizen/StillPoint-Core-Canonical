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
        let month: Int
        let day: Int
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

    let version: String
    let annualTransition: AnnualTransition
    let boundary: Boundary
    let enactmentBoundary: EnactmentBoundary
    let ordinaryCalendar: OrdinaryCalendar
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
        let transition = spec.annualTransition

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
            calendar.quarterRelation
                == "ordinal-seasonal-not-civil-month-triples",
            calendar.yearOpening
                == CalendarCoreSpec.MonthDay(month: 1, day: 1),
            calendar.yearClosing
                == CalendarCoreSpec.MonthDay(month: 12, day: 30),
            calendar.hasFebruary29 == false,
            calendar.hasDecember31 == false,
            transition.rule == "DAY_364_TO_NEXT_YEAR_DAY_001",
            transition.interannualDays == 0,
            transition.reconciliationAllowed == false
        else { return false }

        return true
    }
}
