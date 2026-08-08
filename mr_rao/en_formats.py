"""Validatori per gli identificativi dei Paesi anglofoni (pacchetto EN).

Stessa filosofia dei validatori italiani: il pattern propone, il validatore
decide. Ma qui la forza dei controlli e' molto diseguale, e la differenza
conta piu' che nel pacchetto italiano.

Alcuni identificativi portano una cifra di controllo vera (NHS, SIN, ABN,
TFN, ABA, MRZ): un numero qualsiasi la supera una volta su dieci o su
undici, quindi il validatore basta da solo a distinguere il dato dal
rumore. Altri (NINO, SSN, ITIN, codice postale, telefono NANP) *non hanno
nessun checksum*: si puo' solo verificare la struttura ed escludere gli
intervalli che l'ente emittente non ha mai assegnato. Su quelli il
validatore riduce i falsi positivi ma non li azzera, e la decisione di
sostituire va presa insieme a una parola di contesto.

Questa differenza e' scritta accanto a ogni funzione, perche' e' l'unica
cosa che serve sapere per usarle bene.

Ogni funzione ha accanto una tupla ``VETTORI_<NOME>`` con i suoi casi di
prova. Il terzo elemento dice **da dove viene il valore**: o e' un esempio
pubblicato da chi emette l'identificativo, o e' costruito applicando
l'algoritmo — e in quel caso lo dice. Un vettore di cui non si sa la
provenienza non prova niente: conferma solo che il codice fa quello che ha
gia' fatto quando e' stato scritto.
"""
from __future__ import annotations

import re
import sys


# I separatori che una persona mette dentro un identificativo quando lo
# scrive o lo stampa: spazi, trattini di ogni foggia (compresi quelli
# tipografici che arrivano da Word e dai PDF), punti. Vanno tolti prima di
# guardare le cifre, altrimenti "943 476 5919" e "9434765919" sarebbero due
# dati diversi — e sul primo, che e' la forma in cui l'NHS li stampa, il
# validatore direbbe di no.
_RE_SEPARATORI = re.compile(r"[\s.‐-―\-]")


def _pulisci(candidate: str) -> str:
    """Toglie i separatori e porta in maiuscolo. Non giudica niente."""
    if not candidate:
        return ""
    return _RE_SEPARATORI.sub("", candidate).upper()


def _luhn(digits: str) -> bool:
    """Luhn puro, senza il vincolo di lunghezza delle carte di pagamento.

    ``luhn_ok`` in ``privacy.py`` pretende 13-19 cifre perche' li' serve a
    riconoscere una carta. Qui serve su un SIN di nove cifre, quindi il
    vincolo di lunghezza sta fuori: e' un vincolo del dato, non
    dell'algoritmo.
    """
    totale = 0
    for i, c in enumerate(reversed(digits)):
        n = int(c)
        if i % 2:
            n *= 2
            if n > 9:
                n -= 9
        totale += n
    return totale % 10 == 0


# ---------------------------------------------------------------------------
# Regno Unito — NHS number
# ---------------------------------------------------------------------------

def nhs_number_ok(candidate: str) -> bool:
    """Mod-11 dell'NHS number (NHS Data Dictionary, "NHS NUMBER").

    Checksum vero: una sequenza casuale di dieci cifre lo supera circa una
    volta su undici, quindi qui il validatore decide da solo.

    Il caso che conta e' ``check == 10``: non esiste una cifra sola per
    scriverlo, quindi quei numeri **non sono mai stati emessi**. Trattarli
    come validi (o peggio, farli diventare 0) e' l'errore classico di chi
    reimplementa questo algoritmo: fa passare circa un decimo dei candidati
    che dovrebbe rifiutare.

    Non si controllano gli intervalli di emissione (400-499, 600-708...):
    sono cambiati nel tempo e un numero legittimo emesso prima di una
    revisione resterebbe fuori. Il mod-11 non invecchia.
    """
    s = _pulisci(candidate)
    if len(s) != 10 or not s.isdigit():
        return False
    totale = sum(int(c) * peso for c, peso in zip(s[:9], range(10, 1, -1)))
    check = 11 - (totale % 11)
    if check == 11:
        check = 0
    if check == 10:
        return False
    return check == int(s[9])


VETTORI_NHS_NUMBER = (
    ("943 476 5919", True, "esempio del NHS Data Dictionary (attributo NHS NUMBER), nella forma stampata 3-3-4"),
    ("9434765919", True, "stesso esempio NHS Data Dictionary, senza separatori"),
    ("1234567881", True, "esempio ricorrente nella documentazione di validazione NHS; ricalcolato: somma 208, 208%11=10, check=1"),
    ("9434765900", True, "costruito: primi nove danno somma 297, multiplo di 11, quindi check 11 che diventa 0"),
    ("9434765960", False, "costruito: primi nove danno somma 309, 309%11=1, quindi check=10 — numero mai emesso"),
    ("9434765918", False, "esempio NHS Data Dictionary con l'ultima cifra alterata: il mod-11 non torna"),
    ("943476591", False, "nove cifre: l'NHS number ne ha dieci"),
    ("94347659191", False, "undici cifre"),
    ("943476591A", False, "una lettera al posto della cifra di controllo"),
    ("", False, "stringa vuota"),
)


