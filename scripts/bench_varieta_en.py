"""La stessa manopola, girata sul pacchetto anglosassone e sul resto.

Sul pacchetto italiano cambiare il valore invece della frase ha trovato due
difetti (omocodia e telefono con la barra). Qui si fa lo stesso con i dieci
riconoscitori anglosassoni, i documenti d'identita' e le coordinate
bancarie non-IBAN — nessuno dei quali e' mai stato provato con valori
diversi.

Le cifre di controllo sono calcolate qui, dalle specifiche pubblicate:
NHS mod-11, SIN Luhn, ABN mod-89, TFN mod-11 pesato, ABA 3-7-1, MRZ
ICAO 9303. Chiedere al motore quale sia il valore giusto renderebbe
impossibile scoprire che il motore sbaglia.

Il codice postale britannico merita un'attenzione sua: ha **sei** formati
diversi (A9 9AA, A99 9AA, AA9 9AA, AA99 9AA, A9A 9AA, AA9A 9AA), ed e'
esattamente il tipo di cosa che un pattern copre a meta'.

L'esito, la prima volta che e' girato
-------------------------------------

**Nessun difetto.** Tutti e venti i tipi reggono la varieta' dei valori.

Le quattro cose che sembravano difetti erano **errori dei generatori qui
dentro**, e vale la pena averli scritti perche' sono il modo tipico in cui
un banco mente:

* **SIN** che iniziano per 0 o per 8 — il Canada non li ha mai assegnati, e
  il motore li rifiuta di proposito, con la ragione scritta nel codice;
* **MRZ di una riga sola** — una zona a lettura ottica ne ha due per
  definizione, e il pattern giustamente pretende il blocco intero;
* **MRZ di 43 caratteri** invece di 44: mancava la cifra di controllo del
  numero personale;
* **passaporti con serie inventate** (`MN`, `AA`): dal 2010 l'Italia usa
  `YA` e `YB`, piu' `TA` per i temporanei, ed e' esattamente cio' che il
  motore accetta. Verificato su fonti esterne, non dedotto dal codice.

Perche' qui zero e sul pacchetto italiano due, e' un'ipotesi che vale la
pena scrivere: questi riconoscitori sono nati insieme nella 1.8.0, **con i
vettori di prova presi dalle specifiche degli enti che emettono i
documenti**. Quelli italiani sono cresciuti una versione alla volta.

La colonna «nudo» resta bassa quasi ovunque, e non e' un difetto: nove
cifre o un codice postale senza niente attorno sono indistinguibili da un
numero di pratica. Il contesto e' il progetto, non la toppa.

Perche' questo banco stampa i valori, e perche' CodeQL lo segnala
-----------------------------------------------------------------

La colonna «esempi persi» stampa i valori che il motore non ha riconosciuto,
e `py/clear-text-logging-sensitive-data` la segnala: il flusso parte da
funzioni che si chiamano `carta()`, `telefono()`, `indirizzo()`, `email()`,
`nome()`, e quei valori finiscono in chiaro sullo standard output. La
classificazione e' **corretta**; e' la conclusione sul rischio che non si
applica.

Quei valori non esistono prima di quella stampa. Li fabbrica questo file,
riga per riga, con un generatore a seme fisso, calcolandosi le cifre di
controllo. Il banco non apre nessun documento: genera e prova. Non c'e'
nessun percorso per cui il dato di una persona vera arrivi li'.

**Non sono mascherati di proposito**, ed e' una scelta pagata. Quella
colonna e' lo strumento con cui si capisce *perche'* un valore si perde:
nella 1.16.0 «V.lo Garibaldi 44» ha fatto trovare le abbreviazioni postali
che mancavano, e «Via S. dei Mille 112» ha fatto scoprire che il difetto era
il generatore del banco e non il motore. Con l'esempio mascherato si
vedrebbe solo un conteggio, e si cercherebbe nel posto sbagliato.

La regola resta accesa sul resto del repository, e deve restarci: il giorno
in cui un banco stampasse il contenuto di documenti **veri**, quell'avviso
dovrebbe suonare. E' esattamente il motivo per cui
`scripts/bench_corpus_pubblico.py`, che invece lavora su documenti veri,
stampa **solo conteggi** e mai una riga di testo.
"""
from __future__ import annotations

