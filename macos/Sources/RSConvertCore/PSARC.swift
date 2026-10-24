import CryptoKit
import Foundation

public enum PSARCError: Error, LocalizedError, Equatable {
    case notPSARC
    case unsupported(String)
    case corrupt(String)
    case crypto(Int)

    public var errorDescription: String? {
        switch self {
        case .notPSARC: "Not a PSARC archive"
        case .unsupported(let why): "Unsupported PSARC: \(why)"
        case .corrupt(let why): "Damaged PSARC: \(why)"
        case .crypto(let status): "Encryption error (\(status))"
        }
    }
}

/// Read-only view of a Rocksmith 2014 PSARC archive.
///
/// The file is memory-mapped, so opening is cheap and only the bytes actually
/// touched are paged in. Every size and offset read from the file is checked
/// against the file length before use; the archive is untrusted input.
public final class PSARCArchive: Sendable {
    public struct Entry: Sendable {
        public let name: String
        let zIndex: Int
        public let length: Int
        let offset: Int
        var blockCount: Int { (length + PSARCArchive.blockSize - 1) / PSARCArchive.blockSize }
    }

    static let magic: [UInt8] = Array("PSAR".utf8)
    static let version: UInt32 = 0x0001_0004
    static let compression: [UInt8] = Array("zlib".utf8)
    static let entrySize = 30
    static let blockSize = 65536
    static let flagEncryptedTOC: UInt32 = 4

    // Generous limits that still rule out absurd allocations from crafted headers.
    static let maxEntries = 100_000
    static let maxTOCSize = 64 << 20
    static let maxListingSize = 16 << 20

    let data: Data
    let zLengths: [UInt16]
    public let entries: [Entry]

    public convenience init(url: URL) throws {
        let data: Data
        do {
            // Map only where safe: a mapped file on a network or removable volume
            // that shrinks or disappears mid-read would crash with SIGBUS.
            data = try Data(contentsOf: url, options: [.mappedIfSafe])
        } catch {
            throw PSARCError.corrupt("cannot read file (\(error.localizedDescription))")
        }
        try self.init(data: data)
    }

    public init(data: Data) throws {
        // Offsets below are absolute, so make sure indices start at zero.
        let data = data.startIndex == 0 ? data : Data(data)
        self.data = data
        guard data.count >= 32 else { throw PSARCError.notPSARC }
        let header = [UInt8](data.prefix(32))
        guard Array(header[0..<4]) == Self.magic else { throw PSARCError.notPSARC }
        guard header.be32(4) == Self.version, Array(header[8..<12]) == Self.compression else {
            throw PSARCError.unsupported("version or compression")
        }
        let tocSize = Int(header.be32(12))
        let entrySize = Int(header.be32(16))
        let count = Int(header.be32(20))
        let blockSize = Int(header.be32(24))
        let flags = header.be32(28)

        guard entrySize == Self.entrySize, blockSize == Self.blockSize else {
            throw PSARCError.unsupported("entry size \(entrySize), block size \(blockSize)")
        }
        guard count >= 1, count <= Self.maxEntries else { throw PSARCError.corrupt("entry count \(count)") }
        guard tocSize >= 32 + count * entrySize, tocSize <= min(data.count, Self.maxTOCSize) else {
            throw PSARCError.corrupt("table of contents size")
        }

        var toc = [UInt8](data[32..<tocSize])
        if flags & Self.flagEncryptedTOC != 0 { try TOCCipher.decrypt(&toc) }

        let zCount = (toc.count - count * entrySize) / 2
        var zLengths = [UInt16]()
        zLengths.reserveCapacity(zCount)
        let zBase = count * entrySize
        for i in 0..<zCount { zLengths.append(UInt16(toc[zBase + 2 * i]) << 8 | UInt16(toc[zBase + 2 * i + 1])) }
        self.zLengths = zLengths

        var raw = [(zIndex: Int, length: Int, offset: Int)]()
        raw.reserveCapacity(count)
        for i in 0..<count {
            let b = i * entrySize
            let zIndex = Int(toc.be32(b + 16))
            let length = Int(toc.be40(b + 20))
            let offset = Int(toc.be40(b + 25))
            let blocks = (length + blockSize - 1) / blockSize
            guard zIndex <= zCount, blocks <= zCount - zIndex else { throw PSARCError.corrupt("block index out of range") }
            var stored = 0
            for z in zLengths[zIndex..<(zIndex + blocks)] { stored += z == 0 ? blockSize : Int(z) }
            guard offset >= tocSize, offset <= data.count, stored <= data.count - offset else {
                throw PSARCError.corrupt("entry \(i) extends past end of file")
            }
            raw.append((zIndex, length, offset))
        }

        // Entry 0 is the file listing (newline-separated names of entries 1...).
        let listingEntry = Entry(name: "", zIndex: raw[0].zIndex, length: raw[0].length, offset: raw[0].offset)
        guard listingEntry.length <= Self.maxListingSize else { throw PSARCError.corrupt("listing too large") }
        var listingBytes = [UInt8]()
        try Self.readEntry(listingEntry, data: data, zLengths: zLengths) { listingBytes.append(contentsOf: $0) }
        guard let listing = String(bytes: listingBytes, encoding: .utf8) else { throw PSARCError.corrupt("listing is not UTF-8") }
        let names = listing.split(omittingEmptySubsequences: false, whereSeparator: { $0 == "\n" || $0 == "\r\n" || $0 == "\r" })
            .map(String.init)
        guard names.count >= count - 1 else { throw PSARCError.corrupt("listing has \(names.count) names for \(count - 1) entries") }

        entries = (1..<count).map { i in
            Entry(name: names[i - 1], zIndex: raw[i].zIndex, length: raw[i].length, offset: raw[i].offset)
        }
    }

