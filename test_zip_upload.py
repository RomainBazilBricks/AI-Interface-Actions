#!/usr/bin/env python3
"""
Script de test pour l'upload de fichiers .zip vers Manus.ai
"""
import requests
import zipfile
import tempfile
import os
import time

def create_test_zip():
    """Crée un fichier .zip de test"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Ceci est un fichier de test pour l'upload vers Manus.ai\n")
        f.write("Contenu du fichier de test.\n")
        test_file = f.name
    
    zip_path = tempfile.mktemp(suffix='.zip')
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        zipf.write(test_file, 'test_file.txt')
    
    os.unlink(test_file)
    return zip_path

def test_upload_endpoint():
    """Test l'endpoint d'upload de fichiers .zip"""
    
    # Créer un fichier .zip de test
    zip_path = create_test_zip()
    
    try:
        print("🔬 Test de l'endpoint /upload-zip")
        print(f"📎 Fichier de test créé: {zip_path}")
        
        # URL de l'API (ajustez selon votre configuration)
        api_url = "http://localhost:8000/upload-zip"
        
        # Paramètres de la requête
        files = {'file': ('test_upload.zip', open(zip_path, 'rb'), 'application/zip')}
        data = {
            'message': 'Test d\'upload de fichier .zip via l\'API',
            'platform': 'manus',
            'wait_for_response': 'true',
            'timeout_seconds': '60'
        }
        
        print("📤 Envoi de la requête d'upload...")
        response = requests.post(api_url, files=files, data=data, timeout=10)
        
        print(f"📊 Status code: {response.status_code}")
        print(f"📋 Réponse: {response.json()}")
        
        if response.status_code == 200:
            result = response.json()
            task_id = result.get('task_id')
            
            if task_id:
                print(f"✅ Tâche créée avec succès: {task_id}")
                
                # Vérifier le statut de la tâche
                print("⏳ Vérification du statut de la tâche...")
                status_url = f"http://localhost:8000/task/{task_id}"
                
                for i in range(5):  # Vérifier 5 fois
                    time.sleep(2)
                    status_response = requests.get(status_url)
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        print(f"📈 Statut {i+1}/5: {status_data.get('status', 'unknown')}")
                        
                        if status_data.get('status') in ['completed', 'failed']:
                            print(f"🏁 Tâche terminée: {status_data}")
                            break
                    else:
                        print(f"❌ Erreur lors de la vérification du statut: {status_response.status_code}")
            else:
                print("❌ Pas de task_id dans la réponse")
        else:
            print(f"❌ Erreur HTTP: {response.status_code}")
            print(f"📄 Contenu: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Impossible de se connecter à l'API. Assurez-vous qu'elle est démarrée sur http://localhost:8000")
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
    finally:
        # Nettoyer le fichier de test
        if os.path.exists(zip_path):
            os.unlink(zip_path)
            print("🧹 Fichier de test nettoyé")

if __name__ == "__main__":
    test_upload_endpoint()
