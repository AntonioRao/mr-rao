"""Come i dati arrivano davvero da un file, non come li scriviamo noi.

Perche' questo file esiste
--------------------------

Il banco a due corpora prova frasi scritte bene. Ma un IBAN che esce da un
PDF non e' scritto bene: e' a gruppi di quattro, o spezzato da un a capo. Un
codice fiscale puo' arrivare in minuscolo. Un indirizzo di posta puo' essere
tagliato a meta' dalla giustificazione del testo.

Misurato per la prima volta il 2026-08-09: sulle **forme regolari** il
motore prende il 100% (520 casi su 520, dentro prosa giuridica vera). Sulle
**forme difficili** prendeva il 66,7%, con il 13,3% **perso in silenzio** —
ne' sostituito ne' segnalato, che e' il modo peggiore di sbagliare.

Da quella misura e' uscito un difetto vero, l'indirizzo spezzato dall'a
capo, corretto in `tests/test_email_spezzata.py`. Le forme perse in silenzio
sono scese al 6,7%, e cio' che resta e' il limite dichiarato sui nomi fuori
elenco.

Cosa sorveglia questo file
--------------------------

Che quel quadro non peggiori. Le tre categorie sono tenute separate apposta:
**redatto** e' meglio di **segnalato**, ma segnalato e' enormemente meglio
di **perso in silenzio**, e una percentuale unica confonderebbe le tre cose.

Il banco completo, con gli altri due assi, e' `scripts/bench_testo.py`.
Quelli hanno bisogno di un corpus esterno che non sta nel repository; questi
casi no, perche' cio' che misurano e' la forma del frammento.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]
for percorso in (RADICE, RADICE / "scripts"):
    if str(percorso) not in sys.path:
        sys.path.insert(0, str(percorso))

from bench_testo import (  # noqa: E402
    DIFFICILI,
    SUBSTRATO,
    _inserisci,
    conta,
    esito,
)
from mr_rao.privacy import apply_privacy_filter, no_redaction  # noqa: E402

# Cosa ci si aspetta oggi, caso per caso. Scritto per esteso e non come una
# percentuale: una media unica lascerebbe passare uno scambio fra due
# categorie — un caso che smette di essere segnalato e comincia a sparire in
# silenzio non muoverebbe il totale di un millimetro.
ATTESO = {
    "iban a gruppi di quattro": "redatto",
    "iban spezzato da un a capo": "sospetto",
    "carta a gruppi di quattro": "redatto",
    "carta separata da trattini": "redatto",
    "codice fiscale in minuscolo": "redatto",
    "telefono con punti": "redatto",
    "telefono senza parola davanti": "redatto",
    "email offuscata": "redatto",
    "email spezzata da un a capo": "redatto",
    # Il limite dichiarato: nessun elenco lo contiene, nessuna prova di
    # contesto lo accompagna. Vedi docs/PRIVACY.md, «La regola ritirata».
    "nome straniero, nudo": "perso",
    "nome straniero, titolo davanti": "redatto",
    "nome straniero, firma": "redatto",
    # Era «sospetto» fino alla 1.16.0: nessuna regola vedeva un cognome da
    # solo, perche' il riconoscitore a coppie pretende due parole adiacenti.
    # Dalla 1.17.0 lo prende il **ruolo davanti ai due punti**, che e' la
    # firma degli atti pubblici italiani.
    "solo cognome dopo i due punti": "redatto",
    "cognome che e' parola comune": "sospetto",
    "indirizzo senza civico": "redatto",
}


@pytest.fixture(scope="module")
def esiti():
    return conta(DIFFICILI, [SUBSTRATO])


def test_ogni_caso_difficile_si_comporta_come_previsto(esiti):
    """Un cambiamento qui non e' per forza un peggioramento — ma va guardato.

    Se un caso passa da «perso» a «sospetto» o a «redatto» e' un
    miglioramento: si aggiorna ATTESO e si aggiorna il numero pubblicato in
    `docs/PRIVACY.md`, insieme.
    """
    diverso = {}
    for etichetta, c in esiti.items():
        ottenuto = next(k for k, v in c.items() if v)
        if ottenuto != ATTESO[etichetta]:
            diverso[etichetta] = (ATTESO[etichetta], ottenuto)
    assert not diverso, (
        "questi casi si comportano diversamente da come e' documentato:\n  "
        + "\n  ".join(f"{e}: atteso «{a}», ottenuto «{o}»"
                      for e, (a, o) in diverso.items())
        + "\n\nSe e' un miglioramento, aggiorna ATTESO qui e i numeri in "
          "docs/PRIVACY.md nella stessa passata."
    )


def test_le_perdite_in_silenzio_non_aumentano(esiti):
    """Il numero che conta piu' di tutti.

    «Segnalato» lascia a chi legge la possibilita' di intervenire.
    «Perso in silenzio» no: il documento sembra pulito e non lo e'.
    """
    persi = [e for e, c in esiti.items() if c["perso"]]
    assert len(persi) <= 1, (
        f"le forme perse in silenzio sono {len(persi)}: {persi}. "
        f"Era una sola (il nome fuori elenco) alla 1.14.0"
    )


def test_il_banco_puo_dire_di_no():
    """Con i riconoscitori spenti nessun caso deve risultare «redatto».

    Senza questo controllo un caso il cui valore atteso non compare nel
    frammento risulterebbe «redatto» per sempre, senza che il motore
    c'entri niente. E' successo davvero, sull'IBAN a gruppi di quattro:
    cercavo la forma senza spazi dentro un testo che li aveva.
    """
    spento = no_redaction()
    finti = []
    for etichetta, valore, frammento in DIFFICILI:
        fuori, _ = apply_privacy_filter(_inserisci(SUBSTRATO, frammento), spento)
        if valore not in fuori:
            finti.append(etichetta)
    assert not finti, (
        "questi casi risultano «redatti» anche col filtro spento, quindi non "
        f"misurano niente: {finti}"
    )


def test_esito_guarda_il_testo_e_non_il_conteggio():
    """`esito()` deve rispondere alla domanda giusta.

    Un paragrafo puo' far scattare qualcos'altro: contare le redazioni
    direbbe «preso» anche quando il valore cercato e' ancora lì.
    """
    # Il valore c'e' ancora, ma il testo contiene un'altra email che viene
    # tolta: il conteggio direbbe 1, la risposta giusta e' «perso».
    testo = "scrivi a tizio@esempio.it e cita Kwabena Osei nella relazione"
    assert esito(testo, "Kwabena Osei") == "perso"
