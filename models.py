from datetime import datetime
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy import func, UniqueConstraint, Numeric
from sqlalchemy.orm import backref
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, IntegerField, PasswordField, SubmitField, SelectField, DecimalField, HiddenField
from wtforms.validators import DataRequired, Optional, NumberRange, Length, EqualTo
from flask_wtf.file import FileField, FileAllowed, MultipleFileField
from slugify import slugify 


class Offer(db.Model):
    __tablename__ = "offer"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(150), unique=True, nullable=False)
    description = db.Column(db.Text)
    kind = db.Column(db.String(30), nullable=False)  # 'percent', 'fixed', 'first_month_free', 'stripe_coupon'
    value = db.Column(db.Integer, nullable=True)  # percentage (0-100) or fixed cents
    max_uses = db.Column(db.Integer, nullable=True)  # null = ilimitado
    uses = db.Column(db.Integer, default=0)
    starts_at = db.Column(db.DateTime, default=datetime.utcnow)
    ends_at = db.Column(db.DateTime, nullable=True)
    active = db.Column(db.Boolean, default=True)
    combinable = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    stripe_coupon_id = db.Column(db.String(255), nullable=True)  # si creamos coupon en Stripe
    stripe_promotion_code = db.Column(db.String(255), nullable=True)  # opcion: promotion code id

class OfferUsage(db.Model):
    __tablename__ = "offer_usage"
    id = db.Column(db.Integer, primary_key=True)
    offer_id = db.Column(db.Integer, db.ForeignKey("offer.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


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


user_professions = db.Table(
    'user_professions',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    db.Column('profession_id', db.Integer, db.ForeignKey('profession.id', ondelete='CASCADE'), primary_key=True),
    db.UniqueConstraint('user_id', 'profession_id', name='uq_user_profession')
)

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    profile_pic = db.Column(db.String(100), nullable=True)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20), nullable=True)
    company = db.Column(db.String(100), nullable=True)

    # ⚠️ (Deprecated) mantenla temporalmente para no romper formularios antiguos
    profession = db.Column(db.String(100), nullable=True)

    description = db.Column(db.String(300), nullable=True)
    location = db.Column(db.String(200), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    is_premium = db.Column(db.Boolean, default=False)
    google_id = db.Column(db.String(200), unique=True, nullable=True)
    cv_file = db.Column(db.String(255), nullable=True)
    # dentro de la clase User (ajusta el nombre del tipo/longitud si quieres)
    apple_sub = db.Column(db.String(255), unique=True, nullable=True, index=True)



    comments = db.relationship('Comment', back_populates='user')

    # Nueva relación many-to-many
    professions = db.relationship(
        'Profession',
        secondary=user_professions,
        lazy='joined',
        backref=db.backref('users', lazy='dynamic')
    )

    # ---- Helpers cómodos ----
    def set_professions_from_list(self, names: list[str]):
        """Asigna una lista de nombres (strings). Crea las profesiones si no existen."""
        cleaned = {n.strip() for n in names if n and n.strip()}
        if not cleaned:
            self.professions = []
            return
        existing = {p.name.lower(): p for p in Profession.query.filter(
            func.lower(Profession.name).in_([n.lower() for n in cleaned])
        ).all()}
        result = []
        for n in cleaned:
            key = n.lower()
            if key in existing:
                result.append(existing[key])
            else:
                p = Profession(name=n.strip())
                db.session.add(p)
                result.append(p)
        self.professions = result

    def add_profession_by_name(self, name: str):
        if not name or not name.strip():
            return
        name = name.strip()
        p = Profession.query.filter(func.lower(Profession.name) == name.lower()).first()
        if not p:
            p = Profession(name=name)
            db.session.add(p)
        if p not in self.professions:
            self.professions.append(p)

    @property
    def profession_names(self) -> list[str]:
        return [p.name for p in (self.professions or [])]
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
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

class UserToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    fcm_token = db.Column(db.String(255), unique=True, nullable=False)

    user = db.relationship('User', backref=db.backref('tokens', lazy=True))


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


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Contraseña actual', validators=[DataRequired()])
    new_password = PasswordField('Nueva contraseña', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmar nueva contraseña', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Cambiar contraseña')

class Profession(db.Model):
    __tablename__ = 'profession'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), nullable=False, unique=True)
    popularity = db.Column(db.Integer, nullable=False, default=0)
    
    @staticmethod
    def get_or_create(name: str):
        clean = name.strip()
        if not clean:
            return None
        existing = Profession.query.filter(db.func.lower(Profession.name)==clean.lower()).first()
        if existing:
            return existing
        p = Profession(name=clean, slug=slugify(clean))
        db.session.add(p)
        return p


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

