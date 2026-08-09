# FAQ for people inspecting the redaction engine

*Questo documento in italiano: [PRIVACY_FAQ.md](PRIVACY_FAQ.md).*

Eleven questions a reviewer (human, or assisted by an AI) asks on opening
[`mr_rao/privacy.py`](../mr_rao/privacy.py), the tests and this document.
The answers are aligned to the code: if the code changes and this page does
not, the code wins.

For behaviour per data type: [PRIVACY.en.md](PRIVACY.en.md).
For the local server's threat model: [SECURITY.en.md](../SECURITY.en.md).

---

## 1. Is this a GDPR "anonymisation" engine?

**No — not in the strong sense of the word.**

In EDPB/WP29 terms, *anonymisation* is irreversible and makes
re-identification reasonably impossible. Mr. Rao does **assisted redaction**
(and in part crude pseudonymisation): it replaces pieces of text with
placeholders (`{{CODICE_FISCALE}}`, `{{NAME}}`, …) and leaves the rest of the
document intact — roles, facts, structure, the sequence of events:
everything that identifies a person **without naming them**. Amounts can be
removed, but that box is off by default, so with the default settings they
stay too.

Using it to *reduce* exposure before pasting into an AI, with a human
checking the before/after, is the stated purpose. Using it to say "this file
no longer contains personal data" is **not**.

The code and the documentation talk about redaction, substitution and
limits — not about certification or automatic DPIAs.

---

## 2. How does it decide what to remove? Is there a model?

**No model takes part in the decision.**

Every recogniser is a **pair**: a regular expression that nominates a
candidate + a **validator** that accepts or rejects it.

Examples from the code:

| Data | Validator |
|------|-----------|
| IBAN | mod-97 (ISO 13616) |
| Card | Luhn (ISO/IEC 7812) |
| Italian tax code | 16-character structure + check character (informative / recovery) |
| Italian VAT number | 11 digits + the Italian check digit (informative) |
| Phone | dialling prefix, `3xx` mobile, separators or a context word |
| Amount | currency, thousands separator or accounting context (off by default) |

The same input always produces the same output. Every substitution can be
explained by pointing at the rule. Main file:
[`mr_rao/privacy.py`](../mr_rao/privacy.py).

