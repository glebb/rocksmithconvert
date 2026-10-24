import CryptoKit
import Foundation
import Testing
@testable import RSConvertCore

// MARK: - Fixtures

/// Builds a minimal but structurally real package for the given platform.
func makePackage(_ platform: Platform, artist: String = "Ozzy Osbourne", song: String = "Crazy Train",
                 appID: String = "248750", bigEntry: Int = 200_000) throws -> Data {
    let sngPlain = Array((0..<50_000).map { UInt8(truncatingIfNeeded: $0 &* 31) })
    let hsan = try JSONSerialization.data(withJSONObject: [
        "Entries": ["abc": ["Attributes": ["ArtistName": artist, "SongName": song]]],
    ])
    let dir = platform == .mac ? "macos" : "generic"
    let audio = platform == .mac ? "mac" : "windows"
    let tag = platform == .mac ? "macos" : "dx9"
    let graph = "\u{FEFF}<urn:x> <tag> \"\(tag)\".\n<urn:y> <relpath> \"/songs/bin/\(dir)/song_lead.sng\".\n"
    let items: [PSARCWriter.Item] = [
        .init(name: "songs/bin/\(dir)/song_lead.sng", payload: .bytes(try encryptSNG(sngPlain, key: platform.sngKey))),
        .init(name: "songs/bin/\(dir)/song_empty.sng", payload: .bytes([])),
        .init(name: "manifests/songs_dlc_song/songs_dlc_song.hsan", payload: .bytes(Array(hsan))),
        .init(name: "song_aggregategraph.nt", payload: .bytes(Array(graph.utf8))),
        // Incompressible "audio" exercises raw (stored) blocks and multi-block entries.
        .init(name: "audio/\(audio)/123.wem", payload: .bytes((0..<bigEntry).map { _ in UInt8.random(in: 0...255) })),
        .init(name: "appid.appid", payload: .bytes(Array(appID.utf8))),
    ]
    return try writeArchive(items)
}

func writeArchive(_ items: [PSARCWriter.Item]) throws -> Data {
    let url = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    FileManager.default.createFile(atPath: url.path, contents: nil)
    defer { try? FileManager.default.removeItem(at: url) }
    let handle = try FileHandle(forWritingTo: url)
    try PSARCWriter.write(items, to: handle)
    try handle.close()
    return try Data(contentsOf: url)
}

func encryptSNG(_ plain: [UInt8], key: [UInt8]) throws -> [UInt8] {
    var payload = [UInt8]()
    payload.appendLE32(UInt32(plain.count))
    payload += try plain.withUnsafeBytes { try Zlib.deflate($0) }
    let iv = [UInt8](repeating: 0, count: 16)
    let aes = try AES256(key: key)
    defer { aes.release() }
    try payload.withUnsafeMutableBytes { try aes.ctr($0, iv: iv) }
    var out = [UInt8]()
    out.appendLE32(74); out.appendLE32(3)
    return out + iv + payload + [UInt8](repeating: 0, count: 56)
}

func decryptSNG(_ sng: [UInt8], key: [UInt8]) throws -> [UInt8] {
    var body = Array(sng[24...])
    let aes = try AES256(key: key)
    defer { aes.release() }
    try body.withUnsafeMutableBytes { try aes.ctr($0, iv: Array(sng[8..<24])) }
    let length = Int(body[0]) | Int(body[1]) << 8 | Int(body[2]) << 16 | Int(body[3]) << 24
    return try body.withUnsafeBytes { try Zlib.inflate(UnsafeRawBufferPointer(rebasing: $0[4...]), maxOutput: length).output }
}

extension [UInt8] {
    mutating func appendLE32(_ v: UInt32) { for k in 0..<4 { append(UInt8(truncatingIfNeeded: v >> (8 * UInt32(k)))) } }
}

