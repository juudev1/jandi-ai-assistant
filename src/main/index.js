const { app, BrowserWindow, ipcMain, Tray, Menu, globalShortcut } = require("electron");
import { electronApp, optimizer, is } from '@electron-toolkit/utils'
const path = require("path");
const url = require("url");

let mainWindow;
let settingsWindow;
let chatWindow;
let tray;

// Cuando la aplicación esté lista
app.on("ready", () => {
    // Registra el atajo global para Win+J
    const registered = globalShortcut.register("CommandOrControl+Alt+J", () => {
        toggleChatWindow();
    });

    if (!registered) {
        console.error("No se pudo registrar el atajo de teclado.");
    } else {
        console.log("Atajo registrado: Win+J");
    }

    createTray();

    // Muestra un error si el registro falla
    app.on("will-quit", () => {
        globalShortcut.unregisterAll(); // Desregistra todos los atajos al salir
    });
});

// Crear o alternar la ventana del chat
function toggleChatWindow() {
    if (chatWindow) {
        chatWindow.hide(); // Cierra la ventana si ya está abierta
        chatWindow = null;
    } else {
        createChatWindow(); // Abre la ventana si está cerrada
    }
}

// Liberar recursos al salir
app.on("will-quit", () => {
    globalShortcut.unregisterAll();
});

// Función para crear la ventana de configuración
function createSettingsWindow() {
    settingsWindow = new BrowserWindow({
        width: 400,
        height: 500,
        resizable: false,
        title: "JanDi AI Assistant",
    });

    settingsWindow.setMenu(null);

    if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
        settingsWindow.loadFile(path.join(__dirname, "../renderer/settings/index.html"));
    } else {
        settingsWindow.loadFile(path.join(__dirname, "../renderer/settings/index.html"));
    }
}

// Función para crear la ventana flotante del chat
function createChatWindow(message) {
    chatWindow = new BrowserWindow({
        width: 300,
        height: 150,
        // frame: false,
        alwaysOnTop: true,
        // resizable: false,
    });

    if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
        chatWindow.loadFile(path.join(__dirname, "../renderer/chat/index.html"));
    } else {
        chatWindow.loadFile(path.join(__dirname, "../renderer/chat/index.html"));
    }

    // Manejo de mensajes del Renderer
    ipcMain.on("send-message", (event, message) => {
        console.log("Mensaje recibido:", message);

        // Respuesta predeterminada
        const response = `Respuesta predeterminada para: "${message}"`;
        event.reply("receive-response", response);
    });


}

// Función para crear el icono de bandeja
function createTray() {
    tray = new Tray(path.join(__dirname, "../../assets/images/tray_icon.png"));
    const trayMenu = Menu.buildFromTemplate([
        {
            label: "Abrir aplicación",
            click: () => {
                mainWindow.show();
            },
        },
        {
            label: "Configuración",
            click: () => {
                createSettingsWindow();
            },
        },
        {
            label: "Salir",
            click: () => {
                app.quit();
            },
        },
    ]);
    tray.setContextMenu(trayMenu);

    tray.on("click", () => {
        mainWindow.show();
    }
    );
}

