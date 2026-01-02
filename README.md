# 🧪 Testing - Plateforme de test clients

Serveur de test pour les clients d'Audit IO hébergeant 2 à 5 projets en développement simultané. Ce serveur peut être mis en veille à la demande par le système d'orchestration **Hall** pour optimiser la consommation énergétique.

## 📋 Vue d'ensemble

Le serveur **Testing** héberge les projets en cours de développement pour les clients. Il expose une **API de gestion** permettant :

- Lister les projets/conteneurs en cours d'exécution
- Récupérer l'état détaillé d'un projet
- Planifier ou annuler l'extinction du serveur
- Health check pour la vérification de disponibilité

L'API est **sécurisée par clé API** et interagit directement avec Docker pour gérer les conteneurs.

## 🏗️ Structure

```ascii-art
auditio-infra-testing/
├── docker-compose.yml      # Orchestration du service API
├── Dockerfile              # Image Python 3.11 + FastAPI + Docker CLI
├── requirements.txt        # Dépendances Python
├── README.md               # Ce fichier
├── app/                    # Toute l'application FastAPI
│   ├── main.py             # API FastAPI (port 13492)
│   ├── bp_projects.py      # Blueprint gestion des projets
│   ├── current_projects.json # Liste et paramètres des projets
│   ├── functions.py        # Fonctions utilitaires
│   ├── logger.py           # Logger personnalisé
│   ├── models.py           # Modèles Pydantic
│   ├── parameters.py       # Paramètres globaux
│   └── ...                 # Autres modules
├── logs/                   # Logs applicatifs
├── .ssh/                   # Clés SSH pour accès à l'hôte
├── .gitignore              # Fichier gitignore
└── .env.exemple            # Exemple de fichier d'environnement
```

## 🚀 Démarrage rapide

### 1. Configuration

```bash
# Copier le fichier d'environnement (à créer avec vos variables)
cp .env.exemple .env
```

### 2. Lancer le service

```bash
docker compose up -d
# ou
podman compose up -d
```

### 3. Vérifier

```bash
# Health check
curl http://localhost:13492/health
```

## 📚 API REST

### Authentification

Toutes les routes sauf `/health` nécessitent la clé API dans le header :

```json
{
  "X-API-KEY": "votre-clé-secrète"
}
```

### Routes

[Voir section suivante pour la documentation automatique](### Documentation automatique de l'API)
Principales routes disponibles :
- Healthcheck du serveur
- Extinction planifiée
- Extinction immédiate
- Annulation de l'extinction
- Démarrage d'un projet
- Healthcheck d'un projet (asynchrone)
- Arrêt d'un projet
- Liste des projets

### Documentation automatique de l'API

Toutes les routes, paramètres, schémas et exemples de réponses sont accessibles via la documentation interactive générée par FastAPI :

- **Swagger UI** : [http://localhost:13492/docs](http://localhost:13492/docs)
- **Redoc** : [http://localhost:13492/redoc](http://localhost:13492/redoc)

La documentation est toujours à jour avec le code et permet de tester les endpoints directement depuis l'interface web.

## 🔐 Sécurité

### Clé API

- Stockée dans la variable d'environnement `TESTING_API_KEY`
- Par défaut : `change-me` (⚠️ à remplacer en production)
- Utilisée pour authentifier tous les appels API sauf `/health`

### Accès Docker

- Le conteneur API a accès au socket Docker du hôte (`/var/run/docker.sock`)
- Permet d'interroger et contrôler les conteneurs
- ⚠️ Assurer que seules les requêtes autorisées peuvent accéder à l'API

### Network (optionnel)

- Par défaut : mode bridge (accessible sur le port 13492)
- Pour extinction du hôte : décommenter `network_mode: host` dans docker-compose.yml

## 🐳 Infrastructure Docker

### Service `testing-api`

- **Image** : Python 3.11-slim + Docker CLI + FastAPI
- **Port** : 13492 (interne) → 13492 (hôte)
- **Redémarrage** : automatically (unless-stopped)
- **Variables d'environnement** :
  - `TESTING_API_KEY` : clé API
- **Volumes** : accès au socket Docker

### Commandes utiles

```bash
# Logs de l'API
docker-compose logs -f testing-api

# Arrêter le service
docker-compose down

# Reconstruire l'image
docker-compose build --no-cache

# Vérifier les conteneurs gérés par l'API
docker ps
```

## 🔌 Intégration avec Hall

Le serveur Testing est mis en veille/réveil par le système **Hall** selon les politiques configurées.

### Configuration Hall

Dans `hall/config/domains.json` :

```json
{
  "testing.audit-io.fr": {
    "server": {
      "ip": "<ip-testing>",
      "mac": "<mac-testing>"
    },
    "redirect": {
      "url": "https://testing.audit-io.fr",
      "health_check": "http://<ip-testing>:13492/health"
    },
    "policy": {
      "type": "on_demand",
      "inactivity_timeout": 3600
    }
  }
}
```

### Workflow

1. Utilisateur accède à `testing.audit-io.fr`
2. Hall détecte que le serveur est inactif
3. Hall envoie un **Wake-on-LAN** (WoL)
4. Serveur démarre, conteneurs lancent
5. Hall affiche une **page d'attente** avec polling
6. Quand l'API répond `/health` → redirection automatique
7. Après inactivité → Hall planifie extinction via `/api/shutdown`

## 🛠️ Technologies

- **FastAPI** : Framework web Python haute performance
- **Uvicorn** : Serveur WSGI/ASGI
- **Docker** : Orchestration et gestion des conteneurs
- **Python 3.11** : Runtime léger

## 📊 Monitoring

### Logs

```bash
# En temps réel
docker-compose logs -f

# Derniers N lignes
docker-compose logs --tail=50
```

### Health check

L'endpoint `/health` peut être utilisé pour :

- Monitoring continu
- Polls depuis Hall
- Vérification de disponibilité

## 🚨 Dépannage

| Problème | Solution |
| --- | --- |
| Clé API invalide | Vérifier `TESTING_API_KEY` dans docker-compose.yml ou .env |
| Conteneurs non listés | Vérifier que `/var/run/docker.sock` est accessible |
| Erreur 403 sur les routes | Ajouter le header `X-API-KEY` |
| Serveur ne s'éteint pas | Vérifier les droits root du conteneur, logs de l'API |
| Port 13492 en conflit | Changer le mapping dans `docker-compose.yml` |

## 📝 Environnement

### Variables disponibles

- `TESTING_API_KEY` : clé API (défaut : `change-me`)

### Exemple .env

```conf
TESTING_API_KEY=super-secret-key-12345
```

## 📚 Voir aussi

- [../README.md](../README.md) - Documentation principale du projet
- [../hall/README.md](../hall/README.md) - Hall : orchestrateur
- [../hall/WOL_CHECKLIST.md](../hall/WOL_CHECKLIST.md) - Configuration Wake-on-LAN

---

**Audit IO** - Plateforme de test clients  
Serveur de test orchestré et économe en énergie.
