import Foundation

struct LunarPhaseState: Equatable {
    let ageDays: Double
    let illuminationFraction: Double
    let isWaxing: Bool
    let phaseName: String
    let evidenceLabel: String

    var illuminationPercent: Int {
        Int((illuminationFraction * 100.0).rounded())
    }
}

enum LunarPhaseCalculator {
    // Deterministic mean-lunation witness. This does not mutate the 364-day grid.
    // Reference new moon: 2000-01-06 18:14 UTC.
    // Mean synodic month: 29.530588853 days.
    static let synodicMonthDays = 29.530588853
    private static let referenceNewMoon = Date(timeIntervalSince1970: 947182440)

    static func state(at instant: Date) -> LunarPhaseState {
        let elapsedDays = instant.timeIntervalSince(referenceNewMoon) / 86_400.0
        var age = elapsedDays.truncatingRemainder(dividingBy: synodicMonthDays)
        if age < 0 { age += synodicMonthDays }

        let angle = 2.0 * Double.pi * (age / synodicMonthDays)
        let illumination = 0.5 * (1.0 - cos(angle))
        let waxing = age < synodicMonthDays / 2.0

        return LunarPhaseState(
            ageDays: age,
            illuminationFraction: illumination,
            isWaxing: waxing,
            phaseName: phaseName(ageDays: age),
            evidenceLabel: "MEAN LUNATION · WITNESS ONLY"
        )
    }

    private static func phaseName(ageDays: Double) -> String {
        let eighth = synodicMonthDays / 8.0
        switch ageDays {
        case 0..<eighth / 2.0:
            return "NEW MOON"
        case ..<(eighth * 1.5):
            return "WAXING CRESCENT"
        case ..<(eighth * 2.5):
            return "FIRST QUARTER"
        case ..<(eighth * 3.5):
            return "WAXING GIBBOUS"
        case ..<(eighth * 4.5):
            return "FULL MOON"
        case ..<(eighth * 5.5):
            return "WANING GIBBOUS"
        case ..<(eighth * 6.5):
            return "LAST QUARTER"
        case ..<(eighth * 7.5):
            return "WANING CRESCENT"
        default:
            return "NEW MOON"
        }
    }
}
