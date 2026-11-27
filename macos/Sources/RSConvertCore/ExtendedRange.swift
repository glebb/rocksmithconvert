import Foundation

/// What an RS Extended Range package holds, for the activity line: its arrangements with more strings than stock
/// (a 7- or 8-string guitar, a 5- or 6-string bass), read from the HSAN manifest. Such an arrangement's attributes
/// carry `ExtendedRange` and a positional `Tuning`, one `stringN` per string (github.com/SomeeName/rs-extended-range,
/// docs/release/NATIVE-FORMAT.md).
public enum ExtendedRange {
    /// "Lead 7-string, Bass 5-string", in the order Lead, Rhythm, Combo, Bass (then any other, by name), or nil when
    /// the manifest names no arrangement with more strings than stock.
    public static func summary(fromHSAN data: [UInt8]) -> String? {
        guard let json = try? JSONSerialization.jsonObject(with: Data(data)) as? [String: Any],
              let entries = json["Entries"] as? [String: Any] else { return nil }
        var found: [(name: String, strings: Int)] = []
        for case let entry as [String: Any] in entries.values {
            guard let a = entry["Attributes"] as? [String: Any], a["ExtendedRange"] is [String: Any],
                  let name = a["ArrangementName"] as? String,
                  let tuning = a["Tuning"] as? [String: Any] else { continue }
            let strings = tuning.keys.filter { $0.hasPrefix("string") }.count
            let stock = name.hasPrefix("Bass") ? 4 : 6
            if strings > stock { found.append((name, strings)) }
        }
        guard !found.isEmpty else { return nil }
        let order = ["Lead", "Rhythm", "Combo", "Bass"]
        func rank(_ n: String) -> Int { order.firstIndex { n.hasPrefix($0) } ?? order.count }
        found.sort { (rank($0.name), $0.name) < (rank($1.name), $1.name) }
        return found.map { "\($0.name) \($0.strings)-string" }.joined(separator: ", ")
    }
}
