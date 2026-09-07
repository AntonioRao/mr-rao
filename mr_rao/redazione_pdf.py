# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Redazione di un PDF **senza trasformarlo in immagine**.

Cosa fa
-------

Toglie i byte dei glifi dal flusso di contenuto e mette al loro posto il
segnaposto, scritto con un font standard aggiunto alle risorse della pagina. Il
PDF che esce e' ancora un PDF di testo — selezionabile, ricercabile, dello
stesso peso — e il dato **non c'e' piu' nel file**: non e' coperto da un
rettangolo nero, che si toglie in un minuto e non protegge niente.

Perche' a questo livello, e non a quello degli oggetti
-----------------------------------------------------

L'API a oggetti del motore PDF sembra la strada ovvia e non funziona sui
documenti veri. Misurato su tre, e ognuno rompe un pezzo diverso:

  * su una Gazzetta Ufficiale il testo sta **dentro un Form XObject**, e da li'
    gli oggetti non si possono rimuovere;
  * su una presentazione ogni oggetto e' **una parola**, e «Mario Rossi» non e'
    riconoscibile ne' nell'uno ne' nell'altro;
  * su un manuale gli oggetti restituiscono stringa vuota.

Zero oggetti operabili su tre documenti, e la verifica lo disse senza sconti:
settantatre sostituzioni su settantatre sopravvissute. Il flusso di contenuto
invece si legge su tutti, **anche dentro i form**.

Le due domande, e le due fonti
------------------------------

**Cosa** togliere e **dove** sta sono domande diverse e vanno a fonti diverse.

Il testo ricostruito dal flusso serve a sapere dove stanno i glifi, ma come
testo e' approssimato: gli spazi spesso non sono caratteri, gli a capo si
deducono dalle coordinate, una maiuscola iniziale disegnata a parte spezza un
cognome in due. Farci girare sopra il motore vuol dire perdere delle cose, e
ogni euristica in piu' sugli spazi ne recupera una e ne perde un'altra.

Quindi **cosa** togliere lo decide il testo estratto dal motore PDF — lo stesso
su cui Mr. Rao ha i suoi test e converte tutti i giorni — e la mappa dei glifi
dice soltanto **dove** cercarlo. Questa separazione, da sola, ha portato le
sopravvissute da undici a zero sul primo documento di prova.

Come si mette il segnaposto senza fare i conti
----------------------------------------------

Non si fanno. Dentro un blocco `BT`/`ET` la posizione avanza da sola a ogni
glifo mostrato, quindi basta spezzare l'operatore in tre: la testa con il font
originale, il segnaposto con il font standard, la coda di nuovo con
l'originale. Nessuna coordinata, nessuna larghezza di glifo, nessuna matrice da
comporre — le tre cose che, sbagliate, spostano il testo di mezza pagina.

Il prezzo e' che la riga si ricompone, perche' il segnaposto non e' largo
quanto il valore che ha sostituito. Si vede, e non nasconde niente.

Cosa non fa, dichiarato
-----------------------

  * **le scansioni**. Un PDF senza testo estraibile qui non si tocca: non c'e'
    nessun glifo da togliere, e disegnarci sopra dei rettangoli sarebbe
    esattamente la redazione finta che questo modulo esiste per evitare;
  * gli operatori `'` e `"`, che mostrano il testo **e** vanno a capo:
    spezzarli richiederebbe di replicare l'a capo. Sono rari, e quando
    compaiono la pagina finisce nel ripiego invece di essere tagliata a meta';
  * il testo dentro le **annotazioni** e i campi modulo, che non sta nel flusso
    della pagina.

Il ripiego non e' implementato qui: `EsitoRedazione.pagine_in_ripiego` dice
quali pagine non sono state trattate, e sta al chiamante decidere cosa farne.
Una pagina che finisce li' **non e' stata redatta**, e chiamarla redatta
sarebbe il modo peggiore di sbagliare.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pikepdf
import pypdfium2 as pdfium

from .privacy import PrivacyOptions, apply_privacy_filter
# L'allineamento fra il testo redatto e quello di partenza sta in un modulo
# suo dalla 1.29.0: lo usa anche il nome del file, e due copie di questo
# codice sarebbero due modi diversi di tagliare lo stesso dato.
from .posizioni import (
    ANCORE_DA_PROVARE,
    MINIMO_CERCABILE,
    intervalli_da_togliere,
)

# ---------------------------------------------------------------------------
# Dai byte del flusso al testo: il ponte
# ---------------------------------------------------------------------------

#: Gli operatori che mostrano testo.
MOSTRA = {b"Tj", b"TJ", b"'", b'"'}

#: I due motivi di ripiego che vogliono dire «questa pagina e' una scansione».
#: Sono costanti e non stringhe scritte due volte perche' `redigi_pdf` ci
#: ragiona sopra: se **ogni** pagina e' finita in ripiego per uno di questi, il
#: documento e' una scansione e va rifiutato come tale, non consegnato con un
#: elenco di pagine non trattate lungo quanto il documento.
MOTIVO_SCANSIONE = "nessun testo estraibile: pagina scansionata"
MOTIVO_OCR = "scansione con testo OCR sovrapposto: il dato resta nell'immagine"

#: I modi di rendering del testo (`Tr`) in cui i glifi **non si disegnano**:
#: 3 e' «ne' riempimento ne' contorno», 7 e' «solo ritaglio». Sono i due modi
#: con cui ogni motore OCR mette il testo riconosciuto sopra una scansione:
#: si seleziona e si cerca, ma cio' che si vede sono i pixel sotto.
MODI_INVISIBILI = {3, 7}

#: Sotto questo arretramento (millesimi di em) due parole sono attaccate
#: davvero; sopra, in mezzo c'e' uno spazio che nessun carattere rappresenta.
SOGLIA_SPAZIO = 150

#: Due pezzi la cui ordinata differisce di meno di questo stanno sulla stessa
#: riga. In punti tipografici: sotto il punto e' aggiustamento ottico.
TOLLERANZA_RIGA = 1.0

#: Il font del segnaposto. E' uno dei quattordici standard: non va incorporato,
#: e la sua codifica contiene le graffe — che i font **sottoinsieme** del
#: documento quasi mai contengono, perche' quel documento non le usava.
NOME_RISORSA_STANDARD = "/MrRaoSegnaposto"

#: I caratteri che nessuna delle due parti e' riuscita a decodificare.
IGNOTI = "�￾"

#: Il colore del rettangolo, in RGB da 0 a 1. Verde scuro: si vede a colpo
#: d'occhio su una pagina bianca, e sopra ci sta il bianco con un contrasto
#: che si legge anche stampato in scala di grigi.
COLORE_RETTANGOLO = (0.043, 0.243, 0.157)

#: Quanto il rettangolo deborda dal riquadro del valore, in punti. Senza, le
#: lettere alte e i discendenti toccano il bordo e sembra un errore di stampa.
MARGINE_RETTANGOLO = 1.2

#: Larghezza media di un carattere dell'Helvetica, in frazioni di corpo. Serve
#: solo a decidere se l'etichetta ci sta: e' una stima, e sbaglia dalla parte
#: giusta -- se e' un po' larga il rettangolo esce un po' generoso.
LARGHEZZA_MEDIA_CARATTERE = 0.52

#: Corpo minimo e massimo dell'etichetta. Sotto il minimo non si legge; sopra
#: il massimo un segnaposto in mezzo a un testo piccolo grida piu' del testo.
CORPO_MIN, CORPO_MAX = 5.0, 10.5

#: Quanto puo' scostarsi un pixel dal colore del rettangolo e valere ancora
#: come «e' il rettangolo». Su 255: l'antialiasing ai bordi e la conversione
#: di spazio colore del motore di rendering spostano di qualche unita'.
TOLLERANZA_COLORE = 12

#: Quanta parte del rettangolo deve arrivare a schermo perche' lo si consideri
#: disegnato. Non il 100%: dentro ci sta l'etichetta bianca, che di quel
#: rettangolo copre una fetta, e ai bordi c'e' l'antialiasing. Sotto questa
#: quota il rettangolo c'e' nel file ma **non si vede**, che per chi legge e'
#: la stessa cosa che non esserci.
QUOTA_MINIMA_VISIBILE = 0.30

#: Sulla pagina rifatta «sopra», l'etichetta si ridisegna dentro il
#: rettangolo.
#:
#: Ha un prezzo, e va detto: quel testo si aggiunge a quello che sta gia' nel
#: flusso, quindi su **quelle pagine** il segnaposto compare due volte in un
#: copia-incolla — una volta al suo posto nella frase, e una in fondo alla
#: pagina. L'alternativa e' un rettangolo pieno e muto: si vede che li' c'era
#: un dato, non si vede piu' quale genere di dato fosse.
#:
#: Si e' scelto di tenere l'etichetta perche' il documento redatto si guarda
#: piu' spesso di quanto lo si copi, e perche' «qui c'era un codice fiscale»
#: e' meta' di cio' che un redatto deve dire. Mettendo questa a False si
#: prende l'altro compromesso, senza toccare altro.
ETICHETTA_SUL_RIQUADRO_SOPRA = True


@dataclass
class Glifo:
    """Un glifo mostrato: dove sta nei byte dell'operando, e che carattere e'."""
    scarto: int
    lunghezza: int
    testo: str


@dataclass
class Emissione:
    """Il testo prodotto da un operando di un'istruzione, e da dove viene."""
    contenitore: int
    istruzione: int
    elemento: int
    inizio: int
    glifi: list[Glifo]
    risorsa_font: str
    corpo: float
    #: L'ultimo colore di riempimento visto prima di questo pezzo, come
    #: (operandi, operatore). Serve a **rimetterlo** dopo il segnaposto, che
    #: viene scritto in bianco: senza, il resto della riga proseguirebbe
    #: bianco su bianco, e sparirebbe del testo che non doveva sparire.
    colore: tuple | None = None
    #: Questi glifi erano in modo di rendering invisibile (`3 Tr` o `7 Tr`).
    #: Togliere del testo che non si vede non e' una redazione se cio' che si
    #: vede resta: vedi `_solo_glifi_invisibili`.
    invisibile: bool = False


