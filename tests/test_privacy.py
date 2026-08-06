from mr_rao.privacy import PrivacyOptions, apply_privacy_filter


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


def test_italian_name():
    text = "Firma: Mario Rossi — cordiali saluti"
    out, report = apply_privacy_filter(
        text,
        PrivacyOptions(emails=False, phones=False, names=True, fiscal=False, use_scrubadub=False),
    )
    assert "{{NAME}}" in out or report.counts.get("names", 0) >= 1
