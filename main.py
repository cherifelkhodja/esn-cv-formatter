#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
CV Formatter ESN - Outil d'Automatisation de CV
=============================================================================
Ce script transforme des CVs au format PDF en documents Word (.docx)
standardisés selon le format de l'ESN Gemini Consulting.

L'extraction intelligente des données est réalisée via l'API Google Gemini
(modèle gemini-1.5-flash).

Auteur: Cherif Elkhodja
Version: 1.0.0
Date: 2025-12-09
=============================================================================
"""

# =============================================================================
# IMPORTS - Bibliothèques nécessaires
# =============================================================================

# Bibliothèque standard Python pour les opérations système
import os

# Bibliothèque standard Python pour la manipulation de chemins de fichiers
from pathlib import Path

# Bibliothèque standard Python pour la manipulation JSON
import json

# Bibliothèque standard Python pour les expressions régulières
import re

# Bibliothèque standard Python pour le logging (journalisation)
import logging

# Bibliothèque standard Python pour les arguments en ligne de commande
import sys

# Bibliothèque pour charger les variables d'environnement depuis .env
from dotenv import load_dotenv

# Bibliothèque Google pour l'API Gemini (Intelligence Artificielle)
import google.generativeai as genai

# Bibliothèque pour l'extraction de texte depuis les PDF
from pypdf import PdfReader

# Bibliothèque pour le templating Word (injection de données dans .docx)
from docxtpl import DocxTemplate


# =============================================================================
# CONFIGURATION DU LOGGING
# =============================================================================
# Configuration du système de journalisation pour suivre l'exécution du script.
# Le format inclut l'horodatage, le niveau de log et le message.

logging.basicConfig(
    level=logging.INFO,  # Niveau minimum des messages affichés
    format='%(asctime)s - %(levelname)s - %(message)s',  # Format des messages
    datefmt='%Y-%m-%d %H:%M:%S'  # Format de la date/heure
)

# Création d'un logger spécifique pour ce module
logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES - Chemins et Configuration
# =============================================================================
# Définition des chemins vers les dossiers et fichiers du projet.
# L'utilisation de Path permet une gestion cross-platform des chemins.

# Chemin racine de l'application (dossier contenant ce script)
CHEMIN_RACINE = Path(__file__).parent

# Chemin vers le dossier d'entrée contenant les PDFs à traiter
CHEMIN_INPUT = CHEMIN_RACINE / "input"

# Chemin vers le dossier de sortie où seront générés les DOCX
CHEMIN_OUTPUT = CHEMIN_RACINE / "output"

# Chemin vers le template Word fourni par l'utilisateur
CHEMIN_TEMPLATE = CHEMIN_RACINE / "template_gemini.docx"


# =============================================================================
# INFORMATIONS DU MANAGER (Variables statiques)
# =============================================================================
# Ces informations seront injectées dans chaque CV généré.
# Elles identifient le manager responsable du candidat.

MANAGER_INFO = {
    "nom": "Cherif Elkhodja",
    "email": "cherif.elkhodja@geminiconsulting.fr",
    "telephone": "07 44 09 76 14",
    "adresse": "54 Avenue Hoche, 75008 Paris"
}


# =============================================================================
# PROMPT SYSTÈME GEMINI
# =============================================================================
# Ce prompt définit le comportement de l'IA Gemini lors de l'analyse des CVs.
# Il spécifie :
# - Le rôle de l'IA (expert en recrutement IT)
# - Les règles à respecter (langue française, anonymisation, synthèse)
# - Le format JSON exact attendu en sortie
#
# IMPORTANT : Toute modification de ce prompt doit être documentée dans MEMORY.md

PROMPT_SYSTEME = """
Tu es un expert en recrutement IT. Ta mission est de convertir le texte brut d'un CV en une structure JSON stricte.

