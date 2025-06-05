from flask import Flask, render_template, request, redirect, g, url_for, flash, session, send_from_directory,jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, join_room, leave_room, send
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import RequestEntityTooLarge
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, Optional, NumberRange, Length
from sqlalchemy.orm import backref
import os 
import mimetypes
from flask_cors import CORS
import subprocess
from flask_migrate import Migrate
from flask_login import login_required, current_user, UserMixin, LoginManager, login_user
from flask_wtf.csrf import CSRFProtect, CSRFError, validate_csrf
from sqlalchemy.orm.attributes import InstrumentedAttribute
import logging
from datetime import datetime
from jinja2 import environment
import uuid 
import time
import base64
from flask_wtf.file import FileField, FileAllowed
from flask_mail import Mail, Message as Mailmessage
from itsdangerous import URLSafeTimedSerializer
from email.header import Header


app = Flask(__name__)
app.config['ENV'] = 'production'
app.config['DEBUG'] = False
app.config["SECRET_KEY"] = "AOM11091950"
app.config["WTF_CSRF_ENABLED"] = True
app.config['WTF_CSRF_TIME_LIMIT'] = None  # Token CSRF nunca expira (solo para desarrollo)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'mazo.app.es@gmail.com'
app.config['MAIL_PASSWORD'] = 'wuuvsqlospvdtuzw'  # sin espacios
app.config['MAIL_DEFAULT_SENDER'] = 'mazo.app.es@gmail.com'


#Configuramos la base de datos 
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("SQLALCHEMY_DATABASE_URI", "sqlite:///mazo.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
CORS(app)
csrf = CSRFProtect(app)
csrf.init_app(app)
logging.basicConfig(level=logging.DEBUG)

mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)


# Configuraciones para el directorio de archivos
UPLOAD_FOLDER = 'static/uploads/videos'
CHAT_UPLOAD_FOLDER = 'static/chat_uploads'
THUMBNAIL_FOLDER = "static/chat_uploads/thumbnails"
PROFILE_PICS_FOLDER = 'static/profile_pics'  # <--- Añadido

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'webm', 'mov', 'pdf', 'docx', 'pptx', 'avi', 'mpg'}
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB

for folder in [UPLOAD_FOLDER, CHAT_UPLOAD_FOLDER, PROFILE_PICS_FOLDER]:  # <--- Incluido aquí
    if not os.path.exists(folder):
        os.makedirs(folder)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CHAT_UPLOAD_FOLDER'] = CHAT_UPLOAD_FOLDER
app.config['PROFILE_PICS_FOLDER'] = PROFILE_PICS_FOLDER  # <--- Configuración final


migrate = Migrate(app, db)

@app.route('/security')
def seguridad():
    return render_template('seguridad.html')

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

#Tabla intermedia para los likes
likes_table = db.Table (
    'likes',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True ),
    db.Column('video_id', db.Integer, db.ForeignKey('videos.id'), primary_key=True)
)

class Video(db.Model):
    __tablename__ = 'videos'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    video_url = db.Column(db.String(200), nullable=False)
    hashtags = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    comments_count = db.Column(db.Integer, default=0)
    is_intro = db.Column(db.Boolean, default=False)


    #Relación con el usuario
    user = db.relationship('User', backref='videos_uploaded', lazy=True)

    #Relación con los comentarios
    comments = db.relationship('Comment', back_populates='video', cascade='all, delete-orphan')

    #Relación con los likes
    liked_by = db.relationship(
        'User',
        secondary=likes_table,
        backref='liked_videos', 
        lazy='subquery'
    )
    @property
    def like_count(self):
            print(type(Video.liked_by))
            print(Video.liked_by)
            return len(self.liked_by) if self.liked_by else 0

    
    def __repr__(self):
        return f'<Video {self.title}>'

followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('followed_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)

@app.route('/privacy')
def privacy_policy():
    return render_template('privacy.html', current_date="4 de junio de 2025")

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(300), nullable=False)
    profile_pic = db.Column(db.String(100), nullable=True)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20), nullable=True)
    company = db.Column(db.String(100), nullable=True)
    profession = db.Column(db.String(100), nullable=True)
    description = db.Column(db.String(300), nullable=True)  # Descripción personal opcional (máx 300)
    location = db.Column(db.String(200), nullable=True)      # Ubicación opcional
    is_verified = db.Column(db.Boolean, default=False)

    comments = db.relationship('Comment', back_populates='user')

    # Seguidores y seguidos
    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=backref('followers', lazy='dynamic'),
        lazy='dynamic'
    )

    def __repr__(self):
        return f'<User {self.username}>'

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0

    def is_followed_by(self, user):
        return self.followers.filter(followers.c.follower_id == user.id).count() > 0
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

@app.before_request
def load_user():
    user_id = session.get('user_id')  # Verifica el ID del usuario en la sesión
    if user_id:
        g.user = User.query.get(user_id)  # Carga el usuario desde la base de datos
    else:
        g.user = None  # Si no hay usuario en sesión, asigna None

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    # Devuelve un error JSON si la solicitud es AJAX
    if request.is_json:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    # Redirige a la vista de inicio de sesión para solicitudes normales
    return redirect(url_for('login'))

@app.route('/')
def inicio():
    if current_user.is_authenticated:
        return redirect(url_for('home'))  # o tu ruta principal de videos
    return render_template('inicio.html')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired()])
    company = StringField('Empresa (Opcional)', validators=[Optional()])
    profession = StringField('Profesión (Opcional)', validators=[Optional()])
    description = TextAreaField('Descripción (Opcional)', validators=[Optional(), Length(max=500)])
    location = StringField('Ubicación (Opcional)', validators=[Optional()])
    profile_pic = FileField('Foto de perfil (opcional)', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'webp'])])

@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        name = request.form.get("name", "").strip()
        username = form.username.data.strip()
        phone = request.form.get("phone", "").strip()
        email = form.email.data.strip()
        password = form.password.data.strip()
        confirm_password = form.confirm_password.data.strip()
        company = form.company.data.strip() or None
        profession = form.profession.data.strip() or None
        description = form.description.data.strip() or None
        location = form.location.data.strip() or None

        if password != confirm_password:
            flash("Las contraseñas no coinciden", "error")
            return render_template("register.html", form=form)

        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash("El nombre de usuario o correo ya está en uso.", "error")
            return render_template("register.html", form=form)

        profile_picture = form.profile_pic.data
        filename = None
        if profile_picture:
            filename = secure_filename(profile_picture.filename)
            picture_path = os.path.join(app.config["PROFILE_PICS_FOLDER"], filename)
            profile_picture.save(picture_path)

        new_user = User(
            name=name,
            username=username,
            phone=phone,
            email=email,
            password=generate_password_hash(password),
            company=company,
            profession=profession,
            description=description,
            location=location,
            profile_pic=f"profile_pics/{filename}" if filename else "profile_pics/default.jpg"
        )
        db.session.add(new_user)
        db.session.commit()

        send_verification_email(new_user.email)
        flash('Registro exitoso. Verifica tu email para activar tu cuenta.', 'info')

        return redirect(url_for("login"))

    return render_template("register.html", form=form, user=None)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST': 
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password: 
            flash('Por favor completa todos los campos.', 'error')
            return render_template('login.html')

        # Buscar el usuario en la base de datos
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):  # Verifica la contraseña
            login_user(user)  # Inicia sesión con Flask-Login
            
            # Guardar tanto el ID como el username en la sesión
            session["user_id"] = user.id  
            session["username"] = user.username  # <-- Agregado

            # Verificar si el username se guardó correctamente en la sesión
            print(f"Usuario {user.username} guardado en la sesión.")
            
            flash(f"¡Bienvenido, {user.username}!", "success")
            return redirect(url_for("home"))
        
        flash("Usuario o contraseña incorrectos", "error")

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

