# MEMORY.md - Journal de Bord du Projet CV Formatter

> **Dernière mise à jour** : 2025-12-09
> **Version** : 1.0.0
> **Auteur** : Cherif Elkhodja

---

## 📋 Description du Projet

Outil d'automatisation permettant de transformer des CVs au format PDF en documents Word (.docx) standardisés selon le format de l'ESN Gemini Consulting. L'extraction intelligente des données est réalisée via l'API Google Gemini.

---

## 🏗️ Architecture Technique

```
/app
├── input/                  # Dépôt des CVs PDF à traiter
├── output/                 # CVs Word générés
├── main.py                 # Script principal Python
├── template_gemini.docx    # Template Word (fourni par l'utilisateur)
├── requirements.txt        # Dépendances Python
├── Dockerfile              # Configuration Docker
├── .env.example            # Exemple de configuration
└── MEMORY.md               # Ce fichier de documentation
```

### Stack Technique

| Composant | Version/Outil | Rôle |
|-----------|---------------|------|
| Python | 3.11 | Langage principal |
| google-generativeai | Latest | API Gemini pour extraction IA |
| docxtpl | Latest | Injection données dans template Word |
| pypdf | Latest | Extraction texte des PDF |
| python-dotenv | Latest | Gestion variables d'environnement |
| Docker | Multi-stage | Conteneurisation |

### Flux de Traitement

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│  PDF Input  │───>│ Extraction   │───>│ API Gemini  │───>│ Génération   │
│  (input/)   │    │ Texte (pypdf)│    │ (JSON)      │    │ DOCX (output)│
└─────────────┘    └──────────────┘    └─────────────┘    └──────────────┘
```

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

### Lancement du conteneur

```bash
# Mode standard avec volumes montés
docker run --rm \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/template_gemini.docx:/app/template_gemini.docx \
  --env-file .env \
  cv-formatter

# Mode interactif (debug)
docker run -it --rm \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/template_gemini.docx:/app/template_gemini.docx \
  --env-file .env \
  cv-formatter /bin/bash
```

### Workflow complet

```bash
# 1. Créer le fichier .env à partir de l'exemple
cp .env.example .env
# 2. Éditer .env et ajouter votre clé API Gemini
nano .env
# 3. Placer le template Word
cp votre_template.docx template_gemini.docx
# 4. Placer les CVs PDF dans input/
cp *.pdf input/
# 5. Construire et lancer
docker build -t cv-formatter . && docker run --rm \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/template_gemini.docx:/app/template_gemini.docx \
  --env-file .env \
  cv-formatter
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
3. Sauvegarder et relancer le Docker

### Modifier le Script Python

1. Éditer `main.py`
2. Les sections principales sont :
   - **Configuration** : Variables d'environnement et constantes
   - **PROMPT_SYSTEME** : Le prompt envoyé à Gemini
   - **MANAGER_INFO** : Informations statiques du manager
   - **Fonctions d'extraction** : `extraire_texte_pdf()`
   - **Fonctions API** : `appeler_gemini()`
   - **Fonctions de génération** : `generer_docx()`
3. Reconstruire l'image Docker après modification

### Ajouter une nouvelle compétence métier/fonctionnelle

Modifier le `PROMPT_SYSTEME` dans `main.py` pour inclure des exemples supplémentaires dans les règles de tri.

---

## 📝 Changelog

### v1.0.0 (2025-12-09)
- Version initiale
- Extraction PDF via pypdf
- Intégration API Gemini (gemini-1.5-flash)
- Génération DOCX via docxtpl
- Dockerfile multi-stage optimisé
- Documentation complète

---

## ⚠️ Notes Importantes

1. **Clé API** : Ne jamais commiter le fichier `.env` contenant la clé API Gemini
2. **Template** : Le fichier `template_gemini.docx` doit être fourni par l'utilisateur
3. **Limites API** : Respecter les quotas de l'API Gemini (voir documentation Google)
4. **Anonymisation** : Le prompt garantit l'anonymisation des données personnelles du candidat

---

## 🆘 Dépannage

| Problème | Solution |
|----------|----------|
| "Template non trouvé" | Vérifier que `template_gemini.docx` existe à la racine |
| "Clé API invalide" | Vérifier le fichier `.env` et la validité de la clé |
| "Erreur JSON" | Le CV peut être mal formaté, vérifier les logs |
| "Pas de texte extrait" | Le PDF peut être scanné (image), non textuel |