# ---------------------------------------------------------------------------
# Regno Unito — National Insurance number
# ---------------------------------------------------------------------------

# Lettere mai usate nelle prime due posizioni (HMRC, National Insurance
# Manual NIM39110). D, F, I, Q, U, V non sono mai state allocate; O e'
# vietata solo in seconda posizione perche' si confonde con lo zero, e in
# seconda posizione lo zero non c'e' per distinguerla.
_NINO_VIETATE_PRIME_DUE = frozenset("DFIQUV")

# Prefissi riservati o mai allocati (NIM39110). BG e GB, KN e NK, NT e TN
# sono coppie: ognuna e' l'inverso dell'altra, ed e' proprio l'inversione
# che li ha resi inutilizzabili. ZZ e' riservato ai numeri temporanei.
_NINO_PREFISSI_VIETATI = frozenset({"BG", "GB", "KN", "NK", "NT", "TN", "ZZ"})

_RE_NINO = re.compile(r"^[A-Z]{2}[0-9]{6}[A-D]$")


def nino_ok(candidate: str) -> bool:
    """National Insurance number: **nessun checksum**, solo struttura.

    Il NINO non porta cifra di controllo. Tutto quello che si puo' fare e'
    verificare la forma e togliere le combinazioni che HMRC non ha mai
    allocato — che sono poche. Con due lettere, sei cifre e un suffisso, lo
    spazio dei codici formalmente validi resta enorme: qualunque sequenza
    del tipo "AB123456C" passa, anche se non e' il numero di nessuno.

    Quindi: da solo non basta a decidere una sostituzione. Serve una parola
    di contesto accanto ("NI number", "National Insurance"), oppure il
    codice va segnalato come sospetto invece che sostituito.

    Il suffisso e' preteso: alcune fonti ammettono il NINO senza suffisso
    (forma "temporanea"), ma accettarlo allargherebbe ancora lo spazio dei
    candidati proprio dove e' gia' troppo largo.
    """
    s = _pulisci(candidate)
    if not _RE_NINO.match(s):
        return False
    if s[0] in _NINO_VIETATE_PRIME_DUE or s[1] in _NINO_VIETATE_PRIME_DUE:
        return False
    if s[1] == "O":
        return False
    return s[:2] not in _NINO_PREFISSI_VIETATI


VETTORI_NINO = (
    ("AB 12 34 56 C", True, "costruito secondo NIM39110: prefisso AB allocabile, suffisso C; nella forma spaziata di gov.uk"),
    ("AB123456C", True, "stesso valore senza separatori"),
    ("JG121212A", True, "costruito: prefisso JG allocabile, nessuna lettera vietata, suffisso A"),
    ("QQ123456C", False, "esempio di gov.uk ('For example, QQ 12 34 56 C'): scelto apposta perche' Q non e' mai allocata"),
    ("QQ 12 34 56 C", False, "stesso esempio gov.uk nella forma spaziata"),
    ("BG123456A", False, "NIM39110: prefisso BG mai allocato"),
    ("GB123456A", False, "NIM39110: prefisso GB mai allocato"),
    ("NK123456A", False, "NIM39110: prefisso NK mai allocato"),
    ("KN123456A", False, "NIM39110: prefisso KN mai allocato"),
    ("NT123456A", False, "NIM39110: prefisso NT mai allocato"),
    ("TN123456A", False, "NIM39110: prefisso TN mai allocato"),
    ("ZZ123456A", False, "NIM39110: ZZ riservato ai numeri temporanei"),
    ("DA123456A", False, "D vietata in prima posizione"),
    ("FA123456A", False, "F vietata in prima posizione"),
    ("AD123456A", False, "D vietata anche in seconda posizione"),
    ("AO123456A", False, "O vietata in seconda posizione: si confonde con lo zero"),
    ("OA123456A", True, "costruito: O e' vietata solo in seconda posizione, in prima e' ammessa"),
    ("AB123456E", False, "suffisso ammesso solo A-D"),
    ("AB12345C", False, "cinque cifre invece di sei"),
    ("AB1234567C", False, "sette cifre invece di sei"),
    ("AB123456", False, "manca il suffisso"),
    ("A1B23456C", False, "cifra dove serve una lettera"),
)


# ---------------------------------------------------------------------------
# Stati Uniti — Social Security Number
# ---------------------------------------------------------------------------

