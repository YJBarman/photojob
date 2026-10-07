import cv2


TARGET_RATIO = 35 / 45


def detect_face(image):

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    detector = cv2.CascadeClassifier(
        cv2.data.haarcascades
        + "haarcascade_frontalface_default.xml"
    )

    faces = detector.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(150, 150)
    )

    if len(faces) == 0:
        raise ValueError("No face detected.")

    # For now, use the largest detected face.
    face = max(
        faces,
        key=lambda f: f[2] * f[3]
    )

    return face


def smart_crop(image):

    height, width = image.shape[:2]

    x, y, w, h = detect_face(image)

    print(
        f"Face: x={x}, y={y}, "
        f"w={w}, h={h}"
    )

    # Make crop about 2.2 times the face width.
    crop_width = int(w * 2.2)

    # Calculate height required for 35:45 ratio.
    crop_height = int(
        crop_width / TARGET_RATIO
    )

    # Face center
    face_center_x = x + w / 2

    # Put some space above the head.
    crop_center_y = y + h * 0.65

    # Calculate crop boundaries
    left = int(
        face_center_x - crop_width / 2
    )

    top = int(
        crop_center_y - crop_height / 2
    )

    right = left + crop_width
    bottom = top + crop_height

    # Keep crop inside image
    if left < 0:
        right -= left
        left = 0

    if right > width:
        left -= right - width
        right = width

    if top < 0:
        bottom -= top
        top = 0

    if bottom > height:
        top -= bottom - height
        bottom = height

    # Final safety check
    left = max(0, left)
    top = max(0, top)
    right = min(width, right)
    bottom = min(height, bottom)

    print(
        f"Crop: left={left}, top={top}, "
        f"right={right}, bottom={bottom}"
    )

    return image[top:bottom, left:right]