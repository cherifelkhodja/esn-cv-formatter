# MEMORY.md - Journal de Bord du Projet CV Formatter

> **Dernière mise à jour** : 2025-12-09
> **Version** : 2.0.0 (Plateforme Web)
> **Auteur** : Cherif Elkhodja

---

## 📋 Description du Projet

Plateforme web permettant de transformer des CVs au format PDF en documents Word (.docx) standardisés selon le format de l'ESN Gemini Consulting. L'extraction intelligente des données est réalisée via l'API Google Gemini.

**Nouveautés v2.0 :**
- Interface web moderne avec Bootstrap 5
- Upload drag & drop
- Gestion des fichiers générés
- Serveur de production Gunicorn

---

## 🏗️ Architecture Technique

```
/app
├── app.py                  # Application Flask principale
├── templates/
│   ├── base.html           # Layout de base (navbar, footer)
│   └── index.html          # Page d'accueil avec upload
├── static/
│   └── css/
│       └── style.css       # Styles personnalisés
├── uploads/                # Fichiers PDF temporaires (auto-supprimés)
├── output/                 # CVs Word générés
├── template_gemini.docx    # Template Word (fourni par l'utilisateur)
├── requirements.txt        # Dépendances Python
├── Dockerfile              # Configuration Docker multi-stage
├── .env.example            # Exemple de configuration
└── MEMORY.md               # Ce fichier de documentation
```

### Stack Technique

| Composant | Version/Outil | Rôle |
|-----------|---------------|------|
| Python | 3.11 | Langage principal |
| Flask | 3.0+ | Framework web |
| Gunicorn | 21.0+ | Serveur WSGI production |
| Bootstrap | 5.3 | Framework CSS |
| google-generativeai | Latest | API Gemini pour extraction IA |
| docxtpl | Latest | Injection données dans template Word |
| pypdf | Latest | Extraction texte des PDF |
| python-dotenv | Latest | Gestion variables d'environnement |
| Docker | Multi-stage | Conteneurisation |

### Flux de Traitement

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│ Upload PDF  │───>│ Extraction   │───>│ API Gemini  │───>│ Génération   │
│ (Web)       │    │ Texte (pypdf)│    │ (JSON)      │    │ DOCX         │
└─────────────┘    └──────────────┘    └─────────────┘    └──────────────┘
                                                                │
                                              ┌─────────────────┘
                                              ▼
                                       ┌──────────────┐
                                       │ Téléchargement│
                                       │ (Web)        │
                                       └──────────────┘
```

### Routes API

| Route | Méthode | Description |
|-------|---------|-------------|
| `/` | GET | Page d'accueil avec formulaire d'upload |
| `/upload` | POST | Endpoint pour l'upload et traitement du CV |
| `/telecharger/<nom>` | GET | Téléchargement d'un CV généré |
| `/supprimer/<nom>` | POST | Suppression d'un CV généré |
| `/status` | GET | Health check (configuration, version) |

---

## 🤖 Prompt Système Gemini (v1.0)

```
Tu es un expert en recrutement IT. Ta mission est de convertir le texte brut d'un CV en une structure JSON stricte.

RÈGLES IMPORTANTES :
1. Langue : FRANÇAIS uniquement.
2. Anonymisation : NE JAMAIS inclure l'email, le téléphone ou l'adresse du candidat.
3. Synthèse : Reformule les tâches pour qu'elles soient professionnelles.
4. Tri : "Compétences Métiers" concerne la connaissance d'un secteur (Banque, Assurance, Retail...).
   "Compétences Fonctionnelles" concerne le savoir-faire organisationnel (Gestion de projet, Agilité, Management).
   Ne remplis ces listes que si c'est pertinent.

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
```

---

## 🐳 Commandes Docker

### Construction de l'image

```bash
docker build -t cv-formatter .
```

### Lancement du conteneur (Production)

```bash
# Démarrage en arrière-plan
docker run -d \
  -p 5000:5000 \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/template_gemini.docx:/app/template_gemini.docx \
  --env-file .env \
  --name cv-formatter \
  cv-formatter

# Accéder à l'application : http://localhost:5000
```

### Lancement en mode développement

```bash
# Avec le serveur Flask de développement (hot reload)
docker run -it --rm \
  -p 5000:5000 \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/template_gemini.docx:/app/template_gemini.docx \
  -v $(pwd)/app.py:/app/app.py \
  -v $(pwd)/templates:/app/templates \
  -v $(pwd)/static:/app/static \
  -e FLASK_DEBUG=true \
  --env-file .env \
  cv-formatter python app.py
```

### Gestion du conteneur

```bash
# Voir les logs
docker logs -f cv-formatter

# Arrêter le conteneur
docker stop cv-formatter

# Supprimer le conteneur
docker rm cv-formatter

