import Foundation

private struct WeeklyProtectedTimeState {
    let isSabbath: Bool
    let isLordsDay: Bool
    let isStillPoint: Bool
    let nextBoundary: Date?
    let nextBoundaryLabel: String?
}

private struct AnnualCalendarState {
    let label: String
    let detail: String
    let observance: String
    let jubilee: String
}

enum CivicCalendarEngine {
    static func snapshot(
        now: Date,
        latitude: Double,
        longitude: Double,
        publishedCalendar: PublishedCivicCalendar? = nil,
        calendarCoreSpec: CalendarCoreSpec? = CalendarCoreSpecLoader.load(),
        calendar inputCalendar: Calendar = .current
    ) -> CivicClockSnapshot {
        var calendar = inputCalendar
        calendar.locale = Locale(identifier: "en_US_POSIX")
        _ = publishedCalendar

        let commonClock = commonClockLabel(
            now: now,
            calendar: calendar
        )

        guard let spec = calendarCoreSpec else {
            return CivicClockSnapshot(
                generatedAt: now,
                namedDay: "COMMON DAY",
                weekdayNumber: 0,
                isSabbath: false,
                isLordsDay: false,
                isStillPoint: false,
                previousBoundary: nil,
                nextBoundary: nil,
                boundaryStatus: "CORE SPEC UNAVAILABLE",
                nextProtectedBoundary: nil,
                nextProtectedBoundaryLabel: nil,
                commonCalendarLabel: "CALENDAR",
                commonCalendarDetail: "CORE SPEC UNAVAILABLE",
                commonClockLabel: commonClock,
                observanceLabel: "",
                jubileeLabel: ""
            )
        }

        let pair = SolarBoundaryCalculator.previousAndNextSunset(
            around: now,
            latitude: latitude,
            longitude: longitude,
            calendar: calendar,
            spec: spec
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
                commonCalendarLabel: "COMMON CALENDAR",
                commonCalendarDetail: "HORIZON BOUNDARY UNAVAILABLE",
                commonClockLabel: commonClock,
                observanceLabel: "",
                jubileeLabel: ""
            )
        }

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
            spec: spec,
            calendar: calendar
        )

        let annual = annualState(
            previousBoundary: previous,
            spec: spec,
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
            commonCalendarDetail: annual.detail,
            commonClockLabel: commonClock,
            observanceLabel: annual.observance,
            jubileeLabel: annual.jubilee
        )
    }

    private static func commonClockLabel(
        now: Date,
        calendar: Calendar
    ) -> String {
        let zone = calendar.timeZone
        let legalOffset = zone.secondsFromGMT(for: now)
        let dstOffset = Int(zone.daylightSavingTimeOffset(for: now))
        let standardOffset = legalOffset - dstOffset

        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.timeZone = TimeZone(secondsFromGMT: standardOffset)
        formatter.dateFormat = "HH:mm"
        return formatter.string(from: now)
    }

    private static func weeklyProtectedTimeState(
        now: Date,
        namedCivilDate: Date,
        weekday: Int,
        latitude: Double,
        longitude: Double,
        nextSunset: Date,
        spec: CalendarCoreSpec,
        calendar: Calendar
    ) -> WeeklyProtectedTimeState {
        if weekday == 7 {
            return WeeklyProtectedTimeState(
                isSabbath: true,
                isLordsDay: false,
                isStillPoint: true,
                nextBoundary: nextSunset,
                nextBoundaryLabel: "SABBATH ENDS · LORD'S DAY BEGINS"
            )
        }

        if weekday == 1 {
            let sunday = calendar.startOfDay(for: namedCivilDate)
            let sunrise = SolarBoundaryCalculator.sunrise(
                on: sunday,
                latitude: latitude,
                longitude: longitude,
                calendar: calendar,
                spec: spec
            )

            if let sunrise, now < sunrise {
                return WeeklyProtectedTimeState(
                    isSabbath: false,
                    isLordsDay: true,
                    isStillPoint: true,
                    nextBoundary: sunrise,
                    nextBoundaryLabel:
                        "STILLPOINT RELEASE · SUNDAY SUNRISE"
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

    private static func annualState(
        previousBoundary: Date,
        spec: CalendarCoreSpec,
        calendar: Calendar
    ) -> AnnualCalendarState {
        let cycle = spec.canonicalCycle
        let baseYearDays = spec.ordinaryCalendar.baseYearDays

        let formatter = DateFormatter()
        formatter.calendar = calendar
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = calendar.timeZone
        formatter.dateFormat = "yyyy-MM-dd"
        formatter.isLenient = false

        guard let firstOpening = formatter.date(
            from: cycle.firstOpeningCivilDate
        ) else {
            return AnnualCalendarState(
                label: "COMMON CALENDAR",
                detail: "INVALID CANONICAL OPENING",
                observance: "",
                jubilee: ""
            )
        }

        let currentBoundaryDay = calendar.startOfDay(
            for: previousBoundary
        )
        let firstOpeningDay = calendar.startOfDay(
            for: firstOpening
        )
        guard let offset = calendar.dateComponents(
            [.day],
            from: firstOpeningDay,
            to: currentBoundaryDay
        ).day,
        offset >= 0,
        offset < cycle.totalDays else {
            return AnnualCalendarState(
                label: "COMMON CALENDAR",
                detail: "OUTSIDE RATIFIED 50-YEAR MAP",
                observance: "",
                jubilee: ""
            )
        }

        let yearOffset = offset / baseYearDays
        let ordinal = (offset % baseYearDays) + 1
        let year = cycle.firstYearLabel + yearOffset
        let week = ((ordinal - 1) / spec.ordinaryCalendar.weekDays) + 1
        let dayInWeek =
            ((ordinal - 1) % spec.ordinaryCalendar.weekDays) + 1
        let season = ((ordinal - 1) / spec.ordinaryCalendar.quarterDays) + 1
        let dayOfSeason =
            ((ordinal - 1) % spec.ordinaryCalendar.quarterDays) + 1

        guard let monthDay = monthDay(
            ordinal: ordinal,
            monthLengths: spec.ordinaryCalendar.monthLengths
        ) else {
            return AnnualCalendarState(
                label: "COMMON CALENDAR",
                detail: "INVALID COMMON DATE",
                observance: "",
                jubilee: ""
            )
        }

        let gate = gateForOrdinal(
            ordinal,
            phaseLengths: spec.gates.phaseLengths,
            gateSequence: spec.gates.gateSequence
        )

        let monthName = [
            "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
            "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"
        ][monthDay.month - 1]

        let names = spec.observances.compactMap { observance -> String? in
            guard let start = ordinalFor(
                month: observance.month,
                day: observance.day,
                monthLengths: spec.ordinaryCalendar.monthLengths
            ) else { return nil }

            let end: Int
            if let endMonth = observance.endMonth,
               let endDay = observance.endDay,
               let resolved = ordinalFor(
                    month: endMonth,
                    day: endDay,
                    monthLengths: spec.ordinaryCalendar.monthLengths
               ) {
                end = resolved
            } else {
                end = start
            }
            return (start...end).contains(ordinal)
                ? observance.name
                : nil
        }

        let jubileeYear = yearOffset + 1
        let isJubilee = jubileeYear == 50
        let isSabbatical =
            jubileeYear < 50 && jubileeYear % 7 == 0
        let isReleaseDay =
            isJubilee
            && monthDay.month == 7
            && monthDay.day == 10

        var jubileeText = "JUBILEE Y\(jubileeYear)/50"
        if isSabbatical {
            jubileeText += " · SABBATICAL"
        }
        if isJubilee {
            jubileeText = "JUBILEE YEAR 50"
        }
        if isReleaseDay {
            jubileeText += " · RELEASE"
        }

        let gateText = gate.map { "G\($0)" } ?? "G—"
        return AnnualCalendarState(
            label:
                "Y\(year) · \(monthName) \(String(format: "%02d", monthDay.day)) · DAY \(String(format: "%03d", ordinal))",
            detail:
                "W\(String(format: "%02d", week)) D\(dayInWeek) · S\(season).\(dayOfSeason) · \(gateText)",
            observance: names.joined(separator: " · "),
            jubilee: jubileeText
        )
    }

    private static func monthDay(
        ordinal: Int,
        monthLengths: [Int]
    ) -> (month: Int, day: Int)? {
        var remaining = ordinal
        for (index, length) in monthLengths.enumerated() {
            if remaining <= length {
                return (index + 1, remaining)
            }
            remaining -= length
        }
        return nil
    }

    private static func ordinalFor(
        month: Int,
        day: Int,
        monthLengths: [Int]
    ) -> Int? {
        guard
            (1...monthLengths.count).contains(month),
            (1...monthLengths[month - 1]).contains(day)
        else { return nil }
        return monthLengths.prefix(month - 1).reduce(0, +) + day
    }

    private static func gateForOrdinal(
        _ ordinal: Int,
        phaseLengths: [Int],
        gateSequence: [Int]
    ) -> Int? {
        var start = 1
        for index in phaseLengths.indices {
            let end = start + phaseLengths[index] - 1
            if (start...end).contains(ordinal) {
                return gateSequence[index]
            }
            start = end + 1
        }
        return nil
    }
}
