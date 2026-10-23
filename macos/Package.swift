// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "RSConvert",
    platforms: [.macOS(.v14)],
    products: [
        .executable(name: "RSConvert", targets: ["RSConvert"]),
        .executable(name: "rsconvert-cli", targets: ["RSConvertCLI"]),
        .library(name: "RSConvertCore", targets: ["RSConvertCore"]),
    ],
    targets: [
        // System zlib (ships with macOS); no third-party dependencies anywhere.
        .systemLibrary(name: "CZlib", path: "Sources/CZlib"),
        .target(name: "RSConvertCore", dependencies: ["CZlib"]),
        .executableTarget(name: "RSConvert", dependencies: ["RSConvertCore"]),
        .executableTarget(name: "RSConvertCLI", dependencies: ["RSConvertCore"]),
        .testTarget(name: "RSConvertCoreTests", dependencies: ["RSConvertCore"]),
    ]
)
