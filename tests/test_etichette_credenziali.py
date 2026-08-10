"""Il vocabolario delle etichette che annunciano una credenziale.

Perche' questa strada, e non l'entropia
----------------------------------------

Dopo le forme note (PEM, AWS, GitHub, JWT, Bearer) e le etichette, il buco
che resta e' la stringa di formato ignoto **senza niente scritto accanto**.
Prenderla vorrebbe dire decidere sulla base di «sembra generata a caso» --
e hanno quell'aspetto anche gli hash dei commit, gli UUID, le firme base64
dentro un PDF, i codici a barre, i numeri di serie. Su un documento tecnico
diventa un massacro, e uno strumento che cancella mezzo documento viene
disinstallato.

Allargare il vocabolario prende gran parte degli stessi casi con un rischio
di **natura diversa**: una parola sbagliata si vede subito, si misura, e si
toglie. Una soglia sbagliata sbaglia in silenzio su una classe intera.

I tre gruppi, e perche' non sono uno
-------------------------------------

* **forte** -- l'etichetta da sola annuncia una credenziale, il valore si
  sostituisce comunque. «password:» non ha altri significati;
* **debole** -- l'etichetta in italiano ha anche altri sensi, quindi il
  valore deve **anche** sembrare una credenziale. E' il gruppo che esiste
  perche' «chiave: importante da ricordare» finiva sostituito;
* **corto** -- PIN, CVV, OTP. Quattro cifre non arrivano al minimo di sei
  del valore generico: aggiungerli agli altri elenchi li avrebbe lasciati
  senza effetto, e **un'etichetta scritta che non scatta mai e' peggio di
  un'etichetta mancante**, perche' sembra coperta.

Piu' un quarto caso a se': la **frase di recupero**, l'unico segreto fatto
di parole separate da spazi.

Le due meta' del test
---------------------

Positiva e negativa, e servono tutte e due per una ragione precisa: il
conto dei falsi positivi sul corpus a verita' zero e' rimasto **1 su 8,5 M
di caratteri** prima e dopo l'allargamento -- ma quel numero da solo
sarebbe identico anche se le etichette nuove non scattassero **mai**. La
meta' positiva e' cio' che distingue «non ha aggiunto errori» da «non ha
aggiunto niente».
"""

from __future__ import annotations

import pytest

from mr_rao.privacy import PrivacyOptions, apply_privacy_filter


def redigi(testo: str) -> str:
    return apply_privacy_filter(testo, PrivacyOptions())[0]


# --------------------------------------------------------------- gruppo forte

FORTI = [
    "Refresh token: eyJhbGciOiJIUzI1NiJ9xyz",
    "access_key = AKIA7X2QWERTY9ZZ",
    "Master key: 8f3a9c2e7b1d5406",
    "Signing secret: whsec_9aZ2kQpL",
    "Session key: 77aabbccddee0011",
    "Encryption key: 4d2f8a1b9c3e7f60",
    "api_token: ghs_AAaaBBbb1122",
    "API secret: 9fj20FJ20fj20fj2",
    "Chiave di cifratura: 0011aabbccddeeff",
    "Chiave crittografica: ff00aa11bb22cc33",
    "shared secret: s3cr3t-Sh4red-99",
    "Segreto condiviso: xY7-kL2-mN9-pQ4",
    "Connection string: Server=db;Pwd=Str0ngP4ss",
    "stringa di connessione: postgres://u:p@h/db",
    "Product key: BXQ72-JT4RV-9M2CD",
    "codice di licenza: LIC-99KK-2201",
    "license_key: AB12-CD34-EF56",
    "Passphrase: Tr0ub4dor&3",
    "One-time password: 8842991",
    "Chiave API: sk-live-ZZ77AA22BB",
    "token di accesso: at_9911kkzz77",
]


@pytest.mark.parametrize("frase", FORTI)
def test_un_etichetta_forte_toglie_il_valore(frase: str) -> None:
    assert "{{SECRET" in redigi(frase), (
        "l'etichetta e' scritta nell'elenco ma non morde: quasi sempre e' il "
        "valore che non arriva al minimo di caratteri, o un `\\b` che cade in "
        "mezzo a un trattino"
    )


def test_l_etichetta_resta_e_il_valore_no():
    """Si capisce cosa e' stato tolto, senza leggerlo."""
    fuori = redigi("Password: Tr0ub4dor&3")
    assert fuori.startswith("Password: ")
    assert "Tr0ub4dor" not in fuori


# -------------------------------------------------------------- gruppo corto

CORTI = [
    ("PIN: 4471", "4471"),
    ("CVV 934", "934"),
    ("codice di sicurezza: 8821", "8821"),
    ("OTP n. 552310", "552310"),
    ("PUK: 12345678", "12345678"),
    ("cvc 221", "221"),
    ("Codice di sblocco: 99120", "99120"),
]


@pytest.mark.parametrize("frase,valore", CORTI)
def test_un_codice_corto_viene_tolto(frase: str, valore: str) -> None:
    """Quattro cifre non arrivano al minimo del valore generico.

    E' il motivo per cui questi hanno un pattern loro: senza, l'etichetta
    sarebbe scritta nell'elenco e non scatterebbe mai.
    """
    fuori = redigi(frase)
    assert "{{SECRET" in fuori and valore not in fuori


