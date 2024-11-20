import sys
from pynput import keyboard
from queue import Queue
from tempfile import NamedTemporaryFile
import speech_recognition as sr
from faster_whisper import WhisperModel
from PySide6.QtWidgets import QWidget, QLabel, QApplication, QVBoxLayout, QPushButton, QHBoxLayout, QPushButton, QPlainTextEdit, QComboBox, QSlider
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QColor
import torch
import io
from datetime import datetime, timedelta
import traceback
from Glassmorphism import *


class GlobalHotkeyListener:
    def __init__(self, toggle_callback):
        """
        Inicializa el listener global de teclado.
        :param toggle_callback: Función a ejecutar cuando se detecte el atajo.
        """
        self.toggle_callback = toggle_callback
        self.hotkey = keyboard.HotKey(
            keyboard.HotKey.parse("<cmd>+j"), self.on_activate
        )
        self.listener = keyboard.Listener(
            on_press=self.on_press, on_release=self.on_release)
        self.listener.start()

    def on_activate(self):
        """
        Llama al callback cuando se detecta el atajo.
        """
        self.toggle_callback()

    def on_press(self, key):
        """
        Maneja el evento de tecla presionada.
        """
        self.hotkey.press(key)

    def on_release(self, key):
        """
        Maneja el evento de tecla liberada.
        """
        self.hotkey.release(key)


class Worker(QThread):
    transcription_ready = Signal(str)
    tranlation_ready = Signal(str)

    def __init__(self, app):
        super().__init__()
        self.app = app
        # Crea el modelo Whisper una sola vez
        print("Cargando modelo...")
        print(f"Modelo: {self.app.model_name}")
        self.audio_model = WhisperModel(
            self.app.model_name,  device="cuda", compute_type="float16"
        )
        print(f"Modelo cargado: {self.app.model_name}")
        self.last_sample = bytes()

    def run(self):
        while self.app.running:
            try:
                now = datetime.utcnow()
                if not self.app.data_queue.empty():
                    if self.app.phrase_time and now - self.app.phrase_time > timedelta(seconds=self.app.phrase_timeout):
                        self.last_sample = bytes()

                    self.app.phrase_time = now

                    while not self.app.data_queue.empty():
                        data = self.app.data_queue.get()
                        self.last_sample += data

                    audio_data = sr.AudioData(
                        self.last_sample, self.app.source.SAMPLE_RATE, self.app.source.SAMPLE_WIDTH)
                    wav_data = io.BytesIO(audio_data.get_wav_data())

                    with NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                        temp_file_path = temp_file.name
                        temp_file.write(wav_data.read())

                        original_text = ""
                        segments, info = self.audio_model.transcribe(
                            temp_file_path, language="es")
                        for segment in segments:
                            original_text += segment.text

                        translated_text = ""
                        segments, info = self.audio_model.transcribe(
                            temp_file_path, task="translate", language="es")

                        for segment in segments:
                            translated_text += segment.text

                        self.transcription_ready.emit(original_text)
                        self.tranlation_ready.emit(translated_text)

                    self.last_sample = bytes()  # Reinicia last_sample

            except Exception as e:
                print(f"Error en Worker.run: {e}")
                traceback.print_exc()
            finally:
                QThread.msleep(250)  # Espera para no sobrecargar la CPU


