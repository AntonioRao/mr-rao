import pytest

from mr_rao.privacy import (
    PrivacyOptions,
    apply_privacy_filter,
    iban_checksum_ok,
    options_from_dict,
    options_from_form,
)

SOLO_TELEFONI = PrivacyOptions(
    emails=False, names=False, fiscal=False, phones=True,
    amounts=False, use_scrubadub=False,
)
SOLO_IMPORTI = PrivacyOptions(
    emails=False, names=False, fiscal=False, phones=False,
    amounts=True, use_scrubadub=False,
)
SOLO_FISCALE = PrivacyOptions(
    emails=False, names=False, fiscal=True, phones=False,
    amounts=False, use_scrubadub=False,
)


def test_scrub_email():
    text = "Contattami a mario.rossi@example.com grazie"
    out, report = apply_privacy_filter(text, PrivacyOptions(use_scrubadub=False))
    assert "mario.rossi@example.com" not in out
    assert "{{EMAIL}}" in out
    assert report.counts.get("emails", 0) >= 1


def test_scrub_cf():
    # Synthetic CF-like pattern (not a real person's code)
    text = "CF: RSSMRA80A01H501U fine"
    out, report = apply_privacy_filter(
        text,
        PrivacyOptions(emails=False, phones=False, names=False, fiscal=True, use_scrubadub=False),
    )
    assert "RSSMRA80A01H501U" not in out.upper() or "{{CODICE_FISCALE}}" in out
    assert report.total >= 1


def test_scrub_iban():
    text = "Bonifico su IT60X0542811101000000123456"
    out, report = apply_privacy_filter(
        text,
        PrivacyOptions(emails=False, phones=False, names=False, fiscal=True, use_scrubadub=False),
    )
    assert "{{IBAN}}" in out
    assert report.counts.get("iban", 0) >= 1


def test_scrub_phone_it():
    text = "Chiamami al +39 333 1234567 domani"
    out, report = apply_privacy_filter(
        text,
        PrivacyOptions(emails=False, phones=True, names=False, fiscal=False, use_scrubadub=False),
    )
    assert "{{PHONE}}" in out
    assert report.counts.get("phones", 0) >= 1


def test_privacy_off():
    text = "email test@example.com"
    out, report = apply_privacy_filter(
        text,
        PrivacyOptions(
            emails=False,
            phones=False,
            names=False,
            fiscal=False,
            amounts=False,
            use_scrubadub=False,
        ),
    )
    assert "test@example.com" in out
    assert report.total == 0


# ---------------------------------------------------------------------------
# Regressioni sui falsi positivi: la redazione non deve rovinare il documento
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "testo",
    [
        "protocollo 0123456789 del 2026",
        "numero pratica 0987654321",
        "codice articolo 0123456",
    ],
)
def test_numeri_non_telefonici_restano(testo):
    """Una sequenza di cifre senza prefisso, separatori o parola di contesto
    non è un telefono: prima 'protocollo 0123456789' diventava {{PHONE}}."""
    out, report = apply_privacy_filter(testo, SOLO_TELEFONI)
    assert out == testo
    assert report.total == 0


@pytest.mark.parametrize(
    "testo",
    [
        "Chiamami al +39 333 1234567 domani",
        "fisso 06 12345678",
        "Tel. 0123456789",
        "cellulare: 3331234567",
        "0039 3391234567",
        "chiama 06-1234567",
    ],
)
def test_telefoni_veri_vengono_redatti(testo):
    out, report = apply_privacy_filter(testo, SOLO_TELEFONI)
    assert "{{PHONE}}" in out, testo
    assert report.counts.get("phones", 0) >= 1


@pytest.mark.parametrize(
    "testo",
    [
        "Versione 1.10 del documento",
        "articolo 3.14 del regolamento",
        "capitolo 2.50 pagina 4",
    ],
)
def test_numeri_non_monetari_restano_intatti(testo):
    """Due bug in uno: il numero veniva preso per un importo e il gruppo
    valuta finale si mangiava anche lo spazio ('{{AMOUNT}}del documento')."""
    out, report = apply_privacy_filter(testo, SOLO_IMPORTI)
    assert out == testo
    assert report.total == 0


@pytest.mark.parametrize(
    "testo",
    [
        "Totale € 1.500,00 IVA inclusa",
        "saldo 250,00 da versare",
        "compenso 12,50 EUR",
        "canone 1.234,56 annuo",
        "prezzo 99,90 euro",
    ],
)
def test_importi_veri_vengono_redatti(testo):
    out, report = apply_privacy_filter(testo, SOLO_IMPORTI)
    assert "{{AMOUNT}}" in out, testo
    assert report.counts.get("amounts", 0) >= 1


def test_importo_non_divora_lo_spazio_successivo():
    out, _ = apply_privacy_filter("Totale 1.500,00 da pagare", SOLO_IMPORTI)
    assert "{{AMOUNT}} da pagare" in out


@pytest.mark.parametrize(
    ("candidato", "valido"),
    [
        ("IT60X0542811101000000123456", True),
        ("DE89370400440532013000", True),
        ("FR1420041010050500013M02606", True),
        ("AB12CDEFGHIJKLM", False),   # checksum sbagliato
        ("IT99X0542811101000000123456", False),  # cifre di controllo alterate
    ],
)
def test_iban_checksum(candidato, valido):
    assert iban_checksum_ok(candidato) is valido


def test_token_simil_iban_non_viene_redatto():
    """Il pattern da solo matchava anche parole minuscole: ora vale il mod-97."""
    testo = "riferimento AB12CDEFGHIJKLM e sigla ab12cdefghijklm"
    out, report = apply_privacy_filter(testo, SOLO_FISCALE)
    assert out == testo
    assert report.counts.get("iban", 0) == 0


# ---------------------------------------------------------------------------
# Default fail-safe: chi non dice nulla ottiene la redazione, non il testo in chiaro
# ---------------------------------------------------------------------------


def test_options_from_form_redige_per_default():
    opts = options_from_form({})
    assert opts.emails is True
    assert opts.phones is True
    assert opts.fiscal is True


def test_options_from_dict_redige_per_default():
    assert options_from_dict({}).emails is True
    assert options_from_dict(None).emails is True


def test_privacy_filter_false_resta_rispettato():
    opts = options_from_form({"privacy_filter": "false"})
    assert opts.emails is False
    assert opts.use_scrubadub is False


def test_italian_name():
    text = "Firma: Mario Rossi — cordiali saluti"
    out, report = apply_privacy_filter(
        text,
        PrivacyOptions(emails=False, phones=False, names=True, fiscal=False, use_scrubadub=False),
    )
    assert "{{NAME}}" in out or report.counts.get("names", 0) >= 1
