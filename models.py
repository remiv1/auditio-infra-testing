"""Modèles de données pour l'API d'extinction et de gestion des projets Docker."""

from pydantic import BaseModel
from typing import List, Optional

class ProjectInfo(BaseModel):
    """Informations sur un projet Docker."""
    name: str
    status: str
    ports: Optional[str] = None
    image: Optional[str] = None


class ShutdownResponse(BaseModel):
    """Réponse de la route shutdown."""
    status: str
    message: str


class ProjectsResponse(BaseModel):
    """Réponse de la route projects."""
    count: int
    projects: List[ProjectInfo]
