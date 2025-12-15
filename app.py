from flask import Flask, render_template, request, redirect, g, url_for, flash, session, send_from_directory, abort, jsonify, Blueprint, current_app
from flask_socketio import SocketIO, join_room, leave_room, send
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import RequestEntityTooLarge
import os 
import mimetypes
from flask_cors import CORS
import subprocess
from flask_migrate import Migrate
from flask_login import login_required, current_user, login_user, LoginManager
from flask_wtf.csrf import CSRFProtect, CSRFError, validate_csrf, generate_csrf
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import logging
from datetime import datetime
from jinja2 import environment
import uuid 
import time
import base64
from flask_mail import Mail, Message as Mailmessage
from itsdangerous import URLSafeTimedSerializer
from email.header import Header
from flask_socketio import join_room, emit
from flask import request
import stripe
from flask_babel import Babel, get_locale 
import json, shlex
from sqlalchemy import or_, func, inspect
from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
from pathlib import Path
import sqlalchemy as sa
from itsdangerous import BadSignature, SignatureExpired
from urllib.parse import urlparse
from requests.exceptions import RequestException
import secrets 
from slugify import slugify 
import sys
import jwt
from jwt import PyJWKClient
import traceback 
import logging
from extensions import db
from models import (
    User,
    UserToken,
    user_professions,
    Profession,
    Opinion,
    Comment,
    Reply,
    Video,
    Like,
    Conversation,
    Message,
    Notification,
    Project,
    Offer,
    Response,
    Job,
    RegisterForm,
    OpinionForm,
    ChangePasswordForm,
    ProjectApplication,
    ProjectForm,
    JobApplication,
    JobForm,
    CURRENCY_CHOICES,
)

def print(*args, **kwargs):
    kwargs["file"] = sys.stdout
    return __builtins__.print(*args, **kwargs)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("apple")

# Helper seguro para hacer strip sin fallar si value es None
def _safe_strip(value):
    """Devuelve value.strip() si value no es None, sino cadena vacía."""
    return (value or "").strip()

ENV_PATH = Path(__file__).resolve().parent / ".env"
app = Flask(__name__)
from auth.apple import apple_bp
app.register_blueprint(apple_bp)

app.config.update(
    SECRET_KEY="c65ChhxLvx0nFVW16ZD0cyPyTdvP1q77V5DK2lzAjfw",      # que no cambie entre peticiones
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,          # en http local debe ser False
    REMEMBER_COOKIE_SAMESITE="Lax",
    REMEMBER_COOKIE_SECURE=False,
    SESSION_COOKIE_DOMAIN=None,           # deja que Flask escoja
)


os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
os.environ['EVENTLET_NO_GREENDNS'] = 'yes'
oauth = OAuth(app)
app.config['ENV'] = 'production'
app.config['DEBUG'] = False
app.config["SECRET_KEY"] = "AOM11091950"
app.config["WTF_CSRF_ENABLED"] = True
app.config['WTF_CSRF_TIME_LIMIT'] = None  # Token CSRF nunca expira (solo para desarrollo)
app.config["WTF_CSRF_CHECK_REFERER"] = False
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'mazo.app.es@gmail.com'
app.config['MAIL_PASSWORD'] = 'wuuvsqlospvdtuzw'  # sin espacios
app.config['MAIL_DEFAULT_SENDER'] = 'mazo.app.es@gmail.com'
app.config["STRIPE_SECRET_KEY"] = os.getenv("STRIPE_SECRET_KEY")
app.config["STRIPE_PUBLIC_KEY"] = os.getenv("STRIPE_PUBLIC_KEY")
app.config['BABEL_DEFAULT_LOCALE'] = 'es' 
app.config['BABEL_SUPPORTED_LOCALES'] = ['es', 'en', 'fr', 'de', 'it', 'pt', 'ar', 'ja'] 
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("SQLALCHEMY_DATABASE_URI", "sqlite:///mazo.db")
app.config['CV_UPLOAD_FOLDER'] = os.path.join('static', 'cv')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
UPLOAD_FOLDER = 'static/uploads/videos'
CHAT_UPLOAD_FOLDER = 'static/chat_uploads'
THUMBNAIL_FOLDER = "static/chat_uploads/thumbnails"
PROFILE_PICS_FOLDER = 'static/profile_pics'  # <--- Añadido

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CHAT_UPLOAD_FOLDER'] = CHAT_UPLOAD_FOLDER
app.config['PROFILE_PICS_FOLDER'] = PROFILE_PICS_FOLDER  

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'webm', 'mov', 'pdf', 'docx', 'pptx', 'avi', 'mpg'}
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB

for folder in [UPLOAD_FOLDER, CHAT_UPLOAD_FOLDER, PROFILE_PICS_FOLDER]:  # <--- Incluido aquí
    if not os.path.exists(folder):
        os.makedirs(folder)

db.init_app(app)
USE_EVENTLET = os.getenv("USE_EVENTLET", "0") == "1"
async_mode = "eventlet" if USE_EVENTLET else "threading"

GOOGLE_CLIENT_ID = (os.getenv("GOOGLE_CLIENT_ID") or "").strip()
GOOGLE_CLIENT_SECRET = (os.getenv("GOOGLE_CLIENT_SECRET") or "").strip()
GOOGLE_ANDROID_CLIENT_ID = (os.getenv("GOOGLE_ANDROID_CLIENT_ID") or "").strip()  # opcional
GOOGLE_IOS_CLIENT_ID     = (os.getenv("GOOGLE_IOS_CLIENT_ID") or "").strip()      # opcional

TEAM_ID = os.environ.get('APPLE_TEAM_ID')
CLIENT_ID = os.environ.get('APPLE_CLIENT_ID')
KEY_ID = os.environ.get('APPLE_KEY_ID')
PRIVATE_KEY_PATH = os.environ.get('APPLE_PRIVATE_KEY_PATH')
REDIRECT_URI = os.environ.get('APPLE_REDIRECT_URI')

os.makedirs(app.config['CV_UPLOAD_FOLDER'], exist_ok=True)

# Lee la config sin fallar al importar
PRICE_ID = os.getenv("STRIPE_PRICE_ID")

bp = Blueprint("admin_offers", __name__, url_prefix="/admin/offers")
offers_public = Blueprint("offers_public", __name__, url_prefix='/offers')


# register blueprints
app.register_blueprint(offers_public)
app.register_blueprint(bp)

# Configuración de Stripe (segura)
stripe_key = os.environ.get("STRIPE_SECRET_KEY")
if not stripe_key:
    # En producción quizá prefieras raise RuntimeError para forzar configuración.
    # Para permitir arranque en entornos de test/dev usa logging.warning:
    import logging
    logging.warning("STRIPE_SECRET_KEY no encontrada. Stripe no funcionará hasta que se configure.")
else:
    stripe.api_key = stripe_key

# Extensiones permitidas para CV
ALLOWED_CV_EXTENSIONS = {'pdf', 'doc', 'docx'}

allowed_origins = [
    "https://mazo-app.com",
    "http://localhost:5000",
]
# si usas ngrok en local, añade EXTERNAL_BASE_URL al vuelo
ext_base = os.environ.get("EXTERNAL_BASE_URL")
if ext_base:
    allowed_origins.append(ext_base)

socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)  # permite orígenes y logging

csrf = CSRFProtect(app)
csrf.init_app(app)

logging.basicConfig(level=logging.DEBUG)
stripe.api_key = app.config['STRIPE_SECRET_KEY']

mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)
babel = Babel(app)

convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
metadata = sa.MetaData(naming_convention=convention)

migrate = Migrate(app, db)
google = oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'         # función de login
login_manager.login_message_category = 'info'

app.logger.info('[DBG-LM] login_manager instance id=%s repr=%s login_view=%s', id(login_manager), repr(login_manager), getattr(login_manager, 'login_view', None))

def _dump_before_request_funcs():
    try:
        funcs = app.before_request_funcs or {}
        # funcs is a dict: {None: [fn,...], 'blueprint': [fn,...], ...}
        for bp, flist in funcs.items():
            names = []
            for f in flist:
                try:
                    names.append(f"{getattr(f,'__module__','?')}.{getattr(f,'__name__','<lambda>')}")
                except Exception:
                    names.append(repr(f))
            app.logger.info('[DBG-DUMP] before_request_funcs for %s: %s', bp or 'None', names)
    except Exception as e:
        app.logger.exception('[DBG-DUMP] error dumping before_request_funcs: %s', e)

_dump_before_request_funcs()



# Info del login_manager
try:
    app.logger.info('[DBG-LM] login_manager id=%s repr=%s login_view=%s', id(login_manager), repr(login_manager), getattr(login_manager,'login_view',None))
except Exception:
    app.logger.exception('[DBG-LM] login_manager not accessible')
# ===============================================================================

# ---------- DEBUG: wrapear before_request funcs para ver cuál devuelve algo ----------
import functools

def _wrap_before_request_funcs():
    funcs = app.before_request_funcs or {}
    for bp, flist in list(funcs.items()):
        wrapped = []
        for f in flist:
            # crear wrapper con closure para el f correcto
            def make_wrapper(func):
                @functools.wraps(func)
                def wrapper(*a, **kw):
                    try:
                        rv = func(*a, **kw)
                    except Exception as e:
                        # no interferimos: lanzar la excepción hacia arriba para que lo veas
                        app.logger.exception('[BR-WRAP] exception in before_request %s: %s', func.__name__, e)
                        raise
                    if rv is not None:
                        # Detectado: esta before_request devolvió algo (p. ej. redirect)
                        app.logger.warning('[BR-WRAP] before_request %s returned NON-None: %s', 
                                           f"{getattr(func,'__module__','?')}.{getattr(func,'__name__','<lambda>')}", 
                                           repr(rv))
                    return rv
                return wrapper
            wrapped.append(make_wrapper(f))
        app.before_request_funcs[bp] = wrapped

# Llamar al wrap (temporal)
_wrap_before_request_funcs()
app.logger.info('[BR-WRAP] before_request funcs wrapped for debug')
# -------------------------------------------------------------------------------

def allowed_cv(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_CV_EXTENSIONS
    
def ensure_jobs_projects_tables():
    inspector = inspect(db.engine)
    db.create_all()  # crea todas las tablas de todos los modelos
    # (Opcional) explícito por si quieres:
    if not inspector.has_table("project"):
        Project.__table__.create(bind=db.engine, checkfirst=True)
    if not inspector.has_table("job"):
        Job.__table__.create(bind=db.engine, checkfirst=True)

def init_services():
    import os
    if os.getenv("MAZO_SKIP_SERVICES") == "1":
        print("SKIP services (migrations/CLI)")
        return

    # Importar Firebase SOLO si vamos a usarlo
    import firebase_admin
    from firebase_admin import credentials

    cred_path = os.getenv("FIREBASE_CREDENTIALS")
    if cred_path and os.path.isfile(cred_path):
        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        print("Firebase inicializado")
    else:
        print("WARN: FIREBASE_CREDENTIALS no definido o ruta inválida. Omitiendo Firebase.")

@app.after_request
def add_csrf_cookie(response):
    response.set_cookie('csrf_token', generate_csrf(), samesite='Lax', secure=True)
    return response

@babel.localeselector
def select_locale():
    return session.get('lang') or request.accept_languages.best_match(app.config['BABEL_SUPPORTED_LOCALES'])

def init_services():
    import os, json
    global firebase_ready, messaging

    # Saltar servicios externos en CLI/migraciones
    if os.getenv("MAZO_SKIP_SERVICES") == "1":
        print("SKIP services (migrations/CLI)")
        return

    try:
        import firebase_admin
        from firebase_admin import credentials, messaging as fb_messaging

        creds_env = os.getenv("FIREBASE_CREDENTIALS")
        if not creds_env:
            print("WARN: FIREBASE_CREDENTIALS no definido. Omitiendo Firebase.")
            return

        # Ruta a archivo o JSON embebido
        if os.path.isfile(creds_env):
            cred = credentials.Certificate(creds_env)
        else:
            data = json.loads(creds_env)
            if "private_key" in data:
                data["private_key"] = data["private_key"].replace("\\n", "\n")
            cred = credentials.Certificate(data)

        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)

        # Exponer messaging para el resto del módulo
        messaging = fb_messaging
        firebase_ready = True
        print("Firebase inicializado")

    except Exception as e:
        # No bloquees el arranque por Firebase
        firebase_ready = False
        messaging = None
        print(f"WARN: No se pudo inicializar Firebase: {e}")

@app.context_processor
def inject_locale():
    return dict(current_locale=select_locale()) 

@app.route('/set_language', methods=['POST'])
def set_language():
    lang = request.form.get('language')
    session['lang'] = lang

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(success=True)
    return redirect(request.referrer or url_for('settings'))

