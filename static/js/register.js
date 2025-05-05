// Validación de contraseñas
document.querySelector('form').addEventListener('submit', function (e) {
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirm_password').value;
    if (password !== confirmPassword) {
        alert('Las contraseñas no coinciden.');
        e.preventDefault();
    }
});

// Vista previa de imagen de perfil
document.getElementById('profile_pic').addEventListener('change', function (e) {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function (evt) {
            document.getElementById('profilePreview').src = evt.target.result;
        };
        reader.readAsDataURL(file);
    }
});

// Ocultar mensajes flash
setTimeout(() => {
    document.querySelectorAll('.flash-message').forEach(msg => msg.style.display = 'none');
}, 5000);

// Inicializar el mapa
const map = L.map('map').setView([40.4168, -3.7038], 5);

L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
    maxZoom: 17,
    attribution: 'Map data: &copy; OpenStreetMap contributors, SRTM | Map style: &copy; OpenTopoMap (CC-BY-SA)'
}).addTo(map);

let marker;

function setLocation(lat, lng) {
    if (marker) {
        marker.setLatLng([lat, lng]);
    } else {
        marker = L.marker([lat, lng]).addTo(map);
    }

    // Geocoding inverso
    fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}`)
        .then(response => response.json())
        .then(data => {
            const input = document.getElementById('location');
            if (data.address) {
                const address = data.address;
                const parts = [
                    address.road || address.pedestrian || address.footway || address.cycleway || '',
                    address.city || address.town || address.village || '',
                    address.postcode || ''
                ].filter(Boolean);
                input.value = parts.join(', ');
            } else {
                input.value = `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
            }
        })
        .catch(() => {
            document.getElementById('location').value = `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
        });

    map.setView([lat, lng], 13);
}

// Clic en el mapa
map.on('click', function (e) {
    const { lat, lng } = e.latlng;
    setLocation(lat, lng);
});

// Botón "Usar mi ubicación actual"
document.getElementById('use-my-location')?.addEventListener('click', () => {
    if (!navigator.geolocation) {
        alert("Tu navegador no soporta geolocalización.");
        return;
    }

    navigator.geolocation.getCurrentPosition(
        pos => {
            const { latitude, longitude } = pos.coords;
            setLocation(latitude, longitude);
        },
        () => alert("No se pudo obtener tu ubicación.")
    );
});

// Redibujar mapa
setTimeout(() => {
    map.invalidateSize();
}, 200);

// Autocompletado de ubicación
const locationInput = document.getElementById('location');
const suggestionsBox = document.getElementById('suggestions');

let debounceTimeout;

locationInput.addEventListener('input', function () {
    clearTimeout(debounceTimeout);

    debounceTimeout = setTimeout(() => {
        const query = locationInput.value.trim();
        if (query.length < 3) {
            suggestionsBox.innerHTML = '';
            suggestionsBox.style.display = 'none';
            return;
        }

        fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&addressdetails=1`)
            .then(res => res.json())
            .then(data => {
                suggestionsBox.innerHTML = '';
                if (!data.length) {
                    suggestionsBox.style.display = 'none';
                    return;
                }

                data.slice(0, 5).forEach(place => {
                    if (!place.address) return;

                    const address = place.address;
                    const parts = [
                        address.road || address.pedestrian || address.footway || address.cycleway || '',
                        address.city || address.town || address.village || '',
                        address.postcode || ''
                    ].filter(Boolean);

                    const simplified = parts.join(', ');

                    const div = document.createElement('div');
                    div.textContent = simplified;
                    div.style.padding = '6px';
                    div.style.cursor = 'pointer';
                    div.style.fontSize = '13px';

                    div.onclick = () => {
                        locationInput.value = simplified;
                        suggestionsBox.style.display = 'none';
                        if (place.lat && place.lon) {
                            setLocation(place.lat, place.lon);
                        }
                    };

                    suggestionsBox.appendChild(div);
                });

                suggestionsBox.style.display = 'block';
            })
            .catch(() => {
                suggestionsBox.innerHTML = '';
                suggestionsBox.style.display = 'none';
            });
    }, 300);
});

// Cerrar sugerencias al hacer clic fuera
document.addEventListener('click', (e) => {
    if (!suggestionsBox.contains(e.target) && e.target !== locationInput) {
        suggestionsBox.style.display = 'none';
    }
});
