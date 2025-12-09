# =============================================================================
# Dockerfile - CV Formatter ESN (Plateforme Web)
# =============================================================================
# Build multi-stage optimisé pour réduire la taille de l'image finale.
#
# Stage 1 (builder) : Installation des dépendances avec pip
# Stage 2 (runtime) : Image finale allégée avec Flask + Gunicorn
#
# Usage :
#   docker build -t cv-formatter .
#   docker run -d -p 5000:5000 \
#              -v $(pwd)/output:/app/output \
#              -v $(pwd)/template_gemini.docx:/app/template_gemini.docx \
#              --env-file .env \
#              --name cv-formatter \
#              cv-formatter
# =============================================================================

# =============================================================================
# STAGE 1 : BUILDER
# =============================================================================
# Ce stage installe les dépendances Python dans un environnement virtuel.
# Les fichiers compilés seront copiés dans le stage final.

FROM python:3.11-slim AS builder

# Définition du répertoire de travail pour le build
WORKDIR /build

# Variables d'environnement pour optimiser pip
# - PIP_NO_CACHE_DIR : Désactive le cache pip pour réduire la taille
# - PIP_DISABLE_PIP_VERSION_CHECK : Évite les vérifications de mise à jour
# - PYTHONDONTWRITEBYTECODE : N'écrit pas les fichiers .pyc
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

# Création d'un environnement virtuel Python
# Cet environnement sera copié dans l'image finale
RUN python -m venv /opt/venv

# Activation de l'environnement virtuel pour les commandes suivantes
ENV PATH="/opt/venv/bin:$PATH"

# Copie du fichier des dépendances
COPY requirements.txt .

# Installation des dépendances Python dans l'environnement virtuel
RUN pip install --upgrade pip && \
    pip install -r requirements.txt


# =============================================================================
# STAGE 2 : RUNTIME
# =============================================================================
# Ce stage crée l'image finale allégée contenant uniquement :
# - Python runtime
# - Les dépendances installées (Flask, Gunicorn, etc.)
# - Le code de l'application web

FROM python:3.11-slim AS runtime

# Métadonnées de l'image
LABEL maintainer="Cherif Elkhodja <cherif.elkhodja@geminiconsulting.fr>"
LABEL description="CV Formatter ESN - Plateforme Web de transformation de CV"
LABEL version="2.0.0"

# Variables d'environnement pour l'exécution
# - PYTHONDONTWRITEBYTECODE : Évite la création de fichiers .pyc
# - PYTHONUNBUFFERED : Assure que les logs sont affichés en temps réel
# - PYTHONFAULTHANDLER : Affiche le traceback en cas de crash
# - FLASK_ENV : Mode de Flask (production par défaut)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    FLASK_ENV=production

# Définition du répertoire de travail de l'application
WORKDIR /app

# Copie de l'environnement virtuel depuis le stage builder
# Cela évite de réinstaller les dépendances dans l'image finale
COPY --from=builder /opt/venv /opt/venv

# Activation de l'environnement virtuel
ENV PATH="/opt/venv/bin:$PATH"

# Création des dossiers nécessaires
# - uploads : Fichiers PDF temporaires uploadés
# - output : CVs Word générés
RUN mkdir -p /app/uploads /app/output

# Copie des fichiers de l'application
COPY app.py .
COPY templates/ ./templates/
COPY static/ ./static/

# Copie de la documentation (optionnel, utile pour le debug)
COPY MEMORY.md .

# Note : Le fichier template_gemini.docx n'est PAS copié dans l'image
# Il doit être monté en volume lors de l'exécution pour permettre
# à l'utilisateur de le personnaliser facilement.

# Note : Le fichier .env n'est PAS copié dans l'image pour des raisons
# de sécurité. Il contient la clé API et doit être fourni via --env-file
# ou variables d'environnement.

# Exposition du port de l'application web
EXPOSE 5000

# Health check pour Docker/Kubernetes
# Vérifie que l'application répond correctement
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/status')" || exit 1

# Définition du point d'entrée avec Gunicorn (serveur WSGI de production)
# - workers=2 : Nombre de workers (ajuster selon les ressources)
# - bind=0.0.0.0:5000 : Écoute sur toutes les interfaces, port 5000
# - timeout=120 : Timeout pour les requêtes longues (traitement IA)
# - access-logfile=- : Logs d'accès sur stdout
CMD ["gunicorn", "--workers=2", "--bind=0.0.0.0:5000", "--timeout=120", "--access-logfile=-", "app:app"]
