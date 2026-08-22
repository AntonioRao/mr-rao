# Mr. Rao — Security report sito pubblico 22 agosto 2026

> **Destinatario:** seconda opinione indipendente (Claude o altro revisore).
> Verbale di **misura** su `https://rao.valor-cyber.com` (landing Cloudflare Pages). Non è un audit del tool desktop su `127.0.0.1`.
> Ogni «200 HTML / header presente / non è `.git`» corrisponde a un GET/HEAD del 22/08/2026 o a un file letto.
> **Non contiene segreti.**

**Revisione 2 — 22/08/2026, ore 07:xx.** La prima stesura è stata verificata riga per riga: file letti, sito interrogato di nuovo. Tre esiti, tutti scritti qui sotto:

- la maggior parte delle affermazioni **regge** (§2, §4);
- **MR-L2 era falso** e **MR-L3 sbagliava il numero che era il suo unico contenuto** (§5);
- il report **non vedeva due file veri** serviti dal sito, e con loro il meccanismo che li aveva messi lì (**MR-M3**, §5).

Le correzioni sono state applicate e rimisurate lo stesso giorno: §11 è il verbale di cosa è cambiato e di come lo si è verificato.

Documenti correlati:

- Questo sito (publish): `docs/landing/publish/_headers`, `docs/landing/rigenera_pubblicato.py`
- Tool locale (altra superficie): `SECURITY.md` / `SECURITY.en.md` — **non** descrivono il sito pubblico
- Privacy landing: `docs/PRIVACY.md`, pagine `/plus/privacy/`

Report gemelli:
`C:\ciso-fight\security-report-22-agosto-2026.md` (Fight + Academy)
`C:\valor\docs\security-report-22-agosto-2026.md` (piattaforma VALOR)

---

## 0. Come usare questo documento (checklist per chi verifica)

1. **Due prodotti, due modelli.** Non mescolarli.
   - **Sito** `rao.valor-cyber.com`: marketing statico (home, `/plus/`, `/mobile/`, privacy, APK). Nessun account, nessuna API, nessun dato utente.
   - **App desktop** Mr. Rao: server locale, **senza autenticazione**, bind `127.0.0.1` *di default* (`MR_RAO_HOST` lo cambia — `config.py:139`). Difese in `SECURITY.md`. **Fuori da questo verbale** salvo il richiamo in §8.
2. Sorgente del sito: `C:\Users\anton\mr-rao\docs\landing\publish\`. Rigenerazione pagine e impronte CSP: `python docs/landing/rigenera_pubblicato.py` — **lo script sta fuori dalla cartella pubblicata**, e §5/MR-M3 dice perché.
3. Un GET `/.git/HEAD` che torna **200** **non** basta per gridare «repo esposto». Leggere `Content-Type` e i **primi byte** del body. Dal 22/08 pomeriggio quel path torna **404**; prima era `text/html` della homepage (51 981 byte, `<!DOCTYPE html>`).
4. Non nuclei/ZAP sull'origine. HEAD/GET di path pubblici sì. Non scaricare l'APK in un report.
5. **Non fermarsi allo status code, e non fermarsi al file.** Le due lezioni di questa revisione: un `_headers` che dichiara `max-age=3600` non garantisce che il browser lo riceva (§5/MR-L3), e una cartella che contiene un file lo **pubblica** (§5/MR-M3).
6. Per ogni finding MR-M* / MR-L*: file:riga o comando, confermato / smentito / corretto.
7. **La cache di bordo mente a chi verifica.** Un file appena tolto dal deploy continua a rispondere 200 per un po': interrogare con `Cache-Control: no-cache` **e** un parametro di cache-busting, altrimenti si misura la risposta di prima. Successo durante questa revisione.

---

## 1. Snapshot

| Campo | Valore misurato 22/08/2026 (dopo l'intervento di §11) |
|-------|----------------------------|
| Host | `https://rao.valor-cyber.com` |
| Piattaforma | Cloudflare Pages (static) |
| Home | 200 `text/html; charset=utf-8`, 51 981 byte |
| `/plus/` `/mobile/` `/plus/privacy/` `/plus/privacy/en/` `/en/` `/impresa/` | 200 HTML (pagine vere) |
| `/mobile/MrRao.apk` | 200 `application/vnd.android.package-archive`, 2 535 566 byte, `Content-Disposition: attachment` |
| Path inesistenti | **404** con pagina d'errore propria (2 158 byte) |
| Cookie | **nessuno** (verificato su quattro pagine) |
| Auth / API | **nessuna** sul sito |
| CORS | **nessun header** `Access-Control-Allow-Origin` (era `*`) |
| Tree locale publish | `docs/landing/publish/` — 33 file, tutti pagine, asset, font, CSS, APK, `_headers` |

