import cv2


def detect_face(input_path, output_path):

    # Load image
    image = cv2.imread(input_path)

    if image is None:
        raise FileNotFoundError(
            f"Could not open image: {input_path}"
        )

    # Convert to grayscale
    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    # Load OpenCV's face detector
    face_detector = cv2.CascadeClassifier(
        cv2.data.haarcascades
        + "haarcascade_frontalface_default.xml"
    )

    # Detect faces
    faces = face_detector.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(150, 150)
    )

    print("Faces detected:", len(faces))

    # Draw bounding boxes
    for (x, y, w, h) in faces:

        print(
            f"Face: x={x}, y={y}, "
            f"width={w}, height={h}"
        )

        cv2.rectangle(
            image,
            (x, y),
            (x + w, y + h),
            (0, 255, 0),
            3
        )

    # Save result
    cv2.imwrite(
        output_path,
        image
    )

    print("Saved:", output_path)


if __name__ == "__main__":

    detect_face(
        "input/photo1.jpg",
        "output/face_detected1.jpg"
    )