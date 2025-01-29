import sys
import random
import time
import math
import ctypes
import requests
from threading import Thread, Event
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QLabel,
    QPushButton, QWidget, QSpinBox, QTextEdit, QComboBox,
    QSystemTrayIcon, QMenu, QHBoxLayout, QMessageBox, QShortcut
)
from PyQt5.QtCore import Qt, pyqtSignal, QSettings
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5 import QtCore
import pyautogui
import platform
import subprocess
import os

class MouseMoverApp(QMainWindow):
    log_signal = pyqtSignal(str)
    update_available = pyqtSignal(bool, str)

    def __init__(self):
        super().__init__()
        self.settings = QSettings("YourCompany", "MouseMoverPro")
        self.setWindowTitle("Mouse Mover Pro")
        self.setGeometry(100, 100, 450, 400)
        self.init_ui()
        self.load_settings()
        self.moving_thread = None
        self.stop_event = Event()
        self.log_signal.connect(self.update_log)
        self.update_available.connect(self.handle_update)

        self.init_tray_icon()
        self.setup_hotkeys()
        self.prevent_sleep()
        self.check_update_initial()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()

        # Статус индикатор
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(20, 20)
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("Статус:"))
        status_layout.addWidget(self.status_indicator)
        status_layout.addStretch()

        # Элементы управления
        layout.addLayout(status_layout)
        layout.addWidget(self.create_mode_controls())
        layout.addWidget(self.create_log_widget())
        layout.addWidget(self.create_buttons())

        central_widget.setLayout(layout)
        self.update_status(False)

    def create_log_widget(self):
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        return self.log_display

    def change_theme(self, theme_name):
        if theme_name == "Тёмная":
            self.set_dark_theme()
        elif theme_name == "Светлая":
            self.set_light_theme()
        else:
            self.set_gray_theme()
        self.settings.setValue("theme", theme_name)

    def set_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow, QMessageBox {
                background-color: #2D2D2D;
                color: #FFFFFF;
            }
            QComboBox, QComboBox QAbstractItemView {
                background-color: #3D3D3D;
                color: #FFFFFF;
                border: 1px solid #555;
                selection-background-color: #555;
            }
            QComboBox::drop-down {
                border-color: #555;
            }
            QTextEdit, QSpinBox, QPushButton {
                background-color: #3D3D3D;
                color: #FFFFFF;
                border: 1px solid #555;
            }
            QLabel, QMessageBox QLabel {
                color: #FFFFFF;
            }
            QMessageBox QPushButton {
                background-color: #3D3D3D;
                color: #FFFFFF;
                padding: 5px 10px;
            }
        """)

    def set_light_theme(self):
        self.setStyleSheet("""
            QMainWindow, QMessageBox {
                background-color: #FFFFFF;
                color: #000000;
            }
            QTextEdit, QComboBox, QSpinBox, QPushButton {
                background-color: #F0F0F0;
                color: #000000;
                border: 1px solid #CCC;
            }
            QLabel {
                color: #000000;
            }
            QMessageBox QPushButton {
            background-color: #FFFFFF;
            color: #000000;
            padding: 5px 10px;
            }
        """)

    def set_gray_theme(self):
        self.setStyleSheet("""
            QMainWindow, QMessageBox {
                background-color: #808080;
                color: #FFFFFF;
            }
            QComboBox, QComboBox QAbstractItemView {
                background-color: #A0A0A0;
                color: #FFFFFF;
                border: 1px solid #666
                selection-background-color: #666;
             }
            QComboBox::drop-down {
                border-color: #666;
            }
            QTextEdit, QSpinBox, QPushButton {
                background-color: #A0A0A0;
                color: #FFFFFF;
                border: 1px solid #666;
            }   
            QLabel, QMessageBox QLabel {
                color: #FFFFFF;
            }
            QMessageBox QPushButton {
                background-color: #808080;
                color: #FFFFFF;
                padding: 5px 10px;
            }
        """)

    def load_settings(self):
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        # Загрузка темы
        theme = self.settings.value("theme", "Тёмная")
        self.theme_selector.setCurrentText(theme)
        self.change_theme(theme)

        self.mode_selector.setCurrentIndex(
            self.settings.value("mode", 0, int)
        )
        self.delay_input.setValue(
            self.settings.value("delay", 60, int)
        )
        self.offset_input.setValue(
            self.settings.value("offset", 200, int)
        )
    def closeEvent(self, event):
        self.settings.setValue("theme", self.theme_selector.currentText())
        super().closeEvent(event)

    def start_moving(self):
        self.stop_event.clear()
        self.moving_thread = Thread(target=self.move_mouse_randomly)
        self.moving_thread.start()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.update_status(True)
        self.log_signal.emit("Движение начато")

    def stop_moving(self):
        self.stop_event.set()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.update_status(False)
        self.log_signal.emit("Движение остановлено")
        self.moving_thread = None

    def update_log(self, message):
        self.log_display.append(f"[{time.strftime('%H:%M:%S')}] {message}")

    def create_mode_controls(self):
        container = QWidget()
        layout = QVBoxLayout()

        # Выбор темы
        self.theme_selector = QComboBox()
        self.theme_selector.addItems(["Тёмная", "Светлая", "Серая"])
        self.theme_selector.currentTextChanged.connect(self.change_theme)

        # Режим движения
        self.mode_selector = QComboBox()
        self.mode_selector.addItems(["Случайный", "Круг", "Восьмёрка"])

        # Задержка и смещение
        self.delay_input = QSpinBox()
        self.delay_input.setRange(1, 3600)
        self.offset_input = QSpinBox()
        self.offset_input.setRange(10, 1000)

        # Добавление элементов в layout
        layout.addWidget(QLabel("Тема:"))
        layout.addWidget(self.theme_selector)
        layout.addWidget(QLabel("Режим движения:"))
        layout.addWidget(self.mode_selector)
        layout.addWidget(QLabel("Задержка (секунды):"))
        layout.addWidget(self.delay_input)
        layout.addWidget(QLabel("Макс. смещение:"))
        layout.addWidget(self.offset_input)

        container.setLayout(layout)
        return container

        layout.addWidget(QLabel("Режим движения:"))
        layout.addWidget(self.mode_selector)
        layout.addWidget(QLabel("Задержка (секунды):"))
        layout.addWidget(self.delay_input)
        layout.addWidget(QLabel("Макс. смещение:"))
        layout.addWidget(self.offset_input)

        container.setLayout(layout)
        return container

    def create_buttons(self):
        container = QWidget()
        layout = QHBoxLayout()

        self.start_button = QPushButton("Запуск (Ctrl+S)")
        self.start_button.clicked.connect(self.start_moving)

        self.stop_button = QPushButton("Стоп (Ctrl+Q)")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_moving)

        self.update_button = QPushButton("Проверить обновления")
        self.update_button.clicked.connect(self.check_update)

        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)
        layout.addWidget(self.update_button)

        container.setLayout(layout)
        return container

    def init_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(__file__)
        icon_path = os.path.join(base_path, "mouse_mover_icon.ico")
        self.tray_icon.setIcon(QIcon(icon_path))

        menu = QMenu()
        show_action = menu.addAction("Показать")
        show_action.triggered.connect(self.show_normal)
        menu.addSeparator()
        exit_action = menu.addAction("Выход")
        exit_action.triggered.connect(self.clean_exit)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_normal()

    def show_normal(self):
        self.show()
        self.setWindowState(self.windowState() & ~QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive)
        self.activateWindow()

    def setup_hotkeys(self):
        self.start_hotkey = QShortcut(QKeySequence("Ctrl+S"), self)
        self.start_hotkey.activated.connect(self.start_moving)

        self.stop_hotkey = QShortcut(QKeySequence("Ctrl+Q"), self)
        self.stop_hotkey.activated.connect(self.stop_moving)

    def prevent_sleep(self):
        if platform.system() == "Windows":
            # ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000002)
        elif platform.system() == "Darwin":
            subprocess.Popen(["caffeinate", "-dimsu"])
        else:
            try:
                subprocess.Popen(["systemd-inhibit", "--what=idle", "--mode=block", "--why='MouseMover'"])
            except:
                pass

    def check_update_initial(self):
        if self.settings.value("check_updates", True, bool):
            self.check_update()

    def check_update(self):
        try:
            response = requests.get(
                "https://api.github.com/repos/CallerixX/mouse_mover/releases/latest",
                timeout=5
            )
            response.raise_for_status()  # Проверка HTTP статуса
            data = response.json()
            latest_version = data.get('tag_name', 'v1.0')
            current_version = "v1.0"
            if latest_version > current_version:
                self.update_available.emit(True, latest_version)
            else:
                self.update_available.emit(False, "")
        except requests.exceptions.HTTPError as e:
            self.log_signal.emit(f"Ошибка HTTP: {str(e)}")
        except Exception as e:
            self.log_signal.emit(f"Ошибка: {str(e)}")

    def handle_update(self, available, version):
        if available:
            reply = QMessageBox.question(
                self, 'Обновление доступно',
                f"Доступна новая версия {version}. Обновить сейчас?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.perform_update()
        else:
            QMessageBox.information(self, 'Обновлений нет', "У вас установлена последняя версия")

    def perform_update(self):
        try:
            # Скачать релиз
            response = requests.get(
                "https://api.github.com/repos/CallerixX/mouse_mover/releases/latest"
            )
            assets = response.json()["assets"]
            download_url = assets[0]["browser_download_url"]

            # Скачать и заменить файлы
            self.log_signal.emit("Начато скачивание обновления...")
            os.system(f"curl -L {download_url} -o update.zip")
            os.system("tar -xf update.zip --overwrite")

            # Перезапуск
            self.log_signal.emit("Перезапуск приложения...")
            os.startfile(sys.executable)
            QApplication.quit()

        except Exception as e:
            self.log_signal.emit(f"Ошибка обновления: {str(e)}")

    def update_status(self, active):
        color = "#00FF00" if active else "#FF0000"
        self.status_indicator.setStyleSheet(f"""
            background-color: {color};
            border-radius: 10px;
            border: 2px solid #fff;
        """)

    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("mode", self.mode_selector.currentIndex())
        self.settings.setValue("delay", self.delay_input.value())
        self.settings.setValue("offset", self.offset_input.value())
        self.tray_icon.hide()
        event.accept()

    def clean_exit(self):
        self.stop_moving()
        QApplication.quit()

    def move_mouse_randomly(self):
        try:
            mode = self.mode_selector.currentText()
            delay = self.delay_input.value()
            offset = self.offset_input.value()

            if mode == "Круг":
                self.circular_movement(offset // 2, delay)
            elif mode == "Восьмёрка":
                self.figure_eight(offset // 2, delay)
            else:
                self.random_movement(offset, delay)

        except Exception as e:
            self.log_signal.emit(f"Ошибка: {str(e)}")

    def circular_movement(self, radius, delay):
        angle = 0
        while not self.stop_event.is_set():
            x = radius * math.cos(math.radians(angle))
            y = radius * math.sin(math.radians(angle))
            pyautogui.moveRel(x, y, duration=0.2)  # Уменьшена длительность движения
            angle = (angle + 30) % 360  # Увеличен шаг угла
            time.sleep(delay)

    def figure_eight(self, radius, delay):
        theta = 0
        while not self.stop_event.is_set():
            x = radius * math.sin(math.radians(theta))
            y = radius * math.sin(math.radians(2 * theta)) / 2
            pyautogui.moveRel(x, y, duration=0.2)  # Уменьшена длительность
            theta = (theta + 10) % 360  # Увеличен шаг
            time.sleep(delay)

    def random_movement(self, offset, delay):
        while not self.stop_event.is_set():
            dx = random.randint(-offset, offset)
            dy = random.randint(-offset, offset)
            pyautogui.moveRel(dx, dy, duration=0.5)
            self.log_signal.emit(f"Случайное: {dx}, {dy}")
            time.sleep(delay)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MouseMoverApp()
    window.show()
    sys.exit(app.exec_())
