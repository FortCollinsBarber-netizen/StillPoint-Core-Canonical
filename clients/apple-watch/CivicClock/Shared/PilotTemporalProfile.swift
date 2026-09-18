import Foundation

struct PilotTemporalCalibration: Codable, Equatable {
    struct CommonCalendar: Codable, Equatable {
        let yearLabel: Int
        let openingCivilDate: String
        let day001Weekday: String
        let commonStandardOffsetSeconds: Int
    }

    struct JubileePilot: Codable, Equatable {
        let cycle: Int
        let cycleYear: Int
        let firstCommonYear: Int
    }

    struct LunarWitness: Codable, Equatable {
        let source: String
        let newMoonUTC: String
        let firstQuarterUTC: String
        let fullMoonUTC: String
        let lastQuarterUTC: String
        let nextNewMoonUTC: String
    }

    struct SeasonWitness: Codable, Equatable {
        let source: String
        let juneSolsticeUTC: String
        let septemberEquinoxUTC: String
        let decemberSolsticeUTC: String
    }

    let version: String
    let commonCalendar: CommonCalendar
    let jubileePilot: JubileePilot
    let lunarWitness: LunarWitness
    let seasonWitness: SeasonWitness
}

struct PilotTemporalState: Equatable {
    let commonCalendarLabel: String
    let commonCalendarDetail: String
    let lunarLabel: String
    let seasonLabel: String
    let jubileeLabel: String
    let commonStandardTime: String
}

enum PilotTemporalLoader {
    static func load(bundle: Bundle = .main) -> PilotTemporalCalibration? {
        guard let url = bundle.url(
            forResource: "pilot_calibration_2026",
            withExtension: "json"
        ) else { return nil }
        return load(url: url)
    }

    static func load(url: URL) -> PilotTemporalCalibration? {
        guard
            let data = try? Data(contentsOf: url),
            let profile = try? JSONDecoder().decode(
                PilotTemporalCalibration.self,
                from: data
            )
        else { return nil }
        return profile
    }
}

enum PilotTemporalEngine {
    static func state(
        now: Date,
        previousBoundary: Date,
        profile: PilotTemporalCalibration,
        contract: CalendarCoreContract,
        calendar inputCalendar: Calendar
    ) -> PilotTemporalState? {
        var calendar = inputCalendar
        calendar.locale = Locale(identifier: "en_US_POSIX")

        let formatter = DateFormatter()
        formatter.calendar = calendar
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = calendar.timeZone
        formatter.dateFormat = "yyyy-MM-dd"
        formatter.isLenient = false

        guard let opening = formatter.date(
            from: profile.commonCalendar.openingCivilDate
        ) else { return nil }

        let openingDay = calendar.startOfDay(for: opening)
        let activeBoundaryDay = calendar.startOfDay(for: previousBoundary)

        guard let offset = calendar.dateComponents(
            [.day],
            from: openingDay,
            to: activeBoundaryDay
        ).day else { return nil }

        let ordinal = offset + 1
        let baseYearDays = contract.constants.baseYearDays
        guard ordinal >= 1, ordinal <= baseYearDays else { return nil }

        guard let common = commonPosition(
            ordinal: ordinal,
            day001Weekday: profile.commonCalendar.day001Weekday,
            monthLengths: contract.constants.monthLengths,
            baseYearDays: baseYearDays
        ) else { return nil }

        let year = profile.commonCalendar.yearLabel
        let commonLabel = "PILOT · YEAR \(year) · DAY \(String(format: "%03d", ordinal))"
        let commonDetail = "M\(String(format: "%02d", common.month)) D\(String(format: "%02d", common.day)) · Q\(common.quarter) · W\(String(format: "%02d", common.week)) · D\(common.dayInWeek)"

        let lunar = lunarLabel(now: now, witness: profile.lunarWitness)
        let season = seasonLabel(now: now, witness: profile.seasonWitness)
        let jubilee = jubileeLabel(
            commonYear: year,
            pilot: profile.jubileePilot
        )
        let commonTime = commonStandardTimeString(
            now,
            offsetSeconds: profile.commonCalendar.commonStandardOffsetSeconds
        )

        return PilotTemporalState(
            commonCalendarLabel: commonLabel,
            commonCalendarDetail: commonDetail,
            lunarLabel: lunar,
            seasonLabel: season,
            jubileeLabel: jubilee,
            commonStandardTime: commonTime
        )
    }

