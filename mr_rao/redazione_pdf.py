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

  * **le scansioni senza strato OCR**. Un PDF senza testo estraibile qui non
    si tocca: non c'e' nessun glifo da togliere e nessuna mappa di dove stiano
    le parole, e disegnarci sopra dei rettangoli sarebbe esattamente la
    redazione finta che questo modulo esiste per evitare;
  * **le pagine fatte di un'immagine con poco testo sopra** — un pie' di
    pagina, un timbro. Il testo si legge, l'immagine no: la pagina si
    dichiara non trattata (`MOTIVO_IMMAGINE`);
  * le scansioni con strato OCR la cui immagine **non si riesce a riscrivere**
    (JBIG2, immagini in linea, JPEG in quadricromia): senza poter togliere i
    pixel la pagina si dichiara, non si copre;
  * gli operatori `'` e `"`, che mostrano il testo **e** vanno a capo:
    spezzarli richiederebbe di replicare l'a capo. Sono rari, e quando
    compaiono la pagina finisce nel ripiego invece di essere tagliata a meta'.

Cosa fa oltre il flusso
-----------------------

Il dato non sta solo nei glifi. Si redigono anche le **annotazioni** e i
campi modulo, le **proprieta'** del documento, i titoli dei **segnalibri** e
il **testo di struttura**; si tolgono gli **allegati** e le **miniature di
pagina**. E sulle scansioni con strato OCR si azzerano i **pixel dentro
l'immagine**, sulle coordinate che quello strato dichiara: il rettangolo
disegnato sopra e' un segno per chi legge, non la redazione. Vale per i due
modi in cui un OCR lascia il suo testo: invisibile sopra l'immagine, oppure
scritto normale e poi coperto da lei.

