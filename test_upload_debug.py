#!/usr/bin/env python3
"""
Script de test pour diagnostiquer les problèmes d'upload ZIP
Crée un ZIP fictif et teste l'API étape par étape
"""

import asyncio
import json
import os
import tempfile
import zipfile
import requests
from pathlib import Path

# Configuration
API_BASE_URL = "https://64239c9ce527.ngrok-free.app"  # URL ngrok de la VM
TEST_MESSAGE = "Test d'upload avec ZIP fictif pour diagnostic"

def create_test_zip():
    """Crée un ZIP de test avec quelques fichiers fictifs"""
    print("🔧 Création d'un ZIP de test...")
    
    # Créer un dossier temporaire
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "test_diagnostic.zip")
    
    # Créer le ZIP avec quelques fichiers de test
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        # Ajouter quelques fichiers de test
        zipf.writestr("test1.txt", "Contenu du fichier de test 1\nCeci est un test de diagnostic.")
        zipf.writestr("test2.md", "# Fichier Markdown de test\n\nCeci est un **test** de diagnostic.")
        zipf.writestr("subfolder/test3.json", json.dumps({
            "test": True,
            "purpose": "diagnostic",
            "timestamp": "2025-01-21T12:00:00Z"
        }, indent=2))
    
    file_size = os.path.getsize(zip_path)
    print(f"✅ ZIP créé: {zip_path}")
    print(f"📊 Taille: {file_size} bytes ({file_size/1024:.1f} KB)")
    
    return zip_path

