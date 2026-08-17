# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Riconoscimento e sostituzione dei dati personali (formati italiani).

Ogni riconoscitore e' un'espressione regolare accompagnata da un validatore:
il pattern propone, il validatore decide. E' quello che tiene bassi i falsi
positivi senza rinunciare alla copertura — un IBAN si accetta solo se il
mod-97 torna, una carta solo se passa Luhn, un numero e' un telefono solo
con prefisso, separatore o parola di contesto.

Per i nomi di persona gli elenchi non bastano mai, quindi valgono anche le
regole di contesto: un titolo professionale davanti, un indirizzo di posta
accanto, un nome proprio riconosciuto che tira dentro la parola successiva.
C'era una quarta regola, ``name_guess``: due parole maiuscole che non
sembrano parole italiane sono nome e cognome, **senza nessun riscontro
negli elenchi**. E' stata spenta di default nella 1.7.2 e **ritirata nella
1.13.0**, perche' indovinava senza corroborazione: su 27 moduli
amministrativi in bianco -- documenti che non contengono un solo dato
personale -- costava 2 529 sostituzioni sbagliate contro 27, novantaquattro
volte tanto. Un'opzione che nessuno deve accendere non e' una scelta, e'
una trappola con un'etichetta.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

from mr_rao.en_formats import (
    aba_routing_ok,
    abn_ok,
    itin_ok,
    mrz_check_digit_ok,
    nhs_number_ok,
    nino_ok,
    sin_ok,
    ssn_ok,
    tfn_ok,
)
from mr_rao.it_names import COMMON_CAPITALIZED, FIRST_NAMES, SURNAMES


# ---------------------------------------------------------------------------
# Codici e conti
# ---------------------------------------------------------------------------

# Codice Fiscale (16 alphanumeric, simplified check)
_RE_CF = re.compile(
    r"\b([A-Z]{6}\d{2}[A-EHLMPRST]\d{2}[A-Z]\d{3}[A-Z])\b",
    re.IGNORECASE,
)

# L'OMOCODIA, cioe' il codice fiscale che non ha piu' le cifre dove il
# pattern se le aspetta.
#
# Quando due persone otterrebbero lo stesso codice, l'Agenzia delle Entrate
# ne cambia una: sostituisce le cifre, partendo da destra, con le lettere
# L M N P Q R S T U V. `RSSMRA85T10A562S` diventa `RSSMRA85T1NA562...`, e la
# forma «sei lettere, due cifre, una lettera, due cifre...» non torna piu'.
#
# Misurato su 300 codici con omocodia: **zero** riconosciuti. Il 60% finiva
# fra i sospetti perche' qualche altro pattern ci inciampava, il 40% spariva
# del tutto -- e sono codici fiscali veri, di persone vere, emessi
# regolarmente.
#
# QUI LE CIFRE POSSONO ESSERE LETTERE, MA IL PREZZO E' CHE IL CONTO DEVE
# TORNARE. Il pattern stretto qui sopra sostituisce anche quando il
# carattere di controllo non torna, perche' su un dato personale l'errore va
# fatto nella direzione prudente. Questo no: ammettendo lettere dove
# andrebbero cifre la forma diventa quasi una parola qualsiasi di sedici
# caratteri, e senza l'aritmetica a smentirla si redigerebbe mezzo
# documento. E' la stessa regola di P3.7 -- si allenta solo dove c'e' un
# conto che possa dire di no.
_OMOCODIA_LETTERE = "LMNPQRSTUV"
_RE_CF_OMOCODIA = re.compile(
    rf"\b([A-Z]{{6}}[\dLMNPQRSTUV]{{2}}[A-EHLMPRST][\dLMNPQRSTUV]{{2}}"
    rf"[A-Z][\dLMNPQRSTUV]{{3}}[A-Z])\b",
    re.IGNORECASE,
)

# Partita IVA (IT + 11 digits, or bare 11 digits in fiscal context)
_RE_PIVA = re.compile(
    r"\b(?:IT)?(\d{11})\b",
    re.IGNORECASE,
)

# IBAN (generic + IT). Case-sensitive on purpose: lowercase "words" like
# "ab12cdefghijklm" are not IBANs. Every candidate is checked with mod-97.
_RE_IBAN = re.compile(r"\b([A-Z]{2}\d{2}[A-Z0-9]{11,30})\b")

# L'IBAN come lo stampano le banche: a gruppi di quattro. Il pattern sopra
# pretende i caratteri attaccati, quindi su "IT60 X054 2811 1010 0000 0123
# 456" — la forma piu' comune su carta intestata, bonifici e fatture — non
# trovava nulla. Qui i gruppi sono ammessi, e a scartare i falsi candidati
# ci pensa il mod-97 come sempre.
#
# **Gruppi da UNO, non da due.** Un IBAN si stampa a gruppi di quattro, e
# quando la sua lunghezza non e' divisibile per quattro l'ultimo gruppo e'
# piu' corto -- fino a un carattere solo. Succede a tutti i Paesi la cui
# lunghezza da' resto 1: Portogallo (25), Svizzera (21), Croazia (21),
# Bulgaria (22 no, 22 da' resto 2)... e su quelli il pattern che pretendeva
# almeno due caratteri per gruppo **non riconosceva niente**:
#
#     PT92 DO9G MNU7 7VTU UJ59 6LGU A   ->   restava in chiaro, per intero
#
# Non era un troncamento -- sarebbe stato peggio, perche' il rapporto
# avrebbe detto «1 IBAN sostituito» -- ma un silenzio: zero IBAN trovati su
# un documento che ne conteneva uno.
#
# Ammettere gruppi da un carattere rende il pattern goloso, e va bene
# **perche' adesso c'e' chi lo taglia**: `_prefisso_a_norma` riduce il
# candidato alla lunghezza che il registro ISO 13616 prescrive per quel
# Paese, quindi cio' che il pattern prende in piu' torna al testo invece di
# far fallire il mod-97.
#
# **L'a-capo, uno solo.** Un IBAN stampato su una carta intestata o una
# fattura viene mandato a capo dall'estrattore come qualunque altra riga, e
# fino alla 1.20.0 il separatore ammetteva solo lo spazio e il trattino:
#
#     IT60 X054 2811 1010
#     0000 0123 456          ->  restava in chiaro, per intero
#
# E' lo stesso difetto gia' pagato sugli indirizzi di posta
# (`_RE_EMAIL_SPEZZATA`), e la stessa cura: si concede **un** ritorno a capo,
# non `\s` libero. Il motivo del limite e' una colonna di codici in tabella
# -- li' ogni cella e' un a-capo, e con `\s` libero due codici diversi
# diventerebbero un candidato solo, a cavallo di due righe. A quel punto il
# mod-97 boccia e l'IBAN vero resta in chiaro: la solita sconfitta
# silenziosa.
#
# **Gruppi fino a trenta caratteri, non sei.** Un IBAN non si stampa solo a
# quattro: su un estratto conto capita spezzato secondo la sua struttura --
# `IT87 D6763 451995256291522385`, cioe' paese+controllo, CIN+ABI, e il
# resto attaccato. Con il tetto a sei quel terzo blocco non entrava, e
# l'IBAN restava in chiaro **senza nemmeno un sospetto**: 29 casi sul banco
# del richiamo.
#
# Alzare il tetto rende il pattern molto goloso, e va bene per la stessa
# ragione di prima: `_prefisso_a_norma` taglia alla lunghezza di legge e
# restituisce al testo tutto cio' che avanza. Un pattern goloso davanti a un
# taglio esatto non costa niente; sarebbe costato molto senza.
_RE_IBAN_SPAZIATO = re.compile(
    r"\b([A-Z]{2}\d{2}(?:[ \-\n][A-Z0-9]{1,30}){2,9})(?![\w])"
)

# L'IBAN attaccato alla propria etichetta: "IBANIT60X05428…". Non e' un caso
# di scuola, e' come esce dall'OCR su una scansione degradata -- lo spazio
# fra l'etichetta e il valore si perde, e i due pattern qui sopra, che
# cominciano entrambi con \b, non arrivano nemmeno a proporlo. Il dato
# passerebbe il mod-97: sono le stesse cifre di prima.
#
# Cosa e' ammesso davanti, e perche' solo quello: **lettere**. Una parola
# incollata e' un'etichetta rimasta attaccata; una cifra davanti vorrebbe
# dire entrare in mezzo a un numero piu' lungo, e cio' che se ne ritaglia
# non e' un campo. Il resto non cambia di una virgola: a dire se quel pezzo
# e' un IBAN resta il mod-97, come per ogni altro candidato.
#
# I due pattern coprono la parola intera, dall'inizio alla fine: e' cio' che
# permette di provare i punti di taglio uno per uno senza che la prima prova
# sbagliata si mangi anche le altre.
_RE_IBAN_INCOLLATO = re.compile(
    r"(?<![\w-])[A-Za-z]{2,}[A-Z]{2}\d{2}[A-Z0-9]{11,30}(?![\w-])"
)
_RE_IBAN_SPAZIATO_INCOLLATO = re.compile(
    r"(?<![\w-])(?P<etichetta>[A-Za-z]{2,})"
    r"(?P<valore>[A-Z]{2}\d{2}(?:[ \-][A-Z0-9]{2,6}){2,9})(?![\w])"
)

# La forma che il candidato deve avere, da sola: serve a provare dove finisce
# l'etichetta e dove comincia l'IBAN.
_RE_SOLO_IBAN = re.compile(r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}")

# Carta di pagamento: 13-19 cifre che iniziano con un IIN plausibile e
# passano il controllo di Luhn. Senza Luhn qualunque numero lungo finirebbe
# redatto; con Luhn e' il numero stesso a dire se e' una carta.
#
# Il lookbehind dice due cose diverse in una riga sola:
#
#   (?<![0-9])     mai in mezzo a un numero piu' lungo. Questo e' il vincolo
#                  serio, ed e' rimasto.
#   (?<![0-9]\.)   il punto e' ammesso, **tranne** quando e' un separatore
#                  decimale -- cioe' quando ha una cifra davanti. Cosi'
#                  «123.4539148803436467» resta la coda di un numero, mentre
#                  i puntini di guida di un modulo («.....3760000000000061»)
#                  e l'etichetta incollata («carta6011111111111174») non
#                  fanno piu' perdere il dato.
#
# Prima era `(?<![\w.])`, che rifiutava insieme le tre cose: la cifra, la
# lettera e il punto. Il banco delle scansioni ha mostrato che due su tre
# erano proprio le forme in cui una carta arriva da un modulo scansionato.
# Il **punto come separatore fra i gruppi**, non solo davanti: alcuni
# gestionali stampano `4111.1111.1111.1111`. Il telefono lo accettava gia'
# («010.2471234»), la carta no, e non c'era una ragione: e' lo stesso segno
# usato nello stesso modo.
#
# Non apre agli importi, ed e' il motivo per cui e' sicuro: `[3-6]\d{3}`
# pretende **quattro cifre attaccate** in testa, quindi «3.500,00» e
# «4.111.111» -- dove il punto separa le migliaia dopo una cifra sola --
# non arrivano nemmeno a proporsi. E a dire l'ultima parola resta Luhn.
_RE_CARD = re.compile(
    r"(?<![0-9])(?<![0-9]\.)([3-6]\d{3}(?:[ \-.]?\d{2,6}){2,4})(?![\w])"
)

# Coordinate bancarie italiane senza IBAN: CIN + ABI (5) + CAB (5) + conto
# (12). Senza questo riconoscitore il numero non spariva del tutto: veniva
# spezzato e sostituito dal riconoscitore dei telefoni, quindi il rapporto
# diceva "2 telefoni" dove c'erano delle coordinate bancarie. Un conteggio
# che sbaglia categoria e' peggio di un conteggio che manca, perche' chi
# legge il rapporto si fida.
_RE_BBAN = re.compile(
    r"(?<![\w.])([A-Z])[\s\-]?(\d{5})[\s\-]?(\d{5})[\s\-]?([0-9A-Z]{12})(?![\w])"
)

# La forma discorsiva: "ABI 05428 CAB 11101 CIN X".
_RE_ABI_CAB = re.compile(
    r"(?i)\bABI[\s:]*\d{5}\b[\s,;]*(?:\bCAB[\s:]*\d{5}\b)?"
    r"(?:[\s,;]*\bCIN[\s:]*[A-Z]\b)?"
    # **E il numero di conto che segue**, con o senza etichetta.
    # `ABI 03069 CAB 09606 000012345678` lasciava in chiaro proprio la
    # parte che identifica il conto: le prime due sono coordinate
    # dell'istituto — le stesse per tutti i correntisti di quella filiale —
    # e l'unica cifra personale restava scritta.
    r"(?:[\s,;]*(?:\bc(?:/|\.)?c\.?\b|\bconto\b)?[\s:.n°]*\d{10,14}\b)?"
)

# Il numero di conto **con l'etichetta davanti**: «c/c 000012345678»,
# «conto corrente n. 12345678», «numero di conto 3331234567».
#
# **Due difetti in uno, e il secondo e' peggiore del primo.** Un conto
# etichettato restava in chiaro — ed e' un dato bancario dichiarato, non un
# indizio. E quando le cifre somigliavano a un cellulare veniva contato
# **fra i telefoni**: `numero di conto 3331234567` usciva `{{PHONE_1}}`. Un
# conteggio che sbaglia categoria e' peggio di un conteggio che manca,
# perche' chi legge il rapporto si fida — e' la stessa ragione per cui il
# riconoscitore del BBAN era stato scritto.
#
# Sta qui, e non fra i telefoni, perche' i passi di questo pacchetto girano
# **prima** (43 contro 60): quando arriva il riconoscitore dei telefoni il
# numero non c'e' piu'.
#
# L'etichetta e' obbligatoria e non c'e' nessuna forma nuda: da 8 a 16 cifre
# senza contesto sono un protocollo, un codice articolo, una data lunga.
_RE_CONTO_ETICHETTATO = re.compile(
    r"(?i)(?P<eti>\bc(?:/|\.)?c\.?\b|\bconto\s+corrente\b|\bnumero\s+di\s+conto\b"
    r"|\bconto\s+n(?:um(?:ero)?)?\b)"
    r"[\s:.n°]*"
    r"(?P<val>\d[\d\s.\-]{6,20}\d)(?![\w])"
)


# ---------------------------------------------------------------------------
# Contatti
# ---------------------------------------------------------------------------

# URL. Solo con schema esplicito o con "www.": e' il confine che si
# riconosce a occhio, e non trasforma ogni "nome.it" del testo in un link.
_RE_URL = re.compile(
    r"\b(?:https?|ftp|ftps)://[^\s<>\"'`\]\)]+"
    r"|(?<![\w.])www\.[^\s<>\"'`\]\)]+",
    re.IGNORECASE,
)

# Un numero di telefono e' una sequenza di 6-15 cifre con separatori interni
# facoltativi, eventualmente preceduta da un prefisso internazionale. Il
# pattern propone soltanto: _phone_is_plausible() decide, perche' un numero
# di protocollo e una data hanno esattamente la stessa forma.
# La barra fra prefisso e numero — «Tel. 011/7323929» — e' la forma
# standard delle carte intestate italiane, e mancava: misurato, 300 numeri
# su 300 scritti cosi' venivano **persi in silenzio**, mentre gli stessi
# numeri con lo spazio o il trattino venivano presi. Non era una scelta:
# era una dimenticanza nell'elenco dei separatori.
#
# Ammetterla qui obbliga ad ammetterla anche in `_RE_DATELIKE`, che e' la
# guardia contro le date: senza, `01/02/2024` sarebbe diventato un recapito.
_RE_PHONE = re.compile(
    r"(?<![\w.+])"
    r"(?P<prefix>(?:\+|00)(?P<cc>\d{1,3})[\s./\-]?)?"
    r"(?P<body>\d(?:[\s./\-]?\d){5,14})"
    r"(?![\w])"
)

# Parole che trasformano una sequenza ambigua in un recapito.
_RE_PHONE_CTX = re.compile(
    r"\b(tel|telefono|telefonico|telefonica|cell|cel|cellulare|mobile|mob|"
    r"fax|phone|recapito|centralino|whatsapp)\b"
    r"\.?\s*(?:n\.?|nr\.?|numero)?\s*[:\-]?\s*$",
    re.IGNORECASE,
)

# «Tel.02 1234567»: l'OCR mangia lo spazio dopo l'abbreviazione e il punto
# resta attaccato alle cifre. Il lookbehind del pattern generale rifiuta un
# numero preceduto da un punto -- **ed e' giusto che continui a farlo**: un
# punto davanti a delle cifre e' quasi sempre un decimale, una data o un
# numero di articolo, e il telefono non ha un'aritmetica che possa smentire
# la forma. Un IBAN sbagliato lo scarta il mod-97; un recapito sbagliato non
# lo scarta nessuno.
#
# Quindi qui il lookbehind non e' stato allentato: questa riga **chiede di
# piu'**, cioe' che prima del punto ci sia la parola di contatto. Non e' una
# tolleranza, e' un contesto -- lo stesso che il motore usa gia' per
# accettare un numero corto.
_RE_PHONE_ETICHETTA = re.compile(
    # `(?<!\w)` e non `\b`: senza, «Hotel.02 …» finirebbe per contenere
    # l'etichetta «tel».
    r"(?<!\w)"
    r"(?P<etichetta>(?:tel|telefono|telefonico|telefonica|cell|cel|cellulare|"
    r"mobile|mob|fax|phone|recapito|centralino|whatsapp)\.+[ \t]*)"
    r"(?P<prefix>(?:\+|00)(?P<cc>\d{1,3})[\s.\-]?)?"
    r"(?P<body>\d(?:[ \t\-]?\d){5,14})"
    r"(?![\w])",
    re.IGNORECASE,
)

# Una data scritta con i separatori ha la stessa forma di un numero di
# telefono: "01.02.2024" sono otto cifre che iniziano per zero.
# La barra e' stata aggiunta insieme a quella dei telefoni, e l'ordine non
# e' casuale: `01/02/2024` e' la forma piu' comune di data in italiano, e
# ammettere la barra fra i separatori di un recapito senza ammetterla qui
# avrebbe trasformato ogni data in un numero di telefono.
_RE_DATELIKE = re.compile(
    r"^\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}$|^\d{4}[./\-]\d{1,2}[./\-]\d{1,2}$"
)

# Gruppi di cifre separati, per riconoscere una numerazione di colonne.
_RE_GRUPPI = re.compile(r"\d+")


def _is_numbering_sequence(testo: str) -> bool:
    """Una numerazione di colonne non e' un recapito.

    Sui moduli — 730, Redditi PF, Gazzetta — le colonne sono numerate in
    testa alla tabella: «00 1 2 3 4 5 6 7 8», «33 34 35 36 37». Hanno la
    forma di un numero di telefono spaziato ed erano la prima voce dei falsi
    positivi sui documenti italiani.

    Il segno distintivo e' che i gruppi **contano**: letti come interi
    crescono di uno alla volta. Nessun recapito si scrive cosi'. Si guarda
    la coda e non tutta la sequenza perche' la numerazione e' spesso
    preceduta da un'intestazione ereditata dal pattern («00» da un totale).
    """
    gruppi = [int(g) for g in _RE_GRUPPI.findall(testo)]
    if len(gruppi) < 4:
        return False
    corsa = 1
    for a, b in zip(reversed(gruppi[1:]), reversed(gruppi[:-1])):
        if a - b != 1:
            break
        corsa += 1
    return corsa >= 3

# Email
_RE_EMAIL = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)

# L'indirizzo spezzato dall'estrattore, non da chi scriveva:
#
#     scrivere a g.moretti@
#     studiomoretti.it
#
# Succede ogni volta che un PDF o un .docx manda a capo dentro l'indirizzo.
# Misurato: **perso in silenzio in 20 casi su 20** -- non sostituito e
# nemmeno segnalato, cioe' il modo peggiore di sbagliare.
#
# ATTENZIONE, qui c'e' un difetto gia' pagato una volta (vedi il commento
# sotto, su `_RE_EMAIL_OFFUSCATA`): un riconoscitore di email che
# attraversa le righe con `\s*` si mangia i paragrafi. Per questo il
# permesso e' il piu' stretto possibile:
#
#   * **un solo** ritorno a capo, non `\s*`;
#   * **solo dopo la chiocciola**, dove l'estrattore taglia davvero;
#   * il dominio dopo l'a capo resta strettissimo -- nessuno spazio al suo
#     interno, quindi non puo' arrivare alla parola successiva.
#
# Non si allenta nient'altro: la forma resta `locale@dominio.tld`, la stessa
# che il riconoscitore normale gia' accetta. Cambia solo che fra la
# chiocciola e il dominio puo' esserci l'a capo messo dall'estrattore.
# La parte locale non puo' finire con un punto: lo dice la RFC 5322, e non
# e' un cavillo -- e' cio' che distingue `g.moretti@` da `avv.@`, che nella
# prova a volume era il falso positivo piu' frequente. Il riconoscitore
# normale non ha bisogno di questa stretta perche' non attraversa le righe;
# qui serve, perche' qui il contesto e' piu' povero.
_RE_EMAIL_SPEZZATA = re.compile(
    r"\b[A-Za-z0-9._%+\-]*[A-Za-z0-9_%+\-]"
    r"@[^\S\r\n]*\r?\n[^\S\r\n]*"
    r"[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)

# L'indirizzo scritto per non farsi trovare dai raccoglitori automatici:
# "mario [at] esempio [dot] it". Chi lo scrive cosi' lo fa apposta perche'
# non sembri un'email — e infatti al riconoscitore non sembrava.
# Spazi e tabulazioni, mai il ritorno a capo.
#
# Con `\s*` questo riconoscitore attraversava le righe: su
# «... [punto] it.\n\nRecapiti: ...» il punto finale gli faceva mangiare i due
# ritorni a capo e la parola dopo, e l'uscita diventava «{{EMAIL}}: cell.».
# Il conteggio diceva «1 email» e nient'altro — cioe' il documento perdeva
# testo *in silenzio*, che e' il modo peggiore di sbagliare per un programma
# il cui compito e' far vedere cosa e' stato tolto.
#
# Un indirizzo, anche offuscato, sta su una riga sola. Meglio non riconoscere
# quello scritto a cavallo di due righe che divorare un paragrafo.
_ORIZZ = r"[^\S\r\n]"

# La chiocciola **dichiarata**: fra parentesi di qualunque tipo, o scritta
# per esteso. Chi scrive cosi' sta offuscando, e non c'e' altro modo di
# leggerlo.
_AT_MARCATO = (
    rf"(?:\[{_ORIZZ}*at{_ORIZZ}*\]|\({_ORIZZ}*at{_ORIZZ}*\)"
    rf"|\{{{_ORIZZ}*at{_ORIZZ}*\}}|\bchiocciola\b)"
)
# La chiocciola **presunta**: un `at` nudo fra due spazi. In italiano e' raro,
# in inglese e' una preposizione ordinaria.
_AT_NUDO = rf"{_ORIZZ}+at{_ORIZZ}+"

_PUNTO_MARCATO = (
    rf"(?:\[{_ORIZZ}*(?:dot|punto){_ORIZZ}*\]|\({_ORIZZ}*(?:dot|punto){_ORIZZ}*\)"
    rf"|\bpunto\b|\bdot\b)"
)
_PUNTO_QUALSIASI = rf"(?:{_PUNTO_MARCATO}|\.)"
_LOCALE_OFF = r"[A-Za-z0-9._%+\-]+"
_PEZZO_OFF = r"[A-Za-z0-9\-]+"

# **Il `at` nudo pretende che anche il punto sia offuscato**, e non e' una
# raffinatezza: e' il difetto piu' grosso che il corpus a verita' zero abbia
# rivelato. `available at IRS.gov`, `visit us at IRS.gov`, `estimator at
# www.irs.gov` finivano tutti in `{{EMAIL}}` -- dieci falsi positivi su
# undici, su moduli senza un solo indirizzo di posta. In inglese «at» davanti
# a un dominio e' il modo normale di scrivere «lo trovi qui».
#
# Il criterio: chi maschera un indirizzo lo maschera **tutto**. `mario at
# esempio dot it` resta riconosciuto, `available at IRS.gov` no. La forma
# con le parentesi non ha bisogno di questa stretta, perche' li' l'intenzione
# e' gia' scritta.
_RE_EMAIL_OFFUSCATA = re.compile(
    rf"(?i)\b{_LOCALE_OFF}{_ORIZZ}*"
    rf"(?:{_AT_MARCATO}{_ORIZZ}*{_PEZZO_OFF}"
    rf"(?:{_ORIZZ}*{_PUNTO_QUALSIASI}{_ORIZZ}*{_PEZZO_OFF})+"
    rf"|{_AT_NUDO}{_ORIZZ}*{_PEZZO_OFF}"
    rf"(?:{_ORIZZ}*{_PUNTO_MARCATO}{_ORIZZ}*{_PEZZO_OFF})+)"
)

# La chiocciola **vera**, con lo spazio attorno:
#
#     v.villa @ contabilita.test
#
# Non e' una forma di fantasia: e' come esce da un PDF giustificato, da un
# OCR, e da chi scrive l'indirizzo staccato per non farsi raccogliere dai
# robot. Misurata sul banco del richiamo: **609 indirizzi persi in
# silenzio** su 64 886, ed erano tutti e 609 di questa forma sola.
#
# Il riconoscitore delle forme offuscate qui sopra non la prendeva perche'
# conosce `[at]`, `(at)`, «chiocciola» e « at » -- cioe' tutti i modi di
# *scrivere a parole* la chiocciola, e non la chiocciola con lo spazio.
#
# **Il vincolo che la rende sicura, e senza il quale sarebbe pericolosa**:
# l'ultimo pezzo del dominio dev'essere di **lettere**. Su una fattura o un
# ordine «10 @ 4.50» vuol dire dieci pezzi a 4,50, e con il dominio libero
# diventerebbe un indirizzo di posta — un falso positivo su una notazione
# commerciale comunissima. Con il dominio di lettere, «50» non passa.
#
# Uno spazio da almeno un lato e' obbligatorio: senza spazi la forma e'
# quella normale, che ha gia' il suo riconoscitore e gira prima di questo.
_RE_EMAIL_SPAZIATA = re.compile(
    rf"(?i)\b[A-Za-z0-9._%+\-]+"
    rf"(?:{_ORIZZ}+@{_ORIZZ}*|{_ORIZZ}*@{_ORIZZ}+)"
    rf"[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{{2,}}\b"
)


# ---------------------------------------------------------------------------
# Importi
# ---------------------------------------------------------------------------

# Candidates only — _amount_is_plausible() requires a currency marker, a
# thousands group or a fiscal context word, so that version numbers survive.
_RE_AMOUNT = re.compile(
    r"(?P<cur_pre>€\s*)?"
    r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*[.,]\d{2})\b"
    r"(?P<cur_post>\s*(?:€|EUR\b|euro\b))?",
    re.IGNORECASE,
)

_RE_AMOUNT_CTX = re.compile(
    r"\b(importo|importi|totale|subtotale|saldo|prezzo|costo|iva|imponibile|"
    r"netto|lordo|acconto|fattura|pagamento|canone)\b\W*$",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Segreti tecnici
# ---------------------------------------------------------------------------

# Chiavi, token e password. Sono dati personali di un altro tipo — quelli
# che non ci si accorge di incollare insieme al resto del documento.
_RE_SECRETS = [
    ("private_key", re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
        re.DOTALL,
    )),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}")),
    ("aws_key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b")),
    ("google_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("openai_key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_\-]{20,}\b")),
    ("bearer", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-]{20,}")),
]

# Il caso generico: "password: ...", "api_key = ...". Sostituisce il valore
# e lascia l'etichetta, cosi' si capisce cosa e' stato tolto.
#
# Le etichette sono divise in due gruppi perche' non valgono uguale.
# "password:" non ha altri significati; "chiave:" in italiano ne ha
# parecchi, e infatti "chiave: importante da ricordare" finiva sostituito.
# `{` fuori dal valore: e' cio' che impedisce di rimangiarsi un segnaposto
# gia' inserito. E' la stessa convenzione degli altri pattern (vedi il
# commento sugli indirizzi), e questi due non la seguivano.
#
# Il difetto che ne usciva, su «Chiave: api_key = sk-test-ABCDEF0123456789»:
# il primo passaggio metteva `{{SECRET}}` al posto della credenziale, il
# secondo prendeva `api_key = {{SECRET}}` e sostituiva **il segnaposto**,
# il terzo prendeva `Chiave: api_key`. Il rapporto diceva `secrets: 3` per
# **un** segreto -- e il documento redatto non lo lasciava vedere, perche'
# i tre segnaposto erano identici. E' saltato fuori con la numerazione, che
# ha reso i tre distinguibili: `{{SECRET_3}} = {{SECRET_2}}`, senza l'1.
_VAL_SEGRETO = r"(?P<val>[^\s,;\"'{}]{6,})"

# --------------------------------------------------------------------------
# Il vocabolario delle etichette
# --------------------------------------------------------------------------
#
# **Perche' la strada e' questa e non l'entropia.** Il buco che resta, dopo
# le forme note e le etichette, e' la stringa di formato ignoto **senza**
# niente scritto accanto. Prenderla vorrebbe dire decidere sulla base di
# «sembra generata a caso» -- e hanno quell'aspetto anche gli hash dei
# commit, gli UUID, le firme base64 dentro un PDF, i codici a barre e i
# numeri di serie. Su un documento tecnico diventa un massacro, e uno
# strumento che cancella mezzo documento viene disinstallato.
#
# Allargare il vocabolario prende gran parte degli stessi casi con un
# rischio di natura diversa: una parola sbagliata si vede subito, si misura,
# e si toglie. Una soglia sbagliata sbaglia in silenzio su una classe
# intera.
#
# **Il costo, misurato e non stimato.** Su 8,5 M di caratteri di documenti
# amministrativi e legali italiani dove l'atteso e' zero, il conto dei
# segreti prima di questo allargamento era **1**. Il numero da guardare dopo
# ogni aggiunta e' quello.

# Gruppo forte: l'etichetta da sola annuncia una credenziale, e il valore si
# sostituisce comunque. «password:» non ha altri significati.
_ETICHETTE_FORTI = (
    # password e affini
    r"password|passwd|pwd|parola d'ordine|passphrase|"
    # token
    r"(?:access|refresh|bearer|id|auth|session|sas)[_\- ]?token|token|"
    r"token di (?:accesso|aggiornamento|sessione)|"
    # chiavi
    r"api[_\- ]?key|apikey|api[_\- ]?token|api[_\- ]?secret|"
    r"(?:secret|private|session|master|encryption|signing|access)[_\- ]?key|"
    r"secret[_\- ]access[_\- ]key|"
    r"chiave (?:privata|segreta|api|di accesso|di cifratura|crittografica|di licenza)|"
    # segreti applicativi
    r"secret|(?:client|app|webhook|signing)[_\- ]secret|shared[_\- ]secret|"
    r"segreto condiviso|"
    # stringhe di connessione e firme
    r"connection[_\- ]?string|stringa di connessione|"
    r"shared[_\- ]access[_\- ]signature|"
    # licenze e prodotti
    r"license[_\- ]?key|product[_\- ]?key|codice di licenza|"
    # OTP scritti per esteso (la forma corta e' piu' sotto)
    r"one[_\- ]?time[_\- ]?password|codice usa e getta"
    #
    # `authorization` NON entra, ed e' stato provato: aggiunta all'elenco,
    # su «Authorization: Bearer eyJhbGci...» l'etichetta prendeva come
    # valore la parola **«Bearer»** -- che e' il nome dello schema, non un
    # segreto. L'uscita diventava `Authorization: {{SECRET}} {{SECRET}}`,
    # cioe' meno leggibile di prima, e il rapporto contava due segreti dove
    # ce n'e' uno. Il token vero ce l'ha gia' un riconoscitore suo
    # (`bearer`, fra le forme note), quindi questa etichetta non aggiungeva
    # copertura: solo il difetto. L'ha trovata il corpus di conformita', non
    # un test.
)

