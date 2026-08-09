"""Mr. Rao CLI — convert files and watch folders.

Usage:
  python -m mr_rao.cli convert file.pdf -o out.md
  python -m mr_rao.cli convert *.pdf --merge -o all.md
  python -m mr_rao.cli watch ./inbox ./out
  python -m mr_rao.cli health
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from config import ALLOWED_EXTENSIONS, APP_NAME, APP_VERSION
from mr_rao.converter import ConvertOptions, convert_file, merge_markdowns
from mr_rao.privacy import (
    CORE,
    EN,
    FIELD_DEFAULTS,
    IT,
    PrivacyOptions,
    termini_da,
)
from mr_rao.watch_service import output_path_for, write_atomic


def _build_options(args: argparse.Namespace) -> ConvertOptions:
    privacy_on = not getattr(args, "no_privacy", False)
    # Il nucleo c'e' sempre: spegnerlo vorrebbe dire rinunciare a IBAN e
    # carte, che valgono in ogni Paese.
    pacchetti = (CORE,) + tuple(
        p
        for p, arg in ((IT, "no_pack_it"), (EN, "no_pack_en"))
        if not getattr(args, arg, False)
    )
    return ConvertOptions(
        engine=getattr(args, "engine", "auto"),
        language=getattr(args, "language", "it"),
        # Elencare i campi a mano qui e' una trappola: un riconoscitore
        # aggiunto dopo resterebbe acceso anche con --no-privacy, perche'
        # il suo valore predefinito e' True. I campi si leggono dal motore.
        privacy=PrivacyOptions(
            pacchetti=pacchetti,
            # Le due liste dello studio. Si passano ripetendo l'opzione o da
            # un file con `@elenco.txt`: chi ne ha trenta non li scrive sulla
            # riga di comando, e una lista di clienti nella cronologia della
            # shell e' proprio cio' che questo programma esiste per evitare.
            sempre=termini_da(getattr(args, "sempre", None) or ()),
            mai=termini_da(getattr(args, "mai", None) or ()),
            **{
                **{k: True for k in FIELD_DEFAULTS},
                "amounts": getattr(args, "scrub_amounts", False),
                "dates": getattr(args, "scrub_dates", False),
                # Spenta di default (#5): il flag ora l'accende. `--no-name-guess`
                # resta accettato e non fa niente, perche' e' finito in
                # script e appunti di chi lo usava per difendersi da questa
                # stessa regola. Toglierlo li farebbe fallire per dire loro
                # una cosa che ora e' il comportamento predefinito.
                "name_guess": getattr(args, "name_guess", False),
            },
        )
        if privacy_on
        else PrivacyOptions(**{k: False for k in FIELD_DEFAULTS}),
        include_tables=not getattr(args, "no_tables", False),
        include_frontmatter=not getattr(args, "no_frontmatter", False),
        clean_output=getattr(args, "clean", False),
        force_ocr_pdf=getattr(args, "force_ocr", False),
    )


def _scrivi(riga: str) -> None:
    """Stampa senza morire su una console cp1252.

    I campioni dei sospetti sono mascherati con dei pallini (U+2022): su una
    console italiana predefinita finiscono contro un UnicodeEncodeError, e il
    programma si chiuderebbe proprio mentre sta dicendo la cosa piu'
    importante.
    """
    try:
        print(riga, flush=True)
    except UnicodeEncodeError:
        print(riga.encode("ascii", "replace").decode("ascii"), flush=True)


def _scrivi_err(riga: str) -> None:
    """Come `_scrivi`, ma sul canale degli errori."""
    try:
        print(riga, file=sys.stderr, flush=True)
    except UnicodeEncodeError:
        print(riga.encode("ascii", "replace").decode("ascii"), file=sys.stderr, flush=True)


# --- P0.4: la traccia dell'ultimo errore ----------------------------------
#
# Il problema: dal tasto destro la finestra puo' sparire prima che si legga
# qualcosa. `--attendi` (1.7.x) copre solo il caso in cui l'utente e' davanti
# allo schermo *e* c'e' una console vera: se il processo muore prima che
# Python parli, se stdin non e' un terminale, o se semplicemente l'utente e'
# andato a prendere un caffe', resta un lampo e nient'altro.
#
# Fra le due forme possibili — finestra di messaggio nativa o file — qui si
# sceglie il **file**, per tre motivi:
#
#   1. la richiesta e' «una traccia che si puo' leggere DOPO». Una MessageBox
#      e' esattamente lo stesso limite di `--attendi`: se non c'e' nessuno
#      davanti, non serve a niente e sparisce quando qualcuno clicca OK;
#   2. MessageBoxW e' modale e bloccante. In `watch`, in una pipeline o in CI
#      terrebbe fermo il processo per sempre senza che nessuno la veda: ogni
#      guardia che si aggiunge per evitarlo e' un modo in cui il feedback
#      puo' di nuovo non comparire;
#   3. un eseguibile che muore prima di arrivare a Python non puo' aprire
#      nessuna finestra. Quel caso lo copre il *lanciatore* (il `pause` nel
#      .bat e nel comando del menu contestuale), non il programma.
#
# Ma un registro, su uno strumento di privacy, e' esso stesso un dato. Un
# file che elenca `C:\clienti\Rossi\cartella-clinica.pdf` racconta di chi
# sono i documenti che l'utente converte: e' proprio il metadato che questo
# programma esiste per non far girare. Quindi, dichiarato:
#
#   COSA C'E'    data e ora, l'estensione e la dimensione approssimativa del
#                documento, e il motivo del fallimento.
#   COSA NON     il nome del file, il percorso, la cartella, il contenuto,
#   C'E'         l'elenco delle conversioni riuscite. Il motivo viene ripulito
#                da qualunque percorso prima di essere scritto: i messaggi di
#                sistema (`[Errno 13] ... 'C:\\...\\x.pdf'`) se lo portano
#                dietro.
#   QUANTO       una riga sola, riscritta ogni volta: c'e' l'ultimo errore,
#   RESTA        non una cronologia. Dopo sette giorni la prima conversione
#                successiva lo cancella.
#   DOVE STA     %LOCALAPPDATA%\Mr Rao, cioe' `user_folders.app_data_dir()`.
#                NON `config.WRITABLE_DIR`, che nel portable e' la cartella
#                dell'eseguibile: da li' seguirebbe il programma dentro
#                OneDrive, nei backup e nello zip passato a un collega — lo
#                stesso ragionamento che in config.py tiene SECRET_KEY fuori
#                dal disco. E nemmeno `folders_root()`, che puo' essere
#                Documenti: un file di errori in mezzo ai documenti sembra un
#                documento.
#
# Chi non ne vuole sapere niente: MR_RAO_TRACCIA=0 e non viene scritto nulla.

TRACCIA_GIORNI = 7
TRACCIA_NOME = "ultimo-errore.txt"
_ENV_TRACCIA = "MR_RAO_TRACCIA"
_TRACCIA_SPENTA = {"", "0", "no", "off", "none", "false"}

# Percorsi Windows (`C:\...`, `\\server\...`) e POSIX, quello che si infila
# nei messaggi di sistema senza che nessuno lo abbia chiesto.
#
# Il ramo POSIX pretende **due** segmenti e nessuna lettera prima della barra.
# Una barra sola, presa da sola, mangiava «and/or» e «I/O» trasformando un
# messaggio leggibile in «and<percorso>»: una ripulitura troppo larga non
# protegge di piu', rende solo illeggibile la sola frase utile del file.
_RE_PERCORSO = re.compile(
    r"(?:[A-Za-z]:[\\/]|\\\\)[^\s'\"<>|,;]+"
    r"|(?<![\w.])/[^\s'\"<>|,;/]+/[^\s'\"<>|,;]*"
)


def percorso_traccia() -> Path | None:
    """Dove finisce la traccia, o None se l'utente l'ha spenta."""
    scelta = os.environ.get(_ENV_TRACCIA)
    if scelta is not None:
        if scelta.strip().lower() in _TRACCIA_SPENTA:
            return None
        return Path(scelta).expanduser()
    from mr_rao.user_folders import app_data_dir

    return app_data_dir() / TRACCIA_NOME


def _senza_percorsi(motivo: str, path: Path | None) -> str:
    """Toglie dal messaggio tutto cio' che identifica il documento.

    Prima i nomi veri (che un percorso generico non intercetta se il file si
    chiama `Rossi.pdf` e sta nella cartella corrente), poi qualunque cosa
    somigli a un percorso. In fondo resta la sola frase utile."""
    testo = str(motivo)
    if path is not None:
        pezzi = {str(path), path.name, path.stem}
        try:
            risolto = path.resolve()
            pezzi |= {str(risolto), str(risolto.parent)}
        except OSError:
            pass
        for pezzo in sorted((p for p in pezzi if len(p) > 2), key=len, reverse=True):
            testo = re.sub(re.escape(pezzo), "<documento>", testo, flags=re.IGNORECASE)
    return _RE_PERCORSO.sub("<percorso>", testo).strip()


def _descrivi_documento(path: Path | None) -> str:
    """Il documento senza dire di chi e': estensione e ordine di grandezza."""
    if path is None:
        return "un documento"
    ext = path.suffix.lower() or "senza estensione"
    try:
        byte = path.stat().st_size
    except OSError:
        return f"un file {ext}"
    if byte >= 1024 * 1024:
        misura = f"{byte / (1024 * 1024):.1f} MB".replace(".", ",")
    elif byte >= 1024:
        misura = f"{round(byte / 1024)} KB"
    else:
        misura = f"{byte} byte"
    return f"un file {ext} da {misura}"


