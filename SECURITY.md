# Security Policy

## Project status

AirGapQR is a development-stage open-source project.

AirGapQR v0.5.0 has not undergone a complete independent security audit.

The software should not be treated as a formally audited security product.

## Security model

AirGapQR is designed to transfer files optically between isolated systems using QR codes, without requiring a network connection between the sending and receiving systems.

AirGapQR does not execute received files.

However, users remain responsible for deciding whether a received file is safe to open or use.

## Integrity and authentication

AirGapQR uses SHA-256 to verify file integrity.

A matching SHA-256 value indicates that the reconstructed file bytes match the hash contained in the transfer metadata.

SHA-256 does not authenticate the identity of the sender.

CRC32 is used to detect accidental corruption of individual QR frame payloads.

CRC32 is not an authentication or cryptographic integrity mechanism.

## Protocol validation

AirGapQR v0.5.0 includes validation for malformed and inconsistent protocol data, including:

- strict JSON structure
- strict field types
- transfer ID validation
- SHA-256 and CRC32 format validation
- file-size limits
- frame-count limits
- payload-size limits
- first-frame validation
- duplicate-frame conflict detection
- received-byte limits
- sender-side validation

These protections reduce malformed-input risk but do not constitute a complete security audit.

## Responsible use

For security-sensitive workflows:

- verify release SHA-256 checksums
- obtain AirGapQR from the official project repository
- independently verify critical files before use
- keep air-gapped systems physically and operationally isolated as required by your threat model
- do not assume that a valid AirGapQR transfer makes the transferred file trustworthy

## Reporting security issues

If you discover a potential security vulnerability, please avoid publishing exploit details publicly before the issue can be reviewed.

Use GitHub's private security reporting or Security Advisory mechanism if it is available for this repository.

## No warranty

AirGapQR is distributed under the MIT License and is provided without warranty.

See the LICENSE file for the complete license terms.