# Reconstruire et relancer
docker stop cv-formatter && docker rm cv-formatter && \
docker build -t cv-formatter . && \
docker run -d -p 5000:5000 \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/template_gemini.docx:/app/template_gemini.docx \
  --env-file .env \
  --name cv-formatter \
  cv-formatter
```

### Workflow complet

```bash
# 1. Créer le fichier .env à partir de l'exemple
cp .env.example .env

# 2. Éditer .env et ajouter votre clé API Gemini
nano .env

# 3. Placer le template Word
cp votre_template.docx template_gemini.docx

# 4. Construire et lancer
docker build -t cv-formatter .
docker run -d -p 5000:5000 \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/template_gemini.docx:/app/template_gemini.docx \
  --env-file .env \
  --name cv-formatter \
  cv-formatter

# 5. Ouvrir dans le navigateur
echo "Application disponible sur http://localhost:5000"
```

---

## 🔧 Maintenance

### Modifier le Template Word

1. Ouvrir `template_gemini.docx` avec Microsoft Word ou LibreOffice
2. Les variables Jinja2 utilisables sont :
   - `{{ profil.titre_cible }}` - Titre du profil
   - `{{ profil.annees_experience }}` - Années d'expérience
   - `{{ resume_competences.techniques }}` - Dict des compétences techniques
   - `{{ resume_competences.metiers }}` - Liste compétences métiers
   - `{{ resume_competences.fonctionnelles }}` - Liste compétences fonctionnelles
   - `{{ resume_competences.langues }}` - Liste des langues
   - `{{ formations.diplomes }}` - Liste des diplômes
   - `{{ formations.certifications }}` - Liste des certifications
   - `{{ experiences }}` - Liste des expériences professionnelles
   - `{{ manager.nom }}` - Nom du manager
   - `{{ manager.email }}` - Email du manager
   - `{{ manager.telephone }}` - Téléphone du manager
   - `{{ manager.adresse }}` - Adresse du manager
3. Sauvegarder et le conteneur utilisera automatiquement la nouvelle version

### Modifier l'Application Flask

1. Éditer `app.py` pour la logique backend
2. Éditer `templates/*.html` pour l'interface
3. Éditer `static/css/style.css` pour le style
4. Reconstruire l'image Docker après modification

### Ajouter une nouvelle route API

1. Dans `app.py`, ajouter une nouvelle fonction décorée avec `@app.route()`
2. Documenter la route dans ce fichier MEMORY.md
3. Tester localement avant de reconstruire Docker

### Personnaliser l'interface

L'interface utilise Bootstrap 5 et peut être personnalisée via :
- `templates/base.html` : Structure globale (navbar, footer)
- `templates/index.html` : Page principale
- `static/css/style.css` : Styles personnalisés

---

## 📝 Changelog

### v2.0.0 (2025-12-09)
- Migration vers une plateforme web Flask
- Interface utilisateur moderne avec Bootstrap 5
- Upload drag & drop avec prévisualisation
- Gestion des fichiers générés (liste, téléchargement, suppression)
- Barre de progression animée pendant le traitement
- Serveur de production Gunicorn
- Health check Docker intégré
- Code commenté en français

### v1.0.0 (2025-12-09)
- Version initiale (CLI)
- Extraction PDF via pypdf
- Intégration API Gemini (gemini-1.5-flash)
- Génération DOCX via docxtpl
- Dockerfile multi-stage optimisé

---

## ⚠️ Notes Importantes

1. **Clé API** : Ne jamais commiter le fichier `.env` contenant la clé API Gemini
2. **Template** : Le fichier `template_gemini.docx` doit être fourni par l'utilisateur
3. **Limites API** : Respecter les quotas de l'API Gemini (voir documentation Google)
4. **Anonymisation** : Le prompt garantit l'anonymisation des données personnelles du candidat
5. **Production** : En production, utiliser HTTPS via un reverse proxy (nginx)
6. **Fichiers temporaires** : Les PDFs uploadés sont automatiquement supprimés après traitement

---

## 🆘 Dépannage

| Problème | Solution |
|----------|----------|
| "Template non trouvé" | Vérifier que `template_gemini.docx` est monté en volume |
| "Clé API invalide" | Vérifier le fichier `.env` et la validité de la clé |
| "Erreur JSON" | Le CV peut être mal formaté, vérifier les logs |
| "Pas de texte extrait" | Le PDF peut être scanné (image), non textuel |
| "Port 5000 occupé" | Changer le port : `-p 8080:5000` |
| "Permission denied" | Vérifier les droits sur le dossier output |
| "Container unhealthy" | Vérifier les logs : `docker logs cv-formatter` |

---

## 📊 Métriques et Monitoring

### Health Check

L'endpoint `/status` retourne :
```json
{
  "status": "ok",
  "configuration": {
    "valide": true,
    "erreurs": []
  },
  "version": "2.0.0"
}
```

### Logs Docker

```bash
# Logs en temps réel
docker logs -f cv-formatter

# Dernières 100 lignes
docker logs --tail 100 cv-formatter
```