def ssn_ok(candidate: str) -> bool:
    """SSN: **nessun checksum**, solo le esclusioni pubblicate dalla SSA.

    Dal 2011 la SSA assegna i numeri in modo casuale (randomization), il
    che ha eliminato l'unico controllo indiretto che esisteva prima: la
    corrispondenza fra area number e Stato di emissione. Restano solo tre
    esclusioni:

    - area 000, 666 e 900-999 non sono mai state emesse;
    - gruppo 00 non e' mai stato emesso;
    - seriale 0000 non e' mai stato emesso.

    Sono esclusioni deboli: **l'89% delle sequenze casuali di nove cifre le
    supera** (misurato su duecentomila estrazioni). Nove
    cifre qualsiasi passano quasi sempre, e nove cifre sono anche un numero
    di pratica, un ABN troncato, un identificativo interno. **Da solo non
    giustifica una sostituzione**: serve il contesto ("SSN", "Social
    Security"), o il formato 3-2-4 con i trattini, che e' molto piu' raro
    per caso.

    Attenzione a cosa questa funzione *non* sa: i numeri annullati dalla
    SSA (078-05-1120, 219-09-9999) sono strutturalmente validi e passano.
    Erano numeri veri, stampati su campioni di portafoglio e volantini
    pubblicitari, e la SSA li ha invalidati a mano. Nessuna regola
    strutturale li intercetta: chi vuole escluderli deve tenerne l'elenco.
    """
    s = _pulisci(candidate)
    if len(s) != 9 or not s.isdigit():
        return False
    area, gruppo, seriale = s[:3], s[3:5], s[5:]
    if area in ("000", "666") or area[0] == "9":
        return False
    if gruppo == "00":
        return False
    return seriale != "0000"


VETTORI_SSN = (
    ("123-45-6789", True, "costruito: nessuna esclusione SSA applicabile (area 123, gruppo 45, seriale 6789)"),
    ("123456789", True, "stesso valore senza trattini"),
    ("078-05-1120", True, "il numero della cartella Woolworth (SSA): strutturalmente valido, annullato a mano dalla SSA nel 1938 — le esclusioni non lo intercettano"),
    ("219-09-9999", True, "secondo numero annullato dalla SSA (volantino del 1940): anch'esso strutturalmente valido"),
    ("000-45-6789", False, "SSA: area 000 mai emessa"),
    ("666-45-6789", False, "SSA: area 666 mai emessa"),
    ("900-45-6789", False, "SSA: aree 900-999 mai emesse (estremo inferiore)"),
    ("999-45-6789", False, "SSA: aree 900-999 mai emesse (estremo superiore)"),
    ("987-65-4320", False, "SSA riserva 987-65-4320..4329 alla pubblicita' proprio perche' l'area 987 non e' mai stata emessa"),
    ("123-00-6789", False, "SSA: gruppo 00 mai emesso"),
    ("123-45-0000", False, "SSA: seriale 0000 mai emesso"),
    ("899-99-9999", True, "costruito: estremo appena sotto l'intervallo escluso 900-999"),
    ("12345678", False, "otto cifre"),
    ("1234567890", False, "dieci cifre"),
    ("123-45-678A", False, "una lettera"),
)


# ---------------------------------------------------------------------------
# Stati Uniti — ITIN
# ---------------------------------------------------------------------------

# Intervalli del gruppo centrale ammessi per l'ITIN (IRS). I buchi fra un
# intervallo e l'altro (66-69, 89, 93) non sono arbitrari: sono i gruppi
# che l'IRS ha tenuto fuori, ed e' l'unica cosa che distingue un ITIN da un
# qualunque numero di nove cifre che inizia per 9.
_ITIN_GRUPPI = ((50, 65), (70, 88), (90, 92), (94, 99))


def itin_ok(candidate: str) -> bool:
    """ITIN: **nessun checksum**, struttura e intervalli IRS.

    L'ITIN e' piu' selettivo dell'SSN — prima cifra fissa a 9 e gruppo
    centrale dentro quattro finestre — ma resta un controllo strutturale:
    il 4.4% delle sequenze casuali di nove cifre lo supera (misurato). Non
    e' un checksum: e' un filtro. Vale la stessa cautela dell'SSN.

    Nota che 9 in prima posizione e' esattamente cio' che rende **l'ITIN e
    l'SSN mutuamente esclusivi**: le aree 900-999 che l'SSA non ha mai
    emesso sono quelle che l'IRS usa per gli ITIN. Un numero non puo'
    essere entrambe le cose, e questo aiuta: se ``itin_ok`` dice di si',
    ``ssn_ok`` dice di no per costruzione.
    """
    s = _pulisci(candidate)
    if len(s) != 9 or not s.isdigit():
        return False
    if s[0] != "9":
        return False
    gruppo = int(s[3:5])
    return any(basso <= gruppo <= alto for basso, alto in _ITIN_GRUPPI)


VETTORI_ITIN = (
    ("912-78-1234", True, "costruito sulla regola IRS: prefisso 9, gruppo 78 dentro l'intervallo 70-88"),
    ("912781234", True, "stesso valore senza trattini"),
    ("900-50-0000", True, "costruito: estremo inferiore del primo intervallo IRS (50)"),
    ("900-65-0000", True, "costruito: estremo superiore del primo intervallo IRS (65)"),
    ("900-70-0000", True, "costruito: estremo inferiore del secondo intervallo IRS (70)"),
    ("900-88-0000", True, "costruito: estremo superiore del secondo intervallo IRS (88)"),
    ("900-90-0000", True, "costruito: estremo inferiore del terzo intervallo IRS (90)"),
    ("900-92-0000", True, "costruito: estremo superiore del terzo intervallo IRS (92)"),
    ("900-94-0000", True, "costruito: estremo inferiore del quarto intervallo IRS (94)"),
    ("900-99-0000", True, "costruito: estremo superiore del quarto intervallo IRS (99)"),
    ("912-49-1234", False, "costruito: gruppo 49, appena sotto l'intervallo 50-65"),
    ("912-66-1234", False, "costruito: gruppo 66, nel buco fra 65 e 70"),
    ("912-69-1234", False, "costruito: gruppo 69, ultimo del buco fra 65 e 70"),
    ("912-89-1234", False, "costruito: gruppo 89, nel buco fra 88 e 90"),
    ("912-93-1234", False, "costruito: gruppo 93, il buco singolo fra 92 e 94"),
    ("812-78-1234", False, "non inizia per 9: e' un SSN, non un ITIN"),
    ("91278123", False, "otto cifre"),
)


