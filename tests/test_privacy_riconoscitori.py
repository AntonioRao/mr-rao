"""Riconoscitori aggiunti in 1.4.0: URL, indirizzi, segreti, carte, date,
e le regole di contesto per i nomi di persona.

Il banco di prova sono due testi: una mail italiana realistica, dove tutto
deve sparire, e un verbale amministrativo, dove non deve sparire niente.
Il secondo conta quanto il primo: un filtro che redige tutto e' inutile
esattamente come uno che non redige niente.
"""
import pytest

from mr_rao.privacy import (
    PrivacyOptions,
    apply_privacy_filter,
    luhn_ok,
    no_redaction,
    only,
)


# ---------------------------------------------------------------------------
# URL
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "testo",
    [
        "Scarica da https://portale.esempio.it/pratiche/2024-118?token=ab99 grazie",
        "Il modulo sta su www.comune.roma.it/moduli/delega.pdf",
        "Vedi http://esempio.it/condizioni",
        "Link markdown [le condizioni](https://esempio.it/c) in fondo",
    ],
)
def test_gli_url_vengono_sostituiti(testo):
    out, report = apply_privacy_filter(testo, only("urls"))
    assert "{{URL}}" in out
    assert "http" not in out and "www." not in out
    assert report.counts.get("urls", 0) == 1


def test_l_url_non_si_porta_via_la_punteggiatura_finale():
    out, _ = apply_privacy_filter("Vai su https://esempio.it/pagina.", only("urls"))
    assert out == "Vai su {{URL}}."


def test_un_dominio_nudo_non_e_un_url():
    """Solo http/https/www: altrimenti ogni "nome.it" del testo diventa un link."""
    out, report = apply_privacy_filter("La sede di esempio.it e' a Roma", only("urls"))
    assert out == "La sede di esempio.it e' a Roma"
    assert report.total == 0


# ---------------------------------------------------------------------------
# Telefoni scritti a gruppi
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "testo",
    [
        "cell. 335 123 4567",
        "cellulare 3351234567",
        "chiama il +39 06 4522 8890",
        "in seconda battuta allo 320-441-9982",
        "Fax 06.4522.8891",
        "tel: 06 45228890",
        "Tel. 081/1234567".replace("/", " "),
    ],
)
def test_numeri_scritti_a_gruppi(testo):
    """Il difetto vero: i numeri con gli spazi ogni tre cifre passavano."""
    out, report = apply_privacy_filter(testo, only("phones"))
    assert "{{PHONE}}" in out, out
    assert report.counts.get("phones", 0) == 1


@pytest.mark.parametrize(
    "testo",
    [
        "Protocollo interno: 0123456789",
        "Registrata il 01.02.2024 in archivio",
        "Pratica 2024/118 del registro",
        "Riferimento 9988776655 interno",
        "Importo 1.220,00 EUR",
        "Il CAP e' 00128 Roma",
        "Versione 3.10 del sistema",
    ],
)
def test_cifre_che_non_sono_recapiti(testo):
    out, report = apply_privacy_filter(testo, only("phones"))
    assert out == testo
    assert report.total == 0


# ---------------------------------------------------------------------------
# Indirizzi
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "testo",
    [
        "sede di Via Valle di Perna 315, 00128 Roma",
        "accesso da Viale dell'Umanesimo 12",
        "parcheggio in Piazza dei Navigatori 22/A",
        "magazzino in Corso Vittorio Emanuele II n. 145",
        "centralina in vicolo del Buco 3",
        "ufficio in Largo Brindisi 4",
        "abita in via Roma",
    ],
)
def test_gli_indirizzi_vengono_sostituiti(testo):
    out, report = apply_privacy_filter(testo, only("addresses"))
    assert "{{ADDRESS}}" in out, out
    assert report.counts.get("addresses", 0) == 1


def test_l_indirizzo_si_porta_via_civico_cap_e_comune():
    out, _ = apply_privacy_filter(
        "presso Via Valle di Perna 315, 00128 Roma, con accesso",
        only("addresses"),
    )
    assert out == "presso {{ADDRESS}}, con accesso"


@pytest.mark.parametrize(
    "testo",
    [
        "trasmesso via PEC in data odierna",
        "comunicazione via email al fornitore",
        "nel corso della seduta si e' discusso",
        "il Corso di laurea in ingegneria",
        "spedito via Raccomandata",
    ],
)
def test_le_parole_di_strada_usate_come_parole(testo):
    """«via», «corso», «piazza» sono anche parole italiane comunissime."""
    out, report = apply_privacy_filter(testo, only("addresses"))
    assert out == testo
    assert report.total == 0


# ---------------------------------------------------------------------------
# Nomi: le regole di contesto
# ---------------------------------------------------------------------------


def test_nome_accanto_all_indirizzo_di_posta():
    """Il caso piu' frequente nelle mail, e quello che sfuggiva sempre:
    il cognome non sta in nessun elenco, ma sta accanto a un'email."""
    testo = "Da: Gianmarco Trentini <g.trentini@studio.it>"
    out, _ = apply_privacy_filter(testo, only("emails", "names"))
    assert "Trentini" not in out
    assert "{{NAME}}" in out and "{{EMAIL}}" in out


def test_nome_dopo_un_titolo_professionale():
    testo = "contattare il geom. Nazzareno Sbrolli per il sopralluogo"
    out, _ = apply_privacy_filter(testo, only("names"))
    assert "Sbrolli" not in out and "Nazzareno" not in out
    assert out.startswith("contattare il geom. {{NAME}}")


