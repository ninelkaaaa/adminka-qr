import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis

app = FaceAnalysis(name="buffalo_l")
app.prepare(ctx_id=0, det_size=(640, 640))


def get_embedding(image_file):
    try:
        file_bytes = np.frombuffer(image_file.read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        if img is None:
            return None

        faces = app.get(img)

        if len(faces) == 0:
            return None

        return faces[0].embedding

    except Exception as e:
        print("Embedding error:", e)
        return None