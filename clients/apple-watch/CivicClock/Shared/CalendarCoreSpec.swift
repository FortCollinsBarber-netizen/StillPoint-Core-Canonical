import Foundation

struct CalendarCoreSpec: Codable, Equatable {
    struct Boundary: Codable, Equatable {
        let apparentHorizonZenithDegrees: Double
        let failurePolicy: String
        let protocolId: String
    }

    struct EnactmentBoundary: Codable, Equatable {
        let lawDoesNotSupplyValues: Bool
        let requiredForFinitePublication: [String]
        let status: String
    }

    struct OrdinaryCalendar: Codable, Equatable {
        let baseYearDays: Int
        let monthLengths: [Int]
        let quarterDays: Int
        let quarters: Int
        let weekDays: Int
        let lastCommonMonth: Int
        let lastCommonDay: Int
        let december31Exists: Bool
    }

    struct CanonicalCycle: Codable, Equatable {
        let day001Weekday: String
        let firstOpeningCivilDate: String
        let firstYearLabel: Int
        let totalDays: Int
        let transition: String
        let yearCount: Int
    }

    struct Reconciliation: Codable, Equatable {
        let addressPattern: String?
        let allowedDays: [Int]
        let inheritsOrdinaryFields: Bool
        let namespace: String
    }

    struct Gates: Codable, Equatable {
        let gateSequence: [Int]
        let pairedGateCount: Int
        let phaseLengths: [Int]
        let role: String
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
        let rule: String
        let sourceRefs: [String]
    }

    struct ReferenceRules: Codable, Equatable {
        struct Rule: Codable, Equatable {
            let operation: String
            let status: String

            enum CodingKeys: String, CodingKey {
                case operation = "operator"
                case status
            }
        }

        struct V33Candidate: Codable, Equatable {
            let operation: String
            let springGateOrdinal: Int
            let springGateMonth: Int
            let springGateDay: Int
            let status: String

            enum CodingKeys: String, CodingKey {
                case operation = "operator"
                case springGateOrdinal
                case springGateMonth
                case springGateDay
                case status
            }
        }

        let v32: Rule
        let v33Candidate: V33Candidate
        let operative: Rule

        enum CodingKeys: String, CodingKey {
            case v32 = "v3.2"
            case v33Candidate = "v3.3Candidate"
            case operative
        }
    }

    let version: String
    let boundary: Boundary
    let enactmentBoundary: EnactmentBoundary
    let ordinaryCalendar: OrdinaryCalendar
    let canonicalCycle: CanonicalCycle
    let reconciliation: Reconciliation
    let gates: Gates
    let referenceRules: ReferenceRules
    let observances: [Observance]
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
        let reconciliation = spec.reconciliation
        let gates = spec.gates
        let enactment = spec.enactmentBoundary
        let cycle = spec.canonicalCycle

        guard
            spec.version == supportedVersion,
            spec.boundary.apparentHorizonZenithDegrees.isFinite,
            enactment.status == "annual-cycle-ratified",
            enactment.lawDoesNotSupplyValues == false,
            Set(enactment.requiredForFinitePublication) == Set([
                "referencePoint",
                "publicationAuthority"
            ]),
            calendar.baseYearDays == 364,
            calendar.weekDays == 7,
            calendar.monthLengths == [
                31, 28, 31, 30, 31, 30,
                31, 31, 30, 31, 30, 30
            ],
            calendar.monthLengths.reduce(0, +) == 364,
            calendar.quarterDays == 91,
            calendar.quarters == 4,
            calendar.lastCommonMonth == 12,
            calendar.lastCommonDay == 30,
            calendar.december31Exists == false,
            cycle.firstYearLabel == 2026,
            cycle.firstOpeningCivilDate == "2026-01-01",
            cycle.day001Weekday == "Thursday",
            cycle.yearCount == 50,
            cycle.totalDays == 18_200,
            cycle.transition == "12-30->next-year-01-01",
            reconciliation.namespace == "prohibited",
            reconciliation.inheritsOrdinaryFields == false,
            reconciliation.allowedDays == [0],
            reconciliation.addressPattern == nil,
            gates.phaseLengths.reduce(0, +) == calendar.baseYearDays,
            gates.gateSequence.count == gates.phaseLengths.count,
            gates.pairedGateCount == 6,
            gates.role == "enochic-seasonal-witness-layer",
            spec.referenceRules.operative.operation == "Fixed364",
            spec.referenceRules.operative.status == "ratified",
            spec.observances.allSatisfy({ observance in
                guard (1...12).contains(observance.month) else {
                    return false
                }
                let monthLength = calendar.monthLengths[observance.month - 1]
                guard (1...monthLength).contains(observance.day) else {
                    return false
                }
                if let endMonth = observance.endMonth,
                   let endDay = observance.endDay {
                    guard (1...12).contains(endMonth) else {
                        return false
                    }
                    return (1...calendar.monthLengths[endMonth - 1])
                        .contains(endDay)
                }
                return observance.endMonth == nil && observance.endDay == nil
            })
        else { return false }

        return true
    }
}
