# FILENAME: stage1_make_polygon.py

import os
import glob
import json
import math
import matplotlib.pyplot as plt
from pyproj import Transformer

# === Stage 1: загрузка и нормализация участков ===

min_distance_between_points = 2.0
transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
base_dir = os.getcwd()
polygon_path = os.path.join(base_dir, "polygon.json")

APPLY_ROTATE_AND_MIRROR = True


def extract_coords_geojson(filename):
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    feature = data.get("features", [data])[0]
    geom = feature.get("geometry", {})
    coords = geom.get("coordinates", [[]])[0]

    return [transformer.transform(lon, lat) for lon, lat in coords]


def clean_polygon(coords, tolerance=min_distance_between_points):
    cleaned = []
    last = None
    for x, y in coords:
        if last is None or math.hypot(x - last[0], y - last[1]) >= tolerance:
            cleaned.append((x, y))
            last = (x, y)
    return cleaned


def plot_polygons(coords_list, filename="output_1_stage.png"):
    fig, ax = plt.subplots()
    all_x, all_y = [], []
    for coords in coords_list:
        xs, ys = zip(*coords)
        ax.fill(xs, ys, alpha=0.5, edgecolor="black")
        all_x.extend(xs)
        all_y.extend(ys)
    if not all_x:
        return
    ax.set_aspect("equal")
    plt.savefig(filename, bbox_inches="tight", dpi=300)
    plt.close()


# === 1) читаем geojson ===

coords_raw = []
metadata = []   # {kadastr, price, size, adres}

geojson_files = sorted(glob.glob(os.path.join(base_dir, "**", "*.geojson"), recursive=True))
print(f"📂 Найдено файлов: {len(geojson_files)}")

for file in geojson_files:
    try:
        coords = extract_coords_geojson(file)
        coords = clean_polygon(coords)
        if len(coords) < 3:
            continue

        coords_raw.append(coords)

        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)

        feature = data.get("features", [data])[0]
        props = feature.get("properties", {})
        opts = props.get("options", {})

        kadastr = props.get("label", "")
        price = ""
        size = opts.get("specified_area")
        adres = opts.get("readable_address", "")

        metadata.append({
            "kadastr": kadastr,
            "price": price,
            "size": size,
            "adres": adres
        })

    except Exception as e:
        print(f"⚠️ Ошибка в {file}: {e}")


if not coords_raw:
    print("❌ Нет полигонов.")
    exit()


# === Построение карты повторов последних блоков ===

num_groups = {}   # { "468": ["081802", "085802"] }

for m in metadata:
    parts = m["kadastr"].split(":")
    quarter = parts[-2]
    num = parts[-1]

    if num not in num_groups:
        num_groups[num] = []
    num_groups[num].append(quarter)

# сортируем кварталы в группе
for n in num_groups:
    num_groups[n].sort()


# === 2) центрирование ===

all_points = [pt for poly in coords_raw for pt in poly]
xs, ys = zip(*all_points)
center_x = (min(xs) + max(xs)) / 2
center_y = (min(ys) + max(ys)) / 2
print(f"📌 Центр: ({round(center_x, 2)}, {round(center_y, 2)})")

coords_shifted = []
for poly in coords_raw:
    shifted = [(x - center_x, y - center_y) for x, y in poly]
    shifted.append((shifted[0][0], shifted[0][1]))
    coords_shifted.append(shifted)


# === 3) визуализация ===

plot_polygons(coords_shifted, filename="output_1_stage.png")


# === 4) формирование polygon.json ===

result_data = []

for i, coords in enumerate(coords_shifted):

    meta = metadata[i]
    kadastr = meta["kadastr"]
    price = meta["price"]
    size = meta["size"]
    adres = meta["adres"]

    # Разбор кадастра
    parts = kadastr.split(":")
    quarter = parts[-2]
    num_str = parts[-1]
    num_int = int(num_str)

    # === Логика уникальных номеров ===
    repeat_index = num_groups[num_str].index(quarter)
    offset = repeat_index * 10000
    unique_num = offset + num_int

    idtur = str(unique_num).zfill(5)
    names = idtur            # то же самое
    number = str(num_int)    # только последний блок

    # Координаты
    if APPLY_ROTATE_AND_MIRROR:
        transformed = [[round(y, 6), round(x, 6)] for x, y in coords]
    else:
        transformed = [[round(x, 6), round(y, 6)] for x, y in coords]

    # Порядок полей — по алфавиту, coordinates последним
    result_data.append({
        "adres": adres,
        "id": i + 1,
        "idtur": idtur,
        "kadastr": kadastr,
        "kadastrurl": f"https://nspd.gov.ru/map?query={kadastr.replace(':','%3A')}&zoom=16&theme_id=1&active_layers=36048",
        "names": names,
        "number": number,
        "price": price,
        "size": size,
        "status": "sale",
        "coordinates": [transformed]
    })


with open(polygon_path, "w", encoding="utf-8") as f:
    json.dump({"inc": len(result_data), "data": result_data}, f, ensure_ascii=False, indent=2)

print("💾 Черновик сохранён: polygon.json")
print("=== DONE STAGE 1 ===")


