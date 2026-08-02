#!/usr/bin/env python3
"""Render a compact structured-content diagram as local SVG and HTML."""

from __future__ import annotations

import argparse
import html
import json
import math
import re
import sys
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


KINDS = {"flow", "branches", "framework", "timeline"}
ACCENTS = ("#2f7668", "#cf4b31", "#7552d6", "#335caa")
INK = "#1d1913"
MUTED = "#746d63"
PAPER = "#f4f0e8"
CARD = "#fffdf8"
LINE = "#d8d0c4"


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(value.rstrip() + "\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def text_width(value: str) -> int:
    return sum(2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1 for char in value)


def clip(value: str, limit: int) -> str:
    value = re.sub(r"\s+", " ", str(value)).strip()
    if text_width(value) <= limit:
        return value
    output = ""
    for char in value:
        if text_width(output + char + "…") > limit:
            break
        output += char
    return output.rstrip() + "…"


def wrap(value: str, width: int, max_lines: int) -> list[str]:
    source = re.sub(r"\s+", " ", str(value)).strip()
    if not source:
        return []
    lines: list[str] = []
    current = ""
    for char in source:
        if current and text_width(current + char) > width:
            lines.append(current.strip())
            current = char
            if len(lines) == max_lines:
                break
        else:
            current += char
    if len(lines) < max_lines and current.strip():
        lines.append(current.strip())
    consumed = "".join(lines)
    if text_width(consumed) < text_width(source) and lines:
        lines[-1] = clip(lines[-1], max(2, width - 1)) + "…"
    return lines[:max_lines]


def svg_text(
    x: float,
    y: float,
    value: str,
    *,
    size: int,
    weight: int = 500,
    color: str = INK,
    anchor: str = "middle",
    width: int = 20,
    max_lines: int = 2,
    line_height: int | None = None,
) -> str:
    lines = wrap(value, width, max_lines)
    spacing = line_height or int(size * 1.35)
    spans = "".join(
        f'<tspan x="{x:.1f}" dy="{0 if index == 0 else spacing}">{html.escape(line)}</tspan>'
        for index, line in enumerate(lines)
    )
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'font-size="{size}" font-weight="{weight}" fill="{color}">{spans}</text>'
    )


def validate(spec: dict) -> dict:
    if not isinstance(spec, dict):
        raise ValueError("Diagram spec must be a JSON object.")
    kind = str(spec.get("type") or "")
    if kind not in KINDS:
        raise ValueError(f"type must be one of: {', '.join(sorted(KINDS))}")
    title = str(spec.get("title") or "").strip()
    if not title:
        raise ValueError("title is required.")
    nodes = spec.get("nodes")
    if not isinstance(nodes, list) or not 2 <= len(nodes) <= 8:
        raise ValueError("nodes must contain between 2 and 8 items.")
    normalized: list[dict[str, str]] = []
    ids: set[str] = set()
    for raw in nodes:
        if not isinstance(raw, dict):
            raise ValueError("every node must be an object.")
        identifier = str(raw.get("id") or "").strip()
        node_title = str(raw.get("title") or "").strip()
        if not identifier or not node_title or identifier in ids:
            raise ValueError("every node needs a unique id and a title.")
        ids.add(identifier)
        normalized.append(
            {
                "id": identifier,
                "title": clip(node_title, 32),
                "description": clip(str(raw.get("description") or ""), 76),
            }
        )
    edges = spec.get("edges") or []
    if not isinstance(edges, list):
        raise ValueError("edges must be a list.")
    normalized_edges: list[dict[str, str]] = []
    for raw in edges:
        if not isinstance(raw, dict):
            raise ValueError("every edge must be an object.")
        source = str(raw.get("from") or "")
        target = str(raw.get("to") or "")
        if source not in ids or target not in ids or source == target:
            raise ValueError("edge endpoints must reference two different node ids.")
        normalized_edges.append(
            {"from": source, "to": target, "label": clip(str(raw.get("label") or ""), 18)}
        )
    if not normalized_edges:
        if kind in {"branches", "framework"}:
            normalized_edges = [
                {"from": normalized[0]["id"], "to": item["id"], "label": ""}
                for item in normalized[1:]
            ]
        else:
            normalized_edges = [
                {"from": normalized[index]["id"], "to": normalized[index + 1]["id"], "label": ""}
                for index in range(len(normalized) - 1)
            ]
    return {
        "type": kind,
        "title": clip(title, 54),
        "subtitle": clip(str(spec.get("subtitle") or ""), 96),
        "footer": clip(str(spec.get("footer") or ""), 110),
        "nodes": normalized,
        "edges": normalized_edges,
    }


