"""P9.4 — le intitolazioni non sono persone, e la coppia passava lo stesso.

Perche' esiste
--------------

Il riconoscitore delle coppie non sa che «Giuseppe Meazza» e' uno stadio: due
parole maiuscole adiacenti, tutte e due negli elenchi, e la sequenza sparisce
portandosi via il soggetto della frase. Lo scudo che c'era gia' —
`_ENTITY_WORDS` dentro la sequenza — vedeva solo la parola d'ente **scritta
maiuscola e dentro la sequenza**: «Ospedale Giovanni Paolo II» era schermato,
«l'ospedale Giovanni Paolo II» no. In prosa italiana la forma normale e' la
seconda, ed e' quella che passava.

E' una voce a se' rispetto a P9.2: la' il rischio era il **nome isolato** e si
e' chiuso con la guardia sul contesto; qui il problema e' la **coppia**, che
passa da un'altra strada e ha una soglia sua.

Come e' fatto questo banco
--------------------------

Ogni classe di intitolazione ha il suo **contrappeso**: la stessa parola
d'edificio in una frase dove la persona c'e' davvero. Senza, una regola che
schermasse mezzo documento passerebbe questo file tutta verde — ed e' il modo
in cui una guardia diventa un buco.
"""
import pytest

from mr_rao.privacy import PrivacyOptions, apply_privacy_filter

PROSA = pytest.mark.parametrize("prosa", [True, False], ids=["prosa", "modulo"])


def redigi(testo: str, prosa: bool) -> str:
    return apply_privacy_filter(testo, PrivacyOptions(prosa=prosa))[0]


# --- Cio' che NON dev'essere sostituito -----------------------------------
@PROSA
@pytest.mark.parametrize(
    "testo",
    [
        # La parola d'edificio minuscola, subito davanti.
        "Si gioca allo stadio Giuseppe Meazza domenica.",
        "Ha vinto il premio Italo Calvino nel 2024.",
        "Si e' svolto il torneo Marco Pantani.",
        "Passeggiata al parco Giovanni Falcone.",
        "Concerto allo stadio Renzo Barbera.",
        "Visita a villa Adriana Rossi.",
        # Parole d'ente che c'erano gia', ma solo in maiuscolo e dentro la
        # sequenza: in prosa si scrivono cosi'.
        "Il figlio frequenta il liceo Alessandro Manzoni.",
        "Il paziente e' stato trasferito all'ospedale Giovanni Paolo II.",
        "Lo spettacolo e' al teatro Carlo Felice.",
        "Il bando e' della fondazione Cesare Pavese.",
        # Fra la parola d'edificio e il nome c'e' un'altra parola maiuscola.
        "Il ponte Vittorio Emanuele II e' chiuso al traffico.",
        "La Basilica di San Marco e' a Venezia.",
        # ...oppure un aggettivo che qualifica l'edificio.
        "Consultare la biblioteca nazionale Vittorio Emanuele III.",
        "Scuola primaria Cristoforo Colombo, classe terza.",
        "Il centro sportivo Giacinto Facchetti apre alle 8.",
        # La parola che decide sta dentro la sequenza, ed e' la prima.
        "Residente a San Giovanni Rotondo.",
        "Il paese si chiama Sant'Antonio Abate.",
        "Il cliente e' la San Giorgio Costruzioni.",
    ],
)
def test_intitolazione_non_e_una_persona(testo: str, prosa: bool) -> None:
    assert "{{NAME" not in redigi(testo, prosa), testo


# --- Il contrappeso: la stessa parola, ma la persona c'e' -----------------
#
# Questi casi valgono piu' di quelli sopra. Una guardia che scherma troppo
# passerebbe tutta la prima lista e sarebbe un difetto peggiore di quello che
# corregge: li' si perde il soggetto di una frase, qui si lascia in chiaro il
# nome di una persona vera.
@pytest.mark.parametrize(
    "testo",
    [
        # Fra la parola d'edificio e il nome c'e' un verbo: non e' piu'
        # un'intitolazione, e' una frase.
        "Il premio e' stato consegnato a Mario Rossi.",
        "Allo stadio ho incontrato Mario Rossi.",
        "La villa e' stata venduta a Mario Rossi.",
        # La punteggiatura spezza l'adiacenza: e' un'etichetta di modulo
        # seguita da un valore, non il nome di un edificio.
        "Residenza: Mario Rossi",
        "Zona 3 - referente Mario Rossi",
        "Casa di riposo, ospite Mario Rossi.",
        # La parola d'edificio in coda non scherma niente: scherma solo in
        # testa. Altrimenti «Villa» come cognome coprirebbe il nome davanti.
        "Il documento e' firmato da Mario Villa.",
    ],
)
def test_la_persona_resta_protetta(testo: str) -> None:
    assert "{{NAME" in redigi(testo, prosa=True), testo


