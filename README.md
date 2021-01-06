# Rocksmith 2014 psarc PC to Mac #
Simple OSX tool to convert Rocksmith 2014 PC .psarc files for MAC.

It's based on 0x0L's pyrocksmith (https://github.com/0x0L/rocksmith)

The basic idea is to use pyrocksmith to convert the files and
bundle everything to a nice and clean standalone osx app,
which can be used to do mass conversion of files.

Currently it processes _p.psarc files and converts them, and copies 
files that are already in mac format (_m.psarc) to destination folder (./convert/).

## Building ##
### Requirements ###
* Python 3
* pyinstaller (https://pypi.org/project/pyinstaller/)
* construct
* pycrypto (use easy_install, pip3 might have problems with High Sierra)
* Platypus (https://sveinbjorn.org/platypus)
* pyrocksmith dependencies?

### Making convert.py as standalone executable ###
Running `pyinstaller --onefile ./convert.py` creates a convert executable under .dist/.
Include this file in Platypus bundle so the script can access it.

### Creating osx app with Platypus ###
Load Rocksmith 2014 psarc PC to Mac profile and make sure you have convert executable included in the bundle. Also make sure the script point to the provided Script.sh. Then just create the app.

## Download ##
Readymade package (use at your own risk): https://drive.google.com/drive/folders/1jzGLNy7oisBjsHkzJIMMf9E4V_RBXQ8I?usp=sharing

