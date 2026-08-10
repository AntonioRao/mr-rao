# NOTICE — condizioni aggiuntive, nome e marchio

*This document in English below.*

Mr. Rao è distribuito sotto **GNU AGPL-3.0** ([LICENSE](LICENSE)). Questo file
non toglie niente a quella licenza: aggiunge le poche condizioni che
l'**articolo 7** dell'AGPL-3.0 consente espressamente, e dice cosa **non** è
coperto dalla licenza.

Titolare del copyright: **Antonio Andrea Rao**.

---

## 1. Il nome non è coperto dalla licenza

«**Mr. Rao**» e «**Mr. Rao Plus**» sono nomi commerciali del progetto e del
suo autore. L'AGPL concede diritti sul **codice**, non sui nomi: ai sensi
dell'**articolo 7 lettera e)** dell'AGPL-3.0, **non viene concesso alcun
diritto** d'uso di questi nomi, dei loghi o degli altri segni distintivi del
progetto.

Il codice si può copiare, modificare e ridistribuire — è software libero e
questo resta vero senza eccezioni. **Quello che non si può fare è chiamarlo
come questo.**

## 2. Una versione modificata deve dichiararsi diversa

Ai sensi dell'**articolo 7 lettera c)**, chi distribuisce una versione
modificata deve marcarla in modo ragionevole come **diversa dall'originale**:
nome del prodotto diverso, e nessun nome che possa essere confuso con «Mr.
Rao».

## 3. L'attribuzione va conservata

Ai sensi dell'**articolo 7 lettera b)**, nella documentazione e nelle
schermate informative di una versione modificata deve restare l'indicazione
dell'origine:

> Basato su **Mr. Rao** di Antonio Andrea Rao —
> <https://github.com/AntonioRao/mr-rao>

## 4. Perché queste condizioni sono in questo verso, e non nell'altro

Vale la pena scriverlo, perché la domanda viene naturale: **non è possibile
obbligare un fork a mantenere il nome originale**, e non sarebbe nemmeno
desiderabile.

Non è possibile perché il diritto sui marchi permette di *vietare* l'uso di
un nome, non di *imporlo*, e perché l'articolo 7 dell'AGPL elenca in modo
chiuso le condizioni aggiuntive ammesse: una clausola che obbliga a tenere il
nome sarebbe una «ulteriore restrizione» fuori da quell'elenco, e chi riceve
il codice avrebbe il diritto di **rimuoverla**.

Non sarebbe desiderabile perché il giorno che qualcuno distribuisce una
versione fatta male, quella versione porterebbe **questo** nome, e non ci
sarebbe modo di dire «non è nostra». Il marchio serve esattamente a poterlo
dire.

## 5. Doppio regime di licenza

L'autore, in quanto titolare di **tutti** i diritti sul codice, può concedere
lo stesso software anche con termini diversi dall'AGPL — licenze commerciali
comprese. È la ragione della clausola in [CONTRIBUTING.md](CONTRIBUTING.md):
chi contribuisce concede quel diritto, altrimenti la strada si chiuderebbe per
l'intero progetto.

**Mr. Rao Plus** — l'estensione per browser — è un prodotto distinto, non
distribuito sotto AGPL, e non fa parte di questo repository.

## 6. Corpora di terzi usati per misurare, e non distribuiti

I numeri che questo progetto pubblica — falsi positivi, richiamo, copertura
per categoria — sono misurati su documenti e corpora che **non sono
nostri**. Nessuno di questi materiali sta dentro il repository o dentro il
programma che si installa: gli script in `scripts/` li scaricano dalle
fonti originali sulla macchina di chi esegue la misura, e lì restano.

Il credito sta qui lo stesso, per due ragioni. La prima è che **le nostre
misure si appoggiano al lavoro di qualcun altro**, e citarlo è ciò che le
rende ricontrollabili invece che da credere sulla parola. La seconda è che
le licenze qui sotto chiedono l'attribuzione a chi *usa* il materiale, non
solo a chi lo ridistribuisce.

| Materiale | Cosa misura | Licenza |
|---|---|---|
| Gazzette Ufficiali, moduli dell'Agenzia delle Entrate, moduli IRS (`scripts/scarica_corpus_pubblico.py`) | **Falsi positivi**: documenti pubblici che non contengono dati personali, dove ogni sostituzione è un errore | Documenti pubblici degli enti che li pubblicano |
| `ai4privacy/open-pii-masking-500k-ai4privacy`, righe italiane (`scripts/scarica_corpus_ai4privacy.py`) | **Richiamo** sui dati con una forma riconoscibile | Il campo licenza dice `other`: il corpus è **generato con Llama 3.1/3.3**, quindi porta con sé la Llama Community License e la relativa Acceptable Use Policy, che si ereditano usandolo. Da guardare **prima** di legarlo a un prodotto commerciale |
| `rizzoaiacademy/anonimizzazione-testi-italiano-clean`, split `validation` (`scripts/scarica_corpus_legale_it.py`) | **Richiamo** su testi amministrativi e legali italiani, con valori dai checksum validi | MIT |

