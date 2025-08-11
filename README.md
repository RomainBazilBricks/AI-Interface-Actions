# AI Interface Actions

Outil d'automatisation pour les plateformes IA via leur interface web, permettant d'envoyer des messages et de récupérer les réponses sans API officielle.

## 🚀 Fonctionnalités

- ✅ **Automatisation navigateur** avec Playwright (headless)
- ✅ **API REST** moderne avec FastAPI et documentation Swagger
- ✅ **Exécution asynchrone** des tâches avec suivi en temps réel
- ✅ **Gestion robuste des erreurs** et retry logic
- ✅ **Configuration flexible** via variables d'environnement
- ✅ **Logging structuré** pour debugging efficace
- ✅ **Support Manus.ai** (extensible à d'autres plateformes)

## 📋 Prérequis

- **Python 3.11+**
- **Navigateur Chromium** (installé automatiquement par Playwright)
- **Compte Manus.ai** avec identifiants de connexion

## 🛠 Installation

### 1. Cloner le projet
```bash
git clone <url-du-repo>
cd ai-interface-actions
```

### 2. Créer un environnement virtuel
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 3. Installer les dépendances
```bash
pip install -e .
# ou
pip install -r requirements.txt
```

### 4. Installer les navigateurs Playwright
```bash
playwright install chromium
```

### 5. Configuration
```bash
cp .env.example .env
```

Éditer le fichier `.env` avec vos paramètres (optionnel) :
```env
# Configuration API (optionnel)
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# Configuration navigateur
HEADLESS=true                    # Mode invisible pour usage normal
HEADLESS_SETUP=false            # Mode visible pour setup (false = fenêtre s'ouvre)
USE_PERSISTENT_CONTEXT=true     # Garde la session (comme navigateur normal)

# Note: Plus besoin d'identifiants Manus.ai !
# La connexion se fait manuellement une fois, session valide 30 jours
```

## 🚀 Démarrage

### Démarrage simple
```bash
python -m ai_interface_actions.main
```

### Démarrage avec Uvicorn
```bash
uvicorn ai_interface_actions.api:app --host 0.0.0.0 --port 8000 --reload
```

### Démarrage en production
```bash
uvicorn ai_interface_actions.api:app --host 0.0.0.0 --port 8000 --workers 4
```

L'API sera disponible sur :
- **Interface Swagger** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc
- **Santé de l'API** : http://localhost:8000/health

## 📚 Utilisation de l'API

### 0. **Première utilisation : Connexion manuelle**

```bash
# Ouvrir une page de connexion pour setup initial
curl -X POST "http://localhost:8000/setup-login"
```

Cela ouvre automatiquement Manus.ai dans votre navigateur. Connectez-vous une fois, et c'est fini pour 30 jours !

### 1. Envoi de message asynchrone (recommandé)

```bash
curl -X POST "http://localhost:8000/send-message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Bonjour, comment ça va ?",
    "platform": "manus",
    "wait_for_response": true,
    "timeout_seconds": 60
  }'
```

Réponse :
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "pending",
  "message_sent": "Bonjour, comment ça va ?",
  "ai_response": null,
  "execution_time_seconds": null,
  "error_message": null
}
```

### 2. Suivi du statut de la tâche

```bash
curl "http://localhost:8000/task/123e4567-e89b-12d3-a456-426614174000"
```

Réponse :
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:30:15",
  "result": {
    "success": true,
    "message_sent": "Bonjour, comment ça va ?",
    "ai_response": "Bonjour ! Je vais bien, merci...",
    "page_url": "https://www.manus.ai/chat"
  },
  "error_message": null
}
```

### 3. Envoi synchrone (pour tests rapides)

```bash
curl -X POST "http://localhost:8000/send-message-sync" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Test rapide",
    "platform": "manus"
  }'
```

### 4. Liste des tâches

```bash
curl "http://localhost:8000/tasks?limit=10&status_filter=completed"
```

## 🐳 Déploiement Docker

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Copie et installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installation des navigateurs Playwright
RUN playwright install --with-deps chromium

# Copie du code source
COPY . .

# Variables d'environnement par défaut
ENV PYTHONPATH=/app
ENV HEADLESS=true

EXPOSE 8000

