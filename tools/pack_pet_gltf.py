"""Pack a self-contained glTF with one embedded buffer into a GLB.

Usage: python tools/pack_pet_gltf.py source.gltf output.glb
The input must have an embedded base64 buffer and no external image URIs.
"""

import base64
import json
import struct
import sys
from pathlib import Path


def padded(data: bytes, fill: bytes) -> bytes:
    return data + fill * ((-len(data)) % 4)


def pack(source: Path, target: Path) -> None:
    document = json.loads(source.read_text(encoding="utf-8"))
    buffers = document.get("buffers", [])
    if len(buffers) != 1 or not buffers[0].get("uri", "").startswith(
        "data:application/octet-stream;base64,"
    ):
        raise ValueError("Expected one embedded binary buffer")
    if any(image.get("uri") for image in document.get("images", [])):
        raise ValueError("External or data-URI images need a full glTF converter")

    binary = base64.b64decode(buffers[0].pop("uri").split(",", 1)[1])
    if len(binary) != buffers[0]["byteLength"]:
        raise ValueError("Buffer length differs from glTF metadata")
    json_chunk = padded(json.dumps(document, separators=(",", ":")).encode(), b" ")
    bin_chunk = padded(binary, b"\0")
    total = 12 + 8 + len(json_chunk) + 8 + len(bin_chunk)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as output:
        output.write(struct.pack("<4sII", b"glTF", 2, total))
        output.write(struct.pack("<I4s", len(json_chunk), b"JSON"))
        output.write(json_chunk)
        output.write(struct.pack("<I4s", len(bin_chunk), b"BIN\0"))
        output.write(bin_chunk)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    pack(Path(sys.argv[1]), Path(sys.argv[2]))
