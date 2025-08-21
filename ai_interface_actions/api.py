"""
API FastAPI pour l'automatisation des plateformes IA
"""
import asyncio
import time
import hashlib
import tempfile
import os
from contextlib import asynccontextmanager
from typing import Dict, Any, Set

import structlog
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Response, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

from ai_interface_actions import __version__
from ai_interface_actions.config import settings
from ai_interface_actions.models import (
    MessageRequest, TaskStatusResponse, HealthResponse, TaskStatus,
    FileUploadRequest, FileUploadResponse, ZipUrlUploadRequest
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

# Système de déduplication des requêtes
request_cache: Dict[str, Dict[str, Any]] = {}
processing_requests: Set[str] = set()

def generate_request_hash(request: MessageRequest, client_ip: str = "", user_agent: str = "") -> str:
    """Génère un hash unique pour une requête de message"""
    # Inclure plus d'informations pour une meilleure déduplication
    content = f"{request.message}|{request.platform}|{request.conversation_url}|{client_ip}|{user_agent[:50]}"
    return hashlib.md5(content.encode()).hexdigest()

def is_duplicate_request(request_hash: str, max_age_seconds: int = 15) -> bool:  # Réduit à 15 secondes
    """Vérifie si une requête est un doublon récent"""
    current_time = time.time()
    
    # Nettoyer les anciennes entrées
    expired_keys = []
    for key, data in request_cache.items():
        if current_time - data["timestamp"] > max_age_seconds:
            expired_keys.append(key)
    
    for key in expired_keys:
        request_cache.pop(key, None)
        processing_requests.discard(key)
    
    is_duplicate = request_hash in request_cache or request_hash in processing_requests
    
    if is_duplicate:
        logger.warning("Requête dupliquée détectée", 
                      request_hash=request_hash[:8],
                      in_cache=request_hash in request_cache,
                      in_processing=request_hash in processing_requests)
    
    return is_duplicate

def mark_request_processing(request_hash: str) -> None:
    """Marque une requête comme en cours de traitement"""
    processing_requests.add(request_hash)

def complete_request(request_hash: str, result: Dict[str, Any]) -> None:
    """Marque une requête comme terminée et cache le résultat"""
    processing_requests.discard(request_hash)
    request_cache[request_hash] = {
        "timestamp": time.time(),
        "result": result
    }


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

# Middleware personnalisé pour gérer CORS avec ngrok et logging détaillé
@app.middleware("http")
async def cors_handler(request: Request, call_next):
    # Générer un ID unique pour cette requête
    import uuid
    request_id = str(uuid.uuid4())[:8]
    
    # Logging détaillé de la requête
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    logger.info("Requête reçue", 
               request_id=request_id,
               method=request.method,
               url=str(request.url),
               client_ip=client_ip,
               user_agent=user_agent[:100],  # Limiter la longueur
               headers=dict(request.headers))
    
    # Gérer les requêtes OPTIONS (preflight) explicitement
    if request.method == "OPTIONS":
        logger.info("Requête OPTIONS (preflight CORS)", request_id=request_id)
        response = Response()
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Max-Age"] = "3600"
        response.headers["X-Request-ID"] = request_id
        return response
    
    # Traiter la requête normale
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Logging de la réponse
    logger.info("Réponse envoyée", 
               request_id=request_id,
               status_code=response.status_code,
               process_time=round(process_time, 3))
    
    # Ajouter les headers CORS à toutes les réponses
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["X-Request-ID"] = request_id
    
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


# Endpoint unique /send-message - comportement intelligent selon les paramètres


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


@app.get("/debug/session-status")
async def debug_session_status():
    """
    Endpoint de diagnostic pour vérifier l'état de session Manus.ai
    
    Utile pour diagnostiquer les problèmes de connexion et credentials
    """
    try:
        logger.info("🔍 Début du diagnostic de session")
        
        # Import local pour éviter les dépendances circulaires
        from ai_interface_actions.browser_automation import browser_manager
        
        # Initialiser le navigateur si nécessaire
        await browser_manager.ensure_initialized()
        
        # Créer une page de test
        page = await browser_manager._get_or_create_page("")
        
        # Naviguer vers Manus.ai
        logger.info("Navigation vers Manus.ai pour diagnostic")
        await page.goto(settings.manus_base_url, wait_until="networkidle", timeout=15000)
        
        # Collecter les informations de diagnostic
        diagnostic_info = await page.evaluate("""
            () => {
                return {
                    url: window.location.href,
                    title: document.title,
                    cookies: document.cookie ? document.cookie.split(';').length : 0,
                    localStorage: Object.keys(localStorage).length,
                    sessionStorage: Object.keys(sessionStorage).length,
                    textareas: Array.from(document.querySelectorAll('textarea')).map(t => ({
                        placeholder: t.placeholder,
                        visible: t.offsetParent !== null,
                        disabled: t.disabled
                    })),
                    loginIndicators: {
                        hasLoginButton: !!document.querySelector('button:has-text("Se connecter"), button:has-text("Sign in"), button:has-text("Login")'),
                        hasEmailInput: !!document.querySelector('input[type="email"]'),
                        hasPasswordInput: !!document.querySelector('input[type="password"]'),
                    },
                    bodyText: document.body.innerText.substring(0, 1000)
                };
            }
        """)
        
        # Vérifier les credentials depuis les variables d'environnement
        credentials_info = {
            "manus_cookies_configured": bool(settings.manus_cookies),
            "manus_session_token_configured": bool(settings.manus_session_token),
            "manus_base_url": settings.manus_base_url
        }
        
        # Déterminer le statut de connexion
        is_logged_in = (
            not diagnostic_info["loginIndicators"]["hasLoginButton"] and
            not diagnostic_info["loginIndicators"]["hasEmailInput"] and
            len(diagnostic_info["textareas"]) > 0
        )
        
        logger.info("✅ Diagnostic de session terminé", 
                   logged_in=is_logged_in,
                   url=diagnostic_info["url"])
        
        return {
            "status": "connected" if is_logged_in else "disconnected",
            "timestamp": time.time(),
            "page_info": diagnostic_info,
            "credentials_info": credentials_info,
            "browser_initialized": browser_manager.is_initialized,
            "active_pages": len(browser_manager.active_pages)
        }
        
    except Exception as e:
        logger.error("Erreur lors du diagnostic de session", error=str(e))
        return {
            "status": "error",
            "error": str(e),
            "timestamp": time.time(),
            "browser_initialized": browser_manager.is_initialized if 'browser_manager' in locals() else False
        }


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


@app.post("/upload-zip", response_model=FileUploadResponse)
async def upload_zip_file(
    file: UploadFile = File(...),
    message: str = Form(default=""),
    platform: str = Form(default="manus"),
    conversation_url: str = Form(default=""),
    wait_for_response: bool = Form(default=True),
    timeout_seconds: int = Form(default=60)
):
    """
    Upload un fichier .zip vers Manus.ai avec message optionnel
    
    📎 Fonctionnalités :
    - ✅ Upload de fichiers .zip uniquement
    - ✅ Message d'accompagnement optionnel
    - ✅ Réutilisation de conversations existantes
    - ✅ Traitement asynchrone avec suivi de tâche
    - ✅ Gestion automatique des erreurs
    
    📝 Utilisation :
    ```bash
    curl -X POST "http://localhost:8000/upload-zip" \
      -F "file=@mon_fichier.zip" \
      -F "message=Analyse ce fichier zip" \
      -F "platform=manus"
    ```
    """
    try:
        logger.info("Début d'upload de fichier .zip", 
                   filename=file.filename,
                   content_type=file.content_type,
                   message_length=len(message))
        
        # Validation du fichier
        if not file.filename:
            raise HTTPException(status_code=400, detail="Nom de fichier manquant")
        
        if not file.filename.lower().endswith('.zip'):
            raise HTTPException(status_code=400, detail="Seuls les fichiers .zip sont acceptés")
        
        # Validation des paramètres
        if timeout_seconds < 10 or timeout_seconds > 300:
            raise HTTPException(status_code=400, detail="timeout_seconds doit être entre 10 et 300")
        
        # Lire le contenu du fichier
        file_content = await file.read()
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Fichier vide")
        
        # Limite de taille (500MB par exemple)
        max_size = 500 * 1024 * 1024  # 500MB
        if len(file_content) > max_size:
            raise HTTPException(status_code=400, detail=f"Fichier trop volumineux (max: {max_size//1024//1024}MB)")
        
        # Créer un fichier temporaire
        temp_file_fd, temp_file_path = tempfile.mkstemp(suffix='.zip', prefix='manus_upload_')
        try:
            with os.fdopen(temp_file_fd, 'wb') as temp_file:
                temp_file.write(file_content)
            
            # Exécution SYNCHRONE comme send-message
            logger.info("Début d'upload synchrone de fichier", 
                       filename=file.filename)
            
            # Import local pour éviter les dépendances circulaires
            from ai_interface_actions.browser_automation import browser_manager
            
            # Upload direct et synchrone
            result = await browser_manager.upload_zip_file_to_manus(
                file_path=temp_file_path,
                message=message,
                conversation_url=conversation_url,
                wait_for_response=False,  # Ne pas attendre la réponse IA pour retourner l'URL
                timeout_seconds=timeout_seconds
            )
            
            if not result.get("success", False):
                raise HTTPException(status_code=500, detail=result.get("error", "Erreur lors de l'upload"))
            
            # Créer une tâche pour le tracking (déjà terminée pour l'URL)
            task_id = task_manager.create_task("upload_zip_file", {
                "file_path": temp_file_path,
                "filename": file.filename,
                "message": message,
                "platform": platform,
                "conversation_url": result.get("conversation_url", ""),
                "wait_for_response": wait_for_response,
                "timeout_seconds": timeout_seconds
            })
            
            # Marquer la tâche comme terminée immédiatement (pour l'URL)
            task = task_manager.get_task(task_id)
            if task:
                task.complete_execution(result)
            
            logger.info("Upload de fichier terminé avec succès", 
                       task_id=task_id,
                       filename=file.filename,
                       conversation_url=result.get("conversation_url"))
            
            return FileUploadResponse(
                task_id=task_id,
                status=TaskStatus.COMPLETED,  # ✅ Directement completed
                filename=file.filename,
                message_sent=message,
                conversation_url=result.get("conversation_url"),  # ✅ URL immédiatement disponible
                ai_response=result.get("ai_response"),  # Peut être None si wait_for_response=False
                execution_time_seconds=None,
                error_message=None
            )
            
        except Exception as e:
            # Nettoyer le fichier temporaire en cas d'erreur
            try:
                os.unlink(temp_file_path)
            except:
                pass
            raise e
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur lors de l'upload de fichier", error=str(e), filename=file.filename if file else "unknown")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@app.post("/upload-zip-from-url", response_model=FileUploadResponse)
async def upload_zip_from_url(request: ZipUrlUploadRequest):
    """
    Upload un fichier .zip depuis une URL vers Manus.ai
    
    📎 Fonctionnalités :
    - ✅ Téléchargement automatique depuis n'importe quelle URL
    - ✅ Validation de taille et type de fichier
    - ✅ Message d'accompagnement optionnel
    - ✅ Réutilisation de conversations existantes
    - ✅ Traitement asynchrone avec suivi de tâche
    - ✅ Gestion automatique des erreurs et nettoyage
    
    📝 Utilisation :
    ```bash
    curl -X POST "http://localhost:8000/upload-zip-from-url" \
      -H "Content-Type: application/json" \
      -d '{
        "zip_url": "https://example.com/mon-fichier.zip",
        "message": "Analyse ce fichier zip téléchargé",
        "platform": "manus"
      }'
    ```
    
    📊 Limites :
    - Taille maximale : 100MB
    - Timeout de téléchargement : 30s
    - Formats supportés : .zip uniquement
    """
    try:
        logger.info("Début d'upload de fichier .zip depuis URL", 
                   zip_url=request.zip_url,
                   message_length=len(request.message))
        
        # Import local pour éviter les dépendances circulaires
        from ai_interface_actions.zip_downloader import zip_downloader
        
        # Validation de l'URL
        if not zip_downloader.validate_zip_url(request.zip_url):
            raise HTTPException(status_code=400, detail=f"URL invalide: {request.zip_url}")
        
        # Validation des paramètres
        if request.timeout_seconds < 10 or request.timeout_seconds > 300:
            raise HTTPException(status_code=400, detail="timeout_seconds doit être entre 10 et 300")
        
        # Télécharger le fichier .zip
        logger.info("Téléchargement du fichier .zip depuis l'URL")
        try:
            temp_file_path, original_filename = zip_downloader.download_zip_from_url(request.zip_url)
        except Exception as e:
            logger.error("Erreur lors du téléchargement", zip_url=request.zip_url, error=str(e))
            raise HTTPException(status_code=400, detail=f"Erreur de téléchargement: {str(e)}")
        
        # Exécution SYNCHRONE comme send-message
        logger.info("Début d'upload synchrone depuis URL", 
                   zip_url=request.zip_url,
                   filename=original_filename)
        
        # Import local pour éviter les dépendances circulaires
        from ai_interface_actions.browser_automation import browser_manager
        
        # Upload direct et synchrone
        result = await browser_manager.upload_zip_file_to_manus(
            file_path=temp_file_path,
            message=request.message,
            conversation_url=request.conversation_url,
            wait_for_response=False,  # Ne pas attendre la réponse IA pour retourner l'URL
            timeout_seconds=request.timeout_seconds
        )
        
        if not result.get("success", False):
            error_detail = result.get("error", "Erreur lors de l'upload")
            logger.error("Échec de l'upload ZIP", 
                        error=error_detail,
                        filename=original_filename,
                        conversation_url=request.conversation_url)
            raise HTTPException(status_code=500, detail=f"Échec de l'upload: {error_detail}")
        
        # Créer une tâche pour le tracking (déjà terminée pour l'URL)
        task_id = task_manager.create_task("upload_zip_file", {
            "file_path": temp_file_path,
            "filename": original_filename,
            "message": request.message,
            "platform": request.platform,
            "conversation_url": result.get("conversation_url", ""),
            "wait_for_response": request.wait_for_response,
            "timeout_seconds": request.timeout_seconds,
            "source_url": request.zip_url
        })
        
        # Marquer la tâche comme terminée immédiatement (pour l'URL)
        task = task_manager.get_task(task_id)
        if task:
            task.complete_execution(result)
        
        logger.info("Upload depuis URL terminé avec succès", 
                   task_id=task_id,
                   filename=original_filename,
                   conversation_url=result.get("conversation_url"))
        
        return FileUploadResponse(
            task_id=task_id,
            status=TaskStatus.COMPLETED,  # ✅ Directement completed
            filename=original_filename,
            message_sent=request.message,
            conversation_url=result.get("conversation_url"),  # ✅ URL immédiatement disponible
            ai_response=result.get("ai_response"),  # Peut être None si wait_for_response=False
            execution_time_seconds=None,
            error_message=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur lors de l'upload depuis URL", error=str(e), zip_url=request.zip_url)
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@app.post("/send-message")
async def send_message(request: MessageRequest, http_request: Request):
    """
    Endpoint unique et intelligent pour envoyer des messages à Manus.ai
    
    🧠 Comportement adaptatif selon les paramètres :
    
    📝 Avec conversation_url :
    - Réutilise la page existante (pas de nouvel onglet)
    - Envoi synchrone immédiat dans la conversation
    - Retourne la réponse complète avec ai_response
    - Status: "completed"
    
    🆕 Sans conversation_url :
    - Crée une nouvelle conversation
    - Retourne l'URL rapidement
    - Traitement en arrière-plan si wait_for_response=true
    - Status: "url_ready"
    
    ✅ Avantages :
    - Déduplication automatique des requêtes
    - Pool de pages réutilisables
    - Logs détaillés pour debugging
    - Gestion intelligente des erreurs
    """
    try:
        # Génération du hash de requête pour déduplication
        client_ip = http_request.client.host if http_request.client else ""
        user_agent = http_request.headers.get("user-agent", "")
        request_hash = generate_request_hash(request, client_ip, user_agent)
        
        # Vérification des doublons
        if is_duplicate_request(request_hash, max_age_seconds=10):  # Plus court pour l'endpoint rapide
            if request_hash in request_cache:
                logger.info("Requête dupliquée détectée, retour du cache", request_hash=request_hash[:8])
                return request_cache[request_hash]["result"]
            else:
                logger.warning("Requête déjà en cours de traitement", request_hash=request_hash[:8])
                raise HTTPException(status_code=429, detail="Requête identique déjà en cours de traitement")
        
        # Marquer la requête comme en cours
        mark_request_processing(request_hash)
        logger.info("Nouvelle requête rapide acceptée", request_hash=request_hash[:8])
        
        logger.info("Demande d'envoi rapide avec URL", 
                   platform=request.platform, 
                   has_conversation_url=bool(request.conversation_url),
                   request_hash=request_hash[:8])
        
        # Vérifier que le navigateur est initialisé
        if not browser_manager.is_initialized:
            processing_requests.discard(request_hash)
            raise HTTPException(
                status_code=503, 
                detail="Service temporairement indisponible : navigateur non initialisé. "
                      "Cela peut arriver si Playwright n'est pas installé correctement. "
                      "Veuillez contacter l'administrateur."
            )
        
        # Validation des paramètres
        if not request.message.strip():
            processing_requests.discard(request_hash)
            raise HTTPException(status_code=400, detail="Le message ne peut pas être vide")
        
        if request.platform != "manus":
            processing_requests.discard(request_hash)
            raise HTTPException(status_code=400, detail=f"Plateforme '{request.platform}' non supportée")
        
        # Si URL de conversation fournie, envoyer directement dans la conversation existante
        if request.conversation_url and request.conversation_url.strip():
            logger.info("URL de conversation fournie - envoi direct dans conversation existante", 
                       url=request.conversation_url)
            
            # Envoi direct dans la conversation existante (utilise la logique corrigée)
            result = await browser_manager.send_message_to_manus(
                message=request.message,
                conversation_url=request.conversation_url,
                wait_for_response=request.wait_for_response,
                timeout_seconds=request.timeout_seconds
            )
            
            if not result.get("success", False):
                processing_requests.discard(request_hash)
                raise HTTPException(status_code=500, detail=result.get("error", "Erreur lors de l'envoi"))
            
            # Créer une tâche pour le tracking (optionnel)
            task_id = task_manager.create_task("send_message", {
                "message": request.message,
                "platform": request.platform,
                "conversation_url": request.conversation_url,
                "wait_for_response": request.wait_for_response,
                "timeout_seconds": request.timeout_seconds
            })
            
            # Marquer la tâche comme terminée immédiatement
            task = task_manager.get_task(task_id)
            if task:
                task.complete_execution(result)
            
            response_data = {
                "task_id": task_id,
                "status": "completed",
                "message_sent": request.message,
                "conversation_url": result.get("conversation_url", request.conversation_url),
                "ai_response": result.get("ai_response"),
                "quick_response": False,  # Réponse complète
                "message": "Message envoyé dans conversation existante avec succès"
            }
            
            # Cacher le résultat
            complete_request(request_hash, response_data)
            
            return response_data
        
        else:
            # Nouvelle conversation : envoi direct et complet
            logger.info("Nouvelle conversation, envoi direct avec réponse complète")
            
            # Envoi direct pour éviter les doubles appels
            result = await browser_manager.send_message_to_manus(
                message=request.message,
                conversation_url="",  # Nouvelle conversation
                wait_for_response=request.wait_for_response,
                timeout_seconds=request.timeout_seconds
            )
            
            if not result.get("success", False):
                processing_requests.discard(request_hash)
                raise HTTPException(status_code=500, detail=result.get("error", "Erreur lors de l'envoi"))
            
            # Créer une tâche pour le tracking (déjà terminée)
            task_id = task_manager.create_task("send_message", {
                "message": request.message,
                "platform": request.platform,
                "conversation_url": result.get("conversation_url", ""),
                "wait_for_response": request.wait_for_response,
                "timeout_seconds": request.timeout_seconds
            })
            
            # Marquer la tâche comme terminée immédiatement
            task = task_manager.get_task(task_id)
            if task:
                task.complete_execution(result)
            
            conversation_url = result.get("conversation_url", "")
            
            response_data = {
                "task_id": task_id,
                "status": "completed",
                "message_sent": request.message,
                "conversation_url": conversation_url,
                "ai_response": result.get("ai_response"),
                "quick_response": False,  # Réponse complète maintenant
                "message": "Nouvelle conversation créée et message envoyé avec succès"
            }
            
            # Cacher le résultat
            complete_request(request_hash, response_data)
            
            return response_data
        
    except HTTPException:
        # S'assurer que la requête est retirée du cache de traitement en cas d'erreur HTTP
        if 'request_hash' in locals():
            processing_requests.discard(request_hash)
        raise
    except Exception as e:
        # S'assurer que la requête est retirée du cache de traitement en cas d'erreur
        if 'request_hash' in locals():
            processing_requests.discard(request_hash)
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


@app.post("/admin/clear-cache")
async def clear_request_cache():
    """
    Vide le cache de déduplication des requêtes
    
    Utile en cas de problème de double envoi persistant.
    """
    try:
        global request_cache, processing_requests
        
        cache_size = len(request_cache)
        processing_size = len(processing_requests)
        
        request_cache.clear()
        processing_requests.clear()
        
        logger.info("Cache de déduplication vidé", 
                   cached_requests=cache_size, 
                   processing_requests=processing_size)
        
        return {
            "message": "Cache de déduplication vidé avec succès",
            "cleared_cached_requests": cache_size,
            "cleared_processing_requests": processing_size
        }
        
    except Exception as e:
        logger.error("Erreur lors du vidage du cache", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@app.get("/admin/cache-status")
async def get_cache_status():
    """
    Affiche le statut du cache de déduplication
    """
    try:
        current_time = time.time()
        
        # Analyser les entrées du cache
        cache_entries = []
        for request_hash, data in request_cache.items():
            age_seconds = current_time - data["timestamp"]
            cache_entries.append({
                "hash": request_hash[:8] + "...",
                "age_seconds": round(age_seconds, 2),
                "has_result": "result" in data
            })
        
        processing_entries = [hash_val[:8] + "..." for hash_val in processing_requests]
        
        return {
            "cached_requests": len(request_cache),
            "processing_requests": len(processing_requests),
            "cache_entries": cache_entries,
            "processing_entries": processing_entries,
            "cache_max_age_seconds": 15
        }
        
    except Exception as e:
        logger.error("Erreur lors de la récupération du statut du cache", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@app.post("/debug/simulate-request")
async def simulate_request(message: str = "Test message", client_ip: str = "127.0.0.1"):
    """
    Simule une requête pour tester la déduplication
    """
    try:
        from ai_interface_actions.models import MessageRequest
        
        # Créer une requête simulée
        request = MessageRequest(
            message=message,
            platform="manus",
            conversation_url="",
            wait_for_response=False
        )
        
        # Générer le hash
        request_hash = generate_request_hash(request, client_ip, "debug-user-agent")
        
        # Vérifier si c'est un doublon
        is_duplicate = is_duplicate_request(request_hash)
        
        if not is_duplicate:
            mark_request_processing(request_hash)
            # Simuler le traitement
            import asyncio
            await asyncio.sleep(0.1)
            complete_request(request_hash, {"simulated": True, "timestamp": time.time()})
        
        return {
            "request_hash": request_hash[:8] + "...",
            "is_duplicate": is_duplicate,
            "message": message,
            "client_ip": client_ip,
            "cache_size": len(request_cache),
            "processing_size": len(processing_requests)
        }
        
    except Exception as e:
        logger.error("Erreur lors de la simulation", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@app.get("/admin/active-pages")
async def get_active_pages():
    """
    Affiche les pages actives dans le pool de réutilisation
    """
    try:
        if not browser_manager.is_initialized:
            return {
                "active_pages": 0,
                "pages": [],
                "browser_status": "not_initialized"
            }
        
        pages_info = []
        for conversation_url, page in browser_manager.active_pages.items():
            try:
                is_closed = page.is_closed()
                current_url = page.url if not is_closed else "closed"
                
                pages_info.append({
                    "conversation_url": conversation_url,
                    "current_url": current_url,
                    "is_closed": is_closed,
                    "conversation_id": browser_manager._extract_conversation_id(conversation_url)
                })
            except Exception as e:
                pages_info.append({
                    "conversation_url": conversation_url,
                    "current_url": "error",
                    "is_closed": True,
                    "error": str(e)
                })
        
        return {
            "active_pages": len(browser_manager.active_pages),
            "pages": pages_info,
            "browser_status": "initialized"
        }
        
    except Exception as e:
        logger.error("Erreur lors de la récupération des pages actives", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@app.post("/debug/test-conversation-reuse")
async def test_conversation_reuse(conversation_url: str, message: str = "Test de réutilisation"):
    """
    Teste la réutilisation d'une conversation existante
    """
    try:
        if not browser_manager.is_initialized:
            return {
                "error": "Navigateur non initialisé",
                "browser_status": "not_initialized"
            }
        
        # Vérifier si la page existe déjà
        page_exists = conversation_url in browser_manager.active_pages
        conversation_id = browser_manager._extract_conversation_id(conversation_url)
        
        # Simuler l'appel qui serait fait
        logger.info("Test de réutilisation de conversation", 
                   url=conversation_url, 
                   page_exists=page_exists,
                   conversation_id=conversation_id)
        
        # Tester la récupération/création de page
        page = await browser_manager._get_or_create_page(conversation_url)
        page_was_reused = not page_exists and conversation_url in browser_manager.active_pages
        
        return {
            "conversation_url": conversation_url,
            "conversation_id": conversation_id,
            "page_existed_before": page_exists,
            "page_was_reused": page_was_reused,
            "current_page_url": page.url if not page.is_closed() else "closed",
            "total_active_pages": len(browser_manager.active_pages),
            "test_message": message,
            "recommendation": "Utilisez /send-message avec cette URL pour tester l'envoi réel"
        }
        
    except Exception as e:
        logger.error("Erreur lors du test de réutilisation", error=str(e))
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
        
        # Fallback: vérifier les variables d'environnement MANUS_*
        from ai_interface_actions.config import settings
        if settings.manus_cookies or settings.manus_session_token:
            return {
                "session_exists": True,
                "status": "valid",
                "source": "environment_variables",
                "message": "Session active depuis les variables d'environnement",
                "config": {
                    "has_cookies": bool(settings.manus_cookies),
                    "has_session_token": bool(settings.manus_session_token),
                    "use_persistent_context": settings.use_persistent_context
                }
            }
        
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
        from ai_interface_actions.credentials_client import credentials_client
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
                "is_configured": credentials_client.is_configured()
            }
        }
        
    except Exception as e:
        logger.error("Erreur lors du debug env vars", error=str(e))
        return {"error": f"Erreur debug env: {str(e)}"}

@app.get("/debug/storage-state-test")
async def debug_storage_state_test():
    """
    Test direct de _get_storage_state avec logs détaillés
    """
    try:
        # Tester directement la méthode _get_storage_state
        storage_state = await browser_manager._get_storage_state()
        
        if storage_state:
            return {
                "status": "storage_state_found",
                "cookies_count": len(storage_state.get("cookies", [])),
                "origins_count": len(storage_state.get("origins", [])),
                "cookies_sample": [
                    {"name": c["name"], "domain": c["domain"]} 
                    for c in storage_state.get("cookies", [])[:3]
                ],
                "origins_sample": [
                    {"origin": o["origin"], "localStorage_count": len(o.get("localStorage", []))} 
                    for o in storage_state.get("origins", [])[:2]
                ]
            }
        else:
            return {
                "status": "no_storage_state",
                "message": "Aucun storage_state retourné par _get_storage_state"
            }
            
    except Exception as e:
        logger.error("Erreur lors du test storage state", error=str(e))
        return {"error": f"Erreur test storage: {str(e)}"}

@app.post("/debug/send-message-with-exact-headers")
async def debug_send_message_with_exact_headers(request: MessageRequest):
    """
    Test avec User-Agent et headers EXACTEMENT comme dans vos données
    """
    try:
        # User-Agent EXACT de vos données
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
        
        # Forcer l'utilisation du User-Agent exact
        from playwright.async_api import async_playwright
        import json
        
        # Récupérer le storage state
        storage_state = await browser_manager._get_storage_state()
        if not storage_state:
            return {"error": "Pas de storage state"}
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                storage_state=storage_state,
                user_agent=user_agent,
                viewport={'width': 1440, 'height': 900},
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Ch-Ua': '"Chromium";v="138", "Google Chrome";v="138", "Not=A?Brand";v="99"',
                    'Sec-Ch-Ua-Mobile': '?0',
                    'Sec-Ch-Ua-Platform': '"macOS"'
                }
            )
            page = await context.new_page()
            
            # Naviguer vers Manus.im
            await page.goto("https://www.manus.im/app", wait_until="networkidle")
            await page.wait_for_timeout(3000)
            
            final_url = page.url
            
            # Vérifier si connecté avec debug détaillé
            login_check = await page.evaluate("""
                () => {
                    const indicators = [
                        '[data-testid="chat-input"]',
                        '.chat-container', 
                        'button[data-testid="new-chat"]',
                        'textarea[placeholder*="message"]',
                        'input[placeholder*="message"]',
                        'textarea[placeholder*="Message"]',
                        'input[placeholder*="Message"]',
                        '.chat-input',
                        '[placeholder*="chat"]',
                        '[placeholder*="Chat"]',
                        'button[aria-label*="new"]',
                        'button[aria-label*="New"]',
                        '.new-chat',
                        '.sidebar',
                        '[data-testid="sidebar"]',
                        '.user-menu',
                        '[data-testid="user-menu"]',
                        'nav',
                        '.navigation'
                    ];
                    
                    const found = [];
                    const notFound = [];
                    
                    indicators.forEach(selector => {
                        const element = document.querySelector(selector);
                        if (element) {
                            found.push(selector);
                        } else {
                            notFound.push(selector);
                        }
                    });
                    
                    // Vérifier aussi les éléments de login (pour confirmer qu'on n'est PAS sur la page de login)
                    const loginElements = [
                        'input[type="email"]',
                        'input[type="password"]', 
                        'button[type="submit"]',
                        '.login-form',
                        '.sign-in',
                        '[data-testid="login"]'
                    ];
                    
                    const loginFound = [];
                    loginElements.forEach(selector => {
                        if (document.querySelector(selector)) {
                            loginFound.push(selector);
                        }
                    });
                    
                    return {
                        isLoggedIn: found.length > 0,
                        foundElements: found,
                        notFoundElements: notFound,
                        loginElementsFound: loginFound,
                        pageTitle: document.title,
                        currentUrl: window.location.href
                    };
                }
            """)
            
            is_logged_in = login_check['isLoggedIn']
            
            await browser.close()
            
            return {
                "status": "test_complete",
                "user_agent": user_agent,
                "final_url": final_url,
                "appears_logged_in": is_logged_in,
                "cookies_applied": len(storage_state.get("cookies", [])),
                "test_result": "SUCCESS" if is_logged_in else "FAILED",
                "diagnosis": "Connecté avec succès" if is_logged_in else f"Redirigé vers {final_url}",
                "debug_info": {
                    "found_elements": login_check['foundElements'],
                    "login_elements_found": login_check['loginElementsFound'],
                    "page_title": login_check['pageTitle'],
                    "current_url": login_check['currentUrl']
                }
            }
            
    except Exception as e:
        logger.error("Erreur lors du test avec headers exacts", error=str(e))
        return {"error": f"Erreur test headers: {str(e)}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "ai_interface_actions.api:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    ) 