class TransparentWindow(QWidget):
    def __init__(self, phrase_timeout=3.0, model_name="large-v2", device_id="0", alpha=0.5):
        super().__init__()

        self.phrase_timeout = phrase_timeout
        self.model_name = model_name
        self.device_id = device_id
        self.alpha = alpha
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.cpu_threads = 1

        print("Using device:", self.device)

        self.settings_window = None

        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        # Fondo totalmente transparente
        self.setStyleSheet(f"background-color: rgba(0, 0, 0, {self.alpha});")

        # Layout principal (horizontal)
        self.layout = QHBoxLayout(self)
        # Elimina los márgenes del layout principal
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Container widget para apilar las etiquetas
        label_container = QWidget(self)
        label_layout = QVBoxLayout(label_container)
        label_layout.setContentsMargins(0, 0, 0, 0)
        label_layout.setSpacing(0)  # Sin espacio entre las etiquetas

        self.transcription_label = QLabel("")
        self.transcription_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont("Arial", 12)
        font.setBold(True)
        self.transcription_label.setFont(font)
        color = QColor("#ddff33")
        self.transcription_label.setStyleSheet(f"color: {color.name()};")
        # Añade al layout vertical
        label_layout.addWidget(self.transcription_label)

        self.translated_label = QLabel("")
        self.translated_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.translated_label.setFont(font)
        self.translated_label.setStyleSheet("color: white;")
        # Añade al layout vertical
        label_layout.addWidget(self.translated_label)

        label_container.setLayout(label_layout)
        # Añade el contenedor al layout principal
        self.layout.addWidget(label_container)

        # Widget para los botones (tamaño fijo)
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        # Sin márgenes en el layout de botones
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(0)
        # tamaño
        button_widget.setFixedWidth(100)

        self.settings_button = QPushButton("⚙️")
        # Tamaño fijo para el botón de configuración
        self.settings_button.setFixedSize(25, 25)
        self.settings_button.clicked.connect(self.open_settings)
        button_layout.addWidget(self.settings_button)

        self.close_button = QPushButton("X")
        self.close_button.setFixedSize(20, 20)
        self.close_button.setStyleSheet("background-color: red; color: white;")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)

        button_widget.setLayout(button_layout)
        self.layout.addWidget(button_widget)  # Añade el widget con los botones

        x, y, width, height = self.calculate_geometry()
        self.setGeometry(x, y, width, height)

        self.data_queue = Queue()
        self.phrase_time = None
        self.last_sample = bytes()
        self.running = True

        self.initialize_speech_recognition()

        self.worker_thread = Worker(self)
        self.worker_thread.transcription_ready.connect(
            self.update_transcription_label)
        self.worker_thread.tranlation_ready.connect(
            self.update_translation_label)
        self.worker_thread.start()

        # Temporizador para ocultar la transcripción y minimizar la ventana
        self.hide_timer = QTimer()
        # Conecta al método hide_if_inactive
        self.hide_timer.timeout.connect(self.hide_if_inactive)
        self.hide_timer.start(10000)  # Verifica cada segundo

        # Registra la hora de la última actividad
        self.last_activity_time = datetime.utcnow()

    def calculate_geometry(self):
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        width = 1000
        height = 40
        x = (screen_geometry.width() - width) // 2
        y = screen_geometry.height() - height - 100  # 100px del borde inferior

        return x, y, width, height

    def initialize_speech_recognition(self):
        self.recorder = sr.Recognizer()
        self.recorder.dynamic_energy_threshold = False
        self.source = sr.Microphone(sample_rate=16000)
        try:
            with self.source:
                self.recorder.adjust_for_ambient_noise(self.source)
        except Exception as e:
            print(f"Error: {e}")
        self.recorder.listen_in_background(self.source, self.record_callback)

    def record_callback(self, recognizer, audio):
        data = audio.get_raw_data()
        self.data_queue.put(data)
        # Actualiza el tiempo de la última actividad
        self.last_activity_time = datetime.utcnow()

    def update_transcription_label(self, text):
        self.transcription_label.setText(text)

    def update_translation_label(self, text):
        self.translated_label.setText(text)

    def open_settings(self):
        if self.settings_window is None:  # Crea la ventana solo si no existe
            self.settings_window = SettingsWindow(self)

        self.settings_window.show()  # Muestra la ventana (o la trae al frente si ya existe)

    def closeEvent(self, event):  # Redefine closeEvent
        self.running = False    # Detiene el bucle en el hilo Worker
        self.worker_thread.wait()  # Espera a que el hilo termine

        # Cierra la ventana principal al final
        event.accept()
        sys.exit()

    def update_translation_label(self, text):
        self.translated_label.setText(text)
        # Actualiza el tiempo de la última actividad
        self.last_activity_time = datetime.utcnow()
        # Restaura la ventana si estaba minimizada
        self.setWindowState(Qt.WindowState.WindowActive)
        self.show()  # Muestra la ventana

    def hide_if_inactive(self):
        """
        Oculta las etiquetas y minimiza la ventana si no ha habido actividad durante el tiempo de espera.
        """
        time_since_last_activity = datetime.utcnow() - self.last_activity_time
        # Establece un tiempo límite, por ejemplo, 30 segundos
        if time_since_last_activity > timedelta(seconds=self.phrase_timeout):
            self.transcription_label.setText("")
            self.translated_label.setText("")
            self.setWindowState(Qt.WindowState.WindowMinimized)  # Minimiza
            self.hide()  # Oculta


