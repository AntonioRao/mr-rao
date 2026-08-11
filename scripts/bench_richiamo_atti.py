"""Richiamo delle tre categorie del pacchetto «atti e pratiche».

Il buco che questo banco chiude
-------------------------------

Di `CATASTO`, `PRATICA` e `TARGA` sappiamo quanto **costano**: misurato, zero
falsi positivi su 47 documenti pubblici, e 91 numeri di pratica guardati uno
per uno. Non sappiamo quanto ne **perdiamo**, ed e' la meta' che conta di piu':
un falso positivo si vede rileggendo, un dato perso no.

Come si misura un richiamo senza etichette
------------------------------------------

Il corpus non dice dove stanno i riferimenti catastali. Quindi si tende una
**rete larga** — apposta piu' permissiva del motore — e si guarda cosa prende
lei e non prende lui. La rete non e' la verita': prende anche cose che non
sono dati personali. E' un **elenco di candidati da guardare**, e serve
esattamente a questo: portare a galla le forme a cui non avevamo pensato.

La rete deve essere **piu' larga del motore, non uguale**, altrimenti i persi
sono zero per costruzione e il banco esce verde senza aver guardato niente.
`--controlla-rete` lo verifica: conta quante volte la rete scatta dove il
motore non ha nemmeno un'alternativa che potrebbe scattare.

Cosa esce, e cosa NON esce
--------------------------

Esce: quante forme la rete trova, quante ne toglie il motore, e **i campioni
di quelle perse raggruppati per forma**. Quelli si guardano a mano: alcuni
saranno difetti veri, altri saranno la rete che ha preso una pagina di
relazione. Il numero da solo non decide niente.

Non esce una percentuale da mettere nei documenti. Il denominatore e' una rete
scritta a mano, non una verita', e spacciarlo per richiamo sarebbe un numero
che sembra solido e non lo e'.

I corpora
---------

  * `--legale` il corpus legale italiano (`scripts/scarica_corpus_legale_it.py`):
    e' la fonte migliore, perche' e' pieno di atti e i valori hanno la forma
    giusta;
  * `--testi` una cartella di `.txt` — le Gazzette Ufficiali convertite;
  * `--pdf` una cartella di `.pdf`, letti con il motore PDF. Serve per la
    prosa vera: un atto scritto da un notaio non somiglia a niente di
    sintetico.

Uso::

    venv\\Scripts\\python scripts\\bench_richiamo_atti.py --legale C:\\...\\legale-it.jsonl
    venv\\Scripts\\python scripts\\bench_richiamo_atti.py --pdf "C:\\cartella" --massimo 300
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
if str(RADICE) not in sys.path:
    sys.path.insert(0, str(RADICE))

from mr_rao.privacy import ATTI, CORE, EN, IT, PrivacyOptions  # noqa: E402
from mr_rao.redazione_pdf import intervalli_da_togliere  # noqa: E402

PACCHETTI_ACCESI = (CORE, IT, EN, ATTI)

# ---------------------------------------------------------------------------
# Le reti larghe
# ---------------------------------------------------------------------------
#
# Ognuna e' **deliberatamente piu' permissiva** del riconoscitore corrispondente:
# ammette abbreviazioni che il motore non conosce, distanze maggiori, e forme
# che il motore rifiuta di proposito. E' il punto: cio' che la rete prende e il
# motore no e' l'elenco delle cose da guardare.

#: Catasto: basta la parola «foglio» in qualunque abbreviazione, seguita da un
#: numero, con **una parola di particella entro cento caratteri** — il motore
#: ne vuole molti meno e su una o due righe soltanto.
RETE_CATASTO = re.compile(
    r"(?i)\bf(?:oglio|og|g|\.)\.?\s*:?\s*(?P<num>\d{1,4})"
    r"(?=.{0,100}?\b(?:part(?:icella|\.)?|mapp(?:ale|\.)?|p\.?lla|sub)\b)",
    re.S,
)

#: Pratica: una qualunque parola d'etichetta seguita da cifre entro venti
#: caratteri. Il motore pretende almeno due cifre oppure l'anno, e conosce
#: meno abbreviazioni.
RETE_PRATICA = re.compile(
    r"(?i)\b(?:r\.?\s?g\.?(?:\s?n\.?\s?r\.?)?|ruolo\s+generale"
    r"|prot(?:\.|ocollo|)|rep(?:\.|ertorio|)|rac(?:c|\.|colta|)"
    r"|cron(?:\.|ologico|)|n\.?\s?cron)"
    r"[\s.:n°]{0,8}(?P<num>\d[\d/.\-]{0,15})"
)

#: Targa: quattro lettere **qualsiasi** attorno a tre cifre (il motore rifiuta
#: I, O, Q, U), maiuscole o minuscole, oppure la parola «targa» seguita da
#: qualunque cosa alfanumerica.
RETE_TARGA = re.compile(
    r"(?i)(?:\btarg[ah]\w*[\s.:n°]{0,6}(?P<ctx>[A-Z]{2}[\s.\-]?\d{3,5}[\s.\-]?[A-Z]{0,2})"
    r"|(?<![\w-])(?P<nudo>[A-Z]{2}[\s.\-]?\d{3}[\s.\-]?[A-Z]{2})(?![\w-]))"
)

RETI = {
    "catasto": RETE_CATASTO,
    "pratica": RETE_PRATICA,
    "targa": RETE_TARGA,
}


def _valore(m: re.Match) -> str:
    gruppi = m.groupdict()
    for nome in ("num", "ctx", "nudo"):
        if gruppi.get(nome):
            return gruppi[nome]
    return m.group(0)


def _coperto(inizio: int, fine: int, tolti: list[tuple[int, int, str]]) -> bool:
    """Il tratto trovato dalla rete si sovrappone a uno tolto dal motore?

    **Non «il numero non compare piu' nel testo redatto».** Era il primo
    controllo, ed era sbagliato: in una riga di corpus lunga trecento
    caratteri un «11» compare sempre da qualche altra parte — una data, un
    importo, un CAP — e il banco dichiarava perso un riferimento catastale che
    il motore aveva tolto. Trecentottanta «foglio» falsamente persi venivano
    tutti da li'.

    Gli intervalli veri li da' `intervalli_da_togliere`, che e' lo stesso pezzo
    usato per redigere i PDF ed e' provato: dice **dove** il motore ha
    sostituito, non solo quanto.
    """
    return any(inizio < b and a < fine for a, b, _ in tolti)


def _forma(valore: str, contesto: str) -> str:
    """Come si raggruppano i persi: per **etichetta**, non per numero.

    Due protocolli diversi con la stessa abbreviazione davanti sono lo stesso
    difetto, e vederli come duemila righe distinte nasconde che sono uno.
    """
    davanti = contesto.lower()
    for etichetta in ("racc", "rac.", "rac ", "repertorio", "rep", "protocollo",
                      "prot", "r.g", "rg", "cron", "ruolo generale",
                      "foglio", "fog", "fg", "f.", "targa", "targhe"):
        if etichetta in davanti:
            return etichetta
    return "(nessuna etichetta riconosciuta)"


def misura(testi, massimo_campioni: int = 6) -> dict:
    opzioni = PrivacyOptions(pacchetti=PACCHETTI_ACCESI)
    trovati = collections.Counter()
    presi = collections.Counter()
    persi_per_forma = collections.defaultdict(collections.Counter)
    campioni = collections.defaultdict(list)

    for testo in testi:
        if not testo or not testo.strip():
            continue
        interessante = any(rx.search(testo) for rx in RETI.values())
        if not interessante:
            continue
        tolti = intervalli_da_togliere(testo, opzioni)
        for categoria, rete in RETI.items():
            for m in rete.finditer(testo):
                valore = _valore(m)
                trovati[categoria] += 1
                if _coperto(m.start(), m.end(), tolti):
                    presi[categoria] += 1
                    continue
                contesto = testo[max(0, m.start() - 30):m.end() + 20]
                forma = _forma(valore, contesto)
                persi_per_forma[categoria][forma] += 1
                if len(campioni[(categoria, forma)]) < massimo_campioni:
                    campioni[(categoria, forma)].append(
                        " ".join(contesto.split()))
    return {
        "trovati": dict(trovati),
        "presi": dict(presi),
        "persi_per_forma": {k: dict(v) for k, v in persi_per_forma.items()},
        "campioni": {f"{k[0]}|{k[1]}": v for k, v in campioni.items()},
    }


def righe_legale(percorso: Path):
    with percorso.open(encoding="utf-8") as f:
        for riga in f:
            try:
                yield json.loads(riga).get("source_text", "")
            except json.JSONDecodeError:
                continue


def righe_testi(cartella: Path):
    for f in sorted(cartella.glob("*.txt")):
        yield f.read_text(encoding="utf-8", errors="replace")


def righe_pdf(cartella: Path, massimo: int):
    import pypdfium2 as pdfium

    letti = 0
    for f in sorted(cartella.rglob("*.pdf")):
        if letti >= massimo:
            return
        try:
            documento = pdfium.PdfDocument(str(f))
        except Exception:
            continue
        pezzi = []
        try:
            for pagina in documento:
                tp = pagina.get_textpage()
                pezzi.append(tp.get_text_range())
                tp.close()
        except Exception:
            pass
        finally:
            documento.close()
        letti += 1
        yield "\n".join(pezzi)


def stampa(esito: dict) -> None:
    print()
    print(f"{'categoria':10} {'rete':>8} {'presi':>8} {'persi':>8}  {'':>6}")
    for categoria in RETI:
        rete = esito["trovati"].get(categoria, 0)
        presi = esito["presi"].get(categoria, 0)
        persi = rete - presi
        quota = f"{100 * presi / rete:.1f}%" if rete else "—"
        print(f"{categoria:10} {rete:>8} {presi:>8} {persi:>8}  {quota:>6}")

    for categoria, forme in esito["persi_per_forma"].items():
        if not forme:
            continue
        print(f"\n--- {categoria}: cosa perde, per forma ---")
        for forma, n in sorted(forme.items(), key=lambda x: -x[1]):
            print(f"  {n:>7}  {forma}")
            for esempio in esito["campioni"].get(f"{categoria}|{forma}", [])[:3]:
                print(f"           {esempio[:110]!r}")
    print("\nLa rete non e' la verita': e' un elenco di candidati da guardare.")
    print("Le forme qui sopra vanno lette a mano — alcune sono difetti, altre")
    print("sono la rete che ha preso la pagina di una relazione.")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--legale", type=Path, default=None,
                   help="il .jsonl del corpus legale italiano")
    p.add_argument("--testi", type=Path, default=None,
                   help="cartella di .txt")
    p.add_argument("--pdf", type=Path, default=None,
                   help="cartella di .pdf, letti ricorsivamente")
    p.add_argument("--massimo", type=int, default=400,
                   help="quanti PDF leggere al massimo")
    p.add_argument("--json", type=Path, default=None)
    argomenti = p.parse_args()

    sorgenti = []
    if argomenti.legale and argomenti.legale.is_file():
        sorgenti.append(righe_legale(argomenti.legale))
    if argomenti.testi and argomenti.testi.is_dir():
        sorgenti.append(righe_testi(argomenti.testi))
    if argomenti.pdf and argomenti.pdf.is_dir():
        sorgenti.append(righe_pdf(argomenti.pdf, argomenti.massimo))
    if not sorgenti:
        print("Nessun corpus: --legale FILE, --testi CARTELLA oppure --pdf CARTELLA")
        return 2

    def tutti():
        for sorgente in sorgenti:
            yield from sorgente

    esito = misura(tutti())
    stampa(esito)
    if argomenti.json:
        argomenti.json.write_text(
            json.dumps(esito, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nscritto {argomenti.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
