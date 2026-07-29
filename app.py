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
from flask_login import login_required, current_user, login_user, LoginManager, logout_user
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
from algorithms.feed_algorithm import get_feed_videos
from email.mime.text import MIMEText
import smtplib
from reportlab.platypus import (
    SimpleDocTemplate,
    Spacer,
    Paragraph,
    Table,
    TableStyle,
    Image
)


from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import (
    getSampleStyleSheet
)

from reportlab.lib import enums

# Helper seguro para hacer strip sin fallar si value es None
def _safe_strip(value):
    """Devuelve value.strip() si value no es None, sino cadena vacía."""
    return (value or "").strip()

ENV_PATH = Path(__file__).resolve().parent / ".env"
app = Flask(__name__)

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
PRODUCT_IMAGES_FOLDER = 'static/product_images'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CHAT_UPLOAD_FOLDER'] = CHAT_UPLOAD_FOLDER
app.config['PROFILE_PICS_FOLDER'] = PROFILE_PICS_FOLDER  
app.config['PRODUCT_IMAGES_FOLDER'] = PRODUCT_IMAGES_FOLDER

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'webm', 'mov', 'pdf', 'docx', 'pptx', 'avi', 'mpg'}

app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB

for folder in [UPLOAD_FOLDER, CHAT_UPLOAD_FOLDER, PROFILE_PICS_FOLDER, PRODUCT_IMAGES_FOLDER]:  # <--- Incluido aquí
    if not os.path.exists(folder):
        os.makedirs(folder)

db.init_app(app)
USE_EVENTLET = os.getenv("USE_EVENTLET", "0") == "1"
async_mode = "eventlet" if USE_EVENTLET else "threading"
from models import (
    User,
    UserToken,
    user_professions,
    Profession,
    Opinion,
    Comment,
    Video,
    Conversation,
    ChatMessage,
    Project,
    Offer,
    Response as OpinionResponse,
    Job,
    RegisterForm,
    OpinionForm,
    ChangePasswordForm,
    ProjectApplication,
    ProjectForm,
    JobApplication,
    JobForm,
    Group,
    GroupMember,
    CreateGroupForm,
    GroupMessage,
    EditGroupForm,
    Product,
    ProductImage,
    CreateProductForm,
    CURRENCY_CHOICES,
    Block,
    BlockForm,
    UnblockForm,
    Report,
    ReportForm,
    UserCV,
    EmptyForm,
    CVEducation,
    CVExperience,
    CVSkill,
    CVLanguage,
    CVEducation,
    likes_table,
    OfferUsage,
    followers,
)

csrf = CSRFProtect(app)
csrf.init_app(app)

from auth.google import google_bp
app.register_blueprint(google_bp)

GOOGLE_CLIENT_ID = (os.getenv("GOOGLE_CLIENT_ID") or "").strip()
GOOGLE_CLIENT_SECRET = (os.getenv("GOOGLE_CLIENT_SECRET") or "").strip()
GOOGLE_ANDROID_CLIENT_ID = (os.getenv("GOOGLE_ANDROID_CLIENT_ID") or "").strip()  # opcional
GOOGLE_IOS_CLIENT_ID     = (os.getenv("GOOGLE_IOS_CLIENT_ID") or "").strip()      # opcional

from auth.apple import apple_bp
app.register_blueprint(apple_bp)

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

# Info del login_manager
try:
    app.logger.info('[DBG-LM] login_manager id=%s repr=%s login_view=%s', id(login_manager), repr(login_manager), getattr(login_manager,'login_view',None))
except Exception:
    app.logger.exception('[DBG-LM] login_manager not accessible')
# ===============================================================================

# ---------- DEBUG: wrapear before_request funcs para ver cuál devuelve algo ----------

EXEMPT_PATHS = {
    "/auth/apple/callback",
    "/auth/apple",
    "/auth/google/callback",
    "/mobile/login/google",
}

invite_code = secrets.token_urlsafe(16)

@csrf.exempt
@app.route('/api/csrf-token', methods=['GET'])
def get_csrf_token():
    return jsonify({
        "csrf_token": generate_csrf()
    })

@app.route('/api/current-user')
def api_current_user():

    if current_user.is_authenticated:


        return jsonify({
            "username":
            current_user.username
        })
    return jsonify ({
        "username": None
    }) 
     
    

def _wrap_before_request_funcs():
    """
    Envuelve los before_request, pero saltándose las rutas OAuth
    para evitar errores de CSRF.
    """
    original_funcs = app.before_request_funcs

    for bp, funcs in original_funcs.items():
        new_list = []

        for func in funcs:

            def make_wrapper(func):
                def wrapper(*args, **kwargs):

                    # ⛔ Excluir rutas OAuth del CSRF
                    if request.path in EXEMPT_PATHS:
                        # Saltamos todos los before_request peligrosos
                        return None

                    # Ejecutar el before_request original
                    return func(*args, **kwargs)

                return wrapper

            new_list.append(make_wrapper(func))

        app.before_request_funcs[bp] = new_list

