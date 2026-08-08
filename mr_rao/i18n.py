"""Le due lingue dell'interfaccia.

Un dizionario Python, non gettext. Le ragioni sono tre e sono tutte
vincoli di questo progetto, non preferenze:

1. **Non c'e' un passo di compilazione.** Il pacchetto si costruisce con
   PyInstaller; i `.mo` di gettext andrebbero compilati, committati come
   binari (illeggibili in diff, disallineabili in silenzio dai `.po`) e
   dichiarati a mano nello `.spec`. Un `.py` PyInstaller lo raccoglie da
   solo.
2. **La lingua serve anche fuori dal browser.** Il testo che finisce
   *dentro* il Markdown prodotto -- intestazioni delle email, «Tabelle
   estratte», l'avviso sull'OCR -- lo scrivono thread che un contesto di
   richiesta Flask non ce l'hanno: la cartella sorvegliata e la riga di
   comando. `gettext` risolve la lingua per contesto di richiesta, quindi
   li' non funzionerebbe.
3. **Due lingue e poche centinaia di chiavi** non ripagano un framework.

## La regola che vale piu' di tutte

La lingua dell'interfaccia **non sceglie i riconoscitori**. Uno studio
italiano che tiene la pagina in inglese converte comunque fatture
italiane, e togliergli il codice fiscale senza dirglielo sarebbe un
peggioramento silenzioso della protezione. La lingua *propone* i
pacchetti; le caselle restano indipendenti.

E i **segnaposto non si traducono**: `{{CODICE_FISCALE}}` resta tale anche
in inglese. Nominano lo strumento, non l'interfaccia -- `{{NHS_NUMBER}}` e
`{{NINO}}` sono gia' inglesi, `{{IBAN}}` non e' di nessuna lingua. Chi
confronta due documenti prodotti in sessioni diverse deve vedere le stesse
etichette, e chi ha uno script che cerca `{{CODICE_FISCALE}}` non deve
scoprire che dipendeva da un menu a tendina.
"""
from __future__ import annotations

LINGUE = ("it", "en")
LINGUA_PREDEFINITA = "it"

