# FILENAME: kad_coord_mini.py 
import subprocess
import os

# FILENAME: kad_coord_v1.py

# Получаем путь к директории, где находится скрипт
base_dir = os.path.dirname(os.path.abspath(__file__))

# Список кадастровых номеров
kadastr_numbers = [
    "71:09:020201:4753",
    "71:09:020201:4763"
]

for kad_num in kadastr_numbers:
    print(f"Получаем координаты для {kad_num}...")

    # Формируем путь к выходному файлу
    output_file = os.path.join(base_dir, kad_num.replace(":", "_") + ".geojson")

    try:
        # Запускаем утилиту rosreestr2coord
        result = subprocess.run(
            ["rosreestr2coord", "-c", kad_num, "-o", output_file],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✅ Успешно сохранено в: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка при обработке {kad_num}: {e}")
        print(e.stderr)
