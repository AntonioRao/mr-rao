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


def test_la_nota_non_passa_dal_filtro_privacy(tmp_path):
    """Mr. Rao non deve anonimizzare se stesso.

    La nota in fondo alle email diceva «Documento elaborato da Mr. Rao», e
    «Mr.» e' un titolo esattamente come «Dott.» o «Ing.»: usciva
    «Mr. {{NAME}}». Buffo, ma il danno vero era un altro — quella
    sostituzione **entrava nel conteggio**, e il numero di redazioni che
    chiediamo all'utente di controllare risultava gonfiato di uno su ogni
    singola email convertita.
    """
    from email.message import EmailMessage

    from mr_rao.converter import ConvertOptions, convert_file

    msg = EmailMessage()
    msg["Subject"] = "Prova"
    msg["From"] = "Mario Rossi <m.rossi@example.it>"
    msg["To"] = "destinatario@example.it"
    msg.set_content("Ciao, scrivimi a m.rossi@example.it")
    percorso = tmp_path / "prova.eml"
    percorso.write_bytes(msg.as_bytes())

    r = convert_file(percorso, options=ConvertOptions(include_frontmatter=False))

    assert "Mr. Rao." in r.markdown
    assert "Mr. {{NAME}}" not in r.markdown
    # Un solo nome nel documento: quello del mittente. Non due.
    assert r.redaction.counts.get("names", 0) == 1


def test_il_parser_non_aggiunge_piu_la_nota():
    """La nota la mette convert_file a valle. Se tornasse dentro parse_eml
    tornerebbe anche il conteggio sbagliato, senza che nulla si rompa."""
    import inspect

    from mr_rao import eml_parser

    assert "Documento elaborato" not in inspect.getsource(eml_parser.parse_eml)
    assert "Documento elaborato" in eml_parser.nota_elaborazione()
