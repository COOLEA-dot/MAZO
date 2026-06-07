# app/algorithms/feed_algorithm.py

from app import db
from models import Video, Comment, User, Block


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

    liked_video_ids = [
        video.id
        for video in user.liked_videos
    ]

    commented_video_ids = (
        Comment.query
        .filter(
            Comment.user_id == user.id
        )
        .with_entities(
            Comment.video_id
        )
        .all()
    )

    commented_video_ids = [
        v[0]
        for v in commented_video_ids
    ]

    # =========================
    # 🚫 Usuarios bloqueados
    # =========================

    blocked_users = (
        db.session.query(
            Block.blocked_id
        )
        .filter(
            Block.blocker_id
            == user.id
        )
        .all()
    )

    blocked_users = [
        b[0]
        for b in blocked_users
    ]

    blocked_by_users = (
        db.session.query(
            Block.blocker_id
        )
        .filter(
            Block.blocked_id
            == user.id
        )
        .all()
    )

    blocked_by_users = [
        b[0]
        for b in blocked_by_users
    ]

    # 🔥 FIX REAL
    all_blocked_ids = list(
        set(
            blocked_users +
            blocked_by_users
        )
    )

    print(
        "🚫 BLOCKED IDS:",
        all_blocked_ids
    )

    print(
        "👤 USER:",
        user.id
    )

    # =========================
    # 2️⃣ Obtener vídeos
    # =========================

    query = (
        Video.query
        .join(User)
        .filter(
            Video.user_id
            != user.id
        )
    )

    # 🔥 solo aplicar filtro
    # si hay bloqueados
    if all_blocked_ids:

        query = query.filter(
            ~Video.user_id.in_(
                all_blocked_ids
            )
        )

    videos = query.all()

    print(
        "🎬 VIDEOS FEED:",
        [
            (
                v.id,
                v.user_id
            )
        for v in videos
        ]
    )

    # =========================
    # 3️⃣ Calcular puntuación
    # =========================

    scored_videos = []

    for video in videos:

        score = 0

        # 👍 Likes
        if (
            video.id
            in liked_video_ids
        ):
            score += 2

        # 💬 Comentarios
        if (
            video.id
            in commented_video_ids
        ):
            score += 4

        # 📍 Localización
        if (
            hasattr(
                user,
                "location"
            )
            and user.location
        ):

            if (
                hasattr(
                    video.user,
                    "location"
                )
                and
                video.user.location
                == user.location
            ):
                score += 2

        # ⭐ Premium
        if (
            hasattr(
                video.user,
                "is_premium"
            )
            and
            video.user.is_premium
        ):
            score += 5

        scored_videos.append(
            (video, score)
        )

    # =========================
    # 4️⃣ Ordenar
    # =========================

    scored_videos.sort(
        key=lambda x: x[1],
        reverse=True
    )

    return [
        video
        for video, score
        in scored_videos
    ]