#!/usr/bin/env bash
# Levanta el entorno y abre el dashboard en el navegador.
set -e

cd "$(dirname "$0")"

echo "🏀 Levantando BasketStats Analytics..."
docker compose up -d

URL="http://localhost:8501"

echo "⏳ Esperando a que Streamlit responda en $URL ..."
until curl -s "$URL" >/dev/null 2>&1; do
    sleep 1
done

echo "🌐 Abriendo $URL"
open "$URL"   # macOS. En Linux usar: xdg-open

echo "✅ Listo. Para ver los logs: docker compose logs -f web"
echo "   Para detener: docker compose down"
