"""Il manifesto MSIX per il Microsoft Store.

Il pacchetto dello Store e quello portable sono due confezioni dello stesso
programma, ma si integrano col sistema in due modi diversi: il portable
scrive le voci di menu nel registro (`scripts/mr_rao_shell.ps1`), l'MSIX le
**dichiara** nel manifesto e le lascia applicare a Windows.

Due liste della stessa cosa in due file diversi vanno fuori sincrono: e'
gia' successo in questo repository, quando l'elenco delle estensioni viveva
in due script e la disinstallazione lasciava voci che puntavano a un
eseguibile non piu' esistente. Qui non si possono unire — sono due formati
diversi — quindi almeno si confrontano.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]
MANIFESTO = RADICE / "packaging" / "AppxManifest.xml"
SHELL = RADICE / "scripts" / "mr_rao_shell.ps1"

NS = {
    "m": "http://schemas.microsoft.com/appx/manifest/foundation/windows10",
    "uap": "http://schemas.microsoft.com/appx/manifest/uap/windows10",
}


def albero() -> ET.ElementTree:
    return ET.parse(MANIFESTO)


def test_il_manifesto_e_xml_valido():
    """Un manifesto malformato lo scopre `MakeAppx` in CI, venti minuti dopo."""
    assert MANIFESTO.is_file()
    albero()


def estensioni_manifesto() -> set[str]:
    return {
        e.text.strip().lower()
        for e in albero().getroot().iter(f"{{{NS['uap']}}}FileType")
        if e.text
    }


def estensioni_shell() -> set[str]:
    testo = SHELL.read_text(encoding="utf-8")
    blocco = re.search(r"\$Estensioni\s*=\s*@\((.*?)\)", testo, re.S)
    assert blocco, "non trovo l'elenco delle estensioni in mr_rao_shell.ps1"
    return {e.lower() for e in re.findall(r"'(\.[a-z0-9]+)'", blocco.group(1), re.I)}


def test_le_due_liste_di_estensioni_coincidono():
    """Se il tasto destro apre un .pdf nel portable ma non nello Store, la
    differenza la scopre un utente, non noi."""
    solo_shell = estensioni_shell() - estensioni_manifesto()
    solo_manifesto = estensioni_manifesto() - estensioni_shell()
    assert not solo_shell, f"nel portable ma non nell'MSIX: {sorted(solo_shell)}"
    assert not solo_manifesto, f"nell'MSIX ma non nel portable: {sorted(solo_manifesto)}"


def test_l_identita_e_quella_assegnata_dallo_store():
    """Questi tre valori non si inventano: li assegna lo Store. Un pacchetto
    con un'identita' diversa viene rifiutato dalla certificazione senza
    spiegare granche', e la diagnosi costa un giro completo."""
    identita = albero().getroot().find("m:Identity", NS)
    assert identita.get("Name") == "AntonioAndreaRao.Mr.Rao"
    assert identita.get("Publisher", "").startswith("CN=")
    proprieta = albero().getroot().find("m:Properties", NS)
    assert proprieta.find("m:PublisherDisplayName", NS).text == "Antonio Andrea Rao"


def test_la_versione_ha_l_ultimo_campo_a_zero():
    """Lo Store riserva a se' il quarto numero e rifiuta i pacchetti che lo
    usano. E' una regola che non si scopre leggendo: si scopre a invio
    respinto."""
    versione = albero().getroot().find("m:Identity", NS).get("Version")
    parti = versione.split(".")
    assert len(parti) == 4, versione
    assert parti[3] == "0", f"l'ultimo campo deve essere 0, e' {versione}"


def test_la_versione_del_manifesto_segue_quella_del_programma():
    from config import APP_VERSION

    versione = albero().getroot().find("m:Identity", NS).get("Version")
    assert versione == f"{APP_VERSION}.0", (
        f"manifesto {versione}, programma {APP_VERSION}"
    )


def test_non_chiede_autorizzazioni_di_rete():
    """Mr. Rao apre un server su localhost e non chiama nessuno.

    La scheda dello Store mostra a chi installa le autorizzazioni richieste:
    chiederne una di rete contraddirebbe la sola cosa che questo programma
    promette, e la contraddirebbe nel punto in cui la gente decide se
    fidarsi.
    """
    # Si guardano le capability **dichiarate**, non il testo del file: la
    # prima stesura di questo test cercava la stringa nel sorgente e
    # inciampava nel commento che spiega perche' non la chiediamo. Un
    # commento non e' una dichiarazione, e un test che non sa distinguerli
    # fallisce sulla prova migliore che gli si possa dare.
    radice = albero().getroot()
    dichiarate = {
        c.get("Name")
        for c in radice.iter()
        if c.tag.endswith("Capability")
    }
    vietate = {"internetClient", "internetClientServer", "privateNetworkClientServer"}
    assert not (dichiarate & vietate), f"il manifesto chiede {dichiarate & vietate}"
    assert "runFullTrust" in dichiarate


def test_il_manifesto_punta_all_eseguibile_del_pacchetto():
    app = albero().getroot().find("m:Applications/m:Application", NS)
    assert app.get("EntryPoint") == "Windows.FullTrustApplication"
    assert app.get("Executable", "").endswith("MrRao.exe")