_wrap_before_request_funcs()
app.logger.info(">>> [CSRF WRAPPER ACTIVADO] <<<")

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
    
    blocked_users = db.session.query(User).join(
        Block, Block.blocked_id == User.id
    ).filter(
        Block.blocker_id == current_user.id
    ).all()

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
        redirect_url=redirect_url, 
        blocked_users = blocked_users,
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

    # 🚫 USUARIOS BLOQUEADOS
    blocked_ids = []

    if current_user.is_authenticated:

        blocked_ids = [
            block.blocked_id
            for block in Block.query.filter_by(
                blocker_id=current_user.id
            ).all()
        ]

    # 🎥 VIDEOS DEL FEED
    videos = Video.query.filter(
        ~Video.user_id.in_(blocked_ids)
    ).order_by(
        Video.id.desc()
    ).all()

    video_list = []

    for video in videos:

        is_liked = (
            current_user.is_authenticated
            and current_user in video.liked_by
        )

        video_list.append({

            "url": url_for(
                'uploaded_file',
                filename=video.video_url,
                _external=True
            ),

            "id": video.id,

            "title": video.title,

            "description": video.description,

            "hashtags": video.hashtags,

            "likes": video.like_count,

            "is_liked": is_liked,

            "user": {

                "id": (
                    video.user.id
                    if video.user
                    else 0
                ),

                "username": (
                    video.user.username
                    if video.user
                    else "desconocido"
                ),

                "profile_picture": url_for(
                    'static',
                    filename=(
                        video.user.profile_pic
                        if video.user
                        and video.user.profile_pic
                        else 'default.jpg'
                    ),
                    _external=True
                ),

                "company": (
                    video.user.company
                    if video.user
                    else ""
                ),

                "name": (
                    video.user.name
                    if video.user
                    else ""
                )
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

        # ✅ VALIDACIÓN DE TÉRMINOS (OBLIGATORIO PARA APPLE)
        if not request.form.get("terms"):
            flash("Debes aceptar los Términos y Condiciones.", "error")
            professions = [p.name for p in Profession.query.order_by(Profession.name).all()]
            return render_template("register.html", form=form, user=None, professions=professions)

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
                profile_picture = request.files.get("profile_pic")
        except Exception:
            profile_picture = None

        if profile_picture and getattr(profile_picture, "filename", None):
            safe_name = secure_filename(profile_picture.filename)
            ext = safe_name.rsplit(".", 1)[-1] if "." in safe_name else ""
            filename = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
            picture_folder = app.config.get("PROFILE_PICS_FOLDER", os.path.join("static", "profile_pics"))
            os.makedirs(picture_folder, exist_ok=True)
            picture_path = os.path.join(picture_folder, filename)
            try:
                profile_picture.save(picture_path)
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

        # Guardar la contraseña
        new_user.set_password(password)

        # 🔥 Lógica de referido
        if referral_code:
            referrer = User.query.filter_by(referral_code=referral_code).first()
            if referrer:
                referrer.referred_count = (referrer.referred_count or 0) + 1
                db.session.add(referrer)
                db.session.commit()

                if referrer.referred_count == 3:
                    send_referral_reward_email(referrer.email)

        # Guardar usuario
        db.session.add(new_user)
        db.session.commit()

        # Enviar verificación
        try:
            send_verification_email(new_user.email)
        except Exception as e:
            print("Error enviando email de verificación:", e)

        flash("Registro exitoso. Verifica tu email para activar tu cuenta.", "info")
        return redirect(url_for("login"))

    # GET o fallo validación
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
        username_or_email = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        if not username_or_email or not password:
            flash('Por favor completa todos los campos.', 'error')
            return render_template('login.html')

        user = User.query.filter(
            or_(
                User.username == username_or_email,
                User.email == username_or_email
            )
        ).first()

        if user and user.password_hash and check_password_hash(user.password_hash, password):
            login_user(user, remember=remember)
            flash(f"¡Bienvenido, {user.username}!", "success")

            next_url = request.args.get('next')
            if next_url and urlparse(next_url).netloc == '':
                return redirect(next_url)
            return redirect(url_for('home'))

        flash("Usuario, email o contraseña incorrectos", "error")

    return render_template('login.html')

@app.route(
    '/api/mobile-login',
    methods=['POST']
)
@csrf.exempt
def mobile_login():

    data = request.get_json()

    username_or_email = (
        data.get(
            'username',
            ''
        ).strip()
    )

    password = data.get(
        'password',
        ''
    )

    user = User.query.filter(
        or_(
            User.username
            == username_or_email,

            User.email
            == username_or_email
        )
    ).first()

    if (
        user and
        user.password_hash and
        check_password_hash(
            user.password_hash,
            password
        )
    ):

        login_user(
            user,
            remember=True
        )

        return jsonify({

            "success": True,

            "username":
                user.username,

            "email":
                user.email
        })

    return jsonify({

        "success": False,

        "error":
            "Usuario o contraseña incorrectos"

    }), 401

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

    video = Video.query.get_or_404(video_id)
    user = current_user

    if request.method == 'POST':
        if video in user.liked_videos:
            return jsonify({'success': False, 'message': 'Ya has dado like'}), 400
        user.liked_videos.append(video)
        liked = True

    elif request.method == 'DELETE':
        if video not in user.liked_videos:
            return jsonify({'success': False, 'message': 'No has dado like'}), 200
        user.liked_videos.remove(video)
        liked = False

    db.session.commit()

    return jsonify({
        'success': True,
        'liked': liked,
        'new_likes': len(video.liked_by),
        'comments_count': len(video.comments)
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

    block_form = BlockForm()
    report_form = ReportForm()

    # =========================
    # 👤 USUARIO REAL LOGIN
    # =========================

    if current_user.is_authenticated:

        user = current_user

        # 🔥 asegurar datos frescos
        db.session.refresh(
            user
        )

        chats = get_user_chats(
            user.id
        )

    # =========================
    # 🎬 VIDEO INTRO
    # =========================

    intro_video = (
        Video.query
        .filter_by(
            is_intro=True
        )
        .first()
    )

    # =========================
    # 🧠 FEED
    # =========================

    if user:

        videos = (
            get_feed_videos(
                user
            )
        )

    else:

        videos = (
            Video.query
            .order_by(
                Video.id.desc()
            )
            .all()
        )

    # =========================
    # 🚫 NO MOSTRAR INTRO
    # SI EL USUARIO ESTÁ
    # BLOQUEADO
    # =========================

    if intro_video:

        intro_blocked = False

        if user:

            intro_blocked = (
                Block.query.filter_by(
                    blocker_id=user.id,
                    blocked_id=intro_video.user_id
                ).first()
                is not None
            )

        # 🔥 solo mostrar intro
        # si NO está bloqueado
        if not intro_blocked:

            videos = [
                v
                for v in videos
                if v.id
                != intro_video.id
            ]

            videos.insert(
                0,
                intro_video
            )

    return render_template(
        'home.html',
        user=user,
        videos=videos,
        block_form=block_form,
        report_form=report_form,
        chats=chats
    )

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '').strip()
    location = request.args.get('location', '').strip()

    videos = []
    users = []
    projects = []
    jobs = []

    if query:
        pattern = f"%{query}%"

        # 🔹 VIDEOS
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

        # 🔹 USUARIOS
        users = User.query.filter(
            or_(
                User.name.ilike(pattern),
                User.company.ilike(pattern),
                User.profession.ilike(pattern),
                User.description.ilike(pattern),
                User.location.ilike(pattern)
            )
        ).all()

        # 🔹 PROYECTOS
        projects = Project.query.join(User).filter(
            or_(
                Project.title.ilike(pattern),
                Project.short_description.ilike(pattern),
                Project.description.ilike(pattern),
                Project.location.ilike(pattern),
                User.company.ilike(pattern),
                User.name.ilike(pattern),
                User.profession.ilike(pattern)
            )
        ).order_by(Project.created_at.desc()).all()


        # 🔹 EMPLEOS
        jobs = Job.query.join(User).filter(
           or_(
               Job.title.ilike(pattern),
               Job.short_description.ilike(pattern),
               Job.description.ilike(pattern),
               Job.location.ilike(pattern),
               User.company.ilike(pattern),
               User.name.ilike(pattern),
               User.profession.ilike(pattern)
            )
        ).order_by(Job.created_at.desc()).all()

        flash(f"Resultados para: '{query}'", "info")

    return render_template(
        'search.html',
        videos=videos,
        users=users,
        projects=projects,
        jobs=jobs,
        query=query
    )
    
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

    current_app.logger.info(
        '[chat_view] request.path=%s current_user=%s authenticated=%s cookies=%s',
        request.path,
        getattr(current_user, 'username', None),
        getattr(current_user, 'is_authenticated', None),
        dict(request.cookies)
    )

    sender = current_user

    # --- Buscar receptor ---
    recipient = None
    if str(recipient_identifier).isdigit():
        recipient = db.session.get(User, int(recipient_identifier))

    if not recipient:
        recipient = db.session.query(User).filter_by(username=recipient_identifier).first()

    if not recipient:
        flash('Usuario no encontrado', 'error')
        return redirect(url_for('home'))

    # --- Buscar o crear conversación ---
    conversation = db.session.query(Conversation).filter(
        ((Conversation.user_id == sender.id) & (Conversation.recipient_id == recipient.id)) |
        ((Conversation.user_id == recipient.id) & (Conversation.recipient_id == sender.id))
    ).first()

    if not conversation:
        conversation = Conversation(user_id=sender.id, recipient_id=recipient.id)
        db.session.add(conversation)
        db.session.commit()

    # --- Marcar mensajes como leídos ---
    try:
        db.session.query(ChatMessage).filter(
            ChatMessage.conversation_id == conversation.id,
            ChatMessage.sender_id != sender.id,
            ChatMessage.is_read.is_(False)
        ).update({ChatMessage.is_read: True})
        db.session.commit()
    except Exception as e:
        current_app.logger.exception("[chat_view] error marcando leídos: %s", e)
        db.session.rollback()

    # --- Cargar mensajes ---
    messages = (
        db.session.query(ChatMessage)
        .filter_by(conversation_id=conversation.id)
        .order_by(ChatMessage.timestamp)
        .all()
    )

    room = chat_room_by_username(sender.username, recipient.username)

    return render_template(
        'chat.html',
        recipient=recipient,
        username=sender.username,
        messages=messages,
        room=room,
        conversation_id=conversation.id
    )
@csrf.exempt
@app.route('/api/start-chat/<recipient_identifier>')
@login_required
def api_start_chat(recipient_identifier):

    sender = current_user

    recipient = None

    if str(recipient_identifier).isdigit():
        recipient = db.session.get(
            User,
            int(recipient_identifier)
        )

    if not recipient:
        recipient = User.query.filter_by(
            username=recipient_identifier
        ).first()

    if not recipient:
        return jsonify({
            "success": False,
            "message": "Usuario no encontrado"
        }), 404

    conversation = Conversation.query.filter(
        (
            (Conversation.user_id == sender.id) &
            (Conversation.recipient_id == recipient.id)
        ) |
        (
            (Conversation.user_id == recipient.id) &
            (Conversation.recipient_id == sender.id)
        )
    ).first()

    if not conversation:

        conversation = Conversation(
            user_id=sender.id,
            recipient_id=recipient.id
        )

        db.session.add(conversation)
        db.session.commit()

    return jsonify({
        "success": True,
        "conversation_id": conversation.id,
        "recipient_id": recipient.id,
        "recipient_username": recipient.username
    })

@csrf.exempt
@app.route('/api/chats')
@login_required
def api_chats():

    data = []

    # Chats privados
    chats = get_user_chats(current_user.id)

    for chat in chats:

        profile_pic = chat.get('profile_pic')

        if profile_pic:
            avatar = f"/static/profile_pics/{profile_pic}"
        else:
            avatar = "/static/default_profile.png"

        data.append({
            'id': chat['conversation_id'],
            'name': chat['username'],
            'avatar': avatar,
            'is_group': False
        })

    # Grupos
    memberships = GroupMember.query.filter_by(
        user_id=current_user.id
    ).all()

    for membership in memberships:

        group = Group.query.get(
            membership.group_id
        )

        if not group:
            continue

        if group.image:
            avatar = f"/static/{group.image}"
        else:
            avatar = "/static/default_group.png"

        data.append({
            'id': group.id,
            'name': group.name,
            'avatar': avatar,
            'is_group': True
        })

    return jsonify(data)

@app.route('/api/chat/<int:conversation_id>')
@login_required
def api_chat_messages(conversation_id):

    conversation = Conversation.query.get_or_404(
        conversation_id
    )

    messages = ChatMessage.query.filter_by(
        conversation_id=conversation_id
    ).order_by(
        ChatMessage.timestamp.asc()
    ).all()

    return jsonify([
        {
            "id": m.id,
            "sender_id": m.sender_id,
            "content": m.content,
            "file_url": m.file_url,
            "thumbnail_url": m.thumbnail_url,
            "timestamp": m.timestamp.isoformat()
        }
        for m in messages
    ])

@csrf.exempt
@app.route('/api/send-message', methods=['POST'])
@login_required
def api_send_message():

    data = request.json or {}

    conversation_id = data.get(
        'conversation_id'
    )

    content = data.get(
        'message'
    )

    file_url = data.get(
        'file_url'
    )

    thumbnail_url = data.get(
        'thumbnail_url'
    )

    message = ChatMessage(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        content=content,
        file_url=file_url,
        thumbnail_url=thumbnail_url
    )

    db.session.add(message)
    db.session.commit()

    return jsonify({
        "success": True
    })

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
        
        last_message = ChatMessage.query.filter_by(conversation_id=conv.id).order_by(ChatMessage.timestamp.desc()).first()

        if last_message:
            unread_messages = ChatMessage.query.filter_by(
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
            'conversation_id': conv.id,
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
    # Debug útil
    print(
        "CHATS VIEW - current_user:",
        current_user,
        "is_authenticated:",
        current_user.is_authenticated,
        "id:",
        getattr(current_user, 'id', None)
    )

    user_id = current_user.id

    # Chats privados (como hasta ahora)
    chats = get_user_chats(user_id)

    # 🔹 Grupos donde el usuario es miembro
    groups = (
        db.session.query(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .filter(GroupMember.user_id == user_id)
        .all()
    )

    # Formulario para crear grupo (FlaskForm)
    form = CreateGroupForm()

    return render_template(
        'chat_list.html',
        username=current_user.username,
        chats=chats,
        groups=groups,   # 👈 IMPORTANTE
        form=form
    )

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


def partial_response(abs_path, content_type=None, cache_seconds=60 * 60 * 24 * 7):
    if not os.path.exists(abs_path):
        abort(404)

    file_size = os.path.getsize(abs_path)
    range_header = request.headers.get("Range")
    content_type = content_type or mimetypes.guess_type(abs_path)[0] or "application/octet-stream"

    base_headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": f"public, max-age={cache_seconds}",
        "Last-Modified": datetime.utcfromtimestamp(
            os.path.getmtime(abs_path)
        ).strftime("%a, %d %b %Y %H:%M:%S GMT"),
    }

    # =========================
    # SIN RANGE → 200
    # =========================
    if not range_header:
        response = OpinionResponse(
            open(abs_path, "rb"),
            200,
            mimetype=content_type,
            direct_passthrough=True
        )
        for k, v in base_headers.items():
            response.headers[k] = v
        return response

    # =========================
    # CON RANGE → 206
    # =========================
    try:
        units, rng = range_header.split("=")
        if units != "bytes":
            abort(416)

        start_str, end_str = rng.split("-")
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1
    except Exception:
        abort(416)

    if start >= file_size or end >= file_size or start > end:
        abort(416)

    length = end - start + 1
    with open(abs_path, "rb") as f:
        f.seek(start)
        data = f.read(length)

    response = OpinionResponse(
        data,
        206,
        mimetype=content_type,
        direct_passthrough=True
    )

    base_headers.update({
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Content-Length": str(length),
    })

    for k, v in base_headers.items():
        response.headers[k] = v

    return response

@app.route("/files/<path:filename>")
def serve_file(filename):
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

@csrf.exempt
@app.route('/api/upload_file', methods=['POST'])
@login_required
def api_upload_file():

    print("🔥 API_UPLOAD_FILE EJECUTADA")
    print("FILES:", request.files)
    print("FORM:", request.form)

    return upload_file()

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

@app.route('/groups/create', methods=['POST'])
@login_required
def create_group():
    form = CreateGroupForm()

    if not form.validate_on_submit():
        print(form.errors)
        abort(400)

    invite_code = secrets.token_urlsafe(16)

    group = Group(
        name=form.name.data,
        description=form.description.data,
        owner_id=current_user.id,
        invite_code=invite_code
    )

    # 📸 Imagen opcional
    if form.image.data:
        file = form.image.data
        filename = secure_filename(file.filename)

        upload_folder = os.path.join(
            current_app.root_path,
            'static',
            'group_pics'
        )
        os.makedirs(upload_folder, exist_ok=True)

        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)

        group.image = f'group_pics/{filename}'
    else:
        group.image = None  # se usará la default en el frontend

    db.session.add(group)
    db.session.flush()

    # Creador como admin
    member = GroupMember(
        group_id=group.id,
        user_id=current_user.id,
        is_admin=True
    )
    db.session.add(member)

    db.session.commit()

    return redirect(url_for('view_group', group_id=group.id))

@app.route('/groups/<int:group_id>')
@login_required
def group_info(group_id):
    group = Group.query.get_or_404(group_id)

    # obtener miembros del grupo
    members = GroupMember.query.filter_by(group_id=group.id).all()

    # 🔑 usar la función correcta
    is_admin = is_group_admin(group.id, current_user.id)

    form = EditGroupForm() 

    return render_template(
        'group_info.html',
        group=group,
        members=members,
        is_admin=is_admin,
        form=form,
    )

def is_group_admin(group_id, user_id):
    group = Group.query.get(group_id)
    if not group:
        return False

    if group.owner_id == user_id:
        return True

    return GroupMember.query.filter_by(
        group_id=group_id,
        user_id=user_id,
        is_admin=True
    ).first() is not None

@app.route('/groups/<int:group_id>/edit', methods=['POST'])
@login_required
def edit_group(group_id):
    group = Group.query.get_or_404(group_id)

    # Seguridad: solo admins u owner
    if not is_group_admin(group_id, current_user.id):
        abort(403)

    form = EditGroupForm()

    # CSRF + validación básica
    if not form.validate_on_submit():
        abort(400)

    # Nombre
    if form.name.data:
        group.name = form.name.data.strip()

    # Descripción (puede ser string vacío)
    if form.description.data is not None:
        group.description = form.description.data.strip()

    # Imagen
    if form.image.data:
        file = form.image.data
        filename = secure_filename(file.filename)

        upload_folder = os.path.join('static', 'group_pics')
        os.makedirs(upload_folder, exist_ok=True)

        path = os.path.join(upload_folder, filename)
        file.save(path)

        group.image = f'group_pics/{filename}'

    db.session.commit()

    return redirect(url_for('group_info', group_id=group.id, form=form))

@app.route('/groups/<int:group_id>/make-admin/<int:user_id>', methods=['POST'])
@login_required
def make_group_admin(group_id, user_id):
    member = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=user_id
    ).first_or_404()

    admin = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=current_user.id,
        is_admin=True
    ).first()

    if not admin:
        abort(403)

    member.is_admin = True
    db.session.commit()

    return {"success": True}

@app.route('/groups/<int:group_id>/remove-member/<int:user_id>', methods=['POST'])
@login_required
def remove_group_member(group_id, user_id):
    admin = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=current_user.id,
        is_admin=True
    ).first()

    if not admin or current_user.id == user_id:
        abort(403)

    member = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=user_id
    ).first_or_404()

    db.session.delete(member)
    db.session.commit()

    return {"success": True}


