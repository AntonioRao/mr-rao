# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Il banco a due corpora, in inglese.

Stessa disciplina dell'italiano: una mail dove tutto deve sparire, e un
documento amministrativo dove **non deve sparire niente**. Il secondo conta
piu' del primo, perche' e' l'unico numero che non si puo' migliorare
allargando i riconoscitori.

Che serva non e' un'ipotesi. Prima del pacchetto `en`, il motore italiano
applicato al documento amministrativo inglese produceva **22 sostituzioni
su un testo che non contiene un solo dato personale** -- ventuno nomi piu'
un numero di protocollo scambiato per un recapito. Lo stesso e' successo su
un modulo fiscale statunitense in bianco, scaricato dall'IRS: 22 falsi
positivi su una pagina vuota.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from aiuti import apply_privacy_filter  # segnaposto appiattiti: vedi tests/aiuti.py
from mr_rao.privacy import (
    CORE,
    EN,
    IT,
    PrivacyOptions,
)

DATI = Path(__file__).resolve().parent / "dati"
EMAIL = DATI / "corpus_en_email.txt"
ADMIN = DATI / "corpus_en_admin.txt"

SOLO_EN = PrivacyOptions(pacchetti=(CORE, EN))


def _leggi(p: Path) -> str:
    assert p.is_file(), f"manca il corpus {p}"
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Il documento che deve restare intatto
# ---------------------------------------------------------------------------


def test_il_documento_amministrativo_resta_a_zero():
    """Il criterio della fase 2. Se questo sale, il pacchetto e' peggiorato
    anche se tutti gli altri numeri sono migliorati."""
    out, rep = apply_privacy_filter(_leggi(ADMIN), SOLO_EN)
    assert rep.total == 0, f"falsi positivi: {rep.counts}"
    assert out == _leggi(ADMIN)


def test_il_corpus_amministrativo_contiene_davvero_le_trappole():
    """Un corpus annacquato tiene il test verde senza provare niente.

    Queste parole sono nomi propri inglesi comunissimi usati come parole
    comuni: sono la ragione per cui l'euristica italiana dei nomi qui
    esplode, e devono restare nel file.
    """
    testo = _leggi(ADMIN)
    for trappola in (
        "Mark", "Bill", "Grace", "May", "June", "Rose",
        "Brown", "Green", "Baker", "Price", "Young", "Church", "Sterling",
        "Baker & Price", "Church Road", "Green Lane",
        "Project Manager", "Data Protection Officer",
        "0034578921",  # dieci cifre: sembra un NHS number, e' un protocollo
        "078051120",   # nove cifre: sembra un SSN, e' un numero di lotto
    ):
        assert trappola in testo, f"il corpus ha perso la trappola {trappola!r}"


def test_le_nove_cifre_senza_contesto_non_si_toccano():
    """Il SSN non ha checksum: nove cifre nude passano il controllo
    strutturale quasi nove volte su dieci. Senza i trattini o una parola
    accanto, si lasciano stare."""
    _, rep = apply_privacy_filter("Asset register batch: 078051120", SOLO_EN)
    assert rep.total == 0


def test_il_numero_di_protocollo_non_e_un_telefono():
    """Regressione. "0034578921" veniva letto come prefisso internazionale
    00 piu' Spagna, e redatto: trovato su un documento vero."""
    out, rep = apply_privacy_filter("Protocol number: 0034578921", SOLO_EN)
    assert "{{PHONE}}" not in out
    assert rep.total == 0


def test_il_prefisso_internazionale_vero_resta_riconosciuto():
    """L'altra meta' della correzione qui sopra: il primo tentativo
    cercava il separatore nel solo corpo del numero, e faceva cadere
    "0039 3391234567", dove lo spazio sta fra prefisso e corpo."""
    out, _ = apply_privacy_filter("Tel 0039 3391234567", SOLO_EN)
    assert "{{PHONE}}" in out


# ---------------------------------------------------------------------------
# La mail dove tutto deve sparire
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "categoria,segnaposto",
    [
        ("ssn", "{{SSN}}"),
        ("itin", "{{ITIN}}"),
        ("nhs_number", "{{NHS_NUMBER}}"),
        ("routing_number", "{{ROUTING_NUMBER}}"),
        ("iban", "{{IBAN}}"),
        ("cards", "{{CARD}}"),
        ("emails", "{{EMAIL}}"),
    ],
)
def test_la_mail_perde_gli_identificativi(categoria, segnaposto):
    out, rep = apply_privacy_filter(_leggi(EMAIL), SOLO_EN)
    assert rep.counts.get(categoria), f"{categoria} non riconosciuto"
    assert segnaposto in out


