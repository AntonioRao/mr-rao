# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
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


class TestElencoDeiComposti:
    """I composti scritti nell'elenco, e cosa comprano davvero.

    **Non comprano il composto da solo**, ed è una rinuncia decisa dopo
    averla misurata. Una prima stesura sostituiva «il fascicolo Di Maio»,
    e una revisione avversariale su 357 casi ha mostrato il prezzo: 96
    falsi positivi, «Sala Della Vittoria» e «Rocca Di Papa» compresi — che
    hanno *esattamente la stessa struttura* di «Di Maio». Senza qualcosa
    che dica «qui c'è una persona», un cognome composto e un toponimo sono
    indistinguibili, e nessuna taratura può separarli.

    Gli elenchi servono dove quel qualcosa c'è: l'ordine burocratico con il
    nome di battesimo dall'altra parte, la potatura dopo un titolo, e le
    regole di contesto (ruolo, codice fiscale accanto, saluto).
    """

    @pytest.mark.parametrize(
        "testo",
        [
            "Il fascicolo Di Maio è stato aperto",
            "Il fascicolo La Rocca è stato aperto",
            "Sala Della Vittoria",
            "Rocca Di Papa",
            "Castel Del Monte",
            "Vacanze Di Natale",
            "Trattoria La Vecchia Osteria",
        ],
    )
    def test_il_composto_da_solo_non_basta(self, testo: str) -> None:
        # Le prime due sono cognomi veri, le altre no, e il motore non ha
        # modo di dirlo: la forma è la stessa. Restano tutte.
        assert redigi(testo, prosa=True) == testo
        assert redigi(testo, prosa=False) == testo

    @pytest.mark.parametrize(
        "testo",
        [
            "Il cliente Di Salvo ha aperto un conto",
            "Il sig. Di Maio ha firmato",
        ],
    )
    def test_ma_con_un_contesto_che_dichiara_la_persona_si(self, testo: str) -> None:
        # Qui a dire «persona» è il ruolo o il titolo, non la forma delle
        # parole — ed è lì che l'elenco dei composti lavora.
        assert "{{NAME_1}}" in redigi(testo, prosa=True)

    def test_nessun_composto_e_anche_una_parola_comune(self) -> None:
        # Una collisione qui non darebbe un errore: farebbe sparire una
        # parola italiana da tutti i documenti, in silenzio. «deriso» era
        # nella prima stesura ed è stato tolto per questo.
        from mr_rao.it_names import COMMON_CAPITALIZED, _SURNAMES_COMPOSTI

        composti = _SURNAMES_COMPOSTI.split()
        assert len(composti) > 100, "l'elenco si è svuotato: il banco non prova più niente"
        assert [c for c in composti if c in COMMON_CAPITALIZED] == []

    def test_i_composti_sono_scritti_incollati(self) -> None:
        # Se qualcuno li scrivesse con lo spazio, `split()` li spezzerebbe in
        # due parole e l'elenco si riempirebbe di **particelle**: `di`
        # diventerebbe un cognome, e ogni «Comune di Roma» una persona.
        #
        # Il controllo non guarda la lunghezza — «dileo», «dimeo», «demeo»
        # sono composti veri di cinque lettere, e una soglia li avrebbe
        # bocciati — ma la forma: nessuna voce può *essere* una particella,
        # e ognuna deve cominciare con una di quelle.
        from mr_rao.privacy import _PARTICELLE_COGNOME
        from mr_rao.it_names import _SURNAMES_COMPOSTI

        composti = _SURNAMES_COMPOSTI.split()
        assert [c for c in composti if c in _PARTICELLE_COGNOME] == []
        senza_particella = [
            c for c in composti
            if not any(c.startswith(p) and len(c) > len(p) for p in _PARTICELLE_COGNOME)
        ]
        assert senza_particella == []


def test_la_particella_non_vale_come_riscontro() -> None:
    """«di» non e' il nome di nessuno.

    Su modulo servono due riscontri. Se la particella ne valesse uno,
    «Di Bella» — dove `dibella` negli elenchi non c'e' e `bella` e' una
    parola — passerebbe con una prova sola travestita da due. Il banco
    guarda il caso peggiore: due parole comuni legate da una particella.
    """
    assert redigi("Della Bella", prosa=False) == "Della Bella"


class TestCompostoAccantoAUnaEmail:
    """«Di Salvo Andrea <a.disalvo@...>» usciva come «Di Salvo {{NAME_1}}».

    **Trovato su documenti veri**, non su un banco: un'intestazione di posta
    con decine di destinatari scritti «Cognome Nome». La regola che riconosce
    il nome accanto a un indirizzo pota le parole comuni in testa, una per
    una — e `di` e `salvo` sono tutte e due parole italiane comunissime, una
    preposizione e un avverbio. Restava «Andrea».

    È **mezzo nome**, cioè il modo peggiore di sbagliare: il documento sembra
    trattato e il cognome che identifica la persona è ancora lì. È lo stesso
    difetto per cui `_cognome_appoggiato` era stata scritta, rientrato da
    un'altra porta — quella dell'indirizzo di posta.
    """

    @PROSA
    @pytest.mark.parametrize(
        "testo",
        [
            "Di Salvo Andrea <andrea.disalvo@esempio.it>",
            "Lo Bianco Giuseppe <g.lobianco@esempio.it>",
            "De Luca Anna <a.deluca@esempio.it>",
            "Del Vecchio Marco <m.delvecchio@esempio.it>",
            "La Rocca Silvia <s.larocca@esempio.it>",
        ],
    )
    def test_il_composto_non_resta_indietro(self, testo: str, prosa: bool) -> None:
        fuori = redigi(testo, prosa)
        assert "{{NAME" in fuori
        # Il punto non è che *qualcosa* sia sparito: è che non resti in
        # chiaro la parte che identifica. Senza questa riga il banco
        # passerebbe anche con mezzo nome sostituito.
        for pezzo in testo.split(" <")[0].split():
            assert pezzo not in fuori, f"{pezzo} è rimasto in chiaro"

    @PROSA
    @pytest.mark.parametrize(
        "testo,resta",
        [
            # La prova è la **forma incollata**: senza, qualunque parola
            # comune davanti a un indirizzo diventerebbe un cognome.
            ("il pagamento e' salvo buon fine <info@esempio.it>", "salvo buon fine"),
            ("Contatta mario@esempio.it per il resto", "Contatta"),
            ("Scrivi a supporto@esempio.it", "Scrivi a"),
        ],
    )
    def test_le_parole_comuni_restano_parole(self, testo: str, resta: str, prosa: bool) -> None:
        assert resta in redigi(testo, prosa)
