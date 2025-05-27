#!/bin/bash

# Crear carpeta si no existe
mkdir -p static/uploads

# Crear el enlace simbólico si aún no existe
if [ ! -L static/uploads/videos ]; then
  ln -s /mnt/videos static/uploads/videos
fi

# Lanzar la aplicación
exec gunicorn app:app
