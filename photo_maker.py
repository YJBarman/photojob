from PIL import Image


# 35 x 45 mm portrait ratio
TARGET_WIDTH = 35
TARGET_HEIGHT = 45


def crop_to_ratio(image, target_ratio):
    """Center-crop an image to the requested aspect ratio."""

    width, height = image.size
    current_ratio = width / height

    if current_ratio > target_ratio:
        # Image is too wide
        new_width = int(height * target_ratio)
        left = (width - new_width) // 2

        return image.crop(
            (left, 0, left + new_width, height)
        )

    else:
        # Image is too tall
        new_height = int(width / target_ratio)
        top = (height - new_height) // 2

        return image.crop(
            (0, top, width, top + new_height)
        )


def create_photo(input_file, output_file):
    image = Image.open(input_file).convert("RGB")

    target_ratio = TARGET_WIDTH / TARGET_HEIGHT

    # 1. Crop to correct shape
    image = crop_to_ratio(image, target_ratio)

    # 2. Resize
    # 413 x 531 is approximately 35x45 mm at 300 DPI
    image = image.resize((413, 531), Image.Resampling.LANCZOS)

    # 3. Save
    image.save(
        output_file,
        quality=95,
        dpi=(300, 300)
    )

    print(f"Saved: {output_file}")


if __name__ == "__main__":
    create_photo(
        "input.jpg",
        "passport_photo.jpg"
    )