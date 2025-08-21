#!/bin/bash

echo "🚀 Test CURL avec ZIP réel du projet"
echo "📦 URL ZIP: https://ai-bricks-analyst-production.up.railway.app/api/projects/1754913269434x582556426926555100/zip/download"
echo "🎯 API locale: http://127.0.0.1:8000/upload-zip-from-url"
echo ""

echo "📡 Envoi de la requête..."
echo "⏱️ Timeout: 200s (pour gros fichier)"
echo "🔍 Surveillez les logs de l'API pour voir:"
echo "   - ⚠️ Fichier très volumineux (XXX MB) - timeout ajusté à 180s"
echo "   - 🚀 Début de la simulation du drag & drop"
echo "   - 📊 Transfert de XXX MB vers le navigateur..."
echo "   - ⏱️ Timeout configuré: 180s pour page.evaluate()"
echo "   - ✅ Drag & drop simulé avec succès"
echo ""

curl -X POST http://127.0.0.1:8000/upload-zip-from-url \
  -H "Content-Type: application/json" \
  -d '{
    "zip_url": "https://ai-bricks-analyst-production.up.railway.app/api/projects/1754913269434x582556426926555100/zip/download",
    "message": "Test avec le ZIP réel du projet - analyse des documents.",
    "platform": "manus",
    "conversation_url": "",
    "wait_for_response": false,
    "timeout_seconds": 180
  }' \
  --max-time 200 \
  --connect-timeout 30 \
  -w "\n\n📊 Status HTTP: %{http_code}\n⏱️ Temps total: %{time_total}s\n📦 Taille téléchargée: %{size_download} bytes\n" \
  | jq '.' 2>/dev/null || cat

echo ""
echo "🔍 Si ça fonctionne, vous devriez voir:"
echo "   ✅ status: 'completed'"
echo "   🔗 conversation_url: 'https://www.manus.im/app/...'"
echo "   📁 filename: 'downloaded_file.zip'"
