"""
Module des fonctions utilitaires.
"""

import os
from fastapi import HTTPException, Header
from main import logger

API_KEY = os.environ.get("TESTING_API_KEY", "change-me")


def verify_api_key(x_api_key: str = Header(...)):
    """Vérifie la clé API."""
    if x_api_key != API_KEY:
        logger.warning("Tentative d'accès avec clé API invalide")
        raise HTTPException(status_code=403, detail="Clé API invalide")
    return True
