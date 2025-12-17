import os, time, json, traceback
from flask import Blueprint, request, redirect, session, current_app
from flask_login import login_user
from app import db
from app import User
import jwt
from jwt import PyJWKClient
import requests
 

APPLE_TEAM_ID = os.getenv("APPLE_TEAM_ID")
APPLE_CLIENT_ID = os.getenv("APPLE_CLIENT_ID")
APPLE_KEY_ID = os.getenv("APPLE_KEY_ID")
APPLE_PRIVATE_KEY_PATH = os.getenv("APPLE_PRIVATE_KEY_PATH")
APPLE_REDIRECT_URI = os.getenv("APPLE_REDIRECT_URI")

apple_bp = Blueprint("apple", __name__)

def _unique_username_from_email(email: str) -> str:
    base = email.split("@")[0]
    name = base
    i = 1
    while User.query.filter_by(username=name).first() is not None:
        name = f"{base}{i}"
        i += 1
    return name

def load_private_key():
    with open(APPLE_PRIVATE_KEY_PATH, "r") as f:
        return f.read()

def generate_client_secret():
    now = int(time.time())
    payload = {
        "iss": APPLE_TEAM_ID,
        "iat": now,
        "exp": now + (86400 * 180),
        "aud": "https://appleid.apple.com",
        "sub": APPLE_CLIENT_ID
    }
    headers = {"kid": APPLE_KEY_ID}

    key = load_private_key()
    token = jwt.encode(payload, key, algorithm="ES256", headers=headers)
    return token if isinstance(token, str) else token.decode()

def exchange_code_for_token(code):
    current_app.logger.error(f"[APPLE] Intercambiando code: {code}")

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": APPLE_REDIRECT_URI,
        "client_id": APPLE_CLIENT_ID,
        "client_secret": generate_client_secret()
    }

    resp = requests.post("https://appleid.apple.com/auth/token", data=data, timeout=10)
    current_app.logger.error(f"[APPLE] Token status: {resp.status_code}")
    current_app.logger.error(f"[APPLE] Token response: {resp.text}")

    resp.raise_for_status()
    return resp.json()

def validate_id_token(id_token):
    jwk_client = PyJWKClient("https://appleid.apple.com/auth/keys")
    signing_key = jwk_client.get_signing_key_from_jwt(id_token)
    return jwt.decode(
        id_token,
        signing_key.key,
        algorithms=["RS256", "ES256"],
        audience=APPLE_CLIENT_ID
    )

@apple_bp.route("/auth/apple")
def auth_apple():
    state = os.urandom(16).hex()
    session["apple_auth_state"] = state

    url = (
        "https://appleid.apple.com/auth/authorize"
        f"?response_type=code&response_mode=form_post"
        f"&client_id={APPLE_CLIENT_ID}"
        f"&redirect_uri={APPLE_REDIRECT_URI}"
        f"&state={state}&scope=name%20email"
    )
    return redirect(url)

@apple_bp.route('/auth/apple/callback', methods=['POST', 'GET'])
def auth_apple_callback():
    current_app.logger.error("=== [APPLE CALLBACK] Ahora sí se ejecuta ===")

    try:
        code = request.form.get("code") or request.args.get("code")

        if not code:
            current_app.logger.error("❌ Apple no envió 'code'")
            return "Missing code", 400

        # --- Obtener token de Apple ---
        token_resp = exchange_code_for_token(code)
        id_token_str = token_resp.get("id_token")

        if not id_token_str:
            current_app.logger.error("❌ Apple no devolvió id_token")
            return "No id_token returned", 400

        # --- Validar token ---
        claims = validate_id_token(id_token_str)
        apple_sub = claims.get("sub")
        email = claims.get("email")

        current_app.logger.error(f"[APPLE] SUB={apple_sub} EMAIL={email}")

        # Si Apple NO entrega email → generamos uno temporal
        if not email:
            email = f"apple_{apple_sub}@apple-user.com"
            current_app.logger.error(f"[APPLE] Email no entregado → usando {email}")

        # --- Buscar usuario existente ---
        user = User.query.filter_by(apple_sub=apple_sub).first()

        if not user:
            # Buscar por email
            user = User.query.filter_by(email=email).first()

            if user:
                # Asociar apple_sub a usuario existente
                user.apple_sub = apple_sub
                db.session.commit()
                current_app.logger.error("[APPLE] Usuario encontrado por email → apple_sub asignado")

        # --- Si no existe, crearlo ---
        if not user:
            username = _unique_username_from_email(email)

            user = User(
                username=username,
                email=email,
                apple_sub=apple_sub,
                # NO poner is_verified aquí
            )

            db.session.add(user)
            db.session.commit()

            current_app.logger.error(f"[APPLE] Usuario nuevo creado → id={user.id}")

        # --- Login del usuario ---
        login_user(user)
        current_app.logger.error(f"[APPLE] LOGIN OK → id={user.id}")

        return redirect("/home")

    except Exception as e:
        current_app.logger.exception("❌ ERROR GENERAL EN APPLE CALLBACK")
        return "ERROR CALLBACK", 500