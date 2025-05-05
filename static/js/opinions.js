document.addEventListener('DOMContentLoaded', function () {
    const opinionForm = document.getElementById('opinion-form');
    const reviewsButton = document.querySelector('.btn-reviews');
    const reviewsSection = document.getElementById('reviews-section');
    const closeReviewsButton = document.querySelector('.close-reviews');

    // Enviar una nueva opinión
    if (opinionForm) {
        opinionForm.addEventListener('submit', function (event) {
            event.preventDefault();
            const formData = new FormData(opinionForm);

            fetch(opinionForm.action, {
                method: "POST",
                body: formData,
                headers: { 'X-CSRFToken': document.querySelector('[name=csrf_token]').value }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert(data.message);
                        document.getElementById('no-opinions-message')?.remove();

                        const reviewsList = document.querySelector('.reviews-list');
                        const newReviewHTML = `
                            <div class="review-container" id="review-${data.opinion_id}">
                                <div class="review-header">
                                    <img src="${data.user_profile_pic || '/static/profile_pics/default.jpg'}" class="review-profile-pic">
                                    <div class="review-user-info">
                                        <p class="review-username">
                                            <a href="${data.user_profile_url}">${data.username}</a>
                                        </p>
                                        <p class="review-rating">⭐ ${data.rating}/10</p>
                                    </div>
                                    <button class="delete-opinion-btn" data-opinion-id="${data.opinion_id}">Eliminar</button>
                                </div>
                                <div class="review-content">
                                    <p class="review-text">${data.opinion_text}</p>
                                    <div class="response-form-container">
                                        <form class="response-form" data-opinion-id="${data.opinion_id}">
                                            <textarea name="response" placeholder="Introduce tu respuesta..." required></textarea>
                                            <button type="submit" class="btn btn-info">Responder</button>
                                        </form>
                                    </div>
                                    <button class="show-replies-btn" data-opinion-id="${data.opinion_id}">Mostrar respuestas</button>
                                    <div class="replies hidden" id="replies-${data.opinion_id}"></div>
                                </div>
                            </div>`;

                        reviewsList.insertAdjacentHTML('afterbegin', newReviewHTML);
                        opinionForm.querySelector('textarea').value = '';
                    } else {
                        alert(data.message);
                    }
                })
                .catch(error => alert("Hubo un error: " + error));
        });
    }

    // Mostrar y cerrar la sección de opiniones
    if (reviewsButton) {
        reviewsButton.addEventListener('click', () => {
            reviewsSection.classList.add('show');
            reviewsSection.classList.remove('hidden');
        });
    }

    if (closeReviewsButton) {
        closeReviewsButton.addEventListener('click', () => {
            reviewsSection.classList.remove('show');
            reviewsSection.classList.add('hidden');
        });
    }

    // Eliminar una opinión
    document.body.addEventListener('click', function (event) {
        if (event.target.classList.contains('delete-opinion-btn')) {
            const opinionId = event.target.getAttribute('data-opinion-id');
            const csrfToken = document.querySelector('[name=csrf_token]').value;

            if (confirm('¿Estás seguro de que quieres eliminar esta opinión?')) {
                fetch(`/opinion/${opinionId}/delete`, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrfToken }
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            document.getElementById(`review-${opinionId}`).remove();
                            alert(data.message);
                        } else {
                            alert(data.message);
                        }
                    })
                    .catch(error => alert('Hubo un error: ' + error));
            }
        }
    });

    // Eliminar una respuesta
    document.body.addEventListener('click', function (event) {
        if (event.target.classList.contains('delete-response-btn')) {
            const responseId = event.target.getAttribute('data-response-id');
            const csrfToken = document.querySelector('[name=csrf_token]').value;

            if (confirm('¿Estás seguro de que quieres eliminar esta respuesta?')) {
                fetch(`/response/${responseId}/delete`, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrfToken }
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            document.getElementById(`response-${responseId}`).remove();
                            alert(data.message);
                        } else {
                            alert(data.message);
                        }
                    })
                    .catch(error => alert('Hubo un error: ' + error));
            }
        }
    });

    // Mostrar/Ocultar respuestas
    document.body.addEventListener('click', function (event) {
        if (event.target.classList.contains('show-replies-btn')) {
            const opinionId = event.target.getAttribute('data-opinion-id');
            let repliesContainer = document.getElementById(`replies-${opinionId}`);

            // Si el contenedor de respuestas no existe, lo creamos dentro de la opinión
            if (!repliesContainer) {
                const reviewContainer = document.getElementById(`review-${opinionId}`);
                if (!reviewContainer) return;

                repliesContainer = document.createElement('div');
                repliesContainer.classList.add('replies', 'hidden');
                repliesContainer.id = `replies-${opinionId}`;
                reviewContainer.querySelector('.review-content').appendChild(repliesContainer);
            }

            // Alternar visibilidad
            repliesContainer.classList.toggle('hidden');
            event.target.textContent = repliesContainer.classList.contains('hidden') ? "Mostrar respuestas" : "Ocultar respuestas";

            // Cargar respuestas si aún no han sido cargadas
            if (!repliesContainer.hasAttribute('data-loaded')) {
                fetch(`/opinion/${opinionId}/responses`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            repliesContainer.innerHTML = data.responses.map(response => `
                                <div class="response" id="response-${response.id}">
                                    <div class="response-header">
                                        <img src="${response.user_profile_pic || '/static/profile_pics/default.jpg'}" class="response-profile-pic">
                                        <div class="response-user-info">
                                            <p class="response-username">
                                                <a href="${response.user_profile_url}">${response.username}</a>
                                            </p>
                                        </div>
                                    </div>
                                    <p class="response-text">${response.text}</p>
                                    <button class="delete-response-btn" data-response-id="${response.id}">Eliminar</button>
                                </div>
                            `).join('');
                            repliesContainer.setAttribute('data-loaded', 'true');
                        } else {
                            alert("No se pudieron cargar las respuestas.");
                        }
                    })
                    .catch(error => alert("Hubo un error al cargar las respuestas: " + error));
            }
        }
    });

    // Enviar una respuesta
    document.body.addEventListener('submit', function (event) {
        if (event.target.classList.contains('response-form')) {
            event.preventDefault();

            const form = event.target;
            const opinionId = form.getAttribute('data-opinion-id');
            const textarea = form.querySelector('textarea');
            const responseText = textarea.value.trim();

            if (!responseText) {
                alert("La respuesta no puede estar vacía.");
                return;
            }

            fetch(`/opinion/${opinionId}/respond`, {
                method: "POST",
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrf_token]').value
                },
                body: JSON.stringify({ text: responseText })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert(data.message);

                        const responseHTML = `
                            <div class="response" id="response-${data.response.id}">
                                <div class="response-header">
                                    <img src="${data.response.user_profile_pic || '/static/profile_pics/default.jpg'}" class="response-profile-pic">
                                    <div class="response-user-info">
                                        <p class="response-username">
                                            <a href="${data.response.user_profile_url}">${data.response.username}</a>
                                        </p>
                                    </div>
                                </div>
                                <p class="response-text">${data.response.text}</p>
                                <button class="delete-response-btn" data-response-id="${data.response.id}">Eliminar</button>
                            </div>`;

                        const repliesContainer = document.getElementById(`replies-${opinionId}`);
                        repliesContainer.insertAdjacentHTML('beforeend', responseHTML);
                        textarea.value = '';
                    } else {
                        alert(data.message);
                    }
                })
                .catch(error => alert("Hubo un error: " + error));
        }
    });
});
