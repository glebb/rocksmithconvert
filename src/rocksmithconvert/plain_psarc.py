"""Plain PSARC archives: a table of contents that is not encrypted.

pyrocksmith only reads and writes the stock archive (magic ``PSAR`` with an
encrypted table of contents). Two kinds of package are plain instead:

- RS Extended Range "native" packages (``<name>_rsxr_p.psarc``), which use the
  magic ``PSXR`` (docs/release/NATIVE-FORMAT.md in
  github.com/SomeeName/rs-extended-range);
- DotCharter's earlier plain exports, with the stock magic.

Their SNG entries are usually plain too (flags 1: compressed, not encrypted),
so they have no platform key: a PC <-> Mac conversion only renames paths and
edits the aggregate graph (an encrypted SNG is still re-keyed, see
``services._Converter._convert_sng``). This module reads such an archive into
``{name: bytes}`` and writes it back with the same magic and an unencrypted
table of contents.
"""

import re
import struct
import zlib
from hashlib import md5
from typing import BinaryIO, Dict, Optional, Tuple

STOCK_MAGIC = b"PSAR"
NATIVE_MAGIC = b"PSXR"
VERSION = 0x00010004
ENTRY_SIZE = 30
BLOCK_SIZE = 65536
FLAG_ENCRYPTED_TOC = 4
HEADER = struct.Struct(">4sI4sIIIII")


SNG_MAGIC = 74
SNG_FLAGS_PLAIN = 1
SNG_HEADER_SIZE = 24  # magic, flags, 16-byte IV
SNG_SIGNATURE_SIZE = 56
SNG_MAX_SIZE = 64 << 20


def sng_is_plain(sng: bytes) -> bool:
    """True when an SNG wrapper says compressed and not encrypted (flags 1)."""
    return len(sng) >= 8 and struct.unpack("<II", sng[:8]) == (SNG_MAGIC, SNG_FLAGS_PLAIN)


def check_plain_sng(sng: bytes) -> None:
    """Raises ValueError unless a plain SNG's zlib stream inflates to its declared size,
    so a damaged chart is reported instead of copied. The bytes are kept as they are."""
    if len(sng) <= SNG_HEADER_SIZE + 4 + SNG_SIGNATURE_SIZE:
        raise ValueError("plain SNG too short")
    (length,) = struct.unpack("<I", sng[SNG_HEADER_SIZE : SNG_HEADER_SIZE + 4])
    if length > SNG_MAX_SIZE:
        raise ValueError(f"plain SNG declares {length} bytes")
    try:
        body = zlib.decompressobj().decompress(sng[SNG_HEADER_SIZE + 4 :], length + 1)
    except zlib.error as error:
        raise ValueError(f"damaged plain SNG: {error}") from None
    if len(body) != length:
        raise ValueError("plain SNG length mismatch")


def plain_magic(header: bytes) -> Optional[bytes]:
    """The magic when ``header`` (the first 32 bytes) starts a plain archive, else None."""
    if len(header) < HEADER.size:
        return None
    magic, version, compression, _, entry_size, _, block_size, flags = HEADER.unpack(header[: HEADER.size])
    if magic not in (STOCK_MAGIC, NATIVE_MAGIC) or compression != b"zlib":
        return None
    if version != VERSION or entry_size != ENTRY_SIZE or block_size != BLOCK_SIZE:
        return None
    return None if flags & FLAG_ENCRYPTED_TOC else magic


def read(stream: BinaryIO) -> Tuple[Dict[str, bytes], bytes]:
    """Reads a plain archive; returns its entries in archive order and its magic."""
    data = stream.read()
    magic = plain_magic(data)
    if magic is None:
        raise ValueError("not a plain PSARC archive")
    _, _, _, toc_size, _, count, _, _ = HEADER.unpack(data[: HEADER.size])
    if count < 1 or toc_size < HEADER.size + count * ENTRY_SIZE or toc_size > len(data):
        raise ValueError("damaged PSARC table of contents")
    z_start = HEADER.size + count * ENTRY_SIZE
    z_lengths = struct.unpack(f">{(toc_size - z_start) // 2}H", data[z_start : z_start + (toc_size - z_start) // 2 * 2])

    blobs = []
    for i in range(count):
        entry = data[HEADER.size + i * ENTRY_SIZE : HEADER.size + (i + 1) * ENTRY_SIZE]
        z_index = struct.unpack(">I", entry[16:20])[0]
        length = int.from_bytes(entry[20:25], "big")
        position = int.from_bytes(entry[25:30], "big")
        out = bytearray()
        while len(out) < length:
            if z_index >= len(z_lengths):
                raise ValueError("damaged PSARC: block index out of range")
            stored = z_lengths[z_index] or BLOCK_SIZE
            expected = min(BLOCK_SIZE, length - len(out))
            block = data[position : position + stored]
            if len(block) != stored:
                raise ValueError("damaged PSARC: entry extends past end of file")
            if stored == expected:
                out += block  # stored uncompressed
            else:
                try:
                    chunk = zlib.decompressobj().decompress(block, expected + 1)
                except zlib.error as error:
                    raise ValueError(f"damaged PSARC block: {error}") from None
                if len(chunk) != expected:
                    raise ValueError("damaged PSARC: block size mismatch")
                out += chunk
            position += stored
            z_index += 1
        blobs.append(bytes(out))

    names = re.split(r"\r\n|\r|\n", blobs[0].decode())
    if len(names) < count - 1:
        raise ValueError("damaged PSARC: file listing is too short")
    return dict(zip(names, blobs[1:])), magic


def write(content: Dict[str, bytes], stream: BinaryIO, magic: bytes) -> None:
    """Writes ``content`` (in its order) as a plain archive with ``magic``."""
    if magic not in (STOCK_MAGIC, NATIVE_MAGIC):
        raise ValueError(f"unsupported PSARC magic {magic!r}")
    names = list(content)
    blobs = ["\n".join(names).encode()] + [content[name] for name in names]
    z_lengths = []
    chunks = []
    entries = []
    offset = 0
    for i, blob in enumerate(blobs):
        z_index = len(z_lengths)
        start = offset
        for p in range(0, len(blob), BLOCK_SIZE):
            raw = blob[p : p + BLOCK_SIZE]
            packed = zlib.compress(raw, zlib.Z_BEST_COMPRESSION)
            chunk = packed if len(packed) < len(raw) else raw
            chunks.append(chunk)
            z_lengths.append(len(chunk) % BLOCK_SIZE)
            offset += len(chunk)
        digest = bytes(16) if i == 0 else md5(names[i - 1].encode()).digest()
        entries.append((digest, z_index, len(blob), start))
    toc_size = HEADER.size + ENTRY_SIZE * len(blobs) + 2 * len(z_lengths)
    stream.write(HEADER.pack(magic, VERSION, b"zlib", toc_size, ENTRY_SIZE, len(blobs), BLOCK_SIZE, 0))
    for digest, z_index, length, start in entries:
        stream.write(digest + struct.pack(">I", z_index) + length.to_bytes(5, "big") + (start + toc_size).to_bytes(5, "big"))
    stream.write(b"".join(struct.pack(">H", z) for z in z_lengths))
    for chunk in chunks:
        stream.write(chunk)
