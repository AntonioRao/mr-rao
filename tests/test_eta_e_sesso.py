# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Età e sesso: si trovano, si dicono, **non si tolgono mai**.

Perché questi due non hanno un segnaposto
------------------------------------------

Sono quasi-identificatori, ed è una categoria diversa da tutto il resto del
motore. Un IBAN identifica una persona da solo; «45 anni» no — ma «45 anni»
insieme a un comune piccolo e a una professione la identifica benissimo, ed
è esattamente così che si de-anonimizza un archivio.

Chi lavora su una cartella clinica, su una statistica del personale o su una
perizia sta chiedendo **proprio quei due dati**: toglierli non protegge
nessuno di più e rende il documento inservibile per l'unico uso per cui era
stato preparato. Lasciarli in silenzio, però, vuol dire che chi rilegge non
sa che ci sono.

Quindi la terza via: compaiono nel rapporto. «Ho lasciato in chiaro 3 età,
apposta» è un'informazione che un DPO può usare; il silenzio no.

Tutti i valori sono inventati.
"""

from __future__ import annotations

import pytest

from mr_rao.privacy import PrivacyOptions, apply_privacy_filter


def passa(testo: str, **kw):
    fuori, rapporto = apply_privacy_filter(testo, PrivacyOptions(**kw))
    return fuori, [r["kind"] for r in rapporto.rilevati], rapporto


# ------------------------------------------- la riga che tiene la decisione


@pytest.mark.parametrize(
    "frase",
    [
        "Il ricorrente, di anni 45, residente in Pisa.",
        "Paziente 78enne, sesso: F",
        "Età: 32 - Sesso maschile",
        "Un uomo di 45 anni di età",
        "Genere: femminile",
    ],
)
def test_il_testo_esce_identico(frase: str) -> None:
    """**Il testo non si tocca.** Se un domani qualcuno aggiungesse una
    sostituzione a quei due riconoscitori, romperebbe la ragione per cui
    esistono — e nessun altro test se ne accorgerebbe, perché tutti gli
    altri guardano ciò che il motore *toglie*."""
    fuori, _, _ = passa(frase)
    assert fuori == frase


def test_non_esiste_nessun_segnaposto_per_questi_due() -> None:
    """Non c'è `{{ETA}}` né `{{SESSO}}` nel motore, e non è una svista.

    Il controllo legge il **sorgente**: una costante inventata a metà — il
    riconoscitore che chiama `segnaposto()` con un'etichetta nuova — si
    vedrebbe qui prima che in un documento vero.
    """
    from pathlib import Path

    import mr_rao.privacy as motore

    sorgente = Path(motore.__file__).read_text(encoding="utf-8")
    for vietato in ("{{ETA}}", "{{SESSO}}", "{{AGE}}", "{{GENDER}}"):
        assert vietato not in sorgente, vietato


# ------------------------------------------------- ma si vedono nel rapporto


@pytest.mark.parametrize(
    ("frase", "attesi"),
    [
        ("Il ricorrente, di anni 45, residente in Pisa.", ["eta"]),
        ("Paziente 78enne", ["eta"]),
        ("Età 32", ["eta"]),
        ("Un uomo di 45 anni di età", ["eta"]),
        ("Sesso: M", ["genere"]),
        ("sesso femminile", ["genere"]),
        ("Genere: F", ["genere"]),
        ("Paziente 78enne, sesso: F", ["eta", "genere"]),
        # P8.2: quattro forme che i gruppi `(?i:…)` non coprivano.
        # Il danno non e' un dato che esce: e' un rapporto che conta meno
        # di quello che c'e'. «Ho lasciato in chiaro 3 eta'» vale solo
        # se sono davvero tre.
        ("Un uomo di 45 anni d'ETÀ", ["eta"]),
        ("sesso: f", ["genere"]),
        ("il ricorrente, d' anni 78, residente in Pisa", ["eta"]),
        ("Eta': 45", ["eta"]),
    ],
)
def test_finiscono_nel_rapporto(frase: str, attesi: list[str]) -> None:
    _, trovati, _ = passa(frase)
    assert sorted(trovati) == sorted(attesi), frase


def test_anni_d_eta_prende_anche_eta_non_solo_l_apostrofo() -> None:
    """Il gruppo deve coprire `et[àa]` dopo `d'` e dopo `di`.

    Una prima stesura metteva `et[àa]` solo sul ramo `di`, quindi
    `45 anni d'ETÀ` veniva contato come età fermandosi a `d'` — il
    rapporto diceva sì, il campione no. I due motori devono
    combaciare sul pezzo intero, non solo sul fatto che qualcosa
    sia stato visto.
    """
    _, _, rapporto = passa("Un uomo di 45 anni d'ETÀ.")
    campioni = [r["sample"] for r in rapporto.rilevati if r["kind"] == "eta"]
    assert campioni, rapporto.rilevati
    assert any(len(c) > len("45•••••d'") for c in campioni), campioni


def test_il_rapporto_non_li_conta_fra_le_sostituzioni() -> None:
    """`counts` dice cosa è stato **tolto**. Contarli lì direbbe una cosa
    che non è successa, ed è il conto che l'utente legge per primo."""
    _, _, rapporto = passa("Il ricorrente, di anni 45, sesso M.")
    assert rapporto.counts.get("eta") is None
    assert rapporto.counts.get("genere") is None
    assert rapporto.total == 0
    assert len(rapporto.rilevati) == 2


