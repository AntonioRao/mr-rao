"""Gli esempi stampati nel README devono essere veri.

`docs/PRIVACY.md` e' rimasto per due versioni a descrivere una libreria
che non c'era piu'. La documentazione non fallisce mai da sola: fallisce
in silenzio, e continua a sembrare corretta.

Questo test guarda da due lati, e serve che li guardi entrambi:

* il **motore** si comporta come l'esempio promette;
* l'esempio e' **ancora scritto** in tutti e due i README.

Cambiare il codice senza aggiornare la pagina rompe il primo controllo.
Cambiare la pagina senza verificare il codice rompe il secondo.
"""
from pathlib import Path

import pytest

from mr_rao.privacy import PrivacyOptions, apply_privacy_filter

README = [Path("README.md"), Path("README.it.md")]

# (testo, resta com'e')  — gli stessi sei casi mostrati nella sezione
# «Il motore di anonimizzazione» / «The redaction engine».
ESEMPI = [
    ("Protocollo interno: 0123456789", True),
    ("Registrata il 01.02.2024", True),
    ("Ordine 5551234567890123", True),
    ("IBAN IT60X0542811101000000123456", False),
    ("Carta 4111 1111 1111 1111", False),
    ("cell. 335 123 4567", False),
]


@pytest.mark.parametrize("testo,invariato", ESEMPI)
def test_il_motore_si_comporta_come_promette_il_readme(testo, invariato):
    out, report = apply_privacy_filter(testo, PrivacyOptions())
    if invariato:
        assert out == testo, f"il README promette che resti intatto: {out!r}"
        assert report.total == 0
    else:
        assert out != testo, "il README promette che sparisca"
        assert report.total >= 1


@pytest.mark.parametrize("testo,_", ESEMPI)
@pytest.mark.parametrize("pagina", README, ids=lambda p: p.name)
def test_l_esempio_e_ancora_nel_readme(pagina, testo, _):
    if not pagina.is_file():
        pytest.skip(f"{pagina} non presente")
    assert testo in pagina.read_text(encoding="utf-8"), (
        f"«{testo}» non compare piu' in {pagina}: o l'esempio e' stato "
        f"cambiato senza aggiornare questo test, o la sezione sul motore "
        f"e' sparita dalla pagina."
    )


@pytest.mark.parametrize("pagina", README, ids=lambda p: p.name)
def test_il_readme_rimanda_alla_documentazione_del_motore(pagina):
    """La pagina che spiega il motore era linkata in fondo, fra le note.

    **Ognuno alla sua lingua.** Il README inglese deve puntare a
    `PRIVACY.en.md`: mandare un lettore inglese su un documento italiano
    equivale a non linkarlo, e quello e' il documento in cui vive la
    credibilita' del motore — proprio la pagina che non puo' permettersi di
    risultare illeggibile.
    """
    if not pagina.is_file():
        pytest.skip(f"{pagina} non presente")
    testo = pagina.read_text(encoding="utf-8")
    atteso = "docs/PRIVACY.en.md" if pagina.name == "README.md" else "docs/PRIVACY.md"
    assert atteso in testo, f"{pagina.name} non rimanda a {atteso}"
    # deve stare nella prima meta' della pagina, non in coda
    posizione = testo.index(atteso) / len(testo)
    assert posizione < 0.5, (
        f"il rimando a {atteso} sta al {posizione:.0%} della pagina: "
        f"e' la spiegazione della cosa che distingue questo progetto, "
        f"non una nota a pie' di pagina"
    )