@app.route("/admin/offers/stripe/subscribe", methods=["POST"])
@login_required
def subscribe():
    data = request.json or {}
    payment_method = data.get("payment_method")
    promo_code_text = data.get("promo_code")  # opcional, enviado por el usuario

    # 1) Crear o obtener el cliente
    if not current_user.stripe_customer_id:
        customer = stripe.Customer.create(
            email=current_user.email,
            name=current_user.username,
            metadata={"user_id": current_user.id}
        )
        current_user.stripe_customer_id = customer.id
        db.session.commit()

    customer_id = current_user.stripe_customer_id

    # 2) Asociar el método de pago
    stripe.PaymentMethod.attach(payment_method, customer=customer_id)
    stripe.Customer.modify(customer_id, invoice_settings={"default_payment_method": payment_method})

    # 3) Preparar los argumentos de la suscripción
    sub_kwargs = {
        "customer": customer_id,
        "items": [{"price": PRICE_ID}],
        "payment_behavior": "default_incomplete",
        "expand": ["latest_invoice.payment_intent"],
        "trial_period_days": 30  # 👈 primer mes gratis universal
    }

    # 4) Si el usuario introduce un código promocional, Stripe lo valida
    if promo_code_text:
        promo_list = stripe.PromotionCode.list(code=promo_code_text, limit=1)
        if promo_list.data:
            sub_kwargs["promotion_code"] = promo_list.data[0].id

    # 5) Crear la suscripción
    sub = stripe.Subscription.create(**sub_kwargs)

    current_user.stripe_subscription_id = sub.id
    db.session.commit()

    return jsonify({
        "subscriptionId": sub.id,
        "clientSecret": sub.latest_invoice.payment_intent.client_secret
    }), 201

def apply_coupon_to_subscription(subscription_id, coupon_id):
    stripe.Subscription.modify(
        subscription_id,
        discounts=[{"coupon": coupon_id}],
        proration_behavior="none"
    )

def remove_all_discounts(subscription_id):
    stripe.Subscription.modify(
        subscription_id,
        discounts=[],
        proration_behavior="none"
    )

@app.route("/admin/offers/create", methods=["POST"])
@login_required  # valida admin
def create_offer():
    data = request.json
    name = data["name"]
    slug = data.get("slug") or slugify.slugify(name)
    kind = data["kind"]
    value = data.get("value")
    starts_at = data.get("starts_at")
    ends_at = data.get("ends_at")
    max_uses = data.get("max_uses")
    use_stripe = data.get("use_stripe", False)
    stripe_coupon_id = None
    stripe_promotion_code = None

    # Si pides crear coupon en Stripe
    if use_stripe:
        if kind == "percent":
            coupon = stripe.Coupon.create(percent_off=value, duration="once")
        elif kind == "first_month_free":
            coupon = stripe.Coupon.create(percent_off=100, duration="repeating", duration_in_months=1)
        elif kind == "fixed":
            # Stripe fixed amount for invoices needs currency & amount_off in cents
            coupon = stripe.Coupon.create(amount_off=value, currency="eur", duration="once")
        else:
            coupon = None

        if coupon:
            stripe_coupon_id = coupon.id
            # Crear promotion code asociado (opcional — facilita que el usuario use un código legible)
            promo = stripe.PromotionCode.create(coupon=coupon.id, code=slug.upper())
            stripe_promotion_code = promo.id

    offer = Offer(
        name=name, slug=slug, kind=kind, value=value,
        starts_at=starts_at, ends_at=ends_at, max_uses=max_uses,
        stripe_coupon_id=stripe_coupon_id, stripe_promotion_code=stripe_promotion_code
    )
    db.session.add(offer)
    db.session.commit()
    return jsonify({"ok": True, "offer_id": offer.id})

@app.route("/admin/offers/list", methods=["GET"])
def list_offers():
    now = datetime.utcnow()
    offers = Offer.query.filter(Offer.active==True, Offer.starts_at<=now).filter(
        (Offer.ends_at==None) | (Offer.ends_at>=now)
    ).all()
    return jsonify([{
        "id": o.id, "name": o.name, "slug": o.slug, "kind": o.kind,
        "value": o.value, "stripe_promo": o.stripe_promotion_code
    } for o in offers])

@app.route("/offers/validate", methods=["POST"])
def validate_offer():
    """
    Espera JSON: { "code": "MAZO50" }
    Devuelve JSON: { ok: True/False, type, id, code, percent, new_price_display, msg }
    """
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()
    if not code:
        return jsonify({"ok": False, "msg": "Código vacío"}), 400

    # Asegúrate de haber configurado stripe.api_key en tu app (sk_test) antes de llamar aquí
    try:
        # 1) Intentar encontrar promotion_code en Stripe (devuelve promo id y coupon)
        res = stripe.PromotionCode.list(code=code, limit=1)
        if res and getattr(res, "data", None):
            promo = res.data[0]
            coupon = promo.coupon
            percent = getattr(coupon, "percent_off", None)
            # Puedes calcular new_price_display leyendo tu precio real; aquí uso ejemplo:
            try:
                price_amount = float(current_app.config.get("FRONTEND_BASE_PRICE", 9.99))
            except Exception:
                price_amount = 9.99
            new_price = None
            if percent is not None:
                new_price = round(price_amount * (100 - percent) / 100, 2)
            new_price_display = f"{new_price:.2f} €" if new_price is not None else None

            return jsonify({
                "ok": True,
                "type": "promotion_code",
                "id": promo.id,          # promo_...
                "code": promo.code,      # texto legible
                "percent": percent,
                "new_price_display": new_price_display
            })

    except Exception as e:
        # no matar la petición por un fallo con Stripe — solo loguear y seguir
        current_app.logger.debug("Stripe PromotionCode lookup error: %s", e)

    # 2) Alternativa: busca en tu propia tabla Offer si tienes una (opcional)
    try:
        offer = Offer.query.filter((Offer.slug == code) | (Offer.name == code)).first()
        if offer and offer.active:
            percent = offer.value if offer.kind == "percent" else None
            price_amount = float(current_app.config.get("FRONTEND_BASE_PRICE", 9.99))
            new_price = None
            if percent is not None:
                new_price = round(price_amount * (100 - percent) / 100, 2)
            return jsonify({
                "ok": True,
                "type": "offer",
                "id": offer.id,
                "code": offer.slug,
                "percent": percent,
                "new_price_display": f"{new_price:.2f} €" if new_price is not None else None
            })
    except Exception:
        # si no tienes modelo Offer, ignora esto
        pass

    return jsonify({"ok": False, "msg": "Código no válido"}), 404

@app.route('/settings')
@login_required
def settings():
    stripe_key = current_app.config.get("STRIPE_PUBLISHABLE_KEY") or current_app.config.get("STRIPE_PUBLIC_KEY") or ""
    price_display = "9.99 €"

    # URL de redirección
    try:
        redirect_url = url_for('billing_success')
    except Exception:
        redirect_url = url_for('profile', username=current_user.username)

    return render_template(
        "settings.html",
        stripe_publishable_key=stripe_key,
        validate_url=url_for('validate_offer'),
        subscribe_url=url_for('subscribe'),
        price_display=price_display,
        redirect_url=redirect_url
    )

@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    # Asegúrate de haber configurado STRIPE_SECRET_KEY en current_app.config
    stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY') or os.getenv('STRIPE_SECRET_KEY')

    try:
        # Lógica de selección de cupón (igual a la tuya)
        coupon_id = None
        if not current_user.is_premium:
            coupon_id = "6Yv3IfUM"
        elif getattr(current_user, "has_referred_3_users", False):
            coupon_id = "XUVigsdb"
        elif getattr(current_user, "has_uploaded_10_videos", False):
            coupon_id = "k3XAmNSH"

        params = {
            "payment_method_types": ["card"],
            "mode": "subscription",
            "line_items": [
                {
                    "price": os.getenv('STRIPE_PRICE_ID', 'price_1SJHheIDZoLGPA1zjcpIpgqt'),
                    "quantity": 1,
                }
            ],
            "success_url": url_for('activate_premium', _external=True),  # o activate_premium si es tu ruta
            "cancel_url": url_for('premium', _external=True),
            "metadata": {"user_id": str(current_user.id)},
        }

        if coupon_id:
            params["discounts"] = [{"coupon": coupon_id}]

        checkout_session = stripe.checkout.Session.create(**params)

        # Devuelve ID y URL para máxima compatibilidad con distintos clientes
        return jsonify({"id": checkout_session.id, "url": checkout_session.url})

    except stripe.error.StripeError as e:
        current_app.logger.error("Stripe API error: %s", e)
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.exception("Error creando checkout session")
        return jsonify({"error": "Error interno del servidor"}), 500

@app.route('/pay-with-elements', methods=['POST'])
@login_required
def pay_with_elements():
    try:
        data = request.get_json()
        payment_method_id = data.get('payment_method_id')

        # Crear el intento de pago
        intent = stripe.PaymentIntent.create(
            amount=999,  # en céntimos
            currency='eur',
            payment_method=payment_method_id,
            confirmation_method='manual',
            confirm=True,
        )

        if intent.status == 'requires_action' and intent.next_action.type == 'use_stripe_sdk':
            return jsonify({'requires_action': True, 'payment_intent_client_secret': intent.client_secret})
        elif intent.status == 'succeeded':
            current_user.is_premium = True
            db.session.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Pago no completado.'}), 400
    except Exception as e:
        print("❌ ERROR EN PAGO CON ELEMENTS:", e)
        return jsonify({'error': str(e)}), 400  

@app.route("/stripe/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig = request.headers.get("Stripe-Signature")
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    try:
        event = stripe.Webhook.construct_event(payload, sig, endpoint_secret)
    except Exception as e:
        abort(400)
    # procesar evento...
    return {"ok": True}

@app.route('/security')
def seguridad():
    return render_template('seguridad.html')

@app.route('/.well-known/assetlinks.json')
def assetlinks():
    return send_from_directory('static/.well-known', 'assetlinks.json')

def allowed_file(filename):
    """Verifica si la extensión y el tipo MIME del archivo son válidos"""
    if '.' not in filename:
        print("❌ Error: El archivo no tiene extensión.")
        return False

    ext = filename.rsplit('.', 1)[1].lower()
    mime_type, _ = mimetypes.guess_type(filename)

    print(f"📂 Verificando archivo: {filename} | Extensión: {ext} | MIME: {mime_type}")

    if ext not in ALLOWED_EXTENSIONS:
        print(f"❌ Error: Extensión no permitida ({ext}).")
        return False

    if not mime_type or not mime_type.startswith(('image', 'video', 'application')):
        print(f"❌ Error: Tipo MIME no permitido ({mime_type}).")
        return False

    return True

@app.template_filter('sort')
def sort_filter(value):
    if isinstance(value, list):
        return sorted(value)
    return value

@app.route('/api/videos')
def api_videos():
    videos = Video.query.order_by(Video.id.desc()).all()

    video_list = []
    for video in videos:
        is_liked = current_user.is_authenticated and current_user in video.liked_by

        video_list.append({
            "url": url_for('uploaded_file', filename=video.video_url, _external=True),
            "id": video.id,
            "title": video.title,
            "description": video.description,
            "hashtags": video.hashtags,
            "likes": video.like_count,
            "is_liked": is_liked,
            "user": {
                "username": video.user.username if video.user else "desconocido",
                "profile_picture": url_for(
                    'static', 
                    filename='profile_pics/' + (video.user.profile_pic if video.user and video.user.profile_pic else 'default.jpg'),
                    _external=True
                ),
                "company": video.user.company if video.user else "",
                "name": video.user.name if video.user else ""
            }
        })

    return jsonify(video_list)

@app.route('/privacy')
def privacy_policy():
    return render_template('privacy.html', current_date="4 de junio de 2025")


oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile",  # 👈 email es imprescindible
    },
)

@app.route('/api/me')
@login_required
def api_me():
    return jsonify({
        "username": g.user.username,
        "email":g.user.email,
        "phone": g.user.phone
    })

@app.route('/register_token', methods=['POST'])
@login_required
def register_token():
    token = request.json.get('token')
    if not token:
        return jsonify({'error': 'No token provided'}), 400

    # Verificar si ya existe
    existing = UserToken.query.filter_by(fcm_token=token).first()
    if not existing:
        new_token = UserToken(user_id=current_user.id, fcm_token=token)
        db.session.add(new_token)
        db.session.commit()

    return jsonify({'success': True})

def send_push_notification(tokens, title, body, data=None):
    # Normaliza tokens
    if isinstance(tokens, str):
        tokens = [tokens]
    tokens = [t for t in (tokens or []) if t]
    if not tokens:
        return False, {'error': 'Sin tokens'}

    # Verifica estado de Firebase
    if not firebase_ready or messaging is None:
        return False, {'error': 'Firebase no inicializado'}

    # FCM: máximo 500 tokens por lote
    CHUNK = 500
    total_success, total_failure = 0, 0
    data = {str(k): str(v) for k, v in (data or {}).items()}

    for i in range(0, len(tokens), CHUNK):
        chunk = tokens[i:i+CHUNK]
        msg = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            data=data,
            tokens=chunk
        )
        try:
            resp = messaging.send_multicast(msg)
            total_success += resp.success_count
            total_failure += resp.failure_count
        except Exception as e:
            print("ERROR FCM:", e)
            total_failure += len(chunk)

    return True, {'success': total_success, 'failure': total_failure}

@app.route('/send_test_notification')
@login_required
def send_test_notification():
    # Obtener todos los tokens del usuario actual (puedes modificar para otros usuarios)
    tokens = [t.fcm_token for t in current_user.tokens]

    if not tokens:
        return 'No hay tokens registrados para enviar notificaciones.', 400

    send_push_notification(tokens, '¡Hola!', 'Esta es una notificación de prueba.')

    return 'Notificación enviada'

@app.route('/follow/<int:user_id>', methods=['POST'])
@login_required
def follow_user(user_id):
    user_to_follow = User.query.get_or_404(user_id)
    if current_user.id != user_to_follow.id:
        current_user.follow(user_to_follow)
        db.session.commit()
    return redirect(url_for('profile', username=user_to_follow.username))

