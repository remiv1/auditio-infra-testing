"""
API FastAPI pour la gestion du serveur Testing.
Permet l'extinction du serveur et la récupération des projets en cours.
"""

import os
import subprocess
import logging
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Testing Server API",
    description="API pour la gestion du serveur de test",
    version="1.0.0"
)

API_KEY = os.environ.get("TESTING_API_KEY", "change-me")


def verify_api_key(x_api_key: str = Header(...)):
    """Vérifie la clé API."""
    if x_api_key != API_KEY:
        logger.warning(f"Tentative d'accès avec clé API invalide")
        raise HTTPException(status_code=403, detail="Clé API invalide")
    return True


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


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/api/shutdown", response_model=ShutdownResponse, dependencies=[Depends(verify_api_key)])
def shutdown_server():
    """
    Éteint le serveur de test.
    Nécessite une clé API valide.
    """
    logger.info("Requête d'extinction reçue (programmée +1 min)")
    try:
        # Planifier l'extinction dans 1 minute pour permettre la réponse HTTP
        subprocess.Popen(["shutdown", "-h", "+1"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info("Extinction programmée avec succès pour dans 1 minute")
        return ShutdownResponse(
            status="scheduled",
            message="Extinction programmée dans 1 minute"
        )
    except Exception as e:
        logger.error(f"Erreur lors de la planification de l'extinction: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la planification de l'extinction: {e}")


@app.post("/api/shutdown/now", response_model=ShutdownResponse, dependencies=[Depends(verify_api_key)])
def shutdown_server_now():
    """
    Éteint le serveur immédiatement.
    Nécessite une clé API valide.
    """
    logger.warning("Requête d'extinction IMMÉDIATE reçue")
    try:
        subprocess.Popen(["shutdown", "-h", "now"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info("Extinction immédiate initiée")
        return ShutdownResponse(
            status="initiated",
            message="Extinction immédiate initiée"
        )
    except Exception as e:
        logger.error(f"Erreur lors de l'extinction: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'extinction: {e}")


@app.post("/api/shutdown/cancel", response_model=ShutdownResponse, dependencies=[Depends(verify_api_key)])
def cancel_shutdown():
    """
    Annule une extinction programmée.
    Nécessite une clé API valide.
    """
    logger.info("Requête d'annulation d'extinction reçue")
    try:
        subprocess.run(["shutdown", "-c"], check=True, capture_output=True)
        logger.info("Extinction annulée avec succès")
        return ShutdownResponse(
            status="cancelled",
            message="Extinction annulée"
        )
    except subprocess.CalledProcessError:
        logger.info("Aucune extinction à annuler")
        return ShutdownResponse(
            status="no_shutdown",
            message="Aucune extinction programmée à annuler"
        )
    except Exception as e:
        logger.error(f"Erreur lors de l'annulation: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")


@app.get("/api/projects", response_model=ProjectsResponse, dependencies=[Depends(verify_api_key)])
def list_projects():
    """
    Liste les conteneurs Docker en cours d'exécution.
    Nécessite une clé API valide.
    """
    logger.info("Requête de liste des projets Docker")
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}|{{.Status}}|{{.Ports}}|{{.Image}}"],
            capture_output=True,
            text=True,
            check=True
        )
        
        projects = []
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split("|")
                projects.append(ProjectInfo(
                    name=parts[0] if len(parts) > 0 else "",
                    status=parts[1] if len(parts) > 1 else "",
                    ports=parts[2] if len(parts) > 2 else None,
                    image=parts[3] if len(parts) > 3 else None
                ))
        
        logger.info(f"Liste des projets retournée: {len(projects)} conteneur(s)")
        return ProjectsResponse(count=len(projects), projects=projects)
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur Docker: {e.stderr}")
        raise HTTPException(status_code=500, detail=f"Erreur Docker: {e.stderr}")
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des projets: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")


@app.get("/api/projects/{name}")
def get_project(name: str, _: bool = Depends(verify_api_key)):
    """
    Récupère les informations d'un projet spécifique.
    Nécessite une clé API valide.
    """
    logger.info(f"Requête d'informations pour le projet: {name}")
    try:
        result = subprocess.run(
            ["docker", "inspect", name, "--format", 
             "{{.Name}}|{{.State.Status}}|{{.Config.Image}}|{{.State.StartedAt}}"],
            capture_output=True,
            text=True,
            check=True
        )
        
        parts = result.stdout.strip().split("|")
        project_info = {
            "name": parts[0].lstrip("/") if len(parts) > 0 else name,
            "status": parts[1] if len(parts) > 1 else "unknown",
            "image": parts[2] if len(parts) > 2 else None,
            "started_at": parts[3] if len(parts) > 3 else None
        }
        logger.info(f"Informations du projet {name} retournées")
        return project_info
    
    except subprocess.CalledProcessError:
        logger.warning(f"Projet '{name}' non trouvé")
        raise HTTPException(status_code=404, detail=f"Projet '{name}' non trouvé")
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du projet {name}: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=13492)
