"""La terza manopola sul resto del pacchetto italiano.

Cambiare il **valore** invece della frase aveva gia' trovato due difetti
(codice fiscale con omocodia, telefono con la barra) e aveva assolto i venti
riconoscitori anglosassoni. Restava fuori una parte del pacchetto italiano:
i nomi in forme diverse dalla coppia semplice, gli indirizzi come si
scrivono davvero, i codici fiscali che non sono quelli dell'esempio.

Ne sono usciti due difetti veri, e nessuno dei due era una forma esotica.

**«Giulia» non era un nome.** Stava nell'elenco delle parole comuni per un
motivo solo: fa parte di «Friuli Venezia **Giulia**». Stessa storia per
«Emilia». Sono due dei nomi di battesimo piu' diffusi in Italia, e il
risultato era che «la dott.ssa Giulia Conti» usciva dal documento intera.

**Il cognome sopravviveva al nome.** Quarantadue cognomi degli elenchi sono
anche parole comuni — Conti, Villa, Carta, Porta, Valle, Napoli, Ferrara,
Messina — e dopo un titolo professionale la potatura di coda li buttava via
uno per uno: «il dott. Marco Conti» diventava «il dott. {{NAME}} Conti».
Il nome tolto, il cognome lasciato: il modo peggiore di sbagliare, perche'
il documento sembra trattato.

**E gli indirizzi con l'iniziale puntata non esistevano.** «Via A. Volta 5»,
«piazza G. Verdi 1», «via C. Colombo 44»: il corpo dell'indirizzo non poteva
nemmeno cominciare, perche' pretendeva una minuscola o tre maiuscole e «A.»
non ha ne' l'una ne' le altre. Misurato sui dodici numeri di Gazzetta
Ufficiale del corpus a verita' zero: **quarantuno indirizzi veri** lasciati
in chiaro, fra cui la sede del Ministero dell'ambiente e quella
dell'Istituto Poligrafico stampata su ogni fascicolo.

Un difetto era invece il banco, e vale la pena tenerne memoria: «Via S. dei
Mille» non e' un indirizzo — l'iniziale sta al posto del nome di battesimo,
e «dei Mille» non ne ha uno. Ventidue casi su duecento, e il motore aveva
ragione. E' lo stesso errore dei SIN canadesi che cominciavano per zero.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from mr_rao.privacy import PrivacyOptions, apply_privacy_filter

RADICE = Path(__file__).resolve().parents[1]
for percorso in (RADICE, RADICE / "scripts"):
    if str(percorso) not in sys.path:
        sys.path.insert(0, str(percorso))

from bench_varieta_it import campioni, prova  # noqa: E402

PER_TIPO = 40


@pytest.fixture(scope="module")
def dati():
    return campioni()


def _redigi(testo: str, **kw) -> str:
    return apply_privacy_filter(testo, PrivacyOptions(**kw))[0]


def test_ogni_forma_regge_la_varieta_dei_valori(dati):
    """Con l'etichetta davanti, **tutti** i valori validi, non la maggioranza.

    Un 95% qui non e' «quasi tutto»: e' un valore su venti che esce in
    chiaro, e la ragione sara' una forma particolare che nessuno ha
    guardato — che e' esattamente com'erano nascosti i due difetti sopra.
    """
    difetti = {}
    for tipo, (valori, cornice, opzioni) in dati.items():
        campione = valori[:PER_TIPO]
        redatti, _, persi = prova(campione, cornice, opzioni)
        if redatti < len(campione):
            difetti[tipo] = (redatti, len(campione), persi)
    assert not difetti, (
        "queste forme perdono valori validi del proprio tipo:\n  "
        + "\n  ".join(f"{t}: {r}/{n}, esempi persi: {p}"
                      for t, (r, n, p) in difetti.items())
    )


# --- i nomi ------------------------------------------------------------------

@pytest.mark.parametrize("testo", [
    "la dott.ssa Giulia Conti ha firmato l'atto",
    "il dott. Marco Conti ha firmato l'atto",
    "l'avv. Chiara Villa ha depositato",
    "il geom. Luca Ferrara ha rilevato",
    "la sig.ra Anna Porta ha ritirato",
])
def test_dopo_un_titolo_non_resta_il_cognome(testo):
    """Il cognome e' il dato che identifica: lasciarlo indietro e' peggio che
    non aver fatto niente, perche' il documento sembra trattato."""
    fuori = _redigi(testo)
    assert "{{NAME}}" in fuori
    for parola in ("Conti", "Villa", "Ferrara", "Porta"):
        assert parola not in fuori, f"cognome rimasto in {fuori!r}"


