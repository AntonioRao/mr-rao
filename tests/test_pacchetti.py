"""I pacchetti di riconoscitori: nucleo universale e formati italiani.

Fase 1 di #1. Prima esisteva un solo interruttore, ``fiscal``, e dentro
convivevano l'IBAN — mod-97, valido in tutti i Paesi SEPA — e il codice
fiscale, che esiste solo in Italia. Chi voleva usare Mr. Rao su un documento
straniero doveva prendersi anche i riconoscitori italiani, oppure rinunciare
pure all'IBAN.

Il banco golden (``test_golden_privacy.py``) dimostra che il comportamento
predefinito **non e' cambiato**. Questi test dimostrano l'altra meta': che
la separazione serve davvero a qualcosa, cioe' che scegliendo il solo
nucleo i riconoscitori italiani smettono di girare e gli altri no. Senza
questi, il refactoring avrebbe potuto lasciare `pacchetti` completamente
scollegato e il golden sarebbe rimasto verde lo stesso.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from mr_rao.privacy import (
    CORE,
    DETECTOR_FIELDS,
    EN,
    IT,
    PACCHETTI_NOTI,
    SEQUENZA,
    PrivacyOptions,
)
from aiuti import apply_privacy_filter  # segnaposto appiattiti: vedi tests/aiuti.py

# Un documento con dentro un dato universale e uno italiano, vicini.
TESTO = (
    "Codice fiscale RSSMRA85T10A562S, "
    "IBAN IT60X0542811101000000123456, "
    "carta 4111 1111 1111 1111."
)


# ---------------------------------------------------------------------------
# La sequenza e' coerente con se stessa
# ---------------------------------------------------------------------------


def test_ogni_passo_dichiara_un_pacchetto_noto():
    for passo in SEQUENZA:
        assert passo.pacchetto in PACCHETTI_NOTI, passo.nome


def test_ogni_passo_punta_a_un_campo_che_esiste():
    """Un campo scritto male non alzerebbe un errore: ``getattr`` fallisce
    a tempo di esecuzione, e solo per i documenti che passano di li'."""
    opts = PrivacyOptions()
    for passo in SEQUENZA:
        assert hasattr(opts, passo.campo), f"{passo.nome} -> {passo.campo}"
        assert isinstance(getattr(opts, passo.campo), bool), passo.nome


def test_i_nomi_dei_passi_sono_unici():
    nomi = [p.nome for p in SEQUENZA]
    assert len(nomi) == len(set(nomi)), sorted(nomi)


def test_ogni_interruttore_ha_almeno_un_passo():
    """Una casella nell'interfaccia che non accende niente e' una bugia."""
    coperti = {p.campo for p in SEQUENZA}
    scoperti = set(DETECTOR_FIELDS) - coperti
    assert not scoperti, f"interruttori senza riconoscitore: {sorted(scoperti)}"


def test_ogni_pacchetto_noto_ha_dei_passi():
    """Se la classificazione collassasse su un pacchetto solo, i test di
    selezione qui sotto passerebbero senza dimostrare niente. E un
    pacchetto dichiarato e vuoto sarebbe una voce nell'interfaccia che non
    fa nulla."""
    pacchetti = {p.pacchetto for p in SEQUENZA}
    assert pacchetti == set(PACCHETTI_NOTI)


# ---------------------------------------------------------------------------
# La selezione fa davvero qualcosa
# ---------------------------------------------------------------------------


def test_di_default_sono_accesi_tutti_i_pacchetti():
    """Il caso d'uso vero e' lo studio italiano col contratto inglese, e
    quella persona non deve sapere di dover spuntare una casella.

    Si puo' fare perche' e' stato misurato, non perche' sembra comodo:
    accendendo anche il pacchetto inglese sul corpus italiano il banco
    golden resta identico **carattere per carattere**. I riconoscitori
    inglesi pretendono o una punteggiatura precisa (i trattini 3-2-4 del
    SSN), o una parola di contesto, o un tipo di via inglese: su un
    documento italiano non trovano niente a cui attaccarsi.

    Se un giorno questo test e il golden divergessero, il golden ha
    ragione: vorrebbe dire che un riconoscitore inglese ha cominciato a
    mordere su testo italiano, ed e' un difetto, non una funzione.
    """
    assert PrivacyOptions().pacchetti == (CORE, IT, EN)


