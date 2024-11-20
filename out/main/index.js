"use strict";
const utils = require("@electron-toolkit/utils");
const { app, BrowserWindow, ipcMain, Tray, Menu, globalShortcut } = require("electron");
const path = require("path");
require("url");
let mainWindow;
let settingsWindow;
let chatWindow;
let tray;
app.on("ready", () => {
  const registered = globalShortcut.register("CommandOrControl+Alt+J", () => {
    toggleChatWindow();
  });
  if (!registered) {
    console.error("No se pudo registrar el atajo de teclado.");
  } else {
    console.log("Atajo registrado: Win+J");
  }
  createTray();
  app.on("will-quit", () => {
    globalShortcut.unregisterAll();
  });
});
function toggleChatWindow() {
  if (chatWindow) {
    chatWindow.hide();
    chatWindow = null;
  } else {
    createChatWindow();
  }
}
app.on("will-quit", () => {
  globalShortcut.unregisterAll();
});
function createSettingsWindow() {
  settingsWindow = new BrowserWindow({
    width: 400,
    height: 500,
    resizable: false,
    title: "JanDi AI Assistant"
  });
  settingsWindow.setMenu(null);
  if (utils.is.dev && process.env["ELECTRON_RENDERER_URL"]) {
    settingsWindow.loadFile(path.join(__dirname, "../renderer/settings/index.html"));
  } else {
    settingsWindow.loadFile(path.join(__dirname, "../renderer/settings/index.html"));
  }
}
function createChatWindow(message) {
  chatWindow = new BrowserWindow({
    width: 300,
    height: 150,
    // frame: false,
    alwaysOnTop: true
    // resizable: false,
  });
  if (utils.is.dev && process.env["ELECTRON_RENDERER_URL"]) {
    chatWindow.loadFile(path.join(__dirname, "../renderer/chat/index.html"));
  } else {
    chatWindow.loadFile(path.join(__dirname, "../renderer/chat/index.html"));
  }
  ipcMain.on("send-message", (event, message2) => {
    console.log("Mensaje recibido:", message2);
    const response = `Respuesta predeterminada para: "${message2}"`;
    event.reply("receive-response", response);
  });
}
function createTray() {
  tray = new Tray(path.join(__dirname, "../../assets/images/tray_icon.png"));
  const trayMenu = Menu.buildFromTemplate([
    {
      label: "Abrir aplicación",
      click: () => {
        mainWindow.show();
      }
    },
    {
      label: "Configuración",
      click: () => {
        createSettingsWindow();
      }
    },
    {
      label: "Salir",
      click: () => {
        app.quit();
      }
    }
  ]);
  tray.setContextMenu(trayMenu);
  tray.on(
    "click",
    () => {
      mainWindow.show();
    }
  );
}
