"""Le caselle dell'interfaccia devono comandare il motore.

Regressione di un difetto silenzioso: quando la richiesta portava un
``profile``, il server prendeva il preset e buttava via tutto il resto del
modulo. Siccome l'interfaccia manda *sempre* il profilo, l'intero pannello
«Quali dati nascondere» — interruttore generale compreso — era decorativo:
si spuntava una casella e non cambiava niente, senza nessun errore.

Il difetto non si vedeva dai test perche' i test chiamavano il motore
direttamente. Questi passano dalla stessa porta da cui passa la pagina.
"""
import io

import pytest

from mr_rao.app_factory import create_app

BASE = "http://127.0.0.1:5000"
TESTO = b"Scrivi a mario.rossi@example.it oppure al 335 123 4567"


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def converti(client, **campi):
    campi["file"] = (io.BytesIO(TESTO), "nota.txt")
    r = client.post(
        "/api/convert/sync",
        data=campi,
        content_type="multipart/form-data",
        base_url=BASE,
        headers={"Origin": BASE},
    )
    assert r.status_code == 200, r.status_code
    return r.get_json() or {}


def test_il_profilo_da_solo_applica_il_preset(client):
    md = converti(client, profile="default")["markdown"]
    assert "{{EMAIL_1}}" in md


def test_l_interruttore_generale_vince_sul_profilo(client):
    md = converti(client, profile="default", privacy_filter="false")["markdown"]
    assert "mario.rossi@example.it" in md
    # `{{EMAIL` senza le graffe finali: prende **tutte e due** le forme,
    # numerata e no. Scritto `"{{EMAIL}}" not in md` sarebbe vero anche con
    # il filtro acceso -- l'uscita direbbe `{{EMAIL_1}}` -- cioe' un
    # controllo che non puo' piu' fallire.
    assert "{{EMAIL" not in md


def test_una_singola_casella_vince_sul_profilo(client):
    md = converti(
        client, profile="default", privacy_filter="true", privacy_emails="false"
    )["markdown"]
    assert "mario.rossi@example.it" in md, "la casella Email era spenta"
    assert "{{PHONE_1}}" in md, "le altre caselle devono restare come nel profilo"


def test_si_puo_accendere_un_riconoscitore_su_un_profilo_che_lo_spegne(client):
    md = converti(
        client, profile="no_privacy", privacy_filter="true", privacy_emails="true"
    )["markdown"]
    assert "{{EMAIL_1}}" in md


def test_la_casella_della_numerazione_comanda_il_motore(client):
    """Parita' GUI per l'opzione nuova: la casella deve fare qualcosa.

    E' il difetto che questo file esiste per prevenire -- un pannello che
    sembra comandare il motore e non lo comanda -- e un'opzione aggiunta al
    motore senza il giro completo (modulo, `options_from_form`, pagina) e'
    esattamente quel difetto.
    """
    numerato = converti(client, profile="default")["markdown"]
    piatto = converti(client, profile="default", privacy_numerati="false")["markdown"]
    assert "{{EMAIL_1}}" in numerato
    assert "{{EMAIL}}" in piatto and "{{EMAIL_1}}" not in piatto


def test_il_pannello_rileva_ma_non_sostituire_comanda_il_motore():
    """Parita' GUI per il terzo stato (P6.2).

    Il ramo che l'interfaccia percorre e' quello con il profilo, ed e'
    separato da `options_from_form`: una funzione aggiunta solo li' arriva
    all'API e **non** alla pagina. E' successo con la numerazione mentre la
    scrivevo, quindi qui si prova la strada vera.
    """
    app = create_app()
    app.config["TESTING"] = True
    cliente = app.test_client()

    risposta = converti(cliente, profile="default", privacy_segnala="emails")
    md, rapporto = risposta["markdown"], risposta.get("redaction") or {}
    assert "mario.rossi@example.it" in md, "l'indirizzo doveva restare nel documento"
    assert "{{EMAIL" not in md
    # E la parte che vale davvero: il rapporto dice che c'era.
    assert rapporto.get("detected_counts", {}).get("emails") == 1, rapporto


def test_un_campo_assente_resta_quello_del_profilo(client):
    """Chi chiama l'API con il solo profilo deve avere esattamente il preset."""
    md = converti(client, profile="no_privacy")["markdown"]
    assert "mario.rossi@example.it" in md


def test_anche_le_opzioni_di_uscita_rispondono(client):
    """Non solo la privacy: con un profilo anche «copia pulita» e le tabelle
    venivano ignorate."""
    con = converti(client, profile="default", include_frontmatter="false")["markdown"]
    senza = converti(client, profile="default", include_frontmatter="true")["markdown"]
    assert not con.startswith("---")
    assert senza.startswith("---")


def test_ogni_riconoscitore_ha_la_sua_casella_nella_pagina(client):
    """Parita' GUI: un campo del motore senza casella e' un campo che
    l'utente non puo' governare, e non se ne accorge nessuno."""
    from mr_rao.privacy import FIELD_DEFAULTS

    pagina = client.get("/", base_url=BASE).get_data(as_text=True)
    mancanti = [k for k in FIELD_DEFAULTS if f'id="privacy-{k}"' not in pagina]
    assert not mancanti, f"riconoscitori senza casella: {mancanti}"


def test_ogni_casella_viene_spedita_dal_frontend():
    """La casella c'e' ma il javascript non la manda: stesso effetto."""
    from pathlib import Path

    from mr_rao.privacy import FIELD_DEFAULTS

    js = Path("static/js/app.js").read_text(encoding="utf-8")
    inizio = js.index("const PRIVACY_FIELDS")
    elenco = js[inizio : js.index("]", inizio)]
    mancanti = [k for k in FIELD_DEFAULTS if f'"{k}"' not in elenco]
    assert not mancanti, f"riconoscitori non spediti dalla pagina: {mancanti}"
