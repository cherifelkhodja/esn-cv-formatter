# =============================================================================
# Makefile - CV Formatter ESN
# =============================================================================
# Commandes pratiques pour gérer l'application Docker
#
# Usage : make <commande>
# Aide  : make help
# =============================================================================

# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------
IMAGE_NAME = cv-formatter
CONTAINER_NAME = cv-formatter
PORT = 8080

# Couleurs pour l'affichage
GREEN = \033[0;32m
YELLOW = \033[0;33m
RED = \033[0;31m
NC = \033[0m # No Color

# -----------------------------------------------------------------------------
# Commandes principales
# -----------------------------------------------------------------------------

.PHONY: help build up up-build down restart logs shell status clean

## help: Affiche cette aide
help:
	@echo ""
	@echo "$(GREEN)CV Formatter ESN - Commandes disponibles$(NC)"
	@echo "=========================================="
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/## //' | awk 'BEGIN {FS = ": "}; {printf "$(YELLOW)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""

## build: Construit l'image Docker
build:
	@echo "$(GREEN)Construction de l'image Docker...$(NC)"
	docker build -t $(IMAGE_NAME) .
	@echo "$(GREEN)Image construite avec succès !$(NC)"

## up: Démarre le conteneur en arrière-plan
up:
	@echo "$(GREEN)Démarrage du conteneur...$(NC)"
	@docker run -d \
		-p $(PORT):5000 \
		-v $(PWD)/output:/app/output \
		-v $(PWD)/template_gemini.docx:/app/template_gemini.docx \
		--env-file .env \
		--name $(CONTAINER_NAME) \
		$(IMAGE_NAME)
	@echo "$(GREEN)Application disponible sur http://localhost:$(PORT)$(NC)"

## up-build: Construit l'image et démarre le conteneur
up-build: build up

## down: Arrête et supprime le conteneur
down:
	@echo "$(YELLOW)Arrêt du conteneur...$(NC)"
	@docker stop $(CONTAINER_NAME) 2>/dev/null || true
	@docker rm $(CONTAINER_NAME) 2>/dev/null || true
	@echo "$(GREEN)Conteneur arrêté$(NC)"

## restart: Redémarre le conteneur
restart: down up

## logs: Affiche les logs en temps réel
logs:
	@docker logs -f $(CONTAINER_NAME)

## shell: Ouvre un shell dans le conteneur
shell:
	@docker exec -it $(CONTAINER_NAME) /bin/bash

## status: Affiche le statut du conteneur
status:
	@echo "$(GREEN)Statut du conteneur :$(NC)"
	@docker ps -a --filter "name=$(CONTAINER_NAME)" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
	@echo ""
	@echo "$(GREEN)Health check :$(NC)"
	@curl -s http://localhost:$(PORT)/status 2>/dev/null | python3 -m json.tool || echo "$(RED)Application non accessible$(NC)"

# -----------------------------------------------------------------------------
# Commandes de développement
# -----------------------------------------------------------------------------

.PHONY: dev build-dev clean-images

## dev: Lance en mode développement (hot reload)
dev:
	@echo "$(GREEN)Démarrage en mode développement...$(NC)"
	@docker run -it --rm \
		-p $(PORT):5000 \
		-v $(PWD)/output:/app/output \
		-v $(PWD)/template_gemini.docx:/app/template_gemini.docx \
		-v $(PWD)/app.py:/app/app.py \
		-v $(PWD)/templates:/app/templates \
		-v $(PWD)/static:/app/static \
		-e FLASK_DEBUG=true \
		--env-file .env \
		--name $(CONTAINER_NAME)-dev \
		$(IMAGE_NAME) python app.py

## rebuild: Reconstruit et redémarre
rebuild: down build up

## clean: Supprime le conteneur et l'image
clean: down
	@echo "$(YELLOW)Suppression de l'image...$(NC)"
	@docker rmi $(IMAGE_NAME) 2>/dev/null || true
	@echo "$(GREEN)Nettoyage terminé$(NC)"

## clean-all: Supprime tout (conteneur, image, fichiers générés)
clean-all: clean
	@echo "$(YELLOW)Suppression des fichiers générés...$(NC)"
	@rm -f output/*.docx
	@rm -f uploads/*.pdf
	@echo "$(GREEN)Nettoyage complet terminé$(NC)"

# -----------------------------------------------------------------------------
# Commandes d'initialisation
# -----------------------------------------------------------------------------

.PHONY: init check

## init: Initialise le projet (copie .env.example)
init:
	@echo "$(GREEN)Initialisation du projet...$(NC)"
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(YELLOW)Fichier .env créé. Éditez-le pour ajouter votre clé API Gemini.$(NC)"; \
	else \
		echo "$(YELLOW)Fichier .env déjà existant$(NC)"; \
	fi
	@mkdir -p output uploads
	@echo ""
	@echo "$(GREEN)Prochaines étapes :$(NC)"
	@echo "  1. Éditez .env et ajoutez votre GEMINI_API_KEY"
	@echo "  2. Placez votre template Word : template_gemini.docx"
	@echo "  3. Lancez : make build && make up"

## check: Vérifie la configuration
check:
	@echo "$(GREEN)Vérification de la configuration...$(NC)"
	@echo ""
	@echo "Fichier .env :"
	@if [ -f .env ]; then echo "  $(GREEN)✓ Présent$(NC)"; else echo "  $(RED)✗ Manquant$(NC) - Lancez 'make init'"; fi
	@echo ""
	@echo "Template Word :"
	@if [ -f template_gemini.docx ]; then echo "  $(GREEN)✓ Présent$(NC)"; else echo "  $(RED)✗ Manquant$(NC) - Placez votre template_gemini.docx"; fi
	@echo ""
	@echo "Image Docker :"
	@if docker images $(IMAGE_NAME) | grep -q $(IMAGE_NAME); then echo "  $(GREEN)✓ Construite$(NC)"; else echo "  $(YELLOW)○ Non construite$(NC) - Lancez 'make build'"; fi
	@echo ""
	@echo "Conteneur :"
	@if docker ps --filter "name=$(CONTAINER_NAME)" | grep -q $(CONTAINER_NAME); then \
		echo "  $(GREEN)✓ En cours d'exécution$(NC)"; \
	elif docker ps -a --filter "name=$(CONTAINER_NAME)" | grep -q $(CONTAINER_NAME); then \
		echo "  $(YELLOW)○ Arrêté$(NC) - Lancez 'make up'"; \
	else \
		echo "  $(YELLOW)○ Non créé$(NC) - Lancez 'make up'"; \
	fi