def test_col_solo_nucleo_l_iban_e_la_carta_spariscono_lo_stesso():
    out, rep = apply_privacy_filter(TESTO, PrivacyOptions(pacchetti=(CORE,)))
    assert "{{IBAN}}" in out
    assert "{{CARD}}" in out
    assert rep.counts.get("iban") == 1
    assert rep.counts.get("cards") == 1


def test_col_solo_nucleo_il_codice_fiscale_resta():
    """Il punto di tutta la fase 1: i due riconoscitori erano legati, ora no."""
    out, rep = apply_privacy_filter(TESTO, PrivacyOptions(pacchetti=(CORE,)))
    assert "RSSMRA85T10A562S" in out
    assert "codice_fiscale" not in rep.counts


def test_col_pacchetto_italiano_il_codice_fiscale_sparisce():
    out, rep = apply_privacy_filter(TESTO, PrivacyOptions(pacchetti=(CORE, IT)))
    assert "RSSMRA85T10A562S" not in out
    assert rep.counts.get("codice_fiscale") == 1


def test_senza_nessun_pacchetto_non_succede_niente():
    """Il caso limite che vale la pena fissare: un elenco vuoto non deve
    ricadere silenziosamente sul comportamento predefinito."""
    out, rep = apply_privacy_filter(TESTO, PrivacyOptions(pacchetti=()))
    assert out == TESTO
    assert rep.total == 0


def test_il_sospetto_italiano_non_scatta_senza_il_pacchetto_italiano():
    """I sospetti sono comportamento quanto le sostituzioni: un motore che
    segnala codici fiscali a chi ha chiesto il solo nucleo sta parlando di
    una cosa che non sta cercando."""
    # Sedici caratteri con la proporzione di un codice fiscale, ma troppo
    # lontani dalla forma perche' il recupero OCR possa raddrizzarli: sono
    # necessarie piu' delle due correzioni ammesse. Un codice storpiato da
    # un carattere solo verrebbe *sostituito*, non segnalato, e il test
    # misurerebbe un'altra cosa.
    storpiato = "Da OCR: AB1CD2EF3GH4IJ5K"
    _, solo_core = apply_privacy_filter(storpiato, PrivacyOptions(pacchetti=(CORE,)))
    _, con_it = apply_privacy_filter(storpiato, PrivacyOptions(pacchetti=(CORE, IT)))
    assert not [s for s in solo_core.suspects if s["kind"] == "codice_fiscale"]
    assert [s for s in con_it.suspects if s["kind"] == "codice_fiscale"]


@pytest.mark.parametrize("pacchetti", [(CORE,), (CORE, IT), ()])
def test_filtrare_non_riordina(pacchetti):
    """Filtrare non deve riordinare: l'ordine e' il comportamento."""
    eseguiti = [
        p.nome
        for p in sorted(SEQUENZA, key=lambda p: p.priorita)
        if p.pacchetto in set(pacchetti)
    ]
    indici = [next(i for i, p in enumerate(SEQUENZA) if p.nome == n) for n in eseguiti]
    assert indici == sorted(indici)


def test_l_ordine_dichiarato_coincide_con_quello_eseguito():
    """SEQUENZA si legge dall'alto in basso, ma a decidere e' ``priorita``.

    Se le due cose divergessero, chiunque legga il file per capire l'ordine
    leggerebbe una cosa falsa -- ed e' il file dove l'ordine *e'* il
    comportamento. Meglio tenerli allineati e farlo dire a un test.
    """
    dichiarato = [p.nome for p in SEQUENZA]
    eseguito = [p.nome for p in sorted(SEQUENZA, key=lambda p: p.priorita)]
    assert dichiarato == eseguito