@app.route('/unfollow/<int:user_id>', methods=['POST'])
@login_required
def unfollow_user(user_id):
    user_to_unfollow = User.query.get_or_404(user_id)
    if current_user.id != user_to_unfollow.id:
        current_user.unfollow(user_to_unfollow)
        db.session.commit()
    return redirect(url_for('profile', username=user_to_unfollow.username))

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def inicio():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    return render_template('inicio.html')

from flask_mail import Message
import stripe

def send_referral_reward_email(email):
    """Envía el correo con el cupón de 3 meses gratis al usuario referido."""
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

    # Crear cupón de Stripe (3 meses gratis)
    coupon = stripe.Coupon.create(
        duration="repeating",
        duration_in_months=3,
        percent_off=100,
        name="3 meses gratis por referidos"
    )

    msg = Message(
        "🎁 ¡Has ganado 3 meses gratis en MAZO!",
        recipients=[email]
    )
    msg.body = f"""
    ¡Felicidades! Has invitado a 3 nuevos usuarios a MAZO.

    Usa este código promocional en tu próxima renovación:
    {coupon.id}

    🎉 Este cupón te da 3 meses adicionales totalmente gratis.

    ¡Gracias por ayudar a crecer la comunidad MAZO!
    """
    try:
        mail.send(msg)
        print(f"Correo enviado a {email} con cupón {coupon.id}")
    except Exception as e:
        print("Error enviando correo de referidos:", e)

@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    referral_code = request.args.get("ref")  # captura link de referido

    # Si se envió el formulario y pasó la validación de WTForms
    if form.validate_on_submit():
        # Extraer datos de forma segura (evita AttributeError por None)
        name = _safe_strip(request.form.get("name") or getattr(form, "name", None) and getattr(form.name, "data", ""))
        username = _safe_strip(getattr(form.username, "data", ""))
        phone = _safe_strip(request.form.get("phone") or getattr(form, "phone", None) and getattr(form.phone, "data", ""))
        email = _safe_strip(getattr(form.email, "data", ""))
        password = (getattr(form.password, "data", "") or "").strip()
        confirm_password = (getattr(form.confirm_password, "data", "") or "").strip()
        company = (_safe_strip(getattr(form, "company", None) and getattr(form.company, "data", ""))) or None
        profession = (_safe_strip(getattr(form, "profession", None) and getattr(form.profession, "data", ""))) or None
        description = (_safe_strip(getattr(form, "description", None) and getattr(form.description, "data", ""))) or None
        location = (_safe_strip(getattr(form, "location", None) and getattr(form.location, "data", ""))) or None

        # Validación de contraseñas (por si alguien omite el campo)
        if not password:
            flash("Introduce una contraseña.", "error")
            return render_template("register.html", form=form)

        if password != confirm_password:
            flash("Las contraseñas no coinciden", "error")
            return render_template("register.html", form=form)

        # Crear profesión si es nueva (si viene rellenada)
        if profession:
            existing_prof = Profession.query.filter_by(name=profession).first()
            if not existing_prof:
                new_prof = Profession(name=profession)
                db.session.add(new_prof)
                db.session.commit()

        # Verificar usuario o email existentes
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash("El nombre de usuario o correo ya está en uso.", "error")
            return render_template("register.html", form=form)

        # Guardar foto de perfil (si se subió)
        profile_picture = None
        filename = None
        try:
            if getattr(form, "profile_pic", None) and getattr(form.profile_pic, "data", None):
                profile_picture = form.profile_pic.data
            else:
                # fallback si usas request.files directamente
                profile_picture = request.files.get("profile_pic")
        except Exception:
            profile_picture = None

        if profile_picture and getattr(profile_picture, "filename", None):
            safe_name = secure_filename(profile_picture.filename)
            # generar nombre único para evitar colisiones
            ext = safe_name.rsplit(".", 1)[-1] if "." in safe_name else ""
            filename = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
            picture_folder = app.config.get("PROFILE_PICS_FOLDER", os.path.join("static", "profile_pics"))
            os.makedirs(picture_folder, exist_ok=True)
            picture_path = os.path.join(picture_folder, filename)
            try:
                profile_picture.save(picture_path)
                # Guardaremos la ruta relativa en el modelo
                profile_pic_db_value = f"profile_pics/{filename}"
            except Exception as e:
                print("Error guardando foto de perfil:", e)
                profile_pic_db_value = "profile_pics/default.jpg"
        else:
            profile_pic_db_value = "profile_pics/default.jpg"

        # Crear nuevo usuario
        new_user = User(
            name=name or None,
            username=username or None,
            phone=phone or None,
            email=email or None,
            company=company,
            profession=profession,
            description=description,
            location=location,
            profile_pic=profile_pic_db_value
        )

        # Guardar la contraseña (tu método set_password)
        new_user.set_password(password)

        # 🔥 Lógica de referido (si existe)
        if referral_code:
            referrer = User.query.filter_by(referral_code=referral_code).first()
            if referrer:
                referrer.referred_count = (referrer.referred_count or 0) + 1
                db.session.add(referrer)
                db.session.commit()

                # 🎁 Si alcanzó 3 referidos → enviar correo con promoción
                if referrer.referred_count == 3:
                    send_referral_reward_email(referrer.email)

        # Guardar nuevo usuario en BD
        db.session.add(new_user)
        db.session.commit()

        # Enviar verificación por email (si lo tienes)
        try:
            send_verification_email(new_user.email)
        except Exception as e:
            print("Error enviando email de verificación:", e)

        flash("Registro exitoso. Verifica tu email para activar tu cuenta.", "info")
        return redirect(url_for("login"))

    # Si no es POST o la validación falló, mostrar formulario
    professions = [p.name for p in Profession.query.order_by(Profession.name).all()]
    return render_template("register.html", form=form, user=None, professions=professions)

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Contraseña actualizada correctamente.', 'success')
            return redirect(url_for('profile', username=current_user.username))
        else:
            flash('La contraseña actual no es correcta.', 'danger')
    return render_template('change_password.html', form=form)

@app.route("/api/professions")
def profession_suggestions():
    q = request.args.get("q", "").strip()
    base = Profession.query
    if q:
        base = base.filter(func.lower(Profession.name).like(func.lower(f"%{q}%")))
    items = base.order_by(Profession.name.asc()).limit(10).all()
    return jsonify([p.name for p in items])


def _is_safe_next(next_url: str) -> bool:
    if not next_url:
        return False
    return urlparse(next_url).netloc == ''  # solo rutas internas

@app.before_request
def load_user():
    user_id = session.get('user_id')  # Verifica el ID del usuario en la sesión
    if user_id:
        g.user = User.query.get(user_id)  # Carga el usuario desde la base de datos
    else:
        g.user = None  # Si no hay usuario en sesión, asigna None

@app.before_request
def inject_user_into_g():
    g.user = current_user if current_user.is_authenticated else None


@app.route('/login', methods=['GET', 'POST'])
def login():
  
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))  # checkbox opcional

        if not username or not password:
            flash('Por favor completa todos los campos.', 'error')
            return render_template('login.html')

        user = User.query.filter_by(username=username).first()

        if user and getattr(user, 'password_hash', None) and check_password_hash(user.password_hash, password):
            login_user(user, remember=remember)
            flash(f"¡Bienvenido, {user.username}!", "success")

            # Manejo seguro de 'next'
            next_url = request.args.get('next')
            if next_url and urlparse(next_url).netloc == '':
                return redirect(next_url)
            return redirect(url_for('home'))

        flash("Usuario o contraseña incorrectos", "error")

    # GET: muestra el formulario (conserva ?next=...)
    return render_template('login.html')

def send_verification_email(user_email):
    token = serializer.dumps(user_email, salt='email-confirm')
    confirm_url = url_for('confirm_email', token=token, _external=True)
    html = f'''
    <p>Hola, haz clic en el siguiente enlace para verificar tu email:</p>
    <a href="{confirm_url}">{confirm_url}</a>
    '''

    msg = Mailmessage(
        subject="Verifica tu email",  # Sin codificación extra
        recipients=[user_email],
        html=html
    )
    mail.send(msg)

