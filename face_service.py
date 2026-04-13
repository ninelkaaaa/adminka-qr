import numpy as np
import cv2
import insightface

_model = None


def get_model():
    global _model
    if _model is None:
        _model = insightface.app.FaceAnalysis(
            name="buffalo_l",
            providers=['CPUExecutionProvider']
        )
        _model.prepare(ctx_id=-1, det_size=(320, 320))
    return _model


def get_embedding(image_file):
    try:
        image_file.stream.seek(0)

        file_bytes = np.frombuffer(image_file.read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        if img is None:
            return None

        model = get_model()
        faces = model.get(img)

        if not faces:
            return None

        return faces[0].embedding

    except Exception as e:
        print("FACE ERROR:", e)
        return None