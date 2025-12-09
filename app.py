#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
CV Formatter ESN - Plateforme Web
=============================================================================
Application web Flask permettant de transformer des CVs au format PDF en
documents Word (.docx) standardisés selon le format de l'ESN Gemini Consulting.

L'extraction intelligente des données est réalisée via l'API Google Gemini
(modèle gemini-2.5-flash-lite).

Auteur: Cherif Elkhodja
Version: 2.0.0
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

# Bibliothèque standard Python pour la génération d'UUID
import uuid

# Bibliothèque standard Python pour la gestion du temps
from datetime import datetime

# Framework web Flask et ses utilitaires
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_file,
    flash,
    redirect,
    url_for
)

# Sécurisation des noms de fichiers uploadés
from werkzeug.utils import secure_filename

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
# CHARGEMENT DE LA CONFIGURATION
# =============================================================================
# Chargement des variables d'environnement depuis le fichier .env

# Chemin racine de l'application
CHEMIN_RACINE = Path(__file__).parent

# Chargement du fichier .env
load_dotenv(CHEMIN_RACINE / ".env", override=True)


# =============================================================================
# CRÉATION DE L'APPLICATION FLASK
# =============================================================================

app = Flask(__name__)

# Clé secrète pour les sessions Flask (génération aléatoire si non définie)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24).hex())


# =============================================================================
# CONSTANTES - Chemins et Configuration
# =============================================================================

# Dossier pour les fichiers uploadés (CVs PDF)
DOSSIER_UPLOAD = CHEMIN_RACINE / "uploads"

# Dossier pour les fichiers générés (CVs Word)
DOSSIER_OUTPUT = CHEMIN_RACINE / "output"

# Chemin vers le template Word
CHEMIN_TEMPLATE = CHEMIN_RACINE / "template_gemini.docx"

# Extensions de fichiers autorisées pour l'upload
EXTENSIONS_AUTORISEES = {'pdf'}

# Taille maximale des fichiers (16 Mo)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Création des dossiers s'ils n'existent pas
DOSSIER_UPLOAD.mkdir(parents=True, exist_ok=True)
DOSSIER_OUTPUT.mkdir(parents=True, exist_ok=True)


# =============================================================================
# INFORMATIONS DU MANAGER (Variables statiques)
# =============================================================================
# Ces informations seront injectées dans chaque CV généré.

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

PROMPT_SYSTEME = """
Tu es un expert en recrutement IT. Ta mission est de convertir le texte brut d'un CV en une structure JSON stricte.

RÈGLES IMPORTANTES :
1. Langue : FRANÇAIS uniquement.
2. Anonymisation : NE JAMAIS inclure l'email, le téléphone ou l'adresse du candidat.
3. Synthèse : Reformule les tâches pour qu'elles soient professionnelles et concises.
4. CONCISION : Va à l'essentiel, évite les listes trop longues.
5. FORMAT DES DATES : "Mois Année à Mois Année" (ex: "Janvier 2020 à Décembre 2022") ou "Depuis Mois Année" pour le poste actuel.

RÈGLES POUR LES COMPÉTENCES :
- Compétences techniques : Utilise des catégories SIMPLES (Langages, Frameworks, Base de données, Cloud, Outils, DevOps, etc.). Maximum 5-6 catégories.
- Compétences métiers : UNIQUEMENT les secteurs d'activité majeurs (ex: Banque, Assurance, Retail). Maximum 2-3 items. Laisser vide [] si non pertinent.
- Compétences fonctionnelles : UNIQUEMENT les savoir-faire organisationnels clés (ex: Gestion de projet, Agilité). Maximum 2-3 items. Laisser vide [] si non pertinent.

FORMAT JSON ATTENDU :
{
  "profil": {
    "titre_cible": "String",
    "annees_experience": "String (ex: 5 ans)"
  },
  "resume_competences": {
    "techniques": {
       "Langages": "Python, Java, JavaScript",
       "Frameworks": "React, Spring Boot",
       "Base de données": "PostgreSQL, MongoDB",
       "Cloud": "AWS, Azure"
    },
    "metiers": ["Banque", "Assurance"],
    "fonctionnelles": ["Gestion de projet", "Méthode Agile"],
    "langues": ["Français : Natif", "Anglais : Courant"]
  },
  "formations": {
    "diplomes": [ {"annee": "2015", "libelle": "Master Informatique"} ],
    "certifications": [ {"annee": "2020", "libelle": "AWS Solutions Architect"} ]
  },
  "experiences": [
    {
      "client": "Nom du client ou entreprise",
      "periode": "Janvier 2020 à Décembre 2022 (ou 'Depuis Janvier 2023' si poste actuel)",
      "titre": "Poste occupé",
      "contexte": "Description courte du contexte (1-2 phrases)",
      "taches": {
        "Réalisations": ["Tâche 1", "Tâche 2", "Tâche 3"]
      },
      "environnement_technique": "Technologies utilisées séparées par des virgules"
    }
  ]
}

Réponds UNIQUEMENT avec le JSON, sans texte avant ou après.
"""


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================


