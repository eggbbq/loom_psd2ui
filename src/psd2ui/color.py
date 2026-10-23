"""Bounded, process-local ICC transforms with psd-tools' conversion settings."""
from functools import lru_cache
from io import BytesIO
import logging


@lru_cache(maxsize=8)
def _transform(profile, mode):
    from PIL import ImageCms

    source = ImageCms.ImageCmsProfile(BytesIO(profile))
    target = ImageCms.createProfile("sRGB")
    return ImageCms.buildTransformFromOpenProfiles(source, target, mode, "RGB")


def apply_icc(image, profile):
    # Match pil_io._apply_icc, including alpha and failure diagnostics. Do not
    # cache converted images or skip the actual source-to-sRGB conversion.
    logger = logging.getLogger("psd_tools.api.pil_io")
    try:
        from PIL import ImageCms
    except ImportError:
        logger.warning("ICC profile found but not supported. Install little-cms.")
        return image
    try:
        alpha = image.getchannel("A") if image.mode in ("RGBA", "LA") else None
        working = image if alpha is None else image.convert(image.mode.replace("A", ""))
        result = ImageCms.applyTransform(working, _transform(bytes(profile), working.mode))
    except ImageCms.PyCMSError as exc:
        logger.error("Failed to apply ICC profile: %s", exc)
        return image
    if alpha is not None:
        result.putalpha(alpha)
    return result
