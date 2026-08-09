"""Monta e impacchetta l'MSIX per il Microsoft Store.

Due mestieri, separati apposta:

* **montaggio** — mettere in una cartella cio' che deve finire nel pacchetto.
  Non richiede niente di Windows, quindi si prova ovunque e ha dei test;
* **impacchettamento** — `MakeAppx.exe`, che sta nel Windows SDK. Sui runner
  `windows-latest` c'e'; su una macchina di sviluppo qualunque no. Percio' il
  primo passo non dipende dal secondo: chi non ha l'SDK puo' comunque
  guardare cosa finirebbe dentro.

Cosa NON entra nel pacchetto, ed e' voluto: `Installa Mr Rao.bat`,
`Disinstalla Mr Rao.bat` e `mr_rao_shell.ps1`. Nello Store l'installazione la
fa Windows e le voci di menu le dichiara il manifesto; portarsi dietro uno
script che scrive nel registro sarebbe, nella migliore delle ipotesi, codice
morto dentro un pacchetto sotto certificazione.

Le licenze invece entrano: pystray e' LGPL, e gli obblighi di
redistribuzione valgono per ogni confezione, non solo per lo zip.

Uso:  python scripts/make_msix.py [--solo-layout]
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import APP_VERSION  # noqa: E402

PACCHETTO = ROOT / "dist" / "MrRao-Portable"
LAYOUT = ROOT / "dist" / "msix-layout"
MANIFESTO = ROOT / "packaging" / "AppxManifest.xml"
ASSETS = ROOT / "packaging" / "Assets"


def monta(pacchetto: Path = PACCHETTO, layout: Path = LAYOUT) -> Path:
    """Costruisce la cartella che MakeAppx impacchettera'."""
    eseguibile = pacchetto / "app" / "MrRao.exe"
    if not eseguibile.is_file():
        raise FileNotFoundError(
            f"manca {eseguibile}: costruisci prima il portable "
            "(scripts\\build_portable.bat)"
        )
    if not MANIFESTO.is_file():
        raise FileNotFoundError(f"manca il manifesto {MANIFESTO}")
    if not ASSETS.is_dir() or not any(ASSETS.glob("*.png")):
        raise FileNotFoundError(
            f"mancano le immagini in {ASSETS}: "
            "python scripts/generate_msix_assets.py"
        )

    if layout.exists():
        shutil.rmtree(layout)
    layout.mkdir(parents=True)

    shutil.copytree(pacchetto / "app", layout / "app")
    shutil.copytree(ASSETS, layout / "Assets")
    shutil.copy2(MANIFESTO, layout / "AppxManifest.xml")

    # Licenze: obbligo di redistribuzione, non cortesia.
    for sorgente, destinazione in (
        (ROOT / "LICENSE", layout / "LICENSE.txt"),
        (ROOT / "THIRD_PARTY.md", layout / "THIRD_PARTY.md"),
    ):
        if sorgente.is_file():
            shutil.copy2(sorgente, destinazione)
    if (ROOT / "licenses").is_dir():
        shutil.copytree(ROOT / "licenses", layout / "licenses")

    return layout


def trova_makeappx() -> Path | None:
    """La versione piu' recente dell'SDK, non la prima che capita.

    Gli SDK si accumulano: pescare la prima significa impacchettare con uno
    strumento di cinque anni fa su una macchina che ne ha uno nuovo, e
    scoprirlo da un errore di certificazione.
    """
    import os

    radici = [
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
    ]
    trovati: list[Path] = []
    for radice in radici:
        bin_kit = radice / "Windows Kits" / "10" / "bin"
        if bin_kit.is_dir():
            trovati += list(bin_kit.glob("*/x64/makeappx.exe"))
    if not trovati:
        return None
    return sorted(trovati, key=lambda p: p.parent.parent.name)[-1]


def main() -> int:
    try:
        layout = monta()
    except FileNotFoundError as e:
        print(f"ERRORE: {e}", file=sys.stderr)
        return 1

    quanti = sum(1 for _ in layout.rglob("*") if _.is_file())
    print(f"  layout pronto: {layout}  ({quanti} file)")

    if "--solo-layout" in sys.argv:
        return 0

    makeappx = trova_makeappx()
    if makeappx is None:
        print(
            "ERRORE: MakeAppx.exe non trovato. Fa parte del Windows SDK, che "
            "sui runner windows-latest c'e' e su una macchina di sviluppo "
            "spesso no.\n"
            "  Per vedere solo cosa finirebbe nel pacchetto: --solo-layout",
            file=sys.stderr,
        )
        return 1

    uscita = ROOT / "dist" / f"MrRao-{APP_VERSION}.msix"
    print(f"  {makeappx}")
    esito = subprocess.run(
        [str(makeappx), "pack", "/d", str(layout), "/p", str(uscita), "/o"],
        capture_output=True,
        text=True,
    )
    sys.stdout.write(esito.stdout)
    if esito.returncode != 0:
        sys.stderr.write(esito.stderr)
        print(f"ERRORE: MakeAppx ha risposto {esito.returncode}", file=sys.stderr)
        return esito.returncode

    print(f"  {uscita.name}  {uscita.stat().st_size / 1e6:.1f} MB")
    print()
    print("  Non e' firmato, ed e' giusto cosi': lo firma Microsoft dopo la")
    print("  certificazione. E' l'intero motivo per cui questa strada non")
    print("  costa un certificato.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
