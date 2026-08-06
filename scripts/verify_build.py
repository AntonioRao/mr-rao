"""Avvia l'eseguibile appena costruito e verifica che serva davvero.

Un build che finisce con codice di uscita zero non dice niente su cosa
succede quando si fa doppio clic. E' gia' successo di produrre 390 MB che
aprivano una finestra nera e si chiudevano: PyInstaller aveva incluso un
runtime hook che moriva su un file mancante, prima ancora di arrivare al
nostro codice. Se ne accorse un essere umano avviandolo, non il build.

Da qui in poi se ne accorge il build. Quattro controlli, nell'ordine in
cui fallirebbero:

1. il processo resta vivo dopo l'avvio;
2. /api/health risponde, con la versione giusta e frozen=True;
3. una conversione vera produce testo — e non solo di un .txt: un .docx,
   perche' i formati Office sono vissuti rotti per parecchie versioni
   senza che nessuno se ne accorgesse;
4. l'anonimizzazione lavora davvero sul testo estratto.

Uso:  python scripts/verify_build.py dist/MrRao-Portable/app/MrRao.exe
"""
from __future__ import annotations

import io
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from pathlib import Path

AVVIO_MAX_S = 90
PASSO_S = 1.0


def porta_libera() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def docx_di_prova(testo: str) -> bytes:
    doc = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{testo}</w:t></w:r></w:p></w:body></w:document>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Target="word/document.xml" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"/>'
        "</Relationships>"
    )
    types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-'
        'officedocument.wordprocessingml.document.main+xml"/></Types>'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)
    return buf.getvalue()


def post_multipart(url: str, campi: dict[str, str], nome: str, contenuto: bytes) -> dict:
    confine = "----MrRaoVerify" + uuid.uuid4().hex
    corpo = bytearray()
    for k, v in campi.items():
        corpo += f"--{confine}\r\n".encode()
        corpo += f'Content-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    corpo += f"--{confine}\r\n".encode()
    corpo += (
        f'Content-Disposition: form-data; name="file"; filename="{nome}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode()
    corpo += contenuto + b"\r\n"
    corpo += f"--{confine}--\r\n".encode()

    req = urllib.request.Request(
        url,
        data=bytes(corpo),
        headers={
            "Content-Type": f"multipart/form-data; boundary={confine}",
            "Origin": url.rsplit("/api/", 1)[0],
        },
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def main(argv: list[str]) -> int:
    exe = Path(argv[1] if len(argv) > 1 else "dist/MrRao-Portable/app/MrRao.exe").resolve()
    if not exe.is_file():
        print(f"ERRORE: eseguibile assente: {exe}", file=sys.stderr)
        return 1

    porta = porta_libera()
    base = f"http://127.0.0.1:{porta}"
    ambiente = {
        **os.environ,
        "MR_RAO_PORT": str(porta),
        "MR_RAO_TRAY": "0",
        "MR_RAO_OPEN_BROWSER": "0",
    }
    print(f"avvio  {exe.name} sulla porta {porta}")
    proc = subprocess.Popen(
        [str(exe)],
        cwd=str(exe.parent),
        env=ambiente,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    try:
        salute = None
        scaduto = time.monotonic() + AVVIO_MAX_S
        while time.monotonic() < scaduto:
            if proc.poll() is not None:
                uscita = proc.stdout.read().decode("utf-8", "replace") if proc.stdout else ""
                print(
                    f"FALLITO  il processo e' morto (codice {proc.returncode}) "
                    f"prima di rispondere.\n--- output ---\n{uscita[-3000:]}",
                    file=sys.stderr,
                )
                return 1
            try:
                with urllib.request.urlopen(f"{base}/api/health", timeout=3) as r:
                    salute = json.loads(r.read().decode("utf-8"))
                break
            except (urllib.error.URLError, OSError, TimeoutError):
                time.sleep(PASSO_S)

        if salute is None:
            print(f"FALLITO  nessuna risposta da /api/health in {AVVIO_MAX_S}s", file=sys.stderr)
            return 1

        print(f"  OK     health: v{salute.get('version')} frozen={salute.get('frozen')}")
        if not salute.get("frozen"):
            print("FALLITO  l'eseguibile non si dichiara frozen: non e' il pacchetto", file=sys.stderr)
            return 1

        # Una conversione vera, su un formato che e' gia' stato rotto.
        campi = {
            "profile": "default",
            "privacy_filter": "true",
            "include_frontmatter": "false",
        }
        testo = "Contatta mario.rossi@example.it al 335 123 4567 in via Roma 12"
        esito = post_multipart(
            f"{base}/api/convert/sync", campi, "verifica.docx", docx_di_prova(testo)
        )
        md = esito.get("markdown") or ""
        if "Contatta" not in md:
            print(f"FALLITO  il .docx non ha prodotto testo:\n{md[:400]}", file=sys.stderr)
            return 1
        print(f"  OK     conversione .docx: {len(md)} caratteri, motore {esito.get('engine')}")

        mancanti = [p for p in ("{{EMAIL}}", "{{PHONE}}", "{{ADDRESS}}") if p not in md]
        if mancanti:
            print(f"FALLITO  anonimizzazione incompleta, mancano {mancanti}:\n{md[:400]}", file=sys.stderr)
            return 1
        totale = (esito.get("redaction") or {}).get("total", 0)
        print(f"  OK     anonimizzazione: {totale} sostituzioni")

        # L'icona spedita dev'essere quella del repository. Per un po' il
        # pacchetto ne ha portata una piu' povera, generata al passo 1 del
        # build da un percorso che sovrascriveva l'artwork rifinito a mano:
        # il collegamento sul Desktop funzionava, e mostrava l'icona
        # sbagliata. Nessuno se ne accorge guardando se il file c'e'.
        ico_pacchetto = exe.parent.parent / "mr-rao.ico"
        ico_repo = Path(__file__).resolve().parent.parent / "static" / "img" / "mr-rao.ico"
        if ico_pacchetto.is_file() and ico_repo.is_file():
            if ico_pacchetto.read_bytes() != ico_repo.read_bytes():
                print(
                    f"FALLITO  l'icona del pacchetto ({ico_pacchetto.stat().st_size:,} B) "
                    f"non e' quella del repository ({ico_repo.stat().st_size:,} B)",
                    file=sys.stderr,
                )
                return 1
            print(f"  OK     icona identica al repository: {ico_repo.stat().st_size:,} B")
        else:
            print(f"FALLITO  icona assente nel pacchetto: {ico_pacchetto}", file=sys.stderr)
            return 1

        print("VERIFICA SUPERATA")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
