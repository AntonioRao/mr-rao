"""Il pacchetto «atti e pratiche»: spento di serie, e non e' un ripiego.

Perche' esiste, e perche' e' spento
-----------------------------------

Qui c'e' una divergenza vera fra due pubblici, e hanno ragione tutti e due.

Per un notaio il riferimento catastale **e' il dato piu' sensibile della
frase**: dice esattamente di quale immobile si parla, e da un foglio e una
particella si arriva al proprietario in un pomeriggio.

Per un'azienda il numero di protocollo e' cio' che permette di **ritrovare**
la pratica, e toglierlo rende il documento inservibile senza proteggere
nessuno. Non e' un caso che «protocollo» e «repertorio» stiano gia' nel
vocabolario di cio' che **non** si redige: e' quello che impedisce a ogni
numero di pratica di essere letto come un telefono.

Questo pacchetto **capovolge** quella scelta. Una cosa cosi' non si accende
di serie: si accende da chi sa di volerla.

Due assi, non uno
-----------------

L'interruttore `atti` dice *quale dato*, il pacchetto `ATTI` dice *per quale
mestiere*. Servono tutti e due, ed e' la stessa forma dei pacchetti
nazionali. L'interruttore e' acceso e il pacchetto spento: chi accende il
pacchetto ottiene subito qualcosa, chi spegne l'interruttore lo spegne
comunque.

Tutti i valori sono inventati.
"""

from __future__ import annotations

import pytest

from mr_rao.privacy import (
    ATTI,
    CORE,
    EN,
    IT,
    PACK_FIELD_DEFAULTS,
    PrivacyOptions,
    apply_privacy_filter,
    senza_numeri,
)

ACCESO = (CORE, IT, EN, ATTI)


def redigi(testo: str, pacchetti=None, **kw) -> str:
    opzioni = PrivacyOptions(pacchetti=pacchetti or (CORE, IT, EN), **kw)
    return senza_numeri(apply_privacy_filter(testo, opzioni)[0])


# ------------------------------------------------- il pacchetto e' spento


def test_di_serie_il_pacchetto_e_spento() -> None:
    """La riga che tiene la decisione.

    Se un domani qualcuno lo accendesse «per simmetria» con gli altri due,
    ogni numero di pratica comincerebbe a sparire dai documenti aziendali —
    e nessun altro test se ne accorgerebbe, perche' tutti gli altri girano
    con i pacchetti predefiniti.
    """
    assert PACK_FIELD_DEFAULTS[ATTI] is False
    assert PACK_FIELD_DEFAULTS[IT] is True and PACK_FIELD_DEFAULTS[EN] is True


def test_col_pacchetto_spento_il_catastale_resta() -> None:
    testo = "Immobile identificato al foglio 12 particella 345 sub 6."
    assert redigi(testo) == testo


def test_l_interruttore_da_solo_non_basta() -> None:
    """`atti=True` e' il valore di serie: se bastasse quello, il pacchetto
    non servirebbe a niente e la decisione sarebbe stata aggirata."""
    testo = "Immobile al foglio 12 particella 345."
    assert redigi(testo, atti=True) == testo


# ------------------------------------------------------ acceso, funziona


@pytest.mark.parametrize(
    "frase",
    [
        "Immobile identificato al foglio 12 particella 345 sub 6 in Pisa.",
        "Bene censito al Fg. 245 mapp. 2752 subalterno 52",
        "Riferimento: F. 8 part. 1290",
        "foglio 12, particella 345",
    ],
)
def test_col_pacchetto_acceso_il_catastale_sparisce(frase: str) -> None:
    fuori = redigi(frase, pacchetti=ACCESO)
    assert "{{CATASTO}}" in fuori, fuori


def test_lo_spegne_anche_l_interruttore() -> None:
    """Due assi: chi accende il pacchetto ma spegne l'interruttore non deve
    ottenere niente. Senza questo, `atti=False` sarebbe decorativo."""
    testo = "Immobile al foglio 12 particella 345."
    assert redigi(testo, pacchetti=ACCESO, atti=False) == testo


# ------------------------------------------------ e cosa NON deve prendere


@pytest.mark.parametrize(
    "frase",
    [
        # Il foglio da solo e' la pagina di una relazione.
        "Vedi il foglio 3 della relazione tecnica",
        "Come da foglio 12 allegato",
        # La particella senza il foglio davanti.
        "particella 345 senza foglio davanti",
        # Due numeri lontani: in una tabella catastale le colonne sono
        # «Fg. | Part.», e con una finestra larga si prenderebbero due celle
        # di righe diverse.
        "foglio 12\n\n\nAltro paragrafo\n\nparticella 345",
    ],
)
def test_quello_che_non_e_un_catastale_resta(frase: str) -> None:
    assert "{{CATASTO}}" not in redigi(frase, pacchetti=ACCESO), frase


def test_e_raggiungibile_dall_interfaccia() -> None:
    """Parita' GUI: un pacchetto che si puo' accendere solo dall'API e'
    una funzione che per chi usa il programma non esiste."""
    from mr_rao.app_factory import create_app

    app = create_app()
    app.config["TESTING"] = True
    pagina = app.test_client().get("/", base_url="http://127.0.0.1:5000").get_data(as_text=True)
    assert 'id="privacy-pack_atti"' in pagina
    assert 'id="privacy-atti"' in pagina
    # E **senza** `checked`: la casella del pacchetto dev'essere spenta.
    pezzo = pagina.split('id="privacy-pack_atti"')[1][:40]
    assert "checked" not in pezzo, pezzo
