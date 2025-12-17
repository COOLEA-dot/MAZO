# auth/google.py

import os
import secrets
import base64
import json

from flask import Blueprint, request, redirect, session, url_for, flash, jsonify, current_app
from flask_login import login_user
from google.oauth2 import id_token
import google.auth.transport.requests as grequests

from app import db, oauth
from models import User
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import IntegrityError

GOOGLE_CLIENT_ID = (os.getenv("GOOGLE_CLIENT_ID") or "").strip()
GOOGLE_CLIENT_SECRET = (os.getenv("GOOGLE_CLIENT_SECRET") or "").strip()
GOOGLE_ANDROID_CLIENT_ID = (os.getenv("GOOGLE_ANDROID_CLIENT_ID") or "").strip()  # opcional
GOOGLE_IOS_CLIENT_ID     = (os.getenv("GOOGLE_IOS_CLIENT_ID") or "").strip()      # opcional

google_bp = Blueprint("google_auth", __name__)


def _preferred_external_url(path: str) -> str:
    base = os.environ.get("EXTERNAL_BASE_URL")
    if base:
        return base.rstrip("/") + path

    scheme = request.headers.get("X-Forwarded-Proto", request.scheme) or "https"
    host   = request.headers.get("Host") or request.host
    return f"{scheme}://{host}{path}"


# ------------------- WEB LOGIN -----------------------

@google_bp.get("/login/google")
def login_google():
    cid = (os.getenv("GOOGLE_CLIENT_ID") or "").strip()
    csec = (os.getenv("GOOGLE_CLIENT_SECRET") or "").strip()

    if not cid or not csec:
        current_app.logger.error("[GOAUTH] Missing Google credentials")
        flash("Error interno. Falta configuración de Google OAuth.", "danger")
        return redirect(url_for("login"))

    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    session["oauth_state"] = state
    session["oauth_nonce"] = nonce

    redirect_uri = _preferred_external_url("/auth/google/callback")

    current_app.logger.warning(
        "[GOAUTH] redirect_uri=%s host=%s cid_prefix=%s",
        redirect_uri,
        request.headers.get("Host"),
        cid[:10] + "…",
    )

    return oauth.google.authorize_redirect(
        redirect_uri,
        state=state,
        nonce=nonce,
        prompt="consent",
        include_granted_scopes="true",
        access_type="offline",
    )


# ------------------- GOOGLE CALLBACK -----------------------

@google_bp.get("/auth/google/callback")
def google_callback():
    """Callback oficial de Google OAuth."""
    returned_state = request.args.get("state")
    expected_state = session.pop("oauth_state", None)

    if not returned_state or returned_state != expected_state:
        current_app.logger.warning("[GOAUTH] STATE mismatch")
        flash("Error de autenticación. Intenta de nuevo.", "danger")
        return redirect(url_for("login"))

    try:
        token = oauth.google.authorize_access_token()
    except Exception as e:
        current_app.logger.error(f"[GOAUTH] Error exchanging code: {e}")
        flash("No se pudo completar el login con Google.", "danger")
        return redirect(url_for("login"))

    raw_id = token.get("id_token")

    try:
        nonce = session.pop("oauth_nonce", None)
        claims = oauth.google.parse_id_token(token, nonce=nonce)
    except Exception as e:
        current_app.logger.error(f"[GOAUTH] parse_id_token failed: {e}")
        flash("No se pudo verificar tu identidad con Google.", "danger")
        return redirect(url_for("login"))

    email   = claims.get("email")
    google_id = claims.get("sub")
    name    = claims.get("name")
    picture = claims.get("picture")

    if not google_id:
        flash("No se pudo obtener tu ID de Google.", "danger")
        return redirect(url_for("login"))

    # Buscar o crear usuario
    user = None
    if email:
        user = User.query.filter_by(email=email).first()

    if not user:
        user = User.query.filter_by(google_id=google_id).first()

    if not user:
        username = email.split("@")[0] if email else f"user_{google_id[:8]}"
        user = User(
            username=username,
            email=email,
            name=name,
            profile_pic=picture,
            google_id=google_id,
            password_hash=generate_password_hash(os.urandom(16).hex())
        )
        db.session.add(user)
        db.session.commit()
        current_app.logger.warning(f"[GOAUTH] New user created id={user.id}")

    login_user(user, remember=True)
    current_app.logger.warning(f"[GOAUTH] Login OK user_id={user.id}")

    return redirect(url_for("home"))


# ------------------- MOBILE LOGIN -----------------------

@google_bp.post("/mobile/login/google")
def mobile_google_login():

    data = request.get_json(silent=True) or {}
    token = data.get("idToken")

    if not token:
        return jsonify({"ok": False, "error": "missing_id_token"}), 400

    allowed_auds = [
        c for c in [
            os.getenv("GOOGLE_CLIENT_ID"),
            os.getenv("GOOGLE_ANDROID_CLIENT_ID"),
            os.getenv("GOOGLE_IOS_CLIENT_ID"),
        ] if c
    ]

    req = grequests.Request()
    info = None

    for aud in allowed_auds:
        try:
            info = id_token.verify_oauth2_token(token, req, aud)
            break
        except Exception:
            continue

    if info is None:
        return jsonify({"ok": False, "error": "invalid_token"}), 401

    email = info.get("email")
    google_id = info.get("sub")

    if not email:
        return jsonify({"ok": False, "error": "no_email"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            username=email.split("@")[0],
            email=email,
            google_id=google_id,
            password_hash=generate_password_hash(os.urandom(16).hex()),
        )
        db.session.add(user)
        db.session.commit()

    login_user(user)

    return jsonify({"ok": True, "username": user.username, "email": user.email})
