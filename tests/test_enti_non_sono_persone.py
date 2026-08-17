# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Un ente pubblico non e' un dato personale, e va lasciato dov'e'.

Da dove viene questo test
-------------------------

«Tribunale di Roma» e' un ente pubblico: resta nel testo come contesto, e
toglierlo non protegge nessuno. Da noi la scelta non era mai stata presa
esplicitamente, quindi e' stata **misurata** invece che dichiarata -- ed e'
emerso che meta' della classe era gia' protetta e meta' no.

Il difetto che ha trovato
-------------------------

`_ENTITY_WORDS` conteneva `ospedale`, `istituto`, `fondazione`, e quelli
funzionavano. Non conteneva `policlinico` ne' `teatro`, e li' l'ente spariva
intero:

    Policlinico Agostino Gemelli, Universita' Cattolica  ->  {{NAME}}, Universita' Cattolica
    Teatro Giuseppe Verdi, Trieste                       ->  {{NAME}}, Trieste

Non e' una fuga -- e' il contrario -- ma e' il falso positivo peggiore che
questo prodotto possa fare: la frase perde il soggetto, e chi legge il
documento redatto non sa nemmeno di quale ospedale si parlasse. E' il tipo
di danno che fa disattivare lo strumento.

Perche' il test ha TRE meta', e la terza e' quella che conta
------------------------------------------------------------

Una parola d'ente **scherma l'intera sequenza maiuscola**. Un test che
provasse solo che gli enti restano interi si accontenterebbe della
direzione comoda: allungando `_ENTITY_WORDS` all'infinito passerebbe
sempre, mentre il motore smette via via di proteggere le persone.

La seconda meta' -- persone accanto a un ente, separate da punteggiatura o
da un ruolo -- e' stata **provata e non basta**: il trattino e l'appellativo
spezzano gia' la sequenza, quindi quei casi restano verdi anche mettendo
`studio` nell'elenco. Sono un presidio contro un'altra regressione, non
contro questa.

La terza e' il vincolo vero, e vale perche' e' stata verificata al
contrario: lo schermo scatta solo nella forma **adiacente**, e li' morde
davvero. Con `studio` in `_ENTITY_WORDS`, «Studio Mario Rossi ha trasmesso
la fattura» smette di essere redatto. Quindi l'elenco `TENUTE_FUORI` e'
l'unica parte di questo file che si accorge di un'aggiunta sbagliata.

Il prezzo, che va detto
-----------------------

