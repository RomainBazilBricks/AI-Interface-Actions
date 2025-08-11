#!/usr/bin/env python3
"""
Script de test pour AI Interface Actions
Usage: python scripts/test.py
"""

import asyncio
import json
import sys
import time
from pathlib import Path

import httpx
import structlog

# Configuration du logging pour les tests
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger(__name__)


class AIInterfaceActionsTest:
    """Classe de test pour AI Interface Actions"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.test_results = []
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def add_test_result(self, test_name: str, success: bool, message: str = "", duration: float = 0.0):
        """Ajoute un résultat de test"""
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "duration": duration
        })
        
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} {test_name}", message=message, duration=f"{duration:.2f}s")
    
    async def test_health_endpoint(self):
        """Test de l'endpoint de santé"""
        start_time = time.time()
        test_name = "Health Endpoint"
        
        try:
            response = await self.client.get(f"{self.base_url}/health")
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if "status" in data and "version" in data:
                    self.add_test_result(test_name, True, f"Status: {data['status']}, Version: {data['version']}", duration)
                else:
                    self.add_test_result(test_name, False, "Réponse manquante champs requis", duration)
            else:
                self.add_test_result(test_name, False, f"Code HTTP: {response.status_code}", duration)
                
        except Exception as e:
            duration = time.time() - start_time
            self.add_test_result(test_name, False, f"Exception: {str(e)}", duration)
    
    async def test_root_endpoint(self):
        """Test de l'endpoint racine"""
        start_time = time.time()
        test_name = "Root Endpoint"
        
        try:
            response = await self.client.get(f"{self.base_url}/")
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "version" in data:
                    self.add_test_result(test_name, True, f"Message: {data['message']}", duration)
                else:
                    self.add_test_result(test_name, False, "Réponse malformée", duration)
            else:
                self.add_test_result(test_name, False, f"Code HTTP: {response.status_code}", duration)
                
        except Exception as e:
            duration = time.time() - start_time
            self.add_test_result(test_name, False, f"Exception: {str(e)}", duration)
    
    async def test_swagger_docs(self):
        """Test de la documentation Swagger"""
        start_time = time.time()
        test_name = "Swagger Documentation"
        
        try:
            response = await self.client.get(f"{self.base_url}/docs")
            duration = time.time() - start_time
            
            if response.status_code == 200:
                if "swagger" in response.text.lower() or "openapi" in response.text.lower():
                    self.add_test_result(test_name, True, "Documentation accessible", duration)
                else:
                    self.add_test_result(test_name, False, "Contenu inattendu", duration)
            else:
                self.add_test_result(test_name, False, f"Code HTTP: {response.status_code}", duration)
                
        except Exception as e:
            duration = time.time() - start_time
            self.add_test_result(test_name, False, f"Exception: {str(e)}", duration)
    
    async def test_send_message_validation(self):
        """Test de validation des paramètres d'envoi de message"""
        start_time = time.time()
        test_name = "Message Validation"
        
        try:
            # Test avec message vide
            response = await self.client.post(
                f"{self.base_url}/send-message",
                json={"message": "", "platform": "manus"}
            )
            duration = time.time() - start_time
            
            if response.status_code == 400:
                self.add_test_result(test_name, True, "Validation du message vide fonctionne", duration)
            else:
                self.add_test_result(test_name, False, f"Code HTTP inattendu: {response.status_code}", duration)
                
        except Exception as e:
            duration = time.time() - start_time
            self.add_test_result(test_name, False, f"Exception: {str(e)}", duration)
    
    async def test_task_status_endpoint(self):
        """Test de l'endpoint de statut des tâches"""
        start_time = time.time()
        test_name = "Task Status Endpoint"
        
        try:
            # Test avec un ID de tâche inexistant
            fake_task_id = "00000000-0000-0000-0000-000000000000"
            response = await self.client.get(f"{self.base_url}/task/{fake_task_id}")
            duration = time.time() - start_time
            
            if response.status_code == 404:
                self.add_test_result(test_name, True, "Gestion des tâches inexistantes fonctionne", duration)
            else:
                self.add_test_result(test_name, False, f"Code HTTP inattendu: {response.status_code}", duration)
                
        except Exception as e:
            duration = time.time() - start_time
            self.add_test_result(test_name, False, f"Exception: {str(e)}", duration)
    
    async def test_tasks_list_endpoint(self):
        """Test de l'endpoint de liste des tâches"""
        start_time = time.time()
        test_name = "Tasks List Endpoint"
        
        try:
            response = await self.client.get(f"{self.base_url}/tasks")
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if "tasks" in data and "total" in data:
                    self.add_test_result(test_name, True, f"Nombre de tâches: {data['total']}", duration)
                else:
                    self.add_test_result(test_name, False, "Réponse malformée", duration)
            else:
                self.add_test_result(test_name, False, f"Code HTTP: {response.status_code}", duration)
                
        except Exception as e:
            duration = time.time() - start_time
            self.add_test_result(test_name, False, f"Exception: {str(e)}", duration)
    
    async def run_all_tests(self):
        """Exécute tous les tests"""
        logger.info("🚀 Début des tests AI Interface Actions")
        
        tests = [
            self.test_health_endpoint,
            self.test_root_endpoint,
            self.test_swagger_docs,
            self.test_send_message_validation,
            self.test_task_status_endpoint,
            self.test_tasks_list_endpoint
        ]
        
        for test in tests:
            try:
                await test()
            except Exception as e:
                test_name = test.__name__.replace("test_", "").replace("_", " ").title()
                self.add_test_result(test_name, False, f"Erreur inattendue: {str(e)}")
        
        self.print_summary()
    
    def print_summary(self):
        """Affiche le résumé des tests"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print("\n" + "="*60)
        print("📊 RÉSUMÉ DES TESTS")
        print("="*60)
        
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            print(f"{status} {result['test']:<30} ({result['duration']:.2f}s)")
            if result["message"]:
                print(f"   └─ {result['message']}")
        
        print("\n" + "-"*60)
        print(f"📈 TOTAL: {total_tests} tests")
        print(f"✅ RÉUSSIS: {passed_tests}")
        print(f"❌ ÉCHOUÉS: {failed_tests}")
        print(f"📊 TAUX DE RÉUSSITE: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests == 0:
            print("🎉 TOUS LES TESTS SONT PASSÉS !")
            return True
        else:
            print("⚠️  CERTAINS TESTS ONT ÉCHOUÉ")
            return False


async def wait_for_server(base_url: str, max_attempts: int = 30, delay: float = 1.0):
    """Attend que le serveur soit disponible"""
    logger.info("⏳ Attente du démarrage du serveur...")
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for attempt in range(max_attempts):
            try:
                response = await client.get(f"{base_url}/health")
                if response.status_code == 200:
                    logger.info("✅ Serveur disponible")
                    return True
            except:
                pass
            
            if attempt < max_attempts - 1:
                await asyncio.sleep(delay)
        
        logger.error("❌ Serveur non disponible après {max_attempts} tentatives")
        return False


def check_server_running(base_url: str) -> bool:
    """Vérifie si le serveur fonctionne"""
    import subprocess
    import socket
    from urllib.parse import urlparse
    
    parsed_url = urlparse(base_url)
    host = parsed_url.hostname or "localhost"
    port = parsed_url.port or 8000
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        result = sock.connect_ex((host, port))
        return result == 0
    except:
        return False
    finally:
        sock.close()


async def main():
    """Fonction principale"""
    print("🧪 AI Interface Actions - Tests automatisés")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    # Vérifier si le serveur fonctionne
    if not check_server_running(base_url):
        print("❌ Serveur non détecté sur http://localhost:8000")
        print("\n💡 Pour démarrer le serveur :")
        print("   python -m ai_interface_actions.main")
        print("   # ou")
        print("   uvicorn ai_interface_actions.api:app --reload")
        sys.exit(1)
    
    # Attendre que le serveur soit prêt
    if not await wait_for_server(base_url):
        print("❌ Impossible de se connecter au serveur")
        sys.exit(1)
    
    # Exécuter les tests
    async with AIInterfaceActionsTest(base_url) as tester:
        success = await tester.run_all_tests()
    
    # Code de sortie basé sur le résultat des tests
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrompus par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Erreur fatale: {e}")
        sys.exit(1) 