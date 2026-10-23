import Foundation

/// Remembers which watched files were already handled (by path, size and
/// modification date) so the watch folder isn't reprocessed on every launch.
@MainActor
final class ProcessedLedger {
    struct Fingerprint: Codable, Hashable, Sendable {
        var size: Int64
        var modified: Double

        nonisolated init?(_ url: URL) {
            guard let values = try? url.resourceValues(forKeys: [.fileSizeKey, .contentModificationDateKey, .isRegularFileKey]),
                  values.isRegularFile == true, let size = values.fileSize, let date = values.contentModificationDate else { return nil }
            self.size = Int64(size)
            modified = date.timeIntervalSinceReferenceDate
        }
    }

    private var entries: [String: Fingerprint] = [:]
    private var saveScheduled = false
    private let fileURL: URL

    init() {
        let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("RSConvert", isDirectory: true)
        try? FileManager.default.createDirectory(at: support, withIntermediateDirectories: true)
        fileURL = support.appendingPathComponent("processed.json")
        if let data = try? Data(contentsOf: fileURL),
           let decoded = try? JSONDecoder().decode([String: Fingerprint].self, from: data) {
            entries = decoded
        }
    }

    func contains(_ path: String, _ fingerprint: Fingerprint) -> Bool { entries[path] == fingerprint }

    func record(_ path: String, _ fingerprint: Fingerprint) {
        entries[path] = fingerprint
        saveSoon()
    }

    /// Drops entries for files that no longer exist in `folder`.
    func prune(folder: String, keeping present: Set<String>) {
        let prefix = folder.hasSuffix("/") ? folder : folder + "/"
        let before = entries.count
        entries = entries.filter { !$0.key.hasPrefix(prefix) || present.contains($0.key) }
        if entries.count != before { saveSoon() }
    }

    func removeAll() {
        entries.removeAll()
        saveSoon()
    }

    func saveSoon() {
        guard !saveScheduled else { return }
        saveScheduled = true
        DispatchQueue.main.asyncAfter(deadline: .now() + 1) { [weak self] in
            MainActor.assumeIsolated {
                guard let self else { return }
                self.saveScheduled = false
                if let data = try? JSONEncoder().encode(self.entries) { try? data.write(to: self.fileURL, options: .atomic) }
            }
        }
    }
}
