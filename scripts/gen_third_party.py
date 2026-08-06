"""Genera THIRD_PARTY.md dai metadati dei pacchetti realmente installati.

Perché uno script e non un elenco scritto a mano: un elenco a mano invecchia
in silenzio e sbaglia. La prima stesura di questo file dichiarava Scrubadub
come MIT (è Apache-2.0) e ometteva del tutto python-stdnum, che è LGPL —
cioè proprio la categoria che impone obblighi.

Uso:
    venv\\Scripts\\python scripts\\gen_third_party.py            # scrive THIRD_PARTY.md
    venv\\Scripts\\python scripts\\gen_third_party.py --check    # esce 1 se è da rigenerare
"""
from __future__ import annotations

import sys
from importlib.metadata import distributions
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "THIRD_PARTY.md"

# Dipendenze dirette: come vengono usate nel prodotto.
RUOLI = {
    "markitdown": "Documenti Office/HTML/PDF → Markdown",
    "rapidocr-onnxruntime": "OCR offline (immagini e PDF scansionati)",
    "onnxruntime": "Esecuzione dei modelli OCR",
    "flask": "Server web locale",
    "werkzeug": "Livello WSGI",
    "beautifulsoup4": "Corpo HTML delle email → testo",
    "scrubadub": "Redazione PII (in aggiunta ai riconoscitori italiani)",
    "pdfplumber": "Estrazione testo e tabelle da PDF",
    "pdfminer.six": "Parsing PDF (usato da pdfplumber)",
    "pillow": "Immagini",
    "magika": "Riconoscimento del tipo di file",
    "pystray": "Icona nella barra di sistema",
    "pyyaml": "Verifica del frontmatter nei test",
    "pytest": "Test (solo sviluppo)",
    "pyinstaller": "Build del pacchetto portable (solo sviluppo)",
}

# Licenze che impongono obblighi oltre l'attribuzione.
COPYLEFT = ("LGPL", "GPL", "MPL", "MOZILLA", "EUPL", "CDDL")

NOTICE_LOCALI = {
    "pystray": "licenses/pystray/",
    "python-stdnum": "licenses/python-stdnum/",
}


def licenza(dist) -> str:
    m = dist.metadata
    expr = (m.get("License-Expression") or "").strip()
    if expr:
        return expr
    classifiers = [
        c.split("::")[-1].strip()
        for c in (m.get_all("Classifier") or [])
        if c.startswith("License")
    ]
    if classifiers:
        return "; ".join(dict.fromkeys(classifiers))
    testo = (m.get("License") or "").strip()
    if testo:
        prima = testo.splitlines()[0]
        return prima[:70] + ("…" if len(prima) > 70 else "")
    return "non dichiarata"


def homepage(dist) -> str:
    m = dist.metadata
    for chiave in ("Home-page", "Project-URL"):
        for valore in m.get_all(chiave) or []:
            if "http" in valore:
                return valore.split(", ")[-1].strip()
    return ""


def e_copyleft(lic: str) -> bool:
    su = lic.upper()
    if "GPLV2-OR-LATER WITH A SPECIAL EXCEPTION" in su:
        return True
    return any(k in su for k in COPYLEFT)


def raccogli() -> list[dict]:
    voci = []
    for d in distributions():
        nome = (d.metadata["Name"] or "").strip()
        if not nome:
            continue
        lic = licenza(d)
        voci.append(
            {
                "nome": nome,
                "chiave": nome.lower().replace("_", "-"),
                "versione": d.version,
                "licenza": lic,
                "url": homepage(d),
                "copyleft": e_copyleft(lic),
            }
        )
    return sorted(voci, key=lambda v: v["chiave"])


def riga(v: dict, con_ruolo: bool) -> str:
    nome = f"[{v['nome']}]({v['url']})" if v["url"] else v["nome"]
    notice = NOTICE_LOCALI.get(v["chiave"], "—")
    if notice != "—":
        notice = f"[`{notice}`]({notice})"
    if con_ruolo:
        ruolo = RUOLI.get(v["chiave"], "")
        return f"| {nome} | {v['versione']} | {ruolo} | {v['licenza']} | {notice} |"
    return f"| {nome} | {v['versione']} | {v['licenza']} | {notice} |"


