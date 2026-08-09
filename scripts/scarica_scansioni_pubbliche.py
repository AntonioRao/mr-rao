"""Scarica scansioni di pubblico dominio, per misurare com'e' fatto il degrado.

Perche' esiste
--------------

`misura_degrado_reale.py` ha bisogno di scansioni **grezze**: carta vera
passata da uno scanner vero, senza ripulitura. Non e' facile come sembra.

FUNSD, che e' il corpus di riferimento per i moduli scansionati rumorosi, non
va bene: le sue pagine sono state **ripulite**. Misurato, non supposto —
91,5% dei pixel esattamente a 255 e deviazione standard del fondo 0,000. Il
punto di bianco e' stato tagliato, e con esso il rumore che cercavamo.

Wikimedia Commons invece ha scansioni consegnate come sono uscite dallo
scanner, in pubblico dominio.

Da piu' fonti, e non e' un dettaglio
------------------------------------

La prima raccolta ha preso quattro pagine **dalla stessa categoria**, cioe'
quasi certamente dallo stesso archivio e dallo stesso apparecchio: quattro
pagine ma un solo scanner. I parametri che se ne ricavano descrivono quella
macchina, non «una scansione».

Qui si pesca da piu' categorie indipendenti apposta. La dispersione fra
fonti diverse e' essa stessa un risultato: dice quanto un parametro sia una
costante o una caratteristica del singolo apparecchio.

Educazione verso il servizio
----------------------------

Wikimedia ha risposto `429 Too many requests` alla prima raccolta, chiedendo
di rallentare. Qui si aspetta fra una richiesta e l'altra e ci si presenta
con uno User-Agent che dice chi siamo. Le miniature che il servizio suggerisce
come alternativa **non sono utilizzabili**: ridimensionare e' un filtro, ed e'
esattamente l'informazione che stiamo cercando di misurare.

Uso:
    venv\\Scripts\\python scripts\\scarica_scansioni_pubbliche.py [--quante 20]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
DESTINAZIONE = RADICE / "corpora-locali" / "commons"

UA = "mr-rao-research/1.0 (misura del degrado di scansione; uso locale, non ridistribuito)"
API = "https://commons.wikimedia.org/w/api.php"

# Categorie indipendenti fra loro: archivi diversi, quindi apparecchi diversi.
CATEGORIE = [
    "Category:Scanned documents",
    "Category:Scanned letters",
    "Category:Typewritten documents",
    "Category:Scanned images",
    "Category:Handwritten documents",
]

PAUSA = 4.0  # secondi fra una richiesta e l'altra


def _get(url: str, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=timeout).read()


def elenco(categoria: str, quante: int) -> list[tuple[str, str]]:
    """(titolo, url) delle immagini di una categoria."""
    q = urllib.parse.urlencode(
        {
            "action": "query",
            "format": "json",
            "generator": "categorymembers",
            "gcmtitle": categoria,
            "gcmtype": "file",
            "gcmlimit": str(quante),
            "prop": "imageinfo",
            "iiprop": "url|size|mime",
        }
    )
    try:
        d = json.loads(_get(f"{API}?{q}"))
    except Exception as e:
        print(f"    {categoria}: {e}", file=sys.stderr)
        return []
    fuori = []
    for p in (d.get("query") or {}).get("pages", {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        u = (ii.get("url") or "").split("?")[0]
        if not u or not ii.get("mime", "").startswith("image/"):
            continue
        # Le pagine minuscole non servono: il rumore si misura su una
        # scansione a risoluzione piena, non su una figurina.
        if (ii.get("width") or 0) < 1200:
            continue
        fuori.append((p["title"], u))
    return fuori


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Scansioni di pubblico dominio per la misura")
    ap.add_argument("--quante", type=int, default=20, help="quante pagine in tutto")
    ap.add_argument("--per-categoria", type=int, default=6)
    args = ap.parse_args(argv)

    DESTINAZIONE.mkdir(parents=True, exist_ok=True)
    gia = {p.name for p in DESTINAZIONE.iterdir() if p.is_file()}
    print(f"  gia' presenti: {len(gia)}")

    candidati: list[tuple[str, str, str]] = []
    for cat in CATEGORIE:
        print(f"  cerco in {cat}")
        for titolo, url in elenco(cat, args.per_categoria * 3)[: args.per_categoria]:
            candidati.append((cat, titolo, url))
        time.sleep(PAUSA)

    presi = 0
    for cat, titolo, url in candidati:
        if presi >= args.quante:
            break
        nome = re.sub(
            r"[^A-Za-z0-9._-]", "_", urllib.parse.unquote(url.rsplit("/", 1)[-1])
        )[:80]
        # La cartella tiene traccia della provenienza nel nome: senza, fra un
        # mese non si sa piu' quali pagine vengono dallo stesso archivio, ed
        # e' proprio la cosa da sapere.
        sigla = re.sub(r"[^a-z]", "", cat.split(":")[-1].lower())[:6]
        finale = f"{sigla}__{nome}"
        if finale in gia:
            continue
        try:
            data = _get(url, timeout=180)
        except Exception as e:
            print(f"    salto {nome[:40]}: {e}", file=sys.stderr)
            time.sleep(PAUSA)
            continue
        (DESTINAZIONE / finale).write_bytes(data)
        presi += 1
        print(f"    {finale[:60]:60s} {len(data) / 1e6:5.1f} MB")
        time.sleep(PAUSA)

    print(f"\n  scaricate {presi} pagine nuove in {DESTINAZIONE}")
    print("  (non entrano nel repository: vedi .gitignore)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
