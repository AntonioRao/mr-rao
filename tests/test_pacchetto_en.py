"""Il banco a due corpora, in inglese.

Stessa disciplina dell'italiano: una mail dove tutto deve sparire, e un
documento amministrativo dove **non deve sparire niente**. Il secondo conta
piu' del primo, perche' e' l'unico numero che non si puo' migliorare
allargando i riconoscitori.

Che serva non e' un'ipotesi. Prima del pacchetto `en`, il motore italiano
applicato al documento amministrativo inglese produceva **22 sostituzioni
su un testo che non contiene un solo dato personale** -- ventuno nomi piu'
un numero di protocollo scambiato per un recapito. Lo stesso e' successo su
un modulo fiscale statunitense in bianco, scaricato dall'IRS: 22 falsi
positivi su una pagina vuota.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from mr_rao.privacy import (
    CORE,
    EN,
    IT,
    PrivacyOptions,
    apply_privacy_filter,
)

DATI = Path(__file__).resolve().parent / "dati"
EMAIL = DATI / "corpus_en_email.txt"
ADMIN = DATI / "corpus_en_admin.txt"

SOLO_EN = PrivacyOptions(pacchetti=(CORE, EN))


def _leggi(p: Path) -> str:
    assert p.is_file(), f"manca il corpus {p}"
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Il documento che deve restare intatto
# ---------------------------------------------------------------------------


def test_il_documento_amministrativo_resta_a_zero():
    """Il criterio della fase 2. Se questo sale, il pacchetto e' peggiorato
    anche se tutti gli altri numeri sono migliorati."""
    out, rep = apply_privacy_filter(_leggi(ADMIN), SOLO_EN)
    assert rep.total == 0, f"falsi positivi: {rep.counts}"
    assert out == _leggi(ADMIN)


def test_il_corpus_amministrativo_contiene_davvero_le_trappole():
    """Un corpus annacquato tiene il test verde senza provare niente.

    Queste parole sono nomi propri inglesi comunissimi usati come parole
    comuni: sono la ragione per cui l'euristica italiana dei nomi qui
    esplode, e devono restare nel file.
    """
    testo = _leggi(ADMIN)
    for trappola in (
        "Mark", "Bill", "Grace", "May", "June", "Rose",
        "Brown", "Green", "Baker", "Price", "Young", "Church", "Sterling",
        "Baker & Price", "Church Road", "Green Lane",
        "Project Manager", "Data Protection Officer",
        "0034578921",  # dieci cifre: sembra un NHS number, e' un protocollo
        "078051120",   # nove cifre: sembra un SSN, e' un numero di lotto
    ):
        assert trappola in testo, f"il corpus ha perso la trappola {trappola!r}"


def test_le_nove_cifre_senza_contesto_non_si_toccano():
    """Il SSN non ha checksum: nove cifre nude passano il controllo
    strutturale quasi nove volte su dieci. Senza i trattini o una parola
    accanto, si lasciano stare."""
    _, rep = apply_privacy_filter("Asset register batch: 078051120", SOLO_EN)
    assert rep.total == 0


def test_il_numero_di_protocollo_non_e_un_telefono():
    """Regressione. "0034578921" veniva letto come prefisso internazionale
    00 piu' Spagna, e redatto: trovato su un documento vero."""
    out, rep = apply_privacy_filter("Protocol number: 0034578921", SOLO_EN)
    assert "{{PHONE}}" not in out
    assert rep.total == 0


def test_il_prefisso_internazionale_vero_resta_riconosciuto():
    """L'altra meta' della correzione qui sopra: il primo tentativo
    cercava il separatore nel solo corpo del numero, e faceva cadere
    "0039 3391234567", dove lo spazio sta fra prefisso e corpo."""
    out, _ = apply_privacy_filter("Tel 0039 3391234567", SOLO_EN)
    assert "{{PHONE}}" in out


# ---------------------------------------------------------------------------
# La mail dove tutto deve sparire
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "categoria,segnaposto",
    [
        ("ssn", "{{SSN}}"),
        ("itin", "{{ITIN}}"),
        ("nhs_number", "{{NHS_NUMBER}}"),
        ("routing_number", "{{ROUTING_NUMBER}}"),
        ("iban", "{{IBAN}}"),
        ("cards", "{{CARD}}"),
        ("emails", "{{EMAIL}}"),
    ],
)
def test_la_mail_perde_gli_identificativi(categoria, segnaposto):
    out, rep = apply_privacy_filter(_leggi(EMAIL), SOLO_EN)
    assert rep.counts.get(categoria), f"{categoria} non riconosciuto"
    assert segnaposto in out


@pytest.mark.parametrize(
    "residuo",
    [
        "078-05-1120",                  # SSN
        "912-70-4455",                  # ITIN
        "943 476 5919",                 # NHS number
        "021000021",                    # routing ABA
        "GB29 NWBK 6016 1331 9268 19",  # IBAN
        "4111 1111 1111 1111",          # carta
    ],
)
def test_nessun_identificativo_sopravvive_nella_mail(residuo):
    out, _ = apply_privacy_filter(_leggi(EMAIL), SOLO_EN)
    assert residuo not in out


def test_il_nino_sparisce():
    out, rep = apply_privacy_filter("His NI number is AB 12 34 56 C.", SOLO_EN)
    assert rep.counts.get("nino") == 1
    assert "{{NINO}}" in out


def test_il_nino_di_esempio_diventa_un_sospetto():
    """`QQ` e' il prefisso che gov.uk usa negli esempi **proprio perche'**
    non viene mai emesso. Rifiutarlo e' giusto; tacere no: la stessa forma
    la produce un OCR che ha storpiato le due lettere di un NINO vero."""
    out, rep = apply_privacy_filter("Old entry: QQ 12 34 56 C", SOLO_EN)
    assert "QQ 12 34 56 C" in out
    assert not rep.counts.get("nino")
    assert [s for s in rep.suspects if s["kind"] == "nino"]


# ---------------------------------------------------------------------------
# Il limite, dichiarato
# ---------------------------------------------------------------------------


def test_i_nomi_inglesi_non_sono_ancora_coperti():
    """Questo test **passa perche' il motore non fa una cosa**.

    Non e' una svista: e' il divario dichiarato nella issue #1. Il
    pacchetto `en` copre gli identificativi, non i nomi di persona, e
    finche' e' cosi' e' meglio che sia scritto in un test che qualcuno
    dovra' cancellare di proposito, invece che in un commento che nessuno
    legge. Quando arriveranno i nomi inglesi, questo test va **sostituito**
    con quelli veri, non tolto e basta.
    """
    out, rep = apply_privacy_filter("Dear Mr Daniel Okonkwo,", SOLO_EN)
    assert "Okonkwo" in out
    assert not rep.counts.get("names")


def test_col_pacchetto_italiano_insieme_i_nomi_tornano():
    """I pacchetti sono cumulabili, ed e' il caso d'uso vero: lo studio
    italiano che segue il cliente inglese. Qui l'euristica italiana copre
    -- male, ma copre -- il buco dei nomi."""
    out, rep = apply_privacy_filter(
        "Dear Mr Daniel Okonkwo,", PrivacyOptions(pacchetti=(CORE, IT, EN))
    )
    assert rep.counts.get("names")
    assert "Okonkwo" not in out