def genera() -> str:
    voci = raccogli()
    dirette = [v for v in voci if v["chiave"] in RUOLI]
    indirette = [v for v in voci if v["chiave"] not in RUOLI]
    copyleft = [v for v in voci if v["copyleft"]]

    r: list[str] = []
    a = r.append
    a("# Componenti di terze parti — Mr. Rao")
    a("")
    a("> Generato da `scripts/gen_third_party.py` leggendo i metadati dei pacchetti")
    a("> **realmente installati**. Non modificare a mano: rigenerare.")
    a("")
    a("Mr. Rao **non** è un fork di questi progetti: li usa come dipendenze.")
    a("Le loro licenze restano integre e **prevalgono** sui rispettivi file.")
    a("")
    a("Mr. Rao è distribuito sotto **[AGPL-3.0](LICENSE)**. Tutte le licenze qui")
    a("elencate sono compatibili con l'AGPL-3.0: permissive (MIT, BSD, Apache-2.0,")
    a("PSF), copyleft di file (MPL-2.0, esplicitamente compatibile) e LGPL, che")
    a("l'AGPL può incorporare. La licenza di Mr. Rao **non** limita i diritti che")
    a("queste librerie concedono.")
    a("")
    a(f"Pacchetti nell'ambiente: **{len(voci)}** — di cui **{len(copyleft)}** con obblighi")
    a("oltre la semplice attribuzione (copyleft o eccezioni).")
    a("")

    a("## Licenze con obblighi particolari")
    a("")
    a("Queste impongono adempimenti concreti — testo di licenza, notice, o")
    a("condizioni sulla ridistribuzione — e non la semplice attribuzione.")
    a("Sono elencate per prime perché sono quelle da controllare.")
    a("")
    a("| Progetto | Versione | Licenza | Notice locale |")
    a("|----------|----------|---------|---------------|")
    for v in copyleft:
        a(riga(v, con_ruolo=False))
    a("")
    a("**pystray** (LGPL-3.0) e **python-stdnum** (LGPL-2.1+) sono le uniche due")
    a("librerie LGPL del pacchetto. Per entrambe: testo di licenza, NOTICE e")
    a("istruzioni di sostituzione in `licenses/`. Mr. Rao non impone restrizioni")
    a("aggiuntive su di esse — vedi `LICENSE` §5.")
    a("")
    a("**PyInstaller** è GPLv2-or-later **con eccezione esplicita** che consente di")
    a("costruire e distribuire programmi non liberi: è ciò che rende lecito")
    a("distribuire `MrRao.exe`, il cui bootloader deriva da PyInstaller.")
    a("Serve solo per costruire il pacchetto portable, non a runtime.")
    a("")
    a("**MPL-2.0** (certifi, tqdm) è copyleft *per file*: obbliga a rendere")
    a("disponibile il sorgente dei soli file MPL eventualmente modificati.")
    a("Mr. Rao non li modifica.")
    a("")

    a("## Dipendenze dirette")
    a("")
    a("| Progetto | Versione | Uso in Mr. Rao | Licenza | Notice locale |")
    a("|----------|----------|----------------|---------|---------------|")
    for v in dirette:
        a(riga(v, con_ruolo=True))
    a("")

    a("## Dipendenze indirette")
    a("")
    a("Arrivano come dipendenze delle precedenti. Sono elencate per intero perché")
    a("l'obbligo di attribuzione è di chi distribuisce, non di chi riceve.")
    a("")
    a("<details><summary>Elenco completo ({} pacchetti)</summary>".format(len(indirette)))
    a("")
    a("| Progetto | Versione | Licenza | Notice locale |")
    a("|----------|----------|---------|---------------|")
    for v in indirette:
        a(riga(v, con_ruolo=False))
    a("")
    a("</details>")
    a("")

    a("## In caso di redistribuzione")
    a("")
    a("Conservare almeno:")
    a("")
    a("- `LICENSE` (Mr. Rao)")
    a("- `THIRD_PARTY.md` (questo file)")
    a("- `licenses/` (intera cartella)")
    a("")
    a("La build portable (`scripts/build_portable.bat`) li copia già nel pacchetto.")
    a("")

    a("## Se non vuoi dipendenze LGPL")
    a("")
    a("Disinstalla Scrubadub: sparisce anche python-stdnum, e Mr. Rao continua a")
    a("funzionare con i riconoscitori italiani propri (email, telefoni, codice")
    a("fiscale, P.IVA, IBAN con verifica mod-97, nomi). Per l'icona nella barra")
    a("di sistema, disinstalla pystray: l'app resta utilizzabile dal browser.")
    a("")
    return "\n".join(r) + "\n"


def main(argv: list[str]) -> int:
    testo = genera()
    if "--check" in argv:
        attuale = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if attuale != testo:
            print("THIRD_PARTY.md non è aggiornato: rigenerare con")
            print("    venv\\Scripts\\python scripts\\gen_third_party.py")
            return 1
        print("THIRD_PARTY.md aggiornato.")
        return 0
    OUT.write_text(testo, encoding="utf-8")
    print(f"Scritto {OUT} ({len(testo.splitlines())} righe)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
