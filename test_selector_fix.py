#!/usr/bin/env python3
"""
Test rapide pour vérifier si le sélecteur fonctionne maintenant
"""

import requests
import json

API_BASE_URL = "http://127.0.0.1:8000"

def test_simple_upload():
    """Test avec un petit ZIP simple"""
    print("🧪 Test de l'upload avec sélecteur corrigé...")
    
    # Utiliser une URL ZIP plus petite pour test rapide
    payload = {
        "zip_url": "https://github.com/octocat/Hello-World/archive/refs/heads/master.zip",
        "message": "Test rapide avec sélecteur corrigé",
        "platform": "manus",
        "conversation_url": "",
        "wait_for_response": False,
        "timeout_seconds": 30
    }
    
    print(f"📡 Test avec payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/upload-zip-from-url",
            json=payload,
            timeout=60
        )
        
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCÈS!")
            print(f"🔗 Conversation URL: {data.get('conversation_url', 'N/A')}")
            print(f"📁 Filename: {data.get('filename', 'N/A')}")
            print(f"📊 Status: {data.get('status', 'N/A')}")
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

if __name__ == "__main__":
    print("🚀 TEST SÉLECTEUR CORRIGÉ")
    print("=" * 40)
    
    success = test_simple_upload()
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 LE SÉLECTEUR FONCTIONNE!")
        print("💡 Le problème était bien le placeholder manquant")
    else:
        print("😞 Toujours un problème...")
        print("🔍 Vérifiez les logs de l'API pour plus de détails")