@pytest.mark.parametrize("testo,atteso", [
    ("la Regione Emilia Romagna ha deliberato", "Emilia Romagna"),
    ("il Friuli Venezia Giulia e la Emilia Romagna", "Venezia Giulia"),
    ("Emilia Romagna, Toscana e Liguria", "Emilia Romagna"),
])
def test_le_regioni_restano_regioni(testo, atteso):
    """La controprova dell'allentamento su «Giulia» ed «Emilia».

    Se questo test non ci fosse, il modo piu' semplice di far passare quello
    sopra sarebbe togliere le due parole dall'elenco — e far sparire mezza
    Italia amministrativa dai documenti. E' il vicino a decidere, non la
    parola da sola.
    """
    assert atteso in _redigi(testo)


def test_il_nome_di_regione_non_protegge_la_persona():
    """...e nemmeno il contrario: «Emilia» accanto a un cognome e' una
    persona, e la locuzione geografica non c'entra."""
    assert "{{NAME}}" in _redigi("la sig.ra Emilia Bianchi ha firmato")
    assert "{{NAME}}" in _redigi("Cordiali saluti,\nGiulia Conti")


# --- gli indirizzi -----------------------------------------------------------

@pytest.mark.parametrize("testo", [
    "residente in Via A. Volta 5, 20100 Milano",
    "con sede in piazza G. Verdi, 1 - 00198 Roma",
    "presso via C. Colombo 44 - Roma",
    "recapito in viale L. Bodio n. 37/B - 20158 Milano",
    "domiciliato in P.le Loreto 3, 20100 Milano",
    "domiciliato in L.go Augusto 7, 20122 Milano",
    "domiciliato in V.lo Stretto 2, 90133 Palermo",
    "domiciliato in B.go Pinti 14, 50121 Firenze",
])
def test_indirizzi_nelle_forme_che_si_scrivono_davvero(testo):
    assert "{{ADDRESS}}" in _redigi(testo), testo


def test_il_civico_non_morde_la_parola_dopo():
    """«via C. Colombo 44 - Roma»: il suffisso del civico («12/A», «7-bis»)
    prendeva «- Rom» e lasciava indietro una «a» orfana."""
    fuori = _redigi("sede in via C. Colombo 44 - Roma")
    assert "{{ADDRESS}}" in fuori
    assert "Rom" not in fuori.replace("Roma", "")


@pytest.mark.parametrize("testo", [
    "trasmesso via PEC, 30 giorni prima della scadenza",
    "il file arriva via FTP, 12 volte al giorno",
    "notificato in via amministrativa, 15 giorni dopo",
])
def test_la_prova_che_questo_riconoscitore_puo_dire_di_no(testo):
    """La controprova dell'allentamento sugli indirizzi.

    In italiano «via» vuol dire anche «tramite», ed e' la ragione per cui
    esiste l'elenco delle parole-trappola. Ammettere l'iniziale puntata non
    doveva aprire una porta laterale a quell'elenco: se questo test passasse
    da solo, vorrebbe dire che il riconoscitore ha smesso di guardare la
    parola e guarda solo la forma.
    """
    assert "{{ADDRESS}}" not in _redigi(testo)


# --- il codice fiscale, per meta' della popolazione --------------------------

def test_codice_fiscale_femminile_e_di_chi_e_nato_all_estero():
    """Le donne hanno il giorno di nascita aumentato di 40; chi e' nato
    all'estero ha un codice comune che inizia per Z. Non sono varianti
    rare: sono meta' della popolazione e una fetta grossa dell'altra."""
    for cf in ("RSOMRA85T55Z404A", "BNCLNE90A41H501V"):
        fuori = _redigi(f"codice fiscale {cf}")
        assert "{{CODICE_FISCALE}}" in fuori, cf


def test_sull_omocodia_e_l_aritmetica_a_decidere():
    """La prova che questo riconoscitore puo' dire di no.

    Sul codice fiscale **normale** il carattere di controllo non rifiuta,
    segnala: la forma a sedici caratteri con quell'alternanza di lettere e
    cifre non capita per caso, e il documento e' piu' al sicuro cosi'.
    Sull'**omocodia** no: li' il pattern e' molto piu' largo — ammette
    lettere dove ci sarebbero cifre — e quella larghezza va pagata da un
    conto che possa dire di no.

    Delle ventisei lettere solo due passano: quella giusta, e la `B`, che
    lo strato di correzione OCR trasforma in `8` ottenendo un codice
    valido. Ventiquattro rifiuti su ventisei sono il conto che lavora.
    """
    base = "RSOMRA85T55Z4L4"          # una cifra sostituita dalla lettera L
    respinti = [c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                if base + c in _redigi(f"codice fiscale {base}{c}")]
    assert "{{CODICE_FISCALE}}" in _redigi(f"codice fiscale {base}L")
    assert len(respinti) >= 23, (
        f"solo {len(respinti)}/26 caratteri di controllo respinti: "
        "il riconoscitore sta guardando la forma, non il conto"
    )
