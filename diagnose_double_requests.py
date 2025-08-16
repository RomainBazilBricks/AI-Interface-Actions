#!/usr/bin/env python3
"""
Script de diagnostic avancé pour analyser les doubles requêtes
"""

import asyncio
import aiohttp
import time
import json
from typing import List, Dict, Any

API_BASE_URL = "https://64239c9ce527.ngrok-free.app"

async def monitor_requests():
    """Surveille les requêtes en temps réel"""
    print("🔍 Surveillance des requêtes en temps réel")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # 1. Vider le cache pour commencer proprement
        print("🧹 Nettoyage du cache...")
        try:
            async with session.post(f"{API_BASE_URL}/admin/clear-cache",
                                  headers={"ngrok-skip-browser-warning": "true"}) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"  ✅ Cache vidé: {data.get('cleared_cached_requests', 0)} entrées")
                else:
                    print(f"  ❌ Erreur: {response.status}")
        except Exception as e:
            print(f"  ❌ Exception: {e}")
        
        print()
        
        # 2. Simuler des requêtes pour tester la déduplication
        print("🧪 Test de déduplication avec requêtes simulées")
        
        test_message = f"Test diagnostic - {int(time.time())}"
        
        # Test 1: Requête unique
        print(f"📝 Envoi d'une requête unique: '{test_message}'")
        try:
            async with session.post(f"{API_BASE_URL}/debug/simulate-request",
                                  params={"message": test_message, "client_ip": "192.168.1.100"},
                                  headers={"ngrok-skip-browser-warning": "true"}) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"  ✅ Hash: {data['request_hash']}, Doublon: {data['is_duplicate']}")
                else:
                    print(f"  ❌ Erreur: {response.status}")
        except Exception as e:
            print(f"  ❌ Exception: {e}")
        
        # Test 2: Même requête (devrait être détectée comme doublon)
        print(f"🔄 Envoi de la même requête (doublon attendu)")
        try:
            async with session.post(f"{API_BASE_URL}/debug/simulate-request",
                                  params={"message": test_message, "client_ip": "192.168.1.100"},
                                  headers={"ngrok-skip-browser-warning": "true"}) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"  ✅ Hash: {data['request_hash']}, Doublon: {data['is_duplicate']}")
                else:
                    print(f"  ❌ Erreur: {response.status}")
        except Exception as e:
            print(f"  ❌ Exception: {e}")
        
        print()
        
        # 3. Vérifier le statut du cache
        print("📊 Statut du cache après tests")
        try:
            async with session.get(f"{API_BASE_URL}/admin/cache-status",
                                 headers={"ngrok-skip-browser-warning": "true"}) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"  📦 Requêtes en cache: {data['cached_requests']}")
                    print(f"  ⏳ Requêtes en cours: {data['processing_requests']}")
                    print(f"  ⏰ Âge max: {data['cache_max_age_seconds']}s")
                    
                    if data['cache_entries']:
                        print("  📋 Entrées du cache:")
                        for entry in data['cache_entries']:
                            print(f"    - {entry['hash']}: {entry['age_seconds']}s")
                else:
                    print(f"  ❌ Erreur: {response.status}")
        except Exception as e:
            print(f"  ❌ Exception: {e}")
        
        print()
        
        # 4. Test avec vraie requête send-message
        print("🚀 Test avec vraie requête /send-message")
        real_test_message = f"Diagnostic réel - {int(time.time())}"
        
        request_data = {
            "message": real_test_message,
            "platform": "manus",
            "conversation_url": "",
            "wait_for_response": False,
            "timeout_seconds": 30
        }
        
        print(f"📤 Envoi: '{real_test_message}'")
        
        # Envoyer deux requêtes rapidement
        start_time = time.time()
        
        tasks = []
        for i in range(2):
            task = send_tracked_request(session, request_data, i)
            tasks.append(task)
            if i == 0:
                await asyncio.sleep(0.1)  # Petit délai entre les requêtes
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"⏱️ Temps total: {total_time:.3f}s")
        print("📋 Résultats:")
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"  Requête {i+1}: ❌ Exception - {result}")
            else:
                status = "✅ Succès" if result.get("success", False) else "❌ Échec"
                print(f"  Requête {i+1}: {status}")
                print(f"    Status: {result.get('status_code', 'N/A')}")
                print(f"    Temps: {result.get('response_time', 0):.3f}s")
                print(f"    Request-ID: {result.get('request_id', 'N/A')}")
                if 'error' in result:
                    print(f"    Erreur: {result['error'][:100]}...")

async def send_tracked_request(session: aiohttp.ClientSession, request_data: dict, request_num: int) -> Dict[str, Any]:
    """Envoie une requête avec tracking détaillé"""
    headers = {
        "Content-Type": "application/json",
        "ngrok-skip-browser-warning": "true",
        "X-Debug-Request": f"diagnostic-{request_num}"
    }
    
    try:
        start_time = time.time()
        async with session.post(f"{API_BASE_URL}/send-message", 
                               json=request_data, 
                               headers=headers) as response:
            end_time = time.time()
            
            result = {
                "success": response.status == 200,
                "status_code": response.status,
                "response_time": round(end_time - start_time, 3),
                "request_id": response.headers.get("X-Request-ID", "unknown"),
                "timestamp": time.time()
            }
            
            if response.status == 200:
                data = await response.json()
                result["task_id"] = data.get("task_id")
                result["conversation_url"] = data.get("conversation_url")
            else:
                result["error"] = await response.text()
                
            return result
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": time.time(),
            "response_time": 0,
            "request_id": "exception"
        }

async def main():
    """Fonction principale de diagnostic"""
    print("🔬 Diagnostic avancé des doubles requêtes")
    print("=" * 60)
    print()
    
    # Vérifier la connectivité
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/health",
                                 headers={"ngrok-skip-browser-warning": "true"}) as response:
                if response.status == 200:
                    health_data = await response.json()
                    print(f"✅ API accessible - Statut: {health_data.get('status', 'unknown')}")
                    print(f"🔗 URL: {API_BASE_URL}")
                else:
                    print(f"❌ API non accessible - Code: {response.status}")
                    return
    except Exception as e:
        print(f"❌ Impossible de contacter l'API: {e}")
        return
    
    print()
    
    # Lancer la surveillance
    await monitor_requests()
    
    print()
    print("✨ Diagnostic terminé")
    print()
    print("📋 Recommandations:")
    print("  1. Vérifiez les logs détaillés de votre API")
    print("  2. Si vous voyez encore des doublons, le problème vient du côté client")
    print("  3. Vérifiez votre code JavaScript pour des event listeners multiples")
    print("  4. Utilisez les endpoints /admin/cache-status pour surveiller")

if __name__ == "__main__":
    asyncio.run(main())