@pytest.mark.parametrize(
    "residuo",
    [
        "078-05-1120",                  # SSN
        "912-70-4455",                  # ITIN
        "943 476 5919",                 # NHS number
        "021000021",                    # routing ABA
        "GB29 NWBK 6016 1331 9268 19",  # IBAN
        "4111 1111 1111 1111",          # carta
    ],
)
def test_nessun_identificativo_sopravvive_nella_mail(residuo):
    out, _ = apply_privacy_filter(_leggi(EMAIL), SOLO_EN)
    assert residuo not in out


def test_il_nino_sparisce():
    out, rep = apply_privacy_filter("His NI number is AB 12 34 56 C.", SOLO_EN)
    assert rep.counts.get("nino") == 1
    assert "{{NINO}}" in out


def test_il_nino_di_esempio_diventa_un_sospetto():
    """`QQ` e' il prefisso che gov.uk usa negli esempi **proprio perche'**
    non viene mai emesso. Rifiutarlo e' giusto; tacere no: la stessa forma
    la produce un OCR che ha storpiato le due lettere di un NINO vero."""
    out, rep = apply_privacy_filter("Old entry: QQ 12 34 56 C", SOLO_EN)
    assert "QQ 12 34 56 C" in out
    assert not rep.counts.get("nino")
    assert [s for s in rep.suspects if s["kind"] == "nino"]


# ---------------------------------------------------------------------------
# Il limite, dichiarato
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# I nomi: solo dove il testo dichiara che e' una persona
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "testo,atteso_via",
    [
        ("Dear James,", "apertura epistolare"),
        ("The client is Mr Daniel Okonkwo, aged 47.", "titolo"),
        ("Please copy in Prof. Helen Ashworth when you circulate.", "titolo"),
        ("Attn: Michael Osei in accounts", "attenzione a"),
        ("Sarah Whitfield <s.whitfield@harlow.co.uk> wrote:", "email accanto"),
        ("Kind regards,\n\nSarah Whitfield\nSenior Associate", "firma"),
    ],
)
def test_il_contesto_dichiara_la_persona(testo, atteso_via):
    out, rep = apply_privacy_filter(testo, SOLO_EN)
    assert rep.counts.get("names"), f"non riconosciuto per {atteso_via}: {out!r}"
    assert "{{NAME}}" in out


@pytest.mark.parametrize(
    "formula",
    ["Dear Sir,", "Dear Madam,", "Dear All,", "Dear Team,", "Dear Colleagues,"],
)
def test_le_formule_generiche_non_sono_nomi(formula):
    """Senza questo, ogni lettera formale comincerebbe con un falso
    positivo — ed e' la prima riga, quella che l'utente guarda."""
    out, rep = apply_privacy_filter(formula, SOLO_EN)
    assert out == formula
    assert not rep.counts.get("names")


def test_una_parola_sola_davanti_a_un_indirizzo_non_basta():
    """A differenza dell'italiano non c'e' un elenco a cui chiedere se
    quella parola e' un nome. Davanti a un indirizzo ci finisce di tutto, a
    partire dai verbi: senza questa regola «Contact» sparirebbe."""
    out, _ = apply_privacy_filter("Contact <someone@example.com> today", SOLO_EN)
    assert "Contact" in out


def test_il_limite_dichiarato_un_nome_in_mezzo_alla_frase_sopravvive():
    """**Questo test passa perche' il motore NON fa una cosa.**

    Non e' una svista, e' il divario dichiarato nella issue #1 e in #4.
    Senza titolo, senza firma e senza indirizzo accanto, non c'e' nulla nel
    testo che dica che «Grace Bellamy» e' una persona e non un'azienda o un
    luogo -- e in inglese Grace, Bellamy, Brown, Green e Baker sono tutte e
    due le cose. Prenderlo richiederebbe un modello, che e' esattamente
    cio' che questo prodotto promette di non avere.

    Se un giorno questo test diventasse rosso, prima di correggerlo
    verificare **cosa** e' cambiato: se qualcuno ha aggiunto un'euristica
    sui nomi, il documento amministrativo qui sopra e' il posto dove si
    misura il prezzo.
    """
    testo = "His partner, Grace Bellamy, can be reached at the office."
    out, rep = apply_privacy_filter(testo, SOLO_EN)
    assert out == testo
    assert not rep.counts.get("names")