@app.get('/confirm/<token>', endpoint='confirm_email')
def confirm_email(token):
    try:
        # amplía max_age si quieres (ej. 3 días: 60*60*24*3)
        email = serializer.loads(token, salt='email-confirm', max_age=60*60*24*3)
    except SignatureExpired:
        flash('El enlace de verificación ha expirado.', 'warning')
        return redirect(url_for('login'))
    except BadSignature:
        flash('El enlace de verificación no es válido.', 'danger')
        return redirect(url_for('login'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('login'))

    # Idempotente: si ya estaba verificado, no falla
    if getattr(user, 'is_verified', False):
        flash('Tu correo ya estaba verificado.', 'info')
        return redirect(url_for('login'))  # o dashboard

    user.is_verified = True
    db.session.commit()
    app.logger.info(f"[confirm_email] {email} verificado")

    flash('Correo verificado con éxito. ¡Ya puedes usar todas las funciones!', 'success')
    return redirect(url_for('login'))  # o url_for('dashboard') si prefieres

def _preferred_external_url(path: str) -> str:
    """
    Devuelve una URL absoluta usando EXTERNAL_BASE_URL si existe (prod),
    o el host real de la petición (local/prod sin variable).
    """
    base = os.environ.get("EXTERNAL_BASE_URL")
    if base:
        return base.rstrip("/") + path
    # Sin EXTERNAL_BASE_URL: usa el host que ve Flask (asegúrate de tener ProxyFix)
    scheme = request.headers.get("X-Forwarded-Proto", request.scheme) or "https"
    host   = request.headers.get("Host") or request.host
    return f"{scheme}://{host}{path}"

@app.get("/login/google")
def login_google():
    # Comprobar que las credenciales están cargadas
    cid = (os.getenv("GOOGLE_CLIENT_ID") or "").strip()
    csec = (os.getenv("GOOGLE_CLIENT_SECRET") or "").strip()
    if not cid or not csec:
        app.logger.error("[GOAUTH] Falta GOOGLE_CLIENT_ID o GOOGLE_CLIENT_SECRET en el entorno")
        flash("Config OAuth incompleta en el servidor. Avísame.", "danger")
        return redirect(url_for("login"))

    # Guardar state y nonce para CSRF/OIDC
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    session['oauth_nonce'] = nonce

    # Construir redirect_uri que COINCIDA con lo registrado en Google
    redirect_uri = _preferred_external_url("/auth/google/callback")

    app.logger.warning(
        "[GOAUTH] redirect_uri=%s  host=%s  client_id_prefix=%s",
        redirect_uri,
        request.headers.get("Host"),
        (cid[:12] + "…")
    )

    return oauth.google.authorize_redirect(
        redirect_uri,
        state=state,
        nonce=nonce,
        prompt="consent",
        include_granted_scopes="true",
        access_type="offline",
    )

@app.get("/auth/google/callback", endpoint="google_callback")
def google_callback():
    # ---------- A) CSRF: validar state ----------
    returned_state = request.args.get('state')
    expected_state = session.pop('oauth_state', None)
    if not returned_state or not expected_state or returned_state != expected_state:
        app.logger.warning("[OIDC] STATE mismatch: returned=%r expected=%r", returned_state, expected_state)
        flash("CSRF: el parámetro state no coincide. Vuelve a intentarlo.", "danger")
        return redirect(url_for("login"))

    # ---------- B) Intercambiar code por tokens ----------
    try:
        token = oauth.google.authorize_access_token()
        if not token:
            app.logger.warning("[OIDC] authorize_access_token devolvió token vacío")
            flash("No se obtuvo token de Google", "danger")
            return redirect(url_for("login"))
    except Exception as e:
        app.logger.exception("[OIDC] Error en authorize_access_token: %s", e)
        flash(f"Error de autorización con Google: {e}", "danger")
        return redirect(url_for("login"))

    # DEBUG del token (seguro, sin imprimir secretos)
    raw_id = token.get("id_token")
    app.logger.warning(
        "[OIDC][DBG] has_id_token=%s access_token_len=%s scope=%r",
        bool(raw_id), len(token.get('access_token','')), token.get('scope')
    )

    def _b64url_decode_to_json(b64url: str):
        try:
            padding = '=' * (-len(b64url) % 4)
            data = base64.urlsafe_b64decode(b64url + padding)
            return json.loads(data.decode('utf-8'))
        except Exception as e:
            app.logger.warning("[OIDC][DBG] fallo al decodificar base64url: %s", e)
            return None

    # ---------- C) Intento A: ID Token (sin red) ----------
    info = None
    try:
        nonce = session.pop('oauth_nonce', None)
        claims = oauth.google.parse_id_token(token, nonce=nonce) if nonce else oauth.google.parse_id_token(token)
        if claims:
            app.logger.warning("[OIDC][DBG] id_token.payload(parse_id_token) = %s", json.dumps(claims, ensure_ascii=False))
            info = {
                "email":           claims.get("email"),
                "name":            claims.get("name") or "",
                "picture":         claims.get("picture") or "",
                "sub":             claims.get("sub"),
                "email_verified":  claims.get("email_verified"),
            }
    except Exception as e:
        app.logger.warning("[OIDC] parse_id_token falló: %s", e)

    # ---------- D) Intento B: userinfo OIDC (si falta email) ----------
    if not (info and info.get("email")):
        try:
            resp = oauth.google.get("https://openidconnect.googleapis.com/v1/userinfo")
            app.logger.warning("[OIDC][DBG] userinfo status=%s body=%s", getattr(resp, "status_code", None), getattr(resp, "text", None))
            resp.raise_for_status()
            ui = resp.json()
            info = {
                "email":           ui.get("email"),
                "name":            ui.get("name") or "",
                "picture":         ui.get("picture") or "",
                "sub":             ui.get("sub"),
                "email_verified":  ui.get("email_verified"),
            }
        except RequestException as e:
            app.logger.exception("[OIDC] userinfo error: %s", e)

    # ---------- E) Intento C: Decodificación manual del id_token (debug) ----------
    if not (info and info.get("email")) and raw_id and raw_id.count('.') == 2:
        h_b64, p_b64, _ = raw_id.split('.')
        payload = _b64url_decode_to_json(p_b64) or {}
        app.logger.warning("[OIDC][DBG] id_token.payload(manual) = %s", json.dumps(payload, ensure_ascii=False))
        info = info or {}
        info.setdefault("email", payload.get("email"))
        info.setdefault("name",  payload.get("name") or "")
        info.setdefault("picture", payload.get("picture") or "")
        info.setdefault("sub",   payload.get("sub"))
        info.setdefault("email_verified", payload.get("email_verified"))

    # ---------- F) Modo rescate: permitir login sin email usando 'sub' ----------
    if not info:
        app.logger.warning("[OIDC] No se pudo construir 'info' ni siquiera con decodificación manual.")
        flash("No se pudo obtener datos mínimos de Google. Inténtalo de nuevo.", "danger")
        return redirect(url_for("login"))

    email = info.get("email")
    sub   = info.get("sub")
    if not sub:
        app.logger.warning("[OIDC] Falta 'sub' en claims; no podemos identificar la cuenta.")
        flash("No se pudo identificar tu cuenta de Google (sin 'sub').", "danger")
        return redirect(url_for("login"))

    # Si NO hay email, seguimos adelante usando 'sub' (google_id) como clave
    if not email:
        app.logger.warning("[OIDC] ID Token/userinfo sin 'email'. Seguimos por 'sub' únicamente (modo rescate).")
        # Opción: puedes inventar un email interno no real (si tu modelo requiere no-null):
        # email = f"{sub}@google.local"
        # o permitir email nullable en tu modelo.

    # ---------- G) Crear / actualizar usuario ----------
    user = None
    if email:
        user = User.query.filter_by(email=email).first()

    if not user:
        # Si no encontramos por email, probamos por google_id (sub)
        user = User.query.filter_by(google_id=sub).first()

    if not user:
        user = User(
            username=(email.split("@")[0] if email else f"user_{sub[:8]}"),
            email=email,  # puede ser None si tu modelo lo permite
            name=info.get("name"),
            profile_pic=info.get("picture"),
            google_id=sub,
            password_hash=generate_password_hash(os.urandom(16).hex()),
        )
        db.session.add(user)
        db.session.commit()
        app.logger.warning("[OIDC] Usuario creado: id=%s email=%r google_id=%r", user.id, user.email, user.google_id)
    else:
        updated = False
        if not getattr(user, "google_id", None):
            user.google_id = sub
            updated = True
        if not user.profile_pic and info.get("picture"):
            user.profile_pic = info.get("picture")
            updated = True
        if updated:
            db.session.commit()
            app.logger.warning("[OIDC] Usuario actualizado: id=%s email=%r google_id=%r", user.id, user.email, user.google_id)

    # ---------- H) Login + redirect ----------
    login_user(user, remember=True)
    next_url = request.args.get("next") or url_for("home")
    app.logger.warning("[OIDC][OK] Login completado para user_id=%s; redirect=%s", user.id, next_url)
    return redirect(next_url)

# ========== UTILIDAD: USERNAME ÚNICO DESDE EMAIL ==========
def _unique_username_from_email(email: str) -> str:
    base = email.split("@")[0]
    name = base
    i = 1
    while User.query.filter_by(username=name).first() is not None:
        name = f"{base}{i}"; i += 1
    return name

# ========== LOGIN MÓVIL (ID TOKEN) ==========
# Si usas CSRFProtect global, probablemente necesites eximir esta ruta:
# @csrf.exempt
@app.post("/mobile/login/google")
def mobile_google_login():
    """
    Espera JSON: {"idToken": "<token>"}
    Devuelve: {"ok": True, "username": "...", "email": "..."}
    """
    data = request.get_json(silent=True) or {}
    token = data.get("idToken") or data.get("id_token")
    if not token:
        return jsonify({"ok": False, "error": "missing_id_token"}), 400

    # Acepta varios 'aud' válidos (web + android + ios) por si usas múltiples clientes
    allowed_auds = [c for c in [GOOGLE_CLIENT_ID, GOOGLE_ANDROID_CLIENT_ID, GOOGLE_IOS_CLIENT_ID] if c]
    if not allowed_auds:
        return jsonify({"ok": False, "error": "server_not_configured"}), 500

    req = grequests.Request()
    idinfo = None
    last_err = None
    for aud in allowed_auds:
        try:
            tmp = id_token.verify_oauth2_token(token, req, aud)
            # sanity checks
            iss = tmp.get("iss")
            if iss not in ("accounts.google.com", "https://accounts.google.com"):
                continue
            # si quieres forzar email verificado:
            # if not tmp.get("email_verified", False): continue
            idinfo = tmp
            break
        except Exception as e:
            last_err = e

    if idinfo is None:
        return jsonify({"ok": False, "error": f"invalid_token: {last_err}"}), 401

    email = idinfo.get("email")
    google_id = idinfo.get("sub")
    name = idinfo.get("name")
    picture = idinfo.get("picture")

    if not email:
        return jsonify({"ok": False, "error": "no_email"}), 400

    user = User.query.filter_by(email=email).first()
    if user is None:
        try:
            user = User(
                username=_unique_username_from_email(email),
                email=email,
                name=name,
                profile_pic=picture,
                google_id=google_id,
                password=generate_password_hash(os.urandom(16).hex())
            )
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            # reintenta por google_id
            user = User.query.filter_by(google_id=google_id).first()
            if user is None:
                return jsonify({"ok": False, "error": "db_integrity"}), 500
    else:
        if not getattr(user, "google_id", None):
            user.google_id = google_id
            if not user.profile_pic and picture:
                user.profile_pic = picture
            db.session.commit()

    login_user(user)
    return jsonify({"ok": True, "username": user.username, "email": user.email})
@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(error):
    flash('El archivo es demasiado grande, por favor sube un archivo más pequeño', 'error')
    return redirect(url_for('upload'))

videos = [
    {"id": 1, "likes": 0, "liked_by": []},  # 'liked_by' almacena usuarios que dieron like
    {"id": 2, "likes": 0, "liked_by": []},
]

@app.route('/like/<int:video_id>', methods=['POST', 'DELETE'])
@login_required
def like_video(video_id):
    if 'user_id' not in session:
        return jsonify({"success": False, 'message': 'No estás autorizado para realizar esta acción'}), 401

    video = Video.query.get_or_404(video_id)
    user = current_user

    if request.method == 'POST':
        if video in user.liked_videos:
            return jsonify({'success': False, 'message': 'Ya has dado like a este video'}), 400
        user.liked_videos.append(video)
        liked = True
    elif request.method == 'DELETE':
        if video not in user.liked_videos:
            return jsonify({'success': False, 'message': 'No has dado like en este video'}), 200
        user.liked_videos.remove(video)
        liked = False

    db.session.commit()

 
    likes_count = len(video.liked_by)
    comments_count = len(video.comments)

 # Similar para comentarios

    return jsonify({
       'success': True,
       'liked': liked, 
       'new_likes': likes_count,
       'comments_count': comments_count
    })

@app.route('/comments/<int:video_id>', methods=['POST'])
@login_required
def add_comment(video_id):
    try:
        data = request.get_json()
        comment_data = data.get('comment')
        parent_id = data.get('parent_id')  # Esto es nuevo

        if not comment_data:
            return jsonify({'success': False, 'message': 'Comentario vacío'}), 400

        video = Video.query.get(video_id)
        if not video:
            return jsonify({'success': False, 'message': 'Video no encontrado.'}), 404

        new_comment = Comment(
            content=comment_data,
            video_id=video.id,
            user_id=current_user.id,
            parent_id=parent_id  # Esto es lo nuevo
        )
        db.session.add(new_comment)
        video.comments_count += 1
        db.session.commit()
        db.session.refresh(new_comment)

        return jsonify({
            'success': True,
            'comment': comment_data,
            'username': current_user.username,
            'comment_id': new_comment.id,
            'profile_picture': current_user.profile_pic or 'default.jpg',
            'is_owner': True,
            'parent_id': parent_id
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    
@app.route('/comments/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)

    if comment.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'No tienes permisos'}), 403

    try:
        comment.content = "Comentario eliminado"
        comment.is_deleted = True

        video = Video.query.get(comment.video_id)
        if video:
            video.comments_count = max(0, video.comments_count - 1)

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/comments/<int:video_id>', methods=['GET'])
def get_comments(video_id):
    video = Video.query.get_or_404(video_id)
    comments = Comment.query.filter_by(video_id=video.id).order_by(Comment.id.asc()).all()

    comment_map = {}
    for comment in comments:
        if comment.parent_id is None:
            comment_map[comment.id] = {
                'id': comment.id,
                'content': comment.content,
                'username': comment.user.username,
                'profile_picture': comment.user.profile_pic or 'default.jpg',
                'is_owner': current_user.is_authenticated and comment.user_id == current_user.id,
                'is_deleted': comment.is_deleted,
                'replies': []
            }

    # Añadir respuestas a sus respectivos padres
    for comment in comments:
        if comment.parent_id and comment.parent_id in comment_map:
            comment_map[comment.parent_id]['replies'].append({
                'id': comment.id,
                'content': comment.content if not comment.is_deleted else 'Comentario eliminado',
                'username': comment.user.username,
                'profile_picture': comment.user.profile_pic or 'default.jpg',
                'is_owner': current_user.is_authenticated and comment.user_id == current_user.id,
                'is_deleted': comment.is_deleted
            })

    return jsonify(list(comment_map.values()))

@app.route('/comments/<int:comment_id>/replies', methods=['GET'])
def get_replies(comment_id):
    from sqlalchemy.orm import joinedload

    replies = Comment.query.filter_by(parent_id=comment_id).options(joinedload(Comment.user)).all()

    reply_list = []
    for reply in replies:
        reply_list.append({
            'id': reply.id,
            'content': reply.content if not reply.is_deleted else 'Comentario eliminado',
            'username': reply.user.username,
            'profile_picture': reply.user.profile_pic or 'default.jpg',
            'is_owner': reply.user_id == current_user.id,
            'is_deleted': reply.is_deleted
        })

    return jsonify(reply_list)

@app.route('/home')
def home():
    user = None
    chats = []

    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        if user is None:
            # El usuario no existe, limpiar sesión
            session.pop('user_id', None)
            session.pop('username', None)
        else:
            chats = get_user_chats(user.id)

    # Obtener video introductorio
    intro_video = Video.query.filter_by(is_intro=True).first()

    # Base query excluyendo el video introductorio si existe
    base_query = Video.query
    if intro_video:
        base_query = base_query.filter(Video.id != intro_video.id)

    # Separar videos por tipo de usuario (premium primero)
    premium_videos = (
        base_query.join(User).filter(User.is_premium == True).order_by(Video.id.desc()).all()
    )
    regular_videos = (
        base_query.join(User).filter(User.is_premium == False).order_by(Video.id.desc()).all()
    )

    # Combinar: intro (si existe) + premium + normales
    videos = []
    if intro_video:
        videos.append(intro_video)
    videos.extend(premium_videos)
    videos.extend(regular_videos)

    return render_template('home.html', user=user, videos=videos, chats=chats)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '').strip()
    location = request.args.get('location', '').strip()

    if query:
        # Construir patrón para ilike, seguro para múltiples palabras
        pattern = f"%{query}%"

        # Buscar videos donde título, descripción o usuario relacionado contengan query
        videos = Video.query.join(User).filter(
            or_(
                Video.title.ilike(pattern),
                Video.description.ilike(pattern),
                User.name.ilike(pattern),
                User.company.ilike(pattern),
                User.profession.ilike(pattern),
                User.description.ilike(pattern),
                User.location.ilike(pattern)
            )
        ).order_by(Video.id.desc()).all()

        # Buscar usuarios donde varios campos contengan query
        users = User.query.filter(
            or_(
                User.name.ilike(pattern),
                User.company.ilike(pattern),
                User.profession.ilike(pattern),
                User.description.ilike(pattern),
                User.location.ilike(pattern)
            )
        ).all()

        flash(f"Resultados para: '{query}'", "info")

    else:
        videos, users = [], []

    return render_template('search.html', videos=videos, users=users, query=query)

@app.route('/test-video')
def test_video():
    return render_template('test_video.html')

def search_suggestions():
    query = request.args.get('q','').strip()
    
    if not query:
        return jsonify ([])
    
    suggestions = User.query.filter(
        (User.name.ilike(f"%{query}%")) |
        (User.company.ilike(f"%{query}%")) |
        (User.profession.ilike(f"%{query}%"))
    ).limit(5).all()

    suggestions_list = [{'name': user.name, 'company':user.company, 'profession': user.profession} for user in suggestions]
    return jsonify (suggestions_list)
 
@socketio.on('connect')
def socket_connect():
    # Esto se ejecuta cuando el cliente consigue abrir la conexión websocket/polling
    app.logger.info('SOCKET CONNECT: sid=%s current_user=%s authenticated=%s', 
                    request.sid,
                    getattr(current_user, 'username', None),
                    getattr(current_user, 'is_authenticated', None))
    # opcional: enviar un ping de ack
    emit('server_connect_ack', {'ok': True, 'sid': request.sid})

def _rel_from_root(abs_path):
    if not abs_path:
        return None
    # asume que tu app se sirve desde el directorio raíz del proyecto
    proj_root = os.path.abspath(app.root_path)  # p.ej. /home/user/proj
    abs_path_norm = os.path.abspath(abs_path)
    try:
        rel = os.path.relpath(abs_path_norm, proj_root)
        return rel.replace("\\", "/")  # e.g. "static/chat_uploads/file_123.mp4"
    except Exception as e:
        print("_rel_from_root error", e)
        return None

@app.route('/chat/<recipient_identifier>', methods=['GET'])
@login_required
def chat_with_user(recipient_identifier):
    """
    Mostrar la interfaz del chat. recipient_identifier puede ser username o id numérico.
    """
    # DEBUG: imprimir contexto
    current_app.logger.info(
        '[chat_view] request.path=%s current_user=%s authenticated=%s cookies=%s',
        request.path,
        getattr(current_user, 'username', None),
        getattr(current_user, 'is_authenticated', None),
        dict(request.cookies)
    )

    sender = current_user

    # Intentar interpretar como id entero primero
    recipient = None
    if str(recipient_identifier).isdigit():
        try:
            recipient = User.query.get(int(recipient_identifier))
        except Exception as ex:
            current_app.logger.exception('[chat_view] error buscando por id: %s', ex)

    # Si no lo encontramos por id, buscar por username
    if not recipient:
        recipient = User.query.filter_by(username=recipient_identifier).first()

    if not recipient:
        flash('Usuario no encontrado', 'error')
        return redirect(url_for('home'))

    # Buscar o crear conversación
    conversation = Conversation.query.filter(
        ((Conversation.user_id == sender.id) & (Conversation.recipient_id == recipient.id)) |
        ((Conversation.user_id == recipient.id) & (Conversation.recipient_id == sender.id))
    ).first()

    if not conversation:
        conversation = Conversation(user_id=sender.id, recipient_id=recipient.id)
        db.session.add(conversation)
        db.session.commit()

    # Marcar mensajes del otro usuario como leídos
    try:
        Message.query.filter(
            Message.conversation_id == conversation.id,
            Message.sender_id != sender.id,
            Message.is_read == False
        ).update({'is_read': True})
        db.session.commit()
    except Exception as e:
        current_app.logger.exception("[chat_view] error marcando leídos: %s", e)
        db.session.rollback()

    messages = Message.query.filter_by(conversation_id=conversation.id).order_by(Message.timestamp).all()

    # Sala consistente (helper que ya tienes)
    room = chat_room_by_username(sender.username, recipient.username)

    return render_template('chat.html',
                           recipient=recipient,
                           username=sender.username,
                           messages=messages,
                           room=room,
                           conversation_id=conversation.id)

@socketio.on('join')
def handle_join(data):
    room = data.get('room')
    payload_user = data.get('username')
    app.logger.info('JOIN event received: sid=%s payload_user=%s room=%s', request.sid, payload_user, room)
    app.logger.info('JOIN current_user=%s authenticated=%s', getattr(current_user,'username',None), getattr(current_user,'is_authenticated',None))
    if not room:
        emit('join_ack', {'ok': False, 'error': 'no room provided'}, room=request.sid)
        return
    join_room(room)
    app.logger.info('✅ Usuario unido a la sala: %s (sid=%s)', room, request.sid)
    emit('join_ack', {'ok': True, 'room': room}, room=request.sid)
    emit('user_joined', {'username': payload_user}, room=room, include_self=False)
    # Une a la sala (esto asocia request.sid a la room)
    join_room(room)
    app.logger.info('✅ Usuario unido a la sala: %s (sid=%s)', room, request.sid)

    # Ack al emisor confirmando unión
    emit('join_ack', {'ok': True, 'room': room}, room=request.sid)

    # Notify other users in the room (exclude the sender)
    emit('user_joined', {'username': payload_user}, room=room, include_self=False)

def get_user_chats(user_id):
    conversations = Conversation.query.filter(
        (Conversation.user_id == user_id) | (Conversation.recipient_id == user_id)
    ).all()

    chat_data = []
    for conv in conversations:
        other_user = conv.get_other_user(user_id)
        
        if other_user is None:
            # Si no existe el otro usuario, ignorar esta conversación
            continue
        
        last_message = Message.query.filter_by(conversation_id=conv.id).order_by(Message.timestamp.desc()).first()

        if last_message:
            unread_messages = Message.query.filter_by(
                conversation_id=conv.id,
                is_read=False,
                sender_id=other_user.id  # Solo contar si son mensajes del otro usuario
            ).count()

            has_unread = unread_messages > 0  # True si hay mensajes sin leer
            sent_by_user = last_message.sender_id == user_id
        else:
            has_unread = False
            sent_by_user = False

        chat_data.append({
            'username': other_user.username,
            'profile_pic': other_user.profile_pic.split('/')[-1] if other_user.profile_pic else 'default.jpg',
            'last_message': last_message.content if last_message else "No hay mensajes",
            'sent_by_user': sent_by_user,
            'has_unread': has_unread  
        })

    return chat_data

@app.route('/chats')
@login_required
def chats():
    # current_user ya está disponible y autenticado gracias a @login_required
    print("CHATS VIEW - current_user:", current_user, "is_authenticated:", current_user.is_authenticated, "id:", getattr(current_user, 'id', None))

    user_id = current_user.id
    # get_user_chats debe devolver una lista de objetos/dicts con los campos que usas en la plantilla
    chats = get_user_chats(user_id)

    # Pasamos current_user.username para consistencia (aunque en plantilla también podemos usar current_user)
    return render_template('chat_list.html', username=current_user.username, chats=chats)

def _run(cmd):
    subprocess.run(cmd, check=True)

def transcode_to_streamable_mp4(src_path, out_path):
    # MP4 H.264 + AAC + faststart (inicio rápido) + máx 1280px de ancho
    _run([
        "ffmpeg", "-y", "-i", src_path,
        "-vf", "scale='min(1280,iw)':'-2'",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        out_path
    ])

def extract_thumbnail(src_path, thumb_path):
    _run([
        "ffmpeg", "-y", "-i", src_path,
        "-ss", "00:00:01.000", "-vframes", "1",
        "-vf", "scale=640:-2",
        thumb_path
    ])

def probe_duration(src_path):
    try:
        out = subprocess.check_output([
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            src_path
        ], stderr=subprocess.STDOUT).decode().strip()
        return float(out)
    except Exception:
        return None

def _abs_folder(base_folder):
    # Asegura ruta absoluta basada en app.root_path
    return base_folder if os.path.isabs(base_folder) else os.path.join(app.root_path, base_folder)

def partial_response(abs_path, content_type=None, cache_seconds=60*60*24*7):
    if not os.path.exists(abs_path):
        abort(404)

    file_size = os.path.getsize(abs_path)
    range_header = request.headers.get('Range')
    content_type = content_type or mimetypes.guess_type(abs_path)[0] or 'application/octet-stream'

    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": f"public, max-age={cache_seconds}",
        "Last-Modified": datetime.utcfromtimestamp(os.path.getmtime(abs_path)).strftime('%a, %d %b %Y %H:%M:%S GMT')
    }

    if not range_header:
        return Response(open(abs_path, 'rb'), 200, headers=headers, mimetype=content_type, direct_passthrough=True)

    try:
        units, rng = range_header.split("=")
        if units != "bytes":
            return Response(status=416)
        start_str, end_str = rng.split("-")
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1
    except Exception:
        return Response(status=416)

    if start >= file_size or end >= file_size or start > end:
        return Response(status=416)

    length = end - start + 1
    with open(abs_path, 'rb') as f:
        f.seek(start)
        data = f.read(length)

    headers.update({
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Content-Length": str(length),
    })
    return Response(data, 206, headers=headers, mimetype=content_type, direct_passthrough=True)

