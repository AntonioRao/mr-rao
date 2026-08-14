# Contributing to Mr. Rao

*Questo documento in italiano: [CONTRIBUTING.md](CONTRIBUTING.md). Where the
two disagree on the licensing terms below, **the Italian text is the
authoritative one** — this is a translation, not a second agreement.*

Thanks for the interest. One thing first, so you do not waste your time.

## The licence

Mr. Rao is free software under the **GNU AGPL-3.0** ([LICENSE](LICENSE)). By
opening a pull request you accept that your contribution is distributed
under the same licence.

### And one more thing, stated openly

By opening a pull request you also grant **Antonio Andrea Rao**, the
project's copyright holder, the non-exclusive, perpetual, irrevocable,
royalty-free and transferable right to use, modify and license your
contribution **under terms other than the AGPL** — commercial licences
included, and **including inclusion in separate and even proprietary
products**, not only in this one. You remain the author of your code and
keep every right to reuse it wherever and however you like.

The same grant covers **patents**: if you hold patents your contribution
would infringe, you grant the right to use it without having to ask you.
Without that line the copyright grant would leave standing a weapon that has
nothing to do with copyright — which is why the clause is in the Apache
licence and in every serious CLA.

And you **state two things about the contribution**: that it is yours or that
you have the right to grant it, and that it contains no code taken from a
project with an incompatible licence. It is the part that costs you nothing
and that the project actually needs: without it, every line received is a bet
on where it came from.

The project also reserves the use of the name "Mr. Rao". **The name is not
covered by the AGPL**: whoever copies the code — and is fully entitled to —
may not publish it under this name.

**Why this is needed, without circling the point.** The AGPL permits
commercial use, but it requires anyone who modifies the program or offers it
over a network to publish their own source. Some companies cannot accept
that constraint and ask for a different licence. Granting one is possible
only for someone who holds *all* the rights: a single contribution without
this clause closes that door for the entire project, and reopening it would
mean tracking down every author and asking each one for permission.

It is the same clause Qt and MySQL use, for the same reason.

If you are not comfortable with it — and that is a legitimate position, not
a whim — say so in the pull request instead of accepting something you do
not agree with. There is another way: for instance, describe the defect and
let the project write the fix.

The clause covers **everything** that enters the repository. It used to say
"for contributions of a few lines we do not care", and that sentence was a
hole: nobody ever defined how few is few, and a five-line function is code
just as much as a hundred-line one. A typo or a changed word is still out of
scope, but because it is **not a work of authorship** — not because we grant
an exemption.

**How you accept it.** There is a checkbox in the pull request template
([`.github/pull_request_template.md`](.github/pull_request_template.md)). It
exists to leave a dated trace of acceptance: a clause that lives only in a
file nobody is obliged to open is worth little the day someone says "I never
read that".

In practice: use it, modify it, redistribute it. The only serious obligation
kicks in if you offer it to others over a network — in that case you must
make the source of your version available (section 13).

## What is useful

Look at the [backlog](docs/BACKLOG.md): it is up to date and honest about
what is missing *(Italian)*. Particularly welcome:

- **Recognisers for other countries.** The architecture in
  `mr_rao/privacy.py` is already pattern + validator: adding Spanish NIFs or
  French SIRENs is mostly rule work, not plumbing.
- **False positives and false negatives in the redaction.** If a piece of
  personal data got past it, or a product code was mistaken for an IBAN,
  open an issue with an **invented** example (never real data).
- **Markdown preview.** The renderer is in `static/js/markdown.js`, written
  in house and exercised by `node` from inside pytest. If you find a
  document that renders badly, the case belongs there. One non-negotiable
  rule: **it must never emit a remote `<img>`**, because that would be a
  network call originating from the very document being redacted.
- **Tests.** There are 2217 tests and they are never enough. (The number is
  written before the word "tests" on purpose: that is how
  `scripts/check_docs.py` finds it. Written the other way round it stayed
  stuck at 161 for twenty releases.)

## What you need before a PR

```bash
scripts\quality_gate.bat
```

There are **six** steps, and they are worth knowing by name: when one goes
red, the message says which.

1. `compileall` — the syntax;
2. `scripts/check_import.py` — importing every module, one by one. A circular
   import passes step 1 with flying colours;
3. `mr_rao.cli health` — the dependencies are present and they load;
4. `scripts/gen_third_party.py --check` — the third-party licence list still
   matches the installed packages;
