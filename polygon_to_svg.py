# FILENAME: polygon_to_swg.py

#!/usr/bin/env python3
"""
polygon_to_swg.py

Конвертирует `polygon.json` (или `filtered_polygon.json`) в векторный SVG.

Особенности:
- Поддержка опционального swap координат (если записи в JSON хранятся как [y,x]).
- Масштабирование и отступы для вписывания всех полигонов в холст заданного размера.
- Подписи меток по полю `idtur` (опционально).

Пример:
  python polygon_to_swg.py --input polygon.json --output polygons.svg --width 2000 --padding 20 --swap

"""
from __future__ import annotations

import json
import math
import argparse
from typing import List, Tuple, Dict, Optional

# -------------------- Настройки (редактируйте здесь) --------------------
# По умолчанию рисуем только контуры (без заливки) и без лейблов.
DEFAULT_WIDTH = 2000
DEFAULT_HEIGHT: Optional[int] = None
DEFAULT_PADDING = 20
DEFAULT_SWAP = True
DEFAULT_STROKE = "#222222"
DEFAULT_STROKE_WIDTH = 1.0
DEFAULT_FILL: Optional[str] = None  # None -> прозрачная заливка
DEFAULT_SHOW_LABELS = False
# ------------------------------------------------------------------------


def load_polygons(path: str, swap: bool = False) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("data") or []
    # normalize coordinates optionally
    for it in items:
        coords = it.get("coordinates", [[]])[0]
        if swap:
            it["coordinates"][0] = [[pt[1], pt[0]] for pt in coords]
        else:
            # ensure numbers
            it["coordinates"][0] = [[float(pt[0]), float(pt[1])] for pt in coords]
    return items


def bbox_of_items(items: List[Dict]) -> Tuple[float, float, float, float]:
    minx = miny = float("inf")
    maxx = maxy = float("-inf")
    for it in items:
        for x, y in it.get("coordinates", [[]])[0]:
            if x < minx:
                minx = x
            if y < miny:
                miny = y
            if x > maxx:
                maxx = x
            if y > maxy:
                maxy = y
    if minx == float("inf"):
        return 0, 0, 0, 0
    return minx, miny, maxx, maxy


def polygon_centroid(coords: List[Tuple[float, float]]) -> Tuple[float, float]:
    xs = [p[0] for p in coords]
    ys = [p[1] for p in coords]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def build_svg(items: List[Dict], width: int = DEFAULT_WIDTH, height: Optional[int] = DEFAULT_HEIGHT,
              padding: int = DEFAULT_PADDING, stroke: str = DEFAULT_STROKE, fill: Optional[str] = DEFAULT_FILL,
              stroke_width: float = DEFAULT_STROKE_WIDTH, show_labels: bool = DEFAULT_SHOW_LABELS) -> str:
    minx, miny, maxx, maxy = bbox_of_items(items)
    if maxx - minx == 0 or maxy - miny == 0:
        raise ValueError("Empty or degenerate geometry")

    # target size
    if height is None:
        # preserve aspect ratio
        aspect = (maxy - miny) / (maxx - minx)
        height = int(width * aspect)

    avail_w = width - 2 * padding
    avail_h = height - 2 * padding

    scale_x = avail_w / (maxx - minx)
    scale_y = avail_h / (maxy - miny)
    scale = min(scale_x, scale_y)

    # shift so min maps to padding
    def project(pt):
        x, y = pt
        px = (x - minx) * scale + padding
        # SVG Y goes downwards; keep Y upwards by flipping
        py = height - ((y - miny) * scale + padding)
        return px, py

    svg_lines = []
    svg_lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    svg_lines.append('<rect width="100%" height="100%" fill="white"/>')

    # draw polygons
    for it in items:
        ring = it.get("coordinates", [[]])[0]
        if not ring:
            continue
        points = [project(pt) for pt in ring]
        pts_str = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
        svg_fill = (fill if fill is not None else "none")
        svg_lines.append(f'<polygon points="{pts_str}" fill="{svg_fill}" stroke="{stroke}" stroke-width="{stroke_width}" />')
        if show_labels:
            try:
                cx, cy = polygon_centroid(ring)
                px, py = project((cx, cy))
                label = str(it.get("idtur") or it.get("names") or "")
                svg_lines.append(f'<text x="{px:.1f}" y="{py:.1f}" font-size="12" text-anchor="middle" fill="#000">{label}</text>')
            except Exception:
                pass

    svg_lines.append('</svg>')
    return "\n".join(svg_lines)


def main():
    p = argparse.ArgumentParser(description="Convert polygon.json to SVG")
    p.add_argument("--input", "-i", default="polygon.json", help="input JSON (polygon.json)")
    p.add_argument("--output", "-o", default="polygons.svg", help="output SVG file")
    p.add_argument("--width", "-w", type=int, default=DEFAULT_WIDTH, help="SVG width in pixels")
    # use -H to avoid conflict with argparse's default -h (help)
    p.add_argument("--height", "-H", type=int, default=DEFAULT_HEIGHT, help="SVG height in pixels (optional)")
    p.add_argument("--padding", type=int, default=DEFAULT_PADDING, help="padding in pixels")
    p.add_argument("--swap", action="store_true", default=DEFAULT_SWAP, help="swap stored coordinates [y,x] -> [x,y]")
    p.add_argument("--fill-color", default=DEFAULT_FILL, help="fill color (default: none)")
    p.add_argument("--stroke", default=DEFAULT_STROKE, help="stroke color")
    p.add_argument("--stroke-width", type=float, default=DEFAULT_STROKE_WIDTH, help="stroke width")
    p.add_argument("--labels", action="store_true", default=DEFAULT_SHOW_LABELS, help="show labels from idtur/names")
    args = p.parse_args()

    items = load_polygons(args.input, swap=args.swap)
    svg = build_svg(items, width=args.width, height=args.height, padding=args.padding,
                    stroke=args.stroke, fill=(args.fill_color if args.fill_color is not None else None),
                    stroke_width=args.stroke_width, show_labels=args.labels)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Saved SVG → {args.output}")


if __name__ == "__main__":
    main()
