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
    # La pagina.
    #
    # Alcuni di questi testi **descrivono i riconoscitori**, e li' la
    # traduzione letterale direbbe una bugia: se il suggerimento inglese
    # dicesse «a title in front (Dr., Eng.)» mentre il pacchetto italiano
    # cerca `Dott.` e `Ing.`, l'interfaccia starebbe dichiarando il falso
    # su cio' che il programma fa. Dove succede, l'inglese nomina
    # *entrambi* i pacchetti o descrive il comportamento invece delle
    # parole chiave. Sono segnati uno per uno qui sotto.
    #
    # Le virgolette basse italiane «…» diventano "…" in inglese.
    # ══════════════════════════════════════════════════════════════════
    "meta_descrizione": {
        "it": "Mr. Rao converte documenti, immagini e email in Markdown. "
              "100% offline, OCR, privacy IT.",
        "en": "Mr. Rao turns documents, images and email into Markdown. "
              "100% offline, OCR, personal data removed.",
    },
    # -- pastiglie sotto il titolo ---------------------------------------
    "pill_offline": {"it": "Offline", "en": "Offline"},
    "pill_anonimizza": {
        "it": "Anonimizza nomi · indirizzi · codici",
        "en": "Hides names · addresses · codes",
    },
    "pill_formati": {"it": "PDF · DOCX · XLSX", "en": "PDF · DOCX · XLSX"},
    "pill_ocr": {"it": "OCR", "en": "OCR"},
    "pill_eml": {"it": "Thread .eml", "en": ".eml threads"},
    # -- 1. carica --------------------------------------------------------
    "aria_carica_file": {"it": "Carica file", "en": "Load files"},
    "tip_dropzone": {
        "it": "Trascina qui uno o più file, oppure clicca per sceglierli. "
              "Funziona anche da tastiera con Invio, e con <b>Ctrl+V</b> per "
              "incollare un'immagine copiata (uno screenshot, per esempio).",
        "en": "Drop one or more files here, or click to pick them. It works "
              "from the keyboard too, with Enter, and with <b>Ctrl+V</b> to "
              "paste a copied image (a screenshot, say).",
    },
    "tip_annulla": {
        "it": "Interrompe la conversione in corso. Su un file singolo già "
              "avviato può volerci qualche istante prima che si fermi davvero.",
        "en": "Stops the conversion. On a single file already under way it can "
              "take a moment before it really stops.",
    },
    # -- 2. imposta -------------------------------------------------------
    "etichetta_profilo": {"it": "Profilo", "en": "Profile"},
    "tip_profilo_etichetta": {
        "it": "Una combinazione già pronta di tutte le opzioni. Scegli il "
              "profilo che assomiglia al tuo lavoro e non pensare al resto: se "
              "serve puoi ritoccare le singole voci in «Opzioni avanzate».",
        "en": "A ready-made combination of every option. Pick the profile that "
              "looks like your work and forget the rest: you can still adjust "
              "individual settings under \"Advanced options\".",
    },
    "tip_profilo_scelte": {
        "it": "<b>Predefinito</b> — buono per quasi tutto.<br>"
              "<b>Email legali</b> — massima protezione dei dati personali, "
              "testo pulito.<br>"
              "<b>Fatture</b> — tiene le tabelle e lascia visibili gli importi.<br>"
              "<b>Solo OCR</b> — per scansioni e foto di documenti.<br>"
              "<b>Pronto per LLM</b> — testo da incollare in un assistente AI.<br>"
              "<b>Nessuna redazione</b> — testo integrale, niente sostituzioni.",
        "en": "<b>Default</b> — good for almost everything.<br>"
              "<b>Legal email</b> — strongest protection of personal data, "
              "cleaned-up text.<br>"
              "<b>Invoices</b> — keeps the tables and leaves the figures "
              "visible.<br>"
              "<b>OCR only</b> — for scans and photographs of documents.<br>"
              "<b>LLM-ready</b> — text to paste into an AI assistant.<br>"
              "<b>No redaction</b> — the whole text, nothing replaced.",
    },
    "profilo_default": {"it": "Predefinito", "en": "Default"},
    "profilo_email_legali": {"it": "Email legali", "en": "Legal email"},
    "profilo_solo_ocr": {"it": "Solo OCR", "en": "OCR only"},
    "profilo_llm_ready": {"it": "Pronto per LLM", "en": "LLM-ready"},
    "profilo_no_privacy": {"it": "Nessuna redazione", "en": "No redaction"},
    "hint_profilo_default": {
        "it": "Va bene per quasi tutto: dati personali protetti, tabelle estratte.",
        "en": "Fine for almost everything: personal data protected, tables "
              "extracted.",
    },
    "hint_profilo_email_legali": {
        "it": "Massima protezione dei dati; testo ripulito, pronto da condividere.",
        "en": "Strongest protection; text cleaned up, ready to share.",
    },
    "hint_profilo_solo_ocr": {
        "it": "Legge il testo dalle immagini: per scansioni e foto di documenti.",
        "en": "Reads text off images: for scans and photographs of documents.",
    },
    "hint_profilo_llm_ready": {
        "it": "Testo essenziale con dati protetti, da incollare in un assistente AI.",
        "en": "Bare text with personal data protected, to paste into an AI "
              "assistant.",
    },
    "hint_profilo_no_privacy": {
        "it": "Testo integrale, nessuna sostituzione. Usalo solo su questo computer.",
        "en": "The whole text, nothing replaced. Use it only on this machine.",
    },
    "tip_interruttore_privacy": {
        "it": "Sostituisce i dati personali con segnaposto tipo <b>{{EMAIL}}</b> "
              "prima di consegnarti il Markdown. Serve soprattutto se poi "
              "incolli il testo in un servizio online: quello che è stato tolto "
              "lo vedi nella scheda «Confronto privacy».",
        "en": "Replaces personal data with placeholders such as <b>{{EMAIL}}</b> "
              "before handing you the Markdown. It matters most when the text "
              "then goes into an online service: what was taken out is listed "
              "under \"Privacy comparison\".",
    },
    "privacy_titolo": {
        "it": "Nascondi i dati personali", "en": "Hide personal data",
    },
    "privacy_desc": {
        "it": "Nomi, indirizzi, recapiti, codici, chiavi",
        "en": "Names, addresses, contact details, codes, keys",
    },
    "aria_filtro_privacy": {
        "it": "Attiva filtro privacy", "en": "Turn the privacy filter on",
    },
    "opzioni_avanzate": {"it": "Opzioni avanzate", "en": "Advanced options"},
    "opzioni_avanzate_sub": {
        "it": "lettura del file · dettaglio privacy · più file insieme",
        "en": "how the file is read · privacy detail · several files at once",
    },
    "gruppo_lettura": {
        "it": "Come viene letto il file", "en": "How the file is read",
    },
    "etichetta_metodo": {"it": "Metodo di lettura", "en": "Reading method"},
    "tip_metodo_etichetta": {
        "it": "Nel dubbio lascia Automatico: sceglie da solo e usa l'OCR solo "
              "quando serve.",
        "en": "When in doubt leave it on Automatic: it decides for itself and "
              "only uses OCR when it has to.",
    },
    "tip_metodo_scelte": {
        "it": "<b>Automatico</b> — legge il testo del documento; se non ne trova "
              "(PDF scansionato) passa da solo all'OCR.<br>"
              "<b>Forza OCR</b> — legge sempre l'immagine, riconoscendo il "
              "testo. Più lento, ma è l'unica strada per scansioni e foto.<br>"
              "<b>Solo testo nativo</b> — non usa mai l'OCR: se il documento non "
              "contiene testo, il risultato è vuoto.",
        "en": "<b>Automatic</b> — reads the document's own text; if there is "
              "none (a scanned PDF) it moves to OCR by itself.<br>"
              "<b>Force OCR</b> — always reads the image and recognises the "
              "text. Slower, but the only route for scans and photographs.<br>"
              "<b>Native text only</b> — never uses OCR: if the document holds "
              "no text, the result is empty.",
    },
    "metodo_auto": {"it": "Automatico (consigliato)", "en": "Automatic (recommended)"},
    "metodo_ocr": {
        "it": "Forza OCR — scansioni e foto",
        "en": "Force OCR — scans and photographs",
    },
    "metodo_nativo": {
        "it": "Solo testo nativo — mai OCR", "en": "Native text only — never OCR",
    },
    "hint_ocr_locale": {
        "it": "Il riconoscimento avviene sul tuo computer: nessun file esce da "
              "qui, nessun modello viene scaricato. Il modello OCR è addestrato "
              "sugli alfabeti latini, quindi legge italiano e inglese senza "
              "doverlo impostare.",
        "en": "Recognition happens on your own machine: no file leaves it, no "
              "model is downloaded. The OCR model is trained on Latin scripts, "
              "so it reads Italian and English without being told which.",
    },
    # I due suggerimenti sui pacchetti descrivono il pacchetto *stesso*:
    # nominare le parole italiane sotto «Formati italiani» resta vero anche
    # scrivendo in inglese.
    "tip_pack_it": {
        "it": "Codice fiscale, partita IVA, coordinate bancarie italiane, "
              "indirizzi con via e piazza, telefoni e nomi italiani. Spegnilo "
              "solo se lavori esclusivamente su documenti stranieri.",
        "en": "Codice fiscale, VAT number, Italian bank details, addresses with "
              "via and piazza, Italian phone numbers and names. Birth dates and "
              "euro amounts come with this pack too. Turn it off only if you "
              "work exclusively on documents from elsewhere.",
    },
    "tip_pack_en": {
        "it": "SSN e ITIN statunitensi, National Insurance Number e NHS number "
              "britannici, routing bancario, SIN canadese, ABN e TFN "
              "australiani, indirizzi con Street e Road, e la zona a lettura "
              "automatica dei passaporti.<br><br>Lasciarlo acceso su documenti "
              "italiani non cambia nulla: questi riconoscitori pretendono una "
              "punteggiatura precisa o una parola inglese a cui attaccarsi.",
        "en": "US SSN and ITIN, UK National Insurance and NHS numbers, bank "
              "routing numbers, Canadian SIN, Australian ABN and TFN, addresses "
              "with Street and Road, and the machine-readable zone of "
              "passports.<br><br>Leaving it on for Italian documents changes "
              "nothing: these detectors want precise punctuation or an English "
              "word to hold on to.",
    },
    # Le cifre restano quelle misurate. Gli esempi sono etichette di moduli
    # italiani, e in inglese lo si dice invece di tradurle: sono il testo che
    # il riconoscitore ha davvero incontrato.
    "tip_tipo_documento": {
        "it": "Su una lettera, due parole maiuscole di cui una risulta negli "
              "elenchi sono quasi sempre una persona. Su un modulo sono quasi "
              "sempre l'etichetta di un campo — «Imposta Lorda», «Quadro RN»."
              "<br><br>Misurato: pretendere due riscontri toglie 2739 "
              "sostituzioni sbagliate sui moduli e costa 609 nomi sulle "
              "lettere. Non esiste un valore giusto per entrambi, quindi si "
              "sceglie.<br><br><b>Automatico</b> lo deduce dal file: le email "
              "sono prosa, i fogli di calcolo sono moduli, e nei PDF si contano "
              "le caselle disegnate. Sulle scansioni non si puo' dedurre e "
              "vince la prudenza. Cambialo se il documento ti sembra "
              "classificato male.",
        "en": "In a letter, two capitalised words with one of them on the name "
              "lists are almost always a person. In a form they are almost "
              "always a field label — on an Italian form, \"Imposta Lorda\" or "
              "\"Quadro RN\".<br><br>Measured: demanding two matches removes "
              "2739 wrong replacements on forms and costs 609 names in letters. "
              "No single value is right for both, so it is a choice."
              "<br><br><b>Automatic</b> works it out from the file: email is "
              "prose, spreadsheets are forms, and in a PDF the drawn boxes are "
              "counted. On a scan there is nothing to count and caution wins. "
              "Change it if a document looks wrongly classified.",
    },
    # -- quali dati nascondere ---------------------------------------------
    "tip_emails": {
        "it": "Ogni indirizzo email diventa {{EMAIL}}.",
        "en": "Every email address becomes {{EMAIL}}.",
    },
    "opt_emails_titolo": {"it": "Email", "en": "Email"},
    "opt_emails_desc": {"it": "Indirizzi di posta", "en": "Email addresses"},
    "tip_phones": {
        "it": "Numeri di telefono fissi e cellulari. I numeri che non sembrano "
              "telefoni (protocolli, codici) vengono lasciati stare.",
        "en": "Landline and mobile numbers. Numbers that do not look like phone "
              "numbers — protocol numbers, reference codes — are left alone.",
    },
    "opt_phones_titolo": {"it": "Telefoni", "en": "Phone numbers"},
    "opt_phones_desc": {"it": "Fissi e cellulari", "en": "Landline and mobile"},
    # Riscritto, non tradotto: «Dott., Ing., Geom.» sono le abbreviazioni che
    # il pacchetto italiano cerca davvero. Renderle «Dr., Eng.» avrebbe fatto
    # dire all'interfaccia una cosa falsa su cosa il programma riconosce.
    "tip_names": {
        "it": "Nomi e cognomi. Oltre all'elenco dei nomi italiani valgono le "
              "regole di contesto: un titolo davanti (Dott., Ing., Geom.) e il "
              "nome scritto accanto a un indirizzo email.",
        "en": "First names and surnames. The Italian pack works from a list of "
              "Italian names plus context: an Italian title in front (Dott., "
              "Ing., Geom.) or a name written next to an email address. The "
              "English pack has no list and goes by context alone — a title "
              "(Mr, Mrs, Dr, Prof), a \"Dear …\" opening, or a sign-off such as "
              "\"Kind regards\".",
    },
    "opt_names_titolo": {"it": "Nomi", "en": "Names"},
    "opt_names_desc": {
        "it": "Nomi e cognomi di persona", "en": "People's names and surnames",
    },
    # Riscritto: la regola confronta con il vocabolario **italiano**, e gli
    # esempi sono etichette di moduli italiani. In inglese va detto, o
    # sembrerebbe una regola che vale su qualunque documento.
    # Riscritto: le parole italiane «via, piazza, corso» sono meta' del
    # riconoscitore; l'altra meta' e' inglese e pretende il civico davanti.
    # Tradurre solo le prime avrebbe descritto un programma diverso.
    "tip_addresses": {
        "it": "Via, viale, piazza, corso, largo, contrada... con il nome della "
              "strada, il civico e, se c'è, CAP e comune.",
        "en": "Italian formats: via, viale, piazza, corso, largo, contrada… "
              "followed by the street name, the number and, where there is one, "
              "the postcode and town. English formats: a house number in front "
              "of Street, Road, Avenue, Lane and the like, with a UK postcode "
              "or a US ZIP if present.",
    },
    "opt_addresses_titolo": {"it": "Indirizzi", "en": "Addresses"},
    "opt_addresses_desc": {
        "it": "Vie, piazze, civici, CAP",
        "en": "Streets, squares, numbers, postcodes",
    },
    "tip_urls": {
        "it": "Collegamenti che iniziano con http, https o www. Un link porta "
              "con sé il dominio dell'azienda e spesso un identificativo di "
              "pratica nella parte finale.",
        "en": "Links starting with http, https or www. A link carries the "
              "company's domain with it, and often a case reference at the end.",
    },
    "opt_urls_titolo": {"it": "Indirizzi web", "en": "Web addresses"},
    "opt_urls_desc": {"it": "http, https, www.", "en": "http, https, www."},
    # Riscritto: quali codici vengano cercati dipende dai pacchetti accesi
    # sopra. L'elenco italiano da solo sarebbe incompleto in inglese.
    "tip_fiscal": {
        # L'elenco dei codici esteri c'era solo in inglese. Questo
        # interruttore ne governa **quattordici** su ventiquattro
        # categorie: chi lo spegneva pensando di togliere quattro cose ne
        # toglieva quattordici, e la descrizione non gliel'aveva detto.
        "it": "Gli IBAN sono verificati col calcolo di controllo e le carte di "
              "pagamento con quello di Luhn, così un codice a caso non viene "
              "scambiato per un conto corrente. Quali codici si cercano "
              "dipende dai pacchetti qui sopra: codice fiscale, partita IVA e "
              "coordinate ABI/CAB da quello italiano; SSN, ITIN, NINO, numero "
              "NHS, SIN, routing bancario, ABN, TFN e la riga a lettura "
              "automatica dei passaporti da quello inglese.",
        "en": "IBANs are checked with their check digits and payment cards with "
              "the Luhn calculation, so a stray code is not mistaken for an "
              "account. Which codes are looked for depends on the packs above: "
              "codice fiscale, VAT number and BBAN from the Italian one; SSN, "
              "NINO, NHS number and the rest from the English one.",
    },
    "opt_fiscal_titolo": {
        "it": "Codici fiscali e bancari", "en": "Tax and bank codes",
    },
    "opt_fiscal_desc": {
        # «e i codici esteri» non è un dettaglio: senza, la riga elenca
        # quattro categorie su quattordici e sembra completa.
        "it": "Codice fiscale, P.IVA, IBAN, carte e i codici esteri",
        "en": "Codice fiscale, VAT no., IBAN, cards and the foreign codes",
    },
    "tip_secrets": {
        "it": "Chiavi API, token, password scritte accanto alla loro etichetta e "
              "blocchi di chiave privata. Sono i dati che non ci si accorge di "
              "aver incollato.",
        "en": "API keys, tokens, passwords written next to their label, and "
              "private-key blocks. These are the ones you do not notice having "
              "pasted.",
    },
    "opt_secrets_titolo": {"it": "Chiavi e password", "en": "Keys and passwords"},
    "opt_secrets_desc": {
        "it": "Token, API key, credenziali", "en": "Tokens, API keys, credentials",
    },
    # Riscritto: il riconoscitore accetta anche «born» e «DOB», e viaggia col
    # pacchetto italiano. Entrambe le cose in inglese vanno dette.
    "tip_dates": {
        "it": "Spento di default: verrebbero tolte anche le date che servono. "
              "Attivo, sostituisce solo le date scritte accanto a una parola "
              "di nascita — «nato il», «data di nascita», e gli inglesi "
              "«born» e «DOB». Viaggia col pacchetto dei formati italiani.",
        "en": "Off by default: it would take out dates you need. Switched on, it "
              "only replaces dates written next to a birth word — \"born\", "
              "\"DOB\", or the Italian \"nato il\" and \"data di nascita\". It "
              "comes with the Italian formats pack.",
    },
    "opt_documenti_titolo": {
        "it": "Documenti d'identità", "en": "Identity documents",
    },
    "opt_documenti_desc": {
        "it": "Carta d'identità, patente, passaporto",
        "en": "ID card, driving licence, passport",
    },
    "tip_documenti": {
        "it": "Numeri di carta d'identità, patente e passaporto. "
              "<b>Serve il contesto</b>: questi numeri non hanno una cifra di "
              "controllo, e la loro forma è identica a quella di tanti codici "
              "di protocollo. Si sostituiscono solo se accanto c'è scritto di "
              "che documento si tratta; altrimenti finiscono fra i sospetti, "
              "così il documento resta intero e tu sai dove guardare.",
        "en": "Identity card, driving licence and passport numbers. "
              "<b>Context is required</b>: these numbers carry no check digit "
              "and their shape is identical to countless reference codes. "
              "They are replaced only when the surrounding text says which "
              "document they belong to; otherwise they are flagged as "
              "suspects, so the document stays intact and you know where to "
              "look.",
    },
    # Le due liste dello studio (P1.8). Il testo dice la cosa che conta: non
    # sono l'una l'opposto dell'altra, «mai» e' piu' forte di «sempre».
    "gruppo_termini": {
        "it": "Le tue parole", "en": "Your own terms",
    },
    "termini_sempre_etichetta": {
        "it": "Nascondi sempre", "en": "Always hide",
    },
    "termini_mai_etichetta": {
        "it": "Non toccare mai", "en": "Never touch",
    },
    "termini_segnaposto": {
        "it": "Un termine per riga", "en": "One term per line",
    },
    "tip_termini_sempre": {
        "it": "Nomi che ricorrono in ogni tua pratica e che le regole generali "
              "non possono indovinare: clienti, controparti, nomi di progetto. "
              "<b>Un termine per riga</b>, maiuscole e minuscole indifferenti. "
              "Vengono sostituiti con <code>{{TERM}}</code> prima di ogni altro "
              "riconoscitore.",
        "en": "Names that come up in every one of your files and that general "
              "rules cannot guess: clients, counterparties, project names. "
              "<b>One term per line</b>, case-insensitive. They are replaced "
              "with <code>{{TERM}}</code> before any other recogniser runs.",
    },
    "tip_termini_mai": {
        "it": "Parole che non devono essere toccate da nessun riconoscitore: "
              "denominazioni interne, nomi di prodotto, la tua stessa ragione "
              "sociale. <b>È più forte di «nascondi sempre»</b>: un termine "
              "scritto in tutte e due le liste resta in chiaro. Non compare "
              "nemmeno fra i sospetti — l'hai già deciso tu.",
        "en": "Words no recogniser may touch: internal designations, product "
              "names, your own company name. <b>It outranks \"always hide\"</b>: "
              "a term written in both lists stays in clear text. It is not "
              "flagged as a suspect either — you have already decided.",
    },
    "opt_dates_titolo": {"it": "Date di nascita", "en": "Dates of birth"},
    "opt_dates_desc": {
        "it": "Solo con contesto di nascita", "en": "Only in a birth context",
    },
    # Riscritto: il riconoscitore vede l'euro e le parole di una fattura
    # italiana. «Amounts» avrebbe promesso sterline e dollari che non arrivano.
    "tip_amounts": {
        "it": "Spento di default: nelle fatture gli importi di solito servono. "
              "Attivalo se vuoi condividere un documento senza mostrarne le "
              "cifre. Riconosce solo gli importi in euro — il simbolo €, "
              "«EUR», o una parola di fattura accanto alla cifra — quindi "
              "sterline e dollari restano dove sono. Viaggia col pacchetto "
              "dei formati italiani.",
        "en": "Off by default: on an invoice the figures are usually the point. "
              "Switch it on to share a document without its numbers. It "
              "recognises euro amounts only — a € sign, EUR, or an Italian "
              "invoice word beside the figure — so pounds and dollars are left "
              "alone. It comes with the Italian formats pack.",
    },
    "opt_amounts_titolo": {"it": "Importi in euro", "en": "Euro amounts"},
    "opt_amounts_desc": {"it": "Cifre e totali", "en": "Figures and totals"},
    # Dice sia cosa si guadagna sia cosa si perde: e' l'unica opzione che
    # cambia una proprieta' del risultato invece di aggiungere o togliere un
    # riconoscitore, e la domanda 8 delle FAQ ci costruisce sopra.
    "tip_numerati": {
        "it": "Acceso di default. Persone diverse ricevono numeri diversi "
              "({{NAME_1}}, {{NAME_2}}) e la stessa persona ripetuta riceve "
              "sempre lo stesso: senza, «{{NAME}} ha citato {{NAME}} davanti "
              "a {{NAME}}» non si legge. In cambio l'uscita dice quante "
              "persone distinte ci sono e dove compare ciascuna — non i "
              "valori, ma la struttura. Il numero vale solo dentro questo "
              "documento e non viene salvato da nessuna parte. Spegnilo per "
              "l'uscita della 1.19.",
        "en": "On by default. Different people get different numbers "
              "({{NAME_1}}, {{NAME_2}}) and the same person always gets the "
              "same one: without it, \"{{NAME}} quoted {{NAME}} before "
              "{{NAME}}\" is unreadable. In exchange the output reveals how "
              "many distinct people there are and where each appears — not "
              "the values, but the structure. The number is valid inside "
              "this document only and is never stored. Turn it off for the "
              "1.19 output.",
    },
    "gruppo_segnala": {
        "it": "Rileva ma non sostituire", "en": "Detect but do not replace",
    },
    "hint_segnala": {
        "it": "Le categorie spuntate qui vengono cercate e riportate nel "
              "rapporto, ma restano nel documento. Serve quando un dato ti "
              "serve in chiaro — gli importi di una fattura, l'età in una "
              "cartella — e vuoi comunque la prova scritta che c'era.",
        "en": "Categories ticked here are looked for and listed in the "
              "report, but stay in the document. Useful when you need a "
              "value in the clear — the figures on an invoice, an age in a "
              "medical record — and still want it on record that it was there.",
    },
    "tip_segnala": {
        "it": "Spegnere un riconoscitore vuol dire non cercarlo, e non "
              "lascia traccia: chi rilegge il documento non sa se lì dentro "
              "non c'era niente o se abbiamo guardato dall'altra parte. "
              "Questo è il terzo stato: cercato, trovato, lasciato in "
              "chiaro apposta, e scritto nel rapporto.",
        "en": "Turning a recogniser off means not looking for it, and it "
              "leaves no trace: whoever reads the document later cannot "
              "tell whether there was nothing there or we looked away. This "
              "is the third state: looked for, found, deliberately left in "
              "the clear, and written down in the report.",
    },
    "opt_numerati_titolo": {"it": "Numera i segnaposto", "en": "Number the placeholders"},
    "opt_numerati_desc": {
        "it": "{{NAME_1}}, {{NAME_2}}", "en": "{{NAME_1}}, {{NAME_2}}",
    },
    "tip_include_raw": {
        "it": "Conserva anche il testo originale, così nella scheda «Confronto "
              "privacy» puoi vedere esattamente cosa è stato sostituito. Se lo "
              "spegni risparmi memoria ma perdi quel controllo.",
        "en": "Keeps the original text as well, so the \"Privacy comparison\" "
              "tab can show exactly what was replaced. Turning it off saves "
              "memory but loses that check.",
    },
    "opt_include_raw_titolo": {
        "it": "Permetti il confronto prima/dopo",
        "en": "Allow the before/after comparison",
    },
    "opt_include_raw_desc": {
        "it": "Abilita la scheda di verifica", "en": "Enables the checking tab",
    },
    "hint_privacy_spenta": {
        "it": "Il filtro è spento: il Markdown conterrà i dati personali così "
              "come sono nel documento.",
        "en": "The filter is off: the Markdown will carry the personal data "
              "exactly as the document has it.",
    },
    # -- cosa mettere nel Markdown ------------------------------------------
    "gruppo_contenuto": {
        "it": "Cosa mettere nel Markdown", "en": "What goes into the Markdown",
    },
    "tip_include_tables": {
        "it": "Cerca le tabelle dentro i PDF e le riscrive come tabelle "
              "Markdown, invece di sfilacciarle in righe di testo. Su PDF molto "
              "lunghi rallenta un po'.",
        "en": "Finds the tables inside PDFs and rewrites them as Markdown "
              "tables, instead of fraying them into lines of text. On very long "
              "PDFs it slows things down a little.",
    },
    "opt_tables_titolo": {
        "it": "Estrai le tabelle dai PDF", "en": "Extract tables from PDFs",
    },
    "opt_tables_desc": {
        "it": "Le ricostruisce come tabelle vere", "en": "Rebuilt as real tables",
    },
    "tip_frontmatter": {
        "it": "Utile per archiviare, inutile se devi solo incollare il testo da "
              "qualche parte.",
        "en": "Useful for filing, pointless if you only need to paste the text "
              "somewhere.",
    },
    "opt_frontmatter_titolo": {
        "it": "Scheda informativa in cima", "en": "Information block at the top",
    },
    "opt_frontmatter_desc": {
        "it": "Origine, data, sostituzioni fatte",
        "en": "Source, date, replacements made",
    },
    "tip_clean": {
        "it": "Toglie note a piè di pagina e commenti tecnici, lasciando solo il "
              "contenuto. Comodo quando il testo va incollato in un assistente AI.",
        "en": "Removes footnotes and technical comments, leaving only the "
              "content. Handy when the text is going into an AI assistant.",
    },
    "opt_clean_titolo": {
        "it": "Togli le note tecniche", "en": "Drop the technical notes",
    },
    "opt_clean_desc": {
        "it": "Solo il contenuto, niente commenti",
        "en": "Content only, no comments",
    },
    # -- più file insieme ----------------------------------------------------
    "gruppo_piu_file": {
        "it": "Quando carichi più file insieme",
        "en": "When you load several files at once",
    },
    "tip_merge": {
        "it": "Senza questa spunta ottieni un risultato separato per ciascun file.",
        "en": "Without this ticked you get a separate result for each file.",
    },
    "opt_merge_titolo": {
        "it": "Unisci in un solo documento", "en": "Merge into one document",
    },
    "opt_merge_desc": {"it": "Invece di uno per file", "en": "Instead of one each"},
    "tip_compare": {
        "it": "Prende esattamente 2 file e li mette uno sotto l'altro come "
              "«Documento A» e «Documento B», per confrontarli a colpo d'occhio.",
        "en": "Takes exactly 2 files and puts one under the other as \"Document "
              "A\" and \"Document B\", to compare them at a glance.",
    },
    "opt_compare_titolo": {
        "it": "Metti 2 file a confronto", "en": "Compare 2 files",
    },
    "opt_compare_desc": {
        "it": "Esattamente due, uno sotto l'altro",
        "en": "Exactly two, one under the other",
    },
    # -- 3. risultato --------------------------------------------------------
    "risultato_titolo": {"it": "Risultato Markdown", "en": "Markdown result"},
    "tip_badge_redazioni": {
        "it": "Quanti dati personali sono stati sostituiti con segnaposto. Apri "
              "«Confronto privacy» per vedere quali.<br><br>Se compare <b>«da "
              "controllare»</b>, nel testo è rimasto qualcosa che <i>somiglia</i> "
              "a un dato personale ma non ha superato il controllo — tipicamente "
              "un codice storpiato dall'OCR. Non è stato sostituito perché non "
              "c'era certezza: passaci l'occhio.",
        "en": "How many pieces of personal data were replaced with placeholders. "
              "Open \"Privacy comparison\" to see which.<br><br>If <b>\"to "
              "review\"</b> appears, something in the text <i>looks</i> like "
              "personal data but did not pass the check — typically a code the "
              "OCR mangled. It was left alone because there was no certainty: "
              "give it a look.",
    },
    "tip_copia": {
        "it": "Copia tutto negli appunti, scheda informativa compresa.",
        "en": "Copies everything to the clipboard, information block included.",
    },
    "tip_copia_pulita": {
        "it": "Copia solo il contenuto: via la scheda informativa in cima e le "
              "note tecniche. È la versione da incollare in un assistente AI o "
              "in una mail.",
        "en": "Copies the content only: no information block at the top, no "
              "technical notes. This is the version to paste into an AI "
              "assistant or an email.",
    },
    "scarica_txt": {"it": ".txt", "en": ".txt"},
    "tip_scarica_txt": {
        "it": "Scarica come testo semplice .txt, senza formattazione Markdown.",
        "en": "Downloads as plain .txt, with no Markdown formatting.",
    },
    "scarica_docx": {"it": ".docx", "en": ".docx"},
    "tip_scarica_docx": {
        "it": "Scarica come documento Word, per quello che deve restare un "
              "documento: un atto da pubblicare, un contratto da depositare. "
              "<b>Non è l'originale con sopra dei rettangoli neri</b> — il "
              "documento viene ricostruito dal testo già redatto, quindi il "
              "dato non c'è proprio. In cambio si perde l'impaginazione.",
        "en": "Downloads as a Word document, for things that have to stay "
              "documents: a record to publish, a contract to file. <b>This is "
              "not the original with black boxes on top</b> — the document is "
              "rebuilt from the already-redacted text, so the data is absent "
              "rather than covered. The trade-off is the original layout.",
    },
    "js_docx_scaricato": {
        "it": "Documento .docx scaricato",
        "en": ".docx document downloaded",
    },
    "err_docx_assente": {
        "it": "L'esportazione in .docx richiede python-docx, che qui non c'è. "
              "Nel pacchetto portable è già incluso.",
        "en": "Exporting to .docx needs python-docx, which is not installed "
              "here. The portable package already includes it.",
    },
    "err_niente_da_esportare": {
        "it": "Non c'è nessun documento da esportare.",
        "en": "There is no document to export.",
    },
    "err_docx_fallito": {
        "it": "Non sono riuscito a creare il documento .docx.",
        "en": "Could not build the .docx document.",
    },
    "tip_scarica_md": {
        "it": "Scarica il file Markdown. Puoi anche <b>trascinare questo "
              "pulsante</b> direttamente sul Desktop o in una cartella.",
        "en": "Downloads the Markdown file. You can also <b>drag this "
              "button</b> straight onto the desktop or into a folder.",
    },
    "tip_scheda_testo": {
        "it": "Il Markdown come viene salvato nel file, simboli compresi.",
        "en": "The Markdown as it is saved to the file, symbols included.",
    },
    "tip_scheda_anteprima": {
        "it": "Come apparirà una volta formattato, con titoli e grassetti al "
              "posto dei simboli.",
        "en": "How it will look once formatted, with headings and bold in place "
              "of the symbols.",
    },
    "tip_scheda_confronto": {
        "it": "Mostra il testo prima e dopo la protezione dei dati, con i "
              "segnaposto evidenziati: così controlli cosa è stato tolto — e "
              "cosa è sfuggito.",
        "en": "Shows the text before and after the data was protected, with the "
              "placeholders highlighted: so you can check what was taken out — "
              "and what slipped through.",
    },
    "output_barra": {
        "it": "markdown · trascina il bottone .md sul Desktop",
        "en": "markdown · drag the .md button onto the desktop",
    },
    # -- 4. extra -------------------------------------------------------------
    "sessione_titolo": {
        "it": "Conversioni di questa sessione", "en": "This session's conversions",
    },
    "tip_sessione": {
        "it": "Le conversioni fatte da quando hai aperto questa pagina. Clicca "
              "una voce per rivederne il risultato.",
        "en": "The conversions made since you opened this page. Click an entry "
              "to see its result again.",
    },
    "sessione_vuota": {
        "it": "Nessuna conversione in questa sessione.",
        "en": "No conversions in this session.",
    },
    "sessione_nota": {
        "it": "Restano solo finché la pagina è aperta: niente viene salvato sul "
              "disco.",
        "en": "They last only while the page is open: nothing is written to disk.",
    },
    "watch_titolo": {"it": "Cartella automatica", "en": "Watched folder"},
    "tip_watch_stato": {
        "it": "Stato del monitoraggio e quanti file sono stati convertiti finora.",
        "en": "Whether the folder is being watched, and how many files have been "
              "converted so far.",
    },
    "watch_non_attiva": {"it": "non attiva", "en": "not running"},
    "watch_intro": {
        "it": "Sorveglia una cartella al posto tuo: <strong>ogni file che ci "
              "trascini dentro viene convertito da solo</strong> e il "
              "<code>.md</code> compare nella cartella di uscita. Utile per "
              "convertire tanti documenti senza passare da questa pagina — ci "
              "pensa lui finché non premi «Ferma». Usa il profilo e le opzioni "
              "scelti qui sopra.",
        "en": "Watches a folder for you: <strong>every file you drop in there "
              "gets converted on its own</strong> and the <code>.md</code> "
              "appears in the output folder. Useful for converting many "
              "documents without coming through this page — it carries on until "
              "you stop it. It uses the profile and options chosen above.",
    },
    "watch_predefinite": {
        "it": "Di default: <code>Documenti\\Mr Rao\\Da convertire</code> → "
              "<code>Documenti\\Mr Rao\\Convertiti</code> (create all'avvio se "
              "mancano).",
        "en": "By default: <code>Documents\\Mr Rao\\Da convertire</code> → "
              "<code>Documents\\Mr Rao\\Convertiti</code> (created on start-up "
              "if missing).",
    },
    "watch_inbox_etichetta": {
        "it": "Cartella da monitorare", "en": "Folder to watch",
    },
    "tip_watch_inbox_etichetta": {
        "it": "Ogni file che compare in questa cartella viene convertito.",
        "en": "Every file that turns up in this folder gets converted.",
    },
    "watch_placeholder": {
        "it": "Scegli o usa la cartella predefinita",
        "en": "Pick one, or use the default folder",
    },
    "tip_watch_inbox_campo": {
        "it": "Percorso della cartella dove metterai i documenti da convertire. "
              "Usa «Sfoglia…» per sceglierla.",
        "en": "Path of the folder where you will put the documents to convert. "
              "Use \"Browse…\" to pick it.",
    },
    "sfoglia": {"it": "Sfoglia…", "en": "Browse…"},
    "tip_sfoglia_inbox": {
        "it": "Apre la finestra di Windows per scegliere la cartella da monitorare.",
        "en": "Opens the Windows dialogue to choose the folder to watch.",
    },
    "watch_outbox_etichetta": {
        "it": "Dove salvare i .md", "en": "Where to save the .md files",
    },
    "tip_watch_outbox_etichetta": {
        "it": "Dove finiscono i Markdown convertiti.",
        "en": "Where the converted Markdown ends up.",
    },
    "tip_watch_outbox_campo": {
        "it": "Cartella di uscita dei file .md. Usa «Sfoglia…» per sceglierla.",
        "en": "Output folder for the .md files. Use \"Browse…\" to pick it.",
    },
    "tip_sfoglia_outbox": {
        "it": "Apre la finestra di Windows per scegliere dove salvare i .md.",
        "en": "Opens the Windows dialogue to choose where to save the .md files.",
    },
    "tip_watch_move": {
        "it": "A conversione fatta, sposta il documento originale in una "
              "sottocartella «done», così la cartella monitorata resta pulita e "
              "vedi a colpo d'occhio cosa manca ancora.",
        "en": "Once converted, moves the original document into a \"done\" "
              "subfolder, so the watched folder stays clean and you can see at "
              "a glance what is still to do.",
    },
    "opt_watch_move_titolo": {
        "it": "Sposta gli originali in «done»",
        "en": "Move originals into \"done\"",
    },
    "opt_watch_move_desc": {
        "it": "Tiene pulita la cartella monitorata",
        "en": "Keeps the watched folder clean",
    },
    "watch_attiva": {"it": "Attiva monitoraggio", "en": "Start watching"},
    "tip_watch_attiva": {
        "it": "Comincia a monitorare, usando il profilo e le opzioni impostati "
              "qui sopra.",
        "en": "Starts watching, using the profile and options set above.",
    },
    "watch_disattiva": {"it": "Disattiva", "en": "Stop"},
    "tip_watch_disattiva": {
        "it": "Smette di monitorare. I file già convertiti restano dove sono.",
        "en": "Stops watching. Files already converted stay where they are.",
    },
    # -- piede di pagina -------------------------------------------------------
    "footer_locale": {"it": "100% locale", "en": "100% local"},
    "footer_cloud": {"it": "zero cloud", "en": "no cloud"},
    "footer_licenza": {
        "it": "Copyright © 2026 Antonio Andrea Rao — software libero sotto <strong>GNU "
              "AGPL-3.0</strong>, fornito <strong>senza alcuna garanzia</strong>. "
              "Sei libero di ridistribuirlo alle condizioni della licenza (vedi ⓘ).",
        "en": "Copyright © 2026 Antonio Andrea Rao — free software under <strong>GNU "
              "AGPL-3.0</strong>, provided <strong>with no warranty "
              "whatsoever</strong>. You may redistribute it under the terms of "
              "the licence (see ⓘ).",
    },
    "aria_dipendenze": {
        "it": "Dipendenze open source", "en": "Open source dependencies",
    },
    "footer_lgpl": {
        "it": "Tray: <strong>pystray</strong> © Moses Palmér — "
              "<a href=\"https://github.com/moses-palmer/pystray\" "
              "target=\"_blank\" rel=\"noopener\">sorgente</a>, GNU LGPL v3 "
              "(testi in cartella <code>licenses/pystray/</code>).",
        "en": "Tray icon: <strong>pystray</strong> © Moses Palmér — "
              "<a href=\"https://github.com/moses-palmer/pystray\" "
              "target=\"_blank\" rel=\"noopener\">source</a>, GNU LGPL v3 "
              "(texts in the <code>licenses/pystray/</code> folder).",
    },
    "bottone_licenza": {
        "it": "Licenza e dipendenze", "en": "Licence and dependencies",
    },
    "tip_bottone_licenza": {
        "it": "Licenza Mr. Rao, elenco dipendenze e obblighi LGPL di pystray.",
        "en": "Mr. Rao's licence, the list of dependencies, and pystray's LGPL "
              "obligations.",
    },
    "aria_info": {
        "it": "Informazioni, licenza e dipendenze",
        "en": "About, licence and dependencies",
    },
    "tip_info": {
        "it": "Trasparenza: dipendenze open source, repository e licenza di Mr. Rao.",
        "en": "Transparency: open source dependencies, repositories and Mr. Rao's "
              "licence.",
    },
    # -- riquadro trasparenza ---------------------------------------------------
    "about_titolo": {"it": "Mr. Rao — trasparenza", "en": "Mr. Rao — transparency"},
    "about_sub": {
        "it": "Dipendenze open source, repository e condizioni d’uso del progetto.",
        "en": "Open source dependencies, repositories and the project's terms of "
              "use.",
    },
    "aria_chiudi": {"it": "Chiudi", "en": "Close"},
    "about_licenza_titolo": {"it": "Licenza Mr. Rao", "en": "Mr. Rao's licence"},
    "about_licenza_testo": {
        "it": "Copyright © 2026 Antonio Andrea Rao<br><br>Mr. Rao è <strong>software "
              "libero</strong> sotto <strong>GNU Affero General Public License "
              "v3.0</strong>. Puoi usarlo, studiarlo, modificarlo e "
              "ridistribuirlo — anche in ambito professionale e commerciale — "
              "alle condizioni della licenza.<br><br><strong>Se lo offri ad "
              "altri attraverso una rete</strong>, l'articolo 13 dell'AGPL ti "
              "obbliga a mettere a disposizione degli utenti il codice sorgente "
              "della tua versione. Usato in locale come qui, non cambia nulla."
              "<br><br>Distribuito <strong>SENZA ALCUNA GARANZIA</strong>, "
              "nemmeno implicita di commerciabilità o idoneità a uno scopo "
              "particolare.<br><br>Testo completo in <code>LICENSE</code> · "
              "<a href=\"https://www.gnu.org/licenses/agpl-3.0.html\" "
              "target=\"_blank\" rel=\"noopener\">gnu.org/licenses/agpl-3.0</a>"
              "<br>I componenti di terzi restano sotto le <strong>loro</strong> "
              "licenze (MIT, Apache-2.0, BSD, LGPL…): dettaglio in "
              "<code>THIRD_PARTY.md</code>.",
        "en": "Copyright © 2026 Antonio Andrea Rao<br><br>Mr. Rao is <strong>free "
              "software</strong> under the <strong>GNU Affero General Public "
              "License v3.0</strong>. You may use it, study it, modify it and "
              "redistribute it — professionally and commercially included — "
              "under the terms of the licence.<br><br><strong>If you offer it "
              "to others over a network</strong>, article 13 of the AGPL "
              "requires you to make the source code of your version available "
              "to those users. Run locally, as here, nothing changes.<br><br>"
              "Distributed <strong>WITH NO WARRANTY WHATSOEVER</strong>, not "
              "even the implied warranty of merchantability or fitness for a "
              "particular purpose.<br><br>Full text in <code>LICENSE</code> · "
              "<a href=\"https://www.gnu.org/licenses/agpl-3.0.html\" "
              "target=\"_blank\" rel=\"noopener\">gnu.org/licenses/agpl-3.0</a>"
              "<br>Third-party components stay under <strong>their own</strong> "
              "licences (MIT, Apache-2.0, BSD, LGPL…): detail in "
              "<code>THIRD_PARTY.md</code>.",
    },
    "about_dipendenze_titolo": {
        "it": "Dipendenze e repository", "en": "Dependencies and repositories",
    },
    "dep_markitdown": {
        "it": "Conversione documenti Office/PDF → Markdown (Microsoft)",
        "en": "Office/PDF documents → Markdown (Microsoft)",
    },
    "dep_rapidocr": {
        "it": "OCR offline su immagini e PDF scansionati",
        "en": "Offline OCR on images and scanned PDFs",
    },
    "dep_onnx": {
        "it": "Esecuzione modelli OCR / Magika", "en": "Runs the OCR / Magika models",
    },
    "dep_flask": {
        "it": "Server web locale dell’interfaccia",
        "en": "The interface's local web server",
    },
    "dep_bs4": {
        "it": "HTML delle email → testo leggibile",
        "en": "Email HTML → readable text",
    },
    "dep_pdfplumber": {
        "it": "Tabelle PDF e rendering pagine per OCR",
        "en": "PDF tables, and rendering pages for OCR",
    },
    "dep_pillow": {"it": "Elaborazione immagini", "en": "Image processing"},
    "dep_magika": {
        "it": "Riconoscimento tipo file (usato da MarkItDown)",
        "en": "File-type recognition (used by MarkItDown)",
    },
    "dep_pystray": {
        "it": "System tray © Moses Palmér — notice e testi in licenses/pystray/; "
              "sostituibile (docs/LGPL_PYSTRAY.md). Opzionale: MR_RAO_TRAY=0",
        "en": "System tray © Moses Palmér — notice and texts in "
              "licenses/pystray/; replaceable (docs/LGPL_PYSTRAY.md). Optional: "
              "MR_RAO_TRAY=0",
    },
    "about_lgpl_titolo": {
        "it": "L'unica libreria LGPL", "en": "The one LGPL library",
    },
    "about_lgpl_testo": {
        "it": "<strong>pystray</strong> © 2016–2022 Moses Palmér — "
              "<strong>LGPL-3.0</strong> — usata per l'icona nella barra di "
              "sistema (<a href=\"https://github.com/moses-palmer/pystray\" "
              "target=\"_blank\" rel=\"noopener\">sorgente</a>). Testo di "
              "licenza, notice e istruzioni per sostituirla in "
              "<code>licenses/pystray/</code>.<br><br>Essendo Mr. Rao "
              "distribuito sotto AGPL-3.0 con il sorgente disponibile, "
              "l'obbligo LGPL di permettere la sostituzione della libreria è "
              "soddisfatto di conseguenza: hai già tutto il necessario per "
              "ricostruire il programma con una versione diversa.",
        "en": "<strong>pystray</strong> © 2016–2022 Moses Palmér — "
              "<strong>LGPL-3.0</strong> — used for the system tray icon "
              "(<a href=\"https://github.com/moses-palmer/pystray\" "
              "target=\"_blank\" rel=\"noopener\">source</a>). Licence text, "
              "notice and instructions for replacing it are in "
              "<code>licenses/pystray/</code>.<br><br>Since Mr. Rao is "
              "distributed under AGPL-3.0 with its source available, the LGPL "
              "obligation to allow the library to be replaced is met as a "
              "consequence: you already have everything needed to rebuild the "
              "program against a different version.",
    },
    "about_permissive_titolo": {
        "it": "Licenze permissive (MIT / Apache / BSD)",
        "en": "Permissive licences (MIT / Apache / BSD)",
    },
    "about_permissive_1": {
        "it": "Consentono di costruire prodotti anche sopra le librerie, con "
              "attribuzione. Mr. Rao limita solo il <strong>proprio</strong> "
              "codice/prodotto; le librerie restano libere.",
        "en": "They allow products to be built on top of the libraries, with "
              "attribution. Mr. Rao restricts only <strong>its own</strong> "
              "code and product; the libraries stay free.",
    },
    "about_permissive_2": {
        # Qui c'era «Uso commerciale: autorizzazione a Rao», e contraddiceva
        # la licenza che il riquadro stesso dichiara: l'AGPL l'uso
        # commerciale lo **permette**. Chi leggeva poteva concluderne due
        # cose opposte -- che servisse un permesso, o che il progetto non
        # sapesse cosa dice la propria licenza. Su uno strumento di
        # conformita' la seconda e' peggio della prima.
        "it": "Questo riquadro non è un parere legale. L'uso commerciale è "
              "libero alle condizioni dell'AGPL, obblighi compresi. Serve "
              "una licenza diversa — per includerlo in un prodotto chiuso, "
              "o offrirlo in rete senza pubblicare le proprie modifiche? "
              "Scrivi. File: <code>LICENSE</code>, "
              "<code>THIRD_PARTY.md</code>, <code>licenses/</code>.",
        "en": "This panel is not legal advice. Commercial use is free under "
              "the terms of the AGPL, obligations included. Need different "
              "terms — to ship it inside a closed product, or offer it over "
              "a network without publishing your changes? Get in touch. "
              "Files: <code>LICENSE</code>, <code>THIRD_PARTY.md</code>, "
              "<code>licenses/</code>.",
    },
    "toast_default": {"it": "Operazione completata", "en": "Done"},
    # ══════════════════════════════════════════════════════════════════
    # Quello che scrive il JavaScript.
    #
    # Arrivano tutte dallo stesso dizionario, per `window.MR_RAO_I18N`:
    # un secondo elenco «solo per la pagina» sarebbe il posto dove una
    # traduzione manca senza che nessuno se ne accorga.
    # ══════════════════════════════════════════════════════════════════
    "js_vuoto": {"it": "Vuoto", "en": "Empty"},
    "js_no_raw": {
        "it": "Nessun testo pre-privacy disponibile.",
        "en": "No pre-redaction text available.",
    },
    "js_diff_intestazione": {
        "it": "Prima (grezzo) {prima} car. · Dopo (redatto) {dopo} car. · "
              "Segnaposto evidenziati sotto",
        "en": "Before (raw) {prima} chars · After (redacted) {dopo} chars · "
              "placeholders highlighted below",
    },
    "js_diff_originale": {
        "it": "ORIGINALE (pre-privacy)", "en": "ORIGINAL (before redaction)",
    },
    "js_allegati_email": {"it": "Allegati email:", "en": "Email attachments:"},
    "js_allegato_saltato": {
        "it": "{nome} (saltato: {motivo})", "en": "{nome} (skipped: {motivo})",
    },
    "js_allegato_troppo_grande": {"it": "troppo grande", "en": "too large"},
    "js_allegato_scaricato": {
        "it": "Allegato scaricato: {nome}", "en": "Attachment downloaded: {nome}",
    },
    # Il plurale si sbagliava in tre punti: «1 redazioni» è sbagliato in
    # italiano quanto «1 redactions» in inglese.
    "file_convertiti_uno": {"it": "{n} file convertito", "en": "{n} file converted"},
    "file_convertiti_molti": {"it": "{n} file convertiti", "en": "{n} files converted"},
    "js_elaborazione": {"it": "Elaborazione…", "en": "Working…"},
    "err_batch": {"it": "Errore batch", "en": "Batch error"},
    "js_file_troppo_grande": {
        "it": "File troppo grande: {nome} ({mb} MB). Max {max} MB.",
        "en": "File too large: {nome} ({mb} MB). Maximum {max} MB.",
    },
    "js_invio_troppo_grande": {
        "it": "Invio troppo grande ({mb} MB in totale). Il limite di {max} MB "
              "vale per l'intera richiesta: carica meno file per volta.",
        "en": "The upload is too large ({mb} MB in total). The {max} MB limit "
              "applies to the whole request: load fewer files at a time.",
    },
    "err_confronto_due_file": {
        "it": "Il confronto richiede esattamente 2 file",
        "en": "The comparison needs exactly 2 files",
    },
    "js_batch_in_corso": {"it": "Batch: {n} file…", "en": "Batch: {n} files…"},
    "js_confronto_completato": {
        "it": "Confronto completato", "en": "Comparison done",
    },
    "js_conversione_completata": {
        "it": "Conversione completata", "en": "Conversion done",
    },
    "err_file_non_leggibile": {
        "it": "Non riesco a leggere il file: se e' aperto in Word o Excel, "
              "chiudilo e riprova.",
        "en": "The file could not be read: if it is open in Word or Excel, "
              "close it and try again.",
    },
    "js_immagine_incollata": {
        "it": "Immagine incollata dagli appunti",
        "en": "Image pasted from the clipboard",
    },
    "js_copiato": {"it": "Copiato negli appunti", "en": "Copied to the clipboard"},
    "js_copia_fallita": {"it": "Impossibile copiare", "en": "Could not copy"},
    "js_copiato_pulito": {
        "it": "Copia pulita negli appunti", "en": "Clean copy on the clipboard",
    },
    "js_md_scaricato": {"it": "File .md scaricato", "en": ".md file downloaded"},
    "js_txt_scaricato": {"it": "File .txt scaricato", "en": ".txt file downloaded"},
    "js_scegli_cartella": {"it": "Scegli cartella", "en": "Choose a folder"},
    "js_sfoglia_non_disponibile": {
        "it": "Sfoglia non disponibile", "en": "Browse is not available",
    },
    "js_nessuna_cartella": {
        "it": "Nessuna cartella selezionata", "en": "No folder chosen",
    },
    "js_cartella_impostata": {"it": "Cartella impostata", "en": "Folder set"},
    "js_sfoglia_fallita": {
        "it": "Impossibile aprire Sfoglia…", "en": "Could not open Browse…",
    },
    "js_in_ascolto": {"it": "in ascolto", "en": "watching"},
    "js_scegli_cartelle": {
        "it": "Scegli le cartelle con Sfoglia…",
        "en": "Choose the folders with Browse…",
    },
    "err_watch_fallito": {
        "it": "Watch fallito", "en": "Could not start watching",
    },
    "js_monitoraggio_attivo": {
        "it": "Monitoraggio attivo", "en": "Watching started",
    },
    "js_monitoraggio_disattivo": {
        "it": "Monitoraggio disattivato", "en": "Watching stopped",
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
    # ══════════════════════════════════════════════════════════════════
    # Quello che risponde il server: errori JSON e stato dei lavori.
    # Li legge una persona, non un programma — il codice HTTP e' quello
    # che leggono i programmi.
    # ══════════════════════════════════════════════════════════════════
    "err_nessun_file_richiesta": {
        "it": "Nessun file trovato nella richiesta",
        "en": "No file found in the request",
    },
    "err_nessun_file_valido": {"it": "Nessun file valido", "en": "No valid file"},
    "err_tipo_non_supportato": {
        "it": "Tipo di file \"{ext}\" non supportato. Formati: PDF, DOCX, XLSX, "
              "PPTX, HTML, CSV, TXT, EML e immagini.",
        "en": "File type \"{ext}\" is not supported. Formats: PDF, DOCX, XLSX, "
              "PPTX, HTML, CSV, TXT, EML and images.",
    },
    "err_due_file_ab": {
        "it": "Servono esattamente 2 file (file_a e file_b)",
        "en": "Exactly 2 files are needed (file_a and file_b)",
    },
    "err_nome_mancante": {"it": "Nome file mancante", "en": "Missing file name"},
    "err_file_vuoto_nome": {"it": "File vuoto: {nome}", "en": "Empty file: {nome}"},
    "err_inbox_outbox": {
        "it": "Specificare inbox e outbox", "en": "Give both an inbox and an outbox",
    },
    "err_interno_conversione": {
        "it": "Errore interno durante la conversione.",
        "en": "Internal error during conversion.",
    },
    "err_host": {
        "it": "Host '{host}' non consentito. Usa http://127.0.0.1 oppure "
              "imposta MR_RAO_ALLOWED_HOSTS.",
        "en": "Host '{host}' is not allowed. Use http://127.0.0.1, or set "
              "MR_RAO_ALLOWED_HOSTS.",
    },
    "err_cross_site": {
        "it": "Richiesta cross-site rifiutata", "en": "Cross-site request refused",
    },
    "err_richiesta_troppo_grande": {
        "it": "Richiesta troppo grande. Limite {max} MB per l'intero invio "
              "(non per singolo file).",
        "en": "The request is too large. The {max} MB limit is for the whole "
              "upload, not per file.",
    },
    "err_endpoint": {"it": "Endpoint non trovato", "en": "Endpoint not found"},
    "err_metodo": {"it": "Metodo non consentito", "en": "Method not allowed"},
    "err_server_interno": {
        "it": "Errore interno del server", "en": "Internal server error",
    },
    # -- stato di un lavoro ------------------------------------------------
    "job_in_coda": {"it": "In coda…", "en": "Queued…"},
    "job_avvio": {"it": "Avvio conversione…", "en": "Starting conversion…"},
    "job_annullato": {"it": "Annullato", "en": "Cancelled"},
    "job_completato": {"it": "Completato", "en": "Done"},
    "job_batch": {"it": "Batch in corso…", "en": "Batch under way…"},
    "job_file_n": {"it": "File {i}/{n}: {nome}", "en": "File {i}/{n}: {nome}"},
    "job_merge_completato": {"it": "Merge completato", "en": "Merge done"},
    "job_batch_completato": {"it": "Batch completato", "en": "Batch done"},
    # -- cartella sorvegliata ----------------------------------------------
    "watch_msg_non_attivo": {"it": "non attivo", "en": "not running"},
    "watch_msg_in_attesa": {
        "it": "in attesa di file", "en": "waiting for files",
    },
    "watch_msg_cartella_non_valida": {
        "it": "cartella da monitorare non valida", "en": "watched folder not valid",
    },
    "watch_err_cartella_sparita": {
        "it": "La cartella da monitorare non esiste piu'",
        "en": "The watched folder no longer exists",
    },
    "watch_msg_convertendo": {
        "it": "sto convertendo {nome}", "en": "converting {nome}",
    },
    "watch_msg_errore_file": {"it": "Errore: {nome}", "en": "Error: {nome}"},
    "watch_msg_fatto": {"it": "fatto: {nome}", "en": "done: {nome}"},
    "watch_err_spostamento": {
        "it": "Non riesco a spostare l'originale: {motivo}",
        "en": "The original could not be moved: {motivo}",
    },
    "watch_msg_errore": {
        "it": "errore durante il monitoraggio", "en": "error while watching",
    },

    # -- i nomi delle categorie, per il pannello «rilevato ma non sostituito»
    #
    # Le ventiquattro caselle mostravano l'**identificatore grezzo**: chi le
    # leggeva trovava `bban`, `mrz`, `itin`, `routing_number`, `tfn`. Sono i
    # nomi che il codice usa per parlare a se stesso, non a chi decide cosa
    # lasciare in chiaro in un documento.
    #
    # Quindici categorie non avevano un'etichetta perche' stanno tutte sotto
    # un interruttore solo (`fiscal`): fino a quando la scelta era «tutti o
    # nessuno» nessuno aveva avuto bisogno di nominarle una per una.
    #
    # Dove un'etichetta esiste gia' (`opt_emails_titolo` e le altre otto) si
    # riusa quella: due nomi diversi per la stessa cosa, nella stessa
    # pagina, sono un modo di confondere piu' economico di non tradurre.
    "cat_codice_fiscale": {"it": "Codice fiscale", "en": "Codice fiscale"},
    "cat_partita_iva": {"it": "Partita IVA", "en": "VAT number"},
    "cat_iban": {"it": "IBAN", "en": "IBAN"},
    "cat_bban": {"it": "Coordinate ABI/CAB", "en": "ABI/CAB bank details"},
    "cat_cards": {"it": "Carte di pagamento", "en": "Payment cards"},
    "cat_mrz": {
        "it": "Riga a lettura automatica dei passaporti",
        "en": "Passport machine-readable zone",
    },
    "cat_ssn": {"it": "SSN (Stati Uniti)", "en": "SSN (United States)"},
    "cat_itin": {"it": "ITIN (Stati Uniti)", "en": "ITIN (United States)"},
    "cat_nino": {
        "it": "National Insurance number (Regno Unito)",
        "en": "National Insurance number (UK)",
    },
    "cat_nhs_number": {
        "it": "Numero NHS (Regno Unito)", "en": "NHS number (UK)",
    },
    "cat_sin": {"it": "SIN (Canada)", "en": "SIN (Canada)"},
    "cat_routing_number": {
        "it": "Routing bancario ABA (Stati Uniti)",
        "en": "ABA routing number (United States)",
    },
    "cat_abn": {"it": "ABN (Australia)", "en": "ABN (Australia)"},
    "cat_tfn": {"it": "TFN (Australia)", "en": "TFN (Australia)"},
    "cat_termini": {"it": "Termini protetti", "en": "Protected terms"},
    "cat_catasto": {
        "it": "Riferimenti catastali", "en": "Land registry references",
    },
    "cat_pratica": {
        "it": "Numeri di pratica (R.G., protocollo, repertorio)",
        "en": "Case and file numbers (docket, protocol, deed register)",
    },
    "cat_targa": {"it": "Targhe di veicoli", "en": "Vehicle plates"},
    "cat_eta": {"it": "Età", "en": "Age"},
    "cat_genere": {"it": "Sesso", "en": "Sex"},

    # -- età e sesso: si trovano, si dicono, non si tolgono ---------------
    "opt_quasi_id_titolo": {"it": "Età e sesso", "en": "Age and sex"},
    "opt_quasi_id_desc": {
        "it": "Segnalati nel rapporto, mai tolti dal testo",
        "en": "Reported, never removed from the text",
    },
    "tip_quasi_id": {
        "it": "Sono quasi-identificatori: «45 anni» da solo non identifica "
              "nessuno, ma insieme a un comune piccolo e a una professione "
              "sì — ed è esattamente così che si de-anonimizza un archivio. "
              "**Mr. Rao non li toglie mai**, perché chi lavora su una "
              "cartella clinica o su una statistica del personale sta "
              "chiedendo proprio quei due dati, e toglierli renderebbe il "
              "documento inutile senza proteggere nessuno di più. Li trova e "
              "te li dice: «lasciate in chiaro 3 età, apposta» è "
              "un'informazione, il silenzio no. Se vuoi toglierli davvero, "
              "l'elenco «nascondi sempre» lo fa.",
        "en": "These are quasi-identifiers: «45 years old» identifies nobody "
              "on its own, but together with a small town and an occupation "
              "it does — and that is exactly how an archive gets "
              "de-anonymised. **Mr. Rao never removes them**, because "
              "whoever works on a medical record or on workforce statistics "
              "is asking for precisely those two facts, and removing them "
              "would make the document useless while protecting nobody. It "
              "finds them and tells you: «3 ages left in the clear, on "
              "purpose» is information, silence is not. To remove them for "
              "real, the «always hide» list does it.",
    },

    # -- il pacchetto «atti e pratiche», e il suo interruttore -------------
    "pack_atti_titolo": {"it": "Atti e pratiche", "en": "Deeds and case files"},
    "pack_atti_desc": {
        "it": "Catastali, numeri di pratica, targhe. Spento di serie",
        "en": "Land registry, case numbers, plates. Off by default",
    },
    "tip_pack_atti": {
        "it": "Per notai, avvocati e tecnici. In un atto il riferimento "
              "catastale è il dato più sensibile della frase: dice di quale "
              "immobile si parla, e da lì si risale al proprietario; e il "
              "numero di ruolo identifica le parti quanto il loro nome. Per "
              "un'azienda invece il numero di protocollo è ciò che permette "
              "di **ritrovare** la pratica, e toglierlo rende il documento "
              "inservibile senza proteggere nessuno — ed è il motivo per cui "
              "questo pacchetto è spento finché non lo accendi tu.",
        "en": "For notaries, lawyers and surveyors. In a deed the land "
              "registry reference is the most sensitive thing on the line: "
              "it says which property, and from there the owner is one "
              "search away; and the docket number identifies the parties as "
              "surely as their names. For a company, though, the protocol "
              "number is what lets you **find** the file again, and removing "
              "it makes the document useless while protecting nobody — which "
              "is why this pack stays off until you turn it on.",
    },
    "opt_atti_titolo": {
        "it": "Atti e pratiche", "en": "Deeds and case files",
    },
    "opt_atti_desc": {
        "it": "Catastali, numeri di pratica, targhe",
        "en": "Land registry, case numbers, plates",
    },
    "tip_atti": {
        "it": "«Foglio 12 particella 345 sub 6» diventa un segnaposto. Il "
              "foglio da solo non basta: «foglio 3» in una relazione è la "
              "pagina tre, ed è la coppia foglio+particella a dire che si "
              "parla di un immobile. Insieme spariscono i numeri di pratica "
              "(«R.G. 1234/2023», «Prot. n. 55871») — l'etichetta resta, il "
              "numero no — e le targhe. **Serve anche il pacchetto «Atti e "
              "pratiche» acceso**, che di serie non lo è.",
        "en": "«Foglio 12 particella 345 sub 6» becomes a placeholder. The "
              "sheet alone is not enough — «foglio 3» in a report is page "
              "three — it is the sheet+parcel pair that says a property is "
              "meant. Case numbers go too («R.G. 1234/2023», «Prot. n. "
              "55871»): the label stays, the number does not. So do vehicle "
              "plates. **The «Deeds and case files» pack must be on too**, "
              "and by default it is not.",
    },
}

