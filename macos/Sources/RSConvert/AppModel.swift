import Foundation
import Observation
import RSConvertCore
import UserNotifications

struct LogEntry: Identifiable, Sendable {
    enum Kind: Sendable { case success, skipped, failure, info }
    let id = UUID()
    let date = Date()
    let kind: Kind
    let message: String
    var url: URL?
}

/// All app state and processing. Conversion runs off the main thread with
/// bounded concurrency; everything else is main-actor isolated.
@MainActor
@Observable
final class AppModel {
    enum Origin: Sendable { case manual, watch }

    private struct Job: Sendable {
        let url: URL
        /// Canonical path, used for de-duplication and the watch ledger.
        let key: String
        let origin: Origin
        /// Settings at the time the file was queued, so changes mid-batch don't affect it.
        let options: ConvertOptions
        let output: URL
    }

    // MARK: Settings (persisted)

    var targetPlatform: Platform? { didSet { defaults.set(targetPlatform?.rawValue, forKey: "targetPlatform"); optionsChanged() } }
    var renameScheme: RenameScheme? { didSet { defaults.set(renameScheme?.rawValue, forKey: "renameScheme"); optionsChanged() } }
    var appIDEnabled: Bool { didSet { defaults.set(appIDEnabled, forKey: "appIDEnabled"); optionsChanged() } }
    var appID: String { didSet { defaults.set(appID, forKey: "appID"); optionsChanged() } }
    var overwrite: Bool { didSet { defaults.set(overwrite, forKey: "overwrite") } }
    var notifyOnBackground: Bool { didSet { defaults.set(notifyOnBackground, forKey: "notify") } }
    var watchEnabled: Bool {
        didSet {
            defaults.set(watchEnabled, forKey: "watchEnabled")
            restartWatching()
        }
    }

    private(set) var outputFolder: URL?
    private(set) var watchFolder: URL?

    // MARK: State

    private(set) var log: [LogEntry] = []
    private(set) var batchTotal = 0
    private(set) var batchDone = 0
    private(set) var watchProblem: String?
    /// True while files are dragged over the window or menu bar icon.
    var dropTargeted = false
    var isBusy: Bool { batchDone < batchTotal }
    var progress: Double { batchTotal == 0 ? 0 : Double(batchDone) / Double(batchTotal) }

    /// Called whenever something the menu bar icon reflects changes.
    var onStatusChange: (() -> Void)?

    private let defaults = UserDefaults.standard
    private let outputAccess = FolderAccess(key: "outputFolderBookmark")
    private let watchAccess = FolderAccess(key: "watchFolderBookmark")
    private let ledger = ProcessedLedger()
    private var watcher: FolderWatcher?
    private var stabilityTimer: Timer?
    /// Files seen in the watch folder that may still be downloading/copying.
    private var pending: [String: ProcessedLedger.Fingerprint] = [:]
    private var queue: [Job] = []
    private var queuedPaths: Set<String> = []
    private var running = 0
    private let maxConcurrent = max(2, min(4, ProcessInfo.processInfo.activeProcessorCount / 2))
    private var backgroundResults: [String] = []
    private var lastReportedProblem: String?

    init() {
        targetPlatform = defaults.string(forKey: "targetPlatform").flatMap(Platform.init(rawValue:))
        renameScheme = defaults.string(forKey: "renameScheme").flatMap(RenameScheme.init(rawValue:))
        appIDEnabled = defaults.bool(forKey: "appIDEnabled")
        appID = defaults.string(forKey: "appID") ?? "221680"
        overwrite = defaults.bool(forKey: "overwrite")
        notifyOnBackground = defaults.object(forKey: "notify") as? Bool ?? true
        watchEnabled = defaults.bool(forKey: "watchEnabled")
        outputFolder = outputAccess.url
        watchFolder = watchAccess.url
        restartWatching()
    }

    var options: ConvertOptions {
        ConvertOptions(targetPlatform: targetPlatform, rename: renameScheme,
                       appID: appIDEnabled ? appID.trimmingCharacters(in: .whitespaces) : nil, overwrite: overwrite)
    }

    /// Why processing can't start right now, if anything.
    var configurationProblem: String? {
        if outputFolder == nil { return "Choose an output folder" }
        if !outputAccess.exists { return "Output folder is missing" }
        if options.isNoop { return "Choose a conversion, rename or App ID change" }
        if let id = options.appID, !ConvertOptions.isValidAppID(id) { return "App ID must be 1–10 digits" }
        return nil
    }

