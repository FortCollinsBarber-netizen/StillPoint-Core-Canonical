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
    }

    struct Reconciliation: Codable, Equatable {
        let addressPattern: String
        let allowedDays: [Int]
        let inheritsOrdinaryFields: Bool
        let namespace: String
    }

    struct Gates: Codable, Equatable {
        let gateSequence: [Int]
        let pairedGateCount: Int
        let phaseLengths: [Int]
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

        enum CodingKeys: String, CodingKey {
            case v32 = "v3.2"
            case v33Candidate = "v3.3Candidate"
        }
    }

    let version: String
    let boundary: Boundary
    let enactmentBoundary: EnactmentBoundary
    let ordinaryCalendar: OrdinaryCalendar
    let reconciliation: Reconciliation
    let gates: Gates
    let referenceRules: ReferenceRules
}

enum CalendarCoreSpecLoader {
    static let supportedVersion = "stillpoint-calendar-core-spec-v1"

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
        let v33 = spec.referenceRules.v33Candidate

        guard
            spec.version == supportedVersion,
            spec.boundary.apparentHorizonZenithDegrees.isFinite,
            enactment.status == "external-unresolved",
            enactment.lawDoesNotSupplyValues,
            Set(enactment.requiredForFinitePublication) == Set([
                "firstOpening",
                "referencePoint",
                "ephemerisEvidence",
                "publicationAuthority"
            ]),
            calendar.baseYearDays > 0,
            calendar.weekDays > 0,
            calendar.quarterDays > 0,
            calendar.quarters > 0,
            calendar.monthLengths.reduce(0, +) == calendar.baseYearDays,
            calendar.quarterDays * calendar.quarters == calendar.baseYearDays,
            calendar.baseYearDays % calendar.weekDays == 0,
            reconciliation.namespace == "interannual",
            reconciliation.inheritsOrdinaryFields == false,
            reconciliation.allowedDays.contains(0),
            reconciliation.allowedDays.allSatisfy({
                $0 >= 0 && $0 % calendar.weekDays == 0
            }),
            gates.phaseLengths.reduce(0, +) == calendar.baseYearDays,
            gates.gateSequence.count == gates.phaseLengths.count,
            gates.pairedGateCount > 0,
            !spec.referenceRules.v32.operation.isEmpty,
            !spec.referenceRules.v32.status.isEmpty,
            !v33.operation.isEmpty,
            !v33.status.isEmpty,
            (1...calendar.baseYearDays).contains(v33.springGateOrdinal),
            (1...12).contains(v33.springGateMonth),
            v33.springGateDay > 0
        else { return false }

        return true
    }
}
