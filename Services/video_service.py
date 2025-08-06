import cv2
import os
from Services.yolo_service import analyze_image_file  # Réutilise la logique YOLO existante

def analyze_video(video_path: str, interval_ms: int = 200) -> dict:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"error": "Failed to open video file."}

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = int((fps * interval_ms) / 1000)

    frame_count = 0
    results = []

    while True:
        success, frame = cap.read()
        if not success:
            break

        if frame_count % frame_interval == 0:
            frame_path = f"temp_frame_{frame_count}.jpg"
            cv2.imwrite(frame_path, frame)

            try:
                result = analyze_image_file(frame_path)
                results.append(result)
            except Exception as e:
                print(f"Erreur lors de l'analyse d'une frame {frame_count}: {e}")

            os.remove(frame_path)

        frame_count += 1

    cap.release()
    return aggregate_results(results)


def _make_hashable(obj):
    """
    Transforme récursivement obj (list, dict, tuple, etc.)
    en une forme hashable : tuple ou valeur primitive.
    """
    if isinstance(obj, dict):
        # Sorted items to ensure determinism
        return tuple((k, _make_hashable(v)) for k, v in sorted(obj.items()))
    if isinstance(obj, list) or isinstance(obj, tuple):
        return tuple(_make_hashable(v) for v in obj)
    return obj  # str, int, float, etc.


def aggregate_results(results):
    """
    Prend en entrée une liste de résultats de frames (list ou dict),
    extrait tous les labels, puis supprime les doublons,
    en conservant l'ordre d'apparition.
    """
    aggregated = {
        "detected_labels": [],
        "frame_count": len(results)
    }

    # 1) Rassembler toutes les détections
    for result in results:
        if isinstance(result, list):
            aggregated["detected_labels"].extend(result)
        elif isinstance(result, dict) and "detected_labels" in result:
            aggregated["detected_labels"].extend(result["detected_labels"])
        else:
            # Au cas où your analyze_image_file retourne directement un dict label->score
            aggregated["detected_labels"].append(result)

    # 2) Dédupliquer quel que soit le format
    unique = []
    seen = set()
    for label in aggregated["detected_labels"]:
        key = _make_hashable(label)
        if key not in seen:
            seen.add(key)
            unique.append(label)

    aggregated["detected_labels"] = unique
    return aggregated