@app.route('/groups/invite/<invite_code>')
def group_invite(invite_code):
    group = Group.query.filter_by(invite_code=invite_code).first_or_404()

    if not current_user.is_authenticated:
        return redirect(
            url_for('login', next=url_for('group_invite', invite_code=invite_code))
        )

    already_member = GroupMember.query.filter_by(
        group_id=group.id,
        user_id=current_user.id
    ).first()

    if already_member:
        return redirect(url_for('view_group', group_id=group.id))

    # 👇 OBTENER MIEMBROS DEL GRUPO
    members = (
        GroupMember.query
        .filter_by(group_id=group.id)
        .join(User)
        .all()
    )

    return render_template(
        'join_group.html',
        group=group,
        members=members
    )

@app.route('/groups/send-invite/<int:group_id>', methods=['POST'])
@login_required
def send_group_invite(group_id):
    group = Group.query.get_or_404(group_id)

    # Solo admins del grupo
    is_admin = GroupMember.query.filter_by(
        group_id=group.id,
        user_id=current_user.id,
        is_admin=True
    ).first()

    if not is_admin:
        abort(403)

    data = request.get_json()
    conversation_id = data.get('conversation_id')

    if not conversation_id:
        abort(400)

    invite_url = url_for(
        'group_invite',
        invite_code=group.invite_code,
        _external=True
    )

    content = f"""
    <div class="group-invite-message">
      <p>👥 Te han invitado a un grupo en MAZO</p>
      <a href="{invite_url}" class="group-invite-link">
        🚀 ¡Únete a mi grupo!
      </a>
    </div>
    """

    message = ChatMessage(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        content=content
    )

    db.session.add(message)
    db.session.commit()

    return {"success": True}
@app.route('/groups/invite/accept/<int:group_id>', methods=['POST'])
@login_required
@csrf.exempt
def accept_group_invite(group_id):
    group = Group.query.get_or_404(group_id)

    already_member = GroupMember.query.filter_by(
        group_id=group.id,
        user_id=current_user.id
    ).first()

    if not already_member:
        db.session.add(GroupMember(
            group_id=group.id,
            user_id=current_user.id,
            is_admin=False
        ))
        db.session.commit()

    return redirect(url_for('view_group', group_id=group.id))

@app.route('/api/groups/<int:group_id>/invite', methods=['POST'])
@login_required
@csrf.exempt
def api_send_group_invite(group_id):

    group = Group.query.get_or_404(group_id)

    # Solo administradores del grupo
    admin = GroupMember.query.filter_by(
        group_id=group.id,
        user_id=current_user.id,
        is_admin=True
    ).first()

    if not admin:
        return jsonify({
            "success": False,
            "error": "No autorizado"
        }), 403

    data = request.get_json(silent=True) or {}

    conversation_id = data.get("conversation_id")

    if not conversation_id:
        return jsonify({
            "success": False,
            "error": "conversation_id requerido"
        }), 400

    conversation = Conversation.query.get(conversation_id)

    if not conversation:
        return jsonify({
            "success": False,
            "error": "Conversación no encontrada"
        }), 404

    invite_data = {
        "type": "group_invite",
        "group_id": group.id,
        "group_name": group.name,
        "group_description": group.description,
        "group_image": group.image,
        "invite_code": group.invite_code
    }

    message = ChatMessage(
        conversation_id=conversation.id,
        sender_id=current_user.id,
        content=json.dumps(invite_data)
    )

    db.session.add(message)
    db.session.commit()

    return jsonify({
        "success": True,
        "message_id": message.id
    })

# send_message (reemplaza handle_send_message): usa current_user en vez de 'sender' del cliente
# Imports necesarios (añádelos si no están ya en tu módulo)
@app.route('/group/<int:group_id>')
@login_required
def view_group(group_id):
    group = Group.query.get_or_404(group_id)

    member = GroupMember.query.filter_by(
        group_id=group.id,
        user_id=current_user.id
    ).first()

    if not member:
        abort(403)

    members = GroupMember.query.filter_by(group_id=group.id).all()

    messages = (
        GroupMessage.query
        .filter_by(group_id=group.id)
        .order_by(GroupMessage.timestamp.asc())
        .all()
    )

    # 🔥 NORMALIZAR URLs (ESTO ES LO QUE FALTABA)
    for msg in messages:
        if msg.file_url:
            msg.file_url = normalize_and_wait_file_url(msg.file_url)

        if msg.thumbnail_url:
            msg.thumbnail_url = normalize_and_wait_file_url(msg.thumbnail_url)

    return render_template(
        'group_chat.html',
        group=group,
        members=members,
        messages=messages
    )

@socketio.on('join_group')
def join_group_room(data):
    join_room(f"group_{data['group_id']}")
@socketio.on('send_group_message')
def handle_send_group_message(data):
    print("📩 Recibiendo mensaje de grupo:", data)

    # =========================
    # Seguridad
    # =========================
    sender = current_user
    if not sender or not sender.is_authenticated:
        return {'ok': False, 'error': 'not_authenticated'}

    group_id = data.get('group_id')
    message_text = (data.get('message') or '').strip()
    file = data.get('file')
    filename = data.get('filename')

    if not group_id or (not message_text and not file):
        return {'ok': False, 'error': 'missing_fields'}

    # =========================
    # Comprobar pertenencia al grupo
    # =========================
    member = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=sender.id
    ).first()

    if not member:
        return {'ok': False, 'error': 'not_group_member'}

    file_path = None
    thumbnail_path = None
    file_base64_payload = None
    upload_stream_url = None

    # =========================
    # Procesar archivo
    # =========================
    if file:
        try:
            # -------------------------
            # Caso: string
            # -------------------------
            if isinstance(file, str):

                # Ruta relativa ya válida
                if file.startswith("static/"):
                    file_path = file

                # Archivo pequeño en Base64
                elif file.startswith("data:") and "," in file:
                    if not filename:
                        return {'ok': False, 'error': 'missing_filename'}
                    try:
                        saved = handle_small_file(file, filename)
                        file_path = saved
                    except Exception:
                        file_base64_payload = file

                # URL absoluta (viene de /upload_file)
                elif file.startswith("http://") or file.startswith("https://"):
                    upload_stream_url = file

                    # 🔥 CONVERTIR URL → RUTA RELATIVA PARA BD
                    parsed = urlparse(file)
                    if parsed.path.startswith('/files/'):
                        file_path = parsed.path.replace('/files/', '', 1)
                    else:
                        file_path = None

                else:
                    return {'ok': False, 'error': 'unknown_file_format'}

            # -------------------------
            # Caso: FileStorage (HTTP)
            # -------------------------
            elif hasattr(file, 'filename'):
                uploaded = upload_file(file, CHAT_UPLOAD_FOLDER)
                if isinstance(uploaded, dict):
                    file_path = uploaded.get('file_path')
                    upload_stream_url = uploaded.get('stream_url')
                else:
                    file_path = uploaded

            else:
                return {'ok': False, 'error': 'unsupported_file_object'}

        except Exception as e:
            print("❌ Error procesando archivo grupo:", e)
            return {'ok': False, 'error': 'file_process_error'}

        # =========================
        # Thumbnail si es vídeo
        # =========================
        if file_path and file_path.lower().endswith(('.mp4', '.webm', '.mov', '.avi', '.mpg')):
            try:
                base = os.path.basename(file_path)
                thumb_name = f"thumb_{base}.png"
                thumb_full = os.path.join(THUMBNAIL_FOLDER, thumb_name)
                generate_thumbnail(file_path, thumb_full)
                thumbnail_path = thumb_full.replace("\\", "/")
            except Exception as e:
                print("⚠️ No se pudo generar thumbnail:", e)

    # =========================
    # Guardar en BD (🔥 CLAVE 🔥)
    # =========================
    try:
        group_message = GroupMessage(
            group_id=group_id,
            sender_id=sender.id,
            content=message_text if message_text else None,
            file_url=file_path,          # 👈 RUTA RELATIVA
            thumbnail_url=thumbnail_path
        )
        db.session.add(group_message)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print("❌ Error guardando mensaje de grupo:", e)
        return {'ok': False, 'error': 'db_error'}

    # =========================
    # Normalizar URLs públicas
    # =========================
    public_file_url = normalize_and_wait_file_url(
        file_path,
        fallback_stream_url=upload_stream_url
    )

    public_thumb_url = (
        normalize_and_wait_file_url(thumbnail_path)
        if thumbnail_path else ""
    )

    # =========================
    # Payload al frontend
    # =========================
    payload = {
        'message_id': group_message.id,
        'group_id': group_id,
        'message': message_text,
        'file_url': public_file_url or "",
        'thumbnail_url': public_thumb_url,
        'timestamp': group_message.timestamp.isoformat(),
        'username': sender.username,
        'profile_pic': sender.profile_pic,
        'sender': {
            'id': sender.id,
            'username': sender.username,
            'profile_pic': sender.profile_pic
        }
    }

    if file_base64_payload:
        payload['file_base64'] = file_base64_payload
        payload['file_name'] = filename

    # =========================
    # Emitir al grupo
    # =========================
    room = f"group_{group_id}"
    socketio.emit('group_message', payload, to=room, include_self=True)

    print(f"✅ Mensaje de grupo emitido a {room}")

    return {
        'ok': True,
        'message_id': group_message.id,
        'file_url': public_file_url,
        'thumbnail_url': public_thumb_url
    }

@socketio.on('edit_group_message')
def handle_edit_group_message(data):
    message_id = data.get('message_id')
    new_content = data.get('new_content')

    if not message_id or new_content is None:
        return {'ok': False, 'error': 'missing_fields'}

    msg = GroupMessage.query.get(message_id)
    if not msg:
        return {'ok': False, 'error': 'not_found'}

    if msg.sender_id != current_user.id:
        return {'ok': False, 'error': 'forbidden'}

    msg.content = new_content
    db.session.commit()

    room = f'group_{msg.group_id}'

    socketio.emit('group_message_edited', {
        'message_id': message_id,
        'new_message': new_content,
        'username': current_user.username
    }, to=room)

    return {'ok': True}

@socketio.on('delete_group_message')
def handle_delete_group_message(data):
    message_id = data.get('message_id')

    if not message_id:
        return {'ok': False}

    msg = GroupMessage.query.get(message_id)
    if not msg:
        return {'ok': False}

    if msg.sender_id != current_user.id:
        return {'ok': False}

    group_id = msg.group_id

    db.session.delete(msg)
    db.session.commit()

    socketio.emit(
        'group_message_deleted',
        {'message_id': message_id},
        to=f'group_{group_id}'
    )

    return {'ok': True}

