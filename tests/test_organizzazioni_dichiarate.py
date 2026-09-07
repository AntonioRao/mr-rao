# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Le ragioni sociali: **si trovano, si dicono, non si tolgono.**

## La domanda, e perche' non e' «aggiungere un riconoscitore»

`rizzo-pii` ha un tag `ORG` che sostituisce le ragioni sociali. Mr. Rao fa
l'opposto **di proposito**: `_SIGLE_SOCIETARIE` esiste per impedire che
«il cliente Beta Consulting S.p.A.» diventi «il cliente {{NAME}} S.p.A.», che
il commento in `privacy.py` chiama «il falso positivo peggiore possibile».
Una societa' non e' una persona fisica, il GDPR non la protegge, e in un atto
la ragione sociale e' spesso il soggetto della frase: toglierla rende il
documento illeggibile senza proteggere nessuno.

Resta pero' vero che in un atto la ragione sociale **reidentifica**: «la
Alfa Costruzioni S.r.l. di Santhia'» porta a una persona con due ricerche.
Chi consegna il documento deve saperlo.

## La risposta: il terzo canale

Il rapporto ha gia' tre conti separati — cosa e' stato **tolto** (`counts`),
cosa e' stato **trovato e lasciato apposta** (`detected`), cosa il motore
**non ha saputo decidere** (`suspects`). Le ragioni sociali stanno nel
secondo, dove stanno gia' eta' e sesso: il testo esce identico e il rapporto
dice quante ce ne sono.

Non e' un ripiego: e' l'unica risposta che tiene insieme le due cose vere,
cioe' che togliere una societa' sarebbe sbagliato e che non dirlo sarebbe
incompleto.

Tutti i valori sono inventati.
"""

from __future__ import annotations

from mr_rao.privacy import PrivacyOptions, apply_privacy_filter


def _rapporto(testo: str, **opzioni):
    fuori, rapporto = apply_privacy_filter(testo, PrivacyOptions(**opzioni))
    return fuori, rapporto.to_dict()


def test_la_ragione_sociale_resta_nel_testo():
    """**La riga che tiene ferma la scelta.** Il testo esce identico.

    Se un domani qualcuno mettesse qui una sostituzione, romperebbe la
    ragione per cui questo riconoscitore esiste.
    """
    testo = "Il cespite e' locato alla Alfa Costruzioni S.r.l. di Santhia'."
    fuori, _ = _rapporto(testo)
    assert fuori == testo, f"la societa' e' stata toccata: {fuori!r}"


def test_la_ragione_sociale_finisce_nel_rapporto():
    testo = ("Il cespite e' locato alla Alfa Costruzioni S.r.l. e la perizia "
             "e' della Beta Immobiliare S.p.A.")
    _, rapporto = _rapporto(testo)
    trovate = [r for r in rapporto["detected"] if r["kind"] == "organizzazione"]
    assert len(trovate) == 2, f"attese due societa', trovate {trovate}"
    assert rapporto["detected_counts"].get("organizzazione") == 2


def test_non_conta_come_sostituzione():
    """Il conto di cio' che e' stato tolto non deve gonfiarsi.

    «3 redatti» quando i redatti sono zero e' peggio di non dire niente.
    """
    _, rapporto = _rapporto("Locato alla Alfa Costruzioni S.r.l.")
    assert rapporto["total"] == 0, rapporto["counts"]
    assert "organizzazione" not in rapporto["counts"]


def test_lo_spegnimento_smette_di_cercarle():
    _, rapporto = _rapporto("Locato alla Alfa Costruzioni S.r.l.",
                            organizzazioni=False)
    assert not [r for r in rapporto["detected"] if r["kind"] == "organizzazione"]


def test_una_frase_senza_societa_non_ne_inventa():
    """La riga che impedisce di segnalare mezzo documento."""
    testo = ("Il ricorrente Mario Rossi, nato a Novara, chiede la restituzione "
             "della somma versata il 12/06/2025 presso la sede di Milano.")
    _, rapporto = _rapporto(testo)
    assert not [r for r in rapporto["detected"] if r["kind"] == "organizzazione"], (
        rapporto["detected"])


def test_le_sigle_straniere_contano_come_le_italiane():
    _, rapporto = _rapporto("Fornitore: Acme Systems Ltd e Nordwind GmbH.")
    trovate = [r for r in rapporto["detected"] if r["kind"] == "organizzazione"]
    assert len(trovate) == 2, f"sigle straniere non viste: {trovate}"


def test_il_nome_accanto_alla_societa_resta_protetto():
    """La riga che prova che il riconoscitore non ha rotto lo scudo.

    `_SIGLE_SOCIETARIE` esiste per impedire «il cliente {{NAME}} S.p.A.», ed
    e' la ragione per cui questo riconoscitore non sostituisce: se aggiungerlo
    avesse smontato quello scudo, avremmo peggiorato le cose per contare
    meglio.
    """
    testo = "Il cliente Beta Consulting S.p.A. ha versato l'acconto."
    fuori, _ = _rapporto(testo)
    assert "Beta Consulting S.p.A." in fuori, fuori
    assert "{{NAME" not in fuori, fuori
