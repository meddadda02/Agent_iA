from ultralytics import YOLO 
from PIL import Image, ImageEnhance
import io
import pytesseract
import asyncio
import numpy as np
from Services.moderation_service import ModerationService

# Définir le chemin vers l’exécutable Tesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\salma\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

# Charger YOLOv8x
model = YOLO("yolov8x.pt")


def analyze_with_yolo(image_bytes, conf_threshold=0.3):
    """
    Renvoie la liste des objets détectés par YOLO.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_np = np.array(image)

        results = model.predict(img_np, conf=conf_threshold)
        detections = []

        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                label = model.names[cls_id]
                bbox = [round(coord, 2) for coord in box.xyxy[0].tolist()]
                detections.append({
                    "label": label,
                    "confidence": round(conf, 3),
                    "bbox": bbox
                })

        return detections

    except Exception:
        return []


def ocr_extract_text(image_bytes):
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("L")  # grayscale
        # Optional: light contrast
        image = ImageEnhance.Contrast(image).enhance(1.3)

        # Try a few PSM modes quickly (works great for banners)
        configs = [
            r'--oem 3 --psm 6',   # block of text
            r'--oem 3 --psm 4',   # column(s) of text
            r'--oem 3 --psm 7',   # single text line
        ]
        langs = "eng"  # start simple; add +fra+ara once eng works
        for cfg in configs:
            txt = pytesseract.image_to_string(image, lang=langs, config=cfg).strip()
            if txt:
                return txt
        return ""
    except Exception:
        return ""




async def moderate_text(text):
    """
    Modération texte via Groq.
    """
    if not text:
        return {"message": "Aucun texte détecté", "compatible": True}

    lang = ModerationService.detect_language(text)
    moderation_result = await ModerationService.query_groq_enhanced(text, language=lang)
    compatible_text = moderation_result.get("status") in ["conforme", "safe"]
    return {
        "language": lang,
        "moderation": moderation_result,
        "compatible": compatible_text
    }

async def analyze_image_file(image_path):
    """
    Fonction complète : détection objets, OCR, modération texte.
    """
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    # 1️⃣ Détection objets
    detections = analyze_with_yolo(image_bytes)

    # 2️⃣ OCR global + par crop
    extracted_texts = [ocr_extract_text(image_bytes)]
    for det in detections:
        x1, y1, x2, y2 = map(int, det["bbox"])
        cropped = image.crop((x1, y1, x2, y2))
        buf = io.BytesIO()
        cropped.save(buf, format="JPEG")
        crop_bytes = buf.getvalue()
        text_crop = ocr_extract_text(crop_bytes)
        if text_crop:
            extracted_texts.append(text_crop)

    full_text = " ".join(extracted_texts).strip()

    # 3️⃣ Modération texte uniquement si du texte est présent
    if full_text:
        text_moderation = await moderate_text(full_text)
    else:
        text_moderation = {
            "message": "Aucun texte détecté",
            "compatible": True
        }

    return {
        "objects": detections,
        "ocr_text": full_text,
        "text_moderation": text_moderation
    }


if __name__ == "__main__":
    results = asyncio.run(analyze_image_file("test_image.jpg"))
    print(results)