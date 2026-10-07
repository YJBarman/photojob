from PIL import Image


TARGET_WIDTH = 35
TARGET_HEIGHT = 45

OUTPUT_WIDTH = 413
OUTPUT_HEIGHT = 531


def crop_to_ratio(image, target_ratio):
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


def create_photo(input_path, output_path):

    image = Image.open(input_path).convert("RGB")

    print("Original size:", image.size)

    target_ratio = TARGET_WIDTH / TARGET_HEIGHT

    # Crop
    image = crop_to_ratio(
        image,
        target_ratio
    )

    print("After crop:", image.size)

    # Resize
    image = image.resize(
        (OUTPUT_WIDTH, OUTPUT_HEIGHT),
        Image.Resampling.LANCZOS
    )

    # Save
    image.save(
        output_path,
        quality=95,
        dpi=(300, 300)
    )

    print("Final size:", image.size)
    print("Saved:", output_path)


if __name__ == "__main__":

    create_photo(
        "input/photo1.jpg",
        "output/job_photo1.jpg"
    )