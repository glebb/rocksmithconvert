#!/bin/sh
# Builds a universal (arm64 + x86_64), sandboxed, hardened-runtime RSConvert.app.
#
#   scripts/build-app.sh                 ad-hoc signed, for local use
#   SIGN_IDENTITY="Developer ID Application: Name (TEAMID)" scripts/build-app.sh
#                                        signed for distribution (then notarize the zip)
set -eu

cd "$(dirname "$0")/.."
OUT=build
APP="$OUT/RS Convert.app"
IDENTITY="${SIGN_IDENTITY:--}"

swift build -c release --arch arm64 --arch x86_64 --product RSConvert
BIN="$(swift build -c release --arch arm64 --arch x86_64 --show-bin-path)/RSConvert"

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$BIN" "$APP/Contents/MacOS/RSConvert"
strip -x "$APP/Contents/MacOS/RSConvert"
cp Resources/Info.plist "$APP/Contents/Info.plist"

# Version comes from RSConvertCore/Version.swift; the build number is the git
# commit count, so it always increases (required by macOS for updates).
VERSION="$(sed -n 's/.*static let string = "\(.*\)".*/\1/p' Sources/RSConvertCore/Version.swift)"
BUILD="$(git rev-list --count HEAD 2>/dev/null || echo 1)"
[ -n "$VERSION" ] || { echo "Could not read version from Version.swift" >&2; exit 1; }
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $VERSION" \
    -c "Set :CFBundleVersion $BUILD" "$APP/Contents/Info.plist"
cp Resources/AppIcon.icns "$APP/Contents/Resources/AppIcon.icns"
printf 'APPL????' > "$APP/Contents/PkgInfo"

codesign --force --options runtime --timestamp=none \
    --entitlements Resources/RSConvert.entitlements \
    --sign "$IDENTITY" "$APP"
codesign --verify --strict "$APP"

(cd "$OUT" && rm -f RSConvert.zip && ditto -c -k --keepParent "RS Convert.app" RSConvert.zip)

echo "Built $APP $VERSION ($BUILD), $(du -sh "$APP" | cut -f1)"
lipo -archs "$APP/Contents/MacOS/RSConvert"
