import Foundation

struct PublishedCivicYear: Codable, Equatable {
    let year: Int
    // Civil date whose local sunset opens this year, YYYY-MM-DD.
    let openingCivilDate: String
    // Mature StillPoint model: the ordinary year is 364 days.
    // A transition may carry one seven-day Reconciliation interval.
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
        let namedCivilDate = calendar.date(
            byAdding: .day,
            value: 1,
            to: calendar.startOfDay(for: previous)
        )!
        let weekday = calendar.component(.weekday, from: namedCivilDate)
        let formatter = DateFormatter()
        formatter.calendar = calendar
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = calendar.timeZone
        let weekdayName = formatter.weekdaySymbols[weekday - 1]
        let isSabbath = weekday == 7 // Saturday in Gregorian weekday numbering.

        let annual = annualLabel(
            now: now,
            previousBoundary: previous,
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
        previousBoundary: Date,
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
        formatter.isLenient = false

        let sorted = publishedCalendar.years.sorted { $0.year < $1.year }
        let currentBoundaryDay = calendar.startOfDay(for: previousBoundary)

        for index in sorted.indices {
            let current = sorted[index]

            // Fail closed if a published row tries to invent a non-week correction.
            guard current.reconciliationDaysAfterCompletion == 0
                    || current.reconciliationDaysAfterCompletion == 7
            else { continue }

            guard
                let openingDay = formatter.date(from: current.openingCivilDate),
                let opening = SolarBoundaryCalculator.sunset(
                    on: openingDay,
                    latitude: latitude,
                    longitude: longitude,
                    calendar: calendar
                )
            else { continue }

            guard now >= opening else { continue }

            let openingBoundaryDay = calendar.startOfDay(for: openingDay)
            guard let boundaryOffset = calendar.dateComponents(
                [.day],
                from: openingBoundaryDay,
                to: currentBoundaryDay
            ).day else { continue }

            let legalLength = 364 + current.reconciliationDaysAfterCompletion

            // A published year's authority expires at its declared final dusk.
            guard boundaryOffset >= 0, boundaryOffset < legalLength else { continue }

            // If the next row exists, it must agree with the current row's
            // declared 364/371-boundary length. Inconsistent tables fail closed.
            if sorted.indices.contains(index + 1) {
                let next = sorted[index + 1]
                guard
                    let nextOpeningDay = formatter.date(from: next.openingCivilDate),
                    let publishedSpan = calendar.dateComponents(
                        [.day],
                        from: openingBoundaryDay,
                        to: calendar.startOfDay(for: nextOpeningDay)
                    ).day,
                    publishedSpan == legalLength,
                    let nextOpening = SolarBoundaryCalculator.sunset(
                        on: nextOpeningDay,
                        latitude: latitude,
                        longitude: longitude,
                        calendar: calendar
                    ),
                    now < nextOpening
                else { continue }
            }

            let yearShape = legalLength == 371 ? "53W" : "52W"

            if boundaryOffset >= 364 {
                let reconciliationDay = boundaryOffset - 364 + 1
                return (
                    "RECONCILIATION",
                    "R\(reconciliationDay) · YEAR \(current.year) COMPLETE · \(yearShape)"
                )
            }

            let day = boundaryOffset + 1
            let week = ((day - 1) / 7) + 1
            let dayInWeek = ((day - 1) % 7) + 1
            let season = ((day - 1) / 91) + 1
            return (
                "YEAR \(current.year) · DAY \(String(format: "%03d", day))",
                "S\(season) · W\(String(format: "%02d", week)) · D\(dayInWeek) · \(yearShape)"
            )
        }

        return ("COMMON CALENDAR", "OUTSIDE PUBLISHED TABLE")
    }
}