def scade_traccia(adesso: float | None = None) -> None:
    """Cancella la traccia se e' piu' vecchia di TRACCIA_GIORNI.

    Si chiama all'inizio di ogni conversione: la ritenzione e' limitata da
    sola, senza che l'utente debba ricordarsi di niente. Non fa rumore se
    fallisce — non riuscire a cancellare un file di appoggio non e' un buon
    motivo per non convertire un documento.
    """
    f = percorso_traccia()
    if f is None:
        return
    try:
        if not f.is_file():
            return
        eta = (adesso if adesso is not None else time.time()) - f.stat().st_mtime
        if eta > TRACCIA_GIORNI * 86400:
            f.unlink()
    except OSError:
        pass


def scrivi_traccia(motivo: str, path: Path | None, quanti: int = 1) -> Path | None:
    """Scrive (riscrivendola) la traccia dell'ultimo errore.

    Restituisce il file scritto, o None se la traccia e' spenta o il disco
    non collabora. In UTF-8 **con BOM**: questo file lo apre un umano con
    doppio clic, e senza BOM il Blocco note di Windows 8/10 vecchi mostra
    «e' aperto» al posto di «è aperto» — cioe' il testo sembra guasto proprio
    mentre sta spiegando un guasto.
    """
    f = percorso_traccia()
    if f is None:
        return None
    quando = datetime.now().strftime("%d/%m/%Y %H:%M")
    riga_extra = (
        f"\nIn questa esecuzione i file non convertiti sono {quanti}; qui sotto\n"
        "c'è l'ultimo.\n"
        if quanti > 1
        else ""
    )
    testo = (
        f"{APP_NAME} {APP_VERSION} - ultimo errore\n"
        f"{quando}\n"
        f"{riga_extra}\n"
        f"Non sono riuscito a convertire {_descrivi_documento(path)}.\n\n"
        f"    {_senza_percorsi(motivo, path) or 'motivo non disponibile'}\n\n"
        "-- come leggere questo file --------------------------------------\n"
        "\n"
        "Contiene SOLO l'ultimo errore e viene riscritto da capo ogni volta:\n"
        "non è una cronologia delle tue conversioni.\n"
        "\n"
        "Di proposito non ci trovi il nome del documento, il suo percorso,\n"
        "la cartella o il contenuto. Un elenco dei file che converti sarebbe\n"
        "esso stesso un dato personale, ed è il genere di cosa che Mr. Rao\n"
        "esiste per non far girare.\n"
        "\n"
        f"Puoi cancellarlo quando vuoi. Se non lo fai, dopo {TRACCIA_GIORNI} "
        "giorni lo\ncancella da sola la prima conversione successiva.\n"
        f"Per non scriverlo affatto, imposta {_ENV_TRACCIA}=0\n"
    )
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(testo, encoding="utf-8-sig")
    except OSError as e:
        # Detto, non taciuto: se la traccia non si scrive, chi legge la
        # console deve saperlo, altrimenti andra' a cercare un file che non
        # c'e' e concludera' che il programma mente.
        _scrivi_err(f"  (non riesco a scrivere la traccia in {f}: {e.strerror or e})")
        return None
    return f


