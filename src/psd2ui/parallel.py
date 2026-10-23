"""Isolated PSD render workers. Each process opens its own PSD once."""
from concurrent.futures import ProcessPoolExecutor
from io import BytesIO
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys

from psd_tools import PSDImage

from .diagnostics import Diagnostics


_PSD = None


def worker_count(value):
    if type(value) is not int or value < 0:
        raise ValueError("workers 必须是大于等于 0 的整数；0 自动，1 单进程。")
    count = value or (len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else os.cpu_count() or 1)
    return min(count, 61) if os.name == "nt" else count


def render_worker_count(source, requested, tasks):
    count = min(worker_count(requested), tasks)
    if requested:
        return count
    try:
        memory = os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
    except (ValueError, OSError, AttributeError):
        memory = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True)) if sys.platform == "darwin" else 0
    if memory:
        # Each process owns parsed PSD records, decoded caches and compositor
        # arrays. Reserve half of RAM for the main process, OS and other apps.
        per_process = 256 * 1024**2 + 16 * Path(source).stat().st_size
        count = min(count, max(1, (memory // 2) // per_process))
    return count


def initialize(source):
    global _PSD
    _PSD = PSDImage.open(source)


def render(job):
    from .exporter import composite_image, render_bounds
    from .rasters import write_raster
    indices, path, raster_path = job
    layer = _PSD
    for index in indices:
        layer = layer[index]
    diagnostics = Diagnostics()
    try:
        image, box = composite_image(layer, render_bounds(layer, layer), diagnostics, path)
        with image:
            if raster_path is not None:
                return {"raster": write_raster(image, raster_path), "box": box, "diagnostics": diagnostics.items}
            image.info.clear()
            stream = BytesIO()
            image.save(stream, format="PNG")
            return {"png": stream.getvalue(), "box": box, "diagnostics": diagnostics.items}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}", "diagnostics": diagnostics.items}


def create_pool(source, workers, tasks):
    return ProcessPoolExecutor(max_workers=min(worker_count(workers), tasks),
                               mp_context=multiprocessing.get_context("spawn"),
                               initializer=initialize, initargs=(str(source),))
