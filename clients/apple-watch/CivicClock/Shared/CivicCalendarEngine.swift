import Foundation

struct PublishedCivicYear: Codable, Equatable {
    let year: Int
    // Civil date whose local sunset opens this year, YYYY-MM-DD.
    let openingCivilDate: String
    // Mature StillPoint model: the ordinary year is 364 days.
    // A transition may carry a seven-day Reconciliation interval before next opening.
    let reconciliationDaysAfterCompletion: Int
}

struct PublishedCivicCalendar: Codable, Equatable {
    let version: String
    let years: [PublishedCivicYear]
}

enum CivicCalendarEngine {
    static func snapshot(
        now: Date,
        latitude: Double,
        longitude: Double,
        publishedCalendar: PublishedCivicCalendar? = nil,
        calendar inputCalendar: Calendar = .current
    ) -> CivicClockSnapshot {
        var calendar = inputCalendar
        calendar.locale = Locale(identifier: "en_US_POSIX")

        let pair = SolarBoundaryCalculator.previousAndNextSunset(
            around: now,
            latitude: latitude,
            longitude: longitude,
            calendar: calendar
        )

        guard let previous = pair.previous, let next = pair.next else {
            return CivicClockSnapshot(
                generatedAt: now,
                namedDay: "COMMON DAY",
                weekdayNumber: 0,
                isSabbath: false,
                previousBoundary: pair.previous,
                nextBoundary: pair.next,
                boundaryStatus: "SUN BOUNDARY UNAVAILABLE",
                commonCalendarLabel: "CALENDAR",
                commonCalendarDetail: "FALLBACK RULE NOT ENACTED"
            )
        }

        // A named weekday begins at the previous evening.
        // Example: Friday sunset opens Saturday / Sabbath.
        let namedCivilDate = calendar.date(byAdding: .day, value: 1, to: calendar.startOfDay(for: previous))!
        let weekday = calendar.component(.weekday, from: namedCivilDate)
        let formatter = DateFormatter()
        formatter.calendar = calendar
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = calendar.timeZone
        let weekdayName = formatter.weekdaySymbols[weekday - 1]
        let isSabbath = weekday == 7 // Saturday in Gregorian Calendar weekday numbering.

        let annual = annualLabel(
            now: now,
            latitude: latitude,
            longitude: longitude,
            publishedCalendar: publishedCalendar,
            calendar: calendar
        )

        return CivicClockSnapshot(
            generatedAt: now,
            namedDay: weekdayName.uppercased(),
            weekdayNumber: weekday,
            isSabbath: isSabbath,
            previousBoundary: previous,
            nextBoundary: next,
            boundaryStatus: "NEXT SUNDOWN",
            commonCalendarLabel: annual.label,
            commonCalendarDetail: annual.detail
        )
    }

    private static func annualLabel(
        now: Date,
        latitude: Double,
        longitude: Double,
        publishedCalendar: PublishedCivicCalendar?,
        calendar: Calendar
    ) -> (label: String, detail: String) {
        guard let publishedCalendar else {
            return ("COMMON CALENDAR", "ANNUAL TABLE PENDING")
        }

        let formatter = DateFormatter()
        formatter.calendar = calendar
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = calendar.timeZone
        formatter.dateFormat = "yyyy-MM-dd"

        let sorted = publishedCalendar.years.sorted { $0.year < $1.year }

        for index in sorted.indices {
            let current = sorted[index]
            guard
                let openingDay = formatter.date(from: current.openingCivilDate),
                let opening = SolarBoundaryCalculator.sunset(
                    on: openingDay,
                    latitude: latitude,
                    longitude: longitude,
                    calendar: calendar
                )
            else { continue }

            let nextOpening: Date?
            if sorted.indices.contains(index + 1),
               let nextDay = formatter.date(from: sorted[index + 1].openingCivilDate) {
                nextOpening = SolarBoundaryCalculator.sunset(
                    on: nextDay,
                    latitude: latitude,
                    longitude: longitude,
                    calendar: calendar
                )
            } else {
                nextOpening = nil
            }

            let containsNow = now >= opening && (nextOpening == nil || now < nextOpening!)
            guard containsNow else { continue }

            let completedOrdinaryBoundary = calendar.date(byAdding: .day, value: 364, to: opening)!

            if now >= completedOrdinaryBoundary && current.reconciliationDaysAfterCompletion == 7 {
                let elapsed = max(0, calendar.dateComponents([.day], from: completedOrdinaryBoundary, to: now).day ?? 0)
                let r = min(7, elapsed + 1)
                return ("RECONCILIATION", "R\(r) · YEAR \(current.year) COMPLETE")
            }

            let day = max(1, min(364, (calendar.dateComponents([.day], from: opening, to: now).day ?? 0) + 1))
            let week = ((day - 1) / 7) + 1
            let dayInWeek = ((day - 1) % 7) + 1
            let quarter = ((day - 1) / 91) + 1
            return (
                "YEAR \(current.year) · DAY \(String(format: "%03d", day))",
                "Q\(quarter) · W\(String(format: "%02d", week)) · D\(dayInWeek)"
            )
        }

        return ("COMMON CALENDAR", "OUTSIDE PUBLISHED TABLE")
    }
}
