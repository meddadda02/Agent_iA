from ultralytics import YOLO
from PIL import Image
import io
# Charge le modèle YOLO une seule fois au démarrage
model = YOLO("yolov8n.pt")  # Tu peux changer de modèle selon besoins (ex: yolov8m.pt)

def analyze_with_yolo(image_bytes):
    """
    Analyse une image (bytes) et retourne la liste des objets détectés.
    """
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    results = model(image)

    detections = []
    for result in results:
        for box in result.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            label = model.names[cls_id]
            bbox = [round(coord, 2) for coord in box.xyxy[0].tolist()]  # [x_min, y_min, x_max, y_max]
            detections.append({
                "label": label,
                "confidence": round(conf, 3),
                "bbox": bbox
            })

    return detections


def analyze_image_file(image_path):
    """
    Wrapper to analyze image from file path using the existing `analyze_with_yolo`.
    """
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    return analyze_with_yolo(image_bytes)
