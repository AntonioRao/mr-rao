"""I cognomi composti: «Di Salvo», «De Luca», «D'Amico».

## Il difetto, misurato prima di scrivere una riga

Il riconoscitore dei nomi lavora su **tratti continui di parole che non
sono parole comuni**. Quasi tutte le particelle dei cognomi composti sono
preposizioni, e quindi stanno — giustamente — fra le parole comuni: `di`,
`del`, `della`, `dei`, `degli`, `da`, `dal`, `dalla`, `lo`, `la`. La
particella **spezzava il tratto**, e il nome si sbriciolava in due parole
isolate: una parola sola non basta mai, quindi non restava niente.

    Walter Di Salvo ha firmato   ->   Walter Di Salvo ha firmato

Peggio ancora dopo un titolo, dove usciva **mezzo nome**:

    Il sig. Walter Di Salvo      ->   Il sig. {{NAME_1}} Di Salvo

cioe' il documento sembrava trattato e il cognome era ancora li'.

`de`, `li`, `lu` parole comuni non sono, ed e' tutta qui la ragione per cui
«Luca De Luca» funzionava e «Walter Di Salvo» no: nessuno l'aveva deciso.

## Perche' i casi stanno scritti in tutti e due i modi

`prosa=True` e `prosa=False` sono due motori diversi nella parte che conta:
sul modulo servono **due** riscontri negli elenchi, in prosa ne basta uno.
Un cognome composto che funziona in prosa e non su modulo e' il difetto
travestito, ed e' esattamente quello che c'era.
"""
import pytest

from mr_rao.privacy import PrivacyOptions, apply_privacy_filter

PROSA = pytest.mark.parametrize("prosa", [True, False], ids=["prosa", "modulo"])


def redigi(testo: str, prosa: bool) -> str:
    return apply_privacy_filter(testo, PrivacyOptions(prosa=prosa))[0]


# Il nome di battesimo davanti fa da prova, come per qualunque cognome che
# gli elenchi non conoscono.
@PROSA
@pytest.mark.parametrize(
    "testo",
    [
        "Walter Di Salvo ha firmato il contratto.",
        "Antonio Di Salvatore ha firmato il contratto.",
        "Marco Di Pietro ha firmato il contratto.",
        "Giuseppe Lo Bianco ha firmato il contratto.",
        "Luca De Luca ha firmato il contratto.",
        "Mario D'Amico ha firmato il contratto.",
        "Chiara Dell'Aquila ha firmato il contratto.",
    ],
)
def test_nome_piu_cognome_composto(testo: str, prosa: bool) -> None:
    fuori = redigi(testo, prosa)
    assert "{{NAME_1}}" in fuori
    # Il controllo che conta davvero: non deve restare **niente** del nome.
    # Senza questa riga passerebbe anche una redazione a meta', che e'
    # precisamente il difetto che questo banco esiste per impedire.
    for pezzo in testo.split(" ha firmato")[0].split():
        assert pezzo not in fuori


# L'ordine burocratico — cognome prima, nome dopo — e' quello dei moduli.
@PROSA
def test_cognome_composto_prima_del_nome(prosa: bool) -> None:
    fuori = redigi("Di Salvo Walter", prosa)
    assert fuori == "{{NAME_1}}"


@PROSA
def test_due_persone_restano_due(prosa: bool) -> None:
    fuori = redigi("Antonio Di Salvatore e Marco Di Pietro", prosa)
    assert fuori == "{{NAME_1}} e {{NAME_2}}"


# La forma incollata negli elenchi (`disalvo`, `damico`) rende il composto
# una prova piena da sola: qui non c'e' nessun nome di battesimo a reggerlo.
@PROSA
def test_composto_noto_senza_nome_di_battesimo(prosa: bool) -> None:
    fuori = redigi("Il cliente Di Salvo ha aperto un conto", prosa)
    assert "Di Salvo" not in fuori
    assert "{{NAME_1}}" in fuori


class TestDopoUnTitoloProfessionale:
    """Il posto dove il difetto faceva più male: usciva **mezzo nome**.

    La regola del titolo pota la coda finché trova parole comuni, per non
    inghiottire la frase che segue. Su un cognome composto la potatura lo
    smontava un pezzo per volta — prima «Salvo» (parola comune), poi «Di»
    (preposizione) — e restava `il sig. {{NAME_1}} Di Salvo`: il documento
    sembra trattato e il cognome che identifica la persona è ancora lì.
    """

    @PROSA
    @pytest.mark.parametrize(
        "testo,resto",
        [
            # I primi tre finiscono con una parola comune — «salvo»,
            # «natale», «vecchio» — ed è quello che innesca la potatura.
            # Senza casi così il banco resterebbe verde anche col difetto
            # rimesso: gli altri passano perché la coda non è comune.
            ("Il sig. Walter Di Salvo", ""),
            ("Il sig. Marco Di Natale", ""),
            ("Il sig. Paolo Del Vecchio", ""),
            ("Il dott. Marco Di Pietro ha risposto", " ha risposto"),
            ("Il sig. Luca De Luca", ""),
            ("Il rag. Mario D'Amico", ""),
            ("La dott.ssa Chiara Lo Bianco", ""),
        ],
    )
    def test_il_titolo_non_lascia_indietro_il_cognome(
        self, testo: str, resto: str, prosa: bool
    ) -> None:
        fuori = redigi(testo, prosa)
        assert fuori.endswith("{{NAME_1}}" + resto)

    @PROSA
    def test_la_potatura_di_coda_continua_a_funzionare(self, prosa: bool) -> None:
        # Il motivo per cui la potatura esiste: senza, il titolo si mangia
        # la frase che segue. Allentandola per i composti non deve
        # allentarsi per tutto il resto.
        assert redigi("il dott. Marco Conti", prosa) == "il dott. {{NAME_1}}"


class TestNonDeveRompereQuelloCheFunzionava:
    """La particella e' una preposizione: allentare qui costa caro.

    Ogni caso e' una forma in cui `di`, `del`, `della` compaiono fra due
    maiuscole **senza** essere un cognome. Se uno di questi sparisce, la
    regola e' troppo larga e va stretta, non spiegata.
    """

    @PROSA
    @pytest.mark.parametrize(
        "testo",
        [
            "Il Comune di Roma ha deliberato",
            "La Camera di Commercio di Milano",
            "Ministero della Giustizia",
            "Corte di Cassazione",
            "Banca di Credito Cooperativo",
            "Universita' degli Studi di Padova",
            "Consiglio dei Ministri",
        ],
    )
    def test_enti_e_locuzioni_restano(self, testo: str, prosa: bool) -> None:
        assert redigi(testo, prosa) == testo

    @PROSA
    def test_saluto_non_diventa_persona(self, prosa: bool) -> None:
        assert redigi("Gentile Cliente", prosa) == "Gentile Cliente"


def test_la_particella_non_vale_come_riscontro() -> None:
    """«di» non e' il nome di nessuno.

    Su modulo servono due riscontri. Se la particella ne valesse uno,
    «Di Bella» — dove `dibella` negli elenchi non c'e' e `bella` e' una
    parola — passerebbe con una prova sola travestita da due. Il banco
    guarda il caso peggiore: due parole comuni legate da una particella.
    """
    assert redigi("Della Bella", prosa=False) == "Della Bella"
