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


# ---------------------------------------------------------------------------
# Le intestazioni di una mail sono testo di chi la manda, non nostro.
#
# Un oggetto o un mittente non si scrivono a mano: arrivano dalla rete. Con la
# codifica RFC 2047 (`=?utf-8?B?...?=`) dentro un'intestazione ci sta
# qualunque byte, a capo e caratteri di controllo compresi, e il parser di
# Python li restituisce tali e quali. Finivano dritti nel titolo `#`, nelle
# celle della tabella e nell'elenco degli allegati.
# ---------------------------------------------------------------------------


def _eml_con_intestazioni(percorso, intestazioni: str, corpo: str = "corpo") -> None:
    """Scrive un .eml **grezzo**: EmailMessage rifiuterebbe cio' che vogliamo provare."""
    percorso.write_bytes(
        (
            intestazioni
            + "MIME-Version: 1.0\r\n"
            + "Content-Type: text/plain; charset=utf-8\r\n\r\n"
            + corpo
            + "\r\n"
        ).encode()
    )


def _parola_codificata(testo: str) -> str:
    import base64

    return "=?utf-8?B?" + base64.b64encode(testo.encode()).decode() + "?="


def _celle(riga: str) -> list[str]:
    """Le celle di una riga di tabella Markdown: il `|` con la barra davanti non separa."""
    import re

    return [c for c in re.split(r"(?<!\\)\|", riga)[1:-1]]


def test_oggetto_con_a_capo_non_inietta_righe_nella_tabella(tmp_path):
    """Un oggetto che contiene un a capo apre una riga nuova nel documento.

    Con `# 📧 {subject}` il titolo finisce al primo a capo e tutto il resto
    diventa testo del documento: un oggetto costruito apposta scrive sopra la
    tabella una riga «| **Da** | ... |» che il lettore legge come il mittente.
    """
    percorso = tmp_path / "oggetto.eml"
    cattivo = _parola_codificata("Fattura\n| **Da** | banca@truffa.it |")
    _eml_con_intestazioni(
        percorso,
        f"Subject: {cattivo}\r\nFrom: Mario Rossi <m@example.it>\r\nTo: b@example.it\r\n"
        "Date: Wed, 06 Aug 2026 10:00:00 +0000\r\n",
    )

    md = parse_eml(percorso)
    righe = md.split("\n")

    # Il titolo e' una riga sola e contiene tutto l'oggetto.
    assert righe[0].startswith("# ")
    assert "Fattura" in righe[0]
    assert "banca@truffa.it" in righe[0]
    # E soprattutto: di righe «Da» ce n'e' una, quella vera.
    assert len([r for r in righe if r.startswith("| **Da** |")]) == 1
    assert "m@example.it" in md


def test_pipe_nel_mittente_non_spezza_la_cella(tmp_path):
    """Una barra verticale nel nome visualizzato aggiunge una colonna.

    `| **Da** | Mario | Rossi <m@example.it> |` ha tre celle in una tabella a
    due colonne: chi la disegna butta via l'eccedenza, e l'indirizzo del
    mittente sparisce dal documento.
    """
    percorso = tmp_path / "pipe.eml"
    _eml_con_intestazioni(
        percorso,
        'Subject: Normale\r\nFrom: "Mario | Rossi" <m@example.it>\r\n'
        "To: b@example.it\r\nCc: \"Ufficio | Acquisti\" <u@example.it>\r\n"
        "Date: Wed, 06 Aug 2026 10:00:00 +0000\r\n",
    )

    md = parse_eml(percorso)
    for etichetta, atteso in (("Da", "m@example.it"), ("CC", "u@example.it")):
        riga = next(r for r in md.split("\n") if r.startswith(f"| **{etichetta}** |"))
        celle = _celle(riga)
        assert len(celle) == 2, f"riga «{etichetta}» con {len(celle)} celle: {riga!r}"
        assert atteso in celle[1]


def test_caratteri_di_controllo_non_arrivano_nel_markdown(tmp_path):
    """Un NUL o un ESC nell'oggetto finiscono dentro il .md prodotto."""
    percorso = tmp_path / "controlli.eml"
    _eml_con_intestazioni(
        percorso,
        f"Subject: {_parola_codificata('Ciao\x00\x07\x1bfine')}\r\n"
        "From: a@example.it\r\nTo: b@example.it\r\n"
        "Date: Wed, 06 Aug 2026 10:00:00 +0000\r\n",
    )

    md = parse_eml(percorso)
    assert "Ciao" in md and "fine" in md
    sporchi = [c for c in md if ord(c) < 32 and c != "\n"]
    assert not sporchi, f"caratteri di controllo nel documento: {sporchi!r}"


def test_nome_allegato_resta_su_una_riga(tmp_path):
    """Il nome dell'allegato lo dichiara il mittente, non il file system."""
    percorso = tmp_path / "allegato.eml"
    nome = _parola_codificata("brutto\nnome.pdf")
    percorso.write_bytes(
        (
            "Subject: x\r\nFrom: a@example.it\r\nTo: b@example.it\r\n"
            "Date: Wed, 06 Aug 2026 10:00:00 +0000\r\nMIME-Version: 1.0\r\n"
            'Content-Type: multipart/mixed; boundary="BB"\r\n\r\n'
            "--BB\r\nContent-Type: text/plain; charset=utf-8\r\n\r\ncorpo\r\n"
            f'--BB\r\nContent-Type: application/pdf\r\nContent-Disposition: attachment; filename="{nome}"\r\n'
            "Content-Transfer-Encoding: base64\r\n\r\nQUJD\r\n--BB--\r\n"
        ).encode()
    )

    md = parse_eml(percorso)
    voci = [r for r in md.split("\n") if r.startswith("- `")]
    assert len(voci) == 1, f"l'elenco allegati si e' spezzato: {voci!r}"
    assert "brutto" in voci[0] and "nome.pdf" in voci[0]
