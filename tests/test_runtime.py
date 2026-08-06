"""Regressioni su annullamento, job store, concorrenza e hotfolder."""
import threading
import time

import pytest

from config import MAX_JOBS_KEPT
from mr_rao import routes
from mr_rao.converter import ConvertOptions, convert_file, strip_frontmatter
from mr_rao.jobs import Job, JobStore
from mr_rao.privacy import PrivacyOptions
from mr_rao.watch_service import output_path_for

NO_PRIVACY = PrivacyOptions(
    emails=False, phones=False, names=False, fiscal=False,
    amounts=False, use_scrubadub=False,
)


# ---------------------------------------------------------------------------
# Annulla: prima veniva letto solo dentro il loop OCR delle pagine PDF
# ---------------------------------------------------------------------------


def test_annulla_a_meta_pipeline(tmp_path):
    """L'annullamento arriva dopo la conversione: va onorato al primo
    confine di stadio, senza spendere tempo nel filtro privacy."""
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
        options=ConvertOptions(engine="rapidocr", privacy=PrivacyOptions(use_scrubadub=False)),
    )
    assert "rapidocr" in r.engine_used
    assert "OCR" in r.markdown and "confronto prima/dopo" in r.markdown


def test_nessun_avviso_ocr_sui_documenti_nativi(tmp_path):
    """Su un documento con testo nativo l'avviso sarebbe rumore."""
    p = tmp_path / "nota.txt"
    p.write_text("CF RSSMRA80A01H501U", encoding="utf-8")
    r = convert_file(p, options=ConvertOptions(privacy=PrivacyOptions(use_scrubadub=False)))
    assert "{{CODICE_FISCALE}}" in r.markdown
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