class ChatMessage(db.Model):
    __tablename__ = 'message' 
    
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


CURRENCY_CHOICES = [("EUR","EUR"),("USD","USD"),("GBP","GBP"),("MXN","MXN")]
PERIOD_CHOICES   = [("hour","Hora"),("day","Día"),("month","Mes"),("year","Año")]

class ProjectForm(FlaskForm):
    title = StringField('Título', validators=[DataRequired(), Length(max=150)])
    short_description = StringField('Descripción corta', validators=[DataRequired(), Length(max=180)])
    description = TextAreaField('Descripción larga', validators=[DataRequired(), Length(min=10)])
    location = StringField('Ubicación', validators=[Optional(), Length(max=120)])
    modality = SelectField(
        'Modalidad',
        choices=[('', '— Selecciona —'), ('remoto', 'Remoto'), ('presencial', 'Presencial'), ('hibrido', 'Híbrido')],
        validators=[Optional()]
    )
    # --- NUEVO ---
    price_min = DecimalField('Precio (mín.)', places=2, validators=[Optional(), NumberRange(min=0)])
    price_max = DecimalField('Precio (máx.)', places=2, validators=[Optional(), NumberRange(min=0)])
    price_currency = SelectField('Moneda', choices=[("", "—")] + CURRENCY_CHOICES, validators=[Optional()])

    submit = SubmitField('Publicar proyecto')

class JobForm(FlaskForm):
    title = StringField('Título', validators=[DataRequired(), Length(max=150)])
    short_description = StringField('Descripción corta', validators=[DataRequired(), Length(max=180)])
    description = TextAreaField('Descripción larga', validators=[DataRequired(), Length(min=10)])
    location = StringField('Ubicación', validators=[Optional(), Length(max=120)])
    modality = SelectField(
        'Modalidad',
        choices=[('', '— Selecciona —'), ('remoto', 'Remoto'), ('presencial', 'Presencial'), ('hibrido', 'Híbrido')],
        validators=[Optional()]
    )
    salary_min = DecimalField('Salario (mín.)', places=2, rounding=None, validators=[Optional(), NumberRange(min=0)])
    salary_max = DecimalField('Salario (máx.)', places=2, rounding=None, validators=[Optional(), NumberRange(min=0)])
    salary_currency = SelectField('Moneda', choices=[("", "—")] + CURRENCY_CHOICES, validators=[Optional()])
    salary_period = SelectField('Periodo', choices=[("", "—")] + PERIOD_CHOICES, validators=[Optional()])
    
    submit = SubmitField('Publicar empleo')

class Project(db.Model):
    __tablename__ = "project"
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(150), nullable=False, index=True)
    short_description = db.Column(db.String(180), nullable=True, index=True)  # frase corta
    description = db.Column(db.Text, nullable=False)  # descripción larga
    location = db.Column(db.String(120), index=True)
    modality = db.Column(db.String(20), index=True)  # 'remoto', 'presencial', 'híbrido'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    price_min = db.Column(Numeric(10,2), nullable=True, index=True)
    price_max = db.Column(Numeric(10,2), nullable=True, index=True)
    price_currency = db.Column(db.String(10), nullable=True, index=True)


    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('projects', lazy='dynamic'))

