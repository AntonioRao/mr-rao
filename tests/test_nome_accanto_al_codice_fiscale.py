# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Il nome accanto a un codice fiscale valido e' una persona.

Perche' esiste
--------------

Fino alla 1.22.0 le regole sui nomi erano quattro: titolo davanti, formula
di chiusura, indirizzo di posta accanto, nome e cognome **entrambi
riconosciuti negli elenchi**. L'ultima e' quella che copre la maggior parte
dei casi, e ha un buco preciso: non puo' scattare su una persona che negli
elenchi non c'e'.

Quanto fosse grande quel buco non si sapeva, perche' il corpus con cui
misuravamo il richiamo ha i nomi che stanno nei nostri elenchi (99,98%).
Misurato prendendo le sue frasi e sostituendo i nomi con altri fuori
elenco: il richiamo passava da 99,4% a **0,5%**. Tutto il riconoscimento
veniva dagli elenchi, niente dal contesto.

E in quelle stesse frasi c'era un segnale che non usavamo: un codice
fiscale attaccato al nome. Ha un carattere di controllo, quindi non capita
per caso, e in Italia si rilascia a una persona fisica.

Con la regola: **da 0,5% a 36,0%** su 78 372 nomi fuori elenco, e zero
sostituzioni in piu' sui moduli in bianco.

Cosa deve continuare a fallire
------------------------------

Un codice fiscale accanto a una **ragione sociale**. E' la forma in cui
quel numero compare piu' spesso in un documento amministrativo, e una
regola che la prendesse trasformerebbe ogni intestazione di ente in un
nome di persona -- il falso positivo peggiore che questo motore possa
fare, perche' la frase perde il soggetto.
"""

from __future__ import annotations

import pytest

from mr_rao.privacy import PrivacyOptions, apply_privacy_filter, senza_numeri

# Un codice fiscale vero, che passa il carattere di controllo. Se non
# passasse, il segnaposto non comparirebbe e questi test misurerebbero
# l'assenza di un codice invece della regola.
CF = "RSSMRA85M01H501Z"


def redigi(testo: str) -> str:
    return senza_numeri(apply_privacy_filter(testo, PrivacyOptions())[0])


def test_il_codice_fiscale_di_prova_e_valido() -> None:
    """La guardia della guardia: senza un CF valido tutto il file misura
    una cosa diversa da quella che crede."""
    assert "{{CODICE_FISCALE}}" in redigi(f"codice {CF} qui")


@pytest.mark.parametrize(
    "frase",
    [
        "Contratto tra Beta Consulting S.p.A. e Elicio Nazar CF {cf} del 2023",
        "Atto notarile tra Deon Ucan CF {cf} e Quadrante Meccanica S.r.l.s.",
        "Il sottoscritto Wangchuk Nrayo, codice fiscale {cf}, dichiara",
        "Christopherus Kimete - C.F. {cf}",
        "Aadhav Romanos cod. fisc. {cf}",
    ],
)
def test_una_persona_fuori_dagli_elenchi_viene_riconosciuta(frase: str) -> None:
    """Nessuno di questi nomi sta nei nostri elenchi: senza il codice
    fiscale accanto resterebbero tutti in chiaro."""
    fuori = redigi(frase.format(cf=CF))
    assert "{{NAME}}" in fuori, fuori


def test_senza_il_codice_fiscale_lo_stesso_nome_resta() -> None:
    """Il verso che dimostra che a fare il lavoro e' il codice fiscale e
    non qualcos'altro nella frase.

    E' anche il limite dichiarato del motore: un nome fuori elenco, senza
    niente che dica che li' c'e' una persona, non viene toccato.
    """
    assert "{{NAME}}" not in redigi("Christopherus Kimete - pratica 4471")


def test_una_ragione_sociale_col_codice_fiscale_non_diventa_una_persona() -> None:
    """La forma piu' comune in cui un codice fiscale compare in un
    documento amministrativo. Prenderla vorrebbe dire togliere il soggetto
    alla frase."""
    for ente in (
        f"Comune di Pontremoli CF {CF}",
        f"Agenzia delle Entrate C.F. {CF}",
        f"Istituto Comprensivo Manzoni codice fiscale {CF}",
    ):
        assert "{{NAME}}" not in redigi(ente), ente


def test_una_parola_sola_davanti_al_codice_non_basta() -> None:
    """Davanti all'etichetta `CF` ci finisce spesso l'ultima parola della
    frase precedente, e una parola maiuscola isolata non e' una persona."""
    assert "{{NAME}}" not in redigi(f"Riepilogo CF {CF}")


def test_la_finestra_non_attraversa_le_righe() -> None:
    """Un nome che sta su un'altra riga non e' «accanto».

    Con una finestra che attraversa gli a capo, il motore prenderebbe la
    fine del paragrafo precedente: e' il modo di sbagliare che ha gia'
    pagato una volta con gli indirizzi.
    """
    fuori = redigi(f"Elicio Nazar\n\nSezione 2 - dati fiscali\nCF {CF}")
    assert "{{NAME}}" not in fuori, fuori


# --------------------------------------------------- ruoli e campi dichiarati
#
# Stessa famiglia: il testo **dichiara** che li' c'e' una persona, con un
# sostantivo di ruolo invece che con un titolo o un codice. Misurato sul
# corpus legale, `cliente` precedeva da solo 2.671 dei nomi che restavano in
# chiaro; con ruoli e campi il richiamo sui nomi fuori elenco passa dal 36%
# (solo codice fiscale) al 71%.


@pytest.mark.parametrize(
    "frase",
    [
        "Il cliente Elicio Nazar chiede invio documenti",
        "Ordine online cliente Wangchuk Nrayo del 4 maggio",
        "il promittente acquirente Deon Ucan ha versato la caparra",
        "Il paziente Christopherus Kimete e ricoverato dal 12",
        "il conduttore Aadhav Romanos versa il canone",
        "NOME= Gjylfidane Rojana; PRATICA= 4471",
        "Nominativo: Somlyai Dawson",
    ],
)
def test_un_ruolo_dichiara_una_persona(frase: str) -> None:
    assert "{{NAME}}" in redigi(frase), redigi(frase)


@pytest.mark.parametrize(
    "frase",
    [
        # La ragione sociale dopo un ruolo: e' il motivo per cui i ruoli
        # pretendono due parole, e non basta -- servono anche le sigle.
        "il cliente Beta Consulting S.p.A. ha versato l'acconto",
        "il conduttore Immobiliare Verdi S.r.l. paga il canone",
        "il cliente Delta Systems Ltd ha firmato",
        # Lo scudo delle parole d'ente, che qui vale come altrove.
        "il conduttore Fondazione Verdi paga il canone",
        # Nessun nome dopo il ruolo.
        "Il cliente ha chiesto una copia del contratto",
    ],
)
def test_un_ruolo_davanti_a_un_ente_non_lo_rende_una_persona(frase: str) -> None:
    assert "{{NAME}}" not in redigi(frase), redigi(frase)


def test_la_sigla_si_riconosce_anche_quando_finisce_dentro_al_nome() -> None:
    """Due posti, e servono tutti e due.

    La finestra del ruolo prende fino a tre parole: su `Beta Consulting
    S.p.A.` si ferma prima della sigla, su `Delta Systems Ltd` se la
    inghiotte. Guardando solo il testo che segue, il secondo caso passava.
    """
    assert "{{NAME}}" not in redigi("il cliente Delta Systems Ltd ha firmato")
    assert "{{NAME}}" not in redigi("il cliente Beta Consulting S.p.A. paga")