    private static func commonPosition(
        ordinal: Int,
        day001Weekday: String,
        monthLengths: [Int],
        baseYearDays: Int
    ) -> (
        month: Int,
        day: Int,
        quarter: Int,
        week: Int,
        dayInWeek: Int,
        weekday: String
    )? {
        let weekdays = [
            "Sunday", "Monday", "Tuesday", "Wednesday",
            "Thursday", "Friday", "Saturday"
        ]
        guard
            let start = weekdays.firstIndex(of: day001Weekday),
            monthLengths.count == 12,
            monthLengths.reduce(0, +) == baseYearDays,
            baseYearDays % 4 == 0,
            baseYearDays % 7 == 0
        else { return nil }

        var remaining = ordinal
        var month = 1
        var day = 1
        for (index, length) in monthLengths.enumerated() {
            if remaining <= length {
                month = index + 1
                day = remaining
                break
            }
            remaining -= length
        }

        let quarterDays = baseYearDays / 4
        let quarter = ((ordinal - 1) / quarterDays) + 1
        let week = ((ordinal - 1) / 7) + 1
        let dayInWeek = ((ordinal - 1) % 7) + 1
        let weekday = weekdays[(start + ordinal - 1) % 7]

        return (month, day, quarter, week, dayInWeek, weekday)
    }

    private static func parseUTC(_ value: String) -> Date? {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter.date(from: value)
    }

    private static func lunarLabel(
        now: Date,
        witness: PilotTemporalCalibration.LunarWitness
    ) -> String {
        guard
            let newMoon = parseUTC(witness.newMoonUTC),
            let firstQuarter = parseUTC(witness.firstQuarterUTC),
            let fullMoon = parseUTC(witness.fullMoonUTC),
            let lastQuarter = parseUTC(witness.lastQuarterUTC),
            let nextNewMoon = parseUTC(witness.nextNewMoonUTC)
        else { return "MOON · EVIDENCE UNAVAILABLE" }

        if now < newMoon || now >= nextNewMoon {
            return "MOON · OUTSIDE PUBLISHED LUNATION"
        }
        if now < firstQuarter {
            return "MOON · WAXING CRESCENT"
        }
        if now < fullMoon {
            return "MOON · WAXING GIBBOUS"
        }
        if now < lastQuarter {
            return "MOON · WANING GIBBOUS"
        }
        return "MOON · WANING CRESCENT"
    }

    private static func seasonLabel(
        now: Date,
        witness: PilotTemporalCalibration.SeasonWitness
    ) -> String {
        guard
            let summer = parseUTC(witness.juneSolsticeUTC),
            let autumn = parseUTC(witness.septemberEquinoxUTC),
            let winter = parseUTC(witness.decemberSolsticeUTC)
        else { return "SEASON · EVIDENCE UNAVAILABLE" }

        if now >= summer && now < autumn {
            let total = autumn.timeIntervalSince(summer)
            let elapsed = now.timeIntervalSince(summer)
            let pct = max(0, min(100, elapsed / total * 100))
            return "SEASON · SUMMER \(String(format: "%.1f", pct))%"
        }
        if now >= autumn && now < winter {
            let total = winter.timeIntervalSince(autumn)
            let elapsed = now.timeIntervalSince(autumn)
            let pct = max(0, min(100, elapsed / total * 100))
            return "SEASON · AUTUMN \(String(format: "%.1f", pct))%"
        }
        return "SEASON · OUTSIDE PUBLISHED WINDOW"
    }

    private static func jubileeLabel(
        commonYear: Int,
        pilot: PilotTemporalCalibration.JubileePilot
    ) -> String {
        let offset = commonYear - pilot.firstCommonYear
        guard offset >= 0 else { return "JUBILEE · BEFORE PILOT EPOCH" }

        let absolute = pilot.cycleYear + offset
        let cycleOffset = absolute - 1
        let cycle = pilot.cycle + (cycleOffset / 50)
        let cycleYear = (cycleOffset % 50) + 1

        if cycleYear == 50 {
            return "JUBILEE · C\(cycle) · YEAR 50"
        }

        let block = ((cycleYear - 1) / 7) + 1
        let within = ((cycleYear - 1) % 7) + 1
        return "JUBILEE · C\(cycle) · Y\(cycleYear) · 7Y \(block)/\(within)"
    }

    static func commonStandardTimeString(
        _ date: Date,
        offsetSeconds: Int
    ) -> String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(secondsFromGMT: offsetSeconds)
        formatter.dateFormat = "h:mm a 'MST'"
        return formatter.string(from: date)
    }
}
