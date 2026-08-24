import os
from io import BytesIO
from PIL import Image, UnidentifiedImageError
from django.conf import settings
from django.core.exceptions import ValidationError

IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp", "gif", "svg", "avif", "heic", "heif"]
VIDEO_EXTENSIONS = ["mp4", "webm", "ogg", "mov", "m4v"]

DEFAULT_MAX_IMAGE_SIZE = 25 * 1024 * 1024    # 25 MB
DEFAULT_MAX_VIDEO_SIZE = 500 * 1024 * 1024   # 500 MB


def _get_file_extension(filename):
    if not filename:
        return ""
    _, ext = os.path.splitext(filename)
    return ext.lstrip(".").lower()


def validate_image_file(file_obj):
    """
    Validates that the file:
    1. Does not exceed MAX_IMAGE_UPLOAD_SIZE (25 MB).
    2. Has an allowed image extension.
    3. Has valid image content / binary signature (Pillow verify for raster, XML check for SVG).
    """
    if not file_obj:
        return

    max_size = getattr(settings, "MAX_IMAGE_UPLOAD_SIZE", DEFAULT_MAX_IMAGE_SIZE)
    if hasattr(file_obj, "size") and file_obj.size and file_obj.size > max_size:
        size_mb = file_obj.size / (1024 * 1024)
        max_mb = max_size / (1024 * 1024)
        raise ValidationError(
            f"Image file size ({size_mb:.1f} MB) exceeds maximum allowed limit of {max_mb:.0f} MB."
        )

    filename = getattr(file_obj, "name", "")
    ext = _get_file_extension(filename)
    if ext and ext not in IMAGE_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file extension '.{ext}'. Allowed formats: {', '.join(IMAGE_EXTENSIONS)}."
        )

    # Content signature verification
    pos = file_obj.tell() if hasattr(file_obj, "tell") else 0
    try:
        if ext == "svg":
            header = file_obj.read(4096)
            header_str = header.decode("utf-8", errors="ignore").lower()
            if "<svg" not in header_str and "<?xml" not in header_str:
                raise ValidationError("Upload a valid SVG image file.")
        else:
            try:
                img = Image.open(file_obj)
                img.verify()
            except (UnidentifiedImageError, OSError, SyntaxError, Exception):
                raise ValidationError(
                    "Upload a valid image. The file content is corrupted or unrecognized."
                )
    finally:
        if hasattr(file_obj, "seek"):
            file_obj.seek(pos)


def validate_video_file(file_obj):
    """
    Validates that the video file:
    1. Does not exceed MAX_VIDEO_UPLOAD_SIZE (500 MB).
    2. Has an allowed video extension.
    3. Has a genuine video container binary signature (reads first 4KB only — memory safe).
    """
    if not file_obj:
        return

    max_size = getattr(settings, "MAX_VIDEO_UPLOAD_SIZE", DEFAULT_MAX_VIDEO_SIZE)
    if hasattr(file_obj, "size") and file_obj.size and file_obj.size > max_size:
        size_mb = file_obj.size / (1024 * 1024)
        max_mb = max_size / (1024 * 1024)
        raise ValidationError(
            f"Video file size ({size_mb:.1f} MB) exceeds maximum allowed limit of {max_mb:.0f} MB."
        )

    filename = getattr(file_obj, "name", "")
    ext = _get_file_extension(filename)
    if ext and ext not in VIDEO_EXTENSIONS:
        raise ValidationError(
            f"Unsupported video file extension '.{ext}'. Allowed formats: {', '.join(VIDEO_EXTENSIONS)}."
        )

    # Bounded binary header inspection (max 4096 bytes)
    pos = file_obj.tell() if hasattr(file_obj, "tell") else 0
    try:
        header = file_obj.read(4096)
    finally:
        if hasattr(file_obj, "seek"):
            file_obj.seek(pos)

    if not header or len(header) < 8:
        raise ValidationError(
            "Upload a valid video file. The file is empty or corrupted."
        )

    # Check container signatures
    # 1. MP4 / MOV / M4V: ISO Base Media File Format (ftyp, moov, mdat, wide, free)
    is_isobmff = (
        b"ftyp" in header[:64]
        or b"moov" in header[:64]
        or b"mdat" in header[:64]
        or b"wide" in header[:64]
        or b"free" in header[:64]
    )

    # 2. WebM / MKV: EBML ID 0x1A45DFA3
    is_ebml = header.startswith(b"\x1a\x45\xdf\xa3")

    # 3. Ogg: OggS magic bytes
    is_ogg = header.startswith(b"OggS")

    # 4. AVI: RIFF header with AVI form type
    is_avi = header.startswith(b"RIFF") and b"AVI " in header[:16]

    if not (is_isobmff or is_ebml or is_ogg or is_avi):
        raise ValidationError(
            "Upload a valid video. The file content does not match a supported video format."
        )

