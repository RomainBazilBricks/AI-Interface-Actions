#!/usr/bin/env python3
"""
Script de test pour vérifier la correction du problème de double envoi
"""

import asyncio
import aiohttp
import time
import json
from typing import List, Dict, Any

API_BASE_URL = "https://64239c9ce527.ngrok-free.app"  # URL ngrok de votre serveur
TEST_MESSAGE = "Test de déduplication - " + str(int(time.time()))

async def send_request(session: aiohttp.ClientSession, request_data: dict, delay: float = 0) -> Dict[str, Any]:
    """Envoie une requête à l'API"""
    if delay > 0:
        await asyncio.sleep(delay)
    
    headers = {
        "Content-Type": "application/json",
        "ngrok-skip-browser-warning": "true"
    }
    
    try:
        start_time = time.time()
        async with session.post(f"{API_BASE_URL}/send-message-sync", 
                               json=request_data, 
                               headers=headers) as response:
            end_time = time.time()
            
            result = {
                "status_code": response.status,
                "response_time": round(end_time - start_time, 2),
                "timestamp": time.time()
            }
            
            if response.status == 200:
                data = await response.json()
                result["task_id"] = data.get("task_id")
                result["conversation_url"] = data.get("conversation_url")
                result["success"] = True
            else:
                result["error"] = await response.text()
                result["success"] = False
                
            return result
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": time.time(),
            "response_time": 0
        }

async def test_duplicate_prevention():
    """Test principal de prévention des doublons"""
    print("🧪 Test de prévention des doubles envois")
    print("=" * 50)
    
    # Configuration de la requête
    request_data = {
        "message": TEST_MESSAGE,
        "platform": "manus",
        "conversation_url": "",
        "wait_for_response": False,
        "timeout_seconds": 30
    }
    
    print(f"📝 Message de test: {TEST_MESSAGE}")
    print()
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Envois simultanés (doublons immédiats)
        print("🔄 Test 1: Envois simultanés (2 requêtes identiques)")
        
        # Lancer deux requêtes exactement en même temps
        tasks = [
            send_request(session, request_data),
            send_request(session, request_data, 0.1)  # Léger décalage pour simuler un double clic
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        print("Résultats:")
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"  Requête {i+1}: ❌ Exception - {result}")
            else:
                status = "✅ Succès" if result["success"] else "❌ Échec"
                if result["success"]:
                    print(f"  Requête {i+1}: {status} - Task ID: {result.get('task_id', 'N/A')} - Temps: {result['response_time']}s")
                else:
                    print(f"  Requête {i+1}: {status} - Erreur: {result.get('error', 'Inconnue')}")
        
        print()
        
        # Test 2: Vérifier le cache
        print("🔍 Test 2: Vérification du statut du cache")
        try:
            async with session.get(f"{API_BASE_URL}/admin/cache-status",
                                 headers={"ngrok-skip-browser-warning": "true"}) as response:
                if response.status == 200:
                    cache_data = await response.json()
                    print(f"  Requêtes en cache: {cache_data['cached_requests']}")
                    print(f"  Requêtes en cours: {cache_data['processing_requests']}")
                    print(f"  Âge max du cache: {cache_data['cache_max_age_seconds']}s")
                else:
                    print(f"  ❌ Erreur lors de la récupération du cache: {response.status}")
        except Exception as e:
            print(f"  ❌ Exception lors de la vérification du cache: {e}")
        
        print()
        
        # Test 3: Attendre et tester à nouveau (cache expiré)
        print("⏱️ Test 3: Test après expiration du cache (attente 5s)")
        await asyncio.sleep(5)
        
        # Modifier légèrement le message pour éviter le cache
        new_request_data = request_data.copy()
        new_request_data["message"] = TEST_MESSAGE + " - Test 3"
        
        result3 = await send_request(session, new_request_data)
        status3 = "✅ Succès" if result3["success"] else "❌ Échec"
        print(f"  Nouveau message: {status3}")
        if result3["success"]:
            print(f"    Task ID: {result3.get('task_id', 'N/A')}")
        else:
            print(f"    Erreur: {result3.get('error', 'Inconnue')}")
        
        print()
        
        # Test 4: Nettoyage du cache
        print("🧹 Test 4: Nettoyage du cache")
        try:
            async with session.post(f"{API_BASE_URL}/admin/clear-cache",
                                  headers={"ngrok-skip-browser-warning": "true"}) as response:
                if response.status == 200:
                    clear_data = await response.json()
                    print(f"  ✅ Cache vidé: {clear_data['cleared_cached_requests']} entrées supprimées")
                else:
                    print(f"  ❌ Erreur lors du nettoyage: {response.status}")
        except Exception as e:
            print(f"  ❌ Exception lors du nettoyage: {e}")

async def main():
    """Fonction principale"""
    print("🚀 Démarrage des tests de déduplication")
    print()
    
    # Vérifier que l'API est accessible
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/health",
                                 headers={"ngrok-skip-browser-warning": "true"}) as response:
                if response.status == 200:
                    health_data = await response.json()
                    print(f"✅ API accessible - Statut: {health_data.get('status', 'unknown')}")
                else:
                    print(f"❌ API non accessible - Code: {response.status}")
                    return
    except Exception as e:
        print(f"❌ Impossible de contacter l'API: {e}")
        return
    
    print()
    
    # Lancer les tests
    await test_duplicate_prevention()
    
    print()
    print("✨ Tests terminés")
    print()
    print("📋 Résumé des améliorations:")
    print("  • Protection contre les doubles clics dans l'automatisation navigateur")
    print("  • Déduplication des requêtes API avec cache temporaire")
    print("  • Endpoints d'administration pour gérer le cache")
    print("  • Logs détaillés pour le débogage")

if __name__ == "__main__":
    asyncio.run(main())