def test_le_priorita_rispettano_i_vincoli_che_contano():
    """Non l'ordine esatto -- i tre vincoli per cui quell'ordine esiste."""
    pr = {p.nome: p.priorita for p in SEQUENZA}
    # Gli URL prima delle email: un indirizzo dentro un link non deve
    # spezzare il link.
    assert pr["urls"] < pr["emails"]
    # I codici prima dei telefoni: una partita IVA e' undici cifre.
    assert max(pr["partita_iva"], pr["codice_fiscale"]) < pr["phones"]
    # I riconoscitori esatti prima di quelli tolleranti all'OCR.
    assert pr["codice_fiscale"] < pr["codice_fiscale_ocr"]
    assert pr["iban"] < pr["iban_ocr"]
    # I nomi per ultimi: i segnaposto gia' inseriti fanno da contesto, e il
    # riconoscitore inglese ci si appoggia proprio ({{EMAIL}} accanto a due
    # parole maiuscole). Vale per **tutti** i passi sui nomi, non solo per
    # quello italiano.
    nomi = [p.priorita for p in SEQUENZA if p.campo == "names"]
    altri = [p.priorita for p in SEQUENZA if p.campo != "names"]
    assert min(nomi) > max(altri)


# ---------------------------------------------------------------------------
# Raggiungibile da fuori, non solo da Python
# ---------------------------------------------------------------------------
#
# Il pacchetto EN e' esistito per un giorno intero come codice morto:
# validato, testato, e impossibile da accendere per chiunque non scrivesse
# Python. `pacchetti` non compariva in nessun form, nessun profilo, nessun
# argomento della riga di comando. Un motore che nessuno puo' azionare non
# protegge nessuno.


def test_il_form_puo_scegliere_i_pacchetti():
    from mr_rao.privacy import options_from_form

    assert options_from_form({}).pacchetti == (CORE, IT, EN)
    assert options_from_form({"privacy_pack_en": "false"}).pacchetti == (CORE, IT)
    assert options_from_form({"privacy_pack_it": "false"}).pacchetti == (CORE, EN)
    entrambi = options_from_form(
        {"privacy_pack_it": "false", "privacy_pack_en": "false"}
    )
    assert entrambi.pacchetti == (CORE,)


def test_il_json_puo_scegliere_i_pacchetti():
    from mr_rao.privacy import options_from_dict

    assert options_from_dict({}).pacchetti == (CORE, IT, EN)
    assert options_from_dict({"privacy_pack_en": False}).pacchetti == (CORE, IT)


def test_le_caselle_esistono_nella_pagina():
    """Parita' GUI: se il motore lo sa fare, l'interfaccia deve permetterlo.

    Un'opzione raggiungibile solo dalla riga di comando e' un'opzione che
    la maggior parte delle persone non ha.
    """
    pagina = (
        Path(__file__).resolve().parents[1] / "templates" / "index.html"
    ).read_text(encoding="utf-8")
    for casella in ('id="privacy-pack_it"', 'id="privacy-pack_en"'):
        assert casella in pagina, f"manca la casella {casella}"


def test_il_javascript_manda_i_pacchetti_al_server():
    """La casella che non viene spedita e' peggio di una casella assente:
    sembra di aver scelto qualcosa."""
    js = (
        Path(__file__).resolve().parents[1] / "static" / "js" / "app.js"
    ).read_text(encoding="utf-8")
    for campo in ("privacy_pack_it", "privacy_pack_en"):
        assert campo in js, f"app.js non spedisce {campo}"


def test_la_riga_di_comando_puo_spegnere_un_pacchetto():
    js = (
        Path(__file__).resolve().parents[1] / "mr_rao" / "cli.py"
    ).read_text(encoding="utf-8")
    for flag in ("--no-pack-it", "--no-pack-en"):
        assert flag in js, f"la CLI non espone {flag}"


# ---------------------------------------------------------------------------
# L'euristica dei cognomi e' stata RITIRATA (1.13.0)
#
# Era spenta di default dalla 1.7.2 (#5) e restava accendibile. Il conto su
# documenti che non contengono un solo dato personale:
#
#    8 904 sostituzioni sbagliate su 20 moduli dell'Agenzia delle Entrate
#   14 376 su 8 Gazzette Ufficiali storiche
#    2 888 su 99 moduli fiscali statunitensi
#
# Nel 2026-08 il fenomeno e' stato riprodotto su corpora che non abbiamo
# scritto noi -- 27 moduli amministrativi italiani scaricati dagli enti --
# dove passava da 27 a 2 529 sostituzioni sbagliate. E' quella riproduzione
# indipendente ad aver chiuso la questione: non e' stata tolta perche' era
# rischiosa in teoria, ma perche' era sbagliata in pratica su documenti che
# non avevamo scelto noi.
#
# I test qui sotto sorvegliano il ritiro da tre lati: il motore, la porta
# d'ingresso web e la pagina.
# ---------------------------------------------------------------------------