func tempDir() throws -> URL {
    let url = FileManager.default.temporaryDirectory.appendingPathComponent("rsconvert-tests-\(UUID().uuidString)", isDirectory: true)
    try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
    return url
}

// MARK: - Crypto

@Test func aesMatchesNISTVector() throws {
    // FIPS-197 C.3 (AES-256): CTR with a zero-incremented counter equals ECB of the counter block.
    let key = (0..<32).map { UInt8($0) }
    let block: [UInt8] = [0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88, 0x99, 0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF]
    var zeros = [UInt8](repeating: 0, count: 16)
    let aes = try AES256(key: key)
    defer { aes.release() }
    try zeros.withUnsafeMutableBytes { try aes.ctr($0, iv: block) }
    #expect(zeros.map { String(format: "%02x", $0) }.joined() == "8ea2b7ca516745bfeafc49904b496089")
}

@Test func cfbRoundTripsPartialBlocks() throws {
    let original = (0..<1001).map { UInt8(truncatingIfNeeded: $0 * 7) }
    var data = original
    try TOCCipher.encrypt(&data)
    #expect(data != original)
    try TOCCipher.decrypt(&data)
    #expect(data == original)
}

@Test func ctrCounterCarriesAcrossBytes() throws {
    // Counter ending in 0xFF.. must carry into higher bytes (128-bit big-endian).
    let iv = [UInt8](repeating: 0, count: 15) + [0xFF]
    var a = [UInt8](repeating: 0, count: 32)
    let aes = try AES256(key: Keys.sngMac)
    defer { aes.release() }
    try a.withUnsafeMutableBytes { try aes.ctr($0, iv: iv) }
    var b = [UInt8](repeating: 0, count: 16)
    try b.withUnsafeMutableBytes { try aes.ctr($0, iv: [UInt8](repeating: 0, count: 14) + [1, 0]) }
    #expect(Array(a[16..<32]) == b)
}

// MARK: - PSARC

@Test func archiveRoundTrip() throws {
    let data = try makePackage(.pc)
    let archive = try PSARCArchive(data: data)
    #expect(archive.entries.map(\.name).first == "songs/bin/generic/song_lead.sng")
    #expect(archive.entries.count == 6)
    #expect(Platform.detect(archive.entries.map(\.name)) == .pc)
    let appid = try #require(archive.entry(named: "appid"))
    #expect(String(bytes: try archive.read(appid), encoding: .utf8) == "248750")
    let wem = try #require(archive.entry(named: ".wem"))
    #expect(try archive.read(wem).count == 200_000)
    // Name hashes are MD5 of the path as-is, like the game's own packages.
    let toc = try decryptedTOC(data)
    #expect(Array(toc[30..<46]) == Array(Insecure.MD5.hash(data: Data("songs/bin/generic/song_lead.sng".utf8))))
}

func decryptedTOC(_ data: Data) throws -> [UInt8] {
    let header = [UInt8](data.prefix(32))
    var toc = [UInt8](data[32..<Int(header.be32(12))])
    try TOCCipher.decrypt(&toc)
    return toc
}

@Test func rejectsGarbageAndTruncation() throws {
    #expect(throws: PSARCError.notPSARC) { try PSARCArchive(data: Data("hello".utf8)) }
    #expect(throws: PSARCError.notPSARC) { try PSARCArchive(data: Data(repeating: 0, count: 64)) }
    let good = try makePackage(.mac)
    for cut in [33, 100, good.count / 2, good.count - 1] {
        let truncated = good.prefix(cut)
        // Must throw cleanly (never crash) or, if only the tail is cut, fail when reading.
        if let archive = try? PSARCArchive(data: truncated) {
            #expect(throws: (any Error).self) { for e in archive.entries { try archive.verify(e) } }
        }
    }
}

