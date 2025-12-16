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

@apple_bp.route("/auth/apple/callback", methods=["GET", "POST"])
def auth_apple_callback():
    current_app.logger.error("=== [APPLE CALLBACK] Ahora sí se ejecuta ===")

    code = request.form.get("code") or request.args.get("code")
    if not code:
        return "Missing code", 400

    token_response = exchange_code_for_token(code)
    id_token = token_response.get("id_token")
    if not id_token:
        return "No id_token", 400

    claims = validate_id_token(id_token)

    apple_sub = claims.get("sub")
    email = claims.get("email")

    current_app.logger.error(f"[APPLE] SUB: {apple_sub} EMAIL: {email}")

    user = User.query.filter_by(apple_sub=apple_sub).first()
    if not user and email:
        user = User.query.filter_by(email=email).first()

    if not user:
        user = User(email=email, apple_sub=apple_sub, is_confirmed=True)
        db.session.add(user)
        db.session.commit()

    login_user(user)

    return redirect("/home")
