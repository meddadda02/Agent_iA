import os
import tempfile
import struct
import hmac
import hashlib
import base64
import time
import re
import numpy as np
import librosa
import requests
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from collections import Counter
from scipy.signal import find_peaks
from Shemas.moderation_schemas import ContentCheckResponse

class ACRCloudService:
    def __init__(self):
        self.access_key = os.getenv("ACRCLOUD_ACCESS_KEY")
        self.access_secret = os.getenv("ACRCLOUD_ACCESS_SECRET")
        self.host = os.getenv("ACRCLOUD_HOST", "identify-eu-west-1.acrcloud.com")
        
        self.acrcloud_enabled = bool(self.access_key and self.access_secret)
        
        if not self.access_key or not self.access_secret:
            print("⚠️ ACRCloud désactivé - clés API manquantes")
            print(f" ACCESS_KEY présent: {bool(self.access_key)}")
            print(f" ACCESS_SECRET présent: {bool(self.access_secret)}")
        else:
            print("✅ ACRCloud activé - connexion API disponible")
            print(f" Host: {self.host}")
        
        self.copyright_thresholds = {
            "high_confidence": 0.85,
            "medium_confidence": 0.70,
            "low_confidence": 0.50
        }
        
        self.royalty_free_keywords = {
            "royalty free", "royalty-free", "copyright free", "creative commons",
            "public domain", "no copyright", "free music", "libre de droits",
            "sans copyright", "domaine public", "cc0", "creative commons zero",
            "freesound", "zapsplat", "epidemic sound", "artlist", "musicbed",
            "audio jungle", "pond5", "shutterstock music", "getty images music",
            "youtube audio library", "facebook sound collection", "free music archive",
            "incompetech", "kevin macleod", "bensound", "audionautix"
        }
        
        # Music-related keywords for enhanced detection
        self.music_keywords = {
            'music', 'song', 'tune', 'melody', 'track', 'album', 'single', 'hit',
            'chorus', 'verse', 'bridge', 'refrain', 'hook', 'beat', 'rhythm',
            'instrumental', 'acoustic', 'electric', 'guitar', 'piano', 'drums',
            'bass', 'violin', 'saxophone', 'trumpet', 'flute', 'cello', 'harp',
            'orchestra', 'band', 'group', 'artist', 'singer', 'vocalist', 'rapper',
            'dj', 'producer', 'composer', 'lyricist', 'arranger', 'performer'
        }
        
        self.public_domain_indicators = {
            "classical", "baroque", "mozart", "beethoven", "bach", "chopin",
            "vivaldi", "handel", "haydn", "schubert", "brahms", "tchaikovsky",
            "debussy", "liszt", "wagner", "verdi", "puccini", "rossini",
            "folk", "traditional", "hymn", "spiritual", "gregorian"
        }

    def _get_file_size(self, file_path: str) -> int:
        """Get file size in bytes."""
        try:
            return os.path.getsize(file_path)
        except Exception:
            return 0

    def _estimate_duration_from_size(self, file_path: str) -> float:
        """Estimate audio duration from file size."""
        try:
            file_size = self._get_file_size(file_path)
            if file_size == 0:
                return 0.0
            
            # Rough estimation: assume 128kbps average bitrate
            estimated_duration = file_size / 16000
            estimated_duration = max(1.0, min(estimated_duration, 3600.0))
            
            print(f" Durée estimée: {estimated_duration:.2f}s ({file_size} bytes)")
            return estimated_duration
            
        except Exception:
            return 0.0

    def _get_audio_duration(self, file_path: str) -> float:
        """Return accurate audio duration when possible, fallback to rough estimate."""
        try:
            # Prefer librosa for accurate duration
            dur = librosa.get_duration(path=file_path)
            if dur and dur > 0:
                return float(dur)
        except Exception:
            pass
        # Fallback
        return self._estimate_duration_from_size(file_path)

    def _detect_refrain(self, text: str, audio_path: str) -> Dict[str, Any]:
        """
        Detect refrains in the audio by analyzing both text and audio patterns.
        
        Args:
            text: Transcribed text from the audio
            audio_path: Path to the audio file
            
        Returns:
            Dict with refrain detection results
        """
        result = {
            "refrain_detected": False,
            "refrain_confidence": 0.0,
            "refrain_patterns": []
        }
        
        try:
            # 1. Text-based refrain detection
            if text and len(text.strip()) > 0:
                # Split into lines and clean them
                lines = [line.strip().lower() for line in text.split('\n') if line.strip()]
                
                # Find repeated lines (potential refrains)
                line_counter = Counter(lines)
                repeated_lines = [(line, count) for line, count in line_counter.items() 
                                if count > 1 and len(line.split()) > 2]  # At least 3 words to be meaningful
                
                if repeated_lines:
                    # Calculate confidence based on repetition count and line length
                    total_confidence = 0
                    for line, count in repeated_lines:
                        # More weight to longer lines that repeat more
                        line_confidence = min(0.9, 0.2 + (count * 0.1) + (len(line.split()) * 0.02))
                        total_confidence += line_confidence
                        
                        result["refrain_patterns"].append({
                            "text": line,
                            "occurrences": count,
                            "confidence": min(0.95, line_confidence)
                        })
                    
                    # Average confidence across all patterns
                    if result["refrain_patterns"]:
                        result["refrain_confidence"] = total_confidence / len(result["refrain_patterns"])
                        result["refrain_detected"] = result["refrain_confidence"] > 0.4
            
            # 2. Audio-based refrain detection (if libsndfile is available)
            try:
                # Load audio file
                y, sr = librosa.load(audio_path, sr=None)
                
                # Extract chroma features (musical notes)
                chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
                
                # Calculate similarity matrix
                similarity = librosa.segment.cross_similarity(chroma, chroma, mode='affinity')
                
                # Find repeating segments
                segments = librosa.segment.recurrence_to_lag(similarity)
                
                if len(segments) > 1:
                    # If we find repeating segments, increase confidence
                    audio_confidence = min(0.7, len(segments) * 0.1)
                    result["refrain_confidence"] = max(result["refrain_confidence"], audio_confidence)
                    
                    # If we have audio evidence but no text patterns, add a generic pattern
                    if not result["refrain_patterns"] and audio_confidence > 0.5:
                        result["refrain_patterns"].append({
                            "text": "[Repeating musical pattern detected]",
                            "occurrences": len(segments),
                            "confidence": audio_confidence
                        })
                
                # Update detection based on combined evidence
                result["refrain_detected"] = result["refrain_confidence"] > 0.4
                
            except Exception as audio_error:
                print(f" Audio analysis error (non-fatal): {audio_error}")
                
        except Exception as e:
            print(f" Error in refrain detection: {e}")
            
        return result

    def _detect_autotune(self, audio_path: str) -> Dict[str, Any]:
        """
        Detect autotune usage in audio by analyzing pitch characteristics.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Dict with autotune detection results
        """
        result = {
            "autotune_detected": False,
            "autotune_confidence": 0.0,
            "autotune_artifacts": []
        }
        
        try:
            # Load audio file
            y, sr = librosa.load(audio_path, sr=None)
            
            # Extract pitch using PYIN algorithm
            f0, voiced_flag, voiced_probs = librosa.pyin(y, fmin=librosa.note_to_hz('C2'), 
                                                       fmax=librosa.note_to_hz('C7'))
            
            # Get only voiced segments
            voiced_f0 = f0[voiced_flag]
            
            if len(voiced_f0) < 10:  # Not enough voiced segments
                return result
                
            # Convert to MIDI notes for quantization analysis
            midi_notes = librosa.hz_to_midi(voiced_f0[~np.isnan(voiced_f0)])
            
            # Check for quantization to semitones (characteristic of autotune)
            rounded_notes = np.round(midi_notes)
            note_diffs = np.abs(midi_notes - rounded_notes)
            
            # Autotune typically has very small deviations from semitones
            in_tune = note_diffs < 0.1  # Very close to semitone
            in_tune_ratio = np.mean(in_tune)
            
            # Check for unnatural pitch transitions (sudden jumps to exact semitones)
            if len(voiced_f0) > 10:
                pitch_changes = np.diff(voiced_f0)
                semitone_ratio = 2 ** (1/12)  # Ratio between semitones
                
                # Look for exact semitone jumps (common in heavy autotune)
                semitone_jumps = []
                for i in range(1, len(voiced_f0)):
                    if voiced_f0[i] > 0 and voiced_f0[i-1] > 0:  # Only compare valid pitches
                        ratio = voiced_f0[i] / voiced_f0[i-1]
                        # Check if ratio is close to a semitone interval
                        semitone_diff = round(np.log2(ratio) * 12)
                        expected_ratio = 2 ** (semitone_diff / 12)
                        if abs(ratio - expected_ratio) < 0.01:  # Very close to exact semitone
                            semitone_jumps.append(semitone_diff)
                
                if semitone_jumps:
                    jump_counter = Counter(semitone_jumps)
                    most_common_jump, count = jump_counter.most_common(1)[0]
                    jump_confidence = min(0.7, count / len(semitone_jumps) * 2)
                    
                    result["autotune_artifacts"].append({
                        "type": "exact_semitone_jumps",
                        "count": count,
                        "most_common_jump": most_common_jump,
                        "confidence": jump_confidence
                    })
                    
                    result["autotune_confidence"] = max(result["autotune_confidence"], jump_confidence)
            
            # High ratio of notes exactly on semitones suggests autotune
            if in_tune_ratio > 0.8:
                result["autotune_artifacts"].append({
                    "type": "high_semitone_alignment",
                    "ratio": float(in_tune_ratio),
                    "confidence": min(0.9, (in_tune_ratio - 0.7) * 3)  # Scale 0.7-1.0 to 0.0-0.9
                })
                result["autotune_confidence"] = max(result["autotune_confidence"], 
                                                  min(0.9, (in_tune_ratio - 0.7) * 3))
            
            # Final detection decision
            result["autotune_detected"] = result["autotune_confidence"] > 0.5
            
        except Exception as e:
            print(f" Error in autotune detection: {e}")
            
        return result

    def _analyze_audio_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze audio file metadata using native Python.
        
        Args:
            file_path: Chemin vers le fichier audio
            
        Returns:
            Dict: Dictionnaire contenant les métadonnées audio
        """
        metadata = {
            "title": None,
            "artist": None,
            "album": None,
            "has_metadata": False
        }
        
        try:
            import librosa
            import numpy as np
            from scipy import signal
            import soundfile as sf
            
            # Analyse des métadonnées avec librosa et soundfile
            with sf.SoundFile(file_path) as audio_file:
                metadata.update({
                    "sample_rate": audio_file.samplerate,
                    "channels": audio_file.channels,
                    "duration": float(audio_file.frames) / audio_file.samplerate,
                    "format": audio_file.format,
                    "subtype": audio_file.subtype
                })
                
                # Essayer d'extraire des métadonnées supplémentaires si disponibles
                if hasattr(audio_file, 'extra_info'):
                    metadata.update({
                        "title": getattr(audio_file, 'title', None),
                        "artist": getattr(audio_file, 'artist', None),
                        "album": getattr(audio_file, 'album', None),
                        "has_metadata": True
                    })
            
        except ImportError as e:
            print(f" Erreur d'importation des bibliothèques audio: {e}")
        except Exception as e:
            print(f" Erreur lors de l'analyse des métadonnées audio: {e}")
            
        return metadata
        
    async def _analyze_audio_content(self, file_path: str, transcription: str = None) -> Dict[str, Any]:
        """
        Analyse le contenu audio pour détecter la présence de musique et de copyright.
        
        Args:
            file_path: Chemin vers le fichier audio
            transcription: Transcription texte optionnelle pour analyse complémentaire
            
        Returns:
            Dict avec les résultats de l'analyse audio
        """
        print("🔍 Analyse avancée du contenu audio pour détection de musique...")
        
        # Initialize result with default values
        result = ContentCheckResponse(
            status="success",
            music_detected=False,
            title=None,
            artist=None,
            album=None,
            release_date=None,
            label=None,
            copyright_protected=False,
            platforms={},
            confidence_score=0.0,
            strike_risk_level="low",
            recommendation="Aucune musique détectée",
            is_public_domain=False,
            whitelist_match=False,
            audio_analysis={
                "music_detected": False,
                "music_confidence": 0.0,
                "is_copyrighted": False,
                "copyright_status": "not_applicable",
                "copyright_confidence": 0.0,
                "detected_genres": [],
                "is_public_domain": False,
                "audio_segments": [],
                "has_voice_with_music": False,
                "music_segments": []
            }
        ).dict()
        
        # Analyze metadata
        metadata = self._analyze_audio_metadata(file_path)
        
        # Run refrain and autotune detection if we have transcription or audio
        try:
            if transcription and len(transcription.strip()) > 10:
                print(" Exécution de la détection de refrain...")
                refrain_result = self._detect_refrain(transcription, file_path)
                
                # Update result with refrain detection
                if "audio_analysis" not in result:
                    result["audio_analysis"] = {}
                result["audio_analysis"].update({
                    "refrain_detected": refrain_result["refrain_detected"],
                    "refrain_confidence": refrain_result["refrain_confidence"],
                    "refrain_patterns": refrain_result["refrain_patterns"]
                })
                
                # If refrain is detected with high confidence, update music detection
                if refrain_result["refrain_detected"] and refrain_result["refrain_confidence"] > 0.6:
                    result.update({
                        "music_detected": True,
                        "confidence_score": max(result.get("confidence_score", 0), refrain_result["refrain_confidence"] * 0.8),
                        "recommendation": "Refrain détecté - contenu musical probable"
                    })
            
            # Always try to detect autotune from audio
            print(" Analyse de l'utilisation d'autotune...")
            autotune_result = self._detect_autotune(file_path)
            
            # Update result with autotune detection
            if "audio_analysis" not in result:
                result["audio_analysis"] = {}
            result["audio_analysis"].update({
                "autotune_detected": autotune_result["autotune_detected"],
                "autotune_confidence": autotune_result["autotune_confidence"],
                "autotune_artifacts": autotune_result["autotune_artifacts"]
            })
            
            # If autotune is detected, increase confidence in music detection
            if autotune_result["autotune_detected"]:
                result.update({
                    "music_detected": True,
                    "confidence_score": max(result.get("confidence_score", 0), autotune_result["autotune_confidence"] * 0.9),
                    "recommendation": "Autotune détecté - contenu musical probable"
                })
                
        except Exception as e:
            print(f" Erreur lors de l'analyse audio avancée: {e}")
        
        # Check for common song patterns in transcription
        if transcription and len(transcription.strip()) > 10:
            print(f" Analyse de la transcription: {len(transcription)} caractères")
            
            # Convert to lowercase for case-insensitive matching
            transcription_lower = transcription.lower()
            
            # Check for music-related keywords
            found_keywords = [kw for kw in self.music_keywords if kw in transcription_lower]
            
            # If we find music-related keywords, increase confidence
            if found_keywords:
                keyword_confidence = min(0.7, len(found_keywords) * 0.1)  # Up to 0.7 confidence
                print(f" Mots-clés musicaux détectés: {', '.join(found_keywords)}")
                
                # Update result with keyword detection
                if "audio_analysis" not in result:
                    result["audio_analysis"] = {}
                if "detected_keywords" not in result["audio_analysis"]:
                    result["audio_analysis"]["detected_keywords"] = []
                
                result["audio_analysis"]["detected_keywords"].extend(found_keywords)
                
                # Update music detection if we found significant keywords
                if keyword_confidence > 0.3:
                    result.update({
                        "music_detected": True,
                        "confidence_score": max(result.get("confidence_score", 0), keyword_confidence),
                        "recommendation": f"Termes musicaux détectés: {', '.join(found_keywords[:3])}..."
                    })
            
            # Look for repetitive patterns (common in songs)
            words = transcription_lower.split()
            if len(words) > 5:
                word_freq = {}
                for word in words:
                    word_freq[word] = word_freq.get(word, 0) + 1
                
                # Check for high repetition (indicates song structure)
                max_repetition = max(word_freq.values()) if word_freq else 0
                repetition_ratio = max_repetition / len(words) if words else 0
                
                if repetition_ratio > 0.3:  # 30% repetition suggests song structure
                    print(f" Structure musicale détectée (répétition: {repetition_ratio:.1%})")
                    
                    result.update({
                        "music_detected": True,
                        "title": "Contenu musical détecté",
                        "artist": "Inconnu",
                        "copyright_protected": True,
                        "confidence_score": max(result.get("confidence_score", 0), 0.75),
                        "strike_risk_level": "medium",
                        "recommendation": "Structure musicale détectée dans la transcription - vérification manuelle recommandée"
                    })
        
        # Check filename as fallback if we still don't have music detection
        if not result.get("music_detected"):
            filename_result = await self.analyze_filename_for_copyright(file_path)
            
            # If metadata suggests music but filename analysis says safe, be cautious
            if metadata["has_metadata"] and not filename_result.get("copyright_protected"):
                print(" Métadonnées musicales détectées - analyse prudente")
                filename_result.update({
                    "music_detected": True,
                    "confidence_score": 0.6,
                    "recommendation": "Métadonnées musicales détectées - vérification recommandée"
                })
            
            # Merge filename result with our analysis
            result.update({
                k: v for k, v in filename_result.items() 
                if k not in ["audio_analysis"]  # Preserve our audio analysis
            })
        
        return result

    async def handle_transcription_error(self, message: str = "Analyse audio non disponible") -> Dict[str, Any]:
        """Handle detection errors gracefully."""
        print(f" {message}")
        return ContentCheckResponse(
            status="success",  # Return success instead of error
            music_detected=False,
            title=None,
            artist=None,
            album=None,
            release_date=None,
            label=None,
            copyright_protected=False,
            platforms={},
            confidence_score=0.0,
            strike_risk_level="low",
            recommendation="Analyse basée sur le contenu textuel uniquement",
            is_public_domain=False,
            whitelist_match=False
        ).dict()

    async def analyze_filename_for_copyright(self, file_path: str) -> Dict[str, Any]:
        """Analyze filename and metadata for copyright indicators."""
        filename = os.path.basename(file_path).lower()
        
        for keyword in self.royalty_free_keywords:
            if keyword in filename:
                print(f" Fichier royalty-free détecté: {keyword}")
                return ContentCheckResponse(
                    status="success",
                    music_detected=True,
                    title=os.path.splitext(os.path.basename(file_path))[0],
                    artist="Inconnu",
                    album=None,
                    release_date=None,
                    label="Royalty-Free",
                    copyright_protected=False,
                    platforms={},
                    confidence_score=0.9,
                    strike_risk_level="low",
                    recommendation="Musique libre de droits détectée",
                    is_public_domain=False,
                    whitelist_match=True
                ).dict()
        
        for indicator in self.public_domain_indicators:
            if indicator in filename:
                print(f" Musique domaine public détectée: {indicator}")
                return ContentCheckResponse(
                    status="success",
                    music_detected=True,
                    title=os.path.splitext(os.path.basename(file_path))[0],
                    artist="Domaine Public",
                    album=None,
                    release_date=None,
                    label="Public Domain",
                    copyright_protected=False,
                    platforms={},
                    confidence_score=0.8,
                    strike_risk_level="low",
                    recommendation="Musique du domaine public",
                    is_public_domain=True,
                    whitelist_match=False
                ).dict()
        
        return ContentCheckResponse(
            status="success",
            music_detected=False,
            title=None,
            artist=None,
            album=None,
            release_date=None,
            label=None,
            copyright_protected=False,
            platforms={},
            confidence_score=0.0,
            strike_risk_level="low",
            recommendation="Aucun indicateur de copyright détecté",
            is_public_domain=False,
            whitelist_match=False
        ).dict()

    async def _send_to_acrcloud(self, audio_data: bytes, sample_rate: int = 8000) -> Dict[str, Any]:
        """Send audio data to ACRCloud API."""
        if not self.acrcloud_enabled:
            print(" ACRCloud désactivé - clés API manquantes")
            return {"status": {"msg": "ACRCloud disabled - missing API keys", "code": -1}}
        
        try:
            timestamp = str(int(time.time()))
            http_method = "POST"
            http_uri = "/v1/identify"
            data_type = "audio"
            signature_version = "1"
            
            string_to_sign = f"{http_method}\n{http_uri}\n{self.access_key}\n{data_type}\n{signature_version}\n{timestamp}"
            print(f" String to sign: {string_to_sign}")
            
            # Calculate signature
            sign = hmac.new(
                self.access_secret.encode('utf-8'),
                string_to_sign.encode('utf-8'),
                hashlib.sha1
            ).digest()
            signature = base64.b64encode(sign).decode('utf-8')
            
            # Prepare form data
            files = [
                ('sample', ('sample', audio_data, 'audio/wav'))
            ]
            
            data = {
                'access_key': self.access_key,
                'data_type': data_type,
                'signature_version': signature_version,
                'signature': signature,
                'sample_bytes': str(len(audio_data)),
                'timestamp': timestamp
            }
            
            url = f"https://{self.host}{http_uri}"
            print(f" Envoi à ACRCloud: {len(audio_data)} bytes vers {url}")
            print(f" Access key: {self.access_key[:10]}...")
            print(f" Signature: {signature[:20]}...")
            print(f" Timestamp: {timestamp}")
            
            # Send request with proper headers and timeout
            headers = {
                'accept': 'application/json',
            }
            
            response = requests.post(
                url,
                files=files,
                data=data,
                headers=headers,
                timeout=30
            )
            
            print(f" Status code: {response.status_code}")
            print(f" Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f" Réponse ACRCloud complète: {result}")
                    return result
                except Exception as json_err:
                    print(f" Erreur décodage JSON: {json_err}")
                    return {"status": {"msg": f"Invalid JSON response: {response.text}", "code": -2}}
            else:
                error_msg = response.text
                print(f" Erreur HTTP ACRCloud: {response.status_code}")
                print(f" Réponse complète: {error_msg}")
                return {"status": {"msg": f"HTTP {response.status_code}: {error_msg}", "code": response.status_code}}
                
        except requests.exceptions.RequestException as re:
            print(f" Erreur de requête ACRCloud: {str(re)}")
            return {"status": {"msg": f"Request error: {str(re)}", "code": -3}}
            
        except Exception as e:
            print(f" Erreur inattendue ACRCloud: {type(e).__name__}: {str(e)}")
            import traceback
            print(f" Traceback: {traceback.format_exc()}")
            return {"status": {"msg": f"Unexpected error: {str(e)}", "code": -1}}

    async def _identify_by_chunks(self, audio_path: str, duration: float, transcription: Optional[str]) -> Optional[Dict[str, Any]]:
        """Try ACRCloud on multiple 20s chunks to support large files.

        Returns a ContentCheckResponse-like dict on success, or None if no match.
        """
        try:
            import soundfile as sf
            import numpy as np
        except Exception as e:
            print(f" Chunked identify not available (soundfile import failed): {e}")
            return None

        if duration <= 0:
            duration = self._estimate_duration_from_size(audio_path)

        chunk_sec = 20.0
        hop_sec = 15.0  # overlap 5s
        max_scan = min(duration, 300.0)  # scan up to first 5 minutes to keep cost bounded

        try:
            info = sf.info(audio_path)
            sr = info.samplerate
            total_frames = info.frames
        except Exception as e:
            print(f" Cannot read audio info for chunking: {e}")
            return None

        def sec_to_frame(sec: float) -> int:
            return int(max(0, min(sec, duration)) * sr)

        start = 0.0
        while start < max_scan:
            end = min(start + chunk_sec, duration)
            start_frame = sec_to_frame(start)
            frames = sec_to_frame(end) - start_frame
            if frames <= 0:
                break

            try:
                y, _ = sf.read(audio_path, start=start_frame, frames=frames, dtype='float32', always_2d=False)
                # Write temp WAV chunk
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
                    chunk_path = tf.name
                try:
                    sf.write(chunk_path, y, sr)
                    audio_data = self._prepare_audio_data(chunk_path)
                    if not audio_data:
                        raise RuntimeError("chunk audio prep failed")
                    acr_res = await self._send_to_acrcloud(audio_data)
                    status = acr_res.get("status", {})
                    if status.get("code") == 0:
                        metadata = acr_res.get("metadata", {})
                        music_list = metadata.get("music", [])
                        if music_list:
                            music = music_list[0]
                            score = music.get("score", 0)
                            artists = music.get("artists", [])
                            artist_name = artists[0].get("name") if artists else "Artiste inconnu"
                            album_info = music.get("album", {})
                            album_name = album_info.get("name") if album_info else None
                            genres = [g["name"] for g in music.get("genres", []) if "name" in g]
                            is_public_domain = any(g.lower() in self.public_domain_indicators for g in genres)

                            resp = ContentCheckResponse(
                                status="success",
                                music_detected=True,
                                title=music.get("title"),
                                artist=artist_name,
                                album=album_name,
                                release_date=music.get("release_date"),
                                label=music.get("label"),
                                copyright_protected=True,
                                platforms={"acrcloud": {"score": score, "match": True}},
                                confidence_score=score / 100.0,
                                strike_risk_level=self._calculate_risk_level(score, is_public_domain),
                                recommendation=self._generate_recommendation(music, score, is_public_domain),
                                is_public_domain=is_public_domain,
                                whitelist_match=any(k in (music.get("title", "").lower()) for k in self.royalty_free_keywords),
                                audio_analysis={
                                    "music_detected": True,
                                    "music_confidence": score / 100.0,
                                    "is_copyrighted": True,
                                    "copyright_status": "copyrighted",
                                    "copyright_confidence": score / 100.0,
                                    "detected_genres": genres,
                                    "is_public_domain": is_public_domain,
                                },
                            ).dict()

                            # Adjust global offset
                            try:
                                local_offset = music.get("play_offset_ms") or 0
                                global_offset_ms = int(start * 1000) + int(local_offset)
                                resp["play_offset_ms"] = global_offset_ms
                            except Exception:
                                pass
                            try:
                                resp["duration_ms"] = int(duration * 1000)
                            except Exception:
                                pass
                            return resp
                finally:
                    try:
                        os.remove(chunk_path)
                    except Exception:
                        pass
            except Exception as e:
                print(f" Chunk {start:.1f}-{end:.1f}s failed: {e}")

            start += hop_sec

        return None

    def _prepare_audio_data(self, file_path: str) -> Optional[bytes]:
        """
        Prépare les données audio pour ACRCloud avec une meilleure gestion des formats.
        
        Args:
            file_path: Chemin vers le fichier audio à analyser
            
        Returns:
            bytes: Données audio brutes ou None en cas d'échec
        """
        try:
            # Vérifier l'existence du fichier
            if not os.path.exists(file_path):
                print(f"[ERROR] Fichier introuvable: {file_path}")
                return None
                
            file_size = os.path.getsize(file_path)
            print(f"[AUDIO] Préparation du fichier audio: {os.path.basename(file_path)} ({file_size/1024:.1f} KB)")
            
            # Vérifier la taille minimale du fichier (au moins 1 seconde d'audio)
            min_file_size = 16000  # ~1s à 16kHz, 8 bits
            if file_size < min_file_size:
                print(f"[WARN] Fichier trop petit: {file_size} bytes (minimum recommandé: {min_file_size} bytes)")
                return None
            
            # Lire le fichier en entier (jusqu'à 10MB pour éviter la surcharge mémoire)
            max_file_size = 10 * 1024 * 1024  # 10MB
            read_size = min(file_size, max_file_size)
            
            with open(file_path, 'rb') as f:
                # Lire l'en-tête pour vérifier le format
                header = f.read(4)
                f.seek(0)  # Revenir au début du fichier
                
                # Vérifier les formats audio courants
                if header.startswith(b'RIFF') or header.startswith(b'ID3') or header.startswith(b'OggS') or header.startswith(b'fLaC'):
                    print(f"[AUDIO] Format audio détecté: {'WAV' if header.startswith(b'RIFF') else 'MP3' if header.startswith(b'ID3') else 'OGG' if header.startswith(b'OggS') else 'FLAC'}")
                    audio_data = f.read(read_size)
                else:
                    # Essayer de lire quand même le fichier
                    print("[WARN] Format audio non reconnu, tentative de lecture quand même")
                    audio_data = f.read(read_size)
            
            print(f"[AUDIO] Données audio lues: {len(audio_data)/1024:.1f} KB")
            
            # Vérifier que les données audio sont suffisantes
            if len(audio_data) < min_file_size:
                print(f"[ERROR] Données audio insuffisantes: {len(audio_data)} bytes (minimum: {min_file_size} bytes)")
                return None
                
            return audio_data
                
        except Exception as e:
            import traceback
            print(f"[ERROR] Erreur lors de la préparation audio: {type(e).__name__}")
            print(f"[DEBUG] Détails: {str(e)}")
            print(f"[DEBUG] Stack trace: {traceback.format_exc()}")
            return None

    def _calculate_risk_level(self, score: float, is_public_domain: bool = False) -> str:
        """
        Calcule le niveau de risque en fonction du score de confiance.
        
        Args:
            score: Score de confiance (0-100)
            is_public_domain: Si le contenu est dans le domaine public
            
        Returns:
            Niveau de risque: 'none', 'low', 'medium', 'high', 'critical'
        """
        if is_public_domain:
            return "none"
        
        if score >= 90:
            return "critical"
        elif score >= 75:
            return "high"
        elif score >= 50:
            return "medium"
        elif score >= 30:
            return "low"
        return "none"

    def _generate_recommendation(self, music_data: Dict, score: float, is_public_domain: bool) -> str:
        """Génère une recommandation basée sur les résultats de détection."""
        title = music_data.get("title", "Musique inconnue")
        artist = music_data.get("artists", [{}])[0].get("name", "Artiste inconnu")
        
        if is_public_domain:
            return f"Musique du domaine public détectée: {title} par {artist}"
            
        if score >= 90:
            return f"Musique protégée détectée avec une forte confiance: {title} par {artist} (Score: {score}%)"
        elif score >= 70:
            return f"Musique probablement protégée détectée: {title} par {artist} (Score: {score}%)"
        elif score >= 50:
            return f"Possible musique protégée détectée: {title} par {artist} (Score: {score}%)"
        else:
            return f"Musique détectée mais avec une faible confiance: {title} (Score: {score}%)"

    async def _handle_no_music_detected(self, audio_path: str, transcription: str, reason: str) -> Dict[str, Any]:
        """Gère le cas où aucune musique n'est détectée par ACRCloud."""
        print(f"ℹ️ [ACR] Aucune musique détectée: {reason}")
        
        # Essayer d'analyser le contenu audio comme solution de secours
        content_analysis = await self._analyze_audio_content(audio_path, transcription)
        
        # Si l'analyse de contenu a détecté de la musique, utiliser ces résultats
        if content_analysis.get("music_detected", False):
            print("[ACR] Musique détectée via l'analyse de contenu")
            # Update copyright status based on content analysis
            content_analysis["audio_analysis"]["copyright_status"] = "copyright_free"
            content_analysis["audio_analysis"]["is_copyrighted"] = False
            content_analysis["audio_analysis"]["copyright_confidence"] = 0.8  # High confidence in free music
            return content_analysis
            
        # Check if there's any indication of copyright-free content in the transcription
        is_copyright_free = False
        if transcription:
            transcription_lower = transcription.lower()
            is_copyright_free = any(keyword in transcription_lower for keyword in self.royalty_free_keywords)
        
        # Set copyright status based on analysis
        copyright_status = "not_applicable"
        if is_copyright_free:
            copyright_status = "copyright_free"
        
        # Return default response with explicit copyright status
        result = ContentCheckResponse(
            status="success",
            music_detected=False,
            title=None,
            artist=None,
            album=None,
            release_date=None,
            label=None,
            copyright_protected=False,
            platforms={"acrcloud": {"score": 0, "match": False}},
            confidence_score=0.0,
            strike_risk_level="none",
            recommendation="Aucune musique protégée détectée",
            is_public_domain=False,
            whitelist_match=is_copyright_free,
            audio_analysis={
                "music_detected": False,
                "music_confidence": 0.0,
                "is_copyrighted": False,
                "copyright_status": copyright_status,
                "copyright_confidence": 0.9 if is_copyright_free else 0.0,
                "detected_genres": [],
                "is_public_domain": False
            }
        ).dict()
        return result

    async def recognize_audio(self, audio_path: str, transcription: str = None) -> Dict[str, Any]:
        """
        Reconnaissance audio améliorée utilisant l'API ACRCloud avec gestion avancée des erreurs.
        
        Args:
            audio_path: Chemin vers le fichier audio à analyser
            transcription: Transcription texte optionnelle pour analyse complémentaire
            
        Returns:
            Dict contenant les résultats de l'analyse de copyright
        """
        print(f"🎵 [ACR] Démarrage de l'analyse audio: {os.path.basename(audio_path)}")
        
        # Vérification initiale du fichier
        if not os.path.exists(audio_path):
            error_msg = f"Fichier audio introuvable: {audio_path}"
            print(f"❌ [ACR] {error_msg}")
            return await self.handle_transcription_error(error_msg)

        file_size = self._get_file_size(audio_path)
        duration = self._get_audio_duration(audio_path)
        
        print(f"[ACR] Taille: {file_size/1024:.1f} KB, Durée estimée: {duration:.1f}s")
        
        # Vérification de la taille minimale du fichier
        min_file_size = 16000  # ~1s à 16kHz, 8 bits
        if file_size < min_file_size:
            error_msg = f"Fichier trop petit ({file_size} bytes < {min_file_size} bytes min)"
            print(f"⚠️ [ACR] {error_msg}")
            return await self.handle_transcription_error(error_msg)
        
        # Si le fichier est grand/long, essayer l'identification par segments d'abord
        try:
            if duration > 30.0 or file_size > (4 * 1024 * 1024):
                print("[ACR] Fichier long/grand: tentative d'identification par segments (20s)")
                chunk_resp = await self._identify_by_chunks(audio_path, duration, transcription)
                if chunk_resp:
                    return chunk_resp
        except Exception as e:
            print(f" Chunked identify pre-check failed: {e}")

        # Vérification de l'activation d'ACRCloud
        if not self.acrcloud_enabled:
            print("⚠️ [ACR] Service ACRCloud désactivé - utilisation de l'analyse de secours")
            return await self._analyze_audio_content(audio_path, transcription)
        
        # Essai de reconnaissance avec ACRCloud
        print("[ACR] Préparation des données audio...")
        audio_data = self._prepare_audio_data(audio_path)
        
        if not audio_data:
            print("⚠️ [ACR] Échec de la préparation audio - tentative avec analyse de contenu")
            return await self._analyze_audio_content(audio_path, transcription)
        
        # Envoi à l'API ACRCloud
        print("[ACR] Envoi à l'API ACRCloud...")
        acrcloud_result = await self._send_to_acrcloud(audio_data)
        
        # Analyse de la réponse
        status = acrcloud_result.get("status", {})
        status_code = status.get("code")
        status_msg = status.get("msg", "Inconnu")
        
        print(f"[ACR] Réponse ACRCloud - Code: {status_code}, Message: '{status_msg}'")
        
        # Traitement des différents codes de statut
        if status_code == 0:  # Succès
            metadata = acrcloud_result.get("metadata", {})
            music_data = metadata.get("music", [])
            
            if music_data:
                # Prendre le premier résultat (le plus pertinent)
                music = music_data[0]
                score = music.get("score", 0)
                
                # Récupération des informations sur l'artiste et l'album
                artists = music.get("artists", [])
                artist_name = artists[0].get("name") if artists else "Artiste inconnu"
                album_info = music.get("album", {})
                album_name = album_info.get("name") if album_info else None
                
                # Détection du genre musical
                genres = []
                if "genres" in music and music["genres"]:
                    genres = [g["name"] for g in music["genres"] if "name" in g]
                
                # Vérification des droits d'auteur
                is_public_domain = any(genre.lower() in self.public_domain_indicators for genre in genres)
                
                print(f"✅ [ACR] Musique détectée: {music.get('title', 'Titre inconnu')} par {artist_name}")
                print(f"[ACR] Score: {score}%, Genres: {', '.join(genres) if genres else 'Inconnu'}")
                
                # Determine copyright status
                copyright_status = "copyrighted"
                copyright_confidence = score / 100.0
                
                if is_public_domain:
                    copyright_status = "public_domain"
                    copyright_confidence = max(copyright_confidence, 0.9)  # High confidence for public domain
                elif any(keyword in music.get("title", "").lower() for keyword in self.royalty_free_keywords):
                    copyright_status = "copyright_free"
                    copyright_confidence = max(copyright_confidence, 0.8)  # High confidence for royalty-free
                
                # Construction de la réponse
                resp = ContentCheckResponse(
                    status="success",
                    music_detected=True,
                    title=music.get("title"),
                    artist=artist_name,
                    album=album_name,
                    release_date=music.get("release_date"),
                    label=music.get("label"),
                    copyright_protected=copyright_status == "copyrighted",
                    platforms={"acrcloud": {"score": score, "match": True}},
                    confidence_score=score / 100.0,
                    strike_risk_level=self._calculate_risk_level(score, is_public_domain),
                    recommendation=self._generate_recommendation(music, score, is_public_domain),
                    is_public_domain=is_public_domain,
                    whitelist_match=any(keyword in music.get("title", "").lower() for keyword in self.royalty_free_keywords),
                    audio_analysis={
                        "music_detected": True,
                        "music_confidence": score / 100.0,
                        "is_copyrighted": copyright_status == "copyrighted",
                        "copyright_status": copyright_status,
                        "copyright_confidence": copyright_confidence,
                        "detected_genres": genres,
                        "is_public_domain": is_public_domain
                    }
                ).dict()
                # Ajouter l'offset de lecture si disponible (position du match dans l'audio en ms)
                try:
                    resp["play_offset_ms"] = music.get("play_offset_ms")
                except Exception:
                    pass
                # Ajouter la durée estimée en millisecondes
                try:
                    resp["duration_ms"] = int(duration * 1000)
                except Exception:
                    pass
                return resp
            else:
                print("ℹ️ [ACR] Aucune musique détectée dans la réponse ACRCloud")
                return await self._handle_no_music_detected(audio_path, transcription, "Aucune musique détectée par ACRCloud")
        
        elif status_code == 1001:
            # No music found
            print("✅ Aucune musique détectée par ACRCloud")
            resp = ContentCheckResponse(
                status="success",
                music_detected=False,
                title=None,
                artist=None,
                album=None,
                release_date=None,
                label=None,
                copyright_protected=False,
                platforms={"acrcloud": {"score": 0, "match": False}},
                confidence_score=0.0,
                strike_risk_level="low",
                recommendation="Aucune musique protégée détectée par ACRCloud",
                is_public_domain=False,
                whitelist_match=False
            ).dict()
            try:
                resp["duration_ms"] = int(duration * 1000)
            except Exception:
                pass
            return resp
        
        else:
            error_messages = {
                3001: "Paramètres invalides - vérifiez le format audio",
                3003: "Signature invalide - problème d'authentification",
                3004: "Clé d'accès invalide",
                3005: "Limite de requêtes dépassée",
                3006: "Données audio invalides",
                3014: "Fichier audio trop court"
            }
            
            error_msg = error_messages.get(status_code, f"Erreur ACRCloud inconnue: {status_msg}")
            print(f"❌ {error_msg} (code: {status_code})")
            
            # Si fichier trop grand (3016) ou message le suggère, essayer par segments
            try:
                if status_code == 3016 or "too large" in (status_msg or "").lower():
                    print("[ACR] Fichier trop grand - tentative par segments (20s)")
                    chunk_resp = await self._identify_by_chunks(audio_path, duration, transcription)
                    if chunk_resp:
                        return chunk_resp
            except Exception as e:
                print(f" Chunked identify after error failed: {e}")

            # Fallback à l'analyse de contenu en cas d'erreur
            print(f"⚠️ Tentative de récupération avec analyse de contenu...")
            try:
                result = await self._analyze_audio_content(audio_path, transcription)
                if result.get("music_detected", False):
                    print("✅ Musique détectée via l'analyse de contenu de secours")
                    return result
            except Exception as e:
                print(f" [ACR] Échec de l'analyse de contenu: {str(e)}")
            
            # Si l'analyse de contenu échoue aussi, retourner l'erreur ACRCloud
            resp = ContentCheckResponse(
                status="error",
                music_detected=False,
                title=None,
                artist=None,
                album=None,
                release_date=None,
                label=None,
                copyright_protected=False,
                platforms={"acrcloud": {"score": 0, "match": False, "error": error_msg}},
                confidence_score=0.0,
                strike_risk_level="low",
                recommendation=f"Erreur ACRCloud: {error_msg}",
                is_public_domain=False,
                whitelist_match=False
            ).dict()
            try:
                resp["duration_ms"] = int(duration * 1000)
            except Exception:
                pass
            return resp

    async def check_video_copyright(self, video_path: str) -> Dict[str, Any]:
        """Simplified video copyright check using filename analysis."""
        print(f" Analyse vidéo simplifiée: {video_path}")
        
        if not os.path.exists(video_path):
            return await self.handle_transcription_error("Fichier vidéo non trouvé")
        
        return await self.analyze_filename_for_copyright(video_path)

    async def validate_music_detection(self, detection_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate detection results - always return safe results."""
        if detection_result.get("copyright_protected"):
            confidence = detection_result.get("confidence_score", 0.0)
            if confidence < 0.95:  # Very high threshold to avoid false positives
                print(f" Réduction du risque copyright (confiance: {confidence:.1%})")
                detection_result.update({
                    "copyright_protected": False,
                    "strike_risk_level": "low",
                    "recommendation": "Risque de faux positif - marqué comme sûr"
                })
        
        return detection_result
