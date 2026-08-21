# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Controlla che i documenti pubblicati dicano ancora la verita'.

Nasce da un errore preciso, che vale la pena tenere scritto qui. Mi era
stato chiesto di verificare che tutta la documentazione fosse aggiornata,
avevo risposto di si', e non era vero: `docs/BACKLOG.md` portava in cima
«Ultimo aggiornamento: UI Design System 2.0», fermo a quindici release
prima, e i due README dichiaravano un quality gate da «161 test» quando i
test erano piu' del doppio.

Il motivo per cui erano sfuggiti non e' distrazione, ed e' il punto:
**avevo controllato i documenti che stavo modificando**, non tutti quelli
che esistono. Un controllo che parte dall'elenco delle cose che ho in mano
trova solo quello che ho gia' guardato. Questo parte da `git ls-files`,
che non sa cosa ho toccato oggi.

Nove invarianti, tutte verificabili senza leggere il testo:

1. nessun identificativo duplicato nel backlog — «P2.7» ha significato due
   cose per qualche ora, in due stati diversi;
2. i link relativi puntano a file che esistono;
3. le versioni citate come corrente coincidono con APP_VERSION;
4. i conteggi di test dichiarati coincidono con quelli veri;
5. ogni segnaposto che il motore puo' emettere e' in PRIVACY.md;
6. ogni opzione della riga di comando e' in CLI.md;
7. la versione dichiarata in config.py ha la sua voce nel changelog;
8. le landing HTML pubblicate non dichiarano versioni o conteggi vecchi;
9. il rapporto per il board -- che non e' tracciato, perche' e' interno e
   questo repository e' pubblico -- non dichiara versioni, conteggi o link
   di ieri. E' l'unico controllo che guarda un file **non** tracciato, ed e'
   anche l'unico che puo' **saltare**: su una macchina che quel file non ce
   l'ha (la CI, o il clone di chiunque altro) il salto viene detto, perche'
   un controllo che tace quando non ha guardato sembra passato.

Il changelog e' escluso da (3) e (4) apposta: e' una cronologia, e ogni
voce cita giustamente i numeri del suo momento. Proprio quell'esclusione
lasciava scoperto (7), cioe' il caso in cui la voce non c'e' affatto.

L'ottava e' arrivata per lo stesso motivo delle prime: il controllo
guardava i `.md`, e le landing in `docs/landing/` sono `.html`. Nessuno se
n'e' accorto finche' `docs/landing/index.html` non ha dichiarato la
**1.7.2** con `APP_VERSION` alla 1.11.0 — venti release di scarto su una
pagina pubblicata, sopravvissute a un gate verde tutte le volte. Il
formato del file non c'entra niente con l'invecchiare: cambiava solo
l'estensione che il controllo sapeva aprire.

Questa intestazione ha gia' mentito una volta: diceva «quattro» mentre i
controlli erano sette, perche' chi ne ha aggiunti tre non e' passato di
qui. In un file che esiste per impedire ai documenti di invecchiare in
silenzio, e' la cosa che fa piu' rabbia — e non c'e' un controllo
automatico che possa accorgersene, quindi resta scritto qui.

Uso:  python scripts/check_docs.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import APP_VERSION  # noqa: E402

# La cronologia cita i numeri di quando e' stata scritta: e' il suo mestiere.
CRONOLOGIE = {"docs/CHANGELOG.md"}

# Pagine che non si modificano a mano: sono rigenerate da un sorgente.
# Dire «correggi questo file» su un artefatto vuol dire far fare una modifica
# che il primo rebuild cancella, quindi il messaggio deve indicare il sorgente.
RIGENERATE = {
    "docs/landing/publish/index.html": (
        "docs/landing/01-protocollo-zero.html",
        "python docs/landing/publish/_rebuild.py",
    ),
    # Senza questa voce, un problema sulla pagina inglese pubblicata sarebbe
    # segnalato con «aggiorna il numero nella pagina»: cioe' un invito a
    # modificare a mano un file rigenerato, che la ricostruzione successiva
    # butterebbe via. Il messaggio deve mandare alla sorgente.
    "docs/landing/publish/en/index.html": (
        "docs/landing/01-protocollo-zero.en.html",
        "python docs/landing/publish/_rebuild.py",
    ),
}