class ChatWindow(QtWidgets.QWidget):
    submitted = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.WindowType.WindowStaysOnTopHint |
                            QtCore.Qt.WindowType.FramelessWindowHint |
                            QtCore.Qt.WindowType.Tool)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)


        backgrounds = [
            {
                "background-color": QtGui.QColor(47, 47, 47, 100),
                "opacity": 1
            }
        ]

        # Widget contenedor para el BackDropWrapper
        container = QtWidgets.QWidget(self)
        container_layout = QtWidgets.QVBoxLayout(container)
        container_layout.setContentsMargins(10, 10, 10, 10)

        # Campo de texto
        self.text_edit = QtWidgets.QTextEdit()
        self.text_edit.viewport()
        self.text_edit.setMarkdown("")
     
        self.text_edit.setPlaceholderText("Escribe aquí...")
        self.text_edit.setFixedWidth(400)
        self.text_edit.setMinimumHeight(150)
        self.text_edit.textChanged.connect(self.setTextEdit)

        container_layout.addWidget(self.text_edit)

        # Botón de enviar
        send_button = QtWidgets.QPushButton("Enviar")
        send_button.setStyleSheet("""
            border: none;
            background-color: rgba(255, 255, 255, 0.3);
            color: white;
            font-size: 14px;
            padding: 5px 10px;
            border-radius: 5px;
            margin-top: 10px;
        """)
        send_button.clicked.connect(self.submit_text)
        container_layout.addWidget(
            send_button, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

        # Envolver con BackDropWrapper
        self.backdrop = BackDropWrapper(container, 40, 10, backgrounds)
        # self.backdrop.enable_shine_animation(
        #     angle=135, color=QtGui.QColor(255, 255, 255, 90))
        # self.backdrop.enable_move_animation(offset=(0, -30))

        # Layout principal de ChatWindow
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.backdrop)

        # Ajustar tamaño después de añadir widgets
        self.adjustSize()

        # Centrar en la pantalla
        screen_geometry = QtWidgets.QApplication.primaryScreen().availableGeometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)
        self.hide()

    def setTextEdit(self):
        self.text_edit.setMarkdown(self.text_edit.toPlainText())

    def submit_text(self):
        """
        Envía el texto ingresado y oculta la ventana.
        """
        text = self.text_edit.toPlainText().strip()
        if text:
            self.submitted.emit(text)
            self.text_edit.clear()
            self.hide()

    def toggle(self):
        """
        Alterna la visibilidad de la ventana.
        """
        if self.isVisible():
            self.hide()
        else:
            self.show()

    def focusOutEvent(self, event):
        """
        Oculta la ventana cuando pierde el foco.
        """
        self.hide()
        event.accept()


class SettingsWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        self.setWindowTitle("Configuración")
        self.setWindowModality(Qt.WindowModality.NonModal)  # No modal
        # Quitar transparencia
        self.setWindowOpacity(1.0)

        layout = QVBoxLayout(self)

        # Transparencia
        self.transparency_label = QLabel("Transparencia:")
        self.transparency_slider = QSlider(Qt.Orientation.Horizontal)
        self.transparency_slider.setRange(0, 100)
        # transparency_slider.setValue(int(self.parent.alpha * 100)) # Valor inicial
        # transparency_slider.valueChanged.connect(self.change_transparency)
        layout.addWidget(self.transparency_label)
        layout.addWidget(self.transparency_slider)

        # Modelos
        models_label = QLabel("Modelo:")
        layout.addWidget(models_label)

        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "tiny.en", "base", "base.en",
                                   "small", "small.en", "distil-small.en", "medium", "medium.en", "distil-medium.en", "large-v1",
                                   "large-v2", "large-v3", "large", "distil-large-v2", "distil-large-v3", "large-v3-turbo", "turbo"]
                                  )
        self.model_combo.setCurrentText(
            self.parent.model_name)  # Modelo actual seleccionado
        layout.addWidget(self.model_combo)

        # Botón Guardar
        save_button = QPushButton("Guardar")
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)

        self.setLayout(layout)

        # Configura el valor del slider al crear la ventana
        self.transparency_slider.setValue(int(self.parent.alpha * 100))

        # Conecta el cambio de valor del slider con el método change_transparency
        self.transparency_slider.valueChanged.connect(self.change_transparency)

    def change_transparency(self, value):
        alpha = value / 100.0
        self.parent.setStyleSheet(
            f"background-color: rgba(0, 0, 0, {alpha});")  # Actualiza el estilo

    def save_settings(self):
        self.parent.model_name = self.model_combo.currentText()
        self.hide()


class MainWindow(QWidget):
    def __init__(self,  *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.transcription_window = TransparentWindow(self)
        self.chat_window = ChatWindow()  # No pasar self como parent
        self.chat_window.submitted.connect(self.process_text)

        # self.transcription_window.show()

        # Inicia el listener global para capturar Windows+J
        self.hotkey_listener = GlobalHotkeyListener(self.chat_window.toggle)

    def process_text(self, text):
        # Aquí procesas el texto con la IA
        print(f"Texto recibido: {text}")
        # ... lógica para procesar el texto con la IA ...
        # Ejemplo de cómo mostrar el texto en la ventana de transcripción
        self.transcription_window.update_transcription_label(text)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.chat_window.show()

    with open("style.qss", "r") as f:
        _style = f.read()
        app.setStyleSheet(_style)

    app.exec()
