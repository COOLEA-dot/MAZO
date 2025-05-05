document.addEventListener("DOMContentLoaded", function() {
    let searchInput = document.getElementById("search-input");
    let suggestionsBox = document.getElementById("suggestions");

    searchInput.addEventListener("input", function() {
        let query = this.value.trim();
        if (query.length < 2) {
            suggestionsBox.innerHTML = "";
            return;
        }

        fetch(`/search_suggestions?q=${query}`)
            .then(response => response.json())
            .then(data => {
                suggestionsBox.innerHTML = "";
                data.forEach(item => {
                    let suggestion = document.createElement("div");
                    suggestion.classList.add("suggestion-item");
                    suggestion.textContent = `${item.name} - ${item.profession}`;
                    suggestion.onclick = function() {
                        searchInput.value = item.name;
                        suggestionsBox.innerHTML = "";
                    };
                    suggestionsBox.appendChild(suggestion);
                });
            })
            .catch(error => console.error("Error en sugerencias:", error));
    });
});
