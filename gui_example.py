# FILENAME: gui_example.py

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel
)
import subprocess
import sys

class GeoGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GeoJSON Downloader")

        self.layout = QVBoxLayout(self)

        self.label = QLabel("Выбери файл со списком кадастровых номеров")
        self.layout.addWidget(self.label)

        self.btn_load = QPushButton("Выбрать файл")
        self.btn_load.clicked.connect(self.pick_file)
        self.layout.addWidget(self.btn_load)

        self.btn_start = QPushButton("Скачать участки")
        self.btn_start.clicked.connect(self.run_downloader)
        self.layout.addWidget(self.btn_start)

        self.selected_file = None

    def pick_file(self):
        file, _ = QFileDialog.getOpenFileName(
            self,
            "Выбери файл",
            "",
            "Text files (*.txt)"
        )
        if file:
            self.selected_file = file
            self.label.setText(f"Выбран: {file}")

    def run_downloader(self):
        if not self.selected_file:
            self.label.setText("Ошибка: файл не выбран")
            return

        subprocess.Popen(["python", "get_geojson_by_list.py"])
        self.label.setText("🎉 Запущено!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = GeoGUI()
    gui.resize(400, 200)
    gui.show()
    sys.exit(app.exec())