@dataclass
class EsitoRedazione:
    pagine: int = 0
    valori_da_togliere: int = 0
    glifi_rimossi: int = 0
    segnaposto_inseriti: int = 0
    pagine_in_ripiego: list[int] = field(default_factory=list)
    motivi_ripiego: list[str] = field(default_factory=list)
    #: Nessun testo estraibile in tutto il documento: e' una scansione, e qui
    #: non si tocca niente.
    scansione: bool = False
    #: Le pagine in cui il fondo colorato ha dovuto essere ridisegnato **sopra**
    #: perche' sotto non si vedeva (vedi `_rifai_le_pagine_coperte`). Su queste
    #: il segnaposto compare due volte nel testo copiato: una nella frase, una
    #: in fondo alla pagina. Dirlo e' meglio che lasciarlo scoprire.
    pagine_riquadro_sopra: list[int] = field(default_factory=list)
    #: Le pagine in cui il fondo colorato **non si vede**, e non e' stato
    #: possibile rimediare: il dato e' tolto lo stesso, ma chi guarda la
    #: pagina non ha nessun segno che li' ci fosse qualcosa.
    pagine_senza_riquadro: list[int] = field(default_factory=list)
    #: Quanti valori sono stati tolti dalle **proprieta' del documento** --
    #: titolo, autore, oggetto, e il blocco XMP. Non stanno in nessuna pagina,
    #: quindi non entrano nei conti per pagina, ma sono dati usciti da un file
    #: che si chiama «-redatto.pdf» e vanno contati da qualche parte.
    metadati_tolti: int = 0
    #: Quanti valori sono stati tolti dai **titoli dei segnalibri**. Come i
    #: metadati: testo del documento che non sta in nessun flusso di pagina.
    segnalibri_tolti: int = 0
    #: Quanti **allegati** sono stati rimossi. Non e' un conto di valori ma di
    #: file: un allegato e' un documento intero che non abbiamo redatto, e
    #: viene tolto senza guardarci dentro (vedi `_togli_allegati`). Va detto,
    #: perche' il PDF che esce ha un pezzo in meno di quello che e' entrato.
    allegati_tolti: int = 0
    #: Le pagine in cui il dato stava **nei pixel di una scansione** e il
    #: rettangolo e' stato messo sulle coordinate che lo strato OCR dichiara.
    #: Sono trattate, non in ripiego — ma il rettangolo sta dove l'OCR dice che
    #: sta la parola, e se quello strato e' disallineato rispetto all'immagine
    #: copre i pixel sbagliati. Non e' verificabile dal file: si nomina la
    #: pagina e la si fa guardare.
    pagine_coperte_sull_ocr: list[int] = field(default_factory=list)


class _Contenitore:
    """Una pagina o un Form XObject, con le sue istruzioni da riscrivere."""

    def __init__(self, oggetto):
        self.oggetto = oggetto
        self.istruzioni = list(pikepdf.parse_content_stream(oggetto))
        self.modificato = False


def _da_utf16be(esadecimale: str) -> str:
    grezzo = bytes.fromhex(
        esadecimale if len(esadecimale) % 2 == 0 else "0" + esadecimale)
    try:
        return grezzo.decode("utf-16-be")
    except UnicodeDecodeError:
        return grezzo.decode("latin-1", errors="replace")


