"""
Ensemble des paramètres pour l'API de communication SSH.
"""

from os import getenv, path
from typing import Dict, Any

COMMAND: Dict[str, Any] = {"cert": "/home/auditio-test/.ssh/api-shutdown-key",
           "validate": [
               "UserKnownHostsFile=/dev/null",
               "StrictHostKeyChecking=no"
            ],
            "com": "/sbin/shutdown"}
SSH_USER = getenv("SSH_USER", "auditio-test")
SSH_HOST = getenv("SSH_HOST", "localhost")
PROJECTS_JSON = path.expanduser("/app/current_projects.json")
PROJECTS_ROOT = path.expanduser("~/Projects")
TESTING_API_KEY = getenv("TESTING_API_KEY", "default_testing_api_key")
