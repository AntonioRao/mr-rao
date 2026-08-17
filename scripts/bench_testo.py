# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Quanto e' efficace il motore quando l'OCR non c'entra niente.

Perche' questo banco esiste
---------------------------

Quasi tutte le misure pubblicate riguardano le scansioni, e li' il limite
principale non e' il motore ma l'OCR. Sul testo — email, contratti,
delibere, documenti Office — il motore e' interamente responsabile di cio'
che trova e di cio' che perde, e non c'e' nessuno da incolpare. Fino al
2026-08 quel percorso non era mai stato misurato.

Tre assi
--------

**A. Falsi positivi.** Documenti amministrativi veri e in bianco: non
contengono un solo dato personale, quindi ogni sostituzione e' un errore.
Serve un corpus esterno (`--corpus`).

**B. Richiamo, forme regolari.** Dati dal valore noto dentro prosa vera.
Serve lo stesso corpus.

**C. Richiamo, forme DIFFICILI.** Come i dati arrivano davvero da un `.docx`
o da un PDF: spezzati da un a capo, scritti a gruppi, offuscati, in
minuscolo. Piu' i nomi che nessun elenco contiene. **Questo asse gira
sempre**, perche' non ha bisogno del corpus: il substrato e' un paragrafo
scritto qui.

Sul substrato scritto in casa
-----------------------------

Il paragrafo dell'asse C **l'abbiamo scritto noi**, e vale la regola gia'
pagata: un testo scritto in casa contiene solo le trappole a cui ha pensato
chi lo scrive. Per l'asse C non e' un problema — cio' che si misura e' la
forma del **frammento**, non del contorno — ma i numeri pubblicati vengono
dagli assi A e B, su prosa che non e' nostra.

Il corpus
---------

`--corpus` vuole una cartella di file `.txt`, con questa convenzione sul
nome: `itmod--*.txt` moduli amministrativi italiani in bianco,
`irs--*.txt` moduli fiscali statunitensi in bianco, `gu--*.txt` prosa
giuridica (Gazzetta Ufficiale). I documenti **non stanno nel repository**:
sono scaricabili dagli enti che li pubblicano, pesano decine di megabyte e
non sono nostri da ridistribuire.

Tre esiti, non due
------------------

**redatto** — sostituito. **sospetto** — non sostituito ma segnalato.
**perso in silenzio** — ne' l'uno ne' l'altro: l'unico numero veramente
brutto, perche' il documento sembra pulito e non lo e'.
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
if str(RADICE) not in sys.path:
    sys.path.insert(0, str(RADICE))

from mr_rao.privacy import (  # noqa: E402
    PrivacyOptions,
    apply_privacy_filter,
    no_redaction,
)

# ---------------------------------------------------------------------------
# Valori validi, con le cifre di controllo calcolate qui e non chieste al
# motore: un banco che chiede al prodotto quale sia la risposta giusta non
# puo' scoprire che il prodotto sbaglia.
# ---------------------------------------------------------------------------

_CF_DISPARI = dict(zip(
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    [1, 0, 5, 7, 9, 13, 15, 17, 19, 21, 1, 0, 5, 7, 9, 13, 15, 17, 19, 21,
     2, 4, 18, 20, 11, 3, 6, 8, 12, 14, 16, 10, 22, 25, 24, 23]))
