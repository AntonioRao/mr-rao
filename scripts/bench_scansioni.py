# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Banco di prova: quanto si perde quando il documento e' una scansione.

PRIVACY.md dichiara un limite -- «sulle scansioni la protezione e' piu'
debole» -- e finora quel limite era *stimato*: il banco OCR era sintetico
nel senso peggiore, cioe' fatto di testo perfetto passato per l'OCR. Questo
script lo misura: prende documenti con dati personali **inventati**, li
stampa su una pagina, li fa passare per uno scanner simulato a qualita'
decrescente, li rilegge con il motore OCR vero del prodotto e li dà in pasto
all'anonimizzatore vero. Poi conta.

Cosa conta, e perche' proprio queste tre colonne:

  REDATTA        il dato e' sparito dal testo prodotto;
  SEGNALATA      il dato e' ancora leggibile, ma il rapporto lo elenca
                 fra i sospetti -- chi legge sa dove guardare;
  PERSA          il dato e' ancora leggibile e nessuno lo dice.

La terza e' la sola che fa danno, ed e' per distinguerla dalla seconda che
questo banco esiste. Ce n'e' una quarta, che non e' un merito di nessuno:

  NON LETTA      l'OCR non ha riconosciuto il dato, quindi non e' finito
                 nel Markdown. Non e' una fuga, ma non e' neanche una prova
                 che il filtro funzioni -- e senza questa colonna il degrado
                 estremo sembrerebbe il livello *piu' sicuro* di tutti.

REGOLE DEL BANCO
----------------

**Nessun dato personale reale.** I documenti sono inventati. Le cifre di
controllo (mod-97 dell'IBAN, Luhn della carta, carattere di controllo del
codice fiscale, cifra della partita IVA) sono calcolate qui dentro, con
un'implementazione **indipendente** da quella di ``mr_rao/privacy.py``: se i
campioni fossero costruiti chiamando il validatore del prodotto, il banco
misurerebbe solo che il prodotto e' d'accordo con se' stesso. Le
implementazioni di questo file sono verificate contro vettori di prova
pubblicati (``--verifica``), non contro il prodotto.

**Ripetibile.** Nessuna sorgente di casualita' senza seme: rumore, grana
della carta e inclinazione derivano da semi fissi. Due esecuzioni sullo
stesso ingresso devono stampare la stessa impronta finale.

**Puo' fallire.** L'ultima riga della scala e' un degrado volutamente
illeggibile. Se i numeri non crollano li', il banco non sta misurando la
qualita' della scansione ma qualcos'altro, e va sistemato prima di
crederci. La prima riga (``testo``) e' il soffitto: nessuna immagine,
nessun OCR, solo il filtro sul testo originale.

USO
---

  venv\\Scripts\\python.exe scripts\\bench_scansioni.py
  venv\\Scripts\\python.exe scripts\\bench_scansioni.py --verifica
  venv\\Scripts\\python.exe scripts\\bench_scansioni.py --immagini CARTELLA
  venv\\Scripts\\python.exe scripts\\bench_scansioni.py --documenti 2
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import io
import os
import re
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
if str(RADICE) not in sys.path:
    sys.path.insert(0, str(RADICE))

import numpy as np  # noqa: E402  (arriva con onnxruntime/pandas, non e' nuova)
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402

from mr_rao.ocr_service import ocr_image  # noqa: E402
from mr_rao.privacy import PrivacyOptions, apply_privacy_filter  # noqa: E402


# ===========================================================================
# 1. Cifre di controllo -- implementazione indipendente dal prodotto
# ===========================================================================