def fichier_autorise(nom_fichier: str) -> bool:
    """
    Vérifie si l'extension du fichier est autorisée.

    Args:
        nom_fichier (str): Nom du fichier à vérifier

    Returns:
        bool: True si l'extension est autorisée, False sinon
    """
    # Vérifie la présence d'un point et l'extension
    return '.' in nom_fichier and \
           nom_fichier.rsplit('.', 1)[1].lower() in EXTENSIONS_AUTORISEES


def verifier_configuration() -> dict:
    """
    Vérifie que la configuration est valide.

    Returns:
        dict: Statut de la configuration avec les clés 'valide' et 'erreurs'
    """
    erreurs = []

    # Vérification de la clé API Gemini
    cle_api = os.getenv("GEMINI_API_KEY")
    if not cle_api or cle_api == "votre_cle_api_gemini_ici":
        erreurs.append("Clé API Gemini non configurée")

    # Vérification du template Word
    if not CHEMIN_TEMPLATE.exists():
        erreurs.append("Template Word (template_gemini.docx) non trouvé")

    return {
        "valide": len(erreurs) == 0,
        "erreurs": erreurs
    }


def configurer_gemini() -> bool:
    """
    Configure l'API Gemini avec la clé fournie.

    Returns:
        bool: True si la configuration a réussi, False sinon
    """
    cle_api = os.getenv("GEMINI_API_KEY")
    if not cle_api or cle_api == "votre_cle_api_gemini_ici":
        return False

    try:
        genai.configure(api_key=cle_api)
        return True
    except Exception as erreur:
        logger.error(f"Erreur configuration Gemini: {erreur}")
        return False


def extraire_texte_pdf(chemin_pdf: Path) -> str:
    """
    Extrait le texte brut d'un fichier PDF.

    Args:
        chemin_pdf (Path): Chemin absolu vers le fichier PDF à traiter

    Returns:
        str: Le texte extrait du PDF, pages concaténées

    Raises:
        Exception: Si le PDF ne peut pas être lu ou est corrompu
    """
    logger.info(f"Extraction du texte depuis : {chemin_pdf.name}")

    texte_complet = ""

    try:
        # Création du lecteur PDF
        lecteur = PdfReader(chemin_pdf)
        nombre_pages = len(lecteur.pages)
        logger.info(f"Nombre de pages détectées : {nombre_pages}")

        # Extraction page par page
        for index_page, page in enumerate(lecteur.pages):
            texte_page = page.extract_text()
            if texte_page:
                texte_complet += texte_page + "\n"
            else:
                logger.warning(f"Page {index_page + 1} : aucun texte extrait")

        logger.info(f"Extraction réussie : {len(texte_complet)} caractères")

    except Exception as erreur:
        logger.error(f"Erreur lors de l'extraction : {erreur}")
        raise

    return texte_complet


def nettoyer_reponse_json(reponse_brute: str) -> str:
    """
    Nettoie la réponse de l'API Gemini pour extraire le JSON valide.

    Args:
        reponse_brute (str): La réponse brute retournée par l'API Gemini

    Returns:
        str: Le JSON nettoyé, prêt à être parsé
    """
    reponse = reponse_brute.strip()

    # Suppression des balises markdown
    if reponse.startswith("```json"):
        reponse = reponse[7:]
    elif reponse.startswith("```"):
        reponse = reponse[3:]

    if reponse.endswith("```"):
        reponse = reponse[:-3]

    reponse = reponse.strip()

    # Recherche du JSON dans la réponse
    debut_json = reponse.find('{')
    fin_json = reponse.rfind('}')

    if debut_json != -1 and fin_json != -1 and debut_json < fin_json:
        reponse = reponse[debut_json:fin_json + 1]

    return reponse


