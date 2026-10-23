# RS Convert (native macOS)

A native Swift rewrite of the Rocksmith 2014 CDLC converter. It lives in the menu bar, so watch-folder conversion keeps running with the window closed.

- **Small:** a 1.4 MB universal app (arm64 + x86_64). The PyQt build was 87 MB.
- **Fast:** a typical song converts in 20–50 ms (Python took about 600 ms), and a 227 MB pack takes about 1 s. Audio blocks are copied as they are; only the SNG encryption is re-keyed.
- **Secure:** App Sandbox and hardened runtime. The app can only touch files you drop or choose, and the folders you pick (kept as security-scoped bookmarks). Every size and offset in an archive is bounds-checked, decompression output is capped, and the parser is fuzz-tested. It has no third-party dependencies; it uses only system zlib, CommonCrypto and CryptoKit.

## Features

- Convert between PC (`_p.psarc`) and Mac (`_m.psarc`), or keep the platform.
- Rename to short or full `Artist-Song` names. The rules match the 2.x app, so existing libraries keep their names.
- Change the App ID.
- Drop files or folders onto the window, the Dock icon or the menu bar icon, or use **File › Convert Files…** (⌘O).
- Watch a folder in the background using FSEvents (no polling):
  - A file is processed only once it has finished downloading or copying.
  - Files already handled are remembered between launches.
  - Optionally, you get a notification when files are converted.
- Launch at Login from the menu bar menu.
- Originals are never modified. Output is written to a temp file and then renamed into place atomically. When "Overwrite" is off, existing files are never replaced.

## Changes from 2.x

- The platform is detected from the archive's contents, not trusted from the filename. Files without an `_m`/`_p` suffix now work.
- Python 2.x could overwrite the source file when the output folder was the source folder. That is now refused.
- An SNG that fails to decrypt is now an error. Python silently wrote it without re-encrypting, which produced packages that are broken in game.
- Empty placeholder SNGs (found in RS1 compatibility packs) are now handled.
- Python polled the watch folder every 5 s, re-read every file on each launch, and only guarded against zero-byte files. The new app uses FSEvents, waits until a file's size and date stop changing, and keeps a history of processed files.
- The watch folder can't be the same as the output folder, which prevents feedback loops.
- The App ID can be changed without converting.
- Unchanged entries keep their original order and compressed bytes. PC → Mac → PC round trips are byte-identical to the original file.

## Build

Requirements: Xcode 16 or later (Swift 6). The app runs on macOS 14 or later.

```bash
scripts/build-app.sh
```

This produces `build/RS Convert.app` and `build/RSConvert.zip`, ad-hoc signed. For distribution, set `SIGN_IDENTITY="Developer ID Application: …"` and notarize the zip.

Versioning: the version is set in one place, `Sources/RSConvertCore/Version.swift`. The build script stamps it into the app's Info.plist, and the build number comes from the git commit count. The version shows in the window title, the menu bar menu, the About panel and `rsconvert-cli --version`.

To release:
1. Bump the version in `Version.swift`.
2. Build.
3. Tag the commit with the same version, for example `git tag 3.0.0`.

Tests:

```bash
swift test
```

To also round-trip real packages, run:

```bash
RSCONVERT_SAMPLES=/path/to/psarcs swift test -c release
```

Command line (useful for scripting):

```bash
swift run -c release rsconvert-cli --to mac --rename short -o ~/out file_p.psarc
```

## Layout

- `Sources/RSConvertCore`: PSARC reader and writer, AES (CFB for the TOC, CTR for SNG), zlib, conversion and rename logic.
- `Sources/RSConvert`: the app.
  - `AppDelegate`: menu bar item, menus, window and drop handling.
  - `AppModel`: settings and the processing queue.
  - `FolderWatcher`: FSEvents watching.
  - `ProcessedLedger`: history of processed files.
  - `FolderAccess`: sandbox bookmarks.
- `Sources/RSConvertCLI`: the `rsconvert-cli` tool.
- `Resources`: Info.plist, entitlements, icon.
