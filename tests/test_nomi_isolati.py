"""Il nome di battesimo da solo, quando non è anche una parola (P9.2).

## La rinuncia che c'era, e perché aveva ragione

Un nome isolato non viene sostituito: diventa un sospetto. La ragione è che
«Rosa», «Vera», «Costa», «Villa» sono nomi *e* parole italiane, e il motore
ha già ritirato un'euristica sui nomi per un numero misurato — 8 904
sostituzioni sbagliate su venti moduli in bianco.

## Perché si può allentare, e solo così

Quella ragione **non vale** per «Walter», «Nazzareno», «Samuele», che parole
non sono: sono l'88% dell'elenco (891 nomi su 1017). Ma la stessa parola
cambia natura a seconda di cosa le sta davanti — «Umberto» è un collega,
«ospedale Umberto» è un edificio, «via Umberto» è un indirizzo,
«Sant'Umberto» è un paese — e a distinguerli non c'è niente nella parola.

Quindi l'opzione è **spenta di serie** e ha una guardia sul contesto, e
questo banco tiene le due metà: che i nomi veri vengano presi, e che le
intitolazioni no. Il costo lo misura `scripts/bench_nomi_isolati.py`, che
confronta il motore con e senza: **+15 nomi presi, 0 falsi positivi nuovi**
sulle due popolazioni del banco.
"""
import pytest

from mr_rao.privacy import PrivacyOptions, apply_privacy_filter

PROSA = pytest.mark.parametrize("prosa", [True, False], ids=["prosa", "modulo"])


def redigi(testo: str, acceso: bool, prosa: bool = True) -> str:
    return apply_privacy_filter(
        testo, PrivacyOptions(prosa=prosa, names_alone=acceso)
    )[0]


class TestSpentaDiSerie:
    """Il verso di una rinuncia vecchia non si cambia senza dirlo."""

    def test_di_serie_resta_un_sospetto(self) -> None:
        fuori, rapporto = apply_privacy_filter("Ho parlato con Pietro.", PrivacyOptions())
        assert fuori == "Ho parlato con Pietro."
        assert any(s["kind"] == "nome" for s in rapporto.to_dict()["suspects"])

    def test_il_predefinito_della_dataclass_e_spento(self) -> None:
        # Scritto qui perché è il posto in cui si nota se qualcuno lo
        # accende «tanto è meglio»: cambierebbe l'uscita di ogni conversione
        # già fatta, e nessun altro banco lo direbbe.
        assert PrivacyOptions.names_alone is False


class TestAccesaPrendeINomi:
    @PROSA
    @pytest.mark.parametrize(
        "testo,nome",
        [
            ("Ho parlato con Pietro e mi ha detto di sì.", "Pietro"),
            ("L'appuntamento con Walter è alle 15.", "Walter"),
            ("Chiedi a Nazzareno se ha finito.", "Nazzareno"),
            ("Antonio non è venuto alla riunione.", "Antonio"),
            ("Ho lasciato i documenti a Samuele.", "Samuele"),
        ],
    )
    def test_il_nome_sparisce(self, testo: str, nome: str, prosa: bool) -> None:
        fuori = redigi(testo, acceso=True, prosa=prosa)
        assert nome not in fuori
        assert "{{NAME_1}}" in fuori


class TestQuelloCheNonDeveToccare:
    """Le stesse lettere, davanti una parola diversa.

    Ogni caso qui è un nome di battesimo **identico** a uno della classe
    sopra: se il motore li distingue non è perché conosce la parola, è
    perché guarda cosa le sta davanti. È l'unica cosa che rende
    l'opzione utilizzabile invece che dannosa.
    """

    @PROSA
    @pytest.mark.parametrize(
        "testo,nome",
        [
            ("Il paziente è all'ospedale Umberto.", "Umberto"),
            ("Passeggiata a villa Ada domenica.", "Ada"),
            ("Il figlio frequenta l'istituto Leonardo.", "Leonardo"),
            ("Lo spettacolo è al teatro Carlo.", "Carlo"),
            ("Il paese si chiama Sant'Antonio.", "Antonio"),
            ("Uscita autostradale Amedeo.", "Amedeo"),
            ("Due pizze Margherita e una birra.", "Margherita"),
            ("Il premio Italo è stato assegnato.", "Italo"),
            ("Si gioca allo stadio Giuseppe.", "Giuseppe"),
        ],
    )
    def test_le_intitolazioni_restano(self, testo: str, nome: str, prosa: bool) -> None:
        assert nome in redigi(testo, acceso=True, prosa=prosa)

    @PROSA
    def test_accenderla_non_peggiora_cio_che_gia_sbagliava(self, prosa: bool) -> None:
        """«chiesa di San Pietro» in prosa sparisce **già oggi**.

        Non è questa opzione: è la regola delle coppie, dove in prosa basta
        un riscontro solo, e «San Pietro» ne ha uno. Il banco lo dice
        confrontando acceso e spento invece di pretendere un'uscita: quello
        che si chiede a una funzione nuova è di non peggiorare, e quel
        difetto va misurato per conto suo (è in backlog).
        """
        testo = "La funzione è nella chiesa di San Pietro."
        assert redigi(testo, acceso=True, prosa=prosa) == redigi(
            testo, acceso=False, prosa=prosa
        )

    @PROSA
    def test_i_cognomi_da_soli_restano_sospetti(self, prosa: bool) -> None:
        # L'opzione vale per i **nomi di battesimo**. Un cognome isolato non
        # dice se sia una persona o l'azienda che porta quel cognome, e
        # quella distinzione la parola non ce l'ha.
        assert "Ferraris" in redigi("Il dossier Ferraris è pronto.", True, prosa)

    @PROSA
    def test_i_nomi_che_sembrano_parole_restano_fuori(self, prosa: bool) -> None:
        # «Vittorio» finisce come finiscono le parole italiane (-orio),
        # «Federica» come -ica. Il veto morfologico c'era già e resta: è la
        # rinuncia che tiene l'opzione lontana dai guai.
        assert "Vittorio" in redigi("Il collega Vittorio se ne occupa.", True, prosa)
        assert "Federica" in redigi("Federica richiama nel pomeriggio.", True, prosa)


def test_la_guardia_salta_articoli_e_preposizioni() -> None:
    """«all'ospedale», «della villa», «allo stadio».

    Guardando solo la parola immediatamente precedente la guardia non
    scatterebbe quasi mai, perché in italiano fra l'edificio e il nome ci
    sta sempre un articolo. E l'apostrofo **separa**: tenendolo dentro il
    token, «all'ospedale» non risultava in nessun elenco e tre intitolazioni
    su cinque passavano. L'ha trovato il banco, non una rilettura.
    """
    for testo in (
        "Ricoverato all'ospedale Umberto.",
        "Ci vediamo allo stadio Giuseppe.",
        "I giardini della villa Ada.",
        "Diplomato presso l'istituto Leonardo.",
    ):
        assert redigi(testo, acceso=True) == testo