    /// Byte range of an entry's stored (possibly compressed) blocks.
    func storedRange(_ entry: Entry) -> Range<Int> {
        var stored = 0
        for z in blockSizes(entry) { stored += z == 0 ? Self.blockSize : Int(z) }
        return entry.offset..<(entry.offset + stored)
    }

    func blockSizes(_ entry: Entry) -> ArraySlice<UInt16> { zLengths[entry.zIndex..<(entry.zIndex + entry.blockCount)] }

    /// Reads and decompresses a whole entry. Callers should only use this for
    /// small entries (manifests, SNG, graph); large audio is never materialised.
    public func read(_ entry: Entry, maxSize: Int = 256 << 20) throws -> [UInt8] {
        guard entry.length <= maxSize else { throw PSARCError.corrupt("\(entry.name) is too large to load") }
        var out = [UInt8]()
        out.reserveCapacity(entry.length)
        try Self.readEntry(entry, data: data, zLengths: zLengths) { out.append(contentsOf: $0) }
        return out
    }

    /// Decompresses every block of the entry without keeping the output, to prove integrity.
    func verify(_ entry: Entry) throws {
        try Self.readEntry(entry, data: data, zLengths: zLengths) { _ in }
    }

    public func entry(named suffix: String) -> Entry? { entries.first { $0.name.hasSuffix(suffix) } }

    private static func readEntry(
        _ entry: Entry, data: Data, zLengths: [UInt16], sink: (UnsafeRawBufferPointer) throws -> Void
    ) throws {
        try data.withUnsafeBytes { (file: UnsafeRawBufferPointer) in
            var position = entry.offset
            var produced = 0
            for z in zLengths[entry.zIndex..<(entry.zIndex + entry.blockCount)] {
                let stored = z == 0 ? blockSize : Int(z)
                let expected = min(blockSize, entry.length - produced)
                let block = UnsafeRawBufferPointer(rebasing: file[position..<(position + stored)])
                if stored == expected {
                    // Stored uncompressed (writers only compress when it saves space).
                    try sink(block)
                } else {
                    let inflated = try Zlib.inflate(block, maxOutput: expected)
                    guard inflated.output.count == expected else {
                        throw PSARCError.corrupt("\(entry.name): block size mismatch")
                    }
                    try inflated.output.withUnsafeBytes { try sink($0) }
                }
                position += stored
                produced += expected
            }
        }
    }
}

/// Writes a PSARC archive. Unmodified entries are streamed straight from the
/// source archive's stored blocks (no decompress/recompress), which is what
/// makes conversion of audio-heavy packages fast.
enum PSARCWriter {
    enum Payload {
        case passthrough(PSARCArchive, PSARCArchive.Entry)
        case bytes([UInt8])
    }

    struct Item {
        var name: String
        var payload: Payload
    }

    private struct Prepared {
        var md5: [UInt8]
        var length: Int
        var zLengths: [UInt16]
        var storedSize: Int
        var chunks: [[UInt8]]  // only for .bytes
        var passthrough: (PSARCArchive, Range<Int>)?
    }

