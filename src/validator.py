from PIL import Image
from pathlib import Path

def validate_photo(path, spec):

    with Image.open(path) as image:
        width, height = image.size

    result = {
        "resolution": {
            "width": width,
            "height": height
        },
        "resolution_ok": True,
        "file_size_kb": None,
        "file_size_ok": True,
        "warnings": [],
        "status": "READY"
    }

    # Exact dimensions
    if spec.width_px is not None:

        if width != spec.width_px:
            result["resolution_ok"] = False

        if height != spec.height_px:
            result["resolution_ok"] = False

    # Ranges
    if spec.min_width_px is not None:

        if width < spec.min_width_px:
            result["resolution_ok"] = False

    if spec.max_width_px is not None:

        if width > spec.max_width_px:
            result["resolution_ok"] = False

    if spec.min_height_px is not None:

        if height < spec.min_height_px:
            result["resolution_ok"] = False

    if spec.max_height_px is not None:

        if height > spec.max_height_px:
            result["resolution_ok"] = False

    # File size
    path = Path(path)
    file_size_kb = path.stat().st_size / 1024

    result["file_size_kb"] = round(
        file_size_kb,
        2
    )

    if spec.min_kb is not None:
        if file_size_kb < spec.min_kb:
            result["file_size_ok"] = False

    if spec.max_kb is not None:
        if file_size_kb > spec.max_kb:
            result["file_size_ok"] = False

    # # Live capture warning
    # if spec.live_capture:

    #     result["warnings"].append(
    #         "This application may require live portal capture."
    #     )

    if not result["resolution_ok"]:
        result["status"] = "INVALID"

    if not result["file_size_ok"]:
        result["status"] = "INVALID"

    return result