Lo stesso meccanismo vale per le parole aggiunte: «Clinica Mario Rossi» ora
e' schermato per intero. Non e' un difetto introdotto qui -- «Ufficio Mario
Rossi» e «Fondazione Mario Rossi» si comportano cosi' da sempre -- ma e' il
prezzo di ogni riga dell'elenco, e in quella forma la lettura «ente» e'
quella giusta quasi sempre.
"""

from __future__ import annotations

import pytest

from mr_rao.privacy import PrivacyOptions, apply_privacy_filter, senza_numeri


def redigi(testo: str) -> str:
    # `senza_numeri`: le asserzioni di questo file dicono «l'ente e' intatto»
    # e «la persona e' sparita», non come sono numerati i segnaposto.
    return senza_numeri(apply_privacy_filter(testo, PrivacyOptions())[0])


# Enti e luoghi intitolati a una persona. Il nome proprio c'e' -- ed e'
# proprio il punto: non e' di nessuno che sia vivo e identificabile.
ENTI = [
    "Policlinico Agostino Gemelli, Universita' Cattolica del Sacro Cuore.",
    "Teatro Giuseppe Verdi, Trieste.",
    "Volo in partenza dall'Aeroporto Leonardo da Vinci di Fiumicino.",
    "Iscritto al Liceo Classico Giuseppe Parini di Milano.",
    "Ricoverato presso il Policlinico Umberto I di Roma.",
    "Conservatorio Giuseppe Verdi e Accademia Carrara.",
    "Caserma Salvo D'Acquisto, Comando Provinciale di Roma.",
    "Biblioteca Nazionale Vittorio Emanuele III.",
    "Basilica di San Giovanni in Laterano.",
    "Ricoverato presso l'Ospedale San Raffaele di Milano.",
    "Istituto Comprensivo Alessandro Manzoni, plesso di Lecco.",
    "Istituto Nazionale Tumori Fondazione Pascale, Napoli.",
    "Il Tribunale di Roma ha depositato la sentenza.",
    "Il Comune di Torino ha pubblicato il bando.",
    "Istanza all'Agenzia delle Entrate, Direzione Provinciale di Bari.",
    "Nota del Ministero dell'Interno.",
    "Verbale della Questura di Napoli e della Prefettura di Salerno.",
    "Il Consiglio di Stato ha confermato la decisione del TAR Lazio.",
    "Universita' degli Studi di Padova, Dipartimento di Ingegneria.",
]

# La meta' che tiene onesta l'altra: la persona sta accanto alla parola
# d'ente, e deve sparire lo stesso.
PERSONE = [
    "Policlinico Gemelli - referente Dott. Mario Rossi.",
    "Teatro Verdi, direttore artistico: Giuseppe Bianchi.",
    "Il paziente Andrea Ferrari e' stato dimesso dalla Clinica Santa Rita.",
    "Scuola Media Dante Alighieri, insegnante Laura Colombo.",
    "Comando dei Vigili del Fuoco, ispettore Marco Esposito.",
    "Accademia di Brera, iscritto: Francesco Romano.",
    "Ospedale San Raffaele, primario Dott. Giovanni Ricci.",
    "Istituto Comprensivo Manzoni - genitore: Paolo Greco.",
]


@pytest.mark.parametrize("frase", ENTI)
def test_un_ente_resta_dov_e(frase: str) -> None:
    assert redigi(frase) == frase, (
        "un ente pubblico non e' un dato personale: toglierlo non protegge "
        "nessuno e rende il documento illeggibile"
    )


@pytest.mark.parametrize("frase", PERSONE)
def test_una_persona_accanto_a_un_ente_resta_protetta(frase: str) -> None:
    assert "{{NAME}}" in redigi(frase), (
        "un ruolo o una punteggiatura fra l'ente e la persona spezzano la "
        "sequenza maiuscola, e la persona deve restare protetta"
    )


# Parole che **non** devono entrare in `_ENTITY_WORDS`, nella forma in cui
# lo schermo scatta davvero: parola ed ente attaccati, senza niente in
# mezzo. Ognuna nomina un soggetto che in un documento italiano e' quasi
# sempre una persona fisica -- un professionista, un incaricato -- cioe'
# esattamente il dato da proteggere.
TENUTE_FUORI = [
    ("studio", "Studio Mario Rossi ha trasmesso la fattura."),
    ("studio", "Lo Studio Giulia Bianchi ha depositato il ricorso."),
    ("perito", "Il perito Marco Neri ha firmato la relazione."),
    ("titolare", "Titolare Anna Ferrari, partita IVA attiva dal 2019."),
    ("geometra", "Geometra Luca Moretti, direttore dei lavori."),
    ("notaio", "Notaio Chiara Galli, repertorio n. 4471."),
]


@pytest.mark.parametrize("parola,frase", TENUTE_FUORI)
def test_le_parole_tenute_fuori_non_devono_schermare(parola: str, frase: str) -> None:
    """La guardia contro un'aggiunta sbagliata a `_ENTITY_WORDS`.

    Verificata al contrario prima di scriverla: mettendo `studio`
    nell'elenco, la prima frase smette di essere redatta. E' l'unico test
    del file che si accorge dell'errore che questo file esiste per evitare.
    """
    assert "{{NAME}}" in redigi(frase), (
        f"«{parola}» sembra essere finita in `_ENTITY_WORDS`: da quel momento "
        f"scherma l'intera sequenza, e un professionista scritto in questa "
        f"forma non viene piu' protetto"
    )


def test_l_appellativo_resta_e_il_nome_no() -> None:
    """`Dott.` e `Avv.` sono qualifiche, non identificatori.

    Da noi era gia' cosi', e vale la pena scriverlo: e' il genere di
    comportamento che si perde riscrivendo il riconoscitore senza sapere
    che era voluto.
    """
    fuori = redigi("Il Dott. Bianchi e l'Avv. Rossi erano presenti in udienza.")
    assert "Dott." in fuori and "Avv." in fuori
    assert "Bianchi" not in fuori and "Rossi" not in fuori
