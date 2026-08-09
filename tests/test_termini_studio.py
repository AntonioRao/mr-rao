"""Le due liste dello studio (P1.8).

Il motore decide con regole generali, ma ogni studio ha nomi propri che
ricorrono in ogni pratica — clienti, controparti — e denominazioni interne
che non vanno toccate mai. Prima l'unica leva era spegnere un riconoscitore
intero: un martello per un chiodo.

Le due liste non sono simmetriche, ed e' la cosa che questi test devono
tenere ferma: «sempre» aggiunge un riconoscitore, «mai» mette il termine al
riparo da **tutti**, compresi quelli che non sapresti di dover spegnere.
"""
from __future__ import annotations

import io

import pytest

from mr_rao.app_factory import create_app
from mr_rao.privacy import (
    MAX_TERMINI,
    PrivacyOptions,
    apply_privacy_filter,
    termini_da,
)

BASE = "http://127.0.0.1:5000"


# --------------------------------------------------------------- il motore


def test_sempre_toglie_cio_che_le_regole_non_indovinano():
    testo = "La pratica di Rossi & Partners prosegue."
    out, rep = apply_privacy_filter(
        testo, PrivacyOptions(sempre=termini_da("Rossi & Partners"))
    )
    assert "Rossi & Partners" not in out
    assert "{{TERM}}" in out
    assert rep.counts.get("termini") == 1


def test_mai_protegge_da_ogni_riconoscitore():
    """Non da uno: da tutti.

    Chiedere a ciascun riconoscitore di consultare la lista lascerebbe
    scoperto quello che ci si dimentica di modificare — ed e' il genere di
    difetto che non si vede finche' non esce un dato.
    """
    for testo, termine in (
        ("Scrivi a info@studiolegale.it per la pratica", "info@studiolegale.it"),
        ("Sede legale in via Verdi 12, Milano", "via Verdi 12"),
        ("Il centralino e' 06 55512340", "06 55512340"),
        ("Partita IVA IT12345678903 della societa'", "IT12345678903"),
    ):
        senza = apply_privacy_filter(testo, PrivacyOptions())[0]
        assert termine not in senza, f"il banco non prova niente su {termine!r}"

        con, _ = apply_privacy_filter(testo, PrivacyOptions(mai=termini_da(termine)))
        assert termine in con, f"non protetto: {termine!r}"


def test_mai_vince_su_sempre():
    """Chi scrive «questo non toccarlo mai» dice una cosa piu' specifica."""
    out, rep = apply_privacy_filter(
        "Il progetto Sirio va avanti.",
        PrivacyOptions(sempre=termini_da("Sirio"), mai=termini_da("Sirio")),
    )
    assert "Sirio" in out
    assert not rep.counts.get("termini")


def test_un_termine_protetto_non_diventa_un_sospetto():
    """Segnalare a ogni conversione cio' che l'utente ha deciso di lasciare
    in chiaro e' rumore, non un avviso."""
    testo = "Il referente e' Dott. Nazzareno Sbrolli, come da incarico."
    _, rep = apply_privacy_filter(
        testo, PrivacyOptions(mai=termini_da("Nazzareno Sbrolli"))
    )
    assert not any(
        "Sbrolli" in str(s.get("sample", "")) for s in rep.suspects
    ), "il termine protetto e' finito fra i sospetti"


def test_il_termine_piu_lungo_vince():
    """Con «Rossi» prima di «Rossi & Partners» meta' termine resterebbe."""
    out, _ = apply_privacy_filter(
        "Atto di Rossi & Partners depositato.",
        PrivacyOptions(sempre=termini_da("Rossi\nRossi & Partners")),
    )
    assert "Partners" not in out


def test_maiuscole_indifferenti_e_parola_intera():
    out, rep = apply_privacy_filter(
        "ACME e acme sono la stessa cosa, ma acmeista no.",
        PrivacyOptions(sempre=termini_da("acme")),
    )
    assert rep.counts.get("termini") == 2
    assert "acmeista" in out, "una parola piu' lunga non va spezzata"


def test_il_termine_non_attraversa_il_ritorno_a_capo():
    """Stessa lezione dell'email offuscata (issue #3): uno spazio flessibile
    che ingoia la riga successiva toglie testo e tace."""
    testo = "Il cliente Rossi\nPartners ha scritto."
    out, _ = apply_privacy_filter(
        testo, PrivacyOptions(sempre=termini_da("Rossi Partners"))
    )
    assert out == testo


def test_il_termine_di_due_parole_regge_gli_spazi_del_documento():
    out, _ = apply_privacy_filter(
        "Il cliente Rossi   &\tPartners ha scritto.",
        PrivacyOptions(sempre=termini_da("Rossi & Partners")),
    )
    assert "Partners" not in out


# --------------------------------------------------------------- il parser


