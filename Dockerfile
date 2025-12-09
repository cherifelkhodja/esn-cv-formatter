# =============================================================================
# Dockerfile - CV Formatter ESN
# =============================================================================
# Build multi-stage optimisé pour réduire la taille de l'image finale.
#
# Stage 1 (builder) : Installation des dépendances avec pip
# Stage 2 (runtime) : Image finale allégée avec seulement le nécessaire
#
# Usage :
#   docker build -t cv-formatter .
#   docker run --rm -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output \
#              -v $(pwd)/template_gemini.docx:/app/template_gemini.docx \
#              --env-file .env cv-formatter
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
# --no-compile évite la compilation en bytecode (sera fait au runtime)
RUN pip install --upgrade pip && \
    pip install -r requirements.txt


# =============================================================================
# STAGE 2 : RUNTIME
# =============================================================================
# Ce stage crée l'image finale allégée contenant uniquement :
# - Python runtime
# - Les dépendances installées
# - Le code de l'application

FROM python:3.11-slim AS runtime

# Métadonnées de l'image
LABEL maintainer="Cherif Elkhodja <cherif.elkhodja@geminiconsulting.fr>"
LABEL description="CV Formatter ESN - Transformation automatique de CV PDF vers Word"
LABEL version="1.0.0"

# Variables d'environnement pour l'exécution Python
# - PYTHONDONTWRITEBYTECODE : Évite la création de fichiers .pyc
# - PYTHONUNBUFFERED : Assure que les logs sont affichés en temps réel
# - PYTHONFAULTHANDLER : Affiche le traceback en cas de crash
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1

# Définition du répertoire de travail de l'application
WORKDIR /app

# Copie de l'environnement virtuel depuis le stage builder
# Cela évite de réinstaller les dépendances dans l'image finale
COPY --from=builder /opt/venv /opt/venv

# Activation de l'environnement virtuel
ENV PATH="/opt/venv/bin:$PATH"

# Création des dossiers input et output
# Ces dossiers seront montés en volumes lors de l'exécution
RUN mkdir -p /app/input /app/output

# Copie du script principal Python
COPY main.py .

# Copie de la documentation (optionnel, utile pour le debug)
COPY MEMORY.md .

# Note : Le fichier template_gemini.docx n'est PAS copié dans l'image
# Il doit être monté en volume lors de l'exécution pour permettre
# à l'utilisateur de le personnaliser facilement.

# Note : Le fichier .env n'est PAS copié dans l'image pour des raisons
# de sécurité. Il contient la clé API et doit être fourni via --env-file
# ou variables d'environnement.

# Définition du point d'entrée
# Le script main.py sera exécuté au démarrage du conteneur
CMD ["python", "main.py"]
