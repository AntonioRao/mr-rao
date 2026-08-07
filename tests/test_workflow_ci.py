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
