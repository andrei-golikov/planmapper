# FILENAME: stage2_transform.py

import os
import json
import math

polygon_path = os.path.join(os.getcwd(), "polygon.json")
APPLY_ROTATE_AND_MIRROR = True

DEFAULT_STEP = 50

def generate_debug_grid(
    x_min=-1000, x_max=1000,
    y_min=-1000, y_max=1000,
    step=50, size=10,
    start_index=0
):
    data = []
    centers = {}
    idx = 0

    num_columns = (x_max - x_min) // step

    def col_to_letters(col):
        first = col // 26
        second = col % 26
        return chr(ord('a') + first) + chr(ord('a') + second)

    for x in range(x_min, x_max, step):
        for y in range(y_min, y_max, step):
            x0 = x + (step - size) / 2
            y0 = y + (step - size) / 2

            square = [
                [x0, y0],
                [x0 + size, y0],
                [x0 + size, y0 + size],
                [x0, y0 + size],
                [x0, y0]
            ]

            center = (x0 + size / 2, y0 + size / 2)

            gid = start_index + idx

            col = gid % num_columns
            row = gid // num_columns

            letters = col_to_letters(col)
            index = f"{row:02d}"

            grid_name = f"{letters}{index}"

            data.append((square, gid, grid_name))
            centers[str(gid)] = center
            idx += 1

    return data, centers


def apply_transform(coords, transform, allow_rotation=True):
    out = []
    s = transform["scale"]

    if allow_rotation:
        ang = math.radians(transform["rotation_deg"])
        ca, sa = math.cos(ang), math.sin(ang)
    else:
        ca, sa = 1, 0  # rotation disabled

    ox, oy = transform["offset_x"], transform["offset_y"]

    for x, y in coords:
        x *= s
        y *= s
        xr = x * ca - y * sa + ox
        yr = x * sa + y * ca + oy
        out.append([round(xr, 6), round(yr, 6)])

    return out


def compute_similarity_transform(f1, t1, f2, t2, allow_rotation=True):
    dx1, dy1 = f1
    dx2, dy2 = f2
    tx1, ty1 = t1
    tx2, ty2 = t2

    vf = (dx2 - dx1, dy2 - dy1)
    vt = (tx2 - tx1, ty2 - ty1)

    lf = math.hypot(*vf)
    lt = math.hypot(*vt)

    if lf == 0:
        raise ValueError("Исходные точки совпадают")

    scale = lt / lf

    if allow_rotation:
        af = math.atan2(vf[1], vf[0])
        at = math.atan2(vt[1], vt[0])
        r = at - af
        rd = math.degrees(r)

        ca, sa = math.cos(r), math.sin(r)
        ox = tx1 - scale * (ca * dx1 - sa * dy1)
        oy = ty1 - scale * (sa * dx1 + ca * dy1)
    else:
        rd = 0
        ox = tx1 - scale * dx1
        oy = ty1 - scale * dy1

    return {
        "scale": scale,
        "rotation_deg": rd,
        "offset_x": ox,
        "offset_y": oy
    }


def input_valid_square(prompt, name_to_gid):
    while True:
        v = input(prompt).strip()
        if v in name_to_gid:
            return v
        print("❌ Квадрат не найден. Повтори ввод.")


def main():
    if not os.path.isfile(polygon_path):
        print("❌ Нет polygon.json — сначала Stage1.")
        return

    print(f"📐 Шаг настроечной сетки по умолчанию: {DEFAULT_STEP}")
    inp = input("Введите желаемый шаг сетки (или Enter = по умолчанию): ").strip()
    step = DEFAULT_STEP
    if inp.isdigit():
        v = int(inp)
        if v > 0:
            step = v
            print(f"Используем шаг: {step}")

    allow_rot = True
    inp = input("Разрешать поворот при трансформации сетки? (1 — да, 0 — нет, Enter — да): ").strip()
    if inp == "0":
        allow_rot = False
        print("Поворот ОТКЛЮЧЕН (фиксированный север).")
    else:
        print("Поворот разрешён.")

    with open(polygon_path, "r", encoding="utf-8") as f:
        obj = json.load(f)

    data = obj["data"]

    real_count = sum(
        1 for item in data
        if not item["kadastr"].startswith("99:99:9999999:")
    )
    start_index = real_count

    print("🔧 Генерирую разметочную сетку...")
    grid_data, grid_centers = generate_debug_grid(step=step, start_index=start_index)

    name_to_gid = {}
    for square, gid, grid_name in grid_data:
        if APPLY_ROTATE_AND_MIRROR:
            sq = [[round(y, 6), round(x, 6)] for x, y in square]
        else:
            sq = square

        data.append({
            "id": len(data) + 1,
            "number": grid_name,
            "names": grid_name,
            "kadastr": f"99:99:9999999:{gid}",
            "kadastrurl": "",
            "idtur": str(gid).zfill(5),
            "status": "sale",
            "coordinates": [sq]
        })

        name_to_gid[grid_name] = str(gid)

    obj["data"] = data

    with open(polygon_path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

    print("💾 Сетка добавлена.")

    print("\n🧭 Введите 4 квадрата для трансформации (например aa03):")

    g1 = input_valid_square("1. Исходная → ", name_to_gid)
    g2 = input_valid_square("2. Целевая   → ", name_to_gid)
    g3 = input_valid_square("3. Исходная2 → ", name_to_gid)
    g4 = input_valid_square("4. Целевая2  → ", name_to_gid)

    tr = compute_similarity_transform(
        grid_centers[name_to_gid[g1]],
        grid_centers[name_to_gid[g2]],
        grid_centers[name_to_gid[g3]],
        grid_centers[name_to_gid[g4]],
        allow_rotation=allow_rot
    )

    print("🔧 Трансформация:", tr)

    final = []
    for item in data:
        kid = item["kadastr"]
        coords = item["coordinates"][0]

        if not kid.startswith("99:99:"):
            if APPLY_ROTATE_AND_MIRROR:
                coords = [[y, x] for x, y in coords]

            tcoords = apply_transform(coords, tr, allow_rotation=allow_rot)

            if APPLY_ROTATE_AND_MIRROR:
                tcoords = [[round(y, 6), round(x, 6)] for x, y in tcoords]

            item["coordinates"] = [tcoords]

        final.append(item)

    final_clean = [
        item for item in final
        if not item["kadastr"].startswith("99:99:9999999:")
    ]

    obj["data"] = final_clean

    with open(polygon_path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

    print("🧹 Разметочные квадраты удалены.")
    print("✅ polygon.json сохранён после применения трансформации.")


if __name__ == "__main__":
    main()