**Cosa non facciamo con questi corpora.** Non ci si addestra niente: il
motore di Mr. Rao è deterministico e non ha pesi. Servono solo a misurare —
e i loro limiti sono scritti nella docstring di ciascuno script, perché un
corpus usato per la cosa sbagliata dà numeri che sembrano solidi e non lo
sono.

---
---

# NOTICE — additional terms, name and trademark

Mr. Rao is distributed under the **GNU AGPL-3.0** ([LICENSE](LICENSE)). This
file takes nothing away from that licence: it adds the few conditions that
**section 7** of the AGPL-3.0 expressly allows, and states what the licence
does **not** cover.

Copyright holder: **Antonio Andrea Rao**.

**1. The name is not covered by the licence.** "**Mr. Rao**" and "**Mr. Rao
Plus**" are trade names of the project and its author. The AGPL grants rights
over the **code**, not over names: under **section 7(e)** of the AGPL-3.0,
**no right is granted** to use these names, the logos or the project's other
distinctive signs. The code may be copied, modified and redistributed — it is
free software and that stays true without exception. **What you may not do is
call it by this name.**

**2. A modified version must mark itself as different.** Under **section
7(c)**, anyone distributing a modified version must mark it in reasonable ways
as **different from the original**: a different product name, and no name that
could be confused with "Mr. Rao".

**3. Attribution must be preserved.** Under **section 7(b)**, the
documentation and the about screens of a modified version must keep the
statement of origin: *Based on **Mr. Rao** by Antonio Andrea Rao —
<https://github.com/AntonioRao/mr-rao>*.

**4. Why the conditions point this way and not the other.** It is worth saying
plainly, because the opposite question comes up naturally: **a fork cannot be
compelled to keep the original name**, and it would not be desirable either.
Not possible, because trademark law lets you *forbid* the use of a name, not
*impose* it, and because section 7 lists the permitted additional terms
exhaustively — a clause compelling the name would be a "further restriction"
outside that list, and a recipient would be entitled to **remove it**. Not
desirable, because the day somebody ships a bad version, that version would
carry **this** name and there would be no way to say "that is not ours".
Trademark exists precisely so that one can say it.

**5. Dual licensing.** The author, holding **all** rights over the code, may
license the same software under terms other than the AGPL, commercial licences
included. That is the reason for the clause in
[CONTRIBUTING.en.md](CONTRIBUTING.en.md). **Mr. Rao Plus** — the browser
extension — is a separate product, not distributed under the AGPL, and is not
part of this repository.

**6. Third-party corpora used for measurement, and not redistributed.** The
figures this project publishes — false positives, recall, per-category
coverage — are measured on documents and corpora that are **not ours**. None
of that material is inside the repository or the installed program: the
scripts in `scripts/` download it from the original sources onto the machine
of whoever runs the measurement, and there it stays. The credit belongs here
all the same, for two reasons: our measurements **rest on somebody else's
work**, and citing it is what makes them checkable rather than a matter of
trust; and the licences below ask for attribution from whoever *uses* the
material, not only from whoever redistributes it.

| Material | What it measures | Licence |
|---|---|---|
| Italian *Gazzetta Ufficiale* issues, Agenzia delle Entrate forms, IRS forms (`scripts/scarica_corpus_pubblico.py`) | **False positives**: public documents containing no personal data, where every substitution is an error | Public documents of the bodies that publish them |
| `ai4privacy/open-pii-masking-500k-ai4privacy`, Italian rows (`scripts/scarica_corpus_ai4privacy.py`) | **Recall** on data with a recognisable shape | The licence field says `other`: the corpus is **generated with Llama 3.1/3.3**, so it carries the Llama Community Licence and its Acceptable Use Policy, inherited by using it. To be checked **before** tying it to a commercial product |
| `rizzoaiacademy/anonimizzazione-testi-italiano-clean`, `validation` split (`scripts/scarica_corpus_legale_it.py`) | **Recall** on Italian administrative and legal text, with checksum-valid values | MIT |

Nothing is trained on any of it: the Mr. Rao engine is deterministic and has
no weights. These corpora only measure — and the limits of each are written
in the docstring of its script, because a corpus used for the wrong thing
gives numbers that look solid and are not.
