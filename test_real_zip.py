import requests
import json

# Configuration - API locale pour test avec votre ZIP réel
API_BASE_URL = "http://127.0.0.1:8000"
REAL_ZIP_URL = "https://ai-bricks-analyst-production.up.railway.app/api/projects/1754913269434x582556426926555100/zip/download"

def test_real_zip_upload():
    print("🚀 Test avec le ZIP réel de votre projet...")
    print(f"📦 URL ZIP: {REAL_ZIP_URL}")
    
    url = f"{API_BASE_URL}/upload-zip-from-url"
    payload = {
        "zip_url": REAL_ZIP_URL,
        "message": "Test avec le ZIP réel du projet - analyse des documents.",
        "platform": "manus",
        "conversation_url": "",  # Nouvelle conversation
        "wait_for_response": False,  # Ne pas attendre la réponse IA pour un test rapide
        "timeout_seconds": 180  # 3 minutes pour gros fichier
    }
    headers = {"Content-Type": "application/json"}
    
    print(f"📡 Envoi de la requête...")
    print(f"📄 Payload: {json.dumps(payload, indent=2)}")
    print("⏱️ Démarrage de l'upload (surveillez les logs de l'API)...")
    print("🔍 Attendez les logs détaillés:")
    print("   - ⚠️ Fichier très volumineux (XXX MB) - timeout ajusté à 180s")
    print("   - 🚀 Début de la simulation du drag & drop")
    print("   - 📊 Transfert de XXX MB vers le navigateur...")
    print("   - ⏱️ Timeout configuré: 180s pour page.evaluate()")
    print("   - ✅ Drag & drop simulé avec succès")
    
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers, timeout=200)  # 200s timeout côté client
        response.raise_for_status()
        result = response.json()
        
        print("\n📊 Résultat de l'upload:")
        print(json.dumps(result, indent=2))
        
        if result.get("status") == "completed" and result.get("conversation_url"):
            print(f"✅ SUCCÈS! URL de conversation: {result['conversation_url']}")
            print(f"📁 Filename: {result['filename']}")
            return True
        else:
            print(f"❌ ÉCHEC! Erreur: {result.get('error_message', result.get('error', 'Inconnu'))}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur lors de l'appel API: {e}")
        if e.response:
            print(f"Status Code: {e.response.status_code}")
            print(f"Response data: {e.response.text}")
        return False

if __name__ == "__main__":
    print("🎯 TEST AVEC ZIP RÉEL")
    print("=" * 50)
    success = test_real_zip_upload()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 TEST RÉUSSI - Le ZIP volumineux fonctionne!")
    else:
        print("💥 TEST ÉCHOUÉ - Vérifiez les logs de l'API")
