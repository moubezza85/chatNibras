# Chat NIBRAS - Personnalisation Institutionnelle OFPPT

Ce document détaille l'architecture et les procédures de personnalisation pour la version institutionnelle **Chat NIBRAS** basée sur Open WebUI.

---

## 1. Architecture de Configuration (.env)

Toutes les configurations NIBRAS sont centralisées et surchargeables via le fichier `.env` ou les variables d'environnement Docker sans modification de code source.

| Variable | Description | Valeur par défaut |
| :--- | :--- | :--- |
| `NIBRAS_APP_NAME` | Nom officiel affiché dans l'interface, les titres et le manifeste | `Chat NIBRAS` |
| `NIBRAS_DEFAULT_MODEL` | Modèle LLM par défaut utilisé au démarrage et pour les nouvelles conversations | `qwen3:8b` |
| `NIBRAS_PRIMARY_COLOR` | Couleur primaire institutionnelle (Bleu OFPPT) | `#0066B0` |
| `NIBRAS_SECONDARY_COLOR`| Couleur secondaire institutionnelle (Vert OFPPT) | `#0C8447` |
| `NIBRAS_ACCENT_COLOR` | Couleur d'accent | `#0C8447` |

### Changer de Modèle sans Rebuild

Pour changer de modèle LLM (par exemple passer à `qwen3:14b`, `qwen3:30b` ou tout autre modèle Ollama) :
1. Éditer le fichier `.env` :
   ```env
   NIBRAS_DEFAULT_MODEL=qwen3:14b
   ```
2. Redémarrer le conteneur Docker :
   ```bash
   docker compose restart open-webui
   ```
   *Aucune recompilation de l'image ni modification de frontend n'est nécessaire.*

---

## 2. Identité Visuelle & Palette OFPPT

La palette institutionnelle est extraite du logo officiel OFPPT et centralisée dans [`static/static/custom.css`](static/static/custom.css) et [`src/tailwind.css`](src/tailwind.css) :
- **Bleu OFPPT (Primaire)** : `#0066B0` (Hover: `#00569E`)
- **Vert OFPPT (Secondaire / Accent)** : `#0C8447` (Hover: `#0A733E`)
- **Surface Clair** : `#FFFFFF` sur fond `#F8FAFC`
- **Surface Sombre** : `#0F172A` sur fond `#090E17` (Slate / Navy profond)

---

## 3. Gestion des Assets et Logos

Tous les assets institutionnels (favicons multi-formats, logo, splash screens, web manifests) ont été générés à partir de `logo Chat nibras.png` dans `static/static/` via le script :
```bash
python scripts/generate_nibras_assets.py
```

---

## 4. Construction et Déploiement Docker

### Construction de l'image Docker personnalisée NIBRAS :
```bash
docker build -t chat-nibras:latest .
```

### Démarrage avec Docker Compose :
```bash
docker compose up -d
```

L'application sera accessible sur : `http://localhost:3000` (ou port configuré dans `.env`).

---

## 5. Branche Git

Toutes les modifications sont isolées sur la branche dédiée :
```bash
git checkout nibras
```
Cela garantit une compatibilité totale avec les futures fusions (`git merge origin/main`).
