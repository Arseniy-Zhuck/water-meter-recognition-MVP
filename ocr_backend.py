import numpy as np
engine = None

def ocr_image(image, roi=None):
    crop = image.crop(tuple(roi)) if roi else image
    w, h = crop.size
    scale = min(1.0, 2048 / max(w, h))
    if scale < 1:
        crop = crop.resize((max(1, round(w * scale)), max(1, round(h * scale))))
    if roi:
        result, _ = engine(np.asarray(crop), use_det=False, use_cls=True)
        return [{"text": str(text), "confidence": round(float(score), 4),
                 "box": [[roi[0], roi[1]], [roi[2], roi[1]], [roi[2], roi[3]], [roi[0], roi[3]]]}
                for text, score in result or []]
    result, _ = engine(np.asarray(crop), use_cls=True)
    output = []
    for box, text, score in result or []:
        points = [[round(float(x) / scale + (roi[0] if roi else 0)),
                   round(float(y) / scale + (roi[1] if roi else 0))] for x, y in box]
        output.append({"text": str(text), "confidence": round(float(score), 4), "box": points})
    return output
