# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Catalogo di impronte: frasi caratteristiche del nostro codice, e come cercarle la' fuori.

## Perche' serve, se il repository e' gia' pubblico

Qui la copia e' gia' legale: l'AGPL-3.0 la permette esplicitamente. Un'impronta non impedisce
niente e non lo finge -- serve a TROVARE una copia che non rispetta gli obblighi che quella
licenza porta con se' (attribuzione, stessa licenza, codice disponibile a chi usa il servizio in
rete). L'intestazione di copyright e' identica in ogni file e un copiatore la toglie per prima;
una frase caratteristica sopravvive a un rinominamento del prodotto e a una riformattazione, e
cercandola si arriva alla copia. Dodici impronte su venti dentro un repository altrui, senza
attribuzione, non sono una coincidenza: sono la prova di cosa manca.

## Cosa rende buona un'impronta

Lunga (una frase, non una parola), nostra (prosa italiana dei commenti, identificatori inusuali),
stabile (niente versioni, date, conteggi, percorsi di macchina: cambiano da soli e l'impronta
muore senza che nessuno lo noti), e improbabile per caso. Il filtro qui sotto e' volutamente
severo: un candidato scartato e' un'occasione persa, un candidato debole e' un falso positivo che
fa perdere tempo -- o peggio, una ricerca che punta il dito su un innocente.

Fuori dalla raccolta l'output rigenerato (`docs/landing/publish/`, prodotto da `_rebuild.py`: non
e' dove il testo vive, e' dove finisce) e fuori l'intestazione SPDX stessa: e' uguale in centinaia
di file, non distingue nulla.

## Il catalogo e' privato, lo strumento e' pubblico

`provenance/` e' in `.gitignore` e ci deve restare -- anche in un repository gia' pubblico. Un
catalogo che dice «ecco le mie venti impronte» e' l'elenco preciso di cosa cancellare per rendersi
invisibili. Questo file invece puo' stare in chiaro: sa CERCARE, non sa COSA.

## Perche' `raccogli` non riscrive un catalogo esistente

Le impronte scelte devono restare le stesse nel tempo: una ricerca fatta oggi si confronta con una
fatta fra sei mesi solo se cerca le stesse frasi. Rifare la scelta a ogni lancio azzererebbe lo
storico senza dirlo. Serve `--rifai`, esplicito.

Uso:  python scripts/impronte.py raccogli [--rifai]   sceglie le impronte e scrive il catalogo
      python scripts/impronte.py verifica             sono ancora tutte nel codice? (exit != 0 se no)
      python scripts/impronte.py cerca [--limite N]   le cerca su GitHub code search