    // MARK: Folders

    func chooseOutputFolder() {
        let suggested = outputFolder ?? FolderAccess.steamDLCFolder
        guard let url = FolderAccess.choose(title: "Choose where converted files are saved (usually Rocksmith2014/dlc)", suggested: suggested) else { return }
        outputAccess.set(url)
        outputFolder = url
        restartWatching()
    }

    func chooseWatchFolder() {
        let suggested = watchFolder ?? FolderAccess.realHome.appendingPathComponent("Downloads")
        guard let url = FolderAccess.choose(title: "Choose a folder to watch for new .psarc files", suggested: suggested) else { return }
        watchAccess.set(url)
        watchFolder = url
        if watchEnabled { restartWatching() } else { watchEnabled = true }
    }

    func forgetProcessedHistory() {
        ledger.removeAll()
        info("Watch history cleared; existing files will be processed again")
        rescanWatchFolder()
    }

    /// Watched files rejected because of a settings problem were never recorded,
    /// so once the settings become usable a rescan picks them up again.
    private func optionsChanged() {
        guard lastReportedProblem != nil, configurationProblem == nil else { return }
        rescanWatchFolder()
    }

    // MARK: Watching

    private func restartWatching() {
        watcher?.stop()
        watcher = nil
        pending.removeAll()
        watchProblem = nil
        defer { onStatusChange?() }
        guard watchEnabled else { return }
        guard let folder = watchFolder, watchAccess.exists else {
            watchProblem = watchFolder == nil ? "No watch folder chosen" : "Watch folder is missing"
            return
        }
        if let out = outputFolder, FileScan.samePath(out, folder) {
            watchProblem = "Watch folder must differ from the output folder"
            return
        }
        watcher = FolderWatcher(url: folder) { [weak self] in self?.rescanWatchFolder() }
        rescanWatchFolder()
    }

    func rescanWatchFolder() {
        guard watchEnabled, let folder = watchFolder else { return }
        guard watchAccess.exists else {
            watcher?.stop()
            watcher = nil
            watchProblem = "Watch folder is missing"
            onStatusChange?()
            return
        }
        let files = (try? FileManager.default.contentsOfDirectory(
            at: folder, includingPropertiesForKeys: [.fileSizeKey, .contentModificationDateKey, .isRegularFileKey],
            options: [.skipsHiddenFiles])) ?? []
        // Keys are canonical so they match files queued by hand from this folder.
        let folderKey = FileScan.pathKey(folder)
        var present = Set<String>()
        for file in files where file.pathExtension.lowercased() == "psarc" {
            let key = folderKey + "/" + file.lastPathComponent
            present.insert(key)
            guard let fp = ProcessedLedger.Fingerprint(file), !ledger.contains(key, fp),
                  !queuedPaths.contains(key) else { continue }
            if pending[key] == nil { pending[key] = fp }
        }
        ledger.prune(folder: folderKey, keeping: present)
        scheduleStabilityCheck()
    }

    /// A file is processed only once its size and modification date stop
    /// changing, so half-downloaded or still-copying files are never read.
    private func scheduleStabilityCheck() {
        guard !pending.isEmpty, stabilityTimer == nil else { return }
        stabilityTimer = Timer.scheduledTimer(withTimeInterval: 2, repeats: true) { [weak self] _ in
            MainActor.assumeIsolated { self?.checkPending() }
        }
    }

    private func checkPending() {
        var ready = [URL]()
        for (path, previous) in pending {
            let url = URL(fileURLWithPath: path)
            guard let now = ProcessedLedger.Fingerprint(url) else { pending[path] = nil; continue }
            if now == previous, now.size > 0 {
                pending[path] = nil
                ready.append(url)
            } else {
                pending[path] = now
            }
        }
        if pending.isEmpty {
            stabilityTimer?.invalidate()
            stabilityTimer = nil
        }
        if !ready.isEmpty { enqueue(ready, origin: .watch) }
    }

    // MARK: Processing

