"""RS Extended Range native packages (PSXR magic, plain archive, plain SNGs).

Synthetic packages cover a 7-string guitar, an 8-string guitar and a 5- and
6-string bass, plus a stock 6/4-string package as a control, converted in both
directions. The two real DotCharter exports are used when they are in
~/Downloads (the tests skip cleanly otherwise).
"""

import io
import json
import struct
import zlib
from pathlib import Path

import pytest
from rocksmith.crypto import MAC_KEY, WIN_KEY, decrypt_sng, encrypt_sng
from rocksmith.psarc import PSARC

from rocksmithconvert import plain_psarc
from rocksmithconvert.models import ProcessModel
from rocksmithconvert.services import _Converter


class _Recorder:
    def __init__(self):
        self.calls = []

    def emit(self, value):
        self.calls.append(value)


class _Signals:
    def __init__(self):
        self.info = _Recorder()
        self.update = _Recorder()


# --- Fixtures -----------------------------------------------------------------

SONG = "song"
LAYOUT = {
    # platform: (SNG folder, audio folder, aggregate graph tag, name suffix)
    "PC": ("generic", "windows", "dx9", "_p"),
    "MAC": ("macos", "mac", "macos", "_m"),
}
KEYS = {"PC": WIN_KEY, "MAC": MAC_KEY}
OTHER = {"PC": "MAC", "MAC": "PC"}

# (arrangement, strings, bass): stock charts have 6 (guitar) or 4 (bass) strings.
PACKAGES = {
    "7-string": [("lead", 7, False), ("rhythm", 6, False), ("bass", 4, True)],
    "8-string": [("lead", 8, False)],
    "5-and-6-string-bass": [("bass", 5, True), ("bass2", 6, True), ("lead", 6, False)],
}
STOCK = [("lead", 6, False), ("bass", 4, True)]


def _extended(strings: int, bass: bool) -> bool:
    return strings > (4 if bass else 6)


def _chart(strings: int, bass: bool) -> bytes:
    """An SNG body: SNXR (as DotCharter writes it: version 1, bass flag, string
    count) with N-wide records for an extended chart, otherwise stock-looking bytes."""
    records = bytes((i * 31 + strings) % 256 for i in range(strings * 4000))
    if _extended(strings, bass):
        return b"SNXR" + bytes([1, int(bass), strings, 0]) + records
    return struct.pack("<I", 471) + records


def _plain_sng(body: bytes) -> bytes:
    return struct.pack("<II", 0x4A, 1) + bytes(16) + struct.pack("<I", len(body)) + zlib.compress(body) + bytes(56)


def _manifest(arrangement: str, strings: int, bass: bool) -> bytes:
    attributes = {
        "ArrangementName": "Bass" if bass else arrangement.capitalize(),
        "ArtistName": "Nickelback",
        "SongName": "Burn It to the Ground",
        "Tuning": {f"string{i}": 0 for i in range(strings)},
    }
    if _extended(strings, bass):
        attributes["ExtendedRange"] = {"Version": 1}
    return json.dumps({"Entries": {arrangement: {"Attributes": attributes}}}).encode()


def _content(platform: str, arrangements, encrypt: bool = False):
    """Entries of a package, in archive order, with every SNG plain unless ``encrypt``."""
    sng_dir, audio, tag, _ = LAYOUT[platform]
    content = {}
    graph = ['﻿<urn:audio> <http://emergent.net/aweb/1.0/tag> "%s".' % tag]
    for name, strings, bass in arrangements:
        body = _chart(strings, bass)
        sng = encrypt_sng(body, KEYS[platform]) if encrypt else _plain_sng(body)
        content[f"songs/bin/{sng_dir}/{SONG}_{name}.sng"] = sng
        graph.append(f'<urn:{name}> <http://emergent.net/aweb/1.0/relpath> "/songs/bin/{sng_dir}/{SONG}_{name}.sng".')
    for name, strings, bass in arrangements:
        content[f"manifests/songs_dlc_{SONG}/{SONG}_{name}.json"] = _manifest(name, strings, bass)
    content[f"manifests/songs_dlc_{SONG}/songs_dlc_{SONG}.hsan"] = _manifest(*arrangements[0])
    graph.append(f'<urn:wem> <http://emergent.net/aweb/1.0/relpath> "/audio/{audio}/123.wem".')
    content[f"{SONG}_aggregategraph.nt"] = ("\n".join(graph) + "\n").encode()
    # Incompressible, multi-block "audio" exercises stored blocks.
    content[f"audio/{audio}/123.wem"] = bytes((i * 7919) % 251 for i in range(150_000))
    content["appid.appid"] = b"248750"
    return content


