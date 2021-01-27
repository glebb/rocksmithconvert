import os
import json
import sys
import re
from psarc import PSARC

def _convert(data, mac2pc):
    if mac2pc:
        data = data.replace('audio/mac', 'audio/windows')
        data = data.replace('bin/macos', 'bin/generic')
    else:
        data = data.replace('audio/windows', 'audio/mac')
        data = data.replace('bin/generic', 'bin/macos')
    return data

def convert(filename, output_directory):
    if filename.endswith('_m.psarc'):
        outname = filename.replace('_m.psarc', '_p.psarc')
        mac2pc = True
    elif filename.endswith('_p.psarc'):
        outname = filename.replace('_p.psarc', '_m.psarc')
        mac2pc = False
    else:
        print('Can only convert between MAC and PC!')
        return

    with open(filename, 'rb') as fh:
        content = PSARC().parse_stream(fh)

    head, tail = os.path.split(outname)
    new_content = {}
    short_name = None

    for path, data in content.items():
        if path.endswith('aggregategraph.nt'):
            data = _convert(data.decode(), mac2pc)
            if mac2pc:
                data = data.replace('macos', 'dx9').encode('ascii')
            else:
                data = data.replace('dx9', 'macos').encode('ascii')
        new_content[_convert(path, mac2pc)] = data
        if not short_name and path.endswith('.hsan') and len(tail[:-8]) > 23:
            short_name = create_short_name(tail, data)
    
    outname2 = output_directory + '/'
    if short_name:
        outname2 += short_name + tail[-8:]
    else:
        outname2 += tail 
    
    if os.path.isfile(outname2):
        print(f"{outname2} already exists.")
        return outname2

    with open(outname2, 'wb') as fh:
        PSARC().build_stream(new_content, fh)
    return outname2

def find_by_key(data, target):
    for key, value in data.items():
        if isinstance(value, dict):
            yield from find_by_key(value, target)
        elif key == target:
            yield value

def create_short_name(original, data):
    data_dict = json.loads(data)
    artist = list(find_by_key(data_dict, "ArtistName"))[0]
    song = list(find_by_key(data_dict, "SongName"))[0]
    dd = False
    if 'dd_' in original.lower():
        dd = True
    if len(artist) > 10:
        artist = re.sub("[^A-Za-z]+", '', artist)[:10]
    max_song_length = 10+(10-len(artist))
    if len(song) > max_song_length:
        song = re.sub("[^A-Za-z]+", '', song)[:max_song_length]
    if dd:
        song += "DD"
    return f"{artist}-{song}".replace(' ','')

if __name__ == "__main__":
    if len(sys.argv) != 3 or not os.path.isfile(sys.argv[1]) or not os.path.isdir(sys.argv[2]):
        print('Give filename and existing output directory as arguments')
        sys.exit()
    convert(sys.argv[1], sys.argv[2])