    func enqueue(_ urls: [URL], origin: Origin) {
        let expanded = FileScan.expand(urls)
        if expanded.truncated {
            info("Only the first \(FileScan.maxFiles.formatted()) .psarc files were added; process the rest separately")
        }
        var seen = Set<String>()
        let files = expanded.files
            .map { (url: $0, key: FileScan.pathKey($0)) }
            .filter { !queuedPaths.contains($0.key) && seen.insert($0.key).inserted }
            .sorted { $0.url.lastPathComponent.localizedStandardCompare($1.url.lastPathComponent) == .orderedAscending }
        guard !files.isEmpty else {
            if origin == .manual, !urls.isEmpty { info("No .psarc files found") }
            return
        }
        if origin == .manual, outputFolder == nil { chooseOutputFolder() }
        if let problem = configurationProblem {
            // Watch events can repeat; don't flood the log with the same message.
            if origin == .manual || problem != lastReportedProblem {
                fail("\(problem) — \(files.count) file(s) not processed")
            }
            lastReportedProblem = problem
            return
        }
        lastReportedProblem = nil
        guard let output = outputFolder else { return }
        let options = self.options
        if !isBusy { batchTotal = 0; batchDone = 0 }
        for file in files {
            queue.append(Job(url: file.url, key: file.key, origin: origin, options: options, output: output))
            queuedPaths.insert(file.key)
        }
        batchTotal += files.count
        onStatusChange?()
        pump()
    }

    private func pump() {
        while running < maxConcurrent, !queue.isEmpty {
            let job = queue.removeFirst()
            running += 1
            let priority: TaskPriority = job.origin == .watch ? .utility : .userInitiated
            Task.detached(priority: priority) { [weak self] in
                let fingerprint = ProcessedLedger.Fingerprint(job.url)
                let result = Result { try Converter.process(job.url, into: job.output, options: job.options) }
                await self?.finish(job, result, fingerprint: fingerprint)
            }
        }
    }

    private func finish(_ job: Job, _ result: Result<ConvertOutcome, any Error>, fingerprint: ProcessedLedger.Fingerprint?) {
        running -= 1
        batchDone += 1
        queuedPaths.remove(job.key)
        let name = job.url.lastPathComponent
        switch result {
        case .success(.written(let out, let summary)):
            append(LogEntry(kind: .success, message: "\(name) → \(out.lastPathComponent) (\(summary))", url: out))
            if job.origin == .watch { backgroundResults.append(out.lastPathComponent) }
        case .success(.skipped(let out, let reason)):
            append(LogEntry(kind: .skipped, message: "\(name): skipped, \(out.lastPathComponent) \(reason)", url: out))
        case .failure(let error):
            append(LogEntry(kind: .failure, message: "\(name): \(error.localizedDescription)", url: job.url))
        }
        // Remember watched files whatever the outcome; a changed file gets a new fingerprint and is retried.
        // Files dropped by hand from the watch folder count too, so the watcher doesn't redo them.
        if let fingerprint, job.origin == .watch || isInWatchFolder(job.key) { ledger.record(job.key, fingerprint) }
        if !isBusy { batchFinished() }
        onStatusChange?()
        pump()
    }

    private func batchFinished() {
        if batchTotal > 1 { info("Finished \(batchTotal) files") }
        ledger.saveSoon()
        guard !backgroundResults.isEmpty else { return }
        let names = backgroundResults
        backgroundResults.removeAll()
        if notifyOnBackground { Notifier.post(converted: names) }
    }

    // MARK: Log

    func info(_ message: String) { append(LogEntry(kind: .info, message: message)) }
    private func fail(_ message: String) { append(LogEntry(kind: .failure, message: message)) }

    private func append(_ entry: LogEntry) {
        log.append(entry)
        if log.count > 500 { log.removeFirst(log.count - 500) }
    }

    func clearLog() { log.removeAll() }

    var recentResults: [LogEntry] { log.reversed().filter { $0.kind != .info }.prefix(6).map { $0 } }

    // MARK: Helpers

    private func isInWatchFolder(_ key: String) -> Bool {
        guard let watchFolder else { return false }
        return (key as NSString).deletingLastPathComponent == FileScan.pathKey(watchFolder)
    }
}

enum Notifier {
    @MainActor static func requestAuthorization() {
        guard Bundle.main.bundleIdentifier != nil else { return }
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert]) { _, _ in }
    }

    @MainActor static func post(converted names: [String]) {
        guard Bundle.main.bundleIdentifier != nil else { return }
        let content = UNMutableNotificationContent()
        content.title = names.count == 1 ? "Converted 1 file" : "Converted \(names.count) files"
        content.body = names.prefix(3).joined(separator: "\n") + (names.count > 3 ? "\n…" : "")
        UNUserNotificationCenter.current().add(UNNotificationRequest(identifier: UUID().uuidString, content: content, trigger: nil))
    }
}
