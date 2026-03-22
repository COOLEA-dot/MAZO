# app/algorithms/feed_algorithm.py

from app import db
from models import Video, Comment, User


def get_feed_videos(user):
    """
    Algoritmo principal del feed.
    Prioriza:
    1. Gustos del usuario (likes y comentarios)
    2. Localización
    3. Usuarios premium
    """

    # =========================
    # 1️⃣ Gustos del usuario
    # =========================

    # Vídeos a los que el usuario dio like
    liked_video_ids = [video.id for video in user.liked_videos]

    # Vídeos donde el usuario comentó
    commented_video_ids = (
        Comment.query
        .filter(Comment.user_id == user.id)
        .with_entities(Comment.video_id)
        .all()
    )
    commented_video_ids = [v[0] for v in commented_video_ids]

    # =========================
    # 🚫 Usuarios bloqueados
    # =========================

    # Usuarios que YO he bloqueado
    blocked_users = [
        b.blocked_id for b in user.blocked_users
    ] if hasattr(user, "blocked_users") else []

    # Usuarios que me han bloqueado (opcional pero recomendado)
    blocked_by_users = [
        b.blocker_id for b in user.blocked_by
    ] if hasattr(user, "blocked_by") else []

    # Unión de todos los bloqueos
    all_blocked_ids = set(blocked_users + blocked_by_users)

    # =========================
    # 2️⃣ Obtener vídeos
    # =========================

    videos = Video.query.join(User).all()

    # =========================
    # 3️⃣ Calcular puntuación
    # =========================

    scored_videos = []

    for video in videos:
        score = 0

        # ❌ No mostrar vídeos propios
        if video.user_id == user.id:
            continue

        # 🚫 No mostrar vídeos de usuarios bloqueados
        if video.user_id in all_blocked_ids:
            continue

        # 👍 Likes
        if video.id in liked_video_ids:
            score += 2

        # 💬 Comentarios
        if video.id in commented_video_ids:
            score += 4

        # 📍 Localización
        if hasattr(user, "location") and user.location:
            if hasattr(video.user, "location") and video.user.location == user.location:
                score += 2

        # ⭐ Premium
        if hasattr(video.user, "is_premium") and video.user.is_premium:
            score += 5

        scored_videos.append((video, score))

    # =========================
    # 4️⃣ Ordenar el feed
    # =========================

    scored_videos.sort(key=lambda x: x[1], reverse=True)

    return [video for video, score in scored_videos]