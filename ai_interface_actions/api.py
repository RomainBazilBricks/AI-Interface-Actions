"""
API FastAPI pour l'automatisation des plateformes IA
"""
import asyncio
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

import structlog
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from ai_interface_actions import __version__
from ai_interface_actions.config import settings
from ai_interface_actions.models import (
    MessageRequest, MessageResponse, TaskStatusResponse, HealthResponse, TaskStatus
)
from ai_interface_actions.task_manager import task_manager
from ai_interface_actions.browser_automation import browser_manager
from ai_interface_actions.admin_routes import router as admin_router

# Configuration du logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Variable pour tracker le temps de démarrage
app_start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire du cycle de vie de l'application"""
    # Démarrage
    logger.info("Démarrage de l'application AI Interface Actions")
    
    try:
        # Initialisation du navigateur
        await browser_manager.initialize()
        logger.info("Navigateur initialisé avec succès")
    except Exception as e:
        logger.error("Erreur lors de l'initialisation du navigateur", error=str(e))
        # L'application peut fonctionner sans navigateur pour les endpoints de santé
    
    yield
    
    # Arrêt
    logger.info("Arrêt de l'application")
    try:
        await browser_manager.cleanup()
        logger.info("Ressources nettoyées avec succès")
    except Exception as e:
        logger.error("Erreur lors du nettoyage", error=str(e))


# Création de l'application FastAPI
app = FastAPI(
    title="AI Interface Actions",
    description="Outil d'automatisation pour les plateformes IA via leur interface web",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware personnalisé pour gérer CORS avec ngrok
@app.middleware("http")
async def cors_handler(request: Request, call_next):
    # Gérer les requêtes OPTIONS (preflight) explicitement
    if request.method == "OPTIONS":
        response = Response()
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Max-Age"] = "3600"
        return response
    
    # Traiter la requête normale
    response = await call_next(request)
    
    # Ajouter les headers CORS à toutes les réponses
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "*"
    
    return response

# Configuration CORS - Compatible avec ngrok et développement
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Autorise toutes les origines
    allow_credentials=False,  # Désactiver pour éviter les conflits avec allow_origins=["*"]
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=[
        "*",
        "Accept",
        "Accept-Language", 
        "Content-Type",
        "Content-Language",
        "Authorization",
        "X-Requested-With",
        "ngrok-skip-browser-warning",  # Header spécifique à ngrok
    ],
    expose_headers=["*"],
    max_age=3600,  # Cache preflight pendant 1 heure
)

# Inclure les routes d'administration
app.include_router(admin_router)


