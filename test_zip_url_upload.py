#!/usr/bin/env python3
"""
Script de test pour l'upload de fichiers .zip depuis URL vers Manus.ai
"""
import requests
import time
import json

def test_zip_url_upload():
    """Test l'endpoint d'upload de fichiers .zip depuis URL"""
    
    # URL de l'API
    api_url = "http://localhost:8000/upload-zip-from-url"
    
    # URL d'un fichier .zip de test (vous pouvez remplacer par n'importe quelle URL)
    # Pour ce test, on utilise une URL d'exemple - remplacez par une vraie URL
    test_zip_url = "https://github.com/octocat/Hello-World/archive/refs/heads/master.zip"
    
    print("🔬 Test de l'endpoint /upload-zip-from-url")
    print(f"📎 URL de test: {test_zip_url}")
    
    # Paramètres de la requête
    data = {
        "zip_url": test_zip_url,
        "message": "Test d'upload de fichier .zip depuis URL - analyse le contenu de ce repository GitHub",
        "platform": "manus",
        "wait_for_response": True,
        "timeout_seconds": 60
    }
    
    try:
        print("📤 Envoi de la requête d'upload depuis URL...")
        response = requests.post(
            api_url, 
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"📊 Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"📋 Réponse: {json.dumps(result, indent=2)}")
            
            task_id = result.get('task_id')
            if task_id:
                print(f"✅ Tâche créée avec succès: {task_id}")
                
                # Vérifier le statut de la tâche
                print("⏳ Vérification du statut de la tâche...")
                status_url = f"http://localhost:8000/task/{task_id}"
                
                for i in range(10):  # Vérifier 10 fois max
                    time.sleep(3)
                    status_response = requests.get(status_url)
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        status = status_data.get('status', 'unknown')
                        print(f"📈 Statut {i+1}/10: {status}")
                        
                        if status in ['completed', 'failed']:
                            print(f"🏁 Tâche terminée: {json.dumps(status_data, indent=2)}")
                            break
                            
                        if status == 'failed':
                            print(f"❌ Erreur: {status_data.get('error_message', 'Erreur inconnue')}")
                            break
                    else:
                        print(f"❌ Erreur lors de la vérification du statut: {status_response.status_code}")
            else:
                print("❌ Pas de task_id dans la réponse")
        else:
            print(f"❌ Erreur HTTP: {response.status_code}")
            try:
                error_data = response.json()
                print(f"📄 Détail: {error_data}")
            except:
                print(f"📄 Contenu: {response.text}")
                
    except requests.exceptions.ConnectionError:
        print("❌ Impossible de se connecter à l'API. Assurez-vous qu'elle est démarrée sur http://localhost:8000")
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")

def test_with_custom_url():
    """Permet de tester avec une URL personnalisée"""
    print("\n🎯 Test avec URL personnalisée")
    zip_url = input("Entrez l'URL du fichier .zip à tester: ").strip()
    
    if not zip_url:
        print("❌ URL vide, test annulé")
        return
    
    api_url = "http://localhost:8000/upload-zip-from-url"
    data = {
        "zip_url": zip_url,
        "message": f"Test d'upload depuis {zip_url}",
        "platform": "manus",
        "wait_for_response": True,
        "timeout_seconds": 60
    }
    
    try:
        response = requests.post(api_url, json=data, headers={"Content-Type": "application/json"})
        print(f"📊 Status: {response.status_code}")
        print(f"📋 Réponse: {response.json()}")
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    print("🚀 Tests d'upload de fichiers .zip depuis URL")
    print("=" * 50)
    
    # Test avec URL prédéfinie
    test_zip_url_upload()
    
    # Option pour test personnalisé
    if input("\n🤔 Voulez-vous tester avec une URL personnalisée ? (y/N): ").lower().startswith('y'):
        test_with_custom_url()
    
    print("\n✅ Tests terminés")