TLS: stesso edge del dominio `valor-cyber.com`. Probe HTTP: 301 → HTTPS (misurato).
**Non verificato:** che il dominio sia davvero nella lista *preload* dei browser. L'header dichiara `preload`, che è una cosa diversa dall'esserci.

### Cosa è il sito

Landing del prodotto Mr. Rao: `/` desktop, `/en/` inglese, `/plus/` estensione, `/mobile/` Android + APK, `/plus/privacy/` informativa, `/impresa/`, font e logo self-hosted.

Non è l'app. Convertire file e monitorare cartelle accade **solo** nel processo locale.

---

## 2. Header osservati (`HEAD /`)

| Header | Valore live 22/08, dopo l'intervento |
|--------|-------------------|
| Strict-Transport-Security | `max-age=31536000; includeSubDomains; preload` |
| Content-Security-Policy | `default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'; script-src 'self' 'sha256-TCZ0…' 'sha256-dv+Z…'; style-src 'self' 'sha256-2yCi…' 'sha256-rWeI…'; font-src 'self'; img-src 'self' data:; connect-src 'self'; worker-src 'none'; manifest-src 'self'; upgrade-insecure-requests` |
| X-Frame-Options | `DENY` |
| X-Content-Type-Options | `nosniff` |
| Referrer-Policy | `strict-origin-when-cross-origin` |
| Permissions-Policy | lunga (camera/mic/geo/payment/usb/… tutti `()`) — coincide con `_headers` L19 |
| Cross-Origin-Opener-Policy | `same-origin` — `_headers` L21 |
| Cross-Origin-Resource-Policy | `same-origin` — **`_headers` L22, blocco globale** (vedi MR-L2) |
| Access-Control-Allow-Origin | **assente** — era `*`, staccato in `_headers` (§11) |
| Cache-Control | `public, max-age=0, must-revalidate` |
| Set-Cookie | assente |

Il CSP live è **identico**, carattere per carattere, alla riga di `_headers`: confrontato, non guardato di sfuggita. I due hash script e i due style sono per **IT + EN** (commento L2–5 del file). Un cambio a un inline senza rigenerare **rompe il caricamento** di quella pagina: è voluto, ed è stato verificato oggi che la CSP blocca davvero (un attributo `style=` su `/mobile/` non veniva applicato — corretto).

Questa CSP è **più stretta** di Fight/Academy (hash, non `'unsafe-inline'` sugli script; font `'self'`; `worker-src 'none'`; `upgrade-insecure-requests`) e del marketing `valor-cyber.com`.

---

## 3. Path probe

### 3.1 Pagine e asset veri

Tutti 200 con il proprio tipo: le sei pagine, `/assets/*.svg` (`image/svg+xml`), i sette woff2 (`font/woff2`), i CSS, l'APK. **Inventario completo**: i 33 file di `publish/` sono stati interrogati uno per uno, non a campione.

### 3.2 Path inesistenti — ora 404 veri

| Path | Prima (mattina) | Adesso |
|------|------|--------|
| `/.git/HEAD` `/.env` `/wrangler.toml` `/package.json` | 200 `text/html`, homepage 51 981 byte | **404** + pagina d'errore |
| `/admin` `/login` `/api/` `/VERSION` `/sitemap.xml` `/main.js.map` | idem | **404** |
| `/.well-known/security.txt` | idem | **404** (MR-L1 resta aperto) |
| `/robots.txt` | idem | **200 `text/plain`** — vedi sotto |