def _write(content, magic=plain_psarc.NATIVE_MAGIC, stock_toc=False) -> bytes:
    out = io.BytesIO()
    if stock_toc:
        PSARC(False).build_stream(content, out)  # encrypted table of contents, entries as given
    else:
        plain_psarc.write(content, out, magic)
    return out.getvalue()


def _package(platform: str, arrangements=PACKAGES["7-string"], magic=plain_psarc.NATIVE_MAGIC) -> bytes:
    return _write(_content(platform, arrangements), magic)


def _stock_package(platform: str) -> bytes:
    return _write(_content(platform, STOCK, encrypt=True), stock_toc=True)


def _read_any(data: bytes):
    """(entries as stored, magic or None for a stock archive)."""
    if plain_psarc.plain_magic(data[:32]):
        return plain_psarc.read(io.BytesIO(data))
    return PSARC(False).parse_stream(io.BytesIO(data)), None


def _read(data: bytes):
    return plain_psarc.read(io.BytesIO(data))


def _flags(data: bytes) -> int:
    return struct.unpack(">I", data[28:32])[0]


def _model(target_dir, platform="MAC", rename="Disabled", app_id="Disabled", files=(), overwrite=False):
    return ProcessModel(list(files), str(target_dir), platform, rename, app_id, overwrite)


def _mapped(name: str, target: str) -> str:
    return _Converter(_Signals())._convert(name, target == "PC")


def _expected_graph(graph: bytes, target: str) -> bytes:
    text = _mapped(graph.decode(), target)
    text = text.replace("macos", "dx9") if target == "PC" else text.replace("dx9", "macos")
    return text.encode()


def _convert(src: Path, out: Path, target: str, **model) -> Path:
    out.mkdir(exist_ok=True)
    result = _Converter(_Signals()).process(str(src), _model(out, platform=target, **model))
    return Path(result)


# --- The plain archive reader and writer ---------------------------------------


def test_plain_archive_round_trips():
    data = _package("PC")
    assert data[:4] == b"PSXR"
    assert _flags(data) == 0  # table of contents not encrypted
    content, magic = _read(data)
    assert magic == b"PSXR"
    assert content == _content("PC", PACKAGES["7-string"])
    assert list(content)[0] == "songs/bin/generic/song_lead.sng"
    assert plain_psarc.plain_magic(b"PSXX" + data[4:32]) is None
    out = io.BytesIO()
    plain_psarc.write(content, out, magic)
    assert out.getvalue() == data


def _raw_archive(listing: bytes, blobs) -> bytes:
    """A plain PSXR archive with ``listing`` as entry 0 and every block stored uncompressed."""
    z_lengths, entries, chunks, offset = [], [], [], 0
    for blob in [listing, *blobs]:
        entries.append((len(z_lengths), len(blob), offset))
        for p in range(0, len(blob), plain_psarc.BLOCK_SIZE):
            raw = blob[p : p + plain_psarc.BLOCK_SIZE]
            chunks.append(raw)
            z_lengths.append(len(raw) % plain_psarc.BLOCK_SIZE)
            offset += len(raw)
    toc_size = plain_psarc.HEADER.size + plain_psarc.ENTRY_SIZE * len(entries) + 2 * len(z_lengths)
    out = plain_psarc.HEADER.pack(
        b"PSXR", plain_psarc.VERSION, b"zlib", toc_size, plain_psarc.ENTRY_SIZE, len(entries), plain_psarc.BLOCK_SIZE, 0
    )
    for z_index, length, start in entries:
        out += bytes(16) + struct.pack(">I", z_index) + length.to_bytes(5, "big") + (start + toc_size).to_bytes(5, "big")
    return out + b"".join(struct.pack(">H", z) for z in z_lengths) + b"".join(chunks)


def test_plain_archive_listing_with_crlf_line_ends():
    # The Swift reader and pyrocksmith (splitlines) accept CRLF listings; so does this one.
    content = {"a/one.txt": b"1" * 10, "b/two.txt": b"2" * 70_000}
    parsed, magic = _read(_raw_archive("\r\n".join(content).encode(), content.values()))
    assert magic == b"PSXR" and parsed == content


# --- Conversion of extended-range and stock packages, both directions -----------


