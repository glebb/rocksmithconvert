import Foundation
import Testing
@testable import RSConvertCore

// RS Extended Range native packages with 7- and 8-string guitar and 5- and 6-string
// bass charts, plus a stock 6/4-string control, converted in both directions. The
// two real DotCharter exports are used when they are in ~/Downloads.

/// One arrangement: stock charts have 6 (guitar) or 4 (bass) strings.
struct Arrangement: Sendable, CustomStringConvertible {
    var name: String
    var strings: Int
    var bass: Bool
    var extended: Bool { strings > (bass ? 4 : 6) }
    var description: String { "\(name)(\(strings))" }

    /// SNXR as DotCharter writes it (magic, version 1, bass flag, string count) with
    /// N-wide records for an extended chart, otherwise stock-looking bytes.
    var chart: [UInt8] {
        let records = (0..<(strings * 4000)).map { UInt8(truncatingIfNeeded: $0 &* 31 &+ strings) }
        if extended { return Array("SNXR".utf8) + [1, bass ? 1 : 0, UInt8(strings), 0] + records }
        return [0xD7, 0x01, 0, 0] + records
    }

    func manifest() throws -> [UInt8] {
        var attributes: [String: Any] = [
            "ArrangementName": bass ? "Bass" : name.capitalized, "ArtistName": "Nickelback",
            "SongName": "Burn It to the Ground",
            "Tuning": Dictionary(uniqueKeysWithValues: (0..<strings).map { ("string\($0)", 0) }),
        ]
        if extended { attributes["ExtendedRange"] = ["Version": 1] }
        return Array(try JSONSerialization.data(withJSONObject: ["Entries": [name: ["Attributes": attributes]]]))
    }
}

struct PackageKind: Sendable, CustomStringConvertible {
    var description: String
    var arrangements: [Arrangement]
}

let extendedKinds = [
    PackageKind(description: "7-string", arrangements: [
        .init(name: "lead", strings: 7, bass: false), .init(name: "rhythm", strings: 6, bass: false),
        .init(name: "bass", strings: 4, bass: true)]),
    PackageKind(description: "8-string", arrangements: [.init(name: "lead", strings: 8, bass: false)]),
    PackageKind(description: "5- and 6-string bass", arrangements: [
        .init(name: "bass", strings: 5, bass: true), .init(name: "bass2", strings: 6, bass: true),
        .init(name: "lead", strings: 6, bass: false)]),
]
let stockArrangements = [Arrangement(name: "lead", strings: 6, bass: false), Arrangement(name: "bass", strings: 4, bass: true)]

/// A package in archive order; SNGs plain unless `encryptSNG`, table of contents per `format`.
func makeChartPackage(_ platform: Platform, _ arrangements: [Arrangement], encryptSNG encrypt: Bool = false,
                      format: PSARCWriter.Format = .init(magic: Array("PSXR".utf8), encryptTOC: false),
                      extra: [PSARCWriter.Item] = []) throws -> Data {
    let dir = platform == .mac ? "macos" : "generic"
    let audio = platform == .mac ? "mac" : "windows"
    let tag = platform == .mac ? "macos" : "dx9"
    var items = [PSARCWriter.Item]()
    var graph = ["\u{FEFF}<urn:audio> <http://emergent.net/aweb/1.0/tag> \"\(tag)\"."]
    for a in arrangements {
        let sng = encrypt ? try encryptSNG(a.chart, key: platform.sngKey) : try plainSNG(a.chart)
        items.append(.init(name: "songs/bin/\(dir)/song_\(a.name).sng", payload: .bytes(sng)))
        graph.append("<urn:\(a.name)> <http://emergent.net/aweb/1.0/relpath> \"/songs/bin/\(dir)/song_\(a.name).sng\".")
    }
    for a in arrangements {
        items.append(.init(name: "manifests/songs_dlc_song/song_\(a.name).json", payload: .bytes(try a.manifest())))
    }
    items.append(.init(name: "manifests/songs_dlc_song/songs_dlc_song.hsan", payload: .bytes(try arrangements[0].manifest())))
    graph.append("<urn:wem> <http://emergent.net/aweb/1.0/relpath> \"/audio/\(audio)/123.wem\".")
    items.append(.init(name: "song_aggregategraph.nt", payload: .bytes(Array((graph.joined(separator: "\n") + "\n").utf8))))
    items.append(.init(name: "audio/\(audio)/123.wem", payload: .bytes((0..<150_000).map { UInt8(truncatingIfNeeded: $0 &* 7919 % 251) })))
    items.append(.init(name: "appid.appid", payload: .bytes(Array("248750".utf8))))
    items += extra
    let url = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    FileManager.default.createFile(atPath: url.path, contents: nil)
    defer { try? FileManager.default.removeItem(at: url) }
    let handle = try FileHandle(forWritingTo: url)
    try PSARCWriter.write(items, to: handle, format: format)
    try handle.close()
    return try Data(contentsOf: url)
}

