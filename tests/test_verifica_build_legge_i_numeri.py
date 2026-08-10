"""Il collaudo del pacchetto deve riconoscere l'uscita che il motore produce.

Perche' esiste
--------------

`scripts/verify_build.py` avvia l'eseguibile appena costruito, gli fa
convertire un `.docx`, un `.xlsx` e un `.pptx`, e pretende di ritrovare i
segnaposto nel testo che torna. E' l'unico controllo che guarda il
prodotto **impacchettato**: gira solo dentro `build_portable.bat`, non
dentro pytest.

Quella separazione ha un prezzo, e l'abbiamo pagato. Quando i segnaposto
hanno cominciato a uscire numerati, il collaudo cercava ancora `{{EMAIL}}`
alla lettera, trovava `{{EMAIL_1}}` e respingeva il build: 1755 test verdi
e il pacchetto dichiarato rotto, mentre il pacchetto era a posto e il
metro era vecchio. Nessun test poteva accorgersene, perche' nessun test
sapeva cosa il collaudo si aspetta.

Questo file e' quel legame mancante. Non copia la forma attesa: prende la
frase vera di `verify_build.py`, la fa passare dal motore vero, e chiede
al controllo vero se la riconosce. Il giorno che la forma dell'uscita
cambia di nuovo — numeri, prefissi, qualunque cosa — a dirlo e' pytest in
venti secondi, non il build dopo dieci minuti.

Come potrebbe fallire
---------------------

Se il motore smettesse di redigere quella frase, o la redigesse in una
forma che il collaudo non riconosce, i test qui sotto diventano rossi. E
c'e' il verso opposto: il controllo deve continuare a dire **no** quando
il dato e' rimasto in chiaro, altrimenti avremmo tolto un difetto
mettendo al suo posto una guardia cieca.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from mr_rao.privacy import SENTINELLA, PrivacyOptions, apply_privacy_filter

RADICE = Path(__file__).resolve().parents[1]


def _collaudo():
    """Carica `scripts/verify_build.py`, che non e' un modulo importabile."""
    percorso = RADICE / "scripts" / "verify_build.py"
    spec = importlib.util.spec_from_file_location("verify_build", percorso)
    assert spec and spec.loader, percorso
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


# La frase e le etichette sono quelle di `verify_build.py`. Se la' cambiano
# e qui no, il test sotto se ne accorge: non le confronto a memoria, le
# rileggo dal file.
FRASE = "Contatta mario.rossi@example.it al 335 123 4567 in via Roma 12"
ATTESE = ("EMAIL", "PHONE", "ADDRESS")


def test_la_frase_del_collaudo_e_ancora_questa() -> None:
    """La guardia della guardia.

    Tutto il resto del file poggia sull'idea che il collaudo provi *questa*
    frase. Se qualcuno la cambia la' dentro, i test qui sotto continuerebbero
    a passare misurando una frase che il build non usa piu'.
    """
    sorgente = (RADICE / "scripts" / "verify_build.py").read_text(encoding="utf-8")
    assert FRASE in sorgente


@pytest.mark.parametrize("etichetta", ATTESE)
def test_il_collaudo_riconosce_l_uscita_vera_del_motore(etichetta: str) -> None:
    collaudo = _collaudo()
    redatto, _ = apply_privacy_filter(FRASE, PrivacyOptions())
    assert collaudo.segnaposto_presente(redatto, etichetta), redatto


def test_il_collaudo_accetta_tutte_e_due_le_forme() -> None:
    collaudo = _collaudo()
    assert collaudo.segnaposto_presente("scrivi a {{EMAIL}} oggi", "EMAIL")
    assert collaudo.segnaposto_presente("scrivi a {{EMAIL_1}} oggi", "EMAIL")
    assert collaudo.segnaposto_presente("{{EMAIL_12}} e {{EMAIL_3}}", "EMAIL")


def test_il_collaudo_dice_no_quando_il_dato_e_in_chiaro() -> None:
    """Il verso che conta: senza questo, sarebbe una guardia cieca."""
    collaudo = _collaudo()
    assert not collaudo.segnaposto_presente("scrivi a mario@example.it oggi", "EMAIL")
    assert not collaudo.segnaposto_presente("{{PHONE_1}} soltanto", "EMAIL")
    # Il prefisso da solo non basta: `{{EMAILS}}` non e' `{{EMAIL}}`.
    assert not collaudo.segnaposto_presente("{{EMAILS}}", "EMAIL")


def test_il_marcatore_interno_non_passa_per_un_segnaposto_buono() -> None:
    """`SENTINELLA` non deve mai arrivare a chi legge.

    Se un giorno sfuggisse dall'ultimo passaggio, il testo conterrebbe
    qualcosa che *somiglia* a un segnaposto numerato. Il collaudo deve
    chiamarlo mancante, non farselo bastare.
    """
    collaudo = _collaudo()
    trapelato = f"scrivi a {{{{EMAIL{SENTINELLA}1}}}} oggi"
    assert not collaudo.segnaposto_presente(trapelato, "EMAIL")
