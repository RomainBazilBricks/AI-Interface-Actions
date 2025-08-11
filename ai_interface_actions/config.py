"""
Configuration de l'application avec validation Pydantic
"""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration de l'application"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Configuration API
    api_host: str = Field(default="0.0.0.0", description="Adresse d'écoute de l'API")
    api_port: int = Field(default=8000, description="Port d'écoute de l'API")
    debug: bool = Field(default=False, description="Mode debug")
    api_secret_key: str = Field(default="dev-secret-key", description="Clé secrète pour l'API")
    
    # Configuration Playwright
    headless: bool = Field(default=True, description="Mode headless du navigateur")
    headless_setup: bool = Field(default=False, description="Mode headless pour le setup (False = fenêtre visible)")
    use_persistent_context: bool = Field(default=True, description="Utiliser un contexte persistant (garde la session)")
    window_width: int = Field(default=1440, description="Largeur de fenêtre en mode visible (0 = taille standard)")
    window_height: int = Field(default=900, description="Hauteur de fenêtre en mode visible (0 = taille standard)")
    disable_javascript: bool = Field(default=False, description="Désactiver JavaScript (pour debug)")
    browser_timeout: int = Field(default=30000, description="Timeout global du navigateur (ms)")
    page_timeout: int = Field(default=15000, description="Timeout de chargement des pages (ms)")
    
    # Configuration Manus.ai
    manus_base_url: str = Field(default="https://www.manus.ai", description="URL de base de Manus.ai")
    # Note: Plus besoin d'identifiants - connexion manuelle une fois, session persiste 30 jours
    
    # Sécurité et rate limiting
    rate_limit_per_minute: int = Field(default=10, description="Limite de requêtes par minute")
    
    # Logging
    log_level: str = Field(default="INFO", description="Niveau de log")


# Instance globale des paramètres
settings = Settings() 