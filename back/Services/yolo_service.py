from ultralytics import YOLO 
from PIL import Image, ImageEnhance
import io
import pytesseract
import asyncio
import numpy as np
import re
from Services.moderation_service import ModerationService

# Définir le chemin vers l'exécutable Tesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\salma\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

# Charger YOLOv8x
model = YOLO("yolov8x.pt")

def is_meaningful_text(text: str) -> bool:
    """
    Determines if OCR text is meaningful or just noise/garbage.
    Returns True if text appears to be real content, False if it's OCR noise.
    """
    if not text or len(text.strip()) < 3:
        return False
    
    text = text.strip()
    
    # Count different character types
    letters = len(re.findall(r'[a-zA-ZÀ-ÿ]', text))
    digits = len(re.findall(r'\d', text))
    spaces = len(re.findall(r'\s', text))
    special_chars = len(re.findall(r'[^\w\s]', text))
    total_chars = len(text)
    
    # If text is too short and mostly special characters, it's likely noise
    if total_chars < 15 and special_chars > letters:
        return False
    
    # Calculate ratios
    letter_ratio = letters / total_chars if total_chars > 0 else 0
    special_ratio = special_chars / total_chars if total_chars > 0 else 0
    
    # Text is likely meaningless if:
    # 1. Very high ratio of special characters (>40% instead of 60%)
    # 2. Very low ratio of letters (<30% instead of 20%)
    # 3. Mostly single characters separated by spaces/symbols
    if special_ratio > 0.4 or letter_ratio < 0.3:
        return False
    
    # Check for excessive random character patterns
    random_patterns = re.findall(r'[a-zA-Z]{1,2}\s+[^\w\s]+\s+[a-zA-Z]{1,2}', text)
    if len(random_patterns) > 3:
        return False
    
    # Check for too many isolated letters/symbols
    isolated_chars = re.findall(r'\b[a-zA-Z]\b|\b[^\w\s]\b', text)
    if len(isolated_chars) > total_chars * 0.4:
        return False
    
    # Check for patterns that indicate OCR noise
    # Too many single characters separated by spaces/symbols
    single_char_pattern = re.findall(r'\b\w\b', text)
    if len(single_char_pattern) > len(text.split()) * 0.5:
        return False
    
    # Check for excessive punctuation clusters
    punct_clusters = re.findall(r'[^\w\s]{2,}', text)
    if len(punct_clusters) > 1:
        return False
    
    words = re.findall(r'\b[a-zA-ZÀ-ÿ]{3,}\b', text)
    if len(words) == 0:
        return False
    
    # If it's mostly fragments with no clear words, reject it
    word_chars = sum(len(word) for word in words)
    if word_chars < total_chars * 0.4:
        return False
    
    return True

def clean_ocr_text(text: str) -> str:
    """
    Cleans and filters OCR text, returning empty string if text is meaningless.
    """
    if not text:
        return ""
    
    # Basic cleaning
    text = text.strip()
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Check if text is meaningful
    if not is_meaningful_text(text):
        return ""
    
    return text

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
            cleaned_txt = clean_ocr_text(txt)
            if cleaned_txt:
                return cleaned_txt
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

def analyze_visual_content(detections, image_bytes):
    """
    Analyzes visual content based on YOLO detections and image characteristics.
    Returns compatibility assessment for images without readable text.
    """
    if not detections:
        return {
            "compatible": False,
            "confidence": 0.8,
            "flags": ["no_objects_detected"],
            "reasoning": "Aucun objet détecté - contenu potentiellement problématique ou image de mauvaise qualité"
        }
    
    # Extract detected object labels
    detected_objects = [det["label"].lower() for det in detections]
    object_counts = {}
    for obj in detected_objects:
        object_counts[obj] = object_counts.get(obj, 0) + 1
    
    # Risk assessment based on detected objects
    high_risk_objects = {
        "knife", "gun", "weapon", "fire", "explosion", "blood", "injury", 
        "violence", "fight", "protest", "riot", "police", "military"
    }
    
    medium_risk_objects = {
        "person", "crowd", "group", "gathering", "demonstration", "flag",
        "banner", "sign", "poster", "uniform", "helmet", "mask"
    }
    
    safe_objects = {
        "cat", "dog", "animal", "car", "bicycle", "house", "building", 
        "tree", "flower", "food", "book", "chair", "table", "computer",
        "phone", "bottle", "cup", "couch", "bed", "tv", "clock"
    }
    
    flags = []
    risk_score = 0.0
    
    # Check for high-risk objects
    for obj in detected_objects:
        if any(risk_word in obj for risk_word in high_risk_objects):
            flags.append(f"high_risk_object_{obj}")
            risk_score += 0.8
    
    # Check for medium-risk patterns
    person_count = object_counts.get("person", 0)
    if person_count > 5:
        flags.append("large_crowd_detected")
        risk_score += 0.4
    elif person_count > 2:
        flags.append("group_detected")
        risk_score += 0.2
    
    # Check for potentially concerning combinations
    if "person" in detected_objects and len(detected_objects) > 3:
        flags.append("complex_scene_with_people")
        risk_score += 0.3
    
    # Assess image quality and content density
    total_objects = len(detections)
    if total_objects > 10:
        flags.append("high_object_density")
        risk_score += 0.2
    
    # Conservative approach: flag images with people in complex scenes
    if person_count > 0 and total_objects > 5:
        flags.append("complex_human_scene")
        risk_score += 0.4
    
    # Check for safe content patterns
    safe_object_count = sum(1 for obj in detected_objects if any(safe_word in obj for safe_word in safe_objects))
    if safe_object_count > 0 and person_count == 0:
        risk_score -= 0.3  # Reduce risk for clearly safe content
    
    # Final compatibility decision
    if risk_score >= 0.6:
        compatible = False
        reasoning = f"Contenu visuel potentiellement problématique détecté. Objets: {', '.join(set(detected_objects))}. Signalements: {', '.join(flags)}"
    elif risk_score >= 0.3:
        compatible = False  # Conservative approach - flag for manual review
        reasoning = f"Contenu nécessitant une révision manuelle. Objets détectés: {', '.join(set(detected_objects))}. Analyse visuelle requise."
    else:
        compatible = True
        reasoning = f"Contenu visuel approprié. {total_objects} objet(s) détecté(s): {', '.join(set(detected_objects))}"
    
    confidence = min(0.9, 0.5 + (len(detections) * 0.05))  # Higher confidence with more objects detected
    
    return {
        "compatible": compatible,
        "confidence": confidence,
        "flags": flags,
        "reasoning": reasoning,
        "detected_objects": detected_objects,
        "object_counts": object_counts,
        "risk_score": round(risk_score, 2)
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
    extracted_texts = []
    
    global_text = ocr_extract_text(image_bytes)
    if global_text:
        extracted_texts.append(global_text)
    
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
        text_moderation = analyze_visual_content(detections, image_bytes)

    return {
        "objects": detections,
        "ocr_text": full_text,
        "text_moderation": text_moderation
    }

if __name__ == "__main__":
    results = asyncio.run(analyze_image_file("test_image.jpg"))
    print(results)
