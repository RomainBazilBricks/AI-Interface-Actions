"""
Interface web d'administration pour la configuration des tokens Manus.ai
"""
from fastapi import APIRouter, HTTPException, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
import secrets
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any

import structlog

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/admin-config", tags=["Administration Web"])

# Configuration sécurisée
ADMIN_PASSWORD = os.getenv("ADMIN_CONFIG_PASSWORD", "manus-admin-2025")
security = HTTPBasic()

class SessionConfig(BaseModel):
    session_id: Optional[str] = None
    cookies_raw: Optional[str] = None
    local_storage_raw: Optional[str] = None
    user_id: Optional[str] = None

def verify_admin_password(credentials: HTTPBasicCredentials = Depends(security)):
    """Vérifie le mot de passe administrateur"""
    is_correct_username = secrets.compare_digest(credentials.username, "admin")
    is_correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=401,
            detail="Accès non autorisé",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials

@router.get("/", response_class=HTMLResponse)
async def admin_config_page(credentials: HTTPBasicCredentials = Depends(verify_admin_password)):
    """Page d'administration pour configurer les tokens"""
    
    # Lire la configuration actuelle
    current_config = get_current_session_config()
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🔧 Configuration Manus.ai - Railway</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }}
            
            .container {{
                max-width: 1000px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                overflow: hidden;
            }}
            
            .header {{
                background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }}
            
            .header h1 {{
                font-size: 2.5rem;
                margin-bottom: 10px;
            }}
            
            .header p {{
                opacity: 0.9;
                font-size: 1.1rem;
            }}
            
            .content {{
                padding: 40px;
            }}
            
            .status-card {{
                background: #f8f9fa;
                border-radius: 15px;
                padding: 25px;
                margin-bottom: 30px;
                border-left: 5px solid #28a745;
            }}
            
            .status-card.warning {{
                border-left-color: #ffc107;
                background: #fffbf0;
            }}
            
            .form-group {{
                margin-bottom: 25px;
            }}
            
            .form-group label {{
                display: block;
                font-weight: 600;
                margin-bottom: 8px;
                color: #2c3e50;
                font-size: 1.1rem;
            }}
            
            .form-group .help-text {{
                font-size: 0.9rem;
                color: #6c757d;
                margin-bottom: 10px;
            }}
            
            .form-control {{
                width: 100%;
                padding: 15px;
                border: 2px solid #e9ecef;
                border-radius: 10px;
                font-size: 1rem;
                transition: all 0.3s ease;
                font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            }}
            
            .form-control:focus {{
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }}
            
            textarea.form-control {{
                min-height: 120px;
                resize: vertical;
            }}
            
            .btn {{
                display: inline-block;
                padding: 15px 30px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 1.1rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                text-decoration: none;
            }}
            
            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
            }}
            
            .btn-secondary {{
                background: linear-gradient(135deg, #6c757d 0%, #495057 100%);
                margin-left: 15px;
            }}
            
            .alert {{
                padding: 15px;
                border-radius: 10px;
                margin-bottom: 20px;
            }}
            
            .alert-info {{
                background: #d1ecf1;
                border: 1px solid #bee5eb;
                color: #0c5460;
            }}
            
            .code-block {{
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 15px;
                font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                font-size: 0.9rem;
                white-space: pre-wrap;
                word-break: break-all;
            }}
            
            .grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 30px;
            }}
            
            @media (max-width: 768px) {{
                .grid {{
                    grid-template-columns: 1fr;
                }}
                
                .header h1 {{
                    font-size: 2rem;
                }}
                
                .content {{
                    padding: 20px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔧 Configuration Manus.ai</h1>
                <p>Interface d'administration sécurisée pour Railway</p>
            </div>
            
            <div class="content">
                <div class="status-card {'warning' if not current_config['has_session'] else ''}">
                    <h3>📊 Statut actuel</h3>
                    <p><strong>Session configurée :</strong> {'✅ Oui' if current_config['has_session'] else '❌ Non'}</p>
                    <p><strong>Source :</strong> {current_config['source']}</p>
                    {f"<p><strong>User ID :</strong> {current_config['user_id']}</p>" if current_config['user_id'] else ""}
                </div>
                
                <div class="alert alert-info">
                    <strong>🔍 Instructions :</strong><br>
                    1. Allez sur Manus.ai et ouvrez la console (F12)<br>
                    2. Collez le script d'extraction et copiez les résultats<br>
                    3. Remplissez les champs ci-dessous avec les données extraites<br>
                    4. Cliquez sur "Sauvegarder" pour appliquer la configuration
                </div>
                
                <form method="post" action="/admin-config/save">
                    <div class="grid">
                        <div>
                            <div class="form-group">
                                <label for="session_id">🔑 Session ID</label>
                                <div class="help-text">Token principal de session (cookie session_id)</div>
                                <input type="text" 
                                       class="form-control" 
                                       id="session_id" 
                                       name="session_id" 
                                       value="{current_config.get('session_id', '')}"
                                       placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...">
                            </div>
                            
                            <div class="form-group">
                                <label for="user_id">👤 User ID</label>
                                <div class="help-text">ID utilisateur extrait du localStorage</div>
                                <input type="text" 
                                       class="form-control" 
                                       id="user_id" 
                                       name="user_id"
                                       value="{current_config.get('user_id', '')}"
                                       placeholder="310419663026821823">
                            </div>
                        </div>
                        
                        <div>
                            <div class="form-group">
                                <label for="cookies_raw">🍪 Cookies (Raw)</label>
                                <div class="help-text">Sortie complète de la section COOKIES</div>
                                <textarea class="form-control" 
                                          id="cookies_raw" 
                                          name="cookies_raw" 
                                          placeholder="manus-theme=dark
guest_experiment=input-header-footer
session_id=eyJhbGciOiJIUzI1NiI...">{current_config.get('cookies_raw', '')}</textarea>
                            </div>
                            
                            <div class="form-group">
                                <label for="local_storage_raw">💾 Local Storage (Raw)</label>
                                <div class="help-text">Sortie complète de la section LOCAL STORAGE</div>
                                <textarea class="form-control" 
                                          id="local_storage_raw" 
                                          name="local_storage_raw" 
                                          placeholder="chatHomeViewCollapse=false
UserService.userClientConfig={{...}}">{current_config.get('local_storage_raw', '')}</textarea>
                            </div>
                        </div>
                    </div>
                    
                    <div style="text-align: center; margin-top: 30px;">
                        <button type="submit" class="btn">💾 Sauvegarder Configuration</button>
                        <a href="/admin-config/test" class="btn btn-secondary">🧪 Tester Session</a>
                    </div>
                </form>
                
                <div style="margin-top: 40px; padding-top: 30px; border-top: 2px solid #e9ecef;">
                    <h3>📋 Script d'extraction</h3>
                    <p>Copiez-collez ce script dans la console de Manus.ai :</p>
                    <div class="code-block">console.log("=== COOKIES MANUS.AI ===");
document.cookie.split(';').forEach(cookie => {{
    const [name, value] = cookie.trim().split('=');
    if (name && value) {{
        console.log(`${{name}}=${{value}}`);
    }}
}});

console.log("\\n=== LOCAL STORAGE ===");
Object.keys(localStorage).forEach(key => {{
    console.log(`${{key}}=${{localStorage.getItem(key)}}`);
}});</div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content

@router.post("/save")
async def save_session_config(
    request: Request,
    session_id: str = Form(""),
    user_id: str = Form(""),
    cookies_raw: str = Form(""),
    local_storage_raw: str = Form(""),
    credentials: HTTPBasicCredentials = Depends(verify_admin_password)
):
    """Sauvegarde la configuration de session"""
    try:
        logger.info("💾 Sauvegarde de la configuration de session")
        
        # Parser les données
        config_data = parse_session_data(session_id, user_id, cookies_raw, local_storage_raw)
        
        # Sauvegarder dans un fichier de configuration
        save_session_to_file(config_data)
        
        # Créer les variables d'environnement pour Railway
        env_vars = generate_railway_env_vars(config_data)
        
        logger.info("✅ Configuration sauvegardée avec succès")
        
        # Rediriger avec message de succès
        return RedirectResponse(url="/admin-config/?success=1", status_code=303)
        
    except Exception as e:
        logger.error("❌ Erreur lors de la sauvegarde", error=str(e))
        return RedirectResponse(url="/admin-config/?error=1", status_code=303)

@router.get("/test")
async def test_session(credentials: HTTPBasicCredentials = Depends(verify_admin_password)):
    """Teste la session configurée"""
    try:
        # Importer ici pour éviter les imports circulaires
        from ai_interface_actions.browser_automation import browser_manager
        
        # Tester la récupération de l'état de stockage
        storage_state = browser_manager._get_storage_state()
        
        result = {
            "success": True,
            "storage_state_type": type(storage_state).__name__,
            "has_cookies": False,
            "has_local_storage": False
        }
        
        if isinstance(storage_state, dict):
            result["has_cookies"] = len(storage_state.get("cookies", [])) > 0
            result["has_local_storage"] = len(storage_state.get("origins", [])) > 0
            result["cookies_count"] = len(storage_state.get("cookies", []))
            result["origins_count"] = len(storage_state.get("origins", []))
        elif isinstance(storage_state, str):
            result["file_path"] = storage_state
        
        return {"status": "success", "data": result}
        
    except Exception as e:
        logger.error("❌ Erreur lors du test", error=str(e))
        return {"status": "error", "error": str(e)}

def get_current_session_config() -> Dict[str, Any]:
    """Récupère la configuration actuelle de session"""
    try:
        from ai_interface_actions.config import settings
        
        config = {
            "has_session": False,
            "source": "Aucune",
            "session_id": "",
            "user_id": "",
            "cookies_raw": "",
            "local_storage_raw": ""
        }
        
        # Vérifier les variables d'environnement
        if settings.manus_session_token or settings.manus_cookies:
            config.update({
                "has_session": True,
                "source": "Variables d'environnement",
                "session_id": settings.manus_session_token,
                "user_id": settings.manus_user_id
            })
        
        # Vérifier le fichier session
        elif Path("session_state.json").exists():
            config.update({
                "has_session": True,
                "source": "Fichier session_state.json"
            })
        
        # Lire le fichier de configuration local s'il existe
        config_file = Path("manus_session_config.json")
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    saved_config = json.load(f)
                    config.update(saved_config)
            except Exception:
                pass
        
        return config
        
    except Exception as e:
        logger.error("Erreur lecture config", error=str(e))
        return {"has_session": False, "source": "Erreur", "session_id": "", "user_id": ""}

def parse_session_data(session_id: str, user_id: str, cookies_raw: str, local_storage_raw: str) -> Dict[str, Any]:
    """Parse les données de session extraites"""
    config = {
        "session_id": session_id.strip(),
        "user_id": user_id.strip(),
        "cookies": {},
        "local_storage": {}
    }
    
    # Parser les cookies
    if cookies_raw:
        for line in cookies_raw.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                config["cookies"][key.strip()] = value.strip()
    
    # Parser le localStorage
    if local_storage_raw:
        for line in local_storage_raw.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                config["local_storage"][key.strip()] = value.strip()
    
    return config

def save_session_to_file(config_data: Dict[str, Any]):
    """Sauvegarde la configuration dans un fichier"""
    config_file = Path("manus_session_config.json")
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=2)
    logger.info("Configuration sauvegardée", file=str(config_file))

def generate_railway_env_vars(config_data: Dict[str, Any]) -> Dict[str, str]:
    """Génère les variables d'environnement pour Railway"""
    env_vars = {}
    
    if config_data["session_id"]:
        env_vars["MANUS_SESSION_TOKEN"] = config_data["session_id"]
    
    if config_data["user_id"]:
        env_vars["MANUS_USER_ID"] = config_data["user_id"]
    
    if config_data["cookies"]:
        # Convertir les cookies au format Playwright
        playwright_cookies = []
        for name, value in config_data["cookies"].items():
            playwright_cookies.append({
                "name": name,
                "value": value,
                "domain": ".manus.ai",
                "path": "/",
                "httpOnly": name in ["session_id", "auth_token"],
                "secure": True
            })
        env_vars["MANUS_COOKIES"] = json.dumps(playwright_cookies)
    
    if config_data["local_storage"]:
        env_vars["MANUS_LOCAL_STORAGE"] = json.dumps(config_data["local_storage"])
    
    # Sauvegarder les variables d'environnement dans un fichier
    env_file = Path("railway_env_vars.txt")
    with open(env_file, 'w') as f:
        f.write("# Variables d'environnement pour Railway\n")
        f.write("# Copiez-collez ces variables dans Railway > Variables\n\n")
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    
    logger.info("Variables d'environnement générées", file=str(env_file))
    return env_vars 