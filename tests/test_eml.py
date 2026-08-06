from email.message import EmailMessage

from mr_rao.eml_parser import html_to_text, parse_eml, split_thread


def test_html_to_text_strips_tags():
    html = "<html><head><style>x{}</style></head><body><p>Ciao</p><br><b>Mondo</b></body></html>"
    text = html_to_text(html)
    assert "Ciao" in text
    assert "Mondo" in text
    assert "<p>" not in text
    assert "style" not in text.lower() or "x{}" not in text


def test_split_thread_english():
    body = "Latest reply here\n\nOn Mon, Aug 5, 2026, John Doe wrote:\n> older message"
    segs = split_thread(body)
    assert len(segs) >= 1
    assert "Latest reply" in segs[0]


def test_split_thread_italian():
    body = "Risposta nuova\n\nIl giorno 5 ago 2026, Mario Rossi ha scritto:\nvecchio"
    segs = split_thread(body)
    assert "Risposta nuova" in segs[0]


def test_parse_eml_file(tmp_path):
    msg = EmailMessage()
    msg["Subject"] = "Test Mr Rao"
    msg["From"] = "a@example.com"
    msg["To"] = "b@example.com"
    msg["Date"] = "Wed, 06 Aug 2026 10:00:00 +0000"
    msg.set_content("Ciao dal test.\n\nOn yesterday someone wrote:\nquoted part")

    path = tmp_path / "sample.eml"
    path.write_bytes(msg.as_bytes())

    md = parse_eml(path)
    assert "Test Mr Rao" in md
    assert "Ciao dal test" in md
    assert "Ultimo messaggio" in md
