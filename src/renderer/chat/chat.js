document.getElementById("send-button").addEventListener("click", () => {
    const input = document.getElementById("chat-input");
    const message = input.value.trim();

    if (message) {
        // Muestra el mensaje del usuario
        appendMessage("Tú", message);

        // Envía el mensaje al Main Process
        window.electronAPI.sendMessage(message);

        // Limpia el input
        input.value = "";
    }
});

// Escucha las respuestas del Main Process
window.electronAPI.onReceiveResponse((response) => {
    appendMessage("Asistente", response);
});

// Función para añadir mensajes al chat
function appendMessage(sender, message) {
    const messagesDiv = document.getElementById("messages");
    const messageDiv = document.createElement("div");
    messageDiv.className = "message";
    messageDiv.innerHTML = `
    <div class="flex items-end">
                <div class="bg-ios-gray text-white rounded-2xl p-3 max-w-xs">
                    <p class="text-sm">Hola, ¿en qué puedo ayudarte hoy?</p>
                </div>
            </div>
    `;

    // Desplázate al final
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}
