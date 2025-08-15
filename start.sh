#!/bin/bash
set -e

# === Rutas reales (puedes sobreescribir con variables de entorno en Render) ===
REAL_VIDEOS_DIR="${REAL_VIDEOS_DIR:-/mnt/videos}"
REAL_THUMBS_DIR="${REAL_THUMBS_DIR:-${REAL_VIDEOS_DIR}/thumbnails}"

# === Rutas públicas (dentro de /static) ===
PUBLIC_UPLOADS_DIR="static/uploads"
PUBLIC_VIDEOS_LINK="${PUBLIC_UPLOADS_DIR}/videos"

PUBLIC_CHAT_UPLOADS_DIR="static/chat_uploads"
PUBLIC_THUMBS_LINK="${PUBLIC_CHAT_UPLOADS_DIR}/thumbnails"

# Crear carpetas contenedoras si no existen
mkdir -p "${PUBLIC_UPLOADS_DIR}"
mkdir -p "${PUBLIC_CHAT_UPLOADS_DIR}"

# Asegurar carpeta real de vídeos y miniaturas (por si aún no existen)
mkdir -p "${REAL_VIDEOS_DIR}"
mkdir -p "${REAL_THUMBS_DIR}"

# --- Enlace simbólico para VIDEOS ---
if [ -d "${PUBLIC_VIDEOS_LINK}" ] && [ ! -L "${PUBLIC_VIDEOS_LINK}" ]; then
  rm -rf "${PUBLIC_VIDEOS_LINK}"
fi
if [ ! -L "${PUBLIC_VIDEOS_LINK}" ]; then
  ln -s "${REAL_VIDEOS_DIR}" "${PUBLIC_VIDEOS_LINK}"
fi

# --- Enlace simbólico para THUMBNAILS ---
if [ -d "${PUBLIC_THUMBS_LINK}" ] && [ ! -L "${PUBLIC_THUMBS_LINK}" ]; then
  rm -rf "${PUBLIC_THUMBS_LINK}"
fi
if [ ! -L "${PUBLIC_THUMBS_LINK}" ]; then
  ln -s "${REAL_THUMBS_DIR}" "${PUBLIC_THUMBS_LINK}"
fi

# Lanzar la aplicación (Eventlet, 1 worker para Socket.IO sin message_queue)
gunicorn app:app --worker-class eventlet -w 1