**Test del falso positivo**, da tenere: se `/.git/HEAD` tornasse 200 con `Content-Type: text/plain` e un body che comincia con `ref:`, quella sarebbe un'emergenza vera. Un 200 `text/html` che comincia con `<!DOCTYPE` era un ripiego; oggi non c'è nemmeno più il ripiego.

**`/robots.txt` non è nostro.** Con il ripiego HTML era mascherato; adesso che i path inesistenti fanno 404, emerge il **robots.txt gestito da Cloudflare** (Content Signals Policy: `search`, `ai-input`, `ai-train`). Non è un file del repository e non lo controlliamo da `_headers`: si spegne o si sostituisce dal pannello, sotto *AI Crawl Control*. Metà di MR-L1 è quindi coperta dalla piattaforma, non da noi — cosa diversa dall'averlo fatto.

### 3.3 CORS preflight

`OPTIONS /` con `Origin: https://evil.example` → **405** (Pages non gestisce il preflight). L'header `Access-Control-Allow-Origin: *` che c'era sulle GET **non c'è più** (§11).

### 3.4 Non eseguito

- Analisi dell'APK (signing, backup, cleartext, tracker): altro perimetro (`docs/mr-rao-android.md`, `docs/CODE-SIGNING-POLICY.md` — entrambi esistono, verificato).
- Estensione Plus (store): non è questo host.
- App desktop e i suoi test CSRF/DNS-rebinding: `SECURITY.md`, suite in `tests/`.
- Nuclei.
- Presenza reale nella lista HSTS preload dei browser.

---

## 4. Controlli che tengono

| Controllo | Evidenza |
|-----------|----------|
| HSTS | header live + `_headers` L20 |
| Clickjacking | XFO DENY + CSP `frame-ancestors 'none'` |
| Script | solo `'self'` + due hash; niente `'unsafe-inline'` sugli script |
| Font | `'self'` — woff2 in `docs/landing/publish/fonts/`; **zero riferimenti** a `fonts.googleapis`/`gstatic` in tutta la cartella (cercato) |
| COOP / CORP | `same-origin`, entrambi nel blocco globale di `_headers` |
| Permissions-Policy | deny-list ampia |
| Nessun cookie | `Set-Cookie` assente su `/`, `/plus/`, `/mobile/`, `/plus/privacy/` |
| APK come attachment | `_headers` L46–50, verificato live |
| Hash CSP legati al rigeneratore | commento in testa a `_headers`; `tests/test_landing_pubblicata.py` confronta i file generati e conta le impronte |
| Difese dell'app locale (§8) | esistono nel codice: `config.py:217`, `mr_rao/app_factory.py:39` e `:114` |

---

## 5. Findings

### MR-M1 — `Access-Control-Allow-Origin: *` — Media (igiene / coerenza) — **CHIUSO 22/08**

**Confermato** in verifica: live sì, in `_headers` no. E anche su `valor-cyber.com`, `www.valor-cyber.com` e `mr-rao.pages.dev` → non era una scelta di questo sito.

**Origine, misurata e non dedotta:** nel pannello, la lista delle regole della zona `valor-cyber.com` è **vuota** — nessuna Transform Rule lo aggiunge. È il comportamento predefinito di Cloudflare Pages.

**Correzione applicata:** una riga in `_headers`, non una modifica al pannello — così sta in git, si rilegge in una revisione e non dipende da chi ricorda di averla fatta:

```
/*
  ! Access-Control-Allow-Origin
```

**Verificato dopo il deploy:** l'header non compare più su `/`, `/mobile/`, `/mobile/MrRao.apk`, `/assets/logo.svg`, `/404.css`, `/.git/HEAD`.

### MR-M2 — Fallback 200 HTML su path inesistenti — Bassa/Media — **CHIUSO 22/08**

