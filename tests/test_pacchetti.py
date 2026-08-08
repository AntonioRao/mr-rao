"""I pacchetti di riconoscitori: nucleo universale e formati italiani.

Fase 1 di #1. Prima esisteva un solo interruttore, ``fiscal``, e dentro
convivevano l'IBAN — mod-97, valido in tutti i Paesi SEPA — e il codice
fiscale, che esiste solo in Italia. Chi voleva usare Mr. Rao su un documento
straniero doveva prendersi anche i riconoscitori italiani, oppure rinunciare
pure all'IBAN.

Il banco golden (``test_golden_privacy.py``) dimostra che il comportamento
predefinito **non e' cambiato**. Questi test dimostrano l'altra meta': che
la separazione serve davvero a qualcosa, cioe' che scegliendo il solo
nucleo i riconoscitori italiani smettono di girare e gli altri no. Senza
questi, il refactoring avrebbe potuto lasciare `pacchetti` completamente
scollegato e il golden sarebbe rimasto verde lo stesso.
"""
from __future__ import annotations

import pytest

from mr_rao.privacy import (
    CORE,
    DETECTOR_FIELDS,
    IT,
    PACCHETTI_NOTI,
    SEQUENZA,
    PrivacyOptions,
    apply_privacy_filter,
)

# Un documento con dentro un dato universale e uno italiano, vicini.
TESTO = (
    "Codice fiscale RSSMRA85T10A562S, "
    "IBAN IT60X0542811101000000123456, "
    "carta 4111 1111 1111 1111."
)


# ---------------------------------------------------------------------------
# La sequenza e' coerente con se stessa
# ---------------------------------------------------------------------------


def test_ogni_passo_dichiara_un_pacchetto_noto():
    for passo in SEQUENZA:
        assert passo.pacchetto in PACCHETTI_NOTI, passo.nome


def test_ogni_passo_punta_a_un_campo_che_esiste():
    """Un campo scritto male non alzerebbe un errore: ``getattr`` fallisce
    a tempo di esecuzione, e solo per i documenti che passano di li'."""
    opts = PrivacyOptions()
    for passo in SEQUENZA:
        assert hasattr(opts, passo.campo), f"{passo.nome} -> {passo.campo}"
        assert isinstance(getattr(opts, passo.campo), bool), passo.nome


def test_i_nomi_dei_passi_sono_unici():
    nomi = [p.nome for p in SEQUENZA]
    assert len(nomi) == len(set(nomi)), sorted(nomi)


def test_ogni_interruttore_ha_almeno_un_passo():
    """Una casella nell'interfaccia che non accende niente e' una bugia."""
    coperti = {p.campo for p in SEQUENZA}
    scoperti = set(DETECTOR_FIELDS) - coperti
    assert not scoperti, f"interruttori senza riconoscitore: {sorted(scoperti)}"


def test_ogni_pacchetto_noto_ha_dei_passi():
    """Se la classificazione collassasse su un pacchetto solo, i test di
    selezione qui sotto passerebbero senza dimostrare niente. E un
    pacchetto dichiarato e vuoto sarebbe una voce nell'interfaccia che non
    fa nulla."""
    pacchetti = {p.pacchetto for p in SEQUENZA}
    assert pacchetti == set(PACCHETTI_NOTI)


# ---------------------------------------------------------------------------
# La selezione fa davvero qualcosa
# ---------------------------------------------------------------------------


def test_il_valore_predefinito_e_nucleo_piu_italiano():
    """E' il patto della fase 1: chi non tocca niente ha il motore di ieri."""
    assert PrivacyOptions().pacchetti == (CORE, IT)


def test_col_solo_nucleo_l_iban_e_la_carta_spariscono_lo_stesso():
    out, rep = apply_privacy_filter(TESTO, PrivacyOptions(pacchetti=(CORE,)))
    assert "{{IBAN}}" in out
    assert "{{CARD}}" in out
    assert rep.counts.get("iban") == 1
    assert rep.counts.get("cards") == 1