5. `pytest`;
6. `scripts/check_docs.py` — the published documents still tell the truth:
   versions, test counts, links, placeholders, command-line options.

### The pre-commit gate, if you want it

There is an **optional** `pre-commit` hook: nobody installs it behind your
back, you turn it on and take it off whenever you like.

```bash
venv\Scripts\python scripts\install_hooks.py --install
venv\Scripts\python scripts\install_hooks.py --status
venv\Scripts\python scripts\install_hooks.py --uninstall
```

It copies nothing into `.git/hooks`: it points `core.hooksPath` at
`.githooks/`, so the hook that runs is always the repository's and not an
old copy left on your machine. Uninstalling means removing that one config
line.

**What it runs, and why not the whole gate.** Only `compileall` and
`scripts/check_import.py`: half a second together. The full gate costs about
twenty seconds, almost all of it pytest — and twenty seconds per commit is
not a lot in absolute terms, it is a lot in the wrong place. A slow hook does
not get removed, it gets bypassed: you learn `--no-verify` and from then on
not even the fast half runs. So the hook answers one question, the one worth
asking at every commit: *does this tree load?* If you want the tests too:

```bash
MR_RAO_HOOK_FULL=1 git commit ...
```

That variable adds **pytest and nothing else** (`.githooks/pre-commit`): it is
not "the whole gate". Licences and published documents stay outside the hook
either way, and are checked by running `scripts\quality_gate.bat`.

Two things said openly instead of leaving you to find them out:

- the hook checks **the working tree**, not the index. If you have unstaged
  `.py` changes, what gets checked is not exactly what you are committing —
  and it tells you so on screen. Rebuilding the index in a separate copy
  would be more exact and far easier to get destructively wrong;
- it **does not replace `scripts\quality_gate.bat`** before a pull request.

If you develop on Linux or macOS: `.githooks/` is forced to LF by
`.gitattributes`. This is not style pedantry — a `#!/bin/sh` shebang with a
trailing `\r` simply does not start on Linux, and the error you get is `not
found`, which names the file and not the cause. On Windows, Git's `sh`
tolerates the `\r`, so anyone working only there would never see the defect
and would ship it to everyone else.

Three rules the project gave itself after paying for them:

0. **No feature ships without documentation.** This is not goodwill, it is a
   gate condition. It has happened twice: the Anglo pack shipped in 1.8.0
   with ten recognisers that never made it into the table in `PRIVACY.md`,
   and identity documents were shipped while the backlog still listed them
   as to do. In both cases the gate said green, because it was looking at
   versions, counts and links — things that have nothing to do with a new
   feature.

   Now `scripts/check_docs.py` verifies two things that do have everything
   to do with a new feature:

   - every **placeholder** the engine can emit is in the table in
     `docs/PRIVACY.md`. A new recogniser brings a new one, and there is no
     escaping that;
   - every **command-line option** is in `docs/CLI.md`. The parser is
     interrogated, not read with a regular expression: a check that
     approximates what it verifies misses precisely the case written in a
     way it did not anticipate.

   Both checks were seen to fail before they were believed.

1. **A regression test must be verified to fail on the previous code.** A
   test that passes with the bug still in place proves nothing. If you fix
   something, remove the fix, watch the test go red, put it back.

2. **Licences are not written by hand.** If you add a dependency, regenerate
   the list:
   ```bash
   venv\Scripts\python scripts\gen_third_party.py
   ```
   And if the dependency is copyleft (LGPL, MPL, GPL), add the text and the
   notice in `licenses/` as was done for **pystray** (LGPL-3.0) — today the
   only one that needs a folder of its own. The MPL-2.0 ones present
   (`certifi`, `tqdm`) sit in `THIRD_PARTY.md` among the special
   obligations, with a pointer to the project: MPL asks you to say where the
   source can be found, not to bundle it.
   The gate checks alignment, not the completeness of the obligations: that
   stays the responsibility of whoever adds the dependency.

## Style

- Code and comments in English; user-facing text in Italian.
- Comments explain **why**, not what: the what is readable from the code.
- No new dependencies without a strong reason. Every extra package is weight
  in the portable build and one more licence to respect.

## Reporting a bug

Three lines are enough: what you did, what you expected, what happened. With
the file format and the version (it is in the page footer, or from
`python -m mr_rao.cli --version`).

**Never attach real documents.** If a sample is needed, build a fake one:
this project exists precisely so that real documents do not get passed
around.