#: Le categorie che nel pannello «rilevato ma non sostituito» non hanno
#: senso.
#:
#: `termini` non e' un dato riconosciuto dal motore: e' la lista di parole
#: che **l'utente stesso** ha chiesto di proteggere. Chiedere di segnalarle
#: invece di sostituirle vuol dire chiedere al programma di disobbedire a
#: una richiesta esplicita, e non c'e' un caso in cui serva: chi non vuole
#: che una parola sia sostituita non la mette nell'elenco.
#: `eta` e `genere` non compaiono qui perche' non stanno nemmeno in
#: `CATEGORIE`: sono **sempre e solo** segnalate, quindi non c'e' niente da
#: escludere — non c'e' proprio la casella.
CATEGORIE_NON_SEGNALABILI = frozenset({"termini"})


def etichetta_categoria(categoria: str, lingua: str = LINGUA_PREDEFINITA) -> str:
    """Il nome leggibile di una categoria.

    Preferisce l'etichetta dell'interruttore, quando esiste: `emails` si
    chiama «Email» in due punti della stessa pagina, e chiamarla in due modi
    diversi costerebbe piu' confusione di quanta ne tolga.
    """
    for chiave in (f"opt_{categoria}_titolo", f"cat_{categoria}"):
        if chiave in TESTI:
            return TESTI[chiave].get(lingua, TESTI[chiave][LINGUA_PREDEFINITA])
    return categoria


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
