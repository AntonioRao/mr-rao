# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Regressioni su annullamento, job store, concorrenza e hotfolder."""
import threading
import time

import pytest

from config import MAX_JOBS_KEPT
from mr_rao import routes
from mr_rao.converter import ConvertOptions, convert_file, strip_frontmatter
from mr_rao.jobs import Job, JobStore
from mr_rao.privacy import PrivacyOptions, no_redaction
from mr_rao.watch_service import output_path_for

NO_PRIVACY = no_redaction()


# ---------------------------------------------------------------------------
# Annulla: prima veniva letto solo dentro il loop OCR delle pagine PDF
# ---------------------------------------------------------------------------


def test_annulla_a_meta_pipeline(tmp_path):
    """L'annullamento arriva dopo la conversione: va onorato al primo
    passaggio da uno stadio all'altro, senza spendere tempo nel filtro privacy."""
    p = tmp_path / "nota.txt"
    p.write_text("contenuto", encoding="utf-8")

    letture = []

    def should_cancel():
        letture.append(1)
        return len(letture) > 1  # False al primo controllo, poi True

    r = convert_file(p, options=ConvertOptions(), should_cancel=should_cancel)
    assert r.engine_used == "cancelled"
    assert r.error == "Conversione annullata"
    assert len(letture) >= 2, "il cancel viene letto a più stadi, non solo all'inizio"


def test_annulla_immediato(tmp_path):
    p = tmp_path / "nota.txt"
    p.write_text("contenuto", encoding="utf-8")
    r = convert_file(p, options=ConvertOptions(), should_cancel=lambda: True)
    assert r.engine_used == "cancelled"


# ---------------------------------------------------------------------------
# Job store: i risultati non devono restare in RAM per sempre
# ---------------------------------------------------------------------------


def test_job_scaduti_rimossi():
    store = JobStore()
    vecchio = store.create()
    vecchio.created_at = time.time() - 10_000  # oltre il TTL
    recente = store.create()
    store.cleanup()
    assert store.get(vecchio.id) is None
    assert store.get(recente.id) is not None


def test_tetto_sui_job_conservati():
    store = JobStore()
    for _ in range(MAX_JOBS_KEPT + 20):
        job = store.create()
        job.status = "done"
        job.result = {"markdown": "x" * 1000}
    store.cleanup()
    assert len(store._jobs) <= MAX_JOBS_KEPT


def test_lo_sfoltimento_non_tocca_i_job_in_corso():
    store = JobStore()
    in_corso = []
    for i in range(MAX_JOBS_KEPT + 20):
        job = store.create()
        if i % 10 == 0:
            job.status = "running"
            in_corso.append(job.id)
        else:
            job.status = "done"
    store.cleanup()
    for jid in in_corso:
        assert store.get(jid) is not None, "un job in esecuzione è stato sfrattato"


# ---------------------------------------------------------------------------
# Concorrenza: un thread per richiesta = N OCR simultanei
# ---------------------------------------------------------------------------


def test_le_conversioni_concorrenti_sono_limitate(monkeypatch):
    monkeypatch.setattr(routes, "_worker_slots", threading.BoundedSemaphore(2))

    attivi = 0
    massimo = 0
    lock = threading.Lock()
    finiti = threading.Semaphore(0)

    def lavoro():
        nonlocal attivi, massimo
        with lock:
            attivi += 1
            massimo = max(massimo, attivi)
        time.sleep(0.05)
        with lock:
            attivi -= 1
        finiti.release()

    for _ in range(8):
        routes._spawn(lavoro)
    for _ in range(8):
        assert finiti.acquire(timeout=5), "lavoro non completato"

    assert massimo <= 2, f"fino a {massimo} conversioni in parallelo"


# ---------------------------------------------------------------------------
# Hotfolder: 'a.pdf' e 'a.docx' volevano entrambi 'a.md'
# ---------------------------------------------------------------------------


def test_nomi_output_hotfolder_non_collidono(tmp_path):
    outbox = tmp_path / "out"
    outbox.mkdir()
    inbox = tmp_path / "in"
    inbox.mkdir()

    primo = output_path_for(outbox, inbox / "relazione.pdf")
    assert primo.name == "relazione.md"
    primo.write_text("primo", encoding="utf-8")

    secondo = output_path_for(outbox, inbox / "relazione.docx")
    assert secondo.name == "relazione-docx.md"
    secondo.write_text("secondo", encoding="utf-8")

    terzo = output_path_for(outbox, inbox / "relazione.docx")
    assert terzo.name == "relazione-docx-2.md"

    assert primo.read_text(encoding="utf-8") == "primo", "il primo file è stato sovrascritto"