RÈGLES IMPORTANTES :
1. Langue : FRANÇAIS uniquement.
2. Anonymisation : NE JAMAIS inclure l'email, le téléphone ou l'adresse du candidat.
3. Synthèse : Reformule les tâches pour qu'elles soient professionnelles.
4. Tri : "Compétences Métiers" concerne la connaissance d'un secteur (Banque, Assurance, Retail...). "Compétences Fonctionnelles" concerne le savoir-faire organisationnel (Gestion de projet, Agilité, Management). Ne remplis ces listes que si c'est pertinent.

FORMAT JSON ATTENDU :
{
  "profil": {
    "titre_cible": "String",
    "annees_experience": "String"
  },
  "resume_competences": {
    "techniques": {
       "Clé (ex: Cloud)": "Valeur (ex: AWS, Azure)",
       "Clé (ex: Langages)": "Valeur (ex: Python)"
    },
    "metiers": ["Liste (ex: Finance de marché, Risques) - Laisser vide si non pertinent"],
    "fonctionnelles": ["Liste (ex: Scrum, Encadrement) - Laisser vide si non pertinent"],
    "langues": ["Anglais : Courant", "Français : Natif"]
  },
  "formations": {
    "diplomes": [ {"annee": "AAAA", "libelle": "Diplôme"} ],
    "certifications": [ {"annee": "AAAA", "libelle": "Nom Certif"} ]
  },
  "experiences": [
    {
      "client": "String",
      "periode": "String",
      "titre": "String",
      "contexte": "String",
      "taches": {
        "Réalisations": ["Tâche 1", "Tâche 2"]
      },
      "environnement_technique": "String"
    }
  ]
}

