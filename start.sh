#!/bin/bash

# Crear carpeta contenedora si no existe
mkdir -p static/uploads

# Eliminar carpeta incorrecta si ya existe
if [ -d static/uploads/videos ] && [ ! -L static/uploads/videos ]; then
  rm -rf static/uploads/videos
fi

# Crear el enlace simbólico si no existe
if [ ! -L static/uploads/videos ]; then
  ln -s /mnt/videos static/uploads/videos
fi

# Lanzar la aplicación
exec gunicorn app:app
