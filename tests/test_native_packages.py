"""RS Extended Range native packages (PSXR magic, plain archive, plain SNGs)."""

import io
import json
import struct
import zlib

import pytest

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


def _plain_sng(body: bytes) -> bytes:
    return struct.pack("<II", 0x4A, 1) + bytes(16) + struct.pack("<I", len(body)) + zlib.compress(body) + bytes(56)


def _package(platform: str, magic: bytes = plain_psarc.NATIVE_MAGIC) -> bytes:
    sng_dir, audio, tag = ("macos", "mac", "macos") if platform == "MAC" else ("generic", "windows", "dx9")
    lead = {
        "ArrangementName": "Lead",
        "ArtistName": "Nickelback",
        "SongName": "Burn It to the Ground",
        "ExtendedRange": {"Version": 1},
        "Tuning": {f"string{i}": 0 for i in range(7)},
    }
    hsan = json.dumps({"Entries": {"lead": {"Attributes": lead}}}).encode()
    graph = f'﻿<urn:x> <tag> "{tag}".\n<urn:y> <relpath> "/songs/bin/{sng_dir}/song_lead.sng".\n'
    content = {
        f"songs/bin/{sng_dir}/song_lead.sng": _plain_sng(b"SNXR\x01\x00\x07\x00" + bytes(range(256)) * 200),
        f"songs/bin/{sng_dir}/song_rhythm.sng": _plain_sng(bytes(range(256)) * 100),
        "manifests/songs_dlc_song/songs_dlc_song.hsan": hsan,
        "song_aggregategraph.nt": graph.encode(),
        f"audio/{audio}/123.wem": bytes((i * 7919) % 251 for i in range(150_000)),
        "appid.appid": b"248750",
    }
    out = io.BytesIO()
    plain_psarc.write(content, out, magic)
    return out.getvalue()


def _read(data: bytes):
    return plain_psarc.read(io.BytesIO(data))


def _model(target_dir, platform="MAC", rename="Disabled", app_id="Disabled", files=()):
    return ProcessModel(list(files), str(target_dir), platform, rename, app_id, False)


def test_plain_archive_round_trips():
    data = _package("PC")
    assert data[:4] == b"PSXR"
    assert struct.unpack(">I", data[28:32])[0] == 0  # table of contents not encrypted
    content, magic = _read(data)
    assert magic == b"PSXR"
    assert list(content)[0] == "songs/bin/generic/song_lead.sng"
    assert len(content["audio/windows/123.wem"]) == 150_000
    assert plain_psarc.plain_magic(b"PSXX" + data[4:32]) is None


def test_native_package_converts_pc_to_mac_and_back(tmp_path):
    src = tmp_path / "Nickelback_Burn_v2_rsxr_p.psarc"
    src.write_bytes(_package("PC"))
    (tmp_path / "mac").mkdir()
    (tmp_path / "pc").mkdir()
    converter = _Converter(_Signals())

    mac_path = converter.process(str(src), _model(tmp_path / "mac"))
    assert mac_path == str(tmp_path / "mac" / "Nickelback_Burn_v2_rsxr_m.psarc")
    mac_data = (tmp_path / "mac" / "Nickelback_Burn_v2_rsxr_m.psarc").read_bytes()
    assert mac_data[:4] == b"PSXR"
    assert struct.unpack(">I", mac_data[28:32])[0] == 0
    mac, _ = _read(mac_data)
    pc, _ = _read(src.read_bytes())
    for name in ("song_lead.sng", "song_rhythm.sng"):
        # Plain SNGs stay plain and byte-identical: no Mac key is applied.
        assert mac[f"songs/bin/macos/{name}"] == pc[f"songs/bin/generic/{name}"]
        assert struct.unpack("<II", mac[f"songs/bin/macos/{name}"][:8]) == (0x4A, 1)
    assert mac["audio/mac/123.wem"] == pc["audio/windows/123.wem"]
    graph = mac["song_aggregategraph.nt"].decode("utf-8")
    assert '"macos"' in graph and "bin/macos" in graph and "dx9" not in graph

    back = converter.process(mac_path, _model(tmp_path / "pc", platform="PC"))
    assert back == str(tmp_path / "pc" / "Nickelback_Burn_v2_rsxr_p.psarc")
    again, magic = _read((tmp_path / "pc" / "Nickelback_Burn_v2_rsxr_p.psarc").read_bytes())
    assert magic == b"PSXR" and again == pc


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


def test_plain_stock_package_stays_plain(tmp_path):
    src = tmp_path / "Plain_p.psarc"
    src.write_bytes(_package("PC", magic=b"PSAR"))
    (tmp_path / "out").mkdir()
    result = _Converter(_Signals()).process(str(src), _model(tmp_path / "out", app_id="221680"))
    assert result == str(tmp_path / "out" / "Plain_m.psarc")
    data = (tmp_path / "out" / "Plain_m.psarc").read_bytes()
    content, magic = _read(data)
    assert magic == b"PSAR" and struct.unpack(">I", data[28:32])[0] == 0
    assert content["appid.appid"] == b"221680"
    assert struct.unpack("<II", content["songs/bin/macos/song_lead.sng"][:8]) == (0x4A, 1)


def test_damaged_plain_archive_is_reported(tmp_path):
    data = bytearray(_package("PC"))
    src = tmp_path / "Broken_rsxr_p.psarc"
    src.write_bytes(bytes(data[:2000]))
    with pytest.raises(ValueError, match="Unable to parse PSARC file"):
        _Converter(_Signals())._read_package(str(src))
