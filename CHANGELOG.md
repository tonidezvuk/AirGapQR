# Changelog

All notable changes to AirGapQR are documented in this file.

## v0.5.0

### Added

- Missing-frame reporting on the RECEIVE screen.
- Recovery workflow using `PLAY SELECTED` and `PLAY ALL`.
- Adjustable QR background brightness.
- QR background brightness control in fullscreen mode.
- Software camera zoom:
  - 1.0x
  - 1.25x
  - 1.5x
  - 1.75x
  - 2.0x
- Shared QR decoding pipeline for camera frames and imported QR images.
- Perspective-corrected QR decoding fallback.
- Separate SOURCE SHA-256 and RECEIVED SHA-256 fields.
- Home screen tips and recommendations.
- `SUPPORT THE PROJECT` interface.
- Linux `/dev/video*` camera discovery.
- Linux adaptive window sizing.
- Linux 1366×768 UI adjustment for RECEIVE controls.
- Protocol regression tests.

### Changed

- Default QR payload chunk size reduced to 100 bytes.
- Available frame display intervals are now:
  - 0.25 seconds
  - 0.5 seconds
  - 1 second
  - 2 seconds
  - 3 seconds
  - 5 seconds
- QR rendering now favors sharper module edges.
- Settings preserves active SEND and RECEIVE transfer state.
- Settings now includes `BACK` and `SAVE & BACK`.
- SHA-256 fields display from the first character.
- Recovery inputs and sliders received updated styling.
- Application name updated to `AirGapQR v0.5.0`.
- Windows and Linux releases are distributed as portable builds.

### Protocol hardening

- Strict JSON object validation.
- Strict protocol field types.
- Strict transfer ID format validation.
- SHA-256 hexadecimal validation.
- CRC32 hexadecimal validation.
- Maximum file size enforcement at 5 MiB.
- Maximum frame count enforcement.
- Payload size limits.
- Base64 length limits.
- Total protocol frame text limits.
- Full validation of the first received frame before transfer initialization.
- Invalid first frames no longer initialize transfer state.
- Identical duplicate frames are safely ignored.
- Conflicting duplicate frames are rejected.
- Received payload bytes cannot exceed declared file size.
- Empty payload frames are rejected for non-empty files.
- Sender-side filename, input data, file size, chunk size, and frame-count validation.

### Fixed

- `CLEAR ALL` now resets recovery state.
- `CLEAR ALL` now resets both RECEIVE SHA-256 fields.
- Improved RECEIVE layout behavior on smaller Linux displays.

### Tested

- Protocol regression test suite passes for v0.5.0.
- Windows x64 standalone portable build tested.
- Linux x64 portable build physically tested on Debian 13 with XFCE/X11.

### Security

AirGapQR v0.5.0 has not undergone a complete independent security audit.

CRC32 is used for accidental corruption detection and is not an authentication mechanism.

SHA-256 verifies reconstructed file integrity against transfer metadata but does not authenticate the identity of the sender.
