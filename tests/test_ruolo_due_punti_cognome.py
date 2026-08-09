"""«Il Ministro: GIORGETTI» — un ruolo, due punti, e un cognome solo.

E' la forma con cui si firmano gli atti pubblici italiani, e fino alla
1.16.0 non la vedeva nessuna regola: il riconoscitore a coppie pretende
**due** parole maiuscole adiacenti, e qui la parola e' una. Contata sulle
dodici Gazzette Ufficiali del corpus pubblico: **107 occorrenze** intatte —
GIORGETTI, NORDIO, PIANTEDOSI, LOLLOBRIGIDA, IACOVONI, NISTICO'.

Gli elenchi qui non servono, ed e' il dato che ha deciso il disegno: dei
114 cognomi trovati in quella forma, **28** stanno nei nostri elenchi.
Pretendere il riscontro avrebbe lasciato passare gli altri 86. Cio' che
decide e' il **ruolo davanti ai due punti**.

Nemmeno un modello lo prendeva: l'indagine P3.6 aveva misurato un NER da
64 MiB su questa stessa forma, 3 casi su 42. Non e' una questione di quanto
sa un modello — il segnale sta nella punteggiatura, e una regola da due
righe ci arriva dove un modello da sessantaquattro megabyte non arriva.

Le tre guardie qui sotto non sono state immaginate: ognuna nasce da un falso
positivo visto sul corpus.
"""
from __future__ import annotations

import pytest

from mr_rao.privacy import PrivacyOptions, apply_privacy_filter


def _redigi(testo: str) -> str:
    return apply_privacy_filter(testo, PrivacyOptions())[0]


@pytest.mark.parametrize("testo,cognome", [
    ("Roma, 30 luglio 2022\nIl Ministro: GIORGETTI", "GIORGETTI"),
    ("Il direttore generale del Tesoro: IACOVONI", "IACOVONI"),
    ("Il Guardasigilli: NORDIO", "NORDIO"),
    ("Il Ministro dell’interno: PIANTEDOSI", "PIANTEDOSI"),
    ("Il Commissario straordinario: FIGLIUOLO", "FIGLIUOLO"),
    ("Il Ragioniere generale dello Stato: MAZZOTTA", "MAZZOTTA"),
    ("Il Capo del Dipartimento: CURCIO", "CURCIO"),
    ("Il presidente: NISTICÒ", "NISTICÒ"),
    ("Il dirigente: TROTTA", "TROTTA"),
    ("Il rettore: SCHILLACI", "SCHILLACI"),
])
def test_il_cognome_dopo_il_ruolo_viene_tolto(testo, cognome):
    fuori = _redigi(testo)
    assert "{{NAME}}" in fuori, testo
    assert cognome not in fuori, fuori


def test_nessuno_di_questi_cognomi_e_negli_elenchi():
    """La ragione per cui la regola non chiede il riscontro.

    Se questo test cadesse perche' gli elenchi sono cresciuti, non e' un
    guasto — ma va riletto il disegno: la regola vale **perche'** gli
    elenchi qui non arrivano, e quel giorno la scelta andrebbe rifatta con
    i numeri nuovi.
    """
    from mr_rao.it_names import SURNAMES
    fuori = [c for c in ("giorgetti", "iacovoni", "nordio", "piantedosi",
                         "lollobrigida") if c not in SURNAMES]
    assert len(fuori) >= 4, (
        f"solo {5 - len(fuori)} di questi cognomi mancava dagli elenchi: "
        "vedi il docstring")


# --- le tre guardie, ognuna da un falso positivo vero ------------------------

@pytest.mark.parametrize("testo", [
    "Responsabile: SETTORE TECNICO",
    "Direttore: UFFICIO ACQUISTI",
    "Responsabile: AREA GESTIONE",
    "Dirigente: SERVIZIO ANAGRAFE",
])
def test_le_etichette_dei_campi_non_sono_persone(testo):
    """Su un modulo la stessa forma e' l'intestazione di un campo. E' il
    modo in cui questa regola puo' fare piu' danni, e per questo il valore
    deve essere fatto di parole che italiane non sono."""
    assert "{{NAME}}" not in _redigi(testo), testo


def test_la_virgola_dice_che_i_due_punti_non_sono_del_ruolo():
    """«Responsabile della protezione dei dati, all'indirizzo: INPS»: il
    ruolo c'e', ma i due punti sono di «indirizzo». Quattro occorrenze sui
    moduli in bianco, dove l'atteso e' zero."""
    testo = "Responsabile della protezione dei dati, all’indirizzo: INPS"
    assert "{{NAME}}" not in _redigi(testo)


def test_il_cognome_non_attraversa_l_a_capo():
    """Senza il vincolo di riga si prendeva «IACHINO\\nMINISTERO DELLA»:
    il cognome piu' l'intestazione della sezione dopo."""
    fuori = _redigi("Il direttore generale: IACHINO\nMINISTERO DELLA SALUTE")
    assert "{{NAME}}" in fuori
    assert "MINISTERO DELLA SALUTE" in fuori, fuori


def test_il_titolare_di_una_autorizzazione_non_e_una_persona():
    """«Il titolare A.I.C.: DOC Generici» — nelle Gazzette il titolare di
    un'autorizzazione all'immissione in commercio e' un'azienda. Per questo
    «titolare» non sta fra i ruoli."""
    assert "{{NAME}}" not in _redigi("Il titolare A.I.C.: DOC Generici")


def test_serve_il_maiuscolo():
    """Il maiuscolo e' il terzo segnale, non un dettaglio: in un atto
    firmato il cognome sta in maiuscolo perche' e' una firma. Chiederlo
    costa un richiamo che non abbiamo mai avuto, invece di aprire la porta
    a «Il presidente: Vedi allegato»."""
    assert "{{NAME}}" not in _redigi("Il presidente: Vedi allegato")
