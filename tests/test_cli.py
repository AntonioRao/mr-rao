# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
from mr_rao.cli import main


def test_cli_health():
    assert main(["health"]) == 0


def test_cli_convert_txt(tmp_path):
    src = tmp_path / "x.txt"
    src.write_text("cli test content", encoding="utf-8")
    out = tmp_path / "out.md"
    code = main(
        [
            "convert",
            str(src),
            "-o",
            str(out),
            "--no-privacy",
            "--no-tables",
        ]
    )
    assert code == 0
    assert out.exists()
    assert "cli test content" in out.read_text(encoding="utf-8")


# --- P0.1 e P0.2: l'esito di una conversione non deve sparire -------------
#
# Il tasto destro converte e chiude la finestra all'istante. Restava un .md
# e nessuna idea di cosa fosse stato tolto -- e i *sospetti*, cioe' cio' che
# somiglia a un dato personale ed e' rimasto nel testo, la riga di comando
# non li stampava affatto: vivevano solo nell'interfaccia web.
#
# Il percorso piu' comodo, e quindi il piu' usato, saltava in silenzio il
# controllo che PRIVACY.md chiama «quello che conta».

_SPORCO = (
    "Contatta mario.rossi@example.it al 335 123 4567.\n"
    "Codice fiscale letto male: RSSMRA85T1OA562X\n"
)
_PULITO = "Verbale del Comitato Tecnico. Protocollo 0123456789, Fase Uno.\n"


def _converti(tmp_path, capsys, testo, *extra):
    from mr_rao.cli import main

    src = tmp_path / "documento.txt"
    src.write_text(testo, encoding="utf-8")
    codice = main(["convert", str(src), "-o", str(tmp_path / "out.md"), *extra])
    return codice, capsys.readouterr().out


def test_la_riga_di_comando_stampa_i_sospetti(tmp_path, capsys):
    """Erano il segnale piu' importante, e mancava dal percorso piu' usato."""
    codice, uscita = _converti(tmp_path, capsys, _SPORCO)
    assert codice == 0
    assert "redazioni" in uscita
    assert "da controllare" in uscita
    assert "codice_fiscale" in uscita
    # E il perche', non solo il fatto.
    assert "struttura non torna" in uscita


def test_il_campione_e_mascherato_e_leggibile_ovunque(tmp_path, capsys):
    """Il pallino U+2022 non esiste in cp1252: su una console italiana
    diventerebbe un punto interrogativo, cioe' il carattere che segnala un
    guasto. L'asterisco si legge uguale ovunque."""
    _, uscita = _converti(tmp_path, capsys, _SPORCO)
    assert "•" not in uscita
    assert "RS************2X" in uscita
    # mascherato davvero: il codice per esteso non deve comparire
    assert "RSSMRA85T1OA562X" not in uscita


def test_un_documento_pulito_non_ha_niente_da_dire(tmp_path, capsys):
    """Fermarsi anche a mani vuote insegnerebbe a chiudere senza leggere."""
    codice, uscita = _converti(tmp_path, capsys, _PULITO)
    assert codice == 0
    assert "0 redazioni" in uscita
    assert "da controllare" not in uscita


def test_attendi_non_blocca_quando_nessuno_puo_premere(tmp_path, capsys):
    """In una pipeline non c'e' una console: senza questa guardia la
    conversione resterebbe appesa per sempre su una macchina di build."""
    codice, uscita = _converti(tmp_path, capsys, _SPORCO, "--attendi")
    assert codice == 0
    assert "Premi Invio" not in uscita


def test_il_tasto_destro_chiede_di_attendere():
    """Se `--attendi` sparisse dal .bat, la finestra tornerebbe a chiudersi
    sui sospetti e nessun test se ne accorgerebbe."""
    from pathlib import Path

    bat = Path(__file__).resolve().parents[1] / "scripts" / "open_with_mr_rao.bat"
    # Solo le righe che invocano davvero. Il nome dell'opzione compare anche
    # nel commento che ne spiega la ragione, e contarlo li' terrebbe il test
    # verde su un .bat che ha smesso di passarla.
    invocazioni = [
        r
        for r in bat.read_text(encoding="utf-8", errors="replace").splitlines()
        if "mr_rao.cli convert" in r and not r.lstrip().upper().startswith("REM ")
    ]
    assert invocazioni, "il .bat non invoca piu' la conversione"
    senza = [r.strip() for r in invocazioni if "--attendi" not in r]
    assert not senza, (
        "questi rami convertono senza --attendi, quindi la finestra si "
        f"richiuderebbe sui sospetti: {senza}"
    )
