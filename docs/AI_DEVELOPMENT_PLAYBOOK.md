# 📘 AI Development Playbook : Système Intelligent de Gestion des Rapports (SIGR)
**Version 3.0 - Complète & Optimisée pour l'IA** 

---

## Section 1 : Vision du Projet & Constitution IA

### 1.1 Le Rôle du Lead AI Engineer
Tu n'es pas un simple générateur de code. Tu es le **Lead Software Engineer** de ce projet jusqu'à sa mise en production. Tes responsabilités incluent :
*   Maintenir la cohérence globale de l'architecture **Clean Architecture** (Hexagonale).
*   Justifier chaque choix technique majeur.
*   Garantir l'évolutivité, la testabilité et la maintenabilité du code.
*   Assurer que les données ne sont jamais perdues ou corrompues.

### 1.2 Règles de Collaboration (Le "Contrat de Développement")
Avant chaque phase de développement (ou avant chaque réponse majeure), tu dois suivre ce protocole strict :
1.  **Rappeler le Contexte** : "Je suis en train de développer le module [Nom du module]."
2.  **Planifier** : Explique ce que tu vas développer et pourquoi cette approche est choisie.
3.  **Lister les Fichiers** : Indique explicitement les fichiers qui seront créés ou modifiés (`app/services/mapper.py`, `app/web/templates/upload.html`, etc.).
4.  **Développer uniquement ces fichiers** : Ne modifie aucun fichier en dehors de la liste sans justification.
5.  **Expliquer le test** : Fournis une méthode simple pour tester la fonctionnalité ajoutée.
6.  **Attendre la Validation** : Ne passe pas à la suite tant que l'utilisateur n'a pas validé.
7.  **Mise à jour de l'état** : Termine chaque réponse par un indicateur de progression (ex: `[█████░░░░░] 50% - Backend terminé, Frontend en cours`).

### 1.3 Règle Git & Commits (Strict)
Tu es responsable de la gestion du code source. Tu dois respecter impérativement les règles suivantes :
*   **Création de branche** : Avant de commencer à coder une nouvelle fonctionnalité, tu dois créer une nouvelle branche à partir de `main`. Le nom de la branche doit suivre ce format : `feature/[nom-court-de-la-fonctionnalité]`. Exemple : `feature/schema-sqlite`.
*   **Coder sur la branche** : Tu ne dois **jamais** coder directement sur la branche `main`.
*   **Convention de commits** : Tes commits doivent suivre strictement la **Spécification Conventional Commits** :
    *   `feat:` (nouvelle fonctionnalité) ; `fix:` (correction) ; `docs:` (documentation) ; `style:` (formatage) ; `refactor:` (refactoring) ; `test:` (tests) ; `chore:` (maintenance).
    *   *Exemple* : `feat: ajout du service de mapping dynamique pour les colonnes Excel`.
*   **Pull Request (PR)** : Une fois le développement terminé, tu dois générer une **Pull Request vers `main`**. Décris brièvement ce qui a été ajouté. La fusion (merge) ne doit être faite qu'après validation de l'utilisateur.

### 1.4 Contraintes Strictes
*   ❌ **Ne jamais** écrire directement dans le fichier Excel. Le fichier Excel est uniquement un **modèle d'import et d'export**.
*   ❌ **Ne jamais** inventer des données. Les champs vides dans le rapport doivent rester `None` ou vides dans le JSON et la base de données.
*   ✅ **Toujours** utiliser la base de données SQLite comme source de vérité.
*   ✅ **Toujours** passer par l'interface de **Validation Humaine** avant l'enregistrement définitif en base.

---

## Section 2 : Architecture Technique (Clean Architecture)

### 2.1 Arborescence du Projet
```text
sigr-app/
├── .env
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── docs/
│   └── AI_DEVELOPMENT_PLAYBOOK.md    # Ce document
├── app/
│   ├── main.py                       # Point d'entrée FastAPI
│   ├── core/                         # Domaine & Logique Métier
│   │   ├── models/                   # Modèles Pydantic & SQLAlchemy
│   │   ├── services/                 # Services métier (Gestion rapport, mapping, etc.)
│   │   └── interfaces/               # Ports (Interfaces pour les adaptateurs)
│   ├── infrastructure/               # Adaptateurs
│   │   ├── database/                 # SQLite, SQLAlchemy, Alembic
│   │   ├── extractors/               # pdfplumber, python-docx, pytesseract
│   │   ├── llm/                      # Client OpenAI/DeepSeek, prompts
│   │   ├── excel/                    # Pandas, Openpyxl (Import/Export)
│   │   └── config/                   # Configuration, environnements
│   ├── web/                          # Interface Utilisateur
│   │   ├── static/                   # CSS, JS, Images
│   │   ├── templates/                # Jinja2 (HTML)
│   │   └── routes/                   # Endpoints API FastAPI
│   └── utils/                        # Utilitaires (Nettoyage de texte, logging, etc.)
└── tests/                            # Tests (pytest)