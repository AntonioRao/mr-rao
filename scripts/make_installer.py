"""Compila l'installer .exe (Inno Setup) dal pacchetto portable gia' costruito.

Perche' esiste
--------------

Le confezioni sono tre e vengono tutte dallo **stesso** `dist/MrRao-Portable`:

* lo **zip**, per chi vuole il portatile vero -- chiavetta, niente
  installazione, dati accanto al programma;
* l'**installer .exe**, per il caso piu' comune su Windows: scarico, doppio
  clic, installato, e una voce in «App installate» per toglierlo;
* l'**MSIX**, per il Microsoft Store, che e' l'unica strada in cui il
  pacchetto lo firma Microsoft e SmartScreen tace.

Costruirle in momenti diversi vorrebbe dire tre prodotti che si chiamano
uguale. Vengono dalla stessa cartella e dallo stesso giro di CI.

Due nomi, e il secondo non e' un doppione
-----------------------------------------

Esce `MrRaoSetup-<versione>.exe` **e** `MrRaoSetup.exe` senza numero. Il
secondo e' quello che tiene in piedi
`releases/latest/download/MrRaoSetup.exe`, cioe' i pulsanti nei due README e
nelle due landing. E' la stessa ragione per cui accanto a
`MrRao-Portable-1.20.0.zip` esiste `MrRao-Portable.zip`, ed e' gia' costata
una volta: quando l'archivio versionato entro' nella release, i link col nome
fisso cominciarono a rispondere **404 in silenzio** -- una pagina che invita
a scaricare e un pulsante che non scarica niente.

`iscc` non c'e' su tutte le macchine
------------------------------------

Il compilatore di Inno Setup e' preinstallato sui runner `windows-latest`
(6.7.1); su una macchina di sviluppo qualunque puo' non esserci. Come per
`make_msix.py`, la parte che si puo' provare ovunque -- che i file da
impacchettare ci siano tutti -- non dipende da quella che serve solo a
Windows: `--controlla` verifica e non compila.

Uso:  python scripts/make_installer.py [--controlla]
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import APP_VERSION  # noqa: E402

PACCHETTO = ROOT / "dist" / "MrRao-Portable"
COPIONE = ROOT / "packaging" / "mr-rao.iss"
USCITA = ROOT / "dist"

# Cio' che il copione si aspetta di trovare nel pacchetto portable. Non e'
# un elenco decorativo: se uno di questi manca, `iscc` fallisce dopo aver
# compresso 400 MB, cioe' diversi minuti piu' tardi e con un messaggio che
# nomina un percorso temporaneo.
RICHIESTI = (
    Path("app") / "MrRao.exe",
    Path("mr_rao_shell.ps1"),
    Path("mr-rao.ico"),
    Path("LICENSE.txt"),
    Path("THIRD_PARTY.md"),
    Path("LEGGIMI.txt"),
)


def mancanti(pacchetto: Path = PACCHETTO) -> list[str]:
    """Cosa manca al pacchetto portable per poter compilare l'installer."""
    if not pacchetto.is_dir():
        return [f"manca la cartella {pacchetto}"]
    fuori = [str(r) for r in RICHIESTI if not (pacchetto / r).is_file()]
    if not (pacchetto / "licenses").is_dir():
        fuori.append("licenses/")
    return fuori


def sha256(percorso: Path) -> str:
    h = hashlib.sha256()
    with percorso.open("rb") as f:
        for blocco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(blocco)
    return h.hexdigest()


def aggiorna_impronte(impronte: Path, file: list[Path]) -> None:
    """Aggiunge l'installer a `SHA256SUMS.txt`, senza duplicare.

    Quel file lo scrive `make_release_zip.py`, che conosce solo gli zip.
    Lasciarlo cosi' vorrebbe dire pubblicare un elenco di impronte che non
    nomina uno dei file scaricabili -- e chi verifica non ha modo di sapere
    se manca perche' non serve o perche' se n'e' dimenticato qualcuno.

    Le righe dell'installer si **riscrivono**, non si accodano: questo
    script puo' girare due volte sulla stessa cartella (una prova, poi il
    build vero), e un elenco con due impronte diverse per lo stesso nome e'
    peggio di nessun elenco.
    """
    nomi = {f.name for f in file}
    vecchie = []
    if impronte.is_file():
        vecchie = [
            r
            for r in impronte.read_text(encoding="utf-8").splitlines()
            if r.strip() and r.split("  ")[-1] not in nomi
        ]
    nuove = [f"{sha256(f)}  {f.name}" for f in file]
    impronte.write_text("\n".join(vecchie + nuove) + "\n", encoding="utf-8")


