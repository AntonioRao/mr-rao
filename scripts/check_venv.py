"""Controlla che l'ambiente non contenga resti di disinstallazioni fallite.

Su Windows, quando pip non riesce a cancellare un file perche' e' in uso —
tipicamente un `.pyd` gia' caricato da un processo attivo — non fallisce:
lo **rinomina** anteponendo una tilde e conta di toglierlo dopo. Se quel
"dopo" non arriva, restano cartelle come `~klearn` e, peggio, un residuo
col nome giusto ma senza `__init__.py`.

Quel residuo e' velenoso perche' Python lo considera un *namespace
package*: `import scipy` riesce, `scipy.__file__` e' `None`. PyInstaller
ci casca, chiede il percorso del modulo e muore con un `TypeError` che
non nomina mai la vera causa.

E' successo davvero: la rimozione di una dipendenza ha lasciato 71 MB di
macerie che hanno rotto il build del pacchetto portable due versioni piu'
tardi, con un errore che sembrava un difetto di PyInstaller.

Uso:  python scripts/check_venv.py
"""
from __future__ import annotations

import importlib.metadata as md
import sys
import sysconfig
from pathlib import Path

# Cartelle senza __init__.py che stanno li' legittimamente: librerie
# native affiancate ai pacchetti, e namespace package veri.
_ATTESE = {
    "__pycache__",
    "numpy.libs",
    "pandas.libs",
    "shapely.libs",
    "google",
    "faker",
    "_distutils_hack",
}


def _pacchetti_dichiarati() -> set[str]:
    nomi: set[str] = set()
    for dist in md.distributions():
        for f in dist.files or []:
            parti = Path(str(f)).parts
            if parti:
                nomi.add(parti[0])
    return nomi


def controlla(site_packages: Path) -> list[str]:
    problemi: list[str] = []
    if not site_packages.is_dir():
        return [f"cartella inesistente: {site_packages}"]

    dichiarati = _pacchetti_dichiarati()

    for voce in sorted(site_packages.iterdir()):
        if not voce.is_dir():
            continue
        nome = voce.name

        if nome.startswith("~"):
            problemi.append(
                f"{nome}: resto di una disinstallazione non completata "
                f"(pip rinomina con la tilde cio' che non riesce a cancellare)"
            )
            continue

        if nome in _ATTESE or nome.endswith((".dist-info", ".egg-info", ".libs")):
            continue
        if (voce / "__init__.py").exists() or (voce / "__init__.pyi").exists():
            continue
        if nome in dichiarati:
            continue

        # Nessun __init__.py, nessun pacchetto che lo rivendichi: se dentro
        # c'e' del codice, e' un residuo, e Python lo importera' lo stesso
        # come namespace package.
        codice = [p for p in voce.rglob("*") if p.suffix in (".pyd", ".so", ".py", ".dll")]
        if codice:
            problemi.append(
                f"{nome}/: {len(codice)} file di codice ma nessun "
                f"__init__.py e nessun pacchetto installato che li rivendichi"
            )

    return problemi


def main() -> int:
    site_packages = Path(sysconfig.get_paths()["purelib"])
    problemi = controlla(site_packages)
    if not problemi:
        print(f"venv pulito: {site_packages}")
        return 0
    print(f"Resti di disinstallazioni in {site_packages}:", file=sys.stderr)
    for p in problemi:
        print(f"  - {p}", file=sys.stderr)
    print(
        "\nRimuovi quelle cartelle a mano: un residuo con il nome giusto ma "
        "senza __init__.py fa fallire il build del pacchetto portable con un "
        "errore che non lo nomina.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
