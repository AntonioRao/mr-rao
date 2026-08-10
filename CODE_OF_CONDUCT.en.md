# Code of conduct

*Questo documento in italiano: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Where
the two disagree, the Italian text is the authoritative one — this is a
translation.*

## The rule that comes before the others on this project

**Never write real personal data** — yours or anyone else's — in an issue, a
pull request, a comment or a test file. Not even to show a defect. Not even
"it's only a number".

This is not pedantry: this repository is **public**, and what lands in it stays
recoverable even after a deletion, because it stays in the git history, in
GitHub's cache and in the copies other people have already cloned. Personal
data pasted here to report a defect is exactly the harm this program exists to
prevent, done with our own hands.

If a defect only reproduces with real data, **describe the shape and invent a
value that resembles it**. The recognisers look at structure, not at people: an
invented IBAN that passes mod-97 reproduces the defect just as well as a real
one. The examples in `README.md` and in the tests are all built that way, and
they are a good starting point.

If you notice it has already happened — yours or someone else's — **say so
straight away** to antonio.andrea.rao@gmail.com instead of replying in the
thread: it gets removed before it is indexed, and without drawing attention to
it.

## The rest

This project adopts the **[Contributor Covenant][cc], version 2.1**. In short,
without trying to rewrite it better than it is:

- take part with respect, and assume good faith in others;
- accept criticism of the code without taking it as criticism of yourself;
- no insults, harassment, personal attacks, sexual or violent content, and no
  publishing of other people's private information;
- the maintainer may remove contributions and comments that break these rules,
  and will explain why.

**Where it applies**: in the project's spaces — issues, pull requests,
discussions, comments — and anywhere someone represents the project in public.

**Reporting**: antonio.andrea.rao@gmail.com. Reports are read by one person,
who is also the project's only author, and handled confidentially. If the
report concerns him, saying so openly in a public issue is a legitimate route:
a project with a single maintainer has no third party to appeal to, and
pretending otherwise would be worse than admitting it.

**What happens next**: you get an answer, and an explanation of what was
decided and why. Consequences range from a private clarification to removal of
the content, up to exclusion from the project in serious or repeated cases.

The full Contributor Covenant text, which is what governs in case of doubt, is
at <https://www.contributor-covenant.org/version/2/1/code_of_conduct/>.

[cc]: https://www.contributor-covenant.org