def trova_iscc() -> Path | None:
    """Il compilatore di Inno Setup, cercato dove sta davvero.

    Sui runner GitHub e' nel PATH; su Windows di solito no, ed e' sotto
    Program Files. Cercarlo solo nel PATH vorrebbe dire dire «non c'e'» a
    chi ce l'ha installato.
    """
    nel_path = shutil.which("iscc")
    if nel_path:
        return Path(nel_path)
    for base in (
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        os.environ.get("ProgramFiles", r"C:\Program Files"),
    ):
        for versione in ("Inno Setup 6", "Inno Setup 5"):
            candidato = Path(base) / versione / "ISCC.exe"
            if candidato.is_file():
                return candidato
    return None


def main() -> int:
    fuori = mancanti()
    if fuori:
        print(
            "ERRORE: il pacchetto portable e' incompleto, manca:\n  "
            + "\n  ".join(fuori)
            + "\n  Costruiscilo prima: scripts\\build_portable.bat",
            file=sys.stderr,
        )
        return 1
    if not COPIONE.is_file():
        print(f"ERRORE: manca il copione {COPIONE}", file=sys.stderr)
        return 1

    print(f"  pacchetto: {PACCHETTO}")
    print(f"  copione:   {COPIONE.name}")

    if "--controlla" in sys.argv:
        print("  --controlla: tutto quello che serve c'e'. Non compilo.")
        return 0

    iscc = trova_iscc()
    if iscc is None:
        print(
            "ERRORE: ISCC.exe non trovato. E' il compilatore di Inno Setup, "
            "che sui runner windows-latest c'e' e su una macchina di "
            "sviluppo spesso no.\n"
            "  Per verificare solo che il pacchetto sia completo: --controlla",
            file=sys.stderr,
        )
        return 1

    print(f"  {iscc}")
    esito = subprocess.run(
        [
            str(iscc),
            f"/DAppVersion={APP_VERSION}",
            f"/DSorgentePortable={PACCHETTO}",
            f"/DUscita={USCITA}",
            str(COPIONE),
        ],
        capture_output=True,
        text=True,
    )
    if esito.returncode != 0:
        sys.stdout.write(esito.stdout[-4000:])
        sys.stderr.write(esito.stderr)
        print(f"ERRORE: iscc ha risposto {esito.returncode}", file=sys.stderr)
        return esito.returncode

    versionato = USCITA / f"MrRaoSetup-{APP_VERSION}.exe"
    if not versionato.is_file():
        print(
            f"ERRORE: iscc dice di aver finito ma {versionato.name} non c'e'.",
            file=sys.stderr,
        )
        return 1

    # Il nome fisso e' una **copia**, non un collegamento: gli allegati di
    # una release sono file, e un collegamento diventerebbe un file di pochi
    # byte che non installa niente.
    fisso = USCITA / "MrRaoSetup.exe"
    shutil.copy2(versionato, fisso)

    aggiorna_impronte(USCITA / "SHA256SUMS.txt", [versionato, fisso])

    mb = versionato.stat().st_size / 1e6
    print(f"  {versionato.name}  {mb:.1f} MB")
    print(f"  {fisso.name}  {mb:.1f} MB  (nome fisso: regge latest/download)")
    print("  SHA256SUMS.txt aggiornato con entrambi")
    print()
    print("  Non e' firmato: Windows mostrera' «editore sconosciuto». La")
    print("  provenienza si verifica lo stesso, con l'attestazione Sigstore")
    print("  che il workflow gli attacca:")
    print("    gh attestation verify MrRaoSetup.exe --repo AntonioRao/mr-rao")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