/// The chart inside a plain SNG (after the 24-byte header and the u32 length).
func plainSNGBody(_ sng: [UInt8]) throws -> [UInt8] {
    let length = Int(sng[24]) | Int(sng[25]) << 8 | Int(sng[26]) << 16 | Int(sng[27]) << 24
    return try Array(sng[28...]).withUnsafeBytes { try Zlib.inflate($0, maxOutput: length).output }
}

func entries(_ archive: PSARCArchive) throws -> [(String, [UInt8])] {
    try archive.entries.map { ($0.name, try archive.read($0)) }
}

func convert(_ source: URL, to target: Platform, in dir: URL, options: ConvertOptions? = nil) throws -> URL {
    let out = dir.appendingPathComponent(UUID().uuidString, isDirectory: true)
    try FileManager.default.createDirectory(at: out, withIntermediateDirectories: true)
    var opts = options ?? .init()
    opts.targetPlatform = target
    guard case .written(let url, _) = try Converter.process(source, into: out, options: opts) else {
        throw ConvertError.io("not written: \(source.lastPathComponent)")
    }
    return url
}

/// Checks that `converted` is `original` with only the platform parts changed: same entries
/// in the same order, folders renamed, the graph remapped, everything else byte for byte.
func expectOnlyPlatformPartsChanged(_ original: PSARCArchive, _ converted: PSARCArchive, target: Platform) throws {
    let before = try entries(original), after = try entries(converted)
    #expect(after.map(\.0) == before.map { target.mapPath($0.0) })
    for ((name, a), (_, b)) in zip(before, after) {
        if name.hasSuffix("aggregategraph.nt") {
            #expect(b == target.mapAggregateGraph(a), "\(name)")
        } else {
            #expect(a == b, "\(name)")
        }
    }
}

