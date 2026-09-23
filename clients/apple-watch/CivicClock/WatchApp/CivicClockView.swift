import CoreLocation
import Foundation
import SwiftUI

struct CivicClockView: View {
    @EnvironmentObject private var locationService: LocationService

    var body: some View {
        TimelineView(.periodic(from: .now, by: 30)) { timeline in
            let now = timeline.date
            let snapshot = makeSnapshot(now: now)
            let lunar = LunarPhaseCalculator.state(at: now)

            ScrollView {
                VStack(spacing: 7) {
                    Text("CIVIC")
                        .font(.system(size: 9, weight: .bold))
                        .tracking(1.5)
                        .foregroundStyle(.secondary)

                    Text(now, style: .time)
                        .font(.system(size: 34, weight: .semibold, design: .rounded))
                        .monospacedDigit()
                        .accessibilityLabel("Civil time")

                    Text(now, format: .dateTime.weekday(.abbreviated).month(.abbreviated).day())
                        .font(.caption2)
                        .foregroundStyle(.secondary)

                    Text(snapshot.namedDay)
                        .font(.caption2.weight(.bold))
                        .tracking(1.4)

                    if snapshot.isSabbath {
                        Text("SABBATH")
                            .font(.headline)
                    }

                    if snapshot.isLordsDay {
                        Text("LORD'S DAY")
                            .font(.headline)
                    }

                    if snapshot.isStillPoint {
                        Text("STILLPOINT")
                            .font(.caption.weight(.bold))
                            .tracking(1.2)
                    }

                    Divider()

                    VStack(spacing: 2) {
                        Text("COMMON · \(snapshot.commonClockLabel)")
                            .font(.headline.monospacedDigit())

                        Text(snapshot.commonCalendarLabel)
                            .font(.caption.weight(.semibold))
                            .multilineTextAlignment(.center)

                        Text(snapshot.commonCalendarDetail)
                            .font(.caption2)
                            .multilineTextAlignment(.center)
                            .foregroundStyle(.secondary)

                        if !snapshot.observanceLabel.isEmpty {
                            Text(snapshot.observanceLabel)
                                .font(.caption2.weight(.semibold))
                                .multilineTextAlignment(.center)
                        }

                        if !snapshot.jubileeLabel.isEmpty {
                            Text(snapshot.jubileeLabel)
                                .font(.system(size: 9, weight: .medium))
                                .multilineTextAlignment(.center)
                                .foregroundStyle(.secondary)
                        }
                    }

                    Divider()

                    VStack(spacing: 2) {
                        Text("\(lunar.phaseName) · \(lunar.illuminationPercent)%")
                            .font(.caption.weight(.semibold))
                        Text(lunar.isWaxing ? "WAXING" : "WANING")
                            .font(.system(size: 9, weight: .bold))
                            .tracking(1.0)
                        Text(String(format: "LUNAR AGE %.2f DAYS", lunar.ageDays))
                            .font(.system(size: 8))
                            .foregroundStyle(.secondary)
                        Text(lunar.evidenceLabel)
                            .font(.system(size: 7))
                            .foregroundStyle(.tertiary)
                    }

                    if let protectedBoundary = snapshot.nextProtectedBoundary {
                        Divider()

                        Text(snapshot.nextProtectedBoundaryLabel ?? "NEXT HORIZON BOUNDARY")
                            .font(.caption2.weight(.bold))
                            .multilineTextAlignment(.center)
                            .foregroundStyle(.secondary)

                        Text(protectedBoundary, style: .time)
                            .font(.title3.monospacedDigit())

                        Text(protectedBoundary, style: .relative)
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    } else if let next = snapshot.nextBoundary {
                        Divider()

                        Text(snapshot.boundaryStatus)
                            .font(.caption2.weight(.bold))
                            .foregroundStyle(.secondary)

                        Text(next, style: .time)
                            .font(.title3.monospacedDigit())

                        Text(next, style: .relative)
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }

                    Divider()

                    if let groundZero = locationService.groundZero {
                        Text("GROUND ZERO LOCKED")
                            .font(.system(size: 9, weight: .bold))
                            .tracking(1.0)
                        Text(
                            String(
                                format: "%.6f, %.6f · ±%.0f m",
                                groundZero.latitude,
                                groundZero.longitude,
                                groundZero.horizontalAccuracyMeters
                            )
                        )
                        .font(.system(size: 8, design: .monospaced))
                        .multilineTextAlignment(.center)

                        Text("WGS84 · CORE LOCATION · FULL ACCURACY")
                            .font(.system(size: 7, weight: .medium))
                            .multilineTextAlignment(.center)
                            .foregroundStyle(.secondary)

                        if let altitude = groundZero.altitudeMeters {
                            Text(String(format: "ALT %.1f m", altitude))
                                .font(.system(size: 7, design: .monospaced))
                                .foregroundStyle(.secondary)
                        }

                        Text(groundZero.capturedAt, style: .date)
                            .font(.system(size: 8))
                            .foregroundStyle(.secondary)

                        Text(groundZero.capturedAt, style: .time)
                            .font(.system(size: 8, design: .monospaced))
                            .foregroundStyle(.secondary)

                        Text(GroundZeroBindingPayload.schemaID)
                            .font(.system(size: 6))
                            .multilineTextAlignment(.center)
                            .foregroundStyle(.tertiary)
                    } else if locationService.coordinate == nil {
                        Text("LOCATION NEEDED FOR LOCAL HORIZON BOUNDARIES")
                            .font(.caption2)
                            .multilineTextAlignment(.center)
                            .foregroundStyle(.secondary)
                    } else {
                        Text("MEASURING GROUND ZERO · NEED ≤25 m FIX")
                            .font(.caption2)
                            .multilineTextAlignment(.center)
                            .foregroundStyle(.secondary)
                    }

                    Text("CLOCK TRANSLATES · HORIZON BOUNDARY COUNTS")
                        .font(.system(size: 8, weight: .medium))
                        .multilineTextAlignment(.center)
                        .foregroundStyle(.tertiary)
                        .padding(.top, 3)
                }
                .padding(.horizontal, 6)
            }
            .onAppear {
                CivicClockSharedStore.save(snapshot)
            }
            .onChange(of: snapshot) { _, newValue in
                CivicClockSharedStore.save(newValue)
            }
        }
    }

    private func makeSnapshot(now: Date) -> CivicClockSnapshot {
        guard let coordinate = locationService.coordinate else {
            return CivicClockSharedStore.loadSnapshot() ?? .unavailable
        }

        return CivicCalendarEngine.snapshot(
            now: now,
            latitude: coordinate.latitude,
            longitude: coordinate.longitude,
            publishedCalendar: PublishedCalendarLoader.load(policy: .enactedStillPoint),
            population: CalendarPopulationLoader.load()
        )
    }
}