Il ripiego non e' implementato qui: `EsitoRedazione.pagine_in_ripiego` dice
quali pagine non sono state trattate, e sta al chiamante decidere cosa farne.
Una pagina che finisce li' **non e' stata redatta**, e chiamarla redatta
sarebbe il modo peggiore di sbagliare.
"""
from __future__ import annotations

import ctypes
import io
import math
import re
import zlib
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
#: Il terzo: la pagina e' un'immagine con sopra **poco** testo vero -- un pie'
#: di pagina, un timbro, un numero di protocollo. Il testo c'e', quindi non e'
#: una «scansione» nel senso di `MOTIVO_SCANSIONE`; ma cio' che la pagina dice
#: sta nei pixel, e i pixel qui non li legge nessuno.
MOTIVO_IMMAGINE = ("immagine a tutta pagina con poco testo: "
                   "il contenuto dell'immagine non e' stato esaminato")

#: Quanta parte della pagina deve occupare un'immagine perche' la pagina **sia**
#: quell'immagine. Meta' e non «tutta»: una scansione incollata in un documento
#: di testo ed esportata in PDF arriva con i margini del documento attorno, e
#: su un A4 con due centimetri per lato copre il 70% del foglio.
QUOTA_IMMAGINE_PAGINA = 0.5

#: La stessa soglia, per la **verifica**, che la misura con un altro righello
#: (gli oggetti di pagina di pdfium invece del flusso letto qui). Piu' alta di
#: proposito: due misure indipendenti attorno a una soglia secca finiscono per
#: dare risposte diverse sulla pagina che ci sta a cavallo, e li' la verifica
#: fermerebbe un file che la redazione ha giudicato a posto per mezzo punto
#: percentuale. Cosi' la verifica dice di no solo dove non c'e' da discutere.
QUOTA_IMMAGINE_PAGINA_VERIFICA = 0.75

#: Sotto questa quota di pagina il testo e' «poco»: la somma dei riquadri dei
#: glifi divisa per l'area del foglio. Una riga di pie' di pagina in corpo 8
#: sta sullo 0,2%, tre righe di timbro sullo 0,9%; una lettera di cinque righe
#: sta sul 3%, una pagina piena sul 20%. L'1% separa il timbro dalla lettera.
QUOTA_MINIMA_DI_TESTO = 0.01

#: Di quanto puo' variare un canale dentro una zona azzerata, su 255. Zero
#: quando l'immagine e' riscritta senza perdita; qualche unita' quando e' un
#: JPEG. Sopra, li' dentro c'e' ancora qualcosa da leggere.
TOLLERANZA_ZONA_PIATTA = 8

#: Di quanto si allarga, a destra e a sinistra, il riquadro di un valore su
#: una scansione: una frazione dell'altezza della riga. Lo strato OCR dice
#: dove sta la parola con la precisione con cui l'ha misurata, e alle due
#: estremita' mezza lettera fuori dal riquadro e' mezza lettera che resta nei
#: pixel. Un quarto dell'altezza e' meno dello spazio fra due parole: si
#: mangia il bianco, non la parola accanto.
QUOTA_MARGINE_OCR = 0.25

#: Il lato del blocco di un JPEG con i colori sottocampionati. Una zona
#: azzerata si allarga fino a questo passo: un blocco meta' nero e meta'
#: scritto, ricompresso, sporca la parte nera con l'eco di quella scritta.
BLOCCO_JPEG = 16

#: Le chiavi di un elemento di struttura che contengono testo scritto per
#: essere letto: il testo sostitutivo, la descrizione alternativa, la forma
#: estesa di un'abbreviazione, il titolo dell'elemento.
_CHIAVI_TESTO_STRUTTURA = ("/ActualText", "/Alt", "/E", "/T")

#: Quanti elementi di struttura si visitano al massimo. Un documento vero ne
#: ha qualche migliaio; il tetto e' contro un albero costruito per non finire.
_MASSIMO_ELEMENTI_STRUTTURA = 500_000

#: La matrice che non sposta niente, come sei numeri `a b c d e f`.
_IDENTITA = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

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
    #: vede resta: vedi `_qualche_glifo_invisibile`.
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
    #: Le pagine in cui il dato stava **nei pixel di una scansione**: li' i
    #: pixel sono stati azzerati dentro l'immagine e sopra c'e' il rettangolo,
    #: tutti e due sulle coordinate che lo strato OCR dichiara.
    #: Sono trattate, non in ripiego — ma la zona azzerata sta dove l'OCR dice
    #: che sta la parola, e se quello strato e' disallineato rispetto
    #: all'immagine toglie i pixel sbagliati. Non e' verificabile dal file: si
    #: nomina la pagina e la si fa guardare.
    pagine_coperte_sull_ocr: list[int] = field(default_factory=list)
    #: Quante **miniature di pagina** (`/Thumb`) sono state tolte. Sono
    #: immagini della pagina com'era prima: si tolgono tutte, senza guardarci
    #: dentro, per la stessa ragione degli allegati.
    miniature_tolte: int = 0
    #: Quanti valori sono stati tolti dal **testo di struttura** -- le
    #: stringhe `/ActualText`, `/Alt`, `/E` e `/T` dell'albero che descrive il
    #: documento a chi lo legge con uno screen reader. Come metadati e
    #: segnalibri: testo che non sta in nessun flusso di pagina.
    struttura_tolti: int = 0


class _Contenitore:
    """Una pagina o un Form XObject, con le sue istruzioni da riscrivere."""

    def __init__(self, oggetto, percorso: tuple[int, ...] = ()):
        self.oggetto = oggetto
        self.istruzioni = list(pikepdf.parse_content_stream(oggetto))
        self.modificato = False
        #: Da dove, nel flusso della pagina, si arriva a questo contenitore:
        #: vuoto per la pagina, e per un form i numeri delle istruzioni `Do`
        #: attraversate per raggiungerlo. Con il numero dell'istruzione in
        #: coda dice **quando** una cosa viene dipinta rispetto alle altre:
        #: vedi `_qualche_valore_sotto_un_immagine`.
        self.percorso = percorso


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
           pezzi: list[str], profondita: int,
           percorso: tuple[int, ...] = ()) -> None:
    if profondita > 6:
        return
    try:
        contenitore = _Contenitore(oggetto, percorso)
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
    # pagina. Vedi `_qualche_glifo_invisibile`.
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
                       profondita + 1, percorso + (i,))

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


class _Originale:
    """Il documento di partenza aperto con pdfium: **una volta, e solo se serve**.

    Serve a misurare i riquadri dei valori com'erano prima di toglierli. Sulle
    pagine digitali non serve mai, quindi non si apre finche' qualcuno non lo
    chiede; e una volta aperto resta aperto, perche' un fascicolo di mille
    scansioni lo chiederebbe mille volte.
    """

    def __init__(self, percorso: Path):
        self._percorso = percorso
        self._documento = None

    def documento(self):
        if self._documento is None:
            self._documento = pdfium.PdfDocument(str(self._percorso))
        return self._documento

    def chiudi(self) -> None:
        if self._documento is not None:
            try:
                self._documento.close()
            except Exception:
                pass
            self._documento = None


def _riquadri_originali(originale: _Originale, numero: int, tratti):
    """I riquadri dei valori sulla pagina **di partenza**.

    Si guarda il documento originale perche' e' l'unico posto dove quei
    caratteri esistono ancora: sul risultato sono gia' stati tolti. Serve solo
    dove il dato sta nei pixel, quindi si apre alla bisogna e non a ogni
    documento.

    Se qualcosa va storto si torna a mani vuote e il chiamante rifiuta la
    pagina come faceva prima: meglio nessuna copertura di una copertura
    disegnata su coordinate inventate.

    **I tratti sono quelli del testo estratto da pdfium, non quelli del
    flusso.** Fino alla 1.30.0 qui arrivavano gli indici del testo
    ricostruito dal flusso, e si chiedevano a pdfium i riquadri di *quei*
    numeri: le due numerazioni coincidono sulla prima riga e poi divergono di
    un carattere a ogni a capo, perche' per pdfium un a capo sono due
    caratteri e per il flusso uno. Su un cedolino di quattro righe il
    rettangolo dell'IBAN partiva due caratteri prima e finiva due caratteri
    prima, lasciando scoperta la coda. I banchi avevano tutti una riga sola.

    **Tutti o nessuno.** Un valore di cui non si trova nemmeno un riquadro e'
    un valore di cui non si sa dove stiano i pixel: si torna a mani vuote
    anche per gli altri, perche' una pagina coperta a meta' uscirebbe
    dichiarata coperta.
    """
    try:
        documento = originale.documento()
        if numero >= len(documento):
            return []
        testo = documento[numero].get_textpage()
        try:
            fuori = []
            for tratto in tratti:
                righe = _riquadri_del_tratto(testo, tratto)
                if not righe:
                    return []
                fuori.extend(righe)
            return fuori
        finally:
            testo.close()
    except Exception:
        return []


def _allargati(riquadri) -> list[tuple[float, float, float, float, str]]:
    """I riquadri con un po' di margine ai due lati: vedi `QUOTA_MARGINE_OCR`.

    Si allarga il riquadro e non la sola zona da azzerare, cosi' il
    rettangolo disegnato sopra e i pixel tolti sotto hanno gli stessi bordi:
    altrimenti dal rettangolo spunterebbe una cornice nera.
    """
    fuori = []
    for sinistra, basso, destra, alto, etichetta in riquadri:
        di_piu = QUOTA_MARGINE_OCR * (alto - basso)
        fuori.append((sinistra - di_piu, basso, destra + di_piu, alto, etichetta))
    return fuori


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
        for tratto in tratti:
            fuori.extend(_riquadri_del_tratto(testo, tratto))
    finally:
        testo.close()
    return fuori


def _riquadri_del_tratto(testo_pdfium, tratto) -> list[tuple[float, float, float, float, str]]:
    """I riquadri di un valore: **uno per riga**, non uno solo.

    Un valore a cavallo di due righe -- un indirizzo, un nome lungo -- con un
    riquadro solo darebbe un rettangolo alto quanto le due, che copre anche il
    testo in mezzo. Prima lo si riconosceva dall'altezza e lo si **saltava**:
    andava bene finche' il rettangolo era un segno per chi legge, e non va
    piu' bene adesso che dice dove azzerare i pixel. Un valore saltato e' un
    valore rimasto nell'immagine, su una pagina dichiarata coperta.

    Si apre una riga nuova quando il centro del carattere esce dall'altezza
    della riga in corso.
    """
    inizio, fine, etichetta = tratto
    totale = testo_pdfium.count_chars()
    righe: list[list[float]] = []
    for k in range(inizio, min(fine, totale)):
        try:
            sinistra, basso, destra, alto = testo_pdfium.get_charbox(k)
        except Exception:
            continue
        if sinistra == destra or basso == alto:
            continue  # carattere senza area: spazio o a capo
        centro = (basso + alto) / 2
        if righe and righe[-1][1] <= centro <= righe[-1][3]:
            riga = righe[-1]
            riga[0] = min(riga[0], sinistra)
            riga[1] = min(riga[1], basso)
            riga[2] = max(riga[2], destra)
            riga[3] = max(riga[3], alto)
        else:
            righe.append([sinistra, basso, destra, alto])
    return [(r[0], r[1], r[2], r[3], etichetta) for r in righe]


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


def _testo_e_poco_testo(sorgente: Path) -> tuple[list[str], list[bool]]:
    """Il testo di ogni pagina, e per ognuna se quel testo e' «poco».

    Gemella di `testo_per_pagina`, con una misura in piu' presa **mentre la
    pagina e' gia' aperta**: riaprire il documento pagina per pagina, dopo,
    per chiedere la stessa cosa costerebbe a un fascicolo di mille pagine
    mille aperture.
    """
    documento = pdfium.PdfDocument(str(sorgente))
    testi: list[str] = []
    poco: list[bool] = []
    for pagina in documento:
        pagina_testo = pagina.get_textpage()
        testi.append(pagina_testo.get_text_range())
        try:
            poco.append(_quota_di_testo(pagina, pagina_testo) < QUOTA_MINIMA_DI_TESTO)
        except Exception:
            # Non si e' potuto dimostrare che la pagina sia testo: se ha
            # anche un'immagine che la copre, va dichiarata.
            poco.append(True)
        pagina_testo.close()
    documento.close()
    return testi, poco


def redigi_pdf(sorgente: Path, destinazione: Path,
               opzioni: PrivacyOptions | None = None) -> EsitoRedazione:
    """Scrive in `destinazione` il PDF redatto. Vedi il docstring del modulo."""
    opzioni = opzioni or PrivacyOptions()
    esito = EsitoRedazione()
    per_pagina, poco_testo = _testo_e_poco_testo(sorgente)
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

    originale = _Originale(sorgente)
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
        # La quarta: il testo di struttura, che sta nell'albero del documento
        # e non in una pagina.
        esito.struttura_tolti = _redigi_struttura(pdf, opzioni)
        esito.valori_da_togliere += esito.struttura_tolti
        for numero, pagina in enumerate(pdf.pages):
            testo_estratto = per_pagina[numero] if numero < len(per_pagina) else ""

            # **Prima di tutto, e su ogni pagina**: anche su quelle che qui
            # sotto escono con un `continue`. La miniatura e' un ritratto
            # della pagina originale, e una pagina non trattata che se la
            # porta dietro e' non trattata due volte.
            if _togli_miniatura(pagina):
                esito.miniature_tolte += 1

            # Prima del flusso, perche' non dipende dal flusso: una pagina
            # senza una riga di testo puo' avere un campo modulo pieno.
            esito.valori_da_togliere += _redigi_annotazioni(pdf, pagina, opzioni)

            if not testo_estratto.strip() and _pagina_e_una_scansione(pagina):
                _ripiego(esito, numero, MOTIVO_SCANSIONE)
                continue

            # **Si chiede prima di sapere se ci sono valori**, perche' la
            # risposta serve in tutti e due i casi: senza valori la pagina
            # usciva in silenzio, con un valore nel timbro usciva «trattata».
            pagina_immagine = _pagina_quasi_solo_immagine(
                pagina, poco_testo[numero] if numero < len(poco_testo) else True)

            tratti_estratti = intervalli_da_togliere(testo_estratto, opzioni)
            valori = [(testo_estratto[a:b], s) for a, b, s in tratti_estratti]
            if not valori:
                if pagina_immagine:
                    _ripiego(esito, numero, MOTIVO_IMMAGINE)
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

            # **Il dato sta nei pixel?** Due modi di accorgersene, perche' sono
            # due i modi in cui un OCR lascia il suo testo su una scansione:
            # invisibile **sopra** l'immagine, oppure scritto normale e poi
            # coperto dall'immagine, cioe' **sotto**. Il secondo fino alla
            # 1.30.1 non lo vedeva nessuno: quei glifi sono in modo normale,
            # quindi «si vedevano», e la pagina prendeva la strada delle
            # pagine digitali con i pixel intatti.
            riquadri = None
            nei_pixel = False
            if _pagina_ha_un_immagine(pagina):
                nei_pixel = _qualche_glifo_invisibile(tratti, emissioni)
                if not nei_pixel:
                    dipinte_dopo = _immagini_dipinte_dopo(
                        tratti, emissioni, contenitori, pagina)
                    # I riquadri si misurano solo se un'immagine dipinta dopo
                    # c'e' davvero: sulle pagine digitali, che sono quasi
                    # tutte, qui non si apre niente.
                    if dipinte_dopo:
                        riquadri = _allargati(
                            _riquadri_originali(originale, numero, tratti_estratti))
                        nei_pixel = any(_zone_nell_immagine(matrice, riquadri, 0.0)
                                        for matrice in dipinte_dopo)

            if nei_pixel:
                # **Il dato sta nei pixel, e lo strato OCR dice dove.** Fino
                # alla 1.29.1 qui si rinunciava, ed era onesto: togliere glifi
                # invisibili non toglie niente da un'immagine. Ma le
                # coordinate di quei glifi sono, per come l'OCR le scrive, la
                # mappa delle parole sul foglio: bastano a sapere **quali
                # pixel** togliere dall'immagine, che e' la redazione vera.
                #
                # Il riquadro si misura sui valori **originali** e non sul
                # segnaposto: e' il segnaposto a essere messo dopo, e puo'
                # essere piu' corto del valore che sostituisce -- un
                # `{{NAME_1}}` al posto di un nome lungo lascerebbe scoperta
                # la coda dei pixel. E si misura su **tutti** i valori che il
                # motore ha trovato nel testo estratto, non solo su quelli
                # ritrovati nel flusso: sotto ognuno di loro ci sono pixel.
                #
                # Prima i pixel, poi i glifi, e i glifi solo se i pixel sono
                # andati: una pagina con il testo tolto e l'immagine intatta
                # e' il difetto, non una via di mezzo.
                if riquadri is None:
                    riquadri = _allargati(
                        _riquadri_originali(originale, numero, tratti_estratti))
                if riquadri and _azzera_i_pixel(pagina, riquadri):
                    riquadri_ocr[numero] = riquadri
                    esito.pagine_coperte_sull_ocr.append(numero)
                else:
                    # Senza coordinate, o con un'immagine che non si riesce a
                    # riscrivere, non c'e' niente di vero da fare: si torna
                    # alla risposta di prima, che e' l'unica onesta.
                    _ripiego(esito, numero, MOTIVO_OCR)
                    continue
            elif pagina_immagine:
                # Un valore c'e', ma sta nel poco testo vero sopra
                # un'immagine che nessuno ha letto. Toglierlo e chiamare la
                # pagina trattata sarebbe vero per sette parole e falso per
                # tutto il resto del foglio.
                _ripiego(esito, numero, MOTIVO_IMMAGINE)
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
        originale.chiudi()

    # **Un documento fatto di sole scansioni e' una scansione**, anche quando
    # ha uno strato OCR che rende estraibile il testo. Senza questa riga il
    # rifiuto — che esiste da sempre e che le rotte traducono in un messaggio
    # chiaro — sarebbe scavalcato dal solo fatto che qualcuno ha passato un
    # OCR sul PDF prima di noi: il documento uscirebbe «redatto» con l'elenco
    # delle pagine non trattate lungo quanto il documento intero.
    if (esito.pagine
            and len(esito.pagine_in_ripiego) == esito.pagine
            and all(m in (MOTIVO_SCANSIONE, MOTIVO_OCR, MOTIVO_IMMAGINE)
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


def _qualche_glifo_invisibile(tratti, emissioni: list[Emissione]) -> bool:
    """Fra cio' che c'e' da togliere in questa pagina c'e' testo che non si vede.

    E' il segnale della **scansione gia' passata dall'OCR**, che e' il caso in
    cui questo modulo poteva fare il danno peggiore che sa fare: togliere i
    glifi invisibili — l'unica delle due copie del dato che non si legge — e
    dichiarare la pagina trattata mentre il nome resta a schermo, dentro
    l'immagine. Misurato prima della correzione: due segnaposto inseriti,
    `pagine_in_ripiego` vuoto, e il codice fiscale ancora visibile.

    **Ne basta uno, non servono tutti.** Fino alla 1.30.0 la domanda era «sono
    *tutti* invisibili?», e una scansione con OCR su cui qualcuno aveva
    stampato un timbro di testo vero — «Firmato digitalmente da Mario Rossi»
    — rispondeva di no per via del nome nel timbro: la pagina prendeva la
    strada delle pagine digitali, e il codice fiscale dello strato OCR
    restava intero nei pixel. Un valore visibile accanto non dice niente sui
    pixel sotto gli altri.

    Non basta da sola a decidere: la usa `redigi_pdf` **in and** con la
    presenza di un'immagine. Un testo invisibile su una pagina senza immagini
    non e' una scansione, e li' togliere i glifi e' esattamente il lavoro
    giusto — il dato e' nel file e ne esce.
    """
    for inizio, fine, _segnaposto in tratti:
        for emissione in emissioni:
            if (emissione.invisibile and emissione.inizio < fine
                    and emissione.inizio + len(emissione.glifi) > inizio):
                return True
    return False


def _immagini_dipinte_dopo(tratti, emissioni: list[Emissione],
                           contenitori: list[_Contenitore], pagina) -> list[tuple[float, ...]]:
    """Le matrici delle immagini dipinte **dopo** il testo di almeno un valore.

    E' la domanda che il modo di rendering non sa fare. Un programma di OCR
    puo' scrivere il testo riconosciuto in modo normale e poi dipingerci sopra
    la scansione: i glifi «si vedono» per chi legge il flusso un'istruzione
    alla volta, e non si vedono per chi guarda la pagina. In un PDF cio' che
    viene dopo copre cio' che viene prima, e basta l'ordine a dirlo.

    L'ordine e' quello dei percorsi (vedi `_immagini_disegnate`). Qui si
    torna cio' che viene dopo il **primo glifo** di un valore, il primo in
    tutta la pagina: basta che un'immagine arrivi dopo una sola lettera di un
    dato perche' quella lettera possa esserle finita sotto. Se le stia sopra
    davvero — cioe' se la copra — lo decide chi chiama, con i riquadri.

    «Il primo glifo» e non «l'ultimo», ed e' voluto: la verifica guarda
    carattere per carattere, e una redazione piu' larga di manica di lei
    lascerebbe passare pagine che lei poi ferma.

    Una pagina con lo sfondo dipinto prima del testo torna a mani vuote, ed
    e' il caso di quasi tutte: li' il testo sta sopra, e si vede.
    """
    primo = None
    for inizio, fine, _segnaposto in tratti:
        for e in emissioni:
            if e.inizio < fine and e.inizio + len(e.glifi) > inizio:
                percorso = contenitori[e.contenitore].percorso + (e.istruzione,)
                if primo is None or percorso < primo:
                    primo = percorso
    if primo is None:
        return []
    try:
        return [matrice for _immagine, matrice, percorso in _immagini_disegnate(pagina)
                if percorso > primo]
    except Exception:
        return []


def _pagina_ha_un_immagine(pagina) -> bool:
    """La pagina disegna un'immagine?

    Da sola non vuol dire niente — meta' della carta intestata ha un logo — e
    infatti non decide mai da sola: chi la chiama la mette **in and** con
    un'altra condizione (nessun testo, oppure testo invisibile).

    Si guarda fra le risorse, **scendendo nei form**: una scansione avvolta in
    un Form XObject ha l'immagine un livello sotto, e fermandosi alle risorse
    della pagina quella pagina usciva come una pagina bianca. Resta fuori
    solo l'immagine in linea, che non e' una risorsa: per quella si legge il
    contenuto, ma soltanto se nei byte c'e' l'operatore che la apre — la
    lettura completa di ogni pagina senza immagini costerebbe a tutti i
    documenti per un caso che non capita quasi mai.
    """
    try:
        if _immagine_fra_le_risorse(_risorse(pagina), 0):
            return True
    except Exception:
        pass
    try:
        if not _forse_un_immagine_in_linea(pagina):
            return False
        return any(immagine is None
                   for immagine, _matrice, _percorso in _immagini_disegnate(pagina))
    except Exception:
        return False


def _immagine_fra_le_risorse(risorse, profondita: int) -> bool:
    """C'e' un'immagine fra queste risorse, o fra quelle dei form che contengono."""
    if risorse is None or profondita > 6:
        return False
    xobject = risorse.get("/XObject")
    if xobject is None:
        return False
    for oggetto in xobject.values():
        sottotipo = oggetto.get("/Subtype")
        if sottotipo == pikepdf.Name("/Image"):
            return True
        if sottotipo == pikepdf.Name("/Form") and _immagine_fra_le_risorse(
                oggetto.get("/Resources"), profondita + 1):
            return True
    return False


