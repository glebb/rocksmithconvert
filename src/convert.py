import os
import json
import sys
import re
import argparse
from shutil import copy2
from psarc import PSARC

def _convert(data, mac2pc):
    if mac2pc:
        data = data.replace('audio/mac', 'audio/windows')
        data = data.replace('bin/macos', 'bin/generic')
    else:
        data = data.replace('audio/windows', 'audio/mac')
        data = data.replace('bin/generic', 'bin/macos')
    return data

def rename(filename, output_directory):
    head, tail = os.path.split(filename)
    short_name = None
    
    with open(filename, 'rb') as fh:
        content = PSARC().parse_stream(fh)
    for path, data in content.items():
        if path.endswith('.hsan'):
            short_name = create_short_name(tail, data)
            break
    outname = output_directory + '/' + short_name
    if os.path.isfile(outname):
        print(f"{outname} already exists.")
        return outname       
    copy2(filename, outname)
    return short_name

def convert(filename, output_directory, use_shortnames=False):
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
    short_name = None

    new_content = {}
    for path, data in content.items():
        if path.endswith('aggregategraph.nt'):
            data = _convert(data.decode(), mac2pc)
            if mac2pc:
                data = data.replace('macos', 'dx9').encode('ascii')
            else:
                data = data.replace('dx9', 'macos').encode('ascii')
        new_content[_convert(path, mac2pc)] = data
        if use_shortnames and not short_name and path.endswith('.hsan'):
            short_name = create_short_name(tail, data)
    
    outname = output_directory + '/'
    if short_name:
        outname += short_name
    else:
        outname += tail 
    if os.path.isfile(outname):
        print(f"{outname} already exists.")
        return outname

    with open(outname, 'wb') as fh:
        PSARC().build_stream(new_content, fh)
    return outname

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
    short_name = f"{artist}-{song}" + original[-8:]
    keepcharacters = ('.', '_', '-')
    return "".join(c for c in short_name if c.isalnum() or c in keepcharacters).rstrip()    
   
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("FILE", help=".psarc file")
    parser.add_argument("DIR", help="output directory")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--convert", help="convert file between mac / pc", action='store_true')
    group.add_argument("--convertshort", help="convert file using shortname", action='store_true')
    group.add_argument("--rename", help="don't convert, just rename to shortname", action='store_true')
    args = parser.parse_args()
    if not os.path.isfile(args.FILE) or not os.path.isdir(args.DIR):
        print(args.FILE)
        print(args.DIR)
        print('Filename and output directory must exist')
        sys.exit()
    if args.convert:
        convert(args.FILE, args.DIR, False)
    if args.convertshort:
        convert(args.FILE, args.DIR, True)
    if args.rename:
        rename(args.FILE, args.DIR)

    