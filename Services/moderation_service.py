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
  async def query_groq_enhanced(text: str, model: str = "llama3-8b-8192") -> Dict:
      """Analyse le contenu via l'API Groq - Méthode principale d'analyse"""
      if not GROQ_API_KEY:
          return {
              "status": "conforme",
              "category": "erreur",
              "reasoning": "API Groq non configurée - analyse impossible",
              "is_insult": False
          }
      
      if model not in RULES["groq_models"]:
          model = "llama3-8b-8192"
      
      # Construction du prompt amélioré avec les règles
      categories_list = [f"- {cat}: {desc}" for cat, desc in RULES["moderation_categories"].items()]
      categories_text = "\n".join(categories_list)

      prompt = f"""
Tu es un expert en modération de contenu français. Tu dois analyser ce texte de manière approfondie pour détecter toute violation des catégories suivantes. Sois EXTRÊMEMENT STRICT et VIGILANT. Si une seule règle est enfreinte, le statut doit être 'non_conforme'.

Catégories de modération à vérifier:
{categories_text}

Texte à analyser: "{text}"

RÈGLES D'ANALYSE STRICTES:
- Analyse le CONTEXTE complet et l'INTENTION derrière les mots. Le sarcasme, l'ironie, et les insultes déguisées DOIVENT être détectés.
- TOUTE comparaison dégradante avec un animal, une personne, un groupe, un lieu, ou un objet est une insulte. Ex: "comme un [animal]", "tel un [animal]", "X est un [animal]", "X est un [objet]", "X est un [lieu]".
- Détecte les insultes même déguisées ou utilisant des mots apparemment innocents (ex: "intelligent" dit de manière sarcastique).
- Considère le ton agressif, sarcastique, méprisant ou condescendant.
- Les références à des lieux sensibles (ex: 'casa', 'israël') sont non conformes (catégorie 'places_interdits') si utilisées dans un contexte négatif ou conflictuel.
- Les références à des prénoms sensibles (ex: 'mohammed') sont non conformes (catégorie 'prenoms_sensibles') si utilisées dans un contexte négatif ou dégradant.
- Détecte le spam (mots comme 'gratuit', 'promotion', 'offre', 'cliquez ici', 'gagnez de l'argent', liens non sollicités, messages répétitifs).
- Sois particulièrement vigilant aux insultes indirectes, subtiles et aux sous-entendus.
- Si le texte contient des menaces, de l'incitation à la haine, ou du contenu sexuel, il est 'non_conforme'.

EXEMPLES DE DÉTECTION (ces exemples DOIVENT résulter en 'non_conforme' si le texte est similaire):
- "Tu es vraiment intelligent" (dit de manière sarcastique) = non_conforme, catégorie: insultes
- "Quelle belle personne tu fais" (dit de manière ironique et méprisante) = non_conforme, catégorie: harcèlement
- "X est un porc" = non_conforme, catégorie: insultes (comparaison animale dégradante)
- "comme un âne" = non_conforme, catégorie: insultes (comparaison animale dégradante)
- "tel un chien" = non_conforme, catégorie: insultes (comparaison animale dégradante)
- "Retourne à casa" = non_conforme, catégorie: places_interdits
- "Mohammed est un idiot" = non_conforme, catégorie: prenoms_sensibles, insultes
- "Cliquez ici pour gagner de l'argent GRATUIT!" = non_conforme, catégorie: spam- "Je vais te casser la gueule" = non_conforme, catégorie: violence
- "Ce groupe est plein de racistes" = non_conforme, catégorie: discours_haineux
- "Envoie-moi des photos nues" = non_conforme, catégorie: contenu_sexuel
- "Cette fille est une pute" = non_conforme, catégorie: insultes, contenu_sexuel

Réponds UNIQUEMENT en JSON valide. Si le texte est conforme, la catégorie doit be "aucun".
{{
  "status": "conforme" ou "non_conforme",
  "category": "une des catégories détectées (ex: insultes, harcèlement, spam) ou 'aucun'",
  "reasoning": "explication détaillée de ton analyse et pourquoi le texte est conforme ou non conforme",
  "is_insult": true/false (true si une insulte est détectée, même indirectement)
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
                  "content": "Tu es un modérateur de contenu EXTRÊMEMENT STRICT et VIGILANT. Ton objectif est de détecter TOUTES les formes de contenu non conforme, même les plus subtiles, indirectes, sarcastiques ou déguisées. Tu ne dois laisser passer AUCUNE violation. Si une seule règle est enfreinte, le statut doit être 'non_conforme'. Réponds UNIQUEMENT en JSON valide."
              },
              {"role": "user", "content": prompt}
          ],
          "max_tokens": 500, # Increased max_tokens for more detailed reasoning
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
              
              # Nettoyage du JSON
              if "\`\`\`json" in content:
                  content = content.split("\`\`\`json")[1].split("\`\`\`")[0].strip()
              elif "\`\`\`" in content:
                  content = content.split("\`\`\`")[1].strip()
              
              try:
                  result = json.loads(content)
                  # Validation des champs requis
                  if not all(key in result for key in ["status", "category", "reasoning"]): # 'confidence' supprimé
                      raise ValueError("Champs manquants dans la réponse")
              
                  # Normalisation du statut
                  if result["status"].lower() in ["non_conforme", "non conforme", "non-conforme"]:
                      result["status"] = "non_conforme"
                  elif result["status"].lower() == "conforme":
                      result["status"] = "conforme"
              
                  return result
              
              except (json.JSONDecodeError, ValueError) as e:
                  print(f"Réponse Groq non-JSON ou invalide: {content}")
                  # Analyse de fallback basée sur des mots-clés
                  content_lower = content.lower()
                  
                  # Mots-clés indiquant une violation
                  violation_keywords = RULES.get("fallback_keywords", ["insulte", "offense", "non_conforme", "non conforme", "violation", "inapproprié", "toxique", "harcèlement", "menace", "agressif"])
                  
                  if any(word in content_lower for word in violation_keywords):
                      return {
                          "status": "non_conforme",
                          "category": "insulte",
                          "reasoning": f"Analyse de fallback - contenu potentiellement offensant détecté: {content[:200]}",
                          "is_insult": True
                      }
                  else:
                      return {
                          "status": "conforme",
                          "category": "aucun",
                          "reasoning": f"Analyse de fallback - pas de violation détectée: {content[:200]}",
                          "is_insult": False
                      }

      except Exception as e:
          print(f"Erreur Groq: {e}")
          return {
              "status": "conforme",
              "category": "erreur",
              "reasoning": f"Erreur technique lors de l'analyse Groq: {str(e)}",
              "is_insult": False
          }

  @staticmethod
  def correct_spelling(text: str) -> str:
      """Corrects spelling errors in the text using pyspellchecker and custom rules."""
      if spell is None:
          print("⚠️ Correcteur orthographique non disponible. La correction orthographique sera ignorée.")
          return text
      
      # Custom corrections for common French misspellings that pyspellchecker might miss.
      # These are applied before the general spell checker.
      # Note: 'paye' is a valid word, so correcting it to 'pays' is a strong assumption
      # based on common user intent in phrases like "beau pays".
      custom_word_corrections = {
          "beu": "beau",
          "policie": "police",
          "tuees": "tuer", 
          "paye": "pays",
          "pute": "pute" # Ajouté pour empêcher la correction de 'pute'
      }

      words = text.split()
      corrected_words = []
      for word in words:
          word_lower = word.lower()
          
          # Apply custom corrections first
          if word_lower in custom_word_corrections:
              corrected_words.append(custom_word_corrections[word_lower])
          else:
              # Fallback to pyspellchecker for other words
              corrected_word = spell.correction(word_lower)
              if corrected_word is not None:
                  corrected_words.append(corrected_word)
              else:
                  corrected_words.append(word) # Keep original if no correction found
      
      return " ".join(corrected_words)

  @staticmethod
  async def check_content_comprehensive(text: str, model: str, db: Session, user_id: Optional[int] = None) -> Dict:
      """Analyse complète du contenu utilisant principalement Groq"""
      if not text or text.strip() == "":
          raise ValueError("Le texte ne peut pas être vide.")
      
      if len(text) > RULES["limits"]["max_text_length"]:
          raise ValueError(f"Le texte est trop long (max {RULES['limits']['max_text_length']} caractères).")
      
      # 1. Correction orthographique
      corrected_text = ModerationService.correct_spelling(text)
      if corrected_text != text:
          print(f"Texte original: '{text}'")
          print(f"Texte corrigé (orthographe): '{corrected_text}'")
      
      # Vérification whitelist (sur le texte original pour éviter de whitelister des fautes de frappe)
      if ModerationService.is_whitelisted(text): 
          return {
              "status": "conforme",
              "bert": {"label": "safe"},
              "groq": {"status": "conforme", "reasoning": "Whitelist", "category": "aucun"},
              "message": "Expression whitelist détectée : le texte est conforme.",
              "processed_text": corrected_text, # processed_text reflète le texte corrigé
              "violated_rules": [],
          }
      
      # Traitement spaCy pour le preprocessing (sur le texte corrigé)
      processed_text_for_nlp = corrected_text
      if nlp:
          try:
              doc = nlp(corrected_text)
              lemmas = [token.lemma_ for token in doc if not token.is_stop and not token.is_punct]
              processed_text_for_nlp = " ".join(lemmas) if lemmas else corrected_text
          except Exception as e:
              print(f"Erreur spaCy: {e}")
      
      # ANALYSE BERT
      bert_label = "safe"
      if bert_classifier:
          try:
              # BERT analyse le texte original pour sa classification de toxicité
              bert_output = bert_classifier(text)
              if bert_output and len(bert_output) > 0:
                  bert_label = bert_output[0]['label'].lower()
          except Exception as e:
              print(f"⚠️ Erreur lors de l'analyse BERT: {e}")
      
      # ANALYSE PRINCIPALE AVEC GROQ (sur le texte corrigé)
      groq_result = await ModerationService.query_groq_enhanced(corrected_text, model)
      
      # Définir le statut, le message, les règles violées et la confiance basés UNIQUEMENT sur Groq
      status = groq_result["status"]
      final_message = groq_result["reasoning"]
      violated_rules = [groq_result["category"]] if groq_result["status"] == "non_conforme" and groq_result["category"] != "aucun" else []

      # Si Groq a détecté une erreur, on peut avoir un message de fallback
      if groq_result["category"] == "erreur":
          status = "conforme" # Ou "erreur" si vous voulez un statut spécifique pour les erreurs API
          final_message = f"Erreur lors de l'analyse Groq: {groq_result['reasoning']}. Statut par défaut 'conforme'."
          violated_rules = []
      
      # Sauvegarde en base de données
      try:
          analyzer_entry = Analyzer(
              question=text[:1000], # Sauvegarde la question originale
              response=final_message[:1000],
              toxic=(status == "non_conforme"),
              user_id=user_id
          )
          db.add(analyzer_entry)
          db.commit()
          print("✅ Analyse sauvegardée en base de données")
      except Exception as e:
          print(f"⚠️ Erreur lors de la sauvegarde: {e}")
          db.rollback()
      
      return {
          "status": status,
          "bert": { # BERT result will now reflect actual analysis
              "label": bert_label,
          },
          "groq": groq_result, # Keep Groq's raw result for transparency
          "message": final_message,
          "processed_text": processed_text_for_nlp, # processed_text reflète le texte corrigé et lemmatisé
          "violated_rules": list(set(violated_rules)),
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
              "spellchecker": spell is not None # Ajout du statut du correcteur orthographique
          }
      }
