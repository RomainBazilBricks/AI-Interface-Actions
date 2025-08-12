# 🚂 Guide de Déploiement Railway - AI Interface Actions

## 🔧 Corrections pour l'erreur 500 Playwright

### Problème identifié
L'erreur 500 sur `/send-message-quick` était causée par :
- ❌ Navigateurs Playwright non installés en production
- ❌ Problèmes de permissions entre root et appuser
- ❌ Session Manus.ai manquante

### Solutions implémentées

#### 1. 🛠️ Dockerfile amélioré
- Installation de Playwright en tant qu'utilisateur `appuser` (non-root)
- Script de démarrage intelligent avec vérification automatique
- Gestion des erreurs d'installation gracieuse

#### 2. 🚀 Script de démarrage amélioré (`start-railway.sh`)
- Vérification automatique de l'installation Playwright
- Installation automatique des navigateurs si manquants
- Mode dégradé si l'installation échoue

#### 3. 📡 API plus robuste
- Vérification du statut du navigateur avant traitement
- Messages d'erreur explicites (503 au lieu de 500)
- Gestion spécifique des erreurs Playwright et de session

## 🚀 Déploiement sur Railway

### Étapes de déploiement

1. **Connexion à Railway**
   ```bash
   railway login
   ```

2. **Déploiement du projet**
   ```bash
   railway up
   ```

3. **Configuration des variables d'environnement**
   ```bash
   railway variables set HEADLESS=true
   railway variables set DEBUG=false
   railway variables set LOG_LEVEL=INFO
   ```

### Variables d'environnement importantes

| Variable | Valeur | Description |
|----------|--------|-------------|
| `HEADLESS` | `true` | Mode headless obligatoire en production |
| `DEBUG` | `false` | Désactive le mode debug |
| `LOG_LEVEL` | `INFO` | Niveau de logging |
| `API_HOST` | `0.0.0.0` | Interface d'écoute |
| `API_PORT` | `8000` | Port d'écoute |

## 🔍 Vérification du déploiement

### 1. Vérifier l'état de santé
```bash
curl https://votre-app.up.railway.app/health
```

**Réponse attendue :**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "browser_ready": true,
  "uptime_seconds": 123.45
}
```

### 2. Vérifier le statut de session
```bash
curl https://votre-app.up.railway.app/session-status
```

**Si pas de session :**
```json
{
  "session_exists": false,
  "status": "no_session",
  "message": "Aucune session sauvegardée - utilisez /setup-login pour vous connecter"
}
```

## 🔐 Configuration de la session Manus.ai

### Méthode 1 : Connexion manuelle (Recommandée)
```bash
curl -X POST https://votre-app.up.railway.app/setup-login
```

### Méthode 2 : Variables d'environnement
Si vous avez les tokens de session :
```bash
railway variables set MANUS_SESSION_TOKEN="votre_token"
railway variables set MANUS_AUTH_TOKEN="votre_auth_token"
```

## 🚨 Dépannage

### Erreur 503 "navigateur non initialisé"
**Cause :** Playwright non installé correctement
**Solution :** Redéployer avec le nouveau Dockerfile

### Erreur 401 "Session expirée"
**Cause :** Session Manus.ai expirée (30 jours)
**Solution :** Utiliser `/setup-login` pour se reconnecter

### Erreur 500 générique
**Cause :** Erreur interne non gérée
**Solution :** Vérifier les logs Railway

## 📊 Monitoring

### Endpoints de surveillance
- `/health` - État de santé général
- `/session-status` - Statut de la session Manus.ai
- `/tasks` - Liste des tâches récentes

### Logs utiles
```bash
railway logs --follow
```

## 🔄 Mise à jour

Pour déployer une nouvelle version :
```bash
git add .
git commit -m "Update: description des changements"
git push
railway up
```

## 📝 Notes importantes

1. **Navigateur headless uniquement** : Railway ne supporte pas l'affichage graphique
2. **Session persistante** : La session Manus.ai dure 30 jours
3. **Timeout** : Les requêtes longues peuvent timeout (ajustez si nécessaire)
4. **Ressources** : Surveiller l'utilisation mémoire avec Playwright

## ✅ Checklist post-déploiement

- [ ] `/health` retourne `"browser_ready": true`
- [ ] Session Manus.ai configurée
- [ ] Test de `/send-message-quick` réussi
- [ ] Logs sans erreurs critiques
- [ ] Variables d'environnement correctes 