There are two neural networks in the package, and both sit **upstream** of
this table: RapidOCR (~30 MB of `.onnx` models) reads scans, magika (~3 MB,
loaded by MarkItDown) guesses the file type. They run offline on the CPU and
decide nothing: they hand over text, and from there the rules are in charge.
Detail in [PRIVACY.en.md](PRIVACY.en.md#how-recognition-works).

---

## 3. Why not use Presidio / NER / an LLM for names?

**A product choice, not ignorance of the state of the art.**

The tool's binding goals:

1. **100% local**, zero network calls in the application code
2. **Deterministic** and inspectable by a CISO or a colleague
3. **No model in the decision** — the ones already included (OCR, file type)
   only read, and there is nothing to download or train
4. Specialisation in **Italian documents** (tax code, VAT number, IBAN,
   local writing habits)

Presidio plus NLP, or a local LLM, would raise recall on names in many
cases, at the price of size, of results that are no longer repeatable, of
extra dependencies and of an engine you cannot verify by reading it. Here
names use **four signals** (title, role before a colon, email, list — each
with corroboration) and lists in
[`mr_rao/it_names.py`](../mr_rao/it_names.py) — incomplete by definition.

Anyone who needs an enterprise multilingual pipeline should look elsewhere
(or extend this engine: it is AGPL). Anyone who needs an offline,
inspectable pre-filter before ChatGPT has the right perimeter here.

---

## 4. Are rare surnames and names outside the lists always removed?

**No.**

Signals, from strongest to weakest:

1. Professional title (Dott., Ing., Avv., …)
2. Role, colon, surname in capitals (`Il Ministro: GIORGETTI`) — the
   signature on Italian public acts, added in 1.17.0
3. A name next to an email address
4. A known first name "pulling" the word after it

There used to be a fifth rule — two capitalised words that do not look like
Italian words — which decided **with no corroboration at all**: it was
**withdrawn in 1.13.0**, because across twenty-seven blank administrative
forms it cost 2,529 wrong substitutions against 27. The price is declared: a
name outside the lists and without context now stays, and does not even
produce a suspect.

A rare surname with no context can stay. A surname that is also a common
word can stay. That is why the **before / after** comparison exists in the
UI: it is not cosmetic, it is the intended check.

---

## 5. What happens with scans and an OCR that gets a character wrong?

**Protection is weaker on dirty text — and the engine handles it in two
ways.**

The exact recognisers look for *valid* shapes. OCR produces *almost* valid
ones (`O`/`0`, `l`/`I`, …).

From 1.5.x onwards:

- **Suspects** — what resembles data and was not substituted appears in the
  report (`suspects`) and in the UI as "to check", with a masked sample.
- **OCR recovery (1.6.x)** — for tax codes and IBANs: up to **two** typical
  confusions; substitution happens **only** if the corrected candidate's
  checksum computes. A heuristic does not decide: the arithmetic decides.

Remaining limits:

- three or more errors → often neither recovery nor certainty
- phone numbers and names have **no** checksum
- degradation **has been measured** since 1.11
  (`scripts/bench_scansioni.py`, table in
  [PRIVACY.en.md](PRIVACY.en.md#declared-limits)): on a faded photocopy at
  200 DPI **38%** of the data is silently lost, and suspects catch a
  minority of it. It remains true, though, that **the paper is simulated,
  not real**: the bench degrades images in a controlled, repeatable way; it
  does not replace a corpus of scans made for real

See also the warning when OCR is truncated by timeout: the text at the top
of the document says so.

---

## 6. How do you avoid redacting case numbers, "Comitato Tecnico", dates and internal codes?

**With a second bench, not just the first.**

A filter that removes everything is as useless as one that removes nothing.
The tests use **two** texts:

| Text | Expected |
|------|----------|
| Italian email with many categories of personal data | what must go, goes |
| Formal record full of bodies, plans, case numbers, tender codes | **zero** spurious redactions |

Zero is not a figure of speech: the tests assert `report.total == 0` on the
record. It is a line you can go and read in half a minute, and it is why
this page can afford not to round up elsewhere.

Typical safeguards:

- validators (mod-97, Luhn) against long random numbers
- context for phone numbers, VAT numbers, amounts, dates of birth
- the rule that guessed surnames without corroboration was **withdrawn**
  (1.13.0): it was the main source of spurious redactions on forms
- IBAN: at least one letter already present in the first two positions
  during OCR recovery (a regression: an order number was becoming an IBAN
  that was "valid" under mod-97)

Relevant files: `tests/test_privacy*.py`, `tests/test_sospetti.py`, examples
in the README.

---

## 7. Is the "N redactions" report enough to trust it?

**No. Zero redactions does not mean "clean document".**

Two different silences:

- there was no recognisable personal data
- there was, but in a form the engine could not validate

**Suspects** exist to break that ambiguity. The before/after comparison is
the check that matters. An automatic filter that is trusted blindly is a
risk — that is written in the UI and the README too.

Samples in suspects are masked (`RS••••••••••••2S`): enough to find them
again in the text, not enough to read them from the report alone.

---

## 8. What if I pass the same document twice, or in pieces?

**Placeholders are not numbered.** Two different people become the same
`{{NAME}}`:

```
Scrivi a Mario Rossi <m.rossi@a.it> e a Luigi Bianchi <l.bianchi@b.it>
   →  Scrivi a {{NAME}} <{{EMAIL}}> e a {{NAME}} <{{EMAIL}}>
```

These are two real and opposite properties, and it is better to know them
before discovering them:

- **in the output you cannot reconnect who was who.** That is good for
  exposure, and it confirms question 1: this is not a pseudonymised dataset
  to join on, nor a mapping table to safeguard. There is no map to steal,
  because none is ever built;
- **a document split into pieces loses the context between one piece and
  the next.** Names are also recognised from context — a title in front, an
  email beside, a first name pulling the surname. If the title stays in the
  first block and the name ends up in the second, that signal is gone.

The second is what actually breaks when pasting a long document into a chat
in blocks. **Convert the whole document and paste the result**, rather than
converting the pieces.

Two passes over the same file, on the other hand, give the same result: the
engine is deterministic (question 2), and no state accumulates between one
conversion and the next.

---

## 9. Can I use it in a firm or company as an "official" privacy control?

**As the *sole compensating control*: no.
As a tool within a process: yes, if you frame it honestly.**

A sensible framing:

1. Conversion and redaction **locally**
2. Human review of the result (and of the suspects)
3. Only then, sending to a model or a consultant

**The control is step 2, not step 1.** The tool makes that review feasible
at volumes that would not be manageable by hand; it does not replace it, and
it does not move the responsibility of whoever signs off on the sending.
Anyone quoting step 1 and step 3 while skipping the one in the middle is
describing a different process.

It does not replace:

- impact assessments / internal policies
- enterprise DLP, automatic classification at scale
- contractual obligations to clients about minimisation

Licence **AGPL-3.0**: internal use and paid consultancy are entirely
compatible; if you *modify* the software and offer it *as a network service*
to others, the obligation to offer the source of your version kicks in
(section 13). Detail in [LICENSE](../LICENSE) and the README.

---

## 10. Where to look in the code and the tests (map for reviewers / AI)?

| What | Where |
|------|-------|
| Pipeline and recognisers | [`mr_rao/privacy.py`](../mr_rao/privacy.py) — `apply_privacy_filter`, validators, `find_suspects`, `cf_ocr_recover`, `iban_ocr_recover` |
| Name / common-word lists | [`mr_rao/it_names.py`](../mr_rao/it_names.py) |
| Options from form/CLI/profiles | `PrivacyOptions`, `options_from_form`, [`mr_rao/profiles.py`](../mr_rao/profiles.py) |
| Principles and limits | [PRIVACY.en.md](PRIVACY.en.md) |
| Dual tests and regressions | `tests/test_privacy.py`, `tests/test_privacy_riconoscitori.py`, `tests/test_sospetti.py` |
| Local server security (a separate piece) | [SECURITY.en.md](../SECURITY.en.md), `tests/test_security.py`, `tests/test_limiti_ocr.py` |
| Lessons from real bugs | [CHANGELOG.md](CHANGELOG.md) — every entry states the bug, not just the feature *(Italian)* |

Entry point for an automated analysis: read the module docstring of
`privacy.py`, then `apply_privacy_filter` (the order of the phases), then
the tests that were failing on the regressions cited in the changelog.

---

## 11. If you find a hole or an overclaim, what should you do?

1. **Reproduce** it with a minimal piece of text (no real client documents
   in public issues).
2. Say what you expected and what happened.
3. Prefer a GitHub issue; for something you consider sensitive (e.g. a
   systematic bypass on a class of documents), contact the author privately
   as described in [SECURITY.en.md](../SECURITY.en.md).

The most useful contributions are the ones that raise quality without
inflating false positives on the administrative record: a recogniser that
"catches everything" makes the tool worse.

---

## In one sentence

> Mr. Rao does not guarantee the absence of personal data in the output
> text. It applies rules and checksums to Italian formats, flags doubtful
> cases, and asks for human review. It is inspectable and repeatable; it is
> not a certificate of anonymisation.

If that sentence and the code are not enough for you, do not use it as your
only control — and you would be right not to.
