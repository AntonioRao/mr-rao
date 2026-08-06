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

Uso:  python scripts/make_release_zip.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import APP_VERSION  # noqa: E402

NOME_FISSO = "MrRao-Portable.zip"


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

    print()
    print("  Allegare ENTRAMBI alla release:")
    print(f"    gh release create v{APP_VERSION} \\")
    print(f'      "dist/{versionato.name}" "dist/{fisso.name}" \\')
    print(f'      --title "..." --notes-file ...')
    print()
    print("  Senza il secondo, i link di scaricamento nei README danno 404.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