@pytest.mark.parametrize("source", ["PC", "MAC"])
@pytest.mark.parametrize("kind", list(PACKAGES))
def test_native_package_converts_both_ways(tmp_path, kind, source):
    target = OTHER[source]
    arrangements = PACKAGES[kind]
    src = tmp_path / f"Nickelback_Burn_v2_rsxr{LAYOUT[source][3]}.psarc"
    original = _package(source, arrangements)
    src.write_bytes(original)

    converted = _convert(src, tmp_path / "a", target)
    assert converted.name == f"Nickelback_Burn_v2_rsxr{LAYOUT[target][3]}.psarc"
    data = converted.read_bytes()
    assert data[:4] == b"PSXR" and _flags(data) == 0
    out, magic = _read(data)
    before, _ = _read(original)
    assert magic == b"PSXR"
    # Same entries in the same order, only the platform folders renamed.
    assert list(out) == [_mapped(name, target) for name in before]
    for name, value in before.items():
        if name.endswith("aggregategraph.nt"):
            assert out[name] == _expected_graph(value, target)
        else:
            # Charts (plain SNGs, extended or stock), manifests and audio byte for byte.
            assert out[_mapped(name, target)] == value, name
    sng_dir = LAYOUT[target][0]
    for name, strings, bass in arrangements:
        sng = out[f"songs/bin/{sng_dir}/{SONG}_{name}.sng"]
        assert struct.unpack("<II", sng[:8]) == (0x4A, 1)
        body = zlib.decompress(sng[28:-56])
        if _extended(strings, bass):
            assert body[:8] == b"SNXR" + bytes([1, int(bass), strings, 0])
        manifest = json.loads(out[f"manifests/songs_dlc_{SONG}/{SONG}_{name}.json"])
        assert len(manifest["Entries"][name]["Attributes"]["Tuning"]) == strings
    graph = out[f"{SONG}_aggregategraph.nt"].decode()
    assert f'"{LAYOUT[target][2]}"' in graph and f'"{LAYOUT[source][2]}"' not in graph

    back = _convert(converted, tmp_path / "b", source)
    assert back.name == src.name
    again, magic = _read(back.read_bytes())
    assert magic == b"PSXR" and list(again) == list(before) and again == before
    # Converting the converted file again gives the same bytes: nothing drifts.
    assert _convert(back, tmp_path / "c", target).read_bytes() == data


@pytest.mark.parametrize("source", ["PC", "MAC"])
def test_stock_package_converts_both_ways(tmp_path, source):
    target = OTHER[source]
    src = tmp_path / f"Ozzy_Crazy_Train{LAYOUT[source][3]}.psarc"
    original = _stock_package(source)
    src.write_bytes(original)

    converted = _convert(src, tmp_path / "a", target)
    assert converted.name == f"Ozzy_Crazy_Train{LAYOUT[target][3]}.psarc"
    data = converted.read_bytes()
    assert data[:4] == b"PSAR" and _flags(data) == 4  # stays a stock archive
    out, magic = _read_any(data)
    before, _ = _read_any(original)
    assert magic is None
    assert sorted(out) == sorted(_mapped(name, target) for name in before)
    for name, strings, bass in STOCK:
        sng = out[f"songs/bin/{LAYOUT[target][0]}/{SONG}_{name}.sng"]
        assert struct.unpack("<II", sng[:8]) == (0x4A, 3)
        assert decrypt_sng(sng, KEYS[target]) == _chart(strings, bass)  # re-keyed for the target
    for name, value in before.items():
        if not name.endswith((".sng", "aggregategraph.nt")):
            assert out[_mapped(name, target)] == value
    assert out[f"{SONG}_aggregategraph.nt"] == _expected_graph(before[f"{SONG}_aggregategraph.nt"], target)

    back = _convert(converted, tmp_path / "b", source)
    again, _ = _read_any(back.read_bytes())
    assert sorted(again) == sorted(before)
    for name, strings, bass in STOCK:
        assert decrypt_sng(again[f"songs/bin/{LAYOUT[source][0]}/{SONG}_{name}.sng"], KEYS[source]) == _chart(strings, bass)


def test_native_package_names_keep_the_rsxr_tag(tmp_path):
    converter = _Converter(_Signals())
    out = tmp_path / "out"
    out.mkdir()
    tagged = tmp_path / "long_name_rsxr_p.psarc"
    tagged.write_bytes(_package("PC"))
    assert converter.process(str(tagged), _model(out, rename="Short")) == str(out / "Nickelback-BurnIttoth_rsxr_m.psarc")
    assert converter.process(str(tagged), _model(out, platform="Disabled", rename="Full")) == "Nickelback-BurnIttotheGround_rsxr_p.psarc"

    untagged = tmp_path / "Untagged_p.psarc"
    untagged.write_bytes(_package("PC"))
    assert converter.process(str(untagged), _model(out)) == str(out / "Untagged_rsxr_m.psarc")


