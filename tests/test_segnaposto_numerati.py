"""I segnaposto numerati: `{{NAME_1}}`, `{{NAME_2}}` (P6.1, 1.20.0).

Perche' questo file non appiattisce niente
------------------------------------------

Quasi tutti gli altri test passano da `tests/aiuti.py`, che toglie i numeri
per far tornare vere le asserzioni sui riconoscitori. Se anche questo lo
facesse, la numerazione sarebbe accesa in produzione e **non provata da
nessuna parte**. Qui si chiama il motore com'e', con i suoi valori
predefiniti.

Le tre proprieta' che contano
-----------------------------

1. **Valori diversi, numeri diversi**; **stesso valore, stesso numero.** E'
   la funzione: senza, «{{NAME}} ha citato {{NAME}} davanti a {{NAME}}» non
   si legge.
2. **Il numero non e' stabile fra documenti.** Se lo fosse avremmo inventato
   un identificatore persistente -- un dato personale nuovo, creato da uno
   strumento che esiste per toglierli.
3. **I numeri seguono l'ordine del testo**, non quello in cui scattano i
   riconoscitori, e non toccano cio' che era gia' scritto nel documento.

La terza sembra estetica e non lo e': prima della rinumerazione finale una
riga vera usciva `Chiave: {{SECRET_2}} = {{SECRET_1}}`, e chi legge pensa
che manchi un pezzo di documento.
"""

from __future__ import annotations

from mr_rao.privacy import (
    SENTINELLA,
    PrivacyOptions,
    apply_privacy_filter,
    senza_numeri,
)


def redigi(testo: str, **kw) -> str:
    return apply_privacy_filter(testo, PrivacyOptions(**kw))[0]


# --------------------------------------------------------------- la funzione


def test_persone_diverse_ricevono_numeri_diversi():
    fuori = redigi("Mario Rossi ha citato Giulia Bianchi davanti a Luca Verdi.")
    assert fuori == "{{NAME_1}} ha citato {{NAME_2}} davanti a {{NAME_3}}."


def test_la_stessa_persona_ripetuta_tiene_il_suo_numero():
    fuori = redigi("Mario Rossi ha scritto a Giulia Bianchi; poi Mario Rossi ha richiamato.")
    assert fuori == "{{NAME_1}} ha scritto a {{NAME_2}}; poi {{NAME_1}} ha richiamato."


def test_maiuscole_e_spaziatura_non_fanno_due_persone():
    """«MARIO ROSSI» e «Mario Rossi» sono la stessa persona.

    Se ricevessero due numeri, il documento direbbe che ci sono due persone
    dove ce n'e' una -- cioe' la numerazione racconterebbe una cosa falsa
    invece di una vera.
    """
    fuori = redigi("Mario Rossi ha firmato. Controfirma: MARIO ROSSI.")
    assert fuori.count("{{NAME_1}}") == 2
    assert "{{NAME_2}}" not in fuori


def test_lo_stesso_iban_scritto_in_due_modi_e_lo_stesso_conto():
    """Spaziato e attaccato: stesso numero.

    La chiave del numero e' il valore ripulito da tutto cio' che non e'
    alfanumerico, ed e' il motivo per cui questo caso funziona.
    """
    fuori = redigi(
        "Accredito su IT60 X054 2811 1010 0000 0123 456, "
        "cioe' IT60X0542811101000000123456."
    )
    assert fuori.count("{{IBAN_1}}") == 2, fuori


def test_ogni_categoria_ha_la_sua_numerazione():
    """`{{NAME_1}}` e `{{EMAIL_1}}` convivono: i contatori sono per etichetta."""
    fuori = redigi("Mario Rossi <m.rossi@a.it> e Luigi Bianchi <l.bianchi@b.it>")
    assert fuori == "{{NAME_1}} <{{EMAIL_1}}> e {{NAME_2}} <{{EMAIL_2}}>"


# ------------------------------------------- il vincolo che la tiene innocua


def test_il_numero_non_e_stabile_fra_documenti():
    """La proprieta' su cui si regge la domanda 8 delle FAQ.

    Non e' una promessa sull'implementazione: e' quella che distingue un
    numero da un identificatore. Si prova invertendo l'ordine -- la stessa
    persona cambia numero, quindi non ci si puo' fare un join.
    """
    dritto = redigi("Mario Rossi e Luigi Bianchi")
    rovescio = redigi("Luigi Bianchi e Mario Rossi")
    assert dritto == rovescio == "{{NAME_1}} e {{NAME_2}}"