"""
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOGO = ROOT / "provenance" / "impronte.json"

# Non c'e' vendorizzato in questo repository (le dipendenze arrivano da pip, vedi THIRD_PARTY.md).
# L'unica esclusione reale e' l'output rigenerato -- i due file che _rebuild.py scrive, non l'intera
# cartella: dentro docs/landing/publish/ vivono anche pagine vere non generate (impresa/, plus/).
# In pratica qui non cambia niente (questo script guarda solo .py/.js, e li' non ce ne sono), ma il
# filtro resta lo stesso di marca_copyright.py per lo stesso motivo, non per prudenza spicciola.
ALTRUI = re.compile(r"^docs/landing/publish/(index\.html|en/index\.html)$")

# Aree del prodotto. La quota per area esiste perche' un copiatore puo' prendersi solo il
# front-end, o solo il motore: se tutte le impronte stanno in un solo posto, l'altra meta' di una
# copia parziale non la vede nessuno.
AREE = {
    "core":    lambda p: p.startswith("mr_rao/") and p.endswith(".py"),
    "avvio":   lambda p: "/" not in p and p.endswith(".py"),
    "web":     lambda p: p.startswith("static/js/") and p.endswith(".js"),
    "scripts": lambda p: p.startswith("scripts/") and p.endswith(".py"),
    "tests":   lambda p: p.startswith("tests/") and p.endswith(".py"),
}
# Quote per (area, tipo). Tre tipi perche' proteggono da tre riscritture diverse: i commenti
# cadono se il copiatore li cancella, gli identificatori restano perche' rinominarli tutti rompe
# il codice, le stringhe di interfaccia restano perche' cambiarle cambia il prodotto che si sta
# spacciando per proprio.
QUOTE = {
    ("core", "commento"): 6, ("core", "identificatore"): 3, ("core", "interfaccia"): 2,
    ("avvio", "commento"): 2,
    ("web", "commento"): 3, ("web", "identificatore"): 1, ("web", "interfaccia"): 2,
    ("scripts", "commento"): 3, ("scripts", "interfaccia"): 1,
    ("tests", "commento"): 3,
}
PER_FILE = 2       # mai piu' di due impronte dallo stesso file: se quel file sparisce non crolla il catalogo
MIN_LUNG = 45      # sotto questa lunghezza una frase puo' capitare uguale a due autori diversi
MAX_LUNG = 110     # sopra, la riga e' quasi sempre spezzata a meta' da una riformattazione

# Parole funzionali italiane: la loro presenza e' cio' che rende la frase «nostra» invece che un
# idioma di libreria tradotto o una riga di inglese tecnico che chiunque scriverebbe uguale.
ITALIANE = {
    "che", "non", "per", "con", "una", "uno", "del", "della", "delle", "dei", "degli", "sono", "come",
    "quando", "perche", "perche'", "perché", "questo", "questa", "queste", "questi", "quello", "quella",
    "piu", "piu'", "più", "solo", "anche", "invece", "senza", "dopo", "prima", "sempre", "mai", "ogni",
    "gia", "gia'", "già", "cioe", "cioe'", "cioè", "nel", "nella", "nelle", "sul", "sulla", "dal",
    "dalla", "alla", "allo", "agli", "alle", "essere", "fare", "deve", "devono", "puo", "puo'", "può",
    "serve", "vale", "resta", "vuoto", "riga", "righe", "sopra", "sotto", "ma", "se", "il", "lo", "la",
    "le", "gli", "un", "in", "di", "da", "a", "e", "o", "si", "ci", "ne", "lui", "loro", "noi",
}

# Parole che rendono INUTILE un'impronta perche' identificano il prodotto o l'autore: sono le
# prime cose che un copiatore rinomina, e cercarle trova solo il rumore di chi cita il progetto.
#
# L'elenco si allunga da `provenance/nomi-propri.txt` (una parola per riga, commenti con `#`). I
# nomi che NON devono comparire in un file pubblicabile stanno li' e non qui: questo file viaggia
# con il codice (repository pubblico), quel file no. E' lo stesso confine del catalogo delle
# impronte, e vale per la stessa ragione: cio' che va tenuto fuori dal repository non si scrive
# nel repository.
_PROPRIE_BASE = [r"mr\.?\s*rao", r"rao\b", "antonio", "andrea"]


def _propri_extra() -> list[str]:
    f = ROOT / "provenance" / "nomi-propri.txt"
    if not f.exists():
        return []
    fuori = []
    for riga in f.read_text(encoding="utf-8").splitlines():
        riga = riga.split("#", 1)[0].strip()
        if riga:
            fuori.append(re.escape(riga))
    return fuori


PROPRIE = re.compile("|".join(_PROPRIE_BASE + _propri_extra()), re.I)

# Segnali di instabilita': cambiano da soli (o a ogni build) e l'impronta muore in silenzio.
INSTABILE = re.compile(r"\d|noqa|todo|fixme|type:\s*ignore|https?:|[A-Za-z]:\\|\\\\|SPDX|Copyright")

# Righe di commento che sono codice commentato o marcatori, non prosa.
NON_PROSA = re.compile(r"[{}\[\]<>=;|]|\(\)|::|->|=>")

COMMENTO_PY = re.compile(r"^\s*#\s?(.+?)\s*$")
COMMENTO_JS = re.compile(r"^\s*(?://|\*)\s?(.+?)\s*$")
# Identificatori: soglia lunga apposta. Un nome corto lo inventa chiunque; uno lungo e italiano no.
DEF_PY = re.compile(r"^\s*def\s+(_?[a-z][a-z_]{17,})\s*\(")
COST_PY = re.compile(r"^([A-Z][A-Z_]{15,})\s*=\s*")
DEF_JS = re.compile(r"^\s*(?:async\s+)?(?:function\s+([a-zA-Z_$][a-zA-Z_$]{16,})\s*\(|"
                    r"(?:const|let)\s+([a-zA-Z_$][a-zA-Z_$]{16,})\s*=\s*(?:async\s*)?[(\w])")
COST_JS = re.compile(r"^\s*const\s+([A-Z][A-Z_]{15,})\s*=")
# Morfologia italiana: le desinenze che rendono riconoscibile un identificatore nostro.
ITALIANO_SUFF = re.compile(r"(zione|zioni|mento|menti|enza|enze|anza|anze|ente|enti|ivo|ivi|iva|ive|"
                           r"ato|ati|ata|ate|ito|iti|ita|ite|uto|uti|uta|ute|are|ere|ire|oso|osa|ale|"
                           r"ali|ista|isti|aggio|ezza|tore|trice|uo|io|ia)$")
# Omografi inglesi che quelle desinenze catturano per sbaglio: `state` finisce in «ate», `data» in
# «ata», «ratio» in «io». Senza questa lista un identificatore inglese passerebbe per italiano --
# e sarebbe un'impronta che si trova in migliaia di repository, cioe' un accusatore a caso.
INGLESI = {"state", "data", "date", "update", "create", "private", "template", "generate", "validate",
           "rate", "note", "done", "mode", "base", "code", "role", "site", "line", "page", "name",
           "table", "image", "file", "title", "value", "type", "size", "time", "style", "source",
           "target", "service", "resource", "response", "request", "message", "header", "filter",
           "handle", "render", "tracker", "filtered", "api", "exec", "token", "get", "set", "list",
           "item", "count", "index", "status", "result", "config", "error", "check", "load", "save",
           "init", "main", "test", "build", "parse", "format", "active", "inactive", "ratio", "audio",
           "media", "meta", "delta", "beta", "alpha", "cache", "queue", "route", "scope", "score"}

# Stringhe di interfaccia. I delimitatori devono essere veri apici di apertura/chiusura: senza i
# due controlli di contorno l'espressione aggancia il testo compreso fra gli apostrofi di due
# parole italiane («e'» ... «puo'») dentro un commento, e l'impronta nasce gia' spezzata a meta'.
STRINGA = re.compile(r"(?<![A-Za-zÀ-ÿ0-9_])'([^'\\\n]{45,110})'(?![A-Za-zÀ-ÿ0-9_])"
                     r"|\"([^\"\\\n]{45,110})\"")


def sorgenti() -> dict[str, str]:
    """Percorso -> testo, per i soli file di prima parte tracciati da git."""
    elenco = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True,
                            encoding="utf-8").stdout.splitlines()
    fuori = {}
    for p in elenco:
        if not p.endswith((".py", ".js")) or ALTRUI.search(p):
            continue
        try:
            fuori[p] = (ROOT / p).read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
    return fuori


def pubblicato() -> str:
    """Il testo dei documenti che escono da qui: manuali, landing page, la nota per il board.

    Una frase che sta ANCHE in un documento pubblicato non e' una buona impronta: chi la ritrova
    altrove potrebbe aver copiato la pagina, che e' online per scelta nostra, e non il codice.
    L'impronta deve dimostrare una cosa sola, e questa ne dimostrerebbe due.

    Qui NON si applica il filtro `ALTRUI`, e non e' una dimenticanza: li' e' un filtro sulle
    sorgenti da cui prendere, qui e' un filtro su cosa scartare. Include apposta
    `docs/landing/publish/`: e' output, ma e' anche esattamente il testo che chiunque puo' leggere
    in rete -- allargare questo filtro puo' solo scartare qualche candidato in piu'."""
    elenco = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True,
                            encoding="utf-8").stdout.splitlines()
    pezzi = []
    for p in elenco:
        if not p.endswith((".md", ".html", ".txt")):
            continue
        try:
            pezzi.append((ROOT / p).read_text(encoding="utf-8-sig", errors="replace"))
        except OSError:
            continue
    return "\n".join(pezzi)


def _parole(testo: str) -> list[str]:
    return re.findall(r"[a-zàèéìòù']+", testo.lower())


def prosa_valida(testo: str) -> bool:
    """Una frase italiana nostra, stabile, e non un pezzo di codice commentato."""
    if not (MIN_LUNG <= len(testo) <= MAX_LUNG):
        return False
    if INSTABILE.search(testo) or PROPRIE.search(testo) or NON_PROSA.search(testo):
        return False
    if '"' in testo or "`" in testo:
        return False
    parole = _parole(testo)
    if len(parole) < 8:
        return False
    # Almeno quattro parole funzionali italiane: sotto questa soglia passano le righe di inglese tecnico.
    return sum(1 for p in parole if p in ITALIANE) >= 4


def nome_valido(nome: str) -> bool:
    """Un identificatore vale come impronta se e' lungo, italiano, e non e' un termine di dominio comune."""
    if PROPRIE.search(nome) or re.search(r"\d", nome):
        return False
    pezzi = [p.lower() for p in re.split(r"[_]|(?<=[a-z])(?=[A-Z])", nome) if p]
    if len(pezzi) < 3:
        return False
    # DUE pezzi italiani, non uno: con uno solo passa un identificatore inglese qualunque il cui
    # ultimo pezzo finisce per caso con una desinenza italiana; con due, no.
    italiani = sum(1 for p in pezzi
                   if p not in INGLESI and (p in ITALIANE or ITALIANO_SUFF.search(p)))
    return italiani >= 2


def _occorrenze(testo: str, testi: dict[str, str]) -> list[str]:
    return [p for p, t in testi.items() if testo in t]


def candidati(testi: dict[str, str], testo_pubblicato: str = "") -> list[dict]:
    """Tutti i candidati che superano i filtri, con punteggio. Nessuna scelta ancora."""
    fuori = []
    for percorso, contenuto in testi.items():
        js = percorso.endswith(".js")
        rx_com = COMMENTO_JS if js else COMMENTO_PY
        rx_def, rx_cost = (DEF_JS, COST_JS) if js else (DEF_PY, COST_PY)
        for n, riga in enumerate(contenuto.splitlines(), 1):
            commento = rx_com.match(riga)
            if commento:
                # Su una riga di commento non si cercano stringhe: quello che sembra un letterale e' prosa.
                if prosa_valida(commento.group(1).strip()):
                    fuori.append({"tipo": "commento", "testo": commento.group(1).strip(),
                                  "file": percorso, "riga": n})
                continue
            for rx in (rx_def, rx_cost):
                m = rx.match(riga)
                nome = next((g for g in (m.groups() if m else ()) if g), None)
                if nome and nome_valido(nome):
                    fuori.append({"tipo": "identificatore", "testo": nome, "file": percorso, "riga": n})
            # Una docstring e' prosa di documentazione, non testo mostrato all'utente: chiamarla
            # «interfaccia» renderebbe il rapporto di ricerca meno leggibile proprio dove serve
            # capire in fretta CHE COSA e' stato ritrovato.
            doc = not js and riga.lstrip().startswith(('"""', "'''", 'r"""', "r'''"))
            for gruppi in STRINGA.findall(riga):
                s = (gruppi[0] or gruppi[1]).strip()
                if prosa_valida(s):
                    fuori.append({"tipo": "commento" if doc else "interfaccia", "testo": s,
                                  "file": percorso, "riga": n})

    tenuti = []
    visti = set()
    for c in fuori:
        if c["testo"] in visti:
            continue
        # Un'impronta che compare in molti file e' un modello ripetuto, non una firma: distingue
        # poco, e per cancellarla basta una passata sola. Due occorrenze passano, tre no.
        if len(_occorrenze(c["testo"], testi)) > 2:
            continue
        if testo_pubblicato and c["testo"] in testo_pubblicato:
            continue
        visti.add(c["testo"])
        parole = _parole(c["testo"])
        italiane = sum(1 for p in parole if p in ITALIANE)
        # Il punteggio premia cio' che rende la ricerca conclusiva: lunghezza e densita' di
        # italiano. Il premio all'iniziale maiuscola non e' estetica: una riga che comincia una
        # frase e' meno esposta a una riformattazione che sposti il punto di a capo.
        c["punteggio"] = (len(c["testo"]) + 12 * italiane
                          + (20 if c["testo"][:1].isupper() else 0))
        tenuti.append(c)
    return tenuti