@app.route('/confirm/<token>', endpoint='confirm_email')
def confirm_email(token):
    try:
        email = serializer.loads(token, salt='email-confirm', max_age=3600)
    except:
        flash('El enlace de verificación es inválido o ha expirado.', 'danger')
        return redirect(url_for('login'))

    user = User.query.filter_by(email=email).first()
    if user:
        user.is_verified = True
        db.session.commit()
        flash('Correo verificado con éxito. ¡Ya puedes usar todas las funciones!', 'success')
    else:
        flash('Usuario no encontrado.', 'error')

    return redirect(url_for('login'))

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

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)

    replies = db.relationship(
        'Comment',
        back_populates='parent',
        cascade='all, delete-orphan',
        lazy=True
    )
    parent = db.relationship(
        'Comment',
        back_populates='replies',
        remote_side=[id]
    )

    is_deleted = db.Column(db.Boolean, default=False)  # NUEVO

    user = db.relationship('User', back_populates='comments')
    video = db.relationship('Video', back_populates='comments')

  # Asegúrate de importar si aún no está

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

    if 'user_id' in session:
        user = User.query.get(session['user_id'])

        # ⚠️ Validar que user exista
        if user:
            chats = get_user_chats(user.id)

    # Obtener video introductorio y evitar duplicado en otros videos
    intro_video = Video.query.filter_by(is_intro=True).first()
    
    if intro_video:
        other_videos = Video.query.filter(Video.id != intro_video.id).order_by(Video.id.desc()).all()
        videos = [intro_video] + other_videos
    else:
        videos = Video.query.order_by(Video.id.desc()).all()

    return render_template('home.html', user=user, videos=videos, chats=chats if user else [])

@app.route('/video/<int:video_id>')
def video(video_id):
    video = Video.query.get_or_404(video_id)
    return render_template('video.html', video=video)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q','').strip()
    location = request.args.get('location','').strip()

    if query:
        # Búsqueda de videos, perfiles y profesiones
        videos = Video.query.join(User).filter(
            (Video.title.ilike(f"%{query}%")) | 
            (Video.description.ilike(f"%{query}%")) |
            (User.name.ilike(f"%{query}%")) | 
            (User.company.ilike(f"%{query}%")) | 
            (User.profession.ilike(f"%{query}%")) 
        ).order_by(Video.id.desc()).all()

        #Búsqueda de usuarios (perfiles)
        users = User.query.filter(
            (User.name.ilike(f"%{query}%")) |
            (User.company.ilike(f"%{query}%")) |
            (User.profession.ilike(f"%{query}%")) |
            (User.location.ilike(f"%{query}%"))
        ).all()

        for video in videos:
            print(f"Video ID: {video.id}, URL: {video.video_url}")  

        flash(f"Resultados para: '{query}'", "info")
    else:
        videos, users = [], []
    return render_template('search.html', videos=videos, users=users, query=query)

@app.route('/search_suggestions', methods=['GET'])
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
    
class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id])
    recipient = db.relationship('User', foreign_keys=[recipient_id])

    def get_other_user(self, user_id):
        if self.user_id == user_id:
            return self.recipient
        else:
            return self.user 

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=True)  # Puede ser un mensaje de texto o estar vacío si es un archivo
    file_url = db.Column(db.String(255), nullable=True)  # Ruta del archivo adjunto
    thumbnail_url = db.Column(db.String(255), nullable=True)  # Nueva columna para la miniatura del archivo
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

    conversation = db.relationship('Conversation', backref=db.backref('messages', lazy=True))
    sender = db.relationship('User', foreign_keys=[sender_id])

@socketio.on('join')
def handle_join(data):
    room = data.get('room')
    if room:
        join_room(room)
        print(f"✅ Usuario unido a la sala: {room}")
    else:
        print("❌ Error: No se especificó una sala.")

def get_user_chats(user_id):
    conversations = Conversation.query.filter(
        (Conversation.user_id == user_id) | (Conversation.recipient_id == user_id)
    ).all()

    chat_data = []
    for conv in conversations:
        other_user = conv.get_other_user(user_id)
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
def chats():
    if 'user_id' not in session:
        flash('Por favor inicia sesión para acceder a tus chats', 'error')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    chats = get_user_chats(user_id)

    return render_template('chat_list.html', username=session.get('username'), chats=chats)

