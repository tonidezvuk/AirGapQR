import base64
import zlib
from dataclasses import replace

from protocol import (
    ProtocolError,
    TransferAssembler,
    encode_file,
    MAX_PAYLOAD_BYTES,
)


def expect_error(name, func):
    try:
        func()
    except ProtocolError as exc:
        print(f"[PASS] {name}: {exc}")
        return

    raise AssertionError(f"[FAIL] {name}: ProtocolError nije podignut")


# 1. Normalan encode/decode
data = b"AirGapQR protocol test " * 50

frames = encode_file(
    "test.txt",
    data,
    chunk_size=100
)

assembler = TransferAssembler()

for frame in frames:
    assembler.add_text(frame.to_text())

rebuilt = assembler.build()

assert rebuilt == data
print("[PASS] normalan encode/decode")


# 2. Isti frame kao duplikat mora biti bezopasan
assembler = TransferAssembler()
assembler.add_text(frames[0].to_text())
assembler.add_text(frames[0].to_text())

assert assembler.progress[0] == 1
print("[PASS] identican duplikat")


# 3. Isti index, ali drugi validan payload mora biti odbijen
original = frames[0]

different_payload = b"X" * len(original.payload_bytes())

conflicting = replace(
    original,
    payload_b64=base64.b64encode(different_payload).decode("ascii"),
    crc32=f"{zlib.crc32(different_payload) & 0xffffffff:08x}",
)

assembler = TransferAssembler()
assembler.add_text(original.to_text())

expect_error(
    "konfliktni duplikat",
    lambda: assembler.add_text(conflicting.to_text())
)


# 4. Los CRC mora biti odbijen
wrong_crc = (
    "00000000"
    if original.crc32 != "00000000"
    else "ffffffff"
)

bad_crc = replace(
    original,
    crc32=wrong_crc
)

expect_error(
    "los CRC32",
    lambda: TransferAssembler().add_text(bad_crc.to_text())
)


# 5. Prevelik payload mora biti odbijen
oversized_raw = b"A" * (MAX_PAYLOAD_BYTES + 1)

oversized = replace(
    original,
    payload_b64=base64.b64encode(oversized_raw).decode("ascii"),
    crc32=f"{zlib.crc32(oversized_raw) & 0xffffffff:08x}",
)

expect_error(
    "prevelik payload",
    lambda: oversized.payload_bytes()
)

# 6. Malformed JSON mora biti odbijen
expect_error(
    "malformed JSON",
    lambda: TransferAssembler().add_text("{ovo nije json")
)


# 7. Pogresan tip polja mora biti odbijen
bad_type_text = (
    '{"p":"AGQR","v":"1","id":"0123456789abcdef","n":"x.bin",'
    '"s":1,"h":"' + ("0" * 64) + '","i":0,"t":1,'
    '"d":"QQ==","c":"d3d99e8b"}'
)

expect_error(
    "pogresan tip polja",
    lambda: TransferAssembler().add_text(bad_type_text)
)


# 8. Prevelik file_size mora biti odbijen
too_large_size_text = (
    '{"p":"AGQR","v":1,"id":"0123456789abcdef","n":"x.bin",'
    '"s":5242881,"h":"' + ("0" * 64) + '","i":0,"t":1,'
    '"d":"","c":"00000000"}'
)

expect_error(
    "prevelik file_size",
    lambda: TransferAssembler().add_text(too_large_size_text)
)

print()
print("SVE PROTOCOL PROVERE SU PROSLE.")