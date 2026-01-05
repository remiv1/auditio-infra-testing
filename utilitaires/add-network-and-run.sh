#!/bin/bash

# Vérifier les paramètres
if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <nom_du_projet> <nom_du_service>"
  exit 1
fi

PROJECT_NAME="$1"
SERVICE_NAME="$2"
PROJECT_ROOT="/home/auditio-test/auditio-infra-testing"
JSON_FILE="$PROJECT_ROOT/app/current_projects.json"
NETWORK_NAME="auditio-net"

# Vérifier si le fichier JSON existe
if [ ! -f "$JSON_FILE" ]; then
  echo "Erreur : Le fichier JSON $JSON_FILE n'existe pas."
  exit 1
fi

# Récupérer les informations du projet à partir du fichier JSON
project=$(jq -c ".[] | select(.name == \"$PROJECT_NAME\")" "$JSON_FILE")
if [ -z "$project" ]; then
  echo "Erreur : Projet $PROJECT_NAME introuvable dans $JSON_FILE."
  exit 1
fi

folder=$(echo "$project" | jq -r '.folder')
compose=$(echo "$project" | jq -r '.param.specific_compose')

# Déterminer le chemin du fichier compose
if [ "$compose" != "null" ] && [ -n "$compose" ]; then
  compose_path="/home/auditio-test/Projects/$folder/$compose"
else
  compose_path="/home/auditio-test/Projects/$folder/docker-compose.yml"
fi

echo "Traitement du projet $PROJECT_NAME... et du service $SERVICE_NAME dans le compose $compose_path"

# Vérifier si le fichier compose existe
if [ ! -f "$compose_path" ]; then
  echo "Erreur : Le fichier compose $compose_path n'existe pas."
  exit 1
fi

# Ajouter le réseau au service spécifique
current_networks=$(yq eval ".services.$SERVICE_NAME.networks" "$compose_path")
echo "Réseaux actuels pour le service $SERVICE_NAME : $current_networks"
if [ "$current_networks" == "null" ]; then
  echo "Initialisation des réseaux pour le service $SERVICE_NAME..."
  yq eval -i ".services.$SERVICE_NAME.networks = [\"$NETWORK_NAME\"]" "$compose_path"
else
  if ! yq eval ".services.$SERVICE_NAME.networks[] | select(. == \"$NETWORK_NAME\")" "$compose_path" > /dev/null 2>&1; then
    echo "Ajout du réseau $NETWORK_NAME au service $SERVICE_NAME dans $compose_path..."
    yq eval -i ".services.$SERVICE_NAME.networks += [\"$NETWORK_NAME\"]" "$compose_path"
  fi
fi

# Ajouter la définition du réseau si elle n'existe pas
current_network_definition=$(yq eval ".networks.$NETWORK_NAME" "$compose_path")
echo "Définition actuelle du réseau $NETWORK_NAME : $current_network_definition"
if [ "$current_network_definition" == "null" ]; then
  echo "Ajout de la définition du réseau $NETWORK_NAME dans $compose_path..."
  yq eval -i ".networks.$NETWORK_NAME.external = true" "$compose_path"
fi

# Lancer Podman Compose
echo "docker-compose prêt à être lancé pour le projet $1 avec le réseau $NETWORK_NAME."