_RE_SECRET_KV = re.compile(
    r"(?i)\b(" + _ETICHETTE_FORTI + r")\b"
    r"(?P<sep>\s*[:=]\s*)" + _VAL_SEGRETO
)

# Gruppo debole: etichette che in italiano hanno anche altri significati, e
# il valore deve **anche** sembrare una credenziale. «chiave: importante da
# ricordare» finiva sostituito, ed e' il motivo per cui questo gruppo esiste.
#
# `chiave` sta qui e non fra le forti apposta: «chiave pubblica» non e' un
# segreto, e «parola chiave» nemmeno.
_ETICHETTE_DEBOLI = (
    r"chiave|credenziali|codice di accesso|codice segreto|codice riservato|"
    r"segreto|codice di attivazione|codice di autorizzazione|"
    r"codice utente|user[_\- ]?secret"
)

_RE_SECRET_KV_DEBOLE = re.compile(
    r"(?i)\b(" + _ETICHETTE_DEBOLI + r")\b"
    r"(?P<sep>\s*[:=]\s*)" + _VAL_SEGRETO
)

# Gruppo corto: PIN, CVV, OTP.
#
# Servono un pattern e un valore propri perche' **sono corti**: quattro
# cifre non arrivano al minimo di sei del valore generico, quindi
# aggiungerli agli elenchi qui sopra li avrebbe lasciati senza effetto --
# un'etichetta scritta che non scatta mai e' peggio di un'etichetta
# mancante, perche' sembra coperta.
#
# Quello che li rende sicuri nonostante il valore sia solo cifre e'
# l'etichetta: `PIN`, `CVV`, `OTP` non hanno altri significati in un
# documento. Il limite superiore serve a non prendere codici lunghi che
# sono altro (un numero di pratica, un protocollo): oltre le otto cifre
# non e' piu' un PIN.
_RE_SECRET_CORTO = re.compile(
    r"(?i)\b(pin|codice pin|puk|cvv|cvc|cv2|codice di sicurezza|"
    r"security code|otp|codice otp|codice temporaneo|codice di sblocco)\b"
    r"(?P<sep>\s*[:=]?\s*(?:n\.?|num\.?)?\s*)"
    r"(?P<val>\d{3,8})\b"
)

# Gruppo lungo: la frase di recupero.
#
# Sta a parte perche' e' l'unico segreto fatto di **parole separate da
# spazi**, e con il valore generico -- che si ferma al primo spazio --
# usciva cosi':
#
#     Frase di recupero: {{SECRET}} batteria graffetta corretta
#
# Una parola tolta su dodici. La frase resta utilizzabile, e il rapporto
# dichiara «1 segreto sostituito»: e' il caso peggiore, perche' il numero
# dice che e' andato tutto bene. Meglio non riconoscerla affatto che
# riconoscerla a meta'.
#
# Dodici o ventiquattro parole e' lo standard (BIP-39); qui si accetta da 12
# a 24 per non affezionarsi a un solo formato. Il limite basso e' la
# protezione: «frase di recupero: vedi allegato» ha due parole e non scatta.
_RE_SECRET_FRASE = re.compile(
    r"(?i)\b(seed[_\- ]?phrase|recovery[_\- ]?phrase|frase di recupero|"
    r"frase mnemonica|mnemonic(?:[_\- ]phrase)?)\b"
    r"(?P<sep>\s*[:=]\s*)"
    r"(?P<val>[a-zà-öø-ÿ]{3,}(?:[ \t]+[a-zà-öø-ÿ]{3,}){11,23})\b"
)


def _secret_value_is_plausible(valore: str) -> bool:
    """Una parola italiana non e' una credenziale.

    Serve solo per le etichette ambigue: una credenziale mescola cifre e
    lettere, contiene simboli, oppure e' lunga in un modo che le parole
    non sono.
    """
    if len(valore) >= 16:
        return True
    if any(c.isdigit() for c in valore) and any(c.isalpha() for c in valore):
        return True
    return any(not c.isalnum() for c in valore)


# ---------------------------------------------------------------------------
# Date di nascita
# ---------------------------------------------------------------------------

_MESI = (
    r"gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|"
    r"ottobre|novembre|dicembre"
)

_RE_DATE = re.compile(
    rf"\b\d{{1,2}}[/.\-]\d{{1,2}}[/.\-]\d{{2,4}}\b|\b\d{{1,2}}\s+(?i:{_MESI})\s+\d{{4}}\b"
)

_RE_BIRTH_CTX = re.compile(
    r"(?i)\b(nat[oaie]|nascit[ao]|born|d\.?o\.?b\.?|compleanno)\b[^\n]{0,20}$"
)


# ---------------------------------------------------------------------------
# Documenti d'identita'
# ---------------------------------------------------------------------------
#
# Qui il metodo di casa — «il pattern propone, il validatore decide» — non si
# puo' applicare fino in fondo, e va detto invece di far finta.
#
# Nessuno di questi tre numeri ha una cifra di controllo pubblica. La patente
# ne ha una, ma l'algoritmo non e' pubblicato. Restano quindi solo forme, e
# sono forme **comunissime**: `AA00000AA` e `[A-Z]{2}\d{7}[A-Z]` combaciano
# con sigle di protocollo, codici gara, riferimenti catastali. Da soli
# farebbero strage su un verbale amministrativo.
#
# Al posto del validatore c'e' il **contesto obbligatorio**: si sostituisce
# solo se accanto c'e' scritto di che documento si tratta. Senza contesto la
# forma diventa un **sospetto** — il documento resta leggibile e chi controlla
# sa dove guardare. E' lo stesso trattamento che il motore riserva ai nomi
# quando la prova e' debole.
#
# Formati (verificati, non ricordati):
#   carta d'identita' elettronica   AA00000AA        2 lettere, 5 cifre, 2 lettere
#   passaporto (dal 2010)           YA/YB + 7 cifre  (TA per i temporanei)
#   patente, modello per provincia  AA0000000A
#   patente, duplicati UCO          U1/U2 + 8 alfanumerici

_RE_DOC_ID = re.compile(
    r"(?<![A-Z0-9])("
    # La CIE **spaziata**: sulla tessera il numero e' stampato a gruppi —
    # `CA 12345 AA` — e chi ricopia a mano lo riscrive cosi'. La forma
    # attaccata c'era gia'; questa no, e sono lo stesso documento.
    # Il contesto resta obbligatorio per tutte e due (vedi `_scrub_documenti_id`),
    # quindi allargare la forma non allarga cio' che sparisce da solo.
    r"[A-Z]{2}[ .-]\d{5}[ .-][A-Z]{2}"
    r"|[A-Z]{2}\d{5}[A-Z]{2}"         # carta d'identita' elettronica
    r"|(?:Y[AB]|TA)\d{7}"             # passaporto
    r"|[A-Z]{2}\d{7}[A-Z]"            # patente, modello per provincia
    r"|U[12][A-Z0-9]{8}"              # patente, duplicati UCO
    r")(?![A-Z0-9])"
)

# Cosa deve esserci intorno perche' quella forma sia un documento.
# La finestra guarda **prima e dopo**: sui moduli l'etichetta sta a sinistra
# («Patente n. U1L69I902B»), sulle scansioni delle tessere spesso sopra o
# accanto, e sul retro il numero precede la dicitura.
_RE_DOC_ID_CTX = re.compile(
    r"(?i)\b("
    r"cart[ae]\s+d[i']?\s*identit[\u00e0a]|c\.?\s*i\.?\s*n"
    # La sigla della carta d'identita' elettronica. Mancava: \u00abCIE n.
    # CA12345AA\u00bb e' la forma piu' corta e piu' comune sui moduli, e senza
    # etichetta riconosciuta quel numero restava un sospetto.
    r"|\bcie\b"
    r"|documento\s+d[i']?\s*identit[\u00e0a]"
    r"|identity\s+card|id\s+card"
    r"|patente|driving\s+licence|driver'?s?\s+licen[cs]e|licenza\s+di\s+guida"
    r"|passaporto|passport|libretto"
    r"|permesso\s+di\s+soggiorno|residence\s+permit"
    r"|tessera\s+sanitaria|carta\s+nazionale\s+dei\s+servizi"
    r")\b"
)


# ---------------------------------------------------------------------------
# Indirizzi
# ---------------------------------------------------------------------------

# "Via", "Piazza", "Corso"... sono anche parole comuni ("via email", "nel
# corso della riunione"): l'indirizzo si riconosce perche' subito dopo c'e'
# almeno una parola con l'iniziale maiuscola.
_ADDRESS_KW = (
    r"via|viale|v\.le|vicolo|vico|v\.lo|piazza|p\.zza|p\.za|piazzale|p\.le|"
    r"largo|l\.go|corso|"
    r"c\.so|strada|stradale|contrada|c\.da|localita|località|loc|frazione|"
    r"fraz|borgo|b\.go|lungomare|lungotevere|lungarno|salita|discesa|traversa|"
    r"circonvallazione|rotonda|galleria|passeggiata|riviera|calle|molo|"
    r"banchina|villaggio|residenza|rione|viottolo|sentiero"
)

# Parole che seguono la parola-chiave senza fare un indirizzo: "via PEC",
# "Via Aerea". Sono maiuscole, quindi il vincolo sull'iniziale non basta.
# L'elenco non e' stato immaginato: e' ricavato contando cosa segue davvero
# la parola-chiave su 1 027 documenti veri (moduli in bianco piu' mailing
# list). Li' dentro convivono vie vere — Fermi, Mazzini, Pascoli, Roentgen,
# Marconi — e usi di «via» che vogliono dire «tramite». Solo i secondi entrano
# qui: aggiungere un toponimo vero renderebbe cieco il riconoscitore proprio
# sugli indirizzi.
_ADDRESS_STOPWORDS = frozenset(
    {
        # trasmissione e recapito
        "pec", "email", "mail", "e-mail", "fax", "telefono", "posta",
        "raccomandata", "internet", "web", "aerea", "terra", "mare",
        "telematica", "ordinaria", "breve", "crucis", "libera", "cavo",
        "satellite", "corriere", "telefax", "sms", "etere", "radio",
        "telefonica", "telegrafica", "messaggio", "chat",
        # protocolli e mezzi tecnici: «via USB», «via SSH» — i piu' frequenti
        # nel corpus, e nessuno di questi e' un nome di strada italiano
        "usb", "ssh", "ftp", "sftp", "nfs", "lan", "wan", "vpn", "http",
        "https", "smtp", "imap", "pop3", "telnet", "rsync", "samba", "cifs",
        "bluetooth", "ethernet", "wifi", "wi-fi", "seriale", "parallela",
        "modem", "browser", "terminale", "script", "cron", "api", "rss",
        "proxy", "tunnel", "socket", "in-reply-to", "technologies",
        "software", "hardware", "driver", "kernel", "firmware",
        # applicazioni
        "app", "whatsapp", "telegram", "skype", "zoom", "teams", "meet",
        "messenger", "signal", "portale", "piattaforma", "sito",
        # italiano amministrativo e giuridico: «in via provvisoria»,
        # «per via gerarchica», «in via d'urgenza»
        "giudiziale", "giudiziaria", "amministrativa", "gerarchica",
        "legale", "cautelare", "straordinaria", "provvisoria", "definitiva",
        "preliminare", "principale", "sussidiaria", "subordinata",
        "transitoria", "eccezionale", "urgente", "analogica", "cartacea",
        "informale", "ufficiale", "diplomatica", "sperimentale",
        "prioritaria", "preferenziale", "esclusiva", "generale", "autonoma",
        "diretta", "indiretta", "equitativa", "consensuale", "stragiudiziale",
        "d'urgenza", "presuntiva", "residuale", "alternativa",
    }
)

# Un pezzo di nome proprio: iniziale maiuscola e almeno una minuscola.
# Il vincolo sulla minuscola esclude in un colpo solo gli acronimi (PEC,
# SPA), i numeri romani (II) e i segnaposto gia' inseriti ({{EMAIL}}).
_TOK_MISTO = r"[A-ZÀ-ÖØ-Þ][\w'’\-]*[a-zà-öø-ÿ][\w'’\-]*"

# ...ma cosi' il riconoscitore era CIECO SUL MAIUSCOLO, ed e' proprio dove
# vive: «VIA GARIBALDI 14» su una patente, su un modulo, su qualsiasi
# scansione, restava intatto mentre «Via Garibaldi 14» spariva. Chi legge non
# poteva saperlo.
#
# Il ramo maiuscolo tiene tutte le protezioni del primo:
#   - almeno tre lettere, cosi' i numeri romani corti (II, IV, XI) restano fuori
#   - niente `{`, quindi i segnaposto gia' inseriti non vengono riassorbiti
#   - le parole di `_ADDRESS_STOPWORDS` (PEC, FAX, AEREA...) sono comunque
#     scartate a valle, e in italiano «via» vuol dire anche «tramite»
_TOK_MAIUSC = r"[A-ZÀ-ÖØ-Þ]{3,}(?:['’\-][A-ZÀ-ÖØ-Þ]+)*"

_TOK = rf"(?:{_TOK_MISTO}|{_TOK_MAIUSC})"

# Articoli e preposizioni che stanno dentro un nome di strada.
_CONN = (
    r"(?:d[ei]|del|dello|della|dei|degli|delle|dal|dalla|da|la|lo|le|il|"
    r"san|santa|sant'|santo|santi|ss\.)"
)

# Dentro un indirizzo lo spazio e' **orizzontale**.
#
# Con `\s` il riconoscitore attraversava gli a capo e si portava via la prima
# parola del blocco dopo: «Via Roma 5, 20121 Milano \n Cordiali saluti»
# usciva come «{{ADDRESS}} saluti». Due danni, non uno: una parola sparita
# dal documento -- che non e' una fuga ma e' comunque un documento corrotto,
# e chi legge non ha modo di accorgersene -- e il segnale della firma
# distrutto, perche' «Cordiali saluti» e' proprio cio' che dichiara che
# quello che segue e' una persona.
#
# E' lo stesso difetto gia' pagato nella 1.14.0 con l'email offuscata, e la
# stessa ragione per cui i nomi usano `_SP`. Trovato per caso costruendo un
# esempio prima/dopo da mostrare in pubblico.
_H = r"[ \t]"

_RE_ADDRESS = re.compile(
    rf"(?<!\w)(?i:{_ADDRESS_KW})\.?{_H}+"
    # Il numero romano puo' stare anche in TESTA al nome: «Via XX Settembre»,
    # «Viale IV Novembre». Ce n'e' una in quasi ogni citta' italiana, e non
    # veniva riconosciuta in nessuna delle due grafie -- il primo pezzo del
    # nome doveva contenere una minuscola, e «XX» non ne ha. Deve essere
    # seguito da una parola vera, altrimenti «via II» da solo basterebbe.
    rf"(?P<body>(?:[IVXLC]{{1,5}}{_H}+(?=[A-Za-zÀ-ÿ]))?"
    rf"(?:{_CONN}{_H}+)*"
    # «Via A. Volta 5», «Viale G. Cesare 12», «Via G. B. Vico 3»: sulla
    # carta intestata e sui moduli il nome della strada porta l'iniziale
    # puntata invece del nome per esteso. Senza questo pezzo il corpo non
    # poteva nemmeno *cominciare* -- `_TOK` pretende una lettera minuscola
    # oppure tre maiuscole, e «A.» non ha ne' l'una ne' le altre -- e
    # l'indirizzo intero restava nel documento. Misurato su 200 indirizzi
    # di questa forma: zero riconosciuti prima, tutti dopo.
    rf"(?:[A-ZÀ-ÖØ-Þ]\.[ \t]*){{0,2}}"
    rf"(?:\w+['’])?{_TOK}"
    rf"(?:{_H}+(?:{_CONN}{_H}+|e{_H}+)?(?:\w+['’])?{_TOK}){{0,3}})"
    rf"(?P<roman>{_H}+[IVXLC]{{1,5}}(?![\w]))?"
    # Il suffisso del civico («12/A», «7-bis») non deve poter mordere la
    # parola dopo: su «via C. Colombo 44 - Roma» si prendeva «- Rom» come
    # suffisso e lasciava indietro una «a» orfana. Deve finire dove finisce
    # la parola, non tre lettere dentro.
    rf"(?P<civ>{_H}*,?{_H}*(?:n\.?|nr\.?|snc|km)?{_H}*\d{{1,4}}"
    # Il suffisso del civico («12/A», «7-bis») deve finire dove finisce la
    # parola **e** dove finisce il numero. Fermando solo sulle lettere,
    # «Piazza G. Verdi, 1 - 00198 Roma» prendeva «- 001» come suffisso e
    # lasciava indietro «98 Roma»: il CAP mozzato, e tre cifre orfane in un
    # documento che sembrava trattato. Era gia' passato sotto gli occhi nelle
    # Gazzette Ufficiali senza che lo guardassi.
    rf"(?:{_H}*[/\-]{_H}*[A-Za-z0-9]{{1,3}}(?!\w))?)?"
    # Il CAP e' l'unico pezzo cui si concede **un** a capo, perche' sulla
    # carta intestata l'indirizzo si scrive proprio cosi':
    #     Via A. Volta 5
    #     20121 Milano
    # Uno solo pero': due a capo sono un blocco nuovo, e concederli era il
    # modo in cui «Via Verdi 12, 40100 Bologna \n\n Allegato A» si portava
    # via la «A» dell'allegato.
    rf"(?P<cap>{_H}*[,\-–]?{_H}*(?:\r?\n{_H}*)?\d{{5}}{_H}+{_TOK}"
    rf"(?:{_H}+{_TOK})?"
    # La sigla della provincia, che chiude l'indirizzo: `(MI)`, ` RM`.
    #
    # Restava fuori, e usciva `{{ADDRESS}} (MI)`. Non e' un dato che
    # identifica da solo, ma su un indirizzo e' l'ultimo pezzo in chiaro di
    # una cosa che il documento presenta come un blocco unico -- e un
    # blocco redatto a meta' e' quello che fa dubitare del resto.
    #
    # **Lo schema propone, l'elenco decide** (`_SIGLE_PROVINCIA`). Due
    # lettere maiuscole dopo un comune non bastano: la prima versione di
    # questa riga si mangiava la `IT` di «Milano IT», e domani si sarebbe
    # mangiata «Milano IL GIORNO 5». Le province italiane sono un insieme
    # chiuso di 107 sigle, quindi qui non c'e' niente da indovinare.
    rf"(?:{_H}*\({_H}*(?P<prov_par>[A-Z]{{2}}){_H}*\)"
    rf"|{_H}+(?P<prov>[A-Z]{{2}})(?![\w]))?"
    rf")?"
)

#: Le sigle automobilistiche delle province italiane. Insieme chiuso, quindi
#: **si decide invece di indovinare**: e' lo stesso criterio del mod-97 per
#: gli IBAN, applicato a un elenco invece che a un conto.
_SIGLE_PROVINCIA = frozenset(
    "AG AL AN AO AP AQ AR AT AV BA BG BI BL BN BO BR BS BT BZ CA CB CE CH CL "
    "CN CO CR CS CT CZ EN FC FE FG FI FM FR GE GO GR IM IS KR LC LE LI LO LT "
    "LU MB MC ME MI MN MO MS MT NA NO NU OR PA PC PD PE PG PI PN PO PR PT PU "
    "PV PZ RA RC RE RG RI RM RN RO SA SI SO SP SR SS SU SV TA TE TN TO TP TR "
    "TS TV UD VA VB VC VE VI VR VT VV".split()
)


# ---------------------------------------------------------------------------
# Nomi di persona
# ---------------------------------------------------------------------------

_TITLES = (
    r"sig|sig\.ra|sig\.na|signor|signora|signorina|dott|dott\.ssa|dr|dr\.ssa|"
    r"dottor|dottore|dottoressa|ing|ingegner|ingegnere|avv|avvocato|"
    r"avvocatessa|geom|geometra|arch|architetto|prof|prof\.ssa|professor|"
    r"professore|professoressa|rag|ragionier|ragioniere|onorevole|"
    r"egr|gent|mr|mrs|ms"
)

# Abbreviazioni che **senza il punto sono parole comuni**, e che quindi il
# punto lo devono avere.
#
# `on.` e' «onorevole», e stava insieme agli altri titoli con il punto
# facoltativo. Il risultato: **ogni `on` seguito da una parola maiuscola
# diventava una persona**. In inglese `on` e' una preposizione, quindi
# `reported on Form 1125-A` usciva `reported on {{NAME_1}} 1125-A` e
# `included on Schedule K` perdeva la parola `Schedule`.
#
# Non e' un difetto dei documenti inglesi, e' un difetto che i documenti
# inglesi rivelano: `Income included on Quadro K` sbagliava allo stesso
# modo in italiano. Misurato sul corpus pubblico: **101 nomi inventati** su
# 47 documenti a verita' zero, quasi tutti moduli fiscali statunitensi.
#
# Il punto non e' una formalita': `On. Mario Rossi` e' come si scrive
# davvero l'abbreviazione. Senza punto non e' un'abbreviazione, e' un'altra
# parola. Chi scrive `On Mario Rossi` perde questa regola ma non il
# riconoscimento: nome e cognome adiacenti hanno una regola loro.
_TITOLI_COL_PUNTO = r"on"

# I **ruoli**: sostantivi che dichiarano che quello che segue e' una persona.
#
# `Il cliente Elicio Nazar chiede invio documenti`. E' la stessa forma del
# titolo professionale, su un sostantivo di ruolo invece che su
# un'onorificenza -- e in un documento amministrativo e' molto piu' frequente
# di `Dott.`: misurato sul corpus legale, `cliente` precede da solo 2.671 dei
# nomi che restavano in chiaro.
#
# **Perche' pretendono due parole** e i titoli no. Un titolo lo si scrive
# quasi solo davanti a una persona; un ruolo lo si scrive anche davanti a
# un'azienda -- «il cliente Beta Consulting S.p.A.», «il conduttore Immobiliare
# Verdi S.r.l.». Pretendere nome **e** cognome toglie la maggior parte di
# quei casi, e lo scudo degli enti toglie il resto.
#
# L'elenco e' corto apposta e contiene solo ruoli che una persona fisica
# ricopre in un atto. Non ci vanno le qualifiche professionali generiche
# (`responsabile`, `titolare`, `referente`): quelle precedono un ufficio
# almeno quanto una persona, e il loro contesto tipico e' proprio
# l'intestazione di un ente.
_RUOLI = (
    r"cliente|clienti|utente|utenti|paziente|pazienti|"
    r"acquirente|acquirenti|venditore|venditrice|"
    r"locatore|locatrice|locatario|conduttore|conduttrice|"
    r"testimone|testimoni|ricorrente|resistente|convenuto|convenuta|"
    r"assicurato|assicurata|beneficiario|beneficiaria|"
    r"contribuente|dipendente|intestatario|intestataria"
)

# Le due espressioni si compilano piu' sotto, dopo `_SP`.

# Fra un nome e il suo cognome ci puo' essere uno spazio, non un a capo:
# usare \s farebbe attraversare le righe e incollerebbe la firma alla riga
# successiva, con il risultato che una parola comune trovata li' fa cadere
# tutto il riconoscimento.
_SP = r"[ \t]+"

_RE_TITLE_NAME = re.compile(
    rf"(?<!\w)(?:(?i:{_TITLES})\.?|(?i:{_TITOLI_COL_PUNTO})\.)"
    rf"{_SP}(?P<name>{_TOK}(?:{_SP}{_TOK}){{0,2}})"
)

# Le sigle societarie. Stanno **dopo** la ragione sociale, quindi lo scudo
# delle parole d'ente -- che guarda le parole del nome -- non le vede: su
# «il cliente Beta Consulting S.p.A.» il primo giro di questa regola
# produceva «il cliente {{NAME}} S.p.A.», cioe' il falso positivo peggiore
# possibile su una riga che parla di un'azienda.
_SIGLE_SOCIETARIE = (
    r"s\.?p\.?a\.?|s\.?r\.?l\.?s?\.?|s\.?n\.?c\.?|s\.?a\.?s\.?|"
    r"s\.?c\.?a\.?r\.?l\.?|coop|onlus|ets|aps|spa|srl|"
    r"ltd|llc|inc|plc|gmbh|s\.?a\.?"
)
_RE_SIGLA_DOPO = re.compile(rf"^[ \t]*(?:{_SIGLE_SOCIETARIE})(?![\wÀ-ÿ])", re.I)

# Un ruolo pretende **due** parole: vedi `_RUOLI`.
_RE_RUOLO_NAME = re.compile(
    rf"(?<!\w)(?i:{_RUOLI}){_SP}(?P<name>{_TOK}(?:{_SP}{_TOK}){{1,2}})"
)

# La forma a campo: `NOME= Elicio Nazar;` -- un'etichetta che **dichiara** il
# contenuto invece di descriverlo. Compare negli estratti di record e nei
# tracciati, dove il testo attorno non aiuta per niente: l'unica altra cosa
# sulla riga e' un punto e virgola. Qui basta una parola, perche' l'etichetta
# non lascia spazio a dubbi su cosa ci sia dopo.
_RE_CAMPO_NOME = re.compile(
    rf"(?<!\w)(?i:nome|nominativo|cognome)[ \t]*[=:][ \t]*"
    rf"(?P<name>{_TOK}(?:{_SP}{_TOK}){{0,2}})"
)

# Un nome accanto a un indirizzo di posta: "Mario Rossi <mario@x.it>",
# "mario@x.it (Mario Rossi)". Gira dopo la sostituzione delle email, quindi
# quello che cerca e' il segnaposto.
# Le formule di chiusura italiane. Quello che segue e' una persona: e'
# l'unico contesto in cui un cognome da solo vale come prova.
_CHIUSURE_IT = (
    r"cordiali\s+saluti|distinti\s+saluti|cordialmente|in\s+fede|"
    r"un\s+caro\s+saluto|cari\s+saluti|molti\s+saluti|saluti|ossequi|"
    r"grazie\s+e\s+saluti|resto\s+a\s+disposizione|a\s+presto"
)
_RE_FIRMA_IT = re.compile(
    rf"(?i:{_CHIUSURE_IT})[,.]?[ \t]*(?:\r?\n\s*|[ \t]+)"
    rf"(?P<name>{_TOK}(?:{_SP}{_TOK}){{0,2}})"
)

# Le formule di **apertura**. Sono l'altra meta' della firma: una chiusura
# dichiara che quello che segue e' una persona, e un saluto fa lo stesso
# all'inizio.
#
# Serve perche' un nome di battesimo **da solo** non basta mai — «Rosa»,
# «Vera», «Costa» sono nomi e parole insieme, e sostituirli costerebbe piu'
# di quanto renda. «Ciao Pietro» pero' non e' un nome isolato: e' un nome con
# davanti qualcosa che dice cosa sia, ed e' lo stesso genere di prova del
# titolo professionale e dell'indirizzo di posta accanto.
#
# E' il caso piu' frequente nelle email e nelle chat, dove il cognome spesso
# non c'e' affatto.
_APERTURE_IT = (
    r"ciao|caro|cara|carissimo|carissima|gentile|gentilissimo|gentilissima|"
    r"egregio|egregia|salve|buongiorno|buonasera|buondi'|buonasera a"
)
_RE_SALUTO_NOME = re.compile(
    rf"(?<!\w)(?i:{_APERTURE_IT})[ \t]+"
    rf"(?P<name>{_TOK}(?:{_SP}{_TOK}){{0,2}})"
)

# «Il Ministro: GIORGETTI» — un ruolo, due punti, e un cognome solo.
#
# E' la forma con cui si firmano gli atti pubblici italiani, e nessuna delle
# altre regole la vedeva: il riconoscitore a coppie pretende **due** parole
# adiacenti, e qui la parola e' una sola. Contata sulle Gazzette Ufficiali
# del corpus: 107 occorrenze intatte, GIORGETTI, NORDIO, PIANTEDOSI,
# LOLLOBRIGIDA, IACOVONI. Nemmeno un modello NER da 64 MiB la prendeva
# (3 casi su 42 misurati): non e' una questione di quanto sa un modello, e'
# che il segnale sta nella punteggiatura.
#
# Gli elenchi non servono a niente qui, ed e' il punto: dei 114 cognomi
# trovati, **28** stanno nei nostri elenchi. Pretendere il riscontro
# avrebbe lasciato passare gli altri 86. Quello che decide e' il ruolo
# davanti ai due punti.
#
# Tre guardie, ognuna nata da un falso positivo visto davvero:
#
#  * **niente virgola** fra il ruolo e i due punti. «Responsabile della
#    protezione dei dati, all'indirizzo: INPS» ha un ruolo davanti, ma i
#    due punti non sono i suoi: sono di «indirizzo». La virgola dice che la
#    frase e' andata avanti;
#  * **una riga sola**. Attraversando l'a capo si prendeva
#    «IACHINO\nMINISTERO DELLA», cioe' il cognome piu' l'intestazione della
#    sezione dopo;
#  * **tutto maiuscolo, e nessuna parola comune**. E' il presidio contro
#    l'altra faccia della stessa forma, che su un modulo e' un'etichetta di
#    campo: «Responsabile: SETTORE TECNICO», «Direttore: UFFICIO
#    ACQUISTI». Sono etichette, non persone.
#
# Il maiuscolo non e' un dettaglio estetico: e' il terzo segnale. In un
# atto firmato il cognome sta in maiuscolo perche' e' una firma, e chiederlo
# costa un richiamo che non abbiamo mai avuto invece di aprire «Il
# presidente: Vedi allegato».
_RUOLI_FIRMA = (
    r"ministr[oa]|presidente|vicepresidente|guardasigilli|direttor[ei]|"
    r"direttrice|dirigente|capo|sindaco|prefetto|rettore|assessore|"
    r"commissario|segretari[oa]|procuratore|questore|comandante|"
    r"provveditore|so[vp]rintendente|amministratore|coordinatore|"
    r"ragioniere|responsabile|funzionario"
)

_TOK_FIRMA = r"[A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ'’\-]{2,}"

_RE_RUOLO_COGNOME = re.compile(
    rf"(?<!\w)(?i:{_RUOLI_FIRMA})(?!\w)[^:,;\n]{{0,60}}:[ \t]*"
    rf"(?P<name>{_TOK_FIRMA}(?:[ \t]+{_TOK_FIRMA})?)(?!\w)"
)

# Come si scrive «un segnaposto gia' inserito» dentro un pattern.
#
# Alcune regole non guardano il testo originale ma **cio' che un altro
# riconoscitore ha gia' sostituito**: il nome accanto all'indirizzo di posta
# si riconosce perche' li' accanto c'e' un `{{EMAIL}}`. Scritto alla
# lettera, quel riferimento e' saltato il giorno in cui i segnaposto sono
# diventati numerati (1.20.0): nel testo c'era `{{EMAIL_1}}`, il pattern
# cercava `{{EMAIL}}`, e la regola ha smesso di funzionare in silenzio --
# «Rao <a.rao@example.it>» usciva come «Rao <{{EMAIL_1}}>», con il nome
# ancora li'. Non un falso positivo: un dato lasciato in chiaro.
#
# Sta qui, in un posto solo, perche' il prossimo riconoscitore che si
# aggancia a un segnaposto non debba scoprirlo di nuovo.
# Carattere dell'area a uso privato Unicode: non compare in nessun testo
# vero, e nessun documento puo' contenerlo "per caso". Marca i segnaposto
# che ha messo **questa** conversione, e non sopravvive all'uscita: lo
# toglie `_rinumera_per_comparsa`, che e' anche l'unico posto che lo legge.
SENTINELLA = ""


def _rif_segnaposto(etichetta: str) -> str:
    # Le tre forme in cui quel segnaposto puo' presentarsi mentre il motore
    # sta ancora lavorando: piatto, marcato (l'ha messo questa conversione,
    # vedi `SENTINELLA`) e numerato (c'era gia' nel documento).
    return r"\{\{" + etichetta + rf"(?:[_{SENTINELLA}]\d+)?\}}\}}"