def test_col_solo_nucleo_il_codice_fiscale_resta():
    """Il punto di tutta la fase 1: i due riconoscitori erano legati, ora no."""
    out, rep = apply_privacy_filter(TESTO, PrivacyOptions(pacchetti=(CORE,)))
    assert "RSSMRA85T10A562S" in out
    assert "codice_fiscale" not in rep.counts


def test_col_pacchetto_italiano_il_codice_fiscale_sparisce():
    out, rep = apply_privacy_filter(TESTO, PrivacyOptions(pacchetti=(CORE, IT)))
    assert "RSSMRA85T10A562S" not in out
    assert rep.counts.get("codice_fiscale") == 1


def test_senza_nessun_pacchetto_non_succede_niente():
    """Il caso limite che vale la pena fissare: un elenco vuoto non deve
    ricadere silenziosamente sul comportamento predefinito."""
    out, rep = apply_privacy_filter(TESTO, PrivacyOptions(pacchetti=()))
    assert out == TESTO
    assert rep.total == 0


def test_il_sospetto_italiano_non_scatta_senza_il_pacchetto_italiano():
    """I sospetti sono comportamento quanto le sostituzioni: un motore che
    segnala codici fiscali a chi ha chiesto il solo nucleo sta parlando di
    una cosa che non sta cercando."""
    # Sedici caratteri con la proporzione di un codice fiscale, ma troppo
    # lontani dalla forma perche' il recupero OCR possa raddrizzarli: sono
    # necessarie piu' delle due correzioni ammesse. Un codice storpiato da
    # un carattere solo verrebbe *sostituito*, non segnalato, e il test
    # misurerebbe un'altra cosa.
    storpiato = "Da OCR: AB1CD2EF3GH4IJ5K"
    _, solo_core = apply_privacy_filter(storpiato, PrivacyOptions(pacchetti=(CORE,)))
    _, con_it = apply_privacy_filter(storpiato, PrivacyOptions(pacchetti=(CORE, IT)))
    assert not [s for s in solo_core.suspects if s["kind"] == "codice_fiscale"]
    assert [s for s in con_it.suspects if s["kind"] == "codice_fiscale"]


@pytest.mark.parametrize("pacchetti", [(CORE,), (CORE, IT), ()])
def test_filtrare_non_riordina(pacchetti):
    """Filtrare non deve riordinare: l'ordine e' il comportamento."""
    eseguiti = [
        p.nome
        for p in sorted(SEQUENZA, key=lambda p: p.priorita)
        if p.pacchetto in set(pacchetti)
    ]
    indici = [next(i for i, p in enumerate(SEQUENZA) if p.nome == n) for n in eseguiti]
    assert indici == sorted(indici)


def test_l_ordine_dichiarato_coincide_con_quello_eseguito():
    """SEQUENZA si legge dall'alto in basso, ma a decidere e' ``priorita``.

    Se le due cose divergessero, chiunque legga il file per capire l'ordine
    leggerebbe una cosa falsa -- ed e' il file dove l'ordine *e'* il
    comportamento. Meglio tenerli allineati e farlo dire a un test.
    """
    dichiarato = [p.nome for p in SEQUENZA]
    eseguito = [p.nome for p in sorted(SEQUENZA, key=lambda p: p.priorita)]
    assert dichiarato == eseguito


def test_le_priorita_rispettano_i_vincoli_che_contano():
    """Non l'ordine esatto -- i tre vincoli per cui quell'ordine esiste."""
    pr = {p.nome: p.priorita for p in SEQUENZA}
    # Gli URL prima delle email: un indirizzo dentro un link non deve
    # spezzare il link.
    assert pr["urls"] < pr["emails"]
    # I codici prima dei telefoni: una partita IVA e' undici cifre.
    assert max(pr["partita_iva"], pr["codice_fiscale"]) < pr["phones"]
    # I riconoscitori esatti prima di quelli tolleranti all'OCR.
    assert pr["codice_fiscale"] < pr["codice_fiscale_ocr"]
    assert pr["iban"] < pr["iban_ocr"]
    # I nomi per ultimi: i segnaposto gia' inseriti fanno da contesto.
    assert pr["names"] == max(pr.values())