Réponds UNIQUEMENT avec le JSON, sans texte avant ou après.
"""


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================


def charger_configuration():
    """
    Charge et valide la configuration de l'application.

    Cette fonction effectue les opérations suivantes :
    1. Charge les variables d'environnement depuis le fichier .env
    2. Vérifie la présence de la clé API Gemini
    3. Configure l'API Gemini avec la clé fournie

    Returns:
        bool: True si la configuration est valide, False sinon

    Raises:
        SystemExit: Si la clé API n'est pas configurée
    """
    # Chargement du fichier .env situé à la racine du projet
    # override=True permet de recharger les variables si elles existent déjà
    load_dotenv(CHEMIN_RACINE / ".env", override=True)

    # Récupération de la clé API depuis les variables d'environnement
    cle_api = os.getenv("GEMINI_API_KEY")

    # Vérification que la clé API est présente et non vide
    if not cle_api or cle_api == "votre_cle_api_gemini_ici":
        logger.error("❌ ERREUR: La variable GEMINI_API_KEY n'est pas configurée.")
        logger.error("   Veuillez copier .env.example en .env et renseigner votre clé API.")
        return False

    # Configuration de la bibliothèque Google Generative AI avec la clé
    # Cette étape est nécessaire avant tout appel à l'API
    genai.configure(api_key=cle_api)

    logger.info("✅ Configuration chargée avec succès")
    return True


def verifier_prerequis():
    """
    Vérifie que tous les prérequis sont présents pour l'exécution.

    Cette fonction contrôle :
    1. L'existence du dossier input/
    2. L'existence du fichier template Word
    3. Crée le dossier output/ s'il n'existe pas

    Returns:
        bool: True si tous les prérequis sont satisfaits, False sinon
    """
    # Variable pour suivre le statut de la vérification
    prerequis_ok = True

    # Vérification du dossier input
    # Ce dossier doit contenir les PDFs à traiter
    if not CHEMIN_INPUT.exists():
        logger.error(f"❌ ERREUR: Le dossier input/ n'existe pas : {CHEMIN_INPUT}")
        logger.error("   Créez ce dossier et placez-y vos fichiers PDF.")
        prerequis_ok = False
    else:
        logger.info(f"✅ Dossier input trouvé : {CHEMIN_INPUT}")

    # Vérification du template Word
    # Ce fichier est fourni par l'utilisateur et contient le format ESN
    if not CHEMIN_TEMPLATE.exists():
        logger.error(f"❌ ERREUR: Le template Word n'existe pas : {CHEMIN_TEMPLATE}")
        logger.error("   Veuillez fournir le fichier template_gemini.docx")
        prerequis_ok = False
    else:
        logger.info(f"✅ Template Word trouvé : {CHEMIN_TEMPLATE}")

    # Création du dossier output s'il n'existe pas
    # exist_ok=True évite une erreur si le dossier existe déjà
    # parents=True crée les dossiers parents si nécessaire
    CHEMIN_OUTPUT.mkdir(parents=True, exist_ok=True)
    logger.info(f"✅ Dossier output prêt : {CHEMIN_OUTPUT}")

    return prerequis_ok


def extraire_texte_pdf(chemin_pdf: Path) -> str:
    """
    Extrait le texte brut d'un fichier PDF.

    Cette fonction utilise la bibliothèque pypdf pour lire chaque page
    du PDF et en extraire le contenu textuel.

    Args:
        chemin_pdf (Path): Chemin absolu vers le fichier PDF à traiter

    Returns:
        str: Le texte extrait du PDF, pages concaténées

    Raises:
        Exception: Si le PDF ne peut pas être lu ou est corrompu

    Note:
        Les PDFs scannés (images) ne contiendront pas de texte extractible.
        Dans ce cas, la fonction retournera une chaîne vide.
    """
    logger.info(f"📄 Extraction du texte depuis : {chemin_pdf.name}")

    # Initialisation de la variable qui contiendra tout le texte
    texte_complet = ""

    try:
        # Création d'un objet PdfReader pour lire le fichier
        # Ce reader permet d'accéder aux pages et métadonnées du PDF
        lecteur = PdfReader(chemin_pdf)

        # Récupération du nombre total de pages pour le logging
        nombre_pages = len(lecteur.pages)
        logger.info(f"   📑 Nombre de pages détectées : {nombre_pages}")

        # Itération sur chaque page du PDF
        # L'index commence à 0, mais on affiche à partir de 1 pour l'utilisateur
        for index_page, page in enumerate(lecteur.pages):
            # Extraction du texte de la page courante
            # extract_text() retourne le texte brut de la page
            texte_page = page.extract_text()

            # Vérification que du texte a bien été extrait
            # Certaines pages peuvent être des images sans texte
            if texte_page:
                # Ajout du texte de la page au texte complet
                # On ajoute un saut de ligne entre les pages
                texte_complet += texte_page + "\n"
            else:
                # Avertissement si une page n'a pas de texte
                logger.warning(f"   ⚠️ Page {index_page + 1} : aucun texte extrait (image ?)")

        # Calcul de statistiques sur le texte extrait
        nombre_caracteres = len(texte_complet)
        nombre_mots = len(texte_complet.split())

        logger.info(f"   ✅ Extraction réussie : {nombre_caracteres} caractères, ~{nombre_mots} mots")

    except Exception as erreur:
        # Gestion des erreurs lors de la lecture du PDF
        logger.error(f"   ❌ Erreur lors de l'extraction : {erreur}")
        raise

    return texte_complet


def nettoyer_reponse_json(reponse_brute: str) -> str:
    """
    Nettoie la réponse de l'API Gemini pour extraire le JSON valide.

    L'API Gemini peut parfois retourner le JSON enveloppé dans des balises
    markdown (```json ... ```) ou avec du texte supplémentaire.
    Cette fonction nettoie la réponse pour ne garder que le JSON.

    Args:
        reponse_brute (str): La réponse brute retournée par l'API Gemini

    Returns:
        str: Le JSON nettoyé, prêt à être parsé

    Example:
        >>> nettoyer_reponse_json("```json\\n{\\\"test\\\": 1}\\n```")
        '{"test": 1}'
    """
    # Copie de la réponse pour ne pas modifier l'original
    reponse = reponse_brute.strip()

    # Suppression des balises markdown de code JSON
    # Pattern 1 : ```json au début
    if reponse.startswith("```json"):
        reponse = reponse[7:]  # Supprime les 7 premiers caractères (```json)

    # Pattern 2 : ``` au début (sans spécification de langage)
    elif reponse.startswith("```"):
        reponse = reponse[3:]  # Supprime les 3 premiers caractères (```)

    # Pattern 3 : ``` à la fin
    if reponse.endswith("```"):
        reponse = reponse[:-3]  # Supprime les 3 derniers caractères (```)

    # Suppression des espaces et sauts de ligne en début/fin
    reponse = reponse.strip()

    # Recherche du JSON dans la réponse si elle contient du texte avant/après
    # On cherche le premier '{' et le dernier '}'
    debut_json = reponse.find('{')
    fin_json = reponse.rfind('}')

    # Si on a trouvé les accolades, on extrait le JSON
    if debut_json != -1 and fin_json != -1 and debut_json < fin_json:
        reponse = reponse[debut_json:fin_json + 1]

    return reponse


def appeler_gemini(texte_cv: str) -> dict:
    """
    Envoie le texte du CV à l'API Gemini et récupère les données structurées.

    Cette fonction :
    1. Configure le modèle Gemini (gemini-1.5-flash)
    2. Envoie le prompt système + le texte du CV
    3. Nettoie et parse la réponse JSON
    4. Retourne les données sous forme de dictionnaire Python

    Args:
        texte_cv (str): Le texte brut extrait du CV PDF

    Returns:
        dict: Les données du CV structurées selon le format JSON défini

    Raises:
        json.JSONDecodeError: Si la réponse n'est pas un JSON valide
        Exception: Si l'appel API échoue
    """
    logger.info("🤖 Appel à l'API Gemini en cours...")

    try:
        # =================================================================
        # ÉTAPE 1 : Configuration du modèle Gemini
        # =================================================================
        # On utilise le modèle gemini-1.5-flash pour sa rapidité
        # et son bon rapport qualité/coût pour l'extraction de données
        modele = genai.GenerativeModel('gemini-1.5-flash')

        # =================================================================
        # ÉTAPE 2 : Construction du prompt complet
        # =================================================================
        # Le prompt combine :
        # - Le prompt système (instructions pour l'IA)
        # - Le texte du CV à analyser
        prompt_complet = f"""{PROMPT_SYSTEME}