def layout(spec: dict) -> tuple[int, int, dict[str, tuple[float, float, float, float]]]:
    nodes = spec["nodes"]
    kind = spec["type"]
    positions: dict[str, tuple[float, float, float, float]] = {}
    if kind == "flow":
        if len(nodes) <= 5:
            width, height = 1600, 900
            gap = 34
            card_w = min(260, (width - 160 - gap * (len(nodes) - 1)) / len(nodes))
            start = (width - (card_w * len(nodes) + gap * (len(nodes) - 1))) / 2
            for index, node in enumerate(nodes):
                positions[node["id"]] = (start + index * (card_w + gap), 350, card_w, 230)
        else:
            width, height = 1600, 1020
            first = math.ceil(len(nodes) / 2)
            rows = (nodes[:first], list(reversed(nodes[first:])))
            for row_index, row in enumerate(rows):
                card_w, gap = 260, 38
                start = (width - (card_w * len(row) + gap * (len(row) - 1))) / 2
                for index, node in enumerate(row):
                    positions[node["id"]] = (start + index * (card_w + gap), 280 + row_index * 390, card_w, 220)
    elif kind == "branches":
        width = 1700
        branch_height, branch_gap = 190, 28
        total = (len(nodes) - 1) * branch_height + (len(nodes) - 2) * branch_gap
        start = 280
        height = max(1000, start + total + 110)
        positions[nodes[0]["id"]] = (110, start + total / 2 - 120, 400, 240)
        for index, node in enumerate(nodes[1:]):
            positions[node["id"]] = (
                1090,
                start + index * (branch_height + branch_gap),
                500,
                branch_height,
            )
    elif kind == "framework":
        width, height = 1800, 1450
        canvas_center_x, canvas_center_y = width / 2, 750
        positions[nodes[0]["id"]] = (canvas_center_x - 230, canvas_center_y - 120, 460, 240)
        satellites = nodes[1:]
        radius_x, radius_y = 650, 400
        for index, node in enumerate(satellites):
            angle = -math.pi / 2 + index * (2 * math.pi / len(satellites))
            center_x = canvas_center_x + math.cos(angle) * radius_x
            center_y = canvas_center_y + math.sin(angle) * radius_y
            positions[node["id"]] = (center_x - 200, center_y - 100, 400, 200)
    else:
        width = max(1600, 260 + len(nodes) * 230)
        height = 950
        start = 150
        gap = (width - 300) / max(1, len(nodes) - 1)
        for index, node in enumerate(nodes):
            x = start + index * gap - 115
            y = 220 if index % 2 == 0 else 540
            positions[node["id"]] = (x, y, 230, 190)
    return width, height, positions


def edge_svg(edge: dict, positions: dict[str, tuple[float, float, float, float]]) -> str:
    sx, sy, sw, sh = positions[edge["from"]]
    tx, ty, tw, th = positions[edge["to"]]
    source_center = (sx + sw / 2, sy + sh / 2)
    target_center = (tx + tw / 2, ty + th / 2)

    def boundary(
        center: tuple[float, float], box: tuple[float, float], toward: tuple[float, float]
    ) -> tuple[float, float]:
        dx, dy = toward[0] - center[0], toward[1] - center[1]
        candidates = []
        if dx:
            candidates.append((box[0] / 2) / abs(dx))
        if dy:
            candidates.append((box[1] / 2) / abs(dy))
        scale = min(candidates) if candidates else 0
        return center[0] + dx * scale, center[1] + dy * scale

    x1, y1 = boundary(source_center, (sw, sh), target_center)
    x2, y2 = boundary(target_center, (tw, th), source_center)
    dx, dy = x2 - x1, y2 - y1
    if abs(dx) >= abs(dy):
        path = (
            f"M {x1:.1f} {y1:.1f} C {x1 + dx * .45:.1f} {y1:.1f}, "
            f"{x2 - dx * .45:.1f} {y2:.1f}, {x2:.1f} {y2:.1f}"
        )
    else:
        path = (
            f"M {x1:.1f} {y1:.1f} C {x1:.1f} {y1 + dy * .45:.1f}, "
            f"{x2:.1f} {y2 - dy * .45:.1f}, {x2:.1f} {y2:.1f}"
        )
    label = ""
    if edge["label"]:
        label = svg_text((x1 + x2) / 2, (y1 + y2) / 2 - 12, edge["label"], size=17, weight=650, color=MUTED, width=18, max_lines=1)
    return f'<path d="{path}" fill="none" stroke="#3d3730" stroke-width="4" marker-end="url(#arrow)"/>{label}'


