import zlib

from Crypto.Cipher import AES
from Crypto.Util import Counter

from construct import Int32ul

ARC_KEY = bytes.fromhex(
    'C53DB23870A1A2F71CAE64061FDD0E11'
    '57309DC85204D4C5BFDF25090DF2572C'
)

ARC_IV = bytes.fromhex('E915AA018FEF71FC508132E4BB4CEB42')

MAC_KEY = bytes.fromhex(
    '9821330E34B91F70D0A48CBD62599312'
    '6970CEA09192C0E6CDA676CC9838289D'
)

WIN_KEY = bytes.fromhex(
    'CB648DF3D12A16BF71701414E69619EC'
    '171CCA5D2A142E3E59DE7ADDA18A3A30'
)

PRF_KEY = bytes.fromhex(
    '728B369E24ED0134768511021812AFC0'
    'A3C25D02065F166B4BCC58CD2644F29E'
)

CONFIG_KEY = bytes.fromhex(
    '378B9026EE7DE70B8AF124C1E3097867'
    '0F9EC8FD5E7285A86442DD73068C0473'
)


def pad(data, blocksize=16):
    return data + bytes((blocksize - len(data)) % blocksize)


def aes_bom():
    return AES.new(ARC_KEY, IV=ARC_IV, mode=AES.MODE_CFB, segment_size=128)


def aes_sng(key, ivector):
    iv = int.from_bytes(ivector, 'big')
    ctr = Counter.new(128, initial_value=iv, allow_wraparound=False)
    return AES.new(key, mode=AES.MODE_CTR, counter=ctr)


def decrypt_sng(data, key):
    iv, data = data[8:24], data[24:-56]
    decrypted = aes_sng(key, iv).decrypt(pad(data))
    length, payload = Int32ul.parse(decrypted[:4]), decrypted[4:len(data)]
    payload = zlib.decompress(payload)
    assert len(payload) == length
    return payload


def encrypt_sng(data, key):
    header = Int32ul.build(74) + Int32ul.build(3)
    iv = bytes(16)
    payload = Int32ul.build(len(data))
    payload += zlib.compress(data, zlib.Z_BEST_COMPRESSION)
    encrypted = aes_sng(key, iv).encrypt(pad(payload))[:len(payload)]
    return header + iv + encrypted + bytes(56)


def decrypt_psarc(content):
    # TODO: profile, config
    content = content.copy()
    for k in content:
        if 'songs/bin/macos/' in k:
            content[k] = decrypt_sng(content[k], MAC_KEY)
        elif 'songs/bin/generic/' in k:
            content[k] = decrypt_sng(content[k], WIN_KEY)
    return content


def encrypt_psarc(content):
    # TODO: profile, config
    content = content.copy()
    for k in content:
        if 'songs/bin/macos/' in k:
            content[k] = encrypt_sng(content[k], MAC_KEY)
        elif 'songs/bin/generic/' in k:
            content[k] = encrypt_sng(content[k], WIN_KEY)
    return content
