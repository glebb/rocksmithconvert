import Foundation

public enum Platform: String, Sendable, CaseIterable, Codable {
    case mac
    case pc

    public var displayName: String { self == .mac ? "Mac" : "PC" }
    /// Conventional Rocksmith filename suffix, e.g. `Song_m.psarc`.
    public var fileSuffix: String { self == .mac ? "_m.psarc" : "_p.psarc" }

    var sngKey: [UInt8] { self == .mac ? Keys.sngMac : Keys.sngPC }
    var sngDirectory: String { self == .mac ? "songs/bin/macos/" : "songs/bin/generic/" }

    /// Detects the platform from archive contents rather than trusting the filename.
    static func detect(_ names: [String]) -> Platform? {
        var mac = 0, pc = 0
        for n in names {
            if n.contains("bin/macos/") || n.contains("audio/mac/") { mac += 1 }
            if n.contains("bin/generic/") || n.contains("audio/windows/") { pc += 1 }
        }
        if mac > 0, pc == 0 { return .mac }
        if pc > 0, mac == 0 { return .pc }
        return nil
    }

    /// Rewrites an entry path to the target platform's layout.
    func mapPath(_ path: String) -> String {
        switch self {
        case .pc: path.replacingOccurrences(of: "audio/mac", with: "audio/windows")
                      .replacingOccurrences(of: "bin/macos", with: "bin/generic")
        case .mac: path.replacingOccurrences(of: "audio/windows", with: "audio/mac")
                       .replacingOccurrences(of: "bin/generic", with: "bin/macos")
        }
    }

    /// Rewrites the aggregate graph (RDF-ish text) for the target platform:
    /// paths plus the graphics tag (`dx9` on PC, `macos` on Mac). Done on raw
    /// bytes so the UTF-8 BOM and any non-ASCII content pass through untouched.
    func mapAggregateGraph(_ bytes: [UInt8]) -> [UInt8] {
        var b = bytes
        switch self {
        case .pc:
            b = b.replacing("audio/mac", with: "audio/windows")
            b = b.replacing("bin/macos", with: "bin/generic")
            b = b.replacing("macos", with: "dx9")
        case .mac:
            b = b.replacing("audio/windows", with: "audio/mac")
            b = b.replacing("bin/generic", with: "bin/macos")
            b = b.replacing("dx9", with: "macos")
        }
        return b
    }
}

extension [UInt8] {
    func replacing(_ target: String, with replacement: String) -> [UInt8] {
        let t = Array(target.utf8), r = Array(replacement.utf8)
        guard !t.isEmpty, count >= t.count else { return self }
        var out = [UInt8]()
        out.reserveCapacity(count)
        var i = 0
        while i < count {
            if i <= count - t.count, self[i] == t[0], self[i..<(i + t.count)].elementsEqual(t) {
                out += r
                i += t.count
            } else {
                out.append(self[i])
                i += 1
            }
        }
        return out
    }
}

/// SNG files are AES-256-CTR encrypted with a per-platform key:
/// `[u32 magic=74][u32 flags=3][16 byte IV][ciphertext: u32 length + zlib][56 byte signature]`.
enum SNG {
    static let headerSize = 24
    static let maxDecompressed = 64 << 20

    /// Returns which platform key decrypts this SNG, verified by a full decompress.
    static func detectKey(_ sng: [UInt8], preferred: Platform) throws -> Platform {
        for platform in [preferred, preferred == .mac ? .pc : .mac] {
            if (try? decryptedPayloadLength(sng, key: platform.sngKey)) != nil { return platform }
        }
        throw PSARCError.corrupt("SNG cannot be decrypted with either platform key")
    }

    /// Re-encrypts with the target key. The compressed payload is reused as-is
    /// (no recompression); only the keystream changes. The IV and trailing
    /// signature block are carried over.
    static func rekey(_ sng: [UInt8], from source: Platform, to target: Platform) throws -> [UInt8] {
        guard source != target else { return sng }
        let payloadEnd = try decryptedPayloadLength(sng, key: source.sngKey)
        let iv = Array(sng[8..<headerSize])
        var out = sng
        try out.withUnsafeMutableBytes { buf in
            let region = UnsafeMutableRawBufferPointer(rebasing: buf[headerSize..<payloadEnd])
            try crypt(region, key: source.sngKey, iv: iv)
            try crypt(region, key: target.sngKey, iv: iv)
        }
        return out
    }

    /// Decrypts and inflates to validate; returns the absolute end offset of the encrypted payload.
    private static func decryptedPayloadLength(_ sng: [UInt8], key: [UInt8]) throws -> Int {
        guard sng.count > headerSize + 4 else { throw PSARCError.corrupt("SNG too short") }
        var plain = Array(sng[headerSize...])
        try plain.withUnsafeMutableBytes { try crypt($0, key: key, iv: Array(sng[8..<headerSize])) }
        let length = Int(UInt32(plain[0]) | UInt32(plain[1]) << 8 | UInt32(plain[2]) << 16 | UInt32(plain[3]) << 24)
        guard length <= maxDecompressed else { throw PSARCError.corrupt("SNG declares \(length) bytes") }
        let inflated = try plain.withUnsafeBytes {
            try Zlib.inflate(UnsafeRawBufferPointer(rebasing: $0[4...]), maxOutput: length)
        }
        guard inflated.output.count == length else { throw PSARCError.corrupt("SNG length mismatch") }
        return headerSize + 4 + inflated.consumed
    }

    private static func crypt(_ buf: UnsafeMutableRawBufferPointer, key: [UInt8], iv: [UInt8]) throws {
        let aes = try AES256(key: key)
        defer { aes.release() }
        try aes.ctr(buf, iv: iv)
    }
}
