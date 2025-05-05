document.addEventListener('DOMContentLoaded', function() {
    // Configurar el socket.io si no lo has hecho aún
    const socket = io.connect();

    socket.on('new_message', function(data) {
        const conversationId = data.conversation_id;
        const sender = data.sender;

        // Actualizar los chats en tiempo real
        const chatItems = document.querySelectorAll('.chat-item');

        chatItems.forEach(item => {
            const chatUsername = item.querySelector('h3').textContent;

            // Si el chat tiene mensajes no leídos, se agrega la clase 'unread'
            if (chatUsername === sender) {
                item.classList.add('unread'); // Añadir clase para mostrar la notificación
            }
        });
    });
});
