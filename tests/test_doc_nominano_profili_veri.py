"""Un documento pubblico non puo' nominare un profilo che non esiste.

Perche' questo file esiste
--------------------------

Nella 1.12.0 il profilo «Fatture / contabili» e' stato rimosso, perche' era
un doppione esatto del predefinito (vedi `test_profili_distinti.py`). La
rimozione ha toccato il codice, l'interfaccia e i test.

**Quattro documenti pubblici hanno continuato a raccontarlo per intero**:
`README.md` e `README.it.md` gli dedicavano un caso d'uso («Il profilo
Fatture ricostruisce le tabelle e nasconde codice fiscale, P.IVA e IBAN»),
`PRIVACY.md` lo citava come il posto dove l'euristica del cognome e' spenta,
`PRIVACY_FAQ.md` lo elencava fra i modi di spegnerla.

Il gate dei documenti non poteva accorgersene: confronta **numeri** —
versione dichiarata, conteggio dei test — non se una frase descrive ancora
qualcosa che esiste. Un lettore che avesse cercato quel profilo
nell'interfaccia non l'avrebbe trovato, e avrebbe concluso la cosa giusta
per il motivo sbagliato: che la documentazione non e' affidabile.

Cosa controlla
--------------

Ogni nome di profilo **citato fra virgolette o in grassetto** dentro un
documento tracciato deve corrispondere a un profilo che esiste davvero, con
la sua etichetta italiana o inglese.

Il controllo guarda i file tracciati da git, non un glob: le bozze delle
landing sono gitignorate e non fanno parte di cio' che pubblichiamo.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]
if str(RADICE) not in sys.path:
    sys.path.insert(0, str(RADICE))

from mr_rao.i18n import TESTI  # noqa: E402
from mr_rao.profiles import PROFILES  # noqa: E402

# «profilo "X"», «profilo «X»», «profilo **X**» — e il rovescio inglese,
# «the "X" profile». Il nome catturato e' corto per costruzione: un limite
# di lunghezza evita che una virgoletta di apertura si mangi mezzo paragrafo
# quando la chiusura manca.
_RE_IT = re.compile(r"profil[oi]\s+[«\"'*]{1,2}([^»\"'*\n]{2,30})[»\"'*]{1,2}", re.I)
_RE_EN = re.compile(r"[«\"'*]{1,2}([^»\"'*\n]{2,30})[»\"'*]{1,2}\s+profile", re.I)
# Terza forma, e non e' un di piu': la prima versione di questo file aveva
# solo le due qui sopra, e sui documenti da correggere ne prendeva TRE SU
# QUATTRO. `PRIVACY_FAQ.md` scriveva «profilo Fatture» senza virgolette e
# passava liscio. Un controllo che prende quasi tutti i casi noti e' peggio
# di uno che non c'e', perche' insegna a fidarsi.
#
# Niente `re.I` qui: la maiuscola e' il segnale che distingue un nome
# proprio di profilo da un uso comune della parola («il profilo di rischio»).
_RE_IT_NUDO = re.compile(r"profil[oi]\s+([A-Z][A-Za-zÀ-ÿ']*(?:\s+[a-zA-ZÀ-ÿ']+){0,2})")


def _etichette_valide() -> set[str]:
    """Ogni nome con cui un profilo puo' legittimamente essere chiamato."""
    valide: set[str] = set()
    for chiave, p in PROFILES.items():
        valide.add(chiave.lower())
        valide.add(str(p["label"]).lower())
    # Le etichette inglesi vivono in i18n, non nei profili.
    for chiave, voci in TESTI.items():
        if chiave.startswith("profilo_") and isinstance(voci, dict):
            for testo in voci.values():
                if isinstance(testo, str):
                    valide.add(testo.lower())
    # Sinonimi che nei documenti indicano il predefinito senza nominarlo.
    valide.update({"predefinito", "default", "di default"})
    return valide


def _documenti_tracciati() -> list[tuple[str, str]]:
    uscita = subprocess.run(
        ["git", "ls-files", "*.md", "docs/landing/*.html"],
        cwd=RADICE,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    fonti = []
    for riga in uscita.splitlines():
        riga = riga.strip()
        if not riga:
            continue
        f = RADICE / riga
        if f.is_file():
            fonti.append((riga, f.read_text(encoding="utf-8", errors="replace")))
    return fonti


def test_ci_sono_documenti_da_guardare():
    """Zero file vuol dire zero problemi, per sempre e in silenzio."""
    assert _documenti_tracciati(), (
        "git non traccia nessun .md: se i documenti sono stati spostati, "
        "aggiorna _documenti_tracciati() qui, altrimenti questo controllo "
        "non puo' piu' fallire"
    )


def test_nessun_documento_nomina_un_profilo_inesistente():
    valide = _etichette_valide()
    problemi: list[str] = []
    for nome, testo in _documenti_tracciati():
        # Il changelog e il backlog raccontano la storia, compreso cio' che
        # e' stato tolto: nominare un profilo rimosso li' e' corretto.
        if nome.endswith(("CHANGELOG.md", "BACKLOG.md")):
            continue
        for regex in (_RE_IT, _RE_EN, _RE_IT_NUDO):
            for m in regex.finditer(testo):
                citato = m.group(1).strip().lower()
                if not citato or citato in valide:
                    continue
                # La forma senza virgolette e' avida: prova anche i prefissi,
                # perche' «profilo Solo OCR e il resto della frase» cattura
                # troppo. Se un prefisso e' un profilo vero, va bene cosi'.
                parole = citato.split()
                if any(" ".join(parole[:n]) in valide for n in range(1, len(parole))):
                    continue
                problemi.append(f"{nome}: nomina il profilo «{m.group(1).strip()}»")
    assert not problemi, (
        "questi documenti descrivono profili che non esistono nel programma:\n  "
        + "\n  ".join(sorted(set(problemi)))
        + "\n\nO il profilo va rimesso, o il documento va corretto. Chi legge "
        "cerchera' quella voce nell'interfaccia e non la trovera'."
    )


def test_il_controllo_prende_un_profilo_inventato(tmp_path, monkeypatch):
    """La prova che il test qui sopra puo' davvero fallire.

    Si ricostruisce il difetto del 2026-08-09: un documento che dedica una
    frase intera a un profilo rimosso.
    """
    finto = tmp_path / "FINTO.md"
    finto.write_text(
        'Il profilo «Fatture» ricostruisce le tabelle.\n'
        'The "invoices" profile does the same.\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys.modules[__name__],
        "_documenti_tracciati",
        lambda: [("FINTO.md", finto.read_text(encoding="utf-8"))],
    )
    with pytest.raises(AssertionError) as e:
        test_nessun_documento_nomina_un_profilo_inesistente()
    assert "Fatture" in str(e.value)
    assert "invoices" in str(e.value)


@pytest.mark.parametrize("citazione", [
    'Il profilo «Email legali» toglie nomi.',
    'The "LLM-ready" profile produces lean text.',
    'Il profilo predefinito ricostruisce le tabelle.',
])
def test_i_profili_veri_non_fanno_rumore(citazione, monkeypatch):
    """Un controllo che segnala anche cio' che e' giusto viene spento."""
    monkeypatch.setattr(
        sys.modules[__name__],
        "_documenti_tracciati",
        lambda: [("FINTO.md", citazione)],
    )
    test_nessun_documento_nomina_un_profilo_inesistente()
