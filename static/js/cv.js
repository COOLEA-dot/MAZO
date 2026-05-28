document.addEventListener('DOMContentLoaded', () => {

    // ==========================
    // AÑADIR TRABAJO
    // ==========================
    const addExperienceBtn = document.getElementById(
        'add-experience-btn'
    );

    const experienceContainer = document.getElementById(
        'experience-container'
    );

    if (addExperienceBtn && experienceContainer) {

        addExperienceBtn.addEventListener(
            'click',
            () => {

                const totalJobs =
                    experienceContainer.querySelectorAll(
                        '.experience-card'
                    ).length + 1;

                const card = document.createElement(
                    'div'
                );

                card.classList.add(
                    'experience-card'
                );

                card.innerHTML = `
                    <h3>
                        Trabajo ${totalJobs}
                    </h3>

                    <div class="cv-group">
                        <label>Nombre de la empresa</label>
                        <input type="text" name="company_name[]">
                    </div>

                    <div class="cv-group">
                        <label>Puesto de trabajo</label>
                        <input type="text" name="job_title[]">
                    </div>

                    <div class="cv-group">
                        <label>Fecha inicio</label>
                        <input type="date" name="start_date[]">
                    </div>

                    <div class="cv-group">
                        <label>Fecha fin</label>
                        <input type="date" name="end_date[]">
                    </div>

                    <div class="cv-group">
                        <label>Descripción (opcional)</label>
                        <textarea
                            name="description[]"
                            rows="4">
                        </textarea>
                    </div>
                `;

                experienceContainer.appendChild(
                    card
                );

            }
        );
    }

    // ==========================
    // AÑADIR ESTUDIO
    // ==========================
    const addEducationBtn = document.getElementById(
        'add-education-btn'
    );

    const educationContainer = document.getElementById(
        'education-container'
    );

    if (addEducationBtn && educationContainer) {

        addEducationBtn.addEventListener(
            'click',
            () => {

                const totalEducation =
                    educationContainer.querySelectorAll(
                        '.education-card'
                    ).length + 1;

                const card = document.createElement(
                    'div'
                );

                card.classList.add(
                    'education-card'
                );

                card.innerHTML = `
                    <h3>
                        Estudio ${totalEducation}
                    </h3>

                    <div class="cv-group">
                        <label>Nombre del centro</label>
                        <input type="text" name="school_name[]">
                    </div>

                    <div class="cv-group">
                        <label>Nombre del grado</label>
                        <input type="text" name="degree_name[]">
                    </div>

                    <div class="cv-group">
                        <label>Fecha inicio</label>
                        <input type="date"
                               name="education_start_date[]">
                    </div>

                    <div class="cv-group">
                        <label>Fecha final</label>
                        <input type="date"
                               name="education_end_date[]">
                    </div>

                    <div class="cv-checkbox">

                        <input type="checkbox"
                               name="currently_studying_${totalEducation - 1}">

                        <label>
                            Actualmente cursando
                        </label>

                    </div>
                `;

                educationContainer.appendChild(
                    card
                );

            }
        );
    }

    // ==========================
    // AÑADIR HABILIDAD
    // ==========================
    const addSkillBtn = document.getElementById(
        'add-skill-btn'
    );

    const skillsContainer = document.getElementById(
        'skills-container'
    );

    if (addSkillBtn && skillsContainer) {

        addSkillBtn.addEventListener(
            'click',
            () => {

                const totalSkills =
                    skillsContainer.querySelectorAll(
                        '.skill-card'
                    ).length + 1;

                const card = document.createElement(
                    'div'
                );

                card.classList.add(
                    'skill-card'
                );

                card.innerHTML = `
                    <h3>
                        Habilidad ${totalSkills}
                    </h3>

                    <div class="cv-group">
                        <label>
                            Nombre de habilidad
                        </label>

                        <input
                            type="text"
                            name="skill_name[]">
                    </div>
                `;

                skillsContainer.appendChild(
                    card
                );

            }
        );
    }

    // ==========================
    // AÑADIR IDIOMA
    // ==========================
    const addLanguageBtn = document.getElementById(
        'add-language-btn'
    );

    const languagesContainer = document.getElementById(
        'languages-container'
    );

    if (addLanguageBtn && languagesContainer) {

        addLanguageBtn.addEventListener(
            'click',
            () => {

                const totalLanguages =
                    languagesContainer.querySelectorAll(
                        '.language-card'
                    ).length + 1;

                const card = document.createElement(
                    'div'
                );

                card.classList.add(
                    'language-card'
                );

                card.innerHTML = `
                    <h3>
                        Idioma ${totalLanguages}
                    </h3>

                    <div class="cv-group">
                        <label>Idioma</label>

                        <input
                            type="text"
                            name="language_name[]">
                    </div>

                    <div class="cv-group">
                        <label>Nivel</label>

                        <select name="language_level[]">

                            <option value="">
                                Seleccionar
                            </option>

                            <option value="Nativo">
                                Nativo
                            </option>

                            <option value="Básico">
                                Básico
                            </option>

                            <option value="Intermedio">
                                Intermedio
                            </option>

                            <option value="Avanzado">
                                Avanzado
                            </option>

                            <option value="Profesional">
                                Profesional
                            </option>

                            <option value="Bilingüe">
                                Bilingüe
                            </option>

                        </select>
                    </div>
                `;

                languagesContainer.appendChild(
                    card
                );

            }
        );
    }
    // ==========================
    // PREVIEW FOTO CV
    // ==========================
    const cvPhotoInput = document.getElementById(
        'cv-photo-input'
    );

    const cvPhotoPreview = document.getElementById(
        'cv-photo-preview'
    );

    if (
        cvPhotoInput &&
        cvPhotoPreview
    ) {

        cvPhotoInput.addEventListener(
            'change',
            (event) => {

                const file =
                    event.target.files[0];

                if (!file) return;

                const reader =
                    new FileReader();

                reader.onload =
                    function(e) {

                    cvPhotoPreview.src =
                        e.target.result;
                };

                reader.readAsDataURL(
                    file
                );

            }
        );
    }

});