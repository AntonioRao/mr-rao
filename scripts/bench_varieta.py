"""Non una cornice diversa: un VALORE diverso.

Il banco delle forme misurava se il motore riconosce **lo stesso dato**
scritto in posti diversi. Diceva 100%, e non era una buona notizia: usava
un solo valore per tipo. Dimostrava che le cornici funzionano, non che i
riconoscitori reggano la varieta' dei valori veri.

Qui si gira l'altra manopola: **centinaia di valori distinti per tipo**,
tutti validi, con le cifre di controllo calcolate qui e non chieste al
motore. Una cornice sola, la piu' neutra possibile.

Cosa ha trovato, la prima volta che e' girato
---------------------------------------------

Due difetti che nessun test vedeva, entrambi casi italiani ordinari: il
**codice fiscale con omocodia** (zero riconosciuti su 300, il 40% perso in
silenzio) e il **telefono con la barra** delle carte intestate, `Tel.
011/7323929` (zero su 300, mentre gli stessi numeri con lo spazio o il
trattino venivano presi). Corretti nella 1.15.0.

Cosa questo banco puo' trovare e quello delle forme no
------------------------------------------------------

* carte **American Express**, che hanno 15 cifre e non 16;
* codici fiscali con **omocodia** -- quando due persone otterrebbero lo
  stesso codice, l'Agenzia sostituisce alcune cifre con lettere, e il
  risultato non e' piu' «sei lettere e dieci cifre»;
* numeri fissi con prefisso a **2, 3 o 4 cifre** (02 Milano, 011 Torino,
  0121 Pinerolo): la lunghezza del prefisso cambia la forma del numero;
* IBAN con CIN e ABI qualsiasi, non sempre lo stesso;
* cognomi presi da tutto l'elenco, non uno solo.

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
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
if str(RADICE) not in sys.path:
    sys.path.insert(0, str(RADICE))

from mr_rao.privacy import (  # noqa: E402
    FIRST_NAMES,
    SURNAMES,
    PrivacyOptions,
    apply_privacy_filter,
)

RNG = random.Random(20260809)

# ---------------------------------------------------------------------------
# Generatori — implementazioni indipendenti dal motore
# ---------------------------------------------------------------------------

_CF_DISPARI = dict(zip(
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    [1, 0, 5, 7, 9, 13, 15, 17, 19, 21, 1, 0, 5, 7, 9, 13, 15, 17, 19, 21,
     2, 4, 18, 20, 11, 3, 6, 8, 12, 14, 16, 10, 22, 25, 24, 23]))
_CF_PARI = dict(zip("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                    list(range(10)) + list(range(26))))
# La tabella dell'omocodia: quando il codice collide, l'Agenzia sostituisce
# le cifre (da destra) con queste lettere.
_OMOCODIA = dict(zip("0123456789", "LMNPQRSTUV"))


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


_CONSONANTI = "BCDFGHJKLMNPQRSTVWXYZ"
_MESI = "ABCDEHLMPRST"


def genera_cf(omocodia: int = 0) -> str:
    """Un codice fiscale plausibile, con la cifra di controllo giusta."""
    cognome = "".join(RNG.choice(_CONSONANTI) for _ in range(3))
    nome = "".join(RNG.choice(_CONSONANTI) for _ in range(3))
    anno = f"{RNG.randint(0, 99):02d}"
    mese = RNG.choice(_MESI)
    giorno = f"{RNG.randint(1, 28):02d}"
    comune = RNG.choice("ABCDEFGHL") + f"{RNG.randint(0, 999):03d}"
    base = cognome + nome + anno + mese + giorno + comune
    if omocodia:
        # Si sostituiscono le cifre partendo da destra, come fa l'Agenzia.
        posizioni = [i for i, c in enumerate(base) if c.isdigit()]
        for i in reversed(posizioni[-omocodia:]):
            base = base[:i] + _OMOCODIA[base[i]] + base[i + 1:]
    return cf_valido(base)


def genera_iban() -> str:
    cin = RNG.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    abi = f"{RNG.randint(1, 99999):05d}"
    cab = f"{RNG.randint(1, 99999):05d}"
    conto = f"{RNG.randint(0, 10**12 - 1):012d}"
    return iban_valido(cin + abi + cab + conto)


def genera_carta(circuito: str) -> str:
    prefissi = {"visa": ["4"], "mastercard": ["51", "52", "53", "54", "55"],
                "amex": ["34", "37"], "discover": ["6011"]}
    lunghezze = {"visa": 16, "mastercard": 16, "amex": 15, "discover": 16}
    p = RNG.choice(prefissi[circuito])
    n = lunghezze[circuito]
    corpo = p + "".join(str(RNG.randint(0, 9)) for _ in range(n - len(p) - 1))
    return corpo + luhn(corpo)


# Prefissi telefonici italiani veri, di lunghezza diversa: e' la lunghezza
# che cambia la forma del numero, non la citta'.
PREFISSI_FISSI = ["02", "06", "011", "055", "081", "0121", "0322", "0871"]


def genera_telefono(stile: str) -> str:
    if stile == "cellulare":
        return f"3{RNG.randint(20, 99)} {RNG.randint(100, 999)} {RNG.randint(1000, 9999)}"
    if stile == "cellulare +39":
        return f"+39 3{RNG.randint(20, 99)}{RNG.randint(1000000, 9999999)}"
    pref = RNG.choice(PREFISSI_FISSI)
    resto = "".join(str(RNG.randint(0, 9)) for _ in range(10 - len(pref)))
    if stile == "fisso":
        return f"{pref} {resto}"
    if stile == "fisso +39":
        return f"+39 {pref} {resto}"
    return f"{pref}/{resto}"  # stile con la barra, comune nelle carte intestate


VIE = ["Via", "Viale", "Piazza", "Corso", "Largo", "Vicolo", "Strada",
       "Contrada", "Piazzale", "Borgo"]
LUOGHI = ["Garibaldi", "Verdi", "Dante", "Roma", "Marconi", "Cavour",
          "Mazzini", "Vittorio Veneto", "San Martino", "Zamboni"]


def genera_indirizzo() -> str:
    return (f"{RNG.choice(VIE)} {RNG.choice(LUOGHI)} {RNG.randint(1, 200)}, "
            f"{RNG.randint(10000, 98999)} {RNG.choice(['Milano', 'Roma', 'Torino', 'Bari'])}")


DOMINI = ["studio.it", "esempio.com", "comune.bologna.it", "avvocati.eu",
          "posta-certificata.it", "a.co", "consulenti.legal"]


def genera_email() -> str:
    locale = RNG.choice(["m.rossi", "giulia.bianchi", "info", "a_b", "x-y",
                         "mario.rossi+pec", "n.dangelo"])
    return f"{locale}@{RNG.choice(DOMINI)}"


# ---------------------------------------------------------------------------

QUANTI = 300


def campioni() -> dict[str, list[str]]:
    return {
        "IBAN": [genera_iban() for _ in range(QUANTI)],
        "codice fiscale": [genera_cf() for _ in range(QUANTI)],
        "codice fiscale (omocodia)": [genera_cf(omocodia=RNG.randint(1, 3))
                                      for _ in range(QUANTI)],
        "partita IVA": [piva_valida(f"{RNG.randint(0, 10**10 - 1):010d}")
                        for _ in range(QUANTI)],
        "carta Visa": [genera_carta("visa") for _ in range(QUANTI)],
        "carta Mastercard": [genera_carta("mastercard") for _ in range(QUANTI)],
        "carta Amex (15 cifre)": [genera_carta("amex") for _ in range(QUANTI)],
        "carta Discover": [genera_carta("discover") for _ in range(QUANTI)],
        "telefono cellulare": [genera_telefono("cellulare") for _ in range(QUANTI)],
        "telefono cell. +39": [genera_telefono("cellulare +39") for _ in range(QUANTI)],
        "telefono fisso": [genera_telefono("fisso") for _ in range(QUANTI)],
        "telefono fisso +39": [genera_telefono("fisso +39") for _ in range(QUANTI)],
        "telefono con barra": [genera_telefono("barra") for _ in range(QUANTI)],
        "indirizzo": [genera_indirizzo() for _ in range(QUANTI)],
        "email": [genera_email() for _ in range(QUANTI)],
        "nome+cognome (in elenco)": [
            f"{RNG.choice(sorted(FIRST_NAMES)).title()} {RNG.choice(sorted(SURNAMES)).title()}"
            for _ in range(QUANTI)],
    }


# La cornice piu' neutra possibile: nessuna etichetta che aiuti.
CORNICE = "Nel documento compare {v} come indicato dalle parti."
# E una con l'etichetta, per separare «il riconoscitore non sa leggere quel
# valore» da «il riconoscitore aveva bisogno del contesto».
CORNICE_AIUTATA = {
    "IBAN": "IBAN {v}",
    "codice fiscale": "codice fiscale {v}",
    "codice fiscale (omocodia)": "codice fiscale {v}",
    "partita IVA": "partita IVA {v}",
    "carta Visa": "carta di credito n. {v}",
    "carta Mastercard": "carta di credito n. {v}",
    "carta Amex (15 cifre)": "carta di credito n. {v}",
    "carta Discover": "carta di credito n. {v}",
    "telefono cellulare": "cell. {v}",
    "telefono cell. +39": "cell. {v}",
    "telefono fisso": "tel. {v}",
    "telefono fisso +39": "tel. {v}",
    "telefono con barra": "tel. {v}",
    "indirizzo": "residente in {v}",
    "email": "e-mail: {v}",
    "nome+cognome (in elenco)": "il dott. {v} ha firmato",
}


def prova(valori: list[str], modello: str) -> tuple[int, int, list[str]]:
    """Quanti vengono redatti, quanti segnalati, e qualche esempio perso."""
    opzioni = PrivacyOptions()
    redatti = sospetti = 0
    persi = []
    for v in valori:
        fuori, rep = apply_privacy_filter(modello.format(v=v), opzioni)
        if v not in fuori:
            redatti += 1
        elif rep.suspects:
            sospetti += 1
        elif len(persi) < 3:
            persi.append(v)
    return redatti, sospetti, persi


def main() -> int:
    dati = campioni()
    print("=" * 92)
    print(f"VARIETA' DEI VALORI — {QUANTI} valori distinti per tipo, tutti validi")
    print("=" * 92)
    print(f"\n{'tipo':<28} {'nudo':>16} {'con etichetta':>16}   esempi persi")
    print("-" * 92)
    for tipo, valori in dati.items():
        r1, s1, p1 = prova(valori, CORNICE)
        r2, s2, p2 = prova(valori, CORNICE_AIUTATA[tipo])
        n = len(valori)
        nudo = f"{100*r1/n:5.1f}%"
        if s1:
            nudo += f" +{100*s1/n:.0f}%s"
        aiut = f"{100*r2/n:5.1f}%"
        if s2:
            aiut += f" +{100*s2/n:.0f}%s"
        esempi = ", ".join(p2[:2]) if p2 else ""
        print(f"{tipo:<28} {nudo:>16} {aiut:>16}   {esempi[:32]}")
    print()
    print("  «+N%s» = segnalati come sospetti invece che sostituiti.")
    print("  Colonna «nudo»: nessuna etichetta davanti. Colonna «con etichetta»:")
    print("  la parola di contesto c'e'. La differenza dice se il riconoscitore")
    print("  sa leggere il valore o se gli serviva il contorno.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