# Tabella dei valori per le posizioni **dispari** del codice fiscale
# (DM 23/12/1976). La stessa tabella serve al CIN delle coordinate
# bancarie italiane.
_DISPARI = {
    "0": 1, "1": 0, "2": 5, "3": 7, "4": 9, "5": 13, "6": 15, "7": 17,
    "8": 19, "9": 21, "A": 1, "B": 0, "C": 5, "D": 7, "E": 9, "F": 13,
    "G": 15, "H": 17, "I": 19, "J": 21, "K": 2, "L": 4, "M": 18, "N": 20,
    "O": 11, "P": 3, "Q": 6, "R": 8, "S": 12, "T": 14, "U": 16, "V": 10,
    "W": 22, "X": 25, "Y": 24, "Z": 23,
}
# Posizioni pari: il valore e' semplicemente la posizione nell'alfabeto,
# e per le cifre il loro valore.
_PARI = {c: i for i, c in enumerate("0123456789")}
_PARI.update({c: i for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ")})

_MESI_CF = "ABCDEHLMPRST"
_VOCALI = "AEIOU"


def _solo_lettere(s: str) -> str:
    return re.sub(r"[^A-Z]", "", s.upper())


def _terna_cognome(cognome: str) -> str:
    s = _solo_lettere(cognome)
    ordinate = [c for c in s if c not in _VOCALI] + [c for c in s if c in _VOCALI]
    return ("".join(ordinate) + "XXX")[:3]


def _terna_nome(nome: str) -> str:
    s = _solo_lettere(nome)
    consonanti = [c for c in s if c not in _VOCALI]
    if len(consonanti) >= 4:
        return consonanti[0] + consonanti[2] + consonanti[3]
    ordinate = consonanti + [c for c in s if c in _VOCALI]
    return ("".join(ordinate) + "XXX")[:3]


def carattere_controllo_cf(primi_quindici: str) -> str:
    """Carattere di controllo del codice fiscale, dai quindici che lo precedono."""
    s = primi_quindici.upper()
    if len(s) != 15:
        raise ValueError("servono esattamente quindici caratteri")
    totale = 0
    for posizione, c in enumerate(s, start=1):
        totale += (_DISPARI if posizione % 2 else _PARI)[c]
    return "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[totale % 26]


def codice_fiscale(
    cognome: str, nome: str, anno: int, mese: int, giorno: int, sesso: str,
    belfiore: str,
) -> str:
    """Codice fiscale completo di carattere di controllo. Dati inventati."""
    gg = giorno + (40 if sesso.upper() == "F" else 0)
    corpo = (
        _terna_cognome(cognome)
        + _terna_nome(nome)
        + f"{anno % 100:02d}"
        + _MESI_CF[mese - 1]
        + f"{gg:02d}"
        + belfiore.upper()
    )
    return corpo + carattere_controllo_cf(corpo)


def cifra_luhn(prefisso: str) -> int:
    """Cifra di controllo di Luhn da appendere a ``prefisso`` (ISO/IEC 7812)."""
    totale = 0
    for i, c in enumerate(reversed(prefisso)):
        n = int(c)
        if i % 2 == 0:
            n *= 2
            if n > 9:
                n -= 9
        totale += n
    return (10 - totale % 10) % 10


def carta_pagamento(prefisso: str) -> str:
    """Numero di carta inventato che supera Luhn."""
    return prefisso + str(cifra_luhn(prefisso))


def cifra_partita_iva(prime_dieci: str) -> int:
    """Undicesima cifra della partita IVA (DPR 605/1973, Luhn all'italiana)."""
    totale = 0
    for i, c in enumerate(prime_dieci):
        n = int(c)
        if i % 2:  # posizioni pari, contate da uno
            n *= 2
            if n > 9:
                n -= 9
        totale += n
    return (10 - totale % 10) % 10


def partita_iva(prime_dieci: str) -> str:
    return prime_dieci + str(cifra_partita_iva(prime_dieci))


def _mod97(alfanumerico: str) -> int:
    """Resto ISO 7064 mod-97-10. ``int(c, 36)`` fa la conversione lettera->numero."""
    return int("".join(str(int(c, 36)) for c in alfanumerico)) % 97


def cin_italiano(bban_senza_cin: str) -> str:
    """CIN delle coordinate bancarie italiane (ABI+CAB+conto, 22 caratteri).

    Nessun pezzo della catena lo verifica -- ne' il prodotto ne' questo
    banco -- ma un IBAN italiano senza CIN plausibile non e' un IBAN
    italiano, e il banco non deve contenere dati che *sembrano* validi
    solo dove qualcuno guarda.
    """
    s = bban_senza_cin.upper()
    if len(s) != 22:
        raise ValueError("ABI + CAB + conto = 22 caratteri")
    totale = sum(
        (_DISPARI if posizione % 2 else _PARI)[c]
        for posizione, c in enumerate(s, start=1)
    )
    return "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[totale % 26]


def iban_italiano(abi: str, cab: str, conto: str) -> str:
    """IBAN italiano inventato, con CIN e cifre di controllo mod-97 calcolate."""
    bban_senza_cin = f"{abi}{cab}{conto}"
    cin = cin_italiano(bban_senza_cin)
    bban = cin + bban_senza_cin
    controllo = 98 - _mod97(bban + "IT00")
    return f"IT{controllo:02d}{bban}"


# --- Verifica dei generatori contro vettori pubblicati ---------------------

def verifica_generatori() -> list[str]:
    """Controlla le implementazioni di sopra contro vettori di prova esterni.

    Sono i vettori pubblicati (ISO 13616 per l'IBAN, il classico
    79927398713 per Luhn), **non** i validatori del prodotto: il banco
    dev'essere in grado di dire che il prodotto sbaglia, e non potrebbe se
    prendesse da lui la definizione di «giusto».
    """
    esiti: list[str] = []

    def prova(nome: str, ottenuto, atteso) -> None:
        segno = "OK " if ottenuto == atteso else "NO "
        esiti.append(f"{segno} {nome}: ottenuto {ottenuto!r}, atteso {atteso!r}")

    # IBAN: l'esempio dello standard ISO 13616.
    prova("mod-97 su GB82WEST12345698765432", _mod97("WEST12345698765432GB82"), 1)
    prova(
        "cifre di controllo ricalcolate per l'esempio ISO",
        98 - _mod97("WEST12345698765432GB00"),
        82,
    )
    # Un carattere cambiato non deve piu' tornare.
    prova("mod-97 su un IBAN storpiato", _mod97("WEST12345698765433GB82") == 1, False)

    # Luhn: il numero di prova classico.
    prova("Luhn di 7992739871", cifra_luhn("7992739871"), 3)
    prova("Luhn di 453914880343646", cifra_luhn("453914880343646"), 7)

    # Codice fiscale: l'esempio piu' riprodotto della letteratura italiana,
    # Mario Rossi nato a Roma il 1 gennaio 1980.
    prova(
        "codice fiscale di prova (Rossi Mario, 01/01/1980, H501)",
        codice_fiscale("Rossi", "Mario", 1980, 1, 1, "M", "H501"),
        "RSSMRA80A01H501U",
    )
    prova("terna del cognome «De Luca»", _terna_cognome("De Luca"), "DLC")
    prova("terna del nome «Maria»", _terna_nome("Maria"), "MRA")
    prova("terna del nome «Alessandro»", _terna_nome("Alessandro"), "LSN")

    # Partita IVA: proprieta' -- una cifra cambiata non deve piu' tornare.
    base = "0123456789"
    piva = partita_iva(base)
    rotta = piva[:3] + str((int(piva[3]) + 1) % 10) + piva[4:]
    prova("partita IVA generata lunga 11", len(piva), 11)
    prova(
        "partita IVA con una cifra cambiata non torna",
        cifra_partita_iva(rotta[:10]) == int(rotta[10]),
        False,
    )
    return esiti


# ===========================================================================
# 2. I documenti -- dati inventati, formalmente validi
# ===========================================================================

@dataclass
class Documento:
    nome: str
    testo: str
    # (tipo, valore) dei dati personali che devono sparire.
    attesi: list[tuple[str, str]] = field(default_factory=list)
    # Un documento di controllo non contiene dati personali: ogni
    # sostituzione e' un errore.
    controllo: bool = False


@dataclass
class Soggetto:
    cognome: str
    nome: str
    sesso: str
    anno: int
    mese: int
    giorno: int
    belfiore: str
    via: str
    cap: str
    citta: str
    dominio: str
    abi: str
    cab: str
    conto: str
    iin: str
    piva10: str
    telefono: str
    parola_telefono: str

    @property
    def persona(self) -> str:
        return f"{self.nome} {self.cognome}"

    @property
    def cf(self) -> str:
        return codice_fiscale(
            self.cognome, self.nome, self.anno, self.mese, self.giorno,
            self.sesso, self.belfiore,
        )

    @property
    def email(self) -> str:
        return f"{self.nome.lower()}.{self.cognome.lower()}@{self.dominio}"

    @property
    def iban(self) -> str:
        return iban_italiano(self.abi, self.cab, self.conto)

    @property
    def carta(self) -> str:
        return carta_pagamento(self.iin)

    @property
    def piva(self) -> str:
        return partita_iva(self.piva10)

    @property
    def indirizzo(self) -> str:
        return f"{self.via}, {self.cap} {self.citta}"


# Otto soggetti inventati. I nomi sono quelli che si usano negli esempi
# ("Mario Rossi" e parenti): non appartengono a nessuno. Recapiti, conti e
# codici sono costruiti apposta, non copiati da documenti veri.
SOGGETTI = [
    Soggetto("Rossi", "Mario", "M", 1980, 1, 1, "H501",
             "Via Alessandro Manzoni 14", "20121", "Milano", "esempio.it",
             "05428", "11101", "000000123456", "453914880343646",
             "1234567890", "02 1234567", "Tel."),
    Soggetto("Bianchi", "Giulia", "F", 1975, 6, 22, "F205",
             "Corso Vittorio Emanuele 7", "10128", "Torino", "esempio-srl.it",
             "03069", "01600", "000012345678", "545423455465554",
             "9876543210", "331 4455661", "Cell."),
    Soggetto("Verdi", "Alessandro", "M", 1968, 11, 3, "L219",
             "Piazza della Repubblica 3", "50123", "Firenze", "studioesempio.it",
             "02008", "01005", "000000998877", "371449635398431",
             "5566778899", "055 2210034", "Telefono"),
    Soggetto("Ferrari", "Chiara", "F", 1991, 3, 17, "D612",
             "Viale Giuseppe Garibaldi 88", "40121", "Bologna", "esempio.com",
             "01005", "03200", "000045612300", "601111111111117",
             "1122334455", "051 7788990", "Tel."),
    Soggetto("Esposito", "Antonio", "M", 1959, 9, 30, "F839",
             "Via Toledo 210", "80134", "Napoli", "esempio.net",
             "01030", "03400", "000000777001", "378282246310005",
             "6677889900", "081 5566778", "Recapito"),
    Soggetto("Greco", "Federica", "F", 1987, 5, 12, "A944",
             "Largo Camillo Cavour 21", "70122", "Bari", "esempio.it",
             "05387", "04000", "000000341290", "455673356212114",
             "3344556677", "080 1122334", "Fax"),
    Soggetto("Marchetti", "Lorenzo", "M", 1972, 8, 9, "G273",
             "Contrada San Rocco 5", "90133", "Palermo", "esempio-legale.it",
             "03032", "01602", "000000551122", "491647100025300",
             "7788990011", "339 2200114", "Cellulare"),
    Soggetto("Rinaldi", "Valentina", "F", 1983, 2, 27, "L736",
             "Via Ugo Foscolo 41", "30122", "Venezia", "esempio.org",
             "02008", "02016", "000000889977", "376000000000006",
             "2233445566", "041 9988776", "Tel."),
]


def _lettera(s: Soggetto) -> Documento:
    testo = f"""STUDIO LEGALE ASSOCIATO
{s.indirizzo}

Egr. Sig. {s.persona}

Oggetto: pratica n. 2024/318 - trasmissione documenti

Con la presente si trasmettono gli atti relativi alla pratica in oggetto.
Si prega di verificare i dati anagrafici riportati di seguito.

Codice fiscale: {s.cf}
Partita IVA: IT {s.piva}
{s.parola_telefono} {s.telefono}
Posta elettronica: {s.email}

Il saldo delle competenze puo' essere versato sul conto
IBAN {s.iban}
oppure con carta {s.carta}.

Cordiali saluti,
{s.persona}
"""
    return Documento(
        nome=f"lettera-{s.cognome.lower()}",
        testo=testo,
        attesi=[
            ("nome", s.persona),
            ("indirizzo", s.indirizzo),
            ("codice_fiscale", s.cf),
            ("partita_iva", s.piva),
            ("telefono", s.telefono),
            ("email", s.email),
            ("iban", s.iban),
            ("carta", s.carta),
        ],
    )


def _fattura(s: Soggetto) -> Documento:
    # L'IBAN come lo stampano le banche, a gruppi di quattro.
    iban_gruppi = " ".join(s.iban[i:i + 4] for i in range(0, len(s.iban), 4))
    carta_gruppi = " ".join(s.carta[i:i + 4] for i in range(0, len(s.carta), 4))
    testo = f"""FATTURA N. 118/2024 del 14 marzo 2024

Cliente: Sig.ra {s.persona}
Indirizzo: {s.indirizzo}
Cod. fisc. {s.cf}
P. IVA IT{s.piva}

Descrizione                     Imponibile      IVA        Totale
Consulenza tecnica                 1.200,00    264,00    1.464,00
Rimborso spese                       180,00     39,60      219,60

Modalita' di pagamento: bonifico bancario
IBAN: {iban_gruppi}
In alternativa carta di credito n. {carta_gruppi}

Riferimenti: {s.parola_telefono} {s.telefono} - {s.email}
"""
    return Documento(
        nome=f"fattura-{s.cognome.lower()}",
        testo=testo,
        attesi=[
            ("nome", s.persona),
            ("indirizzo", s.indirizzo),
            ("codice_fiscale", s.cf),
            ("partita_iva", s.piva),
            ("telefono", s.telefono),
            ("email", s.email),
            ("iban", iban_gruppi),
            ("carta", carta_gruppi),
        ],
    )


def _contratto(s: Soggetto) -> Documento:
    testo = f"""CONTRATTO DI PRESTAZIONE D'OPERA PROFESSIONALE

Tra le parti:

Il Dott. {s.persona}, residente in {s.indirizzo},
codice fiscale {s.cf}, partita IVA {s.piva}, di seguito il Professionista;

e la societa' ALFA COSTRUZIONI S.R.L., con sede in Roma, di seguito
il Committente.

Art. 1 - Oggetto
Il Professionista si obbliga a eseguire l'incarico descritto in allegato.

Art. 4 - Corrispettivo e pagamento
Il compenso e' versato sul conto corrente intestato al Professionista,
IBAN {s.iban}. Le eventuali anticipazioni possono essere addebitate
sulla carta {s.carta}.

Art. 7 - Comunicazioni
Ogni comunicazione e' inviata a {s.email} oppure al numero
{s.parola_telefono} {s.telefono}.
"""
    return Documento(
        nome=f"contratto-{s.cognome.lower()}",
        testo=testo,
        attesi=[
            ("nome", s.persona),
            ("indirizzo", s.indirizzo),
            ("codice_fiscale", s.cf),
            ("partita_iva", s.piva),
            ("telefono", s.telefono),
            ("email", s.email),
            ("iban", s.iban),
            ("carta", s.carta),
        ],
    )


def _modulo(s: Soggetto) -> Documento:
    testo = f"""RICHIESTA DI RIMBORSO SPESE - MODULO R4

Cognome e nome ................ {s.persona}
Residenza ..................... {s.indirizzo}
Codice fiscale ................ {s.cf}
Partita IVA ................... IT{s.piva}
{s.parola_telefono} ........... {s.telefono}
Posta elettronica ............. {s.email}

Coordinate per l'accredito
IBAN .......................... {s.iban}
Carta di pagamento ............ {s.carta}

Il sottoscritto dichiara che i dati sopra riportati sono veritieri e
autorizza il trattamento ai sensi del Regolamento UE 2016/679.

Firma ......................... Dott.ssa {s.persona}
"""
    return Documento(
        nome=f"modulo-{s.cognome.lower()}",
        testo=testo,
        attesi=[
            ("nome", s.persona),
            ("indirizzo", s.indirizzo),
            ("codice_fiscale", s.cf),
            ("partita_iva", s.piva),
            ("telefono", s.telefono),
            ("email", s.email),
            ("iban", s.iban),
            ("carta", s.carta),
        ],
    )


# Il documento di controllo: un verbale amministrativo che non contiene un
# solo dato personale. La risposta attesa e' zero sostituzioni a **ogni**
# livello di degrado. Serve a impedire che un banco «migliori» redigendo
# tutto: un filtro che redige tutto e' inutile quanto uno che non redige
# niente.
VERBALE = """VERBALE DI DELIBERAZIONE DEL COMITATO TECNICO N. 47/2024

L'anno duemilaventiquattro, il giorno quattordici del mese di marzo,
presso la sede dell'Ente, si e' riunito il Comitato Tecnico per esaminare
il Piano Industriale e la Fase Uno del programma di sviluppo.

Protocollo n. 2024/0004471 del 14/03/2024
Codice gara: G00471-2024-B
Determinazione dirigenziale n. 118 del 22/02/2024
Capitolo di bilancio 1030204 - Esercizio finanziario 2024

Il Comitato, esaminata la documentazione istruttoria, richiamata la
deliberazione n. 88 del 3 dicembre 2023 e visto il Regolamento Interno,
approva il Quadro Economico rimodulato e dispone la pubblicazione degli
atti all'Albo Pretorio per quindici giorni consecutivi.

Il Piano Operativo e il Documento Unico di Programmazione sono allegati
al presente verbale quali parti integranti.
"""

MODULI_AGENZIA = """MODELLO REDDITI PERSONE FISICHE - QUADRO RN

RN1  Reddito complessivo ............................ euro
RN2  Deduzione per abitazione principale ............ euro
RN4  Reddito imponibile ............................. euro
RN5  Imposta lorda .................................. euro
RN22 Totale detrazioni e crediti d'imposta .......... euro
RN26 Imposta netta .................................. euro
RN45 Differenza .....................................  euro

Quadro RP - Oneri e spese
RP1  Spese sanitarie
RP8  Altre spese detraibili
RP33 Spese per interventi di recupero edilizio

Istruzioni Generali - Fascicolo 1 - Parte II
Il presente modello e' approvato con Provvedimento del Direttore
dell'Agenzia delle Entrate del 15 gennaio 2024.
"""


def costruisci_documenti(quanti_soggetti: int) -> list[Documento]:
    modelli = (_lettera, _fattura, _contratto, _modulo)
    docs: list[Documento] = []
    for i, s in enumerate(SOGGETTI[:quanti_soggetti]):
        docs.append(modelli[i % len(modelli)](s))
    docs.append(Documento("controllo-verbale", VERBALE, [], controllo=True))
    docs.append(Documento("controllo-modello-rn", MODULI_AGENZIA, [], controllo=True))
    return docs


# ===========================================================================
# 3. Lo scanner simulato
# ===========================================================================

MASTER_DPI = 600
LARGHEZZA_POLLICI = 6.4
MARGINE_POLLICI = 0.55
CORPO_PT = 10.5
INTERLINEA = 1.42

_CANDIDATI_FONT = (
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\calibri.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)


def trova_font() -> str:
    for p in _CANDIDATI_FONT:
        if os.path.exists(p):
            return p
    raise SystemExit(
        "nessun font TrueType trovato: il font predefinito di Pillow e' una "
        "bitmap a dimensione fissa e renderebbe la scala dei DPI priva di "
        "significato. Indica un .ttf in _CANDIDATI_FONT."
    )


@dataclass(frozen=True)
class Profilo:
    """Un modo di maltrattare un foglio, non una manopola da girare a piacere."""
    nome: str
    # Stampa / fotocopia: quanto e' frastagliato il bordo del carattere e
    # quanto e' carico l'inchiostro.
    grana_toner: float
    inchiostro: int
    # Scansione: ottica, rumore del sensore, compressione, inclinazione.
    sfocatura: float
    rumore: float
    jpeg: int
    inclinazione: float
    contrasto: float


UFFICIO = Profilo(
    nome="ufficio", grana_toner=34.0, inchiostro=0, sfocatura=0.8,
    rumore=14.0, jpeg=60, inclinazione=0.4, contrasto=1.0,
)
FOTOCOPIA = Profilo(
    nome="fotocopia", grana_toner=48.0, inchiostro=-18, sfocatura=1.3,
    rumore=22.0, jpeg=35, inclinazione=1.2, contrasto=0.55,
)
# La controprova: nessuno consegnerebbe una scansione cosi'. Se i numeri
# non crollano qui, il banco non misura la qualita' della scansione.
ILLEGGIBILE = Profilo(
    nome="illeggibile", grana_toner=70.0, inchiostro=-42, sfocatura=2.6,
    rumore=40.0, jpeg=12, inclinazione=2.5, contrasto=0.28,
)


def rendi_pagina(testo: str, font_path: str) -> Image.Image:
    """Compone il documento su una pagina, alla risoluzione del master."""
    scala = MASTER_DPI / 72.0
    font = ImageFont.truetype(font_path, int(round(CORPO_PT * scala)))
    passo = int(round(CORPO_PT * INTERLINEA * scala))
    righe = testo.split("\n")
    larghezza = int(LARGHEZZA_POLLICI * MASTER_DPI)
    altezza = int(2 * MARGINE_POLLICI * MASTER_DPI) + passo * (len(righe) + 1)
    img = Image.new("L", (larghezza, altezza), 255)
    disegno = ImageDraw.Draw(img)
    x = int(MARGINE_POLLICI * MASTER_DPI)
    y = int(MARGINE_POLLICI * MASTER_DPI)
    for riga in righe:
        disegno.text((x, y), riga, font=font, fill=0)
        y += passo
    return img


def _grana(forma, rng, raggio: float, ampiezza: float) -> np.ndarray:
    """Rumore correlato: la carta ha una grana, non pixel indipendenti.

    Il rumore bianco lo elimina qualunque filtro; quello correlato no, ed e'
    quello che si vede su una scansione vera.
    """
    a = rng.normal(0.0, 1.0, forma).astype(np.float32)
    if raggio > 0:
        sfocato = Image.fromarray(
            np.clip(a * 40 + 128, 0, 255).astype(np.uint8), "L"
        ).filter(ImageFilter.GaussianBlur(raggio))
        a = (np.asarray(sfocato, dtype=np.float32) - 128.0) / 40.0
        a = a / max(float(a.std()), 1e-6)
    return a * ampiezza


def stampa(pagina: Image.Image, profilo: Profilo, seme: int) -> Image.Image:
    """Il foglio fisico: inchiostro che sbava e bordi frastagliati.

    Si calcola **una volta per documento e profilo**: e' lo stesso foglio
    che poi viene scansionato a risoluzioni diverse. Rigenerarlo a ogni DPI
    farebbe variare due cose insieme, e la scala non direbbe piu' niente.
    """
    rng = np.random.default_rng(seme)
    base = np.asarray(
        pagina.filter(ImageFilter.GaussianBlur(1.2)), dtype=np.float32
    )
    base = base + _grana(base.shape, rng, 0.8, profilo.grana_toner)
    soglia = 128 + profilo.inchiostro
    return Image.fromarray(
        np.where(base < soglia, 0, 255).astype(np.uint8), "L"
    )


def scansiona(
    foglio: Image.Image, dpi: int, profilo: Profilo, seme: int, verso: int
) -> Image.Image:
    """Dal foglio al file: inclinazione, campionamento, ottica, sensore, JPEG."""
    rng = np.random.default_rng(seme)
    img = foglio.rotate(
        profilo.inclinazione * verso, resample=Image.BICUBIC, fillcolor=255
    )
    larghezza = max(1, int(round(foglio.width * dpi / MASTER_DPI)))
    altezza = max(1, int(round(foglio.height * dpi / MASTER_DPI)))
    img = img.resize((larghezza, altezza), Image.LANCZOS)
    img = img.filter(ImageFilter.GaussianBlur(profilo.sfocatura))
    a = np.asarray(img, dtype=np.float32)
    a = 255.0 - (255.0 - a) * profilo.contrasto
    a = a + _grana(a.shape, rng, 1.0, profilo.rumore)
    # Illuminazione non uniforme: i bordi del piano sono piu' scuri.
    yy = np.linspace(-1, 1, altezza, dtype=np.float32)[:, None]
    xx = np.linspace(-1, 1, larghezza, dtype=np.float32)[None, :]
    a = a - 12.0 * (xx * xx + yy * yy)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "L")


# ===========================================================================
# 4. Il metro: dov'e' finito ciascun dato
# ===========================================================================

SOGLIA = 0.80  # somiglianza oltre la quale un residuo e' ancora quel dato

REDATTA = "redatta"
SEGNALATA = "segnalata"
PERSA = "persa"
NON_LETTA = "non letta"


def _normalizza(s: str) -> str:
    return re.sub(r"[^0-9A-Za-z]", "", s).upper()


def miglior_finestra(ago: str, pagliaio: str) -> tuple[float, str]:
    """Il pezzo di testo piu' somigliante al dato cercato, e quanto somiglia.

    Serve perche' l'OCR non restituisce mai la stringa esatta: un IBAN con
    un carattere storpiato e' ancora perfettamente leggibile da una persona,
    e contarlo come «sparito» sarebbe la bugia piu' comoda di tutto il banco.

    Restituisce anche la finestra, non solo il numero: un esito «persa» che
    non si puo' guardare e' un'opinione, e ``--dettaglio`` esiste per
    costringere il banco a mostrarla.
    """
    a = _normalizza(ago)
    p = _normalizza(pagliaio)
    if not a or len(p) < len(a):
        return 0.0, ""
    n = len(a)
    confronto = difflib.SequenceMatcher(autojunk=False)
    confronto.set_seq2(a)
    migliore = 0.0
    finestra = ""
    for i in range(len(p) - n + 1):
        confronto.set_seq1(p[i:i + n])
        if confronto.quick_ratio() <= migliore:
            continue
        r = confronto.ratio()
        if r > migliore:
            migliore, finestra = r, p[i:i + n]
            if migliore >= 0.999:
                break
    return migliore, finestra


def somiglianza_massima(ago: str, pagliaio: str) -> float:
    return miglior_finestra(ago, pagliaio)[0]


def _sospetto_copre(campione: str, ago: str, testo: str) -> bool:
    """Il sospetto elencato nel rapporto e' proprio questo dato?

    Del campione il rapporto pubblica solo la maschera (``RS••••••••••••2S``):
    restano i primi due caratteri, gli ultimi due e la lunghezza. Bastano a
    ritrovare la finestra nel testo e a confrontarla con il dato vero.
    """
    if len(campione) <= 4:
        return False
    testa, coda, lung = campione[:2], campione[-2:], len(campione)
    for i in range(len(testo) - lung + 1):
        if testo[i:i + 2] != testa or testo[i + lung - 2:i + lung] != coda:
            continue
        if somiglianza_massima(ago, testo[i:i + lung]) >= SOGLIA:
            return True
    return False


def classifica(
    valore: str, testo_ocr: str, testo_finale: str, sospetti: list[dict]
) -> tuple[str, str]:
    """Dove e' finito il dato, e il residuo che ha fatto decidere cosi'."""
    quanto_ocr, letto = miglior_finestra(valore, testo_ocr)
    if quanto_ocr < SOGLIA:
        return NON_LETTA, letto
    quanto, residuo = miglior_finestra(valore, testo_finale)
    if quanto < SOGLIA:
        return REDATTA, ""
    for s in sospetti:
        if _sospetto_copre(s.get("sample", ""), valore, testo_finale):
            return SEGNALATA, residuo
    return PERSA, residuo


# ===========================================================================
# 5. Il giro
# ===========================================================================

@dataclass
class Riga:
    livello: str
    esiti: dict[str, int] = field(default_factory=dict)
    per_tipo: dict[str, dict[str, int]] = field(default_factory=dict)
    falsi_positivi: int = 0
    secondi: float = 0.0

    def conta(self, tipo: str, esito: str) -> None:
        self.esiti[esito] = self.esiti.get(esito, 0) + 1
        self.per_tipo.setdefault(tipo, {})
        self.per_tipo[tipo][esito] = self.per_tipo[tipo].get(esito, 0) + 1

    @property
    def totale(self) -> int:
        return sum(self.esiti.values())


def _seme(*pezzi) -> int:
    grezzo = "|".join(str(p) for p in pezzi).encode("utf-8")
    return int.from_bytes(hashlib.sha256(grezzo).digest()[:8], "big")


def analizza(testo: str, opzioni: PrivacyOptions) -> tuple[str, dict]:
    finale, rapporto = apply_privacy_filter(testo, opzioni)
    return finale, rapporto.to_dict()


def esegui(
    documenti: list[Documento],
    livelli: list[tuple[str, Profilo | None, int | None]],
    font_path: str,
    cartella_immagini: Path | None,
    incidenti: list[tuple[str, str, str, str, str, str]] | None = None,
) -> list[Riga]:
    opzioni = PrivacyOptions()  # le impostazioni che l'utente trova accese
    righe = [Riga(nome) for nome, _, _ in livelli]

    for indice_doc, doc in enumerate(documenti):
        pagina = None
        fogli: dict[str, Image.Image] = {}
        for indice_livello, (nome_livello, profilo, dpi) in enumerate(livelli):
            riga = righe[indice_livello]
            inizio = time.perf_counter()

            if profilo is None:
                testo_ocr = doc.testo
            else:
                if pagina is None:
                    pagina = rendi_pagina(doc.testo, font_path)
                if profilo.nome not in fogli:
                    fogli[profilo.nome] = stampa(
                        pagina, profilo, _seme("foglio", doc.nome, profilo.nome)
                    )
                verso = 1 if indice_doc % 2 == 0 else -1
                immagine = scansiona(
                    fogli[profilo.nome], dpi, profilo,
                    _seme("scansione", doc.nome, profilo.nome, dpi), verso,
                )
                if cartella_immagini is not None:
                    cartella_immagini.mkdir(parents=True, exist_ok=True)
                    percorso = cartella_immagini / f"{doc.nome}_{nome_livello}.jpg"
                    immagine.save(percorso, format="JPEG", quality=profilo.jpeg)
                else:
                    fd, tmp = tempfile.mkstemp(prefix="bench_scan_", suffix=".jpg")
                    os.close(fd)
                    percorso = Path(tmp)
                    immagine.save(percorso, format="JPEG", quality=profilo.jpeg)
                try:
                    testo_ocr = ocr_image(percorso) or ""
                finally:
                    if cartella_immagini is None:
                        percorso.unlink(missing_ok=True)

            finale, rapporto = analizza(testo_ocr, opzioni)
            if doc.controllo:
                riga.falsi_positivi += int(rapporto["total"])
                if incidenti is not None and rapporto["total"]:
                    incidenti.append((
                        nome_livello, doc.nome, "falso positivo",
                        str(rapporto["counts"]), "", "",
                    ))
            else:
                for tipo, valore in doc.attesi:
                    esito, residuo = classifica(
                        valore, testo_ocr, finale, rapporto["suspects"]
                    )
                    riga.conta(tipo, esito)
                    if incidenti is not None and esito != REDATTA:
                        incidenti.append(
                            (nome_livello, doc.nome, tipo, valore, esito, residuo)
                        )
            riga.secondi += time.perf_counter() - inizio
    return righe


# ===========================================================================
# 6. La tabella
# ===========================================================================

ORDINE = (REDATTA, SEGNALATA, PERSA, NON_LETTA)


def _pct(n: int, tot: int) -> str:
    return f"{100.0 * n / tot:5.1f}%" if tot else "    - "


def tabella(righe: list[Riga]) -> str:
    out = io.StringIO()
    intestazione = (
        f"{'livello':<22} {'dati':>5} {'redatte':>15} {'segnalate':>15} "
        f"{'perse':>15} {'non lette':>15} {'falsi pos.':>10} {'s':>6}"
    )
    out.write(intestazione + "\n")
    out.write("-" * len(intestazione) + "\n")
    for r in righe:
        tot = r.totale
        celle = []
        for esito in ORDINE:
            n = r.esiti.get(esito, 0)
            celle.append(f"{n:4d} {_pct(n, tot)}".rjust(15))
        out.write(
            f"{r.livello:<22} {tot:>5} " + " ".join(celle)
            + f" {r.falsi_positivi:>10} {r.secondi:>6.1f}\n"
        )
    return out.getvalue()


def tabella_per_tipo(righe: list[Riga]) -> str:
    tipi = sorted({t for r in righe for t in r.per_tipo})
    out = io.StringIO()
    intestazione = f"{'livello':<22} " + " ".join(f"{t:>16}" for t in tipi)
    out.write(intestazione + "\n")
    out.write("-" * len(intestazione) + "\n")
    out.write(
        " " * 22 + "  " + " ".join(
            f"{'red/seg/per/nl':>16}" for _ in tipi
        ) + "\n"
    )
    for r in righe:
        celle = []
        for t in tipi:
            d = r.per_tipo.get(t, {})
            celle.append(
                "{}/{}/{}/{}".format(
                    d.get(REDATTA, 0), d.get(SEGNALATA, 0),
                    d.get(PERSA, 0), d.get(NON_LETTA, 0),
                ).rjust(16)
            )
        out.write(f"{r.livello:<22} " + " ".join(celle) + "\n")
    return out.getvalue()


def impronta(righe: list[Riga]) -> str:
    """Un'impronta della tabella: due esecuzioni devono stamparla uguale."""
    pezzi = []
    for r in righe:
        pezzi.append(r.livello)
        pezzi.extend(f"{e}={r.esiti.get(e, 0)}" for e in ORDINE)
        pezzi.append(f"fp={r.falsi_positivi}")
        for t in sorted(r.per_tipo):
            d = r.per_tipo[t]
            pezzi.append(t + ":" + ",".join(f"{e}={d.get(e, 0)}" for e in ORDINE))
    return hashlib.sha256("|".join(pezzi).encode("utf-8")).hexdigest()[:16]


FILTRO_SPENTO = PrivacyOptions(
    emails=False, phones=False, names=False, fiscal=False, amounts=False,
    urls=False, addresses=False, secrets=False, dates=False, documenti=False,
)


def controprova_filtro(documenti: list[Documento]) -> str:
    """Il metro dipende davvero dall'anonimizzatore?

    Si spegne ogni riconoscitore e si rimisura il testo pulito: se il banco
    continuasse a contare redazioni, non starebbe misurando il filtro ma
    qualche altra cosa -- di solito la propria soglia di somiglianza.
    E' la regola di casa: disattivalo e guarda il test diventare rosso.
    """
    conteggi = {REDATTA: 0, SEGNALATA: 0, PERSA: 0, NON_LETTA: 0}
    for doc in documenti:
        if doc.controllo:
            continue
        finale, rapporto = analizza(doc.testo, FILTRO_SPENTO)
        for _tipo, valore in doc.attesi:
            esito, _ = classifica(
                valore, doc.testo, finale, rapporto["suspects"]
            )
            conteggi[esito] += 1
    totale = sum(conteggi.values())
    verdetto = (
        "il metro dipende dall'anonimizzatore: spegnendolo la copertura va a zero."
        if conteggi[REDATTA] == 0 and conteggi[PERSA] == totale
        else "ATTENZIONE: con i riconoscitori spenti il banco conta ancora "
             "redazioni. Il metro non sta misurando il filtro."
    )
    return (
        f"controprova  riconoscitori spenti, testo pulito -> "
        f"{conteggi[REDATTA]} redatte, {conteggi[PERSA]} perse su {totale}\n"
        f"{verdetto}\n"
    )


def controprova(righe: list[Riga]) -> str:
    """Il banco puo' fallire? Confronto fra il livello migliore e il peggiore."""
    per_nome = {r.livello: r for r in righe}
    alto = per_nome.get("ufficio 300")
    basso = per_nome.get("illeggibile 60")
    if alto is None or basso is None:
        return "controprova non eseguibile: manca un livello.\n"

    def copertura(r: Riga) -> float:
        return 100.0 * r.esiti.get(REDATTA, 0) / r.totale if r.totale else 0.0

    a, b = copertura(alto), copertura(basso)
    verdetto = (
        "il banco puo' fallire: il degrado estremo fa crollare la copertura."
        if b <= a - 30.0
        else "ATTENZIONE: la copertura NON crolla sul degrado estremo. "
             "Questo banco non sta misurando la qualita' della scansione."
    )
    return (
        f"controprova  ufficio 300 -> {a:.1f}% redatte, "
        f"illeggibile 60 -> {b:.1f}% redatte\n{verdetto}\n"
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--documenti", type=int, default=len(SOGGETTI),
                   help="quanti soggetti usare (default: tutti)")
    p.add_argument("--immagini", type=Path, default=None,
                   help="cartella dove lasciare le scansioni simulate")
    p.add_argument("--verifica", action="store_true",
                   help="verifica i generatori di cifre di controllo ed esce")
    p.add_argument("--dettaglio", action="store_true",
                   help="elenca ogni dato non redatto con il residuo trovato")
    args = p.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    esiti = verifica_generatori()
    guasti = [e for e in esiti if e.startswith("NO ")]
    if args.verifica:
        print("Verifica dei generatori contro vettori di prova pubblicati:")
        for e in esiti:
            print("  " + e)
        return 1 if guasti else 0
    if guasti:
        print("i generatori di cifre di controllo non passano i vettori di prova:")
        for e in guasti:
            print("  " + e)
        print("esegui --verifica per il dettaglio. Il banco si ferma qui: "
              "campioni non validi misurerebbero un'altra cosa.")
        return 1

    documenti = costruisci_documenti(max(1, args.documenti))
    livelli: list[tuple[str, Profilo | None, int | None]] = [
        ("testo (niente OCR)", None, None),
    ]
    for profilo in (UFFICIO, FOTOCOPIA):
        for dpi in (300, 200, 150, 100):
            livelli.append((f"{profilo.nome} {dpi}", profilo, dpi))
    livelli.append(("illeggibile 60", ILLEGGIBILE, 60))

    con_dati = [d for d in documenti if not d.controllo]
    attesi = sum(len(d.attesi) for d in con_dati)
    print(f"documenti con dati personali: {len(con_dati)} "
          f"({attesi} dati attesi per livello)")
    print(f"documenti di controllo a verita' zero: "
          f"{sum(1 for d in documenti if d.controllo)}")
    print(f"livelli: {len(livelli)}   font: {trova_font()}\n")

    incidenti: list[tuple[str, str, str, str, str, str]] = []
    inizio = time.perf_counter()
    righe = esegui(documenti, livelli, trova_font(), args.immagini, incidenti)
    durata = time.perf_counter() - inizio

    print(tabella(righe))
    print("Per tipo di dato (redatte/segnalate/perse/non lette):\n")
    print(tabella_per_tipo(righe))
    if args.dettaglio:
        print("Dettaglio dei dati non redatti (residuo = come e' rimasto):\n")
        for livello, doc, tipo, valore, esito, residuo in incidenti:
            print(f"  [{livello}] {doc} / {tipo} / {esito}")
            print(f"      atteso : {valore}")
            print(f"      residuo: {residuo}")
        print()
    print(controprova(righe))
    print(controprova_filtro(documenti))
    print(f"impronta dei risultati: {impronta(righe)}")
    print(f"tempo totale: {durata:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