    static func write(_ items: [Item], to handle: FileHandle) throws {
        let listing = Array(items.map(\.name).joined(separator: "\n").utf8)
        var prepared = [try prepare(name: "", bytes: listing)]
        for item in items {
            switch item.payload {
            case .bytes(let bytes):
                prepared.append(try prepare(name: item.name, bytes: bytes))
            case .passthrough(let archive, let entry):
                let range = archive.storedRange(entry)
                prepared.append(Prepared(
                    md5: md5(item.name), length: entry.length, zLengths: Array(archive.blockSizes(entry)),
                    storedSize: range.count, chunks: [], passthrough: (archive, range)))
            }
        }

        let totalZ = prepared.reduce(0) { $0 + $1.zLengths.count }
        let tocSize = 32 + PSARCArchive.entrySize * prepared.count + 2 * totalZ
        var toc = [UInt8]()
        toc.reserveCapacity(tocSize - 32)
        var offset = tocSize
        var zIndex = 0
        for p in prepared {
            guard offset < 1 << 40 else { throw PSARCError.unsupported("archive larger than 1 TB") }
            toc += p.md5
            toc.appendBE(UInt64(zIndex), bytes: 4)
            toc.appendBE(UInt64(p.length), bytes: 5)
            toc.appendBE(UInt64(offset), bytes: 5)
            offset += p.storedSize
            zIndex += p.zLengths.count
        }
        for p in prepared { for z in p.zLengths { toc.appendBE(UInt64(z), bytes: 2) } }
        try TOCCipher.encrypt(&toc)

        var header = PSARCArchive.magic
        header.appendBE(UInt64(PSARCArchive.version), bytes: 4)
        header += PSARCArchive.compression
        header.appendBE(UInt64(tocSize), bytes: 4)
        header.appendBE(UInt64(PSARCArchive.entrySize), bytes: 4)
        header.appendBE(UInt64(prepared.count), bytes: 4)
        header.appendBE(UInt64(PSARCArchive.blockSize), bytes: 4)
        header.appendBE(UInt64(PSARCArchive.flagEncryptedTOC), bytes: 4)

        try handle.write(contentsOf: header + toc)
        for p in prepared {
            if let (archive, range) = p.passthrough {
                try handle.write(contentsOf: archive.data[range])
            } else {
                for chunk in p.chunks { try handle.write(contentsOf: chunk) }
            }
        }
    }

    private static func prepare(name: String, bytes: [UInt8]) throws -> Prepared {
        var zLengths = [UInt16]()
        var chunks = [[UInt8]]()
        var stored = 0
        try bytes.withUnsafeBytes { all in
            var i = 0
            while i < all.count {
                let raw = UnsafeRawBufferPointer(rebasing: all[i..<min(i + PSARCArchive.blockSize, all.count)])
                let compressed = try Zlib.deflate(raw)
                if compressed.count < raw.count {
                    chunks.append(compressed)
                    zLengths.append(UInt16(compressed.count))
                } else {
                    chunks.append(Array(raw))
                    zLengths.append(UInt16(raw.count % PSARCArchive.blockSize))
                }
                stored += chunks[chunks.count - 1].count
                i += PSARCArchive.blockSize
            }
        }
        return Prepared(md5: name.isEmpty ? [UInt8](repeating: 0, count: 16) : md5(name),
                        length: bytes.count, zLengths: zLengths, storedSize: stored, chunks: chunks, passthrough: nil)
    }

    private static func md5(_ name: String) -> [UInt8] { Array(Insecure.MD5.hash(data: Data(name.utf8))) }
}

extension [UInt8] {
    func be32(_ i: Int) -> UInt32 {
        UInt32(self[i]) << 24 | UInt32(self[i + 1]) << 16 | UInt32(self[i + 2]) << 8 | UInt32(self[i + 3])
    }

    func be40(_ i: Int) -> UInt64 {
        var v: UInt64 = 0
        for k in 0..<5 { v = v << 8 | UInt64(self[i + k]) }
        return v
    }

    mutating func appendBE(_ value: UInt64, bytes: Int) {
        for k in stride(from: bytes - 1, through: 0, by: -1) { append(UInt8(truncatingIfNeeded: value >> (8 * UInt64(k)))) }
    }
}
