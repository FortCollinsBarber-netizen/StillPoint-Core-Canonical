import Foundation

/// Energy and permission boundary for the initial immutable Ground Zero fix.
/// A failed attempt can be retried on a later foreground activation; it never
/// silently promotes a low-accuracy or simulated observation to Ground Zero.
enum GroundZeroSamplingPolicy {
    static let maximumDurationSeconds: TimeInterval = 60

    static func shouldBegin(
        sceneActive: Bool,
        authorized: Bool,
        hasGroundZero: Bool,
        isSampling: Bool
    ) -> Bool {
        sceneActive && authorized && !hasGroundZero && !isSampling
    }

    static func shouldContinue(
        startedAt: Date,
        now: Date,
        authorized: Bool,
        hasGroundZero: Bool
    ) -> Bool {
        let elapsed = now.timeIntervalSince(startedAt)
        return authorized
            && !hasGroundZero
            && elapsed >= 0
            && elapsed < maximumDurationSeconds
    }
}
