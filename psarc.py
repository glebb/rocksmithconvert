import zlib
from io import BytesIO
from hashlib import md5

from construct import *

from crypto import aes_bom, pad, decrypt_psarc, encrypt_psarc


class Int40(Construct):
    def _parse(self, stream, context, path):
        return Int64ub.parse(bytes(3) + Bytes(5).parse_stream(stream))

    def _build(self, obj, stream, context, path):
        Bytes(5).build_stream(Int64ub.build(obj)[3:], stream)

    def _sizeof(self, context, path):
        return 5


ENTRY = Struct(
    'md5' / Bytes(16),
    'zindex' / Int32ub,
    'length' / Int40(),
    'offset' / Int40()
)


class BOMAdapter(Adapter):
    def _encode(self, obj, context, path):
        data = Struct(
            'entries' / ENTRY[context.n_entries],
            'zlength' / GreedyRange(Int16ub)
        ).build(obj)
        return aes_bom().encrypt(pad(data))[:len(data)]

    def _decode(self, obj, context, path):
        decrypted_toc = aes_bom().decrypt(pad(obj))[:len(obj)]
        return Struct(
            'entries' / ENTRY[context.n_entries],
            'zlength' / GreedyRange(Int16ub)
        ).parse(decrypted_toc)


VERSION = 65540
ENTRY_SIZE = ENTRY.sizeof()
BLOCK_SIZE = 2**16
ARCHIVE_FLAGS = 4

HEADER = Struct(
    'MAGIC' / Const(b'PSAR'),
    'VERSION' / Const(Int32ub.build(VERSION)),
    'COMPRESSION' / Const(b'zlib'),
    'header_size' / Int32ub,
    'ENTRY_SIZE' / Const(Int32ub.build(ENTRY_SIZE)),
    'n_entries' / Int32ub,
    'BLOCK_SIZE' / Const(Int32ub.build(BLOCK_SIZE)),
    'ARCHIVE_FLAGS' / Const(Int32ub.build(ARCHIVE_FLAGS)),
    'bom' / BOMAdapter(Bytes(this.header_size - 32)),
)


def read_entry(stream, n, bom):
    entry = bom.entries[n]
    stream.seek(entry.offset)
    zlength = bom.zlength[entry.zindex:]

    data = BytesIO()
    length = 0
    for z in zlength:
        if length == entry.length:
            break

        chunk = stream.read(BLOCK_SIZE if z == 0 else z)
        try:
            chunk = zlib.decompress(chunk)
        except zlib.error:
            pass

        data.write(chunk)
        length += len(chunk)

    data = data.getvalue()
    assert (len(data) == entry.length)
    return data


def create_entry(name, data):
    zlength = []
    output = BytesIO()

    for i in range(0, len(data), BLOCK_SIZE):
        raw = data[i:i + BLOCK_SIZE]
        compressed = zlib.compress(raw, zlib.Z_BEST_COMPRESSION)
        if len(compressed) < len(raw):
            output.write(compressed)
            zlength.append(len(compressed))
        else:
            output.write(raw)
            zlength.append(len(raw) % BLOCK_SIZE)

    return {
        'md5': md5(name.encode()).digest() if name != '' else bytes(16),
        'zlength': zlength,
        'length': len(data),
        'data': output.getvalue()
    }


def create_bom(entries):
    offset, zindex, zlength = 0, 0, []
    for entry in entries:
        entry['offset'] = offset
        entry['zindex'] = zindex
        offset += len(entry['data'])
        zindex += len(entry['zlength'])
        zlength += entry['zlength']

    header_size = 32 + ENTRY_SIZE * len(entries) + 2 * len(zlength)
    for entry in entries:
        entry['offset'] += header_size

    return {'entries': entries, 'zlength': zlength, 'header_size': header_size}


class PSARC(Construct):
    def __init__(self, crypto=True):
        self.crypto = crypto
        super().__init__()

    def _parse(self, stream, context, path):
        header = HEADER.parse_stream(stream)
        listing, *entries = [
            read_entry(stream, i, header.bom) for i in range(header.n_entries)
        ]
        listing = listing.decode().splitlines()
        content = dict(zip(listing, entries))
        if self.crypto:
            content = decrypt_psarc(content)
        return content

    def _build(self, content, stream, context, path):
        if self.crypto:
            content = encrypt_psarc(content)

        names = list(sorted(content.keys(), reverse=True))
        data = ['\n'.join(names).encode()] + [content[k] for k in names]

        entries = [create_entry(n, e) for n, e in zip([''] + names, data)]
        bom = create_bom(entries)

        header = HEADER.build(
            {
                'header_size': bom['header_size'],
                'n_entries': len(entries),
                'bom': bom,
            }
        )

        stream.write(header)
        for e in entries:
            stream.write(e['data'])
