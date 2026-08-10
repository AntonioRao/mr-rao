"""Il corpus di conformita' e' aggiornato, completo e capace di dire di no.

Il motore di redazione sta per essere riscritto in TypeScript per un'estensione
browser. `corpus/casi.jsonl` (ingressi curati a mano) e `corpus/atteso.json`
(uscite congelate, generate da `scripts/esporta_corpus_conformita.py`) sono il
contratto fra le due implementazioni: la seconda non deve somigliare alla
prima, deve riprodurre quelle stringhe carattere per carattere.

**Questo file e' la parte che rende il contratto vivo.** Un corpus e' un
documento come un altro: invecchia senza rompere niente, e un corpus
invecchiato e' peggio di nessun corpus — dice di si' a un'implementazione
fedele a un motore che non esiste piu'. Qui si impedisce nei tre modi in cui
puo' marcire:

1. **il motore e' cambiato e l'atteso no.** Si confronta l'impronta (versione
   piu' SHA-256 dei tre sorgenti) *e* si rifanno i conti a memoria. Le due
   cose insieme e non una sola: l'impronta si accorge anche dei cambiamenti
   che oggi non spostano nessuna uscita — un'espressione regolare piu' larga
   che nessun caso esercita — e i conti si accorgono di un'impronta rifatta a
   mano senza rigenerare. Quando questo test diventa rosso, la suite
   TypeScript deve diventarlo con lui: e' il punto in cui la divergenza si
   vede;

2. **un caso e' sparito.** Un ingresso tolto da `casi.jsonl` non rompe
   niente e non lascia traccia: e' copertura che se ne va in silenzio,
   che e' esattamente come nasce una fuga;

3. **il corpus non puo' piu' dire di no.** Se dentro ci fossero solo dati da
   togliere, nessuno si accorgerebbe di un motore che redige TROPPO — e un
   motore che redige troppo distrugge il documento senza che nessun conteggio
   se ne lamenti. Servono le tre popolazioni insieme: casi che sostituiscono,
   casi che non devono sostituire niente, casi che segnalano un sospetto.

Quando il motore cambia **di proposito**:

    venv\\Scripts\\python scripts\\esporta_corpus_conformita.py

e si guarda il diff di `corpus/atteso.json` prima di committarlo. Se dentro
c'e' qualcosa che non si era voluto cambiare, e' li' che lo si scopre.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Come gli altri test che riusano uno script del gate: si importa il modulo
# vero, non se ne riscrive il contenuto qui. Una seconda copia della logica di
# lettura sarebbe una seconda cosa che puo' restare indietro, e resterebbe
# indietro proprio nel file che esiste per accorgersi di chi resta indietro.
RADICE = Path(__file__).resolve().parent.parent
if str(RADICE / "scripts") not in sys.path:
    sys.path.insert(0, str(RADICE / "scripts"))

from esporta_corpus_conformita import (  # noqa: E402
    ATTESO,
    CASI,
    calcola,
    impronta,
    leggi_casi,
)

# La quota minima di casi che NON devono produrre nessuna sostituzione. Non e'
# un numero tondo scelto per bellezza: la meta' del lavoro di questo motore e'
# lasciare stare, e i corpora su cui e' stato tarato — moduli in bianco,
# Gazzette, dichiarazioni fiscali — hanno verita' di riferimento zero. Un
# corpus in cui i negativi scendono sotto un terzo ha smesso di misurare
# quella meta'.
QUOTA_NEGATIVI = 1 / 3


@pytest.fixture(scope="module")
def casi() -> list[dict]:
    return leggi_casi()


@pytest.fixture(scope="module")
def atteso() -> dict:
    return json.loads(ATTESO.read_text(encoding="utf-8"))


def test_i_file_del_corpus_esistono():
    """Senza ingressi o senza atteso tutto il resto passerebbe a vuoto."""
    assert CASI.is_file(), f"manca {CASI}"
    assert ATTESO.is_file(), (
        f"manca {ATTESO}: rigenera con scripts/esporta_corpus_conformita.py"
    )


def test_impronta_del_motore_allineata(atteso):
    """L'atteso e' stato generato da QUESTO motore, non da quello di ieri."""
    attuale = impronta()
    registrata = atteso["motore"]
    if attuale == registrata:
        return

    diverse = [
        f"  {nome}: atteso {registrata['sorgenti'].get(nome, '(assente)')[:12]}, "
        f"ora {sha[:12]}"
        for nome, sha in attuale["sorgenti"].items()
        if registrata["sorgenti"].get(nome) != sha
    ]
    if registrata.get("app") != attuale["app"]:
        diverse.append(
            f"  versione: atteso {registrata.get('app')}, ora {attuale['app']}"
        )
    pytest.fail(
        "corpus/atteso.json e' stato generato da un motore diverso da quello "
        "attuale:\n" + "\n".join(diverse) + "\n\n"
        "Se il motore e' cambiato di proposito, rigenera con\n"
        "  venv\\Scripts\\python scripts\\esporta_corpus_conformita.py\n"
        "e GUARDA IL DIFF: e' l'unico momento in cui si vede se e' cambiato "
        "anche qualcosa che non si voleva cambiare. Poi allinea la suite "
        "dell'implementazione TypeScript, che da adesso sta misurando un "
        "motore che non esiste piu'."
    )


def test_nessun_caso_e_sparito(casi, atteso):
    """Un caso che sparisce e' copertura che sparisce, e non fa rumore."""
    negli_ingressi = {c["id"] for c in casi}
    nell_atteso = set(atteso["casi"])
    mancanti = sorted(negli_ingressi - nell_atteso)
    avanzati = sorted(nell_atteso - negli_ingressi)
    assert not mancanti, (
        f"casi presenti in {CASI.name} ma non nell'atteso: {mancanti}. "
        "Rigenera l'atteso."
    )
    assert not avanzati, (
        f"casi presenti nell'atteso ma non piu' in {CASI.name}: {avanzati}. "
        "Un ingresso tolto dal corpus e' una domanda che non si fa piu': se e' "
        "voluto, dillo nel messaggio di commit; se non lo e', rimettilo."
    )


