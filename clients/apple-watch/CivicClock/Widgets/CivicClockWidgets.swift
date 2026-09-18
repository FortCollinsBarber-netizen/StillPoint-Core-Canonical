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
                    publishedCalendar: PublishedCalendarLoader.load()
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
                Text(entry.snapshot.isSabbath ? "SAB" : shortDay)
                    .font(.caption2.weight(.bold))
                if let next = entry.snapshot.nextBoundary {
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
                    if entry.snapshot.isSabbath {
                        Text("• SABBATH")
                            .font(.caption2.weight(.bold))
                    }
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
            Text(entry.snapshot.namedDay)
        }
    }

    private var shortDay: String {
        String(entry.snapshot.namedDay.prefix(3))
    }

    private var inlineText: String {
        if let next = entry.snapshot.nextBoundary {
            return "\(shortDay) · sundown \(next.formatted(date: .omitted, time: .shortened))"
        }
        return "\(shortDay) · sun boundary unavailable"
    }

    private var rectangularBoundary: String {
        if let next = entry.snapshot.nextBoundary {
            return "Sundown \(next.formatted(date: .omitted, time: .shortened))"
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
        .description("Common-calendar day, Sabbath, and the next local sundown.")
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
