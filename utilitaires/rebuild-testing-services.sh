#!/bin/bash
# Script pour régénérer tous les services systemd testing-<projet> à partir du JSON, en tenant compte du containerizer et du compose spécifique

PROJECT_ROOT="$(dirname $(dirname $(realpath $0)))"
JSON_FILE="$PROJECT_ROOT/app/current_projects.json"
TEMPLATE="$PROJECT_ROOT/utilitaires/testing-project-template.service"
SYSTEMD_DIR="/etc/systemd/system"

# Arrêter et supprimer tous les services testing-<projet>.service (hors testing.service)
for svc in $(systemctl list-unit-files | grep '^testing-' | grep '.service' | awk '{print $1}'); do
  systemctl stop "$svc"
  systemctl disable "$svc"
  rm -f "$SYSTEMD_DIR/$svc"
done

systemctl daemon-reload

projects=$(jq -c '.[]' "$JSON_FILE")
for proj in $projects; do
  name=$(echo "$proj" | jq -r '.name')
  folder=$(echo "$proj" | jq -r '.folder')
  port=$(echo "$proj" | jq -r '.pod_port')
  compose=$(echo "$proj" | jq -r '.param.specific_compose')
  containerizer=$(echo "$proj" | jq -r '.param.containerizer')

  # Déterminer le chemin du compose
  if [ "$compose" != "null" ] && [ -n "$compose" ]; then
    compose_path="/home/auditio-test/Projects/$folder/$compose"
  else
    compose_path="/home/auditio-test/Projects/$folder/docker-compose.yml"
  fi

  # Déterminer la commande de lancement
  case "$containerizer" in
    podman)
      exec_start="/usr/bin/podman compose -f $compose_path up --build"
      exec_stop="/usr/bin/podman compose -f $compose_path down"
      ;;
    docker)
      exec_start="/usr/bin/docker compose -f $compose_path up --build"
      exec_stop="/usr/bin/docker compose -f $compose_path down"
      ;;
    kubernetes)
      exec_start="/usr/bin/kubectl apply -f $compose_path"
      exec_stop="/usr/bin/kubectl delete -f $compose_path"
      ;;
    k8s)
      exec_start="/usr/bin/kubectl apply -f $compose_path"
      exec_stop="/usr/bin/kubectl delete -f $compose_path"
      ;;
    *)
      echo "Containerizer inconnu pour $name : $containerizer"
      continue
      ;;
  esac

  svc_name="testing-$name.service"
  svc_path="$SYSTEMD_DIR/$svc_name"
  # Correction du chemin pour le dossier du projet
  sed "s/{project}/$name/g; s#{project_path}#/home/auditio-test/Projects/$folder#g; s/{external_port}/$port/g; s#{exec_start}#$exec_start#g; s#{exec_stop}#$exec_stop#g" "$TEMPLATE" > "$svc_path"
  systemctl daemon-reload
  systemctl enable "$svc_name"
  echo "Service $svc_name généré et activé (non démarré)."
done

