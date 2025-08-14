"""
Modèles Pydantic pour les requêtes et réponses de l'API
"""
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Statuts possibles d'une tâche"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class MessageRequest(BaseModel):
    """Requête pour envoyer un message sur une plateforme IA"""
    message: str = Field(..., description="Message à envoyer", min_length=1, max_length=10000)
    platform: str = Field(default="manus", description="Plateforme cible (manus, chatgpt, etc.)")
    conversation_url: str = Field(default="", description="URL de conversation existante (optionnel - nouvelle conversation si vide)")
    wait_for_response: bool = Field(default=True, description="Attendre la réponse de l'IA")
    timeout_seconds: int = Field(default=60, description="Timeout pour la réponse", ge=10, le=300)


class MessageResponse(BaseModel):
    """Réponse après envoi d'un message"""
    task_id: str = Field(..., description="ID unique de la tâche")
    status: TaskStatus = Field(..., description="Statut de la tâche")
    message_sent: str = Field(..., description="Message envoyé")
    conversation_url: Optional[str] = Field(None, description="URL de la conversation (pour continuer)")
    ai_response: Optional[str] = Field(None, description="Réponse de l'IA (si disponible)")
    execution_time_seconds: Optional[float] = Field(None, description="Temps d'exécution")
    error_message: Optional[str] = Field(None, description="Message d'erreur (si échec)")


class TaskStatusResponse(BaseModel):
    """Réponse pour le statut d'une tâche"""
    task_id: str = Field(..., description="ID de la tâche")
    status: TaskStatus = Field(..., description="Statut actuel")
    created_at: str = Field(..., description="Date de création")
    updated_at: str = Field(..., description="Dernière mise à jour")
    result: Optional[Dict[str, Any]] = Field(None, description="Résultat de la tâche")
    error_message: Optional[str] = Field(None, description="Message d'erreur")


class HealthResponse(BaseModel):
    """Réponse de santé de l'API"""
    status: str = Field(..., description="Statut de l'API")
    version: str = Field(..., description="Version de l'application")
    browser_ready: bool = Field(..., description="Navigateur prêt")
    uptime_seconds: float = Field(..., description="Durée de fonctionnement") 