@csrf.exempt
@app.route('/api/groups/create', methods=['POST'])
@login_required
def api_create_group():

    name = request.form.get('name')
    description = request.form.get('description', '')

    if not name:
        return jsonify({
            "success": False,
            "error": "Nombre requerido"
        }), 400

    invite_code = secrets.token_urlsafe(16)

    group = Group(
        name=name,
        description=description,
        owner_id=current_user.id,
        invite_code=invite_code
    )

    image = request.files.get('image')

    if image and image.filename:

        filename = secure_filename(image.filename)

        unique_filename = (
            f"{uuid.uuid4().hex}_{filename}"
        )

        os.makedirs(
            os.path.join(
                app.static_folder,
                'group_pics'
            ),
            exist_ok=True
        )

        image_path = os.path.join(
            app.static_folder,
            'group_pics',
            unique_filename
        )

        image.save(image_path)

        group.image = (
            f"group_pics/{unique_filename}"
        )

    db.session.add(group)
    db.session.flush()

    db.session.add(
        GroupMember(
            group_id=group.id,
            user_id=current_user.id,
            is_admin=True
        )
    )

    db.session.commit()

    return jsonify({
        "success": True,
        "group_id": group.id,
        "image": group.image
    })

@csrf.exempt
@app.route('/api/groups/<int:group_id>/add-members', methods=['POST'])
@login_required
def api_add_group_members(group_id):

    data = request.json or {}

    user_ids = data.get('user_ids', [])

    for user_id in user_ids:

        exists = GroupMember.query.filter_by(
            group_id=group_id,
            user_id=user_id
        ).first()

        if not exists:

            db.session.add(
                GroupMember(
                    group_id=group_id,
                    user_id=user_id
                )
            )

    db.session.commit()

    return jsonify({
        "success": True
    })
@csrf.exempt
@app.route('/api/groups')
@login_required
def api_groups():

    memberships = GroupMember.query.filter_by(
        user_id=current_user.id
    ).all()

    result = []

    for membership in memberships:

        group = Group.query.get(
            membership.group_id
        )

        result.append({
            "id": group.id,
            "name": group.name,
            "image": group.image
        })

    return jsonify(result)

@app.route('/api/groups/join', methods=['POST'])
@login_required
@csrf.exempt
def api_join_group():

    data = request.get_json(silent=True) or {}

    invite_code = data.get("invite_code")

    if not invite_code:
        return jsonify({
            "success": False,
            "error": "invite_code requerido"
        }), 400

    group = Group.query.filter_by(
        invite_code=invite_code
    ).first()

    if not group:
        return jsonify({
            "success": False,
            "error": "Grupo no encontrado"
        }), 404

    existing = GroupMember.query.filter_by(
        group_id=group.id,
        user_id=current_user.id
    ).first()

    if existing:
        return jsonify({
            "success": False,
            "error": "Ya perteneces al grupo"
        }), 400

    member = GroupMember(
        group_id=group.id,
        user_id=current_user.id,
        is_admin=False
    )

    db.session.add(member)
    db.session.commit()

    return jsonify({
        "success": True,
        "group_id": group.id
    })

@csrf.exempt
@app.route('/api/groups/<int:group_id>/messages')
@login_required
def api_group_messages(group_id):

    messages = (
        GroupMessage.query
        .filter_by(group_id=group_id)
        .order_by(GroupMessage.timestamp.asc())
        .all()
    )

    return jsonify([
        {
            "id": m.id,
            "content": m.content,
            "sender_id": m.sender_id,
            "username": m.sender.username,
            "profile_pic": m.sender.profile_pic,
            "file_url": m.file_url,
            "thumbnail_url": m.thumbnail_url,
            "timestamp": m.timestamp.isoformat()
        }
        for m in messages
    ])

@csrf.exempt
@app.route('/api/groups/<int:group_id>/send', methods=['POST'])
@login_required
def api_send_group_message(group_id):

    member = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=current_user.id
    ).first()

    if not member:
        return jsonify({
            "success": False
        }), 403

    data = request.get_json() or {}

    content = (
        data.get("message", "")
        .strip()
    )

    file_url = data.get(
        "file_url"
    )

    thumbnail_url = data.get(
        "thumbnail_url"
    )

    if not content and not file_url:
        return jsonify({
            "success": False
        }), 400

    message = GroupMessage(
        group_id=group_id,
        sender_id=current_user.id,
        content=content if content else None,
        file_url=file_url,
        thumbnail_url=thumbnail_url
    )

    db.session.add(message)
    db.session.commit()

    return jsonify({
        "success": True,
        "message_id": message.id
    })

@csrf.exempt
@app.route(
    '/api/groups/message/<int:message_id>/edit',
    methods=['POST']
)
@login_required
def api_edit_group_message(message_id):

    msg = GroupMessage.query.get_or_404(
        message_id
    )

    if msg.sender_id != current_user.id:
        return jsonify({
            "success": False
        }), 403

    data = request.get_json()

    msg.content = data.get(
        'content',
        ''
    )

    db.session.commit()

    return jsonify({
        "success": True
    })

@csrf.exempt
@app.route(
    '/api/groups/message/<int:message_id>/delete',
    methods=['POST']
)
@login_required
def api_delete_group_message(message_id):

    msg = GroupMessage.query.get_or_404(
        message_id
    )

    if msg.sender_id != current_user.id:
        return jsonify({
            "success": False
        }), 403

    db.session.delete(msg)
    db.session.commit()

    return jsonify({
        "success": True
    })

@csrf.exempt
@app.route('/api/groups/<int:group_id>/info')
@login_required
def api_group_info(group_id):

    group = Group.query.get_or_404(
        group_id
    )

    member = GroupMember.query.filter_by(
        group_id=group.id,
        user_id=current_user.id
    ).first()

    if not member:
        return jsonify({}), 403

    return jsonify({

        "id": group.id,

        "name": group.name,

        "description": group.description,

        "invite_code": group.invite_code,

        "owner_id": group.owner_id,

        "is_admin": member.is_admin,

        "image":
            f"/static/{group.image}"
            if group.image else
            "/static/default_group.png"
    })

@csrf.exempt
@app.route('/api/groups/<int:group_id>/edit', methods=['POST'])
@login_required
def api_edit_group(group_id):

    print("FILES:", request.files)
    print("FORM:", request.form)

    group = Group.query.get_or_404(group_id)

    # Solo administradores
    if not is_group_admin(group_id, current_user.id):
        return jsonify({
            "success": False,
            "error": "No autorizado"
        }), 403

    # Nombre
    name = request.form.get("name")
    if name:
        group.name = name.strip()

    # Descripción
    description = request.form.get("description")
    if description is not None:
        group.description = description.strip()

    # Imagen
    image = request.files.get("image")

    if image and image.filename:

        filename = secure_filename(image.filename)

        unique_filename = (
            f"{uuid.uuid4().hex}_{filename}"
        )

        upload_folder = os.path.join(
            app.static_folder,
            "group_pics"
        )

        os.makedirs(
            upload_folder,
            exist_ok=True
        )

        image.save(
            os.path.join(
                upload_folder,
                unique_filename
            )
        )

        group.image = (
            f"group_pics/{unique_filename}"
        )

    db.session.commit()

    return jsonify({

        "success": True,

        "group": {

            "id": group.id,

            "name": group.name,

            "description": group.description,

            "image":
                f"/static/{group.image}"
                if group.image else
                "/static/default_group.png"
        }
    })

@csrf.exempt
@app.route('/api/groups/<int:group_id>/members')
@login_required
def api_group_members(group_id):

    members = (
        GroupMember.query
        .filter_by(group_id=group_id)
        .all()
    )

    return jsonify([
        {
            "user_id":
                member.user.id,

            "username":
                member.user.username,

            "profile_pic":
                f"/static/profile_pics/{member.user.profile_pic}"
                if member.user.profile_pic else "",

            "is_admin":
                member.is_admin
        }
        for member in members
    ])
@csrf.exempt
@app.route(
    '/api/groups/<int:group_id>/make-admin/<int:user_id>',
    methods=['POST']
)
@login_required
def api_make_group_admin(
    group_id,
    user_id
):

    if not is_group_admin(
        group_id,
        current_user.id
    ):
        return jsonify({
            "success": False
        }), 403

    member = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=user_id
    ).first_or_404()

    member.is_admin = True

    db.session.commit()

    return jsonify({
        "success": True
    })
@csrf.exempt
@app.route(
    '/api/groups/<int:group_id>/remove-admin/<int:user_id>',
    methods=['POST']
)
@login_required
def api_remove_group_admin(
    group_id,
    user_id
):

    group = Group.query.get_or_404(
        group_id
    )

    if group.owner_id != current_user.id:
        return jsonify({
            "success": False
        }), 403

    member = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=user_id
    ).first_or_404()

    member.is_admin = False

    db.session.commit()

    return jsonify({
        "success": True
    })
@csrf.exempt
@app.route(
    '/api/groups/<int:group_id>/remove-member/<int:user_id>',
    methods=['POST']
)
@login_required
def api_remove_group_member(
    group_id,
    user_id
):

    if not is_group_admin(
        group_id,
        current_user.id
    ):
        return jsonify({
            "success": False
        }), 403

    member = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=user_id
    ).first_or_404()

    db.session.delete(member)

    db.session.commit()

    return jsonify({
        "success": True
    })
@csrf.exempt
@app.route(
    '/api/groups/<int:group_id>/delete',
    methods=['POST']
)
@login_required
def api_delete_group(group_id):

    group = Group.query.get_or_404(
        group_id
    )

    if group.owner_id != current_user.id:
        return jsonify({
            "success": False
        }), 403

    GroupMessage.query.filter_by(
        group_id=group.id
    ).delete()

    GroupMember.query.filter_by(
        group_id=group.id
    ).delete()

    db.session.delete(group)

    db.session.commit()

    return jsonify({
        "success": True
    })
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
        new_message = ChatMessage(
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

    msg = ChatMessage.query.get(message_id)
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

    msg = ChatMessage.query.get(message_id)
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

@csrf.exempt
@app.route('/api/message/<int:message_id>', methods=['PUT'])
@login_required
def api_edit_message(message_id):

    msg = ChatMessage.query.get(message_id)

    if not msg:
        return jsonify({
            'success': False,
            'error': 'not_found'
        }), 404

    if msg.sender_id != current_user.id:
        return jsonify({
            'success': False,
            'error': 'forbidden'
        }), 403

    data = request.get_json() or {}

    new_content = data.get('content', '')

    msg.content = new_content

    db.session.commit()

    return jsonify({
        'success': True,
        'message_id': msg.id,
        'content': msg.content
    })

@csrf.exempt
@app.route('/api/message/<int:message_id>', methods=['DELETE'])
@login_required
def api_delete_message(message_id):

    msg = ChatMessage.query.get(message_id)

    if not msg:
        return jsonify({
            'success': False,
            'error': 'not_found'
        }), 404

    if msg.sender_id != current_user.id:
        return jsonify({
            'success': False,
            'error': 'forbidden'
        }), 403

    db.session.delete(msg)

    db.session.commit()

    return jsonify({
        'success': True,
        'message_id': message_id
    })

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
    new_message = ChatMessage(
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
        new_message = ChatMessage(
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

@app.route('/api/profile/<username>')
def api_profile(username):

    user = User.query.filter_by(
        username=username
    ).first_or_404()

    current_user_id = (
        current_user.id
        if current_user.is_authenticated
        else None
    )

    # 🎥 Videos
    videos = []

    for video in user.videos_uploaded:

        videos.append({
            "id": video.id,

            "video_url":
                url_for(
                    'uploaded_file',
                    filename=video.video_url,
                    _external=True
                ),

            "thumbnail":
                url_for(
                    'uploaded_file',
                    filename=video.video_url,
                    _external=True
                ),

            "title": video.title
        })

    # ❤️ Likes
    liked_videos = []

    for video in user.liked_videos:

        liked_videos.append({
            "id": video.id,

            "video_url":
                url_for(
                    'uploaded_file',
                    filename=video.video_url,
                    _external=True
                ),

            "title": video.title
        })

    # 🛍️ Productos
    products = []

    for product in user.products:

        if not product.is_active:
            continue

        print(
            f"PRODUCTO {product.id} | "
            f"TITULO={product.title} | "
            f"IMAGES={len(product.images)}"
        )

        image_url = None

        if product.images and len(product.images) > 0:

            print(
                "PRIMERA IMAGEN:",
                product.images[0].image
            )

            image_url = url_for(
                'static',
                filename=f'product_images/{product.images[0].image}',
                _external=True
            )

            print(
                "IMAGE URL:",
                image_url
            )

        products.append({
            "id": product.id,
            "title": product.title,
            "description": product.description,
            "price": float(product.price),
            "image": image_url,
            "user_id": product.user_id,
            "username": product.user.username
        })

    return jsonify({

        "id": user.id,

        "username":
            user.username,

        "name":
            user.name
            or user.username,

        "profile_picture":
            url_for(
                'static',
                filename=(
                    user.profile_pic
                    if user.profile_pic
                    else
                    'profile_pics/default.jpg'
                ),
                _external=True
            ),

        "company":
            user.company,

        "profession":
            ", ".join(
                user.profession_names
            )
            if user.profession_names
            else user.profession,

        "description":
            user.description,

        "location":
            user.location,

        "is_premium":
            user.is_premium,

        "followers":
            user.followers.count(),

        "following":
            user.followed.count(),

        "is_following":
            current_user.is_authenticated
            and current_user.is_following(user),

        "is_owner":
            current_user_id
            == user.id,

        "has_cv":
            bool(user.cv_file),

        "has_cv_pdf":
            bool(user.cv_file),

        "videos":
            videos,

        "liked_videos":
            liked_videos,

        "products":
            products
    })

@app.route('/profile/<username>', methods=['GET', 'POST'])
def profile(username):
    block_form = BlockForm()
    report_form = ReportForm()

    user = User.query.filter_by(username=username).first()

    if not user:
        flash('Usuario no encontrado', 'error')
        return redirect(url_for('home'))

    form = OpinionForm()

    average_rating = db.session.query(
        db.func.avg(Opinion.rating)
    ).filter_by(profile_user_id=user.id).scalar()

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
                        'user_profile_url': url_for(
                            'profile',
                            username=current_user.username
                        ),
                        'user_profile_pic': url_for(
                            'static',
                            filename=current_user.profile_pic
                            if current_user.profile_pic
                            else 'profile_pics/default.jpg'
                        ),
                        'opinion_text': opinion_text,
                        'rating': rating
                    })

                else:
                    return jsonify({
                        'success': False,
                        'message': 'La puntuación debe estar entre 0 y 10.'
                    })

            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'La puntuación ingresada no es válida.'
                })

        else:
            return jsonify({
                'success': False,
                'message': 'Debes escribir una opinión y asignar una puntuación.'
            })

    # Parte GET: cargar perfil y opiniones
    opinions = Opinion.query.filter_by(
        profile_user_id=user.id
    ).all()

    # Videos subidos
    videos = Video.query.filter_by(
        user_id=user.id
    ).all()

    # ❤️ Videos con like
    liked_videos = user.liked_videos

    # Productos
    products = Product.query.filter_by(
        user_id=user.id,
        is_active=True
    ).order_by(
        Product.created_at.desc()
    ).all()

    return render_template(
        'profile.html',
        user=user,
        opinions=opinions,
        form=form,
        average_rating=average_rating,
        videos=videos,
        liked_videos=liked_videos,  # ❤️ NUEVO
        products=products,
        report_form=report_form,
        block_form=block_form
    )


