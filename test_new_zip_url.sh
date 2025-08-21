#!/bin/bash

echo "🚀 Test CURL avec nouvelle URL ZIP"
echo "📦 URL ZIP: https://neon-project-analysis.s3.eu-north-1.amazonaws.com/projects/1754913269434x582556426926555100/zips/242391aab5ab02c338673d2079e846c5aaac2fde5df46a3ceb59ae4ce95ae07a-1754913269434x582556426926555100-documents-1755784671716.zip"
echo "🎯 API locale: http://127.0.0.1:8000/upload-zip-from-url"
echo ""

echo "📡 Envoi de la requête..."
echo "⏱️ Timeout: 200s"
echo "🔍 Logs attendus:"
echo "   - ⚠️ Fichier volumineux (XX MB) - timeout ajusté à XXXs"
echo "   - 🚀 Début de la simulation du drag & drop"
echo "   - ⏱️ Timeout configuré: XXXs pour page.evaluate()"
echo "   - ✅ Drag & drop simulé avec succès"
echo ""

curl -X POST http://127.0.0.1:8000/upload-zip-from-url \
  -H "Content-Type: application/json" \
  -d '{
    "zip_url": "https://neon-project-analysis.s3.eu-north-1.amazonaws.com/projects/1754913269434x582556426926555100/zips/242391aab5ab02c338673d2079e846c5aaac2fde5df46a3ceb59ae4ce95ae07a-1754913269434x582556426926555100-documents-1755784671716.zip",
    "message": "Test avec la nouvelle URL ZIP - vérification des corrections timeout.",
    "platform": "manus",
    "conversation_url": "",
    "wait_for_response": false,
    "timeout_seconds": 120
  }' \
  --max-time 150 \
  --connect-timeout 30 \
  -w "\n\n📊 Status HTTP: %{http_code}\n⏱️ Temps total: %{time_total}s\n📦 Taille téléchargée: %{size_download} bytes\n" \
  | jq '.' 2>/dev/null || cat

echo ""
echo "🎯 Si les corrections fonctionnent:"
echo "   ✅ Pas d'erreur 'timeout' keyword argument"
echo "   ✅ Status: 'completed'"
echo "   🔗 conversation_url valide"
