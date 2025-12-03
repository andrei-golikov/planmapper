# FILENAME: gui_loader.py

# GUI Loader with separate console for Stage2/Stage3, Settings button, and window icon

import sys
import os
import subprocess
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QTextEdit, QLabel, QFileDialog, QHBoxLayout
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QThread, Signal

BASE = os.path.dirname(os.path.abspath(__file__))

DEFAULT_CAD_LIST = os.path.join(BASE, "cad_nums.txt")
STOP_FLAG_PATH = os.path.join(BASE, "stop.flag")
CONFIG_PATH = os.path.join(BASE, "config.json")

NORMAL_SCRIPT = os.path.join(BASE, "get_geojson_by_list.py")
SAFE_SCRIPT   = os.path.join(BASE, "safe_downloader.py")  # UNUSED NOW

STAGE1_SCRIPT = os.path.join(BASE, "stage1_make_polygon.py")
STAGE2_SCRIPT = os.path.join(BASE, "stage2_transform.py")
STAGE3_SCRIPT = os.path.join(BASE, "manual_adjust_polygon_good_twistedaxis.py")

PREVIEW_SCRIPT = os.path.join(BASE, "get_interactive_debug_tool.py")

VENV_PY = os.path.join(BASE, ".GetCoordvenv", "Scripts", "python.exe")


class StreamWorker(QThread):
    line_ready = Signal(str)
    finished = Signal(str)

    def __init__(self, script, cad_file=None):
        super().__init__()
        self.script = script
        self.cad_file = cad_file
        self.process = None

    def run(self):
        try:
            if os.path.exists(STOP_FLAG_PATH):
                try: os.remove(STOP_FLAG_PATH)
                except: pass

            env = os.environ.copy()
            if self.cad_file:
                env["CAD_LIST_FILE"] = self.cad_file

            cmd = [VENV_PY, "-u", "-X", "utf8", self.script]

            self.process = subprocess.Popen(
                cmd,
                cwd=BASE,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace"
            )

            for line in self.process.stdout:
                self.line_ready.emit(line.rstrip("\n"))

            self.process.wait()
            self.finished.emit("✔ Готово.")

        except Exception as e:
            self.finished.emit(f"❌ Ошибка: {e}")


class LoaderGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GetCoords GUI")
        # ICON (generic placeholder, user can replace icon.png)
        icon_path = os.path.join(BASE, "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.cad_list_path = DEFAULT_CAD_LIST
        self.worker = None

        layout = QVBoxLayout(self)

        title = QLabel("GetCoords – Управление пайплайном")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # ROW 1 — list selector
        row_list = QHBoxLayout()
        self.path_label = QLabel(f"Список участков: {self.cad_list_path}")
        row_list.addWidget(self.path_label)

        self.btn_pick_list = QPushButton("Выбрать список (*.txt)")
        self.btn_pick_list.clicked.connect(self.pick_list)
        row_list.addWidget(self.btn_pick_list)
        layout.addLayout(row_list)

        # ROW 2 — Downloader + Settings
        dl_row = QHBoxLayout()
        self.btn_normal = QPushButton("Обычная загрузка")
        self.btn_normal.clicked.connect(lambda: self.start_worker(NORMAL_SCRIPT, self.cad_list_path))
        dl_row.addWidget(self.btn_normal)

        # settings replaces "умная загрузка"
        self.btn_settings = QPushButton("Настройки")
        self.btn_settings.clicked.connect(self.open_settings)
        dl_row.addWidget(self.btn_settings)

        self.btn_stop = QPushButton("⛔ STOP (мягкий)")
        self.btn_stop.clicked.connect(self.stop_loading)
        self.btn_stop.setEnabled(False)
        dl_row.addWidget(self.btn_stop)

        layout.addLayout(dl_row)

        # ROW 3 — Stages
        stage_row = QHBoxLayout()

        self.btn_stage1 = QPushButton("Создание сетки")
        self.btn_stage1.clicked.connect(lambda: self.start_worker(STAGE1_SCRIPT))
        stage_row.addWidget(self.btn_stage1)

        self.btn_stage2 = QPushButton("Первоначальная коррекция")
        self.btn_stage2.clicked.connect(self.start_stage2_console)
        stage_row.addWidget(self.btn_stage2)

        self.btn_stage3 = QPushButton("Ручная коррекция")
        self.btn_stage3.clicked.connect(self.start_stage3_console)
        stage_row.addWidget(self.btn_stage3)

        layout.addLayout(stage_row)

        # ROW 4 — Tools
        tool_row = QHBoxLayout()
        self.btn_preview = QPushButton("Preview")
        self.btn_preview.clicked.connect(lambda: self.start_worker(PREVIEW_SCRIPT))
        tool_row.addWidget(self.btn_preview)

        self.btn_output = QPushButton("Открыть output/")
        self.btn_output.clicked.connect(self.open_output)
        tool_row.addWidget(self.btn_output)
        layout.addLayout(tool_row)

        # LOG
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

        # STATUS
        self.status = QLabel("Готов.")
        layout.addWidget(self.status)

    # ===== File list picking =====
    def pick_list(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Выберите список", "", "Text files (*.txt)"
        )
        if file:
            self.cad_list_path = file
            self.path_label.setText(f"Список участков: {file}")
            self.log.append(f"📄 Выбран список: {file}")

    # ===== Start worker (downloader / preview / stage1) =====
    def start_worker(self, script, cad_file=None):
        self.worker = StreamWorker(script, cad_file)
        self.worker.line_ready.connect(self.on_line)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

        self.status.setText("⏳ Работаем…")
        self.btn_stop.setEnabled(script == NORMAL_SCRIPT)

    # ===== Console stages (Stage2 & Stage3) =====
    def start_stage2_console(self):
        self.log.append("▶ Открываю Stage 2 в отдельной консоли...")
        subprocess.Popen(
            [VENV_PY, STAGE2_SCRIPT],
            cwd=BASE,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )

    def start_stage3_console(self):
        self.log.append("▶ Открываю Stage 3 (Manual) в отдельной консоли...")
        subprocess.Popen(
            [VENV_PY, STAGE3_SCRIPT],
            cwd=BASE,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )

    # ===== Output handlers =====
    def on_line(self, text):
        self.log.append(text)

    def on_finished(self, text):
        self.log.append(text)
        self.status.setText("Готово.")
        self.btn_stop.setEnabled(False)

    # ===== Soft stop =====
    def stop_loading(self):
        try:
            with open(STOP_FLAG_PATH, "w", encoding="utf-8") as f:
                f.write("stop\n")
            self.log.append("⛔ Остановка через stop.flag запрошена…")
            self.status.setText("Ждём graceful exit…")
        except Exception as e:
            self.log.append(f"❌ Не удалось создать stop.flag: {e}")

    # ===== Open output folder =====
    def open_output(self):
        path = os.path.join(BASE, "output")
        if os.path.isdir(path):
            subprocess.Popen(["explorer", path])
        else:
            self.log.append("❌ Папка output не найдена.")

    # ===== Settings =====
    def open_settings(self):
        if os.path.exists(CONFIG_PATH):
            os.startfile(CONFIG_PATH)
        else:
            self.log.append("❌ config.json не найден.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = LoaderGUI()
    gui.resize(900, 650)
    gui.show()
    sys.exit(app.exec())