@app.route('/chat/<recipient_username>')
def chat_with_user(recipient_username):
    if 'user_id' not in session:
        flash('Debes iniciar sesión para acceder al chat', 'error')
        return redirect(url_for('login'))

    sender = User.query.get(session['user_id'])
    recipient = User.query.filter_by(username=recipient_username).first()

    if not recipient:
        flash('Usuario no encontrado', 'error')
        return redirect(url_for('home'))

    # Buscar la conversación entre los dos usuarios
    conversation = Conversation.query.filter(
        ((Conversation.user_id == sender.id) & (Conversation.recipient_id == recipient.id)) |
        ((Conversation.user_id == recipient.id) & (Conversation.recipient_id == sender.id))
    ).first()

    if conversation:
        # Marcar como leídos los mensajes del otro usuario
        Message.query.filter(
            Message.conversation_id == conversation.id,
            Message.sender_id != sender.id,  # Solo marcar los mensajes del otro usuario
            Message.is_read == False
        ).update({'is_read': True})
        
        db.session.commit()  # Guardar cambios en la base de datos

    messages = Message.query.filter_by(conversation_id=conversation.id).order_by(Message.timestamp).all()

    return render_template('chat.html', recipient=recipient, username=session.get('username'), messages=messages)

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
    """Guarda el archivo en la carpeta correspondiente si es válido."""
    file = request.files.get('file')
    folder = request.form.get('folder', app.config['CHAT_UPLOAD_FOLDER'])  # Carpeta por defecto
    filename = request.form.get('filename')

    if not file:
        return jsonify({"error": "No se recibió ningún archivo"}), 400

    if not os.path.exists(folder):
        os.makedirs(folder)

    if hasattr(file, 'filename'):
        filename = file.filename

        # Validar si la extensión es permitida
        if allowed_file(filename):
            ext = os.path.splitext(filename)[1].lower()
            new_filename = secure_filename(f"file_{int(time.time())}{ext}")
            file_url = os.path.join(folder, new_filename).replace("\\", "/")  # Normalizar la ruta

            try:
                # Verificar tamaño del archivo
                file.seek(0, os.SEEK_END)
                file_size = file.tell()
                max_size = app.config['MAX_CONTENT_LENGTH']

                if file_size > max_size:
                    return jsonify({"error": f"El archivo es demasiado grande. Máximo permitido: {max_size / (1024 * 1024)} MB."}), 400

                file.seek(0)
                file.save(file_url)

                thumbnail_url = None  # Solo se genera para videos

                # Generar miniatura si es un video
                if ext in ['.mp4', '.mov', '.webm']:
                    thumbnail_folder = os.path.join(folder, 'thumbnails')
                    if not os.path.exists(thumbnail_folder):
                        os.makedirs(thumbnail_folder)

                    thumbnail_filename = f"{os.path.splitext(new_filename)[0]}.png"
                    thumbnail_url = os.path.join(thumbnail_folder, thumbnail_filename).replace("\\", "/")

                    try:
                        subprocess.run([
                            'ffmpeg', '-i', file_url, '-vframes', '1', '-an', '-s', '320x240', thumbnail_url
                        ], check=True)

                        thumbnail_url = f"chat_uploads/thumbnails/{thumbnail_filename}"
                        print(f"✅ Miniatura generada: {thumbnail_url}")

                    except subprocess.CalledProcessError as e:
                        print(f"⚠️ Error al generar miniatura con FFmpeg: {e}")

                return jsonify({
                    "success": True,
                    "file_url": file_url,
                    "thumbnail_url": thumbnail_url
                }), 200

            except Exception as e:
                return jsonify({"error": f"Error al guardar archivo: {e}"}), 500
        else:
            return jsonify({"error": "El archivo no tiene una extensión permitida"}), 400
    else:
        return jsonify({"error": "El objeto recibido no es un archivo válido"}), 400
    
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