@app.route('/profile')
@login_required
def my_profile():
    return redirect(
        url_for(
            'profile',
            username=current_user.username
        )
    )


@app.route('/product/<int:product_id>')
def view_product(product_id):
    product = Product.query.get_or_404(product_id)

    # solo mostrar productos activos
    if not product.is_active:
        abort(404)

    return render_template(
        'view_product.html',
        product=product,
    )

@app.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)

    if product.user_id != current_user.id:
        abort(403)

    form = CreateProductForm(obj=product)

    if form.validate_on_submit():
        product.title = form.title.data
        product.description = form.description.data
        product.price = float(form.price.data)

        db.session.commit()
        flash('Producto actualizado', 'success')
        return redirect(url_for('view_product', product_id=product.id))

    return render_template('edit_product.html', form=form, product=product)

@app.route('/products/<int:product_id>/delete', methods=['POST'])
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)

    if product.user_id != current_user.id:
        abort(403)

    # Borrar imágenes del disco
    for image in product.images:
        image_path = os.path.join(
            app.config['PRODUCT_IMAGES_FOLDER'],
            image.image
        )
        if os.path.exists(image_path):
            os.remove(image_path)
        db.session.delete(image)

    db.session.delete(product)
    db.session.commit()

    flash('Producto eliminado', 'success')
    return redirect(url_for('profile', username=current_user.username))

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

@app.route(
    '/api/edit-profile',
    methods=['GET']
)
@login_required
def api_get_edit_profile():

    return jsonify({

        "success": True,

        "name":
            current_user.name,

        "email":
            current_user.email,

        "company":
            current_user.company,

        "description":
            current_user.description,

        "location":
            current_user.location,

        "professions":
            current_user.profession_names,

        "profile_picture":
            (
                url_for(
                    'static',
                    filename=current_user.profile_pic,
                    _external=True
                )
                if current_user.profile_pic
                else None
            )
    })

@app.route(
    '/api/edit-profile',
    methods=['POST']
)

@csrf.exempt
@login_required
def api_edit_profile():

    data = request.get_json()

    current_user.name = (
        data.get(
            "name",
            ""
        ).strip()
    )

    current_user.email = (
        data.get(
            "email"
        ) or None
    )

    current_user.company = (
        data.get(
            "company"
        ) or None
    )

    current_user.description = (
        data.get(
            "description"
        ) or None
    )

    current_user.location = (
        data.get(
            "location"
        ) or None
    )

    professions = data.get(
        "professions",
        []
    )

    current_user.set_professions_from_list(
        professions
    )

    # Compatibilidad con la columna antigua
    current_user.profession = (
        professions[0]
        if professions
        else None
    )

    db.session.commit()

    return jsonify({

        "success": True,

        "message":
            "Perfil actualizado correctamente"
    })

@app.route(
    '/api/profile-picture',
    methods=['POST']
)
@login_required
def api_profile_picture():

    profile_pic = request.files.get(
        "profile_pic"
    )

    if not profile_pic:

        return jsonify({

            "success": False,

            "message":
                "No se recibió ninguna imagen"
        }), 400

    filename = secure_filename(
        profile_pic.filename
    )

    name_part, ext = os.path.splitext(
        filename
    )

    unique_name = (
        f"{name_part}_{int(time.time())}{ext}"
    )

    os.makedirs(
        app.config["PROFILE_PICS_FOLDER"],
        exist_ok=True
    )

    path = os.path.join(
        app.config["PROFILE_PICS_FOLDER"],
        unique_name
    )

    profile_pic.save(
        path
    )

    current_user.profile_pic = (
        f"profile_pics/{unique_name}"
    )

    db.session.commit()

    return jsonify({

        "success": True,

        "profile_picture":
            url_for(
                'static',
                filename=current_user.profile_pic,
                _external=True
            )
    })

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

@app.route('/delete_cv', methods=['POST'])
@login_required
def delete_cv():

    # Si el usuario tiene CV guardado
    if current_user.cv_file:

        cv_path = os.path.join(
            app.config['UPLOAD_FOLDER'],
            current_user.cv_file
        )

        # Eliminar archivo físico si existe
        if os.path.exists(cv_path):
            os.remove(cv_path)

        # Borrar referencia en BD
        current_user.cv_file = None
        db.session.commit()

        flash('CV eliminado correctamente', 'success')

    else:
        flash('No tienes ningún CV subido', 'error')

    return redirect(
        url_for(
            'profile',
            username=current_user.username
        )
    )

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

@app.route('/cv/edit', methods=['GET', 'POST'])
@login_required
def edit_cv():

    form = EmptyForm()

    # 🔢 Paso actual
    step = request.args.get(
        'step',
        '1'
    )

    # Buscar CV usuario
    user_cv = UserCV.query.filter_by(
        user_id=current_user.id
    ).first()

    # Crear CV automático
    if not user_cv:

        user_cv = UserCV(
            user_id=current_user.id,
            full_name=current_user.name,
            email=current_user.email,
            phone=current_user.phone,
            location=current_user.location,
            profile_picture=current_user.profile_pic
        )

        db.session.add(user_cv)
        db.session.commit()

    # =================================
    # GUARDAR FORMULARIO
    # =================================
    if request.method == 'POST':

        # ======================
        # STEP 1 - DATOS PERSONALES
        # ======================
        if step == '1':

            user_cv.full_name = request.form.get(
                'full_name'
            )

            user_cv.email = request.form.get(
                'email'
            )

            user_cv.phone = request.form.get(
                'phone'
            )

            user_cv.location = request.form.get(
                'location'
            )

            birth_date = request.form.get(
                'birth_date'
            )

            if birth_date:

                user_cv.birth_date = (
                    datetime.strptime(
                        birth_date,
                        '%Y-%m-%d'
                    ).date()
                )

            # ======================
            # FOTO DEL CV
            # ======================
            cv_photo = request.files.get(
                'cv_profile_picture'
            )

            if (
                cv_photo and
                cv_photo.filename
            ):

                filename = secure_filename(
                    cv_photo.filename
                )

                extension = filename.split(
                    '.'
                )[-1]

                unique_filename = (
                    f'cv_'
                    f'{current_user.id}.'
                    f'{extension}'
                )

                upload_folder = os.path.join(
                    app.root_path,
                    'static',
                    'cv_profiles'
                )

                os.makedirs(
                    upload_folder,
                    exist_ok=True
                )

                save_path = os.path.join(
                    upload_folder,
                    unique_filename
                )

                cv_photo.save(
                    save_path
                )

                user_cv.profile_picture = (
                    unique_filename
                )

        # ======================
        # STEP 2 - EXPERIENCIA
        # ======================
        elif step == '2':

            CVExperience.query.filter_by(
                user_cv_id=user_cv.id
            ).delete()

            company_names = request.form.getlist(
                'company_name[]'
            )

            job_titles = request.form.getlist(
                'job_title[]'
            )

            start_dates = request.form.getlist(
                'start_date[]'
            )

            end_dates = request.form.getlist(
                'end_date[]'
            )

            descriptions = request.form.getlist(
                'description[]'
            )

            for i in range(
                len(company_names)
            ):

                if not company_names[i].strip():
                    continue

                experience = CVExperience(
                    user_cv_id=user_cv.id,
                    company_name=company_names[i],
                    job_title=job_titles[i],
                    description=descriptions[i]
                )

                if start_dates[i]:

                    experience.start_date = (
                        datetime.strptime(
                            start_dates[i],
                            '%Y-%m-%d'
                        ).date()
                    )

                if end_dates[i]:

                    experience.end_date = (
                        datetime.strptime(
                            end_dates[i],
                            '%Y-%m-%d'
                        ).date()
                    )

                db.session.add(
                    experience
                )

        # ======================
        # STEP 3 - EDUCACIÓN
        # ======================
        elif step == '3':

            CVEducation.query.filter_by(
                user_cv_id=user_cv.id
            ).delete()

            school_names = request.form.getlist(
                'school_name[]'
            )

            degree_names = request.form.getlist(
                'degree_name[]'
            )

            start_dates = request.form.getlist(
                'education_start_date[]'
            )

            end_dates = request.form.getlist(
                'education_end_date[]'
            )

            for i in range(
                len(school_names)
            ):

                if not school_names[i].strip():
                    continue

                education = CVEducation(
                    user_cv_id=user_cv.id,
                    school_name=school_names[i],
                    degree_name=degree_names[i],
                    currently_studying=(
                        f'currently_studying_{i}'
                        in request.form
                    )
                )

                if start_dates[i]:

                    education.start_date = (
                        datetime.strptime(
                            start_dates[i],
                            '%Y-%m-%d'
                        ).date()
                    )

                if end_dates[i]:

                    education.end_date = (
                        datetime.strptime(
                            end_dates[i],
                            '%Y-%m-%d'
                        ).date()
                    )

                db.session.add(
                    education
                )

        # ======================
        # STEP 4 - HABILIDADES
        # ======================
        elif step == '4':

            CVSkill.query.filter_by(
                user_cv_id=user_cv.id
            ).delete()

            skill_names = request.form.getlist(
                'skill_name[]'
            )

            for skill_name in skill_names:

                if not skill_name.strip():
                    continue

                skill = CVSkill(
                    user_cv_id=user_cv.id,
                    skill_name=skill_name.strip()
                )

                db.session.add(skill)

        # ======================
        # STEP 5 - IDIOMAS
        # ======================
        elif step == '5':

            CVLanguage.query.filter_by(
                user_cv_id=user_cv.id
            ).delete()

            language_names = request.form.getlist(
                'language_name[]'
            )

            levels = request.form.getlist(
                'language_level[]'
            )

            for i in range(
                len(language_names)
            ):

                if not language_names[i].strip():
                    continue

                language = CVLanguage(
                    user_cv_id=user_cv.id,
                    language_name=language_names[i],
                    level=levels[i]
                )

                db.session.add(
                    language
                )

        # ======================
        # STEP 6 - INFO EXTRA
        # ======================
        elif step == '6':

            user_cv.additional_information = (
                request.form.get(
                    'additional_information'
                )
            )

        db.session.commit()

        # ======================
        # NAVEGACIÓN
        # ======================

        if step == '1':
            return redirect(
                url_for(
                    'edit_cv',
                    step='2'
                )
            )

        elif step == '2':
            return redirect(
                url_for(
                    'edit_cv',
                    step='3'
                )
            )

        elif step == '3':
            return redirect(
                url_for(
                    'edit_cv',
                    step='4'
                )
            )

        elif step == '4':
            return redirect(
                url_for(
                    'edit_cv',
                    step='5'
                )
            )

        elif step == '5':
            return redirect(
                url_for(
                    'edit_cv',
                    step='6'
                )
            )

        elif step == '6':
            return redirect(
                url_for(
                    'cv_design'
                )
            )

    return render_template(
        'edit_cv.html',
        user_cv=user_cv,
        step=step,
        form=form
    )

