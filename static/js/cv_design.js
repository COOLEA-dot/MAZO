document.addEventListener('DOMContentLoaded', () => {

    // ==========================
    // DATOS PREVIEW
    // ==========================
    const previewPhoto =
        document.querySelector(
            '.preview-photo'
        );

    const previewName =
        document.querySelector(
            '.preview-user h3'
        );

    const previewTitle =
        document.querySelector(
            '.preview-user span'
        );

    const sidebar =
        document.querySelector(
            '.preview-sidebar'
        );

    const main =
        document.querySelector(
            '.preview-main'
        );

    // ==========================
    // USER DATA
    // ==========================
const userData = JSON.parse(
    document.getElementById(
        'cv-data'
    ).textContent
);

if (!userData) return;
    // ==========================
    // FOTO PERFIL
    // ==========================
    if (
        previewPhoto &&
        userData.profile_picture
    ) {

        previewPhoto.innerHTML = `
            <img
                src="${userData.profile_picture}"
                alt="profile"
                style="
                    width:100%;
                    height:100%;
                    object-fit:cover;
                    border-radius:50%;
                ">
        `;
    }

    // ==========================
    // NOMBRE
    // ==========================
    if (previewName) {

        previewName.textContent =
            userData.full_name ||
            'Usuario MAZO';
    }

    // ==========================
    // PROFESIÓN
    // ==========================
    if (previewTitle) {

        previewTitle.textContent =
            userData.professional_title ||
            'Profesional';
    }

    // ==========================
    // SIDEBAR
    // ==========================
    if (sidebar) {

        sidebar.innerHTML = '';

        // CONTACTO
        sidebar.innerHTML += `
            <div class="preview-info-card">
                <h4>📍 Ubicación</h4>
                <p>
                    ${
                        userData.location ||
                        'No añadida'
                    }
                </p>
            </div>
        `;

        sidebar.innerHTML += `
            <div class="preview-info-card">
                <h4>📞 Contacto</h4>
                <p>
                    ${
                        userData.phone ||
                        'No añadido'
                    }
                </p>
            </div>
        `;

        // IDIOMAS
        if (
            userData.languages &&
            userData.languages.length
        ) {

            let languagesHTML = '';

            userData.languages.forEach(
                language => {

                languagesHTML += `
                    <div class="preview-tag">
                        ${language.name}
                    </div>
                `;
            });

            sidebar.innerHTML += `
                <div class="preview-info-card">
                    <h4>🌍 Idiomas</h4>
                    <div class="preview-tags">
                        ${languagesHTML}
                    </div>
                </div>
            `;
        }

        // HABILIDADES
        if (
            userData.skills &&
            userData.skills.length
        ) {

            let skillsHTML = '';

            userData.skills.forEach(
                skill => {

                skillsHTML += `
                    <div class="preview-tag">
                        ${skill}
                    </div>
                `;
            });

            sidebar.innerHTML += `
                <div class="preview-info-card">
                    <h4>⭐ Habilidades</h4>
                    <div class="preview-tags">
                        ${skillsHTML}
                    </div>
                </div>
            `;
        }
    }

    // ==========================
    // MAIN CONTENT
    // ==========================
    if (main) {

        main.innerHTML = '';

        // SOBRE MI
        if (userData.about_me) {

            main.innerHTML += `
                <div class="preview-section">
                    <h4>Sobre mí</h4>

                    <p>
                        ${userData.about_me}
                    </p>
                </div>
            `;
        }

        // EXPERIENCIA
        if (
            userData.experiences &&
            userData.experiences.length
        ) {

            let experienceHTML = '';

            userData.experiences.forEach(
                experience => {

                experienceHTML += `
                    <div class="preview-job">

                        <strong>
                            ${experience.job_title}
                        </strong>

                        <span>
                            ${experience.company_name}
                        </span>

                    </div>
                `;
            });

            main.innerHTML += `
                <div class="preview-section">

                    <h4>
                        Experiencia
                    </h4>

                    ${experienceHTML}

                </div>
            `;
        }

        // EDUCACIÓN
        if (
            userData.educations &&
            userData.educations.length
        ) {

            let educationHTML = '';

            userData.educations.forEach(
                education => {

                educationHTML += `
                    <div class="preview-job">

                        <strong>
                            ${education.degree_name}
                        </strong>

                        <span>
                            ${education.school_name}
                        </span>

                    </div>
                `;
            });

            main.innerHTML += `
                <div class="preview-section">

                    <h4>
                        Educación
                    </h4>

                    ${educationHTML}

                </div>
            `;
        }
    }

});