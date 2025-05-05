document.addEventListener('DOMContentLoaded', () => {
    const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
    const csrfToken = csrfTokenMeta ? csrfTokenMeta.getAttribute('content') : '';

    async function loadComments(videoId) {
        const panel = document.querySelector(`.comments-panel[data-video-id="${videoId}"]`);
        const commentList = document.getElementById(`comments-list-${videoId}`);
        if (!panel || !commentList) return;

        commentList.innerHTML = '';

        try {
            const response = await fetch(`/comments/${videoId}`);
            const comments = await response.json();

            comments.forEach(comment => {
                const commentItem = document.createElement('div');
                commentItem.classList.add('comment-item');
                commentItem.dataset.commentId = comment.id;

                const profilePicture = comment.profile_picture || 'default.jpg';
                const profileLink = `/profile/${comment.username}`;
                const contentText = comment.is_deleted
                    ? '<em style="color: gray;">Comentario eliminado</em>'
                    : comment.content;

                const repliesHtml = comment.replies?.length > 0
                    ? `<button class="toggle-replies-btn" data-comment-id="${comment.id}">Mostrar respuestas (${comment.replies.length})</button>
                       <div class="replies-container hidden" id="replies-${comment.id}">
                           ${comment.replies.map(reply => `
                               <div class="reply-item comment-item" data-comment-id="${reply.id}">
                                   <a href="/profile/${reply.username}" class="comment-profile-link">
                                       <img src="/static/${reply.profile_picture || 'default.jpg'}" class="comment-profile-pic" />
                                   </a>
                                   <div class="comment-body">
                                       <a href="/profile/${reply.username}" class="comment-username">${reply.username}</a>
                                       <div class="comment-text">${reply.is_deleted ? '<em style="color:gray;">Comentario eliminado</em>' : reply.content}</div>
                                   </div>
                                   ${reply.is_owner && !reply.is_deleted ? `
                                   <div class="comment-options">
                                       <button class="dots-button">⋯</button>
                                       <div class="options-menu hidden">
                                           <button class="delete-comment-btn" data-comment-id="${reply.id}">Eliminar</button>
                                       </div>
                                   </div>` : ''}
                               </div>
                           `).join('')}
                       </div>` : '';

                commentItem.innerHTML = `
                    <div class="comment-content-wrapper">
                        <a href="${profileLink}" class="comment-profile-link">
                            <img src="/static/${profilePicture}" alt="${comment.username}" class="comment-profile-pic">
                        </a>
                        <div class="comment-body">
                            <a href="${profileLink}" class="comment-username">${comment.username}</a>
                            <div class="comment-text">${contentText}</div>
                            ${repliesHtml}
                        </div>
                        ${comment.is_owner && !comment.is_deleted ? `
                        <div class="comment-options">
                            <button class="dots-button">⋯</button>
                            <div class="options-menu hidden">
                                <button class="delete-comment-btn" data-comment-id="${comment.id}">Eliminar</button>
                            </div>
                        </div>` : ''}
                    </div>
                `;

                if (!comment.is_deleted) {
                    commentItem.addEventListener('click', () => {
                        const form = document.querySelector(`.add-comment-form[data-video-id="${videoId}"]`);
                        const input = form.querySelector('input[name="comment"]');
                        const parentInput = form.querySelector('input[name="parent_id"]');
                        input.placeholder = `Añade una respuesta para @${comment.username}`;
                        parentInput.value = comment.id;
                        input.focus();
                    });
                }

                commentList.appendChild(commentItem);
            });

            const commentCountSpan = document.querySelector(`.comment-button[data-video-id="${videoId}"] .comment-count`);
            if (commentCountSpan) {
                commentCountSpan.textContent = commentList.querySelectorAll('.comment-item').length;
            }

            document.querySelectorAll('.toggle-replies-btn').forEach(button => {
                button.addEventListener('click', () => {
                    const container = document.getElementById(`replies-${button.dataset.commentId}`);
                    container.classList.toggle('hidden');
                    button.textContent = container.classList.contains('hidden')
                        ? `Mostrar respuestas (${container.children.length})`
                        : 'Ocultar respuestas';
                });
            });

        } catch (err) {
            console.error('Error al cargar comentarios:', err);
        }
    }

    document.querySelectorAll('.comment-button').forEach(button => {
        button.addEventListener('click', async () => {
            const videoId = button.dataset.videoId;
            const panel = document.querySelector(`.comments-panel[data-video-id="${videoId}"]`);
            if (panel) {
                panel.classList.toggle('hidden');
                if (!panel.classList.contains('hidden')) {
                    await loadComments(videoId);
                }
            }
        });
    });

    const firstVisibleVideo = document.querySelector('.video-item:not(.hidden)');
    if (firstVisibleVideo) {
        const firstVideoId = firstVisibleVideo.querySelector('.comment-button')?.dataset.videoId;
        const panel = document.querySelector(`.comments-panel[data-video-id="${firstVideoId}"]`);
        if (panel) {
            panel.classList.remove('hidden');
            loadComments(firstVideoId);
        }
    }

    document.querySelectorAll('.add-comment-form').forEach(form => {
        form.addEventListener('submit', async e => {
            e.preventDefault();
            const videoId = form.dataset.videoId;
            const input = form.querySelector('input[name="comment"]');
            const parentId = form.querySelector('input[name="parent_id"]').value;
            const commentText = input.value.trim();
            if (!commentText) return;

            try {
                const response = await fetch(`/comments/${videoId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken,
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify({ comment: commentText, parent_id: parentId || null })
                });

                const result = await response.json();
                if (result.success) {
                    input.value = '';
                    input.placeholder = 'Escribe un comentario...';
                    form.querySelector('input[name="parent_id"]').value = '';
                    await loadComments(videoId);
                } else {
                    console.error('Error al enviar comentario:', result.message);
                }
            } catch (err) {
                console.error('Error al enviar el comentario:', err);
            }
        });
    });

    document.body.addEventListener('click', e => {
        if (e.target.matches('.dots-button')) {
            const menu = e.target.nextElementSibling;
            if (menu) menu.classList.toggle('hidden');
        } else {
            document.querySelectorAll('.options-menu').forEach(menu => {
                menu.classList.add('hidden');
            });
        }

        // Resetear formulario de respuesta
        const clickedInside = e.target.closest('.comment-item') || e.target.closest('.add-comment-form');
        if (!clickedInside) {
            document.querySelectorAll('.add-comment-form').forEach(form => {
                const input = form.querySelector('input[name="comment"]');
                const parentInput = form.querySelector('input[name="parent_id"]');
                input.placeholder = 'Escribe un comentario...';
                parentInput.value = '';
            });
        }
    });

    document.body.addEventListener('click', async e => {
        const deleteButton = e.target.closest('.delete-comment-btn');
        if (deleteButton) {
            const commentId = deleteButton.dataset.commentId;
            try {
                const response = await fetch(`/comments/${commentId}`, {
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });

                const result = await response.json();
                if (result.success) {
                    const panel = deleteButton.closest('.comments-panel');
                    const videoId = panel.dataset.videoId;
                    await loadComments(videoId);
                } else {
                    console.error('Error al eliminar comentario:', result.message);
                }
            } catch (err) {
                console.error('Error al eliminar comentario:', err);
            }
        }
    });
});