@socketio.on('message')
def handle_message(data):
    print("Recibiendo mensaje de WebSocket...")
    print("Datos recibidos:", data)

    if 'username' not in data or 'recipient' not in data or 'message' not in data:
        print("❌ Error: Faltan datos en el mensaje.")
        return jsonify({'error': 'Faltan datos en el mensaje.'}), 400

    sender = data['username']
    recipient = data['recipient']
    message = data['message']
    file = data.get('file')  # Puede ser None, Base64 o una ruta
    filename = data.get('filename')  # Nombre del archivo si viene en Base64

    if not message and not file:
        print("❌ Error: El mensaje está vacío y no hay archivo adjunto.")
        return jsonify({'error': 'El mensaje está vacío y no hay archivo adjunto.'}), 400

    file_path = None
    thumbnail_path = None  # 🔹 Para almacenar la miniatura

    # 🔹 Procesamiento del archivo si existe
    if file:
        print(f"📂 Tipo de archivo recibido: {type(file)}")

        if isinstance(file, str):  # Puede ser Base64 o una ruta guardada
            if file.startswith("static/chat_uploads/"):  # 📌 Verifica si ya está guardado
                file_path = file
                print(f"✅ Archivo ya guardado en: {file_path}")
            elif file.startswith("data:") and "," in file:  # 📌 Detectar Base64 correctamente
                print("📂 Recibiendo archivo como Base64")
                if filename:
                    try:
                        file_path = handle_small_file(file, filename)
                    except Exception as e:
                        print(f"❌ Error al procesar el archivo Base64: {e}")
                        return jsonify({'error': f'Error al procesar el archivo Base64: {e}'}), 400
                else:
                    print("❌ Error: El archivo Base64 no tiene nombre.")
            else:
                print("❌ Error: Formato de archivo desconocido.")
        elif hasattr(file, 'filename'):  # Si es un objeto FileStorage
            print(f"📂 Recibiendo archivo con nombre: {file.filename}")
            file_path = upload_file(file, CHAT_UPLOAD_FOLDER)  # 📌 Asegurar que se guarda en chat_uploads

        # 🔹 Si el archivo es un video, generar miniatura
        if file_path and file_path.lower().endswith(('.mp4', '.webm', '.mov', '.avi', '.mpg')):
            filename = os.path.basename(file_path)
            thumbnail_path = os.path.join(THUMBNAIL_FOLDER, f"thumb_{filename}.png")
            generate_thumbnail(file_path, thumbnail_path)
            thumbnail_path = thumbnail_path.replace("\\", "/")  # 🔹 Normalizar la URL

    print(f"📨 Mensaje de {sender} para {recipient}: {message}, Archivo adjunto: {file_path}, Miniatura: {thumbnail_path}")

    # 🔹 Buscar usuarios en la base de datos
    sender_user = User.query.filter_by(username=sender).first()
    recipient_user = User.query.filter_by(username=recipient).first()

    if sender_user and recipient_user:
        conversation = Conversation.query.filter(
            ((Conversation.user_id == sender_user.id) & (Conversation.recipient_id == recipient_user.id)) |
            ((Conversation.user_id == recipient_user.id) & (Conversation.recipient_id == sender_user.id))
        ).first()

        if not conversation:
            conversation = Conversation(user_id=sender_user.id, recipient_id=recipient_user.id)
            db.session.add(conversation)
            db.session.commit()
            print(f"🆕 Se ha creado una nueva conversación entre {sender} y {recipient}")

        # 🔹 Guardar mensaje en la base de datos con miniatura
        new_message = Message(
            sender_id=sender_user.id,
            conversation_id=conversation.id,
            content=message if message else None,
            file_url=file_path,
            thumbnail_url=thumbnail_path  # 🔹 Guardar la miniatura en la BD
        )

        db.session.add(new_message)
        db.session.commit()

        print(f"✅ Mensaje guardado en la base de datos con ID: {new_message.id}")

        # 🔹 Emitir el mensaje a los clientes conectados
        room = f"chat_{sorted([sender, recipient])[0]}_{sorted([sender, recipient])[1]}"

        socketio.emit('receive_message', {
            'username': sender,
            'message': message,
            'message_id': new_message.id,
            'file_url': file_path if file_path else "",
            'thumbnail_url': thumbnail_path if thumbnail_path else "",
        }, room=room, include_self=True)

        print(f"✅ Mensaje emitido a la sala {room}")

        socketio.emit('new_message', {
            'conversation_id': conversation.id,
            'sender': sender
        }, room=recipient_user.username)

        return jsonify({'success': True, 'file_url': file_path, 'thumbnail_url': thumbnail_path}), 200

    else:
        print(f"❌ Error: Usuario {sender} o {recipient} no encontrado en la base de datos.")
        return jsonify({'error': 'Usuario no encontrado.'}), 400

