"""Rigenera index.html e le impronte CSP di _headers dal sorgente della landing.

Gli inline vengono estratti con `HTMLParser`, non con una regex: una regex su
`<script ...>` sbaglia sui casi che un parser tratta senza pensarci (attributi
che contengono `>`, commenti, tag chiusi in modo strano) e qui sbagliare vuol
dire calcolare l'impronta del blocco sbagliato — cioe' pubblicare un sito che
il browser blocca. Ogni passaggio che potrebbe non trovare niente si ferma
invece di andare avanti in silenzio: un'impronta vecchia non si vede finche'
non si guarda il sito pubblicato.
"""
from pathlib import Path
from html.parser import HTMLParser
import re
import shutil
import hashlib
import base64

root = Path(__file__).resolve().parent
src = (root.parent / "01-protocollo-zero.html").read_text(encoding="utf-8")

# no inline style attributes (allow 'stylesheet' word only via different pattern)
if re.search(r"""\sstyle\s*=""", src):
    raise SystemExit("inline style attributes still present in source")
if "el.style" in src:
    raise SystemExit("el.style still present in source")

html = (src.replace("../../static/img/logo.svg", "assets/logo.svg")
           .replace("../../static/img/favicon.svg", "assets/favicon.svg")
           .replace("../../static/img/favicon.ico", "assets/favicon.ico"))

# Una copia di favicon.ico anche alla radice, senza impronta. Non e' una
# ridondanza: ogni browser chiede /favicon.ico da solo, senza guardare
# l'HTML, e su Pages un percorso che non esiste restituisce index.html.
# Il browser riceve HTML dove si aspetta un'icona, non lo dice a nessuno e
# continua a mostrare quella che aveva in cache.
shutil.copyfile(root / "assets" / "favicon.ico", root / "favicon.ico")

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


for nome in ("logo.svg", "favicon.svg", "favicon.ico"):
    percorso = root / "assets" / nome
    if not percorso.exists():
        continue
    html = html.replace(f"assets/{nome}", f"assets/{nome}?v={impronta(nome)}")

(root / "index.html").write_text(html, encoding="utf-8", newline="\n")

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


parser = Inline()
parser.feed(html)
styles, scripts = parser.styles, parser.scripts

# `[0]` da solo prenderebbe il primo e ignorerebbe gli altri: l'impronta
# coprirebbe meta' pagina e il browser bloccherebbe il resto.
for nome, blocchi in (("style", styles), ("script", scripts)):
    if len(blocchi) != 1:
        raise SystemExit(
            f"attesi 1 blocco <{nome}> inline, trovati {len(blocchi)}: "
            "l'header CSP ne fissa uno solo"
        )


def sh(s: str) -> str:
    return (
        "sha256-"
        + base64.b64encode(hashlib.sha256(s.encode("utf-8")).digest()).decode()
    )


style_h, script_h = sh(styles[0]), sh(scripts[0])
print("STYLE", style_h)
print("SCRIPT", script_h)

hdr_path = root / "_headers"
hdr = hdr_path.read_text(encoding="utf-8")
# `re.sub` che non trova niente restituisce la stringa com'era, senza dire
# niente: e' cosi' che l'impronta e' rimasta vecchia una volta.
for direttiva, hash_atteso in (("script-src", script_h), ("style-src", style_h)):
    hdr, sostituite = re.subn(
        rf"{direttiva} 'self' 'sha256-[^']+'",
        f"{direttiva} 'self' '{hash_atteso}'",
        hdr,
    )
    if sostituite != 1:
        raise SystemExit(
            f"attesa 1 direttiva {direttiva} in _headers, sostituite {sostituite}"
        )
hdr_path.write_text(hdr, encoding="utf-8", newline="\n")
print("OK wrote index.html + _headers")