CMD ["python", "-m", "ai_interface_actions.main"]
```

### Docker Compose
```yaml
version: '3.8'
services:
  ai-interface-actions:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MANUS_LOGIN_EMAIL=${MANUS_LOGIN_EMAIL}
      - MANUS_LOGIN_PASSWORD=${MANUS_LOGIN_PASSWORD}
      - HEADLESS=true
      - DEBUG=false
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
```

## ⚙️ Configuration avancée

### Variables d'environnement

| Variable | Description | Défaut |
|----------|-------------|---------|
| `API_HOST` | Adresse d'écoute | `0.0.0.0` |
| `API_PORT` | Port d'écoute | `8000` |
| `DEBUG` | Mode debug | `false` |
| `HEADLESS` | Mode headless du navigateur | `true` |
| `BROWSER_TIMEOUT` | Timeout navigateur (ms) | `30000` |
| `PAGE_TIMEOUT` | Timeout pages (ms) | `15000` |
| `MANUS_BASE_URL` | URL de base Manus.ai | `https://www.manus.ai` |
| `MANUS_LOGIN_EMAIL` | Email de connexion | *(requis)* |
| `MANUS_LOGIN_PASSWORD` | Mot de passe | *(requis)* |
| `RATE_LIMIT_PER_MINUTE` | Limite de requêtes/min | `10` |
| `LOG_LEVEL` | Niveau de log | `INFO` |

### Personnalisation des sélecteurs

Pour adapter l'outil à d'autres plateformes, modifiez les sélecteurs dans `browser_automation.py` :

```python
# Sélecteurs pour le champ de message
selectors = [
    "textarea[placeholder*='message']",
    "textarea[placeholder*='votre-plateforme']",
    # Ajoutez vos sélecteurs ici
]
```

## 🔧 Développement

### Structure du projet
```
ai_interface_actions/
├── __init__.py           # Package principal
├── config.py             # Configuration Pydantic
├── models.py             # Modèles de données
├── browser_automation.py # Automatisation Playwright
├── task_manager.py       # Gestionnaire de tâches
├── api.py               # API FastAPI
└── main.py              # Point d'entrée
```

### Tests
```bash
# Tests unitaires
pytest tests/

# Tests d'intégration
pytest tests/integration/

# Coverage
pytest --cov=ai_interface_actions
```

### Linting
```bash
# Formatage
black ai_interface_actions/
isort ai_interface_actions/

# Linting
flake8 ai_interface_actions/
mypy ai_interface_actions/
```

## 🚨 Limitations et considérations

### Limitations techniques
- ⚠️ **Dépendance à l'UI** : Sensible aux changements d'interface des plateformes
- ⚠️ **Performance** : Plus lent qu'une API native (5-15 secondes par message)
- ⚠️ **Ressources** : Consomme plus de mémoire qu'un client HTTP simple

### Bonnes pratiques
- ✅ **Rate limiting** : Respectez les limites pour éviter les blocages
- ✅ **Monitoring** : Surveillez les logs pour détecter les changements d'UI
- ✅ **Fallback** : Prévoyez des alternatives en cas d'échec
- ✅ **Sécurité** : Stockez les identifiants de manière sécurisée

### Respect des ToS
- 📋 Utilisez cet outil de manière responsable
- 📋 Respectez les conditions d'utilisation des plateformes
- 📋 Implémentez des délais appropriés entre les requêtes
- 📋 Ne pas abuser du système (usage personnel/professionnel raisonnable)

## 🐛 Dépannage

### Problèmes courants

**1. Navigateur ne se lance pas**
```bash
# Réinstaller Playwright
playwright install --with-deps chromium
```

**2. Sélecteurs non trouvés**
- Vérifiez que la plateforme n'a pas changé son interface
- Activez le mode debug pour voir les pages : `DEBUG=true` et `HEADLESS=false`

**3. Connexion échoue**
- Vérifiez vos identifiants dans le fichier `.env`
- Testez la connexion manuelle sur le site

**4. Timeouts fréquents**
- Augmentez les valeurs de timeout dans la configuration
- Vérifiez votre connexion internet

### Logs de debug
```bash
# Activer les logs détaillés
export LOG_LEVEL=DEBUG
export DEBUG=true
export HEADLESS=false

python -m ai_interface_actions.main
```

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 🤝 Contribution

Les contributions sont les bienvenues ! Veuillez :

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/nouvelle-fonctionnalite`)
3. Commit vos changements (`git commit -am 'Ajouter nouvelle fonctionnalité'`)
4. Push vers la branche (`git push origin feature/nouvelle-fonctionnalite`)
5. Ouvrir une Pull Request

## 📞 Support

Pour toute question ou problème :
- 🐛 **Issues** : Ouvrir un ticket sur GitHub
- 📧 **Email** : contact@example.com
- 📖 **Documentation** : Consulter `/docs` de l'API en cours d'exécution 