def _forse_un_immagine_in_linea(pagina) -> bool:
    """Nei byte del contenuto compare `BI`, che apre un'immagine in linea.

    «Forse», perche' le due lettere possono stare anche dentro una stringa:
    serve solo a decidere se vale la pena leggere il contenuto per davvero.
    """
    contenuti = getattr(pagina, "obj", pagina).get("/Contents")
    if contenuti is None:
        return False
    pezzi = contenuti if isinstance(contenuti, pikepdf.Array) else [contenuti]
    for pezzo in pezzi:
        try:
            if re.search(rb"(?:^|\s)BI\s", pezzo.read_bytes()):
                return True
        except Exception:
            return True  # non si riesce a guardare: si va a leggere
    return False


# ---------------------------------------------------------------------------
# Le immagini: dove sono disegnate, e come se ne azzera un pezzo
# ---------------------------------------------------------------------------


def _matrice(valori) -> tuple[float, ...] | None:
    """Sei numeri, o niente."""
    try:
        numeri = tuple(float(v) for v in valori)
    except Exception:
        return None
    return numeri if len(numeri) == 6 else None


def _componi(prima, poi) -> tuple[float, ...]:
    """La matrice che applica `prima` e, al risultato, `poi`.

    E' il conto dell'operatore `cm`: la matrice nuova si applica **prima** di
    quella corrente, non dopo. Scambiare i due fattori da' lo stesso risultato
    finche' si scala soltanto, e sposta tutto appena c'e' una rotazione.
    """
    a, b, c, d, e, f = prima
    a2, b2, c2, d2, e2, f2 = poi
    return (a * a2 + b * c2, a * b2 + b * d2,
            c * a2 + d * c2, c * b2 + d * d2,
            e * a2 + f * c2 + e2, e * b2 + f * d2 + f2)