@app.route('/files/<path:filename>')
def serve_file(filename):
    # Sirve cualquier fichero bajo tu proyecto (p.ej. 'static/...' o 'uploads/...').
    abs_path = os.path.normpath(os.path.join(app.root_path, filename))
    # Seguridad: evita path traversal
    if not abs_path.startswith(app.root_path):
        abort(403)
    return partial_response(abs_path)

def generate_thumbnail(video_path, thumbnail_path):
    """Genera una miniatura para un video usando FFmpeg"""
    try:
        subprocess.run([
            "ffmpeg", "-i", video_path, "-ss", "00:00:01", "-vframes", "1", thumbnail_path
        ], check=True)
    except subprocess.CalledProcessError:
        print("Error generando miniatura")

#Eventos de SocketIO
@app.route('/upload_file', methods=['POST'])
def upload_file():
    print("[upload_file] inicio")
    file = request.files.get('file')
    folder = request.form.get('folder', app.config.get('CHAT_UPLOAD_FOLDER', 'static/chat_uploads'))
    filename_from_form = request.form.get('filename')

    if not file:
        print("[upload_file] No se recibió 'file' en request.files")
        return jsonify({"success": False, "error": "no_file"}), 400

    print(f"[upload_file] filename recibido: attr.filename={getattr(file, 'filename', None)} form_filename={filename_from_form}")

    # Validaciones
    try:
        # Determinar filename seguro
        original_filename = file.filename or filename_from_form or f"upload_{int(time.time())}"
        if not allowed_file(original_filename):
            print(f"[upload_file] extensión no permitida: {original_filename}")
            return jsonify({"success": False, "error": "bad_extension"}), 400

        abs_folder = _abs_folder(folder)
        os.makedirs(abs_folder, exist_ok=True)

        ext = os.path.splitext(original_filename)[1].lower()
        new_filename = secure_filename(f"file_{int(time.time())}{ext}")
        abs_original_path = os.path.join(abs_folder, new_filename).replace("\\", "/")
        print(f"[upload_file] abs_original_path -> {abs_original_path}")

        # Guardar (comprueba tamaño)
        try:
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            print(f"[upload_file] tamaño archivo: {file_size} bytes")
        except Exception as e:
            print("[upload_file] no se pudo obtener tamaño con seek (continuando):", e)

        max_size = app.config.get('MAX_CONTENT_LENGTH', 50 * 1024 * 1024)
        if file_size and file_size > max_size:
            print(f"[upload_file] archivo demasiado grande: {file_size} > {max_size}")
            return jsonify({"success": False, "error": "too_large", "max": max_size}), 400

        file.save(abs_original_path)
        print("[upload_file] archivo guardado OK")

        # Si es video: intentar optimizar y thumbnail, con logs
        is_video = ext in ['.mp4', '.mov', '.webm']
        abs_final = abs_original_path
        thumb_abs = None

        if is_video:
            try:
                base_noext = os.path.splitext(new_filename)[0]
                optimized_name = f"{base_noext}_stream.mp4"
                abs_optimized_path = os.path.join(abs_folder, optimized_name).replace("\\", "/")
                print(f"[upload_file] transcodificando a {abs_optimized_path}...")
                transcode_to_streamable_mp4(abs_original_path, abs_optimized_path)
                abs_final = abs_optimized_path
                print("[upload_file] transcodificación OK")
            except Exception as e:
                print("[upload_file] transcode failed:", e)
                abs_final = abs_original_path

            try:
                thumbs_dir = os.path.join(abs_folder, "thumbnails")
                os.makedirs(thumbs_dir, exist_ok=True)
                thumb_name = f"{os.path.splitext(new_filename)[0]}.jpg"
                thumb_abs = os.path.join(thumbs_dir, thumb_name).replace("\\", "/")
                print("[upload_file] generando thumbnail en", thumb_abs)
                extract_thumbnail(abs_final, thumb_abs)
                print("[upload_file] thumbnail OK")
            except Exception as e:
                print("[upload_file] thumbnail failed:", e)
                thumb_abs = None

        # Convertir a rutas relativas
        rel_final = _rel_from_root(abs_final)
        rel_original = _rel_from_root(abs_original_path)
        rel_thumb = _rel_from_root(thumb_abs) if thumb_abs else None

        print(f"[upload_file] rel_final={rel_final} rel_original={rel_original} rel_thumb={rel_thumb}")

        # Devolver siempre file_path si es posible
        file_path_for_db = rel_final or rel_original
        stream_url = url_for('serve_file', filename=rel_final, _external=True) if rel_final else None
        thumb_url_public = url_for('serve_file', filename=rel_thumb, _external=True) if rel_thumb else None

        response = {
            "success": True,
            "file_path": file_path_for_db,
            "stream_url": stream_url,
            "thumbnail_url": thumb_url_public,
            "duration": None
        }
        print("[upload_file] respuesta final:", response)
        return jsonify(response), 200

    except Exception as e:
        print("[upload_file] EXCEPCION:", e, file=sys.stderr)
        return jsonify({"success": False, "error": "server_exception", "detail": str(e)}), 500