@Test func rejectsHostileHeaderValues() throws {
    var header = [UInt8]()
    header += Array("PSAR".utf8)
    header.appendBE(0x0001_0004, bytes: 4)
    header += Array("zlib".utf8)
    header.appendBE(0xFFFF_FFFF, bytes: 4)  // TOC size way past EOF
    header.appendBE(30, bytes: 4)
    header.appendBE(0xFFFF_FFFF, bytes: 4)  // absurd entry count
    header.appendBE(65536, bytes: 4)
    header.appendBE(4, bytes: 4)
    #expect(throws: PSARCError.self) { try PSARCArchive(data: Data(header + [UInt8](repeating: 0, count: 256))) }
}

@Test func fuzzedArchivesNeverCrash() throws {
    let good = try makePackage(.pc, bigEntry: 70_000)
    var rng = SystemRandomNumberGenerator()
    for _ in 0..<300 {
        var bytes = [UInt8](good)
        for _ in 0..<Int.random(in: 1...8, using: &rng) {
            bytes[Int.random(in: 32..<min(bytes.count, 2048), using: &rng)] = UInt8.random(in: 0...255, using: &rng)
        }
        if let archive = try? PSARCArchive(data: Data(bytes)) {
            for e in archive.entries { _ = try? archive.verify(e) }
        }
    }
}

// MARK: - Conversion