def test_rename_only_tags_an_untagged_native_package(tmp_path):
    # Same rule as a conversion (and the Swift app): a PSXR package's new name carries _rsxr.
    src = tmp_path / "Untagged_p.psarc"
    src.write_bytes(_package("PC"))
    out = tmp_path / "out"
    out.mkdir()
    name = _Converter(_Signals()).process(str(src), _model(out, platform="Disabled", rename="Full"))
    assert name == "Nickelback-BurnIttotheGround_rsxr_p.psarc"
    assert (out / name).read_bytes() == src.read_bytes()


def test_plain_stock_package_stays_plain(tmp_path):
    src = tmp_path / "Plain_p.psarc"
    src.write_bytes(_package("PC", magic=b"PSAR"))
    (tmp_path / "out").mkdir()
    result = _Converter(_Signals()).process(str(src), _model(tmp_path / "out", app_id="221680"))
    assert result == str(tmp_path / "out" / "Plain_m.psarc")
    data = (tmp_path / "out" / "Plain_m.psarc").read_bytes()
    content, magic = _read(data)
    assert magic == b"PSAR" and _flags(data) == 0
    assert content["appid.appid"] == b"221680"
    assert struct.unpack("<II", content["songs/bin/macos/song_lead.sng"][:8]) == (0x4A, 1)


# --- Fixes -----------------------------------------------------------------------


@pytest.mark.parametrize("app_id", ["", "   ", "abc", "12345678901", "22 1680", "２２１６８０"])
@pytest.mark.parametrize("stock", [False, True])
def test_invalid_app_id_is_refused(tmp_path, app_id, stock):
    # The GUI's App ID box is editable: clearing it used to write an empty appid.appid.
    src = tmp_path / "Song_p.psarc"
    src.write_bytes(_stock_package("PC") if stock else _package("PC"))
    out = tmp_path / "out"
    out.mkdir()
    signals = _Signals()
    with pytest.raises(ValueError, match="App ID must be 1-10 digits"):
        _Converter(signals).process(str(src), _model(out, app_id=app_id))
    assert list(out.iterdir()) == []
    assert any("App ID must be 1-10 digits" in call for call in signals.info.calls)


def test_app_id_is_trimmed(tmp_path):
    src = tmp_path / "Song_rsxr_p.psarc"
    src.write_bytes(_package("PC"))
    result = _convert(src, tmp_path / "out", "MAC", app_id=" 221680 ")
    content, _ = _read(result.read_bytes())
    assert content["appid.appid"] == b"221680"


def test_encrypted_sng_in_plain_archive_is_rekeyed(tmp_path):
    # A plain table of contents does not make the songs plain: an encrypted SNG still
    # needs the target's key (it used to be copied with the PC key into a Mac package).
    content = _content("PC", STOCK, encrypt=True)
    src = tmp_path / "Mixed_p.psarc"
    src.write_bytes(_write(content, magic=b"PSAR"))
    out, magic = _read(_convert(src, tmp_path / "out", "MAC").read_bytes())
    assert magic == b"PSAR"
    for name, strings, bass in STOCK:
        assert decrypt_sng(out[f"songs/bin/macos/{SONG}_{name}.sng"], MAC_KEY) == _chart(strings, bass)


def test_plain_sng_in_stock_archive_stays_plain(tmp_path):
    # An encrypted table of contents with a plain SNG beside an encrypted one: the
    # plain one is copied, the encrypted one re-keyed (both used to be encrypted twice).
    content = _content("PC", STOCK, encrypt=True)
    plain = _plain_sng(_chart(7, False))
    content["songs/bin/generic/song_lead7.sng"] = plain
    src = tmp_path / "Mixed_p.psarc"
    src.write_bytes(_write(content, stock_toc=True))
    out, _ = _read_any(_convert(src, tmp_path / "out", "MAC").read_bytes())
    assert out["songs/bin/macos/song_lead7.sng"] == plain
    assert decrypt_sng(out["songs/bin/macos/song_lead.sng"], MAC_KEY) == _chart(6, False)


