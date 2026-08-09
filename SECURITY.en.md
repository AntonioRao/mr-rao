# Security

*Questo documento in italiano: [SECURITY.md](SECURITY.md).*

## Threat model

Mr. Rao is a **local, single-user tool**. It needs a web server because the
interface lives in a browser, not because it is a network service.

What follows from that:

- **There is no authentication.** Anyone who can reach the port can convert
  files and start watching a folder.
- **It belongs on `127.0.0.1`.** That is the default. `docker-compose.yml`
  publishes the port on localhost only, deliberately.
- **Exposing it on a network is a deliberate choice** and requires an
  authenticating reverse proxy in front. Without one you are handing anybody
  a converter that writes files to your disk.

A warning about what Mr. Rao is **not**: it is not a sandbox for opening
suspicious attachments. The libraries it uses to read PDF, Office and image
files are the same ones every other program uses, and they run without
isolation. Open the documents you would have opened anyway — not the ones
you would not.

## Defences in place

A server on localhost is reachable by **any page** open in the user's
browser. Distinct attacks, distinct controls:

| Attack | Defence |
|--------|---------|
| **DNS rebinding** — an attacker's domain resolving to `127.0.0.1` in order to read the responses | `Host` header allow-list (`MR_RAO_ALLOWED_HOSTS`), **including when listening on `0.0.0.0`** |
| **CSRF** — a cross-site POST (multipart needs no CORS preflight) starting a conversion or a folder watch | External `Sec-Fetch-Site` refused on state-changing methods, with `Origin` as a fallback |
| **Port neighbours** — another page on `127.0.0.1`, different port: to `Origin` it is the same hostname | `Sec-Fetch-Site: same-site` refused |
| **Side effects from GET** — `<img src="http://127.0.0.1:5000/...">` on any page | GETs are read-only: none of them creates a file or a folder |
| **Clickjacking** — the app framed inside another page to get "start watching" clicked | `Content-Security-Policy: frame-ancestors 'none'` |
| **Worker starvation** — one enormous scan tying up the OCR | Caps on pages, on time (`MR_RAO_OCR_TIMEOUT`) and on upload size |

Why **two** anti-CSRF controls rather than one: the `Origin` check is
conditional on the header being present, and a cross-site `<form>`
navigation can arrive without it. Every current browser sends
`Sec-Fetch-Site` on every request, so it covers that branch; `Origin` stays
for clients that do not send it (curl, the CLI, an older browser).

Every defence has its own test in
[`tests/test_security.py`](tests/test_security.py),
[`tests/test_limiti_ocr.py`](tests/test_limiti_ocr.py) and
[`tests/test_user_folders.py`](tests/test_user_folders.py). They are not
decorative: switch a defence off and its test goes red — verified by
switching them off one at a time.

## Signing key

`SECRET_KEY` is random at every start and is **never written to disk**.

Nothing uses it today: no sessions, no signed cookies. The reason for the
change is a future one — the day somebody writes `session[...]`, which in
Flask is one line, a constant committed to a public repository would become
the key that signs the cookies, and nothing would break loudly enough to
notice.

A local file would have been worse than the constant: it would follow the
portable executable into OneDrive, into backups and into the zip handed to a
colleague. It becomes necessary only when sessions have to survive a
restart. `MR_RAO_SECRET` pins it, should that day come first.

## Exposing the app on a network

With `MR_RAO_HOST=0.0.0.0` the host allow-list does **not** become `*`: it
contains this machine's addresses and names. Legitimate access by IP or by
hostname works; the attacker's domain, which carries its own name in the
`Host` header, does not.

Behind a reverse proxy with a public name, declare it:

```bash
MR_RAO_ALLOWED_HOSTS="mr-rao.company.com"
```

Without it the answer is a 403 that names the variable instead of leaving
you to guess.

## How files are handled

- Uploaded files go to a system temporary file, deleted immediately after
  the conversion.
- Pages rasterised during OCR live in a temporary directory that removes
  itself, even if the process dies halfway.
- The interface history is only in the browser's memory: close the page and
  it is gone.
- Job results stay in RAM for at most an hour, with a cap on how many are
  kept.

## Known limits

- **Redaction is not a guarantee.** The recognisers are good but not
  perfect, especially on names. The before/after view exists so that you can
  check: use it before sharing a document.
- **On text obtained through OCR the protection is appreciably weaker.**
  Measured: the same content read from an image produces 3 redactions, read
  from a scanned PDF it produces 1, because OCR mangles the characters
  (`IBAN IT60X…` becomes `TBAN1TB0X…`) and the pattern no longer matches.
  The data stays in the text, deformed but often still identifying. The
  result carries an explicit warning.
- **Cancelling a conversion does not stop it instantly.** The flag is read
  when moving from one stage to the next; a single call into the conversion
  library cannot be interrupted from outside. The same applies to the OCR
  time limit: it stops the following pages, not the page in progress.
- **An OCR truncated by time produces a partial result**, and therefore a
  partial redaction. The document says so at the top, not at the bottom.
- **Watched-folder paths are not confined.** Whoever uses the interface
  picks inbox and outbox wherever they like — that is the feature, not an
  oversight: a hotfolder has to be able to live in Documents or on a network
  drive. The defence is that no external page can start it (see above), and
  that writing produces **only** `.md` files, never overwriting an existing
  one.
- **No sandbox.** The threat model does not include documents crafted to
  attack the parsers. A serious sandbox on Windows (job object,
  AppContainer) is a project of its own; a fake one would protect against
  nothing, and promising it would be worse than not having it.

## Reporting a problem

Open an issue describing:

1. what you did,
2. what you expected,
3. what happened.

For a vulnerability you consider sensitive, write to the author privately
instead of opening a public issue.

An elaborate proof of concept is not required: even "this endpoint does X
and should not" is a useful report.
