#!/usr/bin/env python3
"""
Script de test pour la fonctionnalité de contournement clipboard de Manus
"""

import asyncio
import aiohttp
import json

# URL de l'API (modifiez selon votre configuration)
API_BASE_URL = "https://64239c9ce527.ngrok-free.app"  # URL ngrok de votre VM

async def test_clipboard_workaround():
    """Test de la stratégie de contournement clipboard avec un long prompt"""
    
    # Créer un long prompt simple qui dépasse 3000 caractères
    base_message = "Ceci est un test de la fonctionnalité de contournement clipboard pour Manus. "
    
    # Répéter le message pour dépasser 3000 caractères
    long_prompt = base_message * 50  # Environ 3500 caractères
    
    # Ajouter une instruction simple à la fin
    long_prompt += "\n\nQuestion: Peux-tu confirmer que tu as bien reçu ce long message et me dire combien de caractères il contient approximativement ?"
    
    print(f"Longueur du prompt de test: {len(long_prompt)} caractères")
    
    if len(long_prompt) <= 3000:
        print("⚠️ Le prompt de test n'est pas assez long, ajoutons du contenu...")
        # Ajouter du contenu pour dépasser 3000 caractères
        additional_content = "\n\nCONTENU SUPPLÉMENTAIRE POUR ATTEINDRE LA LIMITE:\n" + "X" * (3100 - len(long_prompt))
        long_prompt += additional_content
    
    print(f"Longueur finale du prompt: {len(long_prompt)} caractères")
    
    # Données de test
    test_data = {
        "message": long_prompt,
        "platform": "manus",
        "conversation_url": "",  # Nouvelle conversation
        "wait_for_response": True,
        "timeout_seconds": 120,
        "use_clipboard_workaround": True  # Activer la stratégie de contournement
    }
    
    print("\n🚀 Test de la stratégie clipboard workaround...")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        try:
            # Envoyer la requête à l'API
            async with session.post(
                f"{API_BASE_URL}/send-message-sync",
                json=test_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                print(f"Status HTTP: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    print("✅ Succès!")
                    print(f"Task ID: {result.get('task_id')}")
                    print(f"Status: {result.get('status')}")
                    print(f"Message envoyé: {result.get('message_sent')}")
                    print(f"URL de conversation: {result.get('conversation_url')}")
                    print(f"Temps d'exécution: {result.get('execution_time_seconds')}s")
                    
                    if result.get('ai_response'):
                        print(f"Réponse IA (extrait): {result.get('ai_response')[:200]}...")
                    
                else:
                    error_text = await response.text()
                    print(f"❌ Erreur HTTP {response.status}: {error_text}")
                    
        except Exception as e:
            print(f"❌ Erreur de connexion: {str(e)}")
            print("Vérifiez que l'API est démarrée et accessible")

async def test_normal_vs_clipboard():
    """Compare l'envoi normal vs clipboard workaround"""
    
    short_message = "Bonjour, ceci est un test de message court."
    
    print("\n🔄 Comparaison: Message normal vs Clipboard workaround")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Message normal
        print("Test 1: Envoi normal...")
        test_normal = {
            "message": short_message,
            "platform": "manus",
            "wait_for_response": False,
            "use_clipboard_workaround": False
        }
        
        try:
            async with session.post(f"{API_BASE_URL}/send-message-sync", json=test_normal) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Normal - Temps: {result.get('execution_time_seconds')}s")
                else:
                    print(f"❌ Normal - Erreur: {response.status}")
        except Exception as e:
            print(f"❌ Normal - Exception: {str(e)}")
        
        # Attendre un peu entre les tests
        await asyncio.sleep(2)
        
        # Test 2: Même message avec clipboard workaround
        print("Test 2: Envoi avec clipboard workaround...")
        test_clipboard = {
            "message": short_message,
            "platform": "manus", 
            "wait_for_response": False,
            "use_clipboard_workaround": True
        }
        
        try:
            async with session.post(f"{API_BASE_URL}/send-message-sync", json=test_clipboard) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Clipboard - Temps: {result.get('execution_time_seconds')}s")
                else:
                    print(f"❌ Clipboard - Erreur: {response.status}")
        except Exception as e:
            print(f"❌ Clipboard - Exception: {str(e)}")

async def main():
    """Fonction principale de test"""
    print("🧪 Tests de la fonctionnalité Clipboard Workaround pour Manus")
    print("=" * 70)
    
    # Test principal avec long prompt
    await test_clipboard_workaround()
    
    # Test de comparaison
    await test_normal_vs_clipboard()
    
    print("\n✨ Tests terminés!")
    print("\nNote: Assurez-vous d'être connecté à Manus.ai dans le navigateur géré par l'API")

if __name__ == "__main__":
    asyncio.run(main())