def leggi_tounicode(flusso: bytes) -> dict[int, str]:
    """Il CMap `/ToUnicode`: da codice di glifo a caratteri.

    Si leggono le due forme che i produttori di PDF scrivono davvero:
    `beginbfchar` (una coppia per riga) e `beginbfrange` (un intervallo, con la
    destinazione singola oppure come elenco). Il resto del formato CMap non
    compare nei ToUnicode generati, e se comparisse questa funzione
    restituirebbe **meno** mappature, non di piu': l'esito e' un carattere non
    decodificato, cioe' un valore che non si ritrova e una pagina che va nel
    ripiego. Sbaglia dalla parte giusta.
    """
    testo = flusso.decode("latin-1", errors="replace")
    mappa: dict[int, str] = {}

    for blocco in re.findall(r"beginbfchar(.*?)endbfchar", testo, re.S):
        for codice, destinazione in re.findall(
                r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", blocco):
            mappa[int(codice, 16)] = _da_utf16be(destinazione)

    for blocco in re.findall(r"beginbfrange(.*?)endbfrange", testo, re.S):
        for da, a, primo in re.findall(
                r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", blocco):
            inizio, fine, base = int(da, 16), int(a, 16), int(primo, 16)
            if fine - inizio > 0xFFFF:
                continue
            for k in range(fine - inizio + 1):
                if base + k < 0x110000:
                    mappa[inizio + k] = chr(base + k)
        for da, _a, elenco in re.findall(
                r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*\[(.*?)\]", blocco, re.S):
            inizio = int(da, 16)
            for k, pezzo in enumerate(re.findall(r"<([0-9A-Fa-f]+)>", elenco)):
                mappa[inizio + k] = _da_utf16be(pezzo)
    return mappa


_NOMI_GLIFO = {
    "space": " ", "period": ".", "comma": ",", "colon": ":", "semicolon": ";",
    "hyphen": "-", "endash": "–", "emdash": "—",
    "quotesingle": "'", "quoteright": "’", "quoteleft": "‘",
    "quotedblleft": "“", "quotedblright": "”", "slash": "/",
    "parenleft": "(", "parenright": ")", "percent": "%", "at": "@",
    "numbersign": "#", "ampersand": "&", "plus": "+", "equal": "=",
    "asterisk": "*", "underscore": "_", "bullet": "•", "degree": "°",
    "Euro": "€", "germandbls": "ß",
}


def _da_nome_glifo(nome: str) -> str:
    n = nome.lstrip("/")
    if n in _NOMI_GLIFO:
        return _NOMI_GLIFO[n]
    if len(n) == 1:
        return n
    esadecimale = re.fullmatch(r"uni([0-9A-Fa-f]{4})", n)
    if esadecimale:
        return chr(int(esadecimale.group(1), 16))
    return IGNOTI[0]


@dataclass
class Font:
    a_due_byte: bool
    tounicode: dict[int, str] = field(default_factory=dict)
    semplice: dict[int, str] = field(default_factory=dict)

    def decodifica(self, grezzo: bytes) -> list[str]:
        """Un elemento per glifo mostrato.

        Il **numero** di elementi conta quanto il loro contenuto: e' quello che
        permette di risalire dal carattere al byte che lo ha disegnato.
        """
        fuori: list[str] = []
        passo = 2 if self.a_due_byte else 1
        for i in range(0, len(grezzo) - passo + 1, passo):
            codice = int.from_bytes(grezzo[i:i + passo], "big")
            if codice in self.tounicode:
                fuori.append(self.tounicode[codice])
            elif codice in self.semplice:
                fuori.append(self.semplice[codice])
            elif not self.a_due_byte and 32 <= codice < 127:
                # Nessuna mappa: la codifica di un font semplice e' ASCII sul
                # tratto stampabile abbastanza spesso da valere piu' di un buco.
                fuori.append(chr(codice))
            else:
                fuori.append(IGNOTI[0])
        return fuori


def carica_font(dizionario) -> Font:
    tounicode: dict[int, str] = {}
    if "/ToUnicode" in dizionario:
        try:
            tounicode = leggi_tounicode(bytes(dizionario.ToUnicode.read_bytes()))
        except Exception:
            tounicode = {}
    semplice: dict[int, str] = {}
    codifica = dizionario.get("/Encoding")
    if codifica is not None and hasattr(codifica, "get"):
        differenze = codifica.get("/Differences")
        if differenze is not None:
            corrente = 0
            for voce in differenze:
                if isinstance(voce, (int, float)):
                    corrente = int(voce)
                else:
                    semplice[corrente] = _da_nome_glifo(str(voce))
                    corrente += 1
    return Font(
        a_due_byte=str(dizionario.get("/Subtype", "")) == "/Type0",
        tounicode=tounicode,
        semplice=semplice,
    )


# ---------------------------------------------------------------------------
# Leggere la pagina: il testo, e da quale byte viene ogni carattere
# ---------------------------------------------------------------------------


def _elementi(operandi):
    """Gli operandi di un `Tj` e quelli **dentro** l'array di un `TJ`, in fila.

    La posizione e' quella dentro l'array, ed e' cio' che serve per riscrivere:
    un `Tj` ha un elemento solo, e la sua posizione e' 0.
    """
    for operando in operandi:
        if isinstance(operando, pikepdf.Array):
            for voce in operando:
                yield voce
        else:
            yield operando


def _ordinata(op: bytes, operandi, ultima):
    """L'ordinata dopo l'operatore, per capire se si e' cambiata riga.

    `Tm` la porta assoluta (l'ultimo dei sei numeri); `Td`/`TD` la spostano di
    `ty`, e uno spostamento nullo vuol dire **stessa riga**; `T*` va sempre a
    capo. Non e' la matrice di testo completa, ne' serve: qui si decide solo se
    fra due pezzi ci va un a capo o uno spazio.
    """
    if op == b"Tm" and len(operandi) >= 6:
        try:
            return float(operandi[5])
        except Exception:
            return ultima
    if op in (b"Td", b"TD") and len(operandi) >= 2:
        try:
            spostamento = float(operandi[1])
        except Exception:
            return ultima
        return ultima if spostamento == 0 else (ultima or 0.0) + spostamento
    return None  # T*: riga nuova per definizione


def _leggi(oggetto, contenitori: list[_Contenitore], emissioni: list[Emissione],
           pezzi: list[str], profondita: int) -> None:
    if profondita > 6:
        return
    try:
        contenitore = _Contenitore(oggetto)
    except Exception:
        return
    contenitori.append(contenitore)
    indice_contenitore = len(contenitori) - 1

    risorse = oggetto.get("/Resources", pikepdf.Dictionary())
    caratteri = risorse.get("/Font", pikepdf.Dictionary())
    forme = risorse.get("/XObject", pikepdf.Dictionary())

    font: Font | None = None
    risorsa = ""
    corpo = 0.0
    ultima_y = None
    colore = None
    spazio_colore = None
    # Il modo di rendering del testo (`Tr`). Serve a una domanda sola, ed e'
    # una domanda che decide se una redazione e' vera: **questi glifi si
    # vedono?** Sopra una scansione passata dall'OCR il testo c'e' ed e' in
    # modo 3, cioe' invisibile — toglierlo non toglie niente a chi guarda la
    # pagina. Vedi `_solo_glifi_invisibili`.
    modo_testo = 0
    cache: dict[str, Font] = {}

    for i, istruzione in enumerate(contenitore.istruzioni):
        operandi = istruzione.operands
        op = str(istruzione.operator).encode("latin-1")

        if op == b"cs":
            # **Lo spazio colore va ricordato insieme al colore**, e non e' un
            # dettaglio: `scn` prende il suo significato dallo spazio corrente.
            # Rimettendo `1 scn` dopo un `1 1 1 rg` — che nel frattempo ha
            # portato lo spazio a DeviceRGB — quel `1` vuol dire un'altra cosa,
            # e su una Gazzetta il risultato era **mezza pagina bianca su
            # bianco**: il testo c'era ancora e non si vedeva piu'.
            spazio_colore = list(operandi)

        elif op in (b"g", b"rg", b"k", b"sc", b"scn"):
            # Il colore corrente si ricorda per poterlo rimettere dopo il
            # segnaposto, che va scritto in bianco. Rimetterne uno a caso —
            # nero, per dire — farebbe cambiare colore al resto della riga in
            # ogni documento che non sia nero su bianco.
            colore = (list(operandi), str(istruzione.operator),
                      spazio_colore if op in (b"sc", b"scn") else None)

        elif op == b"Tr" and len(operandi) >= 1:
            try:
                modo_testo = int(operandi[0])
            except Exception:
                modo_testo = 0

        elif op == b"Tf" and len(operandi) >= 2:
            risorsa = str(operandi[0])
            try:
                corpo = float(operandi[1])
            except Exception:
                corpo = 0.0
            if risorsa not in cache and risorsa in caratteri:
                cache[risorsa] = carica_font(caratteri[risorsa])
            font = cache.get(risorsa)

        elif op == b"Do" and len(operandi) >= 1:
            chiave = str(operandi[0])
            if chiave in forme and str(forme[chiave].get("/Subtype", "")) == "/Form":
                _leggi(forme[chiave], contenitori, emissioni, pezzi,
                       profondita + 1)

        elif op in MOSTRA and font is not None:
            for posizione, operando in enumerate(_elementi(operandi)):
                if isinstance(operando, pikepdf.String):
                    passo = 2 if font.a_due_byte else 1
                    caratteri_glifo = font.decodifica(bytes(operando))
                    if not caratteri_glifo:
                        continue
                    emissioni.append(Emissione(
                        indice_contenitore, i, posizione,
                        sum(len(p) for p in pezzi),
                        [Glifo(k * passo, passo, c)
                         for k, c in enumerate(caratteri_glifo)],
                        risorsa, corpo, colore,
                        modo_testo in MODI_INVISIBILI))
                    pezzi.extend(caratteri_glifo)
                elif isinstance(operando, (int, float)) and operando < -SOGLIA_SPAZIO:
                    # **Lo spazio fra due parole spesso non e' un carattere**:
                    # e' un arretramento dentro l'array. Senza questo «Mario» e
                    # «Rossi» arrivano incollati.
                    pezzi.append(" ")

        elif op in (b"Td", b"TD", b"T*", b"Tm"):
            # A capo **solo se cambia la riga**. Con un a capo a ogni `Tm»,
            # «Il Ministro:» e il cognome che lo segue sulla stessa riga
            # arrivavano separati, e la firma degli atti pubblici non si
            # riconosceva piu'.
            #
            # E la tolleranza non e' prudenza: la maiuscola iniziale di una
            # firma e' disegnata a parte, con una matrice che differisce di
            # frazioni di punto. Senza, un cognome usciva come «G» a capo
            # «IORGETTI».
            nuova_y = _ordinata(op, operandi, ultima_y)
            if ultima_y is None or nuova_y is None:
                cambio = True
            elif isinstance(nuova_y, float) and isinstance(ultima_y, float):
                cambio = abs(nuova_y - ultima_y) > TOLLERANZA_RIGA
            else:
                cambio = True
            if cambio:
                pezzi.append("\n")
            elif pezzi and not pezzi[-1].endswith((" ", "\n")):
                pezzi.append(" ")
            if nuova_y is not None:
                ultima_y = nuova_y


# ---------------------------------------------------------------------------
# Cosa togliere, e dove sta
# ---------------------------------------------------------------------------


def _senza_spazi(testo: str) -> tuple[str, list[int]]:
    """Il testo senza **nessuno** spazio, e da dove viene ogni carattere.

    Non «spazi normalizzati»: tolti del tutto. Nel flusso lo spazio fra due
    parole spesso non e' un carattere, l'a capo si deduce dalle coordinate, e
    una maiuscola disegnata a parte fa comparire uno stacco che nel documento
    non c'e'. Normalizzando, quei tre casi restano tre casi; togliendo gli
    spazi spariscono insieme.
    """
    fuori: list[str] = []
    da_dove: list[int] = []
    for i, c in enumerate(testo):
        if not c.isspace():
            fuori.append(c)
            da_dove.append(i)
    return "".join(fuori), da_dove


def _trova(pagliaio: str, ago: str, da: int) -> int:
    """`str.find`, ma un carattere non decodificato vale per qualunque cosa.

    Serve perche' un accento che il font non dichiara fa fallire il confronto
    sull'intera stringa: «via Niccolo' Tommaseo» non si ritrovava nel flusso
    per una lettera sola, e l'indirizzo restava nel documento.

    Il permesso vale **da tutte e due le parti**, e la seconda meta' e' stata
    aggiunta dopo averne pagato il prezzo: anche l'estrazione restituisce
    caratteri che non sa decodificare, e degli URL sopravvivevano tutti per
    quello — l'ago stesso conteneva un ignoto e non combaciava con niente.
    """
    esatta = pagliaio.find(ago, da)
    if esatta >= 0:
        return esatta
    if not any(c in pagliaio for c in IGNOTI) and not any(c in ago for c in IGNOTI):
        return -1
    # **Con un ciclo in Python questa era quadratica**, e su una Gazzetta di
    # ottantotto pagine piena di caratteri non decodificati non finiva piu'.
    # Stesso comportamento, scritto come espressione regolare.
    modello = "".join(
        "." if c in IGNOTI else f"[{re.escape(c)}{re.escape(IGNOTI)}]"
        for c in ago)
    trovato = re.compile(modello).search(pagliaio, da)
    return trovato.start() if trovato else -1


def _dove_stanno(testo_flusso: str,
                 valori: list[tuple[str, str]]) -> list[tuple[int, int, str]]:
    """(inizio, fine, segnaposto) nel testo del flusso, per ogni occorrenza."""
    compatto, da_dove = _senza_spazi(testo_flusso)
    tratti: list[tuple[int, int, str]] = []
    for valore, segnaposto in valori:
        ago = "".join(c for c in valore if not c.isspace())
        if len(ago) < MINIMO_CERCABILE:
            continue
        da = 0
        while True:
            k = _trova(compatto, ago, da)
            if k < 0:
                break
            tratti.append((da_dove[k], da_dove[k + len(ago) - 1] + 1, segnaposto))
            da = k + len(ago)
    tratti.sort()
    puliti: list[tuple[int, int, str]] = []
    for inizio, fine, segnaposto in tratti:
        if puliti and inizio < puliti[-1][1]:
            # Due tratti accavallati vorrebbero dire tagliare gli stessi glifi
            # due volte.
            continue
        puliti.append((inizio, fine, segnaposto))
    return puliti


# ---------------------------------------------------------------------------
# Riscrivere il flusso
# ---------------------------------------------------------------------------


def _istruzione(operandi: list, operatore: str):
    if operatore == "TJ":
        return pikepdf.ContentStreamInstruction(
            [pikepdf.Array(operandi)], pikepdf.Operator("TJ"))
    return pikepdf.ContentStreamInstruction(
        operandi, pikepdf.Operator(operatore))


def _riscrivi(contenitore: _Contenitore, per_istruzione: dict,
              standard: str) -> tuple[int, int]:
    """Rifa' le istruzioni toccate: testa, segnaposto, coda."""
    rimossi = inseriti = 0
    nuove: list = []
    for i, istruzione in enumerate(contenitore.istruzioni):
        if i not in per_istruzione:
            nuove.append(istruzione)
            continue
        lavori = per_istruzione[i]
        op = str(istruzione.operator).encode("latin-1")
        if op in (b"'", b'"'):
            raise NotImplementedError("operatore ' o \"")

        accumulatore: list = []
        for posizione, operando in enumerate(_elementi(istruzione.operands)):
            if not isinstance(operando, pikepdf.String):
                accumulatore.append(operando)
                continue
            tagli = lavori.get(posizione)
            if not tagli:
                accumulatore.append(operando)
                continue

            # **Piu' tagli nello stesso operando sono il caso normale, non
            # l'eccezione.** Una riga di un atto contiene spesso due nomi, e
            # una riga e' un operando solo: rifiutarli mandava nel ripiego un
            # quarto delle pagine di una Gazzetta.
            tagli = sorted(tagli, key=lambda t: min(t[1]))
            grezzo = bytes(operando)
            emissione = tagli[0][0]
            corpo = emissione.corpo
            risorsa_originale = emissione.risorsa_font

            def pezzo(da: int, a: int, _grezzo=grezzo, _em=emissione) -> bytes:
                return b"".join(
                    _grezzo[g.scarto:g.scarto + g.lunghezza]
                    for k, g in enumerate(_em.glifi) if da <= k < a)

            cursore = 0
            for _emissione, indici, segnaposto in tagli:
                primo, ultimo = min(indici), max(indici)
                if primo < cursore:
                    continue
                testa = pezzo(cursore, primo)
                if testa:
                    accumulatore.append(pikepdf.String(testa))
                if accumulatore:
                    nuove.append(_istruzione(accumulatore, "TJ"))
                    accumulatore = []
                if segnaposto:
                    # **Bianco**, perche' dietro ci finisce un rettangolo
                    # verde scuro. Il colore di prima si rimette subito dopo:
                    # senza, il resto della riga proseguirebbe bianco su
                    # bianco e sparirebbe del testo che non doveva sparire.
                    nuove.append(_istruzione(
                        [pikepdf.Name(standard), corpo], "Tf"))
                    nuove.append(_istruzione([1, 1, 1], "rg"))
                    nuove.append(_istruzione(
                        [pikepdf.String(
                            segnaposto.encode("latin-1", "replace"))], "Tj"))
                    if emissione.colore is not None:
                        operandi_colore, operatore_colore, spazio = emissione.colore
                        if spazio is not None:
                            nuove.append(_istruzione(spazio, "cs"))
                        nuove.append(_istruzione(operandi_colore, operatore_colore))
                    else:
                        nuove.append(_istruzione([0], "g"))
                    nuove.append(_istruzione(
                        [pikepdf.Name(risorsa_originale), corpo], "Tf"))
                    inseriti += 1
                rimossi += len(indici)
                cursore = ultimo + 1

            coda = pezzo(cursore, len(emissione.glifi))
            if coda:
                accumulatore.append(pikepdf.String(coda))
        if accumulatore:
            nuove.append(_istruzione(accumulatore, "TJ"))
    contenitore.istruzioni = nuove
    contenitore.modificato = True
    return rimossi, inseriti


def _riquadri_originali(sorgente: Path, numero: int, tratti):
    """I riquadri dei valori sulla pagina **di partenza**.

    Si apre il documento originale perche' e' l'unico posto dove quei
    caratteri esistono ancora: sul risultato sono gia' stati tolti. Serve solo
    per le scansioni con strato OCR, quindi si apre alla bisogna e non a ogni
    documento.

    Se qualcosa va storto si torna a mani vuote e il chiamante rifiuta la
    pagina come faceva prima: meglio nessuna copertura di una copertura
    disegnata su coordinate inventate.
    """
    try:
        documento = pdfium.PdfDocument(str(sorgente))
    except Exception:
        return []
    try:
        if numero >= len(documento):
            return []
        return riquadri_dei_valori(documento[numero], tratti)
    except Exception:
        return []
    finally:
        documento.close()


def riquadri_dei_valori(pagina_pdfium, tratti) -> list[tuple[float, float, float, float, str]]:
    """Dove sta ogni valore sulla pagina, **prima** di toglierlo.

    Si misura sull'originale e non sul risultato, ed e' l'unico ordine che
    funziona: dopo il taglio quei caratteri non ci sono piu', e non c'e' niente
    da misurare. Tutto il resto della pagina non si muove — si tolgono glifi,
    non si ricompone niente — quindi il riquadro misurato prima e' valido dopo.

    Le coordinate sono in **spazio pagina**, quelle che pdfium restituisce
    tenendo gia' conto di ogni trasformazione: e' la ragione per cui il
    rettangolo si puo' disegnare in fondo al flusso senza rifare i conti delle
    matrici.
    """
    testo = pagina_pdfium.get_textpage()
    fuori = []
    try:
        totale = testo.count_chars()
        for inizio, fine, etichetta in tratti:
            sinistra = basso = None
            destra = alto = None
            for k in range(inizio, min(fine, totale)):
                try:
                    l, b, r, t = testo.get_charbox(k)
                except Exception:
                    continue
                if l == r or b == t:
                    continue  # carattere senza area: spazio o a capo
                sinistra = l if sinistra is None else min(sinistra, l)
                basso = b if basso is None else min(basso, b)
                destra = r if destra is None else max(destra, r)
                alto = t if alto is None else max(alto, t)
            if sinistra is None:
                continue
            # **Un valore a cavallo di due righe darebbe un rettangolo alto
            # quanto le due**, coprendo il testo in mezzo. Si riconosce
            # dall'altezza: piu' del doppio della larghezza di un carattere
            # medio vuol dire che ha scavalcato una riga.
            if (alto - basso) > 3.2 * (destra - sinistra) / max(1, fine - inizio):
                continue
            fuori.append((sinistra, basso, destra, alto, etichetta))
    finally:
        testo.close()
    return fuori


def _rettangoli(riquadri) -> bytes:
    """Solo i rettangoli, da mettere **in testa** al flusso della pagina.

    In testa, quindi **dietro** al testo: il segnaposto e' gia' nel flusso,
    scritto in bianco, e qui gli si mette il fondo sotto. E' l'ordine che
    permette di avere tutto insieme -- il rettangolo colorato, il segnaposto
    leggibile, e il testo che si copia **nell'ordine giusto**, perche' il
    segnaposto sta al suo posto nella riga e non in fondo alla pagina.

    Le coordinate sono in spazio pagina e i rettangoli si disegnano prima di
    qualunque `cm`, quindi valgono cosi' come sono.
    """
    r, v, b = COLORE_RETTANGOLO
    pezzi = []
    for riquadro in riquadri:
        x, y, larghezza, altezza = _misure(riquadro)
        pezzi.append(
            f"q {r:.3f} {v:.3f} {b:.3f} rg "
            f"{x:.2f} {y:.2f} {larghezza:.2f} {altezza:.2f} re f Q\n"
        )
    return "".join(pezzi).encode("latin-1", "replace")


def _misure(riquadro) -> tuple[float, float, float, float]:
    """Il rettangolo da disegnare: angolo in basso a sinistra, e i due lati.

    Le coordinate arrivano da `get_charbox`, che misura in **coordinate
    utente**: sono gia' quelle in cui disegna il flusso di contenuto, e non
    vanno spostate. Chi le confronta con un'immagine renderizzata invece deve
    togliere l'origine del ritaglio -- vedi `quota_visibile`.
    """
    sinistra, basso, destra, alto = riquadro[:4]
    return (
        sinistra - MARGINE_RETTANGOLO,
        basso - MARGINE_RETTANGOLO,
        (destra - sinistra) + 2 * MARGINE_RETTANGOLO,
        (alto - basso) + 2 * MARGINE_RETTANGOLO,
    )


def _rettangoli_con_etichetta(riquadri, risorsa: str) -> bytes:
    """I rettangoli da mettere **in coda**, con dentro l'etichetta riscritta.

    Serve alle pagine che dipingono un proprio fondo -- le slide, le carte
    intestate, i riquadri bianchi arrotondati. Li' il rettangolo messo in testa
    finisce **sotto quel fondo** e non arriva a schermo; in coda si vede, ma
    copre il segnaposto che sta nel flusso, che percio' va riscritto sopra.

    Il prezzo di questa riscrittura sta in ETICHETTA_SUL_RIQUADRO_SOPRA.
    """
    r, v, b = COLORE_RETTANGOLO
    pezzi = []
    for riquadro in riquadri:
        x, y, larghezza, altezza = _misure(riquadro)
        pezzi.append(
            f"q {r:.3f} {v:.3f} {b:.3f} rg "
            f"{x:.2f} {y:.2f} {larghezza:.2f} {altezza:.2f} re f "
        )
        etichetta = riquadro[4] if len(riquadro) > 4 else ""
        if ETICHETTA_SUL_RIQUADRO_SOPRA and etichetta:
            # Il corpo lo detta il rettangolo, non il testo intorno: quello lo
            # ha gia' deciso il primo passaggio, e qui si tratta solo di
            # rientrare in uno spazio noto. Si prende il piu' piccolo fra
            # quanto ci sta in altezza e quanto ci sta in larghezza.
            per_altezza = altezza * 0.72
            per_larghezza = larghezza / (len(etichetta) * LARGHEZZA_MEDIA_CARATTERE)
            corpo = max(CORPO_MIN, min(CORPO_MAX, per_altezza, per_larghezza))
            larga = len(etichetta) * corpo * LARGHEZZA_MEDIA_CARATTERE
            testo_x = x + max(0.4, (larghezza - larga) / 2)
            # 0.26 dell'altezza sotto il testo: la linea di base non sta al
            # centro del rettangolo, ci stanno i discendenti sotto.
            testo_y = y + max(0.4, (altezza - corpo * 0.72) / 2)
            sicuro = (
                etichetta.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
            )
            pezzi.append(
                f"BT {risorsa} {corpo:.2f} Tf 1 1 1 rg "
                f"1 0 0 1 {testo_x:.2f} {testo_y:.2f} Tm ({sicuro}) Tj ET "
            )
        pezzi.append("Q\n")
    return "".join(pezzi).encode("latin-1", "replace")


def _e_il_fondo(colore: tuple[int, int, int]) -> bool:
    atteso = [round(c * 255) for c in COLORE_RETTANGOLO]
    return all(abs(colore[i] - atteso[i]) <= TOLLERANZA_COLORE for i in range(3))


def quota_visibile(pagina_pdfium, riquadri) -> float:
    """Quanta parte dei rettangoli arriva davvero a schermo, da 0 a 1.

    **Si guarda la pagina prodotta, non il file che dovrebbe produrla.** Il
    colore puo' esserci nel flusso di contenuto ed essere coperto dal fondo
    della pagina, e in quel caso il documento e' formalmente giusto e
    praticamente muto: chi lo legge non vede che li' e' stato tolto qualcosa.

    Si rende solo il ritaglio di ogni rettangolo, non la pagina intera: su un
    documento di duecento pagine la differenza e' fra qualche millisecondo e
    parecchi secondi.
    """
    # **Le coordinate del testo e quelle del rendering hanno due origini.**
    # `get_charbox` misura in coordinate utente, cioe' dal `/MediaBox`;
    # `render(crop=...)` conta dai bordi del riquadro di ritaglio. Su un
    # documento rifilato le due cose differiscono di tutto il margine, e la
    # misura guardava un pezzo di pagina dove il rettangolo non c'era: su un
    # manuale vero rispondeva «zero» mentre il riquadro era al suo posto, e
    # faceva rifare due pagine che andavano bene.
    ritaglio = pagina_pdfium.get_cropbox()
    origine_x, origine_y = (float(ritaglio[0]), float(ritaglio[1])) if ritaglio else (0.0, 0.0)
    larghezza_pagina, altezza_pagina = pagina_pdfium.get_size()
    trovati = attesi = 0
    for riquadro in riquadri:
        x, y, larghezza, altezza = _misure(riquadro)
        x -= origine_x
        y -= origine_y
        sinistra = max(0.0, x)
        basso = max(0.0, y)
        destra = min(float(larghezza_pagina), x + larghezza)
        alto = min(float(altezza_pagina), y + altezza)
        if destra - sinistra < 1.0 or alto - basso < 1.0:
            continue
        immagine = pagina_pdfium.render(
            scale=1.0,
            crop=(sinistra, basso, larghezza_pagina - destra, altezza_pagina - alto),
        ).to_pil().convert("RGB")
        dati = immagine.tobytes()
        attesi += immagine.width * immagine.height
        for i in range(0, len(dati), 3):
            if _e_il_fondo((dati[i], dati[i + 1], dati[i + 2])):
                trovati += 1
    if attesi == 0:
        return 0.0
    return trovati / attesi


def riquadri_dei_segnaposto(pagina_pdfium) -> list[tuple[float, float, float, float]]:
    """Solo le coordinate, per chi non ha bisogno di sapere che cosa c'e'
    scritto dentro."""
    return [r[:4] for r in segnaposto_sulla_pagina(pagina_pdfium)]


def segnaposto_sulla_pagina(
    pagina_pdfium,
) -> list[tuple[float, float, float, float, str]]:
    """Dove sono finiti i segnaposto sulla pagina gia' redatta, e quali sono.

    Si misura **dopo** il taglio e non prima, ed e' l'unico ordine che
    funziona: il segnaposto e' piu' lungo del valore che ha sostituito, quindi
    occupa un posto diverso: un rettangolo disegnato sulle coordinate del
    valore originale finirebbe accanto, non sotto.

    L'etichetta serve solo alle pagine da rifare «sopra», dove il rettangolo
    copre il segnaposto scritto nel flusso e bisogna riscriverlo.
    """
    testo = pagina_pdfium.get_textpage()
    fuori = []
    try:
        contenuto = testo.get_text_range()
        for m in re.finditer(r"\{\{[A-Z_]+(?:_\d+)?\}\}", contenuto):
            sinistra = basso = destra = alto = None
            for k in range(m.start(), m.end()):
                try:
                    l, b, r_, t = testo.get_charbox(k)
                except Exception:
                    continue
                if l == r_ or b == t:
                    continue
                sinistra = l if sinistra is None else min(sinistra, l)
                basso = b if basso is None else min(basso, b)
                destra = r_ if destra is None else max(destra, r_)
                alto = t if alto is None else max(alto, t)
            if sinistra is None:
                continue
            # Un segnaposto spezzato su due righe darebbe un rettangolo alto
            # quanto le due, coprendo cio' che sta in mezzo.
            if (alto - basso) > 2.5 * (destra - sinistra) / max(1, m.end() - m.start()) * 2:
                continue
            fuori.append((sinistra, basso, destra, alto, m.group(0)))
    finally:
        testo.close()
    return fuori


def _aggiungi_font_standard(pagina) -> str:
    risorse = pagina.get("/Resources")
    if risorse is None:
        pagina["/Resources"] = pikepdf.Dictionary()
        risorse = pagina["/Resources"]
    if "/Font" not in risorse:
        risorse["/Font"] = pikepdf.Dictionary()
    if NOME_RISORSA_STANDARD not in risorse["/Font"]:
        risorse["/Font"][NOME_RISORSA_STANDARD] = pikepdf.Dictionary(
            Type=pikepdf.Name("/Font"),
            Subtype=pikepdf.Name("/Type1"),
            BaseFont=pikepdf.Name("/Helvetica"),
            Encoding=pikepdf.Name("/WinAnsiEncoding"),
        )
    return NOME_RISORSA_STANDARD


def testo_per_pagina(sorgente: Path) -> list[str]:
    """Il testo estratto dal motore PDF, una stringa per pagina."""
    documento = pdfium.PdfDocument(str(sorgente))
    fuori = []
    for pagina in documento:
        pagina_testo = pagina.get_textpage()
        fuori.append(pagina_testo.get_text_range())
        pagina_testo.close()
    documento.close()
    return fuori


def redigi_pdf(sorgente: Path, destinazione: Path,
               opzioni: PrivacyOptions | None = None) -> EsitoRedazione:
    """Scrive in `destinazione` il PDF redatto. Vedi il docstring del modulo."""
    opzioni = opzioni or PrivacyOptions()
    esito = EsitoRedazione()
    per_pagina = testo_per_pagina(sorgente)
    # **Il testo delle annotazioni conta come testo.** Un modulo in cui tutto
    # sta nei campi — nessuna riga disegnata nel flusso — usciva dichiarato
    # «scansione»: qui si guardava solo il testo estratto dalle pagine, e le
    # annotazioni non le contava nessuno. Il file redatto non veniva nemmeno
    # scritto, e la rotta mandava l'utente a cercare l'OCR per un documento
    # che invece si poteva trattare benissimo.
    if not any(t.strip() for t in per_pagina) and not _ha_annotazioni_con_testo(sorgente):
        esito.pagine = len(per_pagina)
        esito.scansione = True
        return esito

    # Le pagine in cui il rettangolo va messo sulle coordinate dei valori
    # **originali** e non su quelle del segnaposto: sono le scansioni con
    # strato OCR, dove il dato vero sta nei pixel sotto (vedi il ramo
    # `MOTIVO_OCR` qui sotto).
    riquadri_ocr: dict[int, list] = {}

    pdf = pikepdf.open(str(sorgente))
    try:
        esito.pagine = len(pdf.pages)
        # Prima delle pagine, perche' non dipende dalle pagine: le proprieta'
        # del documento sono testo che nessun flusso di contenuto contiene.
        esito.metadati_tolti = _redigi_metadati(pdf, opzioni)
        esito.valori_da_togliere += esito.metadati_tolti
        # Le altre due stanze fuori dalle pagine: il sommario e gli allegati.
        # Stessa ragione dei metadati -- testo che nessun flusso contiene -- e
        # stessa collocazione, prima del giro sulle pagine.
        esito.segnalibri_tolti = _redigi_segnalibri(pdf, opzioni)
        esito.valori_da_togliere += esito.segnalibri_tolti
        # Gli allegati **non** entrano in `valori_da_togliere`: quello conta
        # valori di testo, questo conta file interi. Sommarli farebbe un
        # numero che non significa niente.
        esito.allegati_tolti = _togli_allegati(pdf)
        for numero, pagina in enumerate(pdf.pages):
            testo_estratto = per_pagina[numero] if numero < len(per_pagina) else ""

            # Prima del flusso, perche' non dipende dal flusso: una pagina
            # senza una riga di testo puo' avere un campo modulo pieno.
            esito.valori_da_togliere += _redigi_annotazioni(pdf, pagina, opzioni)

            if not testo_estratto.strip() and _pagina_e_una_scansione(pagina):
                _ripiego(esito, numero, MOTIVO_SCANSIONE)
                continue

            tratti_estratti = intervalli_da_togliere(testo_estratto, opzioni)
            valori = [(testo_estratto[a:b], s) for a, b, s in tratti_estratti]
            if not valori:
                continue
            esito.valori_da_togliere += len(valori)

            contenitori: list[_Contenitore] = []
            emissioni: list[Emissione] = []
            pezzi: list[str] = []
            _leggi(pagina, contenitori, emissioni, pezzi, 0)
            testo_flusso = "".join(pezzi)
            if not testo_flusso.strip():
                _ripiego(esito, numero, "nessun testo nel flusso")
                continue

            tratti = _dove_stanno(testo_flusso, valori)
            if not tratti:
                _ripiego(esito, numero, "nessun valore ritrovato nel flusso")
                continue

            if _solo_glifi_invisibili(tratti, emissioni) and _pagina_ha_un_immagine(pagina):
                # **Il dato sta nei pixel, e lo strato OCR dice dove.** Fino
                # alla 1.29.1 qui si rinunciava, ed era onesto: togliere glifi
                # invisibili non toglie niente da un'immagine. Ma le
                # coordinate di quei glifi sono, per come l'OCR le scrive, la
                # mappa delle parole sul foglio: bastano a dipingere il
                # rettangolo **sopra** l'immagine, che e' la redazione vera.
                #
                # Il riquadro si misura sui valori **originali** e non sul
                # segnaposto: e' il segnaposto a essere messo dopo, e puo'
                # essere piu' corto del valore che sostituisce -- un
                # `{{NAME_1}}` al posto di un nome lungo lascerebbe scoperta
                # la coda dei pixel.
                riquadri = _riquadri_originali(sorgente, numero, tratti)
                if riquadri:
                    riquadri_ocr[numero] = riquadri
                    esito.pagine_coperte_sull_ocr.append(numero)
                else:
                    # Senza coordinate non c'e' niente da coprire: si torna
                    # alla risposta di prima, che e' l'unica vera.
                    _ripiego(esito, numero, MOTIVO_OCR)
                    continue

            lavori: dict[int, dict[int, list]] = {}
            fallito = None
            for inizio, fine, segnaposto in tratti:
                toccate = [e for e in emissioni
                           if e.inizio < fine and e.inizio + len(e.glifi) > inizio]
                if not toccate:
                    fallito = "tratto non ricondotto a nessun glifo"
                    break
                primo = True
                for emissione in toccate:
                    indici = [k for k in range(len(emissione.glifi))
                              if inizio <= emissione.inizio + k < fine]
                    if not indici:
                        continue
                    # **Il segnaposto non si infila piu' nel flusso.** Lo si
                    # disegna dopo, a coordinate assolute, sopra un rettangolo:
                    # cosi' la riga non si ricompone (era il prezzo dichiarato
                    # della prima versione), e il segnaposto compare **una**
                    # volta sola quando si copia il testo.
                    lavori.setdefault(emissione.contenitore, {}) \
                          .setdefault(emissione.istruzione, {}) \
                          .setdefault(emissione.elemento, []) \
                          .append((emissione, indici, segnaposto if primo else ""))
                    primo = False
            if fallito:
                _ripiego(esito, numero, fallito)
                continue

            standard = _aggiungi_font_standard(pagina)
            try:
                for indice, per_istruzione in lavori.items():
                    r, i = _riscrivi(contenitori[indice], per_istruzione, standard)
                    esito.glifi_rimossi += r
                    esito.segnaposto_inseriti += i
            except NotImplementedError as errore:
                _ripiego(esito, numero, str(errore))
                continue

            for contenitore in contenitori:
                if not contenitore.modificato:
                    continue
                grezzo = pikepdf.unparse_content_stream(contenitore.istruzioni)
                if "/Contents" in contenitore.oggetto:
                    contenitore.oggetto.Contents = pdf.make_stream(grezzo)
                else:  # noqa: RET505
                    contenitore.oggetto.write(grezzo)

        pdf.save(str(destinazione))
    finally:
        pdf.close()

    # **Un documento fatto di sole scansioni e' una scansione**, anche quando
    # ha uno strato OCR che rende estraibile il testo. Senza questa riga il
    # rifiuto — che esiste da sempre e che le rotte traducono in un messaggio
    # chiaro — sarebbe scavalcato dal solo fatto che qualcuno ha passato un
    # OCR sul PDF prima di noi: il documento uscirebbe «redatto» con l'elenco
    # delle pagine non trattate lungo quanto il documento intero.
    if (esito.pagine
            and len(esito.pagine_in_ripiego) == esito.pagine
            and all(m in (MOTIVO_SCANSIONE, MOTIVO_OCR)
                    for m in esito.motivi_ripiego)):
        esito.scansione = True

    _dipingi_rettangoli(destinazione, esito, riquadri_ocr)
    return esito


def _dipingi_rettangoli(documento: Path, esito=None, riquadri_ocr=None) -> None:
    """Il secondo passaggio: il fondo colorato sotto i segnaposto.

    **Deve venire dopo il taglio, e in un file gia' scritto.** Il segnaposto e'
    piu' lungo del valore che ha sostituito, quindi occupa un posto diverso:
    un rettangolo disegnato sulle coordinate del valore originale finirebbe
    accanto, non sotto. Le coordinate giuste esistono solo quando il documento
    redatto esiste.

    Se qualcosa va storto **non si tocca il file**: il documento redatto e' gia'
    valido e completo, e il fondo colorato e' una comodita' per chi lo legge.
    Perderlo e' un peccato; consegnare un file rotto no.
    """
    try:
        letto = pdfium.PdfDocument(str(documento))
        per_pagina = []
        try:
            for pagina in letto:
                per_pagina.append(segnaposto_sulla_pagina(pagina))
        finally:
            letto.close()
        # Sulle scansioni con strato OCR ai riquadri del segnaposto si
        # aggiungono quelli dei **valori originali**, misurati sul documento di
        # partenza: li' sotto ci sono i pixel del dato, e il segnaposto da solo
        # non li copre per intero. Si sommano invece di sostituirli perche' non
        # sono alternativi -- uno dice dove si legge il segnaposto, l'altro
        # dove stava il dato -- e coprire un po' di piu' e' l'unico errore
        # accettabile qui.
        for numero, riquadri in (riquadri_ocr or {}).items():
            if numero < len(per_pagina):
                per_pagina[numero] = list(per_pagina[numero]) + list(riquadri)
        if not any(per_pagina):
            return

        pdf = pikepdf.open(str(documento), allow_overwriting_input=True)
        try:
            for numero, pagina in enumerate(pdf.pages):
                if numero < len(per_pagina) and per_pagina[numero]:
                    # `prepend=True`: **dietro** al testo. In coda coprirebbe
                    # il segnaposto che deve incorniciare.
                    pagina.contents_add(_rettangoli(per_pagina[numero]),
                                        prepend=True)
            pdf.save(str(documento))
        finally:
            pdf.close()
    except Exception:
        return

    _rifai_le_pagine_coperte(documento, per_pagina, esito)


def _rifai_le_pagine_coperte(documento: Path, per_pagina, esito=None) -> None:
    """Guarda le pagine appena scritte, e rifa' quelle dove non si vede niente.

    Il rettangolo va **dietro** al testo, e per farlo si mette in testa al
    flusso della pagina. Su una pagina che dipinge un proprio fondo -- una
    slide, una carta intestata, un riquadro bianco arrotondato -- quel fondo
    viene disegnato dopo, e copre il rettangolo. Misurato su dodici PDF veri:
    due, entrambi impaginati come slide. Il documento e' formalmente a posto e
    praticamente muto, perche' il segnaposto e' scritto in bianco e conta sul
    rettangolo che non c'e' piu': **non si vede niente di niente**, ne' che un
    dato e' stato tolto ne' quale.

    Non lo si indovina dalla struttura del PDF, che ha mille modi di dipingere
    un fondo: si **rende la pagina prodotta e si guarda**. E' l'unico controllo
    che risponde alla domanda vera, cioe' «chi apre questo file lo vede?».

    Come il primo passaggio: se qualcosa va storto il file resta com'e'.
    """
    try:
        letto = pdfium.PdfDocument(str(documento))
        try:
            da_rifare = [
                numero
                for numero, riquadri in enumerate(per_pagina)
                if riquadri
                and numero < len(letto)
                and quota_visibile(letto[numero], riquadri) < QUOTA_MINIMA_VISIBILE
            ]
        finally:
            letto.close()
        if not da_rifare:
            return

        pdf = pikepdf.open(str(documento), allow_overwriting_input=True)
        rifatte = []
        try:
            for numero in da_rifare:
                pagina = pdf.pages[numero]
                if not _avvolgi_in_stato_iniziale(pagina):
                    # Flusso sbilanciato: avvolgerlo lo romperebbe, e un
                    # documento rotto e' molto peggio di un riquadro che non
                    # si vede. Resta com'e', e lo dice l'esito.
                    continue
                risorsa = _aggiungi_font_standard(pagina)
                pagina.contents_add(
                    b"Q\n" + _rettangoli_con_etichetta(per_pagina[numero], risorsa),
                    prepend=False,
                )
                rifatte.append(numero)
            pdf.save(str(documento))
        finally:
            pdf.close()
    except Exception:
        return

    _conta_cosa_si_vede_davvero(documento, per_pagina, da_rifare, rifatte, esito)


def _avvolgi_in_stato_iniziale(pagina) -> bool:
    """Mette il contenuto della pagina dentro `q`/`Q`. Falso se non si puo'.

    **Senza questo, cio' che si aggiunge in coda finisce da un'altra parte.**
    Un PDF prodotto da Word o dal browser comincia quasi sempre con un `cm` al
    livello piu' esterno -- tipicamente `0.75 0 0 -0.75 0 altezza`, che porta i
    96 dpi ai 72 del PDF e rovescia l'asse Y. Quel `cm` non sta dentro nessun
    `q`, quindi vale fino alla fine del flusso: le coordinate misurate sulla
    pagina, aggiunte dopo, vengono trasformate una seconda volta.
    Misurato su un curriculum vero: il riquadro chiesto a (21, 771) e'
    comparso a (15,75, 263,6), cioe' a meta' pagina e specchiato.

    Avvolgere il contenuto in `q`/`Q` riporta lo stato a quello iniziale prima
    di cio' che aggiungiamo: `q` va in testa, e la `Q` la mette chi accoda.

    Si rifiuta se il flusso non e' bilanciato -- piu' `Q` che `q` a un certo
    punto, oppure `q` aperte alla fine. Li' la `q` in testa verrebbe chiusa da
    una `Q` del documento, e la nostra `Q` ne chiuderebbe una di troppo.
    """
    profondita = 0
    for istruzione in pikepdf.parse_content_stream(pagina):
        operatore = str(istruzione.operator)
        if operatore == "q":
            profondita += 1
        elif operatore == "Q":
            profondita -= 1
            if profondita < 0:
                return False
    if profondita != 0:
        return False
    pagina.contents_add(b"q\n", prepend=True)
    return True


def _conta_cosa_si_vede_davvero(documento: Path, per_pagina, da_rifare,
                                rifatte, esito) -> None:
    """Guarda **di nuovo**, dopo aver rifatto: si vede o no?

    Il primo sguardo dice quali pagine hanno un problema; questo dice se il
    rimedio ha funzionato. Servono tutti e due, e il motivo e' costato caro:
    la prima versione di questo passaggio disegnava i rettangoli in coda senza
    accorgersi della trasformazione di pagina, li mandava a meta' foglio, e
    dichiarava «pagina rifatta». Il rapporto diceva di si' e il documento
    diceva di no.

    Cio' che resta invisibile finisce in `pagine_senza_riquadro`, dichiarato.
    Un rimedio che non ha funzionato taciuto e' peggio del difetto.
    """
    if esito is None:
        return
    try:
        letto = pdfium.PdfDocument(str(documento))
        try:
            esito.pagine_riquadro_sopra = [
                n for n in rifatte
                if quota_visibile(letto[n], per_pagina[n]) >= QUOTA_MINIMA_VISIBILE
            ]
            esito.pagine_senza_riquadro = [
                n for n in da_rifare
                if n not in esito.pagine_riquadro_sopra
            ]
        finally:
            letto.close()
    except Exception:
        return


def _ripiego(esito: EsitoRedazione, pagina: int, motivo: str) -> None:
    esito.pagine_in_ripiego.append(pagina)
    esito.motivi_ripiego.append(motivo)


#: Le chiavi di testo di un'annotazione. `/Contents` e' la nota che si apre
#: cliccandola, `/RC` la sua versione formattata, `/V` il valore di un campo
#: modulo. Sono **stringhe**, non flussi di contenuto: non passano dalla
#: chirurgia dei glifi, ed e' il motivo per cui restavano intere.
#:
#: Le altre tre le ha aggiunte l'audit del 6 settembre 2026, e hanno tutte
#: dentro il valore vero:
#:
#: * `/DV` e' il valore predefinito, quello a cui il campo torna col comando
#:   «azzera». In un modulo precompilato e' una seconda copia del dato;
#: * `/TU` e' il suggerimento che il lettore mostra passandoci sopra il mouse.
#:   Nei moduli veri contiene spesso un esempio gia' compilato;
#: * `/Opt` e' l'elenco delle scelte di una tendina, che in un modulo uscito da
#:   un gestionale sono i nomi dei clienti. E' l'unica **array**, non stringa.
_CHIAVI_TESTO_ANNOTAZIONE = ("/Contents", "/RC", "/V", "/DV", "/TU")

#: Le chiavi il cui valore e' un elenco di stringhe, non una stringa sola.
_CHIAVI_ELENCO_ANNOTAZIONE = ("/Opt",)


def _ha_annotazioni_con_testo(sorgente: Path) -> bool:
    """C'e' del testo dentro le annotazioni, anche se le pagine sono mute?

    Distingue un **modulo** (tutto nei campi, redigibile) da una **scansione**
    (pixel, e non c'e' niente da togliere). Le due meritano risposte opposte, e
    finora ricevevano la stessa.
    """
    try:
        with pikepdf.open(str(sorgente)) as pdf:
            for pagina in pdf.pages:
                annotazioni = pagina.get("/Annots")
                if not isinstance(annotazioni, pikepdf.Array):
                    continue
                for annotazione in annotazioni:
                    if not isinstance(annotazione, pikepdf.Dictionary):
                        continue
                    for chiave in _CHIAVI_TESTO_ANNOTAZIONE:
                        valore = annotazione.get(chiave)
                        if isinstance(valore, pikepdf.String) and str(valore).strip():
                            return True
                    genitore = annotazione.get("/Parent")
                    if isinstance(genitore, pikepdf.Dictionary):
                        for chiave in _CHIAVI_TESTO_ANNOTAZIONE:
                            valore = genitore.get(chiave)
                            if isinstance(valore, pikepdf.String) and str(valore).strip():
                                return True
    except Exception:
        return False
    return False


def _stringa_redatta(voce, opzioni: PrivacyOptions):
    """Una voce di elenco, redatta. Torna (voce, quanti valori tolti).

    Cio' che non e' una stringa torna com'era: dentro un `/Opt` puo' esserci di
    tutto, e trasformarlo sarebbe rompere il documento per prudenza.
    """
    if not isinstance(voce, pikepdf.String):
        return voce, 0
    testo = str(voce)
    if not testo.strip():
        return voce, 0
    redatto, rapporto = apply_privacy_filter(testo, opzioni)
    if rapporto.total == 0:
        return voce, 0
    return pikepdf.String(redatto), rapporto.total


def _redigi_annotazioni(pdf, pagina, opzioni: PrivacyOptions) -> int:
    """Toglie i dati dalle annotazioni e dai campi modulo di una pagina.

    Il testo di una nota gialla e il valore di un campo compilato **non
    stanno nel flusso della pagina**: stanno in stringhe appese
    all'annotazione. La chirurgia sui glifi non li vedeva, il conteggio non
    li contava, e il file usciva chiamandosi `-redatto.pdf` con dentro un
    codice fiscale leggibile in chiaro aprendo il PDF con un editor di testo.

    Era un limite dichiarato — nel docstring di questo modulo. Finche' la
    redazione si faceva da riga di comando poteva bastare; da quando c'e' un
    pulsante nell'interfaccia non basta piu', perche' li' l'unica frase che
    si legge e' «Tutte le pagine sono state trattate».

    Due mosse, e la seconda e' quella che rende vera la prima:

    1. la stringa si redige come qualunque altro testo;
    2. **l'aspetto memorizzato si butta via.** Un campo modulo porta con se'
       un disegno gia' pronto di come si vede (`/AP`): cambiare il valore
       senza toccarlo lascerebbe sullo schermo il nome di prima, con il
       valore nuovo nascosto sotto. Tolto quello, chi apre il file lo
       ridisegna dal valore redatto — e i lettori che non lo ridisegnano
       mostrano un campo vuoto, che e' l'errore dalla parte giusta.
    """
    annotazioni = pagina.get("/Annots")
    if annotazioni is None or not isinstance(annotazioni, pikepdf.Array):
        return 0

    tolti = 0
    rigenerare = False
    for annotazione in annotazioni:
        # Un PDF malformato puo' avere qualunque cosa qui dentro. Si salta
        # invece di fermarsi: una voce storta non deve far uscire il
        # documento **non** redatto, che sarebbe l'errore dalla parte
        # sbagliata.
        if not isinstance(annotazione, pikepdf.Dictionary):
            continue

        # Il valore puo' stare sul campo padre invece che sul widget: sono lo
        # stesso dato scritto in due posti, e guardarne uno solo vuol dire
        # ripulire quello sbagliato.
        #
        # **Tutta la catena, non il primo genitore.** In un modulo con i campi
        # raggruppati il `/Parent` ha a sua volta un `/Parent`, e il valore sta
        # due livelli sopra: guardandone uno solo restava dov'era. Il limite di
        # profondita' e' contro i documenti storti con una catena circolare,
        # non contro i moduli veri, che di livelli ne hanno due o tre.
        oggetti = [annotazione]
        genitore = annotazione.get("/Parent")
        for _ in range(8):
            if not isinstance(genitore, pikepdf.Dictionary):
                break
            if any(g is genitore for g in oggetti):
                break  # catena circolare: si e' gia' passati di qui
            oggetti.append(genitore)
            genitore = genitore.get("/Parent")

        toccata = False
        for oggetto in oggetti:
            for chiave in _CHIAVI_TESTO_ANNOTAZIONE:
                valore = oggetto.get(chiave)
                if valore is None or not isinstance(valore, pikepdf.String):
                    continue
                testo = str(valore)
                if not testo.strip():
                    continue
                redatto, rapporto = apply_privacy_filter(testo, opzioni)
                if rapporto.total == 0:
                    continue
                oggetto[chiave] = pikepdf.String(redatto)
                tolti += rapporto.total
                toccata = True

            for chiave in _CHIAVI_ELENCO_ANNOTAZIONE:
                elenco = oggetto.get(chiave)
                if not isinstance(elenco, pikepdf.Array):
                    continue
                nuovo = []
                cambiato = False
                for voce in elenco:
                    # Una tendina puo' avere coppie [valore, etichetta]: si
                    # scende di un livello, o si ripulisce solo meta' elenco.
                    if isinstance(voce, pikepdf.Array):
                        dentro = []
                        for pezzo in voce:
                            pulito, quanti = _stringa_redatta(pezzo, opzioni)
                            dentro.append(pulito)
                            if quanti:
                                tolti += quanti
                                cambiato = True
                        nuovo.append(pikepdf.Array(dentro))
                        continue
                    pulito, quanti = _stringa_redatta(voce, opzioni)
                    nuovo.append(pulito)
                    if quanti:
                        tolti += quanti
                        cambiato = True
                if cambiato:
                    oggetto[chiave] = pikepdf.Array(nuovo)
                    toccata = True

        if toccata:
            if "/AP" in annotazione:
                del annotazione["/AP"]
            rigenerare = True

    if rigenerare:
        modulo = pdf.Root.get("/AcroForm")
        if modulo is not None:
            modulo["/NeedAppearances"] = True
    return tolti


#: Le chiavi del dizionario delle informazioni del documento che contengono
#: testo scritto da una persona. `/Producer` e `/CreationDate` non ci sono di
#: proposito: dicono con che programma e quando, non di chi.
_CHIAVI_TESTO_DOCINFO = ("/Title", "/Author", "/Subject", "/Keywords", "/Creator")


def _redigi_metadati(pdf, opzioni: PrivacyOptions) -> int:
    """Le proprieta' del documento sono testo come tutto il resto.

    E' la stessa classe del difetto delle annotazioni chiuso nella 1.24.0, e
    per la stessa ragione: **questo testo non sta nel flusso di contenuto**,
    quindi la chirurgia dei glifi non lo tocca. Un PDF con
    `/Subject: CF RSSMRA85M01H501Z` usciva da un file chiamato «-redatto.pdf»
    con il codice fiscale intero, leggibile in due click nelle proprieta' del
    documento di qualunque lettore.

    Perche' l'XMP si **butta** invece di riscriverlo
    ------------------------------------------------

    Il blocco XMP e' XML, e riscriverne il contenuto a colpi di sostituzione
    testuale vuol dire prima o poi produrre XML rotto: i valori stanno dentro i
    tag ma i nomi delle persone compaiono anche in `dc:creator` insieme a
    strutture RDF, e un segnaposto messo nel posto sbagliato rompe il file per
    tutti i lettori. Il blocco inoltre **duplica** il dizionario delle
    informazioni: buttarlo non toglie niente al documento redatto, e lasciarlo
    a meta' sarebbe la sola opzione davvero pericolosa.

    Si butta **solo se conteneva qualcosa**: un XMP innocuo resta dov'e', e un
    documento senza dati personali nei metadati esce identico a com'e' entrato.
    """
    tolti = 0
    for chiave in _CHIAVI_TESTO_DOCINFO:
        try:
            valore = pdf.docinfo.get(chiave)
        except Exception:
            continue
        if valore is None or not isinstance(valore, pikepdf.String):
            continue
        testo = str(valore)
        if not testo.strip():
            continue
        redatto, rapporto = apply_privacy_filter(testo, opzioni)
        if rapporto.total == 0:
            continue
        pdf.docinfo[chiave] = pikepdf.String(redatto)
        tolti += rapporto.total

    metadati = pdf.Root.get("/Metadata")
    if metadati is not None:
        try:
            grezzo = bytes(metadati.read_bytes()).decode("utf-8", "replace")
        except Exception:
            grezzo = ""
        if grezzo:
            _, rapporto = apply_privacy_filter(grezzo, opzioni)
            if rapporto.total:
                del pdf.Root["/Metadata"]
                tolti += rapporto.total
    return tolti


def _voci_del_sommario(voci):
    """Tutte le voci dell'indice, anche quelle annidate.

    Un sommario e' un albero: fermarsi al primo livello vorrebbe dire redigere
    i capitoli e lasciare in chiaro i paragrafi, che e' proprio dove stanno i
    titoli specifici -- «Posizione di Mario Rossi» sta sotto «Allegati», non
    accanto.
    """
    for voce in voci:
        yield voce
        yield from _voci_del_sommario(voce.children)


def _redigi_segnalibri(pdf, opzioni: PrivacyOptions) -> int:
    """I titoli dei segnalibri sono testo come le proprieta' del documento.

    Il sommario si apre con un click in qualunque lettore, e prima usciva
    intero: un PDF con un segnalibro «Scheda di RSSMRA85M01H501Z» consegnava
    il codice fiscale a chi non apriva nemmeno una pagina.

    Si redige e **non** si cancella. Buttare via il sommario chiuderebbe il
    buco e romperebbe la navigazione di ogni documento lungo, che e' un
    prezzo che nessuno ha chiesto di pagare: i titoli sono stringhe corte,
    esattamente come titolo e oggetto del documento, e lo stesso motore che
    tratta quelli tratta questi.
    """
    try:
        sommario = pdf.open_outline()
    except Exception:
        return 0
    tolti = 0
    try:
        with sommario as indice:
            for voce in _voci_del_sommario(indice.root):
                titolo = voce.title
                if not isinstance(titolo, str) or not titolo.strip():
                    continue
                redatto, rapporto = apply_privacy_filter(titolo, opzioni)
                if rapporto.total == 0:
                    continue
                voce.title = redatto
                tolti += rapporto.total
    except Exception:
        return tolti
    return tolti


def _togli_allegati(pdf) -> int:
    """Gli allegati escono dal documento, senza guardarci dentro.

    Un allegato **e' un altro documento**, non un pezzo di questo: puo' essere
    un `.docx`, un `.jpg`, un PDF a sua volta. Redigerlo vorrebbe dire far
    girare tutto il motore dentro un file che in generale non sappiamo aprire,
    e il ripiego ovvio -- «guardo dentro solo se e' testo» -- lascerebbe
    passare intero proprio il caso peggiore, cioe' l'allegato binario.

    Quindi si tolgono tutti e si contano. Il PDF che esce ha un pezzo in meno
    di quello che e' entrato, ed e' una perdita vera: la si dichiara nel
    rapporto invece di nasconderla, perche' l'alternativa era consegnare un
    file chiamato «-redatto.pdf» con dentro un secondo documento intatto.
    """
    try:
        nomi = list(pdf.attachments)
    except Exception:
        return 0
    tolti = 0
    for nome in nomi:
        try:
            del pdf.attachments[nome]
            tolti += 1
        except Exception:
            continue
    return tolti


def _pagina_e_una_scansione(pagina) -> bool:
    """Pagina senza testo: e' una scansione o e' bianca?

    La differenza conta, perche' le due meritano risposte opposte. Una pagina
    bianca non ha niente da togliere e va bene cosi'. Una pagina scansionata
    dentro un documento digitale **non e' stata redatta**, e finora usciva
    contata fra quelle trattate: stessa strada nel codice, `continue`.

    Il rifiuto esplicito delle scansioni guardava il documento intero, quindi
    scattava solo se *tutte* le pagine erano immagini. Una scansione infilata
    in mezzo a pagine digitali — il caso di ogni allegato firmato a mano —
    non lo faceva scattare.

    Si distinguono per la presenza di un'immagine, che e' il motivo per cui
    non c'e' testo.
    """
    return _pagina_ha_un_immagine(pagina)


def _solo_glifi_invisibili(tratti, emissioni: list[Emissione]) -> bool:
    """Tutto cio' che c'e' da togliere in questa pagina e' testo che non si vede.

    E' il segnale della **scansione gia' passata dall'OCR**, che e' il caso in
    cui questo modulo poteva fare il danno peggiore che sa fare: togliere i
    glifi invisibili — l'unica delle due copie del dato che non si legge — e
    dichiarare la pagina trattata mentre il nome resta a schermo, dentro
    l'immagine. Misurato prima della correzione: due segnaposto inseriti,
    `pagine_in_ripiego` vuoto, e il codice fiscale ancora visibile.

    Non basta da sola a decidere: la usa `redigi_pdf` **in and** con la
    presenza di un'immagine. Un testo invisibile su una pagina senza immagini
    non e' una scansione, e li' togliere i glifi e' esattamente il lavoro
    giusto — il dato e' nel file e ne esce.
    """
    if not tratti:
        return False
    visto = False
    for inizio, fine, _segnaposto in tratti:
        for emissione in emissioni:
            if emissione.inizio < fine and emissione.inizio + len(emissione.glifi) > inizio:
                if not emissione.invisibile:
                    return False
                visto = True
    return visto


def _pagina_ha_un_immagine(pagina) -> bool:
    """C'e' un'immagine fra le risorse della pagina?

    Da sola non vuol dire niente — meta' della carta intestata ha un logo — e
    infatti non decide mai da sola: chi la chiama la mette **in and** con
    un'altra condizione (nessun testo, oppure testo tutto invisibile).
    """
    risorse = pagina.get("/Resources")
    if risorse is None:
        return False
    xobject = risorse.get("/XObject")
    if xobject is None:
        return False
    try:
        return any(
            oggetto.get("/Subtype") == pikepdf.Name("/Image")
            for oggetto in xobject.values()
        )
    except Exception:
        return False


def valore_ancora_presente(valore: str, testo: str) -> bool:
    """Il valore compare ancora, **come parola intera**?

    Cercarlo come sottostringa a spazi tolti sembrava piu' severo ed era solo
    piu' rumoroso: «URSO» si ritrova dentro «concorso», «Ele» dentro «elenco».
    Erano sopravvissuti dichiarati che non erano mai stati la'.

    Gli spazi restano flessibili — nel PDF non sono caratteri e un valore puo'
    uscire spezzato — ma ai due estremi ci vuole un confine di parola.
    """
    caratteri = [c for c in valore if not c.isspace()]
    if len(caratteri) < MINIMO_CERCABILE:
        return False
    modello = r"(?<!\w)" + r"\s*".join(re.escape(c) for c in caratteri) + r"(?!\w)"
    return re.search(modello, testo) is not None


def _annotazioni_per_pagina(sorgente: Path) -> list[str]:
    """Il testo delle note e dei campi modulo, una riga per pagina.

    Gemello di `testo_per_pagina` per la meta' del documento che non sta nel
    flusso. Se il file non si apre torna righe vuote invece di sollevare: la
    verifica deve poter dire «non ho trovato niente», non morire.
    """
    try:
        with pikepdf.open(str(sorgente)) as pdf:
            righe = []
            for pagina in pdf.pages:
                annotazioni = pagina.get("/Annots")
                pezzi: list[str] = []
                if isinstance(annotazioni, pikepdf.Array):
                    for annotazione in annotazioni:
                        if not isinstance(annotazione, pikepdf.Dictionary):
                            continue
                        for chiave in _CHIAVI_TESTO_ANNOTAZIONE:
                            valore = annotazione.get(chiave)
                            if isinstance(valore, pikepdf.String):
                                pezzi.append(str(valore))
                righe.append("\n".join(pezzi))
            return righe
    except Exception:
        return []


def _fuori_dalle_pagine_come_testo(percorso: Path) -> str:
    """Tutto il testo del documento che **non sta in nessuna pagina**.

    Le proprieta' e l'XMP, i titoli dei segnalibri, il contenuto degli
    allegati leggibili come testo.

    Serve alla verifica, e ogni voce di questo elenco e' arrivata dopo un
    difetto: senza i metadati un codice fiscale rimasto nell'oggetto del
    documento usciva **verde**; senza segnalibri e allegati usciva verde uno
    rimasto nel sommario o dentro un file appeso. La verifica guardava flusso
    e annotazioni, cioe' posti in cui quel dato non era mai stato.

    Gli allegati si leggono **con la migliore approssimazione possibile**: un
    `.docx` o un `.jpg` qui diventano byte illeggibili e la ricerca del valore
    non li trova. Non e' un buco della verifica, perche' `_togli_allegati` li
    ha gia' rimossi tutti a monte: questa lettura serve a dire di no se un
    domani quella rimozione smettesse di funzionare, ed e' l'unico caso in cui
    la rete di sicurezza e' piu' debole della correzione che sorveglia. Sta
    scritto qui perche' chi legge «verifica verde» sappia cosa ha guardato.
    """
    try:
        with pikepdf.open(str(percorso)) as pdf:
            pezzi = []
            for chiave in _CHIAVI_TESTO_DOCINFO:
                valore = pdf.docinfo.get(chiave)
                if isinstance(valore, pikepdf.String):
                    pezzi.append(str(valore))
            metadati = pdf.Root.get("/Metadata")
            if metadati is not None:
                try:
                    pezzi.append(
                        bytes(metadati.read_bytes()).decode("utf-8", "replace"))
                except Exception:
                    pass
            try:
                with pdf.open_outline() as indice:
                    pezzi.extend(voce.title for voce in _voci_del_sommario(indice.root)
                                 if isinstance(voce.title, str))
            except Exception:
                pass
            try:
                for nome, spec in pdf.attachments.items():
                    pezzi.append(str(nome))
                    try:
                        pezzi.append(bytes(spec.get_file().read_bytes())
                                     .decode("utf-8", "replace"))
                    except Exception:
                        continue
            except Exception:
                pass
            return "\n".join(pezzi)
    except Exception:
        return ""


def verifica_redazione(sorgente: Path, destinazione: Path,
                       opzioni: PrivacyOptions | None = None) -> dict:
    """**I valori veri ci sono ancora, si' o no.** Un conto non e' una prova.

    Due precisazioni pagate care.

    La prima: non si riesegue il motore sul documento redatto contando cosa
    trova. Sembra la stessa domanda e non lo e' — sul testo redatto il motore
    incontra i **segnaposto gia' inseriti**, e diverse regole si agganciano di
    proposito a un segnaposto per prendere cio' che gli sta accanto. Quelle
    rilevazioni finivano nel conto come sopravvissute, e sedici su diciotto lo
    erano per quel motivo soltanto.

    La seconda: il confronto e' **pagina contro pagina**. Cercare il valore in
    tutto il documento sembrava piu' severo ed era sbagliato: un cognome che il
    motore toglie dove e' una firma e lascia dove e' una voce d'elenco —
    giustamente — veniva ritrovato nella seconda posizione e faceva dichiarare
    sopravvissuta la prima, che era stata tolta.

    `dichiarati_dal_motore` e' l'unico numero qui dentro che questo modulo non
    calcola: senza, la verifica userebbe la stessa funzione con cui si taglia,
    e se quella individuasse meta' dei valori taglierebbe meta' e ne cercherebbe
    meta', uscendo verde senza guardare niente.
    """
    opzioni = opzioni or PrivacyOptions()
    # Il testo della pagina **e** quello delle annotazioni, che sta altrove e
    # per questo era invisibile: `testo_per_pagina` legge il flusso, e una
    # verifica che guarda solo li' non puo' dire di no su una nota o su un
    # campo modulo. E' la classe di difetto che questa riga esiste per far
    # fallire, non per far passare.
    #
    # Non `zip`: `zip` si ferma alla lista piu' corta, quindi se le
    # annotazioni non si leggessero la verifica si ridurrebbe a zero pagine
    # e uscirebbe verde senza aver guardato niente.
    # Cio' che sta fuori dalle pagine -- proprieta', XMP, segnalibri, allegati
    # -- va in coda come se fosse **una pagina in piu'**, e non dentro le
    # pagine vere: appartiene al documento, non a un foglio, e sommarlo a
    # ciascuna pagina lo farebbe contare tante volte quante sono. La coda
    # tiene allineati gli indici delle due liste, che e' cio' su cui regge il
    # confronto pagina contro pagina.
    def _unite(percorso: Path) -> list[str]:
        flusso = testo_per_pagina(percorso)
        note = _annotazioni_per_pagina(percorso)
        pagine = [t + "\n" + (note[i] if i < len(note) else "")
                  for i, t in enumerate(flusso)]
        return pagine + [_fuori_dalle_pagine_come_testo(percorso)]

    prima = _unite(sorgente)
    dopo = _unite(destinazione)

    dichiarati = individuati = 0
    rimasti: list[str] = []
    # **Su quali pagine**, non solo quanti. Chi chiama deve poter distinguere
    # un valore rimasto su una pagina che il rapporto dichiara **non trattata**
    # — dove l'utente e' gia' avvisato e il file si consegna lo stesso — da uno
    # rimasto su una pagina dichiarata a posto, che e' il caso in cui il
    # prodotto direbbe una cosa non vera.
    pagine_con_superstiti: set[int] = set()
    for numero, testo in enumerate(prima):
        _, rapporto = apply_privacy_filter(testo, opzioni)
        dichiarati += rapporto.total
        stessa_pagina = dopo[numero] if numero < len(dopo) else ""
        for a, b, _s in intervalli_da_togliere(testo, opzioni):
            individuati += 1
            if valore_ancora_presente(testo[a:b], stessa_pagina):
                rimasti.append(testo[a:b])
                pagine_con_superstiti.add(numero)
    return {
        "dichiarati_dal_motore": dichiarati,
        "individuati_nel_testo": individuati,
        "persi_prima_di_tagliare": dichiarati - individuati,
        "sopravvissuti": len(rimasti),
        "esempi": rimasti[:5],
        # L'ultimo indice e' la «pagina» dei metadati (vedi `_unite`): non e'
        # un foglio, e non puo' mai essere in ripiego. Un superstite li' vale
        # come uno su una pagina dichiarata trattata.
        "pagine_con_superstiti": sorted(pagine_con_superstiti),
    }