# ---------------------------------------------------------------------------
# Stati Uniti — ABA routing transit number
# ---------------------------------------------------------------------------

# Intervalli delle prime due cifre effettivamente in uso (Federal Reserve /
# Accuity):
#   00-12  distretti della Federal Reserve (primary)
#   21-32  thrift institutions
#   61-72  electronic transaction identifiers
#   80     traveler's cheque
# Fuori da questi intervalli il numero non e' un routing number, anche se
# il checksum torna: il checksum e' a una cifra, quindi da solo lascia
# passare un decimo di tutto.
_ABA_INTERVALLI = ((0, 12), (21, 32), (61, 72), (80, 80))


def aba_routing_ok(candidate: str) -> bool:
    """Routing number ABA: checksum pesato 3-7-1 **piu'** gli intervalli.

    Il solo checksum non basta e la ragione e' aritmetica: e' un controllo
    modulo 10 su nove cifre, quindi una sequenza casuale lo supera una
    volta su dieci. Con gli intervalli delle prime due cifre — che coprono
    poco piu' di un terzo delle combinazioni — si scende al 3.8% misurato
    su duecentomila sequenze casuali. E' la differenza fra un validatore
    che segnala e uno che decide.
    """
    s = _pulisci(candidate)
    if len(s) != 9 or not s.isdigit():
        return False
    prefisso = int(s[:2])
    if not any(basso <= prefisso <= alto for basso, alto in _ABA_INTERVALLI):
        return False
    d = [int(c) for c in s]
    totale = (
        3 * (d[0] + d[3] + d[6])
        + 7 * (d[1] + d[4] + d[7])
        + (d[2] + d[5] + d[8])
    )
    return totale % 10 == 0


VETTORI_ABA_ROUTING = (
    ("011000015", True, "routing number pubblicato della Federal Reserve Bank of Boston; ricalcolato: 3*0+7*2+6=20"),
    ("021000021", True, "routing number pubblicato di JPMorgan Chase (New York); ricalcolato: totale 30"),
    ("121000358", True, "routing number pubblicato di Bank of America (San Francisco); ricalcolato: totale 70"),
    ("011 000 015", True, "esempio Federal Reserve Bank of Boston, con separatori"),
    ("011000016", False, "esempio FRB Boston con l'ultima cifra alterata: il checksum 3-7-1 non torna"),
    ("130000006", False, "costruito: checksum corretto (totale 30) ma prefisso 13, fuori dagli intervalli in uso"),
    ("500000005", False, "costruito: checksum corretto (totale 20) ma prefisso 50, fuori dagli intervalli in uso"),
    ("800000006", True, "costruito: prefisso 80 (traveler's cheque) e checksum corretto (totale 30)"),
    ("01100001", False, "otto cifre"),
    ("0110000150", False, "dieci cifre"),
    ("01100001A", False, "una lettera"),
)


# ---------------------------------------------------------------------------
# Canada — Social Insurance Number
# ---------------------------------------------------------------------------

def sin_ok(candidate: str) -> bool:
    """SIN canadese: Luhn **piu'** le prime cifre mai assegnate.

    La prima cifra dice dove il numero e' stato registrato (1 Atlantico,
    2-3 Quebec, 4-5 Ontario, 6 Praterie/NWT/Nunavut, 7 BC/Yukon, 9
    residenti temporanei). **0 e 8 non sono mai stati assegnati**, quindi
    un numero che inizia cosi' e' invalido anche se il Luhn torna.

    Questo vincolo e' quello che rende il validatore utile: senza, ogni
    sequenza di nove cifre passerebbe una volta su dieci — e nove cifre in
    un documento sono anche un SSN, un numero di pratica, un importo.

    Attenzione: l'esempio piu' diffuso in rete per illustrare il Luhn sul
    SIN e' 046 454 286, che il Luhn lo passa ma inizia per 0. Qui e'
    trattato come invalido, ed e' la scelta giusta per la redazione: chi
    scrive quel numero in un documento sta quasi sempre copiando l'esempio,
    non il SIN di una persona.
    """
    s = _pulisci(candidate)
    if len(s) != 9 or not s.isdigit():
        return False
    if s[0] in ("0", "8"):
        return False
    return _luhn(s)


