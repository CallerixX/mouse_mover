import sys
import random
import time
from threading import Thread, Event
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QWidget, QSpinBox, QTextEdit, QScrollArea, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal
import pyautogui


class MouseMoverApp(QMainWindow):
    log_signal = pyqtSignal(str)  # Сигнал для безопасного обновления лога

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mouse Mover")
        self.setGeometry(100, 100, 400, 300)
        self.mode_selector = QComboBox()
        self.init_ui()
        self.moving_thread = None
        self.stop_event = Event()
        self.log_signal.connect(self.update_log)  # Подключаем сигнал к слоту

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()

        # Добавляем элементы управления
        layout.addWidget(self.create_controls())

        # Добавляем лог с прокруткой
        layout.addWidget(self.create_log_widget())

        # Добавляем кнопки
        layout.addWidget(self.create_buttons())

        central_widget.setLayout(layout)

    def create_controls(self):
        container = QWidget()
        layout = QVBoxLayout()

        self.delay_input = QSpinBox()
        self.delay_input.setRange(1, 3600)
        self.delay_input.setValue(60)

        self.offset_input = QSpinBox()
        self.offset_input.setRange(10, 1000)
        self.offset_input.setValue(200)

        self.mode_selector.addItems(["Случайный", "Круг", "Восьмёрка"])
        layout.addWidget(QLabel("Режим движения:"))
        layout.addWidget(self.mode_selector)

        layout.addWidget(QLabel("Задержка (в секундах):"))
        layout.addWidget(self.delay_input)
        layout.addWidget(QLabel("Максимальное смещение по X и Y:"))
        layout.addWidget(self.offset_input)

        container.setLayout(layout)
        return container

    def create_log_widget(self):
        container = QWidget()
        layout = QVBoxLayout()

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(80)  # Фиксированная высота
        self.log_output.setStyleSheet("""
            background-color: #333; 
            color: #eee; 
            padding: 5px;
            border: 1px solid #555;
        """)

        layout.addWidget(QLabel("Лог активности (последние 3 действия):"))
        layout.addWidget(self.log_output)

        container.setLayout(layout)
        return container

    def create_buttons(self):
        container = QWidget()
        layout = QVBoxLayout()

        self.start_button = QPushButton("Запустить")
        self.start_button.clicked.connect(self.start_moving)

        self.stop_button = QPushButton("Остановить")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_moving)

        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)

        container.setLayout(layout)
        return container

    def update_log(self, message):
        """Обновление лога с сохранением последних 3 записей"""
        current_log = self.log_output.toPlainText().split('\n')
        current_log = [line for line in current_log if line.strip() != '']  # Чистим пустые строки

        if len(current_log) >= 3:
            current_log = current_log[-2:]  # Оставляем последние 2 записи

        current_log.append(message)
        self.log_output.setPlainText('\n'.join(current_log))

        # Автопрокрутка вниз
        self.log_output.verticalScrollBar().setValue(
            self.log_output.verticalScrollBar().maximum()
        )

    def move_mouse_randomly(self):
        try:
            delay = self.delay_input.value()
            offset = self.offset_input.value()
            self.log_signal.emit("Начинаем движение мыши...")

            while not self.stop_event.is_set():
                offset_x = random.randint(-offset, offset)
                offset_y = random.randint(-offset, offset)
                pyautogui.moveRel(offset_x, offset_y, duration=0.5)
                self.log_signal.emit(f"Сдвиг: ({offset_x}, {offset_y})")
                time.sleep(delay)

        except Exception as e:
            self.log_signal.emit(f"Ошибка: {str(e)}")

    def start_moving(self):
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.stop_event.clear()
        self.moving_thread = Thread(target=self.move_mouse_randomly, daemon=True)
        self.moving_thread.start()

    def stop_moving(self):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.stop_event.set()
        self.log_signal.emit("Движение остановлено")

    def closeEvent(self, event):
        """Обработчик закрытия окна"""
        self.stop_moving()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MouseMoverApp()
    window.setStyleSheet("""
        QWidget {
            background-color: #222;
            color: #eee;
        }
        QSpinBox {
            padding: 5px;
        }
    """)
    window.show()
    sys.exit(app.exec_())