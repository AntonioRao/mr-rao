"""Le due parti concorrenti del programma: annullare un lavoro e accendere o
spegnere la cartella sorvegliata.

Sono thread veri su stato condiviso, quindi qui non si sincronizza con le
attese a occhio: ogni incrocio passa da un `threading.Event`, e dove serve
aspettare un fatto (un .md che compare, un thread che muore) si aspetta *quel
fatto* con una scadenza generosa, perche' un runner Windows di CI e' lento e
carico. Nessuna `sleep` regge la logica di un test: al massimo distanzia due
letture di uno stesso fatto.
"""
from __future__ import annotations

import threading
import time
from io import BytesIO
from pathlib import Path

import pytest

from mr_rao import routes, watch_service
from mr_rao.converter import ConvertResult
from mr_rao.jobs import job_store

# Le attese sono lunghe apposta: se il codice e' giusto non ci si arriva mai,
# e se e' sbagliato il test fallisce comunque -- solo un po' piu' tardi.
ATTESA = 60.0  # sblocco fra thread di questo test
SCADENZA = 120.0  # comparsa di un esito prodotto da codice vero (conversione)


def attendi(condizione, scadenza: float = SCADENZA, passo: float = 0.05) -> bool:
    """Aspetta che una condizione diventi vera, entro una scadenza."""
    limite = time.monotonic() + scadenza
    while time.monotonic() < limite:
        if condizione():
            return True
        time.sleep(passo)
    return condizione()


def thread_di_sorveglianza() -> list[threading.Thread]:
    """I giri di sorveglianza vivi adesso, contati per nome del thread."""
    return [t for t in threading.enumerate() if t.name == "mr-rao-watch" and t.is_alive()]


def stato_lavoro(client, job_id: str) -> dict:
    """Lo stato di un lavoro come lo vede la pagina che fa il polling."""
    return client.get(f"/api/jobs/{job_id}").get_json()


def traccia_worker(monkeypatch, nome: str) -> threading.Event:
    """Un Event che scatta quando il thread del lavoro ha finito davvero.

    Serve perche' «lo stato non e' piu' running» non dice niente qui: appena
    si annulla, lo stato e' gia' terminale mentre il worker sta ancora
    girando. Senza questo aggancio l'ultima verifica leggerebbe uno stato di
    passaggio -- e un test che guarda troppo presto passa per caso.
    """
    originale = getattr(routes, nome)
    finito = threading.Event()

    def tracciato(*a, **k):
        try:
            originale(*a, **k)
        finally:
            finito.set()

    monkeypatch.setattr(routes, nome, tracciato)
    return finito


def esito_finto(nome: str, *, errore: str | None = None) -> ConvertResult:
    """Il valore che restituisce un convertitore, senza convertire niente.

    Qui il pezzo sotto esame e' l'impalcatura concorrente -- thread, stato
    condiviso, annullamento -- non MarkItDown: il convertitore va tenuto
    fermo a comando, e un convertitore vero non si ferma dove dico io. Dove
    invece contano i file veri (la cartella sorvegliata che produce un .md)
    questo non si usa.
    """
    return ConvertResult(
        markdown="" if errore else "# finto\n",
        engine_used="cancelled" if errore else "finto",
        source_name=nome,
        source_ext=Path(nome).suffix,
        error=errore,
    )


@pytest.fixture(autouse=True)
def sorveglianza_spenta():
    """Lo stato della cartella sorvegliata e' globale al processo: qualunque
    cosa succeda in un test, il modulo successivo non deve ereditarne un
    thread acceso -- e nessun test di qui dentro deve contare i thread di
    qualcun altro, o il conteggio direbbe due per un motivo che non c'entra.
    """
    watch_service.stop_watch()
    assert attendi(lambda: not thread_di_sorveglianza(), 15.0), (
        "c'era gia' un thread di sorveglianza acceso prima del test"
    )
    yield
    watch_service.stop_watch()
    assert attendi(lambda: not thread_di_sorveglianza(), 15.0), (
        "un thread di sorveglianza e' sopravvissuto alla fine del test"
    )


# --------------------------------------------------------------------------
# Annullamento di un lavoro
# --------------------------------------------------------------------------


