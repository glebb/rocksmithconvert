import AppKit
import Foundation

/// Persists user-chosen folders as security-scoped bookmarks so the sandboxed
/// app keeps access across launches, and holds access open while in use.
@MainActor
final class FolderAccess {
    let key: String
    private(set) var url: URL?

    init(key: String) {
        self.key = key
        restore()
    }

    func set(_ newURL: URL?) {
        stopAccess()
        url = nil
        guard let newURL else {
            UserDefaults.standard.removeObject(forKey: key)
            return
        }
        if let data = try? newURL.bookmarkData(options: .withSecurityScope, includingResourceValuesForKeys: nil, relativeTo: nil) {
            UserDefaults.standard.set(data, forKey: key)
        }
        url = newURL
        _ = newURL.startAccessingSecurityScopedResource()
    }

    private func restore() {
        guard let data = UserDefaults.standard.data(forKey: key) else { return }
        var stale = false
        guard let resolved = try? URL(resolvingBookmarkData: data, options: .withSecurityScope, relativeTo: nil, bookmarkDataIsStale: &stale) else {
            UserDefaults.standard.removeObject(forKey: key)
            return
        }
        _ = resolved.startAccessingSecurityScopedResource()
        url = resolved
        if stale, let fresh = try? resolved.bookmarkData(options: .withSecurityScope, includingResourceValuesForKeys: nil, relativeTo: nil) {
            UserDefaults.standard.set(fresh, forKey: key)
        }
    }

    private func stopAccess() { url?.stopAccessingSecurityScopedResource() }

    var exists: Bool {
        guard let url else { return false }
        var isDir: ObjCBool = false
        return FileManager.default.fileExists(atPath: url.path, isDirectory: &isDir) && isDir.boolValue
    }

    /// Presents a folder picker. `suggested` is used as the starting location.
    static func choose(title: String, suggested: URL?) -> URL? {
        let panel = NSOpenPanel()
        panel.message = title
        panel.prompt = "Choose"
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.canCreateDirectories = true
        panel.allowsMultipleSelection = false
        panel.directoryURL = suggested
        NSApp.activate()
        return panel.runModal() == .OK ? panel.url : nil
    }

    /// The user's real home folder (inside the sandbox `NSHomeDirectory()` is the container).
    static var realHome: URL {
        if let pw = getpwuid(getuid()), let dir = pw.pointee.pw_dir {
            return URL(fileURLWithPath: String(cString: dir), isDirectory: true)
        }
        return FileManager.default.homeDirectoryForCurrentUser
    }

    static var steamDLCFolder: URL {
        realHome.appendingPathComponent("Library/Application Support/Steam/steamapps/common/Rocksmith2014/dlc", isDirectory: true)
    }
}