#Editar el mensaje
@socketio.on('edit_message')
def handle_edit_message(data):
    message_id = data.get('message_id')
    new_content = data.get('new_content')

    if not message_id or not new_content:
        print("Error: Faltan datos para editar el mensaje.")
        return
    
    message = Message.query.get(message_id)
    if message and message.sender_id == session.get('user_id'):
        message.content = new_content
        db.session.commit()

        # Emitir evento para actualizar el mensaje en el frontend
        socketio.emit('message_edited', {
            'message_id': message_id,
            'new_message': new_content,
            'username': message.sender.username
        }, to=f"chat_{message.conversation_id}")

        print(f"Mensaje {message_id} editado correctamente.")
    else:
        print("Error: No se encontró el mensaje o el usuario no tiene permisos.")

# Evento para eliminar el mensaje
@socketio.on('delete_message')
def handle_delete_message(data):
    message_id = data.get('message_id')

    if not message_id:
        print("Error: Faltan datos para eliminar el mensaje.")
        return 
    
    message = Message.query.get(message_id)
    if message and message.sender_id == session.get('user_id'):
        conversation_id = message.conversation_id
        db.session.delete(message)
        db.session.commit()

        # Emitir evento para eliminar el mensaje en el frontend
        socketio.emit('message_deleted', {
            'message_id': message_id
        }, to=f"chat_{conversation_id}")

        print(f"Mensaje {message_id} eliminado correctamente.")
    else:
        print("Error: No se encontró el mensaje o el usuario no tiene permisos.")

@socketio.on('share_video')
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

@app.route('/chat/<int:recipient_id>', methods=['GET', 'POST'])
def send_message(recipient_id):
    if 'user_id' not in session:
        flash('Por favor inicia sesión para acceder al chat', 'error')
        return redirect(url_for('login'))

    sender = User.query.get(session['user_id'])
    recipient = User.query.get_or_404(recipient_id)

    # Buscar la conversación existente entre el usuario y el destinatario
    conversation = Conversation.query.filter(
        ((Conversation.user_id == sender.id) & (Conversation.recipient_id == recipient.id)) |
        ((Conversation.user_id == recipient.id) & (Conversation.recipient_id == sender.id))
    ).first()

    if not conversation:
        # Si no existe la conversación, crear una nueva
        conversation = Conversation(user_id=sender.id, recipient_id=recipient.id)
        db.session.add(conversation)
        db.session.commit()

    # Si se está enviando un mensaje, procesarlo
    if request.method == 'POST':
        message_content = request.form.get('message')
        if message_content:
            new_message = Message(
                conversation_id=conversation.id,
                sender_id=sender.id,
                content=message_content,
                is_read=False
            )
            db.session.add(new_message)
            db.session.commit()

            # Redirigir de nuevo al chat con el nuevo mensaje
            return redirect(url_for('send_message', recipient_id=recipient.id))

    # Obtener todos los mensajes de la conversación
    messages = Message.query.filter_by(conversation_id=conversation.id).order_by(Message.timestamp).all()

    return render_template('chat.html', username=session.get('username'), recipient=recipient, messages=messages, conversation_id=conversation.id)

class OpinionForm(FlaskForm):
    opinion_text = TextAreaField('Opinión', validators=[DataRequired()])
    rating = IntegerField('Puntuación', validators=[DataRequired(), NumberRange(min=0, max=10)])

class Opinion(db.Model):
    __tablename__ = 'opinions'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    rating = db.Column(db.Integer, nullable=False)

    # Usuario que deja la opinión
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('User', foreign_keys=[user_id], backref='opinions')

    # Usuario que recibe la opinión
    profile_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    profile_user = db.relationship('User', foreign_keys=[profile_user_id], backref='received_opinions')

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