def test_annullare_un_lavoro_in_corso_lo_ferma_davvero(app, monkeypatch):
    """Non basta che lo stato dica «annullato»: il lavoro deve smettere.

    Tre file in coda, il convertitore tenuto fermo sul primo finche' non e'
    partito l'annullamento: il secondo e il terzo non devono essere convertiti
    affatto.
    """
    avviato = threading.Event()
    via_libera = threading.Event()
    convertiti: list[str] = []
    cancel_visto: list[bool] = []

    def finto_convert(data, filename, options=None, progress=None, should_cancel=None):
        convertiti.append(filename)
        if len(convertiti) == 1:
            avviato.set()
            assert via_libera.wait(ATTESA), "il test non ha mai dato il via libera"
        cancel_visto.append(bool(should_cancel and should_cancel()))
        return esito_finto(filename)

    monkeypatch.setattr(routes, "convert_bytes", finto_convert)
    worker_finito = traccia_worker(monkeypatch, "_run_job_batch")
    client = app.test_client()

    r = client.post(
        "/api/convert/batch",
        data={
            "files": [
                (BytesIO(b"uno"), "a.txt"),
                (BytesIO(b"due"), "b.txt"),
                (BytesIO(b"tre"), "c.txt"),
            ]
        },
        content_type="multipart/form-data",
    )
    assert r.status_code == 202
    job_id = r.get_json()["job_id"]

    assert avviato.wait(ATTESA), "il lavoro non e' mai partito"
    annulla = client.post(f"/api/jobs/{job_id}/cancel")
    assert annulla.status_code == 200
    assert annulla.get_json() == {"ok": True, "id": job_id}
    via_libera.set()

    assert worker_finito.wait(ATTESA), "il lavoro non si e' mai fermato"

    stato = stato_lavoro(client, job_id)
    assert stato["status"] == "cancelled", stato
    assert stato["result"] is None
    assert convertiti == ["a.txt"], (
        f"dopo l'annullamento sono stati convertiti anche: {convertiti[1:]}"
    )
    assert cancel_visto == [True], (
        "il convertitore non ha visto la richiesta di annullamento"
    )


def test_lo_stato_non_torna_running_dopo_l_annullamento(app, monkeypatch):
    """Un avanzamento in arrivo dal worker non deve resuscitare un annullato.

    Il convertitore vero chiama `progress()` a ogni pagina e si accorge
    dell'annullamento solo al confine fra due fasi: nel mezzo passavano decine
    di avanzamenti, e ognuno rimetteva il lavoro in «running» cancellando il
    messaggio «Annullato dall'utente». Chi guardava la pagina vedeva la barra
    ripartire dopo aver premuto Annulla.

    Gli incroci sono tutti su Event, quindi la lettura cade sempre nello stesso
    punto: dopo l'avanzamento e prima che il worker chiuda il lavoro.
    """
    avviato = threading.Event()
    via_libera = threading.Event()
    avanzamento_fatto = threading.Event()
    riprendi = threading.Event()

    def finto_convert(data, filename, options=None, progress=None, should_cancel=None):
        avviato.set()
        assert via_libera.wait(ATTESA), "il test non ha mai dato il via libera"
        progress(1, 3, "meta' strada")
        avanzamento_fatto.set()
        assert riprendi.wait(ATTESA), "il test non ha mai fatto riprendere"
        return esito_finto(filename, errore="annullata")

    monkeypatch.setattr(routes, "convert_bytes", finto_convert)
    worker_finito = traccia_worker(monkeypatch, "_run_job_single")
    client = app.test_client()

    r = client.post(
        "/api/convert",
        data={"file": (BytesIO(b"ciao"), "a.txt")},
        content_type="multipart/form-data",
    )
    job_id = r.get_json()["job_id"]

    assert avviato.wait(ATTESA), "il lavoro non e' mai partito"
    assert client.post(f"/api/jobs/{job_id}/cancel").status_code == 200
    assert stato_lavoro(client, job_id)["status"] == "cancelled"

    via_libera.set()
    assert avanzamento_fatto.wait(ATTESA), "il worker non ha mai riferito un avanzamento"

    durante = stato_lavoro(client, job_id)
    assert durante["status"] == "cancelled", (
        f"un avanzamento del worker ha rimesso il lavoro in {durante['status']!r}"
    )
    assert durante["message"] != "meta' strada", (
        "il messaggio dell'annullamento e' stato sovrascritto dall'avanzamento"
    )

    riprendi.set()
    assert worker_finito.wait(ATTESA), "il worker non ha mai chiuso il lavoro"
    assert stato_lavoro(client, job_id)["status"] == "cancelled"