def appeler_gemini(texte_cv: str) -> dict:
    """
    Envoie le texte du CV à l'API Gemini et récupère les données structurées.

    Args:
        texte_cv (str): Le texte brut extrait du CV PDF

    Returns:
        dict: Les données du CV structurées selon le format JSON défini

    Raises:
        json.JSONDecodeError: Si la réponse n'est pas un JSON valide
        Exception: Si l'appel API échoue
    """
    logger.info("Appel à l'API Gemini...")

    try:
        # Configuration du modèle
        modele = genai.GenerativeModel('gemini-2.5-flash-lite')

        # Construction du prompt complet
        prompt_complet = f"""{PROMPT_SYSTEME}

Voici le texte du CV à analyser :

{texte_cv}
"""

        # Envoi de la requête
        logger.info("Envoi de la requête à Gemini...")
        reponse = modele.generate_content(prompt_complet)

        # Extraction et parsing du JSON
        reponse_texte = reponse.text
        logger.info("Réponse reçue de Gemini")

        json_nettoye = nettoyer_reponse_json(reponse_texte)

        try:
            donnees = json.loads(json_nettoye)
            logger.info("JSON parsé avec succès")
        except json.JSONDecodeError as erreur_json:
            logger.error(f"Erreur de parsing JSON : {erreur_json}")
            logger.error(f"Réponse brute : {reponse_texte[:500]}...")
            raise

        return donnees

    except Exception as erreur:
        logger.error(f"Erreur lors de l'appel API : {erreur}")
        raise


def generer_docx(donnees_cv: dict, nom_fichier_sortie: str) -> Path:
    """
    Génère un fichier Word (.docx) à partir des données extraites.

    Args:
        donnees_cv (dict): Les données du CV extraites par Gemini
        nom_fichier_sortie (str): Le nom du fichier DOCX à générer

    Returns:
        Path: Chemin vers le fichier généré

    Raises:
        Exception: Si le template ne peut pas être chargé ou le fichier sauvegardé
    """
    logger.info(f"Génération du document Word : {nom_fichier_sortie}")

    try:
        # Chargement du template
        template = DocxTemplate(CHEMIN_TEMPLATE)

        # Préparation du contexte
        contexte = {
            "profil": donnees_cv.get("profil", {}),
            "resume_competences": donnees_cv.get("resume_competences", {}),
            "formations": donnees_cv.get("formations", {}),
            "experiences": donnees_cv.get("experiences", []),
            "manager": MANAGER_INFO
        }

        # Injection des données
        template.render(contexte)

        # Sauvegarde
        chemin_sortie = DOSSIER_OUTPUT / nom_fichier_sortie
        template.save(chemin_sortie)

        logger.info(f"Document sauvegardé : {chemin_sortie}")
        return chemin_sortie

    except Exception as erreur:
        logger.error(f"Erreur lors de la génération : {erreur}")
        raise


def traiter_cv(chemin_pdf: Path) -> dict:
    """
    Traite un fichier CV PDF de bout en bout.

    Args:
        chemin_pdf (Path): Chemin vers le fichier PDF à traiter

    Returns:
        dict: Résultat du traitement avec 'succes', 'message' et 'fichier_sortie'
    """
    logger.info(f"Traitement du CV : {chemin_pdf.name}")

    try:
        # Extraction du texte
        texte_cv = extraire_texte_pdf(chemin_pdf)

        if not texte_cv.strip():
            return {
                "succes": False,
                "message": "Aucun texte n'a pu être extrait du PDF. Le fichier est peut-être scanné (image) ou protégé.",
                "fichier_sortie": None
            }

        # Analyse par Gemini
        donnees_cv = appeler_gemini(texte_cv)

        # Génération du document Word
        nom_sortie = chemin_pdf.stem + "_formatted.docx"
        chemin_sortie = generer_docx(donnees_cv, nom_sortie)

        return {
            "succes": True,
            "message": "CV traité avec succès",
            "fichier_sortie": nom_sortie,
            "chemin_complet": str(chemin_sortie)
        }

    except Exception as erreur:
        logger.error(f"Échec du traitement : {erreur}")
        return {
            "succes": False,
            "message": f"Erreur lors du traitement : {str(erreur)}",
            "fichier_sortie": None
        }


# =============================================================================
# ROUTES FLASK
# =============================================================================


@app.route('/')
def index():
    """
    Page d'accueil de l'application.
    Affiche le formulaire d'upload et la liste des CVs générés.
    """
    # Vérification de la configuration
    config = verifier_configuration()

    # Liste des fichiers générés (triés par date, plus récent en premier)
    fichiers_generes = []
    if DOSSIER_OUTPUT.exists():
        for fichier in sorted(DOSSIER_OUTPUT.glob("*.docx"), key=os.path.getmtime, reverse=True):
            fichiers_generes.append({
                "nom": fichier.name,
                "date": datetime.fromtimestamp(fichier.stat().st_mtime).strftime("%d/%m/%Y %H:%M"),
                "taille": f"{fichier.stat().st_size / 1024:.1f} Ko"
            })

    return render_template(
        'index.html',
        config=config,
        fichiers_generes=fichiers_generes,
        manager=MANAGER_INFO
    )