def test_api_health():
    """Test de l'état de santé de l'API"""
    print("\n🏥 Test de l'état de santé de l'API...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        print(f"📡 Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Status: {data.get('status', 'unknown')}")
            print(f"🔧 Browser Ready: {data.get('browser_ready', False)}")
            print(f"⏱️ Uptime: {data.get('uptime_seconds', 0):.1f}s")
            return True
        else:
            print(f"❌ API non disponible: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur de connexion API: {e}")
        return False

def test_session_status():
    """Test du diagnostic de session"""
    print("\n🔍 Test du diagnostic de session...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/debug/session-status", timeout=30)
        print(f"📡 Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"🔐 Session Status: {data.get('status', 'unknown')}")
            print(f"🌐 Browser Initialized: {data.get('browser_initialized', False)}")
            print(f"📄 Active Pages: {data.get('active_pages', 0)}")
            
            page_info = data.get('page_info', {})
            print(f"🔗 URL: {page_info.get('url', 'N/A')}")
            print(f"📝 Title: {page_info.get('title', 'N/A')}")
            print(f"🍪 Cookies: {page_info.get('cookies', 0)}")
            print(f"📝 Textareas: {len(page_info.get('textareas', []))}")
            
            # Afficher les textareas détectés
            textareas = page_info.get('textareas', [])
            if textareas:
                print("📝 Textareas détectés:")
                for i, ta in enumerate(textareas):
                    print(f"  {i+1}. Placeholder: '{ta.get('placeholder', 'N/A')}', Visible: {ta.get('visible', False)}")
            
            return data.get('status') == 'connected'
        else:
            print(f"❌ Diagnostic échoué: {response.status_code}")
            try:
                error_data = response.json()
                print(f"🔍 Détails: {error_data}")
            except:
                print(f"🔍 Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur de diagnostic: {e}")
        return False

def test_upload_zip_direct(zip_path):
    """Test d'upload direct du ZIP"""
    print(f"\n📤 Test d'upload direct du ZIP: {os.path.basename(zip_path)}")
    
    try:
        with open(zip_path, 'rb') as f:
            files = {'file': (os.path.basename(zip_path), f, 'application/zip')}
            data = {
                'message': TEST_MESSAGE,
                'platform': 'manus',
                'wait_for_response': 'false'
            }
            
            print("📡 Envoi de la requête...")
            response = requests.post(
                f"{API_BASE_URL}/upload-zip", 
                files=files, 
                data=data,
                timeout=120
            )
            
        print(f"📡 Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Upload réussi!")
            print(f"🆔 Task ID: {data.get('task_id', 'N/A')}")
            print(f"📊 Status: {data.get('status', 'N/A')}")
            print(f"🔗 Conversation URL: {data.get('conversation_url', 'N/A')}")
            print(f"📁 Filename: {data.get('filename', 'N/A')}")
            return True, data
        else:
            print(f"❌ Upload échoué: {response.status_code}")
            try:
                error_data = response.json()
                print(f"🔍 Erreur: {error_data.get('detail', 'N/A')}")
            except:
                print(f"🔍 Response: {response.text}")
            return False, None
            
    except Exception as e:
        print(f"❌ Erreur d'upload: {e}")
        return False, None

def test_upload_zip_from_url():
    """Test d'upload depuis URL (simulation)"""
    print(f"\n🌐 Test d'upload depuis URL...")
    
    # Pour ce test, on va utiliser une URL publique de test
    test_url = "https://github.com/RomainBazilBricks/AI-Interface-Actions/archive/refs/heads/main.zip"
    
    try:
        payload = {
            "zip_url": test_url,
            "message": f"{TEST_MESSAGE} (depuis URL)",
            "platform": "manus",
            "wait_for_response": False
        }
        
        print("📡 Envoi de la requête...")
        response = requests.post(
            f"{API_BASE_URL}/upload-zip-from-url",
            json=payload,
            timeout=120
        )
        
        print(f"📡 Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Upload depuis URL réussi!")
            print(f"🆔 Task ID: {data.get('task_id', 'N/A')}")
            print(f"📊 Status: {data.get('status', 'N/A')}")
            print(f"🔗 Conversation URL: {data.get('conversation_url', 'N/A')}")
            print(f"📁 Filename: {data.get('filename', 'N/A')}")
            return True, data
        else:
            print(f"❌ Upload depuis URL échoué: {response.status_code}")
            try:
                error_data = response.json()
                print(f"🔍 Erreur: {error_data.get('detail', 'N/A')}")
            except:
                print(f"🔍 Response: {response.text}")
            return False, None
            
    except Exception as e:
        print(f"❌ Erreur d'upload depuis URL: {e}")
        return False, None

def main():
    """Fonction principale de test"""
    print("🚀 DIAGNOSTIC COMPLET D'UPLOAD ZIP")
    print("=" * 50)
    
    # Étape 1: Créer le ZIP de test
    zip_path = create_test_zip()
    
    try:
        # Étape 2: Tester l'API
        if not test_api_health():
            print("\n❌ ARRÊT: API non disponible")
            return
        
        # Étape 3: Tester la session
        session_ok = test_session_status()
        if not session_ok:
            print("\n⚠️ ATTENTION: Problème de session détecté")
        
        # Étape 4: Tester l'upload direct
        print("\n" + "="*50)
        print("📤 TESTS D'UPLOAD")
        
        direct_success, direct_data = test_upload_zip_direct(zip_path)
        
        # Étape 5: Tester l'upload depuis URL
        url_success, url_data = test_upload_zip_from_url()
        
        # Résumé
        print("\n" + "="*50)
        print("📊 RÉSUMÉ DES TESTS")
        print(f"🏥 API Health: {'✅' if True else '❌'}")
        print(f"🔐 Session: {'✅' if session_ok else '❌'}")
        print(f"📤 Upload Direct: {'✅' if direct_success else '❌'}")
        print(f"🌐 Upload URL: {'✅' if url_success else '❌'}")
        
        if not direct_success and not url_success:
            print("\n❌ TOUS LES UPLOADS ONT ÉCHOUÉ")
            print("🔍 Vérifiez les logs de l'API pour plus de détails")
        elif direct_success or url_success:
            print("\n✅ AU MOINS UN UPLOAD A RÉUSSI")
            print("🎯 Le problème pourrait être spécifique à certains cas")
    
    finally:
        # Nettoyer le fichier temporaire
        try:
            os.unlink(zip_path)
            print(f"\n🧹 Fichier temporaire supprimé: {zip_path}")
        except:
            pass

if __name__ == "__main__":
    main()
