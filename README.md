# Rocksmith 2014 CDLC convert PC / Mac #
Simple standalone OSX app to convert/rename Rocksmith 2014 .psarc files between PC and MAC.

Based on 0x0L's pyrocksmith (https://github.com/0x0L/rocksmith)

## Usage ##
Just drag & drop files you want to convert to the app (supports mass covnersions).
Additionally, you can choose to use short filenames or just rename(copy) the files without conversion.

If target file already exists, operation is skipped. Original files are not modified, the app always
creates new files as a result of conversion/rename.

Example: your CDLC is /Users/john/Downloads/Really_Long_Artist_Name-ThisIsJustATribute_p.psarc
Dropping the file to the app and processing with conversion and rename options enabled, 
following file is produced: /Users/john/Library/Application Support/Steam/steamapps/common/Rocksmith2014/dlc/ReallyLong-ThisIsJust_m.psarc
(target folder of course depends on your selection).

The next time you run the app, settings regarding conversion, renaming and target are as you set them before.

NOTE! Option for renaming is to avoid problems loading CDLC within Rocksmith. 
This is achieved by removing all unecessary characters and also splitting Artist and Song name
if needed. Using rename scheme is optional.

## Building ##
The basic idea is to use pyrocksmith to parse the files and
bundle everything to a nice and clean standalone osx app without additional
dependencies. Batteries included. This is achieved
by using pyinstaller to create a single executable from PyQt app and then Platypus to 
bundle it as an osx app. Platypus packaging is used only for convenience,
to allow dropping files straight on top of the app icon.

### Requirements ###
Check requirements.txt
* Qt 5
* Python 3.6
   * PyQt5
   * pyinstaller (https://pypi.org/project/pyinstaller/)
   * git+https://github.com/0x0L/rocksmith.git
* Platypus (https://sveinbjorn.org/platypus)

### Making convert.py as standalone executable ###
Running `pyinstaller --onefile src/convert_gui.py` creates an executable under .dist/.
Include this file in Platypus bundle so the script can access it.

### Creating osx app with Platypus ###
Rocksmith 2014 CDLC convert pc mac platypus profile and make sure you have "convert_gui" executable included in the bundle. Also make sure the script points to the provided Script.sh. Then just create the app.

## Download & install ##
Download latest readymade package for OSX 10.12 and newer: https://github.com/glebb/rocksmithconvert/releases

* Download the package
* Unzip by double clicking the file (if needed, e.g. Safari does this automatically)
* No installation needed, you can move the app to Applications folder if you like
* Start the app -> osx security kicks in (the first time you run it):
* Allow the app to run by checking osx System Preferences / Security & Privacy / General -> Allow

