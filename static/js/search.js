document.addEventListener("DOMContentLoaded", function () {

    const searchInput = document.getElementById("search-input");
    const suggestionsBox = document.getElementById("suggestions");

    let controller = null;

    searchInput.addEventListener("input", function () {
        const query = this.value.trim();

        if (query.length < 2) {
            suggestionsBox.innerHTML = "";
            suggestionsBox.style.display = "none";
            return;
        }

        // Cancelar petición anterior si existe
        if (controller) controller.abort();
        controller = new AbortController();

        fetch(`/search_suggestions?q=${encodeURIComponent(query)}`, {
            signal: controller.signal
        })
            .then(response => response.json())
            .then(data => {
                suggestionsBox.innerHTML = "";
                suggestionsBox.style.display = "block";

                if (!data.length) {
                    suggestionsBox.innerHTML = `
                        <div class="suggestion-item no-results">
                            ❌ Sin resultados
                        </div>
                    `;
                    return;
                }

                data.forEach(item => {
                    const suggestion = document.createElement("div");
                    suggestion.classList.add("suggestion-item");

                    let icon = "🔍";
                    let subtitle = "";
                    let link = null;

                    switch (item.type) {
                        case "user":
                            icon = "👤";
                            subtitle = item.profession || "Perfil";
                            link = `/profile/${item.username}`;
                            break;

                        case "project":
                            icon = "🧩";
                            subtitle = "Proyecto";
                            link = `/projects/${item.id}`;
                            break;

                        case "job":
                            icon = "💼";
                            subtitle = item.company || "Empleo";
                            link = `/jobs/${item.id}`;
                            break;

                        case "video":
                            icon = "🎥";
                            subtitle = "Video";
                            link = `/video/${item.id}`;
                            break;
                    }

                    suggestion.innerHTML = `
                        <span class="icon">${icon}</span>
                        <div class="text">
                            <strong>${item.name}</strong>
                            <small>${subtitle}</small>
                        </div>
                    `;

                    suggestion.addEventListener("click", () => {
                        if (link) {
                            window.location.href = link;
                        } else {
                            searchInput.value = item.name;
                            document.getElementById("search-form").submit();
                        }
                    });

                    suggestionsBox.appendChild(suggestion);
                });
            })
            .catch(error => {
                if (error.name !== "AbortError") {
                    console.error("Error en sugerencias:", error);
                }
            });
    });

    // Ocultar suggestions al hacer click fuera
    document.addEventListener("click", function (e) {
        if (!searchInput.contains(e.target) && !suggestionsBox.contains(e.target)) {
            suggestionsBox.style.display = "none";
        }
    });

});
