# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Gli allegati di una email escono **come sono entrati**, e adesso lo dicono.

Il difetto, che non e' una fuga ma una frase mancante
-----------------------------------------------------

Un `.eml` porta con se' i suoi allegati, e l'interfaccia li offre in scarico.
Quei file **non passano dal filtro**: sono binari di ogni formato, e Mr. Rao
non sa redigere un `.xlsx` senza convertirlo. Fin qui e' un limite, non un
difetto.

Il difetto e' che non lo diceva. Il documento esce redatto, l'allegato esce
dallo stesso pannello dello stesso programma, e chi lo prende ha tutte le
ragioni di credere che sia stato trattato come il resto — nessuno mette un
avviso in testa a un file che ha appena scaricato da uno strumento di
anonimizzazione. Consegnarlo a un terzo e' la cosa naturale da fare, ed e'
esattamente la cosa che questo programma esiste per non far succedere per
sbaglio.

La risposta non e' redigerli — sarebbe una promessa che il motore non puo'
mantenere su ogni formato — ma **nominare il limite dove l'utente lo incontra**,
cioe' accanto ai bottoni.

Il nome dell'allegato
---------------------

`get_filename()` restituisce quello che c'e' scritto nella mail, e chi manda
la mail non e' dalla nostra parte: puo' esserci un percorso, dei separatori,
dei caratteri di controllo. Finiva nell'attributo `download` di un link. I
browser si difendono da soli, ma «si difende il browser» non e' una difesa
nostra, e il giorno che quel nome finisce in un altro posto — un log, una
cartella — la difesa non c'e' piu'.

Tutti i valori sono inventati.
"""

from __future__ import annotations

from pathlib import Path

from mr_rao.eml_parser import extract_attachments

EML = """\
From: Mario Rossi <mario.rossi@example.it>
To: destinatario@example.it
Subject: Con allegato
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="LIMITE"

--LIMITE
Content-Type: text/plain; charset="utf-8"

Il corpo del messaggio.

--LIMITE
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="{nome}"
Content-Transfer-Encoding: base64

Y29udGVudXRvIGRpIHByb3Zh

--LIMITE--
"""


def _eml(tmp_path: Path, nome: str) -> Path:
    percorso = tmp_path / "messaggio.eml"
    percorso.write_text(EML.format(nome=nome), encoding="utf-8")
    return percorso


def test_il_nome_dell_allegato_non_porta_un_percorso(tmp_path):
    """Chi scrive la mail sceglie quel nome, e non e' dalla nostra parte."""
    allegati = extract_attachments(_eml(tmp_path, "../../../etc/passwd"))
    assert len(allegati) == 1, allegati
    nome = allegati[0]["filename"]
    assert "/" not in nome and "\\" not in nome, nome
    assert ".." not in nome, nome
    assert nome, "il nome non deve restare vuoto: serve un ripiego"


def test_un_nome_normale_resta_quello_che_e(tmp_path):
    """La riga che impedisce di «correggere» buttando via ogni nome.

    Senza, il caso qui sopra sarebbe verde anche chiamando ogni allegato
    `allegato.bin`, e chi ne scarica tre non saprebbe piu' quale e' quale.
    """
    allegati = extract_attachments(_eml(tmp_path, "contratto firmato.pdf"))
    assert allegati[0]["filename"] == "contratto firmato.pdf"


def test_i_caratteri_di_controllo_spariscono(tmp_path):
    """Un a capo dentro un nome di file e' una riga in piu' in ogni registro
    che quel nome attraversa."""
    allegati = extract_attachments(_eml(tmp_path, "nota\r\nriservata.pdf"))
    nome = allegati[0]["filename"]
    assert "\n" not in nome and "\r" not in nome, repr(nome)


# ------------------------------------------------ il limite si dice all'utente


def test_la_pagina_dice_che_gli_allegati_non_sono_redatti():
    """La frase esiste nelle due lingue **ed e' usata**.

    Una frase presente solo nel dizionario non la legge nessuno; una usata
    solo nel codice esce come il nome della sua chiave. Servono tutte e due.
    """
    from mr_rao.i18n import TESTI

    voce = TESTI.get("js_allegati_non_redatti")
    assert voce, "manca la frase che dichiara il limite"
    for lingua in ("it", "en"):
        assert len(voce.get(lingua, "")) > 30, (lingua, voce)
    # In italiano deve dirsi che **non** sono stati toccati: e' la meta' del
    # messaggio che conta, e una traduzione che la perde svuota l'avviso.
    assert "non" in voce["it"].lower()

    js = Path("static/js/app.js").read_text(encoding="utf-8")
    assert "js_allegati_non_redatti" in js, "il pannello non mostra la frase"
