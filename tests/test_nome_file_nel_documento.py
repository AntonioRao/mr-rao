# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Il nome del file entra **dentro** il documento, e prima ci entrava in chiaro.

Il difetto
----------

Un documento si chiama come il suo contenuto: `Rossi_Mario_cartella_clinica.pdf`
e' il nome vero di un file vero, e in uno studio e' la regola, non l'eccezione.
Quel nome finisce in due posti che **viaggiano insieme al documento redatto**:

* il frontmatter, alla riga `source:`;
* le intestazioni del merge, dove ogni pezzo e' titolato col suo file.

Il resto del testo veniva ripulito e il nome no, quindi il Markdown consegnato
diceva il cognome nel primo rigo dopo aver tolto ogni occorrenza dal corpo. E'
la stessa forma dei metadati del PDF, chiusa nella 1.28.0: **testo che non
passa dalla strada in cui vive il filtro**.

Cosa **non** cambia
-------------------

Il nome del `.md` sul disco. Quello e' un file dell'utente sulla sua macchina,
e rinominarglielo sarebbe invadente senza proteggere nessuno: chi riceve il
documento riceve il contenuto, e da li' in poi il nome lo decide chi lo manda.
Il confine e' fra cio' che sta **dentro** il documento e cio' che sta intorno.

Il nome passa dallo **stesso** filtro del testo, con le stesse opzioni: se
l'utente ha spento i nomi, resta; se ha acceso tutto, sparisce come il resto.
Un secondo criterio sarebbe un secondo motore, e in un motore di redazione due
implementazioni sono una divergenza in attesa di succedere.

Tutti i valori sono inventati.
"""

from __future__ import annotations

from mr_rao.converter import (
    ConvertOptions,
    convert_bytes,
    merge_markdowns,
)

NOME = "Rossi_Mario_cartella_clinica.txt"
TESTO = b"Una riga qualunque, senza niente dentro."


def _converti(nome: str = NOME, **kw) -> object:
    return convert_bytes(TESTO, nome, options=ConvertOptions(**kw))


def test_il_frontmatter_non_dice_il_cognome(tmp_path):
    """La riga `source:` viaggia con il documento: e' testo consegnato."""
    esito = _converti()
    assert not esito.error, esito.error
    testa = esito.markdown.split("---")[1] if "---" in esito.markdown else esito.markdown
    assert "Rossi" not in testa, testa
    # Il resto del nome resta: serve a ritrovare il documento, e non e' un dato
    # personale. Togliere tutto il nome sarebbe una perdita senza guadagno.
    assert "cartella_clinica" in testa, testa


def test_il_titolo_del_merge_non_dice_il_cognome():
    """Ogni pezzo del merge e' titolato col suo file: stessa strada, stesso filtro."""
    a = _converti()
    b = _converti("Bianchi_Luigi_referto.txt")
    unito = merge_markdowns([a, b], title="Documento unificato")
    assert "Rossi" not in unito, unito
    assert "Bianchi" not in unito, unito
    assert "referto" in unito, "il merge ha perso il riferimento al secondo file"


def test_col_filtro_spento_il_nome_resta_com_e():
    """La riga che impedisce di «correggere» redigendo sempre.

    Chi spegne la redazione vuole il documento com'e', nome compreso: una
    sostituzione che avviene quando l'utente ha detto di no e' l'errore nella
    direzione peggiore.
    """
    from mr_rao.privacy import no_redaction

    esito = _converti(privacy=no_redaction())
    assert not esito.error, esito.error
    assert "Rossi_Mario_cartella_clinica" in esito.markdown


def test_un_nome_senza_dati_personali_non_viene_toccato():
    """La riga che impedisce di «correggere» buttando via il nome.

    Senza, il primo caso sarebbe verde anche sostituendo ogni `source:` con una
    costante, che e' peggio del difetto: si perderebbe il riferimento su ogni
    documento, compresi i milioni che non hanno un cognome nel nome.
    """
    esito = _converti("verbale_assemblea_2026.txt")
    assert not esito.error, esito.error
    assert "verbale_assemblea_2026" in esito.markdown
