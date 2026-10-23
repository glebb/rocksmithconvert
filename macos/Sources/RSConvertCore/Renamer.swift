import Foundation

public enum RenameScheme: String, Sendable, CaseIterable, Codable {
    /// Artist max 10 letters, song shortened so the whole name stays near 20 letters.
    case short
    /// Artist-Song with only unsafe characters removed (long artists still squashed to letters).
    case full

    public var displayName: String { self == .short ? "Short" : "Full" }
}

/// Builds Rocksmith-friendly filenames from song metadata.
/// Behaviour intentionally matches the 2.x Python app so existing libraries keep their names.
public enum Renamer {
    public struct Metadata: Sendable, Equatable {
        public var artist: String
        public var song: String
        public init(artist: String, song: String) { self.artist = artist; self.song = song }
    }

    /// Reads ArtistName/SongName from an `.hsan` manifest (JSON).
    public static func metadata(fromHSAN data: [UInt8]) throws -> Metadata {
        guard let json = try? JSONSerialization.jsonObject(with: Data(data)) else {
            throw ConvertError.metadata("invalid HSAN manifest")
        }
        guard let artist = find("ArtistName", in: json), !artist.isEmpty else { throw ConvertError.metadata("missing ArtistName") }
        guard let song = find("SongName", in: json), !song.isEmpty else { throw ConvertError.metadata("missing SongName") }
        return Metadata(artist: artist, song: song)
    }

    private static func find(_ key: String, in node: Any) -> String? {
        if let dict = node as? [String: Any] {
            if let value = dict[key] as? String { return value }
            // Sorted for deterministic results across runs.
            for k in dict.keys.sorted() { if let v = find(key, in: dict[k]!) { return v } }
        } else if let array = node as? [Any] {
            for v in array { if let found = find(key, in: v) { return found } }
        }
        return nil
    }

    /// - Parameters:
    ///   - originalName: filename used to detect dynamic-difficulty (`dd_`) packages.
    ///   - suffix: e.g. `_m.psarc`.
    public static func filename(for meta: Metadata, scheme: RenameScheme, originalName: String, suffix: String) throws -> String {
        var artist = Array(meta.artist.unicodeScalars)
        var song = Array(meta.song.unicodeScalars)
        if artist.count > 10 {
            artist = artist.filter(isASCIILetter)
            if scheme == .short { artist = Array(artist.prefix(10)) }
        }
        let maxSong = 10 + (10 - artist.count)
        if scheme == .short, song.count > maxSong {
            song = Array(song.filter(isASCIILetter).prefix(max(maxSong, 0)))
        }
        var songString = String(String.UnicodeScalarView(song))
        if originalName.lowercased().contains("dd_") { songString += "DD" }

        let clean = { (s: String) in
            String(String.UnicodeScalarView(s.decomposedStringWithCompatibilityMapping.unicodeScalars.filter {
                $0.isASCII && (isASCIILetter($0) || ("0"..."9").contains($0) || $0 == "." || $0 == "_" || $0 == "-")
            }))
        }
        let a = clean(String(String.UnicodeScalarView(artist))).trimmingCharacters(in: CharacterSet(charactersIn: "."))
        let s = clean(songString)
        guard !a.isEmpty, !s.isEmpty else { throw ConvertError.metadata("artist or song has no usable characters") }
        return "\(a)-\(s)\(suffix)"
    }

    private static func isASCIILetter(_ c: Unicode.Scalar) -> Bool { ("A"..."Z").contains(c) || ("a"..."z").contains(c) }
}
