"""I sospetti: cio' che somiglia a un dato personale ed e' rimasto.

Il limite piu' serio del motore e' che i riconoscitori cercano forme
*valide* mentre l'OCR produce forme *quasi* valide. `A01` letto `AD1`,
`IT60` letto `lT60`: la struttura non torna, il dato resta nel testo, e
resta perfettamente leggibile da una persona.

Sostituire senza certezza vorrebbe dire redigere mezzo documento. Ma
tacere e' peggio, perche' «3 redazioni» su un documento pulito e «3
redazioni» su un documento che il riconoscitore non ha saputo leggere
sono lo stesso numero e due situazioni opposte.

Questi test verificano le due meta' della promessa: che i sospetti
compaiano dove servono, e che **non** compaiano dove non servono.
"""
import pytest

from mr_rao.privacy import (
    PrivacyOptions,
    apply_privacy_filter,
    cf_check_char_ok,
    no_redaction,
)

# Il verbale amministrativo: nessun dato personale, e nemmeno un sospetto.
VERBALE = """Verbale della riunione del Comitato Tecnico

Il Consiglio di Amministrazione ha approvato il Piano Industriale 2024-2026.
Protocollo 0123456789, delibera 45, versione 3.10, pratica 2024/118.
Registrata il 01.02.2024. Codice Identificativo Gara 1234567890AB.
"""


# ---------------------------------------------------------------------------
# Carattere di controllo del codice fiscale
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cf,valido",
    [
        ("RSSMRA85T10A562S", True),
        ("MRTMTT25D09F205Z", True),
        ("RSSMRA85T10A562X", False),   # ultimo carattere alterato
        ("RSSMRA 85T10 A562S", True),  # con spazi
        ("RSSMRA-85T10-A562S", True),  # con trattini
        ("non-un-codice", False),
    ],
)
def test_carattere_di_controllo(cf, valido):
    assert cf_check_char_ok(cf) is valido


def test_il_codice_fiscale_alterato_viene_comunque_sostituito():
    """Su un dato personale l'errore va fatto nella direzione prudente."""
    out, rep = apply_privacy_filter("CF RSSMRA85T10A562X", PrivacyOptions())
    assert "{{CODICE_FISCALE}}" in out
    assert rep.counts.get("codice_fiscale") == 1


def test_ma_viene_segnalato_come_sospetto():
    """Struttura giusta e controllo sbagliato: quasi sempre il documento
    viene da un OCR, e allora avra' storpiato anche altro."""
    _, rep = apply_privacy_filter("CF RSSMRA85T10A562X", PrivacyOptions())
    tipi = [s["kind"] for s in rep.suspects]
    assert "codice_fiscale" in tipi


def test_un_codice_fiscale_valido_non_genera_sospetti():
    _, rep = apply_privacy_filter("CF RSSMRA85T10A562S", PrivacyOptions())
    assert rep.suspects == []


# ---------------------------------------------------------------------------
# Residui da OCR
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "testo,tipo",
    [
        ("Il codice e RSSMRA85T1OA562S sul modulo", "codice_fiscale"),
        ("IBAN lT60X0542811101000000123456 della banca", "iban"),
        ("cell. 335 l23 4567 per urgenze", "telefono"),
    ],
)
def test_le_forme_quasi_valide_diventano_sospetti(testo, tipo):
    out, rep = apply_privacy_filter(testo, PrivacyOptions())
    assert out == testo, "senza certezza non si sostituisce"
    assert tipo in [s["kind"] for s in rep.suspects], rep.suspects


def test_il_sospetto_e_mascherato():
    """Serve a ritrovarlo nel documento, non a leggerlo: il rapporto puo'
    finire in un log o in una scheda a video."""
    _, rep = apply_privacy_filter("Il codice e RSSMRA85T1OA562S", PrivacyOptions())
    campione = rep.suspects[0]["sample"]
    assert "RSSMRA85T1OA562S" not in campione
    assert campione.startswith("RS") and campione.endswith("2S")
    assert "•" in campione


# ---------------------------------------------------------------------------
# Il contrario: niente rumore
# ---------------------------------------------------------------------------


def test_un_documento_pulito_non_genera_sospetti():
    """Se ogni protocollo diventasse un sospetto, l'avviso non varrebbe
    piu' niente e la gente smetterebbe di guardarlo."""
    _, rep = apply_privacy_filter(VERBALE, PrivacyOptions())
    assert rep.total == 0
    assert rep.suspects == [], rep.suspects


def test_niente_sospetti_a_riconoscitori_spenti():
    """Chi ha spento la redazione non vuole nemmeno gli avvisi."""
    _, rep = apply_privacy_filter("RSSMRA85T1OA562S", no_redaction())
    assert rep.suspects == []


def test_il_rapporto_espone_il_conteggio():
    _, rep = apply_privacy_filter("Il codice e RSSMRA85T1OA562S", PrivacyOptions())
    d = rep.to_dict()
    assert d["suspects_total"] == len(d["suspects"]) >= 1