def segnala_errore(motivo: str, path: Path | None, quanti: int = 1) -> None:
    """Stampa l'errore e lascia la traccia, dicendo dov'e'."""
    _scrivi_err(f"  ERRORE: {motivo}")
    f = scrivi_traccia(motivo, path, quanti)
    if f is not None:
        _scrivi_err("  Se la finestra si chiude, il motivo resta scritto qui:")
        _scrivi_err(f"    {f}")


def _stampa_esito(r) -> bool:
    """Racconta cosa e' successo. Torna True se c'e' qualcosa da guardare.

    Il conteggio delle redazioni da solo era meta' della storia, ed e' la
    meta' rassicurante. L'altra sono i **sospetti**: cio' che somiglia a un
    dato personale ed e' rimasto nel testo perche' il riconoscitore non ha
    potuto esserne certo -- tipicamente un codice storpiato dallo scanner.
    Vivevano solo nell'interfaccia web, cioe' mancavano proprio dal percorso
    piu' comodo e quindi piu' usato: il tasto destro.

    Un documento con «2 redazioni» e due sospetti non e' un documento
    anonimizzato, e dirne solo il primo numero contraddice quello che
    PRIVACY.md dichiara: «zero redazioni non significa documento pulito».
    """
    totale = r.redaction.total
    sospetti = list(getattr(r.redaction, "suspects", None) or [])
    _scrivi(f"  ok ({r.engine_used}) - {totale} redazioni")

    if not sospetti:
        return totale > 0

    _scrivi(f"  !! {len(sospetti)} da controllare: somigliano a dati personali")
    _scrivi("     e sono rimasti nel testo, perche' non c'era certezza.")
    for s in sospetti:
        # Il pallino della maschera (U+2022) sta bene nell'interfaccia web e
        # non esiste in cp1252: su una console italiana diventerebbe un punto
        # interrogativo, cioe' lo stesso carattere che segnala un guasto.
        # Un asterisco si legge uguale ovunque e non sembra un errore.
        campione = str(s.get("sample", "")).replace("•", "*")
        _scrivi(f"       {s.get('kind', '?')}  {campione}")
        perche = s.get("why")
        if perche:
            _scrivi(f"         {perche}")
    return True


