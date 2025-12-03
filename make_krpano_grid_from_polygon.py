# FILENAME: make_krpano_grid_from_polygon.py

import json
import math
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
import matplotlib.pyplot as plt

# ---- НАСТРОЙКИ -------------------------------------------
CAMERA_HEIGHT = 100.0       # высота камеры
INPUT_POLYGON_MAIN = "polygon.json"
INPUT_POLYGON_FILTERED = "filtered_polygon.json"
OUTPUT_XML = "hotspots_grid.xml"
# -----------------------------------------------------------


def get_input_polygon_path():
    if os.path.exists(INPUT_POLYGON_FILTERED):
        print(f"📌 Использую {INPUT_POLYGON_FILTERED}")
        return INPUT_POLYGON_FILTERED
    print(f"📌 Использую {INPUT_POLYGON_MAIN}")
    return INPUT_POLYGON_MAIN


def load_polygon(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("data")
    # Нормализуем формат координат: в `stage1_make_polygon.py` при
    # APPLY_ROTATE_AND_MIRROR=True координаты сохраняются как [y, x].
    # Для внутренней работы (matplotlib, проекция) удобнее иметь
    # стандартный порядок [x, y]. Здесь приводим их в этот вид.
    for item in items:
        ring = item.get("coordinates", [None])[0]
        if not ring:
            continue
        # swap each pair (stored_y, stored_x) -> (x, y)
        item["coordinates"][0] = [[pt[1], pt[0]] for pt in ring]
    return items


def centroid(coords):
    xs = [p[0] for p in coords]
    ys = [p[1] for p in coords]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def select_center_polygon(items):
    """
    Показывает окно matplotlib, позволяет выбрать ОДИН полигон кликом.
    Центроид выбранного полигона возвращается как (cx, cy).
    """
    fig, ax = plt.subplots()
    plt.title("Выбери полигон под коптером (клик)")

    polygons_xy = []

    # рисуем полигоны
    for item in items:
        ring = item["coordinates"][0]
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        ax.fill(xs, ys, alpha=0.2, edgecolor="black")
        polygons_xy.append((ring, item))

    selected_center = {"value": None}

    def onclick(event):
        if event.inaxes != ax:
            return
        x_click, y_click = event.xdata, event.ydata

        # ищем полигон, в который попал клик
        for ring, item in polygons_xy:
            if point_in_polygon(x_click, y_click, ring):
                cx, cy = centroid(ring)
                selected_center["value"] = (cx, cy)
                print(f"📍 Выбран участок {item.get('names')} (центр {cx:.2f}, {cy:.2f})")
                plt.close()
                return

        print("⚠ Клик не попал ни в один участок.")

    fig.canvas.mpl_connect("button_press_event", onclick)
    plt.gca().set_aspect("equal")
    plt.show()

    return selected_center["value"]


# ---- Классический ray-casting ----------------------------------

def point_in_polygon(x, y, poly):
    inside = False
    n = len(poly)
    x1, y1 = poly[0]

    for i in range(1, n + 1):
        x2, y2 = poly[i % n]
        if ((y1 > y) != (y2 > y)):
            xinters = (y - y1) * (x2 - x1) / (y2 - y1 + 1e-12) + x1
            if x < xinters:
                inside = not inside
        x1, y1 = x2, y2

    return inside


# ---- Проекция ---------------------------------------------------

def project_point_to_panorama(x: float, y: float, camera_height: float):
    # Внутренний формат сейчас — (x, y) (после нормализации в load_polygon).
    # Стандартная каноническая проекция (камера в (0, H, 0), точка (x,0,y)):
    vx = x
    vy = camera_height
    vz = y

    r = math.sqrt(vx * vx + vy * vy + vz * vz)
    if r == 0:
        return 0.0, 0.0

    ratio = vy / r
    ratio = max(-1.0, min(1.0, ratio))

    ath = math.degrees(math.atan2(vx, vz))
    atv = math.degrees(math.asin(ratio))
    return ath, atv


# ---- Перевод координат относительно выбранного центра -----------

def shift_polygon(coords, cx, cy):
    """Сдвигает все точки полигона так, что (cx,cy) → (0,0)."""
    return [[x - cx, y - cy] for x, y in coords]


# ---- Формирование хотспотов ------------------------------------

def convert_polygons_to_hotspots(items, camera_height, center_pt):
    hotspots = []

    for idx, item in enumerate(items, start=1):
        coords = item["coordinates"][0]
        if not coords:
            continue

        # сдвигаем координаты относительно выбранного центра
        shifted = shift_polygon(coords, center_pt[0], center_pt[1])

        # убираем повтор последней точки
        ring = shifted
        if len(ring) > 1 and ring[0] == ring[-1]:
            ring = ring[:-1]

        # Use `idtur` from polygon.json as canonical hotspot identifier.
        # Fallback to `names`, then to numeric index if missing.
        raw_id = str(item.get("idtur") or item.get("names") or idx).strip()
        # If the id is purely numeric, zero-fill to 5 digits to get the form hsXXXXX.
        if raw_id.isdigit():
            hs_id = raw_id.zfill(5)
        else:
            hs_id = raw_id

        hotspot = ET.Element(
            "hotspot",
            {"name": f"hs{hs_id}", "style": "plot"}
        )

        for x, y in ring:
            ath, atv = project_point_to_panorama(x, y, camera_height)
            ET.SubElement(
                hotspot,
                "point",
                {"ath": f"{ath:.3f}", "atv": f"{atv:.3f}"}
            )

        hotspots.append(hotspot)

    return hotspots


# ---- Сохранение XML ---------------------------------------------

def save_hotspots_xml(hotspots, output_path):
    root = ET.Element("krpano")
    for hs in hotspots:
        root.append(hs)

    raw = ET.tostring(root, encoding="utf-8")
    parsed = minidom.parseString(raw)
    pretty = parsed.toprettyxml(indent="  ", encoding="utf-8")

    pretty_str = pretty.decode("utf-8")
    pretty_str = "\n".join(
        line for line in pretty_str.splitlines()
        if not line.strip().startswith("<?xml")
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(pretty_str)


# ---- Основной процесс -------------------------------------------

def main():
    polygon_path = get_input_polygon_path()
    items = load_polygon(polygon_path)

    print("🎯 Выбери участок под коптером…")
    center_pt = select_center_polygon(items)

    if center_pt is None:
        print("❌ Центр не выбран — отмена.")
        return

    hotspots = convert_polygons_to_hotspots(items, CAMERA_HEIGHT, center_pt)
    save_hotspots_xml(hotspots, OUTPUT_XML)

    print(f"\n✅ Hotspots saved → {OUTPUT_XML}")
    print(f"📍 Панорама центрирована относительно точки {center_pt}")
    print(f"📏 Camera height = {CAMERA_HEIGHT} m")
    print(f"📦 Polygons converted: {len(hotspots)}")


if __name__ == "__main__":
    main()
