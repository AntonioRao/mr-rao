# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""**Dove** stava, nel testo di partenza, ogni cosa che il motore ha tolto.

Il motore restituisce il testo redatto, non le posizioni. Chi deve intervenire
sul documento originale -- togliere i glifi da un PDF, rimettere i separatori
in un nome di file -- ha bisogno degli indici, e ricavarli e' un lavoro a se'.

Perche' e' un modulo suo
------------------------

Questo codice e' nato dentro `redazione_pdf.py` e ci e' rimasto finche' il PDF
e' stato l'unico a chiederlo. Il secondo chiamante -- il nome del file, che va
redatto conservando i suoi `_` e `.` -- avrebbe voluto una copia, e in un
motore di redazione **due copie sono una divergenza in attesa di succedere**:
si correggono le ancore da una parte, l'altra continua a tagliare male, e il
sintomo e' un dato che resta in mezzo a un documento che si chiama «redatto».

Qui dentro non c'e' nessuna decisione su cosa sia un dato personale: quella la
prende `apply_privacy_filter`, e si chiama da qui. C'e' solo l'allineamento fra
il prima e il dopo.

Prodotto: Mr. Rao. © Antonio Andrea Rao.
"""

from __future__ import annotations

import re

from mr_rao.privacy import PrivacyOptions, apply_privacy_filter

#: Sotto questa lunghezza un frammento non si cerca: troppo corto per dire
#: qualcosa, e cercarlo produce riscontri per caso.
MINIMO_CERCABILE = 3

#: Quante occorrenze di un'ancora si provano prima di arrendersi alla prima.
#: Oltre questo numero il testo e' fatto di ancore ripetute, e insistere costa
#: piu' di quanto renda.
ANCORE_DA_PROVARE = 12


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
        posizione = _ancora(testo, pezzo, cursore, in_attesa, opzioni)
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


def _ancora(testo: str, pezzo: str, da: int, in_attesa: str,
            opzioni: PrivacyOptions) -> int:
    """Dove ricomincia il testo copiato, dopo un valore tolto.

    **La prima occorrenza non basta, e costava una fuga.** Su
    «Scrivi a mario.rossi@example.it.» l'ancora dopo l'e-mail e' un punto
    solo, e il primo punto sta *dentro* l'e-mail: il tratto da tagliare
    diventava «mario», e nel PDF redatto restava
    `{{EMAIL_1}}.rossi@example.it`. La verifica non poteva accorgersene,
    perche' cerca il valore **intero** e quello, spezzato, non c'e' piu'.

    Qui si provano le prime occorrenze e si prende la prima che regge una
    domanda in piu': **il pezzo che verrebbe tagliato e' davvero quel dato?**
    Lo si chiede al motore, che e' l'unico a saperlo. Se nessuna regge -- un
    recapito che si riconosce solo dal contesto, per esempio, da solo non si
    riconosce piu' -- si torna alla prima, cioe' al comportamento di prima:
    questa e' una rete, non un cambio di regola.
    """
    if not in_attesa:
        # Nessun valore tolto in mezzo: l'ancora comincia esattamente qui.
        return da if testo.startswith(pezzo, da) else testo.find(pezzo, da)

    prima = testo.find(pezzo, da)
    if prima < 0:
        return -1
    posizione = prima
    for _ in range(ANCORE_DA_PROVARE):
        if posizione > da and _valore_coerente(testo[da:posizione], in_attesa, opzioni):
            return posizione
        successiva = testo.find(pezzo, posizione + 1)
        if successiva < 0:
            break
        posizione = successiva
    return prima


def _valore_coerente(valore: str, segnaposto: str, opzioni: PrivacyOptions) -> bool:
    """Il motore, rimesso davanti a quel solo pezzo, ci rivede lo stesso dato?

    Serve a scegliere fra due allineamenti possibili, non a decidere se un
    dato e' un dato: chiede se il pezzo candidato, da solo, viene sostituito
    **per intero** e con la **stessa etichetta**.
    """
    valore = valore.strip()
    if not valore:
        return False
    fuori, rapporto = apply_privacy_filter(valore, opzioni)
    if rapporto.total != 1:
        return False
    senza_numero = re.sub(r"\{\{([A-Z_]+?)(?:_\d+)?\}\}", r"{{\1}}", fuori).strip()
    atteso = re.sub(r"\{\{([A-Z_]+?)(?:_\d+)?\}\}", r"{{\1}}", segnaposto)
    return senza_numero == atteso


#: I caratteri che in un nome di file fanno le veci dello spazio.
#: `Rossi_Mario_referto.pdf` e' una frase scritta senza spazi, e il motore --
#: che legge testo, non nomi di file -- non ci vede nessun nome finche' non
#: glieli si mette. Misurato: con gli underscore, zero sostituzioni; con gli
#: spazi, `{{NAME_1}}`.
SEPARATORI_NOME = "_-."


def redigi_nome_file(nome: str, opzioni: PrivacyOptions) -> str:
    """Il nome di un file, redatto **conservando i suoi separatori**.

    Serve dove il nome entra *dentro* un documento che viene consegnato: la
    riga `source:` del frontmatter e le intestazioni del merge. Non tocca il
    file su disco, che e' dell'utente.

    Come funziona, e perche' cosi'
    ------------------------------

    I separatori diventano spazi **uno per uno**, quindi la versione che il
    motore legge ha esattamente la stessa lunghezza dell'originale e gli indici
    combaciano. Si chiedono a `intervalli_da_togliere` le posizioni, e si
    riportano sul nome vero: cosi' `Rossi_Mario_referto.pdf` diventa
    `{{NAME_1}}_referto.pdf` e non `{{NAME_1}} referto pdf`.

    L'estensione resta sempre: dice come leggere il file, e non e' di nessuno.
    """
    if not nome:
        return nome
    punto = nome.rfind(".")
    # Solo un'estensione vera: un punto in coda o all'inizio non lo e'.
    if 0 < punto < len(nome) - 1:
        radice, estensione = nome[:punto], nome[punto:]
    else:
        radice, estensione = nome, ""

    tavola = {ord(c): " " for c in SEPARATORI_NOME}
    leggibile = radice.translate(tavola)
    tratti = intervalli_da_togliere(leggibile, opzioni)
    if not tratti:
        return nome

    fuori: list[str] = []
    cursore = 0
    for inizio, fine, segnaposto in tratti:
        fuori.append(radice[cursore:inizio])
        fuori.append(segnaposto)
        cursore = fine
    fuori.append(radice[cursore:])
    return "".join(fuori) + estensione