@app.route('/cv/design')
@login_required
def cv_design():

    user_cv = UserCV.query.filter_by(
        user_id=current_user.id
    ).first_or_404()

    return render_template(
        'cv_design.html',
        user_cv=user_cv
    )


def generate_cv_pdf(user_cv):

    # ==========================
    # CARPETA PDF
    # ==========================
    pdf_folder = os.path.join(
        app.root_path,
        'static',
        'cv_pdfs'
    )

    os.makedirs(
        pdf_folder,
        exist_ok=True
    )

    filename = (
        f'cv_{user_cv.user_id}.pdf'
    )

    pdf_path = os.path.join(
        pdf_folder,
        filename
    )

    # ==========================
    # CONFIG DOCUMENTO
    # ==========================
    doc = SimpleDocTemplate(
        pdf_path,
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20
    )

    styles = getSampleStyleSheet()

    # ==========================
    # ESTILOS
    # ==========================
    title_style = styles['Title']
    title_style.textColor = colors.black
    title_style.fontSize = 24
    title_style.alignment = 1

    subtitle_style = styles['BodyText']
    subtitle_style.textColor = colors.black
    subtitle_style.fontSize = 12
    subtitle_style.alignment = 1

    heading_style = styles['Heading2']
    heading_style.textColor = colors.black
    heading_style.spaceAfter = 8

    normal_style = styles['BodyText']
    normal_style.textColor = colors.black

    story = []

    # ==========================
    # FOTO PERFIL
    # ==========================
    profile_image = Spacer(
        3*cm,
        3*cm
    )

    if user_cv.profile_picture:

        image_path = os.path.join(
            app.root_path,
            'static',
            'cv_profiles',
            user_cv.profile_picture
        )

        if os.path.exists(
            image_path
        ):

            profile_image = Image(
                image_path,
                width=3*cm,
                height=3*cm
            )

    # ==========================
    # HEADER VERDE MAZO
    # ==========================
    header_content = [

        Spacer(1, 6),

        Paragraph(
            user_cv.full_name or '',
            title_style
        ),

        Paragraph(
            (
                user_cv.professional_title
                or 'Profesional'
            ),
            subtitle_style
        )
    ]

    header_table = Table([
        [
            profile_image,
            header_content
        ]
    ],
    colWidths=[4*cm, 12*cm])

    header_table.setStyle(
        TableStyle([

            (
                'BACKGROUND',
                (0, 0),
                (-1, -1),
                colors.HexColor(
                    '#1FA03D'
                )
            ),

            (
                'VALIGN',
                (0, 0),
                (-1, -1),
                'MIDDLE'
            ),

            (
                'LEFTPADDING',
                (0, 0),
                (-1, -1),
                18
            ),

            (
                'RIGHTPADDING',
                (0, 0),
                (-1, -1),
                18
            ),

            (
                'TOPPADDING',
                (0, 0),
                (-1, -1),
                18
            ),

            (
                'BOTTOMPADDING',
                (0, 0),
                (-1, -1),
                18
            )

        ])
    )

    story.append(
        header_table
    )

    story.append(
        Spacer(1, 12)
    )

    # ==========================
    # SIDEBAR
    # ==========================
    sidebar_content = []

    # UBICACIÓN
    if user_cv.location:

        sidebar_content.append(
            Paragraph(
                '📍 Ubicación',
                heading_style
            )
        )

        sidebar_content.append(
            Paragraph(
                user_cv.location,
                normal_style
            )
        )

        sidebar_content.append(
            Spacer(1, 8)
        )

    # CONTACTO
    if user_cv.phone:

        sidebar_content.append(
            Paragraph(
                '📞 Contacto',
                heading_style
            )
        )

        sidebar_content.append(
            Paragraph(
                user_cv.phone,
                normal_style
            )
        )

        sidebar_content.append(
            Spacer(1, 8)
        )

    # EMAIL
    if user_cv.email:

        sidebar_content.append(
            Paragraph(
                '📧 Email',
                heading_style
            )
        )

        sidebar_content.append(
            Paragraph(
                user_cv.email,
                normal_style
            )
        )

        sidebar_content.append(
            Spacer(1, 8)
        )

    # IDIOMAS
    if user_cv.languages:

        sidebar_content.append(
            Paragraph(
                '🌍 Idiomas',
                heading_style
            )
        )

        for language in user_cv.languages:

            sidebar_content.append(
                Paragraph(
                    f'{language.language_name} - {language.level}',
                    normal_style
                )
            )

        sidebar_content.append(
            Spacer(1, 8)
        )

    # HABILIDADES
    if user_cv.skills:

        sidebar_content.append(
            Paragraph(
                '⭐ Habilidades',
                heading_style
            )
        )

        for skill in user_cv.skills:

            sidebar_content.append(
                Paragraph(
                    skill.skill_name,
                    normal_style
                )
            )

    # ==========================
    # MAIN CONTENT
    # ==========================
    main_content = []

    # SOBRE MÍ
    if user_cv.about_me:

        main_content.append(
            Paragraph(
                'Sobre mí',
                heading_style
            )
        )

        main_content.append(
            Paragraph(
                user_cv.about_me,
                normal_style
            )
        )

        main_content.append(
            Spacer(1, 8)
        )

    # EXPERIENCIA
    if user_cv.experiences:

        main_content.append(
            Paragraph(
                'Experiencia',
                heading_style
            )
        )

        for exp in user_cv.experiences:

            main_content.append(
                Paragraph(
                    f'<b>{exp.job_title}</b>',
                    normal_style
                )
            )

            main_content.append(
                Paragraph(
                    exp.company_name,
                    normal_style
                )
            )

            if exp.description:

                main_content.append(
                    Paragraph(
                        exp.description,
                        normal_style
                    )
                )

            main_content.append(
                Spacer(1, 6)
            )

    # EDUCACIÓN
    if user_cv.educations:

        main_content.append(
            Paragraph(
                'Educación',
                heading_style
            )
        )

        for edu in user_cv.educations:

            main_content.append(
                Paragraph(
                    f'<b>{edu.degree_name}</b>',
                    normal_style
                )
            )

            main_content.append(
                Paragraph(
                    edu.school_name,
                    normal_style
                )
            )

            main_content.append(
                Spacer(1, 5)
            )

    # INFO EXTRA
    if user_cv.additional_information:

        main_content.append(
            Paragraph(
                'Información adicional',
                heading_style
            )
        )

        main_content.append(
            Paragraph(
                user_cv.additional_information,
                normal_style
            )
        )

    # ==========================
    # TABLA PRINCIPAL
    # ==========================
    content_table = Table([
        [
            sidebar_content,
            main_content
        ]
    ],
    colWidths=[4.5*cm, 11.5*cm])

    content_table.setStyle(
        TableStyle([

            (
                'BACKGROUND',
                (0, 0),
                (0, -1),
                colors.HexColor(
                    '#F1F1F1'
                )
            ),

            (
                'BOX',
                (0, 0),
                (-1, -1),
                1,
                colors.HexColor(
                    '#DDDDDD'
                )
            ),

            (
                'VALIGN',
                (0, 0),
                (-1, -1),
                'TOP'
            ),

            (
                'LEFTPADDING',
                (0, 0),
                (-1, -1),
                14
            ),

            (
                'RIGHTPADDING',
                (0, 0),
                (-1, -1),
                14
            ),

            (
                'TOPPADDING',
                (0, 0),
                (-1, -1),
                14
            ),

            (
                'BOTTOMPADDING',
                (0, 0),
                (-1, -1),
                14
            )

        ])
    )

    story.append(
        content_table
    )

    # ==========================
    # GENERAR PDF
    # ==========================
    doc.build(story)

    return (
        f'cv_pdfs/{filename}'
    )

@app.route('/cv/select-design/<design>')
@login_required
def select_cv_design(design):

    user_cv = UserCV.query.filter_by(
        user_id=current_user.id
    ).first_or_404()

    # ==========================
    # DISEÑOS DISPONIBLES
    # ==========================
    allowed_designs = [
        'basic'
    ]

    if design not in allowed_designs:

        flash(
            'Diseño no disponible',
            'error'
        )

        return redirect(
            url_for(
                'cv_design'
            )
        )

    # ==========================
    # GUARDAR DISEÑO
    # ==========================
    user_cv.cv_template = design

    # ==========================
    # GENERAR PDF
    # ==========================
    pdf_path = generate_cv_pdf(
        user_cv
    )

    user_cv.cv_pdf = pdf_path

    db.session.commit()

    flash(
        'CV creado exitosamente',
        'success'
    )

    return redirect(
        url_for(
            'profile',
            username=current_user.username,
            cv_created='1'
        )
    )

@app.route(
    '/professional-cv/<username>'
)
@login_required
def view_professional_cv(username):

    user = User.query.filter_by(
        username=username
    ).first_or_404()

    user_cv = UserCV.query.filter_by(
        user_id=user.id
    ).first()

    # No tiene CV
    if (
        not user_cv or
        not user_cv.cv_pdf
    ):

        flash(
            'Este usuario aún no ha creado un CV profesional.',
            'error'
        )

        return redirect(
            url_for(
                'profile',
                username=username
            )
        )

    # Abrir PDF real
    return redirect(
        url_for(
            'static',
            filename=user_cv.cv_pdf
        )
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
@app.route('/api/upload-video', methods=['POST'])
@login_required
def api_upload_video():

    video_file = request.files.get('video_file')
    title = (request.form.get('title') or '').strip()
    description = (request.form.get('description') or '').strip()
    hashtags = (request.form.get('hashtags') or '').strip()

    if not video_file:
        return jsonify({
            "success": False,
            "message": "No se recibió ningún vídeo"
        }), 400

    if not allowed_file(video_file.filename):
        return jsonify({
            "success": False,
            "message": "Tipo de archivo no permitido"
        }), 400

    try:

        upload_folder = current_app.config.get(
            'UPLOAD_FOLDER',
            'static/uploads/videos'
        )

        os.makedirs(
            upload_folder,
            exist_ok=True
        )

        filename = secure_filename(
            video_file.filename
        )

        ext = filename.rsplit('.', 1)[1].lower()

        unique_filename = (
            f"{uuid.uuid4().hex}.{ext}"
        )

        file_path = os.path.join(
            upload_folder,
            unique_filename
        )

        video_file.save(file_path)

        new_video = Video(
            video_url=unique_filename,
            title=title,
            description=description,
            hashtags=hashtags,
            user_id=current_user.id
        )

        db.session.add(new_video)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Vídeo subido correctamente",
            "video_id": new_video.id,
            "video_url": unique_filename
        })

    except Exception as e:

        print(
            "❌ Error api_upload_video:",
            e
        )

        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500
    
