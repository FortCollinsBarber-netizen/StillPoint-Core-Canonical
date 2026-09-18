import Foundation

struct PublishedCivicYear: Codable, Equatable {
    let year: Int
    let openingCivilDate: String
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
        pilotProfile: PilotTemporalCalibration? = nil,
        calendarCoreContract: CalendarCoreContract? = nil,
        calendar inputCalendar: Calendar = .current
    ) -> CivicClockSnapshot {
        var calendar = inputCalendar
        calendar.locale = Locale(identifier: "en_US_POSIX")

        let zenith = calendarCoreContract?.constants.apparentHorizonZenithDegrees
            ?? SolarBoundaryCalculator.defaultZenithDegrees

        let pair = SolarBoundaryCalculator.previousAndNextSunset(
            around: now,
            latitude: latitude,
            longitude: longitude,
            zenithDegrees: zenith,
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
                commonCalendarDetail: "FALLBACK RULE NOT ENACTED",
                lunarLabel: nil,
                seasonLabel: nil,
                jubileeLabel: nil,
                commonStandardTime: nil
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
            zenithDegrees: zenith,
            nextSunset: next,
            calendar: calendar
        )

        let pilotState: PilotTemporalState?
        if let pilotProfile, let calendarCoreContract {
            pilotState = PilotTemporalEngine.state(
                now: now,
                previousBoundary: previous,
                profile: pilotProfile,
                contract: calendarCoreContract,
                calendar: calendar
            )
        } else {
            pilotState = nil
        }

        let annual = annualLabel(
            now: now,
            previousBoundary: previous,
            latitude: latitude,
            longitude: longitude,
            zenithDegrees: zenith,
            publishedCalendar: publishedCalendar,
            pilotState: pilotState,
            calendarCoreContract: calendarCoreContract,
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
            lunarLabel: pilotState?.lunarLabel,
            seasonLabel: pilotState?.seasonLabel,
            jubileeLabel: pilotState?.jubileeLabel,
            commonStandardTime: pilotState?.commonStandardTime
        )
    }

    private static func weeklyProtectedTimeState(
        now: Date,
        namedCivilDate: Date,
        weekday: Int,
        latitude: Double,
        longitude: Double,
        zenithDegrees: Double,
        nextSunset: Date,
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
                zenithDegrees: zenithDegrees,
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
        zenithDegrees: Double,
        publishedCalendar: PublishedCivicCalendar?,
        pilotState: PilotTemporalState?,
        calendarCoreContract: CalendarCoreContract?,
        calendar: Calendar
    ) -> (label: String, detail: String) {
        guard let publishedCalendar else {
            if let pilotState {
                return (
                    pilotState.commonCalendarLabel,
                    pilotState.commonCalendarDetail
                )
            }
            return ("COMMON CALENDAR", "ANNUAL TABLE PENDING")
        }

        guard let contract = calendarCoreContract else {
            return ("COMMON CALENDAR", "CORE CONTRACT UNAVAILABLE")
        }

        let baseYearDays = contract.constants.baseYearDays
        let allowedReconciliation = contract.constants.reconciliationDaysAllowed
        guard baseYearDays > 0, baseYearDays % 4 == 0 else {
            return ("COMMON CALENDAR", "CORE CONTRACT INVALID")
        }
        let quarterDays = baseYearDays / 4

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

            guard allowedReconciliation.contains(
                current.reconciliationDaysAfterCompletion
            ) else { continue }

            guard
                let openingDay = formatter.date(from: current.openingCivilDate),
                let opening = SolarBoundaryCalculator.sunset(
                    on: openingDay,
                    latitude: latitude,
                    longitude: longitude,
                    zenithDegrees: zenithDegrees,
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

            let legalSpan = baseYearDays + current.reconciliationDaysAfterCompletion
            guard boundaryOffset >= 0, boundaryOffset < legalSpan else { continue }

            if sorted.indices.contains(index + 1) {
                let next = sorted[index + 1]
                guard
                    let nextOpeningDay = formatter.date(from: next.openingCivilDate),
                    let publishedSpan = calendar.dateComponents(
                        [.day],
                        from: openingBoundaryDay,
                        to: calendar.startOfDay(for: nextOpeningDay)
                    ).day,
                    publishedSpan == legalSpan,
                    let nextOpening = SolarBoundaryCalculator.sunset(
                        on: nextOpeningDay,
                        latitude: latitude,
                        longitude: longitude,
                        zenithDegrees: zenithDegrees,
                        calendar: calendar
                    ),
                    now < nextOpening
                else { continue }
            }

            if boundaryOffset >= baseYearDays {
                let reconciliationDay = boundaryOffset - baseYearDays + 1
                return (
                    "RECONCILIATION",
                    "R\(reconciliationDay) · YEAR \(current.year) COMPLETE"
                )
            }

            let day = boundaryOffset + 1
            let week = ((day - 1) / 7) + 1
            let dayInWeek = ((day - 1) % 7) + 1
            let season = ((day - 1) / quarterDays) + 1
            return (
                "YEAR \(current.year) · DAY \(String(format: "%03d", day))",
                "S\(season) · W\(String(format: "%02d", week)) · D\(dayInWeek)"
            )
        }

        return ("COMMON CALENDAR", "OUTSIDE PUBLISHED TABLE")
    }
}