def _risorse(oggetto):
    """Le risorse di una pagina o di un form, anche quando sono ereditate.

    Una pagina puo' non avere `/Resources` e prenderle dal nodo che la
    contiene: e' raro e legale, e senza risalire quella pagina sembra vuota.
    """
    nodo = getattr(oggetto, "obj", oggetto)
    for _ in range(8):
        try:
            risorse = nodo.get("/Resources")
        except Exception:
            return None
        if risorse is not None:
            return risorse
        nodo = nodo.get("/Parent")
        if not isinstance(nodo, pikepdf.Dictionary):
            return None
    return None


def _immagini_disegnate(oggetto, matrice=_IDENTITA, ereditate=None, profondita: int = 0,
                        percorso: tuple[int, ...] = ()):
    """Ogni immagine che il contenuto disegna: dov'e', e **quando** viene dipinta.

    Restituisce terne `(immagine, matrice, percorso)`.

    La matrice porta il quadrato unitario dell'immagine nello **spazio
    pagina**, ed e' il prodotto di tutti i `cm` incontrati per arrivarci,
    dentro e fuori dai form. Per un'**immagine in linea** — scritta dentro il
    flusso, non un oggetto a parte — al posto dell'immagine c'e' `None`: si
    sa dov'e', non la si puo' riscrivere.

    Il percorso sono i numeri delle istruzioni attraversate per arrivarci: uno
    solo per un'immagine disegnata dalla pagina, due per una dentro un form
    (l'istruzione che disegna il form, poi quella dentro di lui). Due
    percorsi si confrontano come si confrontano due numeri di paragrafo, e chi
    viene dopo e' dipinto sopra. Sono gli stessi numeri che usa `_leggi` per
    il testo, perche' le istruzioni sono le stesse lette nello stesso ordine.

    E' una lettura a parte da `_leggi`, che segue il testo: qui servono le
    matrici, la' i font, e tenerle insieme vorrebbe dire una funzione che fa
    due mestieri e li sbaglia tutti e due.
    """
    if profondita > 6:
        return
    risorse = _risorse(oggetto)
    if risorse is None:
        risorse = ereditate
    forme = risorse.get("/XObject") if risorse is not None else None
    pila: list[tuple[float, ...]] = []
    corrente = matrice
    for numero, istruzione in enumerate(pikepdf.parse_content_stream(oggetto)):
        operatore = str(istruzione.operator)
        if operatore == "INLINE IMAGE":
            yield None, corrente, percorso + (numero,)
        elif operatore == "q":
            pila.append(corrente)
        elif operatore == "Q":
            if pila:
                corrente = pila.pop()
        elif operatore == "cm":
            nuova = _matrice(istruzione.operands)
            if nuova is not None:
                corrente = _componi(nuova, corrente)
        elif operatore == "Do" and forme is not None and len(istruzione.operands) >= 1:
            bersaglio = forme.get(str(istruzione.operands[0]))
            if bersaglio is None:
                continue
            sottotipo = str(bersaglio.get("/Subtype", ""))
            if sottotipo == "/Image":
                yield bersaglio, corrente, percorso + (numero,)
            elif sottotipo == "/Form":
                propria = _matrice(bersaglio.get("/Matrix", [])) or _IDENTITA
                yield from _immagini_disegnate(
                    bersaglio, _componi(propria, corrente), risorse, profondita + 1,
                    percorso + (numero,))


def _riquadro_della_pagina(pagina) -> tuple[float, float, float, float]:
    """La parte di foglio che si vede: il ritaglio, o il foglio intero."""
    for chiave in ("/CropBox", "/MediaBox"):
        nodo = getattr(pagina, "obj", pagina)
        for _ in range(8):
            if not isinstance(nodo, pikepdf.Dictionary):
                break
            valore = nodo.get(chiave)
            if valore is not None:
                try:
                    x0, y0, x1, y1 = (float(v) for v in valore)
                except Exception:
                    break
                return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
            nodo = nodo.get("/Parent")
    return (0.0, 0.0, 612.0, 792.0)


def _area_coperta(matrici, riquadro) -> float:
    """Quanta parte del riquadro coprono le immagini messe con quelle matrici.

    Le aree si **sommano**, senza togliere le sovrapposizioni: una scansione
    spezzata in strisce da' la somma giusta, e tre livelli sovrapposti danno
    piu' di uno — che qui si ferma a uno, ed e' l'errore dalla parte giusta.
    """
    sinistra, basso, destra, alto = riquadro
    area = (destra - sinistra) * (alto - basso)
    if area <= 0:
        return 0.0
    coperta = 0.0
    for m in matrici:
        xs = (m[4], m[0] + m[4], m[2] + m[4], m[0] + m[2] + m[4])
        ys = (m[5], m[1] + m[5], m[3] + m[5], m[1] + m[3] + m[5])
        larghezza = min(max(xs), destra) - max(min(xs), sinistra)
        altezza = min(max(ys), alto) - max(min(ys), basso)
        if larghezza > 0 and altezza > 0:
            coperta += larghezza * altezza
    return min(1.0, coperta / area)


def _quota_di_immagine(pagina) -> float:
    """Quanta parte della pagina e' coperta da immagini, da 0 a 1."""
    return _area_coperta(
        [matrice for _immagine, matrice, _percorso in _immagini_disegnate(pagina)],
        _riquadro_della_pagina(pagina))


def _quota_di_testo(pagina_pdfium, testo_pdfium=None) -> float:
    """Quanta parte della pagina e' occupata dai glifi, da 0 a 1.

    La somma dei riquadri dei caratteri sull'area del foglio. Si misura
    l'area e non il numero di caratteri perche' la domanda e' quanto della
    pagina **e'** testo: venti caratteri in corpo 48 sono un titolo che la
    riempie, venti in corpo 8 sono un pie' di pagina.

    Si smette di contare appena si supera la soglia: su una pagina piena
    serve sapere che il testo c'e', non quanto.
    """
    larghezza, altezza = pagina_pdfium.get_size()
    area = float(larghezza) * float(altezza)
    if area <= 0:
        return 1.0
    testo = testo_pdfium if testo_pdfium is not None else pagina_pdfium.get_textpage()
    try:
        somma = 0.0
        for k in range(testo.count_chars()):
            try:
                sinistra, basso, destra, alto = testo.get_charbox(k)
            except Exception:
                continue
            somma += abs(destra - sinistra) * abs(alto - basso)
            if somma >= area * QUOTA_MINIMA_DI_TESTO:
                break
        return somma / area
    finally:
        if testo_pdfium is None:
            testo.close()


def _pagina_quasi_solo_immagine(pagina, poco_testo: bool) -> bool:
    """Un'immagine copre la pagina, e il testo estraibile e' una frazione minima.

    E' la pagina che sfuggiva a tutti e due i controlli: non e' una
    «scansione», perche' il testo estratto non e' vuoto — c'e' il pie' di
    pagina — e non ha niente da togliere, perche' in quelle sette parole non
    c'e' un dato. Usciva identica a com'era entrata, contata fra le trattate.

    `poco_testo` arriva gia' misurato (vedi `_testo_e_poco_testo`), ed e' la
    prima domanda perche' e' quella che costa meno: su una pagina piena di
    testo qui non si legge nemmeno il contenuto.
    """
    if not poco_testo:
        return False
    try:
        return (_pagina_ha_un_immagine(pagina)
                and _quota_di_immagine(pagina) >= QUOTA_IMMAGINE_PAGINA)
    except Exception:
        return False


