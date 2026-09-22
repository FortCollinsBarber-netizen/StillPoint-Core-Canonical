import Foundation

enum SolarBoundaryCalculator {
    static func sunrise(
        on civilDate: Date,
        latitude: Double,
        longitude: Double,
        calendar: Calendar = .current,
        spec: CalendarCoreSpec? = CalendarCoreSpecLoader.load()
    ) -> Date? {
        guard let spec else { return nil }
        return solarEvent(
            on: civilDate,
            latitude: latitude,
            longitude: longitude,
            rising: true,
            zenithDegrees: spec.boundary.apparentHorizonZenithDegrees,
            calendar: calendar
        )
    }

    static func sunset(
        on civilDate: Date,
        latitude: Double,
        longitude: Double,
        calendar: Calendar = .current,
        spec: CalendarCoreSpec? = CalendarCoreSpecLoader.load()
    ) -> Date? {
        guard let spec else { return nil }
        return solarEvent(
            on: civilDate,
            latitude: latitude,
            longitude: longitude,
            rising: false,
            zenithDegrees: spec.boundary.apparentHorizonZenithDegrees,
            calendar: calendar
        )
    }

    private static func solarEvent(
        on civilDate: Date,
        latitude: Double,
        longitude: Double,
        rising: Bool,
        zenithDegrees: Double,
        calendar inputCalendar: Calendar
    ) -> Date? {
        var calendar = inputCalendar
        let timeZone = calendar.timeZone
        let local = calendar.dateComponents([.year, .month, .day], from: civilDate)

        guard
            let year = local.year,
            let month = local.month,
            let day = local.day,
            let localMidnight = calendar.date(from: DateComponents(
                timeZone: timeZone,
                year: year,
                month: month,
                day: day
            )),
            let ordinal = calendar.ordinality(
                of: .day,
                in: .year,
                for: localMidnight
            )
        else { return nil }

        let lngHour = longitude / 15.0
        let approximateHour = rising ? 6.0 : 18.0
        let t = Double(ordinal) + ((approximateHour - lngHour) / 24.0)

        let meanAnomaly = (0.9856 * t) - 3.289
        var trueLongitude = meanAnomaly
            + 1.916 * sin(deg2rad(meanAnomaly))
            + 0.020 * sin(deg2rad(2.0 * meanAnomaly))
            + 282.634
        trueLongitude = normalizedDegrees(trueLongitude)

        var rightAscension = rad2deg(
            atan(0.91764 * tan(deg2rad(trueLongitude)))
        )
        rightAscension = normalizedDegrees(rightAscension)

        let lQuadrant = floor(trueLongitude / 90.0) * 90.0
        let raQuadrant = floor(rightAscension / 90.0) * 90.0
        rightAscension += lQuadrant - raQuadrant
        rightAscension /= 15.0

        let sinDeclination = 0.39782 * sin(deg2rad(trueLongitude))
        let cosDeclination = cos(asin(sinDeclination))

        let cosHour = (
            cos(deg2rad(zenithDegrees))
            - sinDeclination * sin(deg2rad(latitude))
        ) / (
            cosDeclination * cos(deg2rad(latitude))
        )

        guard cosHour >= -1.0, cosHour <= 1.0 else { return nil }

        var hourAngleDegrees = rad2deg(acos(cosHour))
        if rising {
            hourAngleDegrees = 360.0 - hourAngleDegrees
        }
        let hourAngle = hourAngleDegrees / 15.0
        let localMeanTime =
            hourAngle + rightAscension - (0.06571 * t) - 6.622
        let universalHours = normalizedHours(localMeanTime - lngHour)

        var utc = Calendar(identifier: .gregorian)
        utc.timeZone = TimeZone(secondsFromGMT: 0)!
        guard let utcMidnight = utc.date(from: DateComponents(
            timeZone: utc.timeZone,
            year: year,
            month: month,
            day: day
        )) else { return nil }

        var candidate = utcMidnight.addingTimeInterval(
            universalHours * 3600.0
        )

        for _ in 0..<2 {
            if calendar.isDate(candidate, inSameDayAs: localMidnight) {
                return candidate
            }

            if candidate < localMidnight {
                candidate = candidate.addingTimeInterval(86_400)
            } else {
                candidate = candidate.addingTimeInterval(-86_400)
            }
        }

        return calendar.isDate(candidate, inSameDayAs: localMidnight)
            ? candidate
            : nil
    }

    static func previousAndNextSunset(
        around now: Date,
        latitude: Double,
        longitude: Double,
        calendar: Calendar = .current,
        spec: CalendarCoreSpec? = CalendarCoreSpecLoader.load()
    ) -> (previous: Date?, next: Date?) {
        guard let spec else { return (nil, nil) }

        let today = calendar.startOfDay(for: now)
        let yesterday = calendar.date(
            byAdding: .day,
            value: -1,
            to: today
        )!
        let tomorrow = calendar.date(
            byAdding: .day,
            value: 1,
            to: today
        )!

        let todaySunset = sunset(
            on: today,
            latitude: latitude,
            longitude: longitude,
            calendar: calendar,
            spec: spec
        )

        if let todaySunset, now >= todaySunset {
            return (
                todaySunset,
                sunset(
                    on: tomorrow,
                    latitude: latitude,
                    longitude: longitude,
                    calendar: calendar,
                    spec: spec
                )
            )
        }

        return (
            sunset(
                on: yesterday,
                latitude: latitude,
                longitude: longitude,
                calendar: calendar,
                spec: spec
            ),
            todaySunset
        )
    }

    private static func deg2rad(_ value: Double) -> Double {
        value * .pi / 180.0
    }

    private static func rad2deg(_ value: Double) -> Double {
        value * 180.0 / .pi
    }

    private static func normalizedDegrees(_ value: Double) -> Double {
        var result = value.truncatingRemainder(dividingBy: 360.0)
        if result < 0 { result += 360.0 }
        return result
    }

    private static func normalizedHours(_ value: Double) -> Double {
        var result = value.truncatingRemainder(dividingBy: 24.0)
        if result < 0 { result += 24.0 }
        return result
    }
}
