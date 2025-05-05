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
    QSystemTrayIcon, QMenu, QHBoxLayout, QMessageBox, QShortcut,
    QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QSettings
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5 import QtCore
import pyautogui
import platform
import subprocess
import os
import zipfile
import shutil

class MouseMoverApp(QMainWindow):
    log_signal = pyqtSignal(str)
    update_available = pyqtSignal(bool, str)

    def __init__(self):
        super().__init__()
        # Отключение функции безопасности PyAutoGUI (с предупреждением в логах)
        self.original_failsafe = pyautogui.FAILSAFE
        
        self.settings = QSettings("YourCompany", "MouseMoverPro")
        self.setWindowTitle("Mouse Mover Pro")
        self.setGeometry(100, 100, 450, 500)  # Немного увеличен размер окна
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
            QTextEdit, QSpinBox, QPushButton, QCheckBox {
                background-color: #3D3D3D;
                color: #FFFFFF;
                border: 1px solid #555;
            }
            QLabel, QMessageBox QLabel, QCheckBox {
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
            QTextEdit, QComboBox, QSpinBox, QPushButton, QCheckBox {
                background-color: #F0F0F0;
                color: #000000;
                border: 1px solid #CCC;
            }
            QLabel, QCheckBox {
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
            QTextEdit, QSpinBox, QPushButton, QCheckBox {
                background-color: #A0A0A0;
                color: #FFFFFF;
                border: 1px solid #666;
            }   
            QLabel, QMessageBox QLabel, QCheckBox {
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
            self.settings.value("offset", 100, int)  # Уменьшен по умолчанию
        )
        
        # Загрузка настройки безопасности PyAutoGUI
        disable_failsafe = self.settings.value("disable_failsafe", False, bool)
        self.failsafe_checkbox.setChecked(disable_failsafe)
        self.toggle_failsafe(disable_failsafe)
        
        # Загрузка настройки проверки границ экрана
        check_bounds = self.settings.value("check_bounds", True, bool)
        self.bounds_checkbox.setChecked(check_bounds)

    def closeEvent(self, event):
        self.settings.setValue("theme", self.theme_selector.currentText())
        super().closeEvent(event)

    def start_moving(self):
        self.stop_event.clear()
        self.moving_thread = Thread(target=self.move_mouse_randomly)
        self.moving_thread.daemon = True  # Сделаем поток демоном, чтобы не блокировать выход
        self.moving_thread.start()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.update_status(True)
        self.log_signal.emit("Движение начато")

    def stop_moving(self):
        if self.moving_thread and self.moving_thread.is_alive():
            self.stop_event.set()
            # Даем немного времени для остановки потока
            self.moving_thread.join(1.0)
            
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.update_status(False)
        self.log_signal.emit("Движение остановлено")
        self.moving_thread = None

    def update_log(self, message):
        self.log_display.append(f"[{time.strftime('%H:%M:%S')}] {message}")
        # Прокрутка вниз для отображения последних сообщений
        self.log_display.verticalScrollBar().setValue(
            self.log_display.verticalScrollBar().maximum()
        )

    def toggle_failsafe(self, state):
        if state:
            pyautogui.FAILSAFE = False
            self.log_signal.emit("ВНИМАНИЕ: Защита PyAutoGUI отключена")
        else:
            pyautogui.FAILSAFE = True
            self.log_signal.emit("Защита PyAutoGUI включена")
        self.settings.setValue("disable_failsafe", state)

    def create_mode_controls(self):
        container = QWidget()
        layout = QVBoxLayout()

        # Выбор темы
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Тема:"))
        self.theme_selector = QComboBox()
        self.theme_selector.addItems(["Тёмная", "Светлая", "Серая"])
        self.theme_selector.currentTextChanged.connect(self.change_theme)
        theme_layout.addWidget(self.theme_selector)
        layout.addLayout(theme_layout)

        # Режим движения
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Режим движения:"))
        self.mode_selector = QComboBox()
        self.mode_selector.addItems(["Случайный", "Круг", "Восьмёрка", "Безопасный"])
        mode_layout.addWidget(self.mode_selector)
        layout.addLayout(mode_layout)

        # Задержка и смещение
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Задержка (секунды):"))
        self.delay_input = QSpinBox()
        self.delay_input.setRange(1, 3600)
        delay_layout.addWidget(self.delay_input)
        layout.addLayout(delay_layout)

        offset_layout = QHBoxLayout()
        offset_layout.addWidget(QLabel("Макс. смещение:"))
        self.offset_input = QSpinBox()
        self.offset_input.setRange(10, 500)  # Уменьшен максимум
        offset_layout.addWidget(self.offset_input)
        layout.addLayout(offset_layout)

        # Чекбокс для отключения защиты PyAutoGUI
        self.failsafe_checkbox = QCheckBox("Отключить защиту PyAutoGUI (не рекомендуется)")
        self.failsafe_checkbox.stateChanged.connect(self.toggle_failsafe)
        layout.addWidget(self.failsafe_checkbox)
        
        # Чекбокс для проверки границ экрана
        self.bounds_checkbox = QCheckBox("Проверять границы экрана")
        self.bounds_checkbox.setChecked(True)
        layout.addWidget(self.bounds_checkbox)

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
        
        # Проверяем существование файла иконки
        icon_path = os.path.join(base_path, "mouse_mover_icon.ico")
        if not os.path.exists(icon_path):
            self.log_signal.emit(f"Файл иконки не найден: {icon_path}")
            # Используем дефолтную иконку Qt если файл не найден
            self.tray_icon.setIcon(QIcon.fromTheme("input-mouse"))
        else:
            self.tray_icon.setIcon(QIcon(icon_path))

        menu = QMenu()
        show_action = menu.addAction("Показать")
        show_action.triggered.connect(self.show_normal)
        
        # Добавляем переключатели старт/стоп в трей-меню
        start_action = menu.addAction("Запустить")
        start_action.triggered.connect(self.start_moving)
        
        stop_action = menu.addAction("Остановить")
        stop_action.triggered.connect(self.stop_moving)
        
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
        try:
            if platform.system() == "Windows":
                # ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000002)
            elif platform.system() == "Darwin":
                subprocess.Popen(["caffeinate", "-dimsu"])
            else:
                try:
                    subprocess.Popen(["systemd-inhibit", "--what=idle", "--mode=block", "--why='MouseMover'"])
                except:
                    self.log_signal.emit("Не удалось предотвратить сон на Linux")
        except Exception as e:
            self.log_signal.emit(f"Ошибка при настройке предотвращения сна: {str(e)}")

    def check_update_initial(self):
        if self.settings.value("check_updates", True, bool):
            self.check_update()

    def check_update(self):
        try:
            try:
                with open("version.txt", "r") as f:
                    current_version = f.read().strip()
            except FileNotFoundError:
                current_version = "v1.0"
                self.log_signal.emit("Файл version.txt не найден, используется версия по умолчанию v1.0")

            response = requests.get(
                "https://api.github.com/repos/CallerixX/mouse_mover/releases/latest",
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            latest_version = data.get('tag_name', 'v1.0')
            
            if latest_version > current_version:
                self.update_available.emit(True, latest_version)
            else:
                self.update_available.emit(False, "")
        except requests.exceptions.RequestException as e:
            self.log_signal.emit(f"Ошибка соединения: {str(e)}")
        except Exception as e:
            self.log_signal.emit(f"Ошибка проверки обновлений: {str(e)}")

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
            self.log_signal.emit("Начато скачивание обновления...")
            
            # Получаем URL архива
            response = requests.get(
                "https://api.github.com/repos/CallerixX/mouse_mover/releases/latest"
            )
            response.raise_for_status()
            assets = response.json()["assets"]
            download_url = assets[0]["browser_download_url"]

            # Скачиваем архив
            self.log_signal.emit("Скачивание архива...")
            r = requests.get(download_url, stream=True)
            with open("update.zip", "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            self.log_signal.emit("Архив успешно скачан")

            # Распаковываем архив
            self.log_signal.emit("Распаковка обновления...")
            with zipfile.ZipFile("update.zip", "r") as zip_ref:
                zip_ref.extractall("update_temp")
            self.log_signal.emit("Архив успешно распакован")

            # Заменяем файлы
            self.log_signal.emit("Копирование новых файлов...")
            for root, _, files in os.walk("update_temp"):
                for file in files:
                    src_path = os.path.join(root, file)
                    rel_path = os.path.relpath(src_path, "update_temp")
                    dst_path = os.path.join(os.getcwd(), rel_path)
                    
                    # Проверяем, не является ли файл текущим исполняемым скриптом
                    if file == os.path.basename(sys.argv[0]):
                        self.log_signal.emit(f"Пропуск копирования текущего скрипта: {file}")
                        continue
                    
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    try:
                        shutil.copy2(src_path, dst_path)
                        self.log_signal.emit(f"Обновлен файл: {rel_path}")
                    except PermissionError:
                        self.log_signal.emit(f"Ошибка: Нет прав для замены файла {rel_path}")
                    except Exception as e:
                        self.log_signal.emit(f"Ошибка при копировании файла {rel_path}: {str(e)}")

            # Очищаем временные файлы
            self.log_signal.emit("Очистка временных файлов...")
            shutil.rmtree("update_temp", ignore_errors=True)
            os.remove("update.zip")
            self.log_signal.emit("Временные файлы удалены")

            # Перезапуск приложения
            self.log_signal.emit("Перезапуск приложения...")
            subprocess.Popen([sys.executable, sys.argv[0]])
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
        # Сохраняем все настройки перед закрытием
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("mode", self.mode_selector.currentIndex())
        self.settings.setValue("delay", self.delay_input.value())
        self.settings.setValue("offset", self.offset_input.value())
        self.settings.setValue("disable_failsafe", self.failsafe_checkbox.isChecked())
        self.settings.setValue("check_bounds", self.bounds_checkbox.isChecked())
        
        # Восстанавливаем настройку PyAutoGUI failsafe
        pyautogui.FAILSAFE = self.original_failsafe
        
        # Скрываем в трей при закрытии
        if self.tray_icon.isVisible() and self.settings.value("minimize_on_close", True, bool):
            self.hide()
            event.ignore()
        else:
            self.tray_icon.hide()
            event.accept()

    def clean_exit(self):
        self.stop_moving()
        QApplication.quit()

    def is_within_safe_bounds(self, dx, dy):
        """Проверяет, что новая позиция курсора будет в безопасных пределах экрана"""
        if not self.bounds_checkbox.isChecked():
            return True
            
        # Получаем текущую позицию курсора и размеры экрана
        current_x, current_y = pyautogui.position()
        screen_width, screen_height = pyautogui.size()
        
        # Определяем безопасную зону (отступ от края экрана)
        safe_margin = 50
        
        # Рассчитываем новую позицию
        new_x = current_x + dx
        new_y = current_y + dy
        
        # Проверяем, что новая позиция находится в безопасной зоне
        return (safe_margin < new_x < screen_width - safe_margin and 
                safe_margin < new_y < screen_height - safe_margin)

    def move_mouse_randomly(self):
        try:
            mode = self.mode_selector.currentText()
            delay = self.delay_input.value()
            offset = self.offset_input.value()

            if mode == "Круг":
                self.circular_movement(offset // 2, delay)
            elif mode == "Восьмёрка":
                self.figure_eight(offset // 2, delay)
            elif mode == "Безопасный":
                self.safe_movement(offset, delay)
            else:
                self.random_movement(offset, delay)

        except Exception as e:
            self.log_signal.emit(f"Ошибка в потоке движения: {str(e)}")
            # Восстанавливаем кнопки чтобы можно было перезапустить
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.update_status(False)

    def circular_movement(self, radius, delay):
        try:
            angle = 0
            center_x, center_y = pyautogui.position()
            
            while not self.stop_event.is_set():
                # Вычисляем новую позицию
                x = center_x + radius * math.cos(math.radians(angle))
                y = center_y + radius * math.sin(math.radians(angle))
                
                # Проверяем границы экрана если включена опция
                screen_width, screen_height = pyautogui.size()
                if self.bounds_checkbox.isChecked():
                    safe_margin = 50
                    x = max(safe_margin, min(x, screen_width - safe_margin))
                    y = max(safe_margin, min(y, screen_height - safe_margin))
                
                # Двигаем мышь к абсолютной позиции
                pyautogui.moveTo(int(x), int(y), duration=0.2)
                
                # Увеличиваем угол для следующего шага
                angle = (angle + 15) % 360
                
                # Пауза
                for _ in range(int(delay)):
                    if self.stop_event.is_set():
                        break
                    time.sleep(1)
        except Exception as e:
            self.log_signal.emit(f"Ошибка при движении по кругу: {str(e)}")

    def figure_eight(self, radius, delay):
        try:
            theta = 0
            center_x, center_y = pyautogui.position()
            
            while not self.stop_event.is_set():
                # Вычисляем новую позицию
                x = center_x + radius * math.sin(math.radians(theta))
                y = center_y + radius * math.sin(math.radians(2 * theta)) / 2
                
                # Проверяем границы экрана если включена опция
                screen_width, screen_height = pyautogui.size()
                if self.bounds_checkbox.isChecked():
                    safe_margin = 50
                    x = max(safe_margin, min(x, screen_width - safe_margin))
                    y = max(safe_margin, min(y, screen_height - safe_margin))
                
                # Двигаем мышь к абсолютной позиции
                pyautogui.moveTo(int(x), int(y), duration=0.2)
                
                # Увеличиваем угол для следующего шага
                theta = (theta + 10) % 360
                
                # Пауза
                for _ in range(int(delay)):
                    if self.stop_event.is_set():
                        break
                    time.sleep(1)
        except Exception as e:
            self.log_signal.emit(f"Ошибка при движении по восьмёрке: {str(e)}")

    def random_movement(self, offset, delay):
        try:
            while not self.stop_event.is_set():
                # Генерируем случайное смещение
                dx = random.randint(-offset, offset)
                dy = random.randint(-offset, offset)
                
                # Проверяем, что новая позиция будет в безопасных пределах экрана
                attempts = 0
                while not self.is_within_safe_bounds(dx, dy) and attempts < 10:
                    dx = random.randint(-offset, offset)
                    dy = random.randint(-offset, offset)
                    attempts += 1
                
                if attempts == 10:
                    self.log_signal.emit("Не удалось найти безопасное направление, пропускаем ход")
                    time.sleep(delay)
                    continue
                
                # Двигаем мышь
                try:
                    pyautogui.moveRel(dx, dy, duration=0.5)
                    self.log_signal.emit(f"Случайное движение: {dx}, {dy}")
                except Exception as e:
                    self.log_signal.emit(f"Ошибка при движении мыши: {str(e)}")
                
                # Разделяем задержку на мелкие интервалы для быстрой проверки stop_event
                for _ in range(int(delay)):
                    if self.stop_event.is_set():
                        break
                    time.sleep(1)
        except Exception as e:
            self.log_signal.emit(f"Ошибка в случайном движении: {str(e)}")

    def safe_movement(self, offset, delay):
        """Безопасный режим движения с небольшими перемещениями"""
        try:
            # Получаем размеры экрана
            screen_width, screen_height = pyautogui.size()
            
            # Определяем безопасную зону центра экрана
            safe_zone_x = screen_width // 2
            safe_zone_y = screen_height // 2
            safe_radius = min(screen_width, screen_height) // 4
            
            while not self.stop_event.is_set():
                # Получаем текущую позицию
                current_x, current_y = pyautogui.position()
                
                # Если курсор далеко от центра, возвращаем его ближе к центру
                distance_to_center = math.sqrt((current_x - safe_zone_x)**2 + (current_y - safe_zone_y)**2)
                
                if distance_to_center > safe_radius:
                    # Перемещаем мышь ближе к центру
                    angle = math.atan2(safe_zone_y - current_y, safe_zone_x - current_x)
                    move_x = int(20 * math.cos(angle))
                    move_y = int(20 * math.sin(angle))
                    self.log_signal.emit(f"Возвращение к центру: {move_x}, {move_y}")
                else:
                    # Небольшое случайное движение вокруг текущей позиции
                    move_x = random.randint(-10, 10)
                    move_y = random.randint(-10, 10)
                
                # Проверка границ экрана
                new_x = current_x + move_x
                new_y = current_y + move_y
                
                safe_margin = 50
                if new_x < safe_margin or new_x > screen_width - safe_margin:
                    move_x = -move_x  # Инвертируем направление по x
                    
                if new_y < safe_margin or new_y > screen_height - safe_margin:
                    move_y = -move_y  # Инвертируем направление по y
                
                # Двигаем мышь
                pyautogui.moveRel(move_x, move_y, duration=0.3)
                
                # Разделяем задержку на мелкие интервалы для быстрой проверки stop_event
                for _ in range(int(delay)):
                    if self.stop_event.is_set():
                        break
                    time.sleep(1)
        except Exception as e:
            self.log_signal.emit(f"Ошибка в безопасном режиме: {str(e)}")


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        window = MouseMoverApp()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        # Запись фатальной ошибки в файл
        with open("mouse_mover_error.log", "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - КРИТИЧЕСКАЯ ОШИБКА: {str(e)}\n")
        raise
