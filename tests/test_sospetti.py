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
    "testo,storpiato",
    [
        ("Il codice e RSSMRA85T1OA562S sul modulo", "RSSMRA85T1OA562S"),
        ("Il codice e RSSMRA85TIOA562S sul modulo", "RSSMRA85TIOA562S"),
        ("IBAN lT60X0542811101000000123456 della banca", "lT60X0542811101000000123456"),
        ("IBAN IT6OX0542811101000000123456 della banca", "IT6OX0542811101000000123456"),
    ],
)
def test_i_codici_storpiati_dall_ocr_vengono_recuperati(testo, storpiato):
    """Non e' un'euristica a decidere, e' l'aritmetica: si prova a
    correggere fino a due caratteri e si sostituisce **solo** se il
    checksum del candidato torna."""
    out, rep = apply_privacy_filter(testo, PrivacyOptions())
    assert storpiato not in out
    assert rep.counts.get("ocr_corretti", 0) >= 1, rep.counts


def test_il_recupero_non_inventa_codici():
    """Il checksum protegge dai candidati sbagliati, non da uno spazio di
    candidati troppo largo: il numero d'ordine 5551234567890123 diventava
    «SS51234567890123», che il mod-97 lo supera davvero."""
    testo = "Ordine 5551234567890123 del magazzino"
    out, rep = apply_privacy_filter(testo, PrivacyOptions())
    assert out == testo, out
    assert rep.total == 0


@pytest.mark.parametrize(
    "testo,tipo",
    [
        ("cell. 335 l23 4567 per urgenze", "telefono"),
        ("Riferimento ABCDEF12G34H567I in atti", "codice_fiscale"),
        ("P.IVA 01234567890 della ditta", "partita_iva"),
    ],
)
def test_cio_che_il_recupero_non_chiude_resta_un_sospetto(testo, tipo):
    """I sospetti servono per quello che il checksum non puo' salvare:
    un telefono non ha cifra di controllo, e un codice che nemmeno
    correggendolo torna non si puo' sostituire per somiglianza."""
    _, rep = apply_privacy_filter(testo, PrivacyOptions())
    assert tipo in [s["kind"] for s in rep.suspects], rep.suspects


def test_il_sospetto_e_mascherato():
    """Serve a ritrovarlo nel documento, non a leggerlo: il rapporto puo'
    finire in un log o in una scheda a video."""
    _, rep = apply_privacy_filter("Riferimento ABCDEF12G34H567I", PrivacyOptions())
    campione = rep.suspects[0]["sample"]
    assert "ABCDEF12G34H567I" not in campione
    assert campione.startswith("AB") and campione.endswith("7I")
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
    _, rep = apply_privacy_filter("Riferimento ABCDEF12G34H567I", PrivacyOptions())
    d = rep.to_dict()
    assert d["suspects_total"] == len(d["suspects"]) >= 1


# ---------------------------------------------------------------------------
# Forme che nella vita reale sono la norma, e il motore non vedeva
# ---------------------------------------------------------------------------


def test_iban_scritto_a_gruppi_di_quattro():
    """E' come lo stampano le banche su carta intestata, bonifici e
    fatture. Il riconoscitore pretendeva i caratteri attaccati, quindi
    sulla forma piu' comune di tutte non trovava niente."""
    out, rep = apply_privacy_filter(
        "IBAN IT60 X054 2811 1010 0000 0123 456", PrivacyOptions()
    )
    assert out == "IBAN {{IBAN}}"
    assert rep.counts.get("iban") == 1


def test_un_iban_a_gruppi_sbagliato_resta():
    """Anche qui decide il mod-97, non la forma."""
    testo = "IBAN IT60 X054 2811 1010 0000 0123 457"
    out, _ = apply_privacy_filter(testo, PrivacyOptions())
    assert out == testo


@pytest.mark.parametrize(
    "testo",
    [
        "scrivi a mario [at] esempio [dot] it",
        "mario (at) esempio (punto) it",
        "mario chiocciola esempio punto it",
    ],
)
def test_email_offuscate(testo):
    """Chi scrive cosi' lo fa apposta perche' non sembri un'email — e
    infatti al riconoscitore non sembrava."""
    out, rep = apply_privacy_filter(testo, PrivacyOptions())
    assert "{{EMAIL}}" in out
    assert "esempio" not in out


def test_la_partita_iva_ha_la_sua_cifra_di_controllo():
    from mr_rao.privacy import piva_check_ok

    assert piva_check_ok("01234567897") is True
    assert piva_check_ok("00743110157") is True
    assert piva_check_ok("01234567890") is False