# Función para manejar archivos pequeños en Base64
def handle_small_file(file, filename=None):
    """Maneja archivos pequeños en formato Base64."""
    if isinstance(file, str):
        try:
            if not filename:
                print("❌ Error: El nombre del archivo no se proporcionó.")
                return None

            ext = os.path.splitext(filename)[1].lower()
            if ext.replace('.', '') not in ALLOWED_EXTENSIONS:
                print(f"❌ Error: Extensión no permitida ({ext}).")
                return None

            # Limpiar Base64
            file = clean_base64(file)

            # Decodificar Base64
            file_data = base64.b64decode(file, validate=True)

            new_filename = f"{int(time.time())}{ext}"
            file_path = os.path.join(CHAT_UPLOAD_FOLDER, new_filename)

            # Normalizar la ruta para evitar barras invertidas en Windows
            file_path = file_path.replace("\\", "/")

            with open(file_path, "wb") as f:
                f.write(file_data)

            print(f"✅ Archivo Base64 guardado en: {file_path}")
            return file_path
        except Exception as e:
            print(f"❌ Error al procesar el archivo Base64: {e}")
            return None
    return None

def clean_base64(file_str):
    """Limpia el string Base64 eliminando espacios y cabecera."""
    file_str = file_str.strip()  # Elimina espacios en blanco y saltos de línea
    if "," in file_str:  # Si tiene una cabecera "data:image/jpeg;base64,..."
        file_str = file_str.split(",")[1]
    return file_str

def chat_room_by_username(a, b):
    users = sorted([str(a).strip(), str(b).strip()])
    return f"chat_{users[0]}_{users[1]}"

# helpers/salas.py (o en el mismo archivo si prefieres)
@socketio.on('connect')
def socket_connect():
    print("---- SOCKET CONNECT ----")
    print("request.cookies:", dict(request.cookies))
    print("current_user:", getattr(current_user, "username", None),
          "is_authenticated:", current_user.is_authenticated)
    if not current_user.is_authenticated:
        print("-> conexión rechazada: usuario no autenticado")
        return False
    print("-> conexión aceptada para", current_user.username)

# send_message (reemplaza handle_send_message): usa current_user en vez de 'sender' del cliente
# Imports necesarios (añádelos si no están ya en tu módulo)
import os
import time
from flask import url_for, current_app
# Asegúrate de tener: socketio, db, User, Message, Conversation, upload_file, handle_small_file, generate_thumbnail, CHAT_UPLOAD_FOLDER, THUMBNAIL_FOLDER

def normalize_and_wait_file_url(file_path, wait_attempts=6, wait_delay=0.4, fallback_stream_url=None):
    """
    Devuelve URL pública absoluta para frontend.
    - Si fallback_stream_url está presente (p.ej. upload_file devolvió stream_url) lo usa.
    - Si file_path es 'static/...' genera url_for('static', ...,_external=True) (esperando existencia en disco).
    - Si no puede normalizar devuelve fallback_stream_url o file_path.
    """
    # Preferir stream_url devuelto por uploader
    if fallback_stream_url:
        return fallback_stream_url

    if not file_path:
        return ""

    # Si ya es URL absoluta
    if file_path.startswith("http://") or file_path.startswith("https://"):
        return file_path

    try:
        # Caso: path relativo dentro de 'static/'
        if file_path.startswith("static/"):
            fs_path = os.path.join(current_app.root_path, file_path.replace("/", os.sep))
            for _ in range(wait_attempts):
                if os.path.exists(fs_path):
                    break
                time.sleep(wait_delay)
            if not os.path.exists(fs_path):
                current_app.logger.warning(f"[normalize_and_wait_file_url] file not found after waiting: {fs_path}")
            static_root = os.path.join(current_app.root_path, 'static')
            try:
                rel = os.path.relpath(fs_path, static_root).replace("\\", "/")
            except Exception:
                rel = file_path[len("static/"):] if file_path.startswith("static/") else file_path
            return url_for('static', filename=rel, _external=True)

        # Intento heurístico: tratar file_path como dentro de static
        fs_path = os.path.join(current_app.root_path, 'static', file_path.replace("/", os.sep))
        for _ in range(wait_attempts):
            if os.path.exists(fs_path):
                break
            time.sleep(wait_delay)
        if os.path.exists(fs_path):
            try:
                rel = os.path.relpath(fs_path, os.path.join(current_app.root_path, 'static')).replace("\\", "/")
            except Exception:
                rel = file_path
            return url_for('static', filename=rel, _external=True)

    except Exception as e:
        current_app.logger.exception("[normalize_and_wait_file_url] error: %s", e)

    # Fallback: devolver lo recibido
    return file_path or (fallback_stream_url or "")

@socketio.on('send_message')
def handle_send_message(data):
    """
    Handler WebSocket para envío de mensajes (soporta archivos).
    - data esperado: { recipient, message, file?, filename? }
    - Si upload_file devuelve dict con 'stream_url' se usará esa URL pública en el payload.
    - Para data:URI pequeños intenta handle_small_file; si falla, incluye base64 en payload como fallback.
    """
    print("Recibiendo mensaje de WebSocket...")
    print("Datos recibidos (raw):", data)

    # Seguridad: tomar usuario del contexto del servidor (no confiar en el cliente)
    sender_user = current_user
    if not sender_user or not sender_user.is_authenticated:
        print("❌ Envío rechazado: usuario no autenticado")
        return {'ok': False, 'error': 'not_authenticated'}

    recipient_username = data.get('recipient') or data.get('to')
    message_text = (data.get('message') or '').strip()
    file = data.get('file')
    filename = data.get('filename')

    if not recipient_username or (not message_text and not file):
        print("❌ Error: datos faltantes o mensaje vacío.")
        return {'ok': False, 'error': 'missing_fields'}

    file_path = None
    thumbnail_path = None
    file_base64_payload = None
    upload_stream_url = None  # lo que upload_file pueda devolver (p.ej. stream_url)

    # Procesar archivo si viene
    if file:
        try:
            # file como string: puede ser 'static/...' o 'data:...' o URL absoluta
            if isinstance(file, str):
                if file.startswith("static/"):
                    file_path = file
                elif file.startswith("data:") and "," in file:
                    if not filename:
                        return {'ok': False, 'error': 'missing_filename'}
                    try:
                        saved = handle_small_file(file, filename)  # tu impl
                        if isinstance(saved, dict):
                            file_path = saved.get('file_path') or saved.get('rel_path') or None
                            upload_stream_url = saved.get('stream_url') or saved.get('public_url') or None
                        else:
                            file_path = saved
                    except Exception as e:
                        print("⚠️ handle_small_file falló, pasaré base64 en payload:", e)
                        file_base64_payload = file
                elif file.startswith("http://") or file.startswith("https://"):
                    upload_stream_url = file
                    file_path = None
                else:
                    return {'ok': False, 'error': 'unknown_file_format'}
            # file como objeto (FileStorage u otro)
            elif hasattr(file, 'filename'):
                uploaded = upload_file(file, CHAT_UPLOAD_FOLDER)
                if isinstance(uploaded, dict):
                    file_path = uploaded.get('file_path') or uploaded.get('rel_path') or None
                    upload_stream_url = uploaded.get('stream_url') or uploaded.get('public_url') or None
                else:
                    file_path = uploaded
            else:
                return {'ok': False, 'error': 'unsupported_file_object'}
        except Exception as e:
            print(f"❌ Error al procesar archivo: {e}")
            return {'ok': False, 'error': 'file_process_error'}

        # Generar miniatura si es video
        if file_path and file_path.lower().endswith(('.mp4', '.webm', '.mov', '.avi', '.mpg')):
            try:
                base = os.path.basename(file_path)
                thumb_name = f"thumb_{base}.png"
                thumb_full = os.path.join(THUMBNAIL_FOLDER, thumb_name)
                generate_thumbnail(file_path, thumb_full)
                thumbnail_path = thumb_full.replace("\\", "/")
            except Exception as e:
                print(f"⚠️ No se pudo generar miniatura: {e}")
                thumbnail_path = None

    # Buscar destinatario
    recipient_user = User.query.filter_by(username=recipient_username).first()
    if not recipient_user:
        print(f"❌ Error: recipient {recipient_username} no encontrado.")
        return {'ok': False, 'error': 'recipient_not_found'}

    # Buscar o crear conversación
    conversation = Conversation.query.filter(
        ((Conversation.user_id == sender_user.id) & (Conversation.recipient_id == recipient_user.id)) |
        ((Conversation.user_id == recipient_user.id) & (Conversation.recipient_id == sender_user.id))
    ).first()

    if not conversation:
        conversation = Conversation(user_id=sender_user.id, recipient_id=recipient_user.id)
        db.session.add(conversation)
        db.session.commit()
        print(f"🆕 Conversación creada entre {sender_user.username} y {recipient_user.username}")

    # Guardar mensaje en BD (almacenar path relativo si procede)
    try:
        new_message = Message(
            sender_id=sender_user.id,
            conversation_id=conversation.id,
            content=message_text if message_text else None,
            file_url=file_path,
            thumbnail_url=thumbnail_path
        )
        db.session.add(new_message)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error guardando mensaje en DB: {e}")
        return {'ok': False, 'error': 'db_error'}

    print(f"✅ Mensaje guardado con ID: {new_message.id}")

    # Normalizar/obtener la URL pública que enviaremos al frontend.
    # Preferir upload_stream_url si lo tenemos, sino intentar normalizar desde file_path.
    public_file_url = ""
    try:
        public_file_url = normalize_and_wait_file_url(file_path, wait_attempts=6, wait_delay=0.4, fallback_stream_url=upload_stream_url)
    except Exception as e:
        print("⚠️ Error normalizando file URL:", e)
        public_file_url = upload_stream_url or (file_path or "")

    # Construir payload que enviaremos por socket
    payload = {
        'username': sender_user.username,
        'message': message_text,
        'message_id': new_message.id,
        # Enviamos la URL pública (stream_url preferida)
        'file_url': public_file_url or "",
        'thumbnail_url': (normalize_and_wait_file_url(thumbnail_path) if thumbnail_path else ""),
        'timestamp': new_message.timestamp.isoformat()
    }

    # Incluir base64 en payload como fallback (solo para archivos pequeños)
    if file_base64_payload:
        payload['file_base64'] = file_base64_payload
        payload['file_name'] = filename

    # Emitir al room
    room = chat_room_by_username(sender_user.username, recipient_user.username)
    try:
        print(f"[emit] to={room} payload.file_url={payload['file_url']} stream_url={payload.get('stream_url')}")
        socketio.emit('receive_message', payload, to=room, include_self=True)
        print(f"✅ Mensaje emitido a la sala {room} con file_url={payload.get('file_url')}")
    except Exception as e:
        print("⚠️ Error emitiendo por socketio:", e)

    # Respuesta al emisor (si el cliente espera JSON)
    return {'ok': True, 'message_id': new_message.id, 'file_url': public_file_url, 'thumbnail_url': payload.get('thumbnail_url')}

# Edit message: usar current_user.id para comprobar permisos
@socketio.on('edit_message')
def handle_edit_message(data):
    message_id = data.get('message_id')
    new_content = data.get('new_content')
    if not message_id or new_content is None:
        print("Error: Faltan datos para editar el mensaje.")
        return {'ok': False, 'error': 'missing_fields'}

    msg = Message.query.get(message_id)
    if not msg:
        print("Error: mensaje no encontrado")
        return {'ok': False, 'error': 'not_found'}

    if msg.sender_id != current_user.id:
        print("Error: el usuario no tiene permisos para editar este mensaje")
        return {'ok': False, 'error': 'forbidden'}

    msg.content = new_content
    db.session.commit()

    conv = Conversation.query.get(msg.conversation_id)
    u1 = User.query.get(conv.user_id)
    u2 = User.query.get(conv.recipient_id)
    room = chat_room_by_username(u1.username, u2.username)

    socketio.emit('message_edited', {
        'message_id': message_id,
        'new_message': new_content,
        'username': current_user.username
    }, to=room)

    print(f"Mensaje {message_id} editado correctamente.")
    return {'ok': True}


# Delete message: usar current_user.id para comprobar permisos
@socketio.on('delete_message')
def handle_delete_message(data):
    message_id = data.get('message_id')
    if not message_id:
        print("Error: Faltan datos para eliminar el mensaje.")
        return {'ok': False, 'error': 'missing_fields'}

    msg = Message.query.get(message_id)
    if not msg:
        print("Error: mensaje no encontrado")
        return {'ok': False, 'error': 'not_found'}

    if msg.sender_id != current_user.id:
        print("Error: el usuario no tiene permisos para eliminar este mensaje")
        return {'ok': False, 'error': 'forbidden'}

    conv = Conversation.query.get(msg.conversation_id)
    u1 = User.query.get(conv.user_id)
    u2 = User.query.get(conv.recipient_id)
    room = chat_room_by_username(u1.username, u2.username)

    db.session.delete(msg)
    db.session.commit()

    socketio.emit('message_deleted', {'message_id': message_id}, to=room)
    print(f"Mensaje {message_id} eliminado correctamente.")
    return {'ok': True}@socketio.on('share_video')

