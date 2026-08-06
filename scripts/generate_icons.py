"""Generate Mr. Rao brand assets: SVG, PNG, multi-size ICO.

Typography priority: large RAO + readable Mr (not tiny).
Run: python scripts/generate_icons.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static" / "img"
OUT.mkdir(parents=True, exist_ok=True)


def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates += [
            r"C:\Windows\Fonts\segoeuib.ttf",
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\calibrib.ttf",
            r"C:\Windows\Fonts\Bahnschrift.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
    else:
        candidates += [
            r"C:\Windows\Fonts\segoeuib.ttf",  # prefer bold for Mr too (legibility)
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _lerp(a: tuple[int, ...], b: tuple[int, ...], t: float) -> tuple[int, ...]:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def _rounded_mask(size: int, radius: float) -> Image.Image:
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return m


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    cy: float,
    size: int,
    fill=(255, 255, 255, 252),
    tracking: float = 0.0,
) -> tuple[float, float, float, float]:
    """Draw text centered horizontally at vertical center cy. Returns bbox (x0,y0,x1,y1)."""
    if tracking <= 0 or len(text) < 2:
        bb = draw.textbbox((0, 0), text, font=font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        x = (size - tw) / 2 - bb[0]
        y = cy - th / 2 - bb[1]
        draw.text((x + max(1, size // 256), y + max(1, size // 256)), text, font=font, fill=(0, 0, 0, 55))
        draw.text((x, y), text, font=font, fill=fill)
        return (x + bb[0], y + bb[1], x + bb[2], y + bb[3])

    # Manual tracking
    widths = []
    heights = []
    for ch in text:
        b = draw.textbbox((0, 0), ch, font=font)
        widths.append(b[2] - b[0])
        heights.append(b[3] - b[1])
    total = sum(widths) + tracking * (len(text) - 1)
    th = max(heights)
    x_cursor = (size - total) / 2
    y_top = cy - th / 2
    for i, ch in enumerate(text):
        b = draw.textbbox((0, 0), ch, font=font)
        x = x_cursor - b[0]
        y = y_top - b[1]
        draw.text((x + 1, y + 1), ch, font=font, fill=(0, 0, 0, 50))
        draw.text((x, y), ch, font=font, fill=fill)
        x_cursor += widths[i] + tracking
    return (size / 2 - total / 2, y_top, size / 2 + total / 2, y_top + th)


def render_mark(size: int = 512, *, favicon: bool = False) -> Image.Image:
    """App mark: big RAO, clearly readable Mr."""
    base = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = base.load()
    c0 = (37, 99, 235, 255)
    c1 = (124, 58, 237, 255)
    c2 = (6, 182, 212, 255)
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * max(size - 1, 1))
            u = x / max(size - 1, 1)
            v = y / max(size - 1, 1)
            mid = _lerp(c0, c1, t)
            wash = _lerp(mid, c2, max(0.0, (u + v - 1.0) * 0.55))
            px[x, y] = wash

    radius = size * 0.22
    mask = _rounded_mask(size, radius)
    tile = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    tile.paste(base, mask=mask)

    vignette = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vignette)
    pad = int(size * 0.04)
    vd.rounded_rectangle(
        (pad, pad, size - pad - 1, size - pad - 1),
        radius=radius * 0.85,
        outline=(255, 255, 255, 40),
        width=max(1, size // 128),
    )
    tile = Image.alpha_composite(tile, vignette)
    draw = ImageDraw.Draw(tile)

    if size <= 20:
        # monogram only
        font = _font(max(10, int(size * 0.55)), bold=True)
        _draw_centered_text(draw, "R", font, size * 0.50, size)
    elif size <= 36:
        # RAO only — max size for tiny icons
        font = _font(max(12, int(size * 0.38)), bold=True)
        _draw_centered_text(draw, "RAO", font, size * 0.52, size, tracking=size * 0.02)
    else:
        # Full lockup: Mr readable + RAO dominant, both inside safe padding
        mr_px = max(18, int(size * 0.26))
        rao_px = max(26, int(size * 0.42))
        if favicon and size < 64:
            mr_px = max(14, int(size * 0.24))
            rao_px = max(18, int(size * 0.38))
        font_mr = _font(mr_px, bold=True)
        font_rao = _font(rao_px, bold=True)

        # Fit RAO within ~86% width (avoid clipping on rounded corners)
        max_w = size * 0.86
        tracking = size * 0.012
        for _ in range(8):
            widths = []
            for ch in "RAO":
                b = draw.textbbox((0, 0), ch, font=font_rao)
                widths.append(b[2] - b[0])
            total = sum(widths) + tracking * 2
            if total <= max_w:
                break
            rao_px = max(16, int(rao_px * 0.92))
            font_rao = _font(rao_px, bold=True)

        cy_mr = size * 0.28
        cy_rao = size * 0.56
        _draw_centered_text(
            draw, "Mr", font_mr, cy_mr, size, fill=(236, 240, 255, 250), tracking=size * 0.008
        )
        _draw_centered_text(
            draw, "RAO", font_rao, cy_rao, size, fill=(255, 255, 255, 255), tracking=tracking
        )
        line_w = min(size * 0.40, max_w * 0.55)
        ly = size * 0.76
        lx0 = (size - line_w) / 2
        draw.rounded_rectangle(
            (lx0, ly, lx0 + line_w, ly + max(2, size * 0.014)),
            radius=size * 0.01,
            fill=(180, 195, 255, 170),
        )

    glow = tile.filter(ImageFilter.GaussianBlur(radius=max(1, size // 64)))
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow_alpha = glow.split()[3].point(lambda a: int(a * 0.22))
    glow.putalpha(glow_alpha)
    canvas = Image.alpha_composite(canvas, glow)
    canvas = Image.alpha_composite(canvas, tile)
    return canvas


def write_svg() -> None:
    logo = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" role="img" aria-label="Mr RAO">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#2563eb"/>
      <stop offset="55%" stop-color="#7c3aed"/>
      <stop offset="100%" stop-color="#0891b2"/>
    </linearGradient>
    <filter id="soft" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="4" stdDeviation="8" flood-color="#1e3a8a" flood-opacity="0.35"/>
    </filter>
  </defs>
  <rect x="16" y="16" width="480" height="480" rx="112" fill="url(#bg)" filter="url(#soft)"/>
  <rect x="36" y="36" width="440" height="440" rx="100" fill="none" stroke="rgba(255,255,255,0.16)" stroke-width="2"/>
  <text x="256" y="175" text-anchor="middle"
        font-family="Segoe UI, system-ui, -apple-system, sans-serif"
        font-size="120" font-weight="700" fill="rgba(236,240,255,0.98)" letter-spacing="0.06em">Mr</text>
  <text x="256" y="330" text-anchor="middle"
        font-family="Segoe UI, system-ui, -apple-system, sans-serif"
        font-size="175" font-weight="800" fill="#ffffff" letter-spacing="0.04em">RAO</text>
  <rect x="168" y="372" width="176" height="10" rx="5" fill="rgba(180,195,255,0.65)"/>
</svg>
"""
    favicon = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="Mr RAO">
  <defs>
    <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#2563eb"/>
      <stop offset="100%" stop-color="#7c3aed"/>
    </linearGradient>
  </defs>
  <rect width="64" height="64" rx="14" fill="url(#g)"/>
  <text x="32" y="26" text-anchor="middle" font-family="Segoe UI, system-ui, sans-serif"
        font-size="16" font-weight="700" fill="rgba(236,240,255,0.98)" letter-spacing="0.04em">Mr</text>
  <text x="32" y="48" text-anchor="middle" font-family="Segoe UI, system-ui, sans-serif"
        font-size="20" font-weight="800" fill="#ffffff" letter-spacing="0.04em">RAO</text>