def _zone_nell_immagine(matrice, riquadri, margine: float) -> list[tuple[float, ...]]:
    """I riquadri, portati dallo spazio pagina al **quadrato unitario** dell'immagine.

    Un'immagine in un PDF occupa sempre il quadrato da (0, 0) a (1, 1), e la
    matrice dice dove quel quadrato finisce sul foglio. Per sapere quali pixel
    stanno sotto un riquadro si fa il viaggio al contrario, con la matrice
    inversa: cosi' il conto non cambia se l'immagine e' scalata, spostata o
    messa di traverso.

    Torna `(u0, v0, u1, v1)` con la **v verso l'alto**, come nel PDF; i pixel
    contano dall'alto, e il ribaltamento lo fa `_in_pixel`. Cio' che cade
    fuori dall'immagine non torna.
    """
    a, b, c, d, e, f = matrice
    determinante = a * d - b * c
    if abs(determinante) < 1e-9:
        return []
    zone = []
    for riquadro in riquadri:
        sinistra, basso, destra, alto = riquadro[:4]
        us, vs = [], []
        for x in (sinistra - margine, destra + margine):
            for y in (basso - margine, alto + margine):
                us.append((d * (x - e) - c * (y - f)) / determinante)
                vs.append((-b * (x - e) + a * (y - f)) / determinante)
        u0, u1 = max(0.0, min(us)), min(1.0, max(us))
        v0, v1 = max(0.0, min(vs)), min(1.0, max(vs))
        if u1 > u0 and v1 > v0:
            zone.append((u0, v0, u1, v1))
    return zone


def _in_pixel(zona, larghezza: int, altezza: int, passo: int = 1) -> tuple[int, int, int, int]:
    """Dalla zona nel quadrato unitario al rettangolo di pixel che la contiene.

    Si arrotonda sempre **verso fuori**: un pixel toccato a meta' e' un pixel
    che porta meta' di una lettera. Con `passo` il rettangolo si allarga
    ancora, fino al multiplo successivo: serve ai JPEG, vedi `BLOCCO_JPEG`.
    """
    u0, v0, u1, v1 = zona
    x0 = math.floor(u0 * larghezza)
    x1 = math.ceil(u1 * larghezza)
    y0 = math.floor((1.0 - v1) * altezza)
    y1 = math.ceil((1.0 - v0) * altezza)
    if passo > 1:
        x0 -= x0 % passo
        y0 -= y0 % passo
        x1 += -x1 % passo
        y1 += -y1 % passo
    return (max(0, x0), max(0, y0), min(larghezza, x1), min(altezza, y1))


def _azzera_i_pixel(pagina, riquadri) -> bool:
    """Toglie dalle immagini della pagina i pixel che stanno sotto i riquadri.

    **Coprire non e' cancellare.** Fino alla 1.30.0 sopra una scansione con
    strato OCR si toglieva il testo invisibile e si disegnava un rettangolo:
    a schermo il dato non si vedeva piu', e dentro il file c'era ancora tutto.
    L'immagine incorporata non la toccava nessuno, e basta estrarla — lo fa
    qualunque lettore con «salva immagine» — per riavere il foglio intero.

    Qui i pixel si azzerano **dentro** l'immagine, e l'immagine vecchia esce
    dal file. Il rettangolo sopra resta, ma torna a essere quello che e': un
    segno per chi legge.

    Falso se **anche una sola** immagine sotto un riquadro non si puo'
    riscrivere: un'immagine in linea, un formato che qui non si sa aprire, un
    foglio con le dimensioni che non tornano. In quel caso non si tocca
    niente — nemmeno le immagini che si sarebbero potute azzerare — e il
    chiamante dichiara la pagina non trattata. E' la stessa regola dei
    riquadri: una pagina coperta a meta' uscirebbe dichiarata coperta.

    Vale anche per la maschera dell'immagine, quando c'e': in una scansione
    compressa a livelli la forma delle lettere sta li', non nei colori.
    """
    try:
        disegnate = list(_immagini_disegnate(pagina))
    except Exception:
        return False

    per_immagine: dict[tuple[int, int], tuple] = {}
    for immagine, matrice, _percorso in disegnate:
        zone = _zone_nell_immagine(matrice, riquadri, MARGINE_RETTANGOLO)
        if not zone:
            continue
        if immagine is None:
            return False  # immagine in linea: non si puo' riscrivere
        per_immagine.setdefault(immagine.objgen, (immagine, []))[1].extend(zone)

    pronte = []
    for immagine, zone in per_immagine.values():
        bersagli = [immagine]
        for chiave in ("/SMask", "/Mask"):
            maschera = immagine.get(chiave)
            if isinstance(maschera, pikepdf.Stream):
                bersagli.append(maschera)
        for bersaglio in bersagli:
            try:
                nuova = _immagine_azzerata(bersaglio, zone)
            except Exception:
                nuova = None
            if nuova is None:
                return False
            pronte.append((bersaglio, nuova))

    # Si scrive solo adesso, quando si sa che si puo' scrivere tutto.
    for bersaglio, (dati, filtro, chiavi) in pronte:
        bersaglio.write(dati, filter=filtro)
        for chiave, valore in chiavi.items():
            if valore is None:
                if chiave in bersaglio:
                    del bersaglio[chiave]
            else:
                bersaglio[chiave] = valore
    return True


def _filtri(oggetto) -> list[str]:
    filtro = oggetto.get("/Filter")
    if filtro is None:
        return []
    if isinstance(filtro, pikepdf.Array):
        return [str(f) for f in filtro]
    return [str(filtro)]


#: Quante componenti ha un pixel in ogni spazio colore che ha un nome.
_COMPONENTI = {
    "/DeviceGray": 1, "/CalGray": 1, "/Indexed": 1, "/Separation": 1,
    "/DeviceRGB": 3, "/CalRGB": 3, "/Lab": 3,
    "/DeviceCMYK": 4,
}


def _componenti(oggetto) -> int | None:
    """Quante componenti per pixel dichiara l'immagine, se lo si capisce."""
    if bool(oggetto.get("/ImageMask", False)):
        return 1
    spazio = oggetto.get("/ColorSpace")
    if spazio is None:
        return None
    if isinstance(spazio, pikepdf.Array):
        if len(spazio) == 0:
            return None
        nome = str(spazio[0])
        try:
            if nome == "/ICCBased":
                return int(spazio[1].get("/N"))
            if nome == "/DeviceN":
                return len(spazio[1])
        except Exception:
            return None
    else:
        nome = str(spazio)
    return _COMPONENTI.get(nome)


def _immagine_azzerata(oggetto, zone):
    """L'immagine con le zone azzerate, pronta da riscrivere. `None` se non si puo'.

    Torna `(dati, filtro, chiavi)`: i byte gia' compressi, il filtro con cui
    lo sono, e le chiavi del dizionario da cambiare (`None` vuol dire togliere).

    Tre strade, dalla piu' fedele alla meno:

    1. **i campioni cosi' come sono.** Se il flusso si decomprime — Flate,
       LZW, RunLength — si azzerano i bit al loro posto e si ricomprime senza
       perdita. Non si interpreta lo spazio colore: tavolozza, profilo ICC e
       matrice di decodifica restano quelli, e valgono ancora;
    2. **il JPEG, da JPEG.** Decomprimerlo e riscriverlo senza perdita
       moltiplicherebbe per dieci il peso di ogni scansione a colori: si
       riapre, si azzera e si ricomprime con le stesse tabelle;
    3. **il resto, passando da un'immagine.** CCITT e JPEG 2000 si aprono con
       Pillow e si riscrivono come grigio o RGB semplici.

    «Azzerare» vuol dire mettere a zero i campioni, non «dipingere di nero»:
    in un'immagine a tavolozza lo zero e' il primo colore, in una maschera e'
    «dipingi». Non importa di che colore esce, importa che li' dentro non ci
    sia piu' niente: il colore lo mette il rettangolo disegnato sopra.
    """
    try:
        larghezza = int(oggetto.get("/Width"))
        altezza = int(oggetto.get("/Height"))
    except Exception:
        return None
    if larghezza <= 0 or altezza <= 0:
        return None

    filtri = _filtri(oggetto)
    if filtri == ["/DCTDecode"]:
        return _jpeg_azzerato(oggetto, larghezza, altezza, zone)

    try:
        dati = bytearray(oggetto.read_bytes(decode_level=pikepdf.StreamDecodeLevel.all))
    except Exception:
        return _azzerata_passando_da_pillow(oggetto, larghezza, altezza, zone)

    try:
        bit = 1 if bool(oggetto.get("/ImageMask", False)) else int(
            oggetto.get("/BitsPerComponent", 8))
    except Exception:
        return None
    # Le componenti dichiarate per prime; poi le altre plausibili, perche' uno
    # spazio colore puo' essere un nome che rimanda alle risorse della pagina
    # e da qui non si legge. Decide la **lunghezza dei dati**: se non torna
    # con nessuna, non si sa dove stiano i pixel e non si tocca niente.
    dichiarate = _componenti(oggetto)
    passo = 0
    for componenti in ([dichiarate] if dichiarate else []) + [1, 3, 4]:
        candidato = (larghezza * componenti * bit + 7) // 8
        if candidato * altezza == len(dati):
            passo = candidato
            break
    if not passo:
        return None

    bit_per_pixel = componenti * bit
    for zona in zone:
        x0, y0, x1, y1 = _in_pixel(zona, larghezza, altezza)
        _azzera_i_bit(dati, passo, x0 * bit_per_pixel, x1 * bit_per_pixel, y0, y1)
    return zlib.compress(bytes(dati)), pikepdf.Name("/FlateDecode"), {}


