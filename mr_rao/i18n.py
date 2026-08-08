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
    # ══════════════════════════════════════════════════════════════════
    # Testo che finisce DENTRO il Markdown prodotto.
    #
    # Non e' interfaccia, e' il documento: la lingua la porta il lavoro di
    # conversione (`ConvertOptions.lingua`), non la sessione del browser.
    # La cartella sorvegliata e la riga di comando scrivono lo stesso testo
    # senza avere nessuna richiesta HTTP intorno.
    # ══════════════════════════════════════════════════════════════════
    # -- intestazione delle email ---------------------------------------
    "doc_campo": {"it": "Campo", "en": "Field"},
    "doc_valore": {"it": "Valore", "en": "Value"},
    "doc_da": {"it": "Da", "en": "From"},
    "doc_a": {"it": "A", "en": "To"},
    "doc_cc": {"it": "CC", "en": "Cc"},
    "doc_data": {"it": "Data", "en": "Date"},
    "doc_allegati": {"it": "Allegati", "en": "Attachments"},
    "doc_ultimo_messaggio": {"it": "Ultimo messaggio", "en": "Latest message"},
    "doc_messaggio_precedente": {
        "it": "Messaggio precedente #{n}", "en": "Earlier message #{n}",
    },
    "doc_nessun_oggetto": {"it": "(nessun oggetto)", "en": "(no subject)"},
    "doc_mittente_sconosciuto": {
        "it": "(mittente sconosciuto)", "en": "(sender unknown)",
    },
    "doc_destinatario_sconosciuto": {
        "it": "(destinatario sconosciuto)", "en": "(recipient unknown)",
    },
    "doc_data_sconosciuta": {"it": "(data sconosciuta)", "en": "(date unknown)"},
    "doc_allegato_senza_nome": {
        "it": "(allegato senza nome)", "en": "(unnamed attachment)",
    },
    "doc_allegato_oltre": {"it": "oltre {n} MB", "en": "over {n} MB"},
    "doc_eml_senza_testo": {
        "it": "Nessun contenuto testuale trovato nel file .eml.",
        "en": "No text content found in the .eml file.",
    },
    "doc_nota_elaborazione": {
        "it": "Documento elaborato da Mr. Rao. Se il filtro privacy è attivo, "
              "i dati personali sono stati sostituiti con segnaposto.",
        "en": "Document processed by Mr. Rao. If the privacy filter is on, "
              "personal data has been replaced with placeholders.",
    },
    # -- OCR -------------------------------------------------------------
    "doc_tabelle_estratte": {"it": "Tabelle estratte", "en": "Extracted tables"},
    "doc_testo_ocr": {"it": "Testo OCR", "en": "OCR text"},
    "doc_pagina": {"it": "Pagina {n}", "en": "Page {n}"},
    "doc_tabella_pagina": {
        "it": "Tabella (pagina {n})", "en": "Table (page {n})",
    },
    "doc_tabella_pagina_indice": {
        "it": "Tabella (pagina {n}, #{k})", "en": "Table (page {n}, #{k})",
    },
    "doc_ocr_avviso": {
        "it": "Testo estratto tramite OCR (PDF scansionato o con poco testo nativo).",
        "en": "Text extracted with OCR (a scanned PDF, or one with little "
              "native text).",
    },
    "doc_ocr_troncato_titolo": {
        "it": "OCR interrotto dopo {n} pagine su {tot}:",
        "en": "OCR stopped after {n} pages out of {tot}:",
    },
    "doc_ocr_troncato_corpo": {
        "it": "superato il limite di tempo. Il testo qui sotto è **parziale**, e "
              "con esso la rimozione dei dati personali. Alza "
              "`MR_RAO_OCR_TIMEOUT` per completarlo.",
        "en": "the time limit was reached. The text below is **partial**, and so "
              "is the removal of personal data. Raise `MR_RAO_OCR_TIMEOUT` to "
              "finish it.",
    },
    "doc_avviso_ocr_privacy": {
        "it": "Testo ottenuto via OCR: l'anonimizzazione riconosce solo i dati "
              "letti correttamente. Se il riconoscimento ha sbagliato un "
              "carattere, un codice fiscale o un IBAN può essere sfuggito. "
              "**Controlla il confronto prima/dopo prima di condividere.**",
        "en": "Text obtained with OCR: anonymisation only catches data that was "
              "read correctly. If recognition got a character wrong, a codice "
              "fiscale or an IBAN may have slipped through. "
              "**Check the before/after comparison before sharing.**",
    },
    # -- quando non esce testo -------------------------------------------
    "doc_vuoto_titolo": {"it": "Nessun testo estratto.", "en": "No text extracted."},
    "doc_vuoto_corpo": {
        "it": "Il file caricato non contiene testo riconoscibile.",
        "en": "The uploaded file contains no recognisable text.",
    },
    "doc_vuoto_suggerimenti": {"it": "**Suggerimenti:**", "en": "**Suggestions:**"},
    "doc_vuoto_sugg_immagine": {
        "it": "Se è un'immagine, assicurati che il testo sia leggibile.",
        "en": "If it is an image, check that the text is legible.",
    },
    "doc_vuoto_sugg_pdf": {
        "it": "Se è un PDF, prova **Forza RapidOCR** o abilita le tabelle.",
        "en": "If it is a PDF, try **Force OCR** or turn table extraction on.",
    },
    "doc_vuoto_sugg_password": {
        "it": "Se è protetto da password, rimuovi la protezione prima.",
        "en": "If it is password-protected, remove the protection first.",
    },
    "doc_fallita_titolo": {
        "it": "Conversione non riuscita.", "en": "Conversion failed.",
    },
    "doc_fallita_coda": {
        "it": "Non dipende dal documento.", "en": "The document is not the problem.",
    },
    "doc_manca_libreria": {
        "it": "Manca la libreria **{pacchetto}**, necessaria per leggere i file "
              "`{ext}`. Installala con `pip install {pacchetto}`, oppure usa il "
              "pacchetto portable, che la contiene.",
        "en": "The **{pacchetto}** library is missing, and it is needed to read "
              "`{ext}` files. Install it with `pip install {pacchetto}`, or use "
              "the portable package, which already has it.",
    },
    # -- file che non si lascia leggere -----------------------------------
    "doc_file_bloccato_titolo": {
        "it": "Il file è aperto in un altro programma.",
        "en": "The file is open in another program.",
    },
    "doc_file_bloccato_corpo": {
        "it": "`{nome}` è bloccato — succede quando il documento è aperto in "
              "Word, Excel o PowerPoint.",
        "en": "`{nome}` is locked — that happens when the document is open in "
              "Word, Excel or PowerPoint.",
    },
    "doc_file_bloccato_azione": {
        "it": "**Chiudilo e riprova.**", "en": "**Close it and try again.**",
    },
    "doc_file_illeggibile_titolo": {
        "it": "Non riesco a leggere il file.", "en": "The file could not be read.",
    },
    "doc_file_illeggibile_corpo": {"it": "`{nome}`: {motivo}", "en": "`{nome}`: {motivo}"},
    "err_file_illeggibile": {
        "it": "Impossibile leggere il file: {motivo}",
        "en": "The file could not be read: {motivo}",
    },
    "err_annullata": {"it": "Conversione annullata", "en": "Conversion cancelled"},
    # -- unione e confronto ------------------------------------------------
    "doc_titolo_unificato": {"it": "Documento unificato", "en": "Merged document"},
    "doc_titolo_confronto": {"it": "Confronto documenti", "en": "Document comparison"},
    "doc_documento_a": {"it": "Documento A", "en": "Document A"},
    "doc_documento_b": {"it": "Documento B", "en": "Document B"},
    "doc_confronto_nota": {
        "it": "Confronto affiancato (stesso pipeline Mr. Rao su entrambi i file).",
        "en": "Side-by-side comparison (the same Mr. Rao pipeline on both files).",
    },
    "doc_errore": {"it": "Errore: {motivo}", "en": "Error: {motivo}"},
    # -- avanzamento, mentre la conversione lavora --------------------------
    "prog_email": {"it": "Parsing thread email…", "en": "Parsing email thread…"},
    "prog_ocr_immagine": {"it": "OCR immagine…", "en": "OCR on image…"},
    "prog_ocr_pdf": {"it": "OCR PDF…", "en": "OCR on PDF…"},
    "prog_documento": {"it": "Conversione documento…", "en": "Converting document…"},
    "prog_pdf_vuoto": {
        "it": "PDF vuoto o forzato OCR…", "en": "Empty PDF, or OCR forced…",
    },
    "prog_ocr_limite_pagine": {
        "it": "Limite {max} pagine OCR (PDF ne ha {totale})",
        "en": "OCR page limit is {max} (the PDF has {totale})",
    },
    "prog_ocr_limite_tempo": {
        "it": "Limite di tempo OCR a pagina {n}/{tot}",
        "en": "OCR time limit reached at page {n}/{tot}",
    },
    "prog_ocr_pagina": {"it": "OCR pagina {n}/{tot}…", "en": "OCR page {n}/{tot}…"},
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
