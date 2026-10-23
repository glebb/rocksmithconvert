/// Single source of truth for the release version. `scripts/build-app.sh` reads
/// this line and stamps it into the app bundle's Info.plist. Releases are
/// tagged in git with the same string (e.g. `3.0.0`).
public enum RSConvertVersion {
    public static let string = "3.0.0"
}