def test_col_pacchetto_italiano_insieme_i_nomi_tornano():
    """I pacchetti sono cumulabili, ed e' il caso d'uso vero: lo studio
    italiano che segue il cliente inglese. Qui l'euristica italiana copre
    -- male, ma copre -- il buco dei nomi."""
    out, rep = apply_privacy_filter(
        "Dear Mr Daniel Okonkwo,", PrivacyOptions(pacchetti=(CORE, IT, EN))
    )
    assert rep.counts.get("names")
    assert "Okonkwo" not in out


# ---------------------------------------------------------------------------
# Indirizzi: il civico e' il discriminante
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "indirizzo",
    [
        "47 Baker Street, Flat 2B, London NW1 6XE",
        "118 Church Road, Reading RG1 8QW",
        "1600 Pennsylvania Avenue NW, Washington DC 20500",
        "22 Green Lane",
        "9A Sterling Way, Bolton",
    ],
)
def test_un_indirizzo_col_civico_sparisce(indirizzo):
    out, rep = apply_privacy_filter(f"Resident at {indirizzo}.", SOLO_EN)
    assert rep.counts.get("addresses"), out
    assert "{{ADDRESS}}" in out


@pytest.mark.parametrize(
    "frase",
    [
        "the loading bay on Church Road",
        "Green Lane Logistics handles the collection",
        "the Sterling Way depot in Reading",
        "The Young Street office was released",
        "The Wood Hill facility is dormant",
    ],
)
def test_un_nome_di_via_senza_civico_non_e_un_indirizzo(frase):
    """La differenza fra italiano e inglese in una riga.

    In italiano l'indirizzo **comincia** con la parola -- via, piazza,
    corso -- e riconoscerla basta. In inglese **finisce** con essa, e
    quelle stesse parole formano i nomi delle cose: depositi, uffici,
    ragioni sociali. Il civico davanti e' l'unica differenza strutturale
    affidabile. Tutte queste frasi vengono dal corpus amministrativo.
    """
    out, rep = apply_privacy_filter(frase, SOLO_EN)
    assert out == frase
    assert not rep.counts.get("addresses")


def test_il_codice_postale_da_solo_non_si_tocca():
    """Un codice postale britannico ha la forma di un codice articolo."""
    out, _ = apply_privacy_filter("Batch SW1A 1AA was rejected.", SOLO_EN)
    assert "SW1A 1AA" in out


def test_il_codice_postale_col_contesto_sparisce():
    out, rep = apply_privacy_filter("Postcode: SW1A 1AA", SOLO_EN)
    assert rep.counts.get("addresses")
    assert "{{POSTCODE}}" in out


# ---------------------------------------------------------------------------
# Australia
# ---------------------------------------------------------------------------


def test_abn_col_contesto():
    out, rep = apply_privacy_filter("ABN 51 824 753 556", SOLO_EN)
    assert rep.counts.get("abn") == 1
    assert "{{ABN}}" in out


def test_abn_senza_contesto_resta():
    """Undici cifre sono anche un totale, un codice articolo, un
    riferimento. Il mod-89 riduce il rumore, non lo azzera."""
    out, _ = apply_privacy_filter("Line total 51 824 753 556", SOLO_EN)
    assert "51 824 753 556" in out


def test_tfn_col_contesto():
    out, rep = apply_privacy_filter("TFN 123 456 782", SOLO_EN)
    assert rep.counts.get("tfn") == 1
    assert "{{TFN}}" in out


# ---------------------------------------------------------------------------
# La zona a lettura automatica del passaporto
# ---------------------------------------------------------------------------

# Lo specimen di ICAO 9303: due righe TD3 da 44 caratteri.
MRZ_RIGA1 = "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<"
MRZ_RIGA2 = "L898902C36UTO7408122F1204159ZE184226B<<<<<10"
MRZ = f"{MRZ_RIGA1}\n{MRZ_RIGA2}"


def test_il_blocco_mrz_sparisce_intero():
    """Comprese la prima riga, che porta cognome e nome e **non** finisce
    con una cifra di controllo. Cercando riga per riga sarebbe rimasta nel
    documento: il difetto peggiore possibile, sulla riga che conta di piu'.
    """
    out, rep = apply_privacy_filter(f"Documento:\n{MRZ}\nFine.", SOLO_EN)
    assert rep.counts.get("mrz") == 1
    assert "ERIKSSON" not in out
    assert "L898902C36UTO" not in out
    assert "{{MRZ}}" in out


