// swift-tools-version: 5.10
import PackageDescription

let package = Package(
    name: "CivicClockCore",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .library(
            name: "CivicClockWatch",
            targets: ["CivicClockWatch"]
        )
    ],
    targets: [
        .target(
            name: "CivicClockWatch",
            path: "Shared"
        ),
        .testTarget(
            name: "CivicClockTests",
            dependencies: ["CivicClockWatch"],
            path: "Tests"
        )
    ]
)
