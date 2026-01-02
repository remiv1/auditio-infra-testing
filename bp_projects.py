"""API endpoint to start a project using Podman or Docker Compose ou encore K8S."""

import subprocess
import httpx
from fastapi import APIRouter, HTTPException
from models import Project

bp_projects = APIRouter()

@bp_projects.post("/api/projects/{project_name}/start")
def start_project(project_name: str):
    """
    Démarrer un projet en utilisant Podman ou Docker Compose ou K8S.
    Nécessite que le projet soit défini dans current_projects.json.
    Vérifie la santé du projet via /health après le démarrage.
    """
    project_object = Project(project_name=project_name)

    ssh_command = project_object.get_ssh_cmd()
    try:
        subprocess.run(ssh_command, capture_output=True, text=True, check=True)
        return {"status": "starting",
                "message": f"Démarrage du projet {project_name} en cours"
                }, 200
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500,
                            detail=f"Erreur lancement compose (SSH): {e.stderr}") from e

@bp_projects.get("/api/projects/{project_name}/health")
async def check_project_health(project_name: str):
    """
    Vérifie la santé d'un projet en interrogeant son endpoint /health.
    Nécessite que le projet soit défini dans current_projects.json.
    :param project_name: Nom du projet à vérifier (string)
    :return: Dictionnaire avec le statut de santé du projet (dict)
    """
    project_object = Project(project_name=project_name)
    pod_port = project_object.pod_port
    if not pod_port:
        raise HTTPException(status_code=400, detail="Projet sans port défini")
    health_url = f"http://localhost:{pod_port}/health"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(health_url, timeout=2)
        if r.status_code // 100 == 2:
            return {"status": "healthy"}
        raise HTTPException(status_code=503, detail="Projet non healthy")
    except Exception as e:
        message = f"Erreur accès au projet: {e}"
        raise HTTPException(status_code=503, detail=message) from e
