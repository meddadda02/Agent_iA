from transformers import pipeline
import spacy
import httpx
import os
from dotenv import load_dotenv
from typing import Dict
import re
import json
from sqlalchemy.orm import Session
from Models.analyzer_model import Analyzer

# Chargement des variables d'environnement
load_dotenv()


# Chargement des règles depuis le fichier JSON
def load_rules():
  try:
      with open('rules.json', 'r', encoding='utf-8') as f:
          return json.load(f)
  except FileNotFoundError:
      print("Fichier rules.json non trouvé, utilisation des règles par défaut")
      
  except json.JSONDecodeError:
      print("Erreur de format dans rules.json, utilisation des règles par défaut")
      

# Chargement des règles
RULES = load_rules()

# Chargement des modèles
try:
  nlp = spacy.load("fr_core_news_sm")
  print("✅ Modèle spaCy chargé avec succès")
except OSError:
  print("⚠️ Modèle spaCy fr_core_news_sm non trouvé. Installez-le avec: python -m spacy download fr_core_news_sm")
  nlp = None

try:
  bert_classifier = pipeline("text-classification", model="unitary/toxic-bert")
  print("✅ Modèle BERT chargé avec succès")
except Exception as e:
  print(f"⚠️ Erreur lors du chargement du modèle BERT: {e}")
  bert_classifier = None

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
  def detect_insult_patterns(text: str) -> Dict:
      """Détecte les patterns d'insultes dans le texte"""
      text_lower = text.lower()
      detected_patterns = []
      
      # Vérification des patterns d'insultes
      for pattern in RULES["insult_patterns"]:
          if re.search(pattern, text_lower):
              detected_patterns.append(pattern)
      
      # Vérification des insultes d'animaux
      found_animal_insults = []
      for animal in RULES["animal_insults"]:
          if animal in text_lower:
              found_animal_insults.append(animal)
      
      return {
          "has_insult_pattern": len(detected_patterns) > 0,
          "patterns_found": detected_patterns,
          "animal_insults": found_animal_insults,
          "confidence": RULES["thresholds"]["insult_confidence"] if detected_patterns or found_animal_insults else 0.0
      }

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
      
      # Récupération du seuil de confiance
      confidence_key = f"{category}_confidence"
      confidence_value = RULES["thresholds"].get(confidence_key, 0.9)
      
      return {
          "has_violation": len(found_keywords) > 0,
          "keywords_found": found_keywords,
          "confidence": confidence_value if found_keywords else 0.0
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
              "confidence": 0.0,
              "is_insult": False
          }
      
      if model not in RULES["groq_models"]:
          model = "llama3-8b-8192"
      
      # Construction du prompt amélioré avec les règles
      categories_text = ", ".join(RULES["moderation_categories"].keys())
      prompt = f"""
          Tu es un expert en modération de contenu français. Tu dois analyser ce texte de manière approfondie pour détecter :
          {categories_text}

          Texte à analyser: "{text}"

          RÈGLES D'ANALYSE STRICTES:
          - Analyse le CONTEXTE complet et l'INTENTION derrière les mots
          - TOUTE comparaison avec un animal est une insulte : "comme un [animal]", "tel un [animal]", "X est un [animal]"
          - "aya comme un âne" = INSULTE (comparaison dégradante avec un animal)
          - Détecte les insultes même déguisées ou utilisant des mots apparemment innocents
          - Considère le ton agressif, sarcastique ou méprisant
          - Les références à des lieux sensibles (casa, israël) sont non conformes
          - Les références à des prénoms sensibles (mohammed) sont non conformes
          - Détecte le spam (gratuit, promotion, offre)
          - Sois particulièrement vigilant aux insultes indirectes et subtiles
          - **Pour les catégories 'violence' et 'harcèlement', sois extrêmement vigilant aux menaces implicites, à l'intimidation, aux avertissements de conséquences négatives pour autrui, et à toute forme de pression psychologique, même si le langage est indirect ou formulé comme un regret ou un conseil.**
          - **Les phrases qui visent à provoquer de la peur, de l'anxiété ou à exercer une contrainte morale ou psychologique doivent être classées comme 'non_conforme'.**

          EXEMPLES DE DÉTECTION:
          - "Tu es vraiment intelligent" (sarcastique) = insulte
          - "Quelle belle personne tu fais" (ironique) = harcèlement
          - "X est un porc" = insulte (animal)
          - "comme un âne" = insulte (comparaison animale)
          - "tel un chien" = insulte (comparaison animale)
          - "Retourne à casa" = places_interdits

          Réponds UNIQUEMENT en JSON valide:
          {{
              "status": "conforme" ou "non_conforme",
              "category": "une des catégories détectées ou aucun",
              "reasoning": "explication détaillée de ton analyse",
              "confidence": 0.0-1.0,
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
                  "content": "Tu es un expert en modération de contenu français. Tu détectes TOUTES les formes d'insultes, même les plus subtiles et indirectes. Tu es strict et vigilant. Réponds UNIQUEMENT en JSON valide."
              },
              {"role": "user", "content": prompt}
          ],
          "max_tokens": 400,
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
                      "confidence": 0.0,
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
                  if not all(key in result for key in ["status", "category", "reasoning", "confidence"]):
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
                  violation_keywords = [
                      "insulte", "offense", "non_conforme", "non conforme", "violation", 
                      "inapproprié", "toxique", "harcèlement", "menace", "agressif"
                  ]
                  
                  if any(word in content_lower for word in violation_keywords):
                      return {
                          "status": "non_conforme",
                          "category": "insulte",
                          "reasoning": f"Analyse de fallback - contenu potentiellement offensant détecté: {content[:200]}",
                          "confidence": 0.7,
                          "is_insult": True
                      }
                  else:
                      return {
                          "status": "conforme",
                          "category": "aucun",
                          "reasoning": f"Analyse de fallback - pas de violation détectée: {content[:200]}",
                          "confidence": 0.6,
                          "is_insult": False
                      }

      except Exception as e:
          print(f"Erreur Groq: {e}")
          return {
              "status": "conforme",
              "category": "erreur",
              "reasoning": f"Erreur technique lors de l'analyse Groq: {str(e)}",
              "confidence": 0.0,
              "is_insult": False
          }

  @staticmethod
  async def check_content_comprehensive(text: str, model: str, db: Session, user_id: int) -> Dict:
      """Analyse complète du contenu utilisant principalement Groq"""
      if not text or text.strip() == "":
          raise ValueError("Le texte ne peut pas être vide.")
      
      if len(text) > RULES["limits"]["max_text_length"]:
          raise ValueError(f"Le texte est trop long (max {RULES['limits']['max_text_length']} caractères).")
      
      processed_text = text
      bert_result = {"label": "safe", "score": 0.0}  # Valeur par défaut
      
      # Vérification whitelist
      if ModerationService.is_whitelisted(text):
          return {
              "status": "conforme",
              "bert": {"label": "safe", "score": 0.0},
              "groq": {"status": "conforme", "reasoning": "Whitelist", "confidence": 1.0, "category": "aucun"},
              "message": "Expression whitelist détectée : le texte est conforme.",
              "processed_text": processed_text,
              "violated_rules": [],
              "confidence_score": 1.0
          }
      
      # Traitement spaCy pour le preprocessing
      if nlp:
          try:
              doc = nlp(text)
              lemmas = [token.lemma_ for token in doc if not token.is_stop and not token.is_punct]
              processed_text = " ".join(lemmas) if lemmas else text
          except Exception as e:
              print(f"Erreur spaCy: {e}")
      
      # Détection d'insultes par patterns (garde comme fallback)
      insult_analysis = ModerationService.detect_insult_patterns(text)
      
      # Vérification automatique de TOUTES les règles dynamiques
      dynamic_violations = ModerationService.check_all_dynamic_rules(text)
      
      # ANALYSE PRINCIPALE AVEC GROQ
      groq_result = await ModerationService.query_groq_enhanced(text, model)
      
      # Analyse BERT uniquement si Groq n'est pas disponible ou en cas d'erreur
      bert_toxic = False
      if groq_result["status"] == "conforme" and groq_result["category"] == "erreur":
          if bert_classifier:
              try:
                  bert_result = bert_classifier(text)[0]
                  bert_toxic = (
                      bert_result['label'].lower() in RULES["bert_toxic_labels"] and 
                      bert_result['score'] > RULES["thresholds"]["bert_toxicity"]
                  )
              except Exception as e:
                  print(f"Erreur BERT: {e}")
      
      # Compilation des résultats - GROQ EN PRIORITÉ
      violated_rules = []
      messages = []
      confidence_scores = []
      
      # Priorité à l'analyse Groq
      if groq_result["status"] == "non_conforme" and groq_result["category"] != "erreur":
          violated_rules.append(groq_result["category"])
          messages.append(f"Groq: {groq_result['reasoning']}")
          confidence_scores.append(groq_result["confidence"])
      
      # Ajouter les patterns d'insultes seulement si Groq n'a pas détecté de problème
      if not violated_rules and insult_analysis["has_insult_pattern"]:
          violated_rules.append("insultes_et_harcèlement")
          messages.append(f"Pattern d'insulte détecté: {', '.join(insult_analysis['animal_insults'])}")
          confidence_scores.append(insult_analysis["confidence"])
      
      # Ajouter les violations dynamiques seulement si pas déjà détectées par Groq
      if not violated_rules:
          for category, violation in dynamic_violations.items():
              violated_rules.append(category)
              messages.append(f"{category.replace('_', ' ').title()} détecté: {', '.join(violation['keywords_found'])}")
              confidence_scores.append(violation["confidence"])
      
      # BERT en dernier recours
      if not violated_rules and bert_toxic:
          violated_rules.append("contenu_toxique")
          messages.append(f"BERT: contenu toxique ({bert_result['label']}, score {bert_result['score']:.2f})")
          confidence_scores.append(bert_result['score'])
      
      # Determine the final status and confidence score
      status = "conforme"
      final_message = "Le texte semble conforme aux règles de modération."
      global_confidence = groq_result["confidence"] # Start with Groq's confidence for compliant cases

      if violated_rules:
          status = "non conforme"
          # If there are violated rules, the global confidence is the max of all relevant confidences
          # including Groq's if it was non-compliant, or the highest of other rules if Groq was compliant.
          if groq_result["status"] == "non_conforme":
              global_confidence = max(confidence_scores + [groq_result["confidence"]])
          else:
              global_confidence = max(confidence_scores) if confidence_scores else 0.0 # Should not be 0 if violated_rules is not empty
          final_message = " | ".join(messages)
      elif groq_result["status"] == "conforme":
          # If Groq is explicitly compliant and no other rules flagged it, it's compliant.
          # The message should reflect Groq's reasoning if available and positive.
          if groq_result["reasoning"] and groq_result["category"] == "aucun":
              final_message = f"Groq: {groq_result['reasoning']}"
          else:
              final_message = "Le texte semble conforme aux règles de modération."
          global_confidence = groq_result["confidence"]
      else:
          # Fallback for cases where Groq might have an error but no other rules caught anything
          status = "conforme"
          final_message = "Analyse Groq non concluante, mais aucune violation détectée par d'autres méthodes."
          global_confidence = 0.0 # Or some default low confidence

      # Ensure message is not empty if non-compliant
      if status == "non conforme" and not final_message:
          final_message = "Contenu non conforme détecté."
      
      # Sauvegarde en base de données
      try:
          analyzer_entry = Analyzer(
              question=text[:1000],
              response=final_message[:1000], # Use final_message here
              score=str(global_confidence),
              toxic=(status == "non conforme"),
              user_id=user_id # Add this line
          )
          db.add(analyzer_entry)
          db.commit()
          print("✅ Analyse sauvegardée en base de données")
      except Exception as e:
          print(f"⚠️ Erreur lors de la sauvegarde: {e}")
          db.rollback()
      
      return {
          "status": status, # Use the determined status
          "bert": {
              "label": bert_result['label'].lower(),
              "score": bert_result['score']
          },
          "groq": groq_result,
          "message": final_message, # Use the determined message
          "processed_text": processed_text,
          "violated_rules": list(set(violated_rules)),
          "confidence_score": global_confidence
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
              "database": "connected"
          }
      }