def _azzera_i_bit(dati: bytearray, passo: int, da: int, a: int, riga0: int, riga1: int) -> None:
    """Mette a zero i bit da `da` ad `a` (escluso) di ogni riga fra le due date.

    I bit di una riga si contano dal piu' significativo del primo byte, come
    li impacchetta il PDF. Un'immagine a un bit per pixel ne ha otto per
    byte, e un rettangolo che non comincia su un multiplo di otto deve
    lasciare intatti i vicini nello stesso byte.
    """
    if a <= da:
        return
    primo, ultimo = da // 8, (a - 1) // 8
    testa = 0xFF >> (da % 8)
    coda = (0xFF << (7 - (a - 1) % 8)) & 0xFF
    for riga in range(riga0, riga1):
        base = riga * passo
        if primo == ultimo:
            dati[base + primo] &= ~(testa & coda) & 0xFF
            continue
        dati[base + primo] &= ~testa & 0xFF
        dati[base + ultimo] &= ~coda & 0xFF
        if ultimo - primo > 1:
            dati[base + primo + 1:base + ultimo] = bytes(ultimo - primo - 1)


def _jpeg_azzerato(oggetto, larghezza: int, altezza: int, zone):
    """Il JPEG riaperto, azzerato e ricompresso **con le sue tabelle**.

    `quality="keep"` riusa le tabelle di quantizzazione dell'originale: i
    blocchi che non si toccano tornano quasi identici, invece di perdere un
    altro po' di qualita' a ogni redazione.

    Le zone si allargano al blocco (`BLOCCO_JPEG`) perche' un blocco meta'
    nero e meta' scritto, ricompresso, lascia nella parte nera un'eco della
    parte scritta. Allineato al blocco, cio' che e' azzerato e' piatto.

    Solo grigio e RGB. Un JPEG in quadricromia ha le convenzioni di Adobe
    sull'inversione dei canali, e riscriverlo sbagliando darebbe una pagina
    in negativo: si rinuncia, e la pagina viene dichiarata.
    """
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return None
    immagine = Image.open(io.BytesIO(oggetto.read_raw_bytes()))
    immagine.load()
    if immagine.size != (larghezza, altezza) or immagine.mode not in ("L", "RGB"):
        return None
    disegno = ImageDraw.Draw(immagine)
    for zona in zone:
        x0, y0, x1, y1 = _in_pixel(zona, larghezza, altezza, BLOCCO_JPEG)
        if x1 > x0 and y1 > y0:
            disegno.rectangle((x0, y0, x1 - 1, y1 - 1), fill=0)
    buffer = io.BytesIO()
    try:
        immagine.save(buffer, "JPEG", quality="keep", subsampling="keep")
    except Exception:
        buffer = io.BytesIO()
        immagine.save(buffer, "JPEG", quality=90)
    return buffer.getvalue(), pikepdf.Name("/DCTDecode"), {}


def _azzerata_passando_da_pillow(oggetto, larghezza: int, altezza: int, zone):
    """L'ultima strada: aprire l'immagine come immagine, e riscriverla semplice.

    Serve ai formati che il motore PDF non decomprime da solo — il fax (CCITT)
    delle scansioni in bianco e nero, il JPEG 2000. Si perde lo spazio colore
    originale, che diventa grigio o RGB: e' il prezzo per poter riscrivere.

    Si rinuncia davanti a una maschera o a una matrice di decodifica: li' i
    campioni non vogliono dire «colore», e riscriverli come grigio
    cambierebbe la pagina.
    """
    if bool(oggetto.get("/ImageMask", False)) or "/Decode" in oggetto:
        return None
    try:
        from PIL import ImageDraw
        immagine = pikepdf.PdfImage(oggetto).as_pil_image()
        immagine.load()
    except Exception:
        return None
    if immagine.size != (larghezza, altezza) or immagine.mode not in ("1", "L", "RGB"):
        return None
    disegno = ImageDraw.Draw(immagine)
    for zona in zone:
        x0, y0, x1, y1 = _in_pixel(zona, larghezza, altezza)
        if x1 > x0 and y1 > y0:
            disegno.rectangle((x0, y0, x1 - 1, y1 - 1), fill=0)
    chiavi = {
        "/ColorSpace": pikepdf.Name("/DeviceRGB" if immagine.mode == "RGB" else "/DeviceGray"),
        "/BitsPerComponent": 1 if immagine.mode == "1" else 8,
    }
    return zlib.compress(immagine.tobytes()), pikepdf.Name("/FlateDecode"), chiavi


# ---------------------------------------------------------------------------
# Le altre stanze: la miniatura di pagina, il testo di struttura
# ---------------------------------------------------------------------------


def _togli_miniatura(pagina) -> bool:
    """Toglie `/Thumb` dalla pagina. Vero se c'era.

    La miniatura e' un'immagine della pagina **com'era quando qualcuno l'ha
    salvata**: piccola, ma abbastanza da leggere un nome in grassetto o
    un'intestazione, e in ogni caso un ritratto del documento originale
    dentro un file che si chiama «-redatto.pdf». Sopravviveva intatta, perche'
    non sta nel flusso e non e' fra le risorse: e' una chiave del dizionario
    della pagina.

    Si toglie **sempre**, anche dalle pagine senza un solo valore e anche da
    quelle dichiarate non trattate: non si puo' sapere cosa ritrae senza
    leggerla, e non vale niente — ogni lettore la rifa' da se' aprendo il file.
    """
    oggetto = getattr(pagina, "obj", pagina)
    try:
        if "/Thumb" not in oggetto:
            return False
        del oggetto["/Thumb"]
    except Exception:
        return False
    return True


def _elementi_di_struttura(pdf):
    """Ogni elemento dell'albero di struttura, a qualunque profondita'.

    L'albero descrive il documento a chi non lo guarda: titoli, paragrafi,
    figure, e per ognuno il testo da leggere al posto di cio' che e'
    disegnato. I figli stanno in `/K`, che puo' essere un elemento, un elenco,
    o un numero che rimanda al contenuto della pagina.

    Non e' ricorsiva: un albero vero puo' essere profondo quanto i livelli di
    un indice, uno storto puo' esserlo senza fine. Si tiene conto di cio' che
    si e' gia' visto, e c'e' un tetto.
    """
    try:
        radice = pdf.Root.get("/StructTreeRoot")
    except Exception:
        return
    if not isinstance(radice, pikepdf.Dictionary):
        return
    visti: set[tuple[int, int]] = set()
    da_visitare = [radice.get("/K")]
    usciti = 0
    while da_visitare and usciti < _MASSIMO_ELEMENTI_STRUTTURA:
        nodo = da_visitare.pop()
        if isinstance(nodo, pikepdf.Array):
            da_visitare.extend(nodo)
            continue
        if not isinstance(nodo, pikepdf.Dictionary):
            continue
        chiave = nodo.objgen
        if chiave != (0, 0):
            if chiave in visti:
                continue
            visti.add(chiave)
        usciti += 1
        yield nodo
        figli = nodo.get("/K")
        if figli is not None:
            da_visitare.append(figli)


def _redigi_struttura(pdf, opzioni: PrivacyOptions) -> int:
    """Il testo di struttura e' testo come i metadati e i segnalibri.

    Un PDF accessibile porta, accanto a cio' che disegna, cio' che va **letto
    al suo posto**: il testo sostitutivo di una parola spezzata
    (`/ActualText`), la descrizione di una figura (`/Alt`), la forma estesa
    di una sigla (`/E`), il titolo di una sezione (`/T`). Sono stringhe
    appese agli elementi dell'albero, fuori da ogni flusso di pagina: la
    chirurgia dei glifi non le vede, e un cedolino usciva con
    `/Alt (IBAN IT60X...)` in chiaro accanto alla riga da cui l'IBAN era
    stato tolto.

    Si redigono e **non** si butta l'albero: e' cio' che rende il documento
    leggibile a chi usa uno screen reader, e toglierlo per prudenza vorrebbe
    dire consegnare a quelle persone un file peggiore di quello ricevuto.
    """
    tolti = 0
    try:
        for elemento in _elementi_di_struttura(pdf):
            for chiave in _CHIAVI_TESTO_STRUTTURA:
                valore = elemento.get(chiave)
                if not isinstance(valore, pikepdf.String):
                    continue
                testo = str(valore)
                if not testo.strip():
                    continue
                redatto, rapporto = apply_privacy_filter(testo, opzioni)
                if rapporto.total == 0:
                    continue
                elemento[chiave] = pikepdf.String(redatto)
                tolti += rapporto.total
    except Exception:
        return tolti
    return tolti


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
    allegati leggibili come testo, il testo di struttura.

    Serve alla verifica, e ogni voce di questo elenco e' arrivata dopo un
    difetto: senza i metadati un codice fiscale rimasto nell'oggetto del
    documento usciva **verde**; senza segnalibri e allegati usciva verde uno
    rimasto nel sommario o dentro un file appeso; senza il testo di struttura
    usciva verde un IBAN rimasto nella descrizione alternativa di una figura.
    La verifica guardava flusso e annotazioni, cioe' posti in cui quel dato
    non era mai stato.

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
            try:
                for elemento in _elementi_di_struttura(pdf):
                    for chiave in _CHIAVI_TESTO_STRUTTURA:
                        valore = elemento.get(chiave)
                        if isinstance(valore, pikepdf.String):
                            pezzi.append(str(valore))
            except Exception:
                pass
            return "\n".join(pezzi)
    except Exception:
        return ""