def test_l_euristica_non_esiste_piu_nel_motore():
    """Se questo diventa rosso qualcuno l'ha rimessa: prima di aggiornarlo,
    rifare il banco sui moduli veri e guardare il numero."""
    from mr_rao.privacy import FIELD_DEFAULTS

    assert not hasattr(PrivacyOptions(), "name_guess")
    assert "name_guess" not in FIELD_DEFAULTS


def test_chi_prova_ad_accenderla_da_fuori_non_ottiene_niente():
    """La porta d'ingresso vera e' il form del browser, e li' puo' arrivare
    una configurazione vecchia salvata nel `localStorage` di chi usava la
    versione precedente. Deve essere **ignorata**, non deve far fallire la
    conversione: chi torna sul programma dopo un mese non merita un errore
    per una casella che abbiamo tolto noi."""
    from mr_rao.privacy import options_from_dict, options_from_form

    for costruttore in (options_from_form, options_from_dict):
        o = costruttore({"privacy_name_guess": "true"})
        assert not hasattr(o, "name_guess")
        assert o.names is True, "il resto del riconoscimento nomi resta acceso"


def test_la_casella_non_e_piu_nella_pagina():
    """Parita' GUI al contrario: una casella che il motore non legge piu'
    sarebbe peggio di nessuna casella, perche' prometterebbe una scelta che
    non ha piu' nessun effetto."""
    pagina = (
        Path(__file__).resolve().parents[1] / "templates" / "index.html"
    ).read_text(encoding="utf-8")
    assert 'id="privacy-name_guess"' not in pagina


def test_i_due_flag_della_riga_di_comando_restano_accettati():
    """Sono finiti in script e appunti di chi li usava. Farli fallire adesso
    romperebbe quei comandi per comunicare una cosa che e' gia' il
    comportamento del programma: `--no-name-guess` ottiene ancora
    esattamente cio' che chiedeva.

    Il controllo e' sul **parser**, non sull'aiuto: che siano nascosti e che
    siano accettati sono due affermazioni diverse, e la prima non dimostra
    la seconda. Con `parse_args` un flag rimosso alzerebbe SystemExit(2).
    """
    from mr_rao.cli import build_parser

    parser = build_parser()
    for flag in ("--name-guess", "--no-name-guess"):
        args = parser.parse_args(["convert", "documento.pdf", flag])
        assert args.command == "convert"

    # E non fanno niente: le opzioni prodotte sono identiche con e senza.
    import dataclasses

    from mr_rao.cli import _build_options

    nudo = _build_options(parser.parse_args(["convert", "documento.pdf"]))
    con_flag = _build_options(
        parser.parse_args(["convert", "documento.pdf", "--name-guess"])
    )
    assert dataclasses.asdict(nudo) == dataclasses.asdict(con_flag), (
        "`--name-guess` cambia ancora qualcosa: non e' stato ritirato davvero"
    )


# ---------------------------------------------------------------------------
# Prosa o modulo: tre stati, raggiungibili da fuori
# ---------------------------------------------------------------------------


def test_il_tipo_di_documento_ha_tre_stati():
    """«Non lo so» e' una risposta diversa da «e' un modulo», anche se oggi
    portano allo stesso comportamento. Il giorno in cui la stima automatica
    migliorasse, un booleano avrebbe gia' buttato via l'informazione che
    serve per accorgersene."""
    from mr_rao.privacy import options_from_dict, options_from_form, prosa_da

    assert prosa_da("") is None and prosa_da(None) is None
    assert prosa_da("prosa") is True
    assert prosa_da("modulo") is False
    assert options_from_form({}).prosa is None
    assert options_from_form({"privacy_stile": "prosa"}).prosa is True
    assert options_from_dict({"privacy_stile": "modulo"}).prosa is False