VETTORI_SIN = (
    ("130 692 544", True, "costruito: prima cifra 1 (Atlantico), cifra di controllo Luhn calcolata (somma 40)"),
    ("130692544", True, "stesso valore senza separatori"),
    ("046 454 286", False, "esempio piu' diffuso in rete per illustrare il Luhn sul SIN: passa il Luhn ma inizia per 0, mai assegnata"),
    ("830692547", False, "costruito: Luhn corretto (somma 50) ma prima cifra 8, mai assegnata"),
    ("130692545", False, "l'esempio costruito con l'ultima cifra alterata: il Luhn non torna"),
    ("13069254", False, "otto cifre"),
    ("1306925444", False, "dieci cifre"),
    ("13069254A", False, "una lettera"),
)


# ---------------------------------------------------------------------------
# Australia — ABN
# ---------------------------------------------------------------------------

_ABN_PESI = (10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19)


def abn_ok(candidate: str) -> bool:
    """ABN: sottrarre 1 alla prima cifra, pesare, e verificare il mod-89.

    Il modulo 89 e' quello che rende questo controllo il piu' forte del
    pacchetto: un numero casuale di undici cifre lo supera circa una volta
    su 89, cioe' l'1.1%. In pratica, se ``abn_ok`` dice di si', e' un ABN.
    Qui il validatore decide da solo, senza contesto.

    La sottrazione di 1 dalla prima cifra e' la parte che si dimentica, e
    non e' un dettaglio: e' cio' che impedisce a un ABN valido di restare
    valido quando ci si aggiunge davanti uno zero. Per la stessa ragione un
    ABN non inizia mai per 0, e qui si rifiuta invece di andare in negativo.
    """
    s = _pulisci(candidate)
    if len(s) != 11 or not s.isdigit():
        return False
    d = [int(c) for c in s]
    if d[0] == 0:
        return False
    d[0] -= 1
    return sum(x * peso for x, peso in zip(d, _ABN_PESI)) % 89 == 0


VETTORI_ABN = (
    ("51 824 753 556", True, "ABN dell'Australian Taxation Office, usato come esempio nella documentazione ABR sull'algoritmo; ricalcolato: somma 534 = 89*6"),
    ("51824753556", True, "stesso valore senza separatori"),
    ("48 123 123 124", True, "esempio ricorrente nella documentazione ABR di validazione; ricalcolato: somma 267 = 89*3"),
    ("51824753557", False, "l'ABN dell'ATO con l'ultima cifra alterata: somma 553, resto 19"),
    ("51824753566", False, "l'ABN dell'ATO con la penultima cifra alterata: il mod-89 non torna"),
    ("01824753556", False, "costruito: un ABN non inizia mai per 0 (la sottrazione di 1 andrebbe in negativo)"),
    ("5182475355", False, "dieci cifre"),
    ("518247535566", False, "dodici cifre"),
    ("5182475355A", False, "una lettera"),
)


# ---------------------------------------------------------------------------
# Australia — TFN
# ---------------------------------------------------------------------------

_TFN_PESI = (1, 4, 3, 7, 5, 8, 6, 9, 10)


def tfn_ok(candidate: str) -> bool:
    """TFN: somma pesata modulo 11, su otto o nove cifre.

    Le due lunghezze non sono un'ambiguita' del formato: i TFN emessi prima
    degli anni '80 hanno otto cifre e sono tuttora validi. Si usano i primi
    otto pesi, non gli ultimi otto — ed e' il punto in cui questo algoritmo
    si sbaglia piu' spesso, perche' la scelta e' invisibile finche' non si
    prova un TFN vecchio.

    Il modulo 11 su nove cifre lascia passare circa il 9% dei candidati:
    piu' forte del Luhn ma non abbastanza per decidere da solo su un numero
    cosi' corto. Accanto ci vuole una parola di contesto.
    """
    s = _pulisci(candidate)
    if len(s) not in (8, 9) or not s.isdigit():
        return False
    pesi = _TFN_PESI[: len(s)]
    return sum(int(c) * peso for c, peso in zip(s, pesi)) % 11 == 0


VETTORI_TFN = (
    ("123 456 782", True, "TFN di esempio dell'ATO, ricorrente nella documentazione dell'algoritmo; ricalcolato: somma 253 = 11*23"),
    ("123456782", True, "stesso valore senza separatori"),
    ("876 543 210", True, "costruito applicando l'algoritmo ATO: somma 154 = 11*14"),
    ("12345679", True, "costruito: forma storica a otto cifre, ultima cifra calcolata con i primi otto pesi (somma 242 = 11*22)"),
    ("123456789", False, "l'esempio ATO con l'ultima cifra alterata: somma 323, resto 4"),
    ("12345678", False, "costruito: otto cifre, somma 233, resto 2"),
    ("1234567", False, "sette cifre: nessuna forma del TFN"),
    ("1234567820", False, "dieci cifre"),
    ("12345678A", False, "una lettera"),
)


# ---------------------------------------------------------------------------
# Regno Unito — codice postale
# ---------------------------------------------------------------------------

