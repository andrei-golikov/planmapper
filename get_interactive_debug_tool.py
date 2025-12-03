# FILENAME: get_interactive_debug_tool.py

import os
import json
import glob
import matplotlib.pyplot as plt
from pyproj import Transformer

# Преобразование WGS84 → Web Mercator (EPSG:3857)
transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

def extract_coords(filename):
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    geom = data.get("features", [data])[0].get("geometry", data.get("geometry"))
    return geom["coordinates"][0]

def reproject(coords):
    return [transformer.transform(lon, lat) for lon, lat in coords]

def interactive_plot(coords_list, labels):
    fig, ax = plt.subplots()
    patches = []
    annotations = []

    for i, coords in enumerate(coords_list):
        xs, ys = zip(*coords)
        poly = ax.fill(xs, ys, alpha=0.4, label=labels[i])[0]
        patches.append(poly)

        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)

        ann = ax.annotate(
            labels[i],
            xy=(cx, cy),
            xycoords="data",
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
            fontsize=9,
            color="black",
            bbox=dict(boxstyle="round,pad=0.2", fc="yellow", alpha=0.8),
            visible=False
        )
        annotations.append(ann)

    def on_move(event):
        for patch, ann in zip(patches, annotations):
            contains, _ = patch.contains(event)
            ann.set_visible(contains)
        fig.canvas.draw_idle()

    fig.canvas.mpl_connect("motion_notify_event", on_move)
    ax.set_aspect("equal")
    ax.axis("off")
    plt.title("Наведи на участок, чтобы увидеть его номер", fontsize=12)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    base = os.path.dirname(__file__)
    output_root = os.path.join(base, "output")

    # 🔍 Ищем ВСЕ .geojson внутри output на любой глубине
    files = sorted(glob.glob(os.path.join(output_root, "**/*.geojson"), recursive=True))

    coords_list = []
    labels = []

    for file in files:
        name = os.path.splitext(os.path.basename(file))[0]
        try:
            coords = reproject(extract_coords(file))
            coords_list.append(coords)

            # Берём последнюю часть кадастра как подпись
            labels.append(name.split("_")[-1])
        except Exception as e:
            print(f"❌ Ошибка чтения {file}: {e}")

    if coords_list:
        print(f"✅ Загружено участков: {len(coords_list)}")
        interactive_plot(coords_list, labels)
    else:
        print("❌ Не найдено ни одного GeoJSON-файла внутри ./output/")

