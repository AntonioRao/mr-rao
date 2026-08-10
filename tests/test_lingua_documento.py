"""La lingua arriva *dentro* il documento, non solo sullo schermo.

Prima di questi test un utente inglese vedeva una pagina inglese e apriva un
documento italiano: «| Campo | Valore |», «Tabelle estratte», «Ultimo
messaggio». Lo schermo lo si guarda una volta, il documento lo si archivia.

Qui si verificano tre cose che a rileggere il codice non si vedono:

1. che la lingua del *lavoro* (`ConvertOptions.lingua`) arrivi fino al testo;
2. che le note dell'applicazione restino riconoscibili anche in inglese --
   `_RE_NOTA_PRIVACY` e la sua gemella in `app.js` le tolgono dalla «copia
   pulita», e si agganciano all'emoji e al `> ` iniziale;
3. che la lingua **non** sposti i riconoscitori. E' la regola scritta in
   i18n.py, ed e' quella che, se salta, toglie protezione senza dirlo.
"""
from __future__ import annotations

import re
from email.message import EmailMessage
from pathlib import Path

import pytest

from mr_rao.converter import (
    _RE_NOTA_PRIVACY,
    ConvertOptions,
    convert_bytes,
    merge_markdowns,
    ConvertResult,
)
from mr_rao.eml_parser import nota_elaborazione, parse_eml
from mr_rao.i18n import LINGUE
from mr_rao.privacy import PrivacyOptions

TESTO = (
    "Gentile Dott. Mario Rossi, il suo codice fiscale RSSMRA85M01H501Z "
    "risulta registrato. Scriva a mario.rossi@example.it."
)


def _eml(percorso: Path, oggetto: str = "Preventivo") -> Path:
    msg = EmailMessage()
    msg["Subject"] = oggetto
    msg["From"] = "mittente@example.it"
    msg["To"] = "destinatario@example.it"
    msg["Date"] = "Wed, 06 Aug 2026 10:00:00 +0000"
    msg.set_content(TESTO)
    percorso.write_bytes(msg.as_bytes())
    return percorso


# ── 1. la lingua arriva al testo ────────────────────────────────────────


def test_intestazione_email_in_inglese(tmp_path):
    md = parse_eml(_eml(tmp_path / "m.eml"), "en")
    assert "| Field | Value |" in md
    assert "| **From** |" in md
    assert "Latest message" in md
    assert "Campo" not in md and "Ultimo messaggio" not in md


def test_intestazione_email_resta_italiana_per_chi_non_chiede_niente(tmp_path):
    """Il valore predefinito e' l'italiano: la riga di comando e la cartella
    sorvegliata non passano nessuna lingua e non devono cambiare da sole."""
    md = parse_eml(_eml(tmp_path / "m.eml"))
    assert "| Campo | Valore |" in md
    assert "| **Da** |" in md


def test_la_lingua_attraversa_tutta_la_conversione(tmp_path):
    """Non basta che `parse_eml` sappia l'inglese: deve arrivarci partendo
    dalle opzioni del lavoro, che e' il percorso vero."""
    dati = _eml(tmp_path / "m.eml").read_bytes()
    r = convert_bytes(
        dati, "m.eml", options=ConvertOptions(lingua="en", include_frontmatter=False)
    )
    assert "| Field | Value |" in r.markdown
    assert "Document processed by Mr. Rao" in r.markdown


@pytest.mark.parametrize("lingua", LINGUE)
def test_il_titolo_del_merge_lo_decide_la_lingua(lingua):
    """`title=None` significa «decidilo tu»: prima il predefinito era scritto
    nella firma, quindi italiano per sempre."""
    r = ConvertResult(markdown="ciao", engine_used="x", source_name="a.txt", source_ext=".txt")
    unito = merge_markdowns([r], lingua=lingua)
    atteso = "Merged document" if lingua == "en" else "Documento unificato"
    assert f"# {atteso}" in unito


def test_il_confronto_etichetta_i_documenti_nella_lingua_giusta():
    a = ConvertResult(markdown="a", engine_used="x", source_name="a.txt", source_ext=".txt")
    b = ConvertResult(markdown="b", engine_used="x", source_name="b.txt", source_ext=".txt")
    en = merge_markdowns([a, b], compare_mode=True, lingua="en")
    assert "Document A" in en and "Document B" in en
    assert "# Document comparison" in en


