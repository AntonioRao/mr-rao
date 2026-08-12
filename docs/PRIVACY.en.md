# Privacy — Mr. Rao

*Questo documento in italiano: [PRIVACY.md](PRIVACY.md).*

## Principles

1. **Everything local** — nothing is sent to an external service
2. **System fonts** — no request to Google Fonts
3. **History** in memory only, never on disk
4. **Temporary files** deleted once the conversion is done

## How recognition works

Every recogniser is **a regular expression plus a validator**: the pattern
nominates a candidate, the validator decides whether it really is personal
data. That is what keeps false positives low without giving up coverage — an
IBAN is accepted only if mod-97 checks out, a card only if it passes Luhn, a
ten-digit number is a phone number only if it has a dialling prefix, a
separator, or a context word in front of it.

**No model takes part in the decision.** The engine is deterministic: the
same text always gives the same result, there is no score to tune and no
threshold, and every substitution can be explained by pointing at the rule
that produced it.

There *are* neural networks in the package, though, and they should be
stated rather than implied. Two, both **upstream** of the engine:

| Model | Size | What it is for | When it runs |
|-------|------|----------------|--------------|
| RapidOCR (PP-OCRv6, `.onnx`) | ~30 MB | Turning the pixels of a scan into characters | On images and PDFs with no text layer |
| magika, loaded by MarkItDown | ~3 MB | Guessing a file's type from its content | On every conversion |

They run locally, offline, on the CPU: neither leaves the machine, and
neither says whether something is personal data. The OCR hands over text and
stops there; from that point on regular expressions and arithmetic decide —
it is the house principle, *the pattern nominates, the validator decides*,
and the OCR sits upstream even of the pattern.

This splits the responsibility in two, and it is worth knowing in both
directions. On text, the engine's behaviour is entirely inspectable. On
scans, **what the OCR reads badly the engine cannot decide well**: a mangled
IBAN never reaches mod-97, and no rule recovers data the reader did not
read. That is the limit measured further down this page, not a hypothesis.

## What gets replaced

**Placeholders are numbered, and they are numbered by default.** Since 1.20.0
every distinct value gets a number — `{{NAME_1}}`, `{{NAME_2}}` — and the same
value repeated always gets the same one. Without numbers the redacted document
loses its sense: *"{{NAME}} cited {{NAME}} before {{NAME}}"* cannot be read,
and a language model cannot reason over it.

In the table below the placeholders are written in their **base form**,
without a number, because that is what identifies the type. In the real
document they arrive with the suffix, unless "Number the placeholders" is
unticked — then the output goes back to being identical to 1.19.

The number is not a key: it holds **inside one document and nowhere else**.
No number-to-value map exists, because none is ever built, and the same name
in another document gets a different number. A number stable across documents
would be a persistent identifier — that is, a new piece of personal data
invented by us.