_RE_NAME_BEFORE_EMAIL = re.compile(
    rf"(?P<name>{_TOK}(?:{_SP}{_TOK}){{0,2}})(?P<sep>\s*[<\(\[]?\s*){_rif_segnaposto('EMAIL')}"
)
_RE_NAME_AFTER_EMAIL = re.compile(
    rf"{_rif_segnaposto('EMAIL')}(?P<sep>\s*[<\(\[]\s*)(?P<name>{_TOK}(?:{_SP}{_TOK}){{0,2}})"
)

# Il nome accanto a un **codice fiscale**, che e' la dichiarazione piu' forte
# che questo motore possa leggere.
#
# Perche' e' piu' forte di tutte le altre. Un titolo si scrive anche davanti
# a un ente, una formula di chiusura puo' precedere una ragione sociale, un
# indirizzo di posta puo' essere di un ufficio. Un codice fiscale **passa il
# carattere di controllo**: non capita per caso, e in Italia si rilascia a
# una persona fisica. Quando ce n'e' uno valido, che li' accanto ci sia una
# persona non e' un indizio, e' quasi il testo che lo dice.
#
# **E non dipende da nessun elenco**, che e' il punto. Le regole che
# avevamo coprivano il caso «nome e cognome entrambi riconosciuti», cioe'
# proprio quello che un nome mai visto non puo' soddisfare. Misurato: sul
# corpus legale, sostituendo i nomi con altri fuori dai nostri elenchi e
# lasciando le frasi identiche, il richiamo passava da 99,4% a 0,5% --
# tutto il riconoscimento veniva dagli elenchi. E in quelle stesse frasi il
# codice fiscale stava attaccato al nome: `Elicio Nazar CF MNTCRL58D07H163B`.
#
# La finestra e' stretta apposta -- fra il nome e il codice ci sta
# l'etichetta (`CF`, `C.F.`, `codice fiscale`) e nient'altro, sulla stessa
# riga. Con una finestra larga il nome verrebbe preso da un'altra frase, ed
# e' un modo di sbagliare che il motore ha gia' pagato con gli indirizzi.
_ETICHETTA_CF = r"(?:[-–—:,]?[ \t]*(?i:c\.?f\.?|cod(?:ice)?\.?[ \t]*fisc(?:ale)?\.?)[ \t]*:?)?"

_RE_NAME_BEFORE_CF = re.compile(
    rf"(?P<name>{_TOK}(?:{_SP}{_TOK}){{1,2}})"
    rf"(?P<sep>[ \t]*{_ETICHETTA_CF}[ \t]*)"
    rf"{_rif_segnaposto('CODICE_FISCALE')}"
)

# Una sequenza *intera* di parole maiuscole, non una finestra di due o tre.
#
# Con la finestra, "Riferimento Del Piero Alessandro" veniva agganciata a
# partire da "Riferimento": tre parole consumate, dentro una sola del nome,
# e le altre lasciate indietro come parole isolate. Risultato:
# "Riferimento Del {{NAME}} {{NAME}}" — la particella fuori e il nome
# spezzato in due. Prendendo la sequenza intera e decidendo *dentro* quali
# tratti sono nomi, il problema non si pone: e' la stessa ragione per cui
# conviene rilevare gli intervalli prima e sostituirli dopo.
#
# Le graffe nel lookaround non sono un vezzo: `{` e `}` non sono caratteri
# di parola, quindi senza di loro il confine si apre **dentro** un segnaposto
# gia' inserito e il motore si rimangia il proprio lavoro. Vedi la nota su
# `_RE_LONE_TOKEN`, dove il difetto e' stato pagato per davvero.
_RE_NAME_RUN = re.compile(rf"(?<![\w{{]){_TOK}(?:{_SP}{_TOK})*(?![\w}}])")

# Oltre questa lunghezza non e' un nome: e' un titolo scritto in maiuscolo.
_MAX_TOKEN_NOME = 4

# Un nome scritto TUTTO MAIUSCOLO. Il pattern normale pretende almeno una
# minuscola — e' cosi' che esclude in un colpo solo acronimi, numeri romani
# e i segnaposto gia' inseriti — e questo lo rende cieco a "MARIO ROSSI",
# che nelle firme e nelle intestazioni delle mail e' frequentissimo.
# Trovato su una mail vera: quattro sequenze intatte su un testo in cui
# tutto il resto era stato sostituito.
_TOK_UP = r"[A-ZÀ-ÖØ-Þ]{3,}"
_RE_NAME_PAIR_UPPER = re.compile(rf"(?<![\w{{]){_TOK_UP}(?:{_SP}{_TOK_UP}){{1,2}}(?![\w}}])")

# La guardia sulle graffe, e il difetto che l'ha resa necessaria.
#
# `{{NINO}}` — il segnaposto del National Insurance number britannico — e'
# anche un nome di battesimo italiano. `{` e `}` non sono caratteri di
# parola, quindi `(?<!\w)` non impediva niente: questo pattern trovava
# `NINO` **dentro il segnaposto appena inserito**, lo cercava negli elenchi,
# lo trovava, e lo depositava fra i sospetti.
#
# Il testo usciva giusto; a sporcarsi era il rapporto. Ed e' la parte che
# conta di piu': i sospetti dicono «qui c'e' qualcosa che assomiglia a un
# dato personale e **non** l'ho tolto, vallo a guardare». Chi ne trova due o
# tre finti smette di guardarli tutti.
#
# Trovato dal corpus di conformita', non da un test — e per questo il test
# che lo copre (`tests/test_segnaposto_non_riassorbiti.py`) enumera **tutti**
# i segnaposto leggendoli da questo sorgente, invece di provare NINO: oggi
# il collo e' uno su trenta, domani un riconoscitore nuovo puo' portarne un
# altro e nessuno ci penserebbe.
_RE_LONE_TOKEN = re.compile(rf"(?<![\w{{]){_TOK}(?![\w}}])")

# Le parole dopo le quali un nome di battesimo **non e' una persona**.
#
# Servono solo alla regola sul nome isolato (`names_alone`), e sono l'unica
# cosa che la rende utilizzabile: «Umberto» in mezzo a una frase e' un
# collega, «ospedale Umberto» e' un edificio, «via Umberto» e' un indirizzo,
# «Sant'Umberto» e' un paese. La parola sono sempre **le stesse lettere**: a
# distinguerle e' solo cio' che sta davanti.
#
# Tre gruppi, e nessuno dei tre e' stato immaginato:
#   * le parole d'ente, che il motore ha gia' e usa come scudo sulle coppie;
#   * i tipi di via, che il riconoscitore di indirizzi ha gia';
#   * i santi e le intitolazioni, che sono il caso rimasto fuori da tutti e
#     due -- «stadio Giuseppe», «premio Italo», «ponte Vittorio», «villa Ada».
#
# `sala`, `casa`, `centro` sono anche cognomi: qui non fa danno, perche'
# questo elenco **non sostituisce mai**, impedisce soltanto.
_PRIMA_NON_E_PERSONA = frozenset(
    {
        "san", "santa", "santo", "sant", "santi", "beato", "beata",
        "stadio", "palastadio", "palazzetto", "palazzo", "padiglione",
        "ponte", "viadotto", "tunnel", "traforo", "molo", "banchina",
        "premio", "torneo", "trofeo", "concorso", "borsa", "medaglia",
        "villa", "parco", "giardino", "giardini", "campus", "complesso",
        "centro", "polo", "casa", "casale", "cascina", "masseria",
        "hotel", "albergo", "bar", "ristorante", "trattoria", "osteria",
        "pizzeria", "residence", "residenza", "agriturismo", "camping",
        "aula", "sala", "salone", "atrio", "cappella", "cripta",
        "monumento", "statua", "targa", "lapide", "obelisco", "fontana",
        "nave", "motonave", "traghetto", "treno", "locomotiva",
        "quartiere", "rione", "frazione", "borgo", "contrada", "localita",
        "località", "zona", "comprensorio",
        # Le due che il banco ha aggiunto dopo averle viste passare: il nome
        # proprio diventato **prodotto** («pizza Margherita») e l'uscita
        # autostradale intitolata a una persona.
        "pizza", "pizze", "torta", "torte", "gelato", "cocktail", "panino",
        "uscita", "casello", "svincolo", "autostradale", "raccordo",
        # **Queste le ha trovate il corpus pubblico, non un banco fatto in
        # casa**, ed e' la ragione per cui quel corpus esiste.
        #
        # I punti cardinali: sui moduli IRS in bianco sparivano `North
        # Carolina`, `South Carolina`, `West Virginia` -- ventisei
        # sostituzioni su documenti che non contengono un solo dato
        # personale. Carolina, Virginia, Charlotte e Thomas stanno negli
        # elenchi dei nomi, e nessuna regola sulla parola sola puo'
        # accorgersi che li' sono uno Stato.
        "north", "south", "east", "west", "nord", "sud", "est", "ovest",
        # `torre`: sulle Gazzette `Torre Annunziata` -- un comune -- spariva
        # venticinque volte. E l'abbreviazione del santo, che nei toponimi si
        # scrive quasi sempre puntata: `S. Biagio`.
        "torre", "s", "st", "ss", "saint", "box",
    }
)

# Nomi propri che sono anche parole comuni: da soli non bastano.
_AMBIGUOUS_ALONE = frozenset(
    {
        "rosa", "celeste", "vera", "grazia", "pace", "speranza", "gioia",
        "perla", "aurora", "neve", "ambra", "letizia", "allegra", "prima",
        "primo", "secondo", "santa", "santo", "natale", "felice", "vittoria",
        "fortunato", "benedetto", "giusto", "amato", "diana", "iris", "viola",
        "stella", "luna", "alba", "italo", "italia", "domenica", "sabato",
        "marzo", "agosto", "maggio", "conte", "modesto", "candido", "bruno",
        # Trovate sulle Gazzette Ufficiali, non a mente: `Fermo` e' un nome
        # di battesimo, un comune delle Marche **e** un aggettivo («fermo
        # restando»); `Norma` e' un nome, un comune del Lazio e la parola
        # con cui si apre mezzo atto amministrativo. Da sole non provano
        # niente, ed e' esattamente cio' che questo elenco raccoglie.
        "fermo", "norma",
        # `Virginia`: nome di battesimo italiano e Stato americano. Sui moduli
        # IRS compare dentro l'elenco degli Stati -- «Vermont, Virginia, West
        # Virginia, Wisconsin» -- e li' non e' nessuno. Fino alla 1.26
        # scampava per caso: la guardia sull'intitolazione risaliva
        # all'indietro senza badare alle virgole e incontrava il `West` di
        # cinque parole prima. Chiusa quella scorciatoia (P9.4), la parola
        # resta scoperta, ed e' questo l'elenco giusto per lei -- in coppia
        # («Virginia Woolf») continua a essere protetta, perche' qui si
        # decide solo della parola **sola**.
        "virginia",
        "franco", "sereno", "fiore", "fede", "vero", "divo", "duce",
        # Cognomi frequentissimi che sono anche parole comuni. In coppia
        # restano riconoscibili ("Mario Costa"); da soli no, altrimenti
        # ogni "Costa" a inizio frase diventa una persona.
        "costa", "sala", "serra", "rocca", "croce", "prato", "riva", "villa",
        "gatto", "gatti", "gallo", "galli", "lupo", "lupi", "mele", "meli",
        "pesce", "oliva", "sordi", "grassi", "bianco", "bianchi", "verdi",
        "neri", "rossi", "russo", "greco", "moro", "biondi", "longo",
        "marino", "leone", "leoni", "monaco", "corona", "campana", "colomba",
        "fontana", "torre", "porta", "sacco", "cassa", "carta", "banca",
        "arena", "cava", "chiesa", "corso", "piazza", "valle", "monte",
        "ponte", "porto", "punta", "ripa", "sasso", "selva", "vetta",
    }
)


# ---------------------------------------------------------------------------
# Pacchetti
# ---------------------------------------------------------------------------
#
# Un riconoscitore o vale ovunque, o vale in un Paese solo. La distinzione
# non esisteva da nessuna parte: dentro l'unico interruttore ``fiscal``
# convivevano l'IBAN — mod-97, valido in tutti i Paesi SEPA — e il codice
# fiscale, che esiste solo qui. Chi voleva usare Mr. Rao su un documento
# straniero doveva prendersi anche i riconoscitori italiani, oppure
# rinunciare pure all'IBAN.
#
# I nomi restano quelli dei codici lingua ISO 639-1, cosi' il giorno in cui
# l'interfaccia avra' un selettore di lingua i due vocabolari coincidono.
CORE = "core"
IT = "it"
EN = "en"

#: Atti notarili, ricorsi, pratiche edilizie. **Spento di serie**, ed e' il
#: cuore della decisione, non un dettaglio di comodo.
#:
#: Qui c'e' una divergenza vera fra due pubblici, e hanno ragione tutti e
#: due. Per un notaio il riferimento catastale **e'** il dato piu' sensibile
#: della frase: dice esattamente di quale immobile si parla, e da li' si
#: risale al proprietario in un pomeriggio. Per un'azienda il numero di
#: protocollo e' cio' che permette di **ritrovare** la pratica, e toglierlo
#: rende il documento inservibile senza proteggere nessuno.
#:
#: Non si puo' decidere per entrambi con un interruttore acceso di serie,
#: e non e' un caso che «protocollo» e «repertorio» stiano gia' nel
#: vocabolario di cio' che **non** si redige: e' quello che impedisce a ogni
#: numero di pratica di essere letto come un telefono. Questo pacchetto
#: **capovolge** quella scelta, e per questo va acceso da chi sa di volerlo.
ATTI = "atti"

PACCHETTI_NOTI: tuple[str, ...] = (CORE, IT, EN, ATTI)


@dataclass
class PrivacyOptions:
    emails: bool = True
    phones: bool = True
    names: bool = True
    fiscal: bool = True  # CF, P.IVA, IBAN, carte di pagamento
    #: Riferimenti catastali e numeri di pratica.
    #:
    #: Il campo e' acceso, ma i suoi passi stanno nel pacchetto `ATTI`, che
    #: e' **spento**: serve accendere il pacchetto perche' succeda qualcosa.
    #: Sono due assi, come per i pacchetti nazionali -- l'interruttore dice
    #: *quale dato*, il pacchetto dice *per quale mestiere*.
    atti: bool = True
    #: Eta' e sesso: si trovano, si dicono nel rapporto, **non si tolgono**.
    #:
    #: L'interruttore decide se guardare, e non c'e' nessun secondo stato:
    #: acceso li segnala, spento non li cerca. E' l'unico caso nel motore in
    #: cui la sostituzione non esiste proprio, e la ragione sta scritta per
    #: esteso accanto ai due riconoscitori.
    quasi_id: bool = True
    amounts: bool = False
    urls: bool = True
    addresses: bool = True
    secrets: bool = True
    dates: bool = False  # solo date accanto a un contesto di nascita
    # Carta d'identita', patente, passaporto. Interruttore suo e non
    # dentro `fiscal`: un numero di documento non e' un dato fiscale, e
    # chi spegne i codici tributari non intende scoprire il passaporto.
    documenti: bool = True
    # Segnaposto numerati per valore distinto: `{{NAME_1}}`, `{{NAME_2}}`
    # (P6.1). **Acceso di default**, a differenza di `amounts` e `dates`,
    # perche' non aggiunge ne' toglie sostituzioni: cambia solo come sono
    # scritte, e senza numeri il documento redatto perde il senso —
    # «{{NAME}} ha citato {{NAME}} davanti a {{NAME}}» non si legge.
    #
    # Il costo di accenderlo di default e' reale e va detto: cambia
    # l'uscita di ogni conversione, quindi chi aveva costruito qualcosa
    # sopra la forma vecchia se ne accorge. Spegnerlo la riporta identica.
    #
    # Cosa NON e': una sostituzione reversibile. Il numero vive dentro il
    # documento e non porta da nessuna parte; il dizionario numero->valore
    # e' P6.9, sta fermo, e ha un'altra ragione di stare fermo.
    numerati: bool = True
    #: Il nome di battesimo **da solo**, quando non e' anche una parola.
    #:
    #: Oggi un nome isolato e' un sospetto, mai una sostituzione: «Rosa»,
    #: «Vera», «Costa» sono nomi *e* parole italiane. Quella ragione pero'
    #: non vale per «Walter», «Nazzareno», «Ludovica», che parole non sono —
    #: e sono l'88% dell'elenco (891 su 1017).
    #:
    #: **Accesa di serie dalla 1.26.0, e il predefinito l'ha deciso una
    #: misura sui documenti che non abbiamo scritto noi** — l'unico metro
    #: con cui in questo progetto si tocca una regola sui nomi.
    #:
    #: Sui **moduli in bianco**, dove ogni sostituzione e' sbagliata per
    #: costruzione, il costo e' **zero**: 0 in piu' sui venticinque moduli
    #: IRS, 0 sugli undici moduli amministrativi italiani. E' lo stesso
    #: corpus che aveva fatto ritirare l'euristica del cognome con 8 904
    #: sostituzioni sbagliate, quindi si confrontano numeri omogenei.
    #:
    #: Sulle **Gazzette Ufficiali**, dove i nomi ci sono davvero, prende 84
    #: nomi in piu' — «di Gianpaolo», «senatore Alessandro», «e Damiano».
    #:
    #: Lo zero non e' venuto gratis: le prime misure segnavano 26 falsi
    #: positivi sui moduli IRS (`North Carolina`, `West Virginia`,
    #: `St Thomas`) e 25 su un comune (`Torre Annunziata`). Sono diventate
    #: righe di `_PRIMA_NON_E_PERSONA`, e nessun banco scritto in casa le
    #: avrebbe mai prodotte.
    #:
    #: Resta un interruttore, e spento riporta l'uscita a quella della
    #: 1.25.0: il costo di cambiare un predefinito e' reale e va detto.
    names_alone: bool = True
    # QUI C'ERA `name_guess`, RITIRATA NELLA 1.13.0.
    #
    # Era l'euristica del cognome: due parole maiuscole che non sembrano
    # parole italiane sono nome e cognome, **senza nessun riscontro negli
    # elenchi**. Spenta di default dalla 1.7.2 (#5), tolta del tutto adesso.
    #
    # Il conto su documenti che non contengono un solo dato personale:
    # 8 904 sostituzioni sbagliate su venti moduli dell'Agenzia delle
    # Entrate in bianco, 14 376 su otto Gazzette, 2 888 su novantanove
    # moduli fiscali statunitensi. Mangiava «Redditi Persone Fisiche»,
    # «Quadro RN», «Imposta Lorda».
    #
    # **Riprodotto nel 2026-08 su corpora che non abbiamo scritto noi**, che
    # e' cio' che ha chiuso la questione: 27 moduli amministrativi italiani
    # in bianco scaricati da Agenzia Entrate, INPS, ADM e altri passano da
    # 27 sostituzioni sbagliate a 2 529 -- novantaquattro volte. Sui moduli
    # IRS da 15 a 622.
    #
    # Il difetto non era che indovinava: e' che DECIDEVA DA SOLA. Le altre
    # tre regole chiedono un riscontro (titolo, posta, adiacenza); questa
    # no. Lasciarla spenta ma disponibile significava tenere in interfaccia
    # una casella che nessuno deve accendere -- e una scelta che non va mai
    # fatta non e' una scelta, e' una trappola con un'etichetta.
    #
    # Le due liste dello studio (P1.8). Il motore decide con regole generali,
    # ma ogni studio ha nomi propri che ricorrono in ogni pratica — clienti,
    # controparti — e denominazioni interne che non vanno toccate mai. Prima
    # l'unica leva era spegnere un riconoscitore intero, che e' un martello
    # per un chiodo.
    #
    # `mai` non e' l'opposto di `sempre`: e' piu' forte. `sempre` aggiunge un
    # riconoscitore; `mai` mette il termine al riparo da **tutti**, compresi
    # quelli che non sapresti nemmeno di dover spegnere.
    sempre: tuple[str, ...] = ()
    mai: tuple[str, ...] = ()
    # Categorie da **rilevare senza sostituire** (P6.2). Il terzo stato che
    # prima non c'era: fino alla 1.19 spegnere un riconoscitore voleva dire
    # non cercarlo, e chi rileggeva il documento non aveva modo di sapere se
    # li' dentro non c'era niente o se avevamo guardato dall'altra parte.
    #
    #   interruttore acceso, categoria fuori da `segnala`  ->  sostituisce
    #   interruttore acceso, categoria dentro `segnala`    ->  rileva e dice
    #   interruttore spento                                ->  non cerca
    #
    # L'interruttore decide **se guardare**, `segnala` decide **cosa fare di
    # cio' che si trova**: mettere qui una categoria il cui interruttore e'
    # spento non la accende: non c'e' niente da segnalare se nessuno cerca.
    segnala: tuple[str, ...] = ()
    # Quali famiglie di riconoscitori eseguire. Il valore predefinito e' il
    # comportamento di sempre: nucleo universale piu' formati italiani.
    # Un documento inglese vorra' ``(CORE,)`` oggi e ``(CORE, EN)`` domani;
    # uno studio italiano che segue un cliente estero li vorra' entrambi.
    pacchetti: tuple[str, ...] = (CORE, IT, EN)
    # Prosa o modulo. La stessa regola ha segno opposto sulle due
    # popolazioni, e non e' un'opinione -- e' misurato. Su quali corpora,
    # perche' senza quello i numeri sembrano piu' forti di quanto siano:
    #
    #   A) oltre cento documenti amministrativi pubblici (moduli in bianco,
    #      gazzette, volumi statistici): la verita' di riferimento e' zero,
    #      quindi
    #      ogni sostituzione e' un errore;
    #   B) 1500 messaggi di python-list, prosa **inglese** tecnica;
    #   C) 6000 messaggi di mailing list italiane (lists.linux.it, 1103
    #      archivi, 56% in italiano) -- il corpus che conta per una regola
    #      italiana.
    #
    #   riscontro singolo negli elenchi   A: falsi pos.   B: nomi   C: nomi
    #   -> sospetto                              1 637      2 823     7 071
    #   -> sostituzione                          4 376      3 432    10 989
    #
    # Su un modulo «sospetto» toglie 2 739 errori. Su prosa italiana costa
    # il 55% dei nomi (10 989 -> 7 071) e triplica i sospetti, da 0,7 a 2,0
    # per messaggio: a quel punto l'elenco dei sospetti smette di essere
    # consultabile, che e' la funzione su cui si regge l'onesta' del
    # prodotto.
    #
    # La prima taratura era stata fatta sul corpus B, cioe' misurando una
    # regola italiana su testo inglese: dava +21% invece di +50%. Direzione
    # giusta, grandezza sbagliata di piu' del doppio.
    #
    # ``None`` = non si sa. In quel caso si sceglie la prudenza sul
    # documento (sospetto) e non sul richiamo, perche' un falso positivo
    # si vede leggendo l'uscita, un nome lasciato in chiaro no.
    prosa: bool | None = None


@dataclass
class RedactionReport:
    counts: dict[str, int] = field(default_factory=dict)
    total: int = 0
    # Cio' che *assomiglia* a un dato personale ed e' rimasto nel testo.
    # Un riconoscitore che non trova nulla e un documento che non contiene
    # nulla producono lo stesso numero — zero — e sono due situazioni
    # opposte. I sospetti distinguono il silenzio dalla pulizia.
    suspects: list[dict] = field(default_factory=list)
    # Numerazione dei segnaposto (P6.1). Spenta qui e accesa dalle opzioni:
    # il rapporto non conosce `PrivacyOptions`, e non deve.
    numerati: bool = False
    # valore normalizzato -> numero, per etichetta. Vive nel rapporto e
    # **muore con lui**: e' cio' che impedisce alla numerazione di diventare
    # un identificatore persistente (vedi `segnaposto`).
    _numeri: dict[str, dict[str, int]] = field(default_factory=dict, repr=False)
    # Categorie da **rilevare senza sostituire** (P6.2). Vedi `segnaposto`.
    segnala: frozenset[str] = frozenset()
    # Cio' che e' stato trovato e lasciato in chiaro **apposta**. Sta
    # separato dai sospetti perche' e' un'altra cosa: un sospetto e' un
    # dubbio del motore, questo e' una decisione di chi converte.
    rilevati: list[dict] = field(default_factory=list)

    def add(self, kind: str, n: int = 1) -> None:
        if n <= 0:
            return
        self.counts[kind] = self.counts.get(kind, 0) + n
        self.total += n

    def segnaposto(
        self, kind: str, base: str, valore: str, originale: str | None = None
    ) -> str:
        """Conta la sostituzione e restituisce il segnaposto da scrivere.

        Rilevato ma non sostituito (P6.2)
        ---------------------------------

        Se `kind` sta in `segnala`, questo metodo **non sostituisce**:
        rimette nel testo cio' che c'era e lo annota fra i `rilevati`.

        Fino alla 1.19 spegnere un riconoscitore voleva dire *non cercarlo*,
        e le due cose non erano separabili. Per chi deve far confrontare
        degli importi a un modello, o tenere eta' e sesso in una cartella
        clinica, la differenza e' tutta -- e il valore vero non e' nel testo
        ma nel rapporto: «ho lasciato in chiaro 3 importi, apposta» e'
        un'informazione per un DPO, il silenzio no. Oggi un riconoscitore
        spento non lascia traccia, e chi rilegge il documento non ha modo di
        sapere se li' dentro non c'era niente o se abbiamo guardato
        dall'altra parte.

        `originale` esiste per tre chiamanti su cinquantuno: quelli che
        passano un valore **diverso** dal testo trovato -- i codici corretti
        dall'OCR passano la versione buona, perche' e' quella che deve
        ricevere il numero. Restituendo quella si riscriverebbe il documento
        senza sostituire niente, che e' peggio di tutte e due le scelte.
        """
        if kind in self.segnala:
            testo = valore if originale is None else originale
            self.rilevati.append({"kind": kind, "sample": _mask(testo)})
            return testo
        return self._sostituisci(kind, base, valore)

    def rilevata(self, kind: str, valore: str) -> None:
        """Annota un dato trovato e lasciato in chiaro **per costruzione**.

        Non e' la stessa cosa di `segnaposto` con la categoria in `segnala`:
        li' e' una scelta di chi converte, che puo' cambiarla; qui non c'e'
        nessun percorso che sostituisca, e la ragione sta scritta accanto ai
        due riconoscitori che usano questo metodo (eta' e sesso). Chi volesse
        toglierli davvero ha gia' l'elenco «nascondi sempre», che li toglie.
        """
        self.rilevati.append({"kind": kind, "sample": _mask(valore)})

    def solo_rilevata(self, kind: str) -> bool:
        """Questa categoria viene trovata e lasciata in chiaro?

        Serve ai due chiamanti che contano **anche** qualcos'altro accanto
        alla sostituzione (`ocr_corretti`, che vuol dire «recuperato dall'OCR
        *e sostituito*»): in modalita' «segnala» quel contatore direbbe una
        cosa che non e' successa.
        """
        return kind in self.segnala

    def _sostituisci(self, kind: str, base: str, valore: str) -> str:
        """Il comportamento di sempre: conta e restituisce il segnaposto.

        Con la numerazione accesa: `{{NAME_1}}`, `{{NAME_2}}`, e **lo stesso
        valore riceve sempre lo stesso numero dentro lo stesso documento**.

        Perche' serve
        -------------

        Senza numeri, tre persone diverse diventano tre `{{NAME}}` identici
        e il documento redatto perde il senso: «`{{NAME}}` ha citato
        `{{NAME}}` davanti a `{{NAME}}`» non si legge, e un modello
        linguistico non ci puo' ragionare sopra. Con i numeri la frase resta
        una frase, e non serve nessun dizionario reversibile per ottenerlo --
        la numerazione e' una proprieta' del testo redatto, l'archivio dei
        valori veri e' un'altra cosa, e molto piu' pericolosa.

        Il vincolo che la tiene innocua
        -------------------------------

        Il numero **non deve essere stabile fra documenti**. Se `Mario
        Rossi` fosse `{{NAME_7}}` in ogni file, avremmo inventato un
        identificatore persistente -- cioe' un dato personale nuovo, creato
        da noi, in uno strumento che esiste per toglierli. Qui non puo'
        succedere per costruzione: la mappa sta in questo oggetto, che nasce
        e muore con una conversione. Chi un domani la spostasse in un file o
        in una cache condivisa cambierebbe la natura del prodotto, non un
        dettaglio di implementazione.

        Perche' il segnaposto arriva da fuori invece di essere composto qui
        -------------------------------------------------------------------

        `base` e' il letterale `"{{NAME}}"` scritto al punto di chiamata, e
        resta li' apposta: `check_docs.py` e
        `tests/test_segnaposto_non_riassorbiti.py` estraggono i segnaposto
        **leggendo il sorgente del motore**. Componendoli qui da una tabella,
        quelle due guardie smetterebbero di vedere qualsiasi cosa -- e
        passerebbero, verdi, senza guardare niente.
        """
        self.add(kind)
        if not self.numerati:
            return base
        etichetta = base[2:-2]
        # Stesso valore, stesso numero: le differenze di maiuscole, di
        # spaziatura e di punteggiatura non fanno due persone. «MARIO
        # ROSSI» e «Mario Rossi» sono lo stesso nome; «IT60 X054…» e
        # «IT60X054…» lo stesso conto.
        chiave = "".join(c for c in valore.casefold() if c.isalnum())
        assegnati = self._numeri.setdefault(etichetta, {})
        if chiave not in assegnati:
            assegnati[chiave] = len(assegnati) + 1
        # `SENTINELLA` al posto del trattino basso, e sparisce alla fine
        # (`_rinumera_per_comparsa`). Serve a distinguere **i segnaposto che
        # abbiamo messo noi adesso** da quelli che stavano gia' nel
        # documento in ingresso: un file gia' redatto, ripassato dal motore,
        # contiene `{{NAME_5}}` scritti da qualcun altro, e rinumerarli
        # vorrebbe dire riscrivere del testo che non abbiamo toccato.
        return f"{{{{{etichetta}{SENTINELLA}{assegnati[chiave]}}}}}"

    def suspect(self, kind: str, sample: str, why: str) -> None:
        self.suspects.append({"kind": kind, "sample": _mask(sample), "why": why})

    def to_dict(self) -> dict:
        rilevati_per_tipo: dict[str, int] = {}
        for r in self.rilevati:
            rilevati_per_tipo[r["kind"]] = rilevati_per_tipo.get(r["kind"], 0) + 1
        return {
            "counts": dict(self.counts),
            "total": self.total,
            "suspects": list(self.suspects),
            "suspects_total": len(self.suspects),
            # Tre numeri diversi, e tenerli separati e' il punto: `counts`
            # dice cosa e' stato tolto, `detected` cosa e' stato trovato e
            # lasciato **apposta**, `suspects` cosa il motore non ha saputo
            # decidere. Sommarli darebbe un totale che non vuol dire niente.
            "detected": list(self.rilevati),
            "detected_counts": rilevati_per_tipo,
            "detected_total": len(self.rilevati),
        }


_RE_SEGNAPOSTO_NUMERATO = re.compile(r"\{\{([A-Z][A-Z_]*?)_(\d+)\}\}")
# Solo i nostri, quelli ancora marcati.
_RE_SEGNAPOSTO_MARCATO = re.compile(rf"\{{\{{([A-Z][A-Z_]*?){SENTINELLA}(\d+)\}}\}}")