_CF_PARI = dict(zip("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                    list(range(10)) + list(range(26))))


def cf_valido(base15: str) -> str:
    s = sum(_CF_DISPARI[c] if i % 2 == 0 else _CF_PARI[c]
            for i, c in enumerate(base15.upper()))
    return base15.upper() + chr(ord("A") + s % 26)


def luhn(parziale: str) -> str:
    tot, doppia = 0, True
    for c in reversed(parziale):
        d = int(c)
        if doppia:
            d *= 2
            if d > 9:
                d -= 9
        tot += d
        doppia = not doppia
    return str((10 - tot % 10) % 10)


def piva_valida(base10: str) -> str:
    tot = 0
    for i, c in enumerate(base10):
        d = int(c)
        if i % 2:
            d *= 2
            if d > 9:
                d -= 9
        tot += d
    return base10 + str((10 - tot % 10) % 10)


def iban_valido(bban: str) -> str:
    def num(s: str) -> str:
        return "".join(str(ord(c) - 55) if c.isalpha() else c for c in s)

    return f"IT{98 - int(num(bban + 'IT00')) % 97:02d}{bban}"


VALORI = {
    "codice_fiscale": cf_valido("MRTGPP71C15F205"),
    "partita_iva": "IT" + piva_valida("1234567890"),
    "iban": iban_valido("X0542811101000000123456"),
    "carta": "453914880343646" + luhn("453914880343646"),
    "email": "g.moretti@studiomoretti.it",
    "telefono": "+39 335 481 2290",
    "indirizzo": "Via Zamboni 33, 40126 Bologna",
    "nome": "Giuseppe Moretti",
}

CORNICI = {
    "codice_fiscale": [("etichetta", "codice fiscale {v}"),
                       ("in frase", "il sottoscritto, {v}, dichiara"),
                       ("nudo", "{v}")],
    "partita_iva": [("etichetta", "partita IVA {v}"),
                    ("in frase", "iscritta con {v} presso il registro"),
                    ("nudo", "{v}")],
    "iban": [("etichetta", "IBAN {v}"),
             ("in frase", "accreditare sul conto {v} entro trenta giorni"),
             ("nudo", "{v}")],
    "carta": [("etichetta", "carta di credito n. {v}"),
              ("in frase", "pagamento effettuato con {v} in data odierna"),
              ("nudo", "{v}")],
    "email": [("etichetta", "e-mail: {v}"),
              ("in frase", "ogni comunicazione va inviata a {v} entro i termini"),
              ("nudo", "{v}")],
    "telefono": [("etichetta", "tel. {v}"),
                 ("in frase", "reperibile al {v} negli orari di ufficio"),
                 ("nudo", "{v}")],
    "indirizzo": [("etichetta", "residente in {v}"),
                  ("in frase", "con sede in {v} come da visura"),
                  ("nudo", "{v}")],
    # I cinque livelli di prova del motore per i nomi, piu' il caso senza
    # nessuna prova.
    "nome": [("titolo davanti", "il dott. {v} ha sottoscritto"),
             ("firma", "Cordiali saluti,\n{v}"),
             ("accanto a email", "{v} <g.moretti@studiomoretti.it>"),
             ("nome+cognome", "l'incarico e' affidato a {v} per il triennio"),
             ("nudo", "come indicato da {v} nella relazione")],
}

# (etichetta, valore da ritrovare, frammento come compare nel documento).
#
# Il valore da ritrovare dev'essere una stringa che nel frammento c'e'
# DAVVERO: cercando la forma senza spazi dentro un frammento che li ha, il
# caso risulta «redatto» anche a motore spento — cioe' un successo che non
# puo' fallire. E' successo, e la controprova l'ha preso.
DIFFICILI = [
    ("iban a gruppi di quattro", "X054 2811 1010",
     "IBAN IT60 X054 2811 1010 0000 0123 456"),
    ("iban spezzato da un a capo", "00000123456",
     "IBAN IT60X05428111010\n00000123456"),
    ("carta a gruppi di quattro", "0343 6467", "carta 4539 1488 0343 6467"),
    ("carta separata da trattini", "0343-6467", "carta 4539-1488-0343-6467"),
    ("codice fiscale in minuscolo", "mrtgpp71c15f205d",
     "codice fiscale mrtgpp71c15f205d"),
    ("telefono con punti", "335.481.2290", "tel. 335.481.2290"),
    ("telefono senza parola davanti", "335 481 2290",
     "chiamare il 335 481 2290 per conferma"),
    ("email offuscata", "g.moretti", "scrivere a g.moretti[at]studiomoretti.it"),
    ("email spezzata da un a capo", "studiomoretti.it",
     "scrivere a g.moretti@\nstudiomoretti.it"),
    ("nome straniero, nudo", "Kwabena Osei",
     "come indicato da Kwabena Osei nella relazione"),
    ("nome straniero, titolo davanti", "Kwabena Osei",
     "il dott. Kwabena Osei ha sottoscritto"),
    ("nome straniero, firma", "Kwabena Osei", "Cordiali saluti,\nKwabena Osei"),
    ("solo cognome dopo i due punti", "MORETTI", "Il Direttore Generale: MORETTI"),
    ("cognome che e' parola comune", "Chiesa",
     "come indicato da Marco Chiesa nella relazione"),
    ("indirizzo senza civico", "Via Zamboni", "con sede in Via Zamboni, Bologna"),
]

# Substrato per l'asse C quando non c'e' un corpus. Scritto da noi, e la
# limitazione e' dichiarata in cima al file.
SUBSTRATO = (
    "Il presente decreto entra in vigore il giorno successivo a quello della "
    "sua pubblicazione ed e' trasmesso agli organi di controllo per le "
    "verifiche di competenza. Restano ferme le disposizioni gia' adottate in "
    "materia di trasparenza amministrativa e di accesso agli atti, nonche' "
    "gli obblighi di conservazione documentale previsti dalla normativa "
    "vigente per il triennio di riferimento."
)


def corpo(testo: str) -> str:
    """Il documento senza l'intestazione YAML, se e' uscita da Mr. Rao.

    Un corpus fatto di conversioni gia' fatte porta il frontmatter dentro,
    e li' c'e' `generator: "Mr. Rao ..."` — dove `Mr.` e' un titolo e `Rao`
    la parola maiuscola dopo. Misurando i file interi si contava **una**
    sostituzione sbagliata per documento: il motore stava redigendo la
    propria firma, e aveva ragione.
    """
    if testo.startswith("---"):
        fine = testo.find("\n---", 3)
        if fine != -1:
            return testo[fine + 4:]
    return testo


def _inserisci(paragrafo: str, frammento: str) -> str:
    """A meta' paragrafo: ne' in cima ne' in fondo, dove il motore potrebbe
    avere regole di bordo."""
    meta = len(paragrafo) // 2
    taglio = paragrafo.find(" ", meta) + 1 or meta
    return paragrafo[:taglio] + frammento + ". " + paragrafo[taglio:]


def esito(testo: str, valore: str) -> str:
    """redatto / sospetto / perso, guardando il TESTO e non il conteggio.

    Contare le redazioni non basta: il paragrafo potrebbe far scattare
    qualcos'altro. L'unica domanda che conta e' se quel valore e' ancora
    leggibile in chiaro.
    """
    fuori, rep = apply_privacy_filter(testo, PrivacyOptions())
    if valore not in fuori:
        return "redatto"
    return "sospetto" if rep.suspects else "perso"


def conta(righe, paragrafi: list[str]) -> dict[str, dict[str, int]]:
    esiti = {}
    for etichetta, valore, frammento in righe:
        c = {"redatto": 0, "sospetto": 0, "perso": 0}
        for p in paragrafi:
            c[esito(_inserisci(p, frammento), valore)] += 1
        esiti[etichetta] = c
    return esiti


def _tabella(esiti: dict[str, dict[str, int]], n: int) -> dict[str, int]:
    print(f"\n  {'caso':<36} {'redatto':>9} {'sospetto':>9} {'perso':>7}")
    print("  " + "-" * 64)
    totali = {"redatto": 0, "sospetto": 0, "perso": 0}
    for etichetta, c in esiti.items():
        for k in c:
            totali[k] += c[k]
        nota = "  <-- IN SILENZIO" if c["perso"] else ""
        print(f"  {etichetta:<36} {c['redatto']:>8}/{n} "
              f"{c['sospetto']:>9} {c['perso']:>7}{nota}")
    return totali


def paragrafi_reali(cartella: Path, quanti: int, seme: int) -> list[str]:
    """Paragrafi veri, scartando quelli in cui il motore trova gia' qualcosa.

    Senza lo scarto non si saprebbe attribuire il risultato al dato
    inserito invece che a qualcosa che c'era gia'.
    """
    testi = [corpo(f.read_text(encoding="utf-8", errors="replace"))
             for f in sorted(cartella.glob("gu--*.txt"))]
    if not testi:
        return []
    pezzi = [p.strip().replace("\n", " ")
             for p in "\n".join(testi).split("\n\n")]
    pezzi = [p for p in pezzi if 400 <= len(p) <= 1200]
    random.Random(seme).shuffle(pezzi)

    puliti = []
    opzioni = PrivacyOptions()
    for p in pezzi:
        _, rep = apply_privacy_filter(p, opzioni)
        if rep.total == 0 and not rep.suspects:
            puliti.append(p)
        if len(puliti) >= quanti:
            break
    return puliti


def asse_a(cartella: Path) -> None:
    print("=" * 74)
    print("A — FALSI POSITIVI su documenti amministrativi veri, in bianco")
    print("=" * 74)
    opzioni = PrivacyOptions()
    for etichetta, motivo in (("moduli italiani", "itmod--*.txt"),
                              ("moduli IRS", "irs--*.txt")):
        file = sorted(cartella.glob(motivo))
        if not file:
            print(f"\n  {etichetta}: nessun file {motivo} nel corpus")
            continue
        caratteri = tot = sospetti = perfetti = 0
        for f in file:
            t = corpo(f.read_text(encoding="utf-8", errors="replace"))
            caratteri += len(t)
            _, rep = apply_privacy_filter(t, opzioni)
            tot += rep.total
            sospetti += len(rep.suspects)
            perfetti += 1 if rep.total == 0 else 0
        print(f"\n  {etichetta}: {len(file)} documenti, {caratteri:,} caratteri")
        print(f"    sostituzioni sbagliate: {tot}")
        print(f"    documenti perfetti: {perfetti} su {len(file)}")
        print(f"    sospetti (NON modificano il documento): {sospetti}")


def controprova(paragrafi: list[str]) -> bool:
    """Con i riconoscitori spenti nessun caso deve risultare «redatto»."""
    spento = no_redaction()
    finti = [e for e, valore, fr in DIFFICILI
             if valore not in apply_privacy_filter(
                 _inserisci(paragrafi[0], fr), spento)[0]]
    print()
    print("=" * 74)
    if finti:
        print("CONTROPROVA — ATTENZIONE: questi casi risultano «redatti» anche")
        print("col filtro spento, quindi non stanno misurando niente:")
        for e in finti:
            print(f"    {e}")
    else:
        print("CONTROPROVA — filtro spento: nessun caso risulta redatto.")
        print("  Il banco misura davvero il filtro.")
    return not finti


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--corpus", type=Path, default=None,
                   help="cartella con i .txt (itmod--*, irs--*, gu--*)")
    p.add_argument("--paragrafi", type=int, default=20)
    p.add_argument("--seme", type=int, default=20260809)
    args = p.parse_args(argv)

    paragrafi = []
    if args.corpus and args.corpus.is_dir():
        asse_a(args.corpus)
        paragrafi = paragrafi_reali(args.corpus, args.paragrafi, args.seme)
        if paragrafi:
            print()
            print("=" * 74)
            print(f"B — RICHIAMO, forme regolari ({len(paragrafi)} paragrafi veri)")
            print("=" * 74)
            righe = [(f"{t} / {nome}", VALORI[t], mod.format(v=VALORI[t]))
                     for t, cornici in CORNICI.items() for nome, mod in cornici]
            b = _tabella(conta(righe, paragrafi), len(paragrafi))
            n = sum(b.values())
            print(f"\n  redatto {100*b['redatto']/n:.1f}%  "
                  f"segnalato {100*b['sospetto']/n:.1f}%  "
                  f"perso {100*b['perso']/n:.1f}%")
    else:
        print("Nessun corpus: gli assi A e B restano fuori.")
        print("  (--corpus CARTELLA per misurarli; vedi il docstring)")

    if not paragrafi:
        paragrafi = [SUBSTRATO]

    print()
    print("=" * 74)
    print("C — RICHIAMO, forme DIFFICILI: come i dati arrivano da un file vero")
    print("=" * 74)
    c = _tabella(conta(DIFFICILI, paragrafi), len(paragrafi))
    n = sum(c.values())
    print(f"\n  redatto {100*c['redatto']/n:.1f}%  "
          f"segnalato {100*c['sospetto']/n:.1f}%  "
          f"PERSO IN SILENZIO {100*c['perso']/n:.1f}%")

    return 0 if controprova(paragrafi) else 1


if __name__ == "__main__":
    raise SystemExit(main())
