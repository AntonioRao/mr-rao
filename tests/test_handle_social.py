# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Il nome utente preceduto da `@`: `(@mariorossi)`.

## Come e' saltato fuori

Convertendo con Mr. Rao il rapporto tecnico di `rizzo-pii`, il 7 settembre
2026. L'ultima pagina elenca i contributori cosi':

    Alessandro Betti (@bettialessandro), Renato ... (@Renaad), ...

I nomi sono stati redatti. **Gli handle no**, nessuno dei due prodotti li
riconosce, e un handle e' un identificativo diretto: porta a un profilo con
foto, luogo di lavoro e cronologia. Redigere il nome e lasciare `@bettialessandro`
accanto e' peggio che non redigere niente, perche' il documento **sembra**
trattato.

## La regola, e cosa costa

Non c'e' checksum e non c'e' vocabolario: `@` seguito da parola e' anche il
decoratore di ogni linguaggio (`@property`, `@Override`) e la regola di ogni
foglio di stile (`@media`, `@import`). Un elenco di parole da saltare sarebbe
da aggiornare per sempre e sbaglierebbe comunque.

La forma li separa meglio di un elenco: **un decoratore apre la riga, un
handle sta dentro una frase**. Quindi si redige un `@nome` solo quando prima,
sulla stessa riga, c'e' gia' qualcosa — una parola, una parentesi, due punti.

Il prezzo e' dichiarato: un handle a inizio riga resta in chiaro. E' il caso
del post copiato («@mariorossi ha scritto...»), non quello dei documenti che
questo programma converte, dove gli handle stanno in elenchi e recapiti.

Si escludono anche le forme con un punto (`@app.route`, `@example.com`): un
nome utente non ne contiene, un decoratore qualificato e un dominio si'.

Tutti i valori sono inventati.
"""

from __future__ import annotations

from mr_rao.privacy import PrivacyOptions, apply_privacy_filter


def _redigi(testo: str, **opzioni) -> str:
    fuori, _ = apply_privacy_filter(testo, PrivacyOptions(**opzioni))
    return fuori


# ------------------------------------------------------------ cosa si redige


def test_handle_fra_parentesi_dopo_un_nome():
    """Il caso da cui e' nato tutto."""
    fuori = _redigi("Hanno contribuito Alessandro Betti (@bettialessandro) e "
                    "Marco Verdi (@Renaad).")
    assert "@bettialessandro" not in fuori
    assert "@Renaad" not in fuori
    assert "{{HANDLE_1}}" in fuori and "{{HANDLE_2}}" in fuori


def test_handle_dopo_una_parola_di_contesto():
    fuori = _redigi("Scrivimi su @mariorossi oppure su Telegram: @mrossi_74.")
    assert "@mariorossi" not in fuori
    assert "@mrossi_74" not in fuori


def test_lo_stesso_handle_prende_lo_stesso_numero():
    """Come per ogni altro dato: due volte lo stesso profilo, un solo numero."""
    fuori = _redigi("Ne parlano @mariorossi e @annaverdi; poi @mariorossi risponde.")
    assert fuori.count("{{HANDLE_1}}") == 2
    assert "{{HANDLE_2}}" in fuori


def test_lo_spegnimento_lo_lascia_in_chiaro():
    """Un interruttore che non spegne niente e' peggio di nessun interruttore."""
    fuori = _redigi("Contatto (@mariorossi).", handle=False)
    assert "@mariorossi" in fuori


# ------------------------------------------------------- cosa NON si redige


def test_un_decoratore_a_inizio_riga_non_si_tocca():
    """La riga che rende la regola utilizzabile su documenti tecnici."""
    testo = "Esempio:\n@property\n    @staticmethod\n@Override\n@media print"
    fuori = _redigi(testo)
    assert fuori == testo, f"toccato del codice: {fuori!r}"


def test_una_forma_col_punto_non_e_un_handle():
    """`@app.route` e `@example.com`: un nome utente non contiene punti."""
    testo = "Vedi @app.route e la posta @example.com nel manuale."
    fuori = _redigi(testo, emails=False)
    assert "@app.route" in fuori
    assert "@example.com" in fuori


def test_l_indirizzo_di_posta_non_diventa_un_handle():
    """L'email si redige come email, non come handle piu' resto."""
    fuori = _redigi("Scrivere a mario.rossi@example.it per informazioni.")
    assert "{{EMAIL_1}}" in fuori
    assert "HANDLE" not in fuori, f"l'email e' stata smontata: {fuori!r}"


def test_un_decoratore_nominato_dentro_una_frase_non_si_tocca():
    """Il caso che la regola della riga non vede.

    Trovato dalla batteria dal vivo del 7 settembre 2026: «Nota @property qui»
    usciva «Nota {{HANDLE_1}} qui». In un manuale tecnico un decoratore
    nominato dentro una frase e' frequente quanto uno che apre la riga, e la
    forma li' non aiuta — `Nota @property qui` e `Scrivimi su @mariorossi`
    hanno la stessa forma.

    Da qui l'elenco delle parole riservate, che **completa** la regola della
    riga invece di sostituirla: copre solo cio' che la forma non separa.
    """
    testo = ("Vedi @property e @staticmethod nel manuale; la regola @media "
             "vale per la stampa, e @Override in Java.")
    assert _redigi(testo) == testo, f"decoratori redatti: {_redigi(testo)!r}"


def test_l_elenco_riservato_non_copre_i_nomi_veri():
    """La riga che impedisce di allargare l'elenco fino a spegnere tutto."""
    fuori = _redigi("Contributori: Alessandro Betti (@bettialessandro), "
                    "Marco (@marco_rossi), Anna (@annav).")
    for handle in ("@bettialessandro", "@marco_rossi", "@annav"):
        assert handle not in fuori, f"{handle} non redatto: {fuori!r}"


def test_una_chiocciola_isolata_non_basta():
    testo = "Prezzo: 3 @ 5 euro. Vedi @ab e @xy."
    fuori = _redigi(testo)
    assert fuori == testo, f"redatto qualcosa che non e' un handle: {fuori!r}"
