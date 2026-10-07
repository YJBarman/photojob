from pathlib import Path

import cv2
from PIL import Image

from smart_crop import smart_crop
from specifications import PhotoSpec
from image_processor import resize_image, save_jpeg
from compressor import compress_to_size
from validator import validate_photo
import time


def mm_to_pixels(mm, dpi=300):
    """
    Convert millimeters to pixels at a given DPI.
    """

    return round(
        mm / 25.4 * dpi
    )


def get_output_dimensions(specification):
    """
    Determine the final pixel dimensions.

    Priority:

    1. Exact pixel dimensions
    2. Physical dimensions in mm
    3. Dimension range
    """

    # ---------------------------------------------------------
    # Exact pixel dimensions
    # ---------------------------------------------------------

    if (
        specification.width_px is not None
        and specification.height_px is not None
    ):

        return (
            specification.width_px,
            specification.height_px
        )

    # ---------------------------------------------------------
    # Physical dimensions
    # ---------------------------------------------------------

    if specification.physical_size_mm:

        width_mm, height_mm = (
            specification.physical_size_mm
        )

        width_px = mm_to_pixels(
            width_mm
        )

        height_px = mm_to_pixels(
            height_mm
        )

        return (
            width_px,
            height_px
        )

    # ---------------------------------------------------------
    # Dimension range
    #
    # For a range we use the minimum valid dimensions
    # while preserving a square output if the specification
    # does not provide a specific aspect ratio.
    # ---------------------------------------------------------

    if (
        specification.min_width_px is not None
        and specification.min_height_px is not None
    ):

        return (
            specification.min_width_px,
            specification.min_height_px
        )

    # ---------------------------------------------------------
    # No usable dimensions
    # ---------------------------------------------------------

    raise ValueError(
        f"The specification '{specification.name}' "
        "does not contain usable output dimensions. "
        "Use a preset with defined dimensions or "
        "use Custom."
    )


def create_recruitment_photo(
    input_path,
    output_path,
    specification
):

    total_start = time.perf_counter()

    print()
    print("==============================")
    print("RECRUITMENT PHOTO MAKER")
    print("==============================")

    print(
        f"Specification: "
        f"{specification.name}"
    )

    # ---------------------------------------------------------
    # 1. Load original image
    # ---------------------------------------------------------

    stage_start = time.perf_counter()

    input_path = Path(input_path)
    output_path = Path(output_path)

    image = cv2.imread(
        str(input_path)
    )

    if image is None:
        raise FileNotFoundError(
            f"Could not open image: "
            f"{input_path}"
        )

    load_time = time.perf_counter() - stage_start

    print()
    print("Original image:")
    print(image.shape)
    print(f"Timing | Image load: {load_time:.3f}s")

    # ---------------------------------------------------------
    # 2. Smart face-aware crop
    # ---------------------------------------------------------

    stage_start = time.perf_counter()

    cropped = smart_crop(
        image
    )

    crop_time = time.perf_counter() - stage_start

    print()
    print("Smart crop completed.")
    print(f"Timing | Face detection + smart crop: {crop_time:.3f}s")

    # ---------------------------------------------------------
    # 3. OpenCV → PIL
    # ---------------------------------------------------------

    stage_start = time.perf_counter()

    cropped_rgb = cv2.cvtColor(
        cropped,
        cv2.COLOR_BGR2RGB
    )

    pil_image = Image.fromarray(
        cropped_rgb
    )

    conversion_time = time.perf_counter() - stage_start

    print(
        f"Timing | OpenCV → PIL: "
        f"{conversion_time:.3f}s"
    )

    # ---------------------------------------------------------
    # 4. Determine output dimensions
    # ---------------------------------------------------------

    stage_start = time.perf_counter()

    output_width, output_height = (
        get_output_dimensions(
            specification
        )
    )

    dimensions_time = time.perf_counter() - stage_start

    print(
        f"Timing | Dimension calculation: "
        f"{dimensions_time:.3f}s"
    )

    print(
        f"Final dimensions: "
        f"{output_width} × "
        f"{output_height}"
    )

    # ---------------------------------------------------------
    # 5. Resize
    # ---------------------------------------------------------

    stage_start = time.perf_counter()

    final_image = resize_image(
        pil_image,
        output_width,
        output_height
    )

    resize_time = time.perf_counter() - stage_start

    print(
        f"Timing | Resize: "
        f"{resize_time:.3f}s"
    )

    # ---------------------------------------------------------
    # 6. Compress
    # ---------------------------------------------------------

    stage_start = time.perf_counter()

    final_image, quality, size_kb = (
        compress_to_size(
            final_image,
            min_kb=specification.min_kb,
            max_kb=specification.max_kb
        )
    )

    compression_time = time.perf_counter() - stage_start

    print(
        f"Timing | Compression: "
        f"{compression_time:.3f}s"
    )

    print(
        f"Compression selected: "
        f"quality={quality}, "
        f"size={size_kb} KB"
    )

    # ---------------------------------------------------------
    # 7. Create output directory
    # ---------------------------------------------------------

    stage_start = time.perf_counter()

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    directory_time = time.perf_counter() - stage_start

    print(
        f"Timing | Output directory: "
        f"{directory_time:.3f}s"
    )

    # ---------------------------------------------------------
    # 8. Save JPEG
    # ---------------------------------------------------------

    stage_start = time.perf_counter()

    save_jpeg(
        final_image,
        output_path,
        quality=quality
    )

    save_time = time.perf_counter() - stage_start

    print(
        f"Timing | JPEG save: "
        f"{save_time:.3f}s"
    )

    print(
        f"Compression quality: "
        f"{quality}"
    )

    print(
        f"Saved: {output_path}"
    )

    # ---------------------------------------------------------
    # 9. Validate
    # ---------------------------------------------------------

    stage_start = time.perf_counter()

    result = validate_photo(
        output_path,
        specification
    )

    validation_time = time.perf_counter() - stage_start

    print(
        f"Timing | Validation: "
        f"{validation_time:.3f}s"
    )

    print()
    print("VALIDATION")
    print("------------------------------")

    print(
        f"Resolution: "
        f"{result['resolution']['width']} × "
        f"{result['resolution']['height']}"
    )

    print(
        f"File size: "
        f"{result['file_size_kb']} KB"
    )

    print(
        f"Resolution OK: "
        f"{result['resolution_ok']}"
    )

    print(
        f"File size OK: "
        f"{result['file_size_ok']}"
    )

    print(
        f"Status: "
        f"{result['status']}"
    )

    # ---------------------------------------------------------
    # Total timing
    # ---------------------------------------------------------

    total_time = time.perf_counter() - total_start

    print()
    print("==============================")
    print(
        f"Timing | TOTAL ENGINE: "
        f"{total_time:.3f}s"
    )
    print("==============================")

    return result