@app.route(
    '/api/profile/<username>/opinions',
    methods=['GET']
)
def get_profile_opinions(
    username
):

    user = User.query.filter_by(
        username=username
    ).first()

    if not user:

        return jsonify({
            "success": False
        }), 404

    opinions = Opinion.query.filter_by(
        profile_user_id=user.id
    ).all()

    opinions_data = []

    for opinion in opinions:

        opinions_data.append({

            "id":
                opinion.id,

            "is_owner":
                current_user.is_authenticated
                and opinion.user_id
                == current_user.id,

            "text":
                opinion.text,

            "rating":
                opinion.rating,

            "username":
                opinion.user.name
                if opinion.user
                else "Usuario",

            "profile_picture":
                (
                    url_for(
                        'static',
                        filename=
                        opinion.user.profile_pic,
                        _external=True
                    )
                    if opinion.user
                    and opinion.user.profile_pic
                    else url_for(
                        'static',
                        filename=
                        'profile_pics/default.jpg',
                        _external=True
                    )
                ),

            "responses": [

                {
                    "id":
                        response.id,

                    "text":
                        response.text,

                    "username":
                        response.user.name
                        if response.user
                        else "Usuario",

                    "created_at":
                        response.created_at
                        .strftime(
                            '%Y-%m-%d %H:%M'
                        )
                }

                for response
                in opinion.responses
            ]
        })

    return jsonify({

        "success":
            True,

        "opinions":
            opinions_data
    })
@app.route(
    '/api/profile/<username>/opinions',
    methods=['POST']
)
@login_required
def create_opinion(
    username
):

    data = request.get_json()

    text = (
        data.get(
            'text',
            ''
        ).strip()
    )

    rating = data.get(
        'rating'
    )

    if not text:

        return jsonify({
            "success":
                False,
            "message":
                "La opinión es obligatoria"
        }), 400

    if rating is None:

        return jsonify({
            "success":
                False,
            "message":
                "El rating es obligatorio"
        }), 400

    profile_user = User.query.filter_by(
            username=username
        ).first()

    if not profile_user:

        return jsonify({
            "success":
                False
        }), 404

    opinion = Opinion(

            text=text,

            rating=int(
                rating
            ),

            user_id=
                current_user.id,

            profile_user_id=
                profile_user.id
        )

    db.session.add(
        opinion
    )

    db.session.commit()

    return jsonify({

        "success":
            True,

        "message":
            "Opinión creada"
    })

@app.route(
    '/api/opinion/<int:opinion_id>/reply',
    methods=['POST']
)
@login_required
def api_reply_opinion(
    opinion_id
):

    data = request.get_json()

    text = (
        data.get(
            'text',
            ''
        ).strip()
    )

    if not text:

        return jsonify({
            "success":
                False
        }), 400

    opinion = Opinion.query.get(
            opinion_id
        )

    if not opinion:

        return jsonify({
            "success":
                False
        }), 404

    response = OpinionResponse(

            text=text,

            opinion_id=
                opinion_id,

            user_id=
                current_user.id
        )

    db.session.add(
        response
    )

    db.session.commit()

    return jsonify({

        "success":
            True,

        "response": {

            "id":
                response.id,

            "text":
                response.text,

            "username":
                current_user.name
        }
    })

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

    response = OpinionResponse(
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

@app.route('/profile/<username>/followers')
def profile_followers(username):
    user = User.query.filter_by(username=username).first_or_404()
    followers = user.followers.all()

    return render_template(
        'followers.html',
        profile_user=user,
        users=followers,
        title="Seguidores"
    )


@app.route('/profile/<username>/following')
def profile_following(username):
    user = User.query.filter_by(username=username).first_or_404()
    following = user.followed.all()

    return render_template(
        'followers.html',
        profile_user=user,
        users=following,
        title="Siguiendo"
    )

@app.route('/opinion/<int:opinion_id>/responses', methods=['GET'])
def get_responses(opinion_id):
    # Obtener la opinión con el id proporcionado
    opinion = Opinion.query.get(opinion_id)
    
    if not opinion:
        return jsonify({'success': False, 'message': 'La opinión no existe'}), 404

    # Obtener las respuestas asociadas a esta opinión
    responses = OpinionResponse.query.filter_by(opinion_id=opinion_id).all()
    
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
    response = OpinionResponse.query.get(response_id)

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

@app.route('/products/create', methods=['GET', 'POST'])
@login_required
def create_product():
    form = CreateProductForm()

    # 👉 POST válido (incluye CSRF)
    if form.validate_on_submit():

        # 1️⃣ Crear producto (sin imágenes)
        product = Product(
            user_id=current_user.id,
            title=form.title.data,
            description=form.description.data,
            price=float(form.price.data),
            is_active=True,
        )

        db.session.add(product)
        db.session.commit()  # necesario para obtener product.id

        # 2️⃣ Guardar imágenes
        for image in form.images.data:
            if image and image.filename:
                filename = secure_filename(image.filename)
                print("PRODUCT_IMAGES_FOLDER =", app.config.get('PRODUCT_IMAGES_FOLDER'))
                print("Existe carpeta?", os.path.exists(app.config.get('PRODUCT_IMAGES_FOLDER')))
                image.save(os.path.join(app.config['PRODUCT_IMAGES_FOLDER'], filename))

                product_image = ProductImage(
                    product_id=product.id,
                    image=filename
                )
                db.session.add(product_image)

        db.session.commit()

        flash('Producto creado correctamente', 'success')
        return redirect(url_for('profile', username=current_user.username))

    # 👉 GET o POST inválido (errores de validación)
    return render_template('create_product.html', form=form)

@app.route('/profile/<username>/products')
def user_products(username):
    user = User.query.filter_by(username=username).first_or_404()

    products = Product.query.filter_by(
        user_id=user.id,
        is_active=True
    ).order_by(Product.created_at.desc()).all()

    return render_template(
        'products_grid.html',
        products=products,
        user=user
    )

@app.route('/products/<int:product_id>/view', methods=['POST'])
def product_view(product_id):
    product = Product.query.get_or_404(product_id)
    product.views += 1
    db.session.commit()
    return '', 204

@csrf.exempt
@app.route('/api/create-product', methods=['POST'])
@login_required
def api_create_product():

    try:

        print("\n========== CREATE PRODUCT ==========")
        print("USER:", current_user.id)
        print("FORM:", request.form)
        print("FILES:", request.files)

        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price', '0')

        print("TITLE:", title)
        print("PRICE:", price)

        if not title:
            return jsonify({
                'success': False,
                'message': 'El título es obligatorio'
            }), 400

        product = Product(
            user_id=current_user.id,
            title=title,
            description=description,
            price=float(price),
            is_active=True
        )

        db.session.add(product)
        db.session.commit()

        print("PRODUCT CREATED:", product.id)

        files = request.files.getlist('images')

        print("TOTAL IMAGES:", len(files))

        product_folder = app.config['PRODUCT_IMAGES_FOLDER']

        print("PRODUCT_IMAGES_FOLDER:", product_folder)

        os.makedirs(
            product_folder,
            exist_ok=True
        )

        print(
            "FOLDER EXISTS:",
            os.path.exists(product_folder)
        )

        for image in files:

            print("--------------------------------")
            print("IMAGE OBJECT:", image)
            print("FILENAME:", image.filename)

            if image and image.filename:

                filename = (
                    f"{uuid.uuid4().hex}_"
                    f"{secure_filename(image.filename)}"
                )

                save_path = os.path.join(
                    product_folder,
                    filename
                )

                print("SAVE PATH:", save_path)

                image.save(save_path)

                print("FILE EXISTS AFTER SAVE:",
                      os.path.exists(save_path))

                product_image = ProductImage(
                    product_id=product.id,
                    image=filename
                )

                db.session.add(product_image)

                print("DB IMAGE CREATED:",
                      filename)

        db.session.commit()

        print("PRODUCT COMMIT OK")
        print("===================================\n")

        return jsonify({
            'success': True,
            'product_id': product.id,
            'message': 'Producto creado correctamente'
        })

    except Exception as e:

        print("\n❌ ERROR CREATE PRODUCT")
        print(str(e))

        db.session.rollback()

        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@csrf.exempt
@app.route('/api/delete-product/<int:product_id>', methods=['POST'])
@login_required
def api_delete_product(product_id):

    product = Product.query.get_or_404(product_id)

    if product.user_id != current_user.id:
        return jsonify({
            "success": False,
            "message": "No autorizado"
        }), 403

    # borrar imágenes
    for image in product.images:

        try:
            image_path = os.path.join(
                app.config['PRODUCT_IMAGES_FOLDER'],
                image.image
            )

            if os.path.exists(image_path):
                os.remove(image_path)

        except Exception as e:
            print(e)

    ProductImage.query.filter_by(
        product_id=product.id
    ).delete()

    db.session.delete(product)
    db.session.commit()

    return jsonify({
        "success": True
    })
    
@app.route('/delete_video/<int:video_id>', methods=['POST'])
@login_required
def delete_video(video_id):

    video = Video.query.get(video_id)
    if not video:
        flash('El video no existe', 'error')
        return redirect(url_for('home'))

    if video.user_id != current_user.id:
        flash('No tienes permiso para eliminar este video', 'error')
        return redirect(url_for('home'))

    # Eliminar archivo físico
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], video.video_url)
    if os.path.exists(file_path):
        os.remove(file_path)

    # Eliminar de la BD
    db.session.delete(video)
    db.session.commit()

    flash('Video eliminado exitosamente', 'success')

    return redirect(url_for('profile', username=current_user.username))

def is_ios_request():
    ua = request.headers.get('User-Agent', '')
    return 'iPhone' in ua or 'iPad' in ua or 'iPod' in ua

@app.route("/premium")
def premium():
    if is_ios_request():
        return redirect(url_for("home"))
    return render_template("premium.html")


@app.route('/premium/success')
@login_required
def activate_premium():
    if is_ios_request():
        abort(403)

    current_user.is_premium = True
    db.session.commit()
    flash('¡Felicidades! Ahora eres usuario premium 🎉', 'success')
    return redirect(url_for('profile', username=current_user.username))


@app.route('/apple/verify', methods=['POST'])
@login_required
def verify_apple_purchase():
    data = request.get_json()
    transaction_id = data.get('transaction_id')

    if not transaction_id:
        return jsonify({'error': 'Missing transaction id'}), 400

    # Activar premium SOLO desde Apple
    current_user.is_premium = True
    current_user.premium_source = 'apple'
    current_user.apple_transaction_id = str(transaction_id)

    db.session.commit()

    return jsonify({'status': 'ok'})

@app.route('/logout')
def logout():
    session.pop("user_id", None)  # Elimina al usuario de la sesión
    flash("Has cerrado sesión exitosamente", "success")
    return redirect(url_for("login"))

