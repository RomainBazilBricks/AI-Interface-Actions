#!/usr/bin/env python3
"""
Test rapide pour reproduire exactement l'erreur d'upload ZIP
"""

import requests
import json

# Configuration - API locale pour debug
API_BASE_URL = "http://127.0.0.1:8000"
TEST_ZIP_URL = "https://neon-project-analysis.s3.eu-north-1.amazonaws.com/projects/1754764846020x119524286754193400/zips/589aa794c46dfe3386d5d07081c401c55aee3f58ffe19882e4d84dc85ee89565-1754764846020x119524286754193400-documents-1755771294515.zip"

def test_exact_scenario():
    """Reproduit exactement le scénario qui échoue"""
    print("🎯 Test du scénario exact qui échoue...")
    
    # Payload exacte comme dans les logs
    payload = {
        "zip_url": TEST_ZIP_URL,
        "message": "Une fois le traitement de TOUS les documents terminé, déclenche l'étape suiv...",
        "platform": "manus",
        "conversation_url": "",
        "wait_for_response": False,
        "timeout_seconds": 60
    }
    
    print(f"📡 URL: {API_BASE_URL}/upload-zip-from-url")
    print(f"📄 Payload: {json.dumps(payload, indent=2)}")
    
    try:
        print("\n📡 Envoi de la requête...")
        response = requests.post(
            f"{API_BASE_URL}/upload-zip-from-url",
            json=payload,
            timeout=120,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Succès!")
            print(f"📄 Response: {json.dumps(data, indent=2)}")
        else:
            print(f"❌ Échec: {response.status_code}")
            try:
                error_data = response.json()
                print(f"📄 Error Response: {json.dumps(error_data, indent=2)}")
            except:
                print(f"📄 Raw Response: {response.text}")
                
    except requests.exceptions.Timeout:
        print("⏰ Timeout de la requête (120s)")
    except Exception as e:
        print(f"❌ Erreur: {e}")

def test_session_first():
    """Test la session avant l'upload"""
    print("🔍 Vérification de la session...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/debug/session-status", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            status = data.get('status', 'unknown')
            print(f"🔐 Session Status: {status}")
            
            if status == 'connected':
                print("✅ Session OK, procédure d'upload...")
                return True
            else:
                print("❌ Session problématique:")
                page_info = data.get('page_info', {})
                print(f"  🔗 URL: {page_info.get('url', 'N/A')}")
                print(f"  📝 Title: {page_info.get('title', 'N/A')}")
                print(f"  📝 Textareas: {len(page_info.get('textareas', []))}")
                
                # Détails des textareas
                textareas = page_info.get('textareas', [])
                for i, ta in enumerate(textareas):
                    print(f"    {i+1}. '{ta.get('placeholder', 'N/A')}' (visible: {ta.get('visible', False)})")
                
                return False
        else:
            print(f"❌ Diagnostic session échoué: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur diagnostic: {e}")
        return False

def main():
    print("🚀 TEST RAPIDE DE DEBUG")
    print("=" * 40)
    
    # 1. Vérifier la session
    session_ok = test_session_first()
    
    print("\n" + "=" * 40)
    
    # 2. Tester l'upload même si session pas OK (pour voir l'erreur)
    test_exact_scenario()
    
    print("\n" + "=" * 40)
    print("📊 CONCLUSION")
    if not session_ok:
        print("🎯 Le problème semble être lié à la session/connexion Manus.ai")
        print("💡 Solutions possibles:")
        print("   - Reconnecter à Manus.ai")
        print("   - Vérifier les credentials")
        print("   - Redémarrer le navigateur")
    else:
        print("🎯 Session OK mais upload échoue - problème dans la logique d'upload")

if __name__ == "__main__":
    main()