def test_il_tipo_di_documento_e_scegliibile_dalla_pagina():
    """Parita' GUI. La stima automatica sbaglia -- su un verbale impaginato
    come una lettera, su un PDF misto -- e chi ha il documento davanti sa
    cos'e' meglio di qualunque euristica."""
    pagina = (
        Path(__file__).resolve().parents[1] / "templates" / "index.html"
    ).read_text(encoding="utf-8")
    assert 'id="privacy-stile"' in pagina
    for valore in ('value=""', 'value="prosa"', 'value="modulo"'):
        assert valore in pagina, f"manca l'opzione {valore}"
    js = (
        Path(__file__).resolve().parents[1] / "static" / "js" / "app.js"
    ).read_text(encoding="utf-8")
    assert "privacy_stile" in js, "app.js non spedisce il tipo di documento"


def test_il_convertitore_deduce_il_tipo_dal_file():
    """Le estensioni che non hanno bisogno di stima non la fanno."""
    from mr_rao.converter import _e_prosa

    assert _e_prosa(Path("x.eml"), ".eml", "markitdown") is True
    assert _e_prosa(Path("x.txt"), ".txt", "markitdown") is True
    assert _e_prosa(Path("x.xlsx"), ".xlsx", "markitdown") is False
    # Word era fuori dall'elenco, e chi e' fuori si comporta come un modulo:
    # due riscontri invece di uno prima di sostituire un nome. Cioe' nomi
    # lasciati in chiaro nel formato in cui si scrivono le lettere. Questo
    # test non c'era, ed e' il motivo per cui la dimenticanza e' durata.
    for estensione in (".docx", ".doc", ".odt", ".rtf", ".pptx", ".md"):
        assert _e_prosa(Path("x" + estensione), estensione, "markitdown") is True, (
            estensione
        )
    # Su una scansione i vettori non ci sono: contarli darebbe zero, e zero
    # verrebbe letto come «prosa» -- giusto per il motivo sbagliato.
    assert _e_prosa(Path("x.pdf"), ".pdf", "rapidocr_pdf_fallback") is None


# ---------------------------------------------------------------------------
# L'IBAN: il codice Paese e la lunghezza, non solo il mod-97
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "iban,paese",
    [
        ("IT60X0542811101000000123456", "Italia, 27"),
        ("GB29NWBK60161331926819", "Regno Unito, 22"),
        ("DE89370400440532013000", "Germania, 22"),
        ("NL91ABNA0417164300", "Paesi Bassi, 18"),
    ],
)
def test_gli_iban_veri_passano(iban, paese):
    from mr_rao.privacy import iban_checksum_ok

    assert iban_checksum_ok(iban), paese


@pytest.mark.parametrize(
    "finto,perche",
    [
        ("SS51234567890123456789012345", "«SS» non e' un codice Paese"),
        ("XX60X0542811101000000123456", "«XX» non e' assegnato"),
        ("IT60X05428111010000001234", "italiano ma lungo 25 invece di 27"),
    ],
)
def test_i_finti_iban_non_passano(finto, perche):
    """Il mod-97 da solo scarta 96 candidati su 97: su un volume pieno di
    codici lunghi, uno su 97 passa comunque. Sul banco comparivano IBAN su
    documenti che non ne contengono nessuno, «recuperati» dall'OCR --
    12 casi, ora zero. Il checksum protegge dai candidati sbagliati, non da
    uno spazio di candidati troppo largo."""
    from mr_rao.privacy import iban_checksum_ok

    assert not iban_checksum_ok(finto), perche


def test_il_recupero_ocr_non_inventa_iban():
    """Con due correzioni ottiche si arriva a un mod-97 valido per caso.
    Il codice Paese e la lunghezza tolgono quasi tutto quello spazio."""
    from mr_rao.privacy import iban_ocr_recover

    # Un IBAN italiano vero con due caratteri storpiati dall'OCR: va
    # recuperato, e' il motivo per cui la funzione esiste.
    assert iban_ocr_recover("lT6OX0542811101000000123456") is not None
    # Un numero d'ordine qualsiasi: non deve diventare niente.
    assert iban_ocr_recover("5551234567890123456789012345") is None
