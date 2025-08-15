import os
import cv2
import json
import tempfile
import subprocess
from typing import Dict, List, Optional, Tuple

import httpx

from Services.yolo_service import analyze_image_file   # your existing image analyzer (YOLO)
from Services.moderation_service import ModerationService

# --- NEW: BLIP imports ---
from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
import torch

# Load BLIP model once
device = "cuda" if torch.cuda.is_available() else "cpu"
blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-large")
blip_model = BlipForConditionalGeneration.from_pretrained(
    "Salesforce/blip-image-captioning-large"
).to(device)

def caption_frame(image_path: str) -> str:
    """Generate BLIP caption for a single frame."""
    image = Image.open(image_path).convert("RGB")
    inputs = blip_processor(image, return_tensors="pt").to(device)
    out = blip_model.generate(**inputs, max_new_tokens=50)
    return blip_processor.decode(out[0], skip_special_tokens=True)


# ---------- Low-level helpers ----------

def _has_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return True
    except Exception:
        return False

def extract_audio_to_wav(video_path: str) -> Optional[str]:
    if not _has_ffmpeg():
        print("⚠️ ffmpeg not found; cannot extract audio.")
        return None
    tmp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    tmp_wav.close()
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        tmp_wav.name
    ]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if proc.returncode != 0:
            os.unlink(tmp_wav.name)
            print(f"⚠️ ffmpeg audio extract failed: {proc.stderr[:500].decode(errors='ignore')}")
            return None
        return tmp_wav.name
    except Exception as e:
        print(f"⚠️ Audio extraction error: {e}")
        try: os.unlink(tmp_wav.name)
        except Exception: pass
        return None

def extract_subtitles_text(video_path: str) -> str:
    if not _has_ffmpeg():
        print("⚠️ ffmpeg not found; cannot extract subtitles.")
        return ""
    try:
        probe_cmd = [
            "ffprobe", "-v", "error", "-select_streams", "s",
            "-show_entries", "stream=index:stream_tags=language",
            "-of", "json", video_path
        ]
        probe = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if probe.returncode != 0:
            print("ℹ️ No subtitle streams (ffprobe failed).")
            return ""
        data = json.loads(probe.stdout.decode("utf-8", errors="ignore"))
        streams = data.get("streams", [])
        if not streams:
            return ""
        collected_texts: List[str] = []
        for s in streams:
            idx = s.get("index")
            tmp_srt = tempfile.NamedTemporaryFile(delete=False, suffix=".srt")
            tmp_srt.close()
            tried = False
            for map_arg in (f"0:s:{0}", f"0:s:{1}", f"0:s:{2}", f"0:s:{3}"):
                cmd = ["ffmpeg", "-y", "-i", video_path, "-map", map_arg, tmp_srt.name]
                p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
                if p.returncode == 0 and os.path.getsize(tmp_srt.name) > 0:
                    tried = True
                    break
            if not tried:
                abs_map = f"0:{idx}"
                cmd = ["ffmpeg", "-y", "-i", video_path, "-map", abs_map, tmp_srt.name]
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            try:
                with open(tmp_srt.name, "r", encoding="utf-8", errors="ignore") as f:
                    srt = f.read()
                if srt.strip():
                    lines = []
                    for line in srt.splitlines():
                        line = line.strip()
                        if not line or line.isdigit() or "-->" in line:
                            continue
                        lines.append(line)
                    if lines:
                        collected_texts.append("\n".join(lines))
            finally:
                try: os.unlink(tmp_srt.name)
                except Exception: pass
        return "\n".join(collected_texts).strip()
    except Exception as e:
        print(f"⚠️ Subtitle extraction error: {e}")
        return ""

async def transcribe_audio_with_groq(audio_path: str, api_key: Optional[str]) -> str:
    if not api_key or not os.path.exists(audio_path):
        return ""
    GROQ_AUDIO_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            with open(audio_path, "rb") as f:
                files = {"file": (os.path.basename(audio_path), f, "audio/wav")}
                data = {"model": "whisper-large-v3"}
                headers = {"Authorization": f"Bearer {api_key}"}
                resp = await client.post(GROQ_AUDIO_URL, data=data, files=files, headers=headers)
        if resp.status_code != 200:
            print(f"⚠️ Groq Whisper error {resp.status_code}: {resp.text[:500]}")
            return ""
        return resp.json().get("text", "").strip()
    except Exception as e:
        print(f"⚠️ Transcription error: {e}")
        return ""

