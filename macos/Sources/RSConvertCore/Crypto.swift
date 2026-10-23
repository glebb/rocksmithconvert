import CommonCrypto
import Foundation

/// Rocksmith 2014 keys (public knowledge; same values as pyrocksmith and the .NET Rocksmith toolkit).
enum Keys {
    /// PSARC table-of-contents key, AES-256-CFB128.
    static let tocKey = bytes("C53DB23870A1A2F71CAE64061FDD0E1157309DC85204D4C5BFDF25090DF2572C")
    static let tocIV = bytes("E915AA018FEF71FC508132E4BB4CEB42")
    /// SNG keys, AES-256-CTR.
    static let sngMac = bytes("9821330E34B91F70D0A48CBD625993126970CEA09192C0E6CDA676CC9838289D")
    static let sngPC = bytes("CB648DF3D12A16BF71701414E69619EC171CCA5D2A142E3E59DE7ADDA18A3A30")

    private static func bytes(_ hex: String) -> [UInt8] {
        var out = [UInt8]()
        out.reserveCapacity(hex.count / 2)
        var it = hex.makeIterator()
        while let hi = it.next(), let lo = it.next() {
            out.append(UInt8(String([hi, lo]), radix: 16)!)
        }
        return out
    }
}

/// Minimal AES-256 built on CommonCrypto's ECB primitive. CFB128 and CTR are
/// composed explicitly so their exact semantics (full-block feedback, 128-bit
/// big-endian counter) match what the game and existing tools use.
struct AES256 {
    private let cryptor: CCCryptorRef

    init(key: [UInt8]) throws {
        precondition(key.count == kCCKeySizeAES256)
        var ref: CCCryptorRef?
        let status = CCCryptorCreateWithMode(
            CCOperation(kCCEncrypt), CCMode(kCCModeECB), CCAlgorithm(kCCAlgorithmAES),
            CCPadding(ccNoPadding), nil, key, key.count, nil, 0, 0, 0, &ref)
        guard status == kCCSuccess, let ref else { throw PSARCError.crypto(Int(status)) }
        cryptor = ref
    }

    func release() { CCCryptorRelease(cryptor) }

    /// Encrypts whole 16-byte blocks in place.
    private func ecb(_ buf: UnsafeMutableRawBufferPointer) throws {
        precondition(buf.count % 16 == 0)
        guard buf.count > 0 else { return }
        var moved = 0
        let status = CCCryptorUpdate(cryptor, buf.baseAddress, buf.count, buf.baseAddress, buf.count, &moved)
        guard status == kCCSuccess else { throw PSARCError.crypto(Int(status)) }
    }

    /// AES-CFB128. Sequential by nature; only used for the small PSARC TOC.
    func cfb(_ data: inout [UInt8], iv: [UInt8], decrypt: Bool) throws {
        var feedback = iv
        var offset = 0
        while offset < data.count {
            try feedback.withUnsafeMutableBytes { try ecb($0) }
            let n = min(16, data.count - offset)
            for i in 0..<n {
                let c = data[offset + i]
                let p = c ^ feedback[i]
                data[offset + i] = p
                feedback[i] = decrypt ? c : p
            }
            offset += n
        }
    }

    /// AES-CTR keystream XOR over `data`, with a 128-bit big-endian counter starting at `iv`.
    /// Keystream is produced in bulk chunks so the ECB call is amortised.
    func ctr(_ data: UnsafeMutableRawBufferPointer, iv: [UInt8]) throws {
        var counter = iv
        let chunkBlocks = 4096
        var stream = [UInt8](repeating: 0, count: chunkBlocks * 16)
        var offset = 0
        while offset < data.count {
            let remaining = data.count - offset
            let blocks = min(chunkBlocks, (remaining + 15) / 16)
            for b in 0..<blocks {
                stream.replaceSubrange(b * 16..<(b * 16 + 16), with: counter)
                Self.increment(&counter)
            }
            try stream.withUnsafeMutableBytes { try ecb(UnsafeMutableRawBufferPointer(rebasing: $0[0..<(blocks * 16)])) }
            let n = min(remaining, blocks * 16)
            for i in 0..<n { data[offset + i] ^= stream[i] }
            offset += n
        }
    }

    private static func increment(_ counter: inout [UInt8]) {
        var i = 15
        while i >= 0 {
            counter[i] &+= 1
            if counter[i] != 0 { return }
            i -= 1
        }
    }
}

enum TOCCipher {
    static func decrypt(_ data: inout [UInt8]) throws {
        let aes = try AES256(key: Keys.tocKey)
        defer { aes.release() }
        try aes.cfb(&data, iv: Keys.tocIV, decrypt: true)
    }

    static func encrypt(_ data: inout [UInt8]) throws {
        let aes = try AES256(key: Keys.tocKey)
        defer { aes.release() }
        try aes.cfb(&data, iv: Keys.tocIV, decrypt: false)
    }
}