def handle_share_video(data):
    sender_id = session.get('user_id')
    recipient_username = data.get('recipient_username')
    video_url = data.get('video_url')

    if not sender_id or not recipient_username or not video_url:
        print("❌ Error: Datos incompletos para compartir video.")
        return

    recipient = User.query.filter_by(username=recipient_username).first()
    if not recipient:
        print("❌ Usuario receptor no encontrado.")
        return

    # Buscar o crear conversación
    conversation = Conversation.query.filter(
        ((Conversation.user_id == sender_id) & (Conversation.recipient_id == recipient.id)) |
        ((Conversation.user_id == recipient.id) & (Conversation.recipient_id == sender_id))
    ).first()

    if not conversation:
        conversation = Conversation(user_id=sender_id, recipient_id=recipient.id)
        db.session.add(conversation)
        db.session.commit()

    # Crear el mensaje con el video
    new_message = Message(
        conversation_id=conversation.id,
        sender_id=sender_id,
        content=f"[VIDEO]{video_url}",  # marcamos como video compartido
        timestamp=datetime.utcnow(),
        is_read=False
    )
    db.session.add(new_message)
    db.session.commit()

    # Emitir el mensaje al chat
    room = f"chat_{'_'.join(sorted([str(sender_id), str(recipient.id)]))}"
    socketio.emit('new_message', {
        'sender_id': sender_id,
        'recipient_id': recipient.id,
        'content': new_message.content,
        'timestamp': new_message.timestamp.isoformat()
    }, to=room)

    print(f"✅ Video compartido con {recipient.username} en la sala {room}")

@app.route('/chat/<int:recipient_id>/send', methods=['POST'])
@app.route('/chat/<int:recipient_id>', methods=['POST'], endpoint='send_message')
@login_required
def send_message_http(recipient_id):
    recipient = User.query.get_or_404(recipient_id)

    conversation = Conversation.query.filter(
        ((Conversation.user_id == current_user.id) & (Conversation.recipient_id == recipient.id)) |
        ((Conversation.user_id == recipient.id) & (Conversation.recipient_id == current_user.id))
    ).first()

    if not conversation:
        conversation = Conversation(user_id=current_user.id, recipient_id=recipient.id)
        db.session.add(conversation)
        db.session.commit()

    message_content = ''
    files = None
    if request.is_json:
        data = request.get_json(silent=True) or {}
        message_content = (data.get('message') or '').strip()
    else:
        message_content = (request.form.get('message') or '').strip()
        files = request.files.getlist('file_input') if hasattr(request, 'files') else None

    if not message_content and not (files and len(files) > 0):
        if request.is_json:
            return jsonify({'ok': False, 'error': 'missing_message'}), 400
        flash('No se puede enviar un mensaje vacío.', 'error')
        return redirect(url_for('chat_with_user', recipient_identifier=recipient.username))

    file_path = None
    thumbnail_path = None
    upload_stream_url = None

    try:
        if files and len(files) > 0:
            f = files[0]
            uploaded = upload_file(f, CHAT_UPLOAD_FOLDER)
            if isinstance(uploaded, dict):
                file_path = uploaded.get('file_path') or uploaded.get('rel_path') or None
                upload_stream_url = uploaded.get('stream_url') or uploaded.get('public_url') or None
            else:
                file_path = uploaded
            # generar thumb si aplica
            if file_path and file_path.lower().endswith(('.mp4', '.webm', '.mov', '.avi', '.mpg')):
                try:
                    base = os.path.basename(file_path)
                    thumb_name = f"thumb_{base}.png"
                    thumb_full = os.path.join(THUMBNAIL_FOLDER, thumb_name)
                    generate_thumbnail(file_path, thumb_full)
                    thumbnail_path = thumb_full.replace("\\", "/")
                except Exception as e:
                    current_app.logger.warning("[send_message_http] no se pudo generar thumb: %s", e)
                    thumbnail_path = None
    except Exception as e:
        current_app.logger.exception("[send_message_http] error procesando archivo: %s", e)
        if request.is_json:
            return jsonify({'ok': False, 'error': 'file_process_error', 'detail': str(e)}), 500
        flash('Error procesando archivo.', 'error')
        return redirect(url_for('chat_with_user', recipient_identifier=recipient.username))

    # guardar mensaje en BD
    try:
        new_message = Message(
            conversation_id=conversation.id,
            sender_id=current_user.id,
            content=message_content if message_content else None,
            file_url=file_path,
            thumbnail_url=thumbnail_path,
            is_read=False
        )
        db.session.add(new_message)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("[send_message_http] error guardando mensaje: %s", e)
        if request.is_json:
            return jsonify({'ok': False, 'error': 'db_error', 'detail': str(e)}), 500
        flash('Error al guardar el mensaje.', 'error')
        return redirect(url_for('chat_with_user', recipient_identifier=recipient.username))

    # Normalizar URL pública: preferir upload_stream_url si lo hay
    public_file_url = ""
    try:
        public_file_url = normalize_and_wait_file_url(file_path, wait_attempts=6, wait_delay=0.4, fallback_stream_url=upload_stream_url)
    except Exception:
        current_app.logger.exception("[send_message_http] error normalizando file url")

    payload = {
        'username': current_user.username,
        'message': new_message.content or '',
        'message_id': new_message.id,
        'file_url': public_file_url or '',
        'thumbnail_url': (normalize_and_wait_file_url(thumbnail_path) if thumbnail_path else ""),
        'timestamp': new_message.timestamp.isoformat()
    }

    try:
        socketio.emit('receive_message', payload, to=chat_room_by_username(current_user.username, recipient.username), include_self=True)
        current_app.logger.debug("[send_message_http] emit payload: %s", payload)
    except Exception:
        current_app.logger.debug("Socket emission failed or socketio not configured here.", exc_info=True)

    if request.is_json:
        return jsonify({'ok': True, 'message_id': new_message.id, 'message': new_message.content, 'file_url': public_file_url}), 200

    return redirect(url_for('chat_with_user', recipient_identifier=recipient.username))

