import Foundation

/// Path helpers shared by the app's manual and watch-folder intake.
public enum FileScan {
    public static let maxFiles = 10_000

    /// Canonical form of a path, so the same file reached two ways
    /// (`/var/…` vs `/private/var/…`, `a/../b`, symlinks) compares equal.
    public static func pathKey(_ url: URL) -> String {
        url.standardizedFileURL.resolvingSymlinksInPath().path
    }

    /// True when both URLs name the same file or folder. Falls back to the file
    /// system's own identity, which handles case-insensitive volumes correctly
    /// without treating `DLC` and `dlc` as one on case-sensitive ones.
    public static func samePath(_ a: URL, _ b: URL) -> Bool {
        let ca = URL(fileURLWithPath: pathKey(a)), cb = URL(fileURLWithPath: pathKey(b))
        if ca.path == cb.path { return true }
        guard let ia = try? ca.resourceValues(forKeys: [.fileResourceIdentifierKey]).fileResourceIdentifier,
              let ib = try? cb.resourceValues(forKeys: [.fileResourceIdentifierKey]).fileResourceIdentifier else { return false }
        return ia.isEqual(ib)
    }

    /// Expands folders (recursively) and keeps only .psarc files, stopping at
    /// `limit`. `truncated` tells the caller that more files were left out.
    public static func expand(_ urls: [URL], limit: Int = maxFiles) -> (files: [URL], truncated: Bool) {
        var out = [URL]()
        func add(_ url: URL) -> Bool {
            guard url.pathExtension.lowercased() == "psarc" else { return true }
            guard out.count < limit else { return false }
            out.append(url)
            return true
        }
        for url in urls {
            var isDir: ObjCBool = false
            guard FileManager.default.fileExists(atPath: url.path, isDirectory: &isDir) else { continue }
            if isDir.boolValue {
                let walker = FileManager.default.enumerator(
                    at: url, includingPropertiesForKeys: [.isRegularFileKey], options: [.skipsHiddenFiles, .skipsPackageDescendants])
                while let child = walker?.nextObject() as? URL {
                    if !add(child) { return (out, true) }
                }
            } else if !add(url) {
                return (out, true)
            }
        }
        return (out, false)
    }
}
