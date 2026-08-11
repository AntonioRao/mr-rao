"""Il pacchetto «atti e pratiche»: spento di serie, e non e' un ripiego.

Perche' esiste, e perche' e' spento
-----------------------------------

Qui c'e' una divergenza vera fra due pubblici, e hanno ragione tutti e due.

Per un notaio il riferimento catastale **e' il dato piu' sensibile della
frase**: dice esattamente di quale immobile si parla, e da un foglio e una
particella si arriva al proprietario in un pomeriggio.

Per un'azienda il numero di protocollo e' cio' che permette di **ritrovare**
la pratica, e toglierlo rende il documento inservibile senza proteggere
nessuno. Non e' un caso che «protocollo» e «repertorio» stiano gia' nel
vocabolario di cio' che **non** si redige: e' quello che impedisce a ogni
numero di pratica di essere letto come un telefono.

Questo pacchetto **capovolge** quella scelta. Una cosa cosi' non si accende
di serie: si accende da chi sa di volerla.

Due assi, non uno
-----------------

L'interruttore `atti` dice *quale dato*, il pacchetto `ATTI` dice *per quale
mestiere*. Servono tutti e due, ed e' la stessa forma dei pacchetti
nazionali. L'interruttore e' acceso e il pacchetto spento: chi accende il
pacchetto ottiene subito qualcosa, chi spegne l'interruttore lo spegne
comunque.

Tutti i valori sono inventati.
"""

from __future__ import annotations

import pytest

from mr_rao.privacy import (
    ATTI,
    CORE,
    EN,
    IT,
    PACK_FIELD_DEFAULTS,
    PrivacyOptions,
    apply_privacy_filter,
    senza_numeri,
)

ACCESO = (CORE, IT, EN, ATTI)


def redigi(testo: str, pacchetti=None, **kw) -> str:
    opzioni = PrivacyOptions(pacchetti=pacchetti or (CORE, IT, EN), **kw)
    return senza_numeri(apply_privacy_filter(testo, opzioni)[0])


# ------------------------------------------------- il pacchetto e' spento


def test_di_serie_il_pacchetto_e_spento() -> None:
    """La riga che tiene la decisione.

    Se un domani qualcuno lo accendesse «per simmetria» con gli altri due,
    ogni numero di pratica comincerebbe a sparire dai documenti aziendali —
    e nessun altro test se ne accorgerebbe, perche' tutti gli altri girano
    con i pacchetti predefiniti.
    """
    assert PACK_FIELD_DEFAULTS[ATTI] is False
    assert PACK_FIELD_DEFAULTS[IT] is True and PACK_FIELD_DEFAULTS[EN] is True


def test_col_pacchetto_spento_il_catastale_resta() -> None:
    testo = "Immobile identificato al foglio 12 particella 345 sub 6."
    assert redigi(testo) == testo


def test_l_interruttore_da_solo_non_basta() -> None:
    """`atti=True` e' il valore di serie: se bastasse quello, il pacchetto
    non servirebbe a niente e la decisione sarebbe stata aggirata."""
    testo = "Immobile al foglio 12 particella 345."
    assert redigi(testo, atti=True) == testo


# ------------------------------------------------------ acceso, funziona


@pytest.mark.parametrize(
    "frase",
    [
        "Immobile identificato al foglio 12 particella 345 sub 6 in Pisa.",
        "Bene censito al Fg. 245 mapp. 2752 subalterno 52",
        "Riferimento: F. 8 part. 1290",
        "foglio 12, particella 345",
    ],
)
def test_col_pacchetto_acceso_il_catastale_sparisce(frase: str) -> None:
    fuori = redigi(frase, pacchetti=ACCESO)
    assert "{{CATASTO}}" in fuori, fuori


def test_lo_spegne_anche_l_interruttore() -> None:
    """Due assi: chi accende il pacchetto ma spegne l'interruttore non deve
    ottenere niente. Senza questo, `atti=False` sarebbe decorativo."""
    testo = "Immobile al foglio 12 particella 345."
    assert redigi(testo, pacchetti=ACCESO, atti=False) == testo


# ------------------------------------------------ e cosa NON deve prendere


@pytest.mark.parametrize(
    "frase",
    [
        # Il foglio da solo e' la pagina di una relazione.
        "Vedi il foglio 3 della relazione tecnica",
        "Come da foglio 12 allegato",
        # La particella senza il foglio davanti.
        "particella 345 senza foglio davanti",
        # Due numeri lontani: in una tabella catastale le colonne sono
        # «Fg. | Part.», e con una finestra larga si prenderebbero due celle
        # di righe diverse.
        "foglio 12\n\n\nAltro paragrafo\n\nparticella 345",
    ],
)
def test_quello_che_non_e_un_catastale_resta(frase: str) -> None:
    assert "{{CATASTO}}" not in redigi(frase, pacchetti=ACCESO), frase


# ------------------------------------------------------ numeri di pratica


