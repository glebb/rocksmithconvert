# Rocksmith 2014 psarc PC to Mac #
Simple OSX tool to convert Rocksmith 2014 PC .psarc files between PC and MAC.

It's based on 0x0L's pyrocksmith (https://github.com/0x0L/rocksmith)

The basic idea is to use pyrocksmith to convert the files and
bundle everything to a nice and clean standalone osx app,
which can be used to do mass conversion of files.

Conversion always creates a new folder at the same location as the original file. The folder
contains the converted file(s). If file exists, conversion is skipped.
For mac conversions the new folder is 'converted_for_mac' and for pc 'converted_for_pc'.


## Building ##
### Requirements ###
* Python 3
   * pyinstaller (https://pypi.org/project/pyinstaller/)
   * construct
   * pycrypto (pyinstaller might have problems with if installed with pip, using easy_install worked for me)
* Platypus (https://sveinbjorn.org/platypus)
### Making convert.py as standalone executable ###
Running `pyinstaller --onefile src/convert.py` creates a convert executable under .dist/.
Include this file in Platypus bundle so the script can access it.

### Creating osx app with Platypus ###
Rocksmith 2014 CDLC convert pc mac platypus profile and make sure you have "convert" executable included in the bundle. Also make sure the script points to the provided Script.sh. Then just create the app.

## Download ##
Readymade package for OSX 10.12 and newer: https://drive.google.com/drive/folders/1jzGLNy7oisBjsHkzJIMMf9E4V_RBXQ8I?usp=sharing

* Download the package
* Unzip by double clicking the file (if needed, e.g. Safari does this automatically)
* Start the app -> osx security kicks in:
* Allow the app to run by checking osx System Preferences / Security & Privacy / General -> Allow