def test_annullare_un_lavoro_gia_finito_non_lo_stravolge(client):
    """Conversione vera, portata a termine, poi Annulla: e' il doppio clic di
    chi non ha visto la barra arrivare in fondo. La risposta e' un ok, il
    risultato resta al suo posto e lo stato non diventa «annullato»."""
    r = client.post(
        "/api/convert",
        data={"file": (BytesIO(b"buongiorno"), "a.txt")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 202
    job_id = r.get_json()["job_id"]

    assert attendi(
        lambda: stato_lavoro(client, job_id)["status"] not in ("pending", "running")
    ), "la conversione non e' mai finita"
    finito = stato_lavoro(client, job_id)
    assert finito["status"] == "done", finito
    assert finito["result"]

    for _ in range(2):  # due volte: dev'essere indifferente
        annulla = client.post(f"/api/jobs/{job_id}/cancel")
        assert annulla.status_code == 200
        assert annulla.get_json()["ok"] is True

    dopo = stato_lavoro(client, job_id)
    assert dopo["status"] == "done", f"un lavoro finito e' diventato {dopo['status']!r}"
    assert dopo["result"] == finito["result"]
    assert dopo["error"] is None


def test_annullare_un_lavoro_inesistente_risponde_404(client):
    """Un id sconosciuto -- scaduto, o inventato -- non deve far esplodere
    niente: 404 e un messaggio, come per la lettura dello stato."""
    assert job_store.get("non-esiste-proprio") is None
    assert job_store.cancel("non-esiste-proprio") is False

    r = client.post("/api/jobs/non-esiste-proprio/cancel")
    assert r.status_code == 404
    assert r.get_json()["error"]

    assert client.get("/api/jobs/non-esiste-proprio").status_code == 404


# --------------------------------------------------------------------------
# Avvio e arresto della cartella sorvegliata
# --------------------------------------------------------------------------


@pytest.fixture()
def cartelle(tmp_path, monkeypatch):
    """Cartelle di lavoro sotto tmp_path.

    `POST /api/watch` crea comunque le cartelle predefinite, anche quando i
    percorsi arrivano nella richiesta: senza questo dirottamento un test
    lascerebbe cartelle nei Documenti di chi lo esegue.
    """
    monkeypatch.setenv("MR_RAO_FOLDER_ROOT", str(tmp_path / "predefinite"))
    inbox = tmp_path / "in"
    outbox = tmp_path / "out"
    inbox.mkdir()
    outbox.mkdir()
    return inbox, outbox


def test_ciclo_avvio_stato_stop_riavvio(client, cartelle):
    """Il giro completo dalla API: accendi, guarda, spegni, riaccendi.

    La conversione qui e' quella vera: il .md nella cartella di uscita e'
    la prova che il thread non e' solo vivo, ma sta lavorando.
    """
    inbox, outbox = cartelle
    corpo = {"inbox": str(inbox), "outbox": str(outbox), "interval": 0.5}

    acceso = client.post("/api/watch", json=corpo)
    assert acceso.status_code == 200
    assert acceso.get_json()["running"] is True
    assert len(thread_di_sorveglianza()) == 1

    (inbox / "documento.txt").write_text("Buongiorno a tutti", encoding="utf-8")
    assert attendi(lambda: list(outbox.glob("*.md"))), (
        "la cartella sorvegliata non ha convertito niente"
    )

    stato = client.get("/api/watch").get_json()
    assert stato["running"] is True
    assert stato["inbox"] == str(inbox.resolve())
    assert attendi(lambda: client.get("/api/watch").get_json()["processed"] >= 1, 30.0)

    spento = client.delete("/api/watch")
    assert spento.status_code == 200
    assert spento.get_json()["running"] is False
    assert attendi(lambda: not thread_di_sorveglianza(), 30.0), (
        "il thread di sorveglianza e' rimasto vivo dopo la DELETE"
    )
    assert client.get("/api/watch").get_json()["running"] is False

    riacceso = client.post("/api/watch", json=corpo)
    assert riacceso.get_json()["running"] is True
    assert len(thread_di_sorveglianza()) == 1, "il riavvio ha lasciato un thread di troppo"


def test_doppio_avvio_non_lascia_due_thread(client, cartelle):
    """Due volte «Avvia» -- due clic, o due schede aperte sulla stessa pagina
    -- devono lasciare una sola cartella sorvegliata."""
    inbox, outbox = cartelle
    corpo = {"inbox": str(inbox), "outbox": str(outbox), "interval": 0.5}

    assert client.post("/api/watch", json=corpo).get_json()["running"] is True
    assert client.post("/api/watch", json=corpo).get_json()["running"] is True

    assert attendi(lambda: len(thread_di_sorveglianza()) == 1, 30.0), (
        f"thread di sorveglianza vivi: {len(thread_di_sorveglianza())}"
    )
    assert client.get("/api/watch").get_json()["running"] is True


def test_fermare_una_sorveglianza_mai_avviata(client, cartelle):
    """Spegnere quello che non e' acceso: nessuna eccezione, nessun thread,
    e uno stato che dice la verita'."""
    assert not thread_di_sorveglianza()

    for _ in range(2):
        r = client.delete("/api/watch")
        assert r.status_code == 200
        corpo = r.get_json()
        assert corpo["running"] is False
        assert corpo["message"]

    assert watch_service.stop_watch()["running"] is False
    assert not thread_di_sorveglianza()


def test_riavvio_durante_una_conversione_non_lascia_un_thread_orfano(
    cartelle, tmp_path, monkeypatch
):
    """Riaccendere mentre un file e' ancora sotto conversione.

    `stop_watch()` aspetta il thread al massimo 3 secondi: una conversione
    lunga (un PDF con OCR ci mette molto di piu') sfonda quell'attesa e il
    thread resta vivo. Il vecchio giro non deve tornare a lavorare sullo stato
    del nuovo: quando la conversione che lo teneva fermo finisce, quel thread
    deve morire, e di cartelle sorvegliate ne deve restare una sola.

    Il convertitore qui e' tenuto fermo da un Event, non da una sleep: il
    momento del riavvio e' scelto, non sperato.
    """
    inbox, outbox = cartelle
    inbox2 = tmp_path / "in2"
    outbox2 = tmp_path / "out2"
    inbox2.mkdir()
    outbox2.mkdir()

    in_conversione = threading.Event()
    via_libera = threading.Event()

    def finto_convert(filepath, original_name=None, options=None, **_k):
        in_conversione.set()
        assert via_libera.wait(ATTESA), "il test non ha mai dato il via libera"
        return esito_finto(Path(filepath).name)

    monkeypatch.setattr(watch_service, "convert_file", finto_convert)

    (inbox / "lento.txt").write_text("un documento qualsiasi", encoding="utf-8")
    watch_service.start_watch(inbox, outbox, interval=0.5)
    assert in_conversione.wait(ATTESA), "la conversione non e' mai iniziata"
    primo = watch_service._state._thread
    assert primo is not None and primo.is_alive()

    # Riavvio con la conversione ancora ferma: start_watch chiama stop_watch,
    # che aspetta invano i suoi 3 secondi.
    watch_service.start_watch(inbox2, outbox2, interval=0.5)
    secondo = watch_service._state._thread
    assert secondo is not None and secondo is not primo

    via_libera.set()
    assert attendi(lambda: not primo.is_alive(), 30.0), (
        "il vecchio thread di sorveglianza e' rimasto vivo dopo il riavvio: "
        "due giri sullo stesso stato condiviso"
    )
    assert attendi(lambda: len(thread_di_sorveglianza()) == 1, 30.0)
    assert secondo.is_alive()
    assert watch_service.get_watch_state()["running"] is True

    assert watch_service.stop_watch()["running"] is False
    assert attendi(lambda: not thread_di_sorveglianza(), 30.0)


def test_un_lavoro_annullato_in_coda_non_torna_in_corsa(client, monkeypatch):
    """La finestra fra «messo in coda» e «preso in mano dal worker».

    Dietro `MAX_WORKERS` i lavori aspettano il turno. Un annullamento che
    arriva mentre il lavoro e' li' fermo veniva sovrascritto dal worker, che
    all'avvio scriveva «running» senza guardare se qualcuno avesse gia' detto
    di no. Il lavoro non partiva davvero -- il convertitore esce al primo
    controllo -- ma la pagina mostrava la barra ripartire su qualcosa che
    l'utente aveva appena annullato, che e' l'unica cosa che conta per chi ha
    premuto quel tasto.
    """
    from mr_rao import routes
    from mr_rao.converter import ConvertOptions
    from mr_rao.jobs import job_store

    job = job_store.create()
    assert job_store.cancel(job.id) is True
    prima = job.status

    chiamato = []
    monkeypatch.setattr(
        routes, "convert_bytes", lambda *a, **k: chiamato.append(1)
    )
    routes._run_job_single_inner(job, b"testo", "nota.txt", ConvertOptions())

    assert prima == "cancelled"
    assert job.status == "cancelled", "il worker ha riportato in corsa un annullato"
    assert not chiamato, "non doveva nemmeno provare a convertire"
