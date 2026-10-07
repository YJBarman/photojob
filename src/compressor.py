from io import BytesIO
from PIL import Image


def compress_to_size(
    image,
    min_kb=None,
    max_kb=None
):
    """
    Compress a PIL image to JPEG.

    Tries to stay within the requested file-size range.
    Returns:
        image,
        jpeg_quality,
        file_size_kb
    """

    # If there is no maximum size requirement,
    # simply use high quality.
    if max_kb is None:

        buffer = BytesIO()

        image.save(
            buffer,
            format="JPEG",
            quality=95,
            optimize=True
        )

        size_kb = len(buffer.getvalue()) / 1024

        return image, 95, size_kb

    # Start from highest quality and decrease.
    for quality in range(100, 10, -1):

        buffer = BytesIO()

        image.save(
            buffer,
            format="JPEG",
            quality=quality,
            optimize=True
        )

        size_kb = len(buffer.getvalue()) / 1024

        # We found a valid range.
        if (
            (min_kb is None or size_kb >= min_kb)
            and
            size_kb <= max_kb
        ):

            print(
                f"Compression selected: "
                f"quality={quality}, "
                f"size={size_kb:.2f} KB"
            )

            return image, quality, size_kb

    # If we couldn't reach the minimum size,
    # use maximum quality and report the actual size.
    buffer = BytesIO()

    image.save(
        buffer,
        format="JPEG",
        quality=100,
        optimize=False
    )

    size_kb = len(buffer.getvalue()) / 1024

    print(
        f"Warning: image naturally produces "
        f"{size_kb:.2f} KB at maximum quality."
    )

    return image, 100, size_kb