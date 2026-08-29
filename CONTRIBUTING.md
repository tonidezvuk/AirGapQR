# Contributing to AirGapQR

Contributions to AirGapQR are welcome.

AirGapQR is a small open-source project focused on offline optical file transfer, simple behavior, verifiability, and minimal unnecessary dependencies.

## Before contributing

Please keep changes focused and easy to review.

Prefer:

- small, clearly scoped changes
- simple implementations
- minimal new dependencies
- behavior that can be tested offline
- changes that preserve the existing security assumptions of the project

Avoid unnecessary complexity or network dependencies.

## Reporting bugs

When reporting a bug, include:

- AirGapQR version
- operating system
- relevant hardware, especially camera model if applicable
- steps required to reproduce the problem
- expected behavior
- actual behavior
- screenshots or terminal output when useful

Do not include private files, secrets, wallet information, private keys, seed phrases, or other sensitive data.

## Code contributions

Code changes should:

- preserve existing functionality unless the change intentionally modifies it
- include clear reasoning for the change
- avoid unrelated modifications
- preserve platform-specific behavior where required
- pass existing protocol regression tests

For protocol-related changes, additional tests are strongly encouraged.

## Windows and Linux

AirGapQR v0.5.0 currently contains separate Windows and Linux application entry points because camera discovery and some user-interface behavior differ between platforms.

Changes to one platform should not be assumed to be safe for the other platform without testing.

## Protocol changes

Changes to the AirGapQR transfer protocol should be treated carefully.

Protocol changes should document:

- what is changing
- why the change is required
- compatibility implications
- validation rules
- new or modified limits
- corresponding regression tests

Avoid silently changing protocol behavior.

## Security-related changes

AirGapQR has not undergone a complete independent security audit.

Do not describe a change as making AirGapQR "secure", "unbreakable", or formally audited unless that claim can be independently supported.

Potential security vulnerabilities should preferably be reported privately before public exploit details are published.

See `SECURITY.md` for additional information.

## Testing

Before submitting a code change, run the relevant tests.

For protocol changes:

```text
python test_protocol.py
```

Platform-specific user-interface or camera changes should also be tested on the operating system they affect.

## Pull requests

A pull request should explain:

- what changed
- why it changed
- how it was tested
- which platforms were tested

Keep pull requests focused whenever possible.

## License

By contributing to AirGapQR, you agree that your contribution may be distributed under the MIT License used by this project.
