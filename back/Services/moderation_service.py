from transformers import pipeline
import spacy
import httpx
import os
from dotenv import load_dotenv
from typing import Dict, List, Optional, Any
import re
import json
import unicodedata
import asyncio
import time
from sqlalchemy.orm import Session
from Models.analyzer_model import Analyzer # Assurez-vous que c'est le bon import pour votre modèle Analyzer
from spellchecker import SpellChecker # Importation de SpellChecker
import logging

from Services.copyright_service import CopyrightService

# Configuration du logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Chargement des variables d'environnement
load_dotenv()

# Règles par défaut si le fichier JSON n'existe pas
DEFAULT_RULES = {
  "whitelist_expressions": [
      "test de modération", 
      "exemple de texte", 
      "démonstration"
  ],
  "moderation_categories": {
      "insultes": "Détecte les insultes directes ou indirectes, même subtiles, utilisant des animaux/objets pour rabaisser, ou toute forme de langage dégradant.",
      "harcèlement": "Détecte le harcèlement et les menaces",
      "discours_haineux": "Détecte les discours de haine basés sur la race, religion, etc.",
      "contenu_sexuel": "Détecte le contenu sexuel explicite",
      "violence": "Détecte les menaces de violence et contenus violents",
      "contenu_dangereux": "Détecte les contenus dangereux ou illégaux"
  },
  "bert_toxic_labels": ["TOXIC", "toxic"],
  "groq_models": ["llama3-8b-8192", "llama3-8b-8192", "mixtral-8x7b-32768"],
  "limits": {
      "max_text_length": 5000
  },
  "fallback_keywords": ["insulte", "offense", "non_conforme", "non conforme", "violation", "inapproprié", "toxique", "harcèlement", "menace", "agressif"]
}

# Chargement des règles depuis le fichier JSON
def load_rules():
  try:
      with open('rules.json', 'r', encoding='utf-8') as f:
          loaded_rules = json.load(f)
          print(f"✅ Fichier rules.json chargé avec succès.")
          return loaded_rules
  except FileNotFoundError:
      print("Fichier rules.json non trouvé, utilisation des règles par défaut")
      return DEFAULT_RULES
  except json.JSONDecodeError:
      print("Erreur de format dans rules.json, utilisation des règles par défaut")
      return DEFAULT_RULES

# Chargement des règles
RULES = load_rules()

# Configuration Groq par défaut (sans dépendance au fichier de configuration)
GROQ_CONFIG = {
    "max_retries": 3,
    "base_delay": 1.0,
    "max_delay": 10.0,
    "timeout": 15.0,
    "circuit_breaker_threshold": 5,
    "circuit_breaker_timeout": 300
}

# Initialisation du correcteur orthographique pour le français
try:
  spell = SpellChecker(language='fr')
  print("✅ Correcteur orthographique (pyspellchecker) chargé avec succès")
except Exception as e:
  print(f"⚠️ Erreur lors du chargement du correcteur orthographique: {e}")
  spell = None

# Chargement des modèles
try:
  bert_classifier = pipeline("text-classification", model="unitary/toxic-bert")
  print("✅ Modèle BERT chargé avec succès")
except Exception as e:
  print(f"⚠️ Erreur lors du chargement du modèle BERT: {e}")
  bert_classifier = None

try:
  nlp = spacy.load("fr_core_news_sm")
  print("✅ Modèle spaCy chargé avec succès")
except OSError:
  print("⚠️ Modèle spaCy fr_core_news_sm non trouvé. Installez-le avec: python -m spacy download fr_core_news_sm")
  nlp = None


# Configuration API Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

class GroqCircuitBreaker:
    def __init__(self):
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def is_open(self):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > GROQ_CONFIG["circuit_breaker_timeout"]:
                self.state = "HALF_OPEN"
                return False
            return True
        return False
    
    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= GROQ_CONFIG["circuit_breaker_threshold"]:
            self.state = "OPEN"
            print(f"🔴 Circuit breaker OUVERT - trop d'échecs Groq ({self.failure_count})")

groq_circuit_breaker = GroqCircuitBreaker()

