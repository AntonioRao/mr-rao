# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Genera THIRD_PARTY.md dai metadati dei pacchetti realmente installati.

Perché uno script e non un elenco scritto a mano: un elenco a mano invecchia
in silenzio e sbaglia. Una stesura manuale aveva già attribuito una licenza
sbagliata a una dipendenza e ne aveva omessa un'altra con obblighi reali —
proprio la categoria che non si può permettere di sbagliare.

Quali pacchetti, e perché non «tutti quelli installati»
-------------------------------------------------------

L'elenco parte da ciò che Mr. Rao **dichiara** — `requirements.txt` e
`requirements-build.txt` — e segue ciò che quei pacchetti si portano dietro.
Versione e licenza si leggono dai metadati installati; **quali** pacchetti
elencare no.

Prima erano la stessa cosa: si elencava tutto l'ambiente. Il 3 ottobre 2026
il controllo era rosso sulla macchina di sviluppo per sedici pacchetti che
con Mr. Rao non hanno niente a che fare — `rich`, `CacheControl`,
`license-expression` e gli altri: le dipendenze di uno strumento di audit
provato una volta e poi disinstallato, rimaste nel venv. Rigenerare, che è
quello che il messaggio d'errore invita a fare, le avrebbe messe fra le terze
parti del prodotto, in un file che si distribuisce e che dichiara licenze.

Un ambiente accumula cose; un elenco di licenze deve dire cosa c'è nel
pacchetto. Con loro esce dall'elenco anche `pip`, che c'era per la stessa
ragione e che nessun pacchetto distribuito contiene.

Uso:
    venv\\Scripts\\python scripts\\gen_third_party.py            # scrive THIRD_PARTY.md
    venv\\Scripts\\python scripts\\gen_third_party.py --check    # esce 1 se è da rigenerare
