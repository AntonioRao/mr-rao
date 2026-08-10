; Installer Inno Setup per Mr. Rao.
;
; PERCHE' ESISTE
;
; Fino alla 1.20.0 le confezioni erano due: lo zip portable, che si scompatta
; e si installa con un .bat, e l'MSIX per il Microsoft Store. In mezzo manca
; il caso piu' comune su Windows: scarico un file, doppio clic, installato.
;
; QUELLO CHE QUESTO FILE NON FA, ED E' LA COSA PIU' IMPORTANTE
;
; Non sa niente di collegamenti, di menu contestuale e di estensioni. Quella
; roba sta in `mr_rao_shell.ps1`, e questo installer lo **chiama**.
;
; Non e' pigrizia: e' il difetto che quello script era nato per chiudere. Il
; suo commento in testa lo racconta -- quando l'elenco delle estensioni
; viveva in due file, i due sono andati fuori sincrono e la disinstallazione
; lasciava voci di menu che puntavano a un eseguibile non piu' esistente.
; Riscrivere qui dentro le undici chiavi del registro vorrebbe dire ricreare
; quel difetto con una confezione in piu': tre installatori, un elenco solo
; che conta, e due copie che si scoprono sbagliate quando qualcuno se ne
; lamenta.
;
; Percio' qui c'e' una regola sola: **se una cosa la sa gia' lo script, non
; la si riscrive**. C'e' un test che lo verifica (`tests/test_installer.py`),
; perche' una regola senza guardia dura fino alla prossima fretta.
;
; ASCII PURO, come `mr_rao_shell.ps1` e per un motivo imparentato: questo
; file viene compilato da `iscc` su un runner GitHub, e un file di testo con
; accenti e senza BOM viaggia fra codifiche diverse senza dire niente finche'
; non compare una parola storpiata dentro la finestra dell'installazione. Le
; stringhe che l'utente legge stanno in [Messages] piu' sotto, dove il
; problema si affronta una volta sola.
;
; INSTALLAZIONE PER UTENTE, SENZA UAC
;
; Destinazione `%LOCALAPPDATA%\MrRao`, la stessa di `Installa Mr Rao.bat`.
; Non `Program Files`: chiederebbe l'elevazione a chi vuole solo convertire
; un documento, e soprattutto e' una cartella che il programma non puo'
; scrivere. La 1.20.0 e' nata da questo -- dentro un pacchetto MSIX la
; cartella d'installazione e' protetta da ACL, il `mkdir` degli upload
; falliva all'importazione e il programma moriva prima di stampare una riga.
; Un installer che mette gli stessi file in un'altra cartella di sistema
; ripeterebbe l'esperimento gia' fatto.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef SorgentePortable
  #define SorgentePortable "..\dist\MrRao-Portable"
#endif
#ifndef Uscita
  #define Uscita "..\dist"
#endif