@app.route('/profile/<username>', methods=['GET', 'POST'])
def profile(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        flash('Usuario no encontrado', 'error')
        return redirect(url_for('home'))

    form = OpinionForm()
    average_rating = db.session.query(db.func.avg(Opinion.rating)).filter_by(profile_user_id=user.id).scalar()

    # Procesar formulario de opinión
    if request.method == 'POST' and form.validate_on_submit():
        opinion_text = form.opinion_text.data
        rating = form.rating.data

        if opinion_text and rating is not None:
            try:
                if 0 <= rating <= 10:
                    opinion = Opinion(
                        text=opinion_text,
                        rating=rating,
                        user_id=current_user.id,
                        profile_user_id=user.id
                    )
                    db.session.add(opinion)
                    db.session.commit()

                    return jsonify({
                        'success': True,
                        'message': 'Opinión añadida exitosamente',
                        'username': current_user.name,
                        'user_profile_url': url_for('profile', username=current_user.username),
                        'user_profile_pic': url_for('static', filename=current_user.profile_pic if current_user.profile_pic else 'profile_pics/default.jpg'),
                        'opinion_text': opinion_text,
                        'rating': rating
                    })
                else:
                    return jsonify({'success': False, 'message': 'La puntuación debe estar entre 0 y 10.'})
            except ValueError:
                return jsonify({'success': False, 'message': 'La puntuación ingresada no es válida.'})
        else:
            return jsonify({'success': False, 'message': 'Debes escribir una opinión y asignar una puntuación.'})

    # Parte GET: cargar perfil y opiniones
    opinions = Opinion.query.filter_by(profile_user_id=user.id).all()

    videos = Video.query.filter_by(user_id=user.id).all()

    return render_template('profile.html', user=user, opinions=opinions, form=form, average_rating=average_rating, videos=videos)

@app.route('/video/<int:video_id>')
def view_video(video_id):
    video = Video.query.get_or_404(video_id)
    user = User.query.get(video.user_id)

    # Solo los videos del mismo usuario
    lista_videos = Video.query.filter_by(user_id=video.user_id).order_by(Video.id.desc()).all()


    return render_template(
        "view_video.html",
        videos=lista_videos,
        video=video,
        user=user,       
    )

@app.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        company = request.form.get("company", "").strip() or None
        # Nuevo: múltiples profesiones (coma-separado)
        raw_multi = request.form.get("professions", "").strip()
        # Compat: por si aún llega el campo antiguo
        single_legacy = request.form.get("profession", "").strip()

        description = request.form.get("description", "").strip() or None
        location = request.form.get("location", "").strip() or None
        profile_pic = request.files.get("profile_pic")
        email = request.form.get("email", "").strip() or None

        # Campos básicos
        current_user.name = name
        current_user.company = company
        current_user.description = description
        current_user.location = location
        current_user.email = email

        # Profesiones (múltiples)
        if raw_multi:
            names = [x.strip() for x in raw_multi.split(",") if x.strip()]
        elif single_legacy:
            names = [single_legacy]
        else:
            names = []

        current_user.set_professions_from_list(names)
        # (opcional) sincroniza temporalmente la vieja columna
        current_user.profession = names[0] if names else None

        # Foto de perfil (guarda con nombre único para evitar colisiones)
        if profile_pic and profile_pic.filename:
            filename = secure_filename(profile_pic.filename)
            name_part, ext = os.path.splitext(filename)
            unique_name = f"{name_part}_{int(time.time())}{ext}"
            path = os.path.join(app.config["PROFILE_PICS_FOLDER"], unique_name)
            os.makedirs(app.config["PROFILE_PICS_FOLDER"], exist_ok=True)
            profile_pic.save(path)
            current_user.profile_pic = f"profile_pics/{unique_name}"

        db.session.commit()
        flash("Perfil actualizado con éxito.", "success")
        return redirect(url_for("profile", username=current_user.username))

    # GET: precarga profesiones y sugerencias
    professions_prefill = ", ".join(current_user.profession_names)
    profession_options = [p.name for p in Profession.query.order_by(Profession.name.asc()).limit(20)]
    return render_template(
        "edit_profile.html",
        user=current_user,
        professions_prefill=professions_prefill,
        profession_options=profession_options
    )

@app.route('/upload_cv', methods=['POST'])
@login_required
def upload_cv():
    file = request.files.get('cv')
    if not file or file.filename.strip() == '':
        flash('No seleccionaste ningún archivo.', 'error')
        return redirect(request.referrer or url_for('profile', username=current_user.username))

    if not allowed_cv(file.filename):
        flash('Formato no permitido. Usa PDF, DOC o DOCX.', 'error')
        return redirect(request.referrer or url_for('profile', username=current_user.username))

    # Nombre único seguro: <username>_<timestamp>.<ext>
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = secure_filename(f"{current_user.username}_{int(time.time())}.{ext}")

    save_path = os.path.join(app.config['CV_UPLOAD_FOLDER'], filename)
    file.save(save_path)

    # Si ya tenía un CV, opcional: borra el anterior
    try:
        if getattr(current_user, 'cv_file', None):
            old_path = os.path.join(app.config['CV_UPLOAD_FOLDER'], current_user.cv_file)
            if os.path.exists(old_path):
                os.remove(old_path)
    except Exception:
        pass  # Silencioso para no romper el flujo

    # Guarda referencia en BD
    current_user.cv_file = filename
    db.session.commit()

    flash('CV subido correctamente.', 'success')
    return redirect(request.referrer or url_for('profile', username=current_user.username))

@app.route('/cv/<username>')
@login_required
def view_cv(username):
    user = User.query.filter_by(username=username).first_or_404()
    if not user.cv_file:
        flash('Este usuario no tiene CV subido.', 'error')
        return redirect(url_for('profile', username=username))

    # Devuelve el archivo directamente desde /static/cv
    return send_from_directory(
        app.config['CV_UPLOAD_FOLDER'],
        user.cv_file,
        as_attachment=False  # mostrar en navegador si es PDF
    )
@app.after_request
def add_security_headers(response):
    # No aplicar estas cabeceras si la ruta es estática o importante para recursos externos
    if request.path.startswith('/static') or request.path.startswith('/uploads') or request.path.startswith('/create-checkout-session') or request.path.startswith('/premium') or request.path.startswith('/register'):
        return response
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
    response.headers['Cross-Origin-Embedder-Policy'] = 'require-corp'
    return response


# 🔍 Función para verificar si el archivo tiene una extensión permitidadef allowed_file(filename):
    """Verifica si la extensión del archivo es válida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/uploads/videos/<filename>')
def uploaded_file(filename):
    return send_from_directory('static/uploads/videos', filename)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    # DEBUG - confirma que Flask detecta la sesión
    print("UPLOAD VIEW - current_user:", current_user, "is_authenticated:", current_user.is_authenticated, "id:", getattr(current_user, 'id', None))

    if request.method == 'GET':
        return render_template('upload.html')

    # POST
    try:
        # Si usas Flask-WTF: validate_csrf recibirá el token
        validate_csrf(request.form.get('csrf_token'))
    except Exception as e:
        print("❌ CSRF inválido:", e)
        flash('CSRF inválido', 'error')
        return redirect(url_for('upload'))

    video_file = request.files.get('video_file')
    title = (request.form.get('title') or '').strip()
    description = (request.form.get('description') or '').strip()
    hashtags = (request.form.get('hashtags') or '').strip()

    if not video_file:
        print("❌ No se recibió ningún archivo")
        flash('Selecciona un video válido.', 'error')
        return redirect(url_for('upload'))

    if not allowed_file(video_file.filename):
        print("❌ Tipo de archivo no permitido:", video_file.filename)
        flash('Tipo de archivo no permitido.', 'error')
        return redirect(url_for('upload'))

    try:
        # Carpeta configurable desde config (recomendado)
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/uploads/videos')
        os.makedirs(upload_folder, exist_ok=True)

        # Nombre seguro y único
        filename = secure_filename(video_file.filename)
        ext = filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{ext}"
        file_path = os.path.join(upload_folder, unique_filename)

        # Guardar archivo
        video_file.save(file_path)
        print(f"✅ Video guardado localmente en {file_path}")

        # Guardar en BD: usa current_user.id (consistente)
        new_video = Video(
            video_url=unique_filename,  # guarda el nombre/Path relativo
            title=title,
            description=description,
            hashtags=hashtags,
            user_id=current_user.id
        )
        db.session.add(new_video)
        db.session.commit()
        print("✅ Video registrado en la base de datos (id:", new_video.id, ")")

    except Exception as e:
        print("❌ Error guardando el archivo o en BD:", e)
        # opcional: borrar archivo si se creó pero hubo error DB
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
        flash('Error al subir el video.', 'error')
        return redirect(url_for('upload'))

    flash('¡Video subido con éxito!', 'success')
    return redirect(url_for('profile', username=current_user.username))
@app.route('/api/videos', methods=['GET'])
def get_videos():
    videos = Video.query.all()
    video_data = [{"video_url": video.video_url, "title": video.title} for video in videos]
    print("Videos enviados a la API:", video_data)  # Log para depuración
    return {"videos": video_data}

@app.route('/opinion/<int:opinion_id>/respond', methods=['POST'])
@login_required
def reply_opinion(opinion_id):  
    data = request.get_json()
    text = data.get('text')

    if not text:
        return jsonify({'success': False, 'message': 'El texto de la respuesta es obligatorio'}), 400

    opinion = Opinion.query.get(opinion_id)
    if not opinion:
        return jsonify({'success': False, 'message': 'La opinión no existe'}), 404

    response = Response(
        text=text,
        opinion_id=opinion_id,
        user_id=current_user.id
    )

    db.session.add(response)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Respuesta agregada correctamente',
        'response': {
            'id': response.id,
            'text': response.text,
            'username': current_user.name,
            'created_at': response.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
    }), 201

@app.route('/opinion/<int:opinion_id>/responses', methods=['GET'])
def get_responses(opinion_id):
    # Obtener la opinión con el id proporcionado
    opinion = Opinion.query.get(opinion_id)
    
    if not opinion:
        return jsonify({'success': False, 'message': 'La opinión no existe'}), 404

    # Obtener las respuestas asociadas a esta opinión
    responses = Response.query.filter_by(opinion_id=opinion_id).all()
    
    # Preparar las respuestas para enviarlas en formato JSON
    responses_data = [
        {
            'id': response.id,
            'text': response.text,
            'username': response.user.name,  # Aquí puedes acceder al nombre del usuario que respondió
            'created_at': response.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        for response in responses
    ]

    return jsonify({'success': True, 'responses': responses_data})

@app.route('/opinion/<int:opinion_id>/delete', methods=['POST'])
@login_required
def delete_opinion(opinion_id):
    opinion = Opinion.query.get(opinion_id)
    if opinion and opinion.user_id == current_user.id:
        try:
            db.session.delete(opinion)
            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Opinión eliminada correctamente'
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f'Error al eliminar la opinión: {str(e)}'
            })
    return jsonify({
        'success': False,
        'message': 'No tienes permisos para eliminar esta opinión'
    })

@app.route('/response/<int:response_id>/delete', methods=['POST'])
@login_required
def delete_response(response_id):
    response = Response.query.get(response_id)

    if not response:
        return jsonify({"success": False, "message": "Respuesta no encontrada"}), 404

    # Solo el autor de la respuesta o un administrador pueden eliminarla
    if response.user_id != current_user.id:
        return jsonify({"success": False, "message": "No tienes permiso para eliminar esta respuesta"}), 403

    try:
        db.session.delete(response)
        db.session.commit()
        return jsonify({"success": True, "message": "Respuesta eliminada correctamente"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Error al eliminar la respuesta"}), 500
    
@app.route('/delete_video/<int:video_id>', methods=['POST'])
def delete_video(video_id):
    if 'user_id' not in session: 
        flash('Debes iniciar sesión para realizar esta acción', 'error')
        return redirect(url_for('login'))
    
    video = Video.query.get(video_id)
    if not video: 
        flash('El video no existe', 'error')
        return redirect(url_for('home'))
    
    if video.user_id != session['user_id']: 
        flash('No tienes permiso para eliminar este video', 'error')
        return redirect(url_for('home'))
    
    #Eliminar el archivo del servidor
    file_path = os.path.join('static', 'uploads', 'videos', video.video_url)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    #Eliminar el archivo de la base de datos
    db.session.delete(video)
    db.session.commit()

    flash('Video eliminado exitosamente', 'success')
    
    user = User.query.get(session['user_id'])
    print('User obtenido para redirección', user)

    if user:
        return redirect(url_for('profile', username=user.username))
    else:
        return redirect(url_for('home'))

@app.route('/premium')
@login_required
def premium():
    return render_template(
        'premium.html',
        STRIPE_PUBLIC_KEY=app.config['STRIPE_PUBLIC_KEY']  # 👈 esto es necesario
    )

@app.route('/premium/success')
@login_required
def activate_premium():
    current_user.is_premium = True
    db.session.commit()
    flash('¡Felicidades! Ahora eres usuario premium 🎉', 'success')
    return redirect(url_for('profile', username=current_user.username))

@app.route('/logout')
def logout():
    session.pop("user_id", None)  # Elimina al usuario de la sesión
    flash("Has cerrado sesión exitosamente", "success")
    return redirect(url_for("login"))

@app.route('/delete_account')
def eliminar_cuenta():
    return render_template('eliminar-cuenta.html')

@app.route("/jobs", endpoint="jobs")
def jobs_view():
    tab = request.args.get("tab", "proyectos")

    q = (request.args.get("q") or "").strip()
    location = (request.args.get("location") or "").strip()
    modality = (request.args.get("modality") or "").strip()  # '', 'remoto', 'presencial', 'híbrido'

    Model = Project if tab == "proyectos" else Job
    query = Model.query

    if q:
        like = f"%{q}%"
        query = query.filter(or_(Model.title.ilike(like), Model.description.ilike(like)))

    if location:
        query = query.filter(Model.location.ilike(f"%{location}%"))

    if modality:
        query = query.filter(Model.modality == modality)

    results = query.order_by(Model.created_at.desc()).limit(50).all()

    # importante: envia active_tab para que el template marque la pestaña
    return render_template("jobs.html", results=results, active_tab=tab)


@app.route('/jobs/new-project', methods=['GET', 'POST'])
@login_required
def new_project():
    form = ProjectForm()
    if form.validate_on_submit():
        try:
            p = Project(
                title=form.title.data.strip(),
                short_description=form.short_description.data.strip(),
                description=form.description.data.strip(),
                location=form.location.data.strip() if form.location.data else None,
                modality=form.modality.data or None,
                user_id=current_user.id
            )
            # set opcional del precio
            pmin, pmax = form.price_min.data, form.price_max.data
            if pmin is not None or pmax is not None:
                if pmin is not None and pmax is not None and pmax < pmin:
                    flash('El precio máximo no puede ser menor que el mínimo.', 'error')
                    return render_template('projects_form.html', form=form)  # <-- aquí
                p.price_min = pmin
                p.price_max = pmax
                p.price_currency = form.price_currency.data or None

            db.session.add(p)
            db.session.commit()
            flash('Proyecto publicado 🎉', 'success')
            return redirect(url_for('jobs', tab='proyectos'))
        except Exception:
            db.session.rollback()
            flash('No se pudo publicar el proyecto. Inténtalo de nuevo.', 'error')
    return render_template('projects_form.html', form=form)  # <-- y aquí


@app.route('/jobs/new-job', methods=['GET', 'POST'])
@login_required
def new_job():
    form = JobForm()
    if form.validate_on_submit():
        # ---- Validación de rango opcional ----
        smin, smax = form.salary_min.data, form.salary_max.data
        if smin is not None and smax is not None and smax < smin:
            flash('El salario máximo no puede ser menor que el mínimo.', 'error')
            return render_template('jobs_form.html', form=form, kind='empleo')

        try:
            j = Job(
                title=form.title.data.strip(),
                short_description=form.short_description.data.strip(),
                description=form.description.data.strip(),
                location=form.location.data.strip() if form.location.data else None,
                modality=form.modality.data or None,
                user_id=current_user.id
            )

            # ---- Seteo condicional (opcional) ----
            if smin is not None or smax is not None:
                j.salary_min = smin
                j.salary_max = smax
                j.salary_currency = form.salary_currency.data or None
                j.salary_period = form.salary_period.data or None  # 'hour'/'day'/'month'/'year'

            db.session.add(j)
            db.session.commit()
            flash('Oferta de empleo publicada 🎉', 'success')
            return redirect(url_for('jobs', tab='empleos'))
        except Exception as e:
            db.session.rollback()
            # current_app.logger.exception("Error publicando empleo")
            flash('No se pudo publicar la oferta. Inténtalo de nuevo.', 'error')
    return render_template('jobs_form.html', form=form, kind='empleo')

@app.route("/projects/<int:project_id>", endpoint="project_detail")
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    apps = []
    # Solo cargamos solicitudes si el usuario es el autor
    if current_user.is_authenticated and project.user_id and current_user.id == project.user_id:
        apps = (ProjectApplication.query
                .filter_by(project_id=project.id)
                .order_by(ProjectApplication.created_at.desc())
                .all())
    return render_template("project_detail.html", project=project, apps=apps)

@app.route("/jobs/<int:job_id>", endpoint="job_detail")
def job_detail(job_id):
    job = Job.query.get_or_404(job_id)
    apps = []
    # Solo cargamos solicitudes si el usuario es el autor
    if current_user.is_authenticated and job.user_id and current_user.id == job.user_id:
        apps = (JobApplication.query
                .filter_by(job_id=job.id)
                .order_by(JobApplication.created_at.desc())
                .all())
    return render_template("job_detail.html", job=job, apps=apps)

@app.route("/jobs/<int:job_id>/apply", methods=["POST", "GET"], endpoint="apply_job")
@login_required
def apply_job(job_id):
    job = Job.query.get_or_404(job_id)
    if job.user_id == current_user.id:
        flash("No puedes solicitar tu propio empleo.", "warning")
        return redirect(url_for("job_detail", job_id=job.id))

    app_row = JobApplication.query.filter_by(job_id=job.id, applicant_id=current_user.id).first()
    try:
        if app_row and app_row.status == "active":
            flash("Ya has solicitado este empleo.", "info")
        else:
            if not app_row:
                app_row = JobApplication(job_id=job.id, applicant_id=current_user.id, status="active")
                db.session.add(app_row)
            else:
                app_row.status = "active"
            db.session.commit()
            flash("Solicitud enviada.", "success")
    except SQLAlchemyError:
        db.session.rollback()
        flash("No se pudo enviar la solicitud. Inténtalo de nuevo.", "error")

    return redirect(url_for("job_detail", job_id=job.id))

@app.route("/jobs/<int:job_id>/cancel", methods=["POST", "GET"], endpoint="cancel_job_application")
@login_required
def cancel_job_application(job_id):
    job = Job.query.get_or_404(job_id)
    app_row = JobApplication.query.filter_by(job_id=job.id, applicant_id=current_user.id, status="active").first()
    try:
        if app_row:
            app_row.status = "cancelled"
            db.session.commit()
            flash("Solicitud cancelada.", "info")
        else:
            flash("No tienes una solicitud activa para este empleo.", "warning")
    except SQLAlchemyError:
        db.session.rollback()
        flash("No se pudo cancelar la solicitud. Inténtalo de nuevo.", "error")

    return redirect(url_for("job_detail", job_id=job.id))

# --------- PROYECTOS ---------
@app.route("/projects/<int:project_id>/apply", methods=["POST", "GET"], endpoint="apply_project")
@login_required
def apply_project(project_id):
    project = Project.query.get_or_404(project_id)
    if project.user_id == current_user.id:
        flash("No puedes solicitar tu propio proyecto.", "warning")
        return redirect(url_for("project_detail", project_id=project.id))

    app_row = ProjectApplication.query.filter_by(project_id=project.id, applicant_id=current_user.id).first()
    try:
        if app_row and app_row.status == "active":
            flash("Ya has solicitado este proyecto.", "info")
        else:
            if not app_row:
                app_row = ProjectApplication(project_id=project.id, applicant_id=current_user.id, status="active")
                db.session.add(app_row)
            else:
                app_row.status = "active"
            db.session.commit()

            # (Opcional) notificación al dueño
            # try:
            #     create_system_message(sender_id=current_user.id, recipient_id=project.user_id,
            #                           text=f"{current_user.username} ha solicitado tu proyecto: {project.title}")
            # except Exception:
            #     pass

            flash("Solicitud enviada.", "success")
    except SQLAlchemyError:
        db.session.rollback()
        flash("No se pudo enviar la solicitud. Inténtalo de nuevo.", "error")

    return redirect(url_for("project_detail", project_id=project.id))

@app.route("/projects/<int:project_id>/cancel", methods=["POST", "GET"], endpoint="cancel_project_application")
@login_required
def cancel_project_application(project_id):
    project = Project.query.get_or_404(project_id)
    app_row = ProjectApplication.query.filter_by(project_id=project.id, applicant_id=current_user.id, status="active").first()
    try:
        if app_row:
            app_row.status = "cancelled"
            db.session.commit()
            flash("Solicitud cancelada.", "info")
        else:
            flash("No tienes una solicitud activa para este proyecto.", "warning")
    except SQLAlchemyError:
        db.session.rollback()
        flash("No se pudo cancelar la solicitud. Inténtalo de nuevo.", "error")

    return redirect(url_for("project_detail", project_id=project.id))