def test_col_pacchetto_spento_la_pratica_resta() -> None:
    """La riga che protegge il pubblico opposto.

    Qui il pacchetto **capovolge** una scelta presa altrove nel motore: per
    tutti gli altri «protocollo» e «repertorio» servono a dire di *non*
    redigere. Se questo scattasse di serie, ogni numero di pratica
    comincerebbe a sparire dai documenti aziendali.
    """
    testo = "Vista la nota prot. n. 26597 del 19 ottobre."
    assert redigi(testo) == testo


@pytest.mark.parametrize(
    ("frase", "resta"),
    [
        ("Iscritta al n. 1234/2023 R.G. del Tribunale.", "R.G."),
        ("Prot. n. 55871 del 12 marzo 2024", "Prot. n."),
        ("Protocollo 2024/000123", "Protocollo"),
        ("Rep. n. 45678", "Rep. n."),
        ("Vista la procura notarile rep. n. 8757 in data 12 novembre", "rep. n."),
        ("Repertorio n. 45678, raccolta 12345", "raccolta"),
        ("R.G.N.R. 4567/2022", "R.G.N.R."),
        ("cron. 998", "cron."),
    ],
)
def test_sparisce_il_numero_e_resta_l_etichetta(frase: str, resta: str) -> None:
    """Sparisce il numero, **resta la parola**.

    E' la stessa scelta fatta per gli appellativi e per le parole d'ente: la
    parola dice di che genere di dato si trattava, e chi rilegge capisce la
    frase senza poter risalire a niente. Toglierla insieme al numero
    renderebbe il documento illeggibile in cambio di nessuna protezione.
    """
    fuori = redigi(frase, pacchetti=ACCESO)
    assert "{{PRATICA}}" in fuori, fuori
    assert resta in fuori, fuori


def test_il_numero_col_l_anno_non_si_spezza_a_meta() -> None:
    """«Protocollo 2024/000123» e' anno-barra-progressivo.

    Con il numeratore limitato a quattro cifre il pattern ripiegava sulla
    seconda alternativa e sostituiva **meta' numero**, lasciando
    `{{PRATICA}}/000123` nel testo — che e' peggio di non sostituire,
    perche' sembra fatto.
    """
    fuori = redigi("Protocollo 2024/000123", pacchetti=ACCESO)
    assert fuori == "Protocollo {{PRATICA}}"


@pytest.mark.parametrize(
    "frase",
    [
        # Il quinto protocollo di una convenzione non e' un numero di
        # pratica. E' la cifra sola a distinguerli: una pratica ne ha almeno
        # due, oppure ha l'anno accanto.
        "Protocollo n. 5 della Convenzione",
        # Le citazioni di legge sono la forma piu' comune che esista in un
        # atto, e senza l'etichetta davanti finirebbero tutte nel tritacarne.
        "L'articolo 12 del regolamento 2016/679",
        "Il decreto legislativo 231/2001",
        "Ai sensi della legge 241/1990",
    ],
)
def test_quello_che_non_e_una_pratica_resta(frase: str) -> None:
    assert redigi(frase, pacchetti=ACCESO) == frase


def test_la_pratica_la_spegne_anche_l_interruttore() -> None:
    testo = "Prot. n. 55871 del 12 marzo 2024"
    assert redigi(testo, pacchetti=ACCESO, atti=False) == testo


# ---------------------------------- le forme trovate misurando il richiamo
#
# Nessuna di queste sarebbe venuta in mente leggendo il codice: sono uscite
# tendendo una rete piu' larga del motore su un corpus di atti veri e
# guardando cosa prendeva lei e non lui.


@pytest.mark.parametrize(
    ("frase", "resta"),
    [
        # `Rac.` con una c sola: e' l'abbreviazione che gli atti notarili usano
        # davvero. Chiedendo le due c si perdevano 6 728 numeri di raccolta.
        ("atto Rep. 74570 Rac. 1261 del 2017-11-20", "Rac."),
        # Il ruolo generale **senza punti**, comunissimo negli atti.
        ("fattura RG 87220/2020 scadenza 27-11-2020", "RG"),
        ("Atto notarile repertorio RG 99654/2021", "repertorio"),
        # Il «n.» maiuscolo: stava fuori dal gruppo insensibile al caso, e
        # un atto scritto tutto in maiuscolo non veniva riconosciuto.
        ("REPERTORIO N. 182/2023 ROGATO DAL NOTAIO", "REPERTORIO N."),
        ("PROT. N. 55871 del 12 marzo", "PROT. N."),
    ],
)
def test_le_forme_che_il_richiamo_ha_scoperto(frase: str, resta: str) -> None:
    fuori = redigi(frase, pacchetti=ACCESO)
    assert "{{PRATICA}}" in fuori, fuori
    assert resta in fuori, fuori


