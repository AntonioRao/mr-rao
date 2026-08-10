"""I workflow di CI devono riferirsi a cose che esistono.

Un filtro `paths:` che nomina un file sbagliato non protesta: il workflow
semplicemente non parte mai. E' il modo peggiore di rompersi, perche' la
scheda Actions resta verde e il controllo che credi di avere non c'e'.

Lo stesso vale per il comando: un `run:` che punta a uno script inesistente
fallisce, ma solo quando qualcuno lo lancia -- e se il trigger e' un filtro
che non scatta mai, non lo lancia nessuno.

Questi test costano niente e coprono l'unico modo in cui una configurazione
di CI puo' mentire in silenzio.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

RADICE = Path(__file__).resolve().parents[1]
WORKFLOWS = sorted((RADICE / ".github" / "workflows").glob("*.yml"))


def carica(percorso: Path) -> dict:
    return yaml.safe_load(percorso.read_text(encoding="utf-8"))


def trigger(config: dict) -> dict:
    # In YAML `on:` e' il booleano vero, non la stringa "on": e' la
    # sorpresa classica di chi legge un workflow con un parser generico.
    return config.get(True) or config.get("on") or {}


def test_ci_sono_workflow_da_controllare():
    assert WORKFLOWS, "nessun workflow trovato: gli altri test passerebbero a vuoto"


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_il_workflow_e_yaml_valido(workflow):
    config = carica(workflow)
    assert config.get("jobs"), f"{workflow.name} non definisce nessun job"


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_i_percorsi_del_filtro_esistono(workflow):
    """Un `paths:` con un nome sbagliato non scatta mai, e non lo dice."""
    push = trigger(carica(workflow)).get("push") or {}
    mancanti = []
    for schema in push.get("paths", []):
        if any(c in schema for c in "*?["):
            if not list(RADICE.glob(schema)):
                mancanti.append(schema)
        elif not (RADICE / schema).exists():
            mancanti.append(schema)
    assert not mancanti, (
        f"{workflow.name}: il filtro paths nomina {mancanti}, che non esistono. "
        f"Il workflow non partirebbe mai, e la scheda Actions resterebbe verde"
    )


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_gli_script_lanciati_esistono(workflow):
    """Cerca i `run:` che invocano uno script del repository."""
    testo = workflow.read_text(encoding="utf-8")
    mancanti = [
        s
        for s in re.findall(r"run:\s+(scripts[\\/][\w.\\/-]+)", testo)
        if not (RADICE / s.replace("\\", "/")).is_file()
    ]
    assert not mancanti, f"{workflow.name} lancia {mancanti}, che non esistono"


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_nessuna_azione_su_node_20(workflow):
    """checkout@v4 e setup-python@v5 giravano su Node 20, che i runner ora
    forzano su Node 24 stampando un avviso di deprecazione a ogni
    esecuzione. Un avviso fisso in cima al log insegna a non leggere il
    log, ed e' proprio il log che ci ha fatto trovare il difetto delle
    dipendenze Office."""
    vecchie = re.findall(
        r"uses:\s+(actions/(?:checkout@v[1-4]|setup-python@v[1-5]|upload-artifact@v[1-4]|download-artifact@v[1-4]))",
        workflow.read_text(encoding="utf-8"),
    )
    assert not vecchie, f"{workflow.name} usa azioni su Node 20: {vecchie}"


def test_la_ci_importa_i_moduli_e_non_si_ferma_alla_sintassi():
    """P2.7. `compileall` dice che il file e' scritto in Python, non che si
    carica: un import circolare o un nome sparito lo superano e rompono
    l'applicazione all'avvio. E' gia' successo di committarne uno rotto.

    Il passo si controlla qui e non solo nel gate locale perche' il gate
    locale gira dove il difetto e' gia' successo: se qualcuno toglie la riga
    dal workflow, l'unico posto che se ne accorge e' questo."""
    ci = RADICE / ".github" / "workflows" / "ci.yml"
    config = carica(ci)
    passi = config["jobs"]["test"]["steps"]
    comandi = [str(p.get("run", "")) for p in passi]
    testo = " ".join(comandi)

    assert "check_import.py" in testo, "la CI non importa niente, compila e basta"
    assert (RADICE / "scripts" / "check_import.py").is_file()

    # L'ordine conta: con entrambi rotti si vuole leggere prima l'errore di
    # sintassi, che e' quello che spiega l'altro.
    indice = [i for i, c in enumerate(comandi) if "check_import.py" in c][0]
    prima = " ".join(comandi[:indice])
    assert "compileall" in prima, "l'import check deve venire dopo compileall"


def test_il_pacchetto_si_costruisce_in_ci():
    """P2.9. Il gate locale gira sulla stessa macchina che ha il problema:
    non puo' accorgersi di una libreria presente solo nel venv di sviluppo.
    Questo lavoro parte senza venv, e se sparisce sparisce anche l'unico
    controllo che ha quella proprieta'."""
    portable = RADICE / ".github" / "workflows" / "portable.yml"
    assert portable.is_file(), "manca il workflow che costruisce il pacchetto"
    config = carica(portable)
    eventi = trigger(config)
    assert "workflow_dispatch" in eventi, "deve potersi lanciare a mano prima di una release"
    # Nessuna asserzione su push/schedule: finche' il build non e' passato
    # almeno una volta su un runner GitHub sta apposta solo a mano, e un
    # test che pretendesse gli automatismi spingerebbe ad accenderli prima
    # di sapere se funziona.

    passi = config["jobs"]["build"]["steps"]
    comandi = " ".join(str(p.get("run", "")) for p in passi)
    assert "build_portable.bat" in comandi
    # Installare le dipendenze fuori dallo script ricreerebbe l'ambiente
    # preparato a mano che questo lavoro serve a escludere.
    assert "pip install" not in comandi, (
        "le dipendenze le deve installare lo script, nel venv che crea lui"
    )


