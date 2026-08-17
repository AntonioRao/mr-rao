# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""«Ciao Pietro»: il saluto dichiara che quello che segue è una persona.

## Perché esiste

Un nome di battesimo **da solo** non basta mai, ed è una scelta pagata:
«Rosa», «Vera», «Costa», «Villa» sono nomi *e* parole italiane, e
sostituirli costa più di quanto renda — è la stessa misura che ha tolto
8 904 sostituzioni sbagliate su venti moduli in bianco. Quindi un nome
isolato diventa un **sospetto**: sta nel rapporto, resta nel testo.

Ma «Ciao Pietro» non è un nome isolato. Davanti ha una formula che dice
cosa sia, ed è lo stesso genere di prova del titolo professionale, del
nome accanto a un indirizzo di posta e della firma in chiusura — regole
che nel motore ci sono già. Una formula di **chiusura** dichiara che
quello che segue è una persona; una di **apertura** fa lo stesso
all'inizio, ed è il caso più frequente nelle email e nelle chat, dove il
cognome spesso non c'è affatto.

## Il confine, che è tutta la sicurezza della regola

Dopo un saluto ci finisce di tutto: «Ciao Team», «Salve Ufficio»,
«Gentile Cliente». Essere maiuscola non prova niente. Quindi la parola
dev'essere **negli elenchi dei nomi**: senza quel vincolo la regola
prenderebbe la prima parola di ogni messaggio che comincia con «Ciao».
"""
import pytest

from mr_rao.privacy import PrivacyOptions, apply_privacy_filter

PROSA = pytest.mark.parametrize("prosa", [True, False], ids=["prosa", "modulo"])


def redigi(testo: str, prosa: bool) -> str:
    return apply_privacy_filter(testo, PrivacyOptions(prosa=prosa))[0]


@PROSA
@pytest.mark.parametrize(
    "testo,atteso",
    [
        ("Ciao Pietro, ci vediamo domani", "Ciao {{NAME_1}}, ci vediamo domani"),
        ("Caro Marco, grazie di tutto", "Caro {{NAME_1}}, grazie di tutto"),
        ("Gentile Anna Bianchi, in allegato", "Gentile {{NAME_1}}, in allegato"),
        ("Buongiorno Nazzareno, tutto bene?", "Buongiorno {{NAME_1}}, tutto bene?"),
        # Il composto dopo il saluto: le due regole devono convivere.
        ("Ciao Walter Di Salvo, a domani", "Ciao {{NAME_1}}, a domani"),
    ],
)
def test_il_saluto_annuncia_una_persona(testo: str, atteso: str, prosa: bool) -> None:
    assert redigi(testo, prosa) == atteso


class TestQuelloCheIlSalutoNonDeveTirarsiDietro:
    """Ogni caso è una parola maiuscola dopo un saluto che persona non è.

    Se uno di questi sparisce la regola è troppo larga, e va stretta — non
    spiegata.
    """

    @PROSA
    @pytest.mark.parametrize(
        "testo",
        [
            "Gentile Cliente, la informiamo",
            "Ciao Team, buon lavoro",
            "Salve Ufficio Protocollo",
            "Buongiorno Dottore",
            "Gentile Signora, buongiorno",
            "Ciao a tutti",
            "Gentile Direzione, si comunica",
            "Egregio Presidente, con la presente",
        ],
    )
    def test_resta_com_era(self, testo: str, prosa: bool) -> None:
        assert redigi(testo, prosa) == testo


def test_serve_il_saluto_davvero() -> None:
    """Senza formula di apertura il nome isolato resta un sospetto.

    È il controllo che dice che la regola del saluto non ha allargato il
    caso generale. Si prova con `names_alone` **spenta**, perché dalla
    1.26.0 quella è accesa di serie e prenderebbe «Pietro» per conto suo:
    lasciandola accesa, questo banco non proverebbe più niente.
    """
    fuori, rapporto = apply_privacy_filter(
        "Pietro", PrivacyOptions(names_alone=False)
    )
    assert fuori == "Pietro"
    assert any(s["kind"] == "nome" for s in rapporto.to_dict()["suspects"])
