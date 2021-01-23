import os
import json
import sys

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
    head, tail = os.path.split(outname)
    outname2 = output_directory + '/' + tail

    if os.path.isfile(outname2):
        print(f"{outname2} already exists.")
        return outname2

    with open(filename, 'rb') as fh:
        content = PSARC().parse_stream(fh)

    new_content = {}
    for path, data in content.items():
        if path.endswith('aggregategraph.nt'):
            data = _convert(data.decode(), mac2pc)
            if mac2pc:
                data = data.replace('macos', 'dx9').encode('ascii')
            else:
                data = data.replace('dx9', 'macos').encode('ascii')

        new_content[_convert(path, mac2pc)] = data

    with open(outname2, 'wb') as fh:
        PSARC().build_stream(new_content, fh)
    return outname2

if __name__ == "__main__":
    if len(sys.argv) != 3 or not os.path.isfile(sys.argv[1]) or not os.path.isdir(sys.argv[2]):
        print('Give filename and existing output directory as arguments')
        sys.exit()
    convert(sys.argv[1], sys.argv[2])