def test_avviso_quando_la_redazione_lavora_su_testo_ocr(tmp_path, monkeypatch):
    """L'anonimizzazione toglie solo ciò che l'OCR ha letto bene.

    Misurato su un PDF scansionato: `IBAN IT60X…` letto come `TBAN1TB0X…` non
    corrisponde ad alcun pattern, quindi resta nel testo. Chi riceve il
    risultato deve sapere che su un documento OCR la garanzia è più debole.
    """
    from mr_rao import converter

    monkeypatch.setattr(converter, "ocr_image", lambda path, language="it": "CF RSSMRA80A01H501U")
    p = tmp_path / "scansione.png"
    p.write_bytes(b"\x00")

    r = convert_file(
        p,
        options=ConvertOptions(engine="rapidocr", privacy=PrivacyOptions()),
    )
    assert "rapidocr" in r.engine_used
    assert "OCR" in r.markdown and "confronto prima/dopo" in r.markdown


def test_nessun_avviso_ocr_sui_documenti_nativi(tmp_path):
    """Su un documento con testo nativo l'avviso sarebbe rumore."""
    p = tmp_path / "nota.txt"
    p.write_text("CF RSSMRA80A01H501U", encoding="utf-8")
    r = convert_file(p, options=ConvertOptions(privacy=PrivacyOptions()))
    assert "{{CODICE_FISCALE_1}}" in r.markdown
    assert "confronto prima/dopo" not in r.markdown


def test_nessun_avviso_ocr_se_la_privacy_e_spenta(tmp_path, monkeypatch):
    """Senza redazione non c'è nulla che possa sfuggire alla redazione."""
    from mr_rao import converter

    monkeypatch.setattr(converter, "ocr_image", lambda path, language="it": "testo qualsiasi")
    p = tmp_path / "scansione.png"
    p.write_bytes(b"\x00")
    r = convert_file(p, options=ConvertOptions(engine="rapidocr", privacy=NO_PRIVACY))
    assert "confronto prima/dopo" not in r.markdown


def test_scrittura_hotfolder_atomica(tmp_path):
    """Il file dev'esserci intero o non esserci: una scrittura diretta
    interrotta a metà lascia un .md troncato senza che nessuno se ne accorga."""
    from mr_rao.watch_service import write_atomic

    dest = tmp_path / "documento.md"
    write_atomic(dest, "contenuto completo")
    assert dest.read_text(encoding="utf-8") == "contenuto completo"
    # nessun file temporaneo lasciato indietro
    assert list(tmp_path.glob("*.part")) == []

    # sovrascrittura: il contenuto precedente non resta mescolato
    write_atomic(dest, "nuovo")
    assert dest.read_text(encoding="utf-8") == "nuovo"
    assert list(tmp_path.glob("*.part")) == []


def test_memoria_hotfolder_limitata():
    from mr_rao import watch_service

    watch_service._state._seen.clear()
    try:
        for i in range(watch_service.MAX_SEEN + 100):
            watch_service._remember(f"file{i}.pdf:{i}")
        assert len(watch_service._state._seen) <= watch_service.MAX_SEEN
        # le chiavi più recenti sopravvivono
        assert f"file{watch_service.MAX_SEEN + 99}.pdf:{watch_service.MAX_SEEN + 99}" in (
            watch_service._state._seen
        )
    finally:
        watch_service._state._seen.clear()


# ---------------------------------------------------------------------------
# Un file che sta ancora arrivando non e' un file da convertire
# ---------------------------------------------------------------------------


