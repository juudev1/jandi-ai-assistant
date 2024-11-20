const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
    sendMessage: (message) => ipcRenderer.send("send-message", message),
    onReceiveResponse: (callback) =>
        ipcRenderer.on("receive-response", (event, response) => callback(response)),
});