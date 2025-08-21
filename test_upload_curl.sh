#!/bin/bash

# Script de test pour l'upload de fichiers .zip avec curl
# Usage: ./test_upload_curl.sh

echo "🔬 Test de l'endpoint /upload-zip avec curl"

# Créer un fichier .zip de test
echo "📦 Création d'un fichier .zip de test..."
echo "Ceci est un fichier de test pour Manus.ai" > test_content.txt
zip test_upload.zip test_content.txt
rm test_content.txt

echo "📎 Fichier test_upload.zip créé"

# Test de l'endpoint d'upload
echo "📤 Envoi de la requête d'upload..."

curl -X POST "http://localhost:8000/upload-zip" \
  -F "file=@test_upload.zip" \
  -F "message=Test d'upload de fichier .zip via curl" \
  -F "platform=manus" \
  -F "wait_for_response=true" \
  -F "timeout_seconds=60" \
  -H "Accept: application/json" \
  -v

echo ""
echo "🧹 Nettoyage du fichier de test..."
rm -f test_upload.zip

echo "✅ Test terminé"