@app.route('/upload', methods=['POST'])
def upload_fichier():
    """
    Endpoint pour l'upload et le traitement d'un CV PDF.
    Retourne une réponse JSON avec le résultat du traitement.
    """
    # Vérification de la configuration
    config = verifier_configuration()
    if not config["valide"]:
        return jsonify({
            "succes": False,
            "message": f"Configuration invalide : {', '.join(config['erreurs'])}"
        }), 400

    # Configuration de Gemini
    if not configurer_gemini():
        return jsonify({
            "succes": False,
            "message": "Impossible de configurer l'API Gemini"
        }), 500

    # Vérification de la présence du fichier
    if 'fichier' not in request.files:
        return jsonify({
            "succes": False,
            "message": "Aucun fichier envoyé"
        }), 400

    fichier = request.files['fichier']

    # Vérification du nom de fichier
    if fichier.filename == '':
        return jsonify({
            "succes": False,
            "message": "Aucun fichier sélectionné"
        }), 400

    # Vérification de l'extension
    if not fichier_autorise(fichier.filename):
        return jsonify({
            "succes": False,
            "message": "Seuls les fichiers PDF sont acceptés"
        }), 400

    try:
        # Sécurisation du nom de fichier
        nom_securise = secure_filename(fichier.filename)

        # Ajout d'un UUID pour éviter les collisions
        nom_unique = f"{uuid.uuid4().hex[:8]}_{nom_securise}"
        chemin_upload = DOSSIER_UPLOAD / nom_unique

        # Sauvegarde du fichier uploadé
        fichier.save(chemin_upload)
        logger.info(f"Fichier uploadé : {chemin_upload}")

        # Traitement du CV
        resultat = traiter_cv(chemin_upload)

        # Suppression du fichier uploadé après traitement
        if chemin_upload.exists():
            chemin_upload.unlink()
            logger.info(f"Fichier temporaire supprimé : {chemin_upload}")

        return jsonify(resultat)

    except Exception as erreur:
        logger.error(f"Erreur lors de l'upload : {erreur}")
        return jsonify({
            "succes": False,
            "message": f"Erreur lors du traitement : {str(erreur)}"
        }), 500


@app.route('/telecharger/<nom_fichier>')
def telecharger_fichier(nom_fichier: str):
    """
    Endpoint pour télécharger un CV généré.

    Args:
        nom_fichier (str): Nom du fichier à télécharger
    """
    # Sécurisation du nom de fichier
    nom_securise = secure_filename(nom_fichier)
    chemin_fichier = DOSSIER_OUTPUT / nom_securise

    # Vérification de l'existence
    if not chemin_fichier.exists():
        flash("Fichier non trouvé", "error")
        return redirect(url_for('index'))

    # Envoi du fichier
    return send_file(
        chemin_fichier,
        as_attachment=True,
        download_name=nom_securise
    )


@app.route('/supprimer/<nom_fichier>', methods=['POST'])
def supprimer_fichier(nom_fichier: str):
    """
    Endpoint pour supprimer un CV généré.

    Args:
        nom_fichier (str): Nom du fichier à supprimer
    """
    # Sécurisation du nom de fichier
    nom_securise = secure_filename(nom_fichier)
    chemin_fichier = DOSSIER_OUTPUT / nom_securise

    # Vérification et suppression
    if chemin_fichier.exists():
        chemin_fichier.unlink()
        logger.info(f"Fichier supprimé : {chemin_fichier}")
        return jsonify({"succes": True, "message": "Fichier supprimé"})

    return jsonify({"succes": False, "message": "Fichier non trouvé"}), 404


@app.route('/status')
def status():
    """
    Endpoint pour vérifier le statut de l'application.
    Utile pour les health checks Docker/Kubernetes.
    """
    config = verifier_configuration()
    return jsonify({
        "status": "ok" if config["valide"] else "degraded",
        "configuration": config,
        "version": "2.0.0"
    })


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

if __name__ == "__main__":
    # Affichage du message de démarrage
    print("\n" + "="*60)
    print("   CV FORMATTER ESN - Plateforme Web")
    print("   Gemini Consulting")
    print("="*60)

    # Vérification de la configuration
    config = verifier_configuration()
    if not config["valide"]:
        print("\n⚠️  ATTENTION - Configuration incomplète :")
        for erreur in config["erreurs"]:
            print(f"   - {erreur}")
        print("\nL'application démarre mais certaines fonctionnalités seront désactivées.")

    print(f"\n🚀 Démarrage du serveur sur http://0.0.0.0:5000")
    print("="*60 + "\n")

    # Lancement du serveur de développement
    # En production, utiliser gunicorn
    app.run(host='0.0.0.0', port=5000, debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