def test_la_sigla_di_ragusa_non_e_un_numero_di_ruolo() -> None:
    """**Il prezzo di aver ammesso `RG` senza punti**, e come si tiene.

    `RG` nudo e' anche la sigla della provincia di Ragusa, che il
    riconoscitore degli indirizzi ha imparato a tenersi. La discriminante e'
    la barra con l'anno: un numero di ruolo si scrive `12345/2020`, una sigla
    di provincia non e' mai seguita da numero-barra-numero.

    Senza questa riga, «Ragusa RG 97100» perderebbe il CAP.
    """
    for frase in ("residente a Ragusa RG atto",
                  "Comune di Ragusa RG 97100",
                  "Sede in Ragusa RG 12"):
        assert "{{PRATICA}}" not in redigi(frase, pacchetti=ACCESO), frase


# -------------------------------------------------------------- le targhe


def test_col_pacchetto_spento_la_targa_resta() -> None:
    testo = "Veicolo targato AB 123 CD."
    assert redigi(testo) == testo


@pytest.mark.parametrize(
    "frase",
    [
        "Veicolo targato AB 123 CD, di proprieta' della societa'.",
        "Autovettura AB123CD",
        "Rilevata la vettura AB-123-CD",
        # Ciclomotore: due lettere e cinque cifre, e li' la parola davanti
        # e' obbligatoria.
        "Motociclo targa AB 12345",
        "targa n. AB12345",
        # «targato», non solo «targa»: e' la forma piu' comune in un verbale,
        # e chiedendo la parola esatta si perdevano 67 targhe.
        "il veicolo targato AB 12345 sequestrato",
        "targate AB 12345",
        # Tutto minuscolo: nei documenti trascritti a mano c'e', e non e' raro.
        "Il veicolo vm916jx condotto dal conducente",
    ],
)
def test_la_targa_sparisce(frase: str) -> None:
    assert "{{TARGA}}" in redigi(frase, pacchetti=ACCESO), frase


def test_la_targa_a_caso_misto_no() -> None:
    """**Tutto maiuscolo oppure tutto minuscolo, mai misto**, ed e' misurato.

    Ammettere il minuscolo senza condizioni costava un falso positivo su 47
    documenti pubblici: `ge 021 CV`, un frammento d'OCR dentro una frase sulle
    clementine. Quel frammento e' misto, le targhe vere no.
    """
    fuori = redigi("Clementine del ge 021 CV con peduncolo", pacchetti=ACCESO)
    assert "{{TARGA}}" not in fuori, fuori


@pytest.mark.parametrize(
    "frase",
    [
        # Sulle targhe italiane I, O, Q e U non esistono — si confonderebbero
        # con 1 e 0 — ed e' l'unico controllo disponibile qui.
        "IO 123 QU non e' una targa",
        "AU 123 CD nemmeno",
        # Il minuscolo **non** e' piu' qui, ed e' un cambio di decisione, non
        # una svista: fino alla 1.23.0 «ab 123 cd» era escluso perche' «una
        # targa si scrive maiuscola sempre». Misurandolo si e' visto che non e'
        # vero — 135 targhe minuscole su un corpus di atti — e che il costo
        # vero veniva dal caso **misto**, non dal minuscolo. Vedi
        # `test_la_targa_a_caso_misto_no`.
        # Due lettere e cinque cifre senza la parola davanti puo' essere
        # qualunque codice, e infatti quasi sempre lo e'.
        "Codice MB 12345 di magazzino",
        # Tre cifre in mezzo, ma le lettere non bastano.
        "AB 1234 CD",
    ],
)
def test_quello_che_non_e_una_targa_resta(frase: str) -> None:
    assert "{{TARGA}}" not in redigi(frase, pacchetti=ACCESO), frase


def test_la_targa_la_spegne_anche_l_interruttore() -> None:
    testo = "Veicolo targato AB 123 CD."
    assert redigi(testo, pacchetti=ACCESO, atti=False) == testo


# ------------------------------------------------- le tre stanno insieme


def test_le_tre_categorie_sono_dichiarate() -> None:
    """Una categoria che il motore emette ma che non sta in `CATEGORIE` non
    si puo' mettere in «segnala»: sparirebbe in silenzio dall'interfaccia."""
    from mr_rao.privacy import CATEGORIE

    for c in ("catasto", "pratica", "targa"):
        assert c in CATEGORIE, c


def test_e_raggiungibile_dall_interfaccia() -> None:
    """Parita' GUI: un pacchetto che si puo' accendere solo dall'API e'
    una funzione che per chi usa il programma non esiste."""
    from mr_rao.app_factory import create_app

    app = create_app()
    app.config["TESTING"] = True
    pagina = app.test_client().get("/", base_url="http://127.0.0.1:5000").get_data(as_text=True)
    assert 'id="privacy-pack_atti"' in pagina
    assert 'id="privacy-atti"' in pagina
    # E **senza** `checked`: la casella del pacchetto dev'essere spenta.
    pezzo = pagina.split('id="privacy-pack_atti"')[1][:40]
    assert "checked" not in pezzo, pezzo
