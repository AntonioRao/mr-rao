"""Il sito pubblicato dice ancora la stessa versione del repository?

Nasce da una cosa successa il **2026-08-09**. La landing inglese era
corretta, committata e pushata; online c'era ancora la vecchia. Se n'e'
accorto l'utente guardando il sito, e non c'e' niente che glielo avrebbe
detto: il progetto Cloudflare Pages e' a **caricamento diretto**, non
collegato al repository, quindi `git push` non pubblica niente. Finche' non
girano `docs/landing/publish/_rebuild.py` e `wrangler pages deploy`, il
pubblicato resta indietro rispetto a git **in silenzio**.

E' lo stesso modo di rompersi che `scripts/check_docs.py` esiste per
impedire, spostato di un passo piu' in la': quel gate garantisce che il
repository sia coerente con se stesso — `landing_invecchiate()` fallisce se
una pagina locale dichiara un numero che non e' `APP_VERSION` — e nessuno
garantisce che il **pubblicato** sia il repository. Il gate guarda i file;
qui si guarda cosa risponde il server.

**Perche' NON sta nel gate bloccante** (`scripts/quality_gate.bat`) e
nemmeno in `ci.yml`. Fra il momento in cui si pusha il bump di versione e
il momento in cui si pubblica il sito passa del tempo, e in quella finestra
il sito **e' legittimamente indietro**: un controllo rosso per mezz'ora
dopo ogni release non segnala un difetto, addestra a ignorare il rosso —
che e' il modo piu' rapido per rendere inutile anche tutto il resto del
gate. Il posto giusto per una domanda la cui risposta giusta cambia col
tempo e' un controllo **periodico**, non un cancello: gira una volta al
giorno (`.github/workflows/sito-pubblicato.yml`) e a mano quando serve.
Sopravvivere a un giorno di ritardo e' accettabile; il difetto da cui
veniamo era durato di piu' e non lo diceva nessuno.

**Tre esiti, e il terzo non e' il primo.** Il caso «non ho potuto
guardare» (rete assente, DNS che non risolve, 502) non deve mai essere
confuso con «ho guardato ed e' allineato»: un controllo di rete che in caso
di errore tace e' verde proprio quando serve. Qui sono codici di uscita
distinti:

    0  allineato       — la pagina online dichiara APP_VERSION
    1  disallineato    — dichiara un altro numero (indietro, o avanti)
    2  irraggiungibile — non si e' potuto sapere, e viene detto
    3  cieco           — il controllo non ha piu' niente da guardare

Il 3 e' quello che merita piu' attenzione ed e' il piu' facile da non
scrivere: se le pagine pubblicate spariscono dall'elenco, o se online non
c'e' piu' un numero in una forma riconoscibile, tutti i confronti passano
senza confrontare niente. Un controllo che non puo' fallire non e' una
verifica, e questo e' il modo in cui morirebbe senza rumore.

Gli indirizzi non sono scritti qui: si leggono dal `<link rel="canonical">`
delle pagine pubblicate tracciate da git. Una seconda copia dell'indirizzo
e' una seconda cosa che puo' restare indietro, e il giorno che il dominio
cambia questo controllo continuerebbe a interrogare — verde — un sito che
non e' piu' il nostro.

**Un limite misurato, subito dopo il primo deploy vero (2026-08-10).**
Lanciato una quindicina di secondi dopo `wrangler pages deploy`, ha detto
allineata la pagina italiana e **indietro l'inglese**. Non era vero: il file
appena pubblicato dichiarava gia' il numero nuovo, e trenta secondi dopo la
stessa esecuzione diceva allineate tutte e due. Non e' cache HTTP — le
risposte arrivano con `cf-cache-status: DYNAMIC` e `must-revalidate` — e'
la propagazione del deploy fra i nodi di Cloudflare, che per qualche decina
di secondi puo' servire ancora la versione di prima.

Quindi: **una singola esecuzione subito dopo la pubblicazione non e' un
verdetto**. Il giro schedulato delle 06:00 e' lontano da qualunque deploy e
non incontra questa finestra; chi lo lancia a mano dopo aver pubblicato, se
legge «indietro», lo rilanci prima di crederci. Non e' stato aggiunto un
`Cache-Control: no-cache` alla richiesta perche' non c'entra: non e' un
intermediario che conserva la risposta, e un'intestazione che non risolve
il problema che dice di risolvere e' peggio di niente — la prossima persona
la leggerebbe come una garanzia.

Uso:  python scripts/check_sito_pubblicato.py
      python scripts/check_sito_pubblicato.py --tollera-rete-assente
      python scripts/check_sito_pubblicato.py --url https://esempio/  (una sola)
"""
from __future__ import annotations