class ModerationService:
  @staticmethod
  def detect_language_and_dialect_enhanced(text: str) -> Dict[str, Any]:
    """Version améliorée de la détection de langue avec plus de détails et métriques"""
    text_lower = text.lower().strip()
    
    if not text_lower:
        return {
            "language": "fr", 
            "dialect": "standard",
            "confidence_score": 0.0,
            "patterns": {},
            "analysis": {"error": "Texte vide"}
        }
    
    # Analyse des caractères arabes
    arabic_chars = sum(1 for char in text if '\u0600' <= char <= '\u06FF')
    latin_chars = sum(1 for char in text if char.isalpha() and not ('\u0600' <= char <= '\u06FF'))
    total_chars = len([c for c in text if c.isalpha()])
    
    if total_chars == 0:
        return {
            "language": "fr", 
            "dialect": "standard",
            "confidence_score": 0.0,
            "patterns": {},
            "analysis": {"error": "Aucun caractère alphabétique détecté"}
        }
    
    arabic_ratio = arabic_chars / total_chars if total_chars > 0 else 0
    
    def analyze_darija_patterns_enhanced(text: str) -> Dict[str, float]:
        """Analyse améliorée des patterns morphologiques du darija marocain avec métriques"""
        patterns_found = {}
        
        # Mots-clés essentiels darija avec pondération
        essential_darija = {
            'kifach': 1.0, 'nqadro': 0.9, 'nt3lmo': 0.8, 'lhaja': 0.7, 
            'jdida': 0.6, 'daba': 0.8, 'bzaf': 0.9, 'chwiya': 0.8,
            'machi': 1.0, 'ghir': 0.9, 'wach': 1.0, 'chkoun': 0.9, 
            'dyal': 0.8, 'kayn': 0.7, 'makaynch': 1.0, '3lach': 0.9,
            'hadchi': 0.8, 'hada': 0.6, 'hadik': 0.6, 'hadouk': 0.7
        }
        
        # Patterns de conjugaison darija
        conjugation_patterns = {
            r'\bn[a-z]+o\b': 0.8,      # nqadro, ndiro, nmchiw
            r'\bkan[a-z]+\b': 0.7,     # kanqdar, kandir, kanmchi
            r'\bghan[a-z]+\b': 0.8,    # ghanqdar, ghandir
            r'\b[a-z]+ach\b': 0.9,     # kifach, fuqach, 3lach
            r'\b[a-z]+ch\b': 0.6,      # wach, chkoun, chno
        }
        
        import re
        words = text_lower.split()
        
        # Score des mots essentiels
        essential_score = 0
        for word in words:
            if word in essential_darija:
                essential_score += essential_darija[word]
                patterns_found[f"mot_darija_{word}"] = essential_darija[word]
        
        # Score des patterns de conjugaison
        conjugation_score = 0
        for pattern, weight in conjugation_patterns.items():
            matches = re.findall(pattern, text_lower)
            if matches:
                conjugation_score += len(matches) * weight
                patterns_found[f"pattern_{pattern}"] = len(matches) * weight
        
        # Analyse des bigrammes darija
        darija_bigrams = ['ki', 'fa', 'ch', 'nq', 'nt', 'lm', 'dj', 'gh', 'dy', 'al']
        bigram_score = 0
        for i in range(len(text_lower) - 1):
            bigram = text_lower[i:i+2]
            if bigram in darija_bigrams:
                bigram_score += 0.1
        
        patterns_found["essential_words"] = essential_score
        patterns_found["conjugation_patterns"] = conjugation_score
        patterns_found["bigram_score"] = bigram_score
        
        total_score = essential_score + conjugation_score + bigram_score
        return patterns_found, total_score
    
    def analyze_french_patterns_enhanced(text: str) -> Dict[str, float]:
        """Analyse améliorée des patterns français"""
        french_indicators = {
            'le': 0.8, 'la': 0.8, 'les': 0.8, 'de': 0.6, 'du': 0.7, 
            'des': 0.7, 'un': 0.6, 'une': 0.6, 'et': 0.5, 'est': 0.7, 
            'dans': 0.6, 'avec': 0.6, 'pour': 0.6, 'sur': 0.5, 'ce': 0.5,
            'qui': 0.7, 'que': 0.6, 'nous': 0.7, 'vous': 0.7, 'ils': 0.6
        }
        
        words = text_lower.split()
        patterns_found = {}
        total_score = 0
        
        for word in words:
            if word in french_indicators:
                score = french_indicators[word]
                total_score += score
                patterns_found[f"mot_francais_{word}"] = score
        
        return patterns_found, total_score
    
    def analyze_english_patterns_enhanced(text: str) -> Dict[str, float]:
        """Analyse améliorée des patterns anglais"""
        english_indicators = {
            'the': 1.0, 'and': 0.8, 'is': 0.7, 'in': 0.6, 'to': 0.6, 
            'of': 0.7, 'a': 0.5, 'that': 0.6, 'it': 0.6, 'with': 0.6,
            'for': 0.5, 'as': 0.5, 'was': 0.6, 'on': 0.5, 'are': 0.6,
            'you': 0.6, 'this': 0.6, 'be': 0.5, 'at': 0.5, 'by': 0.5
        }
        
        words = text_lower.split()
        patterns_found = {}
        total_score = 0
        
        for word in words:
            if word in english_indicators:
                score = english_indicators[word]
                total_score += score
                patterns_found[f"mot_anglais_{word}"] = score
        
        return patterns_found, total_score
    
    # Analyse complète avec métriques
    darija_patterns, darija_score = analyze_darija_patterns_enhanced(text_lower)
    french_patterns, french_score = analyze_french_patterns_enhanced(text_lower)
    english_patterns, english_score = analyze_english_patterns_enhanced(text_lower)
    
    # Compilation des patterns détectés
    all_patterns = {
        "darija": darija_patterns,
        "french": french_patterns, 
        "english": english_patterns,
        "scores": {
            "darija_total": darija_score,
            "french_total": french_score,
            "english_total": english_score,
            "arabic_ratio": arabic_ratio
        }
    }
    
    # Logique de décision avec score de confiance
    confidence_score = 0.0
    detected_language = "fr"
    detected_dialect = "standard"
    
    if darija_score >= 1.0 or (arabic_ratio > 0.1 and darija_score >= 0.5):
        detected_language = "ar"
        detected_dialect = "maghreb"
        confidence_score = min(darija_score / 3.0, 1.0)
        logger.info(f"Darija détecté avec score: {darija_score:.2f}, confiance: {confidence_score:.2f}")
    
    elif arabic_ratio > 0.3:
        detected_language = "ar"
        detected_dialect = "standard"
        confidence_score = arabic_ratio
    
    elif french_score > english_score and french_score > 0.5:
        detected_language = "fr"
        detected_dialect = "standard"
        confidence_score = min(french_score / 5.0, 1.0)
    
    elif english_score > french_score and english_score > 0.5:
        detected_language = "en"
        detected_dialect = "standard"
        confidence_score = min(english_score / 5.0, 1.0)
    
    else:
        # Analyse contextuelle pour les cas ambigus
        if 'video' in text_lower or 'vidéo' in text_lower:
            if darija_score > 0.3:
                detected_language = "ar"
                detected_dialect = "maghreb"
                confidence_score = 0.6
            elif any(fr_word in text_lower for fr_word in ['va', 'de', 'rire', 'tuer']):
                detected_language = "fr"
                detected_dialect = "standard"
                confidence_score = 0.7
    
    # Analyse détaillée du texte
    text_analysis = {
        "total_chars": len(text),
        "alphabetic_chars": total_chars,
        "arabic_chars": arabic_chars,
        "latin_chars": latin_chars,
        "arabic_ratio": arabic_ratio,
        "word_count": len(text.split()),
        "detected_patterns_count": {
            "darija": len(darija_patterns),
            "french": len(french_patterns),
            "english": len(english_patterns)
        }
    }
    
    return {
        "language": detected_language,
        "dialect": detected_dialect,
        "confidence_score": confidence_score,
        "patterns": all_patterns,
        "analysis": text_analysis
    }

  @staticmethod
  def detect_language_and_dialect(text: str) -> Dict[str, str]:
    """Détecte automatiquement la langue et le dialecte du texte avec une approche intelligente"""
    enhanced_result = ModerationService.detect_language_and_dialect_enhanced(text)
    return {
        "language": enhanced_result["language"],
        "dialect": enhanced_result["dialect"]
    }

  @staticmethod
  def detect_language(text: str) -> str:
      """Détecte automatiquement la langue du texte (fonction simplifiée pour compatibilité)"""
      result = ModerationService.detect_language_and_dialect(text)
      return result["language"]

  @staticmethod
  def is_whitelisted(text: str) -> bool:
      """Vérifie si le texte contient une expression whitelistée"""
      text_lower = text.lower()
      for expr in RULES["whitelist_expressions"]:
          if expr in text_lower:
              return True
      return False

  @staticmethod
  def detect_dynamic_keywords(text: str, category: str) -> Dict:
      """Détecte les mots-clés sensibles basés sur les règles dynamiques"""
      text_lower = text.lower()
      found_keywords = []
      
      # Récupération de la règle pour cette catégorie
      rule_description = RULES["moderation_categories"].get(category, "")
      
      # Extraction des mots entre guillemets simples
      keywords = re.findall(r"'([^']*)'", rule_description)
      
      for keyword in keywords:
          if keyword.lower() in text_lower:
              found_keywords.append(keyword)
      
      return {
          "has_violation": len(found_keywords) > 0,
          "keywords_found": found_keywords,
      }

  @staticmethod
  def check_all_dynamic_rules(text: str) -> Dict:
      """Vérifie toutes les règles dynamiques automatiquement"""
      all_violations = {}
      
      # Parcourir toutes les catégories de modération
      for category in RULES["moderation_categories"].keys():
          # Ignorer les catégories qui ont des fonctions spéciales
          if category in ["insultes", "harcèlement", "discours_haineux", "contenu_sexuel", "violence", "contenu_dangereux"]:
              continue
          
          # Vérifier cette catégorie
          result = ModerationService.detect_dynamic_keywords(text, category)
          if result["has_violation"]:
              all_violations[category] = result
      
      return all_violations

  @staticmethod
  def extract_json_from_response(content: str) -> Optional[Dict]:
      """Extrait et parse le JSON de la réponse Groq de manière robuste"""
      print(f"🔍 Réponse brute Groq: {content[:500]}...")
      
      # Méthode 1: Chercher les blocs JSON avec \`\`\`json
      if "\`\`\`json" in content:
          try:
              json_part = content.split("\`\`\`json")[1].split("\`\`\`")[0].strip()
              result = json.loads(json_part)
              print("✅ JSON extrait avec succès (méthode 1)")
              return result
          except (IndexError, json.JSONDecodeError) as e:
              print(f"⚠️ Échec méthode 1: {e}")
      
      # Méthode 2: Chercher les blocs avec \`\`\`
      if "\`\`\`" in content:
          try:
              json_part = content.split("\`\`\`")[1].strip()
              result = json.loads(json_part)
              print("✅ JSON extrait avec succès (méthode 2)")
              return result
          except (IndexError, json.JSONDecodeError) as e:
              print(f"⚠️ Échec méthode 2: {e}")
      
      # Mthode 3: Chercher des accolades { }
      try:
          start = content.find('{')
          end = content.rfind('}') + 1
          if start != -1 and end > start:
              json_part = content[start:end]
              result = json.loads(json_part)
              print("✅ JSON extrait avec succès (méthode 3)")
              return result
      except json.JSONDecodeError as e:
          print(f"⚠️ Échec méthode 3: {e}")
      
      # Méthode 4: Regex pour extraire le JSON
      try:
          import re
          json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
          matches = re.findall(json_pattern, content, re.DOTALL)
          for match in matches:
              try:
                  result = json.loads(match)
                  if all(key in result for key in ["status", "category", "reasoning"]):
                      print("✅ JSON extrait avec succès (méthode 4)")
                      return result
              except json.JSONDecodeError:
                  continue
      except Exception as e:
          print(f"⚠️ Échec méthode 4: {e}")
      
      print("❌ Impossible d'extraire le JSON de la réponse")
      return None

  @staticmethod
  def smart_fallback_analysis(content: str, original_text: str) -> Dict:
      """Analyse de fallback intelligente qui comprend le contexte"""
      print(f"🔄 Analyse de fallback intelligente pour: '{original_text}'")
      
      content_lower = content.lower()
      
      # Vérifier d'abord si la réponse indique explicitement que c'est conforme
      positive_indicators = [
          "conforme", "compliant", "safe", "innocent", "normal", "appropriate",
          "no violation", "pas de violation", "aucune violation", "pas problématique",
          "simple question", "question innocente", "conversation normale",
          "weather", "météo", "temps", "paris"
      ]
      
      negative_indicators = [
          "non_conforme", "non conforme", "non-conforme", "toxic", "violation",
          "insulte", "insult", "offensive", "inappropriate", "problematic"
      ]
      
      # Compter les indicateurs positifs et négatifs
      positive_count = sum(1 for indicator in positive_indicators if indicator in content_lower)
      negative_count = sum(1 for indicator in negative_indicators if indicator in content_lower)
      
      print(f"📊 Indicateurs positifs: {positive_count}, négatifs: {negative_count}")
      

      # Analyse contextuelle spéciale pour les questions météo
      weather_patterns = [
          "weather", "météo", "temps", "temperature", "température",
          "what is the weather", "quel temps", "comment est le temps"
      ]
      is_weather_question = any(pattern in original_text.lower() for pattern in weather_patterns)
      # Analyse contextuelle pour les expressions familières ou humoristiques
      neutral_expressions = [
          "what the fuck", "wtf", "oh fuck", "fuck it", "what the hell", "damn", "shit", "no way"
      ]
      is_neutral_expression = any(expr in original_text.lower() for expr in neutral_expressions)
      # Si le contexte est neutre/humoristique et pas insultant, considérer comme conforme
      if is_weather_question:
          print("🌤️ Question météo détectée - considérée comme conforme")
          return {
              "status": "conforme",
              "category": "aucun",
              "reasoning": f"Question météo innocente détectée. Analyse de fallback: {content[:200]}...",
              "is_insult": False
          }
      if is_neutral_expression and not any(word in original_text.lower() for word in ["suck", "idiot", "stupid", "hate", "kill"]):
          print("😅 Expression familière/humoristique détectée - considérée comme conforme")
          return {
              "status": "conforme",
              "category": "aucun",
              "reasoning": f"Expression familière/humoristique détectée (ex: 'what the fuck') dans un contexte non insultant. Analyse de fallback: {content[:200]}...",
              "is_insult": False
          }
      
      # Si plus d'indicateurs positifs que négatifs, considérer comme conforme
      if positive_count > negative_count:
          return {
              "status": "conforme",
              "category": "aucun",
              "reasoning": f"Analyse de fallback positive (indicateurs: +{positive_count}/-{negative_count}): {content[:200]}...",
              "is_insult": False
          }
      elif negative_count > positive_count:
          return {
              "status": "non_conforme",
              "category": "contenu_suspect",
              "reasoning": f"Analyse de fallback négative (indicateurs: +{positive_count}/-{negative_count}): {content[:200]}...",
              "is_insult": True
          }
      else:
          # En cas d'égalité, privilégier la sécurité mais être raisonnable
          # Pour les textes courts et innocents, privilégier conforme
          if len(original_text.split()) <= 10 and not any(word in original_text.lower() for word in ['fuck', 'shit', 'damn', 'hell', 'stupid', 'idiot']):
              return {
                  "status": "conforme",
                  "category": "aucun",
                  "reasoning": f"Analyse de fallback: texte court sans mots suspects. {content[:200]}...",
                  "is_insult": False
              }
          else:
              return {
                  "status": "non_conforme",
                  "category": "contenu_suspect",
                  "reasoning": f"Analyse de fallback: incertitude, privilégiant la sécurité. {content[:200]}...",
                  "is_insult": False
              }

  @staticmethod
  async def query_groq_with_retry(text: str, model: str = "llama3-8b-8192", language: str = "fr") -> Dict:
      """
      Analyse le contenu via l'API Groq avec retry automatique et fallback entre modèles
      """
      if not GROQ_API_KEY:
          return {
              "status": "conforme",
              "category": "erreur",
              "reasoning": "API Groq non configurée - analyse impossible",
              "is_insult": False
          }
      
      if groq_circuit_breaker.is_open():
          print("🔴 Circuit breaker ouvert - Groq temporairement désactivé")
          return {
              "status": "conforme",
              "category": "erreur",
              "reasoning": "Service Groq temporairement indisponible (circuit breaker ouvert)",
              "is_insult": False
          }
      
      available_models = RULES.get("groq_models", ["llama3-8b-8192", "llama3-8b-8192", "mixtral-8x7b-32768"])
      models_to_try = [model] + [m for m in available_models if m != model]
      
      for model_attempt in models_to_try:
          print(f"🔄 Tentative avec le modèle: {model_attempt}")
          
          max_retries = GROQ_CONFIG["max_retries"]
          for attempt in range(max_retries):
              try:
                  result = await ModerationService._single_groq_request(text, model_attempt, language, attempt + 1)
                  
                  if result["category"] != "erreur":
                      groq_circuit_breaker.record_success()
                      return result
                  
                  # Si c'est une erreur 503/502/504, on retry
                  if "503" in result["reasoning"] or "502" in result["reasoning"] or "504" in result["reasoning"]:
                      if attempt < max_retries - 1:
                          base_delay = GROQ_CONFIG["base_delay"]
                          max_delay = GROQ_CONFIG["max_delay"]
                          delay = min(base_delay * (2 ** attempt), max_delay)
                          print(f"⏳ Retry dans {delay}s (tentative {attempt + 1}/{max_retries})")
                          await asyncio.sleep(delay)
                          continue
                  
                  # Pour les autres erreurs, passer au modèle suivant
                  break
                  
              except Exception as e:
                  print(f"❌ Erreur lors de la tentative {attempt + 1} avec {model_attempt}: {e}")
                  if attempt < max_retries - 1:
                      base_delay = GROQ_CONFIG["base_delay"]
                      max_delay = GROQ_CONFIG["max_delay"]
                      delay = min(base_delay * (2 ** attempt), max_delay)
                      await asyncio.sleep(delay)
                  else:
                      break
      
      groq_circuit_breaker.record_failure()
      print("❌ Tous les modèles Groq ont échoué - utilisation du fallback intelligent")
      
      return ModerationService.smart_fallback_analysis(
          f"Échec de tous les modèles Groq après {GROQ_CONFIG['max_retries']} tentatives", 
          text
      )

  @staticmethod
  async def _single_groq_request(text: str, model: str, language: str, attempt_num: int) -> Dict:
      """
      Effectue une seule requête vers l'API Groq
      """
      categories_list = [f"- {cat}: {desc}" for cat, desc in RULES["moderation_categories"].items()]
      categories_text = "\n".join(categories_list)
      
      # Configuration des prompts selon la langue détectée
      if language == "fr":
          system_msg = "Tu es un expert en modération de contenu français. Réponds TOUJOURS en français avec un JSON valide."
          prompt_intro = "Tu es un expert en modération de contenu français. Tu dois analyser ce texte français de manière approfondie pour détecter toute violation des catégories suivantes."
          context_rules = """
IMPORTANT :
- Sois STRICT, mais tiens compte du CONTEXTE.
- Considère le slang, l'orthographe phonétique, le verlan et le leetspeak.
- Les avances sexuelles explicites, propositions non sollicitées ou harcèlement sexuel sont NON_CONFORMES, même exprimés en slang ou sous couvert d'humour.
- Si un mot sensible est utilisé à des fins explicatives, pédagogiques ou clairement neutres, le texte est conforme.
- Ne PAS ignorer des formulations sexuelles explicites visant une personne (ex: menaces ou propositions sexuelles) même si le texte contient des expressions familières comme "wtf".
"""
      elif language == "en":
          system_msg = "You are an expert in English content moderation. ALWAYS respond in English with valid JSON."
          prompt_intro = "You are an expert in English content moderation. You must analyze this English text thoroughly to detect any violations of the following categories."
          context_rules = """
IMPORTANT:
- Be STRICT, but consider the CONTEXT.
- Consider slang, phonetic spellings, verlan, and leetspeak.
- Explicit sexual advances, unsolicited propositions, or sexual harassment are NON_COMPLIANT even if expressed with slang or humor.
- If a sensitive word is used for explanatory, educational, or clearly neutral purposes, the text is compliant.
- Do NOT ignore explicit sexual formulations aimed at a person even if the text includes neutral idioms like "wtf".
"""
      elif language == "ar":
          system_msg = "أنت خبير في مراقبة المحتوى العربي. أجب دائماً باللغة العربية مع JSON صحيح."
          prompt_intro = "أنت خبير في مراقبة المحتوى العربي. يجب عليك تحليل هذا النص العربي بعمق للكشف عن أي انتهاكات للفئات التالية."
          context_rules = """
مهم:
- كن صارماً، لكن خذ السياق في الاعتبار.
- ضع في الاعتبار العامية والتهجئة الصوتية ولغة "لييتسبيك".
- المضايقات الجنسية أو العبارات الجنسية الصريحة (حتى لو كانت بروح الدعابة) تعتبر غير مطابقة.
- إذا كانت الكلمات الحساسة لأغراض توضيحية أو تعليمية أو محايدة بوضوح، فالنص مطابق.
"""
      else:
          system_msg = "Tu es un expert en modération de contenu. Réponds dans la langue du texte analysé avec un JSON valide."
          prompt_intro = "Tu es un expert en modération de contenu. Tu dois analyser ce texte de manière approfondie."
          context_rules = """
IMPORTANT :
- Sois STRICT, mais tiens compte du CONTEXTE.
- Analyse dans la langue du texte fourni.
- Considère le slang, le verlan, l'orthographe phonétique et le leetspeak.
- Les avances/propositions sexuelles explicites ou le harcèlement sexuel sont NON CONFORMES même sous couvert d'humour.
- Si un terme sensible est utilisé de manière descriptive/pédagogique neutre, considère conforme.
"""
      prompt = f"""
{prompt_intro}

{context_rules}

Catégories de modération à vérifier:
{categories_text}

Langue du texte: {language}

Texte à analyser: "{text}"

RÈGLES D'ANALYSE STRICTES:
- Analyse le CONTEXTE complet et l'INTENTION derrière les mots.
- Les questions innocentes sur la météo, les directions, ou les informations générales sont CONFORMES.
- Détecte les insultes même déguisées ou utilisant des mots apparemment innocents.
- Considère le ton agressif, sarcastique, méprisant ou condescendant.
- Détecte le spam et les contenus dangereux.

IMPORTANT: Réponds UNIQUEMENT avec un JSON valide, sans texte supplémentaire avant ou après.

{{
  "status": "conforme" ou "non_conforme",
  "category": "une des catégories détectées ou 'aucun'",
  "reasoning": "explication détaillée de ton analyse dans la langue {language}",
  "is_insult": true/false
}}
"""
      
      headers = {
          "Authorization": f"Bearer {GROQ_API_KEY}",
          "Content-Type": "application/json",
      }
      
      json_data = {
          "model": model,
          "messages": [
              {
                  "role": "system",
                  "content": system_msg
              },
              {"role": "user", "content": prompt}
          ],
          "max_tokens": 500,
          "temperature": 0.1
      }
      
      print(f"🔄 Requête Groq (tentative {attempt_num}) - Modèle: {model}")
      
      timeout = GROQ_CONFIG["timeout"]
      async with httpx.AsyncClient(timeout=timeout) as client:
          response = await client.post(GROQ_API_URL, headers=headers, json=json_data)
          
          if response.status_code != 200:
              error_msg = f"Erreur API Groq: {response.status_code}"
              if response.status_code in [503, 502, 504]:
                  error_msg += " (Service temporairement indisponible)"
              elif response.status_code == 429:
                  error_msg += " (Limite de taux dépassée)"
              elif response.status_code == 401:
                  error_msg += " (Clé API invalide)"
              
              print(f"❌ {error_msg} - {response.text[:200]}")
              return {
                  "status": "conforme",
                  "category": "erreur",
                  "reasoning": error_msg,
                  "is_insult": False
              }
          
          data = response.json()
          content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
          
          # Extraction robuste du JSON
          result = ModerationService.extract_json_from_response(content)
          
          if result:
              # Validation des champs requis
              if not all(key in result for key in ["status", "category", "reasoning"]):
                  print("⚠️ Champs manquants dans la réponse JSON")
                  return ModerationService.smart_fallback_analysis(content, text)
              
              # Normalisation du statut
              if result["status"].lower() in ["non_conforme", "non conforme", "non-conforme"]:
                  result["status"] = "non_conforme"
              elif result["status"].lower() == "conforme":
                  result["status"] = "conforme"
              
              print(f"✅ Analyse Groq réussie (modèle: {model}): {result['status']}")
              return result
          else:
              # Fallback intelligent
              print("🔄 Utilisation du fallback intelligent")
              return ModerationService.smart_fallback_analysis(content, text)

  @staticmethod
  async def query_groq_enhanced(text: str, model: str = "llama3-8b-8192", language: str = "fr") -> Dict:
      """
      Point d'entrée principal pour l'analyse Groq - utilise maintenant le système de retry
      """
      return await ModerationService.query_groq_with_retry(text, model, language)

  @staticmethod
  def correct_spelling(text: str, language: str = "fr") -> str:
      """Corrects spelling errors in the text using pyspellchecker and custom rules. Only for French."""
      if language != "fr":
          return text
      if spell is None:
          print("⚠️ Correcteur orthographique non disponible. La correction orthographique sera ignorée.")
          return text
      custom_word_corrections = {
          "beu": "beau",
          "policie": "police",
          "tuees": "tuer",
          "paye": "pays",
          "pute": "pute"
      }
      words = text.split()
      corrected_words = []
      for word in words:
          word_lower = word.lower()
          if word_lower in custom_word_corrections:
              corrected_words.append(custom_word_corrections[word_lower])
          else:
              corrected_word = spell.correction(word_lower)
              if corrected_word is not None:
                  corrected_words.append(corrected_word)
              else:
                  corrected_words.append(word)
      return " ".join(corrected_words)

  @staticmethod
  async def check_content_comprehensive(text: str, model: str, db: Session, user_id: Optional[int] = None, language: str = "auto", entry_type: str = "texte") -> Dict:
    """Analyse complète du contenu utilisant principalement Groq, support multilingue avec résolution de conflits"""
    if not text or text.strip() == "":
        raise ValueError("Le texte ne peut pas être vide.")
    if len(text) > RULES["limits"]["max_text_length"]:
        raise ValueError(f"Le texte est trop long (max {RULES['limits']['max_text_length']} caractères).")
    
    if language == "auto" or language == "" or language is None:
        lang_detection = ModerationService.detect_language_and_dialect(text)
        detected_language = lang_detection["language"]
        detected_dialect = lang_detection["dialect"]
        print(f"🔍 Langue détectée automatiquement: {detected_language} (dialecte: {detected_dialect})")
    else:
        detected_language = language
        detected_dialect = "standard"
        print(f"🔍 Langue spécifiée: {detected_language}")
    
    # Normalisation générique (sans liste de mots): accents, répétitions, leetspeak
    def normalize_input(s):
        import string
        s = s.strip().lower()
        # Supprimer la ponctuation redondante en fin
        while s and s[-1] in ".!?":
            s = s[:-1]

        # Retirer accents/diacritiques
        try:
            s = ''.join(c for c in unicodedata.normalize('NFD', s) if not unicodedata.combining(c))
        except Exception:
            pass

        # Réduire les répétitions excessives: cooool -> cool
        try:
            s = re.sub(r'(.)\1{2,}', r'\1\1', s)
        except Exception:
            pass

        # De-leetspeak générique (sans liste spécifique de mots)
        leet_map = str.maketrans({
            '1': 'i', '!': 'i', '0': 'o', '3': 'e', '4': 'a', '5': 's', '7': 't',
            '@': 'a', '$': 's', '€': 'e', '£': 'l'
        })
        try:
            s = s.translate(leet_map)
        except Exception:
            pass

        # Espace unique
        s = re.sub(r'\s+', ' ', s).strip()
        return s

    normalized_text = normalize_input(text)
    corrected_text = normalized_text
    processed_text_for_nlp = normalized_text
    
    # Correction orthographique seulement pour le français
    if detected_language == "fr":
        corrected_text = ModerationService.correct_spelling(normalized_text, language=detected_language)
        if corrected_text != normalized_text:
            print(f"Texte original: '{normalized_text}'")
            print(f"Texte corrigé (orthographe): '{corrected_text}'")
        if nlp:
            try:
                doc = nlp(corrected_text)
                lemmas = [token.lemma_ for token in doc if not token.is_stop and not token.is_punct]
                processed_text_for_nlp = " ".join(lemmas) if lemmas else corrected_text
            except Exception as e:
                print(f"Erreur spaCy: {e}")
        else:
            processed_text_for_nlp = corrected_text
    else:
        processed_text_for_nlp = normalized_text
    
    # Vérification whitelist (toujours sur le texte original)
    if ModerationService.is_whitelisted(text): 
        return {
            "status": "conforme",
            "bert": {"label": "safe", "confidence": 1.0},
            "groq": {"status": "conforme", "reasoning": "Expression whitelist détectée", "category": "aucun"},
            "message": "Expression whitelist détectée : le texte est conforme.",
            "processed_text": processed_text_for_nlp,
            "violated_rules": [],
            "conflict_detected": False,
            "detected_language": detected_language,
            "detected_dialect": detected_dialect,
            "copyright_strike_risk": False,
            "copyright_analysis": {
                "status": "success",
                "music_detected": False,
                "title": None,
                "artist": None,
                "album": None,
                "release_date": None,
                "label": None,
                "copyright_protected": False,
                "platforms": {}
            },
            "youtube_report": None,
            "automatic_action": "allow",
            "can_publish": True
        }
    
    # ANALYSE BERT (selon la langue)
    bert_label = "safe"
    bert_confidence = 0.0
    if detected_language in ["fr", "en"] and bert_classifier:
        try:
            bert_output = bert_classifier(text)
            if bert_output and len(bert_output) > 0:
                bert_label = bert_output[0]['label'].lower()
                bert_confidence = bert_output[0].get('score', 0.0)
                print(f"🔍 BERT Analysis ({detected_language}): {bert_label} (confidence: {bert_confidence:.3f})")
        except Exception as e:
            print(f"⚠️ Erreur lors de l'analyse BERT: {e}")
    

    # Fournir au LLM le texte original et la version normalisée pour mieux comprendre le slang
    groq_input = f"TEXTE_ORIGINAL: \"{text}\"\nTEXTE_NORMALISE: \"{processed_text_for_nlp}\""
    groq_result = await ModerationService.query_groq_enhanced(groq_input, model, language=detected_language)

    print(f"🎵 Analyse copyright en cours pour le texte: '{text[:50]}...'")
    copyright_analysis = {}
    copyright_strike_risk = False
    youtube_report = None
    automatic_action = "allow"
    can_publish = True
    
    try:
        # Analyser le texte pour détecter des paroles de musique
        copyright_service = CopyrightService()
        copyright_result = await copyright_service.analyze_text_for_music(text)
        # La réponse du service est structurée, avec une clé 'copyright_analysis'
        copyright_analysis = copyright_result.get("copyright_analysis", {})
        lyrics_analysis = copyright_result.get("lyrics_analysis", {})
        
        # Déterminer le risque de strike basé sur l'analyse
        if copyright_analysis.get("music_detected", False) and copyright_analysis.get("copyright_protected", False):
            copyright_strike_risk = True
            automatic_action = "block"
            can_publish = False
            youtube_report = f"Contenu potentiellement protégé détecté: {copyright_analysis.get('title', 'Inconnu')} par {copyright_analysis.get('artist', 'Inconnu')}"
            print(f"⚠️ Risque de copyright détecté: {copyright_analysis.get('title')} - {copyright_analysis.get('artist')}")
        else:
            print(f"✅ Aucun risque de copyright détecté")
            
    except Exception as e:
        print(f"⚠️ Erreur lors de l'analyse copyright: {e}")
        copyright_analysis = {
            "status": "error",
            "music_detected": False,
            "title": None,
            "artist": None,
            "album": None,
            "release_date": None,
            "label": None,
            "copyright_protected": False,
            "platforms": {}
        }

    # Suppression de l'auto-conformité pour expressions familières: décision déléguée à Groq/strict
    # RÉSOLUTION DES CONFLITS BERT vs GROQ
    final_status = groq_result["status"]
    conflict_detected = False

    # Détecter les conflits
    bert_says_toxic = bert_label in RULES.get("bert_toxic_labels", ["toxic"])
    groq_says_toxic = groq_result["status"] == "non_conforme"

    if bert_says_toxic and not groq_says_toxic:
        conflict_detected = True
        print(f"⚠️ CONFLIT DÉTECTÉ: BERT={bert_label} vs GROQ={groq_result['status']}")
        print(f"📝 Texte analysé: '{text}' (langue: {detected_language}, dialecte: {detected_dialect})")

        # Logique de résolution : privilégier Groq si BERT a une faible confiance
        if bert_confidence < 0.7:  # Seuil de confiance faible
            final_status = "conforme"
            print(f"✅ Résolution: GROQ prioritaire (BERT confiance faible: {bert_confidence:.3f})")
        else:
            # Double vérification avec Groq en mode strict
            print("🔄 Double vérification avec Groq en mode strict...")
            strict_groq_result = await ModerationService.query_groq_strict_verification(corrected_text, model, detected_language)
            if strict_groq_result["status"] == "conforme":
                final_status = "conforme"
                print("✅ Résolution: Texte confirmé comme conforme par double vérification")
            else:
                final_status = "non_conforme"
                print("❌ Résolution: Texte confirmé comme non conforme par double vérification")

    elif not bert_says_toxic and groq_says_toxic:
        conflict_detected = True
        print(f"⚠️ CONFLIT DÉTECTÉ: BERT={bert_label} vs GROQ={groq_result['status']}")
        # Dans ce cas, faire confiance à Groq (plus contextuel)
        final_status = "non_conforme"
        print("✅ Résolution: GROQ prioritaire (plus contextuel)")

    # Message final et règles violées
    if final_status != groq_result["status"]:
        if conflict_detected:
            final_message = f"[CONFLIT RÉSOLU] {groq_result['reasoning']} (BERT: {bert_label}, confiance: {bert_confidence:.3f})"
        else:
            final_message = groq_result["reasoning"]
    else:
        final_message = groq_result["reasoning"]

    violated_rules = [groq_result["category"]] if final_status == "non_conforme" and groq_result["category"] != "aucun" else []

    if groq_result["category"] == "erreur":
        if "circuit breaker" in groq_result["reasoning"].lower():
            final_status = "conforme"
            final_message = f"Service de modération temporairement indisponible. Statut par défaut 'conforme'. ({groq_result['reasoning']})"
        elif "503" in groq_result["reasoning"] or "502" in groq_result["reasoning"] or "504" in groq_result["reasoning"]:
            final_status = "conforme"
            final_message = f"Erreur lors de l'analyse Groq: {groq_result['reasoning']}. Statut par défaut 'conforme'."
        else:
            final_status = "conforme"
            final_message = f"Erreur lors de l'analyse: {groq_result['reasoning']}. Statut par défaut 'conforme'."
        violated_rules = []

    # Politique conservatrice: bloquer tout contenu non conforme
    if final_status == "non_conforme":
        automatic_action = "block"
        can_publish = False
    
    # En plus, bloquer si risque de copyright élevé
    if copyright_strike_risk:
        automatic_action = "block"
        can_publish = False
        if final_status == "conforme":
            final_message += f" Cependant, risque de copyright détecté: {youtube_report}"
    
    # Sauvegarde en base
    try:
        analyzer_kwargs = dict(
            question=text[:1000],
            response=final_message[:1000],
            toxic=(final_status == "non_conforme"),
            user_id=user_id,
            type=entry_type
        )
        if hasattr(Analyzer, 'language'):
            analyzer_kwargs['language'] = detected_language
        analyzer_entry = Analyzer(**analyzer_kwargs)
        db.add(analyzer_entry)
        db.commit()
        print(f"✅ Analyse sauvegardée en base de données (type={entry_type}, status={final_status}, langue={detected_language}, dialecte={detected_dialect})")
    except Exception as e:
        print(f"⚠️ Erreur lors de la sauvegarde: {e}")
        db.rollback()
    
    # Préparer la réponse finale
    # Récupérer l'analyse audio depuis copyright_analysis si disponible
    audio_analysis = copyright_analysis.get("audio_analysis", {})
    
    # S'assurer que les champs essentiels sont présents
    if not audio_analysis and isinstance(copyright_analysis, dict):
        audio_analysis = {
            "music_detected": copyright_analysis.get("music_detected", False),
            "music_confidence": copyright_analysis.get("confidence_score", 0.0),
            "is_copyrighted": copyright_analysis.get("copyright_protected", False),
            "copyright_status": "copyrighted" if copyright_analysis.get("copyright_protected") else "copyright_free",
            "copyright_confidence": copyright_analysis.get("confidence_score", 0.0),
            "detected_genres": copyright_analysis.get("detected_genres", []),
            "is_public_domain": copyright_analysis.get("is_public_domain", False),
            "refrain_detected": copyright_analysis.get("refrain_detected", False),
            "refrain_confidence": copyright_analysis.get("refrain_confidence", 0.0),
            "refrain_patterns": copyright_analysis.get("refrain_patterns", []),
            "autotune_detected": copyright_analysis.get("autotune_detected", False),
            "autotune_confidence": copyright_analysis.get("autotune_confidence", 0.0),
            "autotune_artifacts": copyright_analysis.get("autotune_artifacts", [])
        }
    
    # Construire la réponse finale en respectant la résolution des conflits
    response = {
        "status": final_status,
        "bert": {"label": bert_label, "confidence": bert_confidence},
        "groq": groq_result,
        "message": final_message if 'final_message' in locals() else groq_result.get("reasoning", "Analyse effectuée avec succès"),
        "processed_text": processed_text_for_nlp,
        "violated_rules": violated_rules if 'violated_rules' in locals() else [],
        "conflict_detected": conflict_detected if 'conflict_detected' in locals() else False,
        "detected_language": detected_language,
        "detected_dialect": detected_dialect,
        "copyright_strike_risk": copyright_strike_risk,
        "copyright_analysis": copyright_analysis,
        "youtube_report": youtube_report,
        "automatic_action": automatic_action,
        "can_publish": can_publish,
        "audio_analysis": audio_analysis
    }

    return response

  @staticmethod
  async def query_groq_strict_verification(text: str, model: str = "llama3-8b-8192", language: str = "fr") -> Dict:
    """Double vérification stricte avec Groq pour résoudre les conflits"""
    if not GROQ_API_KEY:
        return {
            "status": "conforme",
            "category": "erreur",
            "reasoning": "API Groq non configurée - vérification impossible",
            "is_insult": False
        }
    
    # Prompts selon la langue
    if language == "en":
        system_msg = "You are a content moderation expert performing double verification. Be precise and contextual in your analysis. ALWAYS respond in English with valid JSON only."
        prompt = f"""
You are a content moderation expert. Another system (BERT) detected this text as potentially toxic, but a first contextual analysis suggests it is compliant.

MISSION: Perform a STRICT DOUBLE VERIFICATION to determine if this text is really problematic.

Text to verify: "{text}"
Language: {language}

VERIFICATION CRITERIA:
1. Are there direct or indirect insults?
2. Is there harassment or threats?
3. Is there hateful, sexual or violent content?
4. Is there spam or dangerous content?
5. Is the context innocent (normal question, polite conversation)?

INSTRUCTIONS:
- If the text is an innocent question, normal conversation, or educational content → COMPLIANT
- If you detect a real violation → NON_COMPLIANT
- Be VERY precise in your reasoning

Respond ONLY with valid JSON, no additional text:
{{
  "status": "conforme" or "non_conforme",
  "category": "detected category or 'aucun'",
  "reasoning": "detailed explanation of your verification in English",
  "is_insult": true/false
}}
"""
    elif language == "ar":
        system_msg = "أنت خبير في مراقبة المحتوى تقوم بالتحقق المزدوج. كن دقيقاً وسياقياً في تحليلك. أجب دائماً باللغة العربية مع JSON صحيح فقط."
        prompt = f"""
أنت خبير في مراقبة المحتوى. نظام آخر (BERT) اكتشف هذا النص كمحتوى سام محتمل، لكن التحليل السياقي الأول يشير إلى أنه مطابق.

المهمة: قم بالتحقق المزدوج الصارم لتحديد ما إذا كان هذا النص مشكلة حقاً.

النص المراد التحقق منه: "{text}"
اللغة: {language}

معايير التحقق:
1. هل توجد إهانات مباشرة أو غير مباشرة؟
2. هل يوجد مضايقة أو تهديدات؟
3. هل يوجد محتوى كراهية أو جنسي أو عنيف؟
4. هل يوجد محتوى مزعج أو خطير؟
5. هل السياق بريء (سؤال عادي، محادثة مهذبة)؟

التعليمات:
- إذا كان النص سؤالاً بريئاً أو محادثة عادية أو محتوى تعليمي → مطابق
- إذا اكتشفت انتهاكاً حقيقياً → غير مطابق
- كن دقيقاً جداً في تبريرك

أجب فقط بصيغة JSON صحيح، بدون نص إضافي:
{{
  "status": "conforme" أو "non_conforme",
  "category": "الفئة المكتشفة أو 'aucun'",
  "reasoning": "شرح مفصل للتحقق باللغة العربية",
  "is_insult": true/false
}}
"""
    else:  # français par défaut
        system_msg = "Tu es un expert en modération qui effectue des doubles vérifications. Tu dois être précis et contextuel dans tes analyses. Réponds TOUJOURS en français avec un JSON valide uniquement."
        prompt = f"""
Tu es un expert en modération de contenu. Un autre système (BERT) a détecté ce texte comme potentiellement toxique, mais une première analyse contextuelle suggère qu'il est conforme.

MISSION: Effectue une DOUBLE VÉRIFICATION STRICTE pour déterminer si ce texte est réellement problématique.

Texte à vérifier: "{text}"
Langue: {language}

CRITÈRES DE VÉRIFICATION:
1. Y a-t-il des insultes directes ou indirectes ?
2. Y a-t-il du harcèlement ou des menaces ?
3. Y a-t-il du contenu haineux, sexuel ou violent ?
4. Y a-t-il du spam ou du contenu dangereux ?
5. Le contexte est-il innocent (question normale, conversation polie) ?

INSTRUCTIONS:
- Si le texte est une question innocente, une conversation normale, ou du contenu éducatif → CONFORME
- Si tu détectes une réelle violation → NON_CONFORME
- Sois TRÈS précis dans ton raisonnement

Réponds UNIQUEMENT avec un JSON valide, sans texte supplémentaire:
{{
  "status": "conforme" ou "non_conforme",
  "category": "catégorie détectée ou 'aucun'",
  "reasoning": "explication détaillée de ta vérification en français",
  "is_insult": true/false
}}
"""
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    
    json_data = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": system_msg
            },
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 300,
        "temperature": 0.1
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(GROQ_API_URL, headers=headers, json=json_data)
            
            if response.status_code != 200:
                print(f"Erreur API Groq (vérification): {response.status_code}")
                return {
                    "status": "conforme",
                    "category": "erreur",
                    "reasoning": "Erreur lors de la double vérification",
                    "is_insult": False
                }
            
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            
            # Extraction robuste du JSON
            result = ModerationService.extract_json_from_response(content)
            
            if result:
                return result
            else:
                print(f"Réponse Groq vérification non-JSON: {content}")
                return ModerationService.smart_fallback_analysis(content, text)

    except Exception as e:
        print(f"Erreur Groq vérification: {e}")
        return {
            "status": "conforme",
            "category": "erreur",
            "reasoning": f"Erreur technique lors de la double vérification: {str(e)}",
            "is_insult": False
        }

  @staticmethod
  def get_rules():
      """Retourne les règles de modération"""
      return RULES

  @staticmethod
  def get_available_models():
      """Retourne les modèles disponibles"""
      return {"models": RULES["groq_models"]}

  @staticmethod
  def get_health_status():
      """Retourne le statut de santé des services"""
      return {
          "status": "healthy",
          "services": {
              "spacy": nlp is not None,
              "bert": bert_classifier is not None,
              "groq": GROQ_API_KEY is not None,
              "database": "connected",
              "spellchecker": spell is not None
          },
          "groq_circuit_breaker": {
              "state": groq_circuit_breaker.state,
              "failure_count": groq_circuit_breaker.failure_count,
              "last_failure": groq_circuit_breaker.last_failure_time
          }
      }
