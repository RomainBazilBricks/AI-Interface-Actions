# 🔑 Guide d'extraction de session Manus.ai

Ce guide vous explique comment extraire votre session Manus.ai depuis l'inspecteur du navigateur pour la configurer sur Railway.

## 📋 Étapes d'extraction

### 1. Connectez-vous à Manus.ai

1. Ouvrez votre navigateur (Chrome/Firefox/Safari)
2. Allez sur https://www.manus.ai
3. Connectez-vous avec vos identifiants
4. Naviguez jusqu'au tableau de bord principal

### 2. Ouvrir l'inspecteur

**Chrome/Firefox :**
- Clic droit > "Inspecter l'élément"
- Ou appuyez sur `F12`

**Safari :**
- Développement > Afficher l'inspecteur web
- (Activez d'abord le menu Développement dans Préférences > Avancées)

### 3. Aller dans l'onglet Application/Storage

**Chrome :**
- Cliquez sur l'onglet "Application"
- Dans la sidebar gauche, développez "Storage"

**Firefox :**
- Cliquez sur l'onglet "Stockage"

**Safari :**
- Cliquez sur l'onglet "Stockage"

### 4. Extraire les cookies

1. **Cliquez sur "Cookies"** dans la sidebar
2. **Sélectionnez le domaine Manus.ai** (ex: `https://www.manus.ai`)
3. **Copiez TOUS les cookies importants** :

| Nom du Cookie | Description | Action |
|---------------|-------------|---------|
| `session_token` | Token de session principal | ⭐ OBLIGATOIRE |
| `auth_token` | Token d'authentification | ⭐ OBLIGATOIRE |
| `user_id` | ID utilisateur | ⭐ OBLIGATOIRE |
| `csrf_token` | Token CSRF | Recommandé |
| `remember_token` | Token de mémorisation | Optionnel |

4. **Format à copier pour chaque cookie :**
   ```
   Nom: session_token
   Valeur: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   Domaine: .manus.ai
   Chemin: /
   ```

### 5. Extraire le localStorage (optionnel)

1. **Cliquez sur "Local Storage"** dans la sidebar
2. **Sélectionnez le domaine Manus.ai**
3. **Copiez les clés importantes** :
   - `user_preferences`
   - `auth_state` 
   - `session_data`

## 🔧 Configuration Railway

Une fois les données extraites, configurez ces variables d'environnement sur Railway :

```bash
# Cookies principaux (remplacez par vos vraies valeurs)
MANUS_SESSION_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
MANUS_AUTH_TOKEN=abc123def456...
MANUS_USER_ID=user_12345
MANUS_CSRF_TOKEN=csrf_abc123

# localStorage (optionnel)
MANUS_USER_PREFERENCES={"theme":"dark","lang":"fr"}
MANUS_AUTH_STATE=authenticated
```

## 📝 Script d'extraction automatique (bonus)

Vous pouvez aussi exécuter ce script dans la console du navigateur pour extraire automatiquement :

```javascript
// Copiez-collez dans la console de l'inspecteur
console.log("=== COOKIES MANUS.AI ===");
document.cookie.split(';').forEach(cookie => {
    const [name, value] = cookie.trim().split('=');
    if (name && value) {
        console.log(`${name}=${value}`);
    }
});

console.log("\n=== LOCAL STORAGE ===");
Object.keys(localStorage).forEach(key => {
    console.log(`${key}=${localStorage.getItem(key)}`);
});

console.log("\n=== SESSION STORAGE ===");
Object.keys(sessionStorage).forEach(key => {
    console.log(`${key}=${sessionStorage.getItem(key)}`);
});
```

## 🚀 Avantages de cette méthode

- ✅ **Pas de script local** à exécuter
- ✅ **Délégable** à d'autres utilisateurs
- ✅ **Flexible** : Fonctionne avec n'importe quel navigateur
- ✅ **Sécurisé** : Vous gardez le contrôle des tokens
- ✅ **Rapide** : 2 minutes max

## ⚠️ Sécurité

- **Ne partagez JAMAIS** vos tokens de session publiquement
- **Utilisez des variables d'environnement** Railway (chiffrées)
- **Renouvelez** les tokens tous les 30 jours environ
- **Révocation** : Déconnectez-vous de Manus.ai si tokens compromis

---

Une fois les variables configurées sur Railway, l'application utilisera automatiquement ces tokens au lieu du fichier `session_state.json` ! 🎉 