"""
from __future__ import annotations

import re
import sys
from importlib.metadata import distributions
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "THIRD_PARTY.md"

# Da dove parte l'elenco. Il secondo include il primo con `-r`, e aggiunge
# ciò che serve solo a costruire il pacchetto.
REQUISITI = ("requirements.txt", "requirements-build.txt")

# Dipendenze dirette: come vengono usate nel prodotto.
#
# «Diretta» qui vuol dire **dichiarata da noi** in `requirements.txt` (o in
# `requirements-build.txt` per pyinstaller), non «importante». La distinzione
# e' quella che conta per chi legge: una dipendenza dichiarata la scegliamo
# noi e la togliamo noi; una indiretta arriva perche' l'ha chiesta un'altra,
# e puo' sparire il giorno in cui quella cambia idea.
#
# Questo elenco era gia' scivolato in tutte e due le direzioni: **magika**
# stava fra le dirette pur arrivando da MarkItDown, e otto pacchetti
# dichiarati in `requirements.txt` -- pywebview, pikepdf, pypdfium2, mammoth,
# python-pptx, pandas, openpyxl, xlrd -- finivano fra gli «arrivano come
# dipendenze delle precedenti», che di loro e' falso. Se si aggiunge o si
# toglie una riga in `requirements.txt`, si passa di qui.
RUOLI = {
    "markitdown": "Documenti Office/HTML/PDF → Markdown",
    "mammoth": "Lettura dei .docx dentro MarkItDown",
    "python-pptx": "Lettura dei .pptx dentro MarkItDown",
    "pandas": "Lettura dei .xlsx e .xls dentro MarkItDown",
    "openpyxl": "Lettura dei .xlsx",
    "xlrd": "Lettura dei .xls",
    "rapidocr": "OCR offline (immagini e PDF scansionati), modelli PP-OCRv6 inclusi",
    "python-docx": "Esportazione del documento redatto in .docx",
    "onnxruntime": "Esecuzione dei modelli OCR",
    "flask": "Server web locale",
    "werkzeug": "Livello WSGI",
    "beautifulsoup4": "Corpo HTML delle email → testo",
    "pdfplumber": "Estrazione testo e tabelle da PDF",
    "pdfminer.six": "Parsing PDF (usato da pdfplumber)",
    "pypdfium2": "Redazione PDF→PDF: trova il riquadro di ogni carattere",
    "pikepdf": "Redazione PDF→PDF: taglia il flusso di contenuto e le annotazioni",
    "pillow": "Immagini",
    "pystray": "Icona nella barra di sistema",
    "pywebview": "Finestra dell'applicazione sul motore di rendering di sistema",
    "pyyaml": "Verifica del frontmatter nei test",
    "pytest": "Test (solo sviluppo)",
    "pyinstaller": "Build del pacchetto portable (solo sviluppo)",
}

# Licenze che impongono obblighi oltre l'attribuzione.
COPYLEFT = ("LGPL", "GPL", "MPL", "MOZILLA", "EUPL", "CDDL")

NOTICE_LOCALI = {
    "pystray": "licenses/pystray/",
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


def nome_canonico(nome: str) -> str:
    """Il nome come lo confronta pip: minuscolo, con un solo tipo di separatore.

    `pdfminer.six`, `pdfminer-six` e `pdfminer_six` sono lo stesso pacchetto, e
    chi lo richiede lo scrive in uno qualunque dei tre modi.
    """
    return re.sub(r"[-_.]+", "-", nome).lower()


def dichiarati(file: tuple[Path, ...] | None = None) -> list:
    """I requisiti scritti a mano nei file di `REQUISITI`.

    Si saltano i commenti e le righe che cominciano con `-` (`-r altro.txt`):
    i file da leggere sono gia' elencati tutti in `REQUISITI`.
    """
    from packaging.requirements import Requirement

    percorsi = file if file is not None else tuple(ROOT / n for n in REQUISITI)
    visti: dict[str, object] = {}
    for percorso in percorsi:
        for riga in percorso.read_text(encoding="utf-8").splitlines():
            riga = riga.split("#", 1)[0].strip()
            if not riga or riga.startswith("-"):
                continue
            requisito = Requirement(riga)
            visti.setdefault(nome_canonico(requisito.name), requisito)
    return list(visti.values())


def chiusura(radici, installati: dict) -> tuple[set[str], set[str]]:
    """Cio' da cui il prodotto dipende: le radici, e tutto cio' che richiedono.

    Torna `(nomi, mancanti)`, con i nomi in forma canonica. `mancanti` sono i
    pacchetti richiesti in questo ambiente che non risultano installati: non
    dovrebbero essercene, e se ce ne sono l'elenco esce incompleto.

    Un requisito con una condizione (`; sys_platform == "win32"`,
    `; extra == "ocr"`) conta solo se la condizione e' vera **qui**: e' la
    stessa domanda che si fa pip, e senza farla entrerebbero nell'elenco le
    dipendenze di un altro sistema operativo e di funzioni opzionali che
    nessuno ha chiesto.
    """
    from packaging.requirements import Requirement

    nomi: set[str] = set()
    mancanti: set[str] = set()
    visitati: set[tuple[str, tuple[str, ...]]] = set()
    da_visitare = list(radici)
    while da_visitare:
        requisito = da_visitare.pop()
        nome = nome_canonico(requisito.name)
        chiave = (nome, tuple(sorted(requisito.extras)))
        if chiave in visitati:
            continue
        visitati.add(chiave)
        distribuzione = installati.get(nome)
        if distribuzione is None:
            mancanti.add(nome)
            continue
        nomi.add(nome)
        for testo in distribuzione.requires or []:
            figlio = Requirement(testo)
            if figlio.marker is not None and not any(
                    figlio.marker.evaluate({"extra": extra})
                    for extra in (sorted(requisito.extras) or [""])):
                continue
            da_visitare.append(figlio)
    return nomi, mancanti


def del_prodotto() -> list:
    """Le distribuzioni installate da cui Mr. Rao dipende, e solo quelle."""
    installati = {}
    for d in distributions():
        nome = (d.metadata["Name"] or "").strip()
        if nome:
            installati.setdefault(nome_canonico(nome), d)
    nomi, mancanti = chiusura(dichiarati(), installati)
    if mancanti:
        # Non si ferma niente: l'elenco dice cio' che c'e'. Ma chi lo genera
        # deve saperlo, perche' un pacchetto dichiarato e non installato e' un
        # ambiente che non e' quello del prodotto.
        print("attenzione: richiesti e non installati, quindi fuori dall'elenco: "
              + ", ".join(sorted(mancanti)), file=sys.stderr)
    return [installati[n] for n in sorted(nomi)]


def raccogli() -> list[dict]:
    voci = []
    for d in del_prodotto():
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
    # I pacchetti che nei metadati non dicono sotto quale licenza stanno. Si
    # calcolano invece di essere elencati a mano: un elenco scritto qui
    # direbbe il vero finche' nessuno aggiorna una dipendenza.
    non_dichiarate = [v for v in voci if v["licenza"] == "non dichiarata"]
    # Idem per MPL: la frase in fondo nominava il solo `certifi` mentre nel
    # pacchetto ce n'erano tre.
    mpl = [v for v in voci if "MPL" in v["licenza"].upper()
           or "MOZILLA" in v["licenza"].upper()]

    r: list[str] = []
    a = r.append
    a("# Componenti di terze parti — Mr. Rao")
    a("")
    a("> Generato da `scripts/gen_third_party.py` leggendo i metadati dei pacchetti")
    a("> **realmente installati**, fra quelli da cui Mr. Rao dipende: ciò che")
    a("> dichiara in `requirements.txt` e `requirements-build.txt`, e ciò che quei")
    a("> pacchetti si portano dietro. Non modificare a mano: rigenerare.")
    a("")
    a("Mr. Rao **non** è un fork di questi progetti: li usa come dipendenze.")
    a("Le loro licenze restano integre e **prevalgono** sui rispettivi file.")
    a("")
    a("Mr. Rao è distribuito sotto **[AGPL-3.0](LICENSE)**. Le licenze qui")
    a("elencate sono compatibili con l'AGPL-3.0: permissive (MIT, BSD, Apache-2.0,")
    a("PSF), copyleft di file (MPL-2.0, esplicitamente compatibile) e LGPL, che")
    a("l'AGPL può incorporare. La licenza di Mr. Rao **non** limita i diritti che")
    a("queste librerie concedono.")
    a("")
    if non_dichiarate:
        # La frase precedente diceva «tutte compatibili» mentre la tabella
        # sotto scriveva «non dichiarata» su una riga: due affermazioni dello
        # stesso file che si smentivano. Un pacchetto senza licenza nei
        # metadati non e' incompatibile — e' **non verificabile da qui**, che
        # e' una cosa diversa e va detta come tale.
        elenco = ", ".join(f"`{v['nome']}`" for v in non_dichiarate)
        verbo = "non dichiara" if len(non_dichiarate) == 1 else "non dichiarano"
        riga_giu = "la riga" if len(non_dichiarate) == 1 else "le righe"
        a("**Con un'eccezione, e riguarda cosa si può verificare, non la")
        a(f"compatibilità.** {elenco} {verbo} nessuna licenza nei propri")
        a(f"metadati, quindi {riga_giu} più in basso dice «non dichiarata» e questo")
        a("generatore non ha modo di sapere di più: legge i metadati, non i")
        a("repository. Chi ridistribuisce e ha bisogno della certezza la cerca")
        a("nel sorgente del pacchetto, non in questa tabella.")
        a("")
    a(f"Pacchetti da cui dipende: **{len(voci)}** — di cui **{len(copyleft)}** con obblighi")
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
    a("**pystray** (LGPL-3.0) è l'unica libreria LGPL del pacchetto: testo di")
    a("licenza, NOTICE e istruzioni di sostituzione in `licenses/pystray/`.")
    a("Essendo Mr. Rao distribuito sotto AGPL-3.0 con il sorgente completo,")
    a("l'obbligo LGPL di consentirne la sostituzione è soddisfatto di conseguenza.")
    a("")
    a("**PyInstaller** è GPLv2-or-later **con eccezione esplicita** che consente di")
    a("costruire e distribuire programmi non liberi: è ciò che rende lecito")
    a("distribuire `MrRao.exe`, il cui bootloader deriva da PyInstaller.")
    a("Serve solo per costruire il pacchetto portable, non a runtime.")
    a("")
    if mpl:
        nomi_mpl = ", ".join(v["nome"] for v in mpl)
        a(f"**MPL-2.0** ({nomi_mpl}) è copyleft *per file*: obbliga a rendere")
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

    a("## Se non vuoi nemmeno la dipendenza LGPL")
    a("")
    a("Disinstalla pystray: si perde solo l'icona nella barra di sistema, e")
    a("l'applicazione resta pienamente utilizzabile dal browser e da riga di")
    a("comando. Il riconoscimento dei dati personali non ne dipende.")
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