| Type | Placeholder | How it is decided |
|------|-------------|-------------------|
| Email | `{{EMAIL}}` | Address shape, including obfuscated forms (`[at]`, `chiocciola`, `punto`) and the **spaced at sign** (`mario @ esempio.it`). For that last one the final part of the domain must be letters: without that constraint, `10 @ 4.50` on an invoice would become an address |
| Web addresses | `{{URL}}` | An explicit scheme — `http`, `https`, `ftp`, `ftps` — or `www.`. A bare `name.it` in running text is not enough |
| Phone numbers | `{{PHONE}}` | **Any** international prefix (`+39`, `+44`, `0033`: one to three digits after `+` or `00`), Italian `3xx` mobiles, a context word (`cell`, `tel`, `fax`), or a landline with separators. The **slash** form (`011/7323929`) counts only with a contact word or an international prefix in front |
| Italian tax code | `{{CODICE_FISCALE}}` | 16-character structure. The **check character** does not reject, it flags |
| | | Also recognises **omocodia** — digits replaced by letters when two people collide — but there the check character **must** compute |
| | | Also recovers the OCR-mangled form, if the corrected candidate's check computes |
| Italian VAT number | `{{PARTITA_IVA}}` | `IT` prefix or fiscal context nearby. The **check digit** does not reject, it flags |
| IBAN | `{{IBAN}}` | **Mod-97** (ISO 13616), including written in groups of four as banks print it |
| Non-IBAN bank details | `{{BBAN}}` | CIN+ABI+CAB+account, with banking context nearby |
| Payment cards | `{{CARD}}` | **Luhn** (ISO/IEC 7812) |
| Postal addresses | `{{ADDRESS}}` | Via, viale, piazza, corso, largo, contrada and others, including abbreviated (`V.le`, `P.zza`, `P.le`, `L.go`, `C.so`); street name in full or as an initial (`Via A. Volta`); with number, postcode and town |
| Personal names | `{{NAME}}` | See below |
| Keys and passwords | `{{SECRET}}` | Tokens, API keys, JWTs, private-key blocks, `password: ...` |
| | | Also the **short codes**: PIN, PUK, CVV, CVC, security code, OTP, unlock code. Three to eight digits — above eight it is not a PIN any more, it is a case number — and the label is required, which is what makes them safe: those words have no other meaning in a document |
| | | And the **recovery phrase** (`seed phrase`, `mnemonic phrase`): 12 to 24 words, the BIP-39 standard. It sits apart because it is the only secret made of space-separated words, and with the generic value — which stops at the first space — **one word out of twelve** got substituted, with the report saying "1 secret" and the phrase still usable |
| Land registry references | `{{CATASTO}}` | **«Deeds and case files» pack, off by default.** Sheet **and** parcel together, sub-unit optional. The sheet alone is a page number |
| Case and file numbers | `{{PRATICA}}` | **«Deeds and case files» pack, off by default.** Court docket (R.G.), protocol, deed register (repertorio), collection, chronological number. The label is required and **stays in the text**: the number goes, «Prot. n.» remains. Two digits at least, or a year beside it — «Protocollo n. 5» of a convention is not a case number. The register suffix (`/P`, `/CU`) stays too: it says which register, not which file |
| Vehicle plates | `{{TARGA}}` | **«Deeds and case files» pack, off by default.** `AB 123 CD`, with or without separators. The constraint is not upper case but **consistency**: all upper or all lower, never mixed — `Ab 123 cD` is not a plate, it is a typo or something else. I, O, Q and U do not exist on Italian plates and are rejected. The moped form (`AB 12345`) needs «targa» or «targato» in front |
| Identity documents | `{{DOC_ID}}` | Electronic ID card, driving licence, passport. **The document type must be written nearby**, see below |
| Dates of birth | `{{DATE}}` | **Off by default.** Only with birth context beside it |
| Amounts | `{{AMOUNT}}` | **Off by default.** Currency, thousands separator, or accounting context |
| Your own terms | `{{TERM}}` | The "always hide" list written by whoever is converting |

### Two things Mr. Rao finds and never removes: age and sex

They have no placeholder, and that is not an oversight.

They are **quasi-identifiers**: «45 years old» identifies nobody on its own,
but together with a small town and an occupation it does — and that is exactly
how an archive gets de-anonymised. Removing them, though, protects nobody
further and makes the document useless for the one purpose it was prepared
for: whoever works on a medical record, on workforce statistics or on an
expert report is asking for **precisely those two facts**.

Leaving them in silence would mean the person re-reading does not know they
are there. So the third way, which here is the only right one: **they appear
in the report**, in the `detected_not_replaced` block, kept apart from the
substitutions because adding what was removed to what was left would give a
total that means nothing. «3 ages left in the clear, on purpose» is something
a DPO can act on; silence is not.

They are recognised only where **the context is a declaration**: `di anni 45`,
`45 anni di età`, `45 anni d'ETÀ`, `età: 45`, `Eta': 45`, `d' anni 78`,
`45enne`, `sesso: F`, `sesso: f`, `genere femminile`. A bare
`45 anni` is not looked at, and that is declared: it is nearly always a
duration («after 45 years of service»), and taking it would fill every company
report with flags.

The «Age and sex» switch decides **whether to look**, and has no second state:
on it reports them, off it does not search. Turning it off does not make the
document cleaner, it makes it quieter. Anyone who really wants them gone
already has the **«always hide»** list, which removes them — no capability is
lost, and that is what makes the choice not to offer substitution an honest
one.

### «Report instead of replace»: the third state, and it is not only about those two

Age and sex are the case where that behaviour is **compulsory**. But since
1.20.0 it can be asked for **twenty-six categories** — practically every one
the engine recognises — and the choice is per category, not per family.

The three combinations, and they are three different things:

| switch | category in «report» | what happens |
|---|---|---|
| on | no | **substitutes** — the placeholder arrives |
| on | yes | **finds it and leaves it where it was**, and says so in the report |
| off | — | **does not look**, and leaves no trace |

The middle row is the one that did not exist before, and it serves whoever
needs to read the data: the amounts a model has to compare, an age in a
medical record. The real value is not in the text, it is in the report —
*"I left 3 amounts in the clear, on purpose"* is something a DPO can act on;
silence is not. A recogniser that is **off** leaves no trace, and whoever
re-reads has no way of knowing whether there was nothing in there or whether
we looked the other way.

The one category left out is **"your own terms"**, and that is a decision:
that list is what the user explicitly asked to protect, and reporting it
instead of substituting it would mean disobeying an explicit request.

