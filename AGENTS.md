# Working agreement

Be brief.

For a **new feature**: open an issue in the main repo, write the plan there,
and implement only that plan.

For a **fix found while working**: go straight to the branch, and say in the
pull request what it was and why. The issue is there to decide *what to
build*, not to grant permission to repair what is broken.

Either way, commit to `issue-<n>` (or `fix-<slug>`) and open a pull request
to main. Merge only when the user asks, then update all the documentation in
`docs/*.md`.

---

## Standing rules for this repository

Not new instructions — the ones already paid for, kept here so they do not
have to be learnt twice.

- **Push only when certain.** Commit locally, verify, then ask. Anything
  that reaches GitHub is public.
- **Check CI after every push.** A green run on the developer's machine has
  never proved anything about a clean one.
- **Run the quality gate before committing**: `scripts\quality_gate.bat`.
  Five steps; the last checks that the published documents still tell the
  truth.
- **A check that cannot fail is not a check.** Before saying "verified", ask
  how that check would have said no. Start from `git ls-files`, not from the
  files already open, and verify in an environment that owns nothing.
- **Disable it and watch the test go red.** A test that stays green when the
  thing it guards is removed was guarding nothing.
- **Never pass a backslash through a shell.** `python -c` and heredocs add
  levels of escaping, and `\\\\` does not arrive as expected. Use Edit, or
  build the string with `chr(92)`.
- **Read MarkItDown's dependencies from its own sources**, never guess them
  from the extension: `.docx` needs `mammoth`, not `python-docx`.
- **Italian texts**: "tool" not "attrezzo", "anonimizzazione" not
  "schermatura", "di default" not "di serie".