# ------------------------------------------------ e cosa NON deve prendere


@pytest.mark.parametrize(
    "frase",
    [
        # «45 anni» nudo è quasi sempre una durata, e prenderlo vorrebbe dire
        # riempire di segnalazioni ogni relazione aziendale.
        "dopo 45 anni di servizio",
        "un contratto di 45 anni",
        "una concessione di anni novantanove",
        # Un anno non è un'età.
        "anni 2024",
        # Oltre i 120 è un anniversario o una durata.
        "di anni 450",
        # «genere» ha un altro mestiere in italiano.
        "Il genere letterario del testo",
        "un genere musicale",
    ],
)
def test_quello_che_non_e_eta_o_sesso_non_si_segnala(frase: str) -> None:
    _, trovati, _ = passa(frase)
    assert trovati == [], (frase, trovati)


# ------------------------------------------------------- i due interruttori


def test_l_interruttore_spegne_la_ricerca() -> None:
    """Spento non vuol dire «documento più pulito»: vuol dire più
    silenzioso. Il testo è identico nei due casi — cambia solo il rapporto."""
    frase = "Il ricorrente, di anni 45, sesso M."
    acceso, trovati_a, _ = passa(frase)
    spento, trovati_s, _ = passa(frase, quasi_id=False)
    assert acceso == spento == frase
    assert trovati_a and trovati_s == []


def test_chi_li_vuole_togliere_davvero_ha_gia_uno_strumento() -> None:
    """Nessuna capacità è perduta: l'elenco «nascondi sempre» li toglie.

    È questa riga a rendere onesta la scelta di non offrire la
    sostituzione — senza, sarebbe una funzione mancante travestita da
    decisione.
    """
    fuori, _, rapporto = passa("Il ricorrente, di anni 45.", sempre=("45",))
    assert "45" not in fuori, fuori
    assert rapporto.total >= 1


def test_non_compaiono_fra_le_categorie_sostituibili() -> None:
    """`CATEGORIE` sono le chiavi di `counts`, cioè di ciò che è stato
    **tolto**. Queste due non ci finiscono mai, quindi non stanno lì — e
    così nel pannello «segnala anziché sostituisci» non compare una casella
    che non sarebbe attaccata a niente."""
    from mr_rao.privacy import CATEGORIE

    assert "eta" not in CATEGORIE and "genere" not in CATEGORIE


def test_il_rapporto_sa_come_chiamarle() -> None:
    """Fuori da `CATEGORIE` ma **non senza nome**: il rapporto le elenca, e
    un `kind` grezzo in faccia a chi legge non è un rapporto."""
    from mr_rao.i18n import etichetta_categoria

    for c in ("eta", "genere"):
        for lingua in ("it", "en"):
            nome = etichetta_categoria(c, lingua)
            assert nome and nome != c, (c, lingua, nome)


def test_e_raggiungibile_dall_interfaccia() -> None:
    from mr_rao.app_factory import create_app

    app = create_app()
    app.config["TESTING"] = True
    pagina = app.test_client().get("/", base_url="http://127.0.0.1:5000").get_data(
        as_text=True)
    assert 'id="privacy-quasi_id"' in pagina
    pezzo = pagina.split('id="privacy-quasi_id"')[1][:40]
    assert "checked" in pezzo, pezzo
