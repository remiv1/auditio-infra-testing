"""Modèles de données pour l'API d'extinction et de gestion des projets Docker."""

import os
import json
from typing import Dict, Any
from pydantic import BaseModel
from fastapi import HTTPException
from parameters import SSH_USER, SSH_HOST, COMMAND, PROJECTS_JSON, PROJECTS_ROOT

class ShutdownResponse(BaseModel):
    """Réponse de la route shutdown."""
    status: str
    message: str

class Project():
    """
    Modèle de données pour un projet.
    Méthodes et attributs pour la gestion des projets.
    """
    name: str
    folder: str
    param: Dict[str, Any]
    __running__: bool
    pod_port: int | None = None

    def __init__(self, *, project_name: str):
        """
        Initialise un projet avec les paramètres donnés.
        :param name: Nom du projet (string)
        :param folder: Dossier du projet (string)
        :param param: Paramètres spécifiques du projet (dict)
            keys possibles dans param:
                - specific_compose: Nom du fichier compose spécifique (string)
                - containerizer: Type de containerizer ("podman", "docker", "k8s")
                - nb_containers: Nombre de conteneurs (int)
                - database: présence d'une base de données (bool)
        :param __running__: Statut du projet (bool)
            possibles
        :param pod_port: Port du pod si applicable (int ou None)
        """
        # Charger la liste des projets
        try:
            with open(PROJECTS_JSON, "r", encoding="utf-8") as f:
                projects = json.load(f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur lecture JSON: {e}") from e

        dict_data = next((p for p in projects if p["name"] == project_name), None)
        if not dict_data:
            raise HTTPException(status_code=404, detail="Projet non trouvé")


        self.name = dict_data.get("name", "unknown")
        self.folder = dict_data.get("folder", "unknown")
        self.param = dict_data.get("param", {})
        self.pod_port = dict_data.get("pod_port")
        self.__running__ = False

    def set_running(self, running: bool):
        """
        Setter.
        Définit le statut de fonctionnement du projet.
        :param running: Statut de fonctionnement (bool)
        """
        self.__running__ = running

    def is_running(self) -> bool:
        """
        Getter.
        Retourne le statut de fonctionnement du projet.
        :return: Statut de fonctionnement (bool)
        """
        return self.__running__

    def get_ssh_cmd(self) -> list[str]:
        """
        Génère la commande SSH pour exécuter une commande shell sur l'hôte.
        :param ssh_key: Clé SSH (string)
        :return: Liste des arguments de la commande SSH (list of strings)
        """
        _folder = os.path.join(PROJECTS_ROOT, self.folder)
        if self.param.get("containerizer") == "podman":
            shell_cmd = f"cd '{_folder}' && podman compose -f '" \
                        + f"{self.param.get('specific_compose', 'docker-compose.yml')}' up -d"
        elif self.param.get("containerizer") == "docker":
            shell_cmd = f"cd '{_folder}' && docker compose -f '" \
                        + f"{self.param.get('specific_compose', 'docker-compose.yml')}' up -d"
        elif self.param.get("containerizer") == "k8s":
            shell_cmd = f"cd '{_folder}' && kubectl apply -f '" \
                        + f"{self.param.get('specific_compose', 'k8s-deployment.yml')}'"
        else:
            raise HTTPException(status_code=400, detail="Containerizer non supporté")

        return [
            "ssh", "-i", COMMAND["cert"], "-o", COMMAND["validate"][0], "-o",
            COMMAND["validate"][1], f"{SSH_USER}@{SSH_HOST}", shell_cmd
        ]