# Pagine pubblicate che **non parlano di questo programma**.
#
# `docs/landing/publish/mobile/` descrive Mr. Rao Mobile: altro repository,
# altro artefatto, altra numerazione. Confrontarlo con APP_VERSION lo
# dichiarava vecchio appena pubblicato — «dice 0.1.2, ma e' la 1.27.1» — e la
# risposta comoda sarebbe stata esentare la cartella. Sarebbe stata la
# risposta sbagliata: una pagina esentata puo' dire qualunque numero per
# sempre. Qui cambia il numero atteso, il confronto resta.
#
# Il limite, detto chiaro perche' non si scopra solo il giorno che morde:
# questo repository non contiene l'artefatto mobile, quindi il numero qui
# sotto e' **scritto a mano**. Se la mobile passa a una versione nuova e non si
# tocca ne' le pagine ne' questa riga, il controllo tace. Prende il caso opposto —
# pagine aggiornate e riga no — che e' quello che capita davvero, perche' le
# pagine si toccano quando si pubblica.
VERSIONI_ALTRUI = {
    "docs/landing/publish/mobile/": ("Mr. Rao Mobile", "0.1.4"),
}

_RE_ID = re.compile(r"^\| ([PSA]\d*\.\d+[a-z]?) \|", re.MULTILINE)
_RE_VERSIONE = re.compile(r"(?:versione|version)[-\s:]+(\d+\.\d+\.\d+)", re.I)
# Da tre a cinque cifre, non esattamente tre.
#
# Con `\d{3}` la 1.17.0 ha superato i mille test e il controllo ha cominciato
# a leggere «002» dentro «1002»: diceva che i documenti erano disallineati
# quando erano giusti. Un controllo che sbaglia in questo verso e' meno grave
# di uno che tace, ma e' lo stesso difetto — un numero letto male — proprio
# in cio' che esiste per accorgersi dei numeri letti male.
_RE_CONTEGGIO = re.compile(
    r"(\d{3,5})(?:%20)?[\s-]*(?:test|tests|passing|passati)", re.I)

# Lo stesso difetto e' tornato da un'altra porta: **il separatore delle
# migliaia**. Una pagina che scrive `2&nbsp;001 test` — cioe' duemilauno
# scritto bene — faceva leggere `001`, e il cancello si fermava dicendo che
# il documento era disallineato mentre era l'unico scritto per esteso.
#
# Si normalizza prima di leggere, invece di togliere il separatore dalle
# pagine: quel numero lo legge chi il repository non ce l'ha, e va scritto
# per un umano. È il controllo che deve sapere leggere.
_RE_SEPARATORE_MIGLIAIA = re.compile(
    r"(?<=\d)(?:&nbsp;|&#160;|&#xa0;|[    .’'])(?=\d{3}\b)",
    re.I,
)


def _unisci_cifre(testo: str) -> str:
    """`2&nbsp;001` → `2001`, solo fra cifre e solo su gruppi di tre."""
    return _RE_SEPARATORE_MIGLIAIA.sub("", testo)
# «2 133 test desktop» / «2 133 test Desktop superati»: la parola dopo
# distingue le due suite che il rapporto cita.
_RE_CONTEGGIO_DESKTOP = re.compile(
    r"(\d{3,5})(?:&nbsp;)?[\s-]*test[\s]*desktop", re.I
)
_RE_LINK_AMO = re.compile(
    r"https://addons\.mozilla\.org/(?:[a-z]{2}(?:-[A-Z]{2})?/)?"
    r"firefox/(?:addon/mr-rao-plus/?|downloads/file/\d+/[\w.-]+\.zip)"
)
_RE_LINK = re.compile(r"\]\(([^)#:]+\.(?:md|py|txt|ico|png|yml|bat|ps1))[^)]*\)")
_RE_VOCE_CHANGELOG = re.compile(r"^#{1,3}[ \t]*\[?v?(\d+\.\d+\.\d+)\]?", re.MULTILINE)

# Le landing non scrivono «versione 1.11.0»: scrivono «(v1.11.0)» in un
# paragrafo, «· v1.7.2» in un distintivo, «Edizione 1.7.2» in copertina.
# _RE_VERSIONE non ne prende nessuna, e un controllo che non riconosce come
# la pagina scrive il numero e' un controllo che dice sempre verde.
#
# La `v` (o la parola) e' obbligatoria apposta: un `\d+\.\d+\.\d+` da solo
# in una pagina web pesca 127.0.0.1, che in queste landing compare cinque
# volte ed e' la cosa piu' vera che ci sia scritta.
_RE_VERSIONE_LANDING = re.compile(
    r"(?:(?:versione|version|edizione|edition)[-\s:]+v?|\bv)(\d+\.\d+\.\d+)", re.I
)

