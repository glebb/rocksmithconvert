auto-processing feature, you can set the app to check desired folder at launch and do the processing automatically,
# Rocksmith 2014 CDLC Convert PC / Mac

Simple GUI app for converting or renaming Rocksmith 2014 `.psarc` files between PC and Mac formats.

The app is based on 0x0L's pyrocksmith: https://github.com/0x0L/rocksmith

![Screenshot](docs/screenshot.png)

## What it does

- Drag and drop one or more `.psarc` files into the app.
- Convert between PC (`_p.psarc`) and Mac (`_m.psarc`) packages.
- Rename files with shorter Rocksmith-friendly names.
- Optionally set a custom app ID during conversion.
- Watch a source folder and process new files automatically.

Original files are never modified. The app always writes a new file to the target folder.

## Download and install

Download the latest macOS release here:
https://github.com/glebb/rocksmithconvert/releases

1. Download the zip package.
2. Unzip it if your browser does not do that automatically.
3. Move the app anywhere you want, for example to Applications.
4. On first launch, allow the app in macOS System Settings or System Preferences if Gatekeeper blocks it.

## Usage

Drop files onto the running app to process them. You can also drop files onto the app icon to launch and process them directly.

Common options:

- Convert only
- Rename only
- Convert and rename
- Overwrite existing target files
- Auto-process new files from a source folder

If the target file already exists and overwrite is disabled, the file is skipped.

Example:

Input:
`/Users/john/Downloads/Really_Long_Artist_Name-ThisIsJustATribute_p.psarc`

Possible output:
`/Users/john/Library/Application Support/Steam/steamapps/common/Rocksmith2014/dlc/ReallyLong-ThisIsJust_m.psarc`

The exact result depends on your selected target folder, platform, rename mode, and app ID settings.

### Notes

- Auto-processing remembers your settings and can watch a folder for new `.psarc` files.
- Mixed PC and Mac source files are handled based on the target platform you selected.
- Rename mode exists mainly to avoid Rocksmith issues with long or unusual CDLC filenames.

## Development

The current app is the PyQt-based 2.x rewrite. It keeps pyrocksmith for PSARC handling and adds a desktop UI, saved settings, and threaded processing.

### Requirements

- Python 3.6+
- `requirements.txt` for general development
- `requirements-m1.txt` for modern macOS / Apple Silicon builds using PyQt6
- `requirements-dev.txt` for tests and formatting tools

### Setup

```bash
pip install -r requirements-dev.txt
pip install -e src/.
```

### Run tests

```bash
pytest
```

### Run the app locally

```bash
python -m rocksmithconvert.convert_gui
```

### UI workflow

`mainwindow.ui` is the source of truth for the main window.

Generate Python code with `pyuic5` or `pyuic6`, for example:

```bash
pyuic6 -x src/rocksmithconvert/mainwindow.ui -o src/rocksmithconvert/mainwindow.py
```

After regenerating, replace the generated Qt imports with:

```python
from rocksmithconvert.qt_wrapper import QtCore, QtWidgets
```

This keeps the project compatible with both PyQt5 and PyQt6.

### Build a standalone app

```bash
pyinstaller --name 'RSConvert_GUI' --windowed --onefile src/rocksmithconvert/convert_gui.py --clean --icon=docs/rsconvert.icns --add-binary src/rocksmithconvert/assets:assets
```

On Windows:

```bash
pyinstaller --name RSConvert_GUI --windowed --onefile src/rocksmithconvert/convert_gui.py --clean --icon=docs/rsconvert.ico --add-binary src/rocksmithconvert/assets;assets
```

## Project layout

- `src/rocksmithconvert/controllers.py`: main window controller and signal wiring
- `src/rocksmithconvert/services.py`: conversion, worker threads, and file processing
- `src/rocksmithconvert/models.py`: process model passed into workers
- `src/rocksmithconvert/settings.py`: persistent UI settings
- `tests/`: controller and GUI behavior tests

