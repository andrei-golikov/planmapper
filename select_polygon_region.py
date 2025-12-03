# FILENAME: select_polygon_region.py

#
# Интерактивный инструмент для выбора произвольного контура
# и фильтрации polygon.json: остаются только те участки,
# у которых ВСЕ вершины полигона находятся внутри выбранного пользователем контура.
#
# Выход: filtered_polygon.json

import json
import os
import matplotlib.pyplot as plt

# ----------------------------
#   Функции геометрии
# ----------------------------

def point_in_polygon(x, y, poly):
    """
    Ray casting algorithm.
    poly = [(x1,y1), (x2,y2), ...]
    Возвращает True если точка строго внутри контура.
    """
    inside = False
    n = len(poly)
    px1, py1 = poly[0]

    for i in range(n + 1):
        px2, py2 = poly[i % n]
        # Проверяем пересечение луча с ребром
        if y > min(py1, py2):
            if y <= max(py1, py2):
                if x <= max(px1, px2):
                    if py1 != py2:
                        xinters = (y - py1) * (px2 - px1) / (py2 - py1 + 1e-12) + px1
                    else:
                        xinters = px1
                    if px1 == px2 or x <= xinters:
                        inside = not inside
        px1, py1 = px2, py2

    return inside


def polygon_inside_region(polygon_coords, region):
    """
    polygon_coords — список точек полигона:
        [[x1,y1], [x2,y2], ...]
    region — список точек выделенного полигона пользователем.
    Возвращает True, если ВСЕ точки полигона строго внутри region.
    """
    for x, y in polygon_coords:
        if not point_in_polygon(x, y, region):
            return False
    return True


# ----------------------------
#   Загрузка polygon.json
# ----------------------------

INPUT_JSON = "polygon.json"
OUTPUT_JSON = "filtered_polygon.json"

if not os.path.exists(INPUT_JSON):
    print("❌ Не найден polygon.json — остановка.")
    exit(1)

with open(INPUT_JSON, "r", encoding="utf-8") as f:
    obj = json.load(f)

items = obj.get("data", [])

if not items:
    print("❌ В polygon.json нет данных.")
    exit(1)

# Соберём все точки для отрисовки.
# В `stage1_make_polygon.py` координаты могут быть записаны как [y,x].
# Для корректной отрисовки и логики фильтрации мы используем нормализованную
# версию (x,y) для всех визуальных операций, но при сохранении оставляем
# оригинальные объекты без изменения их порядка, чтобы downstream не сломался.
all_polys = []
for item in items:
    coords = item["coordinates"][0]
    # normalized: convert stored [y,x] -> [x,y]
    try:
        normalized = [[pt[1], pt[0]] for pt in coords]
    except Exception:
        normalized = coords
    all_polys.append(normalized)

# ----------------------------
#   Интерфейс выбора региона
# ----------------------------

region = []
fig, ax = plt.subplots()
plt.title("Кликни точки выделяющего контура (Enter — завершить, Backspace — отменить последнюю точку)")

# рисуем все участки
for poly in all_polys:
    xs, ys = zip(*poly)
    ax.fill(xs, ys, alpha=0.15, edgecolor="black")
# Установим равные масштабы по осям, чтобы избежать искажения (сплющивания)
ax.set_aspect("equal")
ax.relim()
ax.autoscale_view()

marker_plot, = ax.plot([], [], "-o", color="red", linewidth=2)


def onclick(event):
    if event.inaxes != ax:
        return
    region.append((event.xdata, event.ydata))
    xs = [p[0] for p in region]
    ys = [p[1] for p in region]
    marker_plot.set_data(xs, ys)
    fig.canvas.draw()


def onkey(event):
    if event.key == "enter":
        plt.close()
    elif event.key == "backspace":
        if region:
            region.pop()
            xs = [p[0] for p in region]
            ys = [p[1] for p in region]
            marker_plot.set_data(xs, ys)
            fig.canvas.draw()


cid_click = fig.canvas.mpl_connect("button_press_event", onclick)
cid_key   = fig.canvas.mpl_connect("key_press_event", onkey)

plt.show()

# ----------------------------
#   Проверка выбранного региона
# ----------------------------

if len(region) < 3:
    print("❌ Контур слишком маленький — минимум 3 точки.")
    exit(1)

print(f"📐 Выделено точек: {len(region)}")
print("🔍 Фильтрую участки...")

# ----------------------------
#   Фильтрация участков
# ----------------------------

filtered = []
dropped = 0

for item in items:
    orig_poly = item["coordinates"][0]
    # normalize for testing: stored may be [y,x]
    try:
        poly_norm = [[pt[1], pt[0]] for pt in orig_poly]
    except Exception:
        poly_norm = orig_poly

    # Если ВСЕ точки внутри — оставить (append original item to preserve storage format)
    if polygon_inside_region(poly_norm, region):
        filtered.append(item)
    else:
        dropped += 1

# ----------------------------
#   Сохранение
# ----------------------------

out_obj = {"data": filtered}

with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(out_obj, f, ensure_ascii=False, indent=2)

print(f"✅ Готово. Осталось участков: {len(filtered)} (отброшено {dropped})")
print(f"💾 Сохранено в: {OUTPUT_JSON}")