def test_ogni_caso_produce_ancora_il_risultato_congelato(casi, atteso):
    """Il confronto che conta: uscita e rapporto, caso per caso.

    Si ricalcola tutto invece di fidarsi dell'impronta, perche' un'impronta
    aggiornata a mano — o un file rigenerato per sbaglio senza guardare il
    diff — passerebbe il controllo di sopra senza che nessuna uscita sia
    stata verificata.
    """
    ottenuto = calcola(casi)["casi"]
    differenze: list[str] = []
    for id_caso, previsto in atteso["casi"].items():
        adesso = ottenuto.get(id_caso)
        if adesso is None:
            continue  # gia' detto, e meglio, da test_nessun_caso_e_sparito
        if adesso["uscita"] != previsto["uscita"]:
            differenze.append(
                f"{id_caso}: uscita\n"
                f"    atteso  {previsto['uscita']!r}\n"
                f"    ottenuto {adesso['uscita']!r}"
            )
        if adesso["report"] != previsto["report"]:
            differenze.append(
                f"{id_caso}: rapporto\n"
                f"    atteso   {previsto['report']}\n"
                f"    ottenuto {adesso['report']}"
            )
    assert not differenze, (
        f"il motore non produce piu' l'atteso in {len(differenze)} punti:\n"
        + "\n".join(differenze[:20])
        + ("\n  ...(altri)" if len(differenze) > 20 else "")
        + "\n\nSe il cambiamento e' voluto, rigenera con "
        "scripts/esporta_corpus_conformita.py e guarda il diff."
    )


def test_il_corpus_sa_dire_di_no(atteso):
    """Le tre popolazioni ci sono tutte e tre, ed e' l'invariante piu' fragile.

    Sostituisce / non sostituisce niente / segnala un sospetto. Un corpus a
    cui manchi la seconda non puo' accorgersi di un motore che redige troppo;
    uno a cui manchi la terza non prova che i sospetti esistano ancora, e i
    sospetti sono cio' che distingue «non c'era niente» da «non ho visto
    niente».
    """
    casi = atteso["casi"].values()
    con_sostituzioni = [c for c in casi if c["report"]["total"] > 0]
    puliti = [c for c in casi if c["report"]["total"] == 0]
    con_sospetti = [c for c in casi if c["report"]["suspects_total"] > 0]

    assert con_sostituzioni, (
        "nessun caso del corpus produce una sostituzione: cosi' non si "
        "verifica che il motore tolga qualcosa"
    )
    assert puliti, (
        "nessun caso del corpus esce senza sostituzioni. Un corpus fatto solo "
        "di dati da togliere NON PUO' accorgersi di un motore che redige "
        "troppo: aggiungi casi negativi (numeri di protocollo, date, checksum "
        "che non tornano, etichette di campo maiuscole)"
    )
    assert con_sospetti, (
        "nessun caso del corpus produce un sospetto: la meta' onesta del "
        "rapporto — cio' che assomiglia a un dato ed e' rimasto nel testo — "
        "non e' piu' sotto osservazione"
    )

    quota = len(puliti) / len(atteso["casi"])
    assert quota >= QUOTA_NEGATIVI, (
        f"solo il {quota:.0%} dei casi non produce sostituzioni, sotto il "
        f"{QUOTA_NEGATIVI:.0%} minimo. Meta' del mestiere di questo motore e' "
        "lasciare stare, e un corpus sbilanciato sui positivi la smette di "
        "misurare"
    )


def test_ogni_caso_dice_perche_esiste(casi):
    """Un caso senza nota e' un caso che nessuno sapra' piu' interpretare.

    Quando fra un anno l'implementazione TypeScript fallira' su `iban-06`,
    la domanda non sara' «cosa deve uscire» — quello sta nell'atteso — ma
    «perche' deve uscire quello». Senza la nota si finisce ad allineare il
    codice al numero, che e' il modo in cui un banco smette di proteggere.
    """
    muti = [c["id"] for c in casi if not c["nota"].strip()]
    assert not muti, f"casi senza nota: {muti}"
    gruppi = {c["gruppo"] for c in casi}
    assert len(gruppi) >= 20, (
        f"solo {len(gruppi)} gruppi nel corpus: la copertura per riconoscitore "
        "si e' ristretta"
    )
