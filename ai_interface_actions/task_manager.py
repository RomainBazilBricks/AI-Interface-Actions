"""
Gestionnaire de tâches asynchrones
"""
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import structlog

from ai_interface_actions.models import TaskStatus
from ai_interface_actions.browser_automation import browser_manager

logger = structlog.get_logger(__name__)


class Task:
    """Représente une tâche d'automatisation"""
    
    def __init__(self, task_id: str, task_type: str, params: Dict[str, Any]):
        self.task_id = task_id
        self.task_type = task_type
        self.params = params
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.result: Optional[Dict[str, Any]] = None
        self.error_message: Optional[str] = None
        self.execution_start_time: Optional[datetime] = None
        self.execution_end_time: Optional[datetime] = None
    
    @property
    def execution_time_seconds(self) -> Optional[float]:
        """Calcule le temps d'exécution en secondes"""
        if self.execution_start_time and self.execution_end_time:
            return (self.execution_end_time - self.execution_start_time).total_seconds()
        return None
    
    def update_status(self, status: TaskStatus, error_message: Optional[str] = None) -> None:
        """Met à jour le statut de la tâche"""
        self.status = status
        self.updated_at = datetime.now()
        if error_message:
            self.error_message = error_message
    
    def start_execution(self) -> None:
        """Marque le début de l'exécution"""
        self.status = TaskStatus.RUNNING
        self.execution_start_time = datetime.now()
        self.updated_at = datetime.now()
    
    def complete_execution(self, result: Dict[str, Any]) -> None:
        """Marque la fin de l'exécution avec succès"""
        self.status = TaskStatus.COMPLETED
        self.execution_end_time = datetime.now()
        self.updated_at = datetime.now()
        self.result = result
    
    def fail_execution(self, error_message: str) -> None:
        """Marque la fin de l'exécution avec échec"""
        self.status = TaskStatus.FAILED
        self.execution_end_time = datetime.now()
        self.updated_at = datetime.now()
        self.error_message = error_message


class TaskManager:
    """Gestionnaire de tâches asynchrones"""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.max_concurrent_tasks = 5  # Limite de tâches simultanées
    
    def create_task(self, task_type: str, params: Dict[str, Any]) -> str:
        """Crée une nouvelle tâche"""
        task_id = str(uuid.uuid4())
        task = Task(task_id, task_type, params)
        self.tasks[task_id] = task
        
        logger.info("Nouvelle tâche créée", task_id=task_id, task_type=task_type)
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Récupère une tâche par son ID"""
        return self.tasks.get(task_id)
    
    async def execute_task(self, task_id: str) -> None:
        """Exécute une tâche de manière asynchrone"""
        task = self.get_task(task_id)
        if not task:
            logger.error("Tâche introuvable", task_id=task_id)
            return
        
        # Vérifier la limite de tâches simultanées
        if len(self.running_tasks) >= self.max_concurrent_tasks:
            logger.warning("Limite de tâches simultanées atteinte", task_id=task_id)
            task.update_status(TaskStatus.FAILED, "Limite de tâches simultanées atteinte")
            return
        
        # Créer et démarrer la tâche asyncio
        async_task = asyncio.create_task(self._run_task(task))
        self.running_tasks[task_id] = async_task
        
        try:
            await async_task
        except Exception as e:
            logger.error("Erreur lors de l'exécution de la tâche", task_id=task_id, error=str(e))
        finally:
            # Nettoyer la tâche des tâches en cours
            self.running_tasks.pop(task_id, None)
    
    async def _run_task(self, task: Task) -> None:
        """Exécute une tâche spécifique"""
        try:
            task.start_execution()
            logger.info("Début d'exécution de la tâche", task_id=task.task_id, task_type=task.task_type)
            
            if task.task_type == "send_message":
                result = await self._execute_send_message_task(task)
            else:
                raise ValueError(f"Type de tâche non supporté: {task.task_type}")
            
            task.complete_execution(result)
            logger.info("Tâche terminée avec succès", task_id=task.task_id, execution_time=task.execution_time_seconds)
            
        except Exception as e:
            error_msg = str(e)
            task.fail_execution(error_msg)
            logger.error("Échec de la tâche", task_id=task.task_id, error=error_msg)
    
    async def _execute_send_message_task(self, task: Task) -> Dict[str, Any]:
        """Exécute une tâche d'envoi de message"""
        params = task.params
        
        message = params.get("message", "")
        platform = params.get("platform", "manus")
        conversation_url = params.get("conversation_url", "")
        wait_for_response = params.get("wait_for_response", True)
        timeout_seconds = params.get("timeout_seconds", 60)
        use_clipboard_workaround = params.get("use_clipboard_workaround", False)
        
        if not message:
            raise ValueError("Message vide")
        
        if platform == "manus":
            # Choisir la fonction appropriée selon le paramètre
            if use_clipboard_workaround:
                result = await browser_manager.send_message_to_manus_with_clipboard_workaround(
                    message=message,
                    conversation_url=conversation_url,
                    wait_for_response=wait_for_response,
                    timeout_seconds=timeout_seconds
                )
            else:
                result = await browser_manager.send_message_to_manus(
                    message=message,
                    conversation_url=conversation_url,
                    wait_for_response=wait_for_response,
                    timeout_seconds=timeout_seconds
                )
        else:
            raise ValueError(f"Plateforme non supportée: {platform}")
        
        if not result.get("success", False):
            raise Exception(result.get("error", "Erreur inconnue"))
        
        return result
    
    async def start_task_in_background(self, task_id: str) -> None:
        """Démarre une tâche en arrière-plan"""
        asyncio.create_task(self.execute_task(task_id))
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Récupère le statut d'une tâche"""
        task = self.get_task(task_id)
        if not task:
            return None
        
        return {
            "task_id": task.task_id,
            "status": task.status,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "result": task.result,
            "error_message": task.error_message,
            "execution_time_seconds": task.execution_time_seconds
        }
    
    def cleanup_old_tasks(self, max_age_hours: int = 24) -> None:
        """Nettoie les anciennes tâches terminées"""
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        tasks_to_remove = []
        for task_id, task in self.tasks.items():
            if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED] and 
                task.updated_at.timestamp() < cutoff_time):
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
            logger.info("Ancienne tâche supprimée", task_id=task_id)


# Instance globale du gestionnaire de tâches
task_manager = TaskManager() 