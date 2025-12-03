# FILENAME: manual_adjust_polygon_good_twistedaxis.py

import os
import json
import math
import matplotlib.pyplot as plt

def input_float(prompt, default):
    value = input(f"{prompt} (по умолчанию {default}): ").strip()
    if value == "":
        return default
    try:
        return float(value)
    except ValueError:
        print("❌ Введите число.")
        return input_float(prompt, default)

def apply_transform(coords, scale, offset_x, offset_y, rotation_deg):
    angle = math.radians(rotation_deg)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    transformed = []
    for x, y in coords:
        x *= scale
        y *= scale
        x_rot = x * cos_a - y * sin_a + offset_x
        y_rot = x * sin_a + y * cos_a + offset_y
        transformed.append([round(x_rot, 6), round(y_rot, 6)])
    return transformed

def plot_polygons(data, filename="output_corrected.png"):
    fig, ax = plt.subplots()
    all_x, all_y = [], []

    for item in data:
        coords = item["coordinates"][0]
        xs, ys = zip(*coords)
        ax.fill(xs, ys, alpha=0.5, edgecolor='black')
        all_x.extend(xs)
        all_y.extend(ys)

    if not all_x or not all_y:
        print("⚠️ Нет данных для отображения")
        return

    ax.plot(0, 0, marker='x', color='black')
    ax.text(5, 5, "(0,0)", fontsize=8, color='black')
    ax.plot([0, 100], [0, 0], color='red')
    ax.text(110, 0, 'X → восток', color='red')
    ax.plot([0, 0], [0, 100], color='green')
    ax.text(0, 110, 'Y ↑ север', color='green')

    margin = 100
    ax.set_xlim(min(all_x) - margin, max(all_x) + margin)
    ax.set_ylim(min(all_y) - margin, max(all_y) + margin)
    ax.set_aspect("equal")
    ax.grid(True, linestyle="--", alpha=0.3)
    ax.set_title(filename)

    # Поворот и отражение
    plt.gca().invert_yaxis()
    plt.gca().set_aspect('equal')
    plt.savefig(filename, bbox_inches="tight", dpi=300)
    plt.close()
    print(f"✅ Картинка сохранена: {filename}")

def main():
    path = os.path.join(os.getcwd(), "polygon.json")
    if not os.path.isfile(path):
        print("❌ Не найден polygon.json")
        return

    with open(path, "r", encoding="utf-8") as f:
        polygon = json.load(f)

    print("🔧 Введите корректировки:")
    scale     = input_float("Масштаб", 1.0)
    offset_y  = input_float("Смещение по X", 0.0)
    offset_x  = input_float("Смещение по Y", 0.0)
    rotation  = input_float("Поворот (в градусах)", 0.0)

    for item in polygon["data"]:
        coords = item["coordinates"][0]
        item["coordinates"][0] = apply_transform(coords, scale, offset_x, offset_y, rotation)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(polygon, f, ensure_ascii=False, indent=2)
    print("💾 Обновлён: polygon.json")

    plot_polygons(polygon["data"])

if __name__ == "__main__":
    main()