def _aggregate_frame_results(results: List) -> Dict:
    aggregated = {"detected_labels": [], "frame_count_analyzed": len(results)}
    all_labels: List = []
    for r in results:
        if isinstance(r, list):
            all_labels.extend(r)
        elif isinstance(r, dict):
            if "detected_labels" in r and isinstance(r["detected_labels"], list):
                all_labels.extend(r["detected_labels"])
            else:
                all_labels.append(r)
        else:
            all_labels.append(r)
    seen = set()
    unique = []
    def _mk(v):
        """Make a detection result hashable (recursive)."""
        if isinstance(v, dict):
            return tuple(sorted((k, _mk(val)) for k, val in v.items()))
        elif isinstance(v, list):
            return tuple(_mk(item) for item in v)
        else:
            return v
    for v in all_labels:
        key = _mk(v)
        if key not in seen:
            seen.add(key)
            unique.append(v)
    aggregated["detected_labels"] = unique
    return aggregated

def _iterate_frames(video_path: str, interval_ms: int) -> List[str]:
    paths: List[str] = []
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("⚠️ Failed to open video for frame extraction.")
        return paths
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frame_interval = max(1, int((fps * interval_ms) / 1000))
        frame_count = 0
        while True:
            success, frame = cap.read()
            if not success:
                break
            if frame_count % frame_interval == 0:
                tmp_jpg = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                tmp_jpg.close()
                cv2.imwrite(tmp_jpg.name, frame)
                paths.append(tmp_jpg.name)
            frame_count += 1
    finally:
        cap.release()
    return paths


# ---------- Main entry ----------
async def analyze_video_full(
    video_path: str,
    db,
    user_id: Optional[int],
    model: str = "llama3-70b-8192",
    interval_ms: int = 200,
    language_hint: str = ""
) -> Dict:
    report: Dict = {
        "visual_analysis": {},
        "transcript": "",
        "subtitle_text": "",
        "text_moderation": {},
        "summary": {}
    }
    has_ffmpeg = _has_ffmpeg()

    # 1) Visual analysis with YOLO + BLIP
    frame_paths = _iterate_frames(video_path, interval_ms=interval_ms)
    frame_results: List = []
    captions: List[str] = []
    for p in frame_paths:
        try:
            frame_results.append(analyze_image_file(p))
            captions.append(caption_frame(p))
        except Exception as e:
            print(f"⚠️ Frame analyze/caption error ({p}): {e}")
        finally:
            try: os.unlink(p)
            except Exception: pass
    report["visual_analysis"] = _aggregate_frame_results(frame_results)
    report["visual_analysis"]["scene_description"] = " ".join(dict.fromkeys(captions))

    # 2) Subtitles
    subtitle_text = extract_subtitles_text(video_path) if has_ffmpeg else ""
    report["subtitle_text"] = subtitle_text

    # 3) Audio transcript
    transcript = ""
    if has_ffmpeg:
        GROQ_API_KEY = os.getenv("GROQ_API_KEY")
        audio_wav = extract_audio_to_wav(video_path)
        if audio_wav:
            try:
                transcript = await transcribe_audio_with_groq(audio_wav, GROQ_API_KEY)
            finally:
                try: os.unlink(audio_wav)
                except Exception: pass
    report["transcript"] = transcript

    # 4) Text moderation
    combined_text = "\n".join([t for t in [subtitle_text, transcript] if t]).strip()
    if combined_text:
        lang = language_hint if language_hint else "auto"
        moderation = await ModerationService.check_content_comprehensive(
            text=combined_text,
            model=model,
            db=db,
            user_id=user_id,
            language=lang,
            entry_type="video"
        )
    else:
        moderation = {
            "status": "conforme",
            "bert": {"label": "safe", "confidence": 0.0},
            "groq": {"status": "conforme", "category": "aucun", "reasoning": "No speech/subtitles detected", "is_insult": False},
            "message": "No text content detected in audio/subtitles.",
            "processed_text": "",
            "violated_rules": [],
            "conflict_detected": False
        }
    report["text_moderation"] = moderation

    # 5) Summary
    toxic = (moderation.get("status") == "non_conforme")
    report["summary"] = {
        "toxic": toxic,
        "non_conformant_category": (moderation.get("groq", {}) or {}).get("category"),
        "frames_analyzed": report["visual_analysis"].get("frame_count_analyzed", 0),
        "labels_detected_count": len(report["visual_analysis"].get("detected_labels", []))
    }

    return report