In the interface the count is **threefold**, and the three numbers answer
three different questions:

```
🛡️ 12 redactions · ⚠️ 2 to review · 👁 3 in the clear
```

The last one is this section: what the engine found and left where it was, by
the converting user's choice. Hovering over it lists the categories, with the
names people read and not the ones the code uses to talk to itself. Adding it
to the other two would give a total that means nothing, which is why they are
three numbers and not one.

In the document the same information travels with the frontmatter, in the
`detected_not_replaced:` block — separate from `redactions:`. It is the only
part of the report that stays attached to the file: whoever receives it in six
months does not have the HTTP request.

### The Anglo pack

Added in 1.8.0 and left out of this table until 1.11 — a gap that cannot
recur today, because `scripts/check_docs.py` compares the placeholders the
engine can emit with the ones written in **`PRIVACY.md`, the Italian page**,
and fails if it finds a single extra one. That is worth saying plainly rather
than leaving you to assume otherwise: the guard reads one file, and this page
is not it. A placeholder missing *here* and present there passes the gate, so
this table is kept in step by hand.

| Type | Placeholder | How it is decided |
|------|-------------|-------------------|
| NHS number (UK) | `{{NHS_NUMBER}}` | **Mod-11** *and* the word "NHS" beside it |
| ABA routing number (US) | `{{ROUTING_NUMBER}}` | **3-7-1** weighted checksum, the prefix ranges actually in use, *and* a context word |
| SIN (CA) | `{{SIN}}` | **Luhn** *and* a context word |
| ABN (AU) | `{{ABN}}` | **Mod-89** (with 1 subtracted from the first digit) *and* the abbreviation beside it |
| TFN (AU) | `{{TFN}}` | Weighted **mod-11** *and* the abbreviation beside it |
| Passport machine-readable zone | `{{MRZ}}` | **ICAO 9303** check digit on the document number, the date of birth or the expiry date. **The only one that decides on its own** |
| National Insurance number (UK) | `{{NINO}}` | **No checksum**: structure, plus the prefixes HMRC does not issue |
| SSN (US) | `{{SSN}}` | **No checksum**: the hyphenated 3-2-4 form, plus the exclusions published by the SSA. Nine digits run together are left alone |
| ITIN (US) | `{{ITIN}}` | **No checksum**: structure and IRS ranges |
| UK postcode | `{{POSTCODE}}` | **No checksum**, like every postcode: structure *and* a delivery word beside it, when it is not already inside a complete address |
| Anglo street addresses | `{{ADDRESS}}` | The **house number** in front, at least one word in between, and a street type at the end (`Street`, `Road`, `Lane`, `Way`, …), with an optional UK postcode or US ZIP |
| Anglo personal names | `{{NAME}}` | **No list at all**: only where the text declares this is a person — a title in front, an opening or closing formula, an email address beside it |

**The split worth reading is not the one between those with an arithmetic
check and those without.** A checksum on its own is almost never enough: the
NHS mod-11 lets through roughly one ten-digit sequence in nine, and alone it
would redact invoice numbers. **Five of these six arithmetic recognisers
substitute nothing without a context word nearby** — NHS, ABA routing, SIN,
ABN and TFN. The validator cuts the noise, the context zeroes it.

The only one that decides on its own is the **MRZ line**, and not because it
is luckier: because its shape is unrepeatable. Capitals, digits and filler
only, with at least one double `<` — no other line of text looks like that.
It earns its keep precisely there, because an MRZ carries surname, given
name, nationality, date of birth, sex and expiry all at once.

One point about the MRZ, because it is the kind of detail that looks like a
detail: **the composite check digit at the end of the line is not used**, on
purpose. It is computed over **non-contiguous** pieces, and feeding it the
whole line makes it fail every time. Three fields are checked — document
number, date of birth, expiry — and one of them computing is enough.

And where there is no arithmetic at all (NINO, SSN, ITIN) only the structure
is left, plus the published exclusions: there the risk of catching some
unrelated code is higher, and it is the same reason Italian identity
documents demand context.

**A word about an Italian number mistaken for an American one.**
`Tel. 078-05-1120` has exactly the 3-2-4 shape of an SSN, and the Anglo pack
is on by default: an Italian notary was seeing the office switchboard counted
as an "SSN". The data disappeared anyway — the phone step runs afterwards and
catches it — but **the report got the type wrong**, and a report that gets the
type wrong is no use answering someone who asks *what* was in the file. Now a
contact word in front makes the SSN recogniser leave that number alone.

### Why identity documents demand context

It is the only recogniser that cannot lean on an arithmetic check, and that
is worth saying openly. A driving licence number **has no check digit**: no
arithmetic can tell `MI5512340V` apart from a case reference of the same
shape. There were three ways to go, and two of them were bad:

