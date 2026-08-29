# AirGapQR

**Offline optical file transfer across air-gapped systems using QR codes.**

AirGapQR is an open-source application for transferring files between isolated systems without requiring a network connection between them.

The basic model is simple:

**FILE → QR → AIR GAP → QR → FILE**

A file is encoded into a sequence of QR frames on the sending system.  
The receiving system captures those frames using a camera or imported QR images, reconstructs the original file, and verifies its integrity using SHA-256.

## Current version

**AirGapQR v0.5.0**

Development-stage release for Windows x64 and Linux x64.

## Core features

- Offline optical file transfer using QR codes
- No network connection required for transfer
- Maximum file size: 5 MiB
- SHA-256 integrity verification
- CRC32 validation of individual QR frame payloads
- Physical camera receiving
- QR image import
- Missing-frame detection
- Selective frame recovery
- Adjustable frame display speed
- Adjustable QR background brightness
- Fullscreen QR display
- Sharp QR scaling
- Software camera zoom
- Strict protocol validation
- Portable Windows and Linux builds

## Transfer workflow

### Sending system

1. Open AirGapQR.
2. Select **FILE → QR**.
3. Choose a file.
4. Select a frame display interval.
5. Adjust QR background brightness if needed.
6. Use Fullscreen QR if required.

### Receiving system

1. Open AirGapQR.
2. Select **QR → FILE**.
3. Start the camera or import QR frame images.
4. Allow AirGapQR to collect the frames.
5. Check **MISSING FRAMES** if the transfer is incomplete.
6. Use **PLAY SELECTED** on the sending system to retransmit only missing frames.
7. Wait for the transfer to complete.
8. Verify SHA-256 integrity.
9. Save the reconstructed file.

## QR transport

AirGapQR v0.5.0 uses a default payload chunk size of:

**100 bytes per QR frame**

Smaller payloads create more frames but produce simpler QR codes that can be easier for lower-quality cameras to decode.

Available frame display intervals:

- 0.25 seconds
- 0.5 seconds
- 1 second
- 2 seconds
- 3 seconds
- 5 seconds

The default is 2 seconds.

## QR background brightness

AirGapQR can reduce the brightness of the QR background without changing the black QR modules.

This can help cameras affected by:

- overexposure
- white-screen bloom
- poor contrast
- weak focus

Brightness control is available in both the normal SEND view and Fullscreen QR mode.

AirGapQR does not modify operating-system display brightness.

## Sharp QR display

QR display scaling favors sharp module edges rather than smooth image interpolation.

This helps preserve the square structure of QR modules when QR codes are resized on screen.

## Missing frames and recovery

The RECEIVE screen reports the exact QR frames that have not yet been received.

Example:

```text
MISSING FRAMES

17, 43, 88
```

Those frame numbers can be entered on the sending system and replayed using:

```text
PLAY SELECTED
```

AirGapQR will continuously cycle only the selected frames.

Normal transmission can then be restored with:

```text
PLAY ALL
```

## Receive methods

AirGapQR can receive QR frames through:

- a physical camera
- a single imported QR image
- multiple imported QR images

Multiple imported images are automatically sorted using natural numeric ordering.

Camera frames and imported QR images use the same decoding pipeline.

If normal QR decoding fails, AirGapQR can attempt a perspective-corrected decoding fallback.

## Camera zoom

Available software zoom levels:

- 1.0x
- 1.25x
- 1.5x
- 1.75x
- 2.0x

The zoom is implemented inside AirGapQR using a central image crop.

It does not modify:

- camera drivers
- operating-system camera settings
- hardware camera configuration
- firmware

At 1.0x, the original camera frame is used unchanged.

## Settings state preservation

Opening Settings does not destroy an active transfer.

During SEND:

- active QR playback is paused
- the loaded file remains in memory
- current transfer state is preserved
- playback can resume after returning

During RECEIVE:

- the camera can be stopped temporarily
- already received QR frames remain stored
- the camera can restart after returning

Settings includes:

**BACK**

and:

**SAVE & BACK**

## SHA-256 integrity

SHA-256 fields display values from the first character and use dedicated AirGapQR styling.

The SEND screen displays the SHA-256 of the source file.

The RECEIVE screen separately displays:

**SOURCE SHA-256**

and:

**RECEIVED SHA-256**

After a completed transfer, verify that the reconstructed file matches the expected SHA-256.

## Clear / reset behavior

**CLEAR ALL** resets transfer and recovery state, including:

- selected recovery frames
- recovery position
- recovery mode
- recovery input
- received data
- missing-frame display
- SOURCE SHA-256
- RECEIVED SHA-256
- progress information
- transfer state

## Protocol hardening

AirGapQR v0.5.0 includes stricter protocol validation.

### Strict JSON structure

