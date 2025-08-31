import os
import cv2
import json
import tempfile
import subprocess
from typing import Dict, List, Optional, Tuple

import httpx

from Services.yolo_service import analyze_image_file   # your existing image analyzer (YOLO)
from Services.moderation_service import ModerationService

# --- BLIP imports ---
from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
import torch
from datetime import timedelta

# Load BLIP model once
device = "cuda" if torch.cuda.is_available() else "cpu"
blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-large")
blip_model = BlipForConditionalGeneration.from_pretrained(
    "Salesforce/blip-image-captioning-large"
).to(device)

def _format_timestamp(seconds: float) -> str:
    return str(timedelta(seconds=int(seconds)))

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
        return None
    tmp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    tmp_wav.close()
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        tmp_wav.name
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode != 0:
        os.unlink(tmp_wav.name)
        return None
    return tmp_wav.name

def extract_subtitles_with_intervals(video_path: str) -> List[Dict]:
    """Extract subtitles with time intervals and text."""
    subs = []
    if not _has_ffmpeg():
        return subs
    try:
        tmp_srt = tempfile.NamedTemporaryFile(delete=False, suffix=".srt")
        tmp_srt.close()
        cmd = ["ffmpeg", "-y", "-i", video_path, tmp_srt.name]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        with open(tmp_srt.name, "r", encoding="utf-8", errors="ignore") as f:
            blocks = f.read().split("\n\n")
        for block in blocks:
            lines = block.strip().splitlines()
            if len(lines) >= 3:
                timing = lines[1]
                try:
                    start, end = [t.strip() for t in timing.split("-->")]
                except Exception:
                    continue
                text = " ".join(lines[2:]).strip()
                if text:
                    subs.append({"start": start, "end": end, "text": text})
        os.unlink(tmp_srt.name)
    except Exception:
        return []
    return subs

async def transcribe_audio_chunks(video_path: str, api_key: Optional[str], chunk_sec: int = 30) -> List[Dict]:
    """Split audio into chunks, transcribe each, return list with timestamps."""
    if not _has_ffmpeg() or not api_key:
        return []
    audio_wav = extract_audio_to_wav(video_path)
    if not audio_wav:
        return []
    tmp_dir = tempfile.mkdtemp()
    cmd = [
        "ffmpeg", "-i", audio_wav, "-f", "segment",
        "-segment_time", str(chunk_sec),
        "-c", "copy", os.path.join(tmp_dir, "chunk_%03d.wav")
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    os.unlink(audio_wav)

    chunks = sorted([f for f in os.listdir(tmp_dir) if f.startswith("chunk_")])
    results = []
    for idx, fname in enumerate(chunks):
        path = os.path.join(tmp_dir, fname)
        start = idx * chunk_sec
        end = (idx + 1) * chunk_sec
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                with open(path, "rb") as f:
                    files = {"file": (fname, f, "audio/wav")}
                    data = {"model": "whisper-large-v3"}
                    headers = {"Authorization": f"Bearer {api_key}"}
                    resp = await client.post(
                        "https://api.groq.com/openai/v1/audio/transcriptions",
                        data=data, files=files, headers=headers
                    )
            if resp.status_code == 200:
                text = resp.json().get("text", "").strip()
                if text:
                    results.append({
                        "start": _format_timestamp(start),
                        "end": _format_timestamp(end),
                        "text": text
                    })
        except Exception as e:
            print(f"⚠️ Chunk transcription failed: {e}")
        finally:
            try: os.remove(path)
            except Exception: pass
    return results

def _iterate_frames(video_path: str, interval_ms: int) -> List[Tuple[str, float]]:
    frames: List[Tuple[str, float]] = []
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return frames
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
            timestamp = frame_count / fps
            frames.append((tmp_jpg.name, timestamp))
        frame_count += 1
    cap.release()
    return frames

# ---------- Main entry ----------
async def analyze_video_full(
    video_path: str,
    db,
    user_id: Optional[int],
    model: str = "llama3-8b-8192",
    interval_ms: int = 200,
    language_hint: str = ""
) -> Dict:
    report: Dict = {
        "visual_analysis": {},
        "subtitles": [],
        "transcript_segments": [],
        "text_moderation": {},
        "summary": {}
    }
    has_ffmpeg = _has_ffmpeg()
    violations: List[Dict] = []

    # 1) Visual analysis with YOLO + BLIP
    frame_paths = _iterate_frames(video_path, interval_ms=interval_ms)
    frame_results: List[Dict] = []
    for p, ts in frame_paths:
        try:
            detections = analyze_image_file(p)
            caption = caption_frame(p)
            frame_result = {
                "timestamp": _format_timestamp(ts),
                "detections": detections,
                "caption": caption
            }
            frame_results.append(frame_result)
            # optional moderation on captions
            moderation = await ModerationService.check_content_comprehensive(
                text=caption, model=model, db=db,
                user_id=user_id, language=language_hint or "auto",
                entry_type="video"
            )
            if moderation.get("status") == "non_conforme":
                violations.append({
                    "type": "frame",
                    "timestamp": _format_timestamp(ts),
                    "text": caption,
                    "violated_rules": moderation.get("violated_rules", [])
                })
        except Exception as e:
            print(f"⚠️ Frame analyze error: {e}")
        finally:
            try: os.unlink(p)
            except Exception: pass
    report["visual_analysis"] = frame_results

    # 2) Subtitles
    subs = extract_subtitles_with_intervals(video_path) if has_ffmpeg else []
    report["subtitles"] = subs
    for sub in subs:
        moderation = await ModerationService.check_content_comprehensive(
            text=sub["text"], model=model, db=db,
            user_id=user_id, language=language_hint or "auto",
            entry_type="video"
        )
        if moderation.get("status") == "non_conforme":
            violations.append({
                "type": "subtitle",
                "start": sub["start"],
                "end": sub["end"],
                "text": sub["text"],
                "violated_rules": moderation.get("violated_rules", [])
            })

    # 3) Audio transcript (segmented)
    transcript_segments = []
    if has_ffmpeg:
        GROQ_API_KEY = os.getenv("GROQ_API_KEY")
        transcript_segments = await transcribe_audio_chunks(video_path, GROQ_API_KEY)
    report["transcript_segments"] = transcript_segments
    for seg in transcript_segments:
        moderation = await ModerationService.check_content_comprehensive(
            text=seg["text"], model=model, db=db,
            user_id=user_id, language=language_hint or "auto",
            entry_type="video"
        )
        if moderation.get("status") == "non_conforme":
            violations.append({
                "type": "transcript",
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"],
                "violated_rules": moderation.get("violated_rules", [])
            })

    # 4) Global summary
    toxic = any(v for v in violations)
    report["text_moderation"] = {
        "status": "non_conforme" if toxic else "conforme",
        "violations": violations
    }
    report["summary"] = {
        "toxic": toxic,
        "frames_analyzed": len(frame_results),
        "subtitle_blocks": len(subs),
        "transcript_chunks": len(transcript_segments),
        "violations_count": len(violations)
    }

    return report
