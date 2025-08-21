#!/usr/bin/env python3
"""
Test étape par étape pour identifier où ça coince
"""

import requests
import json
import time

API_BASE_URL = "http://127.0.0.1:8000"

def test_step_1_session():
    """Étape 1: Vérifier la session"""
    print("🔍 ÉTAPE 1: Vérification de la session")
    
    response = requests.get(f"{API_BASE_URL}/debug/session-status", timeout=30)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Status: {data.get('status')}")
        print(f"🌐 URL: {data['page_info']['url']}")
        print(f"📝 Title: {data['page_info']['title']}")
        print(f"📄 Textareas: {len(data['page_info']['textareas'])}")
        
        for i, ta in enumerate(data['page_info']['textareas']):
            print(f"  {i+1}. '{ta['placeholder']}' (visible: {ta['visible']})")
        
        return data.get('status') == 'connected'
    else:
        print(f"❌ Erreur: {response.status_code}")
        return False

def test_step_2_find_input():
    """Étape 2: Test direct de détection de zone de saisie"""
    print("\n🎯 ÉTAPE 2: Test de détection de zone de saisie")
    
    # Appeler directement l'endpoint de diagnostic avec plus de détails
    response = requests.get(f"{API_BASE_URL}/debug/session-status", timeout=30)
    
    if response.status_code == 200:
        data = response.json()
        textareas = data['page_info']['textareas']
        
        print(f"📊 Nombre de textareas: {len(textareas)}")
        
        for i, ta in enumerate(textareas):
            placeholder = ta['placeholder']
            visible = ta['visible']
            disabled = ta['disabled']
            
            print(f"  Textarea {i+1}:")
            print(f"    Placeholder: '{placeholder}'")
            print(f"    Visible: {visible}")
            print(f"    Disabled: {disabled}")
            
            # Tester nos sélecteurs
            selectors_to_test = [
                f'textarea[placeholder="{placeholder}"]',
                f'textarea[placeholder*="Attribuez"]',
                f'textarea[placeholder*="tâche"]',
                f'textarea[placeholder*="question"]'
            ]
            
            print(f"    Sélecteurs qui devraient fonctionner:")
            for sel in selectors_to_test:
                print(f"      - {sel}")
        
        return len(textareas) > 0 and any(ta['visible'] and not ta['disabled'] for ta in textareas)
    else:
        print(f"❌ Erreur: {response.status_code}")
        return False

def test_step_3_minimal_upload():
    """Étape 3: Test d'upload minimal avec logs détaillés"""
    print("\n📤 ÉTAPE 3: Test d'upload minimal")
    
    # Payload minimal pour test
    payload = {
        "zip_url": "https://github.com/octocat/Hello-World/archive/refs/heads/master.zip",
        "message": "Test minimal étape par étape",
        "platform": "manus",
        "conversation_url": "",  # Nouvelle conversation
        "wait_for_response": False,
        "timeout_seconds": 30
    }
    
    print(f"📡 Envoi de la requête...")
    print(f"📄 Payload: {json.dumps(payload, indent=2)}")
    
    try:
        # Surveiller les logs en temps réel pendant l'upload
        print("⏱️ Démarrage de l'upload (surveillez les logs de l'API)...")
        
        response = requests.post(
            f"{API_BASE_URL}/upload-zip-from-url",
            json=payload,
            timeout=60
        )
        
        print(f"\n📊 Résultat:")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCÈS!")
            print(f"🔗 Conversation URL: {data.get('conversation_url', 'N/A')}")
            print(f"📁 Filename: {data.get('filename', 'N/A')}")
            return True
        else:
            print(f"❌ ÉCHEC: {response.status_code}")
            try:
                error_data = response.json()
                print(f"📄 Erreur: {error_data.get('detail', 'N/A')}")
            except:
                print(f"📄 Raw: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def main():
    print("🚀 TEST ÉTAPE PAR ÉTAPE")
    print("=" * 50)
    
    # Étape 1: Session
    session_ok = test_step_1_session()
    if not session_ok:
        print("\n❌ ARRÊT: Problème de session")
        return
    
    # Étape 2: Détection
    detection_ok = test_step_2_find_input()
    if not detection_ok:
        print("\n❌ ARRÊT: Problème de détection")
        return
    
    # Étape 3: Upload
    print("\n" + "=" * 50)
    upload_ok = test_step_3_minimal_upload()
    
    # Résumé
    print("\n" + "=" * 50)
    print("📊 RÉSUMÉ")
    print(f"🔐 Session: {'✅' if session_ok else '❌'}")
    print(f"🎯 Détection: {'✅' if detection_ok else '❌'}")
    print(f"📤 Upload: {'✅' if upload_ok else '❌'}")
    
    if session_ok and detection_ok and not upload_ok:
        print("\n🎯 DIAGNOSTIC: Le problème est dans la logique d'upload")
        print("💡 La session et la détection fonctionnent, mais l'upload échoue")
        print("🔍 Regardez les logs de l'API pendant l'étape 3 pour voir où ça coince")

if __name__ == "__main__":
    main()