@Test(arguments: extendedKinds, [Platform.pc, .mac])
func extendedPackageConvertsBothWays(kind: PackageKind, source: Platform) throws {
    let target: Platform = source == .mac ? .pc : .mac
    let dir = try tempDir()
    defer { try? FileManager.default.removeItem(at: dir) }
    let src = dir.appendingPathComponent("Nickelback_Burn_v2_rsxr\(source.fileSuffix)")
    let original = try makeChartPackage(source, kind.arrangements)
    try original.write(to: src)

    let converted = try convert(src, to: target, in: dir)
    #expect(converted.lastPathComponent == "Nickelback_Burn_v2_rsxr\(target.fileSuffix)")
    let data = try Data(contentsOf: converted)
    #expect(Array(data.prefix(4)) == Array("PSXR".utf8) && headerFlags(data) == 0)
    let o = try PSARCArchive(data: original), c = try PSARCArchive(data: data)
    #expect(c.isNative && !c.tocEncrypted)
    try expectOnlyPlatformPartsChanged(o, c, target: target)
    for a in kind.arrangements {
        let sng = try c.read(try #require(c.entry(named: "\(target.sngDirectory)song_\(a.name).sng")))
        #expect(SNG.isPlain(sng))
        #expect(try plainSNGBody(sng) == a.chart)
        let manifest = try c.read(try #require(c.entry(named: "song_\(a.name).json")))
        let json = try JSONSerialization.jsonObject(with: Data(manifest)) as? [String: Any]
        let attrs = ((json?["Entries"] as? [String: Any])?[a.name] as? [String: Any])?["Attributes"] as? [String: Any]
        #expect((attrs?["Tuning"] as? [String: Any])?.count == a.strings)
    }

    // Back to the source platform: the same entries; and converting again gives the same bytes.
    let back = try convert(converted, to: source, in: dir)
    #expect(back.lastPathComponent == src.lastPathComponent)
    let b = try PSARCArchive(url: back)
    #expect(try entries(b).map(\.0) == entries(o).map(\.0))
    #expect(try entries(b).map(\.1) == entries(o).map(\.1))
    #expect(try Data(contentsOf: back) == original)
    #expect(try Data(contentsOf: convert(back, to: target, in: dir)) == data)
}

@Test(arguments: [Platform.pc, .mac])
func stockPackageConvertsBothWays(source: Platform) throws {
    let target: Platform = source == .mac ? .pc : .mac
    let dir = try tempDir()
    defer { try? FileManager.default.removeItem(at: dir) }
    let src = dir.appendingPathComponent("Ozzy_Crazy_Train\(source.fileSuffix)")
    let original = try makeChartPackage(source, stockArrangements, encryptSNG: true, format: .stock)
    try original.write(to: src)

    let converted = try convert(src, to: target, in: dir)
    #expect(converted.lastPathComponent == "Ozzy_Crazy_Train\(target.fileSuffix)")
    let data = try Data(contentsOf: converted)
    #expect(Array(data.prefix(4)) == Array("PSAR".utf8) && headerFlags(data) == 4)
    let o = try PSARCArchive(data: original), c = try PSARCArchive(data: data)
    #expect(!c.isNative && c.tocEncrypted)
    for a in stockArrangements {
        let sng = try c.read(try #require(c.entry(named: "\(target.sngDirectory)song_\(a.name).sng")))
        #expect(!SNG.isPlain(sng))
        #expect(try decryptSNG(sng, key: target.sngKey) == a.chart)  // re-keyed for the target
    }
    let before = try entries(o), after = try entries(c)
    #expect(after.map(\.0) == before.map { target.mapPath($0.0) })
    for ((name, x), (_, y)) in zip(before, after) where !name.hasSuffix(".sng") {
        #expect(name.hasSuffix("aggregategraph.nt") ? y == target.mapAggregateGraph(x) : y == x, "\(name)")
    }
    let back = try PSARCArchive(url: convert(converted, to: source, in: dir))
    for a in stockArrangements {
        let sng = try back.read(try #require(back.entry(named: "\(source.sngDirectory)song_\(a.name).sng")))
        #expect(try decryptSNG(sng, key: source.sngKey) == a.chart)
    }
}

@Test func encryptedSNGInPlainArchiveIsRekeyed() throws {
    // A plain table of contents does not make the songs plain.
    let dir = try tempDir()
    defer { try? FileManager.default.removeItem(at: dir) }
    let src = dir.appendingPathComponent("Mixed_p.psarc")
    try makeChartPackage(.pc, stockArrangements, encryptSNG: true, format: .init(magic: Array("PSAR".utf8), encryptTOC: false))
        .write(to: src)
    let data = try Data(contentsOf: convert(src, to: .mac, in: dir))
    #expect(headerFlags(data) == 0)
    let c = try PSARCArchive(data: data)
    for a in stockArrangements {
        #expect(try decryptSNG(c.read(try #require(c.entry(named: "macos/song_\(a.name).sng"))), key: Keys.sngMac) == a.chart)
    }
}

@Test func plainSNGInStockArchiveStaysPlain() throws {
    let dir = try tempDir()
    defer { try? FileManager.default.removeItem(at: dir) }
    let src = dir.appendingPathComponent("Mixed_p.psarc")
    let seven = try plainSNG(Arrangement(name: "lead7", strings: 7, bass: false).chart)
    try makeChartPackage(.pc, stockArrangements, encryptSNG: true, format: .stock, extra: [
        .init(name: "songs/bin/generic/song_lead7.sng", payload: .bytes(seven)),
        .init(name: "songs/bin/generic/song_placeholder.sng", payload: .bytes([])),
    ]).write(to: src)
    let c = try PSARCArchive(url: convert(src, to: .mac, in: dir))
    #expect(c.tocEncrypted)
    #expect(try c.read(try #require(c.entry(named: "macos/song_lead7.sng"))) == seven)
    #expect(try c.read(try #require(c.entry(named: "macos/song_placeholder.sng"))).isEmpty)
    #expect(try decryptSNG(c.read(try #require(c.entry(named: "macos/song_lead.sng"))), key: Keys.sngMac) == stockArrangements[0].chart)
}

@Test func invalidAppIDIsRefused() throws {
    let dir = try tempDir()
    defer { try? FileManager.default.removeItem(at: dir) }
    let src = dir.appendingPathComponent("Song_rsxr_p.psarc")
    try makeChartPackage(.pc, extendedKinds[0].arrangements).write(to: src)
    for id in ["", " ", "abc", "12345678901", "22 1680"] {
        #expect(throws: ConvertError.invalidAppID) {
            try Converter.process(src, into: dir, options: .init(targetPlatform: .mac, appID: id))
        }
    }
    let c = try PSARCArchive(url: convert(src, to: .mac, in: dir, options: .init(appID: "221680")))
    #expect(c.isNative && !c.tocEncrypted)
    #expect(String(bytes: try c.read(try #require(c.entry(named: "appid"))), encoding: .utf8) == "221680")
}

@Test func renameKeepsTheRsxrTagOfAnyPackage() throws {
    // As in the 2.x app: a name carrying _rsxr keeps it after a rename, whatever the magic.
    let dir = try tempDir()
    defer { try? FileManager.default.removeItem(at: dir) }
    let src = dir.appendingPathComponent("Stock_rsxr_p.psarc")
    try makePackage(.pc).write(to: src)
    #expect(try convert(src, to: .mac, in: dir, options: .init(rename: .short)).lastPathComponent
        == "OzzyOsbour-CrazyTrain_rsxr_m.psarc")
    let plain = dir.appendingPathComponent("Plain_p.psarc")
    try makePackage(.pc).write(to: plain)
    #expect(try convert(plain, to: .mac, in: dir, options: .init(rename: .short)).lastPathComponent
        == "OzzyOsbour-CrazyTrain_m.psarc")
}

// MARK: - Real DotCharter exports in ~/Downloads (skipped when absent)

func realSample(_ name: String) -> URL? {
    let url = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Downloads/\(name)")
    return FileManager.default.fileExists(atPath: url.path) ? url : nil
}

let nickelback = "Nickelback_Burn-It-To-The-Ground_Dell_v2_3_rsxr_p.psarc"
let fearFactory = "Fear-Factory_Soul-Hacker_Dell_v0_2_rsxr_p.psarc"

/// Converts a real PC package to Mac and back, checking charts and audio byte for byte
/// and the SNXR header of each extended chart (suffix: strings, bass).
func checkRealPackage(_ name: String, extended: [String: (Int, Bool)]) throws {
    let src = try #require(realSample(name))
    let dir = try tempDir()
    defer { try? FileManager.default.removeItem(at: dir) }
    let mac = try convert(src, to: .mac, in: dir)
    #expect(mac.lastPathComponent == name.replacingOccurrences(of: "_rsxr_p.psarc", with: "_rsxr_m.psarc"))
    let data = try Data(contentsOf: mac)
    #expect(Array(data.prefix(4)) == Array("PSXR".utf8) && headerFlags(data) == 0)
    let o = try PSARCArchive(url: src), m = try PSARCArchive(data: data)
    try expectOnlyPlatformPartsChanged(o, m, target: .mac)
    #expect(m.entries.contains { $0.name.hasPrefix("songs/bin/macos/") } && m.entries.contains { $0.name.hasPrefix("audio/mac/") })
    #expect(!m.entries.contains { $0.name.contains("generic") || $0.name.contains("windows") })
    for (suffix, (strings, bass)) in extended {
        let sng = try m.read(try #require(m.entry(named: suffix)))
        #expect(SNG.isPlain(sng))
        #expect(try plainSNGBody(sng).prefix(8) == Array("SNXR".utf8) + [1, bass ? 1 : 0, UInt8(strings), 0], "\(suffix)")
    }
    let back = try convert(mac, to: .pc, in: dir)
    #expect(back.lastPathComponent == name)
    let b = try PSARCArchive(url: back)
    #expect(try entries(b).map(\.0) == entries(o).map(\.0))
    #expect(try entries(b).map(\.1) == entries(o).map(\.1))
}

@Test(.enabled(if: realSample(nickelback) != nil))
func realSevenStringPackageWithFiveStringBass() throws {
    try checkRealPackage(nickelback, extended: ["_lead.sng": (7, false), "_bass.sng": (5, true)])
}

@Test(.enabled(if: realSample(fearFactory) != nil))
func realEightStringPackage() throws {
    try checkRealPackage(fearFactory, extended: ["_lead.sng": (8, false)])
}

// The activity line names what an extended-range package holds, from its HSAN manifest
@Test func extendedRangeSummaryNamesTheArrangements() throws {
    func hsan(_ arrangements: [(String, Int, Bool)]) -> [UInt8] {
        var entries: [String: Any] = [:]
        for (i, (name, strings, extended)) in arrangements.enumerated() {
            var a: [String: Any] = ["ArrangementName": name,
                                    "Tuning": Dictionary(uniqueKeysWithValues: (0..<strings).map { ("string\($0)", 0) })]
            if extended { a["ExtendedRange"] = ["Version": 1] }
            entries["id\(i)"] = ["Attributes": a]
        }
        return Array(try! JSONSerialization.data(withJSONObject: ["Entries": entries]))
    }
    #expect(ExtendedRange.summary(fromHSAN: hsan([("Bass", 5, true), ("Rhythm", 6, true), ("Lead", 7, true)]))
            == "Lead 7-string, Bass 5-string")
    #expect(ExtendedRange.summary(fromHSAN: hsan([("Bass", 6, true), ("Lead", 8, true)])) == "Lead 8-string, Bass 6-string")
    #expect(ExtendedRange.summary(fromHSAN: hsan([("Lead", 6, false), ("Bass", 4, false)])) == nil)
    #expect(ExtendedRange.summary(fromHSAN: hsan([("Lead", 6, true), ("Bass", 4, true)])) == nil)
    #expect(ExtendedRange.summary(fromHSAN: Array("not json".utf8)) == nil)
}

@Test(.enabled(if: realSample(nickelback) != nil && realSample(fearFactory) != nil))
func realPackagesNameTheirExtendedArrangements() throws {
    let dir = try tempDir()
    defer { try? FileManager.default.removeItem(at: dir) }
    for (name, want) in [(nickelback, "extended range: Lead 7-string, Bass 5-string"), (fearFactory, "extended range: Lead 8-string")] {
        let result = try Converter.process(try #require(realSample(name)), into: dir,
                                           options: ConvertOptions(targetPlatform: .mac, overwrite: true))
        guard case .written(_, let summary) = result else { Issue.record("\(name) not written"); continue }
        #expect(summary.contains(want), "\(summary)")
    }
}
