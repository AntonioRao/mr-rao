# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
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


# Cartelle che non entrano nel pacchetto Store.
#
# `default-docx-template` e' la forma **scompattata** del modello di
# python-docx, spedita dentro la libreria ma mai aperta: `docx/api.py` carica
# `templates/default.docx`, cioe' lo zip. Verificato, non dedotto -- nel
# codice della libreria la cartella non compare da nessuna parte.
#
# Va tolta perche' contiene `[Content_Types].xml`, che in un pacchetto MSIX
# e' un **nome riservato**: quel file lo genera MakeAppx alla radice. Con
# dentro quella cartella, MakeAppx enumera tutti i 2750 file e poi risponde
# `0x8007007b - nome di file non valido`, senza dire quale. La diagnosi costa
# un giro di CI intero, ed e' il motivo per cui qui sotto c'e' anche un
# rilevatore che lo dice prima.
#
# Riguarda **solo** l'MSIX: nello zip portable la cartella resta, e la
# libreria continua a funzionare identica nelle due confezioni.
#
# `uploads` non entra nel pacchetto, ed e' la seconda meta' della
# correzione al crash all'avvio della 1.20.0.
#
# Nel portable quella cartella e' giusta: sta accanto all'eseguibile ed e'
# scrivibile. Dentro un MSIX finisce in `Program Files\WindowsApps`, dove
# **non si puo' scrivere**: una cartella degli upload li' dentro non e' un
# posto dove caricare qualcosa, e' un posto che sembra pronto e non lo e'.
# I dati adesso vanno nel profilo dell'utente (`config._writable_dir`).
#
# Ed e' anche quello che ha reso il difetto invisibile a lungo: la cartella
# c'era nel layout, quindi sembrava tutto a posto — ma **e' vuota**, e le
# cartelle vuote non sopravvivono all'impacchettamento. Nel pacchetto finito
# non c'era, il `mkdir` all'avvio doveva crearla in sola lettura, e il
# programma moriva prima di stampare una riga.
ESCLUSI = ("default-docx-template", "uploads")

# Nomi che MSIX riserva a se'. Alla radice del pacchetto il manifesto ci
# deve stare; ovunque altro sono un errore.
RISERVATI_OVUNQUE = {"[content_types].xml", "appxblockmap.xml", "appxsignature.p7x"}
RISERVATI_ALLA_RADICE = {"appxmanifest.xml"}
VIETATI = '<>:"|?*'


def nomi_illegali(layout: Path) -> list[str]:
    """I file che MakeAppx rifiutera', trovati prima di chiamarlo.

    MakeAppx segnala il problema con un codice di errore e senza nominare il
    file: leggerlo e' un giro di CI da venti minuti per una diagnosi che si
    puo' fare in mezzo secondo.
    """
    problemi: list[str] = []
    for p in layout.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(layout)
        nome = p.name
        minuscolo = nome.lower()
        alla_radice = len(rel.parts) == 1

        if minuscolo in RISERVATI_OVUNQUE:
            problemi.append(f"{rel}: '{nome}' e' un nome riservato da MSIX")
        elif minuscolo in RISERVATI_ALLA_RADICE and not alla_radice:
            problemi.append(f"{rel}: '{nome}' e' ammesso solo alla radice")
        elif minuscolo.startswith("appxmetadata"):
            problemi.append(f"{rel}: il prefisso 'AppxMetadata' e' riservato")
        elif nome != nome.strip() or nome.endswith("."):
            problemi.append(f"{rel}: il nome finisce con uno spazio o un punto")
        elif any(c in nome for c in VIETATI):
            problemi.append(f"{rel}: contiene un carattere vietato")
    return problemi


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

    shutil.copytree(
        pacchetto / "app", layout / "app", ignore=shutil.ignore_patterns(*ESCLUSI)
    )
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

    problemi = nomi_illegali(layout)
    if problemi:
        print("ERRORE: nomi che MakeAppx rifiutera':", file=sys.stderr)
        for p in problemi:
            print(f"  {p}", file=sys.stderr)
        print(
            "  Se il file serve davvero, va rinominato a monte; se e' un "
            "residuo, aggiungilo a ESCLUSI in questo script.",
            file=sys.stderr,
        )
        return 1

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