# --- Firma Sigstore del pacchetto -----------------------------------------


def _portable() -> dict:
    return carica(RADICE / ".github" / "workflows" / "portable.yml")["jobs"]["build"]


def test_il_pacchetto_viene_firmato():
    """Senza il passo di firma non c'e' niente da verificare, e la riga nei
    README che spiega come verificare diventerebbe una promessa a vuoto."""
    usi = [p.get("uses", "") for p in _portable()["steps"]]
    assert any("attest-build-provenance" in u for u in usi), usi


def test_i_permessi_per_sigstore_ci_sono():
    """`id-token` e' cio' che rende la firma senza chiavi: il runner scambia
    un token OIDC di breve durata con un certificato usa-e-getta. Senza,
    il passo di firma fallisce -- ed e' il genere di cosa che si scopre a
    release in corso."""
    permessi = _portable()["permissions"]
    assert permessi.get("id-token") == "write"
    assert permessi.get("attestations") == "write"


def test_la_pubblicazione_non_avviene_da_sola():
    """`contents: write` sta li' per allegare i file a una release. Deve
    esistere un solo percorso che lo usa, e deve passare da una scelta
    esplicita di chi lancia: una release che cambia da sola non e' un
    automatismo, e' una sorpresa."""
    passi = [p for p in _portable()["steps"] if "gh release" in str(p.get("run", ""))]
    assert len(passi) == 1, passi
    assert passi[0].get("if") == "inputs.pubblica != ''"


def test_alla_release_finiscono_tutti_gli_allegati():
    """Erano tre, da quando c'e' l'installer sono cinque.

    Questo passo ne caricava due: l'archivio versionato era rimasto fuori da
    quando e' entrato (P3.4).

    I due nomi non sono ridondanti, e vale per **tutte e due** le confezioni
    scaricabili. Quello **fisso** e' l'unica cosa che fa funzionare
    `/releases/latest/download/...`, cioe' i pulsanti nei due README e nelle
    due landing: se manca, quei link danno 404 e non lo dice nessuno. Quello
    **versionato** e' cio' che resta riconoscibile nella cartella Download di
    chi scarica.

    L'MSIX non deve esserci: non e' firmato, e uno scaricato da qui non si
    installa. Va allo Store, che e' l'unico posto in cui quel pacchetto ha
    un senso.
    """
    (passo,) = [p for p in _portable()["steps"] if "gh release" in str(p.get("run", ""))]
    comando = str(passo["run"])
    assert "dist/MrRao-Portable.zip" in comando, "manca l'archivio a nome fisso"
    assert "dist/MrRao-Portable-*.zip" in comando, "manca l'archivio versionato"
    assert "dist/MrRaoSetup.exe" in comando, "manca l'installer a nome fisso"
    assert "dist/MrRaoSetup-*.exe" in comando, "manca l'installer versionato"
    assert "SHA256SUMS.txt" in comando, "mancano le impronte"
    assert ".msix" not in comando, "l'MSIX non firmato non va allegato alla release"


