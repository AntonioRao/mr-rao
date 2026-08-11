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

    # Il percorso parte da **questo file**, non dalla cartella corrente: con
    # `Path("static/...")` il test si rompeva lanciando pytest da altrove, e
    # un test che dipende da dove lo lanci, prima o poi lo lanci da altrove.
    js = (Path(__file__).resolve().parents[1] / "static" / "js" / "app.js") \
        .read_text(encoding="utf-8")
    inizio = js.index("const PRIVACY_FIELDS")
    elenco = js[inizio : js.index("]", inizio)]
    mancanti = [k for k in FIELD_DEFAULTS if f'"{k}"' not in elenco]
    assert not mancanti, f"riconoscitori non spediti dalla pagina: {mancanti}"


# ------------------------------------------------------------------------
# I pacchetti e lo stile: la meta' che questo file **non** guardava
# ------------------------------------------------------------------------
#
# Il pannello aveva le sue caselle, il motore i suoi campi, e qui si
# controllava che si corrispondessero — ma solo per i riconoscitori di
# `FIELD_DEFAULTS`. Pacchetti e stile viaggiano su un'altra strada, e quella
# non la guardava nessuno: nel ramo che l'interfaccia percorre **sempre**
# (manda sempre un profilo) venivano buttati via, e le caselle erano
# decorative — si accendeva «Atti e pratiche» e il protocollo restava in
# chiaro, si spegneva l'inglese e l'SSN spariva lo stesso.
#
# L'ha trovato un audit esterno. Queste righe esistono perche' non ricapiti.

TESTO_DI_PROVA = b"Vista la nota prot. n. 26597 del 19 ottobre. SSN 123-45-6789."


def _converti(client, **campi) -> str:
    import io

    dati = {"file": (io.BytesIO(TESTO_DI_PROVA), "prova.txt"), **campi}
    risposta = client.post("/api/convert/sync", base_url=BASE, data=dati,
                           content_type="multipart/form-data")
    assert risposta.status_code == 200, risposta.data[:200]
    return (risposta.get_json() or {}).get("markdown") or ""


def test_il_pacchetto_atti_conta_anche_col_profilo(client):
    """**Il difetto, nel verso in cui fa perdere un dato.**"""
    acceso = _converti(client, profile="default", privacy_pack_atti="true")
    assert "{{PRATICA" in acceso, acceso[-200:]

    spento = _converti(client, profile="default", privacy_pack_atti="false")
    assert "26597" in spento, "col pacchetto spento il protocollo deve restare"


def test_spegnere_un_pacchetto_conta_anche_col_profilo(client):
    """E nel verso opposto: una casella che non spegne e' una leva finta."""
    acceso = _converti(client, profile="default", privacy_pack_en="true")
    assert "{{SSN" in acceso, acceso[-200:]

    spento = _converti(client, profile="default", privacy_pack_en="false")
    assert "{{SSN" not in spento, spento[-200:]


def test_eta_e_sesso_arrivano_fino_allo_schermo():
    """Il terzo conto: trovato, lasciato dov'era, **e detto**.

    Età e sesso non si tolgono mai, per scelta. La frase che regge quella
    scelta è «lasciate in chiaro 3 età, apposta»: se il programma le trova e
    non lo dice, la scelta diventa indistinguibile dal non averle viste.

    Il server le mandava da sempre in `detected_counts`. La pagina non le
    leggeva: zero occorrenze di `detected` in tutto `app.js`. È la stessa
    forma degli altri difetti di questo file — un pezzo di motore che
    dall'interfaccia non esiste — solo che qui mancava l'ultimo tratto.

    Due metà, perché ha due modi di rompersi: il server smette di mandarle,
    oppure la pagina smette di leggerle.
    """
    from pathlib import Path

    app = create_app()
    app.config["TESTING"] = True
    cliente = app.test_client()

    # Etichette esplicite: i due riconoscitori le pretendono apposta — «45»
    # da solo è un numero, ed è la ragione per cui non producono rumore.
    testo = "Paziente. Età: 45. Sesso: M.".encode()
    campi = {"file": (io.BytesIO(testo), "cartella.txt")}
    r = cliente.post("/api/convert/sync", data=campi,
                     content_type="multipart/form-data",
                     base_url=BASE, headers={"Origin": BASE})
    rapporto = (r.get_json() or {}).get("redaction") or {}
    conti = rapporto.get("detected_counts") or {}
    assert conti.get("eta") == 1, rapporto
    assert conti.get("genere") == 1, rapporto
    assert "45" in (r.get_json() or {}).get("markdown", ""), "non si tolgono mai"

    js = (Path(__file__).resolve().parents[1] / "static" / "js" / "app.js") \
        .read_text(encoding="utf-8")
    assert "detected_counts" in js, "il server lo manda e la pagina non lo legge"
    assert "detected_total" in js, "il server lo manda e la pagina non lo legge"

    # E i nomi leggibili devono esserci per ogni categoria che può comparire
    # lì dentro, altrimenti nel riquadro si legge `eta` e `genere` — cioè il
    # codice che parla a se stesso.
    from mr_rao.i18n import TESTI

    for categoria in ("eta", "genere"):
        assert f"cat_{categoria}" in TESTI, categoria


def test_lo_stile_conta_anche_col_profilo():
    """«Lettera o modulo» cambia il segno di diverse regole.

    Buttarla via nel ramo col profilo vuol dire che la stessa pagina, con la
    stessa impostazione, redige in due modi diversi a seconda di come e'
    arrivata la richiesta.
    """
    from flask import Flask, request

    from mr_rao.privacy import prosa_da
    from mr_rao.routes import _merge_privacy

    assert prosa_da("prosa") is True
    assert prosa_da("modulo") is False
    assert prosa_da("") is None, "vuoto vuol dire «non lo so», non «e' un modulo»"

    app = Flask(__name__)
    with app.test_request_context(
            "/", method="POST",
            data={"profile": "default", "privacy_filter": "true",
                  "privacy_stile": "prosa"}):
        assert _merge_privacy(request.form, {}).prosa is True
    with app.test_request_context(
            "/", method="POST",
            data={"profile": "default", "privacy_filter": "true",
                  "privacy_stile": "modulo"}):
        assert _merge_privacy(request.form, {}).prosa is False