</svg>
"""
    (OUT / "logo.svg").write_text(logo, encoding="utf-8")
    (OUT / "favicon.svg").write_text(favicon, encoding="utf-8")
    print(f"  wrote {OUT / 'logo.svg'}")
    print(f"  wrote {OUT / 'favicon.svg'}")


def main() -> None:
    print("Generating Mr. Rao icons (large RAO, readable Mr)...")
    write_svg()

    master = render_mark(512, favicon=False)
    master.save(OUT / "logo.png", format="PNG", optimize=True)
    print(f"  wrote {OUT / 'logo.png'}")

    for s in (16, 32, 48, 64, 128, 256):
        render_mark(s, favicon=True).save(OUT / f"favicon-{s}.png", format="PNG", optimize=True)
    render_mark(64, favicon=True).save(OUT / "favicon.png", format="PNG", optimize=True)
    print("  wrote favicon-*.png + favicon.png")

    ico_master = render_mark(256, favicon=True)
    ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    ico_path = OUT / "mr-rao.ico"
    ico_master.save(ico_path, format="ICO", sizes=ico_sizes)
    ico_master.save(OUT / "favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])
    print(f"  wrote {ico_path}")
    print(f"  wrote {OUT / 'favicon.ico'}")
    # Prefer raster derived from final logo.png so ICO == site mark
    try:
        from scripts.sync_icons_from_logo import main as sync_main

        print("Syncing ICO/favicon from logo.png …")
        sync_main()
    except Exception as e:
        print(f"  (sync_icons_from_logo skipped: {e})")
    print("Done.")


if __name__ == "__main__":
    main()
