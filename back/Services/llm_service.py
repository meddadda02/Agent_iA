import os
import json
import re
from typing import Any, Dict, List, Optional

import groq
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Initialisation du client Groq avec la clé API
client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))

# Modèles : par défaut + fallback (tu peux aussi les définir via les variables d'env)
MODEL_DEFAULT = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
MODEL_FALLBACK = os.getenv("GROQ_MODEL_FALLBACK", "llama-3.1-70b-versatile")


# Services/llm_service.py
class LLMService:
    @staticmethod
    def get_available_models() -> Dict[str, Any]:
        """
        Liste uniquement les modèles LLM disponibles (pas de modèles de vision ou YOLO ici).
        """
        return {
            "models": [MODEL_DEFAULT, MODEL_FALLBACK, "yolov8x","Tesseract-OCR"],
            "default": MODEL_DEFAULT
        }


def _strip_code_fences(s: str) -> str:
    """
    Retire d'éventuelles balises de code ```json ... ``` autour du contenu.
    """
    s = s.strip()
    # Retire un bloc unique de fences au début/fin s'ils existent
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
    if s.endswith("```"):
        s = re.sub(r"\s*```$", "", s)
    return s.strip()


def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Extrait un JSON valide depuis un texte.
    Essaye dans l'ordre :
      1) parse direct (après retrait des fences)
      2) plus grand bloc délimité par { ... }
      3) première occurrence { ... } avec regex
    Retourne None si aucun JSON valide n'est trouvé.
    """
    try:
        s = _strip_code_fences(text)
        # 1) tentative directe
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass

        # 2) plus grand bloc { ... }
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = s[start:end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

        # 3) première occurrence via regex
        for m in re.finditer(r"\{.*?\}", s, re.DOTALL):
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                continue

    except Exception as e:
        print(f"Erreur extraction JSON: {e}")

    return None


def _format_detections_as_text(detections: Optional[List[Dict[str, Any]]]) -> str:
    if not detections:
        return "(aucun objet détecté)"
    parts = []
    for d in detections:
        label = d.get("label", "inconnu")
        conf = d.get("confidence", None)
        if conf is not None:
            parts.append(f"{label} ({conf})")
        else:
            parts.append(f"{label}")
    return ", ".join(parts)


def _build_prompt(detections: Optional[List[Dict[str, Any]]], ocr_text: Optional[str]) -> str:
    detections_text = _format_detections_as_text(detections)
    ocr_text = (ocr_text or "").strip()
    combined_info = f"Objets détectés : {detections_text}\nTexte OCR : {ocr_text}"

    # Instructions strictes pour forcer un JSON propre
    return f"""
Tu es un expert en modération de contenu pour YouTube. Analyse l'image à partir des informations ci-dessous et décide si elle respecte les règles YouTube.

INFORMATIONS IMAGE :
{combined_info}

Évalue les catégories suivantes (violence, souffrance, sexuel/indécent, drogues/objets illicites, symboles haineux, données perso, objets dangereux).
- Croise objets détectés ET texte OCR. Si l'un des deux est non conforme → "compatible": false.
- Ne fais aucune supposition non justifiée par ces données.

CONTRAINTE DE SORTIE :
Réponds UNIQUEMENT par un JSON valide, sans texte autour, SANS balises de code.
Schema attendu :
{{
  "compatible": true|false,
  "commentaire": "phrase courte et claire expliquant la décision"
}}
""".strip()


def _call_groq_json_only(messages: List[Dict[str, str]], model: str) -> str:
    """
    Appelle Groq chat completions et renvoie le contenu texte de la première réponse.
    """
    chat_completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0,
        max_tokens=256,
    )
    return chat_completion.choices[0].message.content


def check_youtube_compatibility(
    detections: Optional[List[Dict[str, Any]]] = None,
    ocr_text: Optional[str] = None
) -> Dict[str, Any]:
    """
    Utilise un LLM pour vérifier la compatibilité YouTube en se basant sur :
      - les objets détectés (YOLO)
      - le texte extrait (OCR)
    Retourne un dict contenant "compatible" (bool|None) et "commentaire" (str).
    """
    prompt = _build_prompt(detections, ocr_text)
    messages = [
        {
            "role": "system",
            "content": "Tu es un modérateur rigoureux. Tu réponds strictement au format demandé."
        },
        {"role": "user", "content": prompt},
    ]

    try:
        # Essai avec le modèle par défaut
        response_text = _call_groq_json_only(messages, MODEL_DEFAULT)
        result = extract_json_from_text(response_text)

        # Si pas de JSON valide, on tente un fallback
        if not isinstance(result, dict):
            try:
                response_text_fb = _call_groq_json_only(messages, MODEL_FALLBACK)
                result = extract_json_from_text(response_text_fb)
            except Exception as e_fb:
                result = None

        if not isinstance(result, dict):
            # Toujours rien : on renvoie le texte brut pour debug
            return {
                "compatible": None,
                "commentaire": "Impossible d'extraire un JSON valide depuis la réponse du LLM."
            }

        # Normalisation minimale du schéma
        compatible = result.get("compatible")
        commentaire = result.get("commentaire") or ""
        if not isinstance(compatible, bool):
            # Si le modèle renvoie quelque chose de non booléen → on marque indéterminé
            return {
                "compatible": None,
                "commentaire": f"Réponse JSON invalide (champ 'compatible' non booléen) : {result}"
            }

        return {
            "compatible": compatible,
            "commentaire": commentaire.strip()[:500]  # on limite un peu la taille par prudence
        }

    except Exception as e:
        return {
            "compatible": None,
            "commentaire": f"Erreur LLM : {str(e)}"
        }