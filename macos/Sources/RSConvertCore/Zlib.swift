import CZlib
import Foundation

enum Zlib {
    struct Inflated {
        var output: [UInt8]
        /// Bytes of input consumed up to the end of the zlib stream.
        var consumed: Int
    }

    /// Inflates a complete zlib stream. Output is capped at `maxOutput` bytes so a
    /// hostile archive cannot use decompression to exhaust memory.
    static func inflate(_ input: UnsafeRawBufferPointer, maxOutput: Int) throws -> Inflated {
        var stream = z_stream()
        guard inflateInit_(&stream, ZLIB_VERSION, Int32(MemoryLayout<z_stream>.size)) == Z_OK else {
            throw PSARCError.corrupt("zlib init failed")
        }
        defer { inflateEnd(&stream) }

        // One spare byte lets us detect output that exceeds the cap.
        var output = [UInt8](repeating: 0, count: maxOutput + 1)
        let status: Int32 = output.withUnsafeMutableBytes { out in
            stream.next_in = UnsafeMutablePointer(mutating: input.bindMemory(to: Bytef.self).baseAddress)
            stream.avail_in = uInt(input.count)
            stream.next_out = out.bindMemory(to: Bytef.self).baseAddress
            stream.avail_out = uInt(out.count)
            return CZlib.inflate(&stream, Z_FINISH)
        }
        guard status == Z_STREAM_END else {
            throw PSARCError.corrupt(status == Z_BUF_ERROR && stream.avail_out == 0
                ? "decompressed data larger than declared" : "invalid zlib data (\(status))")
        }
        output.removeLast(output.count - Int(stream.total_out))
        return Inflated(output: output, consumed: Int(stream.total_in))
    }

    static func deflate(_ input: UnsafeRawBufferPointer, level: Int32 = Z_BEST_COMPRESSION) throws -> [UInt8] {
        var stream = z_stream()
        guard deflateInit_(&stream, level, ZLIB_VERSION, Int32(MemoryLayout<z_stream>.size)) == Z_OK else {
            throw PSARCError.corrupt("zlib init failed")
        }
        defer { deflateEnd(&stream) }
        var output = [UInt8](repeating: 0, count: Int(deflateBound(&stream, uLong(input.count))))
        let status: Int32 = output.withUnsafeMutableBytes { out in
            stream.next_in = UnsafeMutablePointer(mutating: input.bindMemory(to: Bytef.self).baseAddress)
            stream.avail_in = uInt(input.count)
            stream.next_out = out.bindMemory(to: Bytef.self).baseAddress
            stream.avail_out = uInt(out.count)
            return CZlib.deflate(&stream, Z_FINISH)
        }
        guard status == Z_STREAM_END else { throw PSARCError.corrupt("zlib compress failed (\(status))") }
        output.removeLast(output.count - Int(stream.total_out))
        return output
    }
}