class Job(db.Model):
    __tablename__ = "job"
    __table_args__ = {'extend_existing': True} 
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(150), nullable=False, index=True)
    short_description = db.Column(db.String(180), nullable=True, index=True)  # frase corta
    description = db.Column(db.Text, nullable=False)  # descripción larga
    location = db.Column(db.String(120), index=True)
    modality = db.Column(db.String(20), index=True)  # 'remoto', 'presencial', 'híbrido'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    salary_min = db.Column(Numeric(10,2), nullable=True, index=True)
    salary_max = db.Column(Numeric(10,2), nullable=True, index=True)
    salary_currency = db.Column(db.String(10), nullable=True, index=True)
    salary_period = db.Column(db.String(10), nullable=True, index=True)  # hour/day/month/year


    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('jobs', lazy='dynamic'))


class JobApplication(db.Model):
    __tablename__ = "job_application"
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    applicant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="active")  # active | cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    job = db.relationship('Job', backref=db.backref('applications', lazy='dynamic', cascade='all, delete-orphan'))
    applicant = db.relationship('User', backref=db.backref('job_applications', lazy='dynamic'))

    __table_args__ = (UniqueConstraint('job_id', 'applicant_id', name='uq_job_applicant'),)

class ProjectApplication(db.Model):
    __tablename__ = "project_application"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    applicant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="active")  # active | cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    project = db.relationship('Project', backref=db.backref('applications', lazy='dynamic', cascade='all, delete-orphan'))
    applicant = db.relationship('User', backref=db.backref('project_applications', lazy='dynamic'))

    __table_args__ = (UniqueConstraint('project_id', 'applicant_id', name='uq_project_applicant'),)



class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    invite_code = db.Column(db.String(32), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    image = db.Column(db.String(255))  # 👈 NUEVO

    members = db.relationship(
        'GroupMember',
        backref='group',
        cascade='all, delete-orphan'
    )


class GroupMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    is_admin = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref='group_memberships')

class CreateGroupForm(FlaskForm):
    name = StringField(
        'Nombre del grupo',
        validators=[DataRequired(), Length(max=100)]
    )
    description = TextAreaField(
        'Descripción',
        validators=[Length(max=255)]
    )
    image = FileField(
        'Imagen del grupo',
        validators=[FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Solo imágenes')]
    )

class GroupMessage(db.Model):
    __tablename__ = "group_messages"

    id = db.Column(db.Integer, primary_key=True)

    group_id = db.Column(
        db.Integer,
        db.ForeignKey("group.id"),
        nullable=False
    )

    sender_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    content = db.Column(db.Text, nullable=True)

    file_url = db.Column(db.String(255), nullable=True)
    thumbnail_url = db.Column(db.String(255), nullable=True)

    timestamp = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        index=True
    )

    sender = db.relationship("User", backref="group_messages")
    group = db.relationship("Group", backref="messages")

class EditGroupForm(FlaskForm):
    name = StringField(validators=[Length(max=100)])
    description = TextAreaField(validators=[Length(max=255)])
    image = FileField()

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # Relación con la empresa (usuario)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Datos básicos
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)

    # Imagen principal del producto
    image = db.Column(db.String(255), nullable=True)

    # Estado
    is_active = db.Column(db.Boolean, default=True)

    # Métricas (para futuro premium)
    views = db.Column(db.Integer, default=0)
    clicks = db.Column(db.Integer, default=0)
    sales = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='products')

class ProductImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    image = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product', backref='images')

class CreateProductForm(FlaskForm):
    images = MultipleFileField(
        'Imágenes del producto',
        validators=[
            FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Solo imágenes')
        ]
    )

    title = StringField(
        'Nombre del producto',
        validators=[DataRequired()]
    )

    description = TextAreaField('Descripción')

    price = DecimalField(
        'Precio (€)',
        validators=[DataRequired(), NumberRange(min=0)]
    )

    submit = SubmitField('Publicar producto')

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer)
    reported_user_id = db.Column(db.Integer)
    video_id = db.Column(db.Integer, nullable=True)
    reason = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ReportForm(FlaskForm):
    video_id = HiddenField()
    reason = TextAreaField(validators=[DataRequired(), Length(max=255)])
    
class Block(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    blocker_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False
    )

    blocked_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False
    )

class BlockForm(FlaskForm):
    user_id = HiddenField()

class UnblockForm(FlaskForm):
    user_id = HiddenField()