[Setup]
; L'AppId non cambia mai fra le versioni: e' cio' che fa riconoscere a
; Windows che la 1.21 e' un aggiornamento della 1.20 e non un secondo
; programma. Cambiarlo lascerebbe due voci in "App installate", ognuna con
; la sua disinstallazione, e la prima punterebbe a file che non ci sono piu'.
AppId={{7C4E1A93-8D25-4F60-B3A7-2E9F5C81D046}
AppName=Mr. Rao
AppVersion={#AppVersion}
AppVerName=Mr. Rao {#AppVersion}
AppPublisher=Antonio Andrea Rao
AppPublisherURL=https://rao.valor-cyber.com
AppSupportURL=https://github.com/AntonioRao/mr-rao/issues
AppUpdatesURL=https://github.com/AntonioRao/mr-rao/releases

DefaultDirName={localappdata}\MrRao
DefaultGroupName=Mr. Rao
DisableProgramGroupPage=yes
; La pagina della cartella resta: chi installa su una macchina condivisa o
; su un disco diverso deve poter scegliere, e il valore predefinito e' gia'
; quello giusto per tutti gli altri.
DisableDirPage=no

; `lowest` e' una dichiarazione, non una preferenza: con questo valore
; l'installazione non puo' chiedere l'elevazione nemmeno per sbaglio, e
; nessuna riga aggiunta domani puo' trasformarla in un'installazione di
; sistema senza che qualcuno cambi questa parola.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

OutputDir={#Uscita}
OutputBaseFilename=MrRaoSetup-{#AppVersion}
; lzma2 senza `/max`: su ~400 MB di DLL la differenza di dimensione e'
; piccola e quella di tempo no, e questo passo gira a ogni build in CI.
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

SetupIconFile={#SorgentePortable}\mr-rao.ico
UninstallDisplayIcon={app}\app\MrRao.exe,0
UninstallDisplayName=Mr. Rao
LicenseFile={#SorgentePortable}\LICENSE.txt

; Mr. Rao vive nell'area di notifica: aggiornando, l'eseguibile e' quasi
; sempre in esecuzione. Senza questo l'installazione sovrascriverebbe i file
; a meta' e chiederebbe un riavvio; con questo la finestra chiede di
; chiuderlo, e basta.
CloseApplications=yes
RestartApplications=no
; Un riavvio del computer per un convertitore di documenti non e' una cosa
; che si chiede. Se qualche file resta bloccato lo si dice e si prosegue.
AlwaysRestart=no

[Languages]
Name: "it"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[InstallDelete]
; La versione precedente si **rimuove**, non si sovrascrive.
;
; Il numero e' misurato, non temuto: aggiornando dalla 1.3.2 alla 1.3.3 sono
; rimasti 120 MB di librerie non piu' incluse, perche' una copia sovrascrive
; cio' che trova e non tocca cio' che non c'e' piu'. `Installa Mr Rao.bat`
; fa la stessa cosa per la stessa ragione, ed e' il tipo di dettaglio che
; nessuno nota finche' non guarda lo spazio su disco.
Type: filesandordirs; Name: "{app}\app"

[Files]
Source: "{#SorgentePortable}\app\*"; DestDir: "{app}\app"; \
    Flags: recursesubdirs createallsubdirs ignoreversion
; Lo script dei collegamenti viaggia **dentro** l'installazione, non solo
; nel pacchetto: serve anche alla disinstallazione, che avviene mesi dopo e
; da una cartella che non esiste piu'.
Source: "{#SorgentePortable}\mr_rao_shell.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SorgentePortable}\mr-rao.ico"; DestDir: "{app}"; Flags: ignoreversion
; Obbligo di redistribuzione, non cortesia: pystray e' LGPL.
Source: "{#SorgentePortable}\LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SorgentePortable}\THIRD_PARTY.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SorgentePortable}\licenses\*"; DestDir: "{app}\licenses"; \
    Flags: recursesubdirs createallsubdirs ignoreversion
Source: "{#SorgentePortable}\LEGGIMI.txt"; DestDir: "{app}"; Flags: ignoreversion isreadme
Source: "{#SorgentePortable}\docs\*"; DestDir: "{app}\docs"; \
    Flags: recursesubdirs createallsubdirs ignoreversion skipifsourcedoesntexist

[Icons]
; Solo la voce nel menu Start di Inno. Desktop, "Invia a" e menu contestuale
; li crea `mr_rao_shell.ps1` piu' sotto: farli in due posti vorrebbe dire due
; posti dove possono divergere.
Name: "{userprograms}\Mr. Rao"; Filename: "{app}\app\MrRao.exe"; \
    WorkingDir: "{app}\app"; Comment: "Mr. Rao - da documento a Markdown, offline"

[Run]
; Il collegamento sul Desktop, "Invia a" e le undici voci di menu
; contestuale. `-ExecutionPolicy Bypass` serve perche' lo script non e'
; firmato e la policy predefinita di molte macchine lo rifiuterebbe; lo fa
; gia' `Installa Mr Rao.bat` con le stesse parole.
;
; `runasoriginaluser` non e' decorazione: le chiavi che lo script scrive
; stanno in HKCU e i collegamenti nel profilo. Se girasse con un'altra
; identita' finirebbero nel profilo sbagliato -- installazione riuscita,
; e nessun collegamento dove l'utente li cerca.
Filename: "powershell.exe"; \
    Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\mr_rao_shell.ps1"" -InstallDir ""{app}"""; \
    StatusMsg: "Collegamenti e menu contestuale..."; \
    Flags: runhidden runasoriginaluser

Filename: "{app}\app\MrRao.exe"; Description: "Avvia Mr. Rao"; \
    Flags: nowait postinstall skipifsilent runasoriginaluser

[UninstallRun]
; Toglie collegamenti e voci di registro **prima** che i file spariscano:
; lo script ha bisogno di se stesso, e le voci di menu che restano puntano a
; un eseguibile che non c'e' piu'. E' esattamente il guasto che questo script
; e' nato per chiudere, e disinstallare e' il momento in cui si ripresenta.
;
; Niente `runasoriginaluser` qui: e' un flag di [Run] e in questa sezione
; **non esiste** -- `iscc` risponde «a flag that is not supported in this
; section» e si ferma. Non serve nemmeno: con `PrivilegesRequired=lowest`
; la disinstallazione non e' elevata, quindi gira gia' come l'utente che
; possiede le chiavi HKCU e i collegamenti da togliere.
Filename: "powershell.exe"; \
    Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\mr_rao_shell.ps1"" -InstallDir ""{app}"" -Remove"; \
    RunOnceId: "TogliShell"; Flags: runhidden

[Messages]
it.WelcomeLabel2=Mr. Rao trasforma PDF, Office, scansioni ed email in Markdown pulito, con i dati personali gia' rimossi.%n%nTutto avviene sul tuo computer: nessun documento esce da questa macchina.
en.WelcomeLabel2=Mr. Rao turns PDFs, Office files, scans and email into clean Markdown, with personal data already removed.%n%nEverything happens on your computer: no document ever leaves this machine.