def test_l_attestazione_copre_ogni_confezione():
    """La provenienza vale per cio' che si scarica, non per una parte.

    L'attestazione Sigstore e' l'unica risposta che questo progetto puo' dare
    a «da dove viene questo file»: non c'e' un certificato di code signing, e
    il README ci manda esplicitamente (`gh attestation verify`). Una
    confezione lasciata fuori dall'elenco e' una confezione su cui quel
    comando risponde che non ne sa niente -- proprio la piu' nuova, cioe'
    quella su cui Windows fara' l'avviso piu' spaventoso.
    """
    passi = [p for p in _portable()["steps"] if "attest-build-provenance" in str(p.get("uses", ""))]
    assert len(passi) == 1, passi
    soggetti = str(passi[0]["with"]["subject-path"])
    for atteso in ("MrRao-Portable*.zip", "MrRao-*.msix", "MrRaoSetup*.exe"):
        assert atteso in soggetti, f"{atteso} non e' fra i file attestati"


def test_le_licenze_del_pacchetto_pubblicato_non_sono_saltate():
    """Il controllo delle licenze era disattivato qui, e andava bene finche'
    il pacchetto serviva solo a dire si'/no. Da quando viene firmato e
    pubblicato, distribuire un THIRD_PARTY.md che non descrive cio' che c'e'
    dentro e' un problema di licenze -- pystray e' LGPL."""
    testo = (RADICE / ".github" / "workflows" / "portable.yml").read_text(encoding="utf-8")
    passi = [p.get("name", "") for p in _portable()["steps"]]
    assert any("icenze" in n for n in passi), passi
    assert "MR_RAO_GATE_NO_LICENCE_CHECK: " not in testo, (
        "il controllo delle licenze e' di nuovo disattivato nel workflow"
    )


# --- Pubblicazione sul Microsoft Store -------------------------------------


def test_lo_store_non_pubblica_da_solo():
    """Ogni passo che parla con lo Store dev'essere dietro una scelta
    esplicita di chi lancia. Una release che parte per conto suo non e' un
    automatismo, e' una sorpresa -- e sullo Store non si annulla con un
    `git revert`."""
    passi = [
        p for p in _portable()["steps"]
        if "msstore" in str(p.get("run", "")) or "store-apppublisher" in p.get("uses", "")
    ]
    assert passi, "non trovo i passi di pubblicazione sullo Store"
    for p in passi:
        assert p.get("if") == "inputs.pubblica_store != ''", (
            f"il passo «{p.get('name') or p.get('uses')}» pubblica senza interruttore"
        )


def test_i_segreti_si_controllano_prima_di_pubblicare():
    """Un segreto mancante, senza questo, diventa un errore di
    autenticazione a meta' della pubblicazione: il punto peggiore in cui
    scoprirlo."""
    passi = _portable()["steps"]
    nomi = [p.get("name", "") for p in passi]
    indice_controllo = next(i for i, n in enumerate(nomi) if "segreti" in n.lower())
    indice_invio = next(i for i, n in enumerate(nomi) if "allo Store" in n)
    assert indice_controllo < indice_invio, "il controllo arriva dopo l'invio"


def test_i_segreti_hanno_i_nomi_che_il_documento_dichiara():
    """Il workflow e docs/STORE.md devono nominare gli stessi segreti: un
    nome diverso fra i due si scopre solo pubblicando."""
    import re

    testo = (RADICE / ".github" / "workflows" / "portable.yml").read_text(encoding="utf-8")
    doc = (RADICE / "docs" / "STORE.md").read_text(encoding="utf-8")
    usati = set(re.findall(r"secrets\.([A-Z_]+)", testo))
    assert usati, "il workflow non usa nessun segreto"
    for nome in usati:
        if nome == "GITHUB_TOKEN":
            continue
        assert nome in doc, f"il segreto {nome} non e' documentato in docs/STORE.md"
