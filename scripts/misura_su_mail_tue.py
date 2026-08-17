# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Misura Mr. Rao sulle TUE mail, senza far uscire il contenuto.

Serve a colmare il buco del banco di prova: tutti i documenti su cui
abbiamo misurato finora -- moduli in bianco, gazzette, volumi statistici --
sono documenti amministrativi. Della meta' in cui il tool viene usato
davvero, lettere e thread email, non abbiamo un solo campione, perche' le
fonti pubbliche non pubblicano carteggi *privi* di dati personali: un
carteggio pubblico e' pubblico proprio perche' contiene persone.

Questo script chiude il buco senza far leggere le mail a nessuno.

**Cosa esce di qui:** solo numeri, e campioni **mascherati** con lo stesso
meccanismo che il prodotto usa gia' per i sospetti -- «RS••••••••••••2S».
Nessuna frase, nessun nome, nessun indirizzo. Il file di uscita si puo'
leggere prima di mandarlo, ed e' fatto apposta per essere corto.

**Come si usa:**

  1. Esporta le mail in .eml (in Outlook: seleziona, trascina in una
     cartella; oppure File > Salva con nome > Formato messaggio).
  2. venv\\Scripts\\python scripts\\misura_su_mail_tue.py C:\\percorso\\cartella

Le mail non vengono modificate, copiate o spostate: si leggono e basta.
Il file `misura_mail.txt` finisce accanto allo script.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
if str(RADICE) not in sys.path:
    sys.path.insert(0, str(RADICE))

from mr_rao.converter import ConvertOptions, convert_file  # noqa: E402
from mr_rao.privacy import PrivacyOptions, _mask  # noqa: E402

USCITA = Path(__file__).resolve().parent / "misura_mail.txt"
ESTENSIONI = (".eml", ".msg", ".txt", ".pdf", ".docx")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cartella = Path(sys.argv[1])
    if not cartella.is_dir():
        print(f"non e' una cartella: {cartella}", file=sys.stderr)
        return 1

    file = [p for p in sorted(cartella.rglob("*")) if p.suffix.lower() in ESTENSIONI]
    if not file:
        print(f"nessun file .eml/.msg/.pdf/.docx in {cartella}", file=sys.stderr)
        return 1

    conteggi: Counter[str] = Counter()
    sospetti: Counter[str] = Counter()
    campioni: list[str] = []
    vuoti = falliti = 0

    for i, p in enumerate(file, 1):
        print(f"[{i}/{len(file)}] {p.name[:50]}", flush=True)
        try:
            r = convert_file(str(p), options=ConvertOptions(privacy=PrivacyOptions()))
        except Exception:
            falliti += 1
            continue
        if r.error:
            falliti += 1
            continue
        rep = r.redaction
        if not rep.total:
            vuoti += 1
        conteggi.update(rep.counts)
        for s in rep.suspects:
            sospetti[s["kind"]] += 1
            if len(campioni) < 40:
                # Il campione e' gia' mascherato dal motore; si maschera di
                # nuovo per sicurezza, e si tiene solo il motivo.
                campioni.append(f"  {s['kind']:<16} {_mask(s['sample'])}  ({s['why'][:60]})")

    righe = [
        "Misura di Mr. Rao su un campione di posta personale.",
        "Contiene solo numeri e campioni mascherati: nessun contenuto.",
        "",
        f"documenti letti      {len(file)}",
        f"non convertiti       {falliti}",
        f"senza alcuna redazione {vuoti}",
        "",
        "SOSTITUZIONI (quello che il motore ha tolto)",
    ]
    for k, v in conteggi.most_common():
        righe.append(f"  {k:<20} {v:>6}   media {v / max(1, len(file)):.1f} per documento")
    righe += ["", "SOSPETTI (somiglia a un dato personale ed e' rimasto)"]
    for k, v in sospetti.most_common():
        righe.append(f"  {k:<20} {v:>6}   media {v / max(1, len(file)):.1f} per documento")
    righe += ["", "CAMPIONI MASCHERATI DEI SOSPETTI", *campioni]
    righe += [
        "",
        "Da guardare a mano, e da riferire a parole:",
        "  - fra i sospetti, quanti erano davvero persone?",
        "  - fra le sostituzioni, quante hanno tolto qualcosa che serviva?",
        "  - il conteggio dei sospetti e' consultabile o e' troppo lungo?",
    ]

    USCITA.write_text("\n".join(righe) + "\n", encoding="utf-8")
    print("\n" + "\n".join(righe[:14]))
    print(f"\nScritto {USCITA} — leggilo prima di mandarlo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
