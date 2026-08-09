"""Due profili non possono fare la stessa identica cosa.

Perche' questo file esiste
--------------------------

Il profilo «Fatture / contabili» si distingueva da «Predefinito» per una
ragione sola: spegneva l'euristica del cognome (`name_guess`), che su una
fattura piena di ragioni sociali fa piu' danni che bene.

Nella **1.7.2** `name_guess` e' stato spento **di default**. Da quel giorno
l'unica differenza del profilo e' diventata un'istruzione che non
istruiva piu' niente, e «Fatture» ha cominciato a produrre esattamente le
stesse opzioni di «Predefinito». Un doppione con un'etichetta diversa.

**Nessuno se n'e' accorto per quattro release**, perche' niente confrontava
i profili fra loro: i test guardavano che ogni profilo fosse coerente con
se' stesso e con l'interfaccia, mai che fosse diverso dagli altri.

Il danno non e' tecnico, e' di fiducia: chi sceglie «Fatture» crede di
aver detto qualcosa al programma, e non ha detto niente. Una tendina che
offre due strade che portano allo stesso posto insegna che le tendine non
contano.

Cosa controlla
--------------

Che due profili qualsiasi non risolvano nelle **stesse identiche opzioni**.
Il confronto e' sulle opzioni finali (`options_from_profile`), non sui
dizionari di partenza: e' li' che il difetto si nascondeva, perche' i due
dizionari erano diversi — «Fatture» dichiarava due chiavi in piu' — mentre
il risultato era lo stesso. Confrontare la forma invece della sostanza
avrebbe lasciato passare tutto.
"""
from __future__ import annotations

import dataclasses
import itertools
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
if str(RADICE) not in sys.path:
    sys.path.insert(0, str(RADICE))

from mr_rao.profiles import PROFILES, options_from_profile  # noqa: E402


def test_nessun_profilo_e_il_doppione_di_un_altro():
    """Due etichette diverse devono fare due cose diverse."""
    risolti = {nome: options_from_profile(nome) for nome in PROFILES}
    doppioni = [
        (a, b)
        for a, b in itertools.combinations(sorted(risolti), 2)
        if risolti[a] == risolti[b]
    ]
    assert not doppioni, (
        "questi profili producono opzioni identiche, quindi uno dei due mente "
        "a chi lo sceglie: "
        + ", ".join(f"{a} == {b}" for a, b in doppioni)
    )


def test_il_confronto_guarda_le_opzioni_risolte_non_i_dizionari():
    """La prova che il controllo sopra puo' davvero fallire.

    Si ricostruisce il difetto storico: un profilo che dichiara una chiave
    in piu' il cui valore coincide gia' col difetto del motore. I dizionari
    sono diversi, le opzioni no — ed e' esattamente il caso che per quattro
    release nessuno ha visto.
    """
    base = dict(PROFILES["default"])
    finto = dict(base)
    # `name_guess` e' gia' spento di default: dirlo di nuovo non cambia niente.
    finto["privacy_name_guess"] = False
    finto["label"] = "Un doppione"

    assert finto != base, "i dizionari devono essere diversi, o non provo niente"

    PROFILES["_doppione_di_prova"] = finto
    try:
        risolti = {nome: options_from_profile(nome) for nome in PROFILES}
        assert risolti["_doppione_di_prova"] == risolti["default"], (
            "il profilo di prova doveva risultare identico al predefinito"
        )
        doppioni = [
            (a, b)
            for a, b in itertools.combinations(sorted(risolti), 2)
            if risolti[a] == risolti[b]
        ]
        assert doppioni, "il controllo non ha visto un doppione costruito apposta"
    finally:
        del PROFILES["_doppione_di_prova"]


def test_ogni_profilo_ha_etichetta_e_descrizione():
    """Una tendina con una voce senza nome non e' una scelta."""
    for nome, p in PROFILES.items():
        assert p.get("label"), f"{nome}: manca l'etichetta"
        assert p.get("description"), f"{nome}: manca la descrizione"


def test_le_descrizioni_non_si_ripetono():
    """Due descrizioni uguali sono lo stesso inganno delle opzioni uguali,
    visto dall'altra parte: promettono la stessa cosa."""
    viste: dict[str, str] = {}
    for nome, p in PROFILES.items():
        d = p["description"].strip().lower()
        assert d not in viste, (
            f"«{nome}» e «{viste[d]}» hanno la stessa descrizione: {p['description']!r}"
        )
        viste[d] = nome


def test_il_predefinito_esiste():
    """Il resto del programma ci ricade quando la scelta non e' valida."""
    assert "default" in PROFILES
    assert options_from_profile("default") is not None


def test_dataclass_confrontabile():
    """Il controllo poggia sull'uguaglianza di `ConvertOptions`: se un giorno
    smettesse di essere una dataclass confrontabile, tutti i confronti qui
    sopra direbbero «diversi» per sempre, in silenzio."""
    o = options_from_profile("default")
    assert dataclasses.is_dataclass(o)
    assert options_from_profile("default") == o