def _attendi_se_serve(args: argparse.Namespace, da_guardare: bool) -> None:
    """Tiene aperta la finestra quando c'e' qualcosa da leggere.

    Il tasto destro lanciava la conversione e la finestra si chiudeva
    all'istante: restava un .md e nessuna idea di cosa fosse stato tolto o
    segnalato. Il percorso piu' comodo saltava in silenzio il controllo che
    PRIVACY.md chiama «quello che conta».

    Si ferma **solo** se c'e' qualcosa da dire. Fermarsi anche a mani vuote
    insegnerebbe a chiudere senza leggere, che e' peggio di non fermarsi.
    """
    if not getattr(args, "attendi", False) or not da_guardare:
        return
    if not sys.stdin or not sys.stdin.isatty():
        return  # in una pipeline non c'e' nessuno che prema un tasto
    _scrivi("")
    try:
        input("Premi Invio per chiudere. ")
    except (EOFError, KeyboardInterrupt):
        pass


def cmd_convert(args: argparse.Namespace) -> int:
    scade_traccia()
    paths: list[Path] = []
    for p in args.files:
        path = Path(p)
        if path.is_dir():
            for child in sorted(path.iterdir()):
                if child.suffix.lower() in ALLOWED_EXTENSIONS:
                    paths.append(child)
        elif path.exists():
            paths.append(path)
        else:
            # Anche questo e' un fallimento del tasto destro, e sparisce con
            # la finestra come tutti gli altri: lascia la sua traccia.
            segnala_errore(f"File non trovato: {path.name}", path)
            _attendi_se_serve(args, True)
            return 1

    if not paths:
        segnala_errore("Nessun file da convertire.", None)
        _attendi_se_serve(args, True)
        return 1

    opts = _build_options(args)
    results = []
    da_guardare = False
    falliti = 0
    for path in paths:
        _scrivi(f"> {path.name}...")
        r = convert_file(path, options=opts)
        if r.error:
            falliti += 1
            segnala_errore(r.error, path, falliti)
            if not args.merge:
                _attendi_se_serve(args, True)
                return 1
            da_guardare = True
        else:
            da_guardare = _stampa_esito(r) or da_guardare
        results.append(r)

    if args.merge:
        md = merge_markdowns(results, title=args.title or "Documento unificato")
        out = Path(args.output or "merged.md")
        out.write_text(md, encoding="utf-8")
        _scrivi(f"Salvato merge: {out}")
        _attendi_se_serve(args, da_guardare)
        return 0

    for r, path in zip(results, paths):
        if r.error:
            continue
        if args.output and len(paths) == 1:
            out = Path(args.output)
        else:
            out_dir = Path(args.output) if args.output and Path(args.output).is_dir() else path.parent
            if args.output and not Path(args.output).is_dir() and len(paths) == 1:
                out = Path(args.output)
            else:
                out = out_dir / (path.stem + ".md")
        out.write_text(r.markdown, encoding="utf-8")
        _scrivi(f"Salvato: {out}")
    _attendi_se_serve(args, da_guardare)
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    inbox = Path(args.inbox)
    outbox = Path(args.outbox)
    inbox.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)
    opts = _build_options(args)
    scade_traccia()
    seen: set[str] = set()
    print(f"{APP_NAME} watch: {inbox} -> {outbox} (Ctrl+C per uscire)")
    try:
        while True:
            for path in sorted(inbox.iterdir()):
                if not path.is_file():
                    continue
                if path.suffix.lower() not in ALLOWED_EXTENSIONS:
                    continue
                key = f"{path.name}:{path.stat().st_mtime_ns}"
                if key in seen:
                    continue
                # skip partial writes
                try:
                    size1 = path.stat().st_size
                    time.sleep(0.4)
                    if path.stat().st_size != size1:
                        continue
                except OSError:
                    continue
                print(f"> {path.name}")
                r = convert_file(path, options=opts)
                seen.add(key)
                if r.error:
                    # Una cartella osservata gira per ore senza nessuno
                    # davanti: e' il caso in cui la traccia serve di piu'.
                    segnala_errore(r.error, path)
                    continue
                dest = output_path_for(outbox, path)
                write_atomic(dest, r.markdown)
                print(f"  -> {dest}")
                if args.move_done:
                    done = inbox / "done"
                    done.mkdir(exist_ok=True)
                    path.rename(done / path.name)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nWatch terminato.")
        return 0


