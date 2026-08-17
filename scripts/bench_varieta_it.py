# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""La terza manopola sul resto del pacchetto italiano.

Cambiare il **valore** invece della frase ha gia' trovato due difetti
(l'omocodia e il telefono con la barra) e ha assolto i venti riconoscitori
anglosassoni. Restava fuori una parte del pacchetto italiano, e non la meno
importante.

Cosa si prova qui, e perche' proprio questo
-------------------------------------------

**I nomi con le particelle e gli apostrofi.** `De Luca`, `Di Marco`,
`Lo Bianco`, `D'Angelo`, `Dell'Orto`, `Della Valle`: in Italia sono
ovunque, e sono la forma in cui un cognome smette di essere una parola sola.
Un riconoscitore che conta «due parole maiuscole» le vede in un modo tutto
suo.

**Gli indirizzi come si scrivono davvero.** `V.le`, `P.zza`, `C.so`, il
civico con la lettera (`12/A`, `7 bis`), il CAP prima o dopo, la frazione,
il nome di via abbreviato (`Via A. Volta`).

**I codici fiscali che non sono quelli dell'esempio.** Le donne hanno il
giorno di nascita **aumentato di 40**; chi e' nato all'estero ha un codice
comune che inizia per **Z**. Sono meta' della popolazione e una fetta
grossa dell'altra meta'.

**I telefoni che non sono ne' fissi ne' cellulari**: numeri verdi 800,
servizi 199, prefissi esteri.

Piu' URL, segreti (JWT, chiavi AWS, blocchi di chiave privata) e i due
riconoscitori spenti di default, importi e date di nascita, che senza una
prova esplicita non li guarda nessuno.

Le regole del banco
-------------------

I valori sono generati qui, con le cifre di controllo calcolate da questo
file. La cornice porta l'etichetta giusta per il tipo: cio' che si misura e'
se il riconoscitore **sa leggere quel valore**, non se sa indovinare senza
contesto.

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

from mr_rao.privacy import (  # noqa: E402
    PrivacyOptions,
    apply_privacy_filter,
)

RNG = random.Random(20260809)
LET = string.ascii_uppercase

_CF_DISPARI = dict(zip(
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    [1, 0, 5, 7, 9, 13, 15, 17, 19, 21, 1, 0, 5, 7, 9, 13, 15, 17, 19, 21,
     2, 4, 18, 20, 11, 3, 6, 8, 12, 14, 16, 10, 22, 25, 24, 23]))
_CF_PARI = dict(zip("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                    list(range(10)) + list(range(26))))
_CONSONANTI = "BCDFGHJKLMNPQRSTVWXYZ"
_MESI = "ABCDEHLMPRST"


def cf_valido(base15: str) -> str:
    s = sum(_CF_DISPARI[c] if i % 2 == 0 else _CF_PARI[c]
            for i, c in enumerate(base15.upper()))
    return base15.upper() + chr(ord("A") + s % 26)


def genera_cf(donna: bool = False, estero: bool = False) -> str:
    cognome = "".join(RNG.choice(_CONSONANTI) for _ in range(3))
    nome = "".join(RNG.choice(_CONSONANTI) for _ in range(3))
    anno = f"{RNG.randint(0, 99):02d}"
    mese = RNG.choice(_MESI)
    # Le donne hanno il giorno aumentato di 40: e' la sola differenza, e
    # porta il campo a due cifre che iniziano per 4, 5, 6 o 7.
    giorno = RNG.randint(1, 28) + (40 if donna else 0)
    comune = ("Z" if estero else RNG.choice("ABCDEFGHIL")) + f"{RNG.randint(0, 999):03d}"
    return cf_valido(f"{cognome}{nome}{anno}{mese}{giorno:02d}{comune}")


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


# --- nomi -------------------------------------------------------------------

_NOMI = ["Giuseppe", "Maria", "Antonio", "Francesca", "Luca", "Chiara",
         "Alessandro", "Giulia", "Marco", "Elena"]
_COGNOMI_SEMPLICI = ["Moretti", "Ferrari", "Esposito", "Bianchi", "Romano",
                     "Colombo", "Ricci", "Marino", "Gallo", "Conti"]
_PARTICELLE = ["De", "Di", "Da", "Del", "Della", "Dello", "Lo", "La", "Li"]
_APOSTROFI = ["D'Angelo", "D'Amico", "Dell'Orto", "Dell'Aquila", "D'Alessio",
              "Sant'Elia", "De' Rossi"]
_ACCENTATI = ["Nicolò", "Niccolò", "Loré", "Perrò", "Bosè", "Cangià"]
_COMPOSTI = ["Maria Luisa", "Gian Marco", "Pier Paolo", "Anna Rita",
             "Gian Luca", "Maria Teresa"]


def nome_semplice() -> str:
    return f"{RNG.choice(_NOMI)} {RNG.choice(_COGNOMI_SEMPLICI)}"


def nome_con_particella() -> str:
    return (f"{RNG.choice(_NOMI)} {RNG.choice(_PARTICELLE)} "
            f"{RNG.choice(_COGNOMI_SEMPLICI)}")


def nome_con_apostrofo() -> str:
    return f"{RNG.choice(_NOMI)} {RNG.choice(_APOSTROFI)}"


def nome_accentato() -> str:
    return f"{RNG.choice(_NOMI)} {RNG.choice(_ACCENTATI)}"


def nome_composto() -> str:
    return f"{RNG.choice(_COMPOSTI)} {RNG.choice(_COGNOMI_SEMPLICI)}"


# --- indirizzi ---------------------------------------------------------------

_VIE_ESTESE = ["Via", "Viale", "Piazza", "Corso", "Largo", "Vicolo",
               "Strada", "Contrada", "Piazzale", "Borgo", "Lungomare"]
_VIE_ABBREVIATE = ["V.le", "P.zza", "C.so", "V.lo", "P.le"]
_LUOGHI = ["Garibaldi", "Verdi", "Dante", "Roma", "Marconi", "Cavour",
           "Mazzini", "Zamboni", "dei Mille", "San Martino"]
_COMUNI = ["Milano", "Roma", "Torino", "Bari", "Bologna", "Napoli"]


def ind_completo() -> str:
    return (f"{RNG.choice(_VIE_ESTESE)} {RNG.choice(_LUOGHI)} "
            f"{RNG.randint(1, 200)}, {RNG.randint(10000, 98999)} "
            f"{RNG.choice(_COMUNI)}")


def ind_abbreviato() -> str:
    return (f"{RNG.choice(_VIE_ABBREVIATE)} {RNG.choice(_LUOGHI)} "
            f"{RNG.randint(1, 200)}, {RNG.randint(10000, 98999)} "
            f"{RNG.choice(_COMUNI)}")


def ind_civico_con_lettera() -> str:
    civico = f"{RNG.randint(1, 200)}{RNG.choice(['/A', '/B', ' bis', '/1'])}"
    return (f"{RNG.choice(_VIE_ESTESE)} {RNG.choice(_LUOGHI)} {civico}, "
            f"{RNG.randint(10000, 98999)} {RNG.choice(_COMUNI)}")


def ind_con_n() -> str:
    return (f"{RNG.choice(_VIE_ESTESE)} {RNG.choice(_LUOGHI)}, n. "
            f"{RNG.randint(1, 200)} - {RNG.randint(10000, 98999)} "
            f"{RNG.choice(_COMUNI)}")


def ind_via_abbreviata() -> str:
    """«Via A. Volta 5»: il nome della strada ridotto all'iniziale puntata.

    Solo su nomi di una parola. La prima versione pescava dall'elenco
    intero e produceva anche «Via S. dei Mille», che non e' un indirizzo:
    l'iniziale sta al posto del *nome di battesimo*, e «dei Mille» non ne
    ha uno davanti. Ventidue casi su duecento sembravano un difetto del
    motore ed erano una forma che nessun comune ha mai scritto — lo stesso
    errore dei SIN canadesi che cominciavano per zero nel banco inglese.
    """
    semplici = [x for x in _LUOGHI if " " not in x]
    return (f"Via {RNG.choice('ABCDEFGLMPRS')}. {RNG.choice(semplici)} "
            f"{RNG.randint(1, 200)}, {RNG.randint(10000, 98999)} "
            f"{RNG.choice(_COMUNI)}")


def ind_senza_cap() -> str:
    return (f"{RNG.choice(_VIE_ESTESE)} {RNG.choice(_LUOGHI)} "
            f"{RNG.randint(1, 200)}, {RNG.choice(_COMUNI)}")


# --- telefoni e resto --------------------------------------------------------

def tel_verde() -> str:
    return f"800 {RNG.randint(100, 999)} {RNG.randint(100, 999)}"


def tel_servizio() -> str:
    return f"199 {RNG.randint(100, 999)} {RNG.randint(100, 999)}"


def tel_estero() -> str:
    return (f"+{RNG.choice([33, 34, 44, 49])} {RNG.randint(1, 9)} "
            f"{RNG.randint(10000000, 99999999)}")


def url() -> str:
    schema = RNG.choice(["https://", "http://", "www."])
    dom = RNG.choice(["studio-legale.it", "comune.bologna.it", "esempio.com"])
    coda = RNG.choice(["", "/pratiche/2024", "/x?id=7", "/a/b/c.pdf"])
    return f"{schema}{dom}{coda}"


def jwt() -> str:
    def b64(n):
        return "".join(RNG.choice(string.ascii_letters + string.digits + "-_")
                       for _ in range(n))
    return f"eyJ{b64(20)}.eyJ{b64(40)}.{b64(43)}"


def chiave_aws() -> str:
    return "AKIA" + "".join(RNG.choice(string.ascii_uppercase + string.digits)
                            for _ in range(16))


def importo() -> str:
    return f"{RNG.randint(1, 999)}.{RNG.randint(0, 999):03d},{RNG.randint(0, 99):02d} euro"


def data_nascita() -> str:
    return f"{RNG.randint(1, 28):02d}/{RNG.randint(1, 12):02d}/{RNG.randint(1950, 2005)}"


QUANTI = 200


def campioni() -> dict[str, tuple[list[str], str, PrivacyOptions]]:
    """nome -> (valori, cornice, opzioni).

    Le opzioni servono ai due riconoscitori spenti di default: provarli con
    le impostazioni normali direbbe solo che sono spenti, che gia' si sa.
    """
    base = PrivacyOptions()
    con_importi = PrivacyOptions(amounts=True)
    con_date = PrivacyOptions(dates=True)

    def n(f, q=QUANTI):
        return [f() for _ in range(q)]

    return {
        "nome + cognome": (n(nome_semplice), "il dott. {v} ha firmato", base),
        "cognome con particella": (n(nome_con_particella),
                                   "il dott. {v} ha firmato", base),
        "cognome con apostrofo": (n(nome_con_apostrofo),
                                  "il dott. {v} ha firmato", base),
        "cognome accentato": (n(nome_accentato), "il dott. {v} ha firmato", base),
        "nome composto": (n(nome_composto), "il dott. {v} ha firmato", base),
        "nome in firma": (n(nome_semplice), "Cordiali saluti,\n{v}", base),
        "particella in firma": (n(nome_con_particella),
                                "Cordiali saluti,\n{v}", base),
        "CF uomo": (n(lambda: genera_cf()), "codice fiscale {v}", base),
        "CF donna (giorno +40)": (n(lambda: genera_cf(donna=True)),
                                  "codice fiscale {v}", base),
        "CF nato all'estero (Z)": (n(lambda: genera_cf(estero=True)),
                                   "codice fiscale {v}", base),
        "P.IVA con IT": (n(lambda: "IT" + piva_valida(f"{RNG.randint(0, 10**10-1):010d}")),
                         "{v}", base),
        "P.IVA con etichetta": (n(lambda: piva_valida(f"{RNG.randint(0, 10**10-1):010d}")),
                                "partita IVA {v}", base),
        "indirizzo completo": (n(ind_completo), "residente in {v}", base),
        "indirizzo abbreviato": (n(ind_abbreviato), "residente in {v}", base),
        "civico con lettera": (n(ind_civico_con_lettera), "residente in {v}", base),
        "indirizzo con «n.»": (n(ind_con_n), "residente in {v}", base),
        "via con iniziale": (n(ind_via_abbreviata), "residente in {v}", base),
        "indirizzo senza CAP": (n(ind_senza_cap), "residente in {v}", base),
        "numero verde 800": (n(tel_verde), "tel. {v}", base),
        "numero 199": (n(tel_servizio), "tel. {v}", base),
        "telefono estero": (n(tel_estero), "tel. {v}", base),
        "URL": (n(url), "vedi {v}", base),
        "JWT": (n(jwt), "token {v}", base),
        "chiave AWS": (n(chiave_aws), "access key {v}", base),
        "importo (acceso)": (n(importo), "totale {v}", con_importi),
        "data di nascita (accesa)": (n(data_nascita), "nato il {v}", con_date),
    }


def prova(valori, modello, opzioni):
    redatti = sospetti = 0
    persi = []
    for v in valori:
        fuori, rep = apply_privacy_filter(modello.format(v=v), opzioni)
        if v not in fuori:
            redatti += 1
        elif rep.suspects:
            sospetti += 1
        elif len(persi) < 2:
            persi.append(v)
    return redatti, sospetti, persi


def main() -> int:
    print("=" * 96)
    print(f"VARIETA' — resto del pacchetto italiano ({QUANTI} valori distinti per tipo)")
    print("=" * 96)
    print(f"\n{'tipo':<26} {'redatto':>9} {'sospetto':>9} {'perso':>7}   esempi persi")
    print("-" * 96)
    guasti = 0
    for tipo, (valori, cornice, opzioni) in campioni().items():
        r, s, p = prova(valori, cornice, opzioni)
        n = len(valori)
        persi = n - r - s
        if r < n:
            guasti += 1
        nota = "  <<<" if persi else ("  (sospetti)" if s else "")
        print(f"{tipo:<26} {r:>8}/{n} {s:>9} {persi:>7}   "
              f"{', '.join(p[:1])[:30]}{nota}")
    print()
    print("  «<<<» = perso in silenzio, ne' tolto ne' segnalato.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