Voici le texte du CV à analyser :

{texte_cv}
"""

        # =================================================================
        # ÉTAPE 3 : Envoi de la requête à l'API
        # =================================================================
        # generate_content() envoie le prompt et attend la réponse
        # Cette opération peut prendre quelques secondes
        logger.info("   ⏳ Envoi de la requête...")
        reponse = modele.generate_content(prompt_complet)

        # =================================================================
        # ÉTAPE 4 : Extraction du texte de la réponse
        # =================================================================
        # L'objet réponse contient plusieurs attributs, on veut le texte
        reponse_texte = reponse.text
        logger.info("   ✅ Réponse reçue de Gemini")

        # =================================================================
        # ÉTAPE 5 : Nettoyage de la réponse
        # =================================================================
        # Suppression des éventuelles balises markdown autour du JSON
        json_nettoye = nettoyer_reponse_json(reponse_texte)

        # =================================================================
        # ÉTAPE 6 : Parsing du JSON
        # =================================================================
        # Conversion de la chaîne JSON en dictionnaire Python
        # json.loads() parse le JSON et retourne un dict/list
        try:
            donnees = json.loads(json_nettoye)
            logger.info("   ✅ JSON parsé avec succès")
        except json.JSONDecodeError as erreur_json:
            # En cas d'erreur de parsing, on affiche le JSON pour debug
            logger.error(f"   ❌ Erreur de parsing JSON : {erreur_json}")
            logger.error(f"   📝 Réponse brute : {reponse_texte[:500]}...")
            raise

        # =================================================================
        # ÉTAPE 7 : Validation basique de la structure
        # =================================================================
        # Vérification que les clés principales sont présentes
        cles_requises = ["profil", "resume_competences", "formations", "experiences"]
        for cle in cles_requises:
            if cle not in donnees:
                logger.warning(f"   ⚠️ Clé manquante dans la réponse : {cle}")

        return donnees

    except Exception as erreur:
        logger.error(f"   ❌ Erreur lors de l'appel API : {erreur}")
        raise


def generer_docx(donnees_cv: dict, nom_fichier_sortie: str):
    """
    Génère un fichier Word (.docx) à partir des données extraites.

    Cette fonction :
    1. Charge le template Word
    2. Prépare le contexte avec les données du CV + infos manager
    3. Injecte les données dans le template via Jinja2
    4. Sauvegarde le fichier dans le dossier output

    Args:
        donnees_cv (dict): Les données du CV extraites par Gemini
        nom_fichier_sortie (str): Le nom du fichier DOCX à générer

    Raises:
        Exception: Si le template ne peut pas être chargé ou le fichier sauvegardé
    """
    logger.info(f"📝 Génération du document Word : {nom_fichier_sortie}")

    try:
        # =================================================================
        # ÉTAPE 1 : Chargement du template Word
        # =================================================================
        # DocxTemplate charge le fichier .docx et permet l'injection Jinja2
        logger.info("   📂 Chargement du template...")
        template = DocxTemplate(CHEMIN_TEMPLATE)

        # =================================================================
        # ÉTAPE 2 : Préparation du contexte de rendu
        # =================================================================
        # Le contexte est un dictionnaire contenant toutes les variables
        # qui seront accessibles dans le template Word
        contexte = {
            # Données du profil (titre, années d'expérience)
            "profil": donnees_cv.get("profil", {}),

            # Résumé des compétences (techniques, métiers, fonctionnelles, langues)
            "resume_competences": donnees_cv.get("resume_competences", {}),

            # Formations (diplômes et certifications)
            "formations": donnees_cv.get("formations", {}),

            # Liste des expériences professionnelles
            "experiences": donnees_cv.get("experiences", []),

            # Informations du manager (constantes définies en haut du script)
            "manager": MANAGER_INFO
        }

        # Log des données pour vérification
        logger.info(f"   👤 Profil : {contexte['profil'].get('titre_cible', 'Non défini')}")
        logger.info(f"   📊 Expériences : {len(contexte['experiences'])} entrées")

        # =================================================================
        # ÉTAPE 3 : Injection des données dans le template
        # =================================================================
        # render() remplace toutes les variables Jinja2 par leurs valeurs
        # Les variables dans le template sont de la forme {{ variable }}
        logger.info("   🔄 Injection des données dans le template...")
        template.render(contexte)

        # =================================================================
        # ÉTAPE 4 : Sauvegarde du fichier généré
        # =================================================================
        # Construction du chemin complet vers le fichier de sortie
        chemin_sortie = CHEMIN_OUTPUT / nom_fichier_sortie

        # Sauvegarde du document Word
        template.save(chemin_sortie)

        logger.info(f"   ✅ Document sauvegardé : {chemin_sortie}")

    except Exception as erreur:
        logger.error(f"   ❌ Erreur lors de la génération : {erreur}")
        raise


def traiter_cv(chemin_pdf: Path):
    """
    Traite un fichier CV PDF de bout en bout.

    Cette fonction orchestre le processus complet :
    1. Extraction du texte du PDF
    2. Analyse par l'API Gemini
    3. Génération du document Word

    Args:
        chemin_pdf (Path): Chemin vers le fichier PDF à traiter

    Returns:
        bool: True si le traitement a réussi, False sinon
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"🚀 Traitement du CV : {chemin_pdf.name}")
    logger.info(f"{'='*60}")

    try:
        # =================================================================
        # ÉTAPE 1 : Extraction du texte du PDF
        # =================================================================
        texte_cv = extraire_texte_pdf(chemin_pdf)

        # Vérification qu'on a bien extrait du texte
        if not texte_cv.strip():
            logger.error("❌ Aucun texte n'a pu être extrait du PDF.")
            logger.error("   Le PDF est peut-être scanné (image) ou protégé.")
            return False

        # =================================================================
        # ÉTAPE 2 : Analyse par Gemini
        # =================================================================
        donnees_cv = appeler_gemini(texte_cv)

        # =================================================================
        # ÉTAPE 3 : Génération du document Word
        # =================================================================
        # Construction du nom du fichier de sortie
        # On remplace l'extension .pdf par .docx
        nom_sortie = chemin_pdf.stem + "_formatted.docx"

        generer_docx(donnees_cv, nom_sortie)

        logger.info(f"✅ CV traité avec succès : {nom_sortie}")
        return True

    except Exception as erreur:
        logger.error(f"❌ Échec du traitement : {erreur}")
        return False


