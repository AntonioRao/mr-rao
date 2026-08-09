"""L'anteprima Markdown (P1.4).

L'anteprima rende il contenuto di un documento **altrui**. Sono due cose da
tenere ferme insieme, e la seconda pesa piu' della prima:

  - deve essere fedele: liste annidate e tabelle, che il renderer di prima
    non sapeva fare;
  - non deve diventare una porta. Niente HTML del documento che arriva al
    DOM, niente `javascript:` dentro un href, e soprattutto **nessuna
    richiesta di rete**: un `<img src="https://...">` dentro l'anteprima
    sarebbe una chiamata verso l'esterno partita dal documento che stai
    anonimizzando, cioe' esattamente la promessa che Mr. Rao fa e non
    manterrebbe.

Il renderer sta in un file suo per poter essere provato da node senza un
DOM: liste storte e tabelle sbilenche a mano non si guardano mai.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parent.parent
MODULO = RADICE / "static" / "js" / "markdown.js"

node = shutil.which("node")
pytestmark = pytest.mark.skipif(
    node is None, reason="serve node per provare il renderer dell'anteprima"
)


def rendi(*sorgenti: str) -> list[str]:
    """Rende ogni sorgente con il modulo vero, in un processo node."""
    codice = (
        "const md = require(process.argv[1]);"
        "const casi = JSON.parse(process.argv[2]);"
        "process.stdout.write(JSON.stringify(casi.map((c) => md.render(c))));"
    )
    esito = subprocess.run(
        [node, "-e", codice, str(MODULO), json.dumps(list(sorgenti))],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert esito.returncode == 0, esito.stderr
    return json.loads(esito.stdout)


# --------------------------------------------------------------- fedelta'


def test_liste_annidate():
    """Il motivo per cui P1.4 esisteva: prima ogni voce era piatta."""
    (html,) = rendi("- uno\n- due\n  - due a\n  - due b\n- tre\n")
    assert html.count("<ul>") == 2, html
    assert "<li>due<ul><li>due a</li><li>due b</li></ul></li>" in html


def test_lista_numerata_dentro_una_puntata():
    (html,) = rendi("- passo\n    1. primo\n    2. secondo\n")
    assert "<ol>" in html and "<li>primo</li>" in html


def test_una_lista_numerata_che_non_parte_da_uno():
    (html,) = rendi("3. terzo\n4. quarto\n")
    assert '<ol start="3">' in html


def test_cambiare_marcatore_apre_una_lista_nuova():
    """Un elenco puntato dopo uno numerato e' un'altra cosa, non la stessa
    proseguita: unirli darebbe una numerazione che il documento non ha."""
    (html,) = rendi("1. primo\n- puntato\n")
    assert "<ol>" in html and "<ul>" in html


def test_tabella_con_allineamenti():
    (html,) = rendi("| a | b | c |\n|:--|:-:|--:|\n| 1 | 2 | 3 |\n")
    assert "<table>" in html and "<thead>" in html
    assert 'style="text-align:left"' in html
    assert 'style="text-align:center"' in html
    assert 'style="text-align:right"' in html


def test_una_riga_piu_corta_non_sfalsa_la_tabella():
    """Le tabelle uscite da un PDF hanno righe incomplete a ogni pagina."""
    (html,) = rendi("| a | b | c |\n|---|---|---|\n| 1 |\n")
    assert html.count("<td") == 3, html


def test_blocco_di_codice_non_viene_interpretato():
    (html,) = rendi("```python\nx = a_b_c ** 2\n```\n")
    assert "<pre><code" in html
    assert "<em>" not in html and "<strong>" not in html


def test_un_recinto_mai_chiuso_non_mangia_il_documento():
    """Capita con l'OCR. Perdere il resto sarebbe peggio del difetto."""
    (html,) = rendi("prima\n\n```\nx = 1\n")
    assert "prima" in html and "x = 1" in html


def test_citazione_e_riga_orizzontale_e_titoli():
    (html,) = rendi("# Uno\n###### Sei\n\n> citato\n\n---\n")
    assert "<h1>Uno</h1>" in html and "<h6>Sei</h6>" in html
    assert "<blockquote>" in html and "<hr>" in html