# L'espressione regolare ufficiale del Bulk Data Transfer (Royal Mail /
# Government Data Standards Catalogue). Non e' stata riscritta apposta:
# copre anche i casi che nessuno ricorda — i territori d'oltremare (ASCN
# Ascensione, STHL Sant'Elena, TDCU Tristan da Cunha, BBND Diego Garcia,
# BIQQ/FIQQ/SIQQ British Antarctic/Falkland/South Georgia, PCRN Pitcairn,
# TKCA Turks e Caicos), le poste militari BFPO, il Girobank GIR 0AA — e
# riscriverla significa perderli.
_RE_UK_POSTCODE = re.compile(
    r"^(([A-Z]{1,2}[0-9][A-Z0-9]?|ASCN|STHL|TDCU|BBND|[BFS]IQQ|PCRN|TKCA)"
    r" ?[0-9][A-Z]{2}"
    r"|BFPO ?[0-9]{1,4}"
    r"|(KY[0-9]|MSR|VG|AI)[ -]?[0-9]{4}"
    r"|[A-Z]{2} ?[0-9]{2}"
    r"|GE ?CX|GIR ?0A{2}|SAN ?TA1)$"
)


def uk_postcode_ok(candidate: str) -> bool:
    """Codice postale britannico secondo l'espressione regolare ufficiale.

    Qui non si toglie tutto: il separatore e' **parte del formato**, e
    l'espressione ufficiale sa gia' dove ammetterlo (lo spazio facoltativo
    fra outward e inward code, il trattino nei codici caraibici). Passare
    la stringa gia' compattata cambierebbe cio' che l'espressione vede.

    Nessun checksum, come per ogni codice postale. E c'e' un ramo largo di
    cui essere consapevoli: ``[A-Z]{2} ?[0-9]{2}`` — due lettere e due
    cifre — serve ai territori d'oltremare ma accetta anche sequenze
    comunissime tipo "AB 12". Su testo libero e' una sorgente di falsi
    positivi: il codice postale va cercato in coda a un indirizzo, non in
    mezzo a una frase.
    """
    if not candidate:
        return False
    s = re.sub(r"\s+", " ", candidate.strip()).upper()
    return bool(_RE_UK_POSTCODE.match(s))


VETTORI_UK_POSTCODE = (
    ("EC1A 1BB", True, "esempio di formato pubblicato da Royal Mail (formato AA9A 9AA)"),
    ("W1A 0AX", True, "esempio di formato pubblicato da Royal Mail (formato A9A 9AA)"),
    ("M1 1AE", True, "esempio di formato pubblicato da Royal Mail (formato A9 9AA)"),
    ("B33 8TH", True, "esempio di formato pubblicato da Royal Mail (formato A99 9AA)"),
    ("CR2 6XH", True, "esempio di formato pubblicato da Royal Mail (formato AA9 9AA)"),
    ("DN55 1PT", True, "esempio di formato pubblicato da Royal Mail (formato AA99 9AA)"),
    ("SW1A 1AA", True, "codice postale pubblico di Buckingham Palace"),
    ("GIR 0AA", True, "codice storico del Girobank, ramo dedicato nell'espressione ufficiale"),
    ("SAN TA1", True, "codice di Royal Mail per la posta a Babbo Natale, ramo dedicato nell'espressione ufficiale"),
    ("BFPO 1234", True, "British Forces Post Office, ramo dedicato nell'espressione ufficiale"),
    ("ec1a 1bb", True, "esempio Royal Mail in minuscolo: il validatore normalizza"),
    ("EC1A1BB", True, "esempio Royal Mail senza spazio: l'espressione ufficiale lo rende facoltativo"),
    ("EC1A  1BB", True, "esempio Royal Mail con doppio spazio: normalizzato a uno"),
    ("EC1A 1B", False, "manca una lettera nell'inward code"),
    ("EC1A 1BBB", False, "una lettera di troppo nell'inward code"),
    ("1EC A1BB", False, "outward code che inizia per cifra"),
    ("12345", False, "cinque cifre: e' uno ZIP statunitense, non un postcode"),
    ("EC1A 1B1", False, "cifra dove l'inward code vuole una lettera"),
    ("", False, "stringa vuota"),
)


# ---------------------------------------------------------------------------
# Nord America — numerazione telefonica NANP
# ---------------------------------------------------------------------------

_RE_TEL_SEPARATORI = re.compile(r"[\s.()\-+‐-―]")