Incoming protocol frames must:

- contain valid JSON
- contain a JSON object
- contain exactly the expected AGQR fields
- use the expected data type for every field

### Strict field types

String fields must actually be strings.

Integer fields must actually be integers.

Boolean values cannot silently pass as integer protocol values.

### Transfer ID validation

Transfer IDs must match the format generated by AirGapQR:

- exactly 16 characters
- lowercase hexadecimal only

### SHA-256 validation

SHA-256 metadata must contain:

- exactly 64 characters
- lowercase hexadecimal characters only

### CRC32 validation

CRC32 metadata must contain:

- exactly 8 characters
- lowercase hexadecimal characters only

### File size limit

Declared file size is limited to:

**5 MiB**

### Frame count limit

The maximum number of QR frames is bounded.

### Payload limits

AirGapQR limits:

- decoded payload size
- Base64 payload length
- total QR protocol text size

### First-frame validation

The first received frame is fully validated before its metadata can initialize the transfer.

A corrupted first frame therefore cannot lock the receiver into an invalid transfer state.

### Duplicate frame protection

An identical duplicate frame is safely ignored.

If another frame arrives with the same frame index but different payload data, AirGapQR rejects it as a conflicting duplicate.

### Received byte limit

Received payload data cannot exceed the file size declared by the transfer.

### Empty payload protection

Empty payload frames are rejected for non-empty files.

### Sender-side validation

The encoder validates:

- filename
- input data type
- file size
- chunk size
- resulting QR frame count

before generating a transfer.

## Protocol tests

The v0.5.0 protocol regression test suite includes checks for:

- normal encode/decode round trip
- complete file reconstruction
- identical duplicate frames
- conflicting duplicate frames
- corrupted CRC32
- oversized payloads
- malformed JSON
- invalid protocol field types
- oversized file declarations

All current protocol regression tests pass for the v0.5.0 release build.

## Portable builds

### Windows x64

AirGapQR v0.5.0 is distributed as a standalone portable ZIP archive.

No Python installation is required.

Extract the complete archive and keep all files and folders together.

Run:

```text
AirGapQR.exe
```

Do not move `AirGapQR.exe` out of the portable folder by itself.

The portable build can also be stored and run from removable media such as a USB drive, subject to Windows security policies and permissions.

### Linux x64

AirGapQR v0.5.0 is distributed as a standalone portable `.tar.gz` archive.

No Python installation is required when using the packaged release.

For best results, extract the archive onto a native Linux filesystem.

Avoid extracting directly onto FAT/exFAT media because Linux permissions and symbolic links may not be preserved correctly.

The v0.5.0 Linux build has been physically tested on Debian 13 x64 with XFCE/X11.

## Verification

Official release artifacts are accompanied by SHA-256 checksum files.

Users are encouraged to verify downloaded release archives before running them.

Release checksums apply to the complete downloadable archive, not only to the executable contained inside it.

## Network model

AirGapQR does not require an internet connection to perform an optical file transfer.

The sending and receiving systems do not need a network connection between them.

AirGapQR does not automatically open network services or require cloud infrastructure for file transfer.

## Tips & recommendations

- Use Fullscreen QR when the receiving camera has difficulty decoding frames.
- Adjust QR background brightness if the QR image appears overexposed.
- Keep both devices stable during transfer.
- Position the devices close enough for reliable scanning.
- Prevent the display from going to sleep during a transfer.
- Keep devices connected to power during longer transfers.
- Verify SHA-256 integrity after receiving.
- If frames are missing, use **MISSING FRAMES** together with **PLAY SELECTED** instead of restarting the entire transfer.

AirGapQR does not automatically change operating-system sleep, power, display-brightness, camera-driver, or networking settings.

## Security notes

AirGapQR is designed to reduce dependency on network communication during file transfer.

However:

- CRC32 detects accidental corruption of individual QR payloads. It is not an authentication mechanism.
- SHA-256 verifies that reconstructed file bytes match the SHA-256 value contained in the transfer metadata. It does not authenticate the identity of the sender.
- AirGapQR does not execute received files.
- AirGapQR has not undergone a complete independent security audit.

Users should independently verify critical software and data before using AirGapQR for high-value or security-sensitive workflows.

## Project status

AirGapQR v0.5.0 is a development-stage release.

The project favors:

- local operation
- offline capability
- minimal dependencies
- verifiability
- simple and inspectable transfer behavior

## Support the project

AirGapQR includes a discreet **SUPPORT THE PROJECT** option.

AirGapQR does not embed a Bitcoin support address directly in the application.

Current project and support information is published through this repository.

Support functionality does not automatically open, display donation requests after transfers, or affect file-transfer functionality.

## Open-source signature

> May the open source be with you.  
> Open source everything.
>
> — ton_ide_zvuk