@Test func convertsMacToPCAndBack() throws {
    let dir = try tempDir()
    defer { try? FileManager.default.removeItem(at: dir) }
    let src = dir.appendingPathComponent("Song_m.psarc")
    try makePackage(.mac).write(to: src)
    let outDir = dir.appendingPathComponent("out", isDirectory: true)
    try FileManager.default.createDirectory(at: outDir, withIntermediateDirectories: true)

    let result = try Converter.process(src, into: outDir, options: .init(targetPlatform: .pc, appID: "221680"))
    guard case .written(let pcURL, _) = result else { Issue.record("expected write"); return }
    #expect(pcURL.lastPathComponent == "Song_p.psarc")

    let pc = try PSARCArchive(url: pcURL)
    let names = pc.entries.map(\.name)
    #expect(names.contains("songs/bin/generic/song_lead.sng"))
    #expect(names.contains("audio/windows/123.wem"))
    #expect(!names.contains { $0.contains("macos") || $0.contains("audio/mac/") })
    let sng = try pc.read(try #require(pc.entry(named: "song_lead.sng")))
    let original = try PSARCArchive(url: src)
    let origSNG = try original.read(try #require(original.entry(named: "song_lead.sng")))
    #expect(try decryptSNG(sng, key: Keys.sngPC) == decryptSNG(origSNG, key: Keys.sngMac))
    let graph = String(decoding: try pc.read(try #require(pc.entry(named: "aggregategraph.nt"))), as: UTF8.self)
    #expect(graph.hasPrefix("\u{FEFF}"))
    #expect(graph.contains("\"dx9\"") && graph.contains("bin/generic") && !graph.contains("macos"))
    #expect(String(bytes: try pc.read(try #require(pc.entry(named: "appid"))), encoding: .utf8) == "221680")
    #expect(try pc.read(try #require(pc.entry(named: ".wem"))) == original.read(try #require(original.entry(named: ".wem"))))

    // Back to Mac (App ID left as is) must reproduce the original archive byte for byte.
    let back = dir.appendingPathComponent("back", isDirectory: true)
    try FileManager.default.createDirectory(at: back, withIntermediateDirectories: true)
    let src2 = dir.appendingPathComponent("again_p.psarc")
    try makePackage(.mac).write(to: src2)
    _ = try Converter.process(src2, into: outDir, options: .init(targetPlatform: .pc))
    guard case .written(let macURL, _) = try Converter.process(outDir.appendingPathComponent("again_p.psarc"), into: back, options: .init(targetPlatform: .mac))
    else { Issue.record("expected write"); return }
    #expect(macURL.lastPathComponent == "again_m.psarc")
    #expect(try Data(contentsOf: macURL) == Data(contentsOf: src2))
}

@Test func sourceIsNeverModifiedOrReplaced() throws {
    let dir = try tempDir()
    defer { try? FileManager.default.removeItem(at: dir) }
    let src = dir.appendingPathComponent("Song_m.psarc")
    let bytes = try makePackage(.mac)
    try bytes.write(to: src)
    // Same folder, already Mac: output name equals the source.
    #expect(throws: ConvertError.wouldReplaceSource) {
        try Converter.process(src, into: dir, options: .init(targetPlatform: .mac, appID: "1", overwrite: true))
    }
    #expect(try Data(contentsOf: src) == bytes)
}

@Test func existingOutputIsSkippedUnlessOverwrite() throws {
    let dir = try tempDir()
    defer { try? FileManager.default.removeItem(at: dir) }
    let src = dir.appendingPathComponent("Song_m.psarc")
    try makePackage(.mac).write(to: src)
    let out = dir.appendingPathComponent("out", isDirectory: true)
    try FileManager.default.createDirectory(at: out, withIntermediateDirectories: true)
    try Data("old".utf8).write(to: out.appendingPathComponent("Song_p.psarc"))

    let skipped = try Converter.process(src, into: out, options: .init(targetPlatform: .pc))
    #expect(skipped == .skipped(out.appendingPathComponent("Song_p.psarc"), reason: "already exists"))
    #expect(try Data(contentsOf: out.appendingPathComponent("Song_p.psarc")) == Data("old".utf8))

    _ = try Converter.process(src, into: out, options: .init(targetPlatform: .pc, overwrite: true))
    #expect(try PSARCArchive(url: out.appendingPathComponent("Song_p.psarc")).entries.count == 6)
    // No temp files left behind.
    #expect(try FileManager.default.contentsOfDirectory(atPath: out.path) == ["Song_p.psarc"])
}

@Test func renameOnlyClonesFile() throws {
    let dir = try tempDir()
    defer { try? FileManager.default.removeItem(at: dir) }
    let src = dir.appendingPathComponent("whatever_dd_m.psarc")
    try makePackage(.mac).write(to: src)
    let out = dir.appendingPathComponent("out", isDirectory: true)
    try FileManager.default.createDirectory(at: out, withIntermediateDirectories: true)
    guard case .written(let url, _) = try Converter.process(src, into: out, options: .init(rename: .short)) else {
        Issue.record("expected write"); return
    }
    #expect(url.lastPathComponent == "OzzyOsbour-CrazyTrainDD_m.psarc")
    #expect(try Data(contentsOf: url) == Data(contentsOf: src))
}

@Test func detectsPlatformFromContentNotFilename() throws {
    let dir = try tempDir()
    defer { try? FileManager.default.removeItem(at: dir) }
    // Mislabelled: PC content in a file without any platform suffix.
    let src = dir.appendingPathComponent("NoSuffix.psarc")
    try makePackage(.pc).write(to: src)
    let out = dir.appendingPathComponent("out", isDirectory: true)
    try FileManager.default.createDirectory(at: out, withIntermediateDirectories: true)
    guard case .written(let url, _) = try Converter.process(src, into: out, options: .init(targetPlatform: .mac)) else {
        Issue.record("expected write"); return
    }
    #expect(url.lastPathComponent == "NoSuffix_m.psarc")
    #expect(Platform.detect(try PSARCArchive(url: url).entries.map(\.name)) == .mac)
}

@Test func invalidOptionsAreRejected() throws {
    let dir = try tempDir()
    defer { try? FileManager.default.removeItem(at: dir) }
    let src = dir.appendingPathComponent("a_p.psarc")
    try makePackage(.pc).write(to: src)
    #expect(throws: ConvertError.nothingToDo) { try Converter.process(src, into: dir, options: .init()) }
    #expect(throws: ConvertError.invalidAppID) { try Converter.process(src, into: dir, options: .init(appID: "12a")) }
    #expect(throws: ConvertError.notPSARCFile) {
        try Converter.process(dir.appendingPathComponent("x.zip"), into: dir, options: .init(targetPlatform: .mac))
    }
}

// MARK: - Rename parity with the 2.x Python app

@Test(arguments: [
    ("Ozzy Osbourne", "Crazy Train", "x_m.psarc", "OzzyOsbour-CrazyTrain_m.psarc", "OzzyOsbourne-CrazyTrain_m.psarc"),
    ("Really Long Artist Name", "This Is Just A Tribute", "Really_Long_p.psarc", "ReallyLong-ThisIsJust_p.psarc", "ReallyLongArtistName-ThisIsJustATribute_p.psarc"),
    ("AC/DC", "Back In Black", "acdc_dd_p.psarc", "ACDC-BackInBlackDD_p.psarc", "ACDC-BackInBlackDD_p.psarc"),
    ("Motörhead", "Ace of Spades (Live)", "a_m.psarc", "Motorhead-AceofSpades_m.psarc", "Motorhead-AceofSpadesLive_m.psarc"),
    ("Sigur Rós", "Hoppípolla", "s_p.psarc", "SigurRos-Hoppipolla_p.psarc", "SigurRos-Hoppipolla_p.psarc"),
    ("The Jimi Hendrix Experience", "Purple Haze", "jimi_DD_m.psarc", "TheJimiHen-PurpleHazeDD_m.psarc", "TheJimiHendrixExperience-PurpleHazeDD_m.psarc"),
    ("Björk", "Army of Me", "b_p.psarc", "Bjork-ArmyofMe_p.psarc", "Bjork-ArmyofMe_p.psarc"),
    ("Guns N' Roses", "Sweet Child O' Mine", "g_p.psarc", "GunsNRoses-SweetChild_p.psarc", "GunsNRoses-SweetChildOMine_p.psarc"),
    ("Red Hot Chili Peppers 2", "Under the Bridge, Part 2: The Return", "r_m.psarc", "RedHotChil-UndertheBr_m.psarc", "RedHotChiliPeppers-UndertheBridgePart2TheReturn_m.psarc"),
])
func renameMatchesPython(artist: String, song: String, original: String, short: String, full: String) throws {
    let meta = Renamer.Metadata(artist: artist, song: song)
    let suffix = String(original.suffix(8))
    #expect(try Renamer.filename(for: meta, scheme: .short, originalName: original, suffix: suffix) == short)
    #expect(try Renamer.filename(for: meta, scheme: .full, originalName: original, suffix: suffix) == full)
}

@Test func renameNeverProducesPathsOrEmptyNames() throws {
    let evil = Renamer.Metadata(artist: "../AC.DC", song: "/etc/passwd")
    let name = try Renamer.filename(for: evil, scheme: .full, originalName: "a_m.psarc", suffix: "_m.psarc")
    #expect(name == "AC.DC-etcpasswd_m.psarc")
    #expect(throws: ConvertError.self) {
        try Renamer.filename(for: .init(artist: "../../..", song: "x"), scheme: .full, originalName: "a_m.psarc", suffix: "_m.psarc")
    }
    #expect(throws: ConvertError.self) {
        try Renamer.filename(for: .init(artist: "日本", song: "歌"), scheme: .short, originalName: "a_m.psarc", suffix: "_m.psarc")
    }
    #expect(throws: ConvertError.metadata("missing ArtistName")) {
        try Renamer.metadata(fromHSAN: Array(#"{"Entries":[{"SongName":"Song"}]}"#.utf8))
    }
}

@Test func dynamicDifficultyNeedsSeparateWord() {
    for name in ["song_dd_p.psarc", "Song_DD_m.psarc", "song-dd.psarc", "dd_song_p.psarc", "Song (DD)_p.psarc"] {
        #expect(Renamer.isDynamicDifficulty(name), "\(name)")
    }
    for name in ["Kidd_Rock_p.psarc", "Added_m.psarc", "Odd_Song_p.psarc", "ddd_p.psarc"] {
        #expect(!Renamer.isDynamicDifficulty(name), "\(name)")
    }
}

@Test func renameKeepsSuffixWhenPlatformUndetectable() throws {
    let dir = try tempDir()
    defer { try? FileManager.default.removeItem(at: dir) }
    // Neither Mac nor PC paths inside, so the platform can't be read from content.
    let hsan = try JSONSerialization.data(withJSONObject: ["ArtistName": "Muse", "SongName": "Uprising"])
    let src = dir.appendingPathComponent("muse_p.psarc")
    try writeArchive([.init(name: "manifests/x/x.hsan", payload: .bytes(Array(hsan)))]).write(to: src)
    let out = dir.appendingPathComponent("out", isDirectory: true)
    try FileManager.default.createDirectory(at: out, withIntermediateDirectories: true)
    guard case .written(let url, _) = try Converter.process(src, into: out, options: .init(rename: .full)) else {
        Issue.record("expected write"); return
    }
    #expect(url.lastPathComponent == "Muse-Uprising_p.psarc")
}

@Test func sngRekeyUsesDetectedPayloadEnd() throws {
    let plain = Array((0..<10_000).map { UInt8(truncatingIfNeeded: $0 &* 7) })
    let mac = try encryptSNG(plain, key: Keys.sngMac)
    // Preferring the wrong platform still finds the right key.
    let key = try SNG.detectKey(mac, preferred: .pc)
    #expect(key.platform == .mac)
    let pc = try SNG.rekey(mac, from: key.platform, to: .pc, payloadEnd: key.payloadEnd)
    #expect(try decryptSNG(pc, key: Keys.sngPC) == plain)
    #expect(Array(pc.suffix(56)) == Array(mac.suffix(56)))
    #expect(throws: PSARCError.self) { try SNG.rekey(mac, from: .mac, to: .pc, payloadEnd: mac.count + 1) }
}

@Test func missingAppIDEntryIsReported() throws {
    let dir = try tempDir()
    defer { try? FileManager.default.removeItem(at: dir) }
    let src = dir.appendingPathComponent("noid_m.psarc")
    try writeArchive([.init(name: "songs/bin/macos/a.txt", payload: .bytes(Array("x".utf8)))]).write(to: src)
    let out = dir.appendingPathComponent("out", isDirectory: true)
    try FileManager.default.createDirectory(at: out, withIntermediateDirectories: true)

    // App ID was the only request: nothing is written.
    let skipped = try Converter.process(src, into: out, options: .init(appID: "221680"))
    #expect(skipped == .skipped(out.appendingPathComponent("noid_m.psarc"), reason: "not written: package has no App ID entry"))
    #expect(try FileManager.default.contentsOfDirectory(atPath: out.path).isEmpty)

    // Alongside a conversion: written, and the summary says the App ID was left alone.
    guard case .written(_, let summary) = try Converter.process(src, into: out, options: .init(targetPlatform: .pc, appID: "221680"))
    else { Issue.record("expected write"); return }
    #expect(summary.contains("no App ID entry"))
}

// MARK: - File intake

@Test func pathKeyUnifiesEquivalentPaths() throws {
    let dir = try tempDir()
    defer { try? FileManager.default.removeItem(at: dir) }
    let file = dir.appendingPathComponent("a_m.psarc")
    try Data().write(to: file)
    let link = dir.appendingPathComponent("link", isDirectory: true)
    try FileManager.default.createSymbolicLink(at: link, withDestinationURL: dir)
    let viaDots = dir.appendingPathComponent("sub/../a_m.psarc")
    let viaLink = link.appendingPathComponent("a_m.psarc")
    #expect(FileScan.pathKey(viaDots) == FileScan.pathKey(file))
    #expect(FileScan.pathKey(viaLink) == FileScan.pathKey(file))
    // /tmp-style temp dirs live under /private on macOS.
    #expect(FileScan.pathKey(URL(fileURLWithPath: "/private" + FileScan.pathKey(file))) == FileScan.pathKey(file))
}

@Test func samePathRespectsVolumeCaseSensitivity() throws {
    let dir = try tempDir()
    defer { try? FileManager.default.removeItem(at: dir) }
    let lower = dir.appendingPathComponent("dlc", isDirectory: true)
    try FileManager.default.createDirectory(at: lower, withIntermediateDirectories: true)
    let upper = dir.appendingPathComponent("DLC", isDirectory: true)
    let caseSensitive = try dir.resourceValues(forKeys: [.volumeSupportsCaseSensitiveNamesKey]).volumeSupportsCaseSensitiveNames ?? false
    if caseSensitive {
        try FileManager.default.createDirectory(at: upper, withIntermediateDirectories: true)
        #expect(!FileScan.samePath(lower, upper))
    } else {
        #expect(FileScan.samePath(lower, upper))
    }
    #expect(FileScan.samePath(lower, dir.appendingPathComponent("x/../dlc", isDirectory: true)))
    #expect(!FileScan.samePath(lower, dir))
}

@Test func expandReportsTruncation() throws {
    let dir = try tempDir()
    defer { try? FileManager.default.removeItem(at: dir) }
    try FileManager.default.createDirectory(at: dir.appendingPathComponent("sub"), withIntermediateDirectories: true)
    for name in ["a_m.psarc", "b_p.PSARC", "notes.txt", "sub/c_m.psarc"] {
        try Data().write(to: dir.appendingPathComponent(name))
    }
    let all = FileScan.expand([dir])
    #expect(all.files.count == 3 && !all.truncated)
    let exact = FileScan.expand([dir], limit: 3)
    #expect(exact.files.count == 3 && !exact.truncated)
    let cut = FileScan.expand([dir], limit: 2)
    #expect(cut.files.count == 2 && cut.truncated)
}

// MARK: - Real packages (set RSCONVERT_SAMPLES to a folder of .psarc files)

@Test(.enabled(if: ProcessInfo.processInfo.environment["RSCONVERT_SAMPLES"] != nil))
func realPackagesRoundTripByteIdentical() throws {
    let samples = URL(fileURLWithPath: ProcessInfo.processInfo.environment["RSCONVERT_SAMPLES"]!)
    let files = try FileManager.default.contentsOfDirectory(at: samples, includingPropertiesForKeys: [.fileSizeKey])
        .filter { $0.pathExtension == "psarc" && ((try? $0.resourceValues(forKeys: [.fileSizeKey]).fileSize) ?? 0) < 100_000_000 }
    let dir = try tempDir()
    defer { try? FileManager.default.removeItem(at: dir) }
    for file in files {
        guard let platform = Platform.detect(try PSARCArchive(url: file).entries.map(\.name)) else { continue }
        let other: Platform = platform == .mac ? .pc : .mac
        let a = dir.appendingPathComponent(UUID().uuidString, isDirectory: true)
        let b = dir.appendingPathComponent(UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: a, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: b, withIntermediateDirectories: true)
        guard case .written(let converted, _) = try Converter.process(file, into: a, options: .init(targetPlatform: other)),
              case .written(let back, _) = try Converter.process(converted, into: b, options: .init(targetPlatform: platform))
        else { Issue.record("no output for \(file.lastPathComponent)"); continue }
        let original = try PSARCArchive(url: file), roundTrip = try PSARCArchive(url: back)
        #expect(original.entries.map(\.name) == roundTrip.entries.map(\.name), "\(file.lastPathComponent)")
        for (x, y) in zip(original.entries, roundTrip.entries) {
            #expect(try original.read(x) == roundTrip.read(y), "\(file.lastPathComponent): \(x.name)")
        }
    }
}