- replacing on sight would gut half an administrative file — a formal record
  is made of case numbers, resolutions and tender codes with exactly that
  shape;
- staying silent would let through one of the most sensitive data types that
  crosses a law office;
- **requiring the text to say which document it is**, and flagging rather
  than acting when it does not.

The context window is deliberately wide. On a card or a scan the document
type is not next to the number: **it is the heading**, several lines above.
With a narrow window the recogniser could not see the one thing that
authorises it to act, and stayed put precisely on the documents it was
written for.

It has its own switch, `documenti`, and does not sit inside `fiscal`: a
document number is not tax data, and someone turning off tax codes does not
mean to uncover passports.

Across more than a hundred zero-truth documents the measured cost is
**zero**: no wrong substitution, no extra suspect.

## Personal names: nine signals, all of them corroborated

A list of names is never complete, and relying on it alone lets through
every uncommon surname. So context rules count too. `_scrub_names` runs them
in this order, from the strongest signal to the weakest:

1. **A professional title in front** — Dott., Ing., Geom., Avv., Sig.
2. **Role, colon, surname in capitals** — `Il Ministro: GIORGETTI`. This is
   how Italian public acts are signed.
3. **A name before an email address** — `Tizio Caio <t.caio@x.it>`. The most
   frequent case in email.
4. **A name after an email address** — `t.caio@x.it (Tizio Caio)`.
5. **A name next to a valid Italian tax code** — `Elicio Nazar CF
   MNTCRL58D07H163B`. The window is deliberately narrow: between the name and
   the code there is room for the label and nothing else, on the same line.
6. **A declared role** — `il cliente Mario Rossi`. It demands **two** words.
7. **A form field** — `Nome: Mario Rossi`, `COGNOME= …`. Here one word is
   enough: the label leaves no doubt about what follows.
8. **A closing formula** — `Cordiali saluti, Esposito`. It is the one place
   where a surname on its own counts as evidence.
9. **A first name and surname side by side**, both recognised in the lists.
   How many hits are required — one or two — is decided by the prose/form
   threshold, below.

The order is not decorative: the first eight are **context** rules, and they
do not need the name to be in any list. The ninth is the only one leaning on
the lists, which is why it comes last.

There is then a tenth case that **never substitutes**: a single word that
appears in the lists, with nothing around it, becomes a **suspect**. Below
four letters it is not even looked at — "Re" and "Rao" are real Italian
surnames, and on a blank Italian tax return they were being substituted.

All of them require **corroboration**, from a list or from context. There used
to be one that did not, and it was removed.

### Prose or form: how many hits the ninth signal demands

On the weakest signal the same rule points **the opposite way** depending on
the document, and that is not an opinion. In a letter, two capitalised words
of which one is in the lists are almost always a person; on a form they are
almost always a field label — "Imposta Lorda", "Quadro RN".

Measured: demanding two hits removes **2,739** wrong substitutions on blank
administrative forms and costs **609** names across 1,500 real emails. There
is no value that is right for both, so none is picked: the document is looked
at instead.

**The signal that decides lives in the PDF, not in the text.** The boxes on a
form are vector lines and rectangles: they survive reading the file and die in
the conversion, so that is where they are counted. The threshold is **0.5
vector elements per 100 characters**, and it sits in the gap between two
measured populations rather than next to either: the Italian Revenue Agency's
instruction booklets — prose — sit at 0.2, that same agency's forms at 0.7,
and US tax forms between 3.7 and 9.8.

For other formats there is nothing to count: `.eml`, `.txt`, `.md`, `.rtf`,
`.docx`, `.doc`, `.odt`, `.pptx` and `.ppt` are **prose**; `.xlsx`, `.xls`,
`.csv`, `.json` and `.xml` are **forms**.

On a scan the answer is **"unknown"**, and that is a genuine third state:
counting vectors on an image would give zero, and zero would be read as
"prose" — the right answer for the wrong reason. In that case caution is
applied to the document, meaning a suspect, and not to recall: a false
positive shows up on re-reading the output, a name left in the clear does not.

The interface lets you override it by hand. The command line does not: there,
what the program infers always wins.

### The signature on public acts

The second rule deserves a note, because it is the only one where the lists
count for nothing — deliberately. Across the twelve issues of the Italian
official gazette in the public corpus that shape appears **107 times**, and
of the 114 surnames found only **28** are in our lists: demanding
corroboration would have let the other 86 through. What decides is the role
in front of the colon.

On that same shape a 64 MiB NER model caught 3 cases out of 42. It is not a
question of how much a model knows: the signal is in the punctuation.

