import cv2

from smart_crop import smart_crop


image = cv2.imread("input/photo1.jpg")

if image is None:
    raise FileNotFoundError(
        "Could not find input/photo1.jpg"
    )

cropped = smart_crop(image)

cv2.imwrite(
    "output/smart_crop.jpg",
    cropped
)

print("Saved: output/smart_crop.jpg")