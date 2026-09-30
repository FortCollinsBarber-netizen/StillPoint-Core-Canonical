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
    let sourceRefs: [String]
    let weekdayName: String?
    let weekdayNumber: Int?
}

enum CivicCalendarEngine {
    static func snapshot(
        now: Date,
        latitude: Double,
        longitude: Double,
        publishedCalendar: PublishedCivicCalendar? = PublishedCalendarLoader.load(policy: .enactedStillPoint),
        population: CalendarPopulation? = CalendarPopulationLoader.load(),
        externalWitnesses: ExternalCalendarWitnessCatalog? =
            ExternalCalendarWitnessLoader.load(),
        calendarCoreSpec: CalendarCoreSpec? = CalendarCoreSpecLoader.load(),
        calendar inputCalendar: Calendar = .current
    ) -> CivicClockSnapshot {
        var calendar = permanentStandardCalendar(
            now: now,
            inputCalendar: inputCalendar
        )
        calendar.locale = Locale(identifier: "en_US_POSIX")

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
                commonClockLabel: commonClock,
                commonCalendarLabel: "COMMON CALENDAR",
                commonCalendarDetail: "CORE SPEC UNAVAILABLE",
                observanceLabel: "",
                jubileeLabel: "",
                sourceRefs: []
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
                commonClockLabel: commonClock,
                commonCalendarLabel: "COMMON CALENDAR",
                commonCalendarDetail: "HORIZON BOUNDARY UNAVAILABLE",
                observanceLabel: "",
                jubileeLabel: "",
                sourceRefs: []
            )
        }

        let commonCivilDay = calendar.startOfDay(for: now)
        let todaySunset = SolarBoundaryCalculator.sunset(
            on: commonCivilDay,
            latitude: latitude,
            longitude: longitude,
            calendar: calendar,
            spec: spec
        )
        let sacredCivilDay: Date
        if let todaySunset, now >= todaySunset {
            sacredCivilDay = calendar.date(
                byAdding: .day,
                value: 1,
                to: commonCivilDay
            )!
        } else {
            sacredCivilDay = commonCivilDay
        }

        let annual = annualState(
            civilInstant: now,
            publishedCalendar: publishedCalendar,
            population: population,
            spec: spec,
            calendar: calendar
        )
        let sacredDay = annualState(
            civilInstant: sacredCivilDay,
            publishedCalendar: publishedCalendar,
            population: population,
            spec: spec,
            calendar: calendar
        )

        let externalDate = externalProjectionDateLabel(
            now: now,
            calendar: calendar
        )
        let witnessEvents = externalWitnesses?.events(
            onExternalDate: externalDate
        ) ?? []
        let externalWitnessLabel = witnessEvents.map { event in
            event.begins_at == "sunset"
                ? "\(event.name) · SUNSET"
                : event.name
        }.joined(separator: " · ")

        var sourceRefs = annual.sourceRefs
        for event in witnessEvents {
            for ref in event.source_refs where !sourceRefs.contains(ref) {
                sourceRefs.append(ref)
            }
        }

        let localLight = SolarBoundaryCalculator.localLightObservation(
            around: now,
            latitude: latitude,
            longitude: longitude,
            calendar: calendar,
            spec: spec
        )

        let weekly = weeklyProtectedTimeState(
            now: now,
            sacredCivilDay: sacredCivilDay,
            weekdayName: sacredDay.weekdayName,
            latitude: latitude,
            longitude: longitude,
            nextSunset: next,
            spec: spec,
            calendar: calendar
        )

        return CivicClockSnapshot(
            generatedAt: now,
            namedDay: sacredDay.weekdayName?.uppercased() ?? "COMMON DAY",
            weekdayNumber: sacredDay.weekdayNumber ?? 0,
            isSabbath: weekly.isSabbath,
            isLordsDay: weekly.isLordsDay,
            isStillPoint: weekly.isStillPoint,
            previousBoundary: previous,
            nextBoundary: next,
            boundaryStatus: "NEXT SUNDOWN",
            nextProtectedBoundary: weekly.nextBoundary,
            nextProtectedBoundaryLabel: weekly.nextBoundaryLabel,
            commonClockLabel: commonClock,
            commonCalendarLabel: annual.label,
            commonCalendarDetail: annual.detail,
            observanceLabel: annual.observance,
            jubileeLabel: annual.jubilee,
            sourceRefs: sourceRefs,
            externalWitnessLabel: externalWitnessLabel.isEmpty
                ? nil
                : externalWitnessLabel,
            localLightPhase: localLight?.phase,
            civilDawn: localLight?.civilDawn,
            sunrise: localLight?.sunrise,
            sunset: localLight?.sunset,
            civilDusk: localLight?.civilDusk,
            nextLightEvent: localLight?.nextEvent,
            nextLightEventAt: localLight?.nextEventAt
        )
    }

    private static func externalProjectionDateLabel(
        now: Date,
        calendar: Calendar
    ) -> String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.calendar = calendar
        formatter.timeZone = calendar.timeZone
        formatter.dateFormat = "yyyy-MM-dd"
        formatter.isLenient = false
        return formatter.string(from: now)
    }

    private static func permanentStandardCalendar(
        now: Date,
        inputCalendar: Calendar
    ) -> Calendar {
        var calendar = inputCalendar
        let zone = inputCalendar.timeZone
        let legalOffset = zone.secondsFromGMT(for: now)
        let dstOffset = Int(zone.daylightSavingTimeOffset(for: now))
        let standardOffset = legalOffset - dstOffset
        calendar.timeZone = TimeZone(secondsFromGMT: standardOffset)!
        return calendar
    }

    private static func commonClockLabel(
        now: Date,
        calendar: Calendar
    ) -> String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.timeZone = calendar.timeZone
        formatter.dateFormat = "HH:mm"
        return formatter.string(from: now)
    }

    private static func weeklyProtectedTimeState(
        now: Date,
        sacredCivilDay: Date,
        weekdayName: String?,
        latitude: Double,
        longitude: Double,
        nextSunset: Date,
        spec: CalendarCoreSpec,
        calendar: Calendar
    ) -> WeeklyProtectedTimeState {
        if weekdayName == "Saturday" {
            return WeeklyProtectedTimeState(
                isSabbath: true,
                isLordsDay: false,
                isStillPoint: true,
                nextBoundary: nextSunset,
                nextBoundaryLabel: "SABBATH ENDS · LORD'S DAY BEGINS"
            )
        }

        if weekdayName == "Sunday" {
            let sunday = calendar.startOfDay(for: sacredCivilDay)
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
        civilInstant: Date,
        publishedCalendar: PublishedCivicCalendar?,
        population: CalendarPopulation?,
        spec: CalendarCoreSpec,
        calendar: Calendar
    ) -> AnnualCalendarState {
        guard
            let publishedCalendar,
            publishedCalendar.isValidatedForProjection
        else {
            return AnnualCalendarState(
                label: "COMMON CALENDAR",
                detail: "PUBLICATION UNAVAILABLE",
                observance: "",
                jubilee: "",
                sourceRefs: [],
                weekdayName: nil,
                weekdayNumber: nil
            )
        }

        let rows = publishedCalendar.years
        guard rows.count == 50 else {
            return AnnualCalendarState(
                label: "COMMON CALENDAR",
                detail: "50-YEAR PUBLICATION REQUIRED",
                observance: "",
                jubilee: "",
                sourceRefs: [],
                weekdayName: nil,
                weekdayNumber: nil
            )
        }

        let formatter = DateFormatter()
        formatter.calendar = calendar
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = calendar.timeZone
        formatter.dateFormat = "yyyy-MM-dd"
        formatter.isLenient = false

        let currentCivilDay = calendar.startOfDay(for: civilInstant)

        for index in rows.indices {
            let row = rows[index]
            guard
                let openingDay = formatter.date(from: row.openingCivilDate)
            else { continue }

            let openingBoundaryDay = calendar.startOfDay(for: openingDay)
            guard let boundaryOffset = calendar.dateComponents(
                [.day],
                from: openingBoundaryDay,
                to: currentCivilDay
            ).day,
            (0..<spec.ordinaryCalendar.baseYearDays).contains(boundaryOffset)
            else { continue }

            if rows.indices.contains(index + 1) {
                let next = rows[index + 1]
                guard
                    next.year == row.year + 1,
                    let nextOpening = formatter.date(from: next.openingCivilDate),
                    let span = calendar.dateComponents(
                        [.day],
                        from: openingBoundaryDay,
                        to: calendar.startOfDay(for: nextOpening)
                    ).day,
                    span == spec.ordinaryCalendar.baseYearDays
                else { continue }
            }

            let ordinal = boundaryOffset + 1
            guard let monthDay = monthDay(
                ordinal: ordinal,
                monthLengths: spec.ordinaryCalendar.monthLengths
            ) else { continue }

            let week =
                ((ordinal - 1) / spec.ordinaryCalendar.weekDays) + 1
            let dayInWeek =
                ((ordinal - 1) % spec.ordinaryCalendar.weekDays) + 1
            let quarter =
                ((ordinal - 1) / spec.ordinaryCalendar.quarterDays) + 1
            let dayOfQuarter =
                ((ordinal - 1) % spec.ordinaryCalendar.quarterDays) + 1

            let gate = gateForOrdinal(
                ordinal,
                population: population
            )

            let observances = population?.observances.filter { item in
                guard let start = ordinalFor(
                    month: item.month,
                    day: item.day,
                    monthLengths: spec.ordinaryCalendar.monthLengths
                ) else { return false }

                let end: Int
                if let endMonth = item.endMonth,
                   let endDay = item.endDay,
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
            } ?? []

            var sourceRefs = ["1 Enoch 72-82", "Jubilees 6:29-32"]
            for observance in observances {
                for ref in observance.sourceRefs where !sourceRefs.contains(ref) {
                    sourceRefs.append(ref)
                }
            }

            let staticWeekdayIndex = (
                weekdayIndex(spec.ordinaryCalendar.day001Weekday)
                + ordinal - 1
            ) % 7
            let staticWeekday = weekdayNames[staticWeekdayIndex]
            if staticWeekday == "Saturday" {
                for ref in [
                    "Exodus 20:8-11",
                    "Leviticus 23:3",
                    "Numbers 28:9-10"
                ] where !sourceRefs.contains(ref) {
                    sourceRefs.append(ref)
                }
            }

            let jubileeYear = index + 1
            let isSabbatical = jubileeYear < 50 && jubileeYear % 7 == 0
            let isJubilee = jubileeYear == 50
            let isRelease =
                isJubilee && monthDay.month == 7 && monthDay.day == 10

            if isSabbatical {
                for ref in [
                    "Leviticus 25:1-7",
                    "Deuteronomy 15:1-18"
                ] where !sourceRefs.contains(ref) {
                    sourceRefs.append(ref)
                }
            }
            if isJubilee && !sourceRefs.contains("Leviticus 25:8-24") {
                sourceRefs.append("Leviticus 25:8-24")
            }
            if isRelease && !sourceRefs.contains("Leviticus 25:8-13") {
                sourceRefs.append("Leviticus 25:8-13")
            }

            let monthName = [
                "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"
            ][monthDay.month - 1]

            let gateText = gate.map {
                "G\($0.gate) · P\($0.phase)"
            } ?? "G—"

            var jubileeText = "JUBILEE Y\(jubileeYear)/50"
            if isSabbatical {
                jubileeText += " · SABBATICAL"
            }
            if isJubilee {
                jubileeText = "JUBILEE YEAR 50"
            }
            if isRelease {
                jubileeText += " · RELEASE"
            }

            return AnnualCalendarState(
                label:
                    "Y\(row.year) · \(monthName) \(String(format: "%02d", monthDay.day)) · DAY \(String(format: "%03d", ordinal))",
                detail:
                    "\(staticWeekday.uppercased()) · W\(String(format: "%02d", week)) D\(dayInWeek) · S\(quarter).\(dayOfQuarter) · \(gateText)",
                observance:
                    observances.map(\.name).joined(separator: " · "),
                jubilee: jubileeText,
                sourceRefs: sourceRefs,
                weekdayName: staticWeekday,
                weekdayNumber: staticWeekdayIndex + 1
            )
        }

        return AnnualCalendarState(
            label: "COMMON CALENDAR",
            detail: "OUTSIDE PUBLISHED 50-YEAR MAP",
            observance: "",
            jubilee: "",
            sourceRefs: [],
            weekdayName: nil,
            weekdayNumber: nil
        )
    }

    private static let weekdayNames = [
        "Sunday", "Monday", "Tuesday", "Wednesday",
        "Thursday", "Friday", "Saturday"
    ]

    private static func weekdayIndex(_ name: String) -> Int {
        weekdayNames.firstIndex(of: name) ?? 0
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
        population: CalendarPopulation?
    ) -> (phase: Int, gate: Int)? {
        guard let seasonal = population?.seasonalArchitecture else {
            return nil
        }

        var start = 1
        for index in seasonal.phaseLengths.indices {
            let end = start + seasonal.phaseLengths[index] - 1
            if (start...end).contains(ordinal) {
                return (index + 1, seasonal.gateSequence[index])
            }
            start = end + 1
        }
        return nil
    }
}
