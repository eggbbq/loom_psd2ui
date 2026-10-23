"""Temporary RGBA storage: deduplicate before spending CPU encoding PNGs.

Workers write their results directly into the export's private staging area.
Only small records cross process boundaries; decoded images are loaded one
size bucket at a time rather than retaining every PSD raster in memory.
"""
from pathlib import Path

from PIL import Image


def write_raster(image, path):
    Path(path).write_bytes(image.tobytes())
    return {"path": str(path), "size": image.size}


def load_raster(record):
    data = record["data"] if "data" in record else Path(record["path"]).read_bytes()
    return Image.frombytes("RGBA", record["size"], data)


def encode_raster(job):
    record, destination = job
    with load_raster(record) as image:
        image.save(destination, format="PNG")


class RasterStore:
    def __init__(self, directory, memory_limit=128 * 1024**2):
        self.directory = Path(directory)
        self.entries = {}
        self.next_id = 0
        self.memory_limit = memory_limit
        self.memory_bytes = 0

    def write(self, image):
        # Serial rendering avoids a disk round trip for the common small PSD.
        # Process workers always use files, avoiding large pixel IPC payloads.
        size = image.width * image.height * 4
        if self.memory_bytes + size <= self.memory_limit:
            data = image.tobytes()
            self.memory_bytes += len(data)
            return {"data": data, "size": image.size}
        return write_raster(image, self.reserve())

    def reserve(self):
        path = self.directory / f"{self.next_id}.rgba"
        self.next_id += 1
        return path

    def put(self, asset, record):
        previous = self.entries.get(asset)
        self.entries[asset] = record
        if previous is not None:
            if "data" in previous:
                self.memory_bytes -= len(previous["data"])
            else:
                Path(previous["path"]).unlink()

    def size(self, asset):
        return tuple(self.entries[asset]["size"])

    def load(self, asset):
        return load_raster(self.entries[asset])