def test_il_file_ancora_in_scrittura_non_viene_preso_a_meta(tmp_path):
    """Chi scrive nella cartella sorvegliata puo' fermarsi a meta'.

    Una copia da disco di rete, uno scanner, un client di posta che salva
    l'allegato: la scrittura arriva a pezzi, e fra un pezzo e l'altro il file
    resta fermo per un attimo. Se la finestra di controllo e' piu' corta di
    quella pausa, la cartella sorvegliata vede un file «stabile» che stabile
    non e', lo converte, e lascia nella cartella di uscita un .md con dentro
    mezzo documento. L'utente non ha modo di accorgersene: il file c'e' ed e'
    ben formato.

    Questo test **corre davvero** -- un filo scrive lentamente mentre la
    cartella e' sorvegliata -- e non simula niente.

    Il presidio non e' magia: la finestra di quiete e' ora l'intervallo di
    sorveglianza, che l'utente controlla, invece di 0,35 secondi fissi che
    nessuna impostazione poteva allungare. Una pausa piu' lunga
    dell'intervallo puo' ancora ingannare qualunque controllo a campione:
    e' un limite del guardare a intervalli, e va detto invece che nascosto.
    """
    from mr_rao import watch_service

    inbox = tmp_path / "in"
    outbox = tmp_path / "out"
    inbox.mkdir()
    outbox.mkdir()
    opzioni = ConvertOptions(privacy=NO_PRIVACY, include_frontmatter=False)

    # Riscaldamento: la prima conversione importa MarkItDown e costa quasi un
    # secondo. Senza, quell'attesa copre la pausa dello scrittore e la corsa
    # non si vede -- il test passerebbe per il motivo sbagliato.
    riscaldamento = tmp_path / "riscaldamento.txt"
    riscaldamento.write_text("gia' caldo", encoding="utf-8")
    convert_file(riscaldamento, options=opzioni)

    PAUSA = 1.2  # piu' lunga dei 0,35 s del vecchio controllo, piu' corta dell'intervallo

    def scrittore():
        with open(inbox / "lento.txt", "wb") as f:
            f.write(b"PARTE-UNO\n")
            f.flush()
            time.sleep(PAUSA)
            f.write(b"PARTE-DUE\n")
            f.flush()

    filo = threading.Thread(target=scrittore, name="scrittore-lento")
    try:
        filo.start()
        watch_service.start_watch(inbox, outbox, options=opzioni, interval=2.0)
        filo.join()
        scadenza = time.monotonic() + 20
        while time.monotonic() < scadenza and not list(outbox.glob("*.md")):
            time.sleep(0.1)
    finally:
        watch_service.stop_watch()

    uscite = list(outbox.glob("*.md"))
    assert uscite, "la cartella sorvegliata non ha convertito niente"
    for prodotto in uscite:
        testo = prodotto.read_text(encoding="utf-8")
        assert "PARTE-UNO" in testo and "PARTE-DUE" in testo, (
            f"{prodotto.name} contiene solo mezzo documento: {testo!r}"
        )


def test_l_impronta_del_file_guarda_anche_l_orario(tmp_path):
    """La sola dimensione non distingue un file riscritto in casa.

    Stessa lunghezza, contenuto diverso: due campionamenti di `st_size`
    dicono «fermo». L'orario di modifica lo dice, e sta gia' nella chiave
    che la cartella sorvegliata usa per non riconvertire due volte -- non
    guardarlo qui era una dimenticanza, non una scelta.

    L'orario lo forziamo con os.utime: la risoluzione dell'orologio del file
    system e' affare suo, non nostro, e non e' quello che vogliamo provare.
    """
    import os

    from mr_rao.watch_service import _impronta

    percorso = tmp_path / "a.txt"
    percorso.write_bytes(b"AAAA")
    prima = _impronta(percorso)
    percorso.write_bytes(b"BBBB")
    piu_tardi = prima[1] + 10_000_000  # +10 ms in nanosecondi
    os.utime(percorso, ns=(piu_tardi, piu_tardi))
    dopo = _impronta(percorso)

    assert prima[0] == dopo[0], "la dimensione non e' cambiata: e' il caso da coprire"
    assert prima != dopo, "l'impronta non guarda l'orario di modifica"


def test_l_impronta_di_un_file_sparito_e_nulla(tmp_path):
    from mr_rao.watch_service import _impronta

    assert _impronta(tmp_path / "mai-esistito.txt") is None


# ---------------------------------------------------------------------------
# Frontmatter: 'inizia con ---' non basta per dire che c'è un blocco YAML
# ---------------------------------------------------------------------------


def test_strip_frontmatter_rimuove_il_blocco_vero():
    md = '---\ngenerator: "Mr. Rao"\nsource: "a.pdf"\n---\n\n# Titolo\ntesto'
    assert strip_frontmatter(md) == "# Titolo\ntesto"


@pytest.mark.parametrize(
    "md",
    [
        "---\n\nUn documento che inizia con una riga orizzontale\n\n---\n\nsegue altro testo",
        "---\nTesto libero senza chiavi YAML\n---\nresto del documento",
        "# Titolo normale\ntesto",
        "---",
    ],
)
def test_strip_frontmatter_non_mangia_il_contenuto(md):
    """Un documento che parte con una riga orizzontale Markdown perdeva
    tutto il testo fino al '---' successivo."""
    assert strip_frontmatter(md) == md


def test_merge_non_perde_il_corpo_con_riga_orizzontale():
    from mr_rao.converter import ConvertResult, merge_markdowns
    from mr_rao.privacy import RedactionReport

    corpo = "---\n\nPremessa importante\n\n---\n\nConclusione"
    r = ConvertResult(
        markdown=corpo, engine_used="t", source_name="a.txt",
        source_ext=".txt", redaction=RedactionReport(),
    )
    unito = merge_markdowns([r], title="Unito")
    assert "Premessa importante" in unito
    assert "Conclusione" in unito
