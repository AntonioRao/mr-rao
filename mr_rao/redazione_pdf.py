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

# ---------------------------------------------------------------------------
# Dai byte del flusso al testo: il ponte
# ---------------------------------------------------------------------------

#: Gli operatori che mostrano testo.
MOSTRA = {b"Tj", b"TJ", b"'", b'"'}

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

#: Un valore piu' corto di cosi' non si cerca: si ritroverebbe ovunque, e
#: tagliare in mezzo a un'altra parola e' peggio che non tagliare.
MINIMO_CERCABILE = 3


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
    cache: dict[str, Font] = {}

    for i, istruzione in enumerate(contenitore.istruzioni):
        operandi = istruzione.operands
        op = str(istruzione.operator).encode("latin-1")

        if op == b"Tf" and len(operandi) >= 2:
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
                        risorsa, corpo))
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


def intervalli_da_togliere(
        testo: str, opzioni: PrivacyOptions) -> list[tuple[int, int, str]]:
    """(inizio, fine, segnaposto) per ogni sostituzione, sul testo dato.

    Il motore restituisce il testo redatto, non le posizioni. **Non si allinea
    con un diff, si legge la struttura**: il testo redatto e' l'originale con
    dei segnaposto al posto dei valori, quindi i pezzi *fra* i segnaposto sono
    copie letterali e servono da ancora. Cio' che sta fra due ancore e'
    esattamente il valore tolto.

    Con `difflib` non funzionava, e il modo in cui falliva era subdolo:
    `CAFIERO` sostituito da `{{NAME_1}}` condivide con il segnaposto la «A» e
    la «E», quindi l'allineamento restituiva tre tratti — «C», «FI», «RO» —
    invece di uno. Tre frammenti troppo corti per essere cercati, quindi
    scartati: **il cognome restava intero nel documento**, e nessun conteggio
    se ne accorgeva.
    """
    redatto, rapporto = apply_privacy_filter(testo, opzioni)
    if rapporto.total == 0:
        return []

    pezzi = [p for p in re.split(r"(\{\{[A-Z_]+(?:_\d+)?\}\})", redatto) if p]
    tratti: list[tuple[int, int, str]] = []
    cursore = 0
    in_attesa = ""
    for pezzo in pezzi:
        if pezzo.startswith("{{") and pezzo.endswith("}}"):
            in_attesa = pezzo
            continue
        posizione = testo.find(pezzo, cursore)
        if posizione < 0:
            # L'ancora non si ritrova: l'allineamento e' perso, e tagliare a
            # naso e' peggio che non tagliare. Il chiamante lo vede come una
            # pagina senza tratti, e la manda nel ripiego.
            return []
        if posizione > cursore and in_attesa:
            tratti.append((cursore, posizione, in_attesa))
        in_attesa = ""
        cursore = posizione + len(pezzo)
    if in_attesa and cursore < len(testo):
        tratti.append((cursore, len(testo), in_attesa))
    return tratti


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
                    nuove.append(_istruzione(
                        [pikepdf.Name(standard), corpo], "Tf"))
                    nuove.append(_istruzione(
                        [pikepdf.String(
                            segnaposto.encode("latin-1", "replace"))], "Tj"))
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
    if not any(t.strip() for t in per_pagina):
        esito.pagine = len(per_pagina)
        esito.scansione = True
        return esito

    pdf = pikepdf.open(str(sorgente))
    try:
        esito.pagine = len(pdf.pages)
        for numero, pagina in enumerate(pdf.pages):
            testo_estratto = per_pagina[numero] if numero < len(per_pagina) else ""
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
                else:
                    contenitore.oggetto.write(grezzo)

        pdf.save(str(destinazione))
    finally:
        pdf.close()
    return esito


def _ripiego(esito: EsitoRedazione, pagina: int, motivo: str) -> None:
    esito.pagine_in_ripiego.append(pagina)
    esito.motivi_ripiego.append(motivo)


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
    prima = testo_per_pagina(sorgente)
    dopo = testo_per_pagina(destinazione)

    dichiarati = individuati = 0
    rimasti: list[str] = []
    for numero, testo in enumerate(prima):
        _, rapporto = apply_privacy_filter(testo, opzioni)
        dichiarati += rapporto.total
        stessa_pagina = dopo[numero] if numero < len(dopo) else ""
        for a, b, _s in intervalli_da_togliere(testo, opzioni):
            individuati += 1
            if valore_ancora_presente(testo[a:b], stessa_pagina):
                rimasti.append(testo[a:b])
    return {
        "dichiarati_dal_motore": dichiarati,
        "individuati_nel_testo": individuati,
        "persi_prima_di_tagliare": dichiarati - individuati,
        "sopravvissuti": len(rimasti),
        "esempi": rimasti[:5],
    }