def nanp_phone_ok(candidate: str) -> bool:
    """Numero NANP: **nessun checksum**, solo il piano di numerazione.

    Le regole strutturali sono tre e vengono tutte dal piano NANP:

    - NPA (prefisso) e NXX (centrale) iniziano per 2-9: la prima cifra 0 e
      1 e' riservata all'operatore e al prefisso interurbano;
    - il formato N11 (211, 311, ... 911) e' riservato ai servizi, quindi
      non e' ne' un NPA ne' un NXX assegnabile;
    - 555-0100..0199 e' riservato da NANPA alla **finzione**.

    L'ultima regola merita una parola, perche' e' l'unica in cui il
    validatore dice di no a un numero perfettamente ben formato. Un
    555-01xx non e' il numero di nessuno: e' quello che sta nei film, nei
    manuali e negli esempi di documentazione. Sostituirlo non protegge
    nessuno e sporca il conteggio del rapporto — e un conteggio di cui non
    ci si fida vale meno di nessun conteggio. Quindi qui e' **invalido**:
    per la redazione, "non e' un dato personale" e "non e' un numero" hanno
    lo stesso esito.

    Restano circa 6.3 miliardi di combinazioni ammesse su 10 miliardi (il
    62.7% misurato): come filtro e' debolissimo, quasi quanto l'SSN. Dieci
    cifre di seguito sono anche una data piu' un
    protocollo. Serve il contesto, o la punteggiatura tipica (parentesi
    intorno al NPA, trattino prima delle ultime quattro cifre).
    """
    if not candidate:
        return False
    s = _RE_TEL_SEPARATORI.sub("", candidate)
    if not s.isdigit():
        return False
    # Il "1" davanti e' il prefisso interurbano del NANP, non parte del
    # numero: si toglie, altrimenti ogni numero scritto per esteso
    # ("1-800-...") avrebbe una cifra di troppo.
    if len(s) == 11 and s[0] == "1":
        s = s[1:]
    if len(s) != 10:
        return False
    npa, nxx, linea = s[:3], s[3:6], s[6:]
    if npa[0] in "01" or nxx[0] in "01":
        return False
    if npa[1] == "1" and npa[2] == "1":
        return False
    if nxx[1] == "1" and nxx[2] == "1":
        return False
    return not (nxx == "555" and linea.startswith("01"))


VETTORI_NANP_PHONE = (
    ("(212) 555-1234", True, "NPA 212 assegnato a New York; NXX 555 valido; linea 1234 fuori dall'intervallo fittizio"),
    ("212-555-1234", True, "stesso numero, forma con soli trattini"),
    ("2125551234", True, "stesso numero, senza separatori"),
    ("+1 212 555 1234", True, "stesso numero in formato E.164 con prefisso di Paese"),
    ("1-800-555-1212", True, "800-555-1212, l'informazione elenco toll-free: NPA, NXX e linea tutti assegnabili"),
    ("212-555-0100", False, "NANPA riserva 555-0100..0199 alla finzione: estremo inferiore"),
    ("212-555-0199", False, "NANPA riserva 555-0100..0199 alla finzione: estremo superiore"),
    ("(212) 555-0143", False, "555-0143, numero fittizio ricorrente nei manuali: dentro l'intervallo riservato"),
    ("212-555-0200", True, "costruito: appena fuori dall'intervallo fittizio, quindi assegnabile"),
    ("212-555-0099", True, "costruito: appena sotto l'intervallo fittizio, quindi assegnabile"),
    ("911-555-1234", False, "911 e' un N11 riservato ai servizi: non e' un NPA assegnabile"),
    ("411-555-1234", False, "411 e' un N11 riservato ai servizi"),
    ("212-911-1234", False, "N11 non e' assegnabile nemmeno come NXX"),
    ("212-411-1234", False, "idem: 411 come NXX"),
    ("112-555-1234", False, "il NPA non puo' iniziare per 1"),
    ("012-555-1234", False, "il NPA non puo' iniziare per 0"),
    ("212-155-1234", False, "il NXX non puo' iniziare per 1"),
    ("212-055-1234", False, "il NXX non puo' iniziare per 0"),
    ("212555123", False, "nove cifre"),
    ("21255512345", False, "undici cifre senza prefisso interurbano 1"),
    ("212-555-123A", False, "una lettera"),
    ("", False, "stringa vuota"),
)


# ---------------------------------------------------------------------------
# ICAO 9303 — cifra di controllo della zona a lettura ottica
# ---------------------------------------------------------------------------

_MRZ_PESI = (7, 3, 1)


def mrz_check_digit_ok(candidate: str) -> bool:
    """Cifra di controllo ICAO 9303 (documento, nascita, scadenza, composita).

    Il candidato e' il campo **con la sua cifra di controllo in coda**:
    "L898902C<3" e non "L898902C<". E' la forma in cui il campo compare
    nella MRZ, quindi e' anche la forma in cui lo si estrae.

    Il riempitivo '<' vale 0, non e' un carattere da scartare: toglierlo
    farebbe scorrere i pesi 7-3-1 e il controllo darebbe un altro numero.
    E' l'errore piu' comune su questo algoritmo, ed e' silenzioso — il
    risultato resta una cifra plausibile.

    Modulo 10 su un campo corto: un candidato casuale passa una volta su
    dieci. Il controllo serve a confermare un campo gia' individuato dalla
    struttura della MRZ, non a trovarne uno dentro un testo.
    """
    s = _pulisci(candidate)
    if len(s) < 2:
        return False
    dati, check = s[:-1], s[-1]
    if not check.isdigit():
        return False
    totale = 0
    for i, c in enumerate(dati):
        if c.isdigit():
            valore = int(c)
        elif "A" <= c <= "Z":
            valore = ord(c) - 55  # 'A' -> 10 ... 'Z' -> 35
        elif c == "<":
            valore = 0
        else:
            return False
        totale += valore * _MRZ_PESI[i % 3]
    return totale % 10 == int(check)


