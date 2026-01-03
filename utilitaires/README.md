# utilitaires - Gestion des services systemd pour Testing

Ce dossier contient les outils et templates pour automatiser la gestion des services systemd liés à la plateforme Testing et aux projets clients.

## A. Fichiers présents

- **testing.service** : Service principal pour lancer l'infrastructure Testing (podman compose up --build).
- **testing-shutdown.service** : Service systemd pour arrêter proprement tous les services testing-* avant extinction du serveur.
- **testing-project-template.service** : Template de service systemd pour un projet client (à personnaliser via script).
- **rebuild-testing-services.sh** : Script pour régénérer tous les services projets à partir du fichier JSON de configuration.
- **stop-testing-services.sh** : Script appelé par testing-shutdown.service pour arrêter tous les services testing-* et le service principal.

## B. Utilisation

### B1. Régénérer tous les services projets à partir du JSON

Pour synchroniser tous les services systemd des projets clients avec la configuration JSON (création, suppression, activation), utilisez :

```bash
sudo ./rebuild-testing-services.sh
```

Ce script :

- Arrête et supprime tous les services testing-<_projet_>.service existants (hors testing.service)
- Pour chaque projet du fichier app/current_projects.json, crée et active le service correspondant (mais ne le démarre pas)

**Exemple de ports dans docker-compose.yml du projet :**

```yaml
services:
  app:
    image: ...
    ports:
      - "${EXTERNAL_PORT}:80"
```

### B2. Arrêt propre de tous les services

Pour arrêter tous les services testing-* (projets + principal) avant extinction :

```bash
sudo systemctl start testing-shutdown.service
```

Le script stop-testing-services.sh sera exécuté pour arrêter tous les services concernés.

### B3. Personnalisation du template

Le fichier `testing-project-template.service` sert de base pour chaque projet. Les variables `{project}`, `{project_path}` et `{external_port}` sont remplacées automatiquement par le script de régénération.

---

## C. Configuration sudoers pour l'orchestrateur

Pour permettre à l'utilisateur orchestrateur de démarrer et arrêter les services testing* sans mot de passe, ajoutez la ligne suivante dans le fichier sudoers (via `sudo EDITOR=nano visudo`) :

```conf
<username> ALL=NOPASSWD: /bin/systemctl start testing-*, /bin/systemctl stop testing*
<username> ALL=NOPASSWD: /home/auditio-test/auditio-infra-testing/utilitaires/rebuild-testing-services.sh

```

Ainsi, l'utilisateur pourra lancer :

- `systemctl start testing-<projet>.service` (démarrage d'un projet)
- `systemctl stop testing-<projet>.service` (arrêt d'un projet)
- `systemctl stop testing.service` (arrêt du service principal avant extinction)

Le retrait du tiret après `testing` pour le stop permet d'arrêter aussi le service principal `testing.service`.

**Audit IO** - Automatisation de la gestion des services Testing
