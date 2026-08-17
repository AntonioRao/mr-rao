# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Genera l'anteprima social 1280x640 da scripts/social-card.html.

Perché una card disegnata e non uno screenshot dell'app: nel feed di LinkedIn
la card viene mostrata larga circa 450 px. Uno screenshot di pagina, a quella
scala, ha il testo intorno ai 5 px — illeggibile, e all'occhio sembra sfocato
anche quando il file è perfettamente nitido. Serve tipografia grande e poco
testo, cioè una pagina fatta apposta.

Renderizzata a scala 2 (2560x1280) e poi ridotta a 1280x640: il
sovracampionamento rende i bordi del testo molto più puliti.

Uso:
    venv\\Scripts\\python scripts\\make_social_card.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SORGENTE = ROOT / "scripts" / "social-card.html"
OUT = ROOT / "docs" / "img" / "social-preview.png"

CHROME_CANDIDATI = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe",
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
]


def trova_browser() -> Path | None:
    for p in CHROME_CANDIDATI:
        if p.exists():
            return p
    return None


def main() -> int:
    from PIL import Image

    browser = trova_browser()
    if browser is None:
        print("Chrome o Edge non trovati.", file=sys.stderr)
        return 1
    if not SORGENTE.exists():
        print(f"Manca {SORGENTE}", file=sys.stderr)
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    grezzo = OUT.parent / "_card_grezza.png"
    profilo = OUT.parent / "_chrome_card_profile"
    try:
        subprocess.run(
            [
                str(browser),
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--force-device-scale-factor=2",
                "--window-size=1280,640",
                "--virtual-time-budget=4000",
                "--allow-file-access-from-files",
                f"--screenshot={grezzo}",
                f"--user-data-dir={profilo}",
                SORGENTE.as_uri(),
            ],
            check=True,
            capture_output=True,
        )
        if not grezzo.exists():
            print("Chrome non ha prodotto l'immagine.", file=sys.stderr)
            return 1

        im = Image.open(grezzo).convert("RGB")
        if im.size != (1280, 640):
            im = im.resize((1280, 640), Image.LANCZOS)
        im.save(OUT, optimize=True)
        print(f"{OUT.relative_to(ROOT)}  {im.size[0]}x{im.size[1]}  "
              f"{OUT.stat().st_size // 1024} KB")
        return 0
    finally:
        grezzo.unlink(missing_ok=True)
        shutil.rmtree(profilo, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