def senza_numeri(testo: str) -> str:
    """`{{NAME_3}}` torna `{{NAME}}`: il testo redatto nella forma piatta.

    A cosa serve davvero
    --------------------

    A confrontare. Due conversioni dello stesso documento con la
    numerazione accesa differiscono ovunque compaia un valore nuovo, e un
    confronto fra le due non dice piu' niente. Appiattendo i numeri si
    confronta cio' che il motore ha **deciso**, che e' la cosa che
    interessa quando si vuole sapere se e' cambiato il comportamento.

    E' anche il modo giusto di scrivere un controllo negativo. `"{{PHONE}}"
    not in uscita` con la numerazione accesa e' vero **sempre** -- l'uscita
    contiene `{{PHONE_1}}` -- quindi e' un controllo che non puo' fallire.
    Con questa funzione davanti torna a voler dire quello che dice.

    Cosa NON e': un modo di annullare la redazione. Toglie i numeri, non
    rimette i valori; il numero non porta da nessuna parte per costruzione
    (vedi `RedactionReport.segnaposto`).
    """
    return _RE_SEGNAPOSTO_NUMERATO.sub(r"{{\1}}", testo)


def _mask(s: str) -> str:
    """Quanto basta a ritrovarlo nel documento, non a leggerlo."""
    s = s.strip()
    if len(s) <= 4:
        return "•" * len(s)
    return f"{s[:2]}{'•' * (len(s) - 4)}{s[-2:]}"


def _replace_all(text: str, pattern: re.Pattern, placeholder: str, report: RedactionReport, kind: str) -> str:
    def _sub(m: re.Match) -> str:
        # Il valore numerato e' l'intera corrispondenza: questi
        # riconoscitori sostituiscono cio' che hanno trovato, per intero.
        return report.segnaposto(kind, placeholder, m.group(0))

    return pattern.sub(_sub, text)


def _context_before(text: str, start: int, window: int = 24) -> str:
    """The few characters preceding a match, used to disambiguate candidates."""
    return text[max(0, start - window) : start]


# Lunghezza dell'IBAN per Paese, dal registro ISO 13616 tenuto da SWIFT.
# Non e' un dettaglio di comodo: e' cio' che rende il mod-97 una prova
# invece di un filtro.
#
# Il mod-97 da solo scarta 96 candidati su 97. Sembra molto, e su un
# documento con dieci codici lo e'. Su un volume statistico o una Gazzetta
# pieni di codici lunghi, uno su 97 passa lo stesso -- e infatti sul banco
# comparivano IBAN su documenti che non ne contengono nessuno, «recuperati»
# dall'OCR. Il checksum protegge dai candidati sbagliati, non da uno spazio
# di candidati troppo largo.
#
# Codice Paese piu' lunghezza esatta tolgono quasi tutto quello spazio, e
# non costano richiamo: un IBAN vero ha sempre un codice Paese vero e la
# lunghezza del proprio Paese.
_IBAN_LUNGHEZZE = {
    "AD": 24, "AE": 23, "AL": 28, "AT": 20, "AZ": 28, "BA": 20, "BE": 16,
    "BG": 22, "BH": 22, "BR": 29, "BY": 28, "CH": 21, "CR": 22, "CY": 28,
    "CZ": 24, "DE": 22, "DK": 18, "DO": 28, "EE": 20, "EG": 29, "ES": 24,
    "FI": 18, "FO": 18, "FR": 27, "GB": 22, "GE": 22, "GI": 23, "GL": 18,
    "GR": 27, "GT": 28, "HR": 21, "HU": 28, "IE": 22, "IL": 23, "IQ": 23,
    "IS": 26, "IT": 27, "JO": 30, "KW": 30, "KZ": 20, "LB": 28, "LC": 32,
    "LI": 21, "LT": 20, "LU": 20, "LV": 21, "LY": 25, "MC": 27, "MD": 24,
    "ME": 22, "MK": 19, "MR": 27, "MT": 31, "MU": 30, "NL": 18, "NO": 15,
    "PK": 24, "PL": 28, "PS": 29, "PT": 25, "QA": 29, "RO": 24, "RS": 22,
    "SA": 24, "SC": 31, "SD": 18, "SE": 24, "SI": 19, "SK": 24, "SM": 27,
    "ST": 25, "SV": 28, "TL": 23, "TN": 24, "TR": 26, "UA": 29, "VA": 22,
    "VG": 24, "XK": 20,
}


def iban_checksum_ok(candidate: str) -> bool:
    """ISO 13616: codice Paese, lunghezza attesa per quel Paese, mod-97.

    **Si tolgono tutti i separatori che il pattern ammette**, non solo lo
    spazio, ed e' una riga che vale la pena guardare due volte: qui si
    toglieva il solo spazio, mentre `_RE_IBAN_SPAZIATO` accettava anche il
    trattino. Un IBAN scritto `IT60-X054-2811-...` arrivava fin qui, il
    trattino restava dentro, la lunghezza non tornava, e il candidato veniva
    **scartato in silenzio** -- il rapporto diceva zero IBAN.

    E' il difetto che si crea ogni volta che due punti del motore hanno
    un'idea diversa di cosa sia un separatore. Quando si allarga l'uno si
    guarda l'altro.
    """
    s = re.sub(r"[\s\- ]", "", candidate).upper()
    if len(s) < 15 or len(s) > 34:
        return False
    if _IBAN_LUNGHEZZE.get(s[:2]) != len(s):
        return False
    rearranged = s[4:] + s[:4]
    digits = ""
    for ch in rearranged:
        if ch.isdigit():
            digits += ch
        elif "A" <= ch <= "Z":
            digits += str(ord(ch) - 55)
        else:
            return False
    return int(digits) % 97 == 1


