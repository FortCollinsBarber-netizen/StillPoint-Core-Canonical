import Foundation

enum PublishedCalendarLoader {
    static func load(bundle: Bundle = .main) -> PublishedCivicCalendar? {
        guard let url = bundle.url(forResource: "published_calendar", withExtension: "json") else {
            return nil
        }

        guard
            let data = try? Data(contentsOf: url),
            let calendar = try? JSONDecoder().decode(PublishedCivicCalendar.self, from: data)
        else {
            return nil
        }

        return calendar
    }
}
