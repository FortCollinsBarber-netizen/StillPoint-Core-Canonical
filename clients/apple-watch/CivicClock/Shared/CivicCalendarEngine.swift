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

private struct WeeklyProtectedTimeState {
    let isSabbath: Bool
    let isLordsDay: Bool
    let isStillPoint: Bool
    let nextBoundary: Date?
    let nextBoundaryLabel: String?
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
                isLordsDay: false,
                isStillPoint: false,
                previousBoundary: pair.previous,
                nextBoundary: pair.next,
                boundaryStatus: "SUN BOUNDARY UNAVAILABLE",
                nextProtectedBoundary: nil,
                nextProtectedBoundaryLabel: nil,
                commonCalendarLabel: "CALENDAR",
                commonCalendarDetail: "FALLBACK RULE NOT ENACTED"
            )
        }

        // A named weekday begins at the previous evening.
        // Friday sunset opens Saturday / Sabbath.
        // Saturday sunset opens Sunday / Lord's Day.
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

        let weekly = weeklyProtectedTimeState(
            now: now,
            namedCivilDate: namedCivilDate,
            weekday: weekday,
            latitude: latitude,
            longitude: longitude,
            nextSunset: next,
            calendar: calendar
        )

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
            isSabbath: weekly.isSabbath,
            isLordsDay: weekly.isLordsDay,
            isStillPoint: weekly.isStillPoint,
            previousBoundary: previous,
            nextBoundary: next,
            boundaryStatus: "NEXT SUNDOWN",
            nextProtectedBoundary: weekly.nextBoundary,
            nextProtectedBoundaryLabel: weekly.nextBoundaryLabel,
            commonCalendarLabel: annual.label,
            commonCalendarDetail: annual.detail
        )
    }

    private static func weeklyProtectedTimeState(
        now: Date,
        namedCivilDate: Date,
        weekday: Int,
        latitude: Double,
        longitude: Double,
        nextSunset: Date,
        calendar: Calendar
    ) -> WeeklyProtectedTimeState {
        // Gregorian Calendar weekday numbering: Sunday=1 ... Saturday=7.
        if weekday == 7 {
            // Friday sunset -> Saturday sunset.
            return WeeklyProtectedTimeState(
                isSabbath: true,
                isLordsDay: false,
                isStillPoint: true,
                nextBoundary: nextSunset,
                nextBoundaryLabel: "SABBATH ENDS · LORD'S DAY BEGINS"
            )
        }

        if weekday == 1 {
            // Saturday sunset -> Sunday sunset is Lord's Day.
            // StillPoint closes earlier, exactly at Sunday apparent sunrise.
            let sunday = calendar.startOfDay(for: namedCivilDate)
            let sunrise = SolarBoundaryCalculator.sunrise(
                on: sunday,
                latitude: latitude,
                longitude: longitude,
                calendar: calendar
            )

            if let sunrise, now < sunrise {
                return WeeklyProtectedTimeState(
                    isSabbath: false,
                    isLordsDay: true,
                    isStillPoint: true,
                    nextBoundary: sunrise,
                    nextBoundaryLabel: "STILLPOINT RELEASE · SUNDAY SUNRISE"
                )
            }

            return WeeklyProtectedTimeState(
                isSabbath: false,
                isLordsDay: true,
                isStillPoint: false,
                nextBoundary: nextSunset,
                nextBoundaryLabel: "LORD'S DAY ENDS · SUNDAY SUNSET"
            )
        }

        return WeeklyProtectedTimeState(
            isSabbath: false,
            isLordsDay: false,
            isStillPoint: false,
            nextBoundary: nil,
            nextBoundaryLabel: nil
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

            guard boundaryOffset >= 0, boundaryOffset < legalLength else { continue }

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

            if boundaryOffset >= 364 {
                let reconciliationDay = boundaryOffset - 364 + 1
                return (
                    "RECONCILIATION",
                    "R\(reconciliationDay) · YEAR \(current.year) COMPLETE"
                )
            }

            let day = boundaryOffset + 1
            let week = ((day - 1) / 7) + 1
            let dayInWeek = ((day - 1) % 7) + 1
            let season = ((day - 1) / 91) + 1
            return (
                "YEAR \(current.year) · DAY \(String(format: "%03d", day))",
                "S\(season) · W\(String(format: "%02d", week)) · D\(dayInWeek)"
            )
        }

        return ("COMMON CALENDAR", "OUTSIDE PUBLISHED TABLE")
    }
}