def test_due_conversioni_non_si_accumulano():
    """Il contatore nasce e muore con la conversione.

    Un contatore che sopravvivesse darebbe `{{NAME_2}}` al secondo
    documento: sarebbe uno stato condiviso fra due file, cioe' l'inizio
    dell'archivio che questo prodotto non deve avere.
    """
    opzioni = PrivacyOptions()
    primo, _ = apply_privacy_filter("Mario Rossi ha firmato.", opzioni)
    secondo, _ = apply_privacy_filter("Giulia Bianchi ha firmato.", opzioni)
    assert primo == secondo == "{{NAME_1}} ha firmato."


# ------------------------------------------------ ordine, e cosa non si tocca


def test_i_numeri_seguono_l_ordine_del_testo():
    """Il caso vero da cui e' nata la rinumerazione finale.

    I segreti passano da tre pattern diversi e uscivano `{{SECRET_2}} =
    {{SECRET_1}}`: numeri assegnati nell'ordine in cui scattano i
    riconoscitori, che per chi legge non e' nessun ordine.
    """
    fuori = redigi("Chiave: api_key = sk-test-ABCDEF0123456789abcdef")
    assert fuori == "Chiave: {{SECRET_1}} = {{SECRET_2}}"


def test_un_segnaposto_gia_nel_documento_non_viene_rinumerato():
    """Un file gia' redatto, ripassato dal motore.

    I suoi `{{NAME_5}}` sono testo di qualcun altro. Rinumerarli sarebbe
    riscrivere una parte del documento che non abbiamo toccato -- e chi
    riconverte per aggiungere un riconoscitore si ritroverebbe i numeri
    cambiati sotto ai piedi, senza che niente lo dica.
    """
    dentro = "Il referente {{NAME_5}} ha scritto a {{EMAIL_9}}."
    assert redigi(dentro) == dentro


def test_i_due_mondi_convivono_nella_stessa_riga():
    """Numeri vecchi lasciati stare, numeri nuovi assegnati da uno."""
    fuori = redigi("Il referente {{NAME_5}} ha incontrato Mario Rossi.")
    assert fuori == "Il referente {{NAME_5}} ha incontrato {{NAME_1}}."


def test_la_sentinella_non_esce_mai():
    """Il carattere che marca i nostri segnaposto e' interno, e deve restarci.

    Se sopravvivesse all'uscita finirebbe in un documento consegnato a
    qualcuno: invisibile sullo schermo, presente nei byte. E' il tipo di
    difetto che si scopre mesi dopo, da un confronto che non torna.
    """
    testi = [
        "Mario Rossi <m.rossi@a.it>, tel. 06 4455 6677, CF RSSMRA85T10A562S",
        "Chiave: api_key = sk-test-ABCDEF0123456789abcdef",
        "IBAN IT60 X054 2811 1010 0000 0123 456",
        "Il referente {{NAME_5}} ha incontrato Mario Rossi.",
    ]
    for t in testi:
        fuori, _ = apply_privacy_filter(t, PrivacyOptions())
        assert SENTINELLA not in fuori, t


# ------------------------------------------------------- spegnere e riaccendere


def test_spenta_l_uscita_e_quella_di_prima():
    fuori = redigi(
        "Mario Rossi ha citato Giulia Bianchi.", numerati=False
    )
    assert fuori == "{{NAME}} ha citato {{NAME}}."


def test_senza_numeri_riporta_alla_forma_piatta():
    """La funzione pubblica su cui si appoggiano i confronti e i test.

    Serve anche a chi confronta due conversioni: con i numeri, due uscite
    dello stesso documento differiscono ovunque compaia un valore nuovo, e
    il confronto smette di dire qualcosa.
    """
    numerato = redigi("Mario Rossi ha citato Giulia Bianchi.")
    piatto = redigi("Mario Rossi ha citato Giulia Bianchi.", numerati=False)
    assert senza_numeri(numerato) == piatto


def test_il_conteggio_non_cambia_accendendo_o_spegnendo():
    """La numerazione cambia **come** si scrive, non **quanto** si toglie.

    Se il rapporto cambiasse, vorrebbe dire che la numerazione ha alterato
    il comportamento di qualche riconoscitore -- ed e' successo davvero in
    lavorazione: i pattern che si agganciano a `{{EMAIL}}` avevano smesso
    di trovarlo, e un nome restava in chiaro.
    """
    testo = (
        "Mario Rossi <m.rossi@a.it> e Luigi Bianchi <l.bianchi@b.it>, "
        "tel. 06 4455 6677, IBAN IT60 X054 2811 1010 0000 0123 456"
    )
    _, con = apply_privacy_filter(testo, PrivacyOptions())
    _, senza = apply_privacy_filter(testo, PrivacyOptions(numerati=False))
    assert con.to_dict()["counts"] == senza.to_dict()["counts"]
    assert con.to_dict()["suspects"] == senza.to_dict()["suspects"]
