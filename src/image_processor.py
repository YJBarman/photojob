from PIL import Image


def resize_image(
    image,
    width,
    height
):

    return image.resize(
        (width, height),
        Image.Resampling.LANCZOS
    )


def save_jpeg(
    image,
    path,
    quality=90
):

    image.save(
        path,
        format="JPEG",
        quality=quality,
        optimize=True
    )