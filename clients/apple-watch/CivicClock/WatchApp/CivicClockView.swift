import CoreLocation
import SwiftUI

struct CivicClockView: View {
    @EnvironmentObject private var locationService: LocationService

    var body: some View {
        TimelineView(.periodic(from: .now, by: 30)) { timeline in
            let now = timeline.date
            let snapshot = makeSnapshot(now: now)

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

                    if locationService.coordinate == nil {
                        Text("LOCATION NEEDED FOR LOCAL HORIZON BOUNDARIES")
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