import argparse
import re
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

RADICE = Path(__file__).resolve().parents[1]
if str(RADICE) not in sys.path:
    sys.path.insert(0, str(RADICE))
if str(RADICE / "scripts") not in sys.path:
    sys.path.insert(0, str(RADICE / "scripts"))

from config import APP_VERSION  # noqa: E402

# Importati, non ricopiati. Sono le due regole che dicono *come una landing
# scrive il proprio numero* e *cosa in una pagina non e' un'affermazione*:
# duplicarle qui vorrebbe dire due controlli che col tempo rispondono in modo
# diverso alla stessa domanda, cioe' un locale verde e un online rosso (o
# peggio il contrario) per una differenza di regex e non di contenuto.
from check_docs import _RE_CODICE_HTML, _RE_VERSIONE_LANDING  # noqa: E402

TIMEOUT = 15.0
TENTATIVI = 2
PAUSA = 3.0  # secondi fra un tentativo e il successivo

# Cloudflare risponde 403 a certi client automatici senza identita'. Non e'
# un aggiramento: e' dire chi sta chiamando, invece di presentarsi come
# `Python-urllib/3.x` che e' esattamente cio' che i filtri anti-bot cercano.
INTESTAZIONI = {
    "User-Agent": "mr-rao-check-sito-pubblicato/1.0 (+https://github.com/AntonioRao/mr-rao)",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

_RE_CANONICAL = re.compile(
    r"""<link[^>]*\brel=["']canonical["'][^>]*\bhref=["']([^"']+)["']""", re.I
)

ALLINEATO = "allineato"
DISALLINEATO = "disallineato"
IRRAGGIUNGIBILE = "irraggiungibile"
CIECO = "cieco"

USCITE = {ALLINEATO: 0, DISALLINEATO: 1, IRRAGGIUNGIBILE: 2, CIECO: 3}

# Con piu' pagine e piu' esiti si esce con il piu' grave, e «piu' grave» non
# e' il numero piu' alto: un controllo cieco viene prima di tutto perche'
# mette in dubbio anche i verdi che ha appena stampato.
GRAVITA = {CIECO: 3, DISALLINEATO: 2, IRRAGGIUNGIBILE: 1, ALLINEATO: 0}

RIMEDIO = (
    "rigenera con 'python docs/landing/publish/_rebuild.py' e pubblica la "
    "cartella docs/landing/publish con 'wrangler pages deploy' (il progetto "
    "Cloudflare Pages e' a caricamento diretto: il push su GitHub non "
    "pubblica niente)"
)


class Irraggiungibile(Exception):
    """Non si e' potuto guardare. Diverso da «ho guardato ed e' a posto»."""


@dataclass(frozen=True)
class Esito:
    url: str
    stato: str
    dettaglio: str

    def __str__(self) -> str:
        return f"[{self.stato}] {self.url}: {self.dettaglio}"


# --- da dove si prendono gli indirizzi --------------------------------------


def pagine_locali() -> list[Path]:
    """Le pagine pubblicate **tracciate**, come fa `check_docs.landing()`.

    Lo stesso motivo di la': in `docs/landing/` convivono le pagine vere e
    gli scarti di lavoro gitignorati. Un glob sul disco interrogherebbe
    indirizzi che non riguardano nessuno.
    """
    uscita = subprocess.run(
        ["git", "ls-files", "docs/landing/publish/*.html", "docs/landing/publish/*/*.html"],
        cwd=RADICE,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    # Il `*` di un pathspec git attraversa le barre, quindi quei due modelli
    # prendono anche cio' che sta piu' in fondo -- comprese le pagine della
    # privacy dell'estensione, entrate qui dentro il giorno in cui sono state
    # tracciate.
    #
    # Vanno escluse, e non per comodita': questo controllo confronta la
    # versione dichiarata dalla pagina con `APP_VERSION`, e quelle pagine una
    # versione non ce l'hanno ne' la devono avere -- parlano dell'estensione,
    # che ha un numero suo. Il risultato erano due righe «cieco» a ogni
    # esecuzione, cioe' un controllo che non puo' diventare verde: si impara a
    # saltarlo, e il giorno che diventa cieco per un motivo vero non lo legge
    # piu' nessuno.
    pagine = [RADICE / p for p in uscita if "/plus/" not in p]
    # L'esclusione non deve poter mangiare la landing: se un giorno il filtro
    # diventasse troppo largo, meglio fermarsi che controllare niente e
    # stampare tutto verde. Provato allargandolo a `/publish/`: si ferma.
    if len(pagine) < 2:
        raise SystemExit(
            f"pagine da controllare: {len(pagine)}. L'elenco si e' svuotato: "
            "il filtro o il pathspec non prendono piu' le pagine vere."
        )
    return pagine


def indirizzi_pubblicati(pagine: Iterable[Path] | None = None) -> list[str]:
    """Gli URL dichiarati come canonici dalle pagine pubblicate.

    Solo `https`. Un canonical con un altro schema qui non e' un dettaglio
    di stile: `urlopen` aprirebbe volentieri un `file://` letto da un file
    del repository, e il controllo direbbe «allineato» confrontando la
    pagina con se stessa.
    """
    trovati: list[str] = []
    for pagina in pagine_locali() if pagine is None else pagine:
        for m in _RE_CANONICAL.finditer(pagina.read_text(encoding="utf-8")):
            url = m.group(1).strip()
            if url.lower().startswith("https://") and url not in trovati:
                trovati.append(url)
    return trovati


# --- la lettura -------------------------------------------------------------


def scarica(url: str, timeout: float = TIMEOUT, tentativi: int = TENTATIVI) -> str:
    """Scarica la pagina, o solleva `Irraggiungibile` dicendo perche'.

    I tentativi non sono ottimismo: una singola richiesta che incappa in un
    reset di connessione trasformerebbe un controllo giornaliero in un
    generatore di falsi rossi, e un rosso che il giorno dopo si spegne da
    solo insegna ad aspettare invece di guardare.
    """
    quanti = max(1, tentativi)
    ultimo = ""
    for tentativo in range(1, quanti + 1):
        richiesta = urllib.request.Request(url, headers=INTESTAZIONI)  # noqa: S310
        try:
            with urllib.request.urlopen(  # noqa: S310
                richiesta, timeout=timeout, context=ssl.create_default_context()
            ) as risposta:
                grezzo = risposta.read()
            return grezzo.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            # Un 404 sulla pagina pubblicata non e' «rete assente»: e' il
            # sito che non ha piu' quella pagina. Resta comunque un «non ho
            # potuto leggere il numero», e come tale viene detto.
            ultimo = f"HTTP {e.code} {e.reason}"
        except Exception as e:  # URLError, timeout, DNS, TLS
            ultimo = f"{type(e).__name__}: {e}"
        if tentativo < quanti:
            # Ritentare nello stesso istante ripete quasi sempre lo stesso
            # errore: un secondo tentativo senza pausa e' una consolazione,
            # non un rimedio.
            time.sleep(PAUSA)
    raise Irraggiungibile(ultimo or "motivo sconosciuto")


def versioni_dichiarate(html: str) -> list[str]:
    """I numeri di versione che la pagina scaricata dichiara al lettore.

    `<script>` e `<style>` vengono tolti prima, con la stessa regola del
    gate: dentro ci sono numeri a palate e nessuna promessa a nessuno.
    """
    testo = _RE_CODICE_HTML.sub(" ", html)
    viste: list[str] = []
    for m in _RE_VERSIONE_LANDING.finditer(testo):
        if m.group(1) not in viste:
            viste.append(m.group(1))
    return viste


def _tupla(versione: str) -> tuple[int, ...]:
    return tuple(int(p) for p in versione.split("."))


# --- il confronto -----------------------------------------------------------


def confronta_pagina(
    url: str,
    attesa: str = APP_VERSION,
    lettore: Callable[[str], str] = scarica,
) -> Esito:
    """Un solo indirizzo. `lettore` e' iniettabile: e' cio' che rende questo
    controllo verificabile senza rete (vedi `tests/test_sito_pubblicato.py`).
    """
    try:
        html = lettore(url)
    except Irraggiungibile as e:
        return Esito(url, IRRAGGIUNGIBILE, f"non si e' potuto leggere ({e})")

    trovate = versioni_dichiarate(html)
    if not trovate:
        return Esito(
            url,
            CIECO,
            "la pagina scaricata non dichiara nessuna versione riconoscibile. "
            "O il numero e' sparito dal sito, o non e' piu' scritto in una "
            "forma che _RE_VERSIONE_LANDING riconosce: in quel caso questo "
            "controllo non puo' piu' fallire, ed e' peggio di un rosso",
        )

    sbagliate = [v for v in trovate if v != attesa]
    if not sbagliate:
        return Esito(url, ALLINEATO, f"dichiara la {attesa}, come APP_VERSION")

    # `indietro` o `avanti` non e' un dettaglio di cortesia: sono due
    # situazioni diverse. Indietro vuol dire deploy dimenticato; avanti vuol
    # dire copia locale vecchia, oppure qualcosa pubblicato che in git non
    # e' mai entrato — e il secondo caso, chiamato «a posto», sparirebbe.
    pezzi = [
        f"{v} ({'indietro' if _tupla(v) < _tupla(attesa) else 'avanti'})"
        for v in sbagliate
    ]
    return Esito(
        url,
        DISALLINEATO,
        f"online c'e' la {', '.join(pezzi)}, APP_VERSION e' {attesa}. Il sito "
        f"pubblicato non e' il repository: {RIMEDIO}",
    )


def controlla(
    url_da_guardare: list[str] | None = None,
    attesa: str = APP_VERSION,
    lettore: Callable[[str], str] = scarica,
) -> list[Esito]:
    """Tutti gli indirizzi. Zero indirizzi e' un esito, non un successo."""
    indirizzi = indirizzi_pubblicati() if url_da_guardare is None else url_da_guardare
    if not indirizzi:
        return [
            Esito(
                "docs/landing/publish/",
                CIECO,
                "nessuna pagina pubblicata tracciata dichiara un <link "
                "rel=canonical> https. Senza indirizzo non c'e' niente da "
                "interrogare, e questo controllo direbbe verde per sempre: se "
                "le pagine sono state spostate o il dominio e' cambiato, "
                "aggiorna pagine_locali() in scripts/check_sito_pubblicato.py",
            )
        ]
    return [confronta_pagina(u, attesa, lettore) for u in indirizzi]


def peggiore(esiti: list[Esito]) -> str:
    return max((e.stato for e in esiti), key=lambda s: GRAVITA[s], default=CIECO)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Confronta la versione dichiarata dal sito pubblicato con "
            "APP_VERSION. Non pubblica niente e non chiede nessuna credenziale."
        )
    )
    parser.add_argument(
        "--url",
        action="append",
        metavar="INDIRIZZO",
        help="indirizzo da interrogare invece di quelli canonici (ripetibile)",
    )
    parser.add_argument("--timeout", type=float, default=TIMEOUT)
    parser.add_argument("--tentativi", type=int, default=TENTATIVI)
    parser.add_argument(
        "--tollera-rete-assente",
        action="store_true",
        help=(
            "esce con 0 se il sito non si e' potuto raggiungere. Serve a chi "
            "lancia il controllo offline: dire a una persona senza rete che il "
            "suo sito e' rotto e' un falso rosso. NON va usato nel controllo "
            "programmato, dove «non risponde» e' una notizia vera"
        ),
    )
    args = parser.parse_args(argv)

    def lettore(url: str) -> str:
        return scarica(url, timeout=args.timeout, tentativi=args.tentativi)

    esiti = controlla(args.url, APP_VERSION, lettore)
    for e in esiti:
        print(f"  {e}", file=sys.stderr if e.stato != ALLINEATO else sys.stdout)

    stato = peggiore(esiti)
    if stato == ALLINEATO:
        print(f"  sito pubblicato allineato: v{APP_VERSION} su {len(esiti)} pagine")
        return 0
    if stato == IRRAGGIUNGIBILE and args.tollera_rete_assente:
        print("  esito non determinato (rete assente tollerata): NON e' un via libera")
        return 0
    return USCITE[stato]


if __name__ == "__main__":
    raise SystemExit(main())
