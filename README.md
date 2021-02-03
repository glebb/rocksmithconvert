# Rocksmith 2014 CDLC convert PC / Mac #
Simple standalone OSX app to convert/rename Rocksmith 2014 .psarc files between PC and MAC.

Based on 0x0L's pyrocksmith (https://github.com/0x0L/rocksmith)

## Usage ##
Just drag & drop files you want to convert to the app (supports mass covnersions).
Additionally, you can choose to use short filenames or just rename the files without conversion.

After dropping files to the app you choose the operation you want to perform.
The options are convert, convert using shortnames or just rename.
After choosing the operation, you can select the output folder.

If you choose to use the source folder, the app creates a new folders to the same location as the original file. 
The new folder contains the converted file(s). For mac conversions, the folder is called 'converted_for_mac' and for pc 'converted_for_pc'.
For just renaming the files, folder is called 'renamed'. If you choose a specific folder, all
the target files will be placed there.

If target file already exists, operation is skipped.

Example: your CDLC is /Users/john/Downloads/great_music_p.pasarc
Dropping great_music_p.psarc to the app, choosing convert using source folder, the app will output
/Users/john/Downloads/converted_for_mac/great_music_m.pasarc
You then just copy the converted file(s) to your Rocksmith dlc folder as usual (or select that to begin with as target folder).

NOTE! Option for renaming is to avoid problems loading CDLC within Rocksmith. 
This is achieved by removing all unecessary characters and also splitting Artist and Song name
if needed. Using rename scheme is optional.

## Building ##
The basic idea is to use pyrocksmith to convert the files and
bundle everything to a nice and clean standalone osx app without additional
dependencies. Batteries included. This is achieved
by using pyinstaller to create a single executable and then Platypus to 
bundle it as an osx app. Simple bash script is used to execute conversion file by file
and report progress.

Only minimal set of pyrocksmith code is used with slight modifications.

### Requirements ###
* Python 3.6
   * pyinstaller (https://pypi.org/project/pyinstaller/)
   * construct
   * pycrypto (pyinstaller might have problems with if installed with pip, using easy_install worked for me)
* Platypus (https://sveinbjorn.org/platypus)

### Making convert.py as standalone executable ###
Running `pyinstaller --onefile src/convert.py` creates a convert executable under .dist/.
Include this file in Platypus bundle so the script can access it.

### Creating osx app with Platypus ###
Rocksmith 2014 CDLC convert pc mac platypus profile and make sure you have "convert" executable included in the bundle. Also make sure the script points to the provided Script.sh. Then just create the app.

## Download & install ##
Download latest readymade package for OSX 10.12 and newer: https://github.com/glebb/rocksmithconvert/releases

* Download the package
* Unzip by double clicking the file (if needed, e.g. Safari does this automatically)
* No installation needed, you can move the app to Applications folder if you like
* Start the app -> osx security kicks in (the first time you run it):
* Allow the app to run by checking osx System Preferences / Security & Privacy / General -> Allow

