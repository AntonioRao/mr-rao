"""L'indirizzo si mangiava la prima parola del blocco dopo.

    Address: Via A. Volta 5, 20121 Milano
    Account: IT60 X054 2811 1010 0000 0123 456

usciva come `Address: {{ADDRESS}}: {{IBAN}}` — la parola «Account» **sparita
dal documento**. Con una riga vuota in mezzo non cambiava niente: «Via Verdi
12, 40100 Bologna ⏎⏎ Allegato A» si portava via anche la «A».

Due danni, e il secondo e' peggiore del primo:

* una parola tolta dal documento. Non e' una fuga — non esce niente che
  doveva restare — ma e' un documento **corrotto**, e chi legge il confronto
  prima/dopo non ha modo di accorgersene: vede un segnaposto, non vede cosa
  c'era intorno;
* il segnale della firma **distrutto**. «Cordiali saluti» e' esattamente
  cio' che dichiara che quello che segue e' una persona, ed e' l'unico
  contesto in cui un cognome da solo vale come prova. Mangiando «Cordiali»
  si spegne un riconoscitore mentre se ne allarga un altro.

La causa era `\\s` invece di `[ \\t]` dentro il pattern: lo spazio dentro un
indirizzo e' **orizzontale**. E' lo stesso difetto gia' pagato nella 1.14.0
con l'email offuscata, e la stessa ragione per cui i nomi usano `_SP`.

Trovato per caso, costruendo un esempio prima/dopo da mostrare in pubblico —
il che dice qualcosa su quanto valga far girare il motore su un testo che
non e' un caso di prova.
"""
from __future__ import annotations

import pytest

from mr_rao.privacy import PrivacyOptions, apply_privacy_filter


def _redigi(testo: str) -> str:
    return apply_privacy_filter(testo, PrivacyOptions())[0]


@pytest.mark.parametrize("testo,deve_restare", [
    ("Via Roma 5, 20121 Milano\nCordiali saluti", "Cordiali saluti"),
    ("Via Verdi 12, 40100 Bologna\n\nAllegato A", "Allegato A"),
    ("Corso Italia\n\nOggetto: richiesta", "Oggetto: richiesta"),
    ("Via A. Volta 5, 20121 Milano\nAccount: 12345", "Account"),
    ("Piazza Dante 3\nIl Direttore firma", "Il Direttore firma"),
    ("Via Roma 5\n20121 Milano\nTelefono 02 1234567", "Telefono"),
])
def test_l_indirizzo_finisce_dove_finisce_la_riga(testo, deve_restare):
    fuori = _redigi(testo)
    assert "{{ADDRESS}}" in fuori, f"non ha nemmeno visto l'indirizzo: {fuori!r}"
    assert deve_restare in fuori, (
        f"si e' portato via del testo che non era suo: {fuori!r}"
    )


def test_la_firma_sopravvive_all_indirizzo_sopra():
    """Il caso che costa di piu': mangiando «Cordiali» si spegne il
    riconoscitore che sarebbe scattato sulla riga dopo."""
    fuori = _redigi("Via Roma\nCordiali saluti,\nMario Rossi")
    assert "Cordiali saluti" in fuori
    assert "{{NAME}}" in fuori and "Rossi" not in fuori


def test_il_cap_puo_stare_sulla_riga_dopo():
    """Un a capo solo si concede, perche' sulla carta intestata l'indirizzo
    si scrive proprio cosi'. Se questo test non ci fosse, il modo piu'
    semplice di far passare quelli sopra sarebbe vietare ogni a capo — e si
    perderebbero gli indirizzi scritti come li scrive tutto il mondo."""
    fuori = _redigi("Recapito:\nVia A. Volta 5\n20121 Milano")
    assert "{{ADDRESS}}" in fuori
    assert "20121" not in fuori and "Milano" not in fuori, fuori


# --- il civico che mordeva il CAP -------------------------------------------

@pytest.mark.parametrize("testo", [
    "sede in Piazza G. Verdi, 1 - 00198 Roma",
    "sede in via F. Barbarossa n. 7 - 26824 Cavenago",
    "recapito in Via Roma 3 - 40100 Bologna",
])
def test_il_suffisso_del_civico_non_morde_il_cap(testo):
    """«Piazza G. Verdi, 1 - 00198 Roma» prendeva «- 001» come suffisso del
    civico e lasciava indietro «98 Roma»: il CAP mozzato e tre cifre orfane
    in un documento che sembrava trattato.

    Era gia' passato sotto gli occhi nelle Gazzette Ufficiali durante la
    misura della 1.16.0, stampato a schermo, senza che nessuno lo guardasse.
    """
    fuori = _redigi(testo)
    assert fuori.count("{{ADDRESS}}") == 1
    for orfano in ("98 Roma", "24 Cavenago", "00 Bologna"):
        assert orfano not in fuori, f"pezzo di CAP rimasto indietro: {fuori!r}"


@pytest.mark.parametrize("testo", [
    "V.le Europa 12/A, 00144 Roma",
    "Via Roma 7-bis, 20121 Milano",
    "Via Verdi 3/1, 40100 Bologna",
])
def test_il_civico_con_il_suffisso_funziona_ancora(testo):
    """La controprova: la correzione sopra non doveva chiudere il suffisso
    del civico, che esiste davvero — «12/A», «7-bis», «3/1»."""
    assert _redigi(testo).strip() == "{{ADDRESS}}"