def test_il_titolo_non_si_porta_via_la_parola_dopo():
    out, _ = apply_privacy_filter("Gentile Dott. Rao, come da accordi", only("names"))
    assert out == "Gentile Dott. {{NAME}}, come da accordi"


def test_cognome_sconosciuto_dedotto_dal_nome_noto():
    out, _ = apply_privacy_filter("Il collega Ilenia Mastrogiacomo risponde", only("names"))
    assert "Mastrogiacomo" not in out


def test_l_euristica_si_puo_spegnere():
    """Due parole maiuscole ignote: con l'euristica spariscono, senza no."""
    testo = "Riferimento Kwabena Osei per il progetto"
    acceso = PrivacyOptions(**{**only("names").__dict__, "name_guess": True})
    spento = PrivacyOptions(**{**only("names").__dict__, "name_guess": False})

    out_on, _ = apply_privacy_filter(testo, acceso)
    out_off, report_off = apply_privacy_filter(testo, spento)

    assert "{{NAME}}" in out_on and "Osei" not in out_on
    assert out_off == testo and report_off.total == 0


def test_un_nome_proprio_ambiguo_da_solo_resta():
    """«Rosa» e' un nome proprio ed e' un fiore: da sola non basta."""
    out, report = apply_privacy_filter("La Rosa dei venti indica il nord", only("names"))
    assert out.startswith("La Rosa")
    assert report.total == 0


# ---------------------------------------------------------------------------
# Segreti
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "testo,resta",
    [
        ("password: Tr0ub4dor&3", "password"),
        ("api_key = sk-proj-abcdefghijklmnopqrstuvwxyz012345", "api_key"),
        ("client_secret: 9f8e7d6c5b4a39281706", "client_secret"),
    ],
)
def test_le_credenziali_perdono_il_valore_non_l_etichetta(testo, resta):
    out, report = apply_privacy_filter(testo, only("secrets"))
    assert "{{SECRET}}" in out
    assert resta in out, "l'etichetta serve a capire cosa e' stato tolto"
    assert report.counts.get("secrets", 0) >= 1


@pytest.mark.parametrize(
    "testo",
    [
        "AKIAIOSFODNN7EXAMPLE",
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N",
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEow\n-----END RSA PRIVATE KEY-----",
    ],
)
def test_chiavi_riconosciute_dalla_forma(testo):
    out, _ = apply_privacy_filter(testo, only("secrets"))
    assert "{{SECRET}}" in out


# ---------------------------------------------------------------------------
# Carte di pagamento
# ---------------------------------------------------------------------------


def test_luhn_distingue_la_carta_dal_numero_lungo():
    assert luhn_ok("4111 1111 1111 1111")
    assert not luhn_ok("5551234567890123")


def test_la_carta_sparisce_e_il_numero_d_ordine_resta():
    testo = "Carta 4111 1111 1111 1111 - ordine 5551234567890123"
    out, report = apply_privacy_filter(testo, only("fiscal"))
    assert "{{CARD}}" in out
    assert "5551234567890123" in out
    assert report.counts.get("cards", 0) == 1


# ---------------------------------------------------------------------------
# Date di nascita
# ---------------------------------------------------------------------------


def test_solo_le_date_con_contesto_di_nascita():
    testo = "Nato il 14/07/1982 a Reggio. Riunione del 12/03/2024."
    out, report = apply_privacy_filter(testo, only("dates"))
    assert "14/07/1982" not in out
    assert "12/03/2024" in out, "una data di riunione non e' un dato personale"
    assert report.counts.get("dates", 0) == 1


def test_le_date_sono_spente_per_difetto():
    assert PrivacyOptions().dates is False


# ---------------------------------------------------------------------------
# Il contrario: niente falsi positivi su un testo amministrativo
# ---------------------------------------------------------------------------

VERBALE = """Verbale della riunione del Comitato Tecnico

Il Consiglio di Amministrazione ha approvato il Piano Industriale 2024-2026.
La Direzione Generale ha trasmesso il documento via PEC in data 12/03/2024,
protocollo 0123456789, con riferimento alla Delibera 45 del Consiglio Regionale.

Nel corso della seduta si e' discusso della Legge 231 e del Regolamento Europeo.
Il Sistema Informativo sara' aggiornato alla Versione 3.10. Il collaudo del
Nuovo Datacenter e' previsto in due fasi: la Fase Uno riguarda la rete, la
Fase Due i sistemi di backup.

La fattura numero 2024/118 e' stata registrata il 01.02.2024 con protocollo
9988776655. Il Codice Identificativo Gara e' 1234567890AB.
"""


def test_un_verbale_amministrativo_esce_intatto():
    """Il presidio contro l'entusiasmo: qui non c'e' nessun dato personale,
    e con tutti i riconoscitori accesi non deve sparire una parola."""
    out, report = apply_privacy_filter(VERBALE, PrivacyOptions(dates=True))
    assert report.total == 0, report.to_dict()
    assert out == VERBALE


# ---------------------------------------------------------------------------
# Spegnere tutto vuol dire tutto
# ---------------------------------------------------------------------------


def test_no_redaction_spegne_ogni_riconoscitore():
    """Elencare i campi a mano lascia acceso quello aggiunto ieri."""
    opts = no_redaction()
    for campo, valore in vars(opts).items():
        assert valore is False, campo


def test_no_redaction_lascia_il_testo_come_sta():
    testo = "Mario Rossi, mario@x.it, +39 335 1234567, via Roma 1, https://x.it"
    out, report = apply_privacy_filter(testo, no_redaction())
    assert out == testo
    assert report.total == 0


def test_only_rifiuta_un_riconoscitore_inesistente():
    with pytest.raises(ValueError):
        only("telefoni")
