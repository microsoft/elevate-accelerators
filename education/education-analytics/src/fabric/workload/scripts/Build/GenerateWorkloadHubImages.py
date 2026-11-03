from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "Workload" / "Manifest" / "assets" / "images"
SCALE = 3
SEED = 260922

INK = (15, 35, 42)
TEAL = (13, 121, 103)
CYAN = (45, 179, 184)
AMBER = (199, 125, 31)
SILVER = (132, 153, 154)
GOLD = (230, 177, 73)
MINT = (218, 243, 237)
ICE = (238, 249, 248)


def lerp(a: int, b: int, amount: float) -> int:
    return round(a + (b - a) * amount)


def mix(left: tuple[int, int, int], right: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(lerp(left[index], right[index], amount) for index in range(3))


def point(x: float, y: float) -> tuple[int, int]:
    return round(x * SCALE), round(y * SCALE)


def box(left: float, top: float, right: float, bottom: float) -> tuple[int, int, int, int]:
    return round(left * SCALE), round(top * SCALE), round(right * SCALE), round(bottom * SCALE)


def width(value: float) -> int:
    return max(1, round(value * SCALE))


def canvas(size: tuple[int, int], top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    image = Image.new("RGBA", (size[0] * SCALE, size[1] * SCALE), top + (255,))
    draw = ImageDraw.Draw(image)
    for y in range(image.height):
        amount = y / max(1, image.height - 1)
        draw.line((0, y, image.width, y), fill=mix(top, bottom, amount) + (255,))
    return image


def overlay(base: Image.Image) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    return layer, ImageDraw.Draw(layer)


def glow(base: Image.Image, center: tuple[float, float], radius: float, color: tuple[int, int, int], opacity: int) -> None:
    layer, draw = overlay(base)
    draw.ellipse(box(center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius), fill=color + (opacity,))
    layer = layer.filter(ImageFilter.GaussianBlur(width(radius * 0.42)))
    base.alpha_composite(layer)


def glowing_line(
    base: Image.Image,
    points: list[tuple[float, float]],
    color: tuple[int, int, int],
    line_width: float,
    opacity: int = 220,
) -> None:
    glow_layer, glow_draw = overlay(base)
    scaled = [point(*value) for value in points]
    glow_draw.line(scaled, fill=color + (opacity // 2,), width=width(line_width * 4), joint="curve")
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(width(line_width * 3)))
    base.alpha_composite(glow_layer)
    line_layer, line_draw = overlay(base)
    line_draw.line(scaled, fill=color + (opacity,), width=width(line_width), joint="curve")
    base.alpha_composite(line_layer)


def glass_panel(
    base: Image.Image,
    bounds: tuple[float, float, float, float],
    accent: tuple[int, int, int],
    radius: float = 10,
    opacity: int = 190,
) -> None:
    left, top, right, bottom = bounds
    shadow, shadow_draw = overlay(base)
    shadow_draw.rounded_rectangle(box(left + 4, top + 8, right + 4, bottom + 8), radius=width(radius), fill=INK + (60,))
    shadow = shadow.filter(ImageFilter.GaussianBlur(width(10)))
    base.alpha_composite(shadow)

    panel, panel_draw = overlay(base)
    panel_draw.rounded_rectangle(
        box(left, top, right, bottom),
        radius=width(radius),
        fill=(248, 253, 252, opacity),
        outline=accent + (150,),
        width=width(1.1),
    )
    panel_draw.rounded_rectangle(
        box(left + 4, top + 4, right - 4, top + 9),
        radius=width(3),
        fill=accent + (105,),
    )
    base.alpha_composite(panel)


def node(base: Image.Image, center: tuple[float, float], radius: float, color: tuple[int, int, int], core: bool = False) -> None:
    glow(base, center, radius * 2.4, color, 75)
    layer, draw = overlay(base)
    draw.ellipse(box(center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius), fill=color + (235,))
    inset = radius * (0.45 if core else 0.58)
    draw.ellipse(box(center[0] - inset, center[1] - inset, center[0] + inset, center[1] + inset), fill=(247, 253, 252, 235))
    base.alpha_composite(layer)


def perspective_grid(base: Image.Image, horizon: float, bottom: float, center_x: float, span: float) -> None:
    layer, draw = overlay(base)
    for index in range(-8, 9):
        x = center_x + index * span / 8
        draw.line((point(center_x, horizon), point(x, bottom)), fill=TEAL + (30,), width=width(0.6))
    for step in range(9):
        amount = (step / 8) ** 1.8
        y = horizon + (bottom - horizon) * amount
        half = span * amount
        draw.line((point(center_x - half, y), point(center_x + half, y)), fill=TEAL + (28,), width=width(0.6))
    base.alpha_composite(layer)


def ambient_particles(base: Image.Image, region: tuple[float, float, float, float], count: int, rng: random.Random) -> None:
    left, top, right, bottom = region
    layer, draw = overlay(base)
    colors = [TEAL, CYAN, AMBER, SILVER]
    for _ in range(count):
        x = rng.uniform(left, right)
        y = rng.uniform(top, bottom)
        radius = rng.choice([0.6, 0.8, 1.0, 1.4])
        color = rng.choice(colors)
        draw.ellipse(box(x - radius, y - radius, x + radius, y + radius), fill=color + (rng.randint(45, 130),))
    base.alpha_composite(layer)


def render_banner() -> Image.Image:
    rng = random.Random(SEED)
    image = canvas((1920, 240), (225, 240, 245), (247, 239, 215))
    layer, draw = overlay(image)

    # Calm copy-safe sky on the left, grounded campus landscape on the right.
    draw.ellipse(box(1500, -90, 1780, 190), fill=(255, 218, 139, 92))
    draw.polygon([point(0, 194), point(560, 174), point(970, 187), point(1370, 161), point(1920, 176), point(1920, 240), point(0, 240)], fill=(101, 145, 113, 255))
    draw.polygon([point(0, 214), point(540, 194), point(1060, 215), point(1500, 183), point(1920, 204), point(1920, 240), point(0, 240)], fill=(58, 107, 83, 255))

    # Main school buildings, with familiar brick, glass, roof, and windows.
    buildings = [
        (1040, 88, 1295, 190, (178, 111, 77), (105, 63, 50)),
        (1265, 58, 1540, 192, (205, 177, 137), (66, 82, 84)),
        (1510, 105, 1810, 194, (156, 92, 70), (85, 56, 48)),
    ]
    for left, top, right, bottom, wall, roof in buildings:
        draw.rectangle(box(left, top, right, bottom), fill=wall + (255,))
        draw.polygon([point(left - 14, top), point((left + right) / 2, top - 27), point(right + 14, top), point(right, top + 9), point(left, top + 9)], fill=roof + (255,))
        for row in range(2):
            for column in range(max(3, int((right - left) / 54))):
                x = left + 24 + column * 49
                y = top + 26 + row * 38
                draw.rounded_rectangle(box(x, y, x + 23, y + 19), radius=width(2), fill=(181, 220, 224, 255), outline=(74, 96, 99, 190), width=width(1))

    # Campus entrance and library glass face.
    draw.rectangle(box(1352, 95, 1454, 192), fill=(73, 112, 116, 255))
    for x in range(1362, 1450, 18):
        draw.rectangle(box(x, 103, x + 11, 185), fill=(185, 224, 225, 230))
    draw.polygon([point(1308, 193), point(1495, 193), point(1535, 240), point(1248, 240)], fill=(211, 202, 176, 255))

    # Trees and human-scale campus details.
    for x, y, size in [(925, 178, 22), (1005, 191, 16), (1195, 198, 17), (1580, 198, 22), (1840, 196, 24), (1895, 204, 18)]:
        draw.rectangle(box(x - 2, y, x + 3, y + size), fill=(91, 68, 48, 255))
        draw.ellipse(box(x - size, y - size, x + size, y + size), fill=(66, 123, 83, 255))
        draw.ellipse(box(x - size * .7, y - size * 1.25, x + size * .6, y + size * .35), fill=(89, 146, 94, 255))
    for x in [1160, 1665, 1740]:
        draw.ellipse(box(x, 213, x + 7, 220), fill=(31, 46, 50, 255))
        draw.line((point(x + 3, 220), point(x + rng.choice([-4, 4]), 234)), fill=(31, 46, 50, 220), width=width(1.3))

    # Restrained analytics motif: one thin route, not a sci-fi network.
    route = [point(1010, 58), point(1190, 42), point(1370, 64), point(1555, 37), point(1775, 55)]
    draw.line(route, fill=(31, 112, 113, 145), width=width(1.3), joint="curve")
    for x, y in [(1010, 58), (1190, 42), (1370, 64), (1555, 37), (1775, 55)]:
        draw.ellipse(box(x - 3, y - 3, x + 3, y + 3), fill=(248, 252, 249, 255), outline=(31, 112, 113, 210), width=width(1))
    image.alpha_composite(layer)

    # Soft atmospheric depth, without digital glows or particles.
    haze, haze_draw = overlay(image)
    haze_draw.rectangle(box(0, 0, 900, 240), fill=(248, 251, 247, 74))
    haze = haze.filter(ImageFilter.GaussianBlur(width(18)))
    image.alpha_composite(haze)
    return image.resize((1920, 240), Image.Resampling.LANCZOS).convert("RGB")


def render_get_started() -> Image.Image:
    image = canvas((320, 180), (247, 235, 212), (229, 205, 169))
    layer, draw = overlay(image)

    # Warm top-down workspace: onboarding should feel approachable and actionable.
    draw.rectangle(box(0, 0, 320, 180), fill=(210, 178, 137, 90))
    for x in range(-40, 360, 34):
        draw.line((point(x, 0), point(x + 65, 180)), fill=(121, 91, 64, 18), width=width(1))

    # Laptop with a simple three-step setup UI.
    draw.rounded_rectangle(box(60, 23, 258, 138), radius=width(8), fill=(55, 65, 67, 255))
    draw.rounded_rectangle(box(68, 31, 250, 128), radius=width(4), fill=(244, 248, 242, 255))
    draw.polygon([point(49, 138), point(269, 138), point(287, 158), point(31, 158)], fill=(91, 101, 102, 255))
    draw.rounded_rectangle(box(122, 142, 194, 150), radius=width(3), fill=(132, 141, 140, 255))

    # Screen content: folder, checklist, and progress steps without text.
    draw.rounded_rectangle(box(82, 48, 128, 87), radius=width(4), fill=(225, 178, 84, 255))
    draw.rounded_rectangle(box(87, 43, 107, 53), radius=width(3), fill=(238, 194, 105, 255))
    for index, y in enumerate([49, 70, 91]):
        color = (44, 130, 105) if index < 2 else (159, 170, 166)
        draw.ellipse(box(151, y, 161, y + 10), fill=color + (255,))
        if index < 2:
            draw.line((point(153, y + 5), point(156, y + 8), point(160, y + 2)), fill=(250, 252, 248, 255), width=width(1.2), joint="curve")
        draw.rounded_rectangle(box(170, y + 2, 230 - index * 10, y + 7), radius=width(2), fill=color + (105,))

    # Notebook, pencil, coffee, and plant make this distinct from product diagrams.
    draw.rounded_rectangle(box(10, 48, 53, 121), radius=width(4), fill=(238, 241, 226, 255), outline=(137, 117, 88, 130), width=width(1))
    for y in range(60, 112, 12):
        draw.line((point(19, y), point(45, y)), fill=(99, 126, 125, 85), width=width(1))
    draw.polygon([point(34, 32), point(40, 35), point(22, 78), point(17, 83)], fill=(190, 91, 62, 255))
    draw.ellipse(box(268, 35, 310, 76), fill=(247, 244, 227, 255), outline=(126, 91, 67, 150), width=width(1))
    draw.ellipse(box(275, 41, 303, 68), fill=(99, 62, 42, 255))
    draw.arc(box(298, 44, 319, 68), 270, 90, fill=(126, 91, 67, 180), width=width(3))
    draw.rectangle(box(270, 121, 305, 154), fill=(174, 104, 70, 255))
    for leaves in [(271, 91, 287, 131), (286, 84, 300, 129), (299, 96, 311, 135)]:
        draw.ellipse(box(*leaves), fill=(77, 132, 83, 255))
    image.alpha_composite(layer)
    return image.resize((320, 180), Image.Resampling.LANCZOS).convert("RGB")


def render_solution() -> Image.Image:
    image = canvas((984, 552), (246, 248, 246), (225, 234, 230))
    layer, draw = overlay(image)

    # Professional architectural diagram: source systems -> medallion -> report.
    draw.rounded_rectangle(box(40, 58, 944, 494), radius=width(18), fill=(252, 253, 250, 238), outline=(122, 145, 141, 100), width=width(1))
    draw.rectangle(box(40, 58, 944, 104), fill=(50, 85, 84, 255))

    # Left source-system stack uses familiar school records and learning surfaces.
    source_cards = [
        (78, 145, 238, 220, (198, 112, 72)),
        (78, 239, 238, 314, (72, 133, 160)),
        (78, 333, 238, 408, (99, 143, 92)),
    ]
    for index, (left, top, right, bottom, accent) in enumerate(source_cards):
        draw.rounded_rectangle(box(left, top, right, bottom), radius=width(8), fill=(244, 246, 240, 255), outline=accent + (170,), width=width(1.2))
        if index == 0:  # Student information card.
            draw.ellipse(box(left + 18, top + 18, left + 50, top + 50), fill=accent + (205,))
            draw.rounded_rectangle(box(left + 63, top + 18, right - 18, top + 25), radius=width(2), fill=accent + (105,))
            draw.rounded_rectangle(box(left + 63, top + 34, right - 37, top + 40), radius=width(2), fill=accent + (62,))
        elif index == 1:  # Learning assignments.
            draw.rectangle(box(left + 20, top + 17, left + 52, top + 52), fill=accent + (55,), outline=accent + (170,), width=width(1))
            for y in [top + 22, top + 32, top + 42]:
                draw.line((point(left + 27, y), point(left + 46, y)), fill=accent + (150,), width=width(1))
            for y, line_width in [(top + 20, 66), (top + 35, 52), (top + 48, 73)]:
                draw.rounded_rectangle(box(left + 66, y, left + 66 + line_width, y + 5), radius=width(2), fill=accent + (75,))
        else:  # Assessment trend.
            chart = [point(left + 20, top + 52), point(left + 53, top + 39), point(left + 88, top + 46), point(left + 124, top + 21)]
            draw.line(chart, fill=accent + (220,), width=width(2), joint="curve")
            for x, y in [(left + 20, top + 52), (left + 53, top + 39), (left + 88, top + 46), (left + 124, top + 21)]:
                draw.ellipse(box(x - 3, y - 3, x + 3, y + 3), fill=(249, 251, 246, 255), outline=accent + (220,), width=width(1))

    # Three distinct medallion storage layers, intentionally diagrammatic.
    layers = [
        (326, 168, 446, 390, (176, 105, 65)),
        (468, 146, 588, 390, (136, 151, 154)),
        (610, 124, 730, 390, (211, 158, 54)),
    ]
    for index, (left, top, right, bottom, accent) in enumerate(layers):
        draw.rounded_rectangle(box(left, top, right, bottom), radius=width(9), fill=mix((250, 250, 247), accent, 0.10) + (255,), outline=accent + (220,), width=width(1.5))
        draw.ellipse(box(left + 20, top + 21, right - 20, top + 53), fill=accent + (185,))
        draw.rectangle(box(left + 20, top + 37, right - 20, top + 69), fill=accent + (185,))
        draw.arc(box(left + 20, top + 53, right - 20, top + 83), 0, 180, fill=(249, 250, 247, 220), width=width(2))
        for row in range(4):
            y = top + 105 + row * 31
            draw.rounded_rectangle(box(left + 20, y, right - 20 - (row % 2) * 17, y + 8), radius=width(3), fill=accent + (62 + row * 17,))
        # Simple quality marker at the foot of each layer.
        draw.ellipse(box((left + right) / 2 - 12, bottom - 42, (left + right) / 2 + 12, bottom - 18), fill=accent + (210,))
        draw.line((point((left + right) / 2 - 6, bottom - 30), point((left + right) / 2 - 1, bottom - 24), point((left + right) / 2 + 8, bottom - 36)), fill=(252, 252, 248, 255), width=width(2), joint="curve")

    # Directional arrows separate transformation stages clearly.
    for start, end in [(245, 326), (446, 468), (588, 610), (730, 765)]:
        y = 269
        draw.line((point(start, y), point(end - 8, y)), fill=(61, 102, 100, 180), width=width(2))
        draw.polygon([point(end - 8, y - 6), point(end, y), point(end - 8, y + 6)], fill=(61, 102, 100, 200))

    # Right report surface reads as an actual restrained operational dashboard.
    draw.rounded_rectangle(box(765, 136, 910, 414), radius=width(10), fill=(241, 246, 244, 255), outline=(48, 105, 101, 170), width=width(1.3))
    draw.rectangle(box(765, 136, 910, 174), fill=(48, 105, 101, 255))
    draw.ellipse(box(780, 148, 790, 158), fill=(226, 181, 83, 255))
    draw.ellipse(box(797, 148, 807, 158), fill=(207, 220, 214, 255))
    draw.rounded_rectangle(box(783, 193, 892, 247), radius=width(5), fill=(252, 252, 248, 255), outline=(132, 153, 150, 70), width=width(1))
    for index, value in enumerate([17, 30, 24, 42, 38, 49]):
        x = 794 + index * 16
        draw.rounded_rectangle(box(x, 235 - value, x + 8, 235), radius=width(2), fill=(46, 131, 111, 150 + index * 12))
    draw.rounded_rectangle(box(783, 264, 892, 326), radius=width(5), fill=(252, 252, 248, 255), outline=(132, 153, 150, 70), width=width(1))
    trend = [point(793, 310), point(815, 299), point(837, 305), point(859, 280), point(882, 287)]
    draw.line(trend, fill=(197, 120, 58, 220), width=width(2), joint="curve")
    draw.rounded_rectangle(box(783, 343, 832, 393), radius=width(5), fill=(225, 237, 232, 255))
    draw.rounded_rectangle(box(843, 343, 892, 393), radius=width(5), fill=(242, 229, 198, 255))

    # Bottom status rail unifies the architecture without visual effects.
    draw.rounded_rectangle(box(78, 438, 910, 464), radius=width(7), fill=(223, 233, 228, 255))
    for index, x in enumerate([104, 280, 456, 632, 808]):
        draw.ellipse(box(x, 445, x + 12, 457), fill=[(198, 112, 72), (73, 132, 158), (136, 151, 154), (211, 158, 54), (48, 105, 101)][index] + (255,))
        if index < 4:
            draw.line((point(x + 18, 451), point(x + 150, 451)), fill=(91, 119, 114, 80), width=width(1))

    image.alpha_composite(layer)
    return image.resize((984, 552), Image.Resampling.LANCZOS).convert("RGB")


def save(image: Image.Image, name: str) -> None:
    output = OUTPUT / name
    image.save(output, format="PNG", optimize=True, compress_level=9)
    print(f"{output.name}: {image.width}x{image.height}, {output.stat().st_size:,} bytes")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    save(render_banner(), "Education_Banner.png")
    save(render_get_started(), "Education_GetStarted.png")
    save(render_solution(), "Education_Solution.png")


if __name__ == "__main__":
    main()