def scegli(cands: list[dict]) -> tuple[list[dict], list[str]]:
    """(impronte, quote non riempite). Quote per (area, tipo), tetto per file, ordine deterministico."""
    scelte: list[dict] = []
    vuoti: list[str] = []
    per_file: dict[str, int] = {}
    for (area, tipo), quota in QUOTE.items():
        pool = sorted([c for c in cands if AREE[area](c["file"]) and c["tipo"] == tipo],
                      key=lambda c: (-c["punteggio"], c["file"], c["riga"]))
        presi = 0
        for c in pool:
            if presi >= quota:
                break
            if per_file.get(c["file"], 0) >= PER_FILE:
                continue
            per_file[c["file"]] = per_file.get(c["file"], 0) + 1
            c["area"] = area
            scelte.append(c)
            presi += 1
        # Una quota non riempita si DICE. Un catalogo piu' corto del previsto senza spiegazione fa
        # credere che quell'area sia coperta quando non lo e'.
        if presi < quota:
            vuoti.append(f"{area}/{tipo}: {presi} su {quota} (candidati disponibili: {len(pool)})")
    scelte.sort(key=lambda c: (c["area"], c["file"], c["riga"]))
    for i, c in enumerate(scelte, 1):
        c["id"] = f"imp-{i:02d}"
    return scelte, vuoti