def _tratto_nascosto(testo_pdfium, inizio: int, fine: int, ordine) -> bool | None:
    """Qualche carattere di questo tratto c'e' nel file e **non si vede** sulla pagina?

    Due modi di non vedersi, e sono i due modi in cui un OCR lascia il suo
    testo su una scansione: scritto in modo **invisibile**, oppure scritto
    normale e poi **coperto da un'immagine** dipinta dopo. In tutti e due il
    dato vero sta nei pixel, e la verifica deve andare a guardarli. Fino alla
    1.30.1 qui si chiedeva solo il modo di rendering: il testo messo sotto
    l'immagine «si vedeva», e dei pixel non si guardava niente.

    Lo si chiede a **pdfium**, carattere per carattere, e non al lettore del
    flusso che sta in questo modulo: quello e' lo stesso righello con cui si
    e' deciso cosa azzerare, e una verifica che lo riusasse sbaglierebbe
    insieme alla redazione, nello stesso punto e nello stesso verso. La
    redazione conta le istruzioni del flusso; qui si guarda l'ordine degli
    oggetti di pagina come li ha letti un altro motore.

    **Ne basta uno.** E' la stessa regola della redazione, ed e' piu' severa
    di «tutti»: un valore coperto a meta' ha meta' delle sue lettere nei
    pixel.

    `ordine` e' una funzione che torna `_ordine_di_pittura` della pagina: si
    chiama solo quando serve, perche' elencare gli oggetti di una pagina
    costa, e sulle scansioni con testo invisibile non serve mai.

    `None` se la versione di pdfium installata non sa rispondere: chi chiama
    ripiega sull'altro righello, che e' peggio di uno indipendente e meglio
    di nessuno.
    """
    oggetto_del_carattere = getattr(pdfium.raw, "FPDFText_GetTextObject", None)
    modo_del_testo = getattr(pdfium.raw, "FPDFTextObj_GetTextRenderMode", None)
    if oggetto_del_carattere is None or modo_del_testo is None:
        return None
    grezzo = getattr(testo_pdfium, "raw", testo_pdfium)
    for k in range(inizio, min(fine, testo_pdfium.count_chars())):
        oggetto = oggetto_del_carattere(grezzo, k)
        if not oggetto:
            continue  # carattere generato: uno spazio, un a capo
        if int(modo_del_testo(oggetto)) in MODI_INVISIBILI:
            return True
        posizioni, immagini = ordine()
        if not immagini:
            continue
        try:
            sinistra, basso, destra, alto = testo_pdfium.get_charbox(k)
        except Exception:
            continue
        centro = ((sinistra + destra) / 2, (basso + alto) / 2)
        # Un oggetto di testo che non si ritrova nell'elenco non ha un
        # «prima» e un «dopo»: si considera coperto da qualunque immagine gli
        # stia sopra. E' l'errore dalla parte giusta — al peggio si va a
        # guardare dei pixel che non serviva guardare.
        posizione = posizioni.get(ctypes.addressof(oggetto.contents))
        for posizione_immagine, _immagine, matrice in immagini:
            if posizione is not None and posizione_immagine < posizione:
                continue  # dipinta prima del carattere: gli sta sotto
            if _dentro_l_immagine(matrice, centro):
                return True
    return False


def _dentro_l_immagine(matrice, punto) -> bool:
    """Il punto, in spazio pagina, cade dentro l'immagine messa con quella matrice."""
    a, b, c, d, e, f = matrice
    determinante = a * d - b * c
    if abs(determinante) < 1e-9:
        return False
    x, y = punto
    u = (d * (x - e) - c * (y - f)) / determinante
    v = (-b * (x - e) + a * (y - f)) / determinante
    return 0.0 <= u <= 1.0 and 0.0 <= v <= 1.0


def _pagina_tutta_invisibile(percorso: Path, numero: int) -> bool:
    """Il ripiego di `_tratto_nascosto`: tutto il testo della pagina e' invisibile."""
    try:
        with pikepdf.open(str(percorso)) as pdf:
            emissioni: list[Emissione] = []
            _leggi(pdf.pages[numero], [], emissioni, [], 0)
            return bool(emissioni) and all(e.invisibile for e in emissioni)
    except Exception:
        return False


def _ordine_di_pittura(pagina_pdfium) -> tuple[dict[int, int], list[tuple]]:
    """Gli oggetti della pagina nell'ordine in cui pdfium li dipinge.

    Torna due cose: per ogni oggetto il suo posto nella fila, e l'elenco delle
    immagini come `(posto, oggetto, matrice)`. Cio' che ha un posto piu' alto
    viene dipinto dopo, quindi sta sopra.

    E' la stessa domanda di `_immagini_disegnate`, fatta a **un altro
    motore**: pdfium legge il contenuto per conto suo, segue i form per conto
    suo e tiene i conti delle matrici per conto suo. Serve alla verifica
    proprio per questo — se qui e la' si sbagliasse allo stesso modo, la
    verifica direbbe di si' a qualunque cosa la redazione abbia fatto.

    La matrice di un oggetto dentro un form e' relativa al form: si compone
    scendendo, come si fa con i `cm`. Si chiede solo per immagini e form: su
    una pagina dove ogni parola e' un oggetto, chiederla a tutti vorrebbe
    dire migliaia di chiamate per sapere una cosa che non serve.
    """
    grezzo = pdfium.raw
    posizioni: dict[int, int] = {}
    immagini: list[tuple] = []

    def scendi(conta, prendi, contenitore, matrice, livello):
        for indice in range(max(0, conta(contenitore))):
            oggetto = prendi(contenitore, indice)
            if not oggetto:
                continue
            posizione = len(posizioni)
            posizioni[ctypes.addressof(oggetto.contents)] = posizione
            tipo = grezzo.FPDFPageObj_GetType(oggetto)
            if tipo not in (grezzo.FPDF_PAGEOBJ_IMAGE, grezzo.FPDF_PAGEOBJ_FORM):
                continue
            propria = grezzo.FS_MATRIX()
            if not grezzo.FPDFPageObj_GetMatrix(oggetto, propria):
                continue
            composta = _componi(
                (propria.a, propria.b, propria.c, propria.d, propria.e, propria.f),
                matrice)
            if tipo == grezzo.FPDF_PAGEOBJ_IMAGE:
                immagini.append((posizione, oggetto, composta))
            elif livello < 6:
                scendi(grezzo.FPDFFormObj_CountObjects, grezzo.FPDFFormObj_GetObject,
                       oggetto, composta, livello + 1)

    scendi(grezzo.FPDFPage_CountObjects, grezzo.FPDFPage_GetObject,
           getattr(pagina_pdfium, "raw", pagina_pdfium), _IDENTITA, 0)
    return posizioni, immagini


def _immagini_secondo_pdfium(pagina_pdfium) -> list[tuple]:
    """Le immagini della pagina come le vede pdfium: `(oggetto, matrice)`."""
    return [(oggetto, matrice)
            for _posizione, oggetto, matrice in _ordine_di_pittura(pagina_pdfium)[1]]


def _zona_piatta(immagine, rettangolo) -> bool:
    """Dentro il rettangolo non c'e' niente da leggere: e' di un colore solo."""
    x0, y0, x1, y1 = rettangolo
    if x1 <= x0 or y1 <= y0:
        return True
    estremi = immagine.crop(rettangolo).getextrema()
    if estremi and isinstance(estremi[0], tuple):
        return all(massimo - minimo <= TOLLERANZA_ZONA_PIATTA for minimo, massimo in estremi)
    minimo, massimo = estremi
    return massimo - minimo <= TOLLERANZA_ZONA_PIATTA