# ── 2. le note restano riconoscibili in tutte le lingue ─────────────────


@pytest.mark.parametrize("lingua", LINGUE)
def test_la_nota_e_ancora_una_nota_in_ogni_lingua(lingua):
    """`_RE_NOTA_PRIVACY` si aggancia all'emoji e al `> ` iniziale. Se una
    traduzione li spostasse, la «copia pulita» smetterebbe di ripulire --
    in silenzio, perche' nessuno guarda il testo che *non* c'e' piu'."""
    nota = nota_elaborazione(lingua)
    riga = [r for r in nota.split("\n") if r.strip()][-1]
    assert _RE_NOTA_PRIVACY.sub("", riga + "\n") == ""


@pytest.mark.parametrize("lingua", LINGUE)
def test_anche_la_gemella_javascript_riconosce_la_nota(lingua):
    """Le due espressioni sono scritte in due linguaggi e in due file: la
    prova che restano d'accordo va fatta sul sorgente vero, non a memoria."""
    js = Path("static/js/app.js").read_text(encoding="utf-8")
    modelli = re.findall(r'\.replace\(/\^> (\S+) \\\*\.\*\$/gm, ""\)', js)
    assert modelli, "le espressioni gemelle in app.js non ci sono piu'"
    nota = [r for r in nota_elaborazione(lingua).split("\n") if r.strip()][-1]
    gemella = re.compile(r"^> (?:%s) \*.*$" % "|".join(map(re.escape, modelli)), re.M)
    assert gemella.match(nota), f"app.js non toglierebbe piu' la nota in {lingua}"


# ── 3. la lingua non sceglie i riconoscitori ────────────────────────────


@pytest.mark.parametrize("lingua", LINGUE)
def test_i_segnaposto_non_si_traducono(lingua, tmp_path):
    """`{{CODICE_FISCALE}}` resta tale anche in inglese: nomina lo strumento,
    non l'interfaccia, e c'e' chi ha uno script che lo cerca."""
    r = convert_bytes(
        TESTO.encode(),
        "nota.txt",
        options=ConvertOptions(lingua=lingua, include_frontmatter=False),
    )
    assert "{{CODICE_FISCALE_1}}" in r.markdown
    assert "{{EMAIL_1}}" in r.markdown


# ── 4. anche gli errori del server rispondono nella lingua giusta ───────


@pytest.fixture()
def client():
    from mr_rao.app_factory import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


BASE = "http://127.0.0.1:5000"


def test_l_errore_json_segue_la_lingua_del_modulo(client):
    """Il campo `lang` lo manda la pagina: e' l'unico che sa cosa l'utente
    sta guardando adesso."""
    import io

    def errore(lingua):
        r = client.post(
            "/api/convert/sync",
            data={"lang": lingua, "file": (io.BytesIO(b"x"), "prova.exe")},
            content_type="multipart/form-data",
            base_url=BASE,
            headers={"Origin": BASE},
        )
        return r.get_json()["error"]

    assert "is not supported" in errore("en")
    assert "non supportato" in errore("it")


def test_l_errore_json_segue_il_cookie_quando_non_c_e_il_modulo(client):
    """Chi ha cliccato il selettore ha detto qualcosa di piu' preciso del
    suo browser, e vale anche per un endpoint che non riceve moduli."""
    client.set_cookie("mr_rao_lang", "en", domain="127.0.0.1")
    r = client.get("/api/jobs/inesistente", base_url=BASE)
    assert r.get_json()["error"] == "Job not found"


def test_la_lingua_inglese_non_spegne_i_riconoscitori_italiani():
    """Uno studio italiano che tiene la pagina in inglese converte comunque
    fatture italiane. Togliergli il codice fiscale senza dirglielo sarebbe un
    peggioramento silenzioso della protezione."""
    opts = dict(privacy=PrivacyOptions(), include_frontmatter=False)
    it = convert_bytes(TESTO.encode(), "n.txt", options=ConvertOptions(lingua="it", **opts))
    en = convert_bytes(TESTO.encode(), "n.txt", options=ConvertOptions(lingua="en", **opts))
    assert it.redaction.total == en.redaction.total
    assert it.redaction.counts == en.redaction.counts