def test_stock_package_with_empty_sng_placeholder(tmp_path):
    # Zero-length SNG placeholders (e.g. RS1 compatibility packs) made the whole package
    # fall back to an undecrypted read, and every SNG was then encrypted a second time.
    content = _content("PC", STOCK, encrypt=True)
    content["songs/bin/generic/song_placeholder.sng"] = b""
    src = tmp_path / "Compat_p.psarc"
    src.write_bytes(_write(content, stock_toc=True))
    out, _ = _read_any(_convert(src, tmp_path / "out", "MAC").read_bytes())
    assert out["songs/bin/macos/song_placeholder.sng"] == b""
    assert decrypt_sng(out["songs/bin/macos/song_lead.sng"], MAC_KEY) == _chart(6, False)


def test_sng_with_the_other_platforms_key_is_rekeyed(tmp_path):
    content = _content("PC", STOCK, encrypt=True)
    content["songs/bin/generic/song_lead.sng"] = encrypt_sng(_chart(6, False), MAC_KEY)  # mislabelled
    src = tmp_path / "Odd_p.psarc"
    src.write_bytes(_write(content, stock_toc=True))
    out, _ = _read_any(_convert(src, tmp_path / "out", "MAC").read_bytes())
    assert decrypt_sng(out["songs/bin/macos/song_lead.sng"], MAC_KEY) == _chart(6, False)


def test_damaged_plain_sng_is_reported(tmp_path):
    content = _content("PC", PACKAGES["8-string"])
    sng = bytearray(content["songs/bin/generic/song_lead.sng"])
    sng[40] ^= 0xFF
    content["songs/bin/generic/song_lead.sng"] = bytes(sng)
    src = tmp_path / "Broken_rsxr_p.psarc"
    src.write_bytes(_write(content))
    (tmp_path / "out").mkdir()
    with pytest.raises(ValueError, match="song_lead.sng"):
        _Converter(_Signals()).process(str(src), _model(tmp_path / "out"))
    assert list((tmp_path / "out").iterdir()) == []


def test_damaged_plain_archive_is_reported(tmp_path):
    data = bytearray(_package("PC"))
    src = tmp_path / "Broken_rsxr_p.psarc"
    src.write_bytes(bytes(data[:2000]))
    with pytest.raises(ValueError, match="Unable to parse PSARC file"):
        _Converter(_Signals())._read_package(str(src))


# --- Real DotCharter exports ------------------------------------------------------

REAL = {
    # file: {arrangement suffix: (strings, bass)} for the extended charts
    "Nickelback_Burn-It-To-The-Ground_Dell_v2_3_rsxr_p.psarc": {"_lead.sng": (7, False), "_bass.sng": (5, True)},
    "Fear-Factory_Soul-Hacker_Dell_v0_2_rsxr_p.psarc": {"_lead.sng": (8, False)},
}


@pytest.mark.parametrize("filename", list(REAL))
def test_real_native_package_converts_both_ways(tmp_path, filename):
    src = Path.home() / "Downloads" / filename
    if not src.is_file():
        pytest.skip(f"{filename} is not in ~/Downloads")
    original = src.read_bytes()
    before, magic = _read(original)
    assert magic == b"PSXR"

    mac = _convert(src, tmp_path / "mac", "MAC")
    assert mac.name == filename.replace("_rsxr_p.psarc", "_rsxr_m.psarc")
    data = mac.read_bytes()
    assert data[:4] == b"PSXR" and _flags(data) == 0
    out, _ = _read(data)
    assert list(out) == [_mapped(name, "MAC") for name in before]
    assert any(name.startswith("songs/bin/macos/") for name in out)
    assert any(name.startswith("audio/mac/") for name in out)
    assert not any("generic" in name or "windows" in name for name in out)
    for name, value in before.items():
        if name.endswith("aggregategraph.nt"):
            assert out[name] == _expected_graph(value, "MAC")
        else:
            # Charts and audio byte for byte; only the folder names changed.
            assert out[_mapped(name, "MAC")] == value, name
    for suffix, (strings, bass) in REAL[filename].items():
        sng = next(value for name, value in out.items() if name.endswith(suffix))
        assert struct.unpack("<II", sng[:8]) == (0x4A, 1)
        assert zlib.decompress(sng[28:-56])[:8] == b"SNXR" + bytes([1, int(bass), strings, 0])

    pc = _convert(mac, tmp_path / "pc", "PC")
    assert pc.name == filename
    again, _ = _read(pc.read_bytes())
    assert list(again) == list(before) and again == before
