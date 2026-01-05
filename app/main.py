"""
API FastAPI pour la gestion du serveur Testing.
Permet l'extinction du serveur et la récupération des projets en cours.
"""

import subprocess
from typing import List
from fastapi import FastAPI, HTTPException, Depends
from functions import verify_api_key
from models import ShutdownResponse
from logger import logger
from parameters import COMMAND, SSH_USER, SSH_HOST
from route_projects import projects_routeur

app = FastAPI(
    title="Testing Server API",
    description="API pour la gestion du serveur de test des projets clients.",
    version="1.0.0"
)
app.include_router(projects_routeur)

@app.get("/health",
         summary="Health Check",
         tags=["Fonctions", "Général"],
         description="Vérifie que l'API est opérationnelle.",
         responses={200: {"description": "API opérationnelle"}})
def health():
    """Health check endpoint."""
    return {"status": "ok"}

@app.post("/api/shutdown",
          summary="Éteindre le serveur de test",
          tags=["Fonctions", "Général"],
          description="Éteint le serveur de test.",
          response_model=ShutdownResponse,
          dependencies=[Depends(verify_api_key)])
def shutdown_server():
    """
    Éteint le serveur de test.
    Nécessite une clé API valide.
    """
    logger.info("Requête d'extinction reçue (programmée +1 min)")
    try:
        # Planifier l'extinction sur la machine hôte via SSH
        # ATTENTION :
        # 1. Configurez /etc/sudoers sur l'hôte pour permettre à l'utilisateur utilisé par SSH
        # d'exécuter uniquement 'shutdown' sans mot de passe :
        #    exemple :
        #    myuser ALL=(root) NOPASSWD: /sbin/shutdown
        # 2. Ne pas donner NOPASSWD pour toutes les commandes !
        # 3. La clé SSH du conteneur doit être autorisée sur l'hôte.
        ssh_command: List[str] = [
            "ssh", "-i", COMMAND["cert"], "-o", COMMAND["validate"][0], "-o",
            COMMAND["validate"][1], f"{SSH_USER}@{SSH_HOST}", "sudo",
            COMMAND["com"], "-h", "+1"
        ]
        process = subprocess.Popen(
            ssh_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(timeout=10)
        if stdout:
            logger.debug("SSH stdout: %s", stdout.strip())
        if stderr:
            logger.debug("SSH stderr: %s", stderr.strip())
        if process.returncode != 0:
            logger.warning("Commande SSH retournée avec code %d", process.returncode)
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
          summary="Éteindre le serveur immédiatement",
          tags=["Fonctions", "Général"],
          description="Éteint le serveur immédiatement.",
          response_model=ShutdownResponse,
          dependencies=[Depends(verify_api_key)])
def shutdown_server_now():
    """
    Éteint le serveur immédiatement.
    Nécessite une clé API valide.
    A n'utiliser qu'en cas d'urgence, privilégier la méthode programmée.
    """
    logger.warning("Requête d'extinction IMMÉDIATE reçue")
    try:
        # Extinction immédiate via SSH sur l'hôte
        ssh_command: List[str] = [
            "ssh", "-i", COMMAND["cert"], "-o", COMMAND["validate"][0], "-o",
            COMMAND["validate"][1], f"{SSH_USER}@{SSH_HOST}", "sudo", COMMAND["com"],
            "-h", "now"
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
          summary="Annuler une extinction programmée",
          tags=["Fonctions", "Général"],
          description="Annule une extinction programmée du serveur.",
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
        ssh_command: List[str] = [
            "ssh", "-o", COMMAND["validate"][0], "-o", COMMAND["validate"][1],
            f"{SSH_USER}@{SSH_HOST}", "sudo", COMMAND["com"], "-c"
        ]
        result = subprocess.run(
            ssh_command,
            capture_output=True,
            text=True,
            check=False
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
        message = f"Erreur lors de l'annulation de l'extinction: {e}"
        logger.error(message)
        raise HTTPException(status_code=500, detail=message) from e

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=13492)