def test_termini_da_pulisce_la_lista():
    assert termini_da("  Alfa \n\n Beta\nalfa\n\n") == ("Alfa", "Beta")
    assert termini_da(None) == ()
    assert termini_da("a") == (), "un carattere solo sostituirebbe mezzo documento"
    assert termini_da(["Alfa", "Beta"]) == ("Alfa", "Beta")


def test_termini_da_mette_un_tetto():
    """Ogni termine e' un'alternativa in un'unica espressione regolare
    applicata a tutto il documento: un elenco senza freni la fa esplodere."""
    tanti = "\n".join(f"Termine{i}" for i in range(MAX_TERMINI + 50))
    assert len(termini_da(tanti)) == MAX_TERMINI


def test_una_virgola_non_spezza_il_termine():
    assert termini_da("Rossi, Bianchi & Co.") == ("Rossi, Bianchi & Co.",)


def test_un_termine_con_caratteri_speciali_non_e_una_regex():
    """Se il termine finisse dentro il pattern senza escape, un utente che
    scrive «S.p.A. (Roma)» otterrebbe un errore invece di una sostituzione."""
    out, rep = apply_privacy_filter(
        "La Alfa S.p.A. (Roma) partecipa.",
        PrivacyOptions(sempre=termini_da("Alfa S.p.A. (Roma)")),
    )
    assert rep.counts.get("termini") == 1
    assert "(Roma)" not in out


# ------------------------------------------------- la porta dell'interfaccia


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def converti(client, testo: bytes, **campi):
    campi["file"] = (io.BytesIO(testo), "nota.txt")
    r = client.post(
        "/api/convert/sync",
        data=campi,
        content_type="multipart/form-data",
        base_url=BASE,
        headers={"Origin": BASE},
    )
    assert r.status_code == 200, r.status_code
    return (r.get_json() or {}).get("markdown", "")


def test_le_liste_arrivano_al_motore_anche_col_profilo(client):
    """L'interfaccia manda **sempre** un profilo.

    E' il ramo che il pannello «Quali dati nascondere» percorreva senza
    comandare niente, prima del test di parita'. Le due caselle nuove devono
    passare da li' o sono decorative allo stesso modo.
    """
    md = converti(
        client,
        b"La pratica di Rossi & Partners prosegue.",
        profile="default",
        privacy_sempre="Rossi & Partners",
    )
    assert "{{TERM}}" in md
    assert "Rossi & Partners" not in md


def test_la_lista_mai_arriva_al_motore_col_profilo(client):
    md = converti(
        client,
        b"Scrivi a info@studiolegale.it per la pratica",
        profile="default",
        privacy_mai="info@studiolegale.it",
    )
    assert "info@studiolegale.it" in md, "la casella «non toccare mai» non comanda"


def test_a_filtro_spento_le_liste_non_tolgono_niente(client):
    """L'interruttore generale vince anche su «nascondi sempre».

    Chi spegne la redazione vuole il documento com'e'. Una lista che
    continuasse a mordere sarebbe una sostituzione che avviene quando
    l'utente ha detto di no — l'errore nella direzione peggiore.
    """
    md = converti(
        client,
        b"La pratica di Rossi & Partners prosegue.",
        profile="default",
        privacy_filter="false",
        privacy_sempre="Rossi & Partners",
    )
    assert "Rossi & Partners" in md
    assert "{{TERM}}" not in md


def test_senza_le_caselle_non_cambia_niente(client):
    md = converti(client, b"Scrivi a mario.rossi@example.it", profile="default")
    assert "{{EMAIL}}" in md


# ------------------------------------------------------------ parita' GUI


def test_le_due_caselle_esistono_nella_pagina(client):
    """Parita' GUI: configurabile dall'interfaccia, non solo da riga di
    comando. Il motore puo' saperlo fare quanto vuole — se la casella non
    c'e', la funzione non esiste per chi usa il programma."""
    pagina = client.get("/", base_url=BASE).get_data(as_text=True)
    for campo in ("privacy-sempre", "privacy-mai"):
        assert f'id="{campo}"' in pagina, f"manca la casella {campo}"


def test_il_javascript_manda_le_due_caselle():
    from pathlib import Path

    js = Path("static/js/app.js").read_text(encoding="utf-8")
    for chiave in ("privacy_sempre", "privacy_mai"):
        assert chiave in js, f"il modulo non manda {chiave}"


def test_la_riga_di_comando_ha_le_stesse_due_liste(capsys):
    """Le opzioni esistono davvero: si legge dall'aiuto, non dal sorgente."""
    from mr_rao.cli import main

    with pytest.raises(SystemExit):
        main(["convert", "--help"])
    aiuto = capsys.readouterr().out
    assert "--sempre" in aiuto and "--mai" in aiuto


def test_le_liste_della_riga_di_comando_arrivano_al_motore():
    import argparse

    from mr_rao.cli import _build_options

    opts = _build_options(
        argparse.Namespace(sempre=["Alfa", "Beta"], mai=["Gamma"])
    )
    assert opts.privacy.sempre == ("Alfa", "Beta")
    assert opts.privacy.mai == ("Gamma",)