def _commit() -> tuple[str, str]:
    """Data e sha dell'ultimo commit. Non `datetime.now()`: il catalogo dev'essere ripetibile --
    due lanci sullo stesso albero devono produrre lo stesso file, altrimenti non si sa mai se e'
    cambiata la scelta o solo l'orologio."""
    g = subprocess.run(["git", "log", "-1", "--format=%cI%n%H"], cwd=ROOT, capture_output=True,
                       text=True, encoding="utf-8").stdout.split()
    return (g[0], g[1]) if len(g) >= 2 else ("", "")


def carica() -> dict | None:
    try:
        return json.loads(CATALOGO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def posizioni(impronta: dict, testi: dict[str, str]) -> list[str]:
    """Dove sta oggi questa impronta: `file:riga` per ogni occorrenza."""
    fuori = []
    for percorso, contenuto in sorted(testi.items()):
        for n, riga in enumerate(contenuto.splitlines(), 1):
            if impronta["testo"] in riga:
                fuori.append(f"{percorso}:{n}")
    return fuori


def verifica_catalogo(catalogo: dict | None = None) -> tuple[list[dict], list[dict]]:
    """(presenti, mancanti). E' il cuore riusato dalla rete di test: un'impronta tolta da un
    refactoring e' un'impronta che non protegge piu' niente, e sparirebbe senza un solo errore
    visibile."""
    cat = catalogo if catalogo is not None else carica()
    if cat is None:
        return [], []
    testi = sorgenti()
    presenti, mancanti = [], []
    for imp in cat.get("impronte", []):
        dove = posizioni(imp, testi)
        (presenti if dove else mancanti).append({**imp, "dove": dove})
    return presenti, mancanti


# --------------------------------------------------------------------------------------------------
# sottocomandi


def cmd_raccogli(argv: list[str]) -> int:
    if CATALOGO.exists() and "--rifai" not in argv:
        print(f"catalogo gia' presente: {CATALOGO}")
        print("non lo sovrascrivo. Le impronte scelte devono restare stabili: una ricerca fatta oggi si")
        print("confronta con una fatta fra sei mesi solo se cerca le stesse frasi. Forza con --rifai.")
        return 1
    testi = sorgenti()
    scelte, vuoti = scegli(candidati(testi, pubblicato()))
    data, sha = _commit()
    catalogo = {
        "raccolto_il": data,
        "commit": sha,
        "impronte": [{"id": c["id"], "tipo": c["tipo"], "area": c["area"], "testo": c["testo"],
                      "file": c["file"], "riga": c["riga"]} for c in scelte],
    }
    CATALOGO.parent.mkdir(parents=True, exist_ok=True)
    CATALOGO.write_text(json.dumps(catalogo, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"sorgenti di prima parte esaminati: {len(testi)}")
    print(f"impronte scelte: {len(scelte)} su {len({c['file'] for c in scelte})} file -> {CATALOGO}")
    for area in AREE:
        gruppo = [c for c in scelte if c["area"] == area]
        tipi = ", ".join(f"{t}:{sum(1 for c in gruppo if c['tipo'] == t)}"
                         for t in ("commento", "identificatore", "interfaccia")
                         if any(c["tipo"] == t for c in gruppo))
        print(f"  {area}: {len(gruppo)} su {len({c['file'] for c in gruppo})} file ({tipi})")
    for v in vuoti:
        print(f"  QUOTA NON RIEMPITA -- {v}")
    return 0


def cmd_verifica(argv: list[str]) -> int:
    cat = carica()
    if cat is None:
        print(f"nessun catalogo in {CATALOGO} -- lancia prima `raccogli`.")
        return 2
    presenti, mancanti = verifica_catalogo(cat)
    for imp in presenti:
        print(f"  ok   {imp['id']} [{imp['tipo']}] {', '.join(imp['dove'])}")
    for imp in mancanti:
        print(f"  PERSA {imp['id']} [{imp['tipo']}] attesa in {imp['file']}:{imp['riga']}")
        print(f"        {imp['testo']}")
    print(f"\n{len(presenti)}/{len(presenti) + len(mancanti)} impronte ancora presenti "
          f"(catalogo del {cat.get('raccolto_il', '?')})")
    if mancanti:
        print("RIMEDIO: se la riga e' stata riscritta di proposito, rilancia `raccogli --rifai` e")
        print("annota che lo storico delle ricerche riparte da capo. Se e' sparita per sbaglio, rimettila.")
    return 1 if mancanti else 0


# Frase che su GitHub c'e' di sicuro, in migliaia di repository. Serve a tarare lo strumento PRIMA
# di credergli: senza, una ricerca che torna zero su tutte le impronte e' indistinguibile da una
# ricerca rotta -- chiave scaduta, endpoint cambiato, query rifiutata -- e il rapporto direbbe
# «pulito» proprio quando non ha guardato niente. Non deve trovare noi: deve solo dimostrare che sa
# trovare.
TARATURA = "if __name__ == '__main__':"


def _github(testo: str) -> tuple[int, list[str], str]:
    """(numero risultati, repository, errore). La query e' la frase fra virgolette: ricerca esatta."""
    r = subprocess.run(["gh", "api", "-X", "GET", "search/code", "--raw-field", f'q="{testo}"'],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return -1, [], (r.stderr or "").strip().splitlines()[-1] if r.stderr else f"exit {r.returncode}"
    try:
        dati = json.loads(r.stdout)
    except ValueError:
        return -1, [], "risposta non JSON"
    repo = sorted({i["repository"]["full_name"] for i in dati.get("items", [])})
    return dati.get("total_count", 0), repo, ""


def cmd_cerca(argv: list[str]) -> int:
    if not shutil.which("gh"):
        print("`gh` (GitHub CLI) non e' installato o non e' nel PATH: senza non posso interrogare la")
        print("ricerca codice di GitHub. Installalo e autenticati con `gh auth login`, poi rilancia.")
        return 2
    cat = carica()
    if cat is None:
        print(f"nessun catalogo in {CATALOGO} -- lancia prima `raccogli`.")
        return 2
    impronte = cat.get("impronte", [])
    if "--limite" in argv:
        impronte = impronte[:int(argv[argv.index("--limite") + 1])]
    # GitHub limita la ricerca codice a ~10 richieste al minuto anche da autenticati: senza pausa
    # la meta' delle impronte tornerebbe «zero risultati» per un 403, che e' il falso negativo
    # peggiore possibile -- sembra tutto a posto proprio quando lo strumento non ha guardato.
    pausa = float(argv[argv.index("--pausa") + 1]) if "--pausa" in argv else 7.0
    nostri = {"antoniorao/mr-rao"}
    n_tar, _, err_tar = _github(TARATURA)
    if n_tar <= 0:
        print(f"TARATURA FALLITA: la frase di prova ({TARATURA!r}), che su GitHub sta in migliaia di")
        print(f"repository, ha dato {n_tar} risultati{' -- ' + err_tar if err_tar else ''}.")
        print("Non proseguo: con lo strumento in questo stato ogni impronta tornerebbe «zero risultati»")
        print("e il rapporto direbbe «nessuna copia» avendo in realta' guardato nel vuoto.")
        return 3
    print(f"taratura: la frase di prova da' {n_tar} risultati -- lo strumento sa trovare.")
    print(f"cerco {len(impronte)} impronte su GitHub code search, {pausa:g}s di pausa fra una e l'altra "
          f"(~{60 / pausa:.0f}/minuto contro il limite di 10): stimati {len(impronte) * pausa / 60:.1f} minuti.\n")
    trovate, errori = 0, 0
    for i, imp in enumerate(impronte):
        if i:
            time.sleep(pausa)
        n, repo, err = _github(imp["testo"])
        altrui = [r for r in repo if r.lower() not in nostri]
        etichetta = f"{imp['id']} [{imp['tipo']}/{imp['area']}]"
        if n < 0:
            errori += 1
            print(f"  ?? {etichetta} errore: {err}")
        elif altrui:
            trovate += 1
            print(f"  !! {etichetta} {n} risultati, ALTRUI: {', '.join(altrui)}")
            print(f"     {imp['testo']}")
        else:
            print(f"  -- {etichetta} {n} risultati, nessuno fuori dai nostri")
    print(f"\n{trovate} impronte trovate in repository non nostri, {errori} errori su {len(impronte)}.")
    if not trovate and not errori:
        print("Zero e' il risultato ATTESO: e' la linea di base. Serve da confronto per le prossime")
        print("ricerche -- e' quando smette di essere zero che la misura ha fatto il suo lavoro.")
    return 0


def main() -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass
    comandi = {"raccogli": cmd_raccogli, "verifica": cmd_verifica, "cerca": cmd_cerca}
    if len(sys.argv) < 2 or sys.argv[1] not in comandi:
        print(__doc__)
        return 2
    return comandi[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    sys.exit(main())
