# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Il terzo stato: cercato, trovato, lasciato in chiaro **apposta** (P6.2).

Cosa cambia rispetto a spegnere un riconoscitore
------------------------------------------------

Fino alla 1.19 gli stati erano due, e non erano separabili:

    interruttore acceso  ->  cerca e sostituisce
    interruttore spento  ->  non cerca

Chi aveva bisogno di un dato in chiaro -- gli importi di una fattura da far
confrontare a un modello, l'eta' in una cartella clinica -- poteva solo
spegnere. E spegnere **non lascia traccia**: il documento esce con il dato
dentro e il rapporto tace, quindi chi lo rilegge non ha modo di sapere se
li' non c'era niente o se abbiamo guardato dall'altra parte.

Il valore di questa funzione non e' nel testo -- che e' identico nei due
casi -- ma nel rapporto. «Ho lasciato in chiaro 3 importi, apposta» e'
un'informazione per un DPO; il silenzio no. **E' il test centrale di questo
file**, ed e' l'unico modo per accorgersi se un domani i due casi tornassero
a coincidere.

La forma
--------

Le due cose vanno separate: una categoria deselezionata viene comunque
rilevata, e semplicemente non sostituita.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from mr_rao.privacy import (
    CATEGORIE,
    PrivacyOptions,
    apply_privacy_filter,
    categorie_da,
    options_from_dict,
    segnala_da_form,
)

RADICE = Path(__file__).resolve().parent.parent

TESTO = (
    "Mario Rossi, IBAN IT60 X054 2811 1010 0000 0123 456, "
    "importo 1.250,00 EUR, tel. 06 4455 6677"
)


def redigi(testo: str, **kw):
    fuori, rapporto = apply_privacy_filter(testo, PrivacyOptions(**kw))
    return fuori, rapporto.to_dict()


# ------------------------------------------------------------- i tre stati


def test_acceso_sostituisce():
    fuori, r = redigi(TESTO, amounts=True)
    assert "{{IBAN_1}}" in fuori
    assert r["counts"]["iban"] == 1
    assert r["detected_total"] == 0


def test_segnalato_lascia_il_dato_e_lo_scrive_nel_rapporto():
    fuori, r = redigi(TESTO, amounts=True, segnala=("iban",))
    assert "IT60 X054 2811 1010 0000 0123 456" in fuori, "il dato doveva restare"
    assert "iban" not in r["counts"], "non e' stato sostituito, non va contato fra i tolti"
    assert r["detected_counts"] == {"iban": 1}
    # Le altre categorie continuano a lavorare: «segnala» e' per categoria,
    # non un interruttore generale travestito.
    assert "{{PHONE_1}}" in fuori and "{{NAME_1}}" in fuori


def test_spento_non_cerca_e_non_lascia_traccia():
    fuori, r = redigi(TESTO, amounts=True, fiscal=False)
    assert "IT60 X054 2811 1010 0000 0123 456" in fuori
    assert "iban" not in r["counts"]
    assert r["detected_total"] == 0


def test_la_differenza_fra_spento_e_segnalato_e_solo_nel_rapporto():
    """**Il test centrale.**

    Il documento e' identico -- byte per byte -- e il rapporto no. Se un
    domani i due casi tornassero a produrre lo stesso rapporto, questa
    funzione sarebbe sparita senza che niente diventasse rosso altrove: il
    testo non se ne accorgerebbe.
    """
    spento, r_spento = redigi(TESTO, amounts=True, fiscal=False)
    segnalato, r_segnalato = redigi(TESTO, amounts=True, segnala=("iban",))

    assert spento == segnalato, "il documento deve essere lo stesso"
    assert r_spento["detected_total"] == 0
    assert r_segnalato["detected_total"] == 1
    assert r_segnalato["detected"][0]["kind"] == "iban"


def test_il_campione_e_mascherato():
    """Come i sospetti, e per la stessa ragione.

    Il valore e' rimasto nel documento in chiaro: e' proprio percio' che il
    rapporto -- che si esporta, si incolla, si allega -- non deve
    riscriverlo per esteso una seconda volta.
    """
    _, r = redigi(TESTO, segnala=("iban",))
    campione = r["detected"][0]["sample"]
    assert "•" in campione
    assert "IT60 X054 2811 1010 0000 0123 456" not in campione


def test_piu_categorie_insieme():
    fuori, r = redigi(TESTO, amounts=True, segnala=("iban", "amounts"))
    assert "1.250,00 EUR" in fuori and "IT60 X054" in fuori
    assert r["detected_counts"] == {"iban": 1, "amounts": 1}


def test_una_categoria_il_cui_interruttore_e_spento_resta_zitta():
    """`segnala` decide cosa fare di cio' che si trova, non se cercarlo.

    Metterci una categoria che nessuno sta cercando non la accende: non
    c'e' niente da segnalare se il riconoscitore non gira. Scritto qui
    perche' e' la domanda che si fa chiunque legga l'opzione.
    """
    _, r = redigi(TESTO, amounts=True, fiscal=False, segnala=("iban",))
    assert r["detected_total"] == 0