def test_una_citazione_non_riporta_indietro_cio_che_ha_scappato():
    """Segnalato da CodeQL (js/double-escaping) ed era un difetto vero.

    Il blocco veniva riconosciuto sul testo già scappato e poi riportato
    indietro a colpi di `replace`. Un documento che contiene scritto per
    davvero `&quot;` ne usciva con un apice doppio: **testo cambiato**, non
    un problema estetico. Ora i blocchi si riconoscono sul testo com'è, e a
    scappare ci pensa una funzione sola, una volta sola.
    """
    (html,) = rendi("> il campo vale &quot;X&quot; nel tracciato\n")
    assert "&amp;quot;" in html, html
    assert '"X"' not in html


def test_il_ritorno_a_capo_singolo_e_uno_spazio():
    """Un PDF va a capo dove finisce la riga sulla pagina, non dove finisce
    la frase: rispettare quel ritorno a capo spezzerebbe ogni paragrafo."""
    (html,) = rendi("una frase\nspezzata dal PDF\n")
    assert "<p>una frase spezzata dal PDF</p>" == html


def test_il_trattino_basso_dentro_una_parola_non_e_corsivo():
    """`nome_file` e `api_key` in un documento convertito sono la norma."""
    (html,) = rendi("il campo nome_file_lungo va compilato\n")
    assert "<em>" not in html, html


def test_casella_di_spunta():
    (html,) = rendi("- [x] fatto\n- [ ] da fare\n")
    assert "☑" in html and "☐" in html
    assert "<input" not in html, "una spunta cliccabile prometterebbe un comando"


# ------------------------------------------------------------- non e' una porta


def test_l_html_del_documento_non_arriva_al_dom():
    (html,) = rendi("<script>alert(1)</script>\n\n<img src=x onerror=alert(1)>\n")
    # Il testo resta visibile — è contenuto del documento — ma come testo:
    # niente tag aperti, quindi niente `onerror` che sia un attributo.
    assert "<script" not in html
    assert "<img" not in html
    assert "&lt;script&gt;" in html
    assert "&lt;img src=x onerror=alert(1)&gt;" in html


def test_nessuna_immagine_remota_viene_mai_richiesta():
    """La riga che conta: l'anteprima non deve fare uscire niente.

    Un `<img src>` verso l'esterno e' una chiamata di rete partita dal
    documento in lavorazione — la promessa «zero cloud» cadrebbe proprio
    mentre l'utente guarda il risultato dell'anonimizzazione.
    """
    for html in rendi(
        "![foto](https://esempio.invalid/tracciante.png)\n",
        "![](http://tracker.invalid/pixel.gif)\n",
        "![alt](data:image/png;base64,AAAA)\n",
    ):
        assert "<img" not in html, html
        assert "esempio.invalid" not in html and "tracker.invalid" not in html


def test_un_link_pericoloso_diventa_testo():
    for html in rendi(
        "[clicca](javascript:alert(1))\n",
        "[apri](file:///C:/Windows/system.ini)\n",
        "[dati](data:text/html,<script>alert(1)</script>)\n",
    ):
        assert "href" not in html, html
        assert "javascript:" not in html.lower()


def test_un_link_normale_resta_un_link():
    (html,) = rendi("[esempio](https://example.org/pagina)\n")
    assert '<a href="https://example.org/pagina"' in html
    assert 'rel="noopener noreferrer nofollow"' in html


def test_i_segnaposto_della_redazione_restano_leggibili():
    """L'anteprima serve a controllare la redazione: se i segnaposto
    sparissero nel rendering, servirebbe a poco."""
    (html,) = rendi("Scrivi a {{EMAIL}} oppure chiama {{PHONE}}.\n")
    assert "{{EMAIL}}" in html and "{{PHONE}}" in html


# ------------------------------------------------------- collegato alla pagina


def test_la_pagina_carica_il_renderer():
    pagina = (RADICE / "templates" / "index.html").read_text(encoding="utf-8")
    assert "js/markdown.js" in pagina, "il modulo non è incluso nella pagina"
    app = (RADICE / "static" / "js" / "app.js").read_text(encoding="utf-8")
    assert "MrRaoMarkdown" in app, "l'anteprima non usa il renderer"
