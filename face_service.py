import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis

# 🔥 CPU ONLY (ВАЖНО для Railway)
app = FaceAnalysis(
    name="buffalo_l",
    providers=['CPUExecutionProvider']
)

# 🔥 уменьшаем нагрузку (иначе worker падает)
app.prepare(ctx_id=-1, det_size=(320, 320))


def get_embedding(image_file):
    try:
        # читаем файл
        file_bytes = np.frombuffer(image_file.read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        if img is None:
            print("IMAGE DECODE FAILED")
            return None

        faces = app.get(img)

        if not faces:
            print("NO FACE FOUND")
            return None

        embedding = faces[0].embedding
        print("EMBEDDING GENERATED")
        return embedding

    except Exception as e:
        print("FACE ERROR:", str(e))
        return None