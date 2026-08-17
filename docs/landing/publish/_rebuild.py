# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Rigenera le pagine pubblicate e le impronte CSP di _headers dai sorgenti.

Le pagine sono **due**, italiano e inglese, e la seconda non e' una copia
tradotta: e' un file suo, con sezioni sue. Qui cambia solo dove finisce
(`/` e `/en/`) e quali indirizzi vanno riscritti, perche' una pagina in una
sottocartella non puo' usare percorsi relativi per font e immagini che
stanno alla radice.

Gli inline vengono estratti con `HTMLParser`, non con una regex: una regex su
`<script ...>` sbaglia sui casi che un parser tratta senza pensarci (attributi
che contengono `>`, commenti, tag chiusi in modo strano) e qui sbagliare vuol
dire calcolare l'impronta del blocco sbagliato — cioe' pubblicare un sito che
il browser blocca. Ogni passaggio che potrebbe non trovare niente si ferma
invece di andare avanti in silenzio: un'impronta vecchia non si vede finche'
non si guarda il sito pubblicato.

La CSP e' una sola, sotto `/*`, e vale per entrambe le pagine: quindi ogni
direttiva porta **tutte** le impronte, non solo quella dell'ultima pagina
generata. Un solo hash qui vorrebbe dire pubblicare una pagina bianca.
"""
from pathlib import Path
from html.parser import HTMLParser
import re
import shutil
import hashlib
import base64

root = Path(__file__).resolve().parent
sorgenti = root.parent

# (sorgente, file pubblicato, riscritture). Le riscritture sono coppie
# letterali e non regex: sono indirizzi, e un indirizzo o e' quello o non e'.
#
# La pagina inglese sta in /en/ e quindi usa percorsi **assoluti** per font e
# immagini: `fonts/...` da /en/ cercherebbe /en/fonts/, che non esiste, e il
# browser ripiegherebbe sui font di sistema senza dire niente a nessuno.
PAGINE = (
    (
        "01-protocollo-zero.html",
        "index.html",
        (
            ("../../static/img/logo.svg", "assets/logo.svg"),
            ("../../static/img/logo-chrome.svg", "assets/logo-chrome.svg"),
            ("../../static/img/logo-edge.svg", "assets/logo-edge.svg"),
            ("../../static/img/logo-firefox.svg", "assets/logo-firefox.svg"),
            ("../../static/img/favicon.svg", "assets/favicon.svg"),
            ("../../static/img/favicon.ico", "assets/favicon.ico"),
            ('href="01-protocollo-zero.en.html"', 'href="/en/"'),
        ),
    ),
    (
        "01-protocollo-zero.en.html",
        "en/index.html",
        (
            ("../../static/img/logo.svg", "/assets/logo.svg"),
            ("../../static/img/logo-chrome.svg", "/assets/logo-chrome.svg"),
            ("../../static/img/logo-edge.svg", "/assets/logo-edge.svg"),
            ("../../static/img/logo-firefox.svg", "/assets/logo-firefox.svg"),
            ("../../static/img/favicon.svg", "/assets/favicon.svg"),
            ("../../static/img/favicon.ico", "/assets/favicon.ico"),
            ('url("fonts/', 'url("/fonts/'),
            ('href="01-protocollo-zero.html"', 'href="/"'),
        ),
    ),
)


# Gli asset portano l'impronta del proprio contenuto nell'indirizzo.
#
# `_headers` li fa cachare sette giorni, e i nomi sono fissi: cambiando il
# logo, chi era gia' passato dal sito continuava a vedere quello vecchio
# fino alla scadenza. E' successo davvero -- deploy corretto, pagina nuova,
# logo vecchio, per quasi una settimana.
#
# Con `?v=<impronta>` l'indirizzo cambia insieme al file, quindi la cache
# viene aggirata da sola quando serve e continua a valere quando non serve.
def impronta(nome: str) -> str:
    dati = (root / "assets" / nome).read_bytes()
    return hashlib.sha256(dati).hexdigest()[:10]


class Inline(HTMLParser):
    """Raccoglie il testo dei blocchi <style> e <script> senza `src`."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.styles: list[str] = []
        self.scripts: list[str] = []
        self._dove: str | None = None
        # `handle_data` puo' essere chiamata piu' volte per un blocco solo:
        # si accumula qui e si chiude il blocco al tag di chiusura, altrimenti
        # un blocco spezzato sembrerebbe due blocchi.
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "style":
            self._dove = "styles"
        elif tag == "script" and not dict(attrs).get("src"):
            self._dove = "scripts"

    def handle_endtag(self, tag):
        if tag in ("style", "script") and self._dove:
            getattr(self, self._dove).append("".join(self._buf))
            self._buf = []
            self._dove = None

    def handle_data(self, data):
        if self._dove:
            self._buf.append(data)


