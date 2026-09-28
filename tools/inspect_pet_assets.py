"""Validate the seven bundled pet GLBs and print their render metadata."""

import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "frontend/public/assets/pets"
SPECIES = ("cat", "dog", "fox", "rabbit", "panda", "bear", "wolf")


def inspect(path: Path) -> dict:
    data = path.read_bytes()
    if len(data) < 20 or data[:4] != b"glTF" or struct.unpack_from("<I", data, 8)[0] != len(data):
        raise ValueError(f"Invalid GLB header: {path}")
    json_size = struct.unpack_from("<I", data, 12)[0]
    if data[16:20] != b"JSON":
        raise ValueError(f"Missing JSON chunk: {path}")
    document = json.loads(data[20 : 20 + json_size].decode("utf-8"))
    clips = [animation.get("name", "") for animation in document.get("animations", [])]
    bounds = []
    for mesh in document.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            accessor = document["accessors"][primitive["attributes"]["POSITION"]]
            if "min" in accessor and "max" in accessor:
                bounds.append((accessor["min"], accessor["max"]))
    return {
        "bytes": len(data),
        "meshes": len(document.get("meshes", [])),
        "skins": len(document.get("skins", [])),
        "clips": clips,
        "bounds": bounds,
        "roots": [document["nodes"][index].get("name", "") for scene in document.get("scenes", []) for index in scene.get("nodes", [])],
    }


if __name__ == "__main__":
    for species in SPECIES:
        path = ROOT / species / "companion.glb"
        result = inspect(path)
        print(species, json.dumps(result, ensure_ascii=False))
