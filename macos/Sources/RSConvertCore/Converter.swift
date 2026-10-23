import Foundation

public enum ConvertError: Error, LocalizedError, Equatable {
    case notPSARCFile
    case unknownPlatform
    case metadata(String)
    case wouldReplaceSource
    case nothingToDo
    case invalidAppID
    case io(String)

    public var errorDescription: String? {
        switch self {
        case .notPSARCFile: "Not a .psarc file"
        case .unknownPlatform: "Could not tell whether this is a Mac or PC package"
        case .metadata(let why): "Cannot rename: \(why)"
        case .wouldReplaceSource: "Output would overwrite the original file; choose a different output folder"
        case .nothingToDo: "No conversion, rename or App ID change selected"
        case .invalidAppID: "App ID must be 1–10 digits"
        case .io(let why): why
        }
    }
}

public struct ConvertOptions: Sendable, Hashable, Codable {
    public var targetPlatform: Platform?
    public var rename: RenameScheme?
    public var appID: String?
    public var overwrite: Bool

    public init(targetPlatform: Platform? = nil, rename: RenameScheme? = nil, appID: String? = nil, overwrite: Bool = false) {
        self.targetPlatform = targetPlatform
        self.rename = rename
        self.appID = appID
        self.overwrite = overwrite
    }

    public var isNoop: Bool { targetPlatform == nil && rename == nil && appID == nil }

    public static func isValidAppID(_ id: String) -> Bool {
        (1...10).contains(id.count) && id.allSatisfy { $0.isASCII && $0.isNumber }
    }
}

public enum ConvertOutcome: Sendable, Equatable {
    case written(URL, summary: String)
    case skipped(URL, reason: String)
}

public enum Converter {
    /// Processes one package into `outputDirectory`. The source file is never modified.
    public static func process(_ source: URL, into outputDirectory: URL, options: ConvertOptions) throws -> ConvertOutcome {
        guard source.pathExtension.lowercased() == "psarc" else { throw ConvertError.notPSARCFile }
        guard !options.isNoop else { throw ConvertError.nothingToDo }
        if let id = options.appID, !ConvertOptions.isValidAppID(id) { throw ConvertError.invalidAppID }

        let archive = try PSARCArchive(url: source)
        let sourcePlatform = Platform.detect(archive.entries.map(\.name))
        if options.targetPlatform != nil, sourcePlatform == nil { throw ConvertError.unknownPlatform }

        let target = options.targetPlatform ?? sourcePlatform
        let needsConversion = options.targetPlatform != nil && options.targetPlatform != sourcePlatform
        let appIDEntry = archive.entry(named: "appid")
        var currentAppID: String?
        if let appIDEntry { currentAppID = String(bytes: try archive.read(appIDEntry, maxSize: 64), encoding: .utf8) }
        let needsAppID = options.appID != nil && appIDEntry != nil && currentAppID != options.appID

        // Output filename.
        let originalName = source.lastPathComponent
        let stem = String(originalName.dropLast(".psarc".count))
        let suffix = target?.fileSuffix ?? ".psarc"
        let renamedFromSuffix = needsConversion ? stripPlatformSuffix(stem) + suffix : originalName
        let outputName: String
        if let scheme = options.rename {
            guard let hsan = archive.entry(named: ".hsan") else { throw ConvertError.metadata("missing HSAN manifest") }
            let meta = try Renamer.metadata(fromHSAN: try archive.read(hsan, maxSize: 16 << 20))
            outputName = try Renamer.filename(for: meta, scheme: scheme, originalName: renamedFromSuffix, suffix: suffix)
        } else {
            outputName = renamedFromSuffix
        }

        let destination = outputDirectory.appendingPathComponent(outputName, isDirectory: false)
        if isSameFile(source, destination) { throw ConvertError.wouldReplaceSource }
        if !options.overwrite, FileManager.default.fileExists(atPath: destination.path) {
            return .skipped(destination, reason: "already exists")
        }

        var actions = [String]()
        if needsConversion, let target { actions.append("converted to \(target.displayName)") }
        if needsAppID, let id = options.appID { actions.append("App ID \(id)") }
        if options.rename != nil { actions.append("renamed") }
        if actions.isEmpty { actions.append("copied") }

        let written = try atomicWrite(to: destination, overwrite: options.overwrite) { tmp in
            if needsConversion || needsAppID {
                try rebuild(archive, from: sourcePlatform, to: needsConversion ? target : nil,
                            appID: needsAppID ? options.appID : nil, into: tmp)
            } else {
                // Nothing inside changes: clone (instant and space-free on APFS).
                try FileManager.default.removeItem(at: tmp)
                try FileManager.default.copyItem(at: source, to: tmp)
            }
        }
        guard written else { return .skipped(destination, reason: "already exists") }
        return .written(destination, summary: actions.joined(separator: ", "))
    }

