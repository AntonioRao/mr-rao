"""Genera lo screenshot dell'interfaccia per il README.

Perché serve uno script e non uno scatto a mano: la schermata va rifatta a
ogni modifica visibile della UI, e a mano si sbaglia (si fotografa il
risultato vuoto, oppure il server serve ancora il template in cache).

Come funziona, e perché così:

1. Scrive una pagina-ponte temporanea in `static/`. Serve perché Chrome in
   modalità headless non sa interagire con la pagina: non può caricare un
   file e aspettare la conversione. La pagina-ponte invece è servita dalla
   stessa origine dell'app, quindi può pilotarne il DOM.
2. La conversione la fa con una XHR **sincrona**: Chrome scatta sull'evento
   `load`, quindi tutto il lavoro deve concludersi prima di quell'evento.
   Con una fetch asincrona si fotografa un risultato ancora vuoto.
3. Ritaglia lo spazio vuoto sotto il footer cercando l'ultima riga che
   contiene testo chiaro.

Uso:
    venv\\Scripts\\python scripts\\make_screenshot.py --url http://127.0.0.1:5000

Il server dev'essere già avviato **dopo** l'ultima modifica ai template:
Jinja li tiene in cache, quindi un server vecchio serve la pagina vecchia.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
OUT_DIR = ROOT / "docs" / "img"
PONTE = STATIC / "_screenshot_bridge.html"

CHROME_CANDIDATI = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe",
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
]

DOCUMENTO_DEMO = """FATTURA n. 2026/0184

Cliente: Mario Rossi
Via dei Mille 12, Milano
Codice fiscale: RSSMRA80A01H501U
P.IVA: IT01234567890
Email: mario.rossi@example.com
Telefono: +39 333 1234567
IBAN: IT60X0542811101000000123456

Protocollo interno 0123456789 - Versione 1.10 del listino

