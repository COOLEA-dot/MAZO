# wsgi.py
import os
from pathlib import Path
from dotenv import load_dotenv

# 1) Carga .env ANTES de leer variables
load_dotenv(Path(__file__).resolve().parent / ".env")
print("ARCHIVO APPLE ENCONTRADO:", os.path.exists(os.environ.get("APPLE_PRIVATE_KEY_PATH", "")))
# 2) Lee el flag ya con .env cargado
USE_EVENTLET = os.getenv("USE_EVENTLET", "1") == "1"

# 3) Configs de entorno para local/producción
if USE_EVENTLET:
    # Incluso con eventlet, desactiva greendns si te dio problemas en tu servidor
    os.environ.setdefault("EVENTLET_NO_GREENDNS", "yes")
    import eventlet
    eventlet.monkey_patch()  # Debe ocurrir antes de importar la app
else:
    # En local sin eventlet:
    os.environ["EVENTLET_NO_GREENDNS"] = "yes"          # asegura que greendns no entra
    os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")  # permite HTTP en localhost

# 4) Importa la app una vez configurado todo lo anterior
from app import app, socketio

# 5) Ejecutar como script (opcional en local)
if __name__ == "__main__":
    socketio.run(
        app=app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        debug=True,
        use_reloader=True,
    )
