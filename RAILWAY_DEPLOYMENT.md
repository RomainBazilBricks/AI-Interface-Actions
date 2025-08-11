# 🚂 Déploiement sur Railway avec VNC

Ce guide vous explique comment déployer votre application AI Interface Actions sur Railway avec un navigateur visible accessible via VNC pour la configuration initiale de session Manus.ai.

## 📋 Prérequis

- Compte Railway ([railway.app](https://railway.app))
- Client VNC (RealVNC Viewer, TightVNC, ou VNC Viewer)
- Compte Manus.ai actif

## 🏗️ Architecture de la solution

```
Railway Container
├── X11 Virtual Display (:1)
├── VNC Server (port 5900) 
├── Fluxbox Window Manager
├── Chromium Browser (visible via VNC)
└── FastAPI Application (port 8000)
```

## 🚀 Étapes de déploiement

### 1. Préparation du projet

Votre projet contient maintenant les fichiers nécessaires :
- `Dockerfile.railway` - Container avec VNC
- `supervisord.conf` - Gestion des services
- `start-railway.sh` - Script de démarrage
- `railway.yml` - Configuration Railway
- `ai_interface_actions/admin_routes.py` - API d'administration

### 2. Créer le projet sur Railway

1. **Connectez votre repository GitHub à Railway**
   ```bash
   # Si ce n'est pas déjà fait, poussez vos changements
   git add .
   git commit -m "Add Railway VNC support"
   git push origin main
   ```

2. **Créez un nouveau projet Railway**
   - Allez sur [railway.app](https://railway.app)
   - Cliquez sur "New Project" > "Deploy from GitHub repo"
   - Sélectionnez votre repository

3. **Configurez le Dockerfile**
   - Dans les settings du projet Railway
   - Allez dans "Settings" > "Build"
   - Définissez "Dockerfile Path" à `Dockerfile.railway`

### 3. Configuration des variables d'environnement

Dans Railway, allez dans "Variables" et ajoutez :

```bash
# Configuration API
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# Configuration navigateur
HEADLESS=true
HEADLESS_SETUP=false
USE_PERSISTENT_CONTEXT=true
WINDOW_WIDTH=1920
WINDOW_HEIGHT=1080

# Configuration Manus.ai
MANUS_BASE_URL=https://www.manus.ai

# Timeouts
BROWSER_TIMEOUT=60000
PAGE_TIMEOUT=30000

# Logging
LOG_LEVEL=INFO

# Sécurité
RATE_LIMIT_PER_MINUTE=20
```

### 4. Déploiement

1. **Lancez le déploiement**
   - Railway détectera automatiquement le `Dockerfile.railway`
   - Le build peut prendre 5-10 minutes (installation de Chromium)

2. **Vérifiez le déploiement**
   - Attendez que le statut passe à "Active"
   - Notez l'URL publique de votre application

## 🖥️ Configuration de la session via VNC

### 1. Obtenir les informations VNC

Appelez l'API pour obtenir les détails de connexion :

```bash
curl https://votre-app.railway.app/admin/vnc-info
```

Réponse :
```json
{
  "vnc_url": "vnc://votre-app.railway.app:5900",
  "host": "votre-app.railway.app",
  "port": 5900,
  "protocol": "VNC",
  "password_required": false,
  "instructions": [...]
}
```

### 2. Lancer le setup de session

```bash
curl -X POST https://votre-app.railway.app/admin/setup-session
```

Cette commande :
- Ouvre Manus.ai dans le navigateur visible (VNC)
- Programme une sauvegarde automatique après 10 minutes
- Retourne les instructions de connexion VNC

### 3. Connexion VNC

1. **Ouvrez votre client VNC**
   - RealVNC Viewer : [realvnc.com](https://www.realvnc.com/en/connect/download/viewer/)
   - TightVNC : [tightvnc.com](https://www.tightvnc.com/download.php)

2. **Connectez-vous**
   ```
   Serveur : votre-app.railway.app:5900
   Mot de passe : (aucun)
   ```

3. **Vous devriez voir**
   - Un bureau Linux avec Fluxbox
   - Une fenêtre Chromium ouverte sur Manus.ai

### 4. Connexion à Manus.ai

1. **Dans la fenêtre VNC/Chromium**
   - Connectez-vous avec vos identifiants Manus.ai
   - Attendez d'être sur le tableau de bord
   - La session sera automatiquement sauvegardée

2. **Vérification**
   ```bash
   curl https://votre-app.railway.app/admin/session-status
   ```

## 🔧 Gestion et maintenance

### API d'administration disponible

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/admin/session-status` | GET | Statut de la session |
| `/admin/setup-session` | POST | Lancer le setup VNC |
| `/admin/force-save-session` | POST | Sauvegarder immédiatement |
| `/admin/vnc-info` | GET | Infos de connexion VNC |

### Renouvellement de session (tous les ~30 jours)

1. **Méthode automatique**
   ```bash
   curl -X POST https://votre-app.railway.app/admin/setup-session
   # Puis reconnectez-vous via VNC
   ```

2. **Méthode manuelle**
   - Redéployez l'application sur Railway
   - Recommencez la configuration VNC

### Surveillance

```bash
# Vérifier le statut
curl https://votre-app.railway.app/health

# Vérifier la session
curl https://votre-app.railway.app/admin/session-status

# Logs Railway
railway logs
```

## 🛠️ Dépannage

### Le VNC ne répond pas
```bash
# Vérifier les logs Railway
railway logs

# Redémarrer l'application
railway service restart
```

### Session perdue
```bash
# Forcer une nouvelle configuration
curl -X POST https://votre-app.railway.app/admin/setup-session
```

### Navigateur ne s'ouvre pas
- Vérifiez que `HEADLESS_SETUP=false` dans les variables Railway
- Redéployez si nécessaire

## 📊 Ressources et coûts

### Ressources utilisées
- **RAM** : ~800MB (Chromium + VNC + API)
- **CPU** : ~0.5 vCPU
- **Stockage** : ~2GB (image Docker)

### Optimisation des coûts Railway
- L'application peut être mise en veille quand non utilisée
- VNC n'est nécessaire que pour la configuration initiale
- Considérez un plan Railway adapté à votre usage

## 🔒 Sécurité

### Recommandations
- Le VNC n'a pas de mot de passe (accès par URL Railway uniquement)
- Railway fournit HTTPS automatique
- Les sessions sont chiffrées côté navigateur
- Limitez l'accès aux routes `/admin/*` si nécessaire

### Variables sensibles
- Utilisez les variables d'environnement Railway pour les secrets
- Ne commitez jamais d'identifiants dans le code
- La session Manus.ai est stockée de manière sécurisée

## 📞 Support

En cas de problème :
1. Vérifiez les logs Railway : `railway logs`
2. Testez l'API de santé : `curl https://votre-app.railway.app/health`
3. Vérifiez la configuration VNC : `curl https://votre-app.railway.app/admin/vnc-info`

---

🎉 **Votre application est maintenant déployée sur Railway avec support VNC !**

L'avantage de cette solution est que vous n'avez besoin de vous connecter via VNC qu'une seule fois pour configurer la session Manus.ai, qui durera ensuite ~30 jours en mode automatique. 