def _cio_che_non_e_testo(sorgente: Path, destinazione: Path,
                         tratti_per_pagina: list[list[tuple[int, int, str]]]) -> dict:
    """Cio' che puo' restare nel file redatto e che **nessun testo estratto mostra**.

    La verifica cercava i valori nel testo: e' la domanda giusta per i glifi,
    le annotazioni, i metadati. Non dice niente su tre cose che non sono
    testo, e su tutte e tre rispondeva zero:

    * **i pixel.** Un valore che nell'originale stava in testo invisibile
      sopra un'immagine aveva la sua copia vera nei pixel. Qui si prende
      **l'immagine estratta** dal file redatto — non la pagina resa, dove il
      rettangolo copre tutto e la prova e' verde per costruzione — e si
      guarda se sotto il riquadro del valore e' piatta. Se non lo e', li'
      dentro c'e' ancora qualcosa da leggere. Un'immagine che non si riesce
      a estrarre vale come un no: non si e' potuto guardare;
    * **le miniature.** Una pagina del redatto che ha ancora `/Thumb`;
    * **le pagine-immagine.** Un'immagine che copre la pagina, con poco o
      niente testo: di quella pagina non si e' letto il contenuto. Fa
      eccezione quella con uno strato OCR in cui il motore ha trovato dei
      valori, che e' gia' giudicata sui pixel.

    Delle pagine-immagine la verifica dice soltanto **quali sono**: se siano
    state dichiarate non trattate lo sa `EsitoRedazione`, non lei, ed e' chi
    la chiama a fare il confronto — come gia' fa per i valori rimasti nel
    testo di una pagina in ripiego.

    `tratti_per_pagina` sono i valori che il motore ha trovato nel testo di
    ogni pagina dell'originale, con gli indici del testo estratto da pdfium:
    li ha gia' calcolati chi chiama, e rifarli qui vorrebbe dire far girare
    il motore una terza volta su ogni pagina.

    Le domande sono in ordine di costo: su una pagina piena di testo e senza
    valori invisibili — quasi tutte — non si elenca nemmeno un oggetto.
    """
    nei_pixel: list[tuple[int, str]] = []
    pagine_immagine: list[int] = []

    prima = pdfium.PdfDocument(str(sorgente))
    try:
        dopo = pdfium.PdfDocument(str(destinazione))
        try:
            for numero in range(len(prima)):
                pagina = prima[numero]
                testo = pagina.get_textpage()
                try:
                    tratti = tratti_per_pagina[numero] if numero < len(tratti_per_pagina) else []
                    # L'ordine di pittura si calcola una volta per pagina, e
                    # solo se qualcuno lo chiede.
                    calcolato: list = []

                    def ordine(pagina=pagina, calcolato=calcolato):
                        if not calcolato:
                            calcolato.append(_ordine_di_pittura(pagina))
                        return calcolato[0]

                    nascosti = []
                    for tratto in tratti:
                        risposta = _tratto_nascosto(testo, tratto[0], tratto[1], ordine)
                        if risposta is None:
                            risposta = _pagina_tutta_invisibile(sorgente, numero)
                        if risposta:
                            nascosti.append(tratto)

                    if (not nascosti
                            and _quota_di_testo(pagina, testo) < QUOTA_MINIMA_DI_TESTO):
                        larghezza, altezza = pagina.get_size()
                        ritaglio = pagina.get_cropbox() or (0.0, 0.0, larghezza, altezza)
                        quota = _area_coperta(
                            [matrice for _posizione, _oggetto, matrice in ordine()[1]],
                            tuple(float(v) for v in ritaglio))
                        if quota >= QUOTA_IMMAGINE_PAGINA_VERIFICA:
                            pagine_immagine.append(numero)

                    if not nascosti or numero >= len(dopo):
                        continue
                    contenuto = testo.get_text_range()
                    # La pagina resta in una variabile fino in fondo al giro:
                    # gli oggetti che pdfium restituisce vivono quanto lei.
                    pagina_dopo = dopo[numero]
                    immagini = _immagini_secondo_pdfium(pagina_dopo)
                    estratte: dict[int, object] = {}
                    for tratto in nascosti:
                        riquadri = _riquadri_del_tratto(testo, tratto)
                        if _resta_nei_pixel(immagini, estratte, riquadri):
                            nei_pixel.append((numero, contenuto[tratto[0]:tratto[1]]))
                finally:
                    testo.close()
        finally:
            dopo.close()
    finally:
        prima.close()

    miniature: list[int] = []
    with pikepdf.open(str(destinazione)) as pdf:
        for numero, pagina in enumerate(pdf.pages):
            if "/Thumb" in pagina.obj:
                miniature.append(numero)

    return {"nei_pixel": nei_pixel, "miniature": miniature,
            "pagine_immagine": pagine_immagine}


def _resta_nei_pixel(immagini, estratte: dict, riquadri) -> bool:
    """Sotto questi riquadri, in una delle immagini, c'e' ancora qualcosa.

    `estratte` tiene le immagini gia' aperte, una volta per pagina: su un
    foglio con venti valori la stessa scansione servirebbe venti volte.
    """
    for indice, (oggetto, matrice) in enumerate(immagini):
        zone = _zone_nell_immagine(matrice, riquadri, 0.0)
        if not zone:
            continue
        if indice not in estratte:
            estratte[indice] = _immagine_secondo_pdfium(oggetto)
        immagine = estratte[indice]
        if immagine is None:
            return True  # non si e' potuto guardare: non e' un si'
        for zona in zone:
            if not _zona_piatta(immagine, _in_pixel(zona, immagine.width, immagine.height)):
                return True
    return False


def _immagine_secondo_pdfium(oggetto):
    """I pixel di un'immagine come li decodifica pdfium, o `None`.

    Non resa sulla pagina: **estratta**, nella sua griglia di pixel, senza
    matrice e senza cio' che le sta disegnato sopra.
    """
    try:
        grezza = pdfium.raw.FPDFImageObj_GetBitmap(oggetto)
        if not grezza:
            return None
        bitmap = pdfium.PdfBitmap.from_raw(grezza)
        try:
            return bitmap.to_pil().copy()
        finally:
            bitmap.close()
    except Exception:
        return None


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

    La terza, del 3 ottobre 2026: **non tutto cio' che resta e' testo.** Un
    valore puo' restare nei pixel di un'immagine, una pagina intera nella sua
    miniatura, e una pagina fatta di un'immagine puo' non essere mai stata
    letta. Nessuna delle tre si trova cercando una stringa, e su tutte e tre
    questa funzione diceva zero. Adesso entrano in `sopravvissuti` insieme ai
    valori rimasti nel testo, e le tre voci in fondo dicono quanti sono di
    ciascun genere: vedi `_cio_che_non_e_testo`.
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
    def _unite(percorso: Path, flusso: list[str]) -> list[str]:
        note = _annotazioni_per_pagina(percorso)
        pagine = [t + "\n" + (note[i] if i < len(note) else "")
                  for i, t in enumerate(flusso)]
        return pagine + [_fuori_dalle_pagine_come_testo(percorso)]

    flusso_prima = testo_per_pagina(sorgente)
    prima = _unite(sorgente, flusso_prima)
    dopo = _unite(destinazione, testo_per_pagina(destinazione))

    dichiarati = individuati = 0
    rimasti: list[str] = []
    # I valori trovati **nel testo della pagina**, senza quelli delle sue
    # annotazioni: il testo della pagina viene per primo nella stringa unita,
    # quindi i loro indici sono gli stessi che conosce pdfium. Servono a
    # `_cio_che_non_e_testo`, che di ognuno va a guardare i pixel.
    tratti_per_pagina: list[list[tuple[int, int, str]]] = [[] for _ in flusso_prima]
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
        for a, b, segnaposto in intervalli_da_togliere(testo, opzioni):
            individuati += 1
            if numero < len(flusso_prima) and b <= len(flusso_prima[numero]):
                tratti_per_pagina[numero].append((a, b, segnaposto))
            if valore_ancora_presente(testo[a:b], stessa_pagina):
                rimasti.append(testo[a:b])
                pagine_con_superstiti.add(numero)

    altro = _cio_che_non_e_testo(sorgente, destinazione, tratti_per_pagina)
    for numero, valore in altro["nei_pixel"]:
        rimasti.append(valore)
        pagine_con_superstiti.add(numero)
    pagine_con_superstiti.update(altro["miniature"])
    pagine_con_superstiti.update(altro["pagine_immagine"])
    return {
        "dichiarati_dal_motore": dichiarati,
        "individuati_nel_testo": individuati,
        "persi_prima_di_tagliare": dichiarati - individuati,
        # Valori rimasti nel testo o nei pixel, piu' una voce per ogni
        # miniatura e per ogni pagina-immagine: non sono valori, e sono cose
        # che nel file redatto non dovevano esserci senza essere dichiarate.
        "sopravvissuti": (len(rimasti) + len(altro["miniature"])
                          + len(altro["pagine_immagine"])),
        "esempi": rimasti[:5],
        # L'ultimo indice e' la «pagina» dei metadati (vedi `_unite`): non e'
        # un foglio, e non puo' mai essere in ripiego. Un superstite li' vale
        # come uno su una pagina dichiarata trattata.
        "pagine_con_superstiti": sorted(pagine_con_superstiti),
        "nei_pixel": len(altro["nei_pixel"]),
        "miniature_rimaste": altro["miniature"],
        "pagine_immagine": altro["pagine_immagine"],
    }