def test_un_numero_lungo_non_e_un_pin():
    """Oltre le otto cifre non e' piu' un PIN: e' un altro codice.

    Senza il limite superiore, «PIN» davanti a un numero di pratica lungo
    lo farebbe sparire — e un numero di pratica tolto rende il documento
    inservibile per chi deve ritrovarla.
    """
    frase = "PIN: 123456789012"
    assert "{{SECRET" not in redigi(frase)


# ------------------------------------------------------- la frase di recupero


def test_la_frase_di_recupero_sparisce_intera():
    """Il difetto che questo caso ha evitato.

    Con il valore generico -- che si ferma al primo spazio -- usciva
    «Frase di recupero: {{SECRET}} batteria graffetta corretta»: **una
    parola su dodici**. La frase resta utilizzabile e il rapporto dichiara
    «1 segreto sostituito», cioe' il numero dice che e' andato tutto bene.
    Meglio non riconoscerla affatto che riconoscerla a meta'.
    """
    frase = (
        "Frase di recupero: cavallo batteria graffetta corretta zaino "
        "lampada fiume vento pietra sale nube corda"
    )
    fuori = redigi(frase)
    assert fuori == "Frase di recupero: {{SECRET_1}}"


def test_poche_parole_non_sono_una_frase_di_recupero():
    """Il limite basso e' la protezione dell'etichetta.

    «frase di recupero: vedi allegato» e «custodita in cassaforte» sono
    prosa, non un segreto: sotto le dodici parole non scatta niente.
    """
    for frase in [
        "frase di recupero: vedi allegato",
        "frase di recupero: custodita in cassaforte presso lo studio",
    ]:
        assert redigi(frase) == frase


# ------------------------------------------------- quello che NON deve sparire

NON_SEGRETI = [
    # `chiave` ha troppi significati per stare fra le forti
    ("chiave pubblica", "Chiave pubblica: MFkwEwYHKoZIzj0CAQ"),
    ("parola chiave", "parola chiave: sicurezza"),
    ("chiave in senso figurato", "Chiave: importante da ricordare"),
    # etichette deboli con un valore che e' prosa
    ("attivazione allegata", "codice di attivazione: allegato"),
    ("codice utente", "Codice utente: pratica"),
    ("segreto professionale", "segreto professionale: vincolante"),
    # etichette corte senza un numero dietro
    ("PIN senza numero", "PIN della carta smarrita"),
    ("sicurezza antincendio", "Il codice di sicurezza antincendio e' affisso"),
]


@pytest.mark.parametrize("perche,frase", NON_SEGRETI)
def test_cio_che_somiglia_a_un_etichetta_ma_non_lo_e(perche: str, frase: str) -> None:
    assert "{{SECRET" not in redigi(frase), perche


def test_la_carta_col_punto_come_separatore():
    """Alcuni gestionali stampano `4111.1111.1111.1111`.

    Il telefono accettava gia' il punto («010.2471234»), la carta no, e non
    c'era una ragione: e' lo stesso segno usato nello stesso modo.
    """
    fuori = redigi("Carta 4111.1111.1111.1111")
    assert "{{CARD" in fuori and "4111" not in fuori


@pytest.mark.parametrize("frase", [
    "Importo di 3.500,00 euro",
    "Totale 4.111.111 lire",
    "Protocollo 4111.2024",
    "versione 4.11.11.11",
])
def test_il_punto_nelle_carte_non_apre_agli_importi(frase: str) -> None:
    """Il guardiano e' la testa del pattern, non il buon senso.

    `[3-6]\\d{3}` pretende **quattro cifre attaccate** all'inizio, quindi un
    numero con il punto delle migliaia dopo una cifra sola non arriva
    nemmeno a proporsi. E a dire l'ultima parola resta Luhn.
    """
    assert "{{CARD" not in redigi(frase)


def test_authorization_non_e_un_etichetta_e_c_e_una_ragione():
    """L'etichetta provata, aggiunta, e **tolta** — con la prova del perche'.

    Mettendo `authorization` fra le etichette forti, su
    «Authorization: Bearer eyJhbGci...» il valore diventa la parola
    **«Bearer»**: il nome dello schema, non un segreto. L'uscita usciva
    `Authorization: {{SECRET}} {{SECRET}}` — meno leggibile di prima — e il
    rapporto contava due segreti dove ce n'e' uno.

    Il token vero ce l'ha gia' un riconoscitore suo, quindi quell'etichetta
    non aggiungeva copertura: solo il difetto. L'ha trovata il corpus di
    conformita', non un test — e questo test esiste perche' la prossima
    volta la trovi un test.
    """
    fuori = redigi(
        "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dBjftJeZ"
    )
    assert fuori.startswith("Authorization: Bearer {{SECRET"), fuori
    assert fuori.count("{{SECRET") == 1, "il token e' uno solo: lo schema non e' un segreto"


def test_la_chiave_pubblica_non_e_un_segreto():
    """Vale la pena scriverlo da solo: e' l'errore piu' facile da fare.

    Mettendo `chiave` fra le etichette forti — che sembra ragionevole —
    «chiave pubblica» diventerebbe un segreto. Una chiave pubblica e'
    pubblica per definizione, e toglierla rompe un documento tecnico senza
    proteggere nessuno.
    """
    frase = "Chiave pubblica del certificato: MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE"
    assert redigi(frase) == frase