@app.get("/", response_model=Dict[str, str])
async def root():
    """Endpoint racine"""
    return {
        "message": "AI Interface Actions API",
        "version": __version__,
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Vérification de l'état de santé de l'API"""
    try:
        browser_ready = browser_manager.is_initialized
        uptime = time.time() - app_start_time
        
        return HealthResponse(
            status="healthy" if browser_ready else "degraded",
            version=__version__,
            browser_ready=browser_ready,
            uptime_seconds=uptime
        )
    except Exception as e:
        logger.error("Erreur lors de la vérification de santé", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@app.post("/send-message", response_model=MessageResponse)
async def send_message(request: MessageRequest, background_tasks: BackgroundTasks):
    """
    Envoie un message à une plateforme IA
    
    Ce endpoint crée une tâche en arrière-plan et retourne immédiatement un ID de tâche.
    Utilisez l'endpoint /task/{task_id} pour suivre le progrès.
    """
    try:
        logger.info("Nouvelle demande d'envoi de message", 
                   platform=request.platform, 
                   message_length=len(request.message))
        
        # Validation des paramètres
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Le message ne peut pas être vide")
        
        if request.platform != "manus":
            raise HTTPException(status_code=400, detail=f"Plateforme '{request.platform}' non supportée")
        
        # Création de la tâche
        task_params = {
            "message": request.message,
            "platform": request.platform,
            "conversation_url": request.conversation_url,
            "wait_for_response": request.wait_for_response,
            "timeout_seconds": request.timeout_seconds
        }
        
        task_id = task_manager.create_task("send_message", task_params)
        
        # Démarrage de la tâche en arrière-plan
        background_tasks.add_task(task_manager.execute_task, task_id)
        
        logger.info("Tâche créée et démarrée", task_id=task_id)
        
        return MessageResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message_sent=request.message,
            conversation_url=request.conversation_url if request.conversation_url else None,
            ai_response=None,
            execution_time_seconds=None,
            error_message=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur lors de la création de la tâche", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@app.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Récupère le statut d'une tâche
    
    Permet de suivre le progrès d'une tâche d'envoi de message.
    """
    try:
        task_status = task_manager.get_task_status(task_id)
        
        if not task_status:
            raise HTTPException(status_code=404, detail=f"Tâche '{task_id}' introuvable")
        
        return TaskStatusResponse(**task_status)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur lors de la récupération du statut", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@app.post("/send-message-sync", response_model=MessageResponse)
async def send_message_sync(request: MessageRequest):
    """
    Envoie un message de manière synchrone (attend la réponse)
    
    ⚠️ Attention: Cet endpoint peut prendre du temps à répondre (jusqu'à timeout_seconds).
    Utilisez plutôt l'endpoint asynchrone /send-message pour de meilleures performances.
    """
    try:
        logger.info("Demande d'envoi synchrone", 
                   platform=request.platform, 
                   message_length=len(request.message))
        
        # Validation des paramètres
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Le message ne peut pas être vide")
        
        if request.platform != "manus":
            raise HTTPException(status_code=400, detail=f"Plateforme '{request.platform}' non supportée")
        
        # Création et exécution immédiate de la tâche
        task_params = {
            "message": request.message,
            "platform": request.platform,
            "conversation_url": request.conversation_url,
            "wait_for_response": request.wait_for_response,
            "timeout_seconds": request.timeout_seconds
        }
        
        task_id = task_manager.create_task("send_message", task_params)
        
        # Exécution synchrone
        await task_manager.execute_task(task_id)
        
        # Récupération du résultat
        task = task_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=500, detail="Erreur lors de la récupération de la tâche")
        
        if task.status == TaskStatus.FAILED:
            raise HTTPException(status_code=500, detail=task.error_message or "Échec de la tâche")
        
        result = task.result or {}
        
        return MessageResponse(
            task_id=task_id,
            status=task.status,
            message_sent=request.message,
            conversation_url=result.get("conversation_url"),
            ai_response=result.get("ai_response"),
            execution_time_seconds=task.execution_time_seconds,
            error_message=task.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur lors de l'envoi synchrone", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@app.delete("/task/{task_id}")
async def cancel_task(task_id: str):
    """
    Annule une tâche en cours (si possible)
    
    Note: Les tâches déjà en cours d'exécution ne peuvent pas être annulées.
    """
    try:
        task = task_manager.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail=f"Tâche '{task_id}' introuvable")
        
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            raise HTTPException(status_code=400, detail="La tâche est déjà terminée")
        
        if task.status == TaskStatus.RUNNING:
            # Essayer d'annuler la tâche asyncio si elle existe
            async_task = task_manager.running_tasks.get(task_id)
            if async_task and not async_task.done():
                async_task.cancel()
                task.update_status(TaskStatus.FAILED, "Tâche annulée par l'utilisateur")
                logger.info("Tâche annulée", task_id=task_id)
                return {"message": "Tâche annulée avec succès"}
            else:
                raise HTTPException(status_code=400, detail="Impossible d'annuler la tâche en cours")
        
        # Tâche en attente, on peut l'annuler
        task.update_status(TaskStatus.FAILED, "Tâche annulée par l'utilisateur")
        logger.info("Tâche en attente annulée", task_id=task_id)
        
        return {"message": "Tâche annulée avec succès"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur lors de l'annulation", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@app.post("/setup-login")
async def setup_manual_login(background_tasks: BackgroundTasks):
    """
    Ouvre une page pour la connexion manuelle à Manus.ai
    
    Utilisez cet endpoint pour la première configuration.
    La session sera sauvegardée et réutilisée pendant 30 jours.
    """
    try:
        logger.info("Demande d'ouverture de page de connexion manuelle")
        
        # Ouvrir la page en mode visible
        url = await browser_manager.open_login_page()
        
        # Démarrer l'attente de connexion en arrière-plan
        background_tasks.add_task(browser_manager.wait_for_login_and_save_session, 10)
        
        return {
            "message": "Page de connexion ouverte dans votre navigateur",
            "url": url,
            "status": "waiting_for_login",
            "instructions": [
                "1. ✅ Une fenêtre Manus.ai s'est ouverte dans votre navigateur",
                "2. 👤 Connectez-vous avec vos identifiants Manus.ai", 
                "3. 💾 La session sera automatiquement détectée et sauvegardée",
                "4. ❌ Vous pouvez fermer la fenêtre après connexion",
                "5. 🚀 Vous pourrez ensuite utiliser l'API pendant 30 jours"
            ],
            "timeout_minutes": 10
        }
        
    except Exception as e:
        logger.error("Erreur lors de l'ouverture de la page de connexion", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@app.post("/send-message-quick")
async def send_message_quick_url(request: MessageRequest):
    """
    Envoie un message et retourne rapidement l'URL de conversation
    
    Idéal pour récupérer l'URL d'une nouvelle conversation sans attendre la réponse IA.
    La tâche continue en arrière-plan pour la réponse complète.
    """
    try:
        logger.info("Demande d'envoi rapide avec URL", 
                   platform=request.platform, 
                   has_conversation_url=bool(request.conversation_url))
        
        # Vérifier que le navigateur est initialisé
        if not browser_manager.is_initialized:
            raise HTTPException(
                status_code=503, 
                detail="Service temporairement indisponible : navigateur non initialisé. "
                      "Cela peut arriver si Playwright n'est pas installé correctement. "
                      "Veuillez contacter l'administrateur."
            )
        
        # Validation des paramètres
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Le message ne peut pas être vide")
        
        if request.platform != "manus":
            raise HTTPException(status_code=400, detail=f"Plateforme '{request.platform}' non supportée")
        
        # Si URL de conversation fournie, pas besoin de récupération rapide
        if request.conversation_url and request.conversation_url.strip():
            logger.info("URL de conversation déjà fournie, lancement tâche normale")
            
            # Lancer la tâche normale en arrière-plan
            task_params = {
                "message": request.message,
                "platform": request.platform,
                "conversation_url": request.conversation_url,
                "wait_for_response": request.wait_for_response,
                "timeout_seconds": request.timeout_seconds
            }
            
            task_id = task_manager.create_task("send_message", task_params)
            asyncio.create_task(task_manager.execute_task(task_id))
            
            return {
                "task_id": task_id,
                "status": "pending",
                "message_sent": request.message,
                "conversation_url": request.conversation_url,
                "quick_response": True,
                "message": "Message envoyé dans conversation existante"
            }
        
        else:
            # Nouvelle conversation : récupération rapide de l'URL
            logger.info("Nouvelle conversation, récupération rapide de l'URL")
            
            conversation_url = await browser_manager.get_conversation_url_quickly(
                message=request.message,
                conversation_url=request.conversation_url,
                max_wait_seconds=8
            )
            
            # Lancer la tâche complète en arrière-plan pour la réponse IA
            if request.wait_for_response:
                task_params = {
                    "message": request.message,
                    "platform": request.platform,
                    "conversation_url": conversation_url,
                    "wait_for_response": True,
                    "timeout_seconds": request.timeout_seconds
                }
                
                task_id = task_manager.create_task("send_message", task_params)
                asyncio.create_task(task_manager.execute_task(task_id))
            else:
                task_id = None
            
            return {
                "task_id": task_id,
                "status": "url_ready",
                "message_sent": request.message,
                "conversation_url": conversation_url,
                "quick_response": True,
                "message": f"Nouvelle conversation créée. URL disponible immédiatement.",
                "wait_for_ai_response": request.wait_for_response
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur lors de l'envoi rapide", error=str(e))
        
        # Fournir des messages d'erreur plus spécifiques
        if "Executable doesn't exist" in str(e) or "playwright" in str(e).lower():
            raise HTTPException(
                status_code=503, 
                detail="Service temporairement indisponible : navigateurs Playwright non installés. "
                      "L'administrateur doit exécuter 'playwright install' sur le serveur."
            )
        elif "non connecté" in str(e).lower() or "login" in str(e).lower():
            raise HTTPException(
                status_code=401,
                detail="Session expirée : veuillez utiliser l'endpoint /setup-login pour vous reconnecter à Manus.ai"
            )
        else:
            raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@app.get("/debug/credentials")
async def debug_credentials():
    """
    Debug: affiche les credentials récupérés et leur conversion
    """
    try:
        from ai_interface_actions.credentials_client import credentials_client
        
        if not credentials_client.is_configured():
            return {
                "error": "API credentials non configurée",
                "config": {
                    "base_url": credentials_client.base_url,
                    "has_api_key": bool(credentials_client.api_key)
                }
            }
        
        # Récupérer les credentials
        user_email = "romain.bazil@bricks.co"
        credential = await credentials_client.get_credential_for_platform("manus", user_email)
        
        if not credential:
            return {
                "error": "Aucun credential trouvé",
                "user_email": user_email
            }
        
        # Convertir en storage state
        storage_state = credentials_client.get_storage_state_from_credential(credential)
        
        return {
            "success": True,
            "user_email": user_email,
            "credential_id": credential.get("id"),
            "raw_session_data_keys": list(credential.get("sessionData", {}).keys()),
            "storage_state_preview": {
                "cookies_count": len(storage_state.get("cookies", [])) if storage_state else 0,
                "origins_count": len(storage_state.get("origins", [])) if storage_state else 0,
                "cookie_domains": [c["domain"] for c in storage_state.get("cookies", [])] if storage_state else [],
                "cookie_names": [c["name"] for c in storage_state.get("cookies", [])] if storage_state else []
            }
        }
        
    except Exception as e:
        logger.error("Erreur lors du debug des credentials", error=str(e))
        return {
            "error": f"Erreur interne: {str(e)}"
        }


@app.get("/session-status")
async def check_session_status():
    """
    Vérifie le statut de la session Manus.ai
    """
    try:
        from ai_interface_actions.credentials_client import credentials_client
        
        # Vérifier d'abord l'API de credentials (priorité)
        if credentials_client.is_configured():
            try:
                user_email = "romain.bazil@bricks.co"
                credential = await credentials_client.get_credential_for_platform("manus", user_email)
                
                if credential:
                    return {
                        "session_exists": True,
                        "status": "valid",
                        "source": "api_credentials",
                        "credential_id": credential.get("id"),
                        "user_email": user_email,
                        "last_used": credential.get("lastUsedAt"),
                        "message": "Session active depuis l'API de credentials"
                    }
            except Exception as e:
                logger.warning("Erreur lors de la vérification API credentials", error=str(e))
        
        # Fallback: vérifier le fichier local
        from pathlib import Path
        session_file = Path("session_state.json")
        
        if session_file.exists():
            # Lire la date de modification du fichier
            import os
            import datetime
            
            mtime = os.path.getmtime(session_file)
            last_updated = datetime.datetime.fromtimestamp(mtime)
            
            # Calculer l'âge de la session
            age_days = (datetime.datetime.now() - last_updated).days
            
            return {
                "session_exists": True,
                "source": "local_file",
                "last_updated": last_updated.isoformat(),
                "age_days": age_days,
                "expires_in_days": max(0, 30 - age_days),
                "status": "valid" if age_days < 30 else "expired",
                "message": "Session active (fichier local)" if age_days < 30 else "Session expirée - reconnexion requise"
            }
        else:
            return {
                "session_exists": False,
                "status": "no_session",
                "source": "none",
                "message": "Aucune session trouvée - utilisez /setup-login pour vous connecter"
            }
            
    except Exception as e:
        logger.error("Erreur lors de la vérification de session", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@app.get("/tasks", response_model=Dict[str, Any])
async def list_tasks(limit: int = 50, status_filter: str = None):
    """
    Liste les tâches récentes
    
    Args:
        limit: Nombre maximum de tâches à retourner (défaut: 50)
        status_filter: Filtrer par statut (pending, running, completed, failed)
    """
    try:
        tasks = []
        count = 0
        
        # Filtrer et limiter les tâches
        for task_id, task in task_manager.tasks.items():
            if status_filter and task.status != status_filter:
                continue
            
            if count >= limit:
                break
            
            tasks.append({
                "task_id": task_id,
                "status": task.status,
                "task_type": task.task_type,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
                "execution_time_seconds": task.execution_time_seconds
            })
            count += 1
        
        # Trier par date de création (plus récent en premier)
        tasks.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "tasks": tasks,
            "total": len(tasks),
            "running_tasks": len(task_manager.running_tasks)
        }
        
    except Exception as e:
        logger.error("Erreur lors de la liste des tâches", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@app.get("/debug/playwright-test")
async def debug_playwright_cookies():
    """
    Test approfondi de l'application des cookies par Playwright
    """
    try:
        from ai_interface_actions.credentials_client import credentials_client
        
        if not credentials_client.is_configured():
            return {"error": "API credentials non configurée"}
        
        user_email = "romain.bazil@bricks.co"
        credential = await credentials_client.get_credential_for_platform("manus", user_email)
        
        if not credential:
            return {"error": "Aucun credential trouvé"}
        
        storage_state = credentials_client.get_storage_state_from_credential(credential)
        if not storage_state:
            return {"error": "Impossible de convertir le credential"}
        
        # Test Playwright avec debugging détaillé
        from playwright.async_api import async_playwright
        
        # User-Agent réaliste (celui de votre JSON)
        user_agent = credential.get("sessionData", {}).get("user_agent", 
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                storage_state=storage_state,
                user_agent=user_agent,
                viewport={'width': 1440, 'height': 900},
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
            )
            page = await context.new_page()
            
            # 1. Vérifier les cookies AVANT navigation
            cookies_before = await context.cookies()
            
            # 2. Naviguer vers Manus.im
            await page.goto("https://www.manus.im/app", wait_until="networkidle")
            
            # 3. Attendre un peu pour les redirections
            await page.wait_for_timeout(2000)
            
            # 4. Vérifier les cookies APRÈS navigation
            cookies_after = await context.cookies()
            
            # 5. Vérifier le localStorage
            local_storage = await page.evaluate("""
                () => {
                    const items = {};
                    for (let i = 0; i < localStorage.length; i++) {
                        const key = localStorage.key(i);
                        items[key] = localStorage.getItem(key);
                    }
                    return items;
                }
            """)
            
            # 6. Vérifier l'URL finale (login ou app ?)
            final_url = page.url
            
            # 7. Vérifier si des éléments de connexion sont présents
            is_logged_in = await page.evaluate("""
                () => {
                    // Chercher des indicateurs de session active
                    const indicators = [
                        'div[data-testid="user-menu"]',
                        '.user-avatar',
                        '[data-testid="chat-input"]',
                        'button[aria-label*="profile"]',
                        '[data-testid="sidebar"]',
                        '.chat-container',
                        'button[data-testid="new-chat"]'
                    ];
                    
                    return indicators.some(selector => document.querySelector(selector) !== null);
                }
            """)
            
            # 8. Vérifier les erreurs console
            console_errors = []
            page.on("console", lambda msg: console_errors.append(f"{msg.type}: {msg.text}") if msg.type in ["error", "warning"] else None)
            
            # 9. Vérifier les requêtes réseau échouées
            failed_requests = []
            page.on("requestfailed", lambda req: failed_requests.append(f"{req.method} {req.url} - {req.failure}"))
            
            await browser.close()
            
            return {
                "status": "debug_complete_v2",
                "test_config": {
                    "user_agent": user_agent,
                    "extra_headers": True,
                    "viewport": "1440x900"
                },
                "storage_state_applied": {
                    "cookies_count": len(storage_state.get("cookies", [])),
                    "origins_count": len(storage_state.get("origins", []))
                },
                "playwright_results": {
                    "cookies_before_nav": len(cookies_before),
                    "cookies_after_nav": len(cookies_after),
                    "local_storage_items": len(local_storage),
                    "final_url": final_url,
                    "appears_logged_in": is_logged_in
                },
                "cookies_details": {
                    "before": [{"name": c["name"], "domain": c["domain"]} for c in cookies_before],
                    "after": [{"name": c["name"], "domain": c["domain"]} for c in cookies_after]
                },
                "local_storage_keys": list(local_storage.keys()) if local_storage else [],
                "console_errors": console_errors,
                "failed_requests": failed_requests,
                "diagnosis": {
                    "cookies_applied": len(cookies_before) > 0,
                    "cookies_persisted": len(cookies_after) > 0,
                    "local_storage_applied": len(local_storage) > 0,
                    "user_agent_realistic": user_agent != "",
                    "likely_issue": (
                        "Cookies non appliqués" if len(cookies_before) == 0 
                        else "Cookies perdus après navigation" if len(cookies_after) == 0
                        else "localStorage manquant" if len(local_storage) == 0
                        else "User-Agent détecté comme bot" if not is_logged_in and final_url.endswith("/login")
                        else "Session valide mais non reconnue par Manus.im"
                    )
                }
            }
            
    except Exception as e:
        logger.error("Erreur lors du debug Playwright", error=str(e))
        return {"error": f"Erreur debug: {str(e)}"}

@app.get("/debug/env-vars")
async def debug_environment_variables():
    """
    Debug des variables d'environnement MANUS_*
    """
    try:
        from ai_interface_actions.config import settings
        import os
        
        return {
            "status": "debug_env_vars",
            "config_values": {
                "manus_base_url": settings.manus_base_url,
                "use_persistent_context": settings.use_persistent_context,
                "headless": settings.headless,
            },
            "env_vars_raw": {
                "MANUS_SESSION_TOKEN": "***PRÉSENT***" if os.getenv("MANUS_SESSION_TOKEN") else "ABSENT",
                "MANUS_COOKIES": "***PRÉSENT***" if os.getenv("MANUS_COOKIES") else "ABSENT",
                "MANUS_LOCAL_STORAGE": "***PRÉSENT***" if os.getenv("MANUS_LOCAL_STORAGE") else "ABSENT",
                "MANUS_BASE_URL": os.getenv("MANUS_BASE_URL", "ABSENT"),
                "USE_PERSISTENT_CONTEXT": os.getenv("USE_PERSISTENT_CONTEXT", "ABSENT"),
            },
            "env_vars_lengths": {
                "MANUS_SESSION_TOKEN": len(os.getenv("MANUS_SESSION_TOKEN", "")),
                "MANUS_COOKIES": len(os.getenv("MANUS_COOKIES", "")),
                "MANUS_LOCAL_STORAGE": len(os.getenv("MANUS_LOCAL_STORAGE", "")),
            },
            "credentials_api_config": {
                "url": settings.credentials_api_url,
                "has_token": bool(settings.credentials_api_token),
                "is_configured": settings.credentials_api_url and settings.credentials_api_token
            }
        }
        
    except Exception as e:
        logger.error("Erreur lors du debug env vars", error=str(e))
        return {"error": f"Erreur debug env: {str(e)}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "ai_interface_actions.api:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    ) 