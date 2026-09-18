import SwiftUI
import WidgetKit

struct CivicClockEntry: TimelineEntry {
    let date: Date
    let snapshot: CivicClockSnapshot
}

struct CivicClockProvider: TimelineProvider {
    func placeholder(in context: Context) -> CivicClockEntry {
        CivicClockEntry(date: .now, snapshot: .unavailable)
    }

    func getSnapshot(in context: Context, completion: @escaping (CivicClockEntry) -> Void) {
        completion(CivicClockEntry(
            date: .now,
            snapshot: CivicClockSharedStore.loadSnapshot() ?? .unavailable
        ))
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<CivicClockEntry>) -> Void) {
        let now = Date()
        let cached = CivicClockSharedStore.loadSnapshot() ?? .unavailable

        var entries: [CivicClockEntry] = []
        for minute in stride(from: 0, through: 120, by: 15) {
            let date = Calendar.current.date(byAdding: .minute, value: minute, to: now) ?? now
            var snapshot = cached

            if let coordinate = CivicClockSharedStore.loadCoordinate() {
                snapshot = CivicCalendarEngine.snapshot(
                    now: date,
                    latitude: coordinate.latitude,
                    longitude: coordinate.longitude,
                    publishedCalendar: PublishedCalendarLoader.load(),
                    pilotProfile: PilotTemporalLoader.load()
                )
            }

            entries.append(CivicClockEntry(date: date, snapshot: snapshot))
        }

        completion(Timeline(entries: entries, policy: .atEnd))
    }
}

struct CivicClockComplicationView: View {
    @Environment(\.widgetFamily) private var family
    let entry: CivicClockEntry

    var body: some View {
        switch family {
        case .accessoryCircular:
            VStack(spacing: 0) {
                Text(circularState)
                    .font(.caption2.weight(.bold))
                if let next = effectiveNextBoundary {
                    Text(next, style: .time)
                        .font(.system(size: 9, weight: .medium))
                        .monospacedDigit()
                } else {
                    Text("SUN")
                        .font(.system(size: 9, weight: .medium))
                }
            }
            .containerBackground(.clear, for: .widget)

        case .accessoryRectangular:
            VStack(alignment: .leading, spacing: 1) {
                HStack {
                    Text(entry.snapshot.namedDay)
                        .font(.caption2.weight(.bold))
                    Text("• \(stateLabel)")
                        .font(.caption2.weight(.bold))
                }

                Text(entry.snapshot.commonCalendarLabel)
                    .font(.caption.weight(.semibold))
                    .lineLimit(1)

                Text(rectangularBoundary)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
            .containerBackground(.clear, for: .widget)

        case .accessoryInline:
            Text(inlineText)

        default:
            Text(stateLabel)
        }
    }

    private var effectiveNextBoundary: Date? {
        entry.snapshot.nextProtectedBoundary ?? entry.snapshot.nextBoundary
    }

    private var circularState: String {
        if entry.snapshot.isStillPoint { return "SP" }
        if entry.snapshot.isLordsDay { return "LD" }
        if entry.snapshot.isSabbath { return "SAB" }
        return String(entry.snapshot.namedDay.prefix(3))
    }

    private var stateLabel: String {
        if entry.snapshot.isSabbath && entry.snapshot.isStillPoint {
            return "SABBATH · STILLPOINT"
        }
        if entry.snapshot.isLordsDay && entry.snapshot.isStillPoint {
            return "LORD'S DAY · STILLPOINT"
        }
        if entry.snapshot.isLordsDay {
            return "LORD'S DAY"
        }
        return entry.snapshot.namedDay
    }

    private var inlineText: String {
        if let next = effectiveNextBoundary {
            let label = entry.snapshot.nextProtectedBoundaryLabel ?? "sundown"
            return "\(stateLabel) · \(label.lowercased()) \(next.formatted(date: .omitted, time: .shortened))"
        }
        return "\(stateLabel) · horizon boundary unavailable"
    }

    private var rectangularBoundary: String {
        if let next = effectiveNextBoundary {
            let label = entry.snapshot.nextProtectedBoundaryLabel ?? "Sundown"
            return "\(label) · \(next.formatted(date: .omitted, time: .shortened))"
        }
        return entry.snapshot.boundaryStatus
    }
}

struct CivicClockWidget: Widget {
    let kind = "CivicClockWidget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: CivicClockProvider()) { entry in
            CivicClockComplicationView(entry: entry)
        }
        .configurationDisplayName("Civic Clock")
        .description("Common Calendar, Sabbath, Lord's Day, StillPoint, and local horizon boundaries.")
        .supportedFamilies([
            .accessoryCircular,
            .accessoryRectangular,
            .accessoryInline
        ])
    }
}

@main
struct CivicClockWidgetBundle: WidgetBundle {
    var body: some Widget {
        CivicClockWidget()
    }
}