# --- La prova che la guardia sia lei a decidere ---------------------------
#
# «Verificato» senza questo vorrebbe dire poco: i casi sopra potrebbero
# restare intatti per un motivo qualunque -- una parola fuori dagli elenchi,
# una soglia non raggiunta -- e il banco sarebbe verde su un motore che la
# regola non ce l'ha. Qui si cambia **solo** la parola che decide e si guarda
# se l'esito si ribalta.
@pytest.mark.parametrize(
    "con_edificio,senza",
    [
        ("Si gioca allo stadio Giuseppe Meazza domenica.",
         "Si gioca insieme a Giuseppe Meazza domenica."),
        ("Ha vinto il premio Italo Calvino nel 2024.",
         "Ha vinto contro Italo Calvino nel 2024."),
        ("Il figlio frequenta il liceo Alessandro Manzoni.",
         "Il figlio frequenta con Alessandro Manzoni."),
    ],
)
def test_e_la_parola_davanti_a_decidere(con_edificio: str, senza: str) -> None:
    assert "{{NAME" not in redigi(con_edificio, prosa=True)
    assert "{{NAME" in redigi(senza, prosa=True)


# --- Le sigle: «IC», «I.C.S.», «SMS» --------------------------------------
#
# **Le ha dettate un documento vero**: un elenco pubblico di posti di
# sostegno, dove il motore faceva 604 sostituzioni senza che ci fosse un solo
# dato personale, e i ventun nomi distinti erano tutti nomi di **scuole**.
# `istituto` stava gia' fra le parole d'ente; la sua sigla no.
@pytest.mark.parametrize(
    "testo",
    [
        "IC MAZZARRONE - LICODIA",
        "IC Giovanni Verga - Maniace",
        "I.C. Giovanni XXIII",
        "I.C.S. Leonardo Da Vinci II- Belpasso",
        "SC.MEDIA Enrico Fermi",
        "SMS Luigi Pirandello",
        # Fra la sigla e il nome un'altra maiuscola: e' la stessa
        # intitolazione, non un'altra frase.
        "IC MADRE Teresa di Calcutta",
    ],
)
def test_la_sigla_di_scuola_scherma(testo: str) -> None:
    assert "{{NAME" not in redigi(testo, prosa=True), testo


@pytest.mark.parametrize(
    "testo",
    [
        # Minuscolo: `sms` e' un messaggio, non una scuola media. La sigla
        # vale **solo** scritta tutta maiuscola.
        "ho mandato un sms a Mario Rossi",
        # Fra la sigla e il nome c'e' una congiunzione: sono due cose diverse
        # della stessa frase, non un'intitolazione.
        "Il referente ASL e' Mario Rossi",
        "La ASL ha convocato Mario Rossi",
        # Una sigla che in elenco non c'e' non scherma niente.
        "Gentile SIG Mario Rossi",
        # Le iniziali puntate di una persona non sono una sigla d'ente, ed e'
        # la ragione per cui le sigle di due lettere puntate restano fuori.
        "A.R. Mario Rossi ha firmato",
        # La punteggiatura spezza comunque.
        "IC di Belpasso, referente Mario Rossi",
    ],
)
def test_la_sigla_non_copre_le_persone(testo: str) -> None:
    assert "{{NAME" in redigi(testo, prosa=True), testo


# --- Il prezzo, scritto perche' non torni di sorpresa ---------------------
def test_il_prezzo_dichiarato() -> None:
    """«presso casa Mario Rossi» non viene piu' sostituito.

    `casa` e' nell'elenco, l'adiacenza e' pulita, e nessuna regola puo'
    distinguere quella forma da «casa Giuseppe Verdi». E' la stessa rinuncia
    gia' accettata per «Fondazione Mario Rossi» nella 1.20, con in piu' il
    fatto che qui la parola e' minuscola, cioe' un nome comune usato per
    quello che e'. Se un giorno questo test fallisce, qualcuno ha cambiato la
    regola: che sia una scelta, non una sorpresa.
    """
    assert "{{NAME" not in redigi("Ci vediamo presso casa Mario Rossi.", prosa=True)
