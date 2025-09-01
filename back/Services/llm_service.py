import os
import groq
import json
import re
from dotenv import load_dotenv, find_dotenv

# Charge .env depuis la racine du projet si possible
load_dotenv(find_dotenv(), override=False)

client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))

# Services/llm_service.py
class LLMService:
    @staticmethod
    def get_available_models():
        return {"models": ["llama-3.1-8b-instant", "llama-3.1-70b-versatile", "yolov8n"]}



def extract_json_from_text(text: str):
    """Extrait la première portion JSON valide trouvée dans un texte."""
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            json_str = match.group()
            return json.loads(json_str)
    except Exception as e:
        print(f"Erreur extraction JSON: {e}")
    return None

def check_youtube_compatibility(detections):
    prompt = f"""
    Tu es un expert en modération de contenu pour YouTube, chargé d’évaluer si une image respecte les règles de la plateforme.  
    Tu disposes d'une analyse réalisée par un modèle de détection d'objets (YOLO), qui a identifié les éléments suivants dans l’image : {detections}.

    Ta mission est de déterminer si l’image enfreint les politiques de contenu de YouTube, en évaluant les catégories suivantes :

    🔴 **Violence / Guerre**  
    - Armes visibles (fusils, couteaux, explosifs)  
    - Combats, soldats en action, scènes de guerre  
    - Sang, blessures, cadavres  
    - Violences physiques (bagarres, coups)

    😰 **Souffrance humaine**  
    - Expressions de peur, douleur, détresse  
    - Enfants en danger ou négligés  
    - Personnes ligotées, blessées, enfermées

    🔞 **Contenu sexuel ou indécent**  
    - Nudité, sous-vêtements, postures suggestives  
    - Décolletés, maillots trop révélateurs  
    - Activités sexuelles explicites ou implicites

    ⚠️ **Autres violations possibles**  
    - Drogues ou objets illicites  
    - Symboles haineux (nazisme, racisme, etc.)  
    - Données personnelles exposées (CIN, passeport, adresse…)  
    - Objets dangereux (seringues, couteaux, etc.)

    🧠 **Instructions :**
    Analyse intelligemment la scène :  
    - Ne juge pas seulement la présence brute d’un objet.  
    - Évalue le **contexte global** en croisant les objets détectés (ex : une personne + un couteau + une expression de peur = menace probable).

    **Réponds uniquement avec un JSON valide**, au format suivant :  
    - "compatible" : booléen (true = conforme YouTube, false = à modérer)    
    - "commentaire" : une phrase **courte et claire** justifiant l’évaluation


🎯 **Exemples valides :**

```json
{{ "compatible": false, "commentaire": "Contenu sexuellement suggestif" }}
{{ "compatible": true, "commentaire": "Image sans risque" }}
    """

    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.1-8b-instant"
    )

    response_text = chat_completion.choices[0].message.content

    result = extract_json_from_text(response_text)
    if result is None:
        result = {
            "compatible": None,
            "commentaire": f"Impossible d'extraire un JSON valide : {response_text}"
        }

    return result
