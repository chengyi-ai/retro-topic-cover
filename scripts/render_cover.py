#!/usr/bin/env python3
"""Render a reusable 3:4 retro Chinese topic cover from real source images."""

from __future__ import annotations

import argparse
import random
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FONT = ROOT / "assets" / "NotoSerifSC-Black.ttf"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--title-y", type=float, default=.49)
    p.add_argument("--main", required=True, help="Main real photograph or artwork")
    p.add_argument("--collage", help="JSON layout with 1–3 transparent PNG cutouts")
    p.add_argument("--line1", required=True, help="Large off-white headline line")
    p.add_argument("--line2", required=True, help="Red headline line")
    p.add_argument("--output", required=True, help="Output JPG or PNG")
    p.add_argument("--width", type=int, default=1440)
    p.add_argument("--height", type=int, default=1920)
    p.add_argument("--accent", default="#da201e", help="Accent color as #RRGGBB")
    p.add_argument("--focus-x", type=float, default=0.50, help="Main crop focus, 0..1")
    p.add_argument("--focus-y", type=float, default=0.47, help="Main crop focus, 0..1")
    p.add_argument("--no-inserts", action="store_true", help="Hide supporting images")
    p.add_argument("--font", default=str(DEFAULT_FONT), help="Chinese font file")
    return p.parse_args()


def cover_crop(im: Image.Image, size: tuple[int, int], fx=0.5, fy=0.5) -> Image.Image:
    tw, th = size
    scale = max(tw / im.width, th / im.height)
    nw, nh = round(im.width * scale), round(im.height * scale)
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    left = max(0, min(nw - tw, round(nw * fx - tw / 2)))
    top = max(0, min(nh - th, round(nh * fy - th / 2)))
    return im.crop((left, top, left + tw, top + th))


def fit_font(font_path: str, text: str, max_width: int, start: int) -> ImageFont.FreeTypeFont:
    for size in range(start, 39, -2):
        font = ImageFont.truetype(font_path, size)
        if font.getlength(text) <= max_width:
            return font
    return ImageFont.truetype(font_path, 40)


def draw_shadow_text(canvas: Image.Image, xy, text, font, fill, outline):
    x, y = xy
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.text(
        (x + 12, y + 15), text, font=font, fill=(0, 0, 0, 225),
        stroke_width=3, stroke_fill=(0, 0, 0, 190), anchor="la"
    )
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(2)))
    ImageDraw.Draw(canvas).text(
        (x, y), text, font=font, fill=fill,
        stroke_width=0, stroke_fill=outline, anchor="la"
    )


def hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) != 6:
        raise ValueError("--accent must be a six-digit hex color")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def main() -> None:
    args = parse_args()
    w, h = args.width, args.height
    if w < 320 or h < 320 or not 0 <= args.title_y <= .75:
        raise ValueError("Dimensions must be >=320 and title-y must be 0..0.75")
    accent_rgb = hex_rgb(args.accent)
    accent = (*accent_rgb, 255)
    warm_outline = (238, 224, 190, 235)

    main_image = Image.open(args.main).convert("RGB")
    main_image = cover_crop(main_image, (w, h), args.focus_x, args.focus_y)
    main_image = ImageEnhance.Contrast(main_image).enhance(1.08)
    main_image = ImageEnhance.Color(main_image).enhance(0.90)
    canvas = main_image.convert("RGBA")

    # Directional editorial wash; intentionally non-generative.
    wash = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    wp = wash.load()
    for y in range(h):
        for x in range(w):
            edge = max(0.0, min(1.0, (x - w * 0.48) / (w * 0.52)))
            top = max(0.0, 1.0 - y / (h * 0.95))
            alpha = int(6 + 40 * edge + 5 * top)
            wp[x, y] = (*accent_rgb, alpha)
    canvas = Image.alpha_composite(canvas, wash)

    vignette = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(vignette).rectangle((0, int(h * 0.46), w, h), fill=(18, 8, 4, 52))
    canvas = Image.alpha_composite(canvas, vignette.filter(ImageFilter.GaussianBlur(55)))

    font1 = fit_font(args.font, args.line1, int(w * .86), int(w * .145))
    font2 = fit_font(args.font, args.line2, int(w * .92), int(w * .105))
    draw_shadow_text(canvas, (int(w * .055), int(h * args.title_y)), args.line1, font1, (248, 244, 229, 255), warm_outline)
    draw_shadow_text(canvas, (int(w * .94 - font2.getlength(args.line2)), int(h * (args.title_y + .115))), args.line2, font2, accent, warm_outline)

    if args.collage and not args.no_inserts:
        layout_path = Path(args.collage)
        layout = json.loads(layout_path.read_text(encoding="utf-8"))
        items = layout["cutouts"]
        if not 1 <= len(items) <= 3:
            raise ValueError("Use 1–3 cutouts")
        foreground = Image.new("RGBA", canvas.size)
        for item in items:  # back to front
            path = layout_path.parent / item["path"]
            im = Image.open(path).convert("RGBA")
            if im.getchannel("A").getextrema()[0] == 255:
                raise ValueError(f"Cutout must contain transparency: {path}")
            width = round(item["width"] * w)
            if width < 1:
                raise ValueError("Cutout width must be positive")
            im = im.resize((width, round(im.height * width / im.width)), Image.Resampling.LANCZOS)
            x, y = round(item["x"] * w), round(item["y"] * h)
            pad = max(1, round(w / 30))
            mask = Image.new("L", (im.width + 2*pad, im.height + 2*pad))
            mask.paste(im.getchannel("A"), (pad, pad))
            shadow = Image.new("RGBA", mask.size, layout.get("shadow_color", "#811b20"))
            shadow.putalpha(mask.filter(ImageFilter.GaussianBlur(w / 144)).point(lambda v: round(v * .78)))
            foreground.alpha_composite(shadow, (x-pad+round(w/120), y-pad+round(h/192)))
            foreground.alpha_composite(im, (x, y))
        inset = 10 + max(8, round(w / 72))
        canvas.alpha_composite(foreground.crop((inset,inset,w-inset,h-inset)),(inset,inset))

    d = ImageDraw.Draw(canvas)
    d.rectangle((10, 10, w - 11, h - 11), outline=accent, width=max(8, round(w / 72)))
    

    random.seed(221)
    grain = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grain)
    for _ in range(round(w * h * 0.0087)):
        x, y = random.randrange(w), random.randrange(h)
        c = 255 if random.random() > 0.5 else 0
        gd.point((x, y), fill=(c, c, c, random.randrange(4, 18)))
    canvas = Image.alpha_composite(canvas, grain)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    final = canvas.convert("RGB").filter(ImageFilter.UnsharpMask(radius=1.2, percent=115, threshold=4))
    if output.suffix.lower() == ".png":
        final.save(output, optimize=True)
    else:
        final.save(output, quality=94, subsampling=0)


if __name__ == "__main__":
    main()