def test_i_tre_numeri_del_rapporto_restano_separati():
    """`counts`, `detected`, `suspects` rispondono a tre domande diverse.

    Cosa e' stato tolto, cosa e' stato lasciato apposta, cosa il motore non
    ha saputo decidere. Sommarli darebbe un totale che non vuol dire niente,
    e infatti `total` continua a contare solo le sostituzioni.
    """
    _, r = redigi(TESTO, amounts=True, segnala=("iban",))
    assert r["total"] == sum(r["counts"].values())
    assert r["detected_total"] not in (r["total"], r["suspects_total"]) or r["detected_total"] == 1


# ------------------------------------------------- l'OCR e il testo restituito


def test_un_codice_storpiato_dall_ocr_torna_com_era():
    """Il caso che rendeva questa funzione pericolosa.

    Tre chiamanti su cinquantuno passano al motore un valore **diverso** dal
    testo trovato: i codici recuperati dall'OCR passano la versione
    corretta, perche' e' quella che deve ricevere il numero. Restituendo
    quella in modalita' «segnala», il documento uscirebbe **riscritto** --
    il codice storpiato sostituito da quello giusto -- senza che nessuna
    sostituzione risulti nel rapporto. Peggio di tutte e due le scelte.
    """
    storpiato = "Codice fiscale RSSMRA8ST1OA562S"
    fuori, r = redigi(storpiato, segnala=("codice_fiscale",))
    assert fuori == storpiato, "il testo dev'essere identico, storpiature comprese"
    # e il contatore dei recuperi non deve dire che ha corretto qualcosa
    assert "ocr_corretti" not in r["counts"]


def test_il_frontmatter_porta_cio_che_e_stato_lasciato():
    """La parte del rapporto che viaggia col documento.

    L'API restituisce tutto, ma chi riceve il file fra sei mesi non ha la
    risposta HTTP: ha il file. Se il frontmatter tace, «l'ho lasciato
    apposta» resta un'impostazione di qualcuno invece di una cosa scritta —
    e a quel punto la funzione vale la meta'.
    """
    from mr_rao.converter import ConvertOptions, convert_bytes

    esito = convert_bytes(
        TESTO.encode(),
        "nota.txt",
        options=ConvertOptions(privacy=PrivacyOptions(amounts=True, segnala=("iban",))),
    )
    testa = esito.markdown.split("---")[1]
    assert "detected_not_replaced:" in testa, testa
    assert "  iban: 1" in testa
    # Separato dal totale delle sostituzioni: sommarli darebbe un numero
    # che non vuol dire niente.
    assert "redactions:" in testa
    assert "iban" not in testa.split("detected_not_replaced:")[0].split("redactions:")[1]


def test_senza_segnalati_il_frontmatter_non_cambia():
    """Nessun blocco vuoto: un documento normale esce come prima."""
    from mr_rao.converter import ConvertOptions, convert_bytes

    esito = convert_bytes(
        TESTO.encode(), "nota.txt", options=ConvertOptions(privacy=PrivacyOptions())
    )
    assert "detected_not_replaced" not in esito.markdown


# --------------------------------------------------- il vocabolario e le porte


def test_l_elenco_delle_categorie_e_quello_che_il_motore_emette_davvero():
    """La guardia contro l'elenco che invecchia.

    `CATEGORIE` e' scritto a mano, e un elenco scritto a mano di cose che
    stanno altrove va fuori sincrono al primo riconoscitore nuovo. Qui si
    rilegge il sorgente del motore -- come fa `check_docs.py` -- e si
    confrontano i nomi.

    Il difetto che previene e' silenzioso: una categoria che manca da
    `CATEGORIE` non si puo' mettere in «segnala», e chi ci prova riceve
    «categoria inesistente» per una categoria che esiste eccome.

    **Le due forme vanno lette tutte e due**, ed e' la lezione pagata qui:
    la prima versione di questo test leggeva solo `segnaposto("x", ...)` e
    saltava le sei chiamate che passano da `_replace_all`, dove la categoria
    e' l'ultimo argomento. `emails` e `termini` mancavano da `CATEGORIE`, e
    il test era **verde**: l'estrazione aveva lo stesso punto cieco
    dell'elenco che doveva sorvegliare. Se ne e' accorto un test di parita'
    GUI che provava `privacy_segnala=emails` e riceveva «categoria
    inesistente» per la categoria piu' usata del prodotto.
    """
    sorgenti = "".join(
        (RADICE / "mr_rao" / f).read_text(encoding="utf-8")
        for f in ("privacy.py", "en_formats.py")
    )
    emesse = set(re.findall(r'segnaposto\(\s*"([a-z_]+)"', sorgenti))
    emesse |= set(re.findall(r'_replace_all\([^)]*?,\s*report,\s*"([a-z_]+)"\)', sorgenti))
    assert len(emesse) >= 20, (
        f"l'estrazione trova solo {sorted(emesse)}: e' cambiato il modo di "
        "chiamare, e questo test sta per diventare verde senza guardare niente"
    )
    assert emesse == set(CATEGORIE), (
        f"mancano da CATEGORIE: {sorted(emesse - set(CATEGORIE))}; "
        f"in CATEGORIE ma non emesse: {sorted(set(CATEGORIE) - emesse)}"
    )


