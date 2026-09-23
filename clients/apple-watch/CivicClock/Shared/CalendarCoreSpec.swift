import Foundation

struct CalendarCoreSpec: Codable, Equatable {
    struct Boundary: Codable, Equatable {
        let apparentHorizonZenithDegrees: Double
        let failurePolicy: String
        let protocolId: String
        let role: String
    }

    struct DateAddress: Codable, Equatable {
        let month: Int
        let day: Int
    }

    struct Grid: Codable, Equatable {
        let status: String
        let days: Int
        let weeks: Int
        let day001Weekday: String
        let firstDate: DateAddress
        let lastDate: DateAddress
        let december31Exists: Bool
        let nextAfterLastDate: DateAddress
        let interannualDays: Int
    }

    struct OrdinaryCalendar: Codable, Equatable {
        let baseYearDays: Int
        let monthLengths: [Int]
        let quarterDays: Int
        let quarters: Int
        let weekDays: Int
    }

    struct Reconciliation: Codable, Equatable {
        let enabled: Bool
        let addressPattern: String
        let allowedDays: [Int]
        let inheritsOrdinaryFields: Bool
        let namespace: String
    }

    struct EnochicArchitecture: Codable, Equatable {
        let phaseLengths: [Int]
        let gateSequence: [Int]
        let pairedGateCount: Int
        let quarterDays: Int
        let quarters: Int
        let role: String
    }

    let version: String
    let boundary: Boundary
    let grid: Grid
    let ordinaryCalendar: OrdinaryCalendar
    let reconciliation: Reconciliation
    let enochicArchitecture: EnochicArchitecture
}

enum CalendarCoreSpecLoader {
    static let supportedVersion = "stillpoint-calendar-core-spec-v2-fixed-364"

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
        let reconciliation = spec.reconciliation
        let grid = spec.grid
        let enoch = spec.enochicArchitecture

        guard
            spec.version == supportedVersion,
            spec.boundary.apparentHorizonZenithDegrees.isFinite,
            grid.status == "ratified-fixed",
            grid.days == 364,
            grid.weeks == 52,
            grid.day001Weekday == "Thursday",
            grid.firstDate == DateAddress(month: 1, day: 1),
            grid.lastDate == DateAddress(month: 12, day: 30),
            grid.december31Exists == false,
            grid.nextAfterLastDate == DateAddress(month: 1, day: 1),
            grid.interannualDays == 0,
            calendar.baseYearDays == grid.days,
            calendar.weekDays == 7,
            calendar.monthLengths.reduce(0, +) == grid.days,
            calendar.monthLengths.count == 12,
            calendar.monthLengths.last == 30,
            calendar.quarterDays == 91,
            calendar.quarters == 4,
            reconciliation.enabled == false,
            reconciliation.namespace == "abolished",
            reconciliation.allowedDays == [0],
            enoch.phaseLengths.reduce(0, +) == grid.days,
            enoch.gateSequence.count == enoch.phaseLengths.count,
            enoch.pairedGateCount == 6,
            enoch.quarterDays == 91,
            enoch.quarters == 4
        else { return false }

        return true
    }
}