def card_svg(node: dict, box: tuple[float, float, float, float], index: int) -> str:
    x, y, width, height = box
    accent = ACCENTS[index % len(ACCENTS)]
    title_size = 26 if height >= 220 else 23
    title_width = max(12, int(width / 14))
    title_line_height = int(title_size * 1.3)
    title_lines = wrap(node["title"], title_width, 2)
    title_y = y + 84
    description_y = title_y + max(0, len(title_lines) - 1) * title_line_height + 38
    description_line_height = 26
    description_width = max(16, int(width / 12))
    description_bottom = y + height - 18
    description_lines = max(
        1,
        min(3, 1 + int(max(0, description_bottom - description_y) / description_line_height)),
    )
    return "".join(
        (
            f'<rect x="{x + 12:.1f}" y="{y + 14:.1f}" width="{width:.1f}" height="{height:.1f}" rx="20" fill="#c9c0b3" opacity=".34"/>',
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" rx="20" fill="{CARD}" stroke="{LINE}" stroke-width="2"/>',
            f'<path d="M {x + 20:.1f} {y:.1f} H {x + width - 20:.1f}" stroke="{accent}" stroke-width="8" stroke-linecap="round"/>',
            f'<circle cx="{x + width / 2:.1f}" cy="{y + 38:.1f}" r="17" fill="{accent}" opacity=".14"/>',
            f'<text x="{x + width / 2:.1f}" y="{y + 45:.1f}" text-anchor="middle" font-size="18" font-weight="800" fill="{accent}">{index + 1:02d}</text>',
            svg_text(x + width / 2, title_y, node["title"], size=title_size, weight=780, width=title_width, max_lines=2, line_height=title_line_height),
            svg_text(x + width / 2, description_y, node["description"], size=17, color=MUTED, width=description_width, max_lines=description_lines, line_height=description_line_height),
        )
    )


def render_svg(spec: dict) -> str:
    width, height, positions = layout(spec)
    subtitle = svg_text(72, 220, spec["subtitle"], size=23, color=MUTED, anchor="start", width=82, max_lines=2, line_height=32) if spec["subtitle"] else ""
    edges = "".join(edge_svg(edge, positions) for edge in spec["edges"])
    cards = "".join(card_svg(node, positions[node["id"]], index) for index, node in enumerate(spec["nodes"]))
    footer = svg_text(72, height - 48, spec["footer"], size=18, color=MUTED, anchor="start", width=106, max_lines=2) if spec["footer"] else ""
    accessible = "; ".join(f'{node["title"]}: {node["description"]}' for node in spec["nodes"])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title description">
<title id="title">{html.escape(spec["title"])}</title>
<desc id="description">{html.escape(accessible)}</desc>
<defs>
  <style>text{{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}}</style>
  <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M 32 0 L 0 0 0 32" fill="none" stroke="#d7d0c4" stroke-width="1" opacity=".55"/></pattern>
  <marker id="arrow" markerUnits="userSpaceOnUse" markerWidth="16" markerHeight="16" refX="14" refY="8" orient="auto"><path d="M 0 0 L 16 8 L 0 16 z" fill="#3d3730"/></marker>
</defs>
<rect width="{width}" height="{height}" fill="{PAPER}"/><rect width="{width}" height="{height}" fill="url(#grid)"/>
<rect x="18" y="18" width="{width - 36}" height="{height - 36}" fill="none" stroke="#bfb6a9" stroke-width="1"/>
<rect x="64" y="48" width="48" height="48" fill="#cf4b31"/><text x="88" y="81" text-anchor="middle" font-size="28" font-weight="900" fill="white">书</text>
<text x="126" y="82" font-size="22" font-weight="760" fill="{INK}">赛博书屋</text>
{svg_text(64, 137, spec["title"], size=50, weight=850, anchor="start", width=54, max_lines=2, line_height=56)}
{subtitle}
<g>{edges}</g><g>{cards}</g>{footer}
</svg>'''


def render_html(spec: dict, svg_name: str) -> str:
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(spec["title"])}</title>
<style>html,body{{margin:0;min-height:100%;background:#d9d2c8}}body{{display:grid;place-items:center;padding:24px;box-sizing:border-box}}img{{display:block;width:min(100%,1600px);height:auto;box-shadow:0 18px 60px rgba(34,29,23,.18)}}@media(max-width:700px){{body{{padding:8px}}}}</style>
</head><body><img src="{html.escape(svg_name)}" alt="{html.escape(spec["title"])}"></body></html>'''


def safe_name(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.")
    if not normalized:
        raise ValueError("name must contain at least one safe filename character.")
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--name", default="structured-diagram")
    args = parser.parse_args()
    try:
        source = Path(args.spec).expanduser()
        spec = validate(json.loads(source.read_text(encoding="utf-8")))
        output = Path(args.output_dir).expanduser().resolve()
        output.mkdir(parents=True, exist_ok=True)
        name = safe_name(args.name)
        svg_path = output / f"{name}.svg"
        html_path = output / f"{name}.html"
        atomic_text(svg_path, render_svg(spec))
        atomic_text(html_path, render_html(spec, svg_path.name))
        receipt = {
            "status": "complete",
            "type": spec["type"],
            "node_count": len(spec["nodes"]),
            "svg": str(svg_path),
            "html": str(html_path),
            "generated_at": now(),
        }
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "unavailable", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