def main():
    """
    Point d'entrée principal du script.

    Cette fonction :
    1. Affiche un message de bienvenue
    2. Charge et vérifie la configuration
    3. Vérifie les prérequis (dossiers, template)
    4. Liste et traite tous les PDFs du dossier input
    5. Affiche un récapitulatif des résultats
    """
    # =================================================================
    # Affichage du message de bienvenue
    # =================================================================
    print("\n" + "="*60)
    print("   CV FORMATTER ESN - Gemini Consulting")
    print("   Transformation automatique de CV PDF vers Word")
    print("="*60 + "\n")

    # =================================================================
    # Chargement de la configuration
    # =================================================================
    if not charger_configuration():
        logger.error("⛔ Arrêt du programme : configuration invalide")
        sys.exit(1)

    # =================================================================
    # Vérification des prérequis
    # =================================================================
    if not verifier_prerequis():
        logger.error("⛔ Arrêt du programme : prérequis manquants")
        sys.exit(1)

    # =================================================================
    # Recherche des fichiers PDF à traiter
    # =================================================================
    # glob("*.pdf") retourne tous les fichiers .pdf du dossier input
    fichiers_pdf = list(CHEMIN_INPUT.glob("*.pdf"))

    # Vérification qu'il y a des PDFs à traiter
    if not fichiers_pdf:
        logger.warning("⚠️ Aucun fichier PDF trouvé dans le dossier input/")
        logger.info("   Placez vos CVs au format PDF dans le dossier input/")
        sys.exit(0)

    logger.info(f"📁 {len(fichiers_pdf)} fichier(s) PDF trouvé(s) à traiter")

    # =================================================================
    # Traitement de chaque fichier PDF
    # =================================================================
    # Compteurs pour le récapitulatif
    succes = 0
    echecs = 0

    for chemin_pdf in fichiers_pdf:
        if traiter_cv(chemin_pdf):
            succes += 1
        else:
            echecs += 1

    # =================================================================
    # Affichage du récapitulatif
    # =================================================================
    print("\n" + "="*60)
    print("   RÉCAPITULATIF")
    print("="*60)
    print(f"   ✅ Succès : {succes}")
    print(f"   ❌ Échecs : {echecs}")
    print(f"   📁 Fichiers générés dans : {CHEMIN_OUTPUT}")
    print("="*60 + "\n")

    # Code de sortie basé sur les résultats
    # 0 = tout OK, 1 = au moins un échec
    sys.exit(0 if echecs == 0 else 1)


# =============================================================================
# POINT D'ENTRÉE DU SCRIPT
# =============================================================================
# Cette condition vérifie que le script est exécuté directement
# (et non importé comme module dans un autre script)

if __name__ == "__main__":
    main()
