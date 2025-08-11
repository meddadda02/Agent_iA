from transformers import pipeline
import spacy
import httpx
import os
from dotenv import load_dotenv
from typing import Dict, List, Optional
import re
import json
from sqlalchemy.orm import Session
from Models.analyzer_model import Analyzer # Assurez-vous que c'est le bon import pour votre modèle Analyzer
from spellchecker import SpellChecker # Importation de SpellChecker

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
  "groq_models": ["llama3-8b-8192", "llama3-70b-8192", "mixtral-8x7b-32768"],
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

if GROQ_API_KEY:
  print("✅ Clé API Groq configurée")
else:
  print("⚠️ Clé API Groq non configurée")

class ModerationService:
  @staticmethod
  def detect_language(text: str) -> str:
      """Détecte automatiquement la langue du texte"""
      text_lower = text.lower().strip()
      
      # Mots-clés français courants
      french_keywords = [
          'le', 'la', 'les', 'de', 'du', 'des', 'un', 'une', 'et', 'est', 'dans', 'pour', 'avec', 'sur', 'par',
          'comment', 'pourquoi', 'quand', 'où', 'que', 'qui', 'quoi', 'quel', 'quelle',
          'bonjour', 'salut', 'merci', 'oui', 'non', 'peut-être', 'temps', 'aujourd\'hui'
      ]
      
      # Mots-clés anglais courants
      english_keywords = [
          'the', 'and', 'is', 'in', 'to', 'of', 'a', 'that', 'it', 'with', 'for', 'as', 'was', 'on', 'are',
          'what', 'how', 'when', 'where', 'why', 'who', 'which',
          'hello', 'hi', 'thank', 'thanks', 'yes', 'no', 'maybe', 'weather', 'today', 'like'
      ]
      
      # Mots-clés arabes courants
      arabic_keywords = [
          'في', 'من', 'إلى', 'على', 'هذا', 'هذه', 'التي', 'الذي', 'كان', 'كانت',
          'ما', 'كيف', 'متى', 'أين', 'لماذا', 'من', 'أي',
          'مرحبا', 'شكرا', 'نعم', 'لا', 'ربما'
      ]
      
      words = text_lower.split()
      
      french_score = sum(1 for word in words if word in french_keywords)
      english_score = sum(1 for word in words if word in english_keywords)
      arabic_score = sum(1 for word in words if word in arabic_keywords)
      
      # Détection basée sur les caractères arabes
      arabic_chars = sum(1 for char in text if '\u0600' <= char <= '\u06FF')
      if arabic_chars > len(text) * 0.3:  # Plus de 30% de caractères arabes
          return "ar"
      
      # Comparaison des scores
      if french_score > english_score and french_score > arabic_score:
          return "fr"
      elif english_score > french_score and english_score > arabic_score:
          return "en"
      elif arabic_score > 0:
          return "ar"
      else:
          # Détection par défaut basée sur des patterns
          if any(word in text_lower for word in ['what', 'how', 'when', 'where', 'weather', 'like', 'today']):
              return "en"
          elif any(word in text_lower for word in ['comment', 'pourquoi', 'quand', 'où', 'temps', 'aujourd\'hui']):
              return "fr"
          else:
              return "fr"  # Par défaut français

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
      
      # Méthode 1: Chercher les blocs JSON avec ```json
      if "```json" in content:
          try:
              json_part = content.split("```json")[1].split("```")[0].strip()
              result = json.loads(json_part)
              print("✅ JSON extrait avec succès (méthode 1)")
              return result
          except (IndexError, json.JSONDecodeError) as e:
              print(f"⚠️ Échec méthode 1: {e}")
      
      # Méthode 2: Chercher les blocs avec ```
      if "```" in content:
          try:
              json_part = content.split("```")[1].strip()
              result = json.loads(json_part)
              print("✅ JSON extrait avec succès (méthode 2)")
              return result
          except (IndexError, json.JSONDecodeError) as e:
              print(f"⚠️ Échec méthode 2: {e}")
      
      # Méthode 3: Chercher des accolades { }
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
          "non_conforme", "non-conforme", "non conforme", "toxic", "violation",
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
  async def query_groq_enhanced(text: str, model: str = "llama3-70b-8192", language: str = "fr") -> Dict:
      """Analyse le contenu via l'API Groq - Méthode principale d'analyse, prompt identique pour audio et texte"""
      if not GROQ_API_KEY:
          return {
              "status": "conforme",
              "category": "erreur",
              "reasoning": "API Groq non configurée - analyse impossible",
              "is_insult": False
          }
      if model not in RULES["groq_models"]:
          model = "llama3-70b-8192"
      
      categories_list = [f"- {cat}: {desc}" for cat, desc in RULES["moderation_categories"].items()]
      categories_text = "\n".join(categories_list)
      
      # Configuration des prompts selon la langue détectée
      if language == "fr":
          system_msg = "Tu es un expert en modération de contenu français. Réponds TOUJOURS en français avec un JSON valide."
          prompt_intro = "Tu es un expert en modération de contenu français. Tu dois analyser ce texte français de manière approfondie pour détecter toute violation des catégories suivantes."
          context_rules = """
IMPORTANT :
- Sois STRICT, mais tiens compte du CONTEXTE.
- Si un mot sensible est utilisé dans un but explicatif, pédagogique ou neutre, le texte est conforme.
- Tu ne dois PAS signaler les mots sensibles s'ils ne sont pas utilisés avec une intention négative, violente, insultante, sexuelle ou dangereuse.
"""
      elif language == "en":
          system_msg = "You are an expert in English content moderation. ALWAYS respond in English with valid JSON."
          prompt_intro = "You are an expert in English content moderation. You must analyze this English text thoroughly to detect any violations of the following categories."
          context_rules = """
IMPORTANT:
- Be STRICT, but consider the CONTEXT.
- If a sensitive word is used for explanatory, educational, or neutral purposes, the text is compliant.
- You should NOT flag sensitive words if they are not used with negative, violent, insulting, sexual, or dangerous intent.
- Consider idiomatic expressions and context, especially in English or sports contexts.
"""
      elif language == "ar":
          system_msg = "أنت خبير في مراقبة المحتوى العربي. أجب دائماً باللغة العربية مع JSON صحيح."
          prompt_intro = "أنت خبير في مراقبة المحتوى العربي. يجب عليك تحليل هذا النص العربي بعمق للكشف عن أي انتهاكات للفئات التالية."
          context_rules = """
مهم:
- كن صارماً، لكن خذ السياق في الاعتبار.
- إذا تم استخدام كلمة حساسة لأغراض توضيحية أو تعليمية أو محايدة، فالنص مطابق.
- يجب ألا تبلغ عن الكلمات الحساسة إذا لم تُستخدم بقصد سلبي أو عنيف أو مهين أو جنسي أو خطير.
"""
      else:
          system_msg = "Tu es un expert en modération de contenu. Réponds dans la langue du texte analysé avec un JSON valide."
          prompt_intro = "Tu es un expert en modération de contenu. Tu dois analyser ce texte de manière approfondie."
          context_rules = """
IMPORTANT :
- Sois STRICT, mais tiens compte du CONTEXTE.
- Analyse dans la langue du texte fourni.
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
      
      try:
          async with httpx.AsyncClient(timeout=30.0) as client:
              response = await client.post(GROQ_API_URL, headers=headers, json=json_data)
              
              if response.status_code != 200:
                  print(f"Erreur API Groq: {response.status_code} - {response.text}")
                  return {
                      "status": "conforme",
                      "category": "erreur",
                      "reasoning": f"Erreur API Groq: {response.status_code}",
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
                  
                  print(f"✅ Analyse Groq réussie: {result['status']}")
                  return result
              else:
                  # Fallback intelligent
                  print("🔄 Utilisation du fallback intelligent")
                  return ModerationService.smart_fallback_analysis(content, text)

      except Exception as e:
          print(f"Erreur Groq: {e}")
          return {
              "status": "conforme",
              "category": "erreur",
              "reasoning": f"Erreur technique lors de l'analyse Groq: {str(e)}",
              "is_insult": False
          }

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
    
    # Détection automatique de la langue si nécessaire
    if language == "auto" or language == "":
        detected_language = ModerationService.detect_language(text)
        print(f"🔍 Langue détectée automatiquement: {detected_language}")
    else:
        detected_language = language
        print(f"🔍 Langue spécifiée: {detected_language}")
    
    # Normalisation stricte pour garantir la cohérence texte/audio
    def normalize_input(s):
        import string
        s = s.strip().lower()
        # Supprimer la ponctuation finale (.,!?)
        while s and s[-1] in ".!?":
            s = s[:-1]
        return s.strip()

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
    

    # ANALYSE PRINCIPALE AVEC GROQ (avec la langue détectée)
    groq_result = await ModerationService.query_groq_enhanced(corrected_text, model, language=detected_language)

    # Logique spéciale : expressions familières/humoristiques
    neutral_expressions = [
        "what the fuck", "wtf", "oh fuck", "fuck it", "what the hell", "damn", "shit", "no way"
    ]
    is_neutral_expression = any(expr in normalized_text for expr in neutral_expressions)
    is_insulting = any(word in normalized_text for word in ["suck", "idiot", "stupid", "hate", "kill"])
    if is_neutral_expression and not is_insulting:
        print("😅 Expression familière/humoristique détectée - statut forcé conforme")
        final_status = "conforme"
        final_message = "Expression familière/humoristique détectée : le texte est conforme."
        violated_rules = []
        conflict_detected = False
        groq_result = {
            "status": "conforme",
            "category": "aucun",
            "reasoning": "Expression familière/humoristique détectée (ex: 'what the fuck') dans un contexte non insultant.",
            "is_insult": False
        }
    else:
        # RÉSOLUTION DES CONFLITS BERT vs GROQ
        final_status = groq_result["status"]
        conflict_detected = False

        # Détecter les conflits
        bert_says_toxic = bert_label in RULES.get("bert_toxic_labels", ["toxic"])
        groq_says_toxic = groq_result["status"] == "non_conforme"

        if bert_says_toxic and not groq_says_toxic:
            conflict_detected = True
            print(f"⚠️ CONFLIT DÉTECTÉ: BERT={bert_label} vs GROQ={groq_result['status']}")
            print(f"📝 Texte analysé: '{text}' (langue: {detected_language})")

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
            final_status = "conforme"
            final_message = f"Erreur lors de l'analyse Groq: {groq_result['reasoning']}. Statut par défaut 'conforme'."
            violated_rules = []
    
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
        print(f"✅ Analyse sauvegardée en base de données (type={entry_type}, status={final_status}, langue={detected_language})")
    except Exception as e:
        print(f"⚠️ Erreur lors de la sauvegarde: {e}")
        db.rollback()
    
    return {
        "status": final_status,
        "bert": {"label": bert_label, "confidence": bert_confidence},
        "groq": groq_result,
        "message": final_message,
        "processed_text": processed_text_for_nlp,
        "violated_rules": list(set(violated_rules)),
        "conflict_detected": conflict_detected,
        "detected_language": detected_language,
    }

  @staticmethod
  async def query_groq_strict_verification(text: str, model: str = "llama3-70b-8192", language: str = "fr") -> Dict:
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
          }
      }