@app.route('/delete-account', methods=['POST'])
@login_required
def delete_account():

    try:

        user = User.query.get(
            current_user.id
        )

        if not user:
            return jsonify({
                "success": False
            }), 404

        delete_user_and_related_data(
            user
        )

        logout_user()

        db.session.commit()

        session.clear()

        return jsonify({
            "success": True
        })

    except Exception as e:

        db.session.rollback()

        print(
            "ERROR AL ELIMINAR CUENTA:"
        )

        print(e)

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def delete_user_and_related_data(user):

    # ==========================
    # FOLLOWERS
    # ==========================

    db.session.execute(
        followers.delete().where(
            followers.c.follower_id == user.id
        )
    )

    db.session.execute(
        followers.delete().where(
            followers.c.followed_id == user.id
        )
    )

    # ==========================
    # LIKES
    # ==========================

    db.session.execute(
        likes_table.delete().where(
            likes_table.c.user_id == user.id
        )
    )

    # ==========================
    # VIDEOS
    # ==========================

    video_ids = [
        video.id
        for video in Video.query.filter_by(
            user_id=user.id
        ).all()
    ]

    if video_ids:

        db.session.execute(
            likes_table.delete().where(
                likes_table.c.video_id.in_(
                    video_ids
                )
            )
        )

        Comment.query.filter(
            Comment.video_id.in_(
                video_ids
            )
        ).delete(
            synchronize_session=False
        )

    Video.query.filter_by(
        user_id=user.id
    ).delete()

    # ==========================
    # COMMENTS
    # ==========================

    Comment.query.filter_by(
        user_id=user.id
    ).delete()

    # ==========================
    # OPINIONS
    # ==========================

    opinion_ids = [
        opinion.id
        for opinion in Opinion.query.filter(
            (Opinion.user_id == user.id) |
            (Opinion.profile_user_id == user.id)
        ).all()
    ]

    if opinion_ids:
        print("RESPONSE =", OpinionResponse)
        print("BASES =", OpinionResponse.__bases__)
        print("HAS QUERY =", hasattr(OpinionResponse, "query"))
        OpinionResponse.query.filter(
            OpinionResponse.opinion_id.in_(
                opinion_ids
            )
        ).delete(
            synchronize_session=False
        )

        Opinion.query.filter(
            Opinion.id.in_(
                opinion_ids
            )
        ).delete(
            synchronize_session=False
        )

    OpinionResponse.query.filter_by(
        user_id=user.id
    ).delete()

    # ==========================
    # BLOCKS
    # ==========================

    Block.query.filter_by(
        blocker_id=user.id
    ).delete()

    Block.query.filter_by(
        blocked_id=user.id
    ).delete()

    # ==========================
    # PRIVATE CHAT
    # ==========================

    conversation_ids = [
        c.id
        for c in Conversation.query.filter(
            (Conversation.user_id == user.id) |
            (Conversation.recipient_id == user.id)
        ).all()
    ]

    if conversation_ids:

        ChatMessage.query.filter(
            ChatMessage.conversation_id.in_(
                conversation_ids
            )
        ).delete(
            synchronize_session=False
        )

    Conversation.query.filter(
        (Conversation.user_id == user.id) |
        (Conversation.recipient_id == user.id)
    ).delete(
        synchronize_session=False
    )
    # ==========================
    # GROUPS
    # ==========================

    GroupMessage.query.filter_by(
        sender_id=user.id
    ).delete()

    GroupMember.query.filter_by(
        user_id=user.id
    ).delete(
        synchronize_session=False
    )

    Group.query.filter_by(
        owner_id=user.id
    ).delete(
        synchronize_session=False
    )

    # ==========================
    # PROJECTS
    # ==========================

    ProjectApplication.query.filter_by(
        applicant_id=user.id
    ).delete()

    Project.query.filter_by(
        user_id=user.id
    ).delete()

    # ==========================
    # JOBS
    # ==========================

    JobApplication.query.filter_by(
        applicant_id=user.id
    ).delete()

    Job.query.filter_by(
        user_id=user.id
    ).delete()

    # ==========================
    # PRODUCTS
    # ==========================

    product_ids = [
        p.id
        for p in Product.query.filter_by(
            user_id=user.id
        ).all()
    ]

    if product_ids:

        ProductImage.query.filter(
            ProductImage.product_id.in_(
                product_ids
            )
        ).delete(
            synchronize_session=False
        )

    Product.query.filter_by(
        user_id=user.id
    ).delete()

    # ==========================
    # CV
    # ==========================

    UserCV.query.filter_by(
        user_id=user.id
    ).delete()

    # ==========================
    # TOKENS
    # ==========================

    UserToken.query.filter_by(
        user_id=user.id
    ).delete()

    # ==========================
    # REPORTS
    # ==========================

    Report.query.filter(
        (Report.reporter_id == user.id) |
        (Report.reported_user_id == user.id)
    ).delete(
        synchronize_session=False
    )

    # ==========================
    # OFFERS
    # ==========================

    OfferUsage.query.filter_by(
        user_id=user.id
    ).delete()

    # ==========================
    # USER
    # ==========================

    db.session.delete(user)

@app.route(
    '/api/delete-account',
    methods=['POST']
)
@login_required
def api_delete_account():

    try:

        user = User.query.get(
            current_user.id
        )

        if not user:
            return jsonify({
                "success": False
            }), 404

        delete_user_and_related_data(
            user
        )

        logout_user()

        db.session.commit()

        session.clear()

        return jsonify({
            "success": True
        })

    except Exception as e:

        db.session.rollback()

        print(
            "DELETE ACCOUNT ERROR:"
        )

        print(e)

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


    
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

@app.route('/report_video/<int:video_id>', methods=['POST'])
@login_required
def report_video(video_id):
    form = ReportForm()

    if not form.validate_on_submit():
        return jsonify({"success": False, "error": "CSRF inválido"}), 400

    try:
        video = Video.query.get(video_id)

        # 🔗 URL del video
        video_url = url_for('view_video', video_id=video_id, _external=True)

        # 🔥 guardar en DB
        new_report = Report(
            reporter_id=current_user.id,
            reported_user_id=video.user_id if video else None,
            video_id=video_id,
            reason=request.form.get("reason")
        )

        db.session.add(new_report)
        db.session.commit()

        # 🔥 EMAIL
        message = f"""
🚩 NUEVO REPORTE

👤 Usuario que reporta: {current_user.username}
🎥 Video ID: {video_id}
📍 URL: {video_url}
👤 Usuario reportado: {video.user.username if video else "Desconocido"}

📝 Motivo:
{request.form.get("reason")}
"""

        msg = MIMEText(message)
        msg["Subject"] = "🚩 Nuevo reporte en MAZO"
        msg["From"] = "mazo.app.es@gmail.com"
        msg["To"] = "mazo.app.es@gmail.com"

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.ehlo()

        # 🔥 AQUÍ VA TU APP PASSWORD
        server.login("mazo.app.es@gmail.com", "wuuvsqlospvdtuzw")

        server.send_message(msg)
        server.quit()

        return jsonify({"success": True})

    except Exception as e:
        print("❌ ERROR REPORT:", e)
        return jsonify({"success": False}), 500

@app.route('/report_user/<int:user_id>', methods=['POST'])
@login_required
def report_user(user_id):
    form = ReportForm()

    if not form.validate_on_submit():
        return jsonify({"success": False, "error": "CSRF inválido"}), 400

    try:
        user = User.query.get(user_id)

        # 🔗 URL del perfil
        profile_url = url_for('profile', username=user.username, _external=True) if user else "N/A"

        # 🔥 guardar en DB
        new_report = Report(
            reporter_id=current_user.id,
            reported_user_id=user_id,
            video_id=None,
            reason=request.form.get("reason")
        )

        db.session.add(new_report)
        db.session.commit()

        # 🔥 EMAIL (MISMO FORMATO QUE VIDEO)
        message = f"""
🚩 NUEVO REPORTE

👤 Usuario que reporta: {current_user.username}
👤 Usuario reportado: {user.username if user else "Desconocido"}
📍 Perfil: {profile_url}

📝 Motivo:
{request.form.get("reason")}
"""

        msg = MIMEText(message)
        msg["Subject"] = "🚩 Nuevo reporte en MAZO"
        msg["From"] = "mazo.app.es@gmail.com"
        msg["To"] = "mazo.app.es@gmail.com"

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.ehlo()

        server.login("mazo.app.es@gmail.com", "wuuvsqlospvdtuzw")

        server.send_message(msg)
        server.quit()

        return jsonify({"success": True})

    except Exception as e:
        print("❌ ERROR REPORT USER:", e)
        return jsonify({"success": False}), 500
    
    
@app.route('/block_user/<int:user_id>', methods=['POST'])
@login_required
def block_user(user_id):
    form = BlockForm()

    # 🔒 Validar CSRF correctamente
    if not form.validate_on_submit():
        return jsonify({
            "success": False,
            "error": "CSRF token inválido"
        }), 400

    try:
        # 🚫 No permitir bloquearse a sí mismo
        if user_id == current_user.id:
            return jsonify({
                "success": False,
                "error": "No puedes bloquearte a ti mismo"
            }), 400

        # 🔍 Verificar que el usuario existe
        user_to_block = User.query.get(user_id)
        if not user_to_block:
            return jsonify({
                "success": False,
                "error": "Usuario no encontrado"
            }), 404

        # 🔍 Comprobar si ya está bloqueado
        existing_block = Block.query.filter_by(
            blocker_id=current_user.id,
            blocked_id=user_id
        ).first()

        if existing_block:
            return jsonify({
                "success": True,
                "message": "Usuario ya bloqueado"
            })

        # ✅ Crear bloqueo
        new_block = Block(
            blocker_id=current_user.id,
            blocked_id=user_id
        )

        db.session.add(new_block)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Usuario bloqueado"
        })

    except Exception as e:
        print("❌ ERROR EN BLOCK_USER:", e)

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/blocked_users')
@login_required
def blocked_users():
    block_form = BlockForm()
    unblock_form = UnblockForm()

    blocked_users = db.session.query(User).join(
        Block, Block.blocked_id == User.id
    ).filter(
        Block.blocker_id == current_user.id
    ).all()

    return render_template(
        "blocked_users.html",
        blocked_users=blocked_users,
        block_form=block_form,
        unblock_form = unblock_form,
    )

@app.route('/unblock_user/<int:user_id>', methods=['POST'])
@login_required
def unblock_user(user_id):
    form = UnblockForm()
    try:
        block = Block.query.filter_by(
            blocker_id=current_user.id,
            blocked_id=user_id
        ).first()

        if not block:
            return jsonify({"success": False, "error": "No existe bloqueo"}), 404

        db.session.delete(block)
        db.session.commit()

        return jsonify({"success": True})

    except Exception as e:
        print("❌ ERROR UNBLOCK:", e)
        return jsonify({"success": False}), 500

@app.route(
    '/api/blocked-users',
    methods=['GET']
)
@login_required
def api_blocked_users():

    blocked_users = (
        db.session.query(User)
        .join(
            Block,
            Block.blocked_id == User.id
        )
        .filter(
            Block.blocker_id == current_user.id
        )
        .all()
    )

    return jsonify({

        "success": True,

        "users": [

            {
                "id":
                    user.id,

                "username":
                    user.username,

                "name":
                    user.name,

                "profile_picture":
                    (
                        url_for(
                            'static',
                            filename=user.profile_pic,
                            _external=True
                        )
                        if user.profile_pic
                        else url_for(
                            'static',
                            filename='profile_pics/default.jpg',
                            _external=True
                        )
                    )
            }

            for user
            in blocked_users
        ]
    })

@app.route(
    '/api/unblock-user/<int:user_id>',
    methods=['POST']
)
@login_required
def api_unblock_user(user_id):

    block = Block.query.filter_by(
        blocker_id=current_user.id,
        blocked_id=user_id
    ).first()

    if not block:

        return jsonify({
            "success": False
        }), 404

    db.session.delete(block)
    db.session.commit()

    return jsonify({
        "success": True
    })
@app.route(
    '/api/change-password',
    methods=['POST']
)
@login_required
def api_change_password():

    data = request.get_json()

    current_password = data.get(
        "current_password",
        ""
    )

    new_password = data.get(
        "new_password",
        ""
    )

    if not current_user.check_password(
        current_password
    ):

        return jsonify({

            "success": False,

            "message":
                "Contraseña actual incorrecta"
        }), 400

    current_user.set_password(
        new_password
    )

    db.session.commit()

    return jsonify({

        "success": True,

        "message":
            "Contraseña actualizada"
    })
   
@app.route('/support')
def support():
    return render_template('support.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')