@app.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        company = request.form.get("company", "").strip() or None
        profession = request.form.get("profession", "").strip() or None
        description = request.form.get("description", "").strip() or None
        location = request.form.get("location", "").strip() or None
        profile_pic = request.files.get("profile_pic")
        email = request.form.get("email", "").strip()

        current_user.name = name
        current_user.company = company
        current_user.profession = profession
        current_user.description = description
        current_user.location = location
        current_user.email = email

        if profile_pic and profile_pic.filename != "":
            filename = secure_filename(profile_pic.filename)
            path = os.path.join(app.config["PROFILE_PICS_FOLDER"], filename)
            profile_pic.save(path)
            current_user.profile_pic = f"profile_pics/{filename}"

        db.session.commit()
        flash("Perfil actualizado con éxito.", "success")
        return redirect(url_for("profile", username=current_user.username))

    return render_template("edit_profile.html", user=current_user)


@app.after_request
def add_security_headers(response):
    if request.path.startswith('/static') or request.path.startswith('/uploads'):
        return response  # No agregar cabeceras para estos archivos
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
    response.headers['Cross-Origin-Embedder-Policy'] = 'require-corp'
    return response

# 🔍 Función para verificar si el archivo tiene una extensión permitidadef allowed_file(filename):
    """Verifica si la extensión del archivo es válida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/uploads/videos/<filename>')
def uploaded_file(filename):
    return send_from_directory('static/uploads/videos', filename)

@app.route('/upload', methods=['POST', 'GET'])
def upload():
    if 'user_id' not in session:
        flash('Debes iniciar sesión para subir videos.', 'error')
        return redirect(url_for('login'))

    if request.method == 'GET':
        return render_template('upload.html')

    if request.method == 'POST':
        print("➡️ Iniciando proceso de subida...")

        try:
            validate_csrf(request.form.get('csrf_token'))
        except Exception as e:
            print("❌ CSRF inválido:", e)
            flash('CSRF inválido', 'error')
            return redirect(url_for('upload'))

        video_file = request.files.get('video_file')
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        hashtags = request.form.get('hashtags', '').strip()

        if not video_file:
            print("❌ No se recibió ningún archivo")
            flash('Selecciona un video válido.', 'error')
            return redirect(url_for('upload'))

        if not allowed_file(video_file.filename):
            print("❌ Tipo de archivo no permitido")
            flash('Tipo de archivo no permitido.', 'error')
            return redirect(url_for('upload'))

        try:
            # Crear un nombre único
            file_extension = video_file.filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
            file_path = os.path.join('static/uploads/videos', unique_filename)

            # Guardar archivo local
            video_file.save(file_path)
            print(f"✅ Video guardado localmente en {file_path}")

            # Guardar en base de datos
            new_video = Video(
                video_url=unique_filename,  # Solo el nombre del archivo
                title=title,
                description=description,
                hashtags=hashtags,
                user_id=session['user_id']
            )
            db.session.add(new_video)
            db.session.commit()
            print("✅ Video registrado en la base de datos")

        except Exception as e:
            print("❌ Error guardando el archivo:", e)
            flash('Error al subir el video.', 'error')
            return redirect(url_for('upload'))

        flash('¡Video subido con éxito!', 'success')
        return redirect(url_for('home'))

@app.route('/api/videos', methods=['GET'])
def get_videos():
    videos = Video.query.all()
    video_data = [{"video_url": video.video_url, "title": video.title} for video in videos]
    print("Videos enviados a la API:", video_data)  # Log para depuración
    return {"videos": video_data}

class Response(db.Model):
    __tablename__ = 'responses'
    
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relación con la opinión
    opinion_id = db.Column(db.Integer, db.ForeignKey('opinions.id'))
    opinion = db.relationship('Opinion', backref=db.backref('responses', lazy=True))
    
    # Usuario que responde
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('User', foreign_keys=[user_id])

    def __init__(self, text, opinion_id, user_id):
        self.text = text
        self.opinion_id = opinion_id
        self.user_id = user_id

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

@app.route('/logout')
def logout():
    session.pop("user_id", None)  # Elimina al usuario de la sesión
    flash("Has cerrado sesión exitosamente", "success")
    return redirect(url_for("login"))

@app.route('/delete_account')
def eliminar_cuenta():
    return render_template('eliminar-cuenta.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()   # Y las vuelve a crear con los nuevos tamaños

    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)