Descrizione                 Quantita   Importo
Consulenza tecnica              12     1.440,00
Licenza software annuale         1       600,00
Totale imponibile                      2.040,00"""

PONTE_HTML = """<!doctype html>
<html lang="it">
<head><meta charset="utf-8"><title>scatto</title>
<style>html,body{margin:0;padding:0;background:#060912}iframe{display:block;width:100vw;height:100vh;border:0}</style>
</head>
<body>
<script>
const CONTENUTO = __CONTENUTO__;
const fd = new FormData();
fd.append('file', new File([CONTENUTO], 'fattura-2026-0184.txt', {type: 'text/plain'}));
fd.append('profile', 'default');
const xhr = new XMLHttpRequest();
xhr.open('POST', '/api/convert/sync', false);
xhr.send(fd);
const esito = JSON.parse(xhr.responseText);

// Niente iframe: dalla 1.7.0 l'app manda `frame-ancestors 'none'`, quindi
// il browser rifiuta di caricarla dentro un riquadro -- anche dalla stessa
// origine. Lo scatto usciva grigio con l'icona di file rotto, e siccome la
// schermata era gia' stata fatta prima di quella intestazione, nessuno se
// n'era accorto per tre versioni.
//
// Si scarica la pagina, la si monta qui dentro e la si fotografa: stessa
// origine, nessun riquadro, e soprattutto **nessuna deroga alla sicurezza
// del prodotto per comodita' di uno script**.
fetch('/__LANG__').then(r => r.text()).then(html => {
  const doc = new DOMParser().parseFromString(html, 'text/html');
  {
  doc.getElementById('markdown-output').textContent = esito.markdown;
  doc.getElementById('result-card').style.display = 'flex';
  const badge = doc.getElementById('redaction-badge');
  const totale = (esito.redaction && esito.redaction.total) || 0;
  if (badge && totale) {
    badge.style.display = 'inline-flex';
    badge.textContent = '\\u{1F6E1}\\uFE0F ' + totale + ' __REDAZIONI__';
  }
  const stile = doc.createElement('style');
  stile.textContent = '.info-fab{display:none!important}';
  doc.head.appendChild(stile);
  const cronologia = doc.getElementById('history-list');
  if (cronologia) {
    cronologia.innerHTML = '<button type="button" class="history-item">' +
      '<span class="hi-name">fattura-2026-0184.md</span>' +
      '<span class="hi-meta">__ADESSO__ \\u00b7 \\u{1F6E1}\\uFE0F' + totale + '</span></button>';
  }
  }
  document.replaceChild(doc.documentElement, document.documentElement);
});
</script>
</body>
</html>
"""


def trova_browser() -> Path | None:
    for p in CHROME_CANDIDATI:
        if p.exists():
            return p
    return None


def server_attivo(url: str) -> bool:
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/api/health", timeout=3) as r:
            return r.status == 200
    except (urllib.error.URLError, OSError):
        return False


def ritaglia_e_salva(grezzo: Path, larghezza_finale: int = 1500,
                     lingua: str = "it") -> tuple[int, int]:
    from PIL import Image

    im = Image.open(grezzo).convert("RGB")
    larg, alt = im.size

    def ha_testo(y: int) -> bool:
        return any(max(im.getpixel((x, y))) > 130 for x in range(0, larg, 12))

    ultima = alt - 1
    while ultima > 0 and not ha_testo(ultima):
        ultima -= 10

    ritagliata = im.crop((0, 0, larg, min(alt, ultima + 110)))
    altezza = round(ritagliata.size[1] * larghezza_finale / larg)
    finale = ritagliata.resize((larghezza_finale, altezza), Image.LANCZOS)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # L'italiano tiene il nome storico: e' linkato dal README e dal sito,
    # e rinominarlo romperebbe immagini gia' pubblicate.
    nome = "schermata.png" if lingua == "it" else f"schermata-{lingua}.png"
    finale.save(OUT_DIR / nome, optimize=True)
    # Anteprima social 1280x640: solo intestazione e area di rilascio
    # Solo dall'italiano: e' l'anteprima usata dal sito e dai social, e
    # deve restare una sola. Rigenerarla a ogni lingua la farebbe cambiare
    # a seconda dell'ultimo comando lanciato.
    if lingua == "it":
        im.crop((0, 0, larg, round(larg / 2))).resize((1280, 640), Image.LANCZOS).save(
            OUT_DIR / "social-preview.png", optimize=True
        )
    return finale.size


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Screenshot dell'interfaccia per il README")
    ap.add_argument("--url", default="http://127.0.0.1:5000", help="URL dell'app già avviata")
    # La schermata del README inglese deve mostrare l'interfaccia inglese:
    # promettere due lingue e mostrarne una sola e' la stessa incoerenza
    # che abbiamo appena tolto dai documenti.
    ap.add_argument("--lang", default="it", choices=["it", "en"], help="lingua da fotografare")
    ap.add_argument("--width", type=int, default=1360, help="larghezza finestra in px CSS")
    ap.add_argument("--height", type=int, default=2500, help="altezza finestra in px CSS")
    args = ap.parse_args(argv)

    browser = trova_browser()
    if browser is None:
        print("Chrome o Edge non trovati: servono per lo scatto headless.", file=sys.stderr)
        return 1

    if not server_attivo(args.url):
        print(f"Nessuna app in ascolto su {args.url}. Avviala prima:", file=sys.stderr)
        print("    python app.py", file=sys.stderr)
        return 1

    import json

    PONTE.write_text(
        PONTE_HTML.replace("__CONTENUTO__", json.dumps(DOCUMENTO_DEMO))
                   .replace("__LANG__", "" if args.lang == "it" else "?lang=" + args.lang)
                   .replace("__REDAZIONI__", "redazioni" if args.lang == "it" else "redactions")
                   .replace("__ADESSO__", "adesso" if args.lang == "it" else "just now"),
        encoding="utf-8",
    )
    grezzo = OUT_DIR / "_grezzo.png"
    profilo = OUT_DIR / "_chrome_profile"
    try:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                str(browser),
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--force-device-scale-factor=2",
                f"--window-size={args.width},{args.height}",
                "--virtual-time-budget=6000",
                f"--screenshot={grezzo}",
                f"--user-data-dir={profilo}",
                f"{args.url.rstrip('/')}/static/{PONTE.name}",
            ],
            check=True,
            capture_output=True,
        )
        if not grezzo.exists():
            print("Chrome non ha prodotto l'immagine.", file=sys.stderr)
            return 1
        dimensioni = ritaglia_e_salva(grezzo, lingua=args.lang)
        peso = (OUT_DIR / "schermata.png").stat().st_size // 1024
        print(f"docs/img/schermata.png      {dimensioni[0]}x{dimensioni[1]}  {peso} KB")
        print("docs/img/social-preview.png 1280x640")
        return 0
    finally:
        PONTE.unlink(missing_ok=True)
        grezzo.unlink(missing_ok=True)
        shutil.rmtree(profilo, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
