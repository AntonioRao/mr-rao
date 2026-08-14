# Code signing policy — Mr. Rao

This document says who can cause a Mr. Rao binary to be signed, what has to
be true before that happens, and how anyone can check the result without
taking our word for it.

It is public because a signing policy that only the signer can read proves
nothing: the point of a signature is to let a stranger decide whether to
trust a file, and a stranger cannot evaluate a promise they cannot see.

**Current status: releases downloaded from GitHub are not code-signed.**
The application to the SignPath Foundation was **declined in August 2026**:
they look for projects with an established community, and this one does not
have it yet. No free certificate carrying the author's name exists — a
certificate authority has to verify an identity, and that check is what they
charge for.

**The route that removes the Windows warning is the Microsoft Store**, where
the package is signed by Microsoft and Smart App Control trusts it. For the
portable zip and the installer the integrity guarantees stay the ones
described under
[What already protects a release](#what-already-protects-a-release) — which
are not weaker than a signature, only different, and Windows does not read
them.

## Who does what

Mr. Rao is maintained by one person, Antonio Andrea Rao. Writing that a
review board exists would be the easiest lie in this document, so instead:

| Role | Who | What it means here |
|------|-----|--------------------|
| Author | Antonio Andrea Rao | Writes the code and opens the changes |
| Reviewer | Antonio Andrea Rao | Reviews before merge — the same person, so the review is *procedural*, not independent |
| Approver | Antonio Andrea Rao | The only account that can trigger a signed release |

**The honest consequence:** on a one-person project the separation of duties
is not between people, it is between a person and a machine. Nothing here
relies on a second human catching a mistake. What it relies on is that the
automated gate runs on a machine the author does not control and cannot
persuade, and that everything it checks is public.

If the project ever gains a second maintainer, the Reviewer row must name
someone other than the Author, and this table must be updated **before** the
next signed release, not after.

## What must be true before anything is signed

1. **The change is on `main` and public.** Nothing is signed from a private
   branch or a working directory.
2. **Continuous integration is green** on the exact commit being released.
   Two workflows run, and it is worth knowing which one checks what, because
   they are not the same. `ci.yml` runs four steps — byte-compile, an import
   of every module, a dependency health check, and the full test suite. The
   **six-step quality gate** — the four above plus third-party licence
   alignment and the check that fails when published documentation stops
   matching the code — runs inside the release build itself
   (`scripts/build_portable.bat` calls `scripts/quality_gate.bat`), which is
   the workflow that produces the package that would be signed. The licence
   step is left out of `ci.yml` deliberately, with the reason written in the
   file: it compares the list against the versions installed on the
   maintainer's machine, and a clean runner resolves different ones, so
   there it would fail for the wrong reason. What matters for this policy is
   that no package reaches the signing step without the six of them having
   passed — but "CI is green" alone is a weaker statement than it looks.
3. **The package is built on a clean GitHub-hosted runner**, never on a
   developer machine. This is not a formality: three releases once shipped
   Office libraries that were present only because they happened to be in
   the developer's virtual environment, and no local check could have seen
   it. The build creates its own environment from the declared dependency
   list, and a verification step converts a real `.docx`, `.xlsx` and
   `.pptx` afterwards — if a declared dependency is missing, the package is
   rejected instead of published.
4. **The release is triggered manually**, by the maintainer, for a named
   tag. There is no trigger that signs on every push.

A build that fails any of these is not signed and not published. There is no
override.

## Accounts and access

- The GitHub account that can trigger a release has **multi-factor
  authentication** enabled.
- No signing key is stored on a developer machine, in the repository, or in
  a CI secret. Under the SignPath Foundation model the private key never
  leaves the Foundation's hardware security module and the maintainer never
  receives it.
- Secrets used by release automation are stored as GitHub Actions secrets,
  scoped to this repository, and are never printed to a log.

## What already protects a release

These exist today and will continue to exist after signing is in place. They
answer a different question than a signature does — *where did this file
come from* rather than *who is willing to be named for it*.

- **`SHA256SUMS.txt`** is published with every release, so a download can be
  checked byte for byte.
- **GitHub Artifact Attestations (Sigstore)** are generated for the release
  artifacts. They tie a binary to the exact workflow run, repository and
  commit that produced it, and can be verified with
  `gh attestation verify`. Signing proves *someone* stands behind the file;
  an attestation proves *which build* made it. The second is harder to fake
  and is the one that would catch a compromised release pipeline.
- **The fixed archive name never changes** between releases
  (`MrRao-Portable.zip`), because the download links in the READMEs and on
  the website depend on it. The version is carried by the tag and by a
  second, versioned archive.

## Reporting a problem

If you believe a released binary does not match what this repository
produced, or that a signature is attached to something it should not be,
write to <antonio.andrea.rao@gmail.com>. Include the file name, the release
tag and the SHA-256 you observed.

## Changes to this policy

This file is versioned in the repository. Its history is the record: if a
rule here was ever relaxed, `git log docs/CODE-SIGNING-POLICY.md` shows when
and in which commit. A policy whose past cannot be inspected is a statement
of intent, not a control.
