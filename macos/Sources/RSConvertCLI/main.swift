import Foundation
import RSConvertCore

// Command-line front end, mainly for scripting and verification.

func usage() -> Never {
    FileHandle.standardError.write(Data("""
    usage: rsconvert-cli [--version] [--to mac|pc] [--rename short|full] [--appid ID] [--overwrite] -o OUTPUT_DIR [--] FILE...

    """.utf8))
    exit(64)
}

var options = ConvertOptions()
var output: URL?
var files = [URL]()
var args = CommandLine.arguments.dropFirst().makeIterator()
while let arg = args.next() {
    switch arg {
    case "--to": guard let v = args.next(), let p = Platform(rawValue: v.lowercased()) else { usage() }; options.targetPlatform = p
    case "--rename": guard let v = args.next(), let s = RenameScheme(rawValue: v.lowercased()) else { usage() }; options.rename = s
    case "--appid": guard let v = args.next() else { usage() }; options.appID = v
    case "--overwrite": options.overwrite = true
    case "-o", "--output": guard let v = args.next() else { usage() }; output = URL(fileURLWithPath: v, isDirectory: true)
    case "--version": print("rsconvert-cli \(RSConvertVersion.string)"); exit(0)
    case "-h", "--help": usage()
    case "--": while let f = args.next() { files.append(URL(fileURLWithPath: f)) }
    default:
        if arg.hasPrefix("-") {
            FileHandle.standardError.write(Data("rsconvert-cli: unknown option \(arg)\n".utf8))
            usage()
        }
        files.append(URL(fileURLWithPath: arg))
    }
}
guard let output, !files.isEmpty else { usage() }

var failed = false
for file in files {
    let start = Date()
    do {
        switch try Converter.process(file, into: output, options: options) {
        case .written(let url, let summary):
            print("OK   \(file.lastPathComponent) -> \(url.lastPathComponent) (\(summary), \(Int(Date().timeIntervalSince(start) * 1000)) ms)")
        case .skipped(let url, let reason):
            print("SKIP \(file.lastPathComponent) -> \(url.lastPathComponent): \(reason)")
        }
    } catch {
        failed = true
        print("FAIL \(file.lastPathComponent): \(error.localizedDescription)")
    }
}
exit(failed ? 1 : 0)
