"""Mr. Rao CLI — convert files and watch folders.

Usage:
  python -m mr_rao.cli convert file.pdf -o out.md
  python -m mr_rao.cli convert *.pdf --merge -o all.md
  python -m mr_rao.cli watch ./inbox ./out
  python -m mr_rao.cli health
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from config import ALLOWED_EXTENSIONS, APP_NAME, APP_VERSION
from mr_rao.converter import ConvertOptions, convert_file, merge_markdowns
from mr_rao.privacy import FIELD_DEFAULTS, PrivacyOptions
from mr_rao.watch_service import output_path_for, write_atomic


def _build_options(args: argparse.Namespace) -> ConvertOptions:
    privacy_on = not getattr(args, "no_privacy", False)
    return ConvertOptions(
        engine=getattr(args, "engine", "auto"),
        language=getattr(args, "language", "it"),
        # Elencare i campi a mano qui e' una trappola: un riconoscitore
        # aggiunto dopo resterebbe acceso anche con --no-privacy, perche'
        # il suo valore predefinito e' True. I campi si leggono dal motore.
        privacy=PrivacyOptions(
            **{
                **{k: True for k in FIELD_DEFAULTS},
                "amounts": getattr(args, "scrub_amounts", False),
                "dates": getattr(args, "scrub_dates", False),
                "name_guess": not getattr(args, "no_name_guess", False),
            }
        )
        if privacy_on
        else PrivacyOptions(**{k: False for k in FIELD_DEFAULTS}),
        include_tables=not getattr(args, "no_tables", False),
        include_frontmatter=not getattr(args, "no_frontmatter", False),
        clean_output=getattr(args, "clean", False),
        force_ocr_pdf=getattr(args, "force_ocr", False),
    )


def cmd_convert(args: argparse.Namespace) -> int:
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
            print(f"File non trovato: {p}", file=sys.stderr)
            return 1

    if not paths:
        print("Nessun file da convertire.", file=sys.stderr)
        return 1

    opts = _build_options(args)
    results = []
    for path in paths:
        print(f"> {path.name}...", flush=True)
        r = convert_file(path, options=opts)
        if r.error:
            print(f"  ERRORE: {r.error}", file=sys.stderr)
            if not args.merge:
                return 1
        else:
            print(f"  ok ({r.engine_used}, redactions={r.redaction.total})")
        results.append(r)

    if args.merge:
        md = merge_markdowns(results, title=args.title or "Documento unificato")
        out = Path(args.output or "merged.md")
        out.write_text(md, encoding="utf-8")
        print(f"Salvato merge: {out}")
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
        print(f"Salvato: {out}")
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    inbox = Path(args.inbox)
    outbox = Path(args.outbox)
    inbox.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)
    opts = _build_options(args)
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
                    print(f"  ERRORE: {r.error}")
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
        from rapidocr_onnxruntime import RapidOCR  # noqa: F401

        print("rapidocr: ok")
    except Exception as e:
        print(f"rapidocr: FAIL ({e})")
    try:
        import bs4  # noqa: F401

        print("beautifulsoup4: ok")
    except Exception as e:
        print(f"beautifulsoup4: FAIL ({e})")
    return 0


def main(argv: list[str] | None = None) -> int:
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
        "--no-name-guess",
        action="store_true",
        help="Disattiva l'euristica del cognome (due parole maiuscole)",
    )
    p_conv.add_argument("--no-tables", action="store_true")
    p_conv.add_argument("--no-frontmatter", action="store_true")
    p_conv.add_argument("--clean", action="store_true", help="Output pulito per LLM")
    p_conv.add_argument("--force-ocr", action="store_true")
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

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
