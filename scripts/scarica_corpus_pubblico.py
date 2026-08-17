# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Riscarica il corpus pubblico a verita' zero, da fonti versionate.

Perche' esiste
--------------

Il corpus non sta nel repository e non ci deve stare: sono documenti degli
enti che li pubblicano, e non sono nostri da ridistribuire. Fin qui, giusto.

Il difetto era un altro, e si e' visto quando il corpus non c'era piu' su
questa macchina: **non era ricostruibile**. L'atteso congelato in
`tests/dati/corpus_pubblico_atteso.json` porta un'impronta dell'elenco dei
file -- utile a sapere che il corpus e' cambiato -- ma nessun indirizzo da
cui riprendere quei file. Un banco che si puo' solo perdere, non rifare.

Questo script chiude quel buco: le fonti stanno in
`tests/dati/corpus_pubblico_fonti.json`, versionate, e da li' chiunque
ricostruisce lo stesso corpus. Il file scaricato porta con se' un
`manifesto.json` con l'impronta di ogni documento, quindi due esecuzioni
diverse si confrontano invece di doversi credere.

Cosa NON fa
-----------

Non promette che i documenti siano gli stessi di prima. Il corpus originale
aveva 54 documenti -- 27 moduli italiani, 15 IRS, 12 Gazzette -- ma i nomi
dei file non erano registrati da nessuna parte, quindi **quel corpus non e'
recuperabile**. Questo ne costruisce uno nuovo, riproducibile, e i numeri
attesi vanno rifatti su di lui: l'impronta cambia, ed e' giusto che il banco
lo dica invece di confrontare mele con pere.

Uso
---

    venv\\Scripts\\python scripts\\scarica_corpus_pubblico.py --in CARTELLA
    venv\\Scripts\\python scripts\\scarica_corpus_pubblico.py --in CARTELLA --verifica

`--verifica` non scarica niente: ricontrolla le impronte di quello che c'e'
gia' e dice cosa manca o e' cambiato.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
FONTI = RADICE / "tests" / "dati" / "corpus_pubblico_fonti.json"
NOME_MANIFESTO = "manifesto.json"

# Alcuni portali rispondono 403 a un client che non si presenta.
INTESTAZIONI = {"User-Agent": "Mozilla/5.0 (compatible; mr-rao-corpus/1.0)"}
TIMEOUT = 60


def impronta(dati: bytes) -> str:
    return hashlib.sha256(dati).hexdigest()


def scarica_uno(fonte: dict, dove: Path) -> dict:
    """Scarica un documento. Non solleva: restituisce l'esito, sempre."""
    destinazione = dove / fonte["nome"]
    try:
        richiesta = urllib.request.Request(fonte["url"], headers=INTESTAZIONI)
        with urllib.request.urlopen(richiesta, timeout=TIMEOUT) as risposta:
            dati = risposta.read()
    except (urllib.error.URLError, OSError, TimeoutError) as errore:
        return {**fonte, "esito": "non scaricato", "perche": str(errore)[:120]}

    # Un portale che risponde 200 con una pagina di errore e' il modo piu'
    # comune di ritrovarsi un corpus di HTML travestito da PDF, e un banco
    # che misura su quello e' verde per il motivo sbagliato.
    if fonte["nome"].endswith(".pdf") and not dati.startswith(b"%PDF"):
        return {**fonte, "esito": "non e' un PDF", "perche": repr(dati[:24])}

    destinazione.write_bytes(dati)
    return {**fonte, "esito": "ok", "byte": len(dati), "sha256": impronta(dati)}