import random
import string
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
if str(RADICE) not in sys.path:
    sys.path.insert(0, str(RADICE))

from mr_rao.privacy import PrivacyOptions, apply_privacy_filter  # noqa: E402

RNG = random.Random(20260809)
LET = string.ascii_uppercase


# --- generatori con conto, dalle specifiche ---------------------------------

def nhs() -> str | None:
    """10 cifre, mod-11 pesato 10..2. Resto 10 = numero non valido."""
    base = [RNG.randint(0, 9) for _ in range(9)]
    s = sum(d * (10 - i) for i, d in enumerate(base))
    c = 11 - (s % 11)
    if c == 11:
        c = 0
    if c == 10:
        return None
    n = "".join(map(str, base)) + str(c)
    return f"{n[:3]} {n[3:6]} {n[6:]}"


def sin() -> str:
    """SIN canadese: 9 cifre, Luhn — e la prima cifra non e' 0 ne' 8.

    La prima versione di questo generatore le ammetteva, e il banco
    segnalava un difetto che non c'era: **0 e 8 non sono mai stati
    assegnati**, e il motore li rifiuta di proposito anche quando il Luhn
    torna. Generare valori che l'ente non emette non misura il prodotto,
    misura la fantasia di chi scrive il banco.
    """
    base = str(RNG.choice([1, 2, 3, 4, 5, 6, 7, 9]))
    base += "".join(str(RNG.randint(0, 9)) for _ in range(7))
    tot, doppia = 0, True
    for ch in reversed(base):
        d = int(ch)
        if doppia:
            d *= 2
            if d > 9:
                d -= 9
        tot += d
        doppia = not doppia
    n = base + str((10 - tot % 10) % 10)
    return f"{n[:3]}-{n[3:6]}-{n[6:]}"


def abn() -> str:
    """ABN australiano: 11 cifre, meno 1 alla prima, mod-89."""
    pesi = [10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19]
    while True:
        d = [RNG.randint(1, 9)] + [RNG.randint(0, 9) for _ in range(10)]
        prova = d[:]
        prova[0] -= 1
        if sum(x * p for x, p in zip(prova, pesi)) % 89 == 0:
            n = "".join(map(str, d))
            return f"{n[:2]} {n[2:5]} {n[5:8]} {n[8:]}"


def tfn() -> str:
    """TFN australiano: 9 cifre, mod-11 pesato."""
    pesi = [1, 4, 3, 7, 5, 8, 6, 9, 10]
    while True:
        d = [RNG.randint(0, 9) for _ in range(9)]
        if sum(x * p for x, p in zip(d, pesi)) % 11 == 0:
            n = "".join(map(str, d))
            return f"{n[:3]} {n[3:6]} {n[6:]}"


def aba() -> str:
    """Routing ABA: 9 cifre, 3-7-1, con prefisso in uso."""
    prefisso = RNG.choice(list(range(1, 13)) + list(range(21, 33))
                          + list(range(61, 73)))
    while True:
        d = [int(c) for c in f"{prefisso:02d}"] + [RNG.randint(0, 9) for _ in range(7)]
        s = (3 * (d[0] + d[3] + d[6]) + 7 * (d[1] + d[4] + d[7])
             + (d[2] + d[5] + d[8]))
        if s % 10 == 0:
            return "".join(map(str, d))


def ssn() -> str:
    """SSN: nessun conto, ma esclusioni pubblicate dalla SSA."""
    while True:
        a = RNG.randint(1, 899)
        if a == 666:
            continue
        return f"{a:03d}-{RNG.randint(1, 99):02d}-{RNG.randint(1, 9999):04d}"


def itin() -> str:
    """ITIN: area 9xx, gruppo negli intervalli IRS."""
    gruppo = RNG.choice(list(range(50, 66)) + list(range(70, 89))
                        + list(range(90, 93)) + list(range(94, 100)))
    return f"9{RNG.randint(0, 99):02d}-{gruppo}-{RNG.randint(1, 9999):04d}"


_NINO_VIETATI = {"BG", "GB", "NK", "KN", "TN", "NT", "ZZ"}