    static func rebuild(_ archive: PSARCArchive, from source: Platform?, to target: Platform?, appID: String?, into url: URL) throws {
        var items = [PSARCWriter.Item]()
        items.reserveCapacity(archive.entries.count)
        for entry in archive.entries {
            var name = entry.name
            var payload = PSARCWriter.Payload.passthrough(archive, entry)
            if let target, let source {
                name = target.mapPath(entry.name)
                // Zero-length SNGs exist as placeholders (e.g. RS1 compatibility packs); nothing to re-key.
                if entry.name.hasSuffix(".sng"), entry.name.contains(source.sngDirectory), entry.length > 0 {
                    let sng = try archive.read(entry)
                    let actual = try SNG.detectKey(sng, preferred: source)
                    payload = .bytes(try SNG.rekey(sng, from: actual, to: target))
                } else if entry.name.hasSuffix("aggregategraph.nt") {
                    payload = .bytes(target.mapAggregateGraph(try archive.read(entry)))
                }
            }
            if let appID, entry.name.hasSuffix("appid") {
                payload = .bytes(Array(appID.utf8))
            }
            if case .passthrough = payload { try archive.verify(entry) }
            items.append(.init(name: name, payload: payload))
        }
        let handle = try FileHandle(forWritingTo: url)
        defer { try? handle.close() }
        try PSARCWriter.write(items, to: handle)
        try handle.synchronize()
    }

    // MARK: - File helpers

    static func hasPlatformSuffix(_ stem: String) -> Bool {
        let l = stem.lowercased()
        return l.hasSuffix("_m") || l.hasSuffix("_p")
    }

    static func stripPlatformSuffix(_ stem: String) -> String {
        hasPlatformSuffix(stem) ? String(stem.dropLast(2)) : stem
    }

    static func isSameFile(_ a: URL, _ b: URL) -> Bool {
        if a.standardizedFileURL.resolvingSymlinksInPath().path == b.standardizedFileURL.resolvingSymlinksInPath().path {
            return true
        }
        // Catches case-insensitive volumes and hard links.
        guard let ia = try? FileManager.default.attributesOfItem(atPath: a.path),
              let ib = try? FileManager.default.attributesOfItem(atPath: b.path) else { return false }
        return (ia[.systemFileNumber] as? Int) == (ib[.systemFileNumber] as? Int)
            && (ia[.systemNumber] as? Int) == (ib[.systemNumber] as? Int)
    }

    /// Writes via a hidden temp file in the destination folder, then renames into
    /// place atomically. Without `overwrite` the rename refuses to replace an
    /// existing file (closing the check-then-write race). Returns false if skipped.
    static func atomicWrite(to destination: URL, overwrite: Bool, body: (URL) throws -> Void) throws -> Bool {
        let dir = destination.deletingLastPathComponent()
        let tmp = dir.appendingPathComponent(".\(destination.lastPathComponent).\(UUID().uuidString).tmp")
        guard FileManager.default.createFile(atPath: tmp.path, contents: nil, attributes: [.posixPermissions: 0o644]) else {
            throw ConvertError.io("Cannot write to \(dir.path)")
        }
        do {
            try body(tmp)
            let flags = overwrite ? 0 : UInt32(RENAME_EXCL)
            if renamex_np(tmp.path, destination.path, flags) != 0 {
                let err = errno
                try? FileManager.default.removeItem(at: tmp)
                if err == EEXIST { return false }
                throw ConvertError.io("Cannot move file into place: \(String(cString: strerror(err)))")
            }
            return true
        } catch {
            try? FileManager.default.removeItem(at: tmp)
            throw error
        }
    }
}