def cmd_health(_args: argparse.Namespace) -> int:
    print(f"{APP_NAME} v{APP_VERSION}")
    print("status: ok")
    try:
        from markitdown import MarkItDown  # noqa: F401

        print("markitdown: ok")
    except Exception as e:
        print(f"markitdown: FAIL ({e})")
    try:
        from rapidocr import RapidOCR  # noqa: F401

        print("rapidocr: ok")
    except Exception as e:
        print(f"rapidocr: FAIL ({e})")
    try:
        import bs4  # noqa: F401

        print("beautifulsoup4: ok")
    except Exception as e:
        print(f"beautifulsoup4: FAIL ({e})")

    # Il percorso della traccia si stampa **sempre**, anche quando il file
    # non c'e'. Una traccia che l'utente non sa dove cercare non e' una
    # traccia: e quando serve davvero la finestra si e' gia' chiusa, quindi
    # il posto dove dirlo dev'essere raggiungibile a freddo.
    f = percorso_traccia()
    if f is None:
        print(f"traccia errori: disattivata ({_ENV_TRACCIA})")
    else:
        stato = "presente" if f.is_file() else "nessun errore registrato"
        print(f"traccia errori: {f} ({stato})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Il parser, costruito a parte da chi lo esegue.

    Serve perche' `scripts/check_docs.py` possa **interrogarlo** invece di
    leggere questo file con un'espressione regolare: il controllo che le
    opzioni siano tutte documentate deve guardare le opzioni vere, non una
    loro approssimazione. Una regex qui sopra si perderebbe la prima opzione
    scritta in un modo che non aveva previsto, e tacerebbe.
    """
    parser = argparse.ArgumentParser(
        prog="mr-rao",
        description=f"{APP_NAME} - convertitore documenti -> Markdown offline",
    )
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {APP_VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_conv = sub.add_parser("convert", help="Converti uno o più file")
    p_conv.add_argument("files", nargs="+", help="File o cartelle")
    p_conv.add_argument("-o", "--output", help="File o cartella di output")
    p_conv.add_argument("--engine", default="auto", choices=["auto", "rapidocr", "markitdown"])
    p_conv.add_argument(
        "--language", default="it",
        help="ignorato: il modello OCR è unico (alfabeti latini). Mantenuto per compatibilità.",
    )
    p_conv.add_argument("--merge", action="store_true", help="Unisci in un solo Markdown")
    p_conv.add_argument("--title", default="Documento unificato")
    p_conv.add_argument("--no-privacy", action="store_true")
    p_conv.add_argument("--scrub-amounts", action="store_true")
    p_conv.add_argument(
        "--scrub-dates",
        action="store_true",
        help="Redigi le date accanto a un contesto di nascita",
    )
    p_conv.add_argument(
        "--name-guess",
        action="store_true",
        help="Accendi l'euristica del cognome (due parole maiuscole). Spenta "
             "di default: su moduli e verbali produce molti falsi positivi",
    )
    p_conv.add_argument(
        "--no-name-guess",
        action="store_true",
        help=argparse.SUPPRESS,  # ora e' il comportamento predefinito
    )
    p_conv.add_argument(
        "--no-pack-it",
        action="store_true",
        help="Spegni i riconoscitori italiani (codice fiscale, P.IVA, BBAN, vie, nomi)",
    )
    p_conv.add_argument(
        "--no-pack-en",
        action="store_true",
        help="Spegni i riconoscitori anglosassoni (SSN, NINO, NHS, passaporti)",
    )
    p_conv.add_argument(
        "--sempre",
        action="append",
        metavar="TERMINE",
        help="Nascondi sempre questo termine (ripetibile). I nomi che "
        "ricorrono in ogni pratica e che le regole generali non indovinano",
    )
    p_conv.add_argument(
        "--mai",
        action="append",
        metavar="TERMINE",
        help="Non far toccare questo termine da nessun riconoscitore "
        "(ripetibile). Vince su --sempre",
    )
    p_conv.add_argument("--no-tables", action="store_true")
    p_conv.add_argument("--no-frontmatter", action="store_true")
    p_conv.add_argument("--clean", action="store_true", help="Output pulito per LLM")
    p_conv.add_argument("--force-ocr", action="store_true")
    p_conv.add_argument(
        "--attendi",
        action="store_true",
        help="Tieni aperta la finestra se c'e' qualcosa da controllare "
        "(lo usa il tasto destro; inutile in uno script)",
    )
    p_conv.set_defaults(func=cmd_convert)

    p_watch = sub.add_parser("watch", help="Osserva cartella e converte automaticamente")
    p_watch.add_argument("inbox", help="Cartella di ingresso")
    p_watch.add_argument("outbox", help="Cartella di uscita .md")
    p_watch.add_argument("--interval", type=float, default=2.0)
    p_watch.add_argument("--move-done", action="store_true")
    p_watch.add_argument("--engine", default="auto")
    p_watch.add_argument(
        "--language", default="it",
        help="ignorato: il modello OCR è unico (alfabeti latini). Mantenuto per compatibilità.",
    )
    p_watch.add_argument("--no-privacy", action="store_true")
    p_watch.add_argument("--scrub-amounts", action="store_true")
    p_watch.add_argument("--scrub-dates", action="store_true")
    p_watch.add_argument("--no-name-guess", action="store_true")
    p_watch.add_argument("--no-tables", action="store_true")
    p_watch.add_argument("--no-frontmatter", action="store_true")
    p_watch.add_argument("--clean", action="store_true")
    p_watch.add_argument("--force-ocr", action="store_true")
    p_watch.set_defaults(func=cmd_watch)

    p_health = sub.add_parser("health", help="Verifica dipendenze")
    p_health.set_defaults(func=cmd_health)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