def nino() -> str:
    prima = "ABCEGHJKLMNOPRSTWXYZ"
    seconda = "ABCEGHJKLMNPRSTWXYZ"
    while True:
        p = RNG.choice(prima) + RNG.choice(seconda)
        if p not in _NINO_VIETATI:
            break
    return f"{p} {RNG.randint(0,99):02d} {RNG.randint(0,99):02d} {RNG.randint(0,99):02d} {RNG.choice('ABCD')}"


def postcode(formato: str) -> str:
    """I sei formati veri del Royal Mail."""
    L = lambda: RNG.choice("ABCDEFGHIJKLMNOPRSTUWYZ")  # noqa: E731
    D = lambda: str(RNG.randint(0, 9))                  # noqa: E731
    fine = f"{D()}{RNG.choice('ABDEFGHJLNPQRSTUWXYZ')}{RNG.choice('ABDEFGHJLNPQRSTUWXYZ')}"
    fuori = {
        "A9 9AA": f"{L()}{D()} {fine}",
        "A99 9AA": f"{L()}{D()}{D()} {fine}",
        "AA9 9AA": f"{L()}{L()}{D()} {fine}",
        "AA99 9AA": f"{L()}{L()}{D()}{D()} {fine}",
        "A9A 9AA": f"{L()}{D()}{L()} {fine}",
        "AA9A 9AA": f"{L()}{L()}{D()}{L()} {fine}",
    }
    return fuori[formato]


def _mrz_check(s: str) -> str:
    pesi = [7, 3, 1]
    tot = 0
    for i, c in enumerate(s):
        if c.isdigit():
            v = int(c)
        elif c == "<":
            v = 0
        else:
            v = ord(c.upper()) - 55
        tot += v * pesi[i % 3]
    return str(tot % 10)


_COGNOMI_MRZ = ["ROSSI", "BIANCHI", "ESPOSITO", "FERRARI", "GRECO"]
_NOMI_MRZ = ["MARIO", "GIULIA", "LUCA", "ANNA", "PAOLO"]


def mrz() -> str:
    """Il blocco MRZ **intero** di un passaporto: due righe da 44, ICAO 9303.

    Due errori sono passati di qui, e sono istruttivi.

    Il primo: una riga sola. Una zona a lettura ottica ne ha **due** per
    definizione, e il motore pretende il blocco intero — giustamente, perche'
    quarantaquattro caratteri maiuscoli isolati sono una stringa qualsiasi.

    Il secondo: 43 caratteri invece di 44, perche' mancava la cifra di
    controllo del **numero personale**. Il banco dava 0% e sembrava un
    difetto del prodotto.
    """
    cognome = RNG.choice(_COGNOMI_MRZ)
    nome = RNG.choice(_NOMI_MRZ)
    riga1 = f"P<ITA{cognome}<<{nome}".ljust(44, "<")

    doc = "".join(RNG.choice(LET + string.digits) for _ in range(9))
    nascita = f"{RNG.randint(50,99):02d}{RNG.randint(1,12):02d}{RNG.randint(1,28):02d}"
    scadenza = f"{RNG.randint(26,35):02d}{RNG.randint(1,12):02d}{RNG.randint(1,28):02d}"
    personale = "<" * 14
    composita = (doc + _mrz_check(doc) + nascita + _mrz_check(nascita)
                 + scadenza + _mrz_check(scadenza)
                 + personale + _mrz_check(personale))
    riga2 = (f"{doc}{_mrz_check(doc)}ITA{nascita}{_mrz_check(nascita)}"
             f"{RNG.choice('MF')}{scadenza}{_mrz_check(scadenza)}"
             f"{personale}{_mrz_check(personale)}{_mrz_check(composita)}")
    return f"{riga1}\n{riga2}"


def bban() -> str:
    """Coordinate italiane senza IBAN: CIN + ABI + CAB + conto."""
    return (f"{RNG.choice(LET)} {RNG.randint(1,99999):05d} "
            f"{RNG.randint(1,99999):05d} {RNG.randint(0,10**12-1):012d}")


def cie() -> str:
    """Carta d'identita' elettronica: 2 lettere, 5 cifre, 2 lettere."""
    return (f"{RNG.choice(LET)}{RNG.choice(LET)}{RNG.randint(0,99999):05d}"
            f"{RNG.choice(LET)}{RNG.choice(LET)}")