def sh(s: str) -> str:
    return (
        "sha256-"
        + base64.b64encode(hashlib.sha256(s.encode("utf-8")).digest()).decode()
    )


# Una copia di favicon.ico anche alla radice, senza impronta. Non e' una
# ridondanza: ogni browser chiede /favicon.ico da solo, senza guardare
# l'HTML, e su Pages un percorso che non esiste restituisce index.html.
# Il browser riceve HTML dove si aspetta un'icona, non lo dice a nessuno e
# continua a mostrare quella che aveva in cache.
shutil.copyfile(root / "assets" / "favicon.ico", root / "favicon.ico")

impronte: dict[str, list[str]] = {"script": [], "style": []}

for nome_sorgente, uscita, riscritture in PAGINE:
    src = (sorgenti / nome_sorgente).read_text(encoding="utf-8")

    # no inline style attributes (allow 'stylesheet' word only via different pattern)
    if re.search(r"""\sstyle\s*=""", src):
        raise SystemExit(f"{nome_sorgente}: inline style attributes still present")
    if "el.style" in src:
        raise SystemExit(f"{nome_sorgente}: el.style still present in source")

    html = src
    for prima, dopo in riscritture:
        # Un indirizzo che non c'e' piu' e' un rebuild che pubblica un
        # percorso rotto in silenzio: la pagina va online, il font non
        # arriva e nessuno lo scopre guardando il sorgente.
        if prima not in html:
            raise SystemExit(f"{nome_sorgente}: non trovo '{prima}' da riscrivere")
        html = html.replace(prima, dopo)

    for nome in (
        "logo.svg",
        "logo-chrome.svg",
        "logo-edge.svg",
        "logo-firefox.svg",
        "favicon.svg",
        "favicon.ico",
    ):
        percorso = root / "assets" / nome
        if not percorso.exists():
            continue
        html = html.replace(f"assets/{nome}", f"assets/{nome}?v={impronta(nome)}")

    destinazione = root / uscita
    destinazione.parent.mkdir(parents=True, exist_ok=True)
    destinazione.write_text(html, encoding="utf-8", newline="\n")

    parser = Inline()
    parser.feed(html)

    # `[0]` da solo prenderebbe il primo e ignorerebbe gli altri: l'impronta
    # coprirebbe meta' pagina e il browser bloccherebbe il resto.
    for nome, blocchi in (("style", parser.styles), ("script", parser.scripts)):
        if len(blocchi) != 1:
            raise SystemExit(
                f"{nome_sorgente}: atteso 1 blocco <{nome}> inline, trovati "
                f"{len(blocchi)}: l'header CSP ne fissa uno per pagina"
            )
        h = sh(blocchi[0])
        if h not in impronte[nome]:
            impronte[nome].append(h)
        print(f"{uscita:16} {nome.upper():6} {h}")

hdr_path = root / "_headers"
hdr = hdr_path.read_text(encoding="utf-8")
# `re.sub` che non trova niente restituisce la stringa com'era, senza dire
# niente: e' cosi' che l'impronta e' rimasta vecchia una volta.
#
# La direttiva puo' gia' portarne una o piu' di una: si riscrive il gruppo
# intero, altrimenti aggiungendo la seconda pagina si otterrebbe una CSP con
# l'impronta di una sola.
for direttiva in ("script-src", "style-src"):
    attese = " ".join(f"'{h}'" for h in impronte[direttiva.split("-")[0]])
    hdr, sostituite = re.subn(
        rf"{direttiva} 'self'(?: 'sha256-[^']+')+",
        f"{direttiva} 'self' {attese}",
        hdr,
    )
    if sostituite != 1:
        raise SystemExit(
            f"attesa 1 direttiva {direttiva} in _headers, sostituite {sostituite}"
        )
hdr_path.write_text(hdr, encoding="utf-8", newline="\n")
print(f"OK wrote {len(PAGINE)} pagine + _headers")