The permission is paid for with three constraints, each born from a measured
false positive: there can be no **comma** between the role and the colon
(*"Responsabile della protezione dei dati, all'indirizzo: INPS"* — that
colon does not belong to the role); the surname does not cross a **line
break**; and it must be **all capitals and not a common word**, otherwise on
a form it would swallow the field labels (*"Responsabile: SETTORE
TECNICO"*).

### When the common word is also a surname

Forty-two surnames in the lists are also ordinary Italian words — Conti,
Villa, Carta, Porta, Valle, Forte, Gentile, Grande — or city names that in
Italy are extremely common surnames: Napoli, Ferrara, Messina, Catania,
Salerno, Udine, Brescia. Until 1.15.0 the common word always won, and *"il
dott. Marco Conti"* came out as *"il dott. NAME Conti"*: the first name
removed and the surname left behind, which is a document that looks
processed and is not.

Since 1.16.0 the last word stays if it is a known surname **and** has in
front of it a word that really is in the lists. The pair is required: shape
alone is not enough, otherwise every "Valle" at the end of a sentence would
become a person.

Two words deserve a note of their own. **Giulia** and **Emilia** were among
the common words for one reason only: they are parts of *Friuli Venezia
Giulia* and *Emilia Romagna*. They are also two of the most widespread given
names in Italy. Removing them from the list would have made half of
administrative Italy disappear from documents, so nothing was removed:
**the neighbouring word decides**. If "Venezia" comes before, or "Romagna"
after, it is a region; otherwise it is a person.

### The rule that was withdrawn, and what removing it costs

Until 1.12.0 there was a **surname heuristic**: two capitalised words in a
row that do not look like Italian words are a first name and a surname,
**with no corroboration from the lists at all**. It was off by default from
1.7.2 and was **withdrawn entirely in 1.13.0**.

The bill on documents that contain not one item of personal data: 8,904
wrong substitutions across twenty blank Italian Revenue Agency forms, 14,376
across eight issues of the official gazette, 2,888 across ninety-nine US tax
forms. It ate "Redditi Persone Fisiche", "Quadro RN", "Imposta Lorda". In
2026 the phenomenon was **reproduced on twenty-seven administrative forms
downloaded straight from the agencies** — documents we did not choose —
where it went from 27 wrong substitutions to 2,529.

The defect was not that it guessed: it is that it **decided on its own**.

**The price, stated in full.** A first name and surname that are in neither
list, with no title in front, no signature and no email address beside them,
now **stays in the document** — and does not even become a suspect, because
a suspect requires at least one corroborating signal. A foreign name alone
in the middle of a text is the typical case. It is a real loss, and it is
the price we chose: the alternative was being wrong ninety-four times as
often on documents that contain nobody.

The limit is under test in `tests/test_privacy_riconoscitori.py`, so that if
one day a new rule covers it, this page gets updated together with the test
instead of being forgotten.

## How it is verified

The bench is **two** texts, not one:

- an **Italian email** with names, addresses, contact details, URLs, IBAN,
  VAT number, tax code and an amount: all of it must go;
- an **administrative record** full of "Comitato Tecnico", "Piano
  Industriale", "Fase Uno", case numbers, dates and tender codes: **none of
  it must go**.

The second matters as much as the first. A filter that redacts everything is
exactly as useless as one that redacts nothing, and the record is what stops
us buying coverage by making the tool worse.

### On text, with no OCR involved — measured 2026-08-09

Almost every number on this page concerns scans, where the main limit is the
OCR. On email, contracts, resolutions and Office documents the engine is
**entirely responsible**, and there is nobody else to blame. That path had
never been measured: `scripts/bench_testo.py`.

**False positives: zero.** Across 3.6 million characters of real, blank
administrative forms — 27 Italian ones downloaded from the Revenue Agency,
INPS, Customs, the Ministry of Justice and the Chambers of Commerce, plus 15
IRS forms — **no wrong substitution**, 42 documents out of 42 clean.
Documents we did not choose: that is the difference that counts.

**Recall on regular forms: 100%.** Data of known value inserted into real
paragraphs of the official gazette, verified clean before insertion: 520
cases out of 520, no silent losses. Eight data types in three frames each,
and names at **four** levels of evidence — title in front, signature, next to
an email, first name plus surname — plus the **bare** case, which has no
evidence at all and is there on purpose: it is what measures the limit
declared further down, not a fifth level.

**Recall on difficult forms: 73% redacted, 20% flagged, 6.7% silently
lost.** It is the honest number, because that is how data actually arrives
from a `.docx` or a PDF:

| Form | Outcome |
|------|---------|
| IBAN and card in groups of four or with hyphens, tax code in lower case, phone with dots or with no word in front, obfuscated `[at]` email, address without a street number, **email split by a line break** | redacted |
| IBAN split by a line break · `Il Direttore Generale: MORETTI` · a surname that is also a common word (`Marco Chiesa`) | **flagged**, not removed |
| First name and surname outside both lists, with no title, signature or email beside them | **silently lost** |

The only silent loss left is the limit declared above, the one the
withdrawal of the heuristic made explicit. The other two categories are not
equivalent and the table keeps them apart on purpose: **flagged** leaves the
reader a chance to act, **silently lost** does not.

**What this measurement found.** An email address broken across lines by the
extractor — `g.moretti@` at the end of one line and the domain on the next —
disappeared silently in 20 cases out of 20. Fixed in 1.14.0, with the
narrowest possible permission: one line break, only after the at sign.

### The variety of values — measured 2026-08-09

The two measurements above change the **sentence** the data appears in.
Changing the **value** is a different question, and it found two defects
that none of the others could see. Three hundred distinct valid values per
type: `scripts/bench_varieta.py`.

Holding at 100%: IBANs with any CIN and ABI; Visa, Mastercard, Discover and
**15-digit American Express** cards; landlines with 2-, 3- and 4-digit area
codes; addresses with ten different words for "street"; fifty mail domains.

Two did not hold, and were fixed in 1.15.0:

- the **tax code under *omocodia*** — the form in which the Revenue Agency
  replaces some digits with the letters `L M N P Q R S T U V` because two
  people would otherwise get the same code: **zero recognised out of 300**,
  40% silently lost. It is now removed, but **only if the check character
  computes**: admitting letters where the code wants digits makes the shape
  almost any sixteen-character word, and there the arithmetic is not an
  extra, it is what holds the whole thing up;
- the **phone number with a slash**, `Tel. 011/7323929`, the standard form on
  Italian letterheads: **zero out of 300**, while the same numbers with a
  space or a hyphen were caught. It is now removed **if there is a contact
  word in front** — a phone number has no arithmetic that can contradict its
  shape, so the permission is paid for by demanding context.

Deliberately still at zero: the **bare VAT number**. Eleven digits with no
`IT` prefix and no fiscal context nearby are indistinguishable from any
other number.

The same question turned on the **ten Anglo recognisers** — NHS, National
Insurance, SSN, ITIN, ABA routing, SIN, ABN, TFN, all six UK postcode formats,
MRZ — plus Italian identity documents and non-IBAN bank details, found
nothing: `scripts/bench_varieta_en.py`, twenty types in all, every one at
100%.

On the **rest of the Italian pack** (`scripts/bench_varieta_it.py`,
twenty-six forms, two hundred values each) three defects did come out, fixed
in 1.16.0: the two about names described above, and **addresses with an
initial** — *"Via A. Volta 5"*, *"piazza G. Verdi 1"* — which the recogniser
could not even begin to parse. That last one, measured on the public corpus
where the engine had been substituting **nothing**, pulls **41 real
addresses** out of twelve issues of the official gazette, with zero false
positives: `via PEC, 30` and `via FTP, 12` stay untouched.

Already holding: surnames with a particle (De, Di, Lo, Della), with an
apostrophe (D'Angelo, Dell'Orto), accented, compound first names; **female**
tax codes (day of birth +40) and those of people **born abroad** (town code
`Z…`); street numbers with a letter, addresses with no postcode; 800
freephone and 199 service numbers, foreign dialling codes; URLs, JWTs, AWS
keys, amounts, dates of birth.

### Parity across formats

The same document in ten formats — `.txt`, `.html`, `.csv`, `.json`, `.xml`,
`.docx`, `.xlsx`, `.pptx`, `.eml` and a `.png` that goes through OCR — has to
protect identically, because the extractor changes from one format to the
next. **Eight data items out of eight in all ten**, none left readable.
Bench: `scripts/bench_formati.py`.

### So that recall cannot fall silently

Every measurement above counts **errors** on documents that contain nothing.
It is the right half to look at first — an over-redacting engine is
unusable — but it is one half, and the other is invisible by construction:
if a change made the engine stop seeing "piazza G. Verdi, 1", every
zero-truth bench would stay green. **Zero errors on an empty document is
also what a switched-off engine produces.**

`scripts/bench_corpus_pubblico.py` looks at the other half, and does it on
documents **we did not write**: issues of the official gazette and forms
downloaded from the agencies that publish them. It fails in two directions —
if a substitution appears on the blank forms (where the expectation is
zero), and if the number of substitutions on real prose **falls**. The
numbers are frozen together with a fingerprint of the file list, so pointing
it at a different corpus is reported instead of looking like a regression.

The corpus is not in the repository: it is tens of megabytes and it is not
ours to redistribute. The test skips and says so, but the **four** tests that
exercise the **mechanism** always run — a check that only runs on the
developer's machine is not a check.

## Suspects

The recognisers look for **valid** shapes. OCR produces **almost** valid
ones: `A01` read as `AD1`, `IT60` read as `lT60`. The structure does not
compute, the data stays in the text — and stays readable by a person.

Substituting without certainty would mean redacting half the document. But
staying silent is worse: "3 redactions" on a clean document and "3
redactions" on a document the recogniser could not read are the same number
and two opposite situations.

So, after substitution, a pass over the remaining text flags what resembles
personal data without being enough to remove. They appear in the report as
`suspects`, and in the interface next to the count: **"🛡️ 3 redactions · ⚠️
2 to review"**. If something was left in the clear on purpose, the third
count — `👁 N in the clear`, explained above — appears beside them.

Samples are masked (`RS••••••••••••2S`): enough to find them again in the
document, not enough to read them.

A clean administrative document — case numbers, resolutions, tender codes,
dates — produces **zero** suspects. If every number became a warning, the
warning would stop being worth anything.

## Recovering mangled codes

Suspects say where to look. For codes that carry a check digit we can do
better: **try to correct them**.

The engine takes the candidate, applies the typical optical-recognition
confusions — `O`↔`0`, `I`↔`1`, `S`↔`5`, `B`↔`8`, and above all a lower-case
L read in place of a capital I — for **at most two characters**, and
substitutes only if the corrected candidate's checksum computes.

A heuristic does not decide: the arithmetic decides.

```
RSSMRA85T1OA562S    →  {{CODICE_FISCALE}}   1 correction, check OK
lT60X05428…123456   →  {{IBAN}}             1 correction, mod-97 OK
lT60X05428…123457   →  unchanged            no correction saves it
```

**The checksum alone is not enough**, and that is a lesson paid for: the
first version turned the order number `5551234567890123` into
`SS51234567890123`, and that candidate really does pass mod-97. If you can
convert any sequence of digits into an IBAN, sooner or later you will hit
one. The candidate space has to be narrowed too: at least one of the two
leading characters must already be a letter.

## Report

The API response carries **three separate counts**, and keeping them separate
is the point:

| field | what it says |
|---|---|
| `counts`, `total` | what was **removed** |
| `detected`, `detected_counts`, `detected_total` | what was found and **left on purpose** — age, sex, and the categories put in "report" |
| `suspects`, `suspects_total` | what the engine **could not decide** |

Adding them together would give a total that means nothing. The interface
shows all three beside the result, and the **"Privacy comparison"** panel
shows the text before and after. That panel is the check that matters: it is
where you see what was removed and, above all, what got through — because a
silent loss, by definition, appears in none of the three numbers.

## Declared limits

- **No list of surnames is complete**, and since 1.13.0 there is no longer a
  heuristic guessing the missing ones: a first name and surname outside the
  lists, with no title, signature or email address beside them, **stays in
  the document and does not even produce a suspect**. See "The rule that was
  withdrawn" above.
- **On scans the protection is weaker, and now there is a number for it.**
  `scripts/bench_scansioni.py` prints 8 documents containing invented
  personal data — it computes the check digits itself, with an
  implementation independent of the engine's and verified against the
  published ISO 13616 and Luhn vectors — puts them through a simulated
  scanner, then through the real OCR and the real redaction engine. Out of
  64 expected data items per level:

  | scan | redacted | flagged | **silently lost** | not read by the OCR |
  |---|---|---|---|---|
  | text, no OCR | 100% | 0% | 0% | 0% |
  | scanner in good order, 300 / 200 / 150 / 100 DPI | 94–100% | 0% | 0–6% | 0–3% |
  | faded photocopy, 300 DPI | 94% | 2% | 3% | 2% |
  | faded photocopy, 200 DPI | 47% | 6% | **38%** | 9% |
  | faded photocopy, 150 DPI | 6% | 2% | **25%** | 67% |

  **It is not the resolution.** Between 300 and 100 DPI, on a clean scan,
  coverage does not get worse: the differences are noise. What matters is
  the quality of the mark — a faded photocopy at 200 DPI loses more than
  half the data, and that document is perfectly legible to the eye.

  **And the loss is almost always silent.** This line used to say that "what
  remains gets flagged": the measurement says otherwise. Of the data left
  readable in the Markdown, suspects catch a minority — 0 out of 4 on clean
  scans, 4 out of 28 on the 200 DPI photocopy. The **"Privacy comparison"**
  panel remains the only check that sees everything.

  **One cause of those losses has been removed.** Where degradation is
  severe the OCR **glues the data to the label in front of it** —
  `IBANIT60X05…`, `Tel.02 1234567`, a card number stuck to a form's guide
  dots — and the recognisers, which demanded a break before the candidate,
  never got as far as nominating it. The data passed its own arithmetic
  check and stayed in the clear anyway: it was the same digits as before,
  only attached to the word in front.

  A word glued in front is now allowed, and for phone numbers — which have
  no arithmetic able to contradict the shape — **only** the contact word
  before the dot is allowed. The rest is unchanged: a **digit** in front
  still stops everything, because that would mean cutting a piece out of a
  longer number. Mod-97, Luhn and the check character still decide: the
  pattern nominates, the validator decides.

  **The bill:** silently lost data goes from 60 to 46 out of 640 (−23%), and
  scans from a scanner in good order no longer lose any. The cost measured
  before believing it: across 203 real scanned documents the loosened
  patterns nominate **not one candidate**; across 434,000 characters of real
  text they nominate 4 and none passes the validator; and on an
  administrative document built specifically to set them off they nominate
  12 — wrong substitutions: zero.

  **False positives do not get worse:** on the zero-truth control documents
  wrong substitutions stay **zero at every level of degradation**, even when
  the OCR returns garbage.

  A warning about the bench itself: **the paper is simulated, not real.** It
  measures the OCR and the redaction engine on images degraded in a
  controlled, repeatable way; it does not replace a corpus of scans made for
  real.
- **A truncated OCR produces a partial redaction.** If a scan exceeds the
  time cap (`MR_RAO_OCR_TIMEOUT`, 15 minutes by default), extraction stops
  and the engine has only seen the pages that were read. The document says
  so at the top, before the text: the reader has to know *before* trusting
  it.
- **Names remain the hard part.** The bench is no longer synthetic: since
  1.8.0 it is over a hundred public administrative documents taken from the
  web, scans included, where the expected answer is **zero** — so every
  substitution is an error by construction — plus 7,500 mailing-list
  messages. False positives on names fell from 6,339 to 1,637: **measured,
  not estimated**. But 1,637 is not zero, and a rare surname in an ambiguous
  context can still stay, or disappear when it should not. The heuristic
  that guessed without corroboration, which was the main source of errors,
  was **withdrawn in 1.13.0**.
- **PDF→PDF redaction does not treat every page, and it declares that page by
  page.** A PDF in and a PDF out is a separate path
  (`mr_rao/redazione_pdf.py`), with limits of its own:
  - **scans are refused**, and the refusal is per page, not per document. With
    no extractable text there are no glyphs to remove: drawing black
    rectangles over them would look like redaction and would not be it. A
    scanned page tucked in among digital ones — the hand-signed attachment —
    is the typical case, and it used to be counted among the pages treated. A
    **blank** page, on the other hand, is not an alarm: it has nothing to
    remove, and it stays silent;
  - **pages that fall back are not redacted.** When the extracted text cannot
    be found in the content stream, or a span cannot be traced to any glyph,
    the page comes out **as it was**. Those pages appear in
    `pagine_in_ripiego` with the reason beside them, and the panel shows them
    **always**, even when there are none, in the suspects' colour — which
    here means "your turn to look". Calling them redacted would be the worst
    possible way to be wrong;
  - the `'` and `"` text operators are declared out of scope.

  **The PDF follows the same options as the Markdown, profile included** — and
  since 1.24.0 the profile too. It did not before: the PDF routes built their
  options without looking at the chosen profile, so the same page, with the
  same boxes ticked, could produce a Markdown redacted one way and a PDF
  redacted another. The difference showed up only by opening the two files
  side by side, which is where nobody looks. The rule now lives in one place
  (`_privacy_dalla_richiesta`), and it has a name of its own precisely so that
  a new route cannot repeat the defect.

  **Annotations and form fields, on the other hand, are in, since 1.24.0.**
  They were not before, and the defect was a serious one: that text does not
  live in the page's content stream, so it came out intact from a file named
  `-redatto.pdf` — an Italian tax code still legible inside a document whose
  name says otherwise. Along with the value, the field's stored appearance
  (`/AP`) is discarded and `NeedAppearances` is turned on: without that, the
  old name would still be drawn on screen, with the data removed only
  underneath.
- **The formats covered are Italian and Anglo.** Italian tax code, VAT
  number, IBAN and BBAN; NHS number, National Insurance number, SSN, ITIN,
  ABA routing number, Canadian SIN, Australian ABN and TFN, UK postcode,
  passport MRZ lines. A German phone number or a Spanish NIF has **no**
  dedicated recogniser: on those documents the filter sees less than it
  looks like it does.
- **It does not replace a DPIA or legal advice.**

## Reviewer questions

Eleven questions typical of someone who clones the repository and inspects
the engine (with an AI's help, too), with answers aligned to the code:

**→ [PRIVACY_FAQ.en.md](PRIVACY_FAQ.en.md)**