def patente() -> str:
    """Patente italiana: sigla provincia + cifre + lettera."""
    return f"{RNG.choice(LET)}{RNG.choice(LET)}{RNG.randint(1000000,9999999)}{RNG.choice(LET)}"


def passaporto() -> str:
    """Passaporto italiano: serie **YA**, **YB** (dal 2010) o **TA**.

    Le due lettere non sono libere. Il primo generatore le sorteggiava
    dall'alfabeto e produceva cose come `MN4850617`, che l'Italia non
    emette: il banco segnalava un difetto inesistente. Verificato su fonti
    esterne, non dedotto dal pattern del motore.
    """
    return f"{RNG.choice(['YA', 'YB', 'TA'])}{RNG.randint(1000000,9999999)}"


def token() -> str:
    return "ghp_" + "".join(RNG.choice(string.ascii_letters + string.digits)
                            for _ in range(36))


QUANTI = 200


def campioni() -> dict[str, tuple[list[str], str]]:
    """nome -> (valori, cornice con l'etichetta giusta)."""
    def n(f, q=QUANTI):
        fuori = []
        while len(fuori) < q:
            v = f()
            if v:
                fuori.append(v)
        return fuori

    return {
        "NHS number": (n(nhs), "NHS number {v}"),
        "National Insurance": (n(nino), "National Insurance number {v}"),
        "SSN": (n(ssn), "SSN {v}"),
        "ITIN": (n(itin), "ITIN {v}"),
        "ABA routing": (n(aba), "routing number {v}"),
        "SIN canadese": (n(sin), "SIN {v}"),
        "ABN australiano": (n(abn), "ABN {v}"),
        "TFN australiano": (n(tfn), "TFN {v}"),
        "postcode A9 9AA": (n(lambda: postcode("A9 9AA")), "postcode {v}"),
        "postcode A99 9AA": (n(lambda: postcode("A99 9AA")), "postcode {v}"),
        "postcode AA9 9AA": (n(lambda: postcode("AA9 9AA")), "postcode {v}"),
        "postcode AA99 9AA": (n(lambda: postcode("AA99 9AA")), "postcode {v}"),
        "postcode A9A 9AA": (n(lambda: postcode("A9A 9AA")), "postcode {v}"),
        "postcode AA9A 9AA": (n(lambda: postcode("AA9A 9AA")), "postcode {v}"),
        "MRZ passaporto": (n(mrz, 60), "{v}"),
        "BBAN": (n(bban), "coordinate bancarie {v}"),
        "carta identita (CIE)": (n(cie), "carta d'identita' n. {v}"),
        "patente": (n(patente), "patente di guida n. {v}"),
        "passaporto": (n(passaporto), "passaporto n. {v}"),
        "token / chiave": (n(token), "api key {v}"),
    }


def prova(valori: list[str], modello: str) -> tuple[int, int, list[str]]:
    o = PrivacyOptions()
    redatti = sospetti = 0
    persi = []
    for v in valori:
        fuori, rep = apply_privacy_filter(modello.format(v=v), o)
        if v not in fuori:
            redatti += 1
        elif rep.suspects:
            sospetti += 1
        elif len(persi) < 2:
            persi.append(v)
    return redatti, sospetti, persi


def main() -> int:
    print("=" * 92)
    print(f"VARIETA' — pacchetto anglosassone, documenti, coordinate ({QUANTI} valori per tipo)")
    print("=" * 92)
    print(f"\n{'tipo':<24} {'nudo':>14} {'con etichetta':>15}   esempi persi")
    print("-" * 92)
    for tipo, (valori, cornice) in campioni().items():
        r1, s1, p1 = prova(valori, "Nel documento compare {v} come da atti.")
        r2, s2, p2 = prova(valori, cornice)
        n = len(valori)
        a = f"{100*r1/n:5.1f}%" + (f" +{100*s1/n:.0f}s" if s1 else "")
        b = f"{100*r2/n:5.1f}%" + (f" +{100*s2/n:.0f}s" if s2 else "")
        segnale = "  <<<" if r2 < n * 0.99 else ""
        print(f"{tipo:<24} {a:>14} {b:>15}   {', '.join(p2[:1])[:26]}{segnale}")
    print()
    print("  «<<<» = non riconosciuto nemmeno con l'etichetta davanti.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