# `<style>` e `<script>` sono codice, non affermazioni: dentro ci sono numeri
# a palate (z-index, durate, coordinate) e nessuna promessa al lettore.
_RE_CODICE_HTML = re.compile(r"(?is)<(script|style)\b[^>]*>.*?</\1\s*>")


def documenti() -> list[Path]:
    """Tutti i .md tracciati da git, non quelli che mi ricordo di avere."""
    uscita = subprocess.run(
        ["git", "ls-files", "*.md"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split()
    return [ROOT / p for p in uscita]


def landing() -> list[Path]:
    """Le landing HTML **tracciate**, non quelle che stanno nella cartella.

    In `docs/landing/` convivono le pagine pubblicate e gli scarti di lavoro:
    `02-carta-bianca.html`, `03-motore-vivo.html` e le anteprime sono
    gitignorate, dichiarano la 1.7.2 e nessuno le aggiornera' mai, perche'
    non fanno parte del progetto. Un glob sul disco le pescherebbe e il gate
    diventerebbe rosso per file che non esistono per chi clona il repository:
    il modo piu' rapido per far disattivare un controllo e' fargli dire cose
    che non riguardano nessuno.
    """
    uscita = subprocess.run(
        ["git", "ls-files", "docs/landing/*.html"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return [ROOT / p for p in uscita]


def _relativo(f: Path) -> str:
    return f.relative_to(ROOT).as_posix()


def _fonti_md() -> list[tuple[str, str]]:
    """I documenti su cui hanno senso i controlli (3) e (4), gia' letti."""
    return [
        (_relativo(f), f.read_text(encoding="utf-8"))
        for f in documenti()
        if _relativo(f) not in CRONOLOGIE
    ]


def _fonti_landing() -> list[tuple[str, str]]:
    return [
        (_relativo(f), _RE_CODICE_HTML.sub(" ", f.read_text(encoding="utf-8")))
        for f in landing()
    ]


def id_duplicati() -> list[str]:
    """Un elenco in cui non si puo' citare un identificativo non serve."""
    problemi = []
    for f in documenti():
        ids = _RE_ID.findall(f.read_text(encoding="utf-8"))
        visti: dict[str, int] = {}
        for i in ids:
            visti[i] = visti.get(i, 0) + 1
        for i, n in sorted(visti.items()):
            if n > 1:
                problemi.append(f"{_relativo(f)}: '{i}' compare {n} volte")
    return problemi


def link_rotti() -> list[str]:
    problemi = []
    for f in documenti():
        for m in _RE_LINK.finditer(f.read_text(encoding="utf-8")):
            if not (f.parent / m.group(1)).resolve().exists():
                problemi.append(f"{_relativo(f)}: link a '{m.group(1)}' che non esiste")
    return problemi


def versioni_incoerenti(
    fonti: list[tuple[str, str]] | None = None,
    regex: re.Pattern[str] = _RE_VERSIONE,
) -> list[str]:
    """Le versioni citate come corrente devono essere APP_VERSION.

    `fonti` e `regex` esistono perche' la stessa domanda si pone anche fuori
    dai `.md` — le landing HTML — e il confronto e' identico: cambia solo
    dove si legge e come la pagina scrive il numero. Duplicare il corpo
    avrebbe prodotto due controlli che col tempo rispondono in modo diverso
    alla stessa domanda, che e' esattamente il difetto che questo file esiste
    per impedire.
    """
    problemi = []
    for nome, testo in (_fonti_md() if fonti is None else fonti):
        prodotto, attesa = versione_attesa(nome)
        for m in regex.finditer(testo):
            if m.group(1) != attesa:
                di_chi = f" di {prodotto}" if prodotto else ""
                problemi.append(
                    f"{nome}: dice versione{di_chi} {m.group(1)}, ma e' la {attesa}"
                )
    return problemi


def versione_attesa(nome: str) -> tuple[str | None, str]:
    """Quale numero deve dichiarare questo file, e di quale prodotto.

    Quasi sempre APP_VERSION. L'eccezione sono le pagine di VERSIONI_ALTRUI,
    che parlano di un altro prodotto: li' il confronto non sparisce, cambia
    termine. Il nome del prodotto finisce nel messaggio perche' «dice 0.1.2,
    ma e' la 1.27.1» su una pagina della mobile manda a correggere la cosa
    sbagliata.
    """
    for prefisso, (prodotto, versione) in VERSIONI_ALTRUI.items():
        if nome.startswith(prefisso):
            return prodotto, versione
    return None, APP_VERSION


def conteggi_incoerenti(
    reale: int, fonti: list[tuple[str, str]] | None = None
) -> list[str]:
    problemi = []
    for nome, testo in (_fonti_md() if fonti is None else fonti):
        for m in _RE_CONTEGGIO.finditer(_unisci_cifre(testo)):
            if m.group(1) != str(reale):
                problemi.append(f"{nome}: dice {m.group(1)} test, ma sono {reale}")
    return problemi


def segnaposto_non_documentati() -> list[str]:
    """Ogni segnaposto che il motore puo' emettere dev'essere in PRIVACY.md.

    Nasce da un difetto reale e ripetuto: i documenti d'identita' sono usciti
    e non erano scritti da nessuna parte, e prima di loro dieci riconoscitori
    del pacchetto inglese — SSN, NINO, NHS number — erano nel programma dalla
    1.8.0 senza una riga nella tabella.

    Il gate diceva verde perche' guardava versioni, conteggi e link: non
    poteva accorgersi di una funzione senza documentazione. Un controllo che
    su una cosa non puo' fallire, su quella cosa non e' una verifica.

    Il segnaposto e' il punto giusto dove guardare perche' e' cio' che
    l'utente **vede nel documento**: un riconoscitore nuovo ne porta uno
    nuovo, e da li' non si scappa.
    """
    sorgenti = "".join(
        (ROOT / "mr_rao" / f).read_text(encoding="utf-8")
        for f in ("privacy.py", "en_formats.py")
        if (ROOT / "mr_rao" / f).is_file()
    )
    emessi = sorted(set(re.findall(r'"(\{\{[A-Z_]+\}\})"', sorgenti)))
    privacy = (ROOT / "docs" / "PRIVACY.md").read_text(encoding="utf-8")
    return [
        f"docs/PRIVACY.md: il motore puo' emettere {s}, ma non e' documentato"
        for s in emessi
        if s not in privacy
    ]


def moduli_non_mappati() -> list[str]:
    """Ogni modulo di `mr_rao/` dev'essere nella tabella di ARCHITECTURE.

    Meta' meccanica di **P3.19**, e nasce da un difetto reale: la scorciatoia
    sugli appunti e' uscita nella 1.18.0 con il suo modulo `appunti.py`, e la
    mappa del progetto continuava a non nominarlo. E' proprio la pagina che
    si legge per orientarsi prima di toccare qualcosa: un modulo che non c'e'
    e' un pezzo di programma che, per chi arriva, non esiste.

    Il presidio dei segnaposto (sopra) non poteva vederlo — un modulo nuovo
    non porta per forza un segnaposto nuovo.

    **L'altra meta' di P3.19 resta fuori di proposito.** Sarebbe contare i
    «segnali» dei nomi dentro la prosa di tre documenti per verificare che
    dicano lo stesso numero: un controllo che estrae un concetto dal testo
    approssima cio' che verifica, e si perde proprio il caso scritto in un
    modo che non aveva previsto. Qui invece il confronto e' fra nomi di file
    veri e testo letterale, e non c'e' niente da interpretare.

    Vale per **tutte** le lingue della pagina: una tabella tradotta che
    dimentica un modulo lascia indietro chi legge quella lingua, che e'
    esattamente il lettore che la traduzione doveva servire.
    """
    moduli = sorted(
        p.name
        for p in (ROOT / "mr_rao").glob("*.py")
        if p.name != "__init__.py"
    )
    problemi: list[str] = []
    for pagina in ("ARCHITECTURE.md", "ARCHITECTURE.en.md"):
        percorso = ROOT / "docs" / pagina
        if not percorso.is_file():
            continue
        testo = percorso.read_text(encoding="utf-8")
        problemi += [
            f"docs/{pagina}: il modulo mr_rao/{m} non e' nella tabella dei moduli"
            for m in moduli
            if m not in testo
        ]
    return problemi


def opzioni_cli_non_documentate() -> list[str]:
    """Ogni opzione della riga di comando dev'essere in docs/CLI.md.

    Il parser viene **interrogato**, non letto con un'espressione regolare:
    un controllo che approssima cio' che deve verificare si perde proprio il
    caso scritto in un modo che non aveva previsto, e tace.
    """
    sys.path.insert(0, str(ROOT))
    from mr_rao.cli import build_parser

    def opzioni(parser) -> set[str]:
        fuori: set[str] = set()
        for azione in parser._actions:
            fuori.update(o for o in azione.option_strings if o.startswith("--"))
            scelte = getattr(azione, "choices", None)
            if hasattr(scelte, "items"):  # i sottocomandi
                for sotto in scelte.values():
                    fuori |= opzioni(sotto)
        return fuori

    doc = ROOT / "docs" / "CLI.md"
    if not doc.is_file():
        return ["docs/CLI.md non esiste: le opzioni non sono documentate"]
    testo = doc.read_text(encoding="utf-8")
    # `--help` la scrive argparse da sola su ogni sottocomando.
    return [
        f"docs/CLI.md: l'opzione {o} esiste ma non e' documentata"
        for o in sorted(opzioni(build_parser()) - {"--help"})
        if o not in testo
    ]


def versione_senza_changelog(
    versione: str = APP_VERSION, changelog: str | None = None
) -> list[str]:
    """La versione dichiarata in `config.py` dev'essere nel changelog.

    E' gia' successo una volta: `APP_VERSION` bumpata, release fatta, e la
    cronologia ferma alla versione prima. Nessuno degli altri controlli poteva
    accorgersene: anzi, il changelog e' escluso apposta da `versioni_incoerenti`
    e `conteggi_incoerenti`, perche' una cronologia cita giustamente i numeri
    del suo momento. Quell'esclusione lasciava scoperto proprio il caso in cui
    il numero *nuovo* non c'e' per niente.

    Si aggancia alle intestazioni (`## 1.10.0 - titolo`) e non a una ricerca
    del numero nel testo: «1.10.0» citato dentro un paragrafo di un'altra voce
    farebbe passare il controllo senza che la voce esista. La lettura e'
    tollerante su spazi, livello di `#`, `v` iniziale e parentesi quadre dello
    stile Keep a Changelog, perche' e' formattazione, non sostanza.

    Non pretende che la voce sia in cima: durante lo sviluppo si toccano
    versioni gia' pubblicate, e un controllo che grida su ogni fix di una voce
    vecchia lo si finisce per disattivare.
    """
    if changelog is None:
        doc = ROOT / "docs" / "CHANGELOG.md"
        if not doc.is_file():
            return ["docs/CHANGELOG.md non esiste: nessuna versione e' documentata"]
        changelog = doc.read_text(encoding="utf-8")

    versioni = _RE_VOCE_CHANGELOG.findall(changelog)
    if not versioni:
        # Zero intestazioni riconosciute vuol dire regex alla deriva, non
        # changelog pulito: senza questo, il controllo direbbe verde per sempre.
        return [
            "docs/CHANGELOG.md: non riconosco nessuna intestazione di versione. "
            "Se il formato e' cambiato, aggiorna _RE_VOCE_CHANGELOG in "
            "scripts/check_docs.py, altrimenti questo controllo non puo' piu' fallire"
        ]
    if versione in versioni:
        return []
    # Il testo resta ASCII come tutti gli altri messaggi di questo file: finisce
    # su stderr, e una console Windows legacy non sa scrivere le caporali.
    return [
        f"docs/CHANGELOG.md: config.py dichiara la versione {versione}, ma non c'e' "
        f"la voce corrispondente (l'ultima documentata e' la {versioni[0]}). "
        f"Aggiungi in cima al changelog una sezione '## {versione} - <titolo>' che "
        f"racconti cosa cambia, oppure riporta APP_VERSION a una versione gia' "
        f"pubblicata se il rilascio non e' ancora stato deciso."
    ]


def landing_invecchiate(reale: int) -> list[str]:
    """Le pagine pubblicate non devono dichiarare numeri di ieri.

    Sono la prima cosa che un estraneo legge del progetto e l'ultima che
    qualcuno ricorda di aggiornare: non si rompono, non compaiono in un
    diff quando si bumpa la versione, e nessun test le apriva. Il risultato
    misurato: `index.html` ferma alla 1.7.2 con il programma alla 1.11.0.

    Riusa i controlli (3) e (4) invece di rifarli, cosi' un `.md` e una
    landing che dicono la stessa bugia ricevono la stessa risposta.
    """
    fonti = _fonti_landing()
    if not fonti:
        # Zero file vuol dire zero problemi, per sempre e in silenzio: e' il
        # modo in cui questo controllo morirebbe senza che nessuno lo noti.
        return [
            "docs/landing/: git non traccia nessuna pagina .html. Se le landing "
            "sono state spostate o rinominate, aggiorna landing() in "
            "scripts/check_docs.py, altrimenti questo controllo non puo' piu' "
            "fallire"
        ]

    problemi: list[str] = []
    dichiarate = 0
    for fonte in fonti:
        nome, testo = fonte
        # Contano solo le pagine che parlano di **questo** programma: se
        # restassero in piedi le sole pagine della mobile, il conteggio
        # sarebbe diverso da zero e il controllo «nessuno dichiara piu' una
        # versione» tacerebbe proprio nel caso che deve prendere.
        if versione_attesa(nome)[0] is None:
            dichiarate += len(_RE_VERSIONE_LANDING.findall(testo))
        trovati = versioni_incoerenti([fonte], _RE_VERSIONE_LANDING)
        trovati += conteggi_incoerenti(reale, [fonte])
        sorgente = RIGENERATE.get(nome)
        if sorgente:
            coda = (
                f". Non modificare questo file a mano: e' rigenerato. Correggi "
                f"{sorgente[0]} e rilancia '{sorgente[1]}'"
            )
        else:
            coda = (
                ". Aggiorna il numero nella pagina: e' pubblicata, e la legge "
                "chi il repository non ce l'ha"
            )
        problemi += [p + coda for p in trovati]

    if not dichiarate:
        # Se nessuna pagina dichiara piu' una versione, il confronto gira a
        # vuoto: non e' una buona notizia, e' un controllo spento.
        problemi.append(
            "docs/landing/: nessuna pagina tracciata dichiara una versione. O il "
            "numero e' sparito dalle landing (rimettilo: e' cio' che rende "
            "verificabile il resto), o non e' piu' scritto in una forma che "
            "_RE_VERSIONE_LANDING riconosce - in quel caso aggiorna la regex in "
            "scripts/check_docs.py, perche' cosi' il controllo non puo' fallire"
        )
    return problemi


def test_raccolti() -> int:
    """Quanti test esistono davvero, chiesto a pytest invece che contati a mano."""
    py = ROOT / "venv" / "Scripts" / "python.exe"
    eseguibile = str(py) if py.is_file() else sys.executable
    uscita = subprocess.run(
        [eseguibile, "-m", "pytest", "--collect-only", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    ).stdout.strip().splitlines()
    for riga in reversed(uscita):
        m = re.match(r"(\d+) tests? collected", riga.strip())
        if m:
            return int(m.group(1))
    raise RuntimeError("non riesco a contare i test: " + "\n".join(uscita[-3:]))


# Il rapporto per il board: sta sul disco dell'autore e **non e' tracciato**,
# perche' e' un documento interno e questo repository e' pubblico.
AUDIT = "audit_mr_rao_report.html"


def audit_invecchiato(reale: int) -> tuple[list[str], bool]:
    """Il rapporto per il board dice numeri di ieri?

    **Perche' e' un controllo diverso dagli altri.** Tutti i controlli di
    questo file guardano cio' che git traccia, ed e' una scelta: un glob sul
    disco pesca gli scarti di lavoro e il gate diventa rosso per file che
    chi clona non ha. Questo rapporto pero' non e' uno scarto — e' il
    documento che l'autore mostra a terzi — e non e' tracciato perche' e'
    interno e il repository e' pubblico.

    Il risultato e' che invecchia meglio di qualunque altra cosa: nessun
    banco lo apre, il gate non lo vede, e le sue cifre non vengono
    confrontate con niente. Misurato il 2026-08-14: dichiarava la 1.25.0 con
    il programma alla 1.26.0, 1 999 test invece di 2 133, e **«Plus 0.1.31 su
    Chrome e Edge» quando sugli store c'era la 0.1.25**. Quest'ultima non e'
    una cifra vecchia: e' un'affermazione falsa consegnata a qualcuno che non
    ha modo di verificarla.

    Restituisce anche se il controllo ha **davvero guardato**: sulla CI il
    file non c'e' e il salto va detto, non taciuto. Un controllo che quando
    non trova niente da controllare risponde «tutto bene» e' verde proprio
    dove servirebbe.
    """
    f = ROOT / AUDIT
    if not f.is_file():
        return [], False
    testo = _RE_CODICE_HTML.sub(" ", f.read_text(encoding="utf-8"))
    fonte = [(AUDIT, testo)]
    problemi = versioni_incoerenti(fonte, _RE_VERSIONE_LANDING)
    problemi += conteggi_desktop_incoerenti(reale, testo)
    problemi += link_amo_diverso(testo)
    return [
        p + ". E' il documento che mostri a terzi: una cifra vecchia li' "
        "dentro e' un'affermazione sbagliata, non un fastidio"
        for p in problemi
    ], True


def conteggi_desktop_incoerenti(reale: int, testo: str) -> list[str]:
    """Il conteggio dei test **desktop**, e solo quello.

    Il controllo generale non va bene qui, e lo ha detto al primo giro: il
    rapporto cita due suite -- «2 133 test desktop» e «1 190 test Plus» -- e
    `_RE_CONTEGGIO` prende qualunque numero seguito da «test», quindi
    bocciava il numero di Plus dicendo che avrebbe dovuto essere quello del
    desktop. Due numeri veri, un controllo che ne conosce uno solo.

    Il numero di Plus non e' verificabile da qui: nasce in un altro
    repository, che questo non ha. Resta scritto a mano, e resta un buco
    dichiarato invece di un controllo che finge.
    """
    reali = _RE_CONTEGGIO_DESKTOP.findall(_unisci_cifre(testo))
    if not reali:
        return [
            f"{AUDIT}: non dichiara nessun conteggio di test desktop. Se la "
            "frase e' cambiata aggiorna _RE_CONTEGGIO_DESKTOP, altrimenti "
            "questo controllo non puo' piu' fallire"
        ]
    return [
        f"{AUDIT}: dice {n} test desktop, ma sono {reale}"
        for n in reali
        if n != str(reale)
    ]


def link_amo_diverso(testo: str) -> list[str]:
    """Il link Firefox del rapporto dev'essere quello delle pagine pubblicate.

    La scheda store (`/addon/mr-rao-plus/`) e' il link da tenere allineato.
    Un vecchio zip `/downloads/file/…` e' lo stesso controllo: se compare
    in un posto e non nelle landing, e' un link morto o rimasto indietro.
    """
    quali = _RE_LINK_AMO.findall(testo)
    if not quali:
        return []
    attesi = set()
    for _, pagina in _fonti_landing():
        attesi.update(_RE_LINK_AMO.findall(pagina))
    if not attesi:
        return []
    diversi = sorted(set(quali) - attesi)
    return [
        f"{AUDIT}: il link Firefox punta a {d}, le landing dicono "
        f"{sorted(attesi)[0]}"
        for d in diversi
    ]


def main() -> int:
    reale = test_raccolti()
    guai_audit, audit_letto = audit_invecchiato(reale)
    problemi = (
        id_duplicati()
        + link_rotti()
        + versioni_incoerenti()
        + conteggi_incoerenti(reale)
        + segnaposto_non_documentati()
        + moduli_non_mappati()
        + opzioni_cli_non_documentate()
        + versione_senza_changelog()
        + landing_invecchiate(reale)
        + guai_audit
    )
    if problemi:
        print(f"DOCUMENTI DISALLINEATI ({len(problemi)}):", file=sys.stderr)
        for p in problemi:
            print(f"  {p}", file=sys.stderr)
        print(
            "\nSono affermazioni che chi legge il repository puo' verificare in "
            "trenta secondi. Se non tornano, non torna nemmeno il resto.",
            file=sys.stderr,
        )
        return 1
    print(
        f"  documenti allineati: {len(documenti())} file + {len(landing())} landing, "
        f"{reale} test, v{APP_VERSION}"
    )
    # Il salto si dice. Su una macchina che il rapporto non ce l'ha -- la CI,
    # o il clone di chiunque altro -- questo controllo non guarda niente, e
    # tacerlo lo farebbe sembrare passato.
    print(
        f"  {AUDIT}: allineato"
        if audit_letto
        else f"  {AUDIT}: non c'e' su questa macchina, controllo saltato"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
