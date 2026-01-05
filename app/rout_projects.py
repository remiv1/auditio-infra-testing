"""API endpoint to start a project using Podman or Docker Compose ou encore K8S."""

import hashlib
import os
import json
from typing import Dict, Any
import asyncio
import subprocess
import httpx
import aiofiles
from fastapi import APIRouter, HTTPException, Request, Depends
from models import Project
from parameters import PROJECTS_JSON, TESTING_API_KEY, SSH_USER, SSH_HOST
from functions import verify_api_key

projects_routeur = APIRouter()

@projects_routeur.post("/api/projects/{project_name}/start",
                    summary="Démarrer un projet",
                    description="Démarrer un projet en utilisant Podman ou Docker Compose ou K8S.",
                    tags=["Projects"],
                    responses={200: {"description": "Projet démarré avec succès"},
                                500: {"description": "Erreur lors du démarrage du projet"}})
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

@projects_routeur.get("/api/projects/{project_name}/health",
    summary="Vérifier la santé d'un projet",
    description="Vérifie la santé d'un projet en interrogeant son endpoint /health.",
    tags=["Projects"],
    responses={200: {"description": "Projet en bonne santé"},
                503: {"description": "Projet non healthy ou inaccessible"}})
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

@projects_routeur.get("/api/projects",
    summary="Lister les projets",
    description="Retourne la liste des projets définis dans current_projects.json.",
    tags=["Projects"],
    responses={200: {"description": "Liste des projets récupérée avec succès"},
                500: {"description": "Erreur lors de la récupération de la liste des projets"}})
def list_projects() -> Dict[str, Any]:
    """
    Retourne la liste des projets définis dans current_projects.json.
    """
    try:
        with open(PROJECTS_JSON, "r", encoding="utf-8") as f:
            projects = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lecture JSON: {e}") from e
    return {"count": len(projects), "projects": projects}

@projects_routeur.post("/api/projects/{project_name}/stop",
    summary="Arrêter un projet",
    description="Arrête le projet spécifié via SSH (podman/docker compose down ou équivalent).",
    tags=["Projects"],
    responses={200: {"description": "Projet arrêté avec succès"},
                500: {"description": "Erreur lors de l'arrêt du projet"}})
def stop_project(project_name: str):
    """
    Arrête le projet spécifié via SSH (podman/docker compose down ou équivalent).
    """
    project_object = Project(project_name=project_name)
    ssh_command = project_object.get_ssh_cmd(stop=True)
    try:
        subprocess.run(ssh_command, capture_output=True, text=True, check=True)
        return {"status": "stopping", "message": f"Arrêt du projet {project_name} en cours"}, 200
    except subprocess.CalledProcessError as e:
        message = f"Erreur arrêt compose (SSH): {e.stderr}"
        raise HTTPException(status_code=500, detail=message) from e

@projects_routeur.post("/api/projects/sync",
    summary="Synchroniser la configuration des projets",
    description="Remplace config projets si JSON reçu différent, puis génération des services.",
    tags=["Projects"],
    responses={200: {"description": "Configuration synchronisée et services régénérés"},
               304: {"description": "Aucun changement détecté"},
               500: {"description": "Erreur lors de la synchronisation"}},
    dependencies=[Depends(verify_api_key)])
async def sync_projects(request: Request):
    """
    Reçoit un JSON de projets, le compare à l'existant, l'enregistre si différent,
    et lance le script de régénération.
    """
    # Vérification du token API
    api_key = request.headers.get("x-api-key")
    if not api_key or api_key != TESTING_API_KEY:
        raise HTTPException(status_code=403, detail="Clé API manquante ou invalide.")

    try:
        new_json = await request.json()
        new_json_str = json.dumps(new_json, sort_keys=True, ensure_ascii=False)
        new_hash = hashlib.sha256(new_json_str.encode("utf-8")).hexdigest()

        # Ajout de logs pour débogage
        print("Nouveau JSON reçu :", new_json)
        print("Hash du nouveau JSON :", new_hash)

        # Lire l'existant
        if os.path.exists(PROJECTS_JSON):
            async with aiofiles.open(PROJECTS_JSON, "r", encoding="utf-8") as f:
                old_json_str = await f.read()
                old_json = json.loads(old_json_str)
            old_json_str = json.dumps(old_json, sort_keys=True, ensure_ascii=False)
            old_hash = hashlib.sha256(old_json_str.encode("utf-8")).hexdigest()

            # Ajout de logs pour débogage
            print("JSON existant :", old_json)
            print("Hash de l'ancien JSON :", old_hash)
        else:
            old_hash = None
            print("Aucun fichier JSON existant trouvé.")

        if new_hash == old_hash:
            print("Aucun changement détecté entre les JSON.")
            return {"status": "no_change", "message": "Aucun changement détecté."}, 304

        # Écrire le nouveau JSON
        async with aiofiles.open(PROJECTS_JSON, "w", encoding="utf-8") as f:
            await f.write(new_json_str)
            print("Nouveau JSON écrit dans le fichier.")

        # Lancer le script de régénération
        # Exécution du script via SSH sur l'hôte
        ssh_command = [
            "ssh", f"{SSH_USER}@{SSH_HOST}", "-i", "/home/auditio-test/.ssh/api-shutdown-key",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "StrictHostKeyChecking=no",
            "sudo", "/home/auditio-test/auditio-infra-testing/utilitaires/rebuild-testing-services.sh"
        ]
        process = await asyncio.create_subprocess_exec(
            *ssh_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        print("Sortie standard du script :", stdout.decode())
        print("Erreur standard du script :", stderr.decode())
        if process.returncode != 0:
            raise RuntimeError(stderr.decode())

        return {"status": "updated", "message": "Configuration synchronisée et services régénérés."}
    except Exception as e:
        print("Erreur lors de la synchronisation des projets :", e)
        raise HTTPException(status_code=500, detail=f"Erreur synchronisation projets: {e}") from e
