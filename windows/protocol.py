from __future__ import annotations

import base64
import hashlib
import json
import math
import secrets
import zlib
from dataclasses import dataclass
from typing import List

PROTOCOL = "AGQR"
VERSION = 1
MAX_FILE_SIZE = 5 * 1024 * 1024
MAX_TOTAL_FRAMES = 60000
MAX_PAYLOAD_BYTES = 4096
MAX_PAYLOAD_B64_CHARS = ((MAX_PAYLOAD_BYTES + 2) // 3) * 4
MAX_FRAME_TEXT_CHARS = 10000

class ProtocolError(ValueError):
    pass

@dataclass(frozen=True)
class TransferFrame:
    protocol: str
    version: int
    transfer_id: str
    filename: str
    file_size: int
    sha256: str
    index: int
    total: int
    payload_b64: str
    crc32: str

    def to_text(self) -> str:
        obj = {
            "p": self.protocol, "v": self.version, "id": self.transfer_id,
            "n": self.filename, "s": self.file_size, "h": self.sha256,
            "i": self.index, "t": self.total, "d": self.payload_b64, "c": self.crc32,
        }
        return json.dumps(obj, separators=(",", ":"), ensure_ascii=True)

    @staticmethod
    def from_text(text: str) -> "TransferFrame":
        if not isinstance(text, str):
            raise ProtocolError("QR payload mora biti tekst.")

        if len(text) > MAX_FRAME_TEXT_CHARS:
            raise ProtocolError("QR payload je prevelik.")

        try:
            obj = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProtocolError("QR payload nije validan AGQR JSON.") from exc
        if not isinstance(obj, dict):
            raise ProtocolError("AGQR frame mora biti JSON objekat.")
        
        required = {"p","v","id","n","s","h","i","t","d","c"}
        if set(obj) != required:
            raise ProtocolError("AGQR frame ima neocekivana polja.")

        if not isinstance(obj["p"], str):
            raise ProtocolError("Polje p mora biti string.")

        if type(obj["v"]) is not int:
            raise ProtocolError("Polje v mora biti integer.")

        if not isinstance(obj["id"], str):
            raise ProtocolError("Polje id mora biti string.")

        if not isinstance(obj["n"], str):
            raise ProtocolError("Polje n mora biti string.")

        if type(obj["s"]) is not int:
            raise ProtocolError("Polje s mora biti integer.")

        if not isinstance(obj["h"], str):
            raise ProtocolError("Polje h mora biti string.")

        if type(obj["i"]) is not int:
            raise ProtocolError("Polje i mora biti integer.")

        if type(obj["t"]) is not int:
            raise ProtocolError("Polje t mora biti integer.")

        if not isinstance(obj["d"], str):
            raise ProtocolError("Polje d mora biti string.")

        if not isinstance(obj["c"], str):
            raise ProtocolError("Polje c mora biti string.")
        

        f = TransferFrame(
            protocol=obj["p"],
            version=obj["v"],
            transfer_id=obj["id"],
            filename=obj["n"],
            file_size=obj["s"],
            sha256=obj["h"],
            index=obj["i"],
            total=obj["t"],
            payload_b64=obj["d"],
            crc32=obj["c"]
        )

        f.validate()
        return f

    def validate(self):
        if self.protocol != PROTOCOL: 
            raise ProtocolError("Nepoznat protokol.")
        if self.version != VERSION: 
            raise ProtocolError("Nepodrzana verzija protokola.")
        if len(self.transfer_id) != 16 or any(
            ch not in "0123456789abcdef" for ch in self.transfer_id
        ):
            raise ProtocolError("Los transfer ID.")
        if not (0 <= self.file_size <= MAX_FILE_SIZE):
            raise ProtocolError("Los file size.")
        if len(self.sha256) != 64 or any(
            ch not in "0123456789abcdef" for ch in self.sha256
        ):
            raise ProtocolError("Los SHA-256.")
        if len(self.crc32) != 8 or any(
            ch not in "0123456789abcdef" for ch in self.crc32
        ):
            raise ProtocolError("Los CRC32.")
        if not (1 <= self.total <= MAX_TOTAL_FRAMES):
            raise ProtocolError("Los broj frame-ova.")

        if not (0 <= self.index < self.total):
            raise ProtocolError("Los frame indeks.")
        if not self.filename or len(self.filename) > 255:
            raise ProtocolError("Los naziv fajla.")

    def payload_bytes(self) -> bytes:
        if len(self.payload_b64) > MAX_PAYLOAD_B64_CHARS:
            raise ProtocolError("Base64 payload je prevelik.")
        try:
            raw = base64.b64decode(self.payload_b64, validate=True)
        except Exception as exc:
            raise ProtocolError("Base64 payload nije validan.") from exc

        if len(raw) > MAX_PAYLOAD_BYTES:
            raise ProtocolError("Payload frame-a je prevelik.")

        crc = f"{zlib.crc32(raw) & 0xffffffff:08x}"

        if crc != self.crc32:
            raise ProtocolError("CRC32 frame-a nije ispravan.")

        return raw

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def encode_file(filename: str, data: bytes, chunk_size: int = 100) -> List[TransferFrame]:

    if not isinstance(filename, str) or not filename or len(filename) > 255:
        raise ProtocolError("Los naziv fajla.")

    if type(data) is not bytes:
        raise ProtocolError("Podaci fajla moraju biti bytes.")

    if len(data) > MAX_FILE_SIZE:
        raise ProtocolError("Fajl je prevelik.")

    if type(chunk_size) is not int or not (1 <= chunk_size <= MAX_PAYLOAD_BYTES):
        raise ProtocolError("Los chunk size.")

    transfer_id = secrets.token_hex(8)
    digest = sha256_hex(data)
    total = max(1, math.ceil(len(data)/chunk_size))

    if total > MAX_TOTAL_FRAMES:
        raise ProtocolError("Prevelik broj frame-ova.")

    frames = []
    for i in range(total):
        chunk = data[i*chunk_size:(i+1)*chunk_size]
        frames.append(TransferFrame(
            protocol=PROTOCOL, version=VERSION, transfer_id=transfer_id,
            filename=filename, file_size=len(data), sha256=digest,
            index=i, total=total, payload_b64=base64.b64encode(chunk).decode("ascii"),
            crc32=f"{zlib.crc32(chunk) & 0xffffffff:08x}",
        ))
    return frames

class TransferAssembler:
    def __init__(self): self.reset()

    def reset(self):
        self.transfer_id = self.filename = self.sha256 = None
        self.file_size = self.total = None
        self.parts = {}
        self.received_bytes = 0

    def add_text(self, text: str):
        frame = TransferFrame.from_text(text)
        payload = frame.payload_bytes()

        if frame.file_size > 0 and len(payload) == 0:
            raise ProtocolError("Prazan payload nije dozvoljen za neprazan fajl.")

        if self.transfer_id is None:
            self.transfer_id = frame.transfer_id
            self.filename = frame.filename
            self.file_size = frame.file_size
            self.sha256 = frame.sha256
            self.total = frame.total

        else:
            if self.transfer_id != frame.transfer_id:
                raise ProtocolError(
                    f"Drugi transfer ID: expected={self.transfer_id}, got={frame.transfer_id}"
                )

            if self.filename != frame.filename:
                raise ProtocolError(
                    f"Drugi filename: expected={self.filename}, got={frame.filename}"
                )

            if self.file_size != frame.file_size:
                raise ProtocolError(
                    f"Drugi file size: expected={self.file_size}, got={frame.file_size}"
                )

            if self.sha256 != frame.sha256:
                raise ProtocolError(
                    f"Drugi SHA-256: expected={self.sha256}, got={frame.sha256}"
                )

            if self.total != frame.total:
                raise ProtocolError(
                    f"Drugi total frames: expected={self.total}, got={frame.total}"
                )

        if frame.index in self.parts:
            if self.parts[frame.index] != payload:
                raise ProtocolError(
                    f"Konfliktni duplikat frame-a {frame.index + 1}."
                )

            return frame

        if self.received_bytes + len(payload) > self.file_size:
            raise ProtocolError("Primljeni podaci prelaze deklarisanu velicinu fajla.")
        
        self.parts[frame.index] = payload
        self.received_bytes += len(payload)
        return frame

    @property
    def progress(self):
        return (len(self.parts), self.total or 0)

    @property
    def missing_indices(self):
        if not self.total:
            return []
        return [i for i in range(self.total) if i not in self.parts]

    @property
    def complete(self):
        return bool(self.total) and len(self.parts) == self.total

    def build(self):
        if not self.complete:
            raise ProtocolError("Transfer nije kompletan.")
        data = b"".join(self.parts[i] for i in range(self.total))
        if len(data) != self.file_size:
            raise ProtocolError("Velicina fajla se ne poklapa.")
        if sha256_hex(data) != self.sha256:
            raise ProtocolError("SHA-256 se ne poklapa.")
        return data
