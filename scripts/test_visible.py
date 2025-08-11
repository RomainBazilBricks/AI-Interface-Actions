#!/usr/bin/env python3
"""
Script de test pour AI Interface Actions avec navigateur visible
Permet de voir le navigateur en action lors de l'envoi d'un message
"""

import asyncio
import httpx
import json
import time
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_MESSAGE = f"Test automatisé depuis le navigateur visible - {datetime.now().strftime('%H:%M:%S')}"

async def test_visible_browser():
    """Test avec navigateur visible"""
    print("🚀 Test AI Interface Actions - Navigateur Visible")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # 1. Vérifier que l'API fonctionne
            print("1️⃣  Vérification de l'état de l'API...")
            health_response = await client.get(f"{API_BASE_URL}/health")
            if health_response.status_code != 200:
                print("❌ API non accessible")
                return
            
            health_data = health_response.json()
            print(f"✅ API opérationnelle - Version: {health_data['version']}")
            print(f"   Browser ready: {health_data['browser_ready']}")
            
            # 2. Vérifier le statut de la session
            print("\n2️⃣  Vérification de la session Manus.ai...")
            session_response = await client.get(f"{API_BASE_URL}/session-status")
            session_data = session_response.json()
            print(f"   Session active: {session_data['session_exists']}")
            if session_data['session_exists'] and 'session_age_days' in session_data:
                print(f"   Âge de la session: {session_data['session_age_days']:.1f} jours")
            
            # 3. Configurer pour mode visible (temporairement)
            print("\n3️⃣  Configuration du navigateur en mode visible...")
            print("   ⚠️  Le navigateur va s'ouvrir en mode visible")
            print("   📱 Vous pourrez voir toutes les actions en temps réel")
            
            # 4. Envoyer le message en mode rapide
            print(f"\n4️⃣  Envoi du message: '{TEST_MESSAGE}'")
            print("   🔄 Lancement de l'automatisation...")
            
            # Utiliser l'endpoint rapide pour voir l'URL immédiatement
            message_data = {
                "message": TEST_MESSAGE,
                "platform": "manus",
                "wait_for_response": True,
                "timeout_seconds": 30
            }
            
            start_time = time.time()
            response = await client.post(
                f"{API_BASE_URL}/send-message-quick",
                json=message_data
            )
            
            if response.status_code == 200:
                result = response.json()
                elapsed = time.time() - start_time
                
                print(f"✅ Message envoyé avec succès ! ({elapsed:.1f}s)")
                print(f"   📝 Task ID: {result.get('task_id', 'N/A')}")
                print(f"   🔗 URL Conversation: {result.get('conversation_url', 'N/A')}")
                print(f"   📊 Status: {result.get('status', 'N/A')}")
                
                # 5. Si on a un task_id, suivre le progrès
                task_id = result.get('task_id')
                if task_id and result.get('wait_for_ai_response'):
                    print(f"\n5️⃣  Attente de la réponse IA (Task: {task_id})...")
                    
                    # Attendre la réponse complète
                    for attempt in range(12):  # 60 secondes max
                        await asyncio.sleep(5)
                        status_response = await client.get(f"{API_BASE_URL}/tasks/{task_id}/status")
                        
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            current_status = status_data.get('status')
                            
                            print(f"   📊 Status: {current_status}")
                            
                            if current_status == "completed":
                                result_data = status_data.get('result', {})
                                ai_response = result_data.get('ai_response', '')
                                
                                print("✅ Réponse IA reçue !")
                                print(f"   💬 Réponse: {ai_response[:200]}...")
                                break
                            elif current_status == "failed":
                                error = status_data.get('error', 'Erreur inconnue')
                                print(f"❌ Échec: {error}")
                                break
                        
                        if attempt == 11:
                            print("⏰ Timeout - La réponse IA prend plus de temps que prévu")
                
                print(f"\n🎯 Test terminé avec succès !")
                print(f"   🌐 URL de la conversation: {result.get('conversation_url', 'N/A')}")
                
            else:
                print(f"❌ Erreur lors de l'envoi: {response.status_code}")
                print(f"   Détails: {response.text}")
                
        except Exception as e:
            print(f"❌ Erreur durant le test: {str(e)}")

def main():
    """Point d'entrée principal"""
    print("🔧 Démarrage du test avec navigateur visible...")
    print("   ⚠️  Assurez-vous que HEADLESS_SETUP=false dans votre .env")
    print("   📱 Le navigateur va s'ouvrir automatiquement")
    print()
    
    # Lancer le test
    asyncio.run(test_visible_browser())

if __name__ == "__main__":
    main() 