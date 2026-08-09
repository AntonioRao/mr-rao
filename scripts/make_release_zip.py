"""Prepara gli archivi da allegare alla release.

Ne produce **due**, dallo stesso pacchetto:

* ``MrRao-Portable-<versione>.zip`` — quello che si scarica sapendo cosa si
  sta scaricando, e che resta riconoscibile nella cartella Download;
* ``MrRao-Portable.zip`` — stesso contenuto, nome fisso.

Il secondo esiste per una ragione sola: GitHub serve
``/releases/latest/download/<nome>`` soltanto se il nome dell'allegato non
cambia da una versione all'altra. E' quel percorso a rendere possibile un
link di scaricamento diretto che non invecchia, senza passare dalla pagina
delle release — che e' una pagina che si trova solo se si sa che esiste.

Se una release viene pubblicata **senza** l'archivio a nome fisso, tutti i
link di scaricamento nei due README smettono di funzionare, e lo fanno in
silenzio: restituiscono un 404 a chi clicca, e nessun avviso a chi
pubblica. Per questo i due archivi si creano insieme, qui, invece che a
mano al momento della pubblicazione.

Scrive anche ``SHA256SUMS.txt``, da allegare alla release. Non sostituisce
una firma digitale e non va spacciato per tale: chiunque possa sostituire lo
zip puo' sostituire anche il file delle impronte. Serve a un'altra cosa, piu'
modesta e comunque utile — dire a chi ha scaricato se il file e' **integro**,
cioe' se e' arrivato intero e se e' lo stesso che si trova sulla pagina delle
release. Contro uno scaricamento troncato o un mirror qualsiasi vale; contro
chi controlla la pagina non vale niente.

Uso:  python scripts/make_release_zip.py
"""
from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import APP_VERSION  # noqa: E402

NOME_FISSO = "MrRao-Portable.zip"
NOME_IMPRONTE = "SHA256SUMS.txt"


def sha256(percorso: Path) -> str:
    """L'impronta, letta a blocchi: il pacchetto pesa oltre 150 MB e leggerlo
    tutto in memoria per farne l'hash e' uno spreco senza motivo."""
    h = hashlib.sha256()
    with percorso.open("rb") as f:
        for blocco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(blocco)
    return h.hexdigest()


def main() -> int:
    pacchetto = ROOT / "dist" / "MrRao-Portable"
    if not (pacchetto / "app" / "MrRao.exe").is_file():
        print(f"ERRORE: pacchetto assente o incompleto: {pacchetto}", file=sys.stderr)
        return 1

    versionato = ROOT / "dist" / f"MrRao-Portable-{APP_VERSION}.zip"
    fisso = ROOT / "dist" / NOME_FISSO
    for vecchio in (versionato, fisso):
        if vecchio.exists():
            vecchio.unlink()

    print(f"  archivio di {pacchetto} ...")
    shutil.make_archive(str(versionato.with_suffix("")), "zip", str(pacchetto))
    shutil.copy2(versionato, fisso)

    for f in (versionato, fisso):
        print(f"  {f.name:32s} {f.stat().st_size / 1e6:6.1f} MB")

    # I due archivi sono la stessa sequenza di byte -- il secondo e' una copia
    # del primo -- quindi l'impronta e' una sola e vale per entrambi. Si
    # scrivono lo stesso tutte e due le righe: chi verifica ha in mano *un*
    # file e cerca *quel* nome, e non deve stare a ragionare sul perche' non
    # c'e'. Il formato e' quello di `sha256sum`, cosi' su Linux e macOS si
    # controlla con `sha256sum -c SHA256SUMS.txt` senza spiegazioni.
    impronta = sha256(versionato)
    assert impronta == sha256(fisso), "le due copie devono essere identiche"

    impronte = ROOT / "dist" / NOME_IMPRONTE
    impronte.write_text(
        "".join(f"{impronta}  {f.name}\n" for f in (versionato, fisso)),
        encoding="utf-8",
    )
    print(f"  {NOME_IMPRONTE:32s} {impronta}")

    print()
    print("  Allegare TUTTI E TRE alla release:")
    print(f"    gh release create v{APP_VERSION} \\")
    print(f'      "dist/{versionato.name}" "dist/{fisso.name}" \\')
    print(f'      "dist/{NOME_IMPRONTE}" \\')
    print(f'      --title "..." --notes-file ...')
    print()
    print("  Senza il secondo, i link di scaricamento nei README danno 404.")
    print("  Nelle note di rilascio conviene incollare anche l'impronta:")
    print(f"    SHA-256: {impronta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