def _storpia(riga: str, *posizioni: int) -> str:
    """Cambia le cifre di controllo indicate, lasciando il resto intatto."""
    caratteri = list(riga)
    for p in posizioni:
        caratteri[p] = "7" if caratteri[p] != "7" else "8"
    return "".join(caratteri)


def test_un_campo_storpiato_non_basta_a_far_sopravvivere_un_mrz():
    """Prudenza, di proposito.

    Se il numero del documento non torna ma la data di nascita si', quel
    blocco resta chiaramente la zona a lettura automatica di un documento,
    e dentro ci sono nome e cittadinanza. Redigerlo e' la scelta giusta:
    l'errore, su un dato personale, va fatto nella direzione prudente.
    """
    riga2 = _storpia(MRZ_RIGA2, 9)  # solo la cifra del numero documento
    out, rep = apply_privacy_filter(f"Documento:\n{MRZ_RIGA1}\n{riga2}\nFine.", SOLO_EN)
    assert rep.counts.get("mrz") == 1
    assert "ERIKSSON" not in out


def test_un_mrz_illeggibile_diventa_un_sospetto():
    """Quando **nessuna** delle tre cifre di controllo torna, non si puo'
    piu' dire che sia un documento -- ma nemmeno tacere: quella forma la
    produce un OCR che ha sbagliato a leggere un passaporto vero, e li'
    dentro c'e' tutto.

    Le tre cifre sono quelle dei campi che le portano accanto: numero del
    documento (posizione 10), nascita (20), scadenza (28). Non si usa la
    cifra composita di fine riga, che si calcola su pezzi non contigui:
    darle in pasto la riga intera la fa fallire sempre, e un controllo che
    dice sempre di no non distingue niente.
    """
    riga2 = _storpia(MRZ_RIGA2, 9, 19, 27)
    storpiato = f"{MRZ_RIGA1}\n{riga2}"
    out, rep = apply_privacy_filter(f"Documento:\n{storpiato}\nFine.", SOLO_EN)
    assert not rep.counts.get("mrz")
    assert [s for s in rep.suspects if s["kind"] == "mrz"]
    assert "ERIKSSON" in out  # non sostituito: era il punto


def test_una_riga_di_sole_maiuscole_non_e_un_mrz():
    """Senza il doppio riempitivo non e' una zona a lettura automatica: e'
    un titolo, un codice, una riga di tabella."""
    testo = "Documento:\nRIEPILOGO0123456789ABCDEFGHILMNOPQRS\nFine."
    out, rep = apply_privacy_filter(testo, SOLO_EN)
    assert out == testo
    assert not rep.suspects


# ---------------------------------------------------------------------------
# I nomi italiani a livelli di prova: il caso che aveva bloccato il merge
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "testo,chi",
    [
        ("La pratica e' seguita da Ludovica Sbrancagnoli.", "Sbrancagnoli"),
        ("Ha partecipato Federico Guglielmoni.", "Guglielmoni"),
        ("Il perito Osvaldo Trentacoste ha depositato.", "Trentacoste"),
    ],
)
def test_un_nome_in_mezzo_alla_frase_sparisce_sulla_prosa(testo, chi):
    """Il difetto che aveva fermato la riscrittura dei nomi italiani.

    Portando gli elenchi da «sostituisce» a «segnala», un nome senza titolo
    e senza firma sopravviveva -- e in una lettera e' il caso piu' comune
    che esista. Lo recupera il parametro prosa/modulo: su una lettera un
    riscontro solo negli elenchi basta, su un modulo no.

    Misurato su 6000 messaggi di mailing list italiane: 10 989 nomi in modo
    prosa contro 7 071 in modo modulo, e i sospetti scendono da 2,0 a 0,7
    per messaggio.
    """
    opts = PrivacyOptions(pacchetti=(CORE, IT), prosa=True)
    out, rep = apply_privacy_filter(testo, opts)
    assert rep.counts.get("names"), out
    assert chi not in out


def test_lo_stesso_nome_su_un_modulo_resta_un_sospetto():
    """L'altra meta', e il motivo per cui il parametro esiste: la stessa
    sequenza su un modulo e' quasi sempre l'etichetta di un campo."""
    testo = "La pratica e' seguita da Ludovica Sbrancagnoli."
    opts = PrivacyOptions(pacchetti=(CORE, IT), prosa=False)
    out, rep = apply_privacy_filter(testo, opts)
    assert not rep.counts.get("names")
    assert "Sbrancagnoli" in out
    assert [s for s in rep.suspects if s["kind"] == "nome"]