# Chiave -> {lingua: testo}. Tenerle insieme invece che in due file
# separati serve a una cosa: una traduzione che manca si vede leggendo,
# non eseguendo.
TESTI: dict[str, dict[str, str]] = {
    # -- intestazione e promessa -------------------------------------
    "titolo_pagina": {
        "it": "{app} — Documenti in Markdown",
        "en": "{app} — Documents into Markdown",
    },
    "sottotitolo": {
        "it": "Converti documenti, immagini e thread email in Markdown puro.",
        "en": "Turn documents, images and email threads into plain Markdown.",
    },
    "sottotitolo_forte": {
        "it": "Con i dati personali già rimossi.",
        "en": "With the personal data already stripped out.",
    },
    "sottotitolo_coda": {
        "it": "Offline, sul tuo computer.",
        "en": "Offline, on your own machine.",
    },
    # -- passi ---------------------------------------------------------
    "passo_carica": {"it": "Carica", "en": "Load"},
    "passo_imposta": {"it": "Imposta", "en": "Set up"},
    "passo_risultato": {"it": "Risultato", "en": "Result"},
    "passo_extra": {"it": "Extra", "en": "Extras"},
    # -- caricamento ---------------------------------------------------
    "trascina_qui": {"it": "Trascina qui i file", "en": "Drop your files here"},
    "trascina_sotto": {
        "it": "oppure clicca per sceglierli · anche più file insieme · "
              "incolla un'immagine con Ctrl+V",
        "en": "or click to pick them · several at once is fine · "
              "paste an image with Ctrl+V",
    },
    "conversione_in_corso": {"it": "Conversione in corso…", "en": "Converting…"},
    "annulla": {"it": "Annulla", "en": "Cancel"},
    # -- pacchetti e tipo di documento ---------------------------------
    "gruppo_pacchetti": {
        "it": "Formati di quale Paese", "en": "Which country's formats",
    },
    "pack_it_titolo": {"it": "Formati italiani", "en": "Italian formats"},
    "pack_it_desc": {
        "it": "Codice fiscale, P.IVA, BBAN, vie, nomi",
        "en": "Codice fiscale, VAT number, BBAN, streets, names",
    },
    "pack_en_titolo": {"it": "Formati anglosassoni", "en": "English-speaking formats"},
    "pack_en_desc": {
        "it": "SSN, NINO, NHS, passaporti, vie inglesi",
        "en": "SSN, NINO, NHS, passports, English streets",
    },
    "tipo_documento": {"it": "Tipo di documento", "en": "Document type"},
    "tipo_auto": {"it": "Automatico (consigliato)", "en": "Automatic (recommended)"},
    "tipo_prosa": {
        "it": "Lettera, email, contratto", "en": "Letter, email, contract",
    },
    "tipo_modulo": {
        "it": "Modulo, verbale, prospetto", "en": "Form, minutes, schedule",
    },
    # -- risultato -----------------------------------------------------
    "gruppo_nascondere": {"it": "Quali dati nascondere", "en": "What to hide"},
    "copia": {"it": "Copia", "en": "Copy"},
    "copia_pulita": {"it": "Copia solo il testo", "en": "Copy text only"},
    "scarica_md": {"it": "Scarica .md", "en": "Download .md"},
    "scheda_testo": {"it": "Testo Markdown", "en": "Markdown text"},
    "scheda_anteprima": {"it": "Anteprima", "en": "Preview"},
    "scheda_confronto": {"it": "Confronto privacy", "en": "Privacy comparison"},
    # -- il contatore, con il plurale ----------------------------------
    "redazioni_una": {"it": "{n} redazione", "en": "{n} redaction"},
    "redazioni_molte": {"it": "{n} redazioni", "en": "{n} redactions"},
    "sospetti_uno": {"it": "{n} da controllare", "en": "{n} to review"},
    "sospetti_molti": {"it": "{n} da controllare", "en": "{n} to review"},
    # -- errori --------------------------------------------------------
    "err_nessun_file": {"it": "Nessun file selezionato", "en": "No file selected"},
    "err_file_vuoto": {"it": "File vuoto", "en": "Empty file"},
    "err_troppo_grande": {"it": "File troppo grande", "en": "File too large"},
    "err_job_assente": {"it": "Job non trovato", "en": "Job not found"},
    "err_conversione": {
        "it": "Errore durante la conversione. Controlla il file e riprova.",
        "en": "Error during conversion. Check the file and try again.",
    },
    "err_file_bloccato": {
        "it": "Il file è aperto in un altro programma: chiudilo e riprova.",
        "en": "The file is open in another program: close it and try again.",
    },
    "err_server_irraggiungibile": {
        "it": "Impossibile contattare Mr. Rao. Verifica che il server sia avviato.",
        "en": "Can't reach Mr. Rao. Check that the server is running.",
    },
}


def t(chiave: str, lingua: str = LINGUA_PREDEFINITA, **campi) -> str:
    """Il testo nella lingua chiesta, con i segnaposto sostituiti.

    Se la chiave non esiste torna la chiave stessa invece di sollevare:
    una stringa mancante deve produrre un'interfaccia brutta, non una
    pagina di errore. Il test sulle chiavi la trova prima che ci arrivi
    un utente.
    """
    voce = TESTI.get(chiave)
    if voce is None:
        return chiave
    testo = voce.get(lingua) or voce.get(LINGUA_PREDEFINITA, chiave)
    return testo.format(**campi) if campi else testo


def plurale(base: str, n: int, lingua: str = LINGUA_PREDEFINITA) -> str:
    """Singolare e plurale. «1 redazioni» e' sbagliato in entrambe le
    lingue, e oggi lo scriviamo in tre punti diversi."""
    suffisso = "_una" if n == 1 else "_molte"
    if base + suffisso not in TESTI:
        suffisso = "_uno" if n == 1 else "_molti"
    return t(base + suffisso, lingua, n=n)


def lingua_da(accept_language: str | None, cookie: str | None = None,
              query: str | None = None) -> str:
    """Quale lingua mostrare, in ordine di precedenza.

    La scelta esplicita vince sempre: chi ha cliccato il selettore ha
    detto qualcosa di piu' preciso di quanto dica il suo browser.
    L'italiano solo se il browser lo chiede davvero; per tutto il resto
    del mondo l'inglese e' la scelta piu' utile.
    """
    for candidato in (query, cookie):
        if candidato and candidato.strip().lower() in LINGUE:
            return candidato.strip().lower()
    if accept_language and accept_language.strip().lower().startswith("it"):
        return "it"
    return "en" if accept_language else LINGUA_PREDEFINITA