# Tabelle del carattere di controllo del codice fiscale (DM 23/12/1976).
# I caratteri in posizione dispari pesano diversamente da quelli in
# posizione pari: e' quello che rende il controllo capace di accorgersi
# anche di due caratteri scambiati fra loro.
_CF_DISPARI = {
    **{c: v for c, v in zip("0123456789", (1, 0, 5, 7, 9, 13, 15, 17, 19, 21))},
    **{
        c: v
        for c, v in zip(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            (1, 0, 5, 7, 9, 13, 15, 17, 19, 21, 2, 4, 18, 20, 11,
             3, 6, 8, 12, 14, 16, 10, 22, 25, 24, 23),
        )
    },
}
_CF_PARI = {
    **{c: int(c) for c in "0123456789"},
    **{c: i for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ")},
}


def cf_check_char_ok(candidate: str) -> bool:
    """Carattere di controllo del codice fiscale.

    Non serve a rifiutare: un codice fiscale con la struttura giusta viene
    sostituito comunque, perche' su un dato personale l'errore va fatto
    nella direzione prudente. Serve a **sapere**: se la struttura torna e
    il carattere di controllo no, quasi sempre il documento arriva da un
    OCR che ha storpiato un carattere — e allora conviene guardare se ha
    storpiato anche qualcos'altro.
    """
    s = re.sub(r"[\s\-.]", "", candidate).upper()
    if len(s) != 16 or not s.isalnum():
        return False
    try:
        totale = sum(
            (_CF_DISPARI if i % 2 == 0 else _CF_PARI)[c]
            for i, c in enumerate(s[:15])
        )
    except KeyError:
        return False
    return "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[totale % 26] == s[15]


def piva_check_ok(candidate: str) -> bool:
    """Cifra di controllo della partita IVA (undici cifre, Luhn all'italiana).

    Stessa scelta del codice fiscale: non rifiuta, informa. Undici cifre in
    un contesto fiscale restano sostituite comunque; se il controllo non
    torna, il numero diventa un sospetto — perche' o non era una partita
    IVA, o il documento e' storpiato.
    """
    p = re.sub(r"[\s\-.]", "", candidate)
    if len(p) != 11 or not p.isdigit():
        return False
    totale = 0
    for i, c in enumerate(p[:10]):
        n = int(c)
        if i % 2:
            n *= 2
            if n > 9:
                n -= 9
        totale += n
    return (10 - totale % 10) % 10 == int(p[10])


# ---------------------------------------------------------------------------
# Tolleranza agli errori dell'OCR, tenuta a bada dai checksum
# ---------------------------------------------------------------------------

# Le confusioni tipiche del riconoscimento ottico, nelle due direzioni.
# Non servono a indovinare: servono a proporre un candidato che poi deve
# passare il *suo* controllo matematico. E' l'unico modo di essere
# tolleranti senza aprire la porta ai falsi positivi.
_A_CIFRA = {
    "O": "0", "D": "0", "Q": "0", "I": "1", "L": "1", "Z": "2", "E": "3",
    "A": "4", "S": "5", "G": "6", "T": "7", "B": "8", "J": "3",
}
_A_LETTERA = {
    "0": "O", "1": "I", "2": "Z", "3": "E", "4": "A", "5": "S", "6": "G",
    "7": "T", "8": "B",
}

# Confusioni fra lettere. Sembrano superflue — sono gia' lettere — ma la
# piu' frequente di tutte e' proprio questa: la elle minuscola letta al
# posto della i maiuscola. "IT60" diventa "lT60", che di lettere ne ha
# ancora due e quindi supera ogni controllo di forma, e fallisce il mod-97.
_FRA_LETTERE = {"l": "I", "|": "I", "¦": "I", "ı": "I", "…": "I"}

# Struttura del codice fiscale: L = lettera, D = cifra.
_CF_FORMA = "LLLLLLDDLDDLDDDL"

MAX_CORREZIONI_OCR = 2


def _coerce(token: str, forma: str) -> tuple[str, int] | None:
    """Porta ogni carattere nella classe che la struttura richiede.

    Restituisce (candidato, quante correzioni) oppure None se ne servono
    troppe: oltre due non e' piu' un errore di lettura, e' un altro dato.
    """
    if len(token) != len(forma):
        return None
    fuori = []
    corretti = 0
    for c, atteso in zip(token.upper(), forma):
        if atteso == "D":
            if c.isdigit():
                fuori.append(c)
                continue
            sostituto = _A_CIFRA.get(c)
        else:
            if c.isalpha():
                fuori.append(c)
                continue
            sostituto = _A_LETTERA.get(c)
        if sostituto is None:
            return None
        fuori.append(sostituto)
        corretti += 1
        if corretti > MAX_CORREZIONI_OCR:
            return None
    return "".join(fuori), corretti


def cf_ocr_recover(token: str) -> str | None:
    """Un codice fiscale storpiato dall'OCR, se il controllo lo conferma."""
    esito = _coerce(token, _CF_FORMA)
    if not esito:
        return None
    candidato, corretti = esito
    if corretti == 0 or not _RE_CF.fullmatch(candidato):
        return None
    return candidato if cf_check_char_ok(candidato) else None


def iban_ocr_recover(token: str) -> str | None:
    """Un IBAN storpiato dall'OCR, se il mod-97 lo conferma."""
    pulito = re.sub(r"\s", "", token)
    if not 15 <= len(pulito) <= 34:
        return None
    # Almeno una delle due iniziali dev'essere gia' una lettera.
    #
    # Senza questo vincolo il numero d'ordine 5551234567890123 diventava
    # "SS51234567890123" con due correzioni, e quel candidato il mod-97 lo
    # supera. Il checksum protegge dai candidati sbagliati, non da uno
    # spazio di candidati troppo largo: se puoi trasformare qualunque
    # sequenza di cifre in un IBAN, prima o poi ne azzecchi uno.
    if not any(c.isalpha() for c in pulito[:2]):
        return None
    forma = "LLDD" + "A" * (len(pulito) - 4)
    fuori = []
    corretti = 0
    for grezzo, atteso in zip(pulito, forma):
        c = grezzo.upper()
        if atteso == "A":  # alfanumerico: va bene qualunque cosa
            fuori.append(c)
            continue
        if atteso == "L":
            if grezzo in _FRA_LETTERE:
                sostituto = _FRA_LETTERE[grezzo]
            elif c.isalpha():
                fuori.append(c)
                continue
            else:
                sostituto = _A_LETTERA.get(c)
        else:
            if c.isdigit():
                fuori.append(c)
                continue
            sostituto = _A_CIFRA.get(c)
        if sostituto is None:
            return None
        corretti += 1
        if corretti > MAX_CORREZIONI_OCR:
            return None
        fuori.append(sostituto)
    candidato = "".join(fuori)
    if corretti == 0 or not candidato.isalnum():
        return None
    return candidato if iban_checksum_ok(candidato) else None


def luhn_ok(candidate: str) -> bool:
    """Controllo di Luhn (ISO/IEC 7812). Un numero lungo qualsiasi lo
    supera una volta su dieci: unito al vincolo sul primo digit e sulla
    lunghezza, basta a distinguere una carta da un codice interno."""
    digits = [int(c) for c in candidate if c.isdigit()]
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _phone_is_plausible(m: re.Match, contesto: bool | None = None) -> bool:
    """Decide se una sequenza di cifre e' un numero di telefono.

    Accetta con prefisso internazionale, con prefisso di cellulare italiano
    (3xx) o con una parola di contesto davanti; per i fissi pretende anche
    un separatore, cosi' un numero di protocollo di dieci cifre resta al
    suo posto.

    ``contesto`` serve a chi ha gia' la parola di contatto **dentro** la
    corrispondenza — «Tel.02 1234567», dove l'etichetta e il numero escono
    attaccati dall'OCR. Li' guardare all'indietro da ``m.start()`` leggerebbe
    cio' che precede «Tel.», cioe' il posto sbagliato. Non e' una scorciatoia
    per saltare il controllo: e' lo stesso controllo, fatto dove il dato sta.
    """
    body = m.group("body")
    if _RE_DATELIKE.match(body.strip()):
        return False

    digits = re.sub(r"\D", "", body)
    n = len(digits)
    has_sep = any(sep in body for sep in (" ", "-", ".", "/"))
    ctx = (
        contesto
        if contesto is not None
        else bool(_RE_PHONE_CTX.search(_context_before(m.string, m.start())))
    )

    # LA BARRA COSTA UNA PAROLA DI CONTESTO, e la ragione e' la stessa per
    # cui in P3.7 i telefoni non sono stati allentati come IBAN e carte: un
    # recapito **non ha nessuna aritmetica** che possa smentirne la forma,
    # quindi ogni permesso in piu' si paga chiedendo qualcos'altro.
    #
    # Misurato: ammettendo la barra senza condizioni, su 3,3 milioni di
    # caratteri di moduli fiscali comparivano 2 sostituzioni sbagliate --
    # numerazioni di colonne come «315 316 317 318 319 /» che la barra
    # saldava in un numero unico abbastanza lungo. Chiedendo la parola di
    # contatto il costo torna a zero, e il caso vero non si perde: su una
    # carta intestata la barra viene sempre dopo «Tel.».
    # Il prefisso internazionale vale quanto la parola di contatto: «+39
    # 011/7323929» si dichiara da solo.
    if "/" in body and not ctx and not m.group("prefix"):
        return False

    # Una numerazione di colonne si riconosce dalla forma, ma una parola di
    # contesto vale piu' della forma: se davanti c'e' scritto «tel.», e'
    # un recapito anche se le cifre per caso contano.
    if not ctx and _is_numbering_sequence(m.group(0)):
        return False

    prefix = m.group("prefix")
    if prefix:
        # Lo "00" internazionale e' anche l'inizio di moltissimi numeri di
        # pratica: "0034578921" e' un protocollo, e il pattern lo leggeva
        # come una chiamata in Spagna (00-34, poi sei cifre). Trovato su un
        # documento amministrativo inglese vero, dove ogni sostituzione e'
        # per definizione un errore.
        #
        # La differenza e' come sono scritti: un numero internazionale per
        # esteso ha quasi sempre una spaziatura -- "0044 7700 900412" --
        # mentre un codice di riferimento e' un blocco unico. Il "+" resta
        # affidabile senza altre prove, perche' dentro un numero di
        # protocollo non ci finisce.
        #
        # Il separatore va cercato in **tutta** la corrispondenza, non solo
        # nel corpo: in "0039 3391234567" lo spazio sta fra prefisso e
        # corpo, e guardare il solo corpo faceva rifiutare un numero vero.
        tutto = m.group(0)
        sep_ovunque = any(s in tutto for s in (" ", "-", "."))
        if prefix.startswith("00") and not sep_ovunque and not ctx:
            return False
        # Nessun indicativo di Paese comincia per zero: sono numeri da 1 a
        # 999 e lo zero e' proprio il carattere che li introduce. Le tabelle
        # statistiche invece sono piene di «000 000 000 116», che il
        # pattern leggeva come una chiamata verso il Paese numero 0.
        if not ctx and (m.group("cc") or "").startswith("0"):
            return False
        return 6 <= n <= (11 if m.group("cc") == "39" else 14)

    if ctx:
        return 6 <= n <= 13

    # Cellulare italiano. La decade 30x non e' assegnata a nessun operatore:
    # «300 000 201», che su una tabella e' un valore, non e' un recapito.
    if digits.startswith("3") and digits[1:2] != "0" and 9 <= n <= 10:
        return True

    # Fisso italiano. Il prefisso di distretto e' 0 seguito da una cifra
    # significativa — 02, 06, 011, 081 — mai da un altro zero: «000 000 52»
    # su una tabella di valori non e' un recapito.
    if (digits.startswith("0") and digits[1:2] != "0"
            and 8 <= n <= 11 and has_sep):
        return True

    return False


def _amount_is_plausible(m: re.Match) -> bool:
    """A decimal is an amount only with a currency marker, a thousands
    group, or a fiscal context word — not every '1.10' in the text."""
    if m.group("cur_pre") or m.group("cur_post"):
        return True
    num = m.group("num")
    if num.count(".") + num.count(",") > 1:  # e.g. 1.500,00
        return True
    return bool(_RE_AMOUNT_CTX.search(_context_before(m.string, m.start())))


def _is_common_word(token: str) -> bool:
    # Anche le parole che fermano il riconoscitore di indirizzi: "via
    # Corriere Espresso" non e' un indirizzo, e non e' neanche una
    # persona. Un presidio dentro un riconoscitore non protegge gli altri.
    t = token.lower().strip("'’-")
    return t in COMMON_CAPITALIZED or t in _ADDRESS_STOPWORDS


# Due parole stanno nell'elenco delle parole comuni per un motivo solo: sono
# meta' del nome di una regione. Ma «Giulia» ed «Emilia» sono anche due dei
# nomi di battesimo piu' diffusi in Italia, e il prezzo era che
# «la dott.ssa Giulia Conti» restava intera nel documento -- comune e
# cognome comune, nessuno dei due contava come prova.
#
# Toglierle dall'elenco avrebbe rotto «Friuli Venezia Giulia» ed «Emilia
# Romagna», che nei documenti amministrativi ci sono quasi sempre. Quindi
# non si toglie niente: si guarda la parola accanto. E' la stessa regola di
# sempre -- si allenta solo dove c'e' qualcosa che possa dire di no -- e qui
# a dire di no e' il vicino, non un conto.
_LOCUZIONI_GEOGRAFICHE = {
    "giulia": {"prima": frozenset({"venezia"}), "dopo": frozenset()},
    "emilia": {"prima": frozenset(), "dopo": frozenset({"romagna"})},
}


# Le particelle dei cognomi composti: «Di Salvo», «De Luca», «Lo Bianco».
#
# **Perche' esistono qui e non nell'elenco dei cognomi.** Quasi tutte sono
# preposizioni, e quindi stanno — giustamente — fra le parole comuni: `di`,
# `del`, `della`, `dei`, `degli`, `da`, `dal`, `dalla`, `lo`, `la`. Il
# riconoscitore lavora su tratti continui di parole *non* comuni, quindi la
# particella **spezzava il tratto**: «Walter Di Salvo» diventava «Walter» e
# «Salvo», due parole isolate, e una parola sola non basta mai. Il cognome
# restava in chiaro senza che niente lo segnalasse.
#
# Misurato prima di scrivere una riga: `Walter Di Salvo ha firmato` usciva
# intatto sia in prosa sia su modulo, e `Il sig. Walter Di Salvo` usciva
# come `Il sig. {{NAME_1}} Di Salvo` — il nome tolto e il cognome lasciato,
# che e' il modo peggiore di sbagliare.
#
# `de`, `li`, `lu` sono nell'insieme ma parole comuni non sono: infatti «Luca
# De Luca» funzionava gia'. L'insieme le tiene lo stesso, perche' la regola
# dev'essere la stessa per tutte — se domani `de` finisse fra le parole
# comuni, il difetto tornerebbe da quella porta.
#
# `san`, `santa`, `santo` **restano fuori**: aprono i toponimi (San Giovanni,
# Santa Croce), che sui documenti sono molti piu' dei cognomi.
_PARTICELLE_COGNOME = frozenset({
    "di", "de", "del", "dello", "della", "delle", "dei", "degli",
    "da", "dal", "dalla", "dallo", "dagli", "lo", "la", "li", "lu",
})


def _forma_incollata(particella: str, seguente: str) -> str:
    """«di» + «salvo» -> «disalvo», come stanno negli elenchi."""
    return particella + seguente


def _cognome_composto_noto(particella: str, seguente: str) -> bool:
    """La coppia «particella + parola» e' un cognome che gli elenchi hanno gia'.

    **L'elenco dei cognomi contiene gia' 151 composti**, ma incollati e senza
    apostrofo — `disalvo`, `dipietro`, `damico`, `dangelo` — perche' la lista
    di provenienza era normalizzata cosi'. Nei documenti si scrive «Di Salvo»,
    quindi quel dato c'era da sempre ed era irraggiungibile: bastava provare
    la forma incollata prima di dire di no.
    """
    if particella not in _PARTICELLE_COGNOME:
        return False
    return _forma_incollata(particella, seguente) in SURNAMES


def _cognome_apostrofato(token: str) -> bool:
    """«D'Amico», «Dell'Aquila»: il pezzo dopo l'apostrofo fa il cognome.

    Stessa storia della forma incollata, con l'apostrofo al posto dello
    spazio: negli elenchi c'e' `damico`, nel documento c'e' `D'Amico`.
    """
    t = token.lower().strip("'’-.,;:")
    pezzi = re.split(r"['’]", t)
    if len(pezzi) != 2 or not pezzi[1]:
        return False
    testa, coda = pezzi
    if testa not in _PARTICELLE_COGNOME and testa not in {"d", "dell", "l", "sant"}:
        return False
    return (testa + coda) in SURNAMES or coda in SURNAMES or coda in FIRST_NAMES


def _cognome_appoggiato(tokens: list[str]) -> bool:
    """L'ultima parola e' comune, ma e' un cognome noto e davanti ha un nome.

    Quarantadue cognomi degli elenchi sono anche parole comuni: Conti,
    Villa, Carta, Porta, Valle, Forte, Gentile, Grande, e i nomi di citta'
    che sono cognomi frequentissimi -- Napoli, Ferrara, Messina, Catania,
    Salerno, Ragusa, Udine, Brescia. Dopo un titolo professionale la
    potatura di coda li buttava via uno per uno, e «il dott. Marco Conti»
    usciva come «il dott. {{NAME}} Conti»: il nome tolto e il cognome
    lasciato, che e' il modo peggiore di sbagliare -- il documento sembra
    trattato e il dato che identifica la persona e' ancora li'.

    Non basta che l'ultima parola sia un cognome: deve avere davanti una
    parola che negli elenchi c'e' davvero. E' la prova che si tratta di una
    coppia nome-cognome e non della parola comune finita per caso in fondo
    a una frase.
    """
    if len(tokens) < 2:
        return False
    ultimo = tokens[-1].lower().strip("'’-.,;:")
    prima = tokens[-2].lower().strip("'’-.,;:")
    if ultimo in SURNAMES and (prima in FIRST_NAMES or prima in SURNAMES):
        return True
    # Il cognome composto, dove fra il nome e il cognome c'e' la particella.
    #
    # Senza questo ramo la potatura di coda smontava il nome un pezzo per
    # volta: «il sig. Walter Di Salvo» perdeva prima «Salvo» (parola comune),
    # poi «Di» (preposizione), e usciva `il sig. {{NAME_1}} Di Salvo` — il
    # nome tolto e il cognome lasciato. E' lo stesso difetto per cui questa
    # funzione era stata scritta, rientrato da un'altra porta.
    if prima in _PARTICELLE_COGNOME:
        if _cognome_composto_noto(prima, ultimo):
            return True
        if len(tokens) >= 3 and (ultimo in SURNAMES or ultimo in FIRST_NAMES):
            avanti = tokens[-3].lower().strip("'’-.,;:")
            return avanti in FIRST_NAMES or avanti in SURNAMES
    return False


def _is_common_in_context(tokens: list[str], i: int) -> bool:
    """Come ``_is_common_word``, ma sa cosa c'e' intorno."""
    t = tokens[i].lower().strip("'’-.,;:")
    loc = _LOCUZIONI_GEOGRAFICHE.get(t)
    if loc is not None:
        prec = tokens[i - 1].lower().strip("'’-.,;:") if i > 0 else ""
        succ = tokens[i + 1].lower().strip("'’-.,;:") if i + 1 < len(tokens) else ""
        return prec in loc["prima"] or succ in loc["dopo"]
    return _is_common_word(tokens[i])


# Terminazioni tipiche di sostantivi e aggettivi italiani. Nessun elenco di
# parole puo' essere completo, ma la morfologia non ha bisogno di elenchi:
# "Industriale" e "Tecnico" finiscono come finiscono le parole, non come
# finiscono i cognomi. Vale solo per l'euristica: un cognome riconosciuto
# resta un cognome anche se termina in -ale (Vitale, Natale).
_WORDLIKE_SUFFIXES = (
    "zione", "zioni", "sione", "sioni", "mento", "menti", "aggio", "aggi",
    "anza", "enza", "ismo", "ista", "isti", "iste", "tore", "trice", "trici",
    "ale", "ali", "are", "ile", "ili", "ico", "ica", "ici", "iche",
    "oso", "osa", "osi", "ose", "ivo", "iva", "ivi", "ive", "bile", "bili",
    "ezza", "ezze", "orio", "oria", "ario", "aria", "esimo", "evole",
    "ura", "ure", "udine", "eria", "ficio", "logia", "grafia", "metro",
)


# Parole che dicono «questa sequenza e' un ente, non una persona».
# Trovate sui documenti veri, non immaginate: la sezione dell'otto per
# mille di un modello Redditi ne e' fatta quasi per intero.
_ENTITY_WORDS = frozenset(
    {
        "chiesa", "chiese", "parrocchia", "diocesi", "curia", "arcidiocesi",
        "congregazione", "confessione", "unione", "comunita", "comunità",
        "associazione", "associazioni", "fondazione", "fondazioni",
        "istituto", "istituti", "ente", "enti", "organizzazione", "onlus",
        "societa", "società", "cooperativa", "consorzio", "azienda",
        "agenzia", "ministero", "dipartimento", "direzione", "ufficio",
        "comune", "provincia", "regione", "prefettura", "questura",
        "camera", "tribunale", "procura", "corte", "commissione",
        "universita", "università", "ospedale", "banca", "cassa",
        "federazione", "confederazione", "sindacato", "partito",
        "repubblica", "stato", "governo", "presidenza", "segreteria",
        "gazzetta", "bollettino", "registro", "albo", "elenco",
        # --- luoghi e istituzioni intitolati a una persona (1.20.0) ---
        #
        # Aggiunte dopo una misura, non a intuito: `Ospedale San Raffaele` e
        # `Istituto Comprensivo Alessandro Manzoni` restavano intatti perche'
        # `ospedale` e `istituto` erano gia' qui, mentre `Policlinico Agostino
        # Gemelli` diventava `{{NAME}}` e `Teatro Giuseppe Verdi` pure. Sono
        # falsi positivi su una classe intera, e distruttivi: la frase perde
        # il soggetto, non un dato.
        #
        # **Il criterio, e perche' e' stretto.** Una parola di questo elenco
        # scherma l'INTERA sequenza maiuscola (vedi `_scrub_names`): se ne
        # entra una che in un documento vero precede il nome di una persona
        # viva, quella persona smette di essere protetta. Quindi qui va solo
        # cio' che nomina un **edificio o un'istituzione** e che non regge un
        # nome di persona come intestatario.
        #
        # **Il prezzo, misurato e non stimato.** Lo schermo scatta solo nella
        # forma *adiacente* -- parola d'ente e nome attaccati, senza
        # punteggiatura ne' ruolo in mezzo. Quindi «Policlinico Gemelli -
        # referente Dott. Mario Rossi» resta protetto (il trattino e
        # l'appellativo spezzano la sequenza), mentre «Clinica Mario Rossi»
        # ora e' schermato per intero. E' il prezzo di ogni riga di questo
        # elenco, comprese quelle che c'erano gia' -- «Ufficio Mario Rossi»
        # e «Fondazione Mario Rossi» si comportano cosi' da sempre -- ed e'
        # accettato perche' in quella forma la lettura «ente» e' quella
        # giusta quasi sempre. Non e' accettabile per le parole qui sotto.
        #
        # Restano fuori apposta:
        #
        #   * `studio`  -- «Studio Legale Avv. Mario Rossi» e' un
        #                  professionista, cioe' esattamente il dato da
        #                  proteggere;
        #   * `ordine`, `opera`, `parco`, `porto`, `monte` -- parole comuni o
        #                  verbi, che entrerebbero in sequenze che non sono
        #                  enti;
        #   * le sigle (`INPS`, `ASL`) -- sono un token solo, non le vede il
        #                  riconoscitore delle coppie, e schermerebbero
        #                  «ASL Mario Rossi» senza guadagnare niente.
        "policlinico", "poliambulatorio", "clinica", "presidio", "distretto",
        "teatro", "cinema", "auditorium", "museo", "biblioteca", "pinacoteca",
        "conservatorio", "accademia", "galleria",
        "aeroporto", "stazione", "interporto",
        "scuola", "liceo", "ginnasio", "convitto", "seminario", "collegio",
        "ateneo", "politecnico", "facolta", "facoltà",
        "caserma", "comando", "municipio", "circoscrizione", "consolato",
        "ambasciata", "senato", "parlamento", "ispettorato", "osservatorio",
        "soprintendenza", "sovrintendenza", "autorita", "autorità", "garante",
        "basilica", "cattedrale", "duomo", "santuario", "abbazia", "monastero",
        "convento", "oratorio", "istituzione", "cassazione",
    }
)


def _is_entity_word(token: str) -> bool:
    return token.lower().strip("'’-.,;:") in _ENTITY_WORDS


def _looks_like_word(token: str) -> bool:
    t = token.lower().strip("'’-")
    if len(t) < 5:
        return False
    return t.endswith(_WORDLIKE_SUFFIXES)


# Forme che *assomigliano* a un dato a struttura fissa. Girano sul testo
# gia' redatto: quello che e' stato sostituito non c'e' piu', quindi cio'
# che resta e' davvero rimasto.
_RE_QUASI_CF = re.compile(r"(?<![\w-])[A-Z0-9]{16}(?![\w-])")

# Per il recupero serve tollerare anche la minuscola: la elle minuscola
# letta al posto della i maiuscola e' la confusione piu' frequente di tutte.
_RE_FUZZY_CF = re.compile(r"(?<![\w-])[A-Za-z0-9]{16}(?![\w-])")

# Per l'IBAN il pattern dei sospetti non basta: pretende due cifre in
# terza e quarta posizione, e quelle sono proprio le posizioni che l'OCR
# storpia ("IT60" letto "IT6O"). Qui si accetta qualunque sequenza
# alfanumerica lunga come un IBAN, purche' almeno una delle due iniziali
# sia gia' una lettera; a scartarla ci pensa il mod-97.
_RE_FUZZY_IBAN = re.compile(
    r"(?<![\w-])(?=[A-Za-z0-9]?[A-Za-z])[A-Za-z0-9]{15,34}(?![\w-])"
)

# Le prime due lettere sono quelle che l'OCR sbaglia piu' spesso: "IT60"
# letto "lT60" o "1T6O". Qui non si pretende la maiuscola, altrimenti il
# sospetto non scatterebbe proprio nel caso che lo motiva.
_RE_QUASI_IBAN = re.compile(
    r"(?<![\w-])[A-Za-z0-9]{2}\d{2}[A-Za-z0-9]{11,30}(?![\w-])"
)

_RE_QUASI_CARTA = re.compile(r"(?<![\w.])(?:\d[ \-]?){15,16}(?![\w])")

# Un recapito storpiato: dopo "cell." o "tel." una sequenza che mescola
# cifre e lettere non e' un numero, ma quasi sempre lo era prima della
# scansione.
_RE_QUASI_TEL = re.compile(
    r"(?i)\b(?:tel|cell|cellulare|telefono|fax|recapito)\b\.?\s*[:\-]?\s*"
    r"(?P<val>[0-9A-Za-z][0-9A-Za-z \-.]{5,18}[0-9A-Za-z])"
)


def find_suspects(text: str, report: RedactionReport, opts: PrivacyOptions) -> None:
    """Segnala cio' che somiglia a un dato personale ed e' rimasto.

    E' la risposta al limite piu' serio del motore: sul testo prodotto da
    un OCR i riconoscitori cercano forme *valide* e trovano forme *quasi*
    valide — `A01` letto `AD1`, `IT60` letto `1T6O` — e il dato resta nel
    testo, ancora perfettamente leggibile da una persona.

    Non si puo' sostituire senza certezza, o si redige mezzo documento.
    Ma si puo' dire dove guardare: "3 redatti, 2 sospetti" e' una frase
    onesta, "3 redatti" da sola no.
    """
    if not text:
        return

    if opts.phones:
        for m in _RE_QUASI_TEL.finditer(text):
            tok = m.group("val")
            if sum(c.isdigit() for c in tok) >= 5 and any(c.isalpha() for c in tok):
                report.suspect(
                    "telefono",
                    tok,
                    "preceduto da una parola di contatto ma contiene lettere: "
                    "possibile lettura OCR sbagliata",
                )

    if opts.fiscal:
        # Il quasi-codice-fiscale e' italiano; il quasi-IBAN e la
        # quasi-carta valgono ovunque, quindi restano fuori dal pacchetto.
        if IT in opts.pacchetti:
            for m in _RE_QUASI_CF.finditer(text):
                tok = m.group(0)
                lettere = sum(c.isalpha() for c in tok)
                cifre = sum(c.isdigit() for c in tok)
                # Un hash o un identificativo non hanno questa proporzione.
                if 6 <= lettere <= 11 and 5 <= cifre <= 10:
                    report.suspect(
                        "codice_fiscale",
                        tok,
                        "sedici caratteri con la proporzione di un codice "
                        "fiscale, ma la struttura non torna: possibile "
                        "lettura OCR sbagliata",
                    )
        for m in _RE_QUASI_IBAN.finditer(text):
            tok = m.group(0)
            if sum(c.isalpha() for c in tok) < 3 or sum(c.isdigit() for c in tok) < 8:
                continue
            report.suspect(
                "iban",
                tok,
                "ha la forma di un IBAN ma non supera il controllo mod-97",
            )
        for m in _RE_QUASI_CARTA.finditer(text):
            cifre = re.sub(r"\D", "", m.group(0))
            if len(cifre) in (15, 16):
                report.suspect(
                    "carta",
                    m.group(0),
                    "sedici cifre che non superano il controllo di Luhn",
                )


def _scrub_urls(text: str, report: RedactionReport) -> str:
    def _sub(m: re.Match) -> str:
        raw = m.group(0)
        trail = ""
        while raw and raw[-1] in ".,;:!?)]}'\"":
            trail = raw[-1] + trail
            raw = raw[:-1]
        if not raw:
            return m.group(0)
        return report.segnaposto("urls", "{{URL}}", raw) + trail

    return _RE_URL.sub(_sub, text)


def _scrub_secrets(text: str, report: RedactionReport) -> str:
    for kind, pattern in _RE_SECRETS:
        text = _replace_all(text, pattern, "{{SECRET}}", report, "secrets")

    def _kv(m: re.Match) -> str:
        # Il numero segue il **valore**, non l'etichetta: `token: abc` e
        # `api_key: abc` sono la stessa credenziale scritta due volte, e
        # devono ricevere lo stesso numero.
        return (
            m.group(1)
            + m.group("sep")
            + report.segnaposto("secrets", "{{SECRET}}", m.group("val"))
        )

    def _kv_debole(m: re.Match) -> str:
        if not _secret_value_is_plausible(m.group("val")):
            return m.group(0)
        return (
            m.group(1)
            + m.group("sep")
            + report.segnaposto("secrets", "{{SECRET}}", m.group("val"))
        )

    def _corto(m: re.Match) -> str:
        return (
            m.group(1)
            + m.group("sep")
            + report.segnaposto("secrets", "{{SECRET}}", m.group("val"))
        )

    # La frase di recupero per prima: e' l'unica il cui valore contiene
    # spazi, e se passasse dopo gli altri troverebbe la prima parola gia'
    # sostituita.
    text = _RE_SECRET_FRASE.sub(_corto, text)
    text = _RE_SECRET_KV.sub(_kv, text)
    text = _RE_SECRET_KV_DEBOLE.sub(_kv_debole, text)
    return _RE_SECRET_CORTO.sub(_corto, text)


def _scrub_birth_dates(text: str, report: RedactionReport) -> str:
    def _sub(m: re.Match) -> str:
        if not _RE_BIRTH_CTX.search(_context_before(m.string, m.start(), 40)):
            return m.group(0)
        return report.segnaposto("dates", "{{DATE}}", m.group(0))

    return _RE_DATE.sub(_sub, text)


# ---------------------------------------------------------------------------
# Pacchetto «atti e pratiche» (spento di serie, vedi ATTI)
# ---------------------------------------------------------------------------

# Il riferimento catastale: foglio, particella, subalterno.
#
# **E' il candidato migliore per cominciare**, e la ragione e' la stessa per
# cui il codice fiscale accanto a un nome funziona: il contesto qui non e' un
# indizio, e' una dichiarazione. «Foglio 12 particella 345 sub 6» non capita
# per caso in nessun altro genere di frase.
#
# Per un notaio e' il dato **piu' sensibile** della riga: dice esattamente di
# quale immobile si parla, e da un riferimento catastale al proprietario si
# arriva in un pomeriggio. Per chiunque altro e' rumore, ed e' il motivo per
# cui sta in un pacchetto spento.
#
# Le tre parole devono stare **vicine**, sulla stessa riga o su due: in una
# tabella catastale le colonne sono «Fg. | Part. | Sub», e con una finestra
# larga si prenderebbero tre celle di righe diverse.
_CATASTO_FOGLIO = r"(?:f(?:oglio|g)?\.?)"
_CATASTO_PART = r"(?:part(?:icella|\.)?|mapp(?:ale|\.)?|p\.lla)"
_CATASTO_SUB = r"(?:sub(?:alterno|\.)?)"
_H_CAT = r"[^\S\r\n]"

_RE_CATASTO = re.compile(
    rf"(?<!\w)(?i:{_CATASTO_FOGLIO}){_H_CAT}*:?{_H_CAT}*\d{{1,4}}"
    rf"(?:{_H_CAT}*[,;\-–]?{_H_CAT}*(?:\r?\n{_H_CAT}*)?"
    rf"(?i:{_CATASTO_PART}){_H_CAT}*:?{_H_CAT}*\d{{1,5}}"
    rf"(?:{_H_CAT}*[,;\-–]?{_H_CAT}*(?:\r?\n{_H_CAT}*)?"
    rf"(?i:{_CATASTO_SUB}){_H_CAT}*:?{_H_CAT}*\d{{1,4}})?)"
)


def _scrub_catasto(text: str, report: RedactionReport) -> str:
    """Il riferimento catastale, **solo** con foglio e particella insieme.

    Il foglio da solo non basta e non deve bastare: «foglio 3» in una
    relazione e' la pagina tre. E' la coppia a essere una dichiarazione, e
    il subalterno e' facoltativo perche' non tutti gli immobili ne hanno.
    """
    def _sub(m: re.Match) -> str:
        return report.segnaposto("catasto", "{{CATASTO}}", m.group(0))

    return _RE_CATASTO.sub(_sub, text)


# Il numero di pratica: R.G., protocollo, repertorio, raccolta, cronologico.
#
# **Questa e' la regola che capovolge una scelta gia' presa**, e va letta
# sapendolo. Altrove nel motore «protocollo» e «repertorio» servono a dire di
# *non* redigere: sono cio' che impedisce a un numero di dieci cifre di essere
# letto come un telefono. Qui l'etichetta fa il lavoro opposto, e per un
# pubblico opposto -- in un atto il numero di ruolo generale identifica le
# parti quanto il loro nome, perche' da quel numero si arriva al fascicolo.
#
# Per un'azienda toglierlo rende il documento inservibile senza proteggere
# nessuno: e' precisamente il motivo per cui il pacchetto e' spento di serie.
#
# L'etichetta e' **obbligatoria** e non e' un rafforzativo: un numero con un
# anno accanto e' la forma piu' comune che esista in un documento, e senza la
# parola davanti si redigerebbero le citazioni di legge.
_PRATICA_ETICHETTA = (
    r"(?:r\.[^\S\r\n]?g\.?(?:[^\S\r\n]?n\.[^\S\r\n]?r\.?)?"
    r"|ruolo[^\S\r\n]+generale"
    r"|prot(?:\.|ocollo)"
    r"|rep(?:\.|ertorio)"
    # **`Rac.` con una c sola**: e' l'abbreviazione che gli atti notarili usano
    # davvero accanto al repertorio — «Rep. 55231 Rac. 7814». Chiedendo le due
    # c si perdevano 6 728 numeri di raccolta su un corpus di atti, ed e' la
    # forma piu' frequente delle due.
    r"|racc?(?:\.|olta)"
    r"|cron(?:\.|ologico))"
)

# Il ruolo generale scritto **senza punti**, che negli atti e' comunissimo:
# «fattura RG 87220/2020», «repertorio RG 99654/2021».
#
# Sta separato dalle altre etichette, e non per ordine: `RG` nudo e' anche la
# **sigla della provincia di Ragusa**, che il riconoscitore degli indirizzi ha
# imparato a tenersi. Ammetterlo alle stesse condizioni delle altre vorrebbe
# dire mangiarsi un CAP dopo il nome di un comune — «Ragusa RG 97100».
#
# La discriminante e' l'anno: un numero di ruolo si scrive `12345/2020`, una
# sigla di provincia non e' mai seguita da numero-barra-numero. Quindi il
# ruolo nudo si accetta **solo nella forma con la barra**, e i 6 919 casi del
# corpus di atti hanno tutti quella forma.
_PRATICA_RG_NUDO = r"(?:r[^\S\r\n]?g(?:[^\S\r\n]?n[^\S\r\n]?r)?)"

# **La cifra sola non basta, la coppia con l'anno si'.** «Protocollo n. 5» in
# un trattato e' il quinto protocollo, non un numero di pratica; «prot. 7/2024»
# lo e'. Chiedere due cifre -- oppure una barra con l'anno -- e' l'unica parte
# di questa regola che sappia dire di no, e c'e' un test che la muove in
# peggio per controllare in che verso si sposta il conto.
#
# La barra prende **tutte** le cifre dei due lati e non solo un anno di
# quattro: «Protocollo 2024/000123» e' anno-barra-progressivo, ed e' scritto
# in questo verso almeno quanto nell'altro. Con il numeratore limitato a
# quattro cifre il pattern ripiegava sulla seconda alternativa e sostituiva
# **meta' numero**, lasciando «{{PRATICA}}/000123» nel testo -- che e' peggio
# di non sostituire, perche' sembra fatto.
_PRATICA_NUM = r"(?:\d{1,8}[^\S\r\n]*/[^\S\r\n]*\d{1,8}|\d{2,8})"

#: Solo la forma numero-barra-numero: e' quella che distingue un ruolo
#: generale da una sigla di provincia.
_PRATICA_NUM_BARRA = r"\d{1,8}[^\S\r\n]*/[^\S\r\n]*\d{1,8}"

_RE_PRATICA = re.compile(
    rf"(?<!\w)(?i:{_PRATICA_ETICHETTA})[^\S\r\n]*:?[^\S\r\n]*"
    rf"(?:[nN][.°]?[^\S\r\n]*)?(?P<val>{_PRATICA_NUM})(?!\d)"
)

_RE_PRATICA_RG_NUDO = re.compile(
    rf"(?<!\w)(?i:{_PRATICA_RG_NUDO})[^\S\r\n]*:?[^\S\r\n]*"
    rf"(?:[nN][.°]?[^\S\r\n]*)?(?P<val>{_PRATICA_NUM_BARRA})(?!\d)"
)

# La forma con l'etichetta **dopo**, che negli atti e' quella canonica:
# «n. 1234/2023 R.G.». Solo per il ruolo generale: «12345 prot.» non si scrive.
_RE_PRATICA_POST = re.compile(
    r"(?<!\w)(?:[nN][.°][^\S\r\n]*)?(?P<val>" + _PRATICA_NUM + r")"
    r"[^\S\r\n]*(?i:r\.[^\S\r\n]?g\.?(?:[^\S\r\n]?n\.[^\S\r\n]?r\.?)?)(?!\w)"
)


def _scrub_pratica(text: str, report: RedactionReport) -> str:
    """Numeri di pratica, **tenendo l'etichetta nel testo**.

    Sparisce il numero, resta «Prot. n.». E' la stessa scelta fatta per gli
    appellativi e per le parole d'ente: la parola dice di che genere di dato
    si trattava, e chi rilegge capisce la frase senza poter risalire a niente.
    Toglierla insieme al numero renderebbe il documento illeggibile in cambio
    di nessuna protezione in piu'.

    Cosa non trova, dichiarato: il numero in una tabella la cui intestazione
    di colonna sta dieci righe sopra. Li' l'etichetta non c'e', e senza
    etichetta questa regola non deve scattare.
    """
    def _sub(m: re.Match) -> str:
        prima = m.string[m.start():m.start("val")]
        return prima + report.segnaposto("pratica", "{{PRATICA}}", m.group("val"))

    def _sub_post(m: re.Match) -> str:
        # Anche qui **tutto cio' che non e' il numero resta**, compreso il
        # «n.» davanti: e' la stessa regola di sopra, e dimenticarla qui
        # faceva sparire l'abbreviazione insieme alla cifra.
        prima = m.string[m.start():m.start("val")]
        dopo = m.string[m.end("val"):m.end()]
        return prima + report.segnaposto("pratica", "{{PRATICA}}", m.group("val")) + dopo

    # L'ordine conta: il ruolo nudo per ultimo, su cio' che e' rimasto. Le
    # etichette con i punti sono piu' specifiche e vanno servite prima.
    fuori = _RE_PRATICA_POST.sub(_sub_post, _RE_PRATICA.sub(_sub, text))
    return _RE_PRATICA_RG_NUDO.sub(_sub, fuori)


# La targa italiana. **Il pattern propone, l'alfabeto decide**: sulle targhe
# non esistono I, O, Q, U -- si confonderebbero con 1 e 0 -- e quelle quattro
# lettere mancanti sono l'unico controllo aritmetico disponibile qui. Non e'
# molto, ma e' vero: rifiuta circa una sigla inventata su due.
_TARGA_L = "[ABCDEFGHJKLMNPRSTVWXYZ]"

# Tutto maiuscolo **oppure** tutto minuscolo, mai misto — e la regola non e'
# estetica, e' misurata.
#
# Il maiuscolo secco perdeva 135 targhe su un corpus di atti, tutte scritte
# `vm916jx`: nei documenti trascritti a mano il minuscolo c'e' e non e' raro.
# Ammettere il minuscolo senza condizioni pero' costava un falso positivo su 47
# documenti pubblici — `ge 021 CV`, un frammento di OCR dentro una frase sulle
# clementine. Quel frammento e' **misto**, le targhe vere no: chiedere che le
# quattro lettere abbiano tutte lo stesso caso recupera le 135 e rifiuta lui.
_TARGA_L_MIN = "[abcdefghjklmnprstvwxyz]"
_RE_TARGA = re.compile(
    rf"(?<![\w-])(?:{_TARGA_L}{{2}}[ .-]?\d{{3}}[ .-]?{_TARGA_L}{{2}}"
    rf"|{_TARGA_L_MIN}{{2}}[ .-]?\d{{3}}[ .-]?{_TARGA_L_MIN}{{2}})(?![\w-])"
)

# La targa di motocicli e ciclomotori -- due lettere e **cinque** cifre -- ha
# una forma molto piu' comune: «MB 12345» puo' essere qualunque codice. Qui
# la parola davanti e' obbligatoria, ed e' il prezzo giusto per una forma che
# da sola non dice niente.
#
# «targato», non solo «targa»: e' la forma piu' comune in un verbale — «il
# veicolo targato AB 12345». Chiedendo la parola esatta si perdevano 67 targhe
# su un corpus di atti, tutte scritte cosi'.
_RE_TARGA_CTX = re.compile(
    r"(?i:targ(?:a|he|at[oaie]))[^\S\r\n]*:?[^\S\r\n]*(?:[nN][.°]?[^\S\r\n]*)?"
    rf"(?P<val>{_TARGA_L}{{2}}[ .-]?\d{{5}})(?![\w-])"
)

# La targa **del vecchio formato provinciale**: due lettere di provincia e
# fino a sei cifre — `MI 123456`, `RM 987654`. Si trova negli atti di
# compravendita di veicoli e nelle perizie su mezzi storici.
#
# Tre condizioni insieme, e servono tutte e tre:
#
#  1. **il contesto e' obbligatorio** (`targa`, `veicolo`, `autovettura`,
#     `autocarro`, `motoveicolo`, `ciclomotore`, `immatricolat*`,
#     `telaio`), perche' `MI 123456` da solo e' indistinguibile da un numero
#     di protocollo, da un codice articolo o da un importo in centesimi;
#  2. **le due lettere devono essere una sigla di provincia vera**
#     (`_SIGLE_PROVINCIA`, che serviva gia' agli indirizzi): `XY 123456` non
#     e' mai stata una targa, e senza questo vincolo la regola prenderebbe
#     qualunque coppia di lettere seguita da cifre;
#  3. **le cifre sono da 4 a 6**: sotto le quattro si entra nel territorio
#     dei numeri civici e dei codici brevi.
#
# Il formato e' fuori uso dal 1994, quindi qui non si perde niente di vivo:
# si guadagna sui documenti che parlano del passato, che sono esattamente
# quelli in cui il vecchio formato compare.
_RE_TARGA_STORICA_CTX = re.compile(
    r"(?i:targ(?:a|he|at[oaie])|veicolo|autoveicolo|autovettura|autocarro"
    r"|motoveicolo|ciclomotore|rimorchio|immatricolat[oaie]|telaio)"
    r"[^\S\r\n]*:?[^\S\r\n]*(?:[nN][.°]?[^\S\r\n]*)?"
    r"(?P<val>[A-Z]{2}[ .-]?\d{4,6})(?![\w-])"
)


def _scrub_targhe(text: str, report: RedactionReport) -> str:
    """Targhe di veicoli.

    Una targa e' un identificatore diretto -- dal PRA si arriva
    all'intestatario in un accesso -- ma sta nel pacchetto spento insieme al
    resto: in un verbale serve toglierla, in un ordine di acquisto di flotta
    aziendale toglierla cancella l'oggetto del documento.
    """
    def _sub(m: re.Match) -> str:
        return report.segnaposto("targa", "{{TARGA}}", m.group(0))

    def _sub_ctx(m: re.Match) -> str:
        prima = m.string[m.start():m.start("val")]
        return prima + report.segnaposto("targa", "{{TARGA}}", m.group("val"))

    def _sub_storica(m: re.Match) -> str:
        # La sigla dev'essere una provincia vera: `XY 123456` non e' mai
        # stata una targa. Se non lo e', il testo torna intatto — non un
        # sospetto, perche' senza la sigla giusta non c'e' nemmeno il
        # sospetto.
        val = m.group("val")
        sigla = val[:2].upper()
        if sigla not in _SIGLE_PROVINCIA:
            return m.group(0)
        prima = m.string[m.start():m.start("val")]
        return prima + report.segnaposto("targa", "{{TARGA}}", val)

    out = _RE_TARGA_CTX.sub(_sub_ctx, text)
    out = _RE_TARGA_STORICA_CTX.sub(_sub_storica, out)
    return _RE_TARGA.sub(_sub, out)


# ---------------------------------------------------------------------------
# Eta' e sesso: si trovano, si dicono, **non si tolgono mai**
# ---------------------------------------------------------------------------
#
# Sono quasi-identificatori, ed e' una categoria diversa da tutto il resto di
# questo file. Un IBAN identifica una persona da solo; «45 anni» no -- ma «45
# anni» insieme a un comune piccolo e a una professione la identifica benissimo,
# ed e' esattamente cosi' che si de-anonimizza un archivio.
#
# **Perche' non c'e' nessun percorso che li sostituisca.** Chi chiede a un
# modello di ragionare su una cartella clinica, su una statistica del personale
# o su una perizia sta chiedendo proprio di quei due dati: toglierli non
# protegge nessuno di piu' e rende il documento inservibile per l'unico uso per
# cui era stato preparato. Lasciarli in silenzio, pero', vuol dire che chi
# rilegge non sa che ci sono.
#
# Quindi la terza via, che qui e' la sola giusta: **compaiono nel rapporto**.
# «Ho lasciato in chiaro 3 eta' e 1 sesso, apposta» e' un'informazione che un
# DPO puo' usare per decidere; il silenzio no.
#
# E niente e' perduto: chi vuole toglierli davvero ha gia' l'elenco «nascondi
# sempre», che li toglie senza che serva un'altra leva.

# Solo le forme in cui il contesto e' una **dichiarazione**, non un indizio.
# «45 anni» nudo e' quasi sempre una durata -- «dopo 45 anni di servizio»,
# «un contratto di 45 anni» -- e prenderlo vorrebbe dire riempire di
# segnalazioni ogni relazione aziendale. Dichiarato: l'eta' scritta cosi' non
# la vediamo, ed e' la scelta giusta finche' l'unico esito e' una riga di
# rapporto.
# I gruppi `(?i:…)` coprono **tutto** il pezzo che deve ignorare le
# maiuscole. Lasciare `et[àa]` o `[MF]` fuori (come fino alla 1.24.0)
# produceva quattro silenzi: `45 anni d'ETÀ`, `sesso: f`, `d' anni 78`,
# `Eta': 45`. Nessun dato usciva — questi riconoscitori non sostituiscono
# — ma il rapporto contava meno di quello che c'era.
_RE_ETA = re.compile(
    r"(?<!\w)(?:"
    r"(?i:d'[^\S\r\n]*|di[^\S\r\n]+)anni[^\S\r\n]+(?P<a>\d{1,3})"
    r"|(?P<b>\d{1,3})[^\S\r\n]+anni[^\S\r\n]+(?i:(?:d'[^\S\r\n]*|di[^\S\r\n]+)et[àa])"
    r"|(?i:et[àa]'?)[^\S\r\n]*:?[^\S\r\n]+(?P<c>\d{1,3})"
    r"|(?P<d>\d{1,3})enne"
    r")(?!\d)"
)

# Il campo etichettato dei moduli e dei record. La lettera sola («M», «F») non
# si guarda senza l'etichetta davanti: sarebbe una lettera qualsiasi.
_RE_SESSO = re.compile(
    r"(?<!\w)(?i:sesso|genere)[^\S\r\n]*:?[^\S\r\n]*"
    r"(?P<v>(?i:maschile|femminile|maschio|femmina|[MF])(?![\w]))"
)


def _scrub_eta_sesso(text: str, report: RedactionReport) -> str:
    """Li trova e li **restituisce identici**. Non e' un segnaposto mancato.

    Il testo esce dalla funzione com'era entrato: l'unico effetto e' una riga
    nel rapporto. Se un domani qualcuno aggiungesse qui una sostituzione,
    romperebbe la ragione per cui questi due riconoscitori esistono — e c'e'
    un test che tiene fermo proprio questo.
    """
    for m in _RE_ETA.finditer(text):
        valore = next(g for g in m.groups() if g is not None)
        eta = int(valore)
        # Oltre i 120 non e' un'eta': e' un anniversario, una durata, o un
        # numero che ha trovato la parola sbagliata accanto.
        if eta <= 120:
            report.rilevata("eta", m.group(0))
    for m in _RE_SESSO.finditer(text):
        report.rilevata("genere", m.group(0))
    return text


def _scrub_documenti_id(text: str, report: RedactionReport) -> str:
    """Numeri di carta d'identita', patente e passaporto.

    Il contesto e' **obbligatorio**, non un rafforzativo. Senza cifra di
    controllo queste forme sono indistinguibili da un numero di protocollo, e
    sostituire a vista vorrebbe dire cancellare mezza pratica amministrativa.

    Cosa non trova, dichiarato: il numero scritto in una tabella dove
    l'intestazione di colonna sta dieci righe sopra. In quel caso diventa un
    sospetto, che e' l'esito giusto — il documento resta intero e chi rilegge
    sa dove guardare.
    """
    def _sub(m: re.Match) -> str:
        # Finestra larga, e non e' generosita': su una carta d'identita' o
        # una patente il tipo di documento e' il TITOLO, sei o sette righe
        # sopra il numero. Con 60 caratteri il caso piu' comune -- la
        # scansione della tessera -- non veniva mai riconosciuto.
        intorno = m.string[max(0, m.start() - 300) : m.end() + 120]
        if not _RE_DOC_ID_CTX.search(intorno):
            report.suspect(
                "documento",
                m.group(0),
                "ha la forma di un numero di documento d'identita', ma "
                "intorno non c'e' scritto di che documento si tratta: "
                "potrebbe essere un protocollo o un codice pratica",
            )
            return m.group(0)
        return report.segnaposto("documenti", "{{DOC_ID}}", m.group(0))

    return _RE_DOC_ID.sub(_sub, text)


def _scrub_addresses(text: str, report: RedactionReport) -> str:
    def _sub(m: re.Match) -> str:
        corpo = m.group("body")
        # Le iniziali puntate non sono la parola che decide: in «Via A.
        # Volta» la parola da confrontare con l'elenco e' «Volta».
        parole = [p for p in corpo.split() if not re.fullmatch(r"[A-Za-zÀ-ÿ]\.", p)]
        first = (parole[0] if parole else corpo.split()[0]).lower().strip(".,'’")
        if first in _ADDRESS_STOPWORDS:
            return m.group(0)
        # Tutto maiuscolo: serve anche il numero civico.
        #
        # Nel testo a maiuscole e minuscole l'iniziale maiuscola distingue
        # gia' il nome proprio dal resto. In un testo tutto maiuscolo quel
        # segnale non c'e' piu', e le parole-chiave deboli aprono decine di
        # toponimi che indirizzi non sono: BORGO SAN LORENZO, BORGO
        # VALSUGANA, STRADA DEL VINO sono comuni e itinerari, non recapiti.
        # Misurato: 83 sostituzioni sbagliate su documenti dove l'atteso e'
        # zero, quasi tutte di questa forma.
        #
        # Il civico e' il segnale che resta: «VIA GARIBALDI 14» e «VIA
        # ARENULA 70» ce l'hanno, un nome di comune in un elenco no. Chi
        # scrive un indirizzo per farci arrivare qualcuno scrive il numero.
        if not re.search(r"[a-zà-öø-ÿ]", corpo) and not m.group("civ"):
            return m.group(0)

        # La sigla di provincia: lo schema l'ha proposta, qui si decide.
        #
        # Se non e' una provincia vera **torna al testo**, invece di far
        # fallire tutta la corrispondenza: l'indirizzo resta riconosciuto e
        # le due lettere restano dov'erano. Su «Via Roma 12, 20121 Milano IL
        # GIORNO 5» si redige l'indirizzo e «IL GIORNO 5» non si tocca.
        preso = m.group(0)
        sigla = m.group("prov")
        if sigla and sigla not in _SIGLE_PROVINCIA:
            # Solo la forma senza parentesi puo' pescare una parola: `(XX)`
            # sta fra parentesi e non e' una parola della frase.
            preso = preso[: m.start("prov") - m.start(0)].rstrip()
            coda = m.group(0)[len(preso):]
            return report.segnaposto("addresses", "{{ADDRESS}}", preso) + coda
        if m.group("prov_par") and m.group("prov_par") not in _SIGLE_PROVINCIA:
            preso = preso[: m.start("prov_par") - m.start(0)].rstrip().rstrip("(").rstrip()
            coda = m.group(0)[len(preso):]
            return report.segnaposto("addresses", "{{ADDRESS}}", preso) + coda

        return report.segnaposto("addresses", "{{ADDRESS}}", preso)

    return _RE_ADDRESS.sub(_sub, text)


# Le parole che davanti a un nome dicono «edificio», non «persona». Sta qui
# fuori perche' la usano due guardie diverse: quella sul nome isolato
# (`_dopo_una_intitolazione`) e quella sulla coppia
# (`_intitolazione_adiacente`).
def _dice_edificio(parola: str) -> bool:
    return (
        parola in _PRIMA_NON_E_PERSONA
        or parola in _ENTITY_WORDS
        or re.fullmatch(_ADDRESS_KW, parola) is not None
    )


# Articoli e preposizioni: fra la parola d'edificio e il nome ci stanno quasi
# sempre, e senza saltarle nessuna delle due guardie scatterebbe.
_ARTICOLI_E_PREPOSIZIONI = frozenset(
    {
        "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "l", "dell",
        "all", "nell", "sull", "dall", "del", "dello", "della", "dei", "degli",
        "delle", "al", "allo", "alla", "ai", "agli", "alle", "nel", "nello",
        "nella", "nei", "negli", "nelle", "dal", "dallo", "dalla", "dai",
        "dagli", "dalle", "sul", "sullo", "sulla", "sui", "sugli", "sulle",
        "di", "a", "da", "in", "su", "con", "per", "tra", "fra", "e",
    }
)


# Aggettivi che qualificano l'edificio e non decidono niente: fra la parola
# che dice «edificio» e il nome ci si infilano, e senza saltarli la risalita
# si ferma su di loro. «biblioteca nazionale Vittorio Emanuele III», «scuola
# primaria Cristoforo Colombo», «centro sportivo Giacinto Facchetti»: tre
# intitolazioni che il banco vedeva passare per una parola in mezzo.
#
# Sono aggettivi, quindi **non possono essere loro** la parola che decide, e
# saltarli fa arrivare la risalita una parola piu' indietro -- mai piu' di
# quanto la risalita gia' facesse sulle maiuscole. Il prezzo: «il
# responsabile tecnico Mario Rossi» non cambia (`responsabile` edificio non
# e'), «l'ufficio tecnico Mario Rossi» si comporta ora come «Ufficio Mario
# Rossi», che era gia' schermato dalla 1.20.
_QUALIFICATORI = frozenset(
    {
        "nazionale", "statale", "comunale", "provinciale", "regionale",
        "civico", "civica", "municipale", "cittadino", "cittadina",
        "primaria", "primario", "secondaria", "secondario", "elementare",
        "media", "medie", "superiore", "superiori", "inferiore",
        "comprensivo", "classico", "scientifico", "linguistico", "artistico",
        "tecnico", "tecnica", "professionale", "magistrale",
        "sportivo", "sportiva", "polivalente", "olimpico", "olimpica",
        "militare", "generale", "centrale", "maggiore", "vecchio", "vecchia",
        "nuovo", "nuova", "storico", "storica", "antico", "antica",
        "grande", "piccolo", "piccola", "santissimo", "santissima",
    }
)


# Le **sigle** che dicono «edificio»: `IC`, `I.C.S.`, `SMS`, `SC.MEDIA`.
#
# Stanno separate dalle parole per una ragione sola, e non e' l'estetica:
# **contano solo scritte tutte maiuscole**. `sms` minuscolo e' un messaggio —
# «ho mandato un sms a Mario Rossi» — e metterlo fra le parole d'edificio
# lascerebbe in chiaro quel Mario Rossi. `SMS` maiuscolo, davanti a un nome,
# e' una scuola media.
#
# **Le ha dettate un documento vero**, non l'immaginazione: su un elenco
# pubblico di posti di sostegno — nessun dato personale dentro — il motore
# faceva 604 sostituzioni, e ventuno nomi distinti erano tutti nomi di
# **scuole**: «IC MAZZARRONE», «I.C.S. Giovanni XXIII», «SC.MEDIA Fermi».
# `istituto` stava gia' fra le parole d'ente, la sua sigla no.
#
# I punti si tolgono prima del confronto, quindi `I.C.S.` e `ICS` sono la
# stessa voce. Restano fuori le sigle di **due lettere puntate** che sono
# quasi sempre le iniziali di una persona — `S.G.`, `A.R.` — perche' li'
# schermare vorrebbe dire lasciare in chiaro un nome vero.
_SIGLE_DI_ENTE = frozenset(
    {
        "ic", "ics", "icd", "iis", "iiss", "isis", "itis", "itc", "itet",
        "ipsia", "ipseoa", "ipsseoa", "its", "cpia", "sms", "smim",
        "scmedia", "scelementare", "scinfanzia",
        "asl", "asp", "ausl", "usl", "irccs", "ipab", "iacp", "acer",
    }
)


def _sigla_di_ente(token: str) -> bool:
    """Vale **solo** se il token e' scritto tutto maiuscolo nel testo."""
    nudo = token.strip("'’-.,;:()[]")
    if len(nudo) < 2 or not nudo.replace(".", "").isupper():
        return False
    return nudo.replace(".", "").lower() in _SIGLE_DI_ENTE


# La sigla attaccata al nome: `IC `, `I.C. `, `SC.MEDIA `. Si legge a parte
# perche' il punto ferma la risalita normale — ed e' giusto che la fermi:
# e' cio' che tiene protetto «Residenza: Mario Rossi».
_RE_SIGLA_PRIMA = re.compile(r"(?<![\w.])([A-Z][A-Z.]{1,11})[ \t]*$")


# Quanto indietro si guarda. Serve solo la coda attaccata al nome: oltre
# «l'ospedale civile Giovanni Paolo» non c'e' piu' niente da leggere, e senza
# un limite un documento tutto maiuscolo farebbe risalire pagine intere.
_CODA_MAX = 120


def _intitolazione_adiacente(testo: str, posizione: int) -> bool:
    """P9.4 — la **coppia** che e' un'intitolazione: «stadio Giuseppe Meazza».

    Il riconoscitore delle coppie non sa che quello e' uno stadio: due parole
    maiuscole di fila, tutte e due negli elenchi, e la sequenza sparisce
    portandosi via il soggetto della frase. Lo scudo che gia' c'era --
    `_is_entity_word` dentro la sequenza -- vede solo la parola d'ente
    **scritta maiuscola e dentro la sequenza**: «Ospedale Giovanni Paolo II»
    era schermato, «l'ospedale Giovanni Paolo II» no. In prosa italiana la
    forma normale e' la seconda.

    **Perche' non e' `_dopo_una_intitolazione` (quella dei nomi soli).**
    Quella guardia salta la punteggiatura, e va bene dov'e': un nome solo e'
    l'appiglio piu' debole del motore. Sulle coppie no. «Residenza: Mario
    Rossi» e «Zona 3 - referente Mario Rossi» sono un'etichetta di modulo
    seguita da una persona vera, e `residenza` e `zona` stanno nell'elenco:
    con la guardia larga quelle due persone smetterebbero di essere protette.
    Qui quindi si legge **solo la coda di lettere e spazi** che tocca il nome,
    e qualunque segno -- due punti, virgola, trattino, cifra -- ferma la
    risalita.

    Il prezzo, dichiarato: «presso casa Mario Rossi» non viene piu'
    sostituito. `casa` e' in elenco, l'adiacenza e' pulita, e nessuna regola
    puo' distinguere quella forma da «casa Giuseppe Verdi». E' la stessa
    rinuncia gia' accettata per «Fondazione Mario Rossi», con in piu' il
    fatto che qui la parola e' minuscola, cioe' un nome comune usato per
    quello che e'.
    """
    # Prima la sigla: `IC Mazzarrone`, `I.C.S. Giovanni XXIII`. Il punto
    # ferma la risalita normale, quindi va letta a parte.
    sigla = _RE_SIGLA_PRIMA.search(testo[max(0, posizione - 24):posizione])
    if sigla is not None and _sigla_di_ente(sigla.group(1)):
        return True

    # **A mano e all'indietro, non con una espressione regolare.** La prima
    # stesura tagliava `testo[:posizione]` e ci cercava `(?:\w+\s*)+$`: su un
    # documento lungo quel taglio e' una copia a ogni sequenza, e l'ancora
    # finale fa ripartire il motore da ogni posizione. Sul corpus pubblico il
    # banco non e' arrivato in fondo in dieci minuti. Qui si guardano al
    # massimo `_CODA_MAX` caratteri, una volta.
    i = posizione
    inizio = max(0, posizione - _CODA_MAX)
    while i > inizio and (testo[i - 1].isalpha()
                          or testo[i - 1] in " \t'’"):
        i -= 1
    visto_articolo = False
    for parola in reversed(re.findall(r"[^\W\d_]+", testo[i:posizione])):
        if _dice_edificio(parola.lower()):
            return True
        # La sigla **senza punti**, dentro la coda: «IC MADRE Teresa di
        # Calcutta». Con i punti la coda si spezza e la trova il controllo
        # in fondo; senza, `IC` e' una parola maiuscola come le altre.
        #
        # **Ma solo se fra la sigla e il nome ci sono altre maiuscole, non
        # un articolo.** Senza questa condizione «il referente ASL e Mario
        # Rossi» smetteva di essere protetto: `e` e' una congiunzione, la
        # risalita la salta come salta gli articoli, e trovava `ASL` una
        # parola piu' in la'. Una sigla attaccata a un nome proprio nomina
        # un ente; una sigla separata da una congiunzione e' un'altra cosa
        # nella frase.
        if _sigla_di_ente(parola) and not visto_articolo:
            return True
        # Si continua a risalire **solo** attraverso maiuscole e articoli. Le
        # maiuscole fanno parte della stessa intitolazione: in «il ponte
        # Vittorio Emanuele II» il tratto che sta per essere sostituito
        # comincia a «Emanuele», e la parola che decide -- `ponte` -- sta
        # dietro a «Vittorio». Alla prima parola minuscola che edificio non
        # e' ci si ferma, ed e' cio' che tiene protetto «il premio e' stato
        # consegnato a Mario Rossi»: `consegnato` chiude la risalita prima
        # che `premio` si possa vedere.
        if parola.lower() in _ARTICOLI_E_PREPOSIZIONI:
            visto_articolo = True
            continue
        if parola[:1].isupper() or parola.lower() in _QUALIFICATORI:
            continue
        return False
    # La coda e' finita senza decidere: tutte maiuscole, articoli o
    # aggettivi. Allora la parola che decide puo' essere la **sigla appena
    # prima della coda** — «IC MADRE Teresa di Calcutta», «I.C. GIOVANNI
    # XXIII»: fra la sigla e il nome c'e' un'altra parola maiuscola, e il
    # punto della sigla ferma la risalita normale.
    sigla = _RE_SIGLA_PRIMA.search(testo[max(0, i - 24):i])
    return sigla is not None and _sigla_di_ente(sigla.group(1))


def _dopo_una_intitolazione(testo: str, posizione: int) -> bool:
    """Davanti al nome c'e' una parola che dice «edificio», non «persona».

    Si guarda **l'ultima parola prima**, saltando articoli e preposizioni
    articolate: nei documenti si scrive «l'ospedale Umberto», «allo stadio
    Giuseppe», «della villa Ada», e con la sola parola immediatamente
    precedente la guardia non scatterebbe quasi mai.
    """
    # L'apostrofo **separa**, non fa parte della parola: nei documenti si
    # scrive «all'ospedale», «l'istituto», «dell'aeroporto», e tenendolo
    # dentro il token la guardia leggeva «all'ospedale» — che in nessun
    # elenco c'e' — e lasciava passare tre intitolazioni su cinque. Trovato
    # dal banco, non a mente.
    # La sigla vale anche qui: dopo che il riconoscitore delle coppie ha
    # schermato «IC Giovanni Verga», la parola sola («Giovanni») arriva a
    # questa regola, e senza la sigla davanti se la riprenderebbe — mezzo
    # nome di scuola sostituito, che e' il difetto di partenza travestito.
    sigla = _RE_SIGLA_PRIMA.search(testo[max(0, posizione - 24):posizione])
    if sigla is not None and _sigla_di_ente(sigla.group(1)):
        return True

    prima = testo[:posizione]
    parole = re.findall(r"[^\W\d_]+", prima.lower())
    salta = _ARTICOLI_E_PREPOSIZIONI
    dice_edificio = _dice_edificio

    # **Si risale tutta la sequenza di maiuscole, non solo la parola prima.**
    #
    # «Liceo Classico Giuseppe Parini», «Biblioteca Nazionale Vittorio
    # Emanuele III», «Istituto Comprensivo Alessandro Manzoni»: fra la parola
    # d'ente e il nome ce n'e' un'altra, e guardando solo quella la guardia
    # non scattava. Il riconoscitore delle coppie quelle sequenze le scherma
    # gia' — una parola d'ente scherma **l'intera** sequenza — e questa regola
    # gira dopo, sul testo che quella ha lasciato intatto: senza risalire, si
    # rimangiava lo scudo di chi era passato prima. Tre banchi di
    # `test_enti_non_sono_persone.py` l'hanno detto subito.
    #
    # Si risale solo finche' le parole sono **maiuscole**: la sequenza finisce
    # dove finisce il nome proprio, e «all'ospedale ho incontrato Pietro» non
    # viene toccato dalla parola «ospedale», che sta cinque parole indietro e
    # fuori dalla sequenza.
    #
    # **E la risalita si ferma dove si spezza l'adiacenza** (P9.4). Fra una
    # parola maiuscola e la successiva ci devono stare solo spazi: un a capo,
    # una cifra, un segno di punteggiatura vogliono dire che quella maiuscola
    # e' un'altra frase. Senza questa condizione, su una Gazzetta Ufficiale la
    # risalita partiva da «MARGHERITA CARDONA ALBINI», scavalcava due codici
    # pratica -- che contengono le lettere maiuscole di «24A03016» -- e
    # arrivava a «La direttrice d'ufficio:» due righe sopra: la redattrice
    # della Gazzetta smetteva di essere protetta. L'ha trovato la misura sul
    # corpus pubblico, non un banco fatto in casa.
    maiuscole = list(re.finditer(r"[^\W\d_]+", prima))
    i = len(maiuscole) - 1
    fine = posizione
    while i >= 0 and maiuscole[i].group(0)[:1].isupper():
        if prima[maiuscole[i].end():fine].strip(" \t'’-"):
            break
        if dice_edificio(maiuscole[i].group(0).lower()):
            return True
        # La sigla dentro la sequenza di maiuscole: «IC MADRE Teresa».
        if _sigla_di_ente(maiuscole[i].group(0)):
            return True
        fine = maiuscole[i].start()
        i -= 1

    # `parole[: i + 1]`, non tutte: si riprende **da dove la risalita sulle
    # maiuscole si e' fermata**. Ripartire dal fondo voleva dire rileggere le
    # maiuscole appena scartate e decidere su quelle: in «il ponte Vittorio
    # Emanuele II» la guardia si fermava su `vittorio` -- che edificio non e'
    # -- e non arrivava mai a `ponte`, due parole piu' indietro.
    for parola in reversed(parole[: i + 1]):
        if parola in salta or parola in _QUALIFICATORI:
            continue
        return dice_edificio(parola)
    return False


def _dentro_una_sequenza_di_ente(testo: str, dopo: int) -> bool:
    """La parola d'ente sta **dopo** il nome: «Marco Chiesa», «Anna Villa».

    Il riconoscitore delle coppie scherma l'intera sequenza quando ci trova
    una parola d'ente, e lo fa in tutte e due le direzioni. Questa regola
    gira dopo, su ciò che quello ha lasciato intatto: guardando solo
    all'indietro toglieva il **nome** e lasciava il resto — «come indicato da
    {{NAME_1}} Chiesa» — che è il modo peggiore di sbagliare, perché il
    documento sembra trattato.

    Trovato da `tests/test_forme_difficili.py`, che quel caso lo teneva
    congelato da versioni: senza, sarebbe passato per un miglioramento.
    """
    resto = testo[dopo:]
    for m in re.finditer(r"[^\W\d_]+|\S", resto):
        parola = m.group(0)
        if not parola[:1].isalpha() or not parola[:1].isupper():
            return False
        if parola.lower() in _ENTITY_WORDS or parola.lower() in _PRIMA_NON_E_PERSONA:
            return True
    return False


def _scrub_names(
    text: str,
    report: RedactionReport,
    prosa: bool | None = None,
    soli: bool = False,
) -> str:
    """Sostituisce i nomi di persona, dal segnale piu' forte al piu' debole.

    Aveva un parametro ``guess`` in piu', ritirato nella 1.13.0 insieme
    all'euristica che comandava: vedi il docstring del modulo.
    """

    # 1. Titolo professionale: "il geom. Nazzareno Sbrolli".
    def _title_sub(m: re.Match) -> str:
        name = m.group("name")
        tokens = name.split()
        while tokens and _is_common_in_context(tokens, len(tokens) - 1):
            if _cognome_appoggiato(tokens):
                break
            tokens.pop()
        if not tokens:
            return m.group(0)
        kept = " ".join(tokens)
        # La chiave e' `kept`, non `name`: quando la coda viene restituita
        # al testo, il nome sostituito e' solo la parte tenuta -- e due
        # occorrenze della stessa persona con code diverse devono comunque
        # ricevere lo stesso numero.
        segno = report.segnaposto("names", "{{NAME}}", kept)
        return m.group(0).replace(name, segno + name[len(kept):], 1)

    text = _RE_TITLE_NAME.sub(_title_sub, text)

    # 1-bis. Ruolo, due punti, cognome in maiuscolo: «Il Ministro: URSO».
    def _ruolo_sub(m: re.Match) -> str:
        name = m.group("name")
        tokens = name.split()
        if any(_is_common_word(t) or _is_entity_word(t) for t in tokens):
            return m.group(0)
        return m.group(0).replace(name, report.segnaposto("names", "{{NAME}}", name), 1)

    text = _RE_RUOLO_COGNOME.sub(_ruolo_sub, text)

    # 2. Nome accanto a un indirizzo di posta.
    def _email_name_sub(m: re.Match) -> str:
        name = m.group("name")
        tokens = name.split()
        dropped = []
        while tokens and _is_common_in_context(tokens, 0):
            # **La particella del cognome composto non si butta via.**
            #
            # `Di Salvo Andrea <a.disalvo@...>` usciva come `Di Salvo
            # {{NAME_1}}`: la potatura di testa toglie le parole comuni una
            # per una, e `di` e `salvo` sono tutte e due parole italiane
            # comunissime -- una preposizione e un avverbio. Restava
            # «Andrea», cioe' **mezzo nome**, che e' il modo peggiore di
            # sbagliare: il documento sembra trattato e il cognome che
            # identifica la persona e' ancora li'.
            #
            # Trovato su documenti veri (intestazioni di posta con decine di
            # destinatari nella forma «Cognome Nome»), non su un banco.
            #
            # La condizione e' la stessa del riconoscitore delle coppie e
            # non e' «la parola sembra un cognome»: la **forma incollata**
            # dev'essere un cognome degli elenchi, `di`+`salvo` = `disalvo`.
            # Senza quella prova, qualunque «salvo Mario <...>» diventerebbe
            # un cognome composto.
            part = tokens[0].lower().strip("'’-.,;:")
            if (
                len(tokens) >= 2
                and part in _PARTICELLE_COGNOME
                and _cognome_composto_noto(part, tokens[1].lower().strip("'’-.,;:"))
            ):
                break
            dropped.append(tokens.pop(0))
        if not tokens:
            return m.group(0)
        # Una sola parola maiuscola davanti a un indirizzo non basta a
        # farne un nome: davanti a un'email ci finisce di tutto, a
        # partire dai verbi. "Contatta mario@x.it" faceva sparire il
        # verbo. Serve una coppia — nome e cognome — oppure una parola
        # che negli elenchi ci sia davvero.
        if len(tokens) == 1:
            solo = tokens[0].lower().strip("'’-")
            if solo not in FIRST_NAMES and solo not in SURNAMES:
                return m.group(0)
        prefix = (" ".join(dropped) + " ") if dropped else ""
        tenuto = name[len(prefix):] if prefix else name
        segno = report.segnaposto("names", "{{NAME}}", tenuto)
        return m.group(0).replace(name, prefix + segno, 1)

    text = _RE_NAME_BEFORE_EMAIL.sub(_email_name_sub, text)
    text = _RE_NAME_AFTER_EMAIL.sub(_email_name_sub, text)

    # 2-ter. Il nome accanto a un codice fiscale valido.
    def _cf_name_sub(m: re.Match) -> str:
        name = m.group("name")
        tokens = name.split()
        # Lo scudo degli enti vale qui come altrove: `Comune di Roma CF
        # 01234...` non e' una persona, ed e' proprio la forma in cui un
        # codice fiscale compare accanto a una ragione sociale. Senza questo
        # la regola trasformerebbe ogni intestazione di ente in un nome.
        if any(_is_entity_word(t) for t in tokens):
            return m.group(0)
        # Una parola sola non basta nemmeno qui: davanti all'etichetta `CF`
        # ci finisce spesso l'ultima parola della frase precedente.
        # `{1,2}` nel pattern gia' pretende almeno due parole; questo
        # resta come guardia se il pattern cambiasse.
        if len(tokens) < 2:
            return m.group(0)
        segno = report.segnaposto("names", "{{NAME}}", name)
        return m.group(0).replace(name, segno, 1)

    text = _RE_NAME_BEFORE_CF.sub(_cf_name_sub, text)

    # 2-quater. Ruoli e campi: «il cliente X», «NOME= X».
    def _dichiarato_sub(m: re.Match) -> str:
        name = m.group("name")
        tokens = name.split()
        if any(_is_entity_word(t) for t in tokens):
            return m.group(0)
        # La sigla societaria si cerca in due posti, e servono tutti e due:
        # **dopo** il nome (`Beta Consulting S.p.A.`, dove la finestra si e'
        # fermata prima) e come **ultima parola presa** (`Delta Systems Ltd`,
        # dove la finestra se l'e' inghiottita). Guardando solo il testo che
        # segue, il secondo caso passava.
        if _RE_SIGLA_DOPO.match(text[m.end("name"):m.end("name") + 12]):
            return m.group(0)
        if _RE_SIGLA_DOPO.match(tokens[-1]):
            return m.group(0)
        segno = report.segnaposto("names", "{{NAME}}", name)
        return m.group(0).replace(name, segno, 1)

    text = _RE_RUOLO_NAME.sub(_dichiarato_sub, text)
    text = _RE_CAMPO_NOME.sub(_dichiarato_sub, text)

    # 2-bis. La firma. Una formula di chiusura dichiara che quello che
    # segue e' una persona, ed e' l'unico posto dove un cognome da solo --
    # «Cordiali saluti, Esposito» -- e' davvero un cognome e non la parola
    # «esposito». Senza questa regola, portare gli elenchi da «sostituisce»
    # a «segnala» avrebbe fatto sopravvivere le firme, che sono il punto in
    # cui il nome compare quasi sempre.
    def _firma_sub(m: re.Match) -> str:
        name = m.group("name")
        tokens = [t.lower().strip("'’-.,;:") for t in name.split()]
        if not tokens or all(_is_common_in_context(tokens, i) or _is_entity_word(t)
                             for i, t in enumerate(tokens)):
            return m.group(0)
        return m.group(0).replace(name, report.segnaposto("names", "{{NAME}}", name), 1)

    text = _RE_FIRMA_IT.sub(_firma_sub, text)

    # 2-quinquies. Il saluto che apre: «Ciao Pietro», «Gentile Anna».
    def _saluto_sub(m: re.Match) -> str:
        name = m.group("name")
        tokens = name.split()
        # La coda si pota come dopo un titolo: «Ciao Marco, ci vediamo»
        # arriva qui con «Marco» e le parole che seguono, e quelle non sono
        # del nome.
        while tokens and _is_common_in_context(tokens, len(tokens) - 1):
            if _cognome_appoggiato(tokens):
                break
            tokens.pop()
        if not tokens or any(_is_entity_word(t) for t in tokens):
            return m.group(0)
        # **La parola dev'essere negli elenchi.** Dopo un saluto ci finisce
        # di tutto — «Ciao Team», «Salve Ufficio», «Gentile Cliente» — e il
        # solo fatto di essere maiuscola non dice niente: qui la prova non e'
        # la forma della parola, e' che il saluto annunci qualcuno di cui
        # sappiamo il nome. Senza questa riga la regola prenderebbe la prima
        # parola maiuscola di ogni messaggio che comincia con «Ciao».
        primo = tokens[0].lower().strip("'’-.,;:")
        if primo not in FIRST_NAMES and primo not in SURNAMES:
            return m.group(0)
        kept = " ".join(tokens)
        segno = report.segnaposto("names", "{{NAME}}", kept)
        return m.group(0).replace(name, segno + name[len(kept):], 1)

    text = _RE_SALUTO_NOME.sub(_saluto_sub, text)

    # 3. Elenchi (nome proprio o cognome noto) e, se abilitata,
    #    4. euristica: due parole maiuscole che non sono parole italiane.
    def _pair_sub(m: re.Match) -> str:
        # Il pattern e' avido: "Studio Legale Trentini" arriva qui tutto
        # insieme. Una parola comune in mezzo non deve far cadere il
        # riconoscimento dell'intera sequenza, quindi si lavora sui tratti
        # continui di parole che comuni non sono, e il resto si ricompone
        # con gli spazi originali.
        parts = re.split(rf"({_SP})", m.group(0))
        tokens, seps = parts[0::2], parts[1::2]
        # Una parola d'ente da' un nome all'intera sequenza, e quel nome
        # non e' di una persona: «CHIESA EVANGELICA VALDESE» e' un ente,
        # non un cognome, e sui moduli dell'otto per mille compare a
        # decine. E' lo stesso presidio che nel pacchetto inglese impedisce
        # a «Green Lane Logistics» di diventare una persona -- li' lo fanno
        # i tipi di via, qui le parole di ente.
        if any(_is_entity_word(t) for t in tokens):
            return m.group(0)
        # P9.4 — la parola che dice «edificio» **in testa alla sequenza**.
        #
        # «San Giovanni Rotondo», «Sant'Antonio Abate», «San Giorgio
        # Costruzioni», «Torre Annunziata»: qui la parola che decide non sta
        # davanti alla sequenza, sta dentro, ed e' la prima. La guardia che
        # legge il contesto precedente non la vede per costruzione, e
        # `_ENTITY_WORDS` non la contiene: `san` un ente non e'.
        #
        # **Solo la prima parola**, non una qualunque, ed e' cio' che rende
        # accettabile il prezzo. Una parola di questo elenco in mezzo o in
        # coda non scherma niente: «Mario Rossi Villa» resta protetto. In
        # testa invece la lettura «edificio» e' quella giusta quasi sempre,
        # e vale la stessa rinuncia scritta sopra `_ENTITY_WORDS`: «Villa
        # Mario Rossi» e «Casa Mario Rossi» smettono di essere sostituiti.
        #
        # L'apostrofo separa anche qui: «Sant'Antonio Abate» e' un token
        # solo, e la parola che decide e' `sant`, non `sant'antonio`.
        if tokens:
            testa = tokens[0].lower().strip("'’-.,;:")
            if _dice_edificio(testa) or _dice_edificio(re.split(r"['’]", testa)[0]):
                return m.group(0)
            # La sigla dentro la sequenza: «IC MAZZARRONE - LICODIA», dove
            # `IC` e' una parola maiuscola come le altre e finisce nel
            # tratto. Vale la stessa regola: solo in testa, e solo maiuscola.
            if _sigla_di_ente(tokens[0]):
                return m.group(0)
        common = [_is_common_in_context(tokens, i) for i in range(len(tokens))]
        # Il cognome che e' anche una parola comune, **appoggiato al nome di
        # battesimo che ha davanti**.
        #
        # `_cognome_appoggiato` esisteva gia' e faceva esattamente questo,
        # ma girava solo dopo un titolo professionale: qui, dove passano le
        # sequenze maiuscole normali, la parola comune spezzava la coppia e
        # il nome restava da solo -- e una parola sola non basta mai.
        #
        # **Misurato, non immaginato**: sul banco del richiamo i nomi persi
        # in silenzio erano 5 571, e **quattro cognomi ne facevano il 96%**
        # -- Villa (un edificio), Conti (i conti), Messina (una citta'),
        # Gentile (l'apertura di una lettera). Tutti e quattro stanno negli
        # elenchi delle parole comuni apposta, ed e' giusto che ci stiano:
        # e' la scelta che ha tolto 8 904 sostituzioni sbagliate sui moduli
        # in bianco. Cio' che mancava non era togliere la parola dall'elenco
        # -- sarebbe stato tornare indietro -- ma accorgersi che con un nome
        # di battesimo davanti quella parola non e' piu' ambigua.
        #
        # **La direzione conta ed e' tutta la sicurezza della regola**:
        # «Tommaso Gentile» e' una persona, «Gentile Cliente» resta un
        # saluto, perche' li' la parola comune viene per prima.
        #
        # `not common[i - 1]`: l'appoggio dev'essere un token che stiamo
        # gia' accettando come nome. Senza, due parole comuni di fila si
        # tirerebbero a vicenda dentro la sequenza.
        for i in range(1, len(tokens)):
            if common[i] and not common[i - 1] and _cognome_appoggiato(tokens[i - 1 : i + 1]):
                common[i] = False

        # La particella del cognome composto non spezza piu' la sequenza.
        #
        # `ponte[i]` la marca: entra nel nome, ma **non conta come
        # riscontro** — «di» non e' un nome di nessuno. Senza questa
        # distinzione «Di Salvo» avrebbe due riscontri invece di uno e
        # scavalcherebbe la soglia dei moduli senza averne il diritto.
        #
        # **A tenere il ponte dev'essere un nome di battesimo, e nient'altro.**
        #
        # La prima stesura si accontentava che la parola davanti alla
        # particella risultasse negli elenchi. Sembrava prudente e non lo era:
        # gli elenchi dei cognomi contengono centinaia di sostantivi italiani
        # — `sala`, `costa`, `rocca`, `bosco`, `casale`, `croce`, `fonte`,
        # `fontana`, `marina`, `valle`, `torre`, `conte`, `papa` — quindi la
        # regola scattava su **qualunque** «Sostantivo Di Sostantivo» scritto
        # con le maiuscole di cortesia. Misurato da una revisione avversariale
        # su 357 casi: 96 falsi positivi nuovi, e 7 passavano anche la soglia
        # dei moduli. `Sala Della Vittoria` e `Rocca Di Papa` sparivano.
        #
        # Il difetto era **strutturale e non di taratura**: la particella non
        # contava come riscontro, ma saldava in un unico tratto due parole che
        # prima erano isolate, e due isolate non bastavano mai mentre due
        # nello stesso tratto bastano. Il ponte non aggiungeva una prova:
        # toglieva il muro che teneva innocue quelle due.
        #
        # Ora i modi sono due, e in tutti e due c'e' un **nome di battesimo**:
        #   1. davanti c'e' un nome di battesimo e dopo la particella non c'e'
        #      una parola comune — «Walter Di Salvo», «Antonio Di Salvatore»;
        #   2. la forma incollata e' un cognome degli elenchi **e** un nome di
        #      battesimo sta di la' della coppia — «Di Salvo Walter», l'ordine
        #      burocratico dei moduli.
        #
        # Cio' che si perde e' il composto **da solo**, senza nessun nome
        # accanto: «il fascicolo Di Maio» non viene piu' sostituito. E' la
        # rinuncia giusta, perche' in quella forma un cognome composto e un
        # toponimo sono la stessa cosa — `Rocca Di Papa` e `Di Maio` hanno
        # esattamente la stessa struttura, e nessuna regola puo' distinguerli
        # senza qualcosa che dica «qui c'e' una persona». Quando quel qualcosa
        # c'e' — un titolo, un ruolo, un codice fiscale accanto, un saluto —
        # sono le regole di contesto a prenderlo, e quelle usano gli elenchi
        # dei composti come prima.
        #
        # In ogni caso la particella deve stare **dentro** una sequenza di
        # maiuscole: il «di» della prosa normale e' minuscolo e qui non
        # arriva mai. Ma non basta, e la revisione l'ha mostrato: intestazioni,
        # oggetti, ragioni sociali ed etichette di modulo le maiuscole ce
        # l'hanno.
        riscontro = [
            t.lower().strip("'’-") in FIRST_NAMES
            or t.lower().strip("'’-") in SURNAMES
            or _cognome_apostrofato(t)
            for t in tokens
        ]

        def _e_nome_di_battesimo(k: int) -> bool:
            return (
                0 <= k < len(tokens)
                and not common[k]
                and tokens[k].lower().strip("'’-.,;:") in FIRST_NAMES
            )

        ponte = [False] * len(tokens)
        for i in range(len(tokens) - 1):
            part = tokens[i].lower().strip("'’-.,;:")
            if part not in _PARTICELLE_COGNOME:
                continue
            dopo = tokens[i + 1].lower().strip("'’-.,;:")
            composto = _cognome_composto_noto(part, dopo)
            nome_prima = _e_nome_di_battesimo(i - 1)
            nome_dopo = _e_nome_di_battesimo(i + 2)
            if not ((nome_prima and not common[i + 1])
                    or (composto and (nome_prima or nome_dopo))):
                continue
            common[i] = False
            ponte[i] = True
            if composto:
                # «Di Natale», «Del Vecchio»: la seconda parola e' comune di
                # suo, ma incollata alla particella e' un cognome e basta.
                common[i + 1] = False
                riscontro[i + 1] = True

        pieces: list[tuple[str, int]] = []  # (testo, indice ultimo token)
        i = 0
        while i < len(tokens):
            if common[i]:
                pieces.append((tokens[i], i))
                i += 1
                continue
            j = i
            while j < len(tokens) and not common[j]:
                j += 1
            run = [t.lower().strip("'’-") for t in tokens[i:j]]
            # **Due** riscontri, non uno.
            #
            # Prima bastava che *una* parola della sequenza stesse negli
            # elenchi perche' l'intera sequenza sparisse. Su un modulo
            # amministrativo e' quasi sempre vero per caso: gli elenchi
            # contengono 2181 cognomi, e molti sono anche parole comuni --
            # Chiesa, Costa, Monte, Villa, Ponte, Sala, Carta, Banca.
            # «Imposta Lorda» spariva perche' una delle due somigliava a un
            # cognome.
            #
            # Nome e cognome adiacenti, entrambi riconosciuti, sono invece
            # una prova vera: e' la stessa regola che nel pacchetto inglese
            # decide «Sarah Whitfield». Il riscontro singolo non si butta,
            # diventa un **sospetto**: il documento resta intatto e chi
            # legge sa dove guardare.
            #
            # Fino alla 1.13.0 qui c'era una terza strada: `guessed`, che
            # sostituiva quando NESSUNA delle parole sembrava italiana --
            # cioe' senza nessun riscontro negli elenchi. E' quella che e'
            # stata ritirata: indovinava e decideva da sola.
            # `riscontro`/`ponte` invece dell'elenco letto qui: la particella
            # di un cognome composto sta dentro il nome ma non e' il nome di
            # nessuno, e contarla darebbe a «Di Salvo» due prove al prezzo di
            # una.
            noti = sum(
                1 for k in range(i, j) if riscontro[k] and not ponte[k]
            )
            lungo_giusto = 2 <= len(run) <= _MAX_TOKEN_NOME
            # Su prosa un riscontro solo basta: «da Ludovica Sbrancagnoli»
            # in una frase e' quasi sempre una persona, e pretendere due
            # riscontri costerebbe 609 nomi su 1500 email vere. Su un
            # modulo lo stesso riscontro e' quasi sempre un'etichetta, e
            # accettarlo costa 2 739 sostituzioni sbagliate.
            bastano = 1 if prosa else 2
            # P9.4: davanti alla sequenza c'e' una parola che dice
            # «edificio». `inizio` e' la posizione del primo token del
            # tratto **nel testo intero**, non nella corrispondenza: la
            # parola che decide sta fuori dalla sequenza maiuscola, e da
            # `m.group(0)` non si vede.
            inizio = m.start() + sum(len(p) for p in parts[: 2 * i])
            if lungo_giusto and noti >= bastano and _intitolazione_adiacente(text, inizio):
                original = tokens[i]
                for k in range(i + 1, j):
                    original += seps[k - 1] + tokens[k]
                pieces.append((original, j - 1))
                i = j
                continue
            if lungo_giusto and noti >= bastano:
                pieces.append(
                    (report.segnaposto("names", "{{NAME}}", " ".join(tokens[i:j])), j - 1)
                )
            else:
                if lungo_giusto and noti == 1 and not prosa:
                    report.suspect(
                        "nome",
                        " ".join(tokens[i:j]),
                        "una sola parola risulta negli elenchi dei nomi: "
                        "non basta a dire che sia una persona, ma potrebbe "
                        "esserlo",
                    )
                original = tokens[i]
                for k in range(i + 1, j):
                    original += seps[k - 1] + tokens[k]
                pieces.append((original, j - 1))
            i = j

        out = pieces[0][0]
        for prev, cur in zip(pieces, pieces[1:]):
            out += seps[prev[1]] + cur[0]
        return out

    text = _RE_NAME_RUN.sub(_pair_sub, text)
    text = _RE_NAME_PAIR_UPPER.sub(_pair_sub, text)

    # 5. Nome o cognome isolato ("Ciao Marco,", una firma con il solo
    #    cognome). Solo se non e' anche una parola comune: "Rosa" da sola
    #    resta un fiore, "Costa" da sola resta un costo.
    def _lone_sub(m: re.Match) -> str:
        tok = m.group(0).lower().strip("'’-")
        # Sotto le quattro lettere una parola isolata non e' una prova.
        # «Re» e' un cognome italiano vero, ed e' anche una parola, un
        # titolo e mezza abbreviazione: su un modello Redditi in bianco
        # veniva sostituito cinque volte. Stessa sorte per «Rao», che sta
        # nel nostro stesso nome.
        #
        # Un elenco di eccezioni non basterebbe: i cognomi corti che sono
        # anche parole sono decine, e ne salterebbero fuori altri a ogni
        # documento nuovo. Meglio una regola che si spiega in una riga.
        #
        # Il prezzo: un cognome corto scritto da solo, senza titolo e
        # senza indirizzo accanto, non viene piu' preso. Era l'appiglio
        # piu' debole che avevamo, ed e' quello che sbagliava di piu'.
        if len(tok) < 4:
            return m.group(0)
        if tok in _AMBIGUOUS_ALONE or tok in COMMON_CAPITALIZED:
            return m.group(0)
        # Il veto morfologico c'era gia', ma girava solo sulle coppie e non
        # sulla parola isolata -- che e' l'appiglio piu' debole dei due, e
        # avrebbe quindi dovuto essere il piu' protetto. Le terminazioni
        # italiane (-zione, -mento, -ale) dicono «questa e' una parola»
        # meglio di qualunque elenco di eccezioni scritto a mano, che va
        # allungato a ogni documento nuovo.
        if _looks_like_word(tok):
            return m.group(0)
        if tok not in FIRST_NAMES and tok not in SURNAMES:
            return m.group(0)
        # Il nome di battesimo che parola italiana non e', quando davanti non
        # ha niente che dica «qui c'e' un edificio».
        #
        # E' P9.2 del backlog, ed e' spenta di serie: cambia il verso di una
        # rinuncia vecchia, e chi ha costruito qualcosa sull'uscita di ieri
        # deve poterla ritrovare identica. Vale **solo per i nomi di
        # battesimo**: un cognome isolato -- «Esposito», «Ferraris» -- resta
        # un sospetto, perche' li' la parola da sola non dice se sia una
        # persona o un'azienda che porta quel cognome.
        if (
            soli
            and tok in FIRST_NAMES
            and not _dopo_una_intitolazione(text, m.start())
            and not _dentro_una_sequenza_di_ente(text, m.end())
        ):
            return report.segnaposto("names", "{{NAME}}", m.group(0))
        # Una parola sola, in elenco, senza nient'altro intorno: e' il
        # segnale piu' debole che abbiamo, e sostituire su quello vuol dire
        # cancellare «Costa», «Monte» e «Villa» ogni volta che compaiono in
        # un documento amministrativo. Diventa un sospetto: il documento
        # resta leggibile e chi lo controlla sa dove guardare.
        report.suspect(
            "nome",
            m.group(0),
            "risulta negli elenchi dei nomi ma non ha nulla intorno che "
            "dica che sia una persona: nessun titolo, nessuna firma, "
            "nessun indirizzo accanto",
        )
        return m.group(0)

    return _RE_LONE_TOKEN.sub(_lone_sub, text)


def _scrub_emails(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    out = _replace_all(text, _RE_EMAIL, "{{EMAIL}}", report, "emails")
    # Dopo quello normale, non prima: cosi' un indirizzo scritto per bene su
    # una riga sola viene preso dal riconoscitore stretto, e questo vede solo
    # cio' che l'altro ha lasciato -- cioe' i casi davvero spezzati.
    out = _replace_all(out, _RE_EMAIL_SPEZZATA, "{{EMAIL}}", report, "emails")
    # La chiocciola con lo spazio prima di quello offuscato: sono due forme
    # diverse dello stesso indirizzo e l'ordine non cambia il risultato, ma
    # questa e' la piu' frequente delle due sui documenti veri.
    out = _replace_all(out, _RE_EMAIL_SPAZIATA, "{{EMAIL}}", report, "emails")
    return _replace_all(out, _RE_EMAIL_OFFUSCATA, "{{EMAIL}}", report, "emails")


def _scrub_cf(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    def _sub(m: re.Match) -> str:
        # Si sostituisce comunque: su un dato personale l'errore va fatto
        # nella direzione prudente. Ma se la struttura torna e il carattere
        # di controllo no, quasi sempre il testo viene da un OCR che ha
        # storpiato un carattere -- e allora ne avra' storpiati altri, che
        # nessun riconoscitore ha visto.
        if not cf_check_char_ok(m.group(1)):
            report.suspect(
                "codice_fiscale",
                m.group(1),
                "sostituito, ma il carattere di controllo non torna: "
                "il documento potrebbe contenere altri dati storpiati",
            )
        return report.segnaposto("codice_fiscale", "{{CODICE_FISCALE}}", m.group(1))

    def _sub_omocodia(m: re.Match) -> str:
        # Nessun sospetto e nessuna indulgenza: o il carattere di controllo
        # torna, o non e' un codice fiscale. Vedi il commento sul pattern.
        if not cf_check_char_ok(m.group(1)):
            return m.group(0)
        return report.segnaposto("codice_fiscale", "{{CODICE_FISCALE}}", m.group(1))

    out = _RE_CF.sub(_sub, text)
    # Dopo quello stretto: cosi' un codice normale viene preso da chi lo sa
    # gia' fare, e questo vede solo cio' che l'altro ha lasciato.
    return _RE_CF_OMOCODIA.sub(_sub_omocodia, out)


def _prefisso_a_norma(candidato: str) -> str | None:
    """Il candidato tagliato alla lunghezza che il suo Paese prescrive.

    Il pattern degli IBAN spaziati non sa dove finisce il numero: indovina
    contando i gruppi. Indovinare ha due modi di sbagliare, e la tabella
    ISO 13616 -- che qui c'e' gia', serve a `iban_checksum_ok` -- li chiude
    tutti e due, perche' la lunghezza di un IBAN **non e' un'opinione**:

    * **prendere troppo**, inghiottendo la parola dopo. Prima il mod-97
      bocciava il candidato allungato e l'IBAN restava in chiaro: una
      sconfitta silenziosa. Ora il di piu' viene restituito al testo;
    * **prendere troppo poco**, lasciando la coda fuori dal segnaposto. E'
      il caso peggiore dei due, perche' il rapporto direbbe «1 IBAN
      sostituito» mentre meta' del numero e' ancora li'.

    Restituisce `None` se il codice Paese non e' nel registro o se i
    caratteri non bastano: in tutti e due i casi non e' un IBAN, e a dirlo
    non serve il mod-97.
    """
    attesa = _IBAN_LUNGHEZZE.get(candidato[:2])
    if attesa is None:
        return None
    contati = 0
    for i, c in enumerate(candidato):
        if c.isalnum():
            contati += 1
            if contati == attesa:
                return candidato[: i + 1]
    return None


def _scrub_iban(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    def _sub(m: re.Match) -> str:
        candidato = m.group(1)
        # Un a-capo si concede, due no: vedi `_RE_IBAN_SPAZIATO`. Il conto
        # sta qui e non nel pattern perche' «al massimo uno» in un'espressione
        # regolare si scrive solo duplicando mezzo pattern, e mezzo pattern
        # duplicato e' mezzo pattern che un giorno cambia da una parte sola.
        if candidato.count("\n") > 1:
            return m.group(0)
        preso = _prefisso_a_norma(candidato)
        if preso is None or not iban_checksum_ok(preso):
            return m.group(0)
        # Cio' che il pattern ha preso oltre la lunghezza di legge non e'
        # parte dell'IBAN e torna al testo: era la parola accanto.
        segno = report.segnaposto("iban", "{{IBAN}}", preso)
        return segno + candidato[len(preso):] + m.group(0)[len(candidato):]

    def _sub_incollato(m: re.Match) -> str:
        """La parola intera: qui si cerca dove finisce l'etichetta.

        Si provano tutti i punti di taglio, dal piu' lungo al piu' corto, e
        vince il primo che passa il mod-97. Provarne uno solo non basterebbe:
        «CoordinateIT86O0200…» ha piu' di un taglio che *ha la forma* di un
        IBAN, e uno solo e' quello vero. Se non ne passa nessuno la parola
        torna indietro identica -- che e' il comportamento di prima.
        """
        parola = m.group(0)
        for i in range(2, len(parola) - 14):
            if not parola[i - 1].isalpha():
                break
            coda = parola[i:]
            if _RE_SOLO_IBAN.fullmatch(coda) and iban_checksum_ok(coda):
                return parola[:i] + report.segnaposto("iban", "{{IBAN}}", coda)
        return parola

    def _sub_spaziato_incollato(m: re.Match) -> str:
        valore = m.group("valore")
        if not iban_checksum_ok(valore):
            return m.group(0)
        return m.group("etichetta") + report.segnaposto("iban", "{{IBAN}}", valore)

    out = _RE_IBAN.sub(_sub, text)
    out = _RE_IBAN_SPAZIATO.sub(_sub, out)
    # Dopo i due esatti, e solo su cio' che e' rimasto: se il valore stava
    # staccato l'ha gia' preso il pattern di prima.
    out = _RE_IBAN_INCOLLATO.sub(_sub_incollato, out)
    return _RE_IBAN_SPAZIATO_INCOLLATO.sub(_sub_spaziato_incollato, out)


def _scrub_cards(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    def _sub(m: re.Match) -> str:
        if not luhn_ok(m.group(1)):
            return m.group(0)
        return report.segnaposto("cards", "{{CARD}}", m.group(1))

    return _RE_CARD.sub(_sub, text)


def _scrub_bban(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    # Prima dei telefoni: 22 cifre di coordinate bancarie hanno la stessa
    # forma di due numeri di telefono attaccati.
    def _sub(m: re.Match) -> str:
        ctx = _context_before(m.string, m.start(), 40).lower()
        if not any(k in ctx for k in ("bban", "coordinate", "c/c", "conto", "cin ")):
            return m.group(0)
        return report.segnaposto("bban", "{{BBAN}}", m.group(0))

    out = _RE_BBAN.sub(_sub, text)
    out = _replace_all(out, _RE_ABI_CAB, "{{BBAN}}", report, "bban")

    def _sub_conto(m: re.Match) -> str:
        # Le cifre vere, senza separatori: sotto le otto e' un numero
        # qualunque — un civico, un anno, un codice di due lettere — e
        # l'etichetta da sola non basta a farne un conto.
        cifre = re.sub(r"\D", "", m.group("val"))
        if not 8 <= len(cifre) <= 16:
            return m.group(0)
        prima = m.string[m.start():m.start("val")]
        return prima + report.segnaposto("bban", "{{BBAN}}", m.group("val"))

    return _RE_CONTO_ETICHETTATO.sub(_sub_conto, out)


# Recupero dei codici storpiati dall'OCR. Gira dopo i riconoscitori esatti,
# su cio' che e' rimasto, e sostituisce *solo* se il checksum del candidato
# corretto torna. E' quello che permette di essere tolleranti senza aprire
# ai falsi positivi: non decide un'euristica, decide l'aritmetica.
def _scrub_fuzzy_cf(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    def _sub(m: re.Match) -> str:
        corretto = cf_ocr_recover(m.group(0))
        if corretto is None:
            return m.group(0)
        if not report.solo_rilevata("codice_fiscale"):
            report.add("ocr_corretti")
        # La chiave e' il codice **corretto**, non quello storpiato: se lo
        # stesso codice fiscale compare una volta pulito e una volta rovinato
        # dall'OCR, sono la stessa persona e devono avere lo stesso numero.
        return report.segnaposto(
            "codice_fiscale", "{{CODICE_FISCALE}}", corretto, originale=m.group(0)
        )

    return _RE_FUZZY_CF.sub(_sub, text)


def _scrub_fuzzy_iban(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    def _sub(m: re.Match) -> str:
        corretto = iban_ocr_recover(m.group(0))
        if corretto is None:
            return m.group(0)
        if not report.solo_rilevata("iban"):
            report.add("ocr_corretti")
        return report.segnaposto("iban", "{{IBAN}}", corretto, originale=m.group(0))

    return _RE_FUZZY_IBAN.sub(_sub, text)


def _scrub_piva(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    # Only replace if preceded by context keywords nearby or IT prefix.
    def _sub(m: re.Match) -> str:
        # Gli spazi si tolgono prima di cercare le parole di contesto.
        #
        # Senza, «P. IVA 98157711791» -- con lo spazio dopo il punto, cioe'
        # **come si scrive su meta' delle fatture italiane** -- non
        # corrispondeva a nessuna delle chiavi: nel contesto c'era «p. iva»
        # e si cercava «p.iva». Tutte le altre forme funzionavano
        # («P.IVA», «Partita IVA», «C.F./P.IVA», «partita I.V.A.»), e questa
        # e' rimasta scoperta finche' il banco del richiamo non l'ha
        # contata: 312 partite IVA valide perse in silenzio su 18 695.
        ctx = _context_before(m.string, m.start()).lower()
        ctx_compatto = ctx.replace(" ", "").replace("\t", "")
        raw = m.group(0)
        if raw.upper().startswith("IT") or any(
            k in ctx or k in ctx_compatto
            for k in ("p.iva", "piva", "partita", "vat", "c.f.")
        ):
            # Stessa scelta del codice fiscale: sostituisce comunque, e se
            # la cifra di controllo non torna lo dice.
            if not piva_check_ok(m.group(1)):
                report.suspect(
                    "partita_iva",
                    m.group(1),
                    "sostituita, ma la cifra di controllo non torna: "
                    "o non era una partita IVA, o il documento e' storpiato",
                )
            return report.segnaposto("partita_iva", "{{PARTITA_IVA}}", m.group(1))
        return raw

    return _RE_PIVA.sub(_sub, text)


def _scrub_phones(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    def _sub(m: re.Match) -> str:
        if not _phone_is_plausible(m):
            return m.group(0)
        return report.segnaposto("phones", "{{PHONE}}", m.group(0))

    def _sub_etichetta(m: re.Match) -> str:
        # Il contesto qui non si cerca all'indietro: **e' dentro la
        # corrispondenza**. Cercarlo indietro da m.start() guarderebbe cio'
        # che sta prima di «Tel.», cioe' il posto sbagliato.
        if not _phone_is_plausible(m, contesto=True):
            return m.group(0)
        numero = m.group(0)[len(m.group("etichetta")):]
        return m.group("etichetta") + report.segnaposto("phones", "{{PHONE}}", numero)

    out = _RE_PHONE.sub(_sub, text)
    return _RE_PHONE_ETICHETTA.sub(_sub_etichetta, out)


def _scrub_amounts(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    def _sub(m: re.Match) -> str:
        if not _amount_is_plausible(m):
            return m.group(0)
        return report.segnaposto("amounts", "{{AMOUNT}}", m.group(0))

    return _RE_AMOUNT.sub(_sub, text)


# ---------------------------------------------------------------------------
# Pacchetto EN: gli identificativi anglosassoni
# ---------------------------------------------------------------------------
#
# La regola che decide qui e' una sola, e viene da una misura: su 20.000
# sequenze casuali di nove cifre, il controllo strutturale del SSN ne accetta
# quasi il novanta per cento. Non e' un validatore, e' un filtro di forma.
# Quindi **niente si sostituisce sulle cifre nude**: o c'e' la punteggiatura
# che identifica il formato (i trattini 3-2-4 del SSN), o c'e' una parola di
# contesto accanto. Dove invece esiste un checksum vero -- NHS mod-11,
# routing 3-7-1, SIN Luhn -- il validatore fa meta' del lavoro e il contesto
# copre l'altra meta'.
#
# Senza questa regola il pacchetto EN redigerebbe numeri di protocollo,
# codici articolo e riferimenti di fattura: esattamente il difetto che il
# corpus amministrativo esiste per intercettare.

_RE_SSN = re.compile(r"(?<![\w-])(\d{3}-\d{2}-\d{4})(?![\w-])")
# Due lettere qualsiasi, non solo quelle ammesse: le esclusioni di HMRC le
# applica ``nino_ok``. Metterle nel pattern sembra piu' efficiente e invece
# rompe la regola della casa -- il pattern propone, il validatore decide --
# e soprattutto rende invisibile il caso che conta: un NINO vero con le due
# lettere storpiate dall'OCR non somiglierebbe piu' a niente, e non
# finirebbe nemmeno fra i sospetti.
_RE_NINO = re.compile(
    r"(?<![\w])([A-Z]{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?[A-D])(?![\w])"
)
# Dieci cifre, nella spaziatura 3-3-4 in cui l'NHS le stampa oppure attaccate.
_RE_NHS = re.compile(r"(?<![\w-])(\d{3}[ -]?\d{3}[ -]?\d{4})(?![\w-])")
_RE_NOVE_CIFRE = re.compile(r"(?<![\w-])(\d{3}[ -]?\d{3}[ -]?\d{3}|\d{9})(?![\w-])")

_CTX_NHS = ("nhs", "health number", "patient number")
_CTX_ROUTING = ("routing", "aba", "rtn", "transit number")
_CTX_SIN = ("sin", "social insurance", "numero di assicurazione sociale")


def _con_contesto(m: re.Match, parole: tuple[str, ...], finestra: int = 40) -> bool:
    ctx = _context_before(m.string, m.start(), finestra).lower()
    return any(p in ctx for p in parole)


def _scrub_en_ssn(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    """SSN e ITIN, solo nella forma trattinata 3-2-4.

    Nove cifre attaccate non si toccano: sarebbero indistinguibili da un
    numero di pratica. I trattini nelle posizioni giuste sono l'unica cosa
    che rende il formato riconoscibile, e le esclusioni della SSA (aree
    000, 666, 900-999; gruppo 00; seriale 0000) fanno il resto.

    L'ITIN va provato per primo: comincia per 9, che ``ssn_ok`` rifiuta.
    """
    def _sub(m: re.Match) -> str:
        raw = m.group(1)
        # `Tel. 078-05-1120` e `Fax: 090-12-3456` sono numeri italiani, non
        # SSN: la forma 3-2-4 e' identica, e l'unica cosa che separa i due
        # casi e' l'etichetta che li precede. Senza questa riga un notaio
        # italiano -- che il pacchetto inglese ce l'ha acceso di serie -- si
        # vedeva contare come «SSN» il centralino dello studio. Il dato
        # spariva comunque, ma il rapporto diceva il falso sulla tipologia, e
        # un rapporto che sbaglia il tipo non serve a rispondere a chi chiede
        # *cosa* c'era nel file.
        #
        # Qui si lascia stare, non si sostituisce: il passo dei telefoni gira
        # dopo e quel numero lo prende lo stesso. Non e' una speranza, e' la
        # riga che regge la correzione — se smettesse di prenderlo, il numero
        # resterebbe in chiaro. Provato nei due versi in
        # `tests/test_ssn_non_e_un_telefono.py`.
        if _RE_PHONE_CTX.search(_context_before(m.string, m.start(), 40)):
            return raw
        if itin_ok(raw):
            return report.segnaposto("itin", "{{ITIN}}", raw)
        if ssn_ok(raw):
            return report.segnaposto("ssn", "{{SSN}}", raw)
        # La forma c'e' ma la SSA quel numero non l'ha mai emesso: non si
        # sostituisce, e lo si dice.
        report.suspect(
            "ssn",
            raw,
            "ha la forma di un SSN ma cade in un intervallo mai assegnato: "
            "o non e' un SSN, o e' storpiato",
        )
        return raw

    return _RE_SSN.sub(_sub, text)


def _scrub_en_nino(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    """National Insurance Number britannico.

    Nessun checksum, ma le esclusioni di HMRC -- D, F, I, Q, U, V mai come
    prima o seconda lettera, O mai come seconda, sette prefissi mai
    allocati -- tolgono buona parte dello spazio delle lettere, e la forma
    «due lettere, sei cifre, una lettera fra A e D» in un testo normale non
    capita per caso.
    """
    def _sub(m: re.Match) -> str:
        if not nino_ok(m.group(1)):
            # La forma c'e' ma il prefisso non e' fra quelli allocati.
            # Succede in due casi opposti: qualcuno ha copiato l'esempio di
            # gov.uk (che usa QQ apposta, perche' non viene mai emesso),
            # oppure un OCR ha storpiato le lettere di un NINO vero. Il
            # secondo caso e' il motivo per cui va segnalato.
            report.suspect(
                "nino",
                m.group(1),
                "ha la forma di un National Insurance Number ma il prefisso "
                "non e' mai stato allocato: o e' un esempio, o e' storpiato",
            )
            return m.group(0)
        return report.segnaposto("nino", "{{NINO}}", m.group(0))

    return _RE_NINO.sub(_sub, text)


def _scrub_en_nhs(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    """NHS number: mod-11, ma serve comunque il contesto.

    Il mod-11 lascia passare circa una sequenza di dieci cifre su nove: da
    solo redigerebbe numeri di fattura. Con la parola «NHS» accanto invece
    e' quasi certo, ed e' cosi' che compare nei documenti veri.
    """
    def _sub(m: re.Match) -> str:
        if not _con_contesto(m, _CTX_NHS) or not nhs_number_ok(m.group(1)):
            return m.group(0)
        return report.segnaposto("nhs_number", "{{NHS_NUMBER}}", m.group(0))

    return _RE_NHS.sub(_sub, text)


def _scrub_en_nove_cifre(
    text: str, report: RedactionReport, opts: PrivacyOptions
) -> str:
    """Routing bancario statunitense e SIN canadese.

    Stessa lunghezza, checksum diversi, e nessuno dei due si puo' cercare
    senza contesto: nove cifre sono la forma piu' comune che esista in un
    documento amministrativo. Sono un passo solo perche' competono per lo
    stesso testo, e chi decide e' la parola che sta davanti.
    """
    def _sub(m: re.Match) -> str:
        raw = m.group(1)
        if _con_contesto(m, _CTX_ROUTING) and aba_routing_ok(raw):
            return report.segnaposto("routing_number", "{{ROUTING_NUMBER}}", raw)
        if _con_contesto(m, _CTX_SIN) and sin_ok(raw):
            return report.segnaposto("sin", "{{SIN}}", raw)
        return raw

    return _RE_NOVE_CIFRE.sub(_sub, text)


# ---------------------------------------------------------------------------
# Indirizzi inglesi, e il codice postale che ci sta dentro
# ---------------------------------------------------------------------------
#
# Il discriminante e' **il numero civico**, e non e' un dettaglio.
#
# In italiano l'indirizzo comincia con la parola: «via», «piazza», «corso».
# In inglese finisce con essa -- Street, Road, Lane, Way -- e quelle parole
# formano anche i nomi delle cose: «the loading bay on Church Road», «the
# Sterling Way depot», «Green Lane Logistics», «the Young Street office».
# Sono tutte nel corpus amministrativo, e un riconoscitore che si fermasse
# al tipo di via le redigerebbe tutte e quattro.
#
# Un indirizzo vero porta il civico davanti. E' l'unica differenza
# strutturale affidabile fra «47 Baker Street» e «Baker Street».

_EN_TIPI_VIA = (
    r"street|st|road|rd|avenue|ave|lane|ln|close|drive|way|court|ct|place|pl|"
    r"square|sq|terrace|gardens|gdns|crescent|cres|row|walk|mews|boulevard|"
    r"blvd|highway|hwy|parkway|pkwy|circle|cir|trail"
)

# Il codice postale britannico, nella forma che compare nella posta
# ordinaria. La regex ufficiale del governo ha anche i rami dei territori
# d'oltremare, che accettano cose come "AB 12": in un documento
# amministrativo quella forma capita per caso.
_UK_POSTCODE = r"[A-Z]{1,2}\d[A-Z\d]?[ ]?\d[A-Z]{2}"
_US_ZIP = r"\d{5}(?:-\d{4})?"

_RE_EN_ADDRESS = re.compile(
    r"(?<![\w/-])"
    r"\d{1,5}[A-Za-z]?"                                   # il civico
    # Almeno **una** parola fra il civico e il tipo di via: e' il nome della
    # strada, e in un indirizzo vero c'e' sempre. Con zero ammesse bastava
    # «numero + parola che e' anche un tipo di via», e sui moduli fiscali
    # statunitensi in bianco usciva `43 Court` (da «43 Court Ordered
    # Payments»), `225 St`, `2 Circle`: nove indirizzi inventati su documenti
    # che non ne contengono nessuno. Un civico attaccato al tipo di via senza
    # nome in mezzo non e' un indirizzo, e' un numero seguito da una parola.
    rf"{_SP}(?:{_TOK}{_SP}){{1,3}}(?i:{_EN_TIPI_VIA})\b"   # ... Baker Street
    rf"(?:{_SP}(?i:NE|NW|SE|SW|N|S|E|W)\b)?"              # ... Avenue NW
    rf"(?:,[ \t]*[^,\n]{{1,40}}){{0,3}}"                  # interno, citta'
    rf"(?:[ \t]+(?:{_UK_POSTCODE}|{_US_ZIP}))?"           # e il codice postale
)

# Un codice postale rimasto fuori da un indirizzo completo. Da solo non si
# tocca: la forma britannica somiglia a un codice articolo. Serve una
# parola che dica che li' c'e' un recapito.
_RE_EN_POSTCODE = re.compile(rf"(?<![\w-])({_UK_POSTCODE})(?![\w-])")
_CTX_INDIRIZZO = (
    "postcode", "post code", "zip", "address", "residing", "resident",
    "delivery", "registered office", "correspondence",
)


def _scrub_en_addresses(
    text: str, report: RedactionReport, opts: PrivacyOptions
) -> str:
    def _sub(m: re.Match) -> str:
        return report.segnaposto("addresses", "{{ADDRESS}}", m.group(0))

    out = _RE_EN_ADDRESS.sub(_sub, text)

    def _sub_cap(m: re.Match) -> str:
        if not _con_contesto(m, _CTX_INDIRIZZO):
            return m.group(0)
        return report.segnaposto("addresses", "{{POSTCODE}}", m.group(0))

    return _RE_EN_POSTCODE.sub(_sub_cap, out)


# ---------------------------------------------------------------------------
# Australia, e i documenti di viaggio
# ---------------------------------------------------------------------------

_RE_ABN = re.compile(r"(?<![\w-])(\d{2}[ ]?\d{3}[ ]?\d{3}[ ]?\d{3}|\d{11})(?![\w-])")
_RE_TFN = re.compile(r"(?<![\w-])(\d{3}[ ]?\d{3}[ ]?\d{2,3})(?![\w-])")

_CTX_ABN = ("abn", "australian business number")
_CTX_TFN = ("tfn", "tax file number")

# Le righe in fondo a un passaporto: solo maiuscole, cifre e il riempitivo
# "<". Il doppio riempitivo e' cio' che nessun'altra riga di testo ha, ed e'
# quello che rende la ricerca sicura.
#
# Si cerca il **blocco**, non la singola riga, e la ragione e' che la prima
# riga -- quella che contiene cognome e nome -- finisce con i riempitivi,
# non con una cifra di controllo. Cercando riga per riga, quella non
# avrebbe superato nessun controllo: sarebbe diventata un sospetto, e il
# nome sarebbe rimasto nel documento. Cioe' il difetto peggiore possibile,
# proprio sulla riga che conta di piu'.
_RE_MRZ = re.compile(r"(?m)^(?:[A-Z0-9<]{28,44}\r?\n){1,2}[A-Z0-9<]{28,44}$")


def _scrub_en_au(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    """ABN e TFN australiani.

    Entrambi hanno un checksum vero -- mod-89 e mod-11 -- ma entrambi sono
    solo cifre: senza la sigla accanto si redigerebbero i totali di una
    fattura. Il checksum riduce il rumore, il contesto lo azzera.
    """
    def _sub_abn(m: re.Match) -> str:
        if not _con_contesto(m, _CTX_ABN) or not abn_ok(m.group(1)):
            return m.group(0)
        return report.segnaposto("abn", "{{ABN}}", m.group(0))

    def _sub_tfn(m: re.Match) -> str:
        if not _con_contesto(m, _CTX_TFN) or not tfn_ok(m.group(1)):
            return m.group(0)
        return report.segnaposto("tfn", "{{TFN}}", m.group(0))

    out = _RE_ABN.sub(_sub_abn, text)
    return _RE_TFN.sub(_sub_tfn, out)


def _scrub_mrz(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    """La zona a lettura automatica di un passaporto o di una carta.

    Non si cerca il numero del documento: da solo non ha nulla che lo
    distingua da un codice qualsiasi. Si cerca la **riga** -- solo
    maiuscole, cifre e riempitivi, con almeno un doppio "<" -- e poi la
    cifra di controllo ICAO conferma che non e' una stringa qualunque.

    Vale la pena perche' una riga MRZ contiene cognome, nome,
    cittadinanza, data di nascita, sesso e scadenza tutti insieme: e' il
    pezzo di testo piu' denso di dati personali che possa capitare in un
    documento scansionato.
    """
    def _sub(m: re.Match) -> str:
        blocco = m.group(0)
        if "<<" not in blocco:
            return blocco
        # I campi che portano la propria cifra di controllo subito accanto:
        # numero del documento (posizioni 1-10), data di nascita (14-20),
        # scadenza (22-28). Non si usa la cifra composita di fine riga
        # perche' quella si calcola su pezzi **non contigui**, e darle in
        # pasto la riga intera la fa sempre fallire.
        campi = ((0, 10), (13, 20), (21, 28))
        righe = blocco.splitlines()
        if not any(
            mrz_check_digit_ok(r[a:b])
            for r in righe
            for a, b in campi
            if len(r) >= b and r[b - 1].isdigit()
        ):
            report.suspect(
                "mrz",
                blocco.replace("\n", " "),
                "ha la forma della zona a lettura automatica di un documento "
                "ma nessuna cifra di controllo torna: possibile lettura OCR "
                "sbagliata, e li' dentro ci sono nome, nascita e cittadinanza",
            )
            return blocco
        return report.segnaposto("mrz", "{{MRZ}}", blocco)

    return _RE_MRZ.sub(_sub, text)


# ---------------------------------------------------------------------------
# Nomi inglesi: solo dove il testo dice che e' un nome
# ---------------------------------------------------------------------------
#
# Qui non c'e' nessun elenco di nomi, ed e' una scelta.
#
# In italiano l'euristica «due parole maiuscole che non sono parole
# italiane» regge perche' -zione, -mento e -ale sono terminazioni di parole
# e non di cognomi. In inglese quella separazione non esiste: -son, -ton,
# -er sono entrambe le cose. E le parole inglesi comunissime che sono anche
# nomi -- Mark, Bill, Grace, Will, May, June, Rose, Brown, Green, Baker,
# Price, Young, Church, Sterling -- rendono qualunque elenco una macchina
# per falsi positivi. Misurato: il motore italiano applicato a un documento
# amministrativo inglese produceva 22 sostituzioni su un testo senza un
# solo dato personale, e 22 su un modulo fiscale statunitense in bianco.
#
# Quindi si sostituisce **solo dove il testo dichiara che quella e' una
# persona**: un titolo davanti, una formula di apertura o di chiusura, un
# indirizzo di posta accanto. Sono regole di contesto pure, che non
# costano un byte di dati e non sbagliano quasi mai.
#
# Il prezzo e' dichiarato: un nome in mezzo a una frase, senza titolo e
# senza firma, **sopravvive**. Per prenderlo servirebbe un modello, che
# violerebbe la promessa del prodotto (issue #4). Chi vuole quel richiamo
# la' sa dove chiederlo; chi legge il report vede il divario nei sospetti
# invece di scoprirlo dopo.

# «Rev.» e «Hon.» erano in questo elenco e sono stati tolti dopo averli
# visti mordere su documenti veri: su un modulo fiscale statunitense in
# bianco, «(Rev. January 2011)» -- cioe' *revised* -- diventava
# «(Rev. {{NAME}} 2011)». Un titolo che vale anche come abbreviazione di
# un'altra parola non e' una prova di contesto: e' un'ambiguita'.
_EN_TITOLI = (
    r"mr|mrs|ms|miss|mx|dr|prof|professor|sir|dame|"
    r"capt|captain|lord|lady|madam"
)

# Parole che seguono un titolo o un «Dear» senza essere nomi di persona.
# Senza questo elenco «Dear Sir», «Dear All» e «Dear Team» diventerebbero
# tre falsi positivi in cima a ogni lettera formale.
_EN_NON_NOMI = frozenset(
    {
        "sir", "sirs", "madam", "madams", "all", "team", "teams",
        "colleagues", "colleague", "customer", "customers", "client",
        "clients", "friend", "friends", "both", "everyone", "everybody",
        "member", "members", "resident", "residents", "parent", "parents",
        "student", "students", "applicant", "applicants", "reader",
    }
)

_RE_EN_TITLE_NAME = re.compile(
    rf"(?<!\w)(?i:{_EN_TITOLI})\.?{_SP}(?P<name>{_TOK}(?:{_SP}{_TOK}){{0,2}})"
)

# «Dear James,» — l'apertura epistolare e' la dichiarazione piu' esplicita
# che esista: quello che segue e' una persona, o e' una delle formule
# generiche di _EN_NON_NOMI.
_RE_EN_DEAR = re.compile(
    rf"(?<!\w)(?i:dear|attn|attention|c/o)[:.]?{_SP}"
    rf"(?P<name>{_TOK}(?:{_SP}{_TOK}){{0,2}})"
)

# La firma: una formula di chiusura, un a capo, e il nome. E' il punto in
# cui in una mail di lavoro il nome compare praticamente sempre, e dove
# nessun'altra regola lo prenderebbe -- non ha titolo davanti e non ha
# l'indirizzo accanto.
_EN_CHIUSURE = (
    r"(?:kind|best|warm|kindest)?\s*regards|"
    r"yours\s+(?:sincerely|faithfully|truly)|sincerely(?:\s+yours)?|"
    r"best\s+wishes|many\s+thanks|with\s+thanks|thanks\s+and\s+regards"
)
_RE_EN_FIRMA = re.compile(
    rf"(?i:{_EN_CHIUSURE})[,.]?[ \t]*\r?\n\s*(?P<name>{_TOK}(?:{_SP}{_TOK}){{0,2}})"
)

# Un nome attaccato a un indirizzo gia' sostituito. A differenza
# dell'italiano non si accetta **mai** una parola sola: senza elenchi non
# c'e' modo di distinguere «Contact {{EMAIL}}» da «Sarah {{EMAIL}}», e il
# verbo verrebbe redatto. Due parole maiuscole davanti a un indirizzo sono
# invece quasi sempre nome e cognome.
_RE_EN_NOME_PRIMA_EMAIL = re.compile(
    rf"(?P<name>{_TOK}{_SP}{_TOK}(?:{_SP}{_TOK})?)"
    rf"(?P<sep>\s*[<\(\[]\s*){_rif_segnaposto('EMAIL')}"
)
_RE_EN_NOME_DOPO_EMAIL = re.compile(
    rf"{_rif_segnaposto('EMAIL')}(?P<sep>\s*[<\(\[]\s*)"
    rf"(?P<name>{_TOK}{_SP}{_TOK}(?:{_SP}{_TOK})?)"
)


def _en_nome_utile(name: str) -> str | None:
    """Toglie dalla coda le parole che non sono nomi, e dice se resta nulla."""
    tokens = name.split()
    while tokens and tokens[-1].lower().strip(".,;:'’-") in _EN_NON_NOMI:
        tokens.pop()
    if not tokens:
        return None
    if tokens[0].lower().strip(".,;:'’-") in _EN_NON_NOMI:
        return None
    return " ".join(tokens)


def _scrub_en_names(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    def _sub(m: re.Match) -> str:
        name = m.group("name")
        utile = _en_nome_utile(name)
        if utile is None:
            return m.group(0)
        # Si sostituisce solo la parte utile: la coda ("Thank you" dopo la
        # virgola non ci arriva, ma un titolo di coda si').
        segno = report.segnaposto("names", "{{NAME}}", utile)
        return m.group(0).replace(name, segno + name[len(utile):], 1)

    for pattern in (
        _RE_EN_TITLE_NAME,
        _RE_EN_DEAR,
        _RE_EN_FIRMA,
        _RE_EN_NOME_PRIMA_EMAIL,
        _RE_EN_NOME_DOPO_EMAIL,
    ):
        text = pattern.sub(_sub, text)
    return text


@dataclass(frozen=True)
class Passo:
    """Un riconoscitore nella sequenza, con il pacchetto che lo possiede.

    ``nome`` non e' decorativo: e' l'identificativo con cui i test dicono
    quale passo intendono, e non deve cambiare quando cambia il nome della
    funzione.
    """

    nome: str
    pacchetto: str
    campo: str  # il campo di PrivacyOptions che lo accende
    priorita: int
    esegui: Callable[[str, RedactionReport, PrivacyOptions], str]


# **L'ordine di questa lista e' il comportamento del motore.** Non e'
# casuale: i segreti per primi (una chiave privata contiene di tutto), gli
# URL prima delle email (un indirizzo dentro un link non deve spezzare il
# link), i codici prima dei telefoni (una partita IVA e' undici cifre), i
# nomi per ultimi, quando i segnaposto gia' inseriti fanno da contesto.
# Spostare una riga qui cambia cio' che esce: il banco golden se ne accorge.
#
# La **priorita' e' del tipo di dato, non del pacchetto**: un codice fiscale
# (it) e un SSN (en) devono girare insieme, prima dei telefoni, perche' e'
# quello che oggi impedisce a un telefono di mangiarsi una partita IVA. Se
# l'ordine seguisse i pacchetti, aggiungerne un terzo lo romperebbe -- e si
# vedrebbe come una redazione sbagliata, non come un errore di ordinamento.
SEQUENZA: tuple[Passo, ...] = (
    Passo("secrets", CORE, "secrets", 10, lambda t, r, o: _scrub_secrets(t, r)),
    Passo("urls", CORE, "urls", 20, lambda t, r, o: _scrub_urls(t, r)),
    Passo("emails", CORE, "emails", 30, _scrub_emails),
    # La riga MRZ di un passaporto contiene cognome, nome, cittadinanza,
    # data di nascita e scadenza tutti insieme: va tolta intera, prima che
    # gli altri riconoscitori la smontino a pezzi e ne lascino meta'.
    Passo("mrz", EN, "fiscal", 39, _scrub_mrz),
    # I codici: 40-49. L'ordine interno conta -- i riconoscitori esatti
    # prima di quelli tolleranti all'OCR, che girano su cio' che e' rimasto.
    Passo("codice_fiscale", IT, "fiscal", 40, _scrub_cf),
    Passo("iban", CORE, "fiscal", 41, _scrub_iban),
    Passo("cards", CORE, "fiscal", 42, _scrub_cards),
    Passo("bban", IT, "fiscal", 43, _scrub_bban),
    Passo("codice_fiscale_ocr", IT, "fiscal", 44, _scrub_fuzzy_cf),
    Passo("iban_ocr", CORE, "fiscal", 45, _scrub_fuzzy_iban),
    Passo("partita_iva", IT, "fiscal", 46, _scrub_piva),
    # Gli identificativi anglosassoni stanno nella stessa fascia dei codici
    # italiani, non dopo: e' la ragione per cui la priorita' e' del tipo di
    # dato. Un SSN deve essere deciso prima che il riconoscitore dei
    # telefoni veda nove cifre e le prenda per un recapito.
    Passo("ssn", EN, "fiscal", 47, _scrub_en_ssn),
    Passo("nino", EN, "fiscal", 47, _scrub_en_nino),
    Passo("nhs_number", EN, "fiscal", 48, _scrub_en_nhs),
    Passo("routing_sin", EN, "fiscal", 49, _scrub_en_nove_cifre),
    Passo("abn_tfn", EN, "fiscal", 49, _scrub_en_au),
    Passo("date_nascita", IT, "dates", 50, lambda t, r, o: _scrub_birth_dates(t, r)),
    # Il pattern e' internazionale (prefisso +CC, parola di contesto anche
    # in inglese); restano italiane solo le due scorciatoie senza contesto,
    # cellulare 3xx e fisso 0xx, dentro _phone_is_plausible. Vanno separate
    # quando arrivera' il pacchetto inglese con le regole NANP.
    Passo("documenti_id", IT, "documenti", 52,
          lambda t, r, o: _scrub_documenti_id(t, r)),
    # Pacchetto «atti e pratiche», spento di serie: vedi `ATTI`.
    #
    # Il numero di pratica sta **prima** dei telefoni di proposito: le due
    # regole guardano la stessa cifra con l'intenzione opposta -- il
    # riconoscitore dei telefoni rifiuta un protocollo, questo lo cerca -- e
    # chi ha acceso il pacchetto ha detto quale delle due vuole.
    Passo("pratica", ATTI, "atti", 54, lambda t, r, o: _scrub_pratica(t, r)),
    Passo("catasto", ATTI, "atti", 55, lambda t, r, o: _scrub_catasto(t, r)),
    Passo("targhe", ATTI, "atti", 56, lambda t, r, o: _scrub_targhe(t, r)),
    # Non tocca il testo: l'unico effetto e' una riga di rapporto. Sta nel
    # pacchetto italiano perche' sono le parole italiane a dichiararli.
    Passo("eta_sesso", IT, "quasi_id", 58,
          lambda t, r, o: _scrub_eta_sesso(t, r)),
    Passo("phones", CORE, "phones", 60, _scrub_phones),
    # Euro e parole italiane: "importo", "imponibile", "canone".
    Passo("amounts", IT, "amounts", 65, _scrub_amounts),
    Passo("addresses", IT, "addresses", 70, lambda t, r, o: _scrub_addresses(t, r)),
    Passo("addresses_en", EN, "addresses", 71, _scrub_en_addresses),
    Passo(
        "names", IT, "names", 90,
        lambda t, r, o: _scrub_names(t, r, prosa=o.prosa, soli=o.names_alone),
    ),
    # Stessa fascia dei nomi italiani: se i due pacchetti sono accesi
    # insieme gira prima quello italiano, che e' piu' aggressivo, e questo
    # raccoglie cio' che resta.
    Passo("names_en", EN, "names", 91, _scrub_en_names),
)


# Le due liste dello studio: quanti termini e quanto lunghi. Non e' avarizia,
# e' che ogni termine diventa un'alternativa in un'unica espressione regolare
# applicata a tutto il documento, e un elenco senza freni la fa esplodere.
MAX_TERMINI = 500
MAX_LUNGHEZZA_TERMINE = 120

# Segnaposto per i termini protetti. I due caratteri di delimitazione stanno
# nell'area a uso privato di Unicode: non sono `\w`, non compaiono in un
# documento vero, e nessun riconoscitore puo' accorgersene. Dentro solo
# lettere minuscole, cosi' nemmeno l'euristica dei nomi ci inciampa.
_APERTA, _CHIUSA = chr(0xE000), chr(0xE001)


def termini_da(valore) -> tuple[str, ...]:
    """Legge la lista di termini scritta dall'utente.

    Un termine per riga: e' come lo si scrive in una casella di testo, e una
    virgola dentro un termine ("Rossi, Bianchi & Co.") non deve spezzarlo in
    due. Vuoti e duplicati cadono; l'ordine di scrittura si conserva perche'
    e' l'ordine in cui l'utente li rilegge.
    """
    if valore is None:
        return ()
    if isinstance(valore, (list, tuple)):
        righe = [str(v) for v in valore]
    else:
        righe = str(valore).splitlines()

    fuori: list[str] = []
    visti: set[str] = set()
    for riga in righe:
        t = " ".join(riga.split())[:MAX_LUNGHEZZA_TERMINE].strip()
        # Un termine di un carattere solo sostituirebbe mezzo documento.
        if len(t) < 2 or t.lower() in visti:
            continue
        visti.add(t.lower())
        fuori.append(t)
        if len(fuori) >= MAX_TERMINI:
            break
    return tuple(fuori)


def _regex_termini(termini: tuple[str, ...]) -> re.Pattern | None:
    """Un'espressione sola per tutta la lista, i piu' lunghi per primi.

    L'ordine conta: con "Rossi" prima di "Rossi & Partners" la ricerca si
    fermerebbe al cognome e mezzo termine resterebbe scoperto.

    Gli spazi interni diventano spazi **orizzontali**: un termine di due
    parole va riconosciuto anche se il documento lo separa con due spazi o
    con una tabulazione, ma non deve attraversare un ritorno a capo — e'
    esattamente l'errore che aveva l'email offuscata (issue #3), dove `\\s*`
    si mangiava la riga successiva.
    """
    if not termini:
        return None
    pezzi = []
    for t in sorted(termini, key=len, reverse=True):
        corpo = r"[^\S\r\n]+".join(re.escape(p) for p in t.split())
        prima = r"(?<!\w)" if t[:1].isalnum() or t[:1] == "_" else ""
        dopo = r"(?!\w)" if t[-1:].isalnum() or t[-1:] == "_" else ""
        pezzi.append(f"{prima}(?:{corpo}){dopo}")
    return re.compile("|".join(pezzi), re.IGNORECASE)


def _proteggi(text: str, termini: tuple[str, ...]) -> tuple[str, dict[str, str]]:
    """Mette al riparo i termini della lista «mai», prima di ogni altra cosa.

    Sostituirli con un segnaposto inerte e rimetterli alla fine e' l'unico
    modo perche' la protezione valga davvero per tutti i riconoscitori. La
    via alternativa — chiedere a ognuno di controllare la lista — lascia
    scoperto il riconoscitore che ci si dimentica di modificare, ed e' il
    genere di difetto che non si vede finche' non esce un dato.
    """
    rex = _regex_termini(termini)
    if rex is None:
        return text, {}

    tavola: dict[str, str] = {}

    def _sub(m: re.Match) -> str:
        chiave = f"{_APERTA}{_numero_a_lettere(len(tavola))}{_CHIUSA}"
        tavola[chiave] = m.group(0)
        return chiave

    return rex.sub(_sub, text), tavola


def _numero_a_lettere(n: int) -> str:
    fuori = ""
    n += 1
    while n:
        n, resto = divmod(n - 1, 26)
        fuori = chr(97 + resto) + fuori
    return fuori


def _ripristina(text: str, tavola: dict[str, str]) -> str:
    for chiave, originale in tavola.items():
        text = text.replace(chiave, originale)
    return text


def apply_privacy_filter(
    text: str,
    options: PrivacyOptions | None = None,
) -> tuple[str, RedactionReport]:
    """Apply selected redactions. Returns (cleaned_text, report).

    I riconoscitori, il loro ordine e il pacchetto a cui appartengono stanno
    tutti in ``SEQUENZA``. Qui resta solo la regola di esecuzione: un passo
    gira se il suo pacchetto e' fra quelli scelti **e** se il suo
    interruttore e' acceso. Erano due cose diverse scritte come una sola.
    """
    if not text:
        return text, RedactionReport()

    opts = options or PrivacyOptions()
    report = RedactionReport(numerati=opts.numerati, segnala=frozenset(opts.segnala))
    out = text

    # Prima di tutto il resto: i termini della lista «mai» escono di scena e
    # rientrano alla fine. Un termine che sta in tutte e due le liste resta
    # protetto — chi scrive «questo non toccarlo mai» sta dicendo una cosa
    # piu' specifica di chi scrive «togli sempre quello».
    out, protetti = _proteggi(out, opts.mai)

    rex_sempre = _regex_termini(opts.sempre)
    if rex_sempre is not None:
        out = _replace_all(out, rex_sempre, "{{TERM}}", report, "termini")

    attivi = set(opts.pacchetti)
    # Ordinamento stabile: a parita' di priorita' vale l'ordine di
    # dichiarazione in SEQUENZA, che e' l'ordine dei pacchetti core -> it.
    for passo in sorted(SEQUENZA, key=lambda p: p.priorita):
        if passo.pacchetto not in attivi:
            continue
        if not getattr(opts, passo.campo):
            continue
        out = passo.esegui(out, report, opts)

    # I sospetti si cercano mentre i termini protetti sono ancora nascosti:
    # segnalare a ogni conversione un dato che l'utente ha chiesto
    # espressamente di lasciare in chiaro e' rumore, non un avviso.
    find_suspects(out, report, opts)
    return _rinumera_per_comparsa(_ripristina(out, protetti)), report


def _rinumera_per_comparsa(testo: str) -> str:
    """I numeri seguono l'ordine del testo, non quello dei riconoscitori.

    Perche' serve un secondo passaggio
    ----------------------------------

    I numeri vengono assegnati mentre si sostituisce, e i riconoscitori non
    scattano nell'ordine in cui le cose stanno scritte: i segreti passano da
    tre pattern diversi, i nomi da cinque. Il risultato era leggibile solo
    per fortuna, e su una riga vera veniva cosi':

        Chiave: {{SECRET_2}} = {{SECRET_1}}

    Chi legge non ha modo di sapere che il 2 e' arrivato prima del 1 per
    ragioni di implementazione, e la prima cosa che pensa e' che manchi un
    pezzo di documento.

    Cosa NON cambia
    ---------------

    L'unica proprieta' che conta: **lo stesso valore tiene lo stesso
    numero**. Qui si rinumerano segnaposto identici, quindi due occorrenze
    dello stesso valore -- che sono lo stesso segnaposto -- restano
    identiche. Cambia solo quale numero, e in meglio.

    E resta vero che il numero non e' stabile fra documenti: dipende
    dall'ordine di comparsa in *questo* testo, che e' esattamente cio' che
    lo tiene un'informazione locale invece di un identificatore.

    Cosa NON tocca
    --------------

    I segnaposto che stavano gia' nel documento. Un file redatto e poi
    ripassato dal motore contiene `{{NAME_5}}` scritti in un'altra
    conversione: rinumerarli sarebbe riscrivere testo che non abbiamo
    toccato. La distinzione la fa `SENTINELLA`, che marca solo i nostri e
    sparisce proprio qui.
    """
    if SENTINELLA not in testo:
        return testo
    nuovi: dict[str, dict[str, int]] = {}

    def _assegna(m: re.Match) -> str:
        etichetta, numero = m.group(1), m.group(2)
        per_etichetta = nuovi.setdefault(etichetta, {})
        if numero not in per_etichetta:
            per_etichetta[numero] = len(per_etichetta) + 1
        return f"{{{{{etichetta}_{per_etichetta[numero]}}}}}"

    return _RE_SEGNAPOSTO_MARCATO.sub(_assegna, testo)


# I campi booleani esposti da form, JSON e profili, con il loro valore
# predefinito. Tenerli in un posto solo evita che l'interfaccia e il motore
# vadano fuori sincrono quando se ne aggiunge uno.
# I pacchetti nazionali, come interruttori. Il nucleo non c'e': vale
# ovunque e non si spegne, spegnerlo vorrebbe dire rinunciare a IBAN e
# carte su qualunque documento.
#
# Sono campi separati da FIELD_DEFAULTS perche' rispondono a una domanda
# diversa: quelli dicono *quali dati* nascondere, questi *di quale Paese*.
# Un utente puo' volere tutti i riconoscitori accesi su documenti solo
# italiani, o solo gli indirizzi su documenti di due Paesi.
PACK_FIELD_DEFAULTS: dict[str, bool] = {
    IT: True,
    EN: True,
    # Spento: vedi `ATTI`. Un pacchetto che capovolge una scelta gia' presa
    # non puo' accendersi da solo.
    ATTI: False,
}


def _pacchetti_da(flag) -> tuple[str, ...]:
    """Costruisce la tupla dei pacchetti dai loro interruttori.

    Sono **tre** — italiano, anglosassone, atti — e la docstring diceva «due»
    da quando il terzo e' arrivato: un commento che conta male e' il primo
    posto in cui si smette di credere ai commenti.
    """
    scelti = [p for p, d in PACK_FIELD_DEFAULTS.items() if flag("privacy_pack_" + p, d)]
    return (CORE, *scelti)


def prosa_da(valore) -> bool | None:
    """«prosa», «modulo» o vuoto -> True, False, None.

    Tre stati e non due: «non lo so» e' una risposta diversa da «e' un
    modulo», anche se oggi portano allo stesso comportamento. Il giorno in
    cui la stima automatica migliorasse, un booleano avrebbe gia' buttato
    via l'informazione che serve per accorgersene.
    """
    v = (str(valore) if valore is not None else "").strip().lower()
    if v in ("prosa", "prose", "lettera", "true", "1"):
        return True
    if v in ("modulo", "form", "false", "0"):
        return False
    return None


FIELD_DEFAULTS: dict[str, bool] = {
    "emails": True,
    "phones": True,
    "names": True,
    "fiscal": True,
    # Acceso, ma i suoi passi vivono nel pacchetto `ATTI` che e' **spento**:
    # l'interruttore dice *quale dato*, il pacchetto dice *per quale
    # mestiere*, e finche' il secondo e' spento questo non fa niente. Sta
    # qui lo stesso perche' e' un interruttore vero: deve comparire in
    # `no_redaction()` e nell'interfaccia come tutti gli altri.
    "atti": True,
    # Acceso, ma non sostituisce **mai**: segnala e basta. Spegnerlo non
    # rende il documento piu' pulito, lo rende piu' silenzioso.
    "quasi_id": True,
    "amounts": False,
    "urls": True,
    "addresses": True,
    "secrets": True,
    "dates": False,
    "documenti": True,
}

# Ogni campo qui e' un riconoscitore. Finche' c'e' stata `name_guess` non
# era vero -- non era un riconoscitore, era un modo di riconoscere i nomi --
# e questa tupla esisteva per escluderla. Ritirata quella nella 1.13.0, le
# due cose coincidono: se un giorno tornassero a divergere, il filtro va
# rimesso qui e non aggirato a valle.
DETECTOR_FIELDS: tuple[str, ...] = tuple(FIELD_DEFAULTS)

# Le categorie che il motore sa nominare: sono le chiavi di `counts`, cioe'
# il vocabolario con cui il rapporto parla gia' all'utente. `segnala` usa
# questo e non `FIELD_DEFAULTS` perche' rispondono a due domande diverse, e
# con due granularita' diverse:
#
#   * l'interruttore dice **se cercare**, per famiglia (`fiscal` copre CF,
#     partita IVA, IBAN e carte insieme);
#   * `segnala` dice **cosa fare di cio' che si trova**, per categoria --
#     ed e' proprio la finezza che serve: «lasciami gli IBAN in chiaro ma
#     togli i codici fiscali» non si puo' dire con l'interruttore.
#
# L'elenco e' scritto a mano e **verificato da un test** contro i nomi che
# il motore emette davvero (`tests/test_rileva_senza_sostituire.py`): un
# elenco del genere tenuto allineato a mano invecchia al primo
# riconoscitore nuovo, e un nome mancante qui vorrebbe dire che quella
# categoria non si puo' mettere in «segnala» -- in silenzio.
CATEGORIE: tuple[str, ...] = (
    "abn", "addresses", "amounts", "bban", "cards", "catasto",
    # `eta` e `genere` NON stanno qui, ed e' giusto cosi': non sono mai
    # chiavi di `counts`, perche' non c'e' nessun percorso che le sostituisca.
    # Vivono in `detected_counts`, che e' un altro conto e un'altra frase.
    # Metterle qui offrirebbe una casella «segnala anziche' sostituire» che
    # non e' attaccata a niente.
    "codice_fiscale", "dates", "documenti", "emails", "iban", "itin", "mrz",
    "names", "nhs_number", "nino", "partita_iva", "phones", "pratica",
    "routing_number", "secrets", "sin", "ssn", "targa", "termini", "tfn",
    "urls",
)


def categorie_da(valore) -> tuple[str, ...]:
    """Legge l'elenco delle categorie da «rileva ma non sostituire».

    Un nome sconosciuto **non passa in silenzio**. Un refuso -- `email` per
    `emails` -- produrrebbe altrimenti un'opzione che sembra impostata e non
    fa niente: l'utente crede di aver lasciato in chiaro gli indirizzi, il
    documento esce redatto lo stesso, e non c'e' nessun segnale. E' la
    stessa ragione per cui `only()` rifiuta i riconoscitori inesistenti.
    """
    if valore is None:
        return ()
    if isinstance(valore, (list, tuple)):
        nomi = [str(v) for v in valore]
    else:
        nomi = [p for p in re.split(r"[\s,;]+", str(valore)) if p]

    fuori: list[str] = []
    ignoti: list[str] = []
    for n in nomi:
        n = n.strip().lower()
        if not n:
            continue
        if n not in CATEGORIE:
            ignoti.append(n)
        elif n not in fuori:
            fuori.append(n)
    if ignoti:
        raise ValueError(
            "categorie inesistenti: " + ", ".join(sorted(ignoti))
            + ". Quelle valide sono: " + ", ".join(CATEGORIE)
        )
    return tuple(fuori)


def no_redaction() -> PrivacyOptions:
    """Tutti i riconoscitori spenti.

    Serve un modo solo di dirlo. Elencare i campi a mano nel punto in cui
    servono significa che il giorno in cui se ne aggiunge uno quel punto
    resta indietro — e siccome i valori predefiniti sono accesi, il difetto
    si manifesta come una redazione che avviene quando non dovrebbe.

    `numerati` e' nominato a mano, ed e' l'unica eccezione: non e' un
    riconoscitore -- non decide **se** togliere qualcosa, ma **come** si
    scrive cio' che e' stato tolto -- quindi non sta in `FIELD_DEFAULTS`.
    Spegnerlo qui non cambia niente (senza redazione non c'e' niente da
    numerare) e tiene vera l'invariante che il test verifica: dopo
    `no_redaction()` nessun interruttore booleano e' acceso. Vale la pena
    perche' quell'invariante e' cio' che accorge di un riconoscitore nuovo
    dimenticato qui dentro.
    """
    return PrivacyOptions(
        **{k: False for k in FIELD_DEFAULTS}, numerati=False, names_alone=False
    )


def only(*fields: str) -> PrivacyOptions:
    """Solo i riconoscitori indicati, tutti gli altri spenti.

    Costruire ``PrivacyOptions`` elencando i campi da spegnere sembra
    equivalente e non lo e': i campi non nominati restano accesi, e un test
    che crede di isolare un riconoscitore ne sta misurando cinque.
    """
    unknown = set(fields) - set(FIELD_DEFAULTS)
    if unknown:
        raise ValueError(f"riconoscitori inesistenti: {sorted(unknown)}")
    return PrivacyOptions(**{k: (k in fields) for k in FIELD_DEFAULTS})


def segnala_da_form(form) -> tuple[str, ...]:
    """Le categorie da «rileva ma non sostituire», come le manda la pagina.

    Due strade, e servono tutte e due: una casella per categoria
    (`privacy_segnala_iban=on`), che e' quello che fa l'interfaccia, e un
    campo unico con i nomi separati (`privacy_segnala=iban,amounts`), che e'
    quello che serve a chi chiama l'API da uno script senza doversi
    inventare venti campi.
    """
    if not hasattr(form, "get"):
        return ()
    dal_campo = list(categorie_da(form.get("privacy_segnala")))
    for c in CATEGORIE:
        val = form.get("privacy_segnala_" + c)
        if val is None:
            continue
        acceso = val if isinstance(val, bool) else str(val).lower() in ("1", "true", "yes", "on")
        if acceso and c not in dal_campo:
            dal_campo.append(c)
    return tuple(dal_campo)


def options_from_form(form) -> PrivacyOptions:
    """Build PrivacyOptions from Flask request.form (or dict-like)."""
    def flag(key: str, default: bool) -> bool:
        if key not in form:
            return default
        val = form.get(key)
        if isinstance(val, bool):
            return val
        return str(val).lower() in ("1", "true", "yes", "on")

    # Master switch. Fail-safe: an API client that omits the field gets the
    # redactions, it never gets plaintext PII by accident (same default as the CLI).
    if not flag("privacy_filter", True):
        return no_redaction()

    return PrivacyOptions(
        pacchetti=_pacchetti_da(flag),
        prosa=prosa_da(form.get("privacy_stile") if hasattr(form, "get") else None),
        sempre=termini_da(form.get("privacy_sempre") if hasattr(form, "get") else None),
        mai=termini_da(form.get("privacy_mai") if hasattr(form, "get") else None),
        segnala=segnala_da_form(form),
        # Nominato a mano: non e' un riconoscitore, quindi non sta in
        # `FIELD_DEFAULTS` (vedi `no_redaction`). Il valore predefinito e'
        # quello della dataclass, non `True` scritto qui: uno solo dei due
        # posti puo' essere la verita'.
        numerati=flag("privacy_numerati", PrivacyOptions.numerati),
        # Come `numerati`: non e' un riconoscitore -- non dice *quale dato*
        # cercare, dice quanta prova serve su un dato che il motore trova
        # gia' -- quindi non sta in `FIELD_DEFAULTS` e va nominata qui.
        names_alone=flag("privacy_names_alone", PrivacyOptions.names_alone),
        **{k: flag("privacy_" + k, d) for k, d in FIELD_DEFAULTS.items()},
    )


def options_from_dict(data: dict | None) -> PrivacyOptions:
    data = data or {}
    if not data.get("privacy_filter", True):
        return no_redaction()
    return PrivacyOptions(
        pacchetti=_pacchetti_da(lambda k, d: bool(data.get(k, d))),
        prosa=prosa_da(data.get("privacy_stile")),
        sempre=termini_da(data.get("privacy_sempre")),
        mai=termini_da(data.get("privacy_mai")),
        segnala=categorie_da(data.get("privacy_segnala")),
        numerati=bool(data.get("privacy_numerati", PrivacyOptions.numerati)),
        names_alone=bool(
            data.get("privacy_names_alone", PrivacyOptions.names_alone)
        ),
        **{k: bool(data.get("privacy_" + k, d)) for k, d in FIELD_DEFAULTS.items()},
    )