def converti_tutti(dove: Path, nomi: list[str]) -> list[tuple[str, str]]:
    """Da PDF a `.txt`, con la conversione del prodotto.

    Non con una libreria qualsiasi: il banco deve misurare il motore sul
    testo **come arriva davvero**, OCR compreso dove serve. Estrarre il
    testo in un altro modo misurerebbe un percorso che nessun utente
    percorre.
    """
    if str(RADICE) not in sys.path:
        sys.path.insert(0, str(RADICE))
    from mr_rao.converter import ConvertOptions, convert_file  # noqa: PLC0415

    # `include_raw` tiene il testo **prima** della redazione in
    # `markdown_raw`, ed e' quello che serve: `markdown` e' gia' filtrato.
    #
    # Questo commento c'era gia' prima di questa riga, e il codice sotto
    # prendeva `markdown` lo stesso. Il corpus e' arrivato al banco gia'
    # redatto -- si vedeva `{{EMAIL}}` dentro le Gazzette -- e il banco ha
    # riportato **1 sostituzione su 7,9 milioni di caratteri** di prosa
    # giuridica italiana, cioe' un risultato spettacolare per il motivo
    # peggiore. Un corpus gia' pulito misura zero per costruzione.
    # `include_frontmatter=False` non e' un dettaglio estetico: il
    # frontmatter contiene `generator: "Mr. Rao 1.19.1"`, e **Rao e' un
    # cognome negli elenchi**. Lasciandolo, ogni documento del corpus
    # comincia con una sostituzione che ha prodotto il nostro convertitore,
    # non il documento -- 47 falsi positivi regalati alla misura.
    opzioni = ConvertOptions(include_raw=True, include_frontmatter=False)
    falliti: list[tuple[str, str]] = []
    for i, nome in enumerate(sorted(nomi), 1):
        sorgente = dove / nome
        destinazione = sorgente.with_suffix(".txt")
        if destinazione.exists():
            continue
        try:
            esito = convert_file(sorgente, options=opzioni)
        except Exception as errore:  # noqa: BLE001 - un documento non deve fermare il lotto
            falliti.append((nome, f"{type(errore).__name__}: {errore}"))
            continue
        # Niente ripiego su `markdown`: se il grezzo non c'e', il documento
        # si dichiara fallito. Ripiegare sul testo redatto darebbe un file
        # che sembra un documento e non lo e' piu', e nessuno se ne
        # accorgerebbe finche' i conteggi non sono assurdamente bassi.
        testo = getattr(esito, "markdown_raw", None)
        if not testo:
            falliti.append((nome, "nessun testo grezzo (markdown_raw vuoto)"))
            continue
        if "{{" in testo:
            falliti.append((nome, "il testo e' gia' redatto: contiene segnaposto"))
            continue
        destinazione.write_text(testo, encoding="utf-8")
        print(f"  [{i:3}/{len(nomi)}] {nome[:48]:50} {len(testo):>9} caratteri")
    return falliti


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--in", dest="dove", required=True, type=Path)
    p.add_argument("--verifica", action="store_true")
    p.add_argument(
        "--converti",
        action="store_true",
        help="dopo lo scaricamento produce i .txt che il banco legge, "
        "usando la conversione di Mr. Rao -- cioe' la strada da cui i "
        "documenti arrivano davvero al motore",
    )
    a = p.parse_args()

    if not FONTI.exists():
        print(f"manca l'elenco delle fonti: {FONTI}", file=sys.stderr)
        return 2
    fonti = json.loads(FONTI.read_text(encoding="utf-8"))["fonti"]

    a.dove.mkdir(parents=True, exist_ok=True)
    manifesto = a.dove / NOME_MANIFESTO

    if a.verifica:
        if not manifesto.exists():
            print(f"nessun manifesto in {a.dove}: scarica prima.", file=sys.stderr)
            return 2
        atteso = json.loads(manifesto.read_text(encoding="utf-8"))["documenti"]
        guasti = 0
        for d in atteso:
            f = a.dove / d["nome"]
            if not f.exists():
                print(f"  MANCA      {d['nome']}")
                guasti += 1
            elif impronta(f.read_bytes()) != d["sha256"]:
                print(f"  CAMBIATO   {d['nome']}")
                guasti += 1
        print(f"\n{len(atteso) - guasti}/{len(atteso)} documenti integri")
        return 1 if guasti else 0

    print(f"{len(fonti)} fonti -> {a.dove}")
    with ThreadPoolExecutor(max_workers=6) as ex:
        esiti = list(ex.map(lambda f: scarica_uno(f, a.dove), fonti))

    ok = [e for e in esiti if e["esito"] == "ok"]
    ko = [e for e in esiti if e["esito"] != "ok"]

    manifesto.write_text(
        json.dumps(
            {
                "documenti": [
                    {"nome": e["nome"], "gruppo": e["gruppo"], "url": e["url"],
                     "byte": e["byte"], "sha256": e["sha256"]}
                    for e in sorted(ok, key=lambda e: e["nome"])
                ]
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )

    per_gruppo: dict[str, list] = {}
    for e in ok:
        per_gruppo.setdefault(e["gruppo"], []).append(e)
    for g in sorted(per_gruppo):
        n = per_gruppo[g]
        print(f"  {g:8} {len(n):3} documenti  {sum(x['byte'] for x in n) / 1e6:7.1f} MB")

    # Quello che non e' arrivato si dice, non si tace: un corpus a meta' che
    # sembra intero produce numeri piu' bassi e nessun sospetto.
    if ko:
        print(f"\n{len(ko)} NON scaricati:")
        for e in ko:
            print(f"  {e['nome']:52} {e['esito']}: {e['perche'][:60]}")
    print(f"\n{len(ok)}/{len(fonti)} documenti, manifesto in {manifesto}")

    if a.converti:
        print("\nconversione in testo (e' la stessa che usa il prodotto):")
        falliti = converti_tutti(a.dove, [e["nome"] for e in ok])
        if falliti:
            print(f"  {len(falliti)} NON convertiti:")
            for nome, perche in falliti:
                print(f"    {nome:52} {perche[:60]}")
        print(f"  {len(ok) - len(falliti)}/{len(ok)} convertiti")
        return 1 if (ko or falliti) else 0

    return 1 if ko else 0


if __name__ == "__main__":
    raise SystemExit(main())