**Confermato**: undici path inventati tornavano tutti 200 con la homepage.

**Correzione applicata:** `docs/landing/publish/404.html` (+ `404.css`). Cloudflare Pages, se trova una `404.html` alla radice, la serve **con stato 404** al posto del ripiego. Nessuna Transform Rule, nessun `not_found_handling` da toccare nel pannello.

Due vincoli, scritti perché non si scoprano dopo: la pagina **non può avere inline** (`<style>`/`<script>`), che la CSP a impronte bloccherebbe — lo stile sta in `404.css`; ed è **bilingue in una pagina sola**, perché il ripiego non sa quale lingua cercasse chi ci è finito.

**Verificato:** `/.git/HEAD` → 404; la pagina si carica con lo stile applicato (`color: rgb(61,255,154)`), il marchio caricato, **zero violazioni CSP** in console.

### MR-M3 — La cartella pubblicata spediva anche ciò che non era il sito — Media — **CHIUSO 22/08** *(non era nel report)*

Il primo report non guardava l'inventario. Interrogando **tutti** i 33 file di `publish/`, due erano serviti e non dovevano esserci:

| Path | Cosa era |
|------|----------|
| `/_rebuild.py` | 200, `application/octet-stream`, 8 423 byte, **byte per byte identico** al file su disco: lo script che costruisce il sito, pubblicato sul sito |
| `/test-results/.last-run.json` | 200, `application/json`, 45 byte: `{"status": "failed", "failedTests": []}` — un residuo di Playwright, mai tracciato da git |

Nessuno dei due conteneva segreti: il primo è AGPL e sta già su GitHub, il secondo dice solo che una corsa di test era rossa. **Il finding non sono i due file: è il meccanismo.** `wrangler pages deploy docs/landing/publish` spedisce *tutto quello che si trova nella cartella*, tracciato o no, e nessuno se ne accorge. Al loro posto può esserci qualunque cosa qualcuno appoggi lì.

**Cosa non funziona, provato:** `.assetsignore` — Pages lo ignora **e pubblica anche quello** (misurato: `/.assetsignore` → 200, 769 byte).

**Correzione applicata:**

- `test-results/` rimossa;
- lo script spostato in `docs/landing/rigenera_pubblicato.py`, **fuori** dalla cartella pubblicata, con tutti i richiami aggiornati (quattro script, tre banchi, tre documenti);
- un banco nuovo, `test_nella_cartella_pubblicata_non_ci_sono_file_di_troppo`, elenca la cartella e fallisce su qualunque file che non sia una pagina, un asset, un font, un CSS, l'APK o `_headers`. È questo che impedisce al difetto di tornare.

**Verificato:** entrambi i path → 404. `.wrangler/` (che contiene l'id dell'account) **non** era servito nemmeno prima: Pages salta le cartelle che cominciano per punto, e anche questo è stato misurato invece che dedotto.

### MR-M3-bis — «chiuso» misurato sul deploy invece che sul servizio — Media — **il difetto è chiuso, la copia servita no**

Segnalato dall'utente poche ore dopo aver letto «CHIUSO» qui sopra: `/_rebuild.py` → 200, 8 423 byte; `/test-results/.last-run.json` → 200. Aveva ragione, e la voce MR-M3 era stata dichiarata chiusa con una misura che rispondeva a **un'altra domanda**.

**Le due domande, che non sono la stessa:**

