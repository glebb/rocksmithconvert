# TODO

Notes on improvements worth doing next.

- `services.py`: replace bare `except:` blocks with specific exception handling so PSARC parsing and worker failures are easier to debug.
- `services.py`: add direct tests for conversion, rename, and app ID rewriting. Current tests mostly cover controller-to-model wiring.
- `services.py`: document the filename rewrite and PSARC metadata transforms. The logic works, but the intent is not obvious when reading the code.
- `settings.py`: tighten the PyQt version detection and review whether scanning all widgets is broader than needed.
- `README.md`: add a short troubleshooting section for Gatekeeper, missing target folder, and skipped existing files.
- Packaging: review whether the PyInstaller command and spec file can share more of the build configuration.
- General cleanup: add a few module or method docstrings in the non-generated source files with the most logic.