VETTORI_MRZ_CHECK_DIGIT = (
    ("L898902C<3", True, "campo numero-documento dello specimen ICAO 9303; ricalcolato: somma 313, cifra 3"),
    ("7408122", True, "campo data-di-nascita dello specimen ICAO 9303 (740812 + 2); ricalcolato: somma 122"),
    ("1204159", True, "campo data-di-scadenza dello specimen ICAO 9303 (120415 + 9); ricalcolato: somma 49"),
    ("l898902c<3", True, "stesso campo ICAO in minuscolo: il validatore normalizza"),
    ("L898902C<4", False, "campo ICAO con la cifra di controllo alterata"),
    ("L898902C<0", False, "campo ICAO con un'altra cifra di controllo alterata"),
    ("L898902C374081221204159ZE184226B<<<<<10", True, "cifra di controllo composita della seconda riga TD3 dello specimen ICAO 9303 (documento+nascita+scadenza+dati opzionali); ricalcolata: somma 790"),
    ("L898902C374081221204159ZE184226B<<<<<11", False, "stessa composita ICAO con la cifra alterata"),
    ("12<346", True, "costruito: riempitivo in mezzo al campo, somma 7+6+0+21+12=46"),
    ("12346", False, "lo stesso campo con il riempitivo tolto: i pesi 7-3-1 scorrono, somma 44, la cifra 6 non torna piu' — il '<' vale 0 ma occupa una posizione"),
    ("7408123", False, "data di nascita ICAO con la cifra di controllo alterata"),
    ("L898902C<X", False, "cifra di controllo che non e' una cifra"),
    ("L898902C*3", False, "carattere fuori dall'alfabeto ICAO (solo 0-9, A-Z, '<')"),
    ("3", False, "un solo carattere: non ci sono dati da controllare"),
    ("", False, "stringa vuota"),
)


# ---------------------------------------------------------------------------
# Banco di prova
# ---------------------------------------------------------------------------

# La tabella lega ogni funzione ai suoi vettori. Tenerla esplicita invece di
# frugare in globals() serve a una cosa sola: se qualcuno aggiunge una
# funzione e si dimentica i vettori, il banco resta verde e nessuno se ne
# accorge. Qui la dimenticanza si vede, perche' la riga non c'e'.
BANCO = (
    ("nhs_number_ok", nhs_number_ok, VETTORI_NHS_NUMBER),
    ("nino_ok", nino_ok, VETTORI_NINO),
    ("ssn_ok", ssn_ok, VETTORI_SSN),
    ("itin_ok", itin_ok, VETTORI_ITIN),
    ("aba_routing_ok", aba_routing_ok, VETTORI_ABA_ROUTING),
    ("sin_ok", sin_ok, VETTORI_SIN),
    ("abn_ok", abn_ok, VETTORI_ABN),
    ("tfn_ok", tfn_ok, VETTORI_TFN),
    ("uk_postcode_ok", uk_postcode_ok, VETTORI_UK_POSTCODE),
    ("nanp_phone_ok", nanp_phone_ok, VETTORI_NANP_PHONE),
    ("mrz_check_digit_ok", mrz_check_digit_ok, VETTORI_MRZ_CHECK_DIGIT),
)


def esegui_banco() -> int:
    """Passa ogni vettore nella sua funzione. Restituisce i fallimenti.

    CodeQL py/clear-text-logging-sensitive-data: la stampa qui sotto mostra
    SSN, NINO e simili in chiaro, ed e' voluto. Quei valori sono le costanti
    ``VETTORI_*`` di questo file — pubblicate da chi emette l'identificativo
    oppure costruite applicando l'algoritmo, come dice il terzo elemento di
    ogni tupla. Nessun dato di chi usa il programma passa da questa funzione:
    e' un banco che si lancia a mano (``python -m mr_rao.en_formats``) e la
    riga esce solo quando un vettore fallisce. Mascherarla renderebbe
    impossibile capire *quale* vettore e' andato storto, che e' l'unica cosa
    che quella riga serve a dire.
    """
    falliti = 0
    totali = 0
    for nome, funzione, vettori in BANCO:
        errori = []
        for valore, atteso, provenienza in vettori:
            totali += 1
            try:
                ottenuto = funzione(valore)
            except Exception as exc:  # un'eccezione e' un fallimento, non un crash
                errori.append((valore, atteso, f"eccezione {exc!r}", provenienza))
                continue
            if ottenuto != atteso:
                errori.append((valore, atteso, ottenuto, provenienza))
        falliti += len(errori)
        esito = "PASS" if not errori else "FAIL"
        print(f"[{esito}] {nome:<20} {len(vettori) - len(errori)}/{len(vettori)}")
        for valore, atteso, ottenuto, provenienza in errori:
            print(f"       {valore!r}: atteso {atteso}, ottenuto {ottenuto} — {provenienza}")
    print("-" * 60)
    print(f"{totali - falliti}/{totali} vettori superati, {falliti} falliti")
    return falliti


if __name__ == "__main__":
    sys.exit(1 if esegui_banco() else 0)