@pytest.mark.parametrize("sbagliata", ["email", "IBANN", "codice fiscale", "nomi"])
def test_un_nome_sbagliato_non_passa_in_silenzio(sbagliata: str):
    """Un refuso deve farsi sentire.

    Se `email` (invece di `emails`) fosse accettato e ignorato, l'utente
    crederebbe di aver lasciato in chiaro gli indirizzi, il documento
    uscirebbe redatto lo stesso, e non ci sarebbe **nessun** segnale.
    """
    with pytest.raises(ValueError, match="categorie inesistenti"):
        categorie_da(sbagliata)


def test_le_due_forme_del_modulo():
    """La pagina manda un campo unico, uno script puo' mandare le caselle."""
    assert segnala_da_form({"privacy_segnala": "iban, amounts"}) == ("iban", "amounts")
    assert segnala_da_form({"privacy_segnala_iban": "on"}) == ("iban",)
    assert segnala_da_form({"privacy_segnala_iban": "off"}) == ()
    assert segnala_da_form({}) == ()


def test_arriva_dal_json_dell_api():
    opzioni = options_from_dict({"privacy_segnala": ["iban"]})
    assert opzioni.segnala == ("iban",)


def _pagina() -> str:
    from mr_rao.app_factory import create_app

    app = create_app()
    app.config['TESTING'] = True
    return app.test_client().get('/', base_url='http://127.0.0.1:5000').get_data(as_text=True)


def test_la_pagina_mostra_una_casella_per_ogni_categoria():
    """Il motore le accetta tutte, l'interfaccia deve offrirle tutte.

    Le caselle si generano da `CATEGORIE`, non da un elenco copiato nel
    template: una categoria nuova compare il giorno che nasce. Questo test
    e' cio' che impedisce di tornare all'elenco copiato senza accorgersene —
    una voce che manca nel pannello non e' visibile da nessuna parte, e chi
    la cerca conclude che la funzione non ce l'ha.

    **Le esclusioni sono dichiarate, non implicite.** `termini` non e' un
    dato riconosciuto dal motore: e' la lista di parole che l'utente stesso
    ha chiesto di proteggere, e chiedere di segnalarle invece di
    sostituirle vuol dire chiedere al programma di disobbedire. Sta in
    `CATEGORIE_NON_SEGNALABILI`, e il test pretende che quell'insieme resti
    piccolo: un'esclusione per volta si argomenta, venti sarebbero il modo
    di far sparire il pannello senza che nessuno se ne accorga.
    """
    from mr_rao.i18n import CATEGORIE_NON_SEGNALABILI

    pagina = _pagina()
    assert 'id="segnala-panel"' in pagina
    for c in CATEGORIE:
        atteso = c not in CATEGORIE_NON_SEGNALABILI
        c_e = f'id="privacy-segnala-{c}"' in pagina
        assert c_e is atteso, (
            f"{c}: nel pannello={c_e}, atteso={atteso}. Se l'esclusione e' "
            "voluta va dichiarata in CATEGORIE_NON_SEGNALABILI, col perche'."
        )
    assert len(CATEGORIE_NON_SEGNALABILI) <= 2, sorted(CATEGORIE_NON_SEGNALABILI)


def test_le_caselle_hanno_un_nome_leggibile():
    """`bban`, `mrz`, `routing_number` sono i nomi con cui il codice parla a
    se stesso.

    Il pannello li mostrava cosi'. Non e' un difetto che rompe qualcosa: e'
    un pannello che chiede una decisione a chi non ha gli elementi per
    prenderla — che in un programma sulla riservatezza e' peggio di un
    errore, perche' non si vede.

    Guarda **tutt'e due** le lingue: un'etichetta tradotta a meta' si nota
    solo cambiando lingua, cioe' quasi mai.
    """
    from mr_rao.i18n import CATEGORIE_NON_SEGNALABILI, etichetta_categoria

    pagina = _pagina()
    grezzi = []
    for c in CATEGORIE:
        if c in CATEGORIE_NON_SEGNALABILI:
            continue
        assert etichetta_categoria(c, "it") != c, (
            f"{c} non ha un'etichetta italiana: aggiungi `cat_{c}` in i18n"
        )
        assert etichetta_categoria(c, "en") != c, f"{c} non ha l'etichetta inglese"
        # `>opt-title">bban<` sarebbe l'identificatore stampato tale e quale.
        if f'"opt-title">{c}<' in pagina:
            grezzi.append(c)
    assert not grezzi, f"nel pannello compaiono ancora gli identificatori: {grezzi}"


def test_ogni_categoria_e_accettata():
    """Nessuna categoria e' irraggiungibile dall'esterno.

    Un elenco in cui una voce non e' selezionabile e' peggio di una voce
    mancante: c'e' scritta, e non funziona.
    """
    assert categorie_da(",".join(CATEGORIE)) == CATEGORIE
