"""Rebuild favicon / mr-rao.ico from static/img/logo.png (site mark)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static" / "img"


def main() -> None:
    src_path = OUT / "logo.png"
    if not src_path.exists():
        raise SystemExit(f"Missing {src_path}")

    src = Image.open(src_path).convert("RGBA")
    sizes = [16, 24, 32, 48, 64, 128, 256]
    frames: list[Image.Image] = []
    for s in sizes:
        im = src.resize((s, s), Image.Resampling.LANCZOS)
        frames.append(im)
        im.save(OUT / f"favicon-{s}.png", format="PNG", optimize=True)

    frames[sizes.index(64)].save(OUT / "favicon.png", format="PNG", optimize=True)

    # Multi-size Windows ICO (Desktop shortcut)
    frames[-1].save(
        OUT / "mr-rao.ico",
        format="ICO",
        sizes=[(s, s) for s in sizes],
    )
    # Browser favicon.ico
    frames[sizes.index(32)].save(
        OUT / "favicon.ico",
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48)],
    )

    # Keep favicon.svg in sync with logo.svg aesthetics
    (OUT / "favicon.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="Mr RAO">
  <defs>
    <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#2563eb"/>
      <stop offset="55%" stop-color="#7c3aed"/>
      <stop offset="100%" stop-color="#0891b2"/>
    </linearGradient>
  </defs>
  <rect width="64" height="64" rx="14" fill="url(#g)"/>
  <rect x="4" y="4" width="56" height="56" rx="12" fill="none" stroke="rgba(255,255,255,0.16)" stroke-width="1"/>
  <text x="32" y="26" text-anchor="middle" font-family="Segoe UI, system-ui, sans-serif"
        font-size="15" font-weight="700" fill="rgba(236,240,255,0.98)" letter-spacing="0.04em">Mr</text>
  <text x="32" y="46" text-anchor="middle" font-family="Segoe UI, system-ui, sans-serif"
        font-size="18" font-weight="800" fill="#ffffff" letter-spacing="0.04em">RAO</text>
  <rect x="20" y="51" width="24" height="2" rx="1" fill="rgba(180,195,255,0.65)"/>
</svg>
""",
        encoding="utf-8",
    )

    print("Synced icons from logo.png:")
    for name in ("mr-rao.ico", "favicon.ico", "favicon.png", "favicon.svg"):
        p = OUT / name
        print(f"  {name:16} {p.stat().st_size:6d} B")


if __name__ == "__main__":
    main()
