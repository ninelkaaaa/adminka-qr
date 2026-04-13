import numpy as np
import cv2
from insightface.app import FaceAnalysis

app = FaceAnalysis(
    name="buffalo_l",
    providers=['CPUExecutionProvider']
)

app.prepare(ctx_id=-1, det_size=(320, 320))


def get_embedding(image_file):
    try:
        file_bytes = np.frombuffer(image_file.read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        if img is None:
            return None

        faces = app.get(img)

        if not faces:
            return None

        return faces[0].embedding

    except Exception as e:
        print("FACE ERROR:", e)
        return None