# Rocksmith 2014 CDLC convert PC / Mac #
Simple standalone OSX app to convert/rename Rocksmith 2014 .psarc files between PC and MAC.

Based on 0x0L's pyrocksmith (https://github.com/0x0L/rocksmith)

## Download & install ##
Download latest readymade package for OSX 10.12 and newer: https://github.com/glebb/rocksmithconvert/releases

* Download the zip package
* Unzip by double clicking the file (if needed, e.g. Safari does this automatically)
* No installation needed, you can move the app to Applications folder if you like
* Start the app -> osx security kicks in (the first time you run it):
* Allow the app to run by checking osx System Preferences / Security & Privacy / General -> Allow

## Usage ##
Just drag & drop files you want to convert to the app (supports mass covnersions).
Additionally, you can choose to use short filenames or just rename(copy) the files without conversion.

If target file already exists, operation is skipped. Original files are not modified, the app always
creates new files as a result of conversion/rename.

Example: your CDLC is /Users/john/Downloads/Really_Long_Artist_Name-ThisIsJustATribute_p.psarc
Dropping the file to the app and processing with conversion and rename options enabled, 
following file is produced: /Users/john/Library/Application Support/Steam/steamapps/common/Rocksmith2014/dlc/ReallyLong-ThisIsJust_m.psarc
(target folder of course depends on your selection).

The next time you run the app, settings are as you set them before. With remembering settings combined with
auto-processing feature, you can set the app to check desired folder at launch and do the processing automatically,
without any user interaction. You can use it to scan Downloads folder and automatically convert
files dlc/cdlc folder. It doesn't matter what files are in the source folder, only files that are
not in target already will be processed.

If source folder contains both pc (_p.psarc) and mac (_m.psarc) files, the processor picks all of them
and either copies or converts the files based on platform selection to the target folder.

NOTE! Option for renaming is to avoid problems loading CDLC within Rocksmith. 
This is achieved by removing all unecessary characters and also splitting Artist and Song name
if needed. Using rename scheme is optional.

## Versions ##

1.1 Was the first public release. It is considerably different from the current version. See details from the
[1.1 readme](https://github.com/glebb/rocksmithconvert/blob/v1.1/README.md). The main difference is that 1.1
user interface was build on platypus and applescript. Most of it was implemented as pure bash script.
It did (still does) its job, but considering the limitations, it was not feasible to develop it much further as
adding new features became increasingly awkward.

2.x Is the current branch, based on PyQt5. It still uses pyrocksmith as it's core for the psarc file handling,
but otherwise it's a complete rewrite. New features include e.g. permanent settings and using threads for
processing, making it much faster. In theory, it should also work cross platform (it hasn't been developed or tested
with Windows though!)

## Development & building from source ##
The basic idea is to use pyrocksmith to parse the files and
bundle everything to a nice and clean standalone osx app without additional
dependencies. Batteries included. This is achieved
by using pyinstaller to create a single executable from PyQt app and then Platypus to 
bundle it as an osx app. Platypus packaging is used only for convenience,
to allow dropping files straight on top of the app icon, which pyinstaller doesn't seem to handle easily.

### Requirements ###
Check requirements.txt
* Qt 5
* Python 3.6
   * PyQt5
   * pyinstaller (https://pypi.org/project/pyinstaller/)
   * git+https://github.com/0x0L/rocksmith.git
* Platypus (https://sveinbjorn.org/platypus)

### Making convert_gui.py as standalone executable ###
Running `pyinstaller --onefile src/convert_gui.py` creates an executable under .dist/.
Include this file in Platypus bundle so the script can access it.

### Creating osx app with Platypus ###
Rocksmith 2014 CDLC convert pc mac platypus profile and make sure you have "convert_gui" executable included in the bundle. Also make sure the script points to the provided Script.sh. Then just create the app.


