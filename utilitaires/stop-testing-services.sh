#!/bin/bash
# Arrêt propre de tous les services testing-*

for s in $(systemctl list-units --type=service --state=running | grep '^testing-' | awk '{print $1}'); do
  echo "Arrêt du service $s"
  systemctl stop "$s"
done
systemctl stop testing.service
