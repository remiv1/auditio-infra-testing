"""
API FastAPI pour la gestion du serveur Testing.
Permet l'extinction du serveur et la récupération des projets en cours.
"""

import subprocess
from fastapi import FastAPI, HTTPException, Depends
from functions import verify_api_key
from models import ShutdownResponse, ProjectsResponse, ProjectInfo
from logger import logger

app = FastAPI(
    title="Testing Server API",
    description="API pour la gestion du serveur de test",
    version="1.0.0"
)


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
        # Planifier l'extinction sur la machine hôte via SSH
        # ATTENTION :
        # 1. Configurez /etc/sudoers sur l'hôte pour permettre à l'utilisateur utilisé par SSH d'exécuter uniquement 'shutdown' sans mot de passe :
        #    exemple :
        #    myuser ALL=(root) NOPASSWD: /sbin/shutdown
        # 2. Ne pas donner NOPASSWD pour toutes les commandes !
        # 3. La clé SSH du conteneur doit être autorisée sur l'hôte.
        ssh_user = "auditio-test"  # À adapter
        ssh_host = "localhost"  # À adapter si besoin
        ssh_command = [
            "ssh", "-o", "UserKnownHostsFile=/dev/null", "-o", "StrictHostKeyChecking=no",
            f"{ssh_user}@{ssh_host}", "sudo", "/sbin/shutdown", "-h", "+1"
        ]
        subprocess.Popen(
            ssh_command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        logger.info("Extinction programmée avec succès pour dans 1 minute")
        return ShutdownResponse(
            status="scheduled",
            message="Extinction programmée dans 1 minute"
        )
    except Exception as e:
        message = f"Erreur lors de la planification de l'extinction: {e}"
        logger.error(message)
        raise HTTPException(status_code=500, detail=message) from e


@app.post("/api/shutdown/now",
          response_model=ShutdownResponse,
          dependencies=[Depends(verify_api_key)])
def shutdown_server_now():
    """
    Éteint le serveur immédiatement.
    Nécessite une clé API valide.
    """
    logger.warning("Requête d'extinction IMMÉDIATE reçue")
    try:
        # Extinction immédiate via SSH sur l'hôte
        ssh_user = "auditio-test"  # À adapter
        ssh_host = "localhost"  # À adapter si besoin
        ssh_command = [
            "ssh", "-o", "UserKnownHostsFile=/dev/null", "-o", "StrictHostKeyChecking=no",
            f"{ssh_user}@{ssh_host}", "sudo", "/sbin/shutdown", "-h", "now"
        ]
        subprocess.Popen(
            ssh_command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        logger.info("Extinction immédiate initiée")
        return ShutdownResponse(
            status="initiated",
            message="Extinction immédiate initiée"
        )
    except Exception as e:
        logger.error("Erreur lors de l'extinction: %s", e)
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'extinction: {e}") from e


@app.post("/api/shutdown/cancel",
          response_model=ShutdownResponse,
          dependencies=[Depends(verify_api_key)])
def cancel_shutdown():
    """
    Annule une extinction programmée.
    Nécessite une clé API valide.
    """
    logger.info("Requête d'annulation d'extinction reçue")
    try:
        # Annulation extinction via SSH sur l'hôte
        ssh_user = "auditio-test"  # À adapter
        ssh_host = "localhost"  # À adapter si besoin
        ssh_command = [
            "ssh", "-o", "UserKnownHostsFile=/dev/null", "-o", "StrictHostKeyChecking=no",
            f"{ssh_user}@{ssh_host}", "sudo", "/sbin/shutdown", "-c"
        ]
        result = subprocess.run(
            ssh_command,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            logger.info("Extinction annulée avec succès")
            return ShutdownResponse(
                status="cancelled",
                message="Extinction annulée"
            )
        else:
            logger.info("Aucune extinction à annuler")
            return ShutdownResponse(
                status="no_shutdown",
                message="Aucune extinction programmée à annuler"
            )
    except Exception as e:
        logger.error("Erreur lors de l'annulation de l'extinction: %s", e)
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'annulation de l'extinction: {e}") from e

#TODO: Refaire la fonction sans pouvoir utiliser l'API Docker Python (Podman sur serveur de test)
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
        message = f"Liste des projets retournée: {len(projects)} conteneur(s)"
        logger.info(message)
        return ProjectsResponse(count=len(projects), projects=projects)

    except subprocess.CalledProcessError as e:
        message = f"Erreur lors de l'exécution de la commande Docker: {e.stderr}"
        logger.error(message)
        raise HTTPException(status_code=500, detail=message) from e
    except Exception as e:
        message = f"Erreur lors de la récupération des projets: {e}"
        logger.error(message)
        raise HTTPException(status_code=500, detail=message) from e


@app.get("/api/projects/{name}")
def get_project(name: str, _: bool = Depends(verify_api_key)):
    """
    Récupère les informations d'un projet spécifique.
    Nécessite une clé API valide.
    """
    message = f"Récupération des informations pour le projet: {name}"
    logger.info(message)
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
        message = f"Informations du projet '{name}' récupérées avec succès"
        logger.info(message)
        return project_info

    except subprocess.CalledProcessError as e:
        message = f"Projet '{name}' non trouvé"
        logger.warning(message)
        raise HTTPException(status_code=404, detail=message) from e
    except Exception as e:
        message = f"Erreur lors de la récupération du projet {name}: {e}"
        logger.error(message)
        raise HTTPException(status_code=500, detail=message) from e


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=13492)