| Domanda | Come si misura | Risposta il 22/08 |
|---|---|---|
| il file è nel deploy? | con un `?cb=` (la query cambia la chiave di cache → si arriva all'origine) | **no**, 404 |
| un visitatore lo riceve? | **senza** query e **senza** `Cache-Control` | **sì**, 200 |

Verificare la prima e scrivere «chiuso» è l'errore. Un `Cache-Control: no-cache` mandato dal client **non** basta: Cloudflare lo ignora. È la query string a cambiare la chiave.

**Dove sta la copia, misurato:** non nella cache di zona. Una `Purge Everything` **confermata dal pannello** («Purge request successfully received») non ha azzerato l'`Age`, che continua a crescere dal momento del deploy in cui quei file c'erano ancora. La risposta porta `cf-cache-status: DYNAMIC`, `Cache-Control: public, s-maxage=604800`, `x-robots-tag: noindex` e le **impronte CSP di un deploy vecchio**. L'alias di produzione `mr-rao.pages.dev` risponde 404 sugli stessi percorsi: è quindi qualcosa legato al **nome host**, davanti a Pages.

**Cosa non l'ha risolto** (tutto provato e misurato): quattro deploy successivi; `Purge Everything`; purga per hostname; purga per URL; tre regole `404` esplicite in `_redirects` — che non vengono nemmeno consultate, perché la copia viene servita prima.

**Cosa resta da fare:** ripuntare il dominio personalizzato sul progetto Pages (toglierlo e rimetterlo), che è l'unico rimedio rimasto e va fatto sapendo che il sito resta irraggiungibile per il tempo della riassegnazione. In alternativa la copia scade da sola: `s-maxage` dichiara sette giorni.

**Cosa è cambiato perché non ricapiti:** `scripts/check_sito_non_espone.py` interroga il sito **come un visitatore** — nessuna query, nessuna intestazione — su un elenco di percorsi vietati che comprende *i file che ci sono finiti davvero*, non solo i classici da scanner. Gira ogni giorno insieme al controllo delle versioni (`.github/workflows/sito-pubblicato.yml`) e distingue due guasti opposti: «serve ciò che non deve» e «non serve ciò che deve» — perché un sito spento risponde 404 a tutto, e un controllo che cerca solo i 200 di troppo lo chiamerebbe pulito.

### MR-L1 — `security.txt` — Bassa — **CHIUSO 22/08**

**Scritto e pubblicato.** Contact (lo stesso indirizzo che le pagine mostrano già in nove punti: non espone niente di nuovo), Expires, Preferred-Languages, Canonical, Policy che rimanda a `SECURITY.md`.

**Dove sta, e perché non dove dovrebbe:** Cloudflare Pages **non pubblica le cartelle che cominciano per punto** — misurato: il file al suo posto standard rispondeva 404, come `.assetsignore` e `.wrangler/`. Sta quindi in `/security.txt`, e all'indirizzo di RFC 9116 ci arriva una riscrittura in `_redirects` (`200`, non `301`: chi cerca è uno strumento, e riceve il file invece di un salto da seguire).

**Verificato:** `/.well-known/security.txt` e `/security.txt` → 200 `text/plain; charset=utf-8`, 1 428 byte, stesso contenuto.

**La scadenza è sorvegliata.** Un `security.txt` scaduto è peggio di uno assente: promette un canale che nessuno guarda più. `Expires` è il 22/08/2027, e `tests/test_landing_pubblicata.py` diventa rosso **trenta giorni prima** — non il giorno dopo, quando il danno è fatto.

`robots.txt` non è in questa voce: lo serve Cloudflare (§3.2), e la domanda è semmai se quel contenuto è quello che si vuole dire.

### MR-L2 — CORP sul documento HTML — **SMENTITO**

Il report diceva: *«CORP è su `/fonts/*` e `/assets/*` (L20, L25), non nel blocco globale L7–15»*, e attribuiva l'header visto sulla home a «probabilmente Pages o cache».

**Falso.** `Cross-Origin-Resource-Policy: same-origin` è nel blocco `/*` (riga 14 quel giorno, 22 dopo l'aggiunta di §11), e c'è dal commit `cbb5661` dell'8 agosto 2026 — verificato leggendo il file e la sua storia in git. L'header live viene da lì. Non c'è niente da rendere esplicito: era già esplicito.

Vale la pena dire **come** l'errore è passato: chi ha scritto la voce ha guardato le due occorrenze sotto `/fonts/` e `/assets/` e ha concluso sull'assenza della terza senza cercarla. È lo stesso modo in cui nascono i falsi positivi che questo documento esiste per smontare.

### MR-L3 — Cache dell'APK — **CORRETTO, poi CHIUSO 22/08**

Il report diceva «cache 1 h» e ne traeva: *«chi vuole l'APK vecchio in cache ha al massimo 1 h»*. Ha letto la riga `max-age=3600` di `_headers` senza misurare la risposta.

**Live erano 14 400 secondi: quattro ore.** Quattro volte il numero su cui poggiava l'unica affermazione della voce.

**Perché:** *Browser Cache TTL* della zona = **4 ore** (letto nel pannello). Si comporta da pavimento: alza i valori più bassi e lascia stare quelli più alti. Ecco perché `/fonts/*` (1 anno) e `/assets/*` (7 giorni) arrivavano intatti e solo l'APK no.

**Correzione applicata:** una **Cache Rule** limitata a un solo file —
`http.host eq "rao.valor-cyber.com" and http.request.uri.path eq "/mobile/MrRao.apk"` → *Eligible for cache*, *Browser TTL: Respect origin TTL*.

Ristretta all'APK di proposito: applicarla a tutto il sito avrebbe reso l'HTML «eligible for cache», e una pagina servita dal bordo dopo un deploy è **esattamente** il difetto già pagato il 9 agosto (il sito che resta indietro senza dirlo). Il TTL di zona non è stato toccato: vale ancora per gli altri siti.

**Verificato:** `/mobile/MrRao.apk` → `public, max-age=3600`. Home e `/mobile/` restano `max-age=0, must-revalidate`; font e asset invariati.

### MR-L4 — APK pubblico con nome senza versione — Info / by design

`/mobile/MrRao.apk` fisso: il link è scritto anche fuori dal sito. Non è un leak. La pagina dichiara versione, dimensione e SHA-256 del file servito, ed è quella la cosa che dice quale versione si sta scaricando — verificato oggi: l'APK servito è **byte per byte** quello firmato (`0f34a5a9…`, 2 535 566 byte, Mr. Rao Mobile 0.1.7).

---

## 6. Cosa non è un finding

- 404 su `/admin` `/login` `/api/`: non esistono quelle app sul sito.
- Source map: `/main.js.map` non esiste.
- Assenza di cookie e di autenticazione: è una landing.
- `Server: cloudflare`.
- `.wrangler/` nella cartella sorgente: contiene l'id dell'account ma **non viene pubblicato** (misurato).

---

## 7. Playbook di verifica

Tempo: 15–25 min.

1. `curl -sI https://rao.valor-cyber.com/` — confronta con `docs/landing/publish/_headers`. `Access-Control-Allow-Origin` **non deve esserci**.
2. `curl -sI https://rao.valor-cyber.com/.git/HEAD` → **404**. Se tornasse 200, leggere `Content-Type` e i primi byte prima di allarmarsi.
3. Stesso per `/.env`, `/_rebuild.py`, `/test-results/.last-run.json`: tutti 404.
4. **Con cache-busting**: `?cb=$RANDOM` e `-H "Cache-Control: no-cache"`. Senza, si misura la risposta di prima — successo durante questa revisione.
5. `curl -sI https://rao.valor-cyber.com/mobile/MrRao.apk` — `application/vnd.android.package-archive`, `Content-Disposition: attachment`, `max-age=3600`.
6. Inventario, non campione: elencare `docs/landing/publish/` e interrogare ogni file. Oppure lanciare `pytest tests/test_landing_pubblicata.py`, che lo fa sui file locali.
7. Impronte CSP: se si cambia un inline nelle due pagine, `python docs/landing/rigenera_pubblicato.py` deve aggiornare `_headers`. Un hash stantio **rompe** la pagina (fail-closed): è il comportamento giusto.
8. Non usare `SECURITY.md` della root come stato del sito: parla del server locale.
9. Tabella finding: confermato / smentito / corretto.

---

## 8. Fuori perimetro (così non si confonde)

`SECURITY.md` in radice `mr-rao` riguarda **l'app locale**:

- niente auth, bind `127.0.0.1` **di default** (`MR_RAO_HOST` lo cambia)
- DNS rebinding → `MR_RAO_ALLOWED_HOSTS` (`config.py:217`)
- CSRF → `Sec-Fetch-Site` + `Origin` (`mr_rao/app_factory.py:39`)
- GET solo lettura — **non verificato in questa revisione**
- CSP `frame-ancestors 'none'` sull'app (`mr_rao/app_factory.py:114`)

Se ti chiedono «Mr. Rao è sicuro?», sono **due** risposte. Questo file risponde solo al sito.

---

## 9. Priorità

1. ~~Togliere `Access-Control-Allow-Origin: *`~~ — fatto (MR-M1).
2. ~~404 vero sui path inesistenti~~ — fatto (MR-M2).
3. ~~Non pubblicare ciò che non è il sito~~ — fatto, con un banco che lo tiene (MR-M3).
4. ~~Far arrivare al browser il `max-age` dichiarato per l'APK~~ — fatto (MR-L3).
5. ~~`security.txt`~~ — fatto (MR-L1), con la scadenza sorvegliata da un banco.
6. **`robots.txt` gestito da Cloudflare**: leggerlo e decidere se è quello che si vuole dire (§3.2). È l'unica voce ancora aperta.

---

## 10. Esito in una frase

**Il 22 agosto 2026, dopo l'intervento, `rao.valor-cyber.com` è una landing statica con CSP a hash, font in casa, COOP/CORP, HSTS, nessun cookie, nessun header CORS, 404 veri sui path inesistenti e un `security.txt` con la scadenza sorvegliata, e nella cartella pubblicata solo ciò che è il sito. Le due cose che la prima stesura di questo report non aveva visto — uno script di build servito online e un residuo di test — erano lì per lo stesso motivo, e ora c'è un banco che se ne accorge al posto nostro.**

---

## 11. Verbale dell'intervento del 22/08/2026

| Cosa | Dove | Verifica |
|------|------|----------|
| Staccato `Access-Control-Allow-Origin` | `_headers`, riga `! Access-Control-Allow-Origin` | header assente su sei path |
| Aggiunta pagina 404 | `publish/404.html` + `404.css` | undici path inventati → 404; nessuna violazione CSP; stile e marchio caricati |
| Tolto il residuo di Playwright | cancellata `publish/test-results/` | 404 **dal deploy**; una copia continua a essere servita sul dominio, vedi MR-M3-bis |
| Spostato il rigeneratore | `publish/_rebuild.py` → `docs/landing/rigenera_pubblicato.py` | 404; lo script rigenera le due pagine e `_headers` identici a prima |
| `.assetsignore` provato e scartato | — | Pages lo ignora e lo pubblica: `/.assetsignore` → 200. Rimosso |
| Cache Rule per il solo APK | pannello Cloudflare, zona `valor-cyber.com` | `/mobile/MrRao.apk` → `max-age=3600`; HTML, font e asset invariati |
| Banco che impedisce il ritorno | `tests/test_landing_pubblicata.py` | fallisce se in `publish/` compare un file che non è pagina/asset/font/CSS/APK/`_headers` |
| Scritto `security.txt` | `publish/security.txt` + riscrittura in `_redirects` | 200 `text/plain` su tutti e due gli indirizzi; un banco fallisce 30 giorni prima della scadenza |

Nella stessa sessione, ma **fuori dal perimetro di sicurezza**, è stata corretta la barra di navigazione sul telefono: su 375 px teneva undici voci, diventava alta 187 px e copriva 91 px di titolo. Ora tutte le pagine usano lo stesso menu a scomparsa sotto i 72rem. È nel changelog, non qui: non era un problema di sicurezza, e mescolarlo renderebbe questo verbale meno leggibile.

**Non toccato nel pannello:** *Browser Cache TTL* di zona (4 ore) resta com'è — vale per gli altri siti della zona e cambiarlo sarebbe stato un intervento fuori dal perimetro di questo verbale. La Cache Rule lo scavalca per un file solo.
