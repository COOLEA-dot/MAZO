from flask import Blueprint, redirect, request, session, current_app, url_for
import os

apple_bp = Blueprint('apple', __name__)

# RUTA SIMPLE PARA PROBAR REGISTRO
@apple_bp.route('/auth/apple')
def auth_apple():
    # construye una URL simple para comprobar que el blueprint funciona.
    # En la integración completa reemplazaremos esto por el flujo real.
    client_id = os.environ.get('APPLE_CLIENT_ID', 'com.mazo.signin')
    redirect_uri = os.environ.get('APPLE_REDIRECT_URI', 'https://mazo-app.com/auth/apple/callback')
    state = os.urandom(8).hex()
    session['apple_auth_state'] = state
    auth_url = f"https://appleid.apple.com/auth/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&state={state}"
    return redirect(auth_url)

@apple_bp.route('/auth/apple/callback', methods=['POST','GET'])
def auth_apple_callback():
    # placeholder para comprobar callback
    code = request.form.get('code') or request.args.get('code')
    return f"Callback recibido. code={code}", 200
