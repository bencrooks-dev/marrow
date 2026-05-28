# Governance

This document explains how decisions are made for **ARI** (the [Agent Runtime
Interface](ARI-SPEC.md) specification) and for **marrow** (its reference
implementation). It is deliberately honest about the project's current stage and
the path to neutral governance — because a standard that looks like one company's
property does not get adopted.

## Two things, governed differently

| | **ARI** (the standard) | **marrow** (the implementation) |
|---|---|---|
| What it is | A language-neutral spec | An Apache-2.0 codebase |
| License | CC BY 4.0 (spec text) | Apache-2.0 |
| Change process | [RFC process](docs/ari-rfc-process.md) | normal PRs + [STABILITY.md](STABILITY.md) |
| Goal | belong to the whole industry | be the canonical, conformant runtime |

Keeping these distinct is a governance requirement, not a formality: anyone may
implement ARI without touching marrow, and the spec must be able to outlive any
single implementation.

## Current stage (be honest)

ARI is at **v0.1 (Draft)** and marrow is **pre-1.0**. Today the project is
**maintainer-led** (a small maintainer set, effectively a BDFL model). This is
normal and appropriate for this stage — but it is explicitly a *stage*, not the
end state. We do not pretend to be a foundation we are not.

## Decision-making (now)

- **Routine changes** (bug fixes, docs, additive non-breaking features): a
  maintainer reviews and merges via PR.
- **Spec changes to ARI**: follow the [RFC process](docs/ari-rfc-process.md). A
  Draft-stage spec can change with maintainer approval + a recorded rationale in
  the RFC; once a section reaches **Stable**, it follows the
  backward-compatibility rules in [ARI-SPEC §11](ARI-SPEC.md#11-versioning-and-stability).
- **Breaking changes** require an RFC, a migration note, and a minor-version
  deprecation window.

## Path to neutral governance (the commitment)

We will move ARI out of a single-vendor home as adoption justifies it. The
triggers, in order:

1. **Second independent conformant implementation** exists and passes the
   [conformance kit](ari-conformance/) → publish a public RFC process and an open
   decision log.
2. **External contributors / adopters** beyond the originating maintainer →
   establish a working group with named stewards from more than one organization.
3. **Material industry adoption** → move the ARI spec to a neutral home (its own
   org/repo) under an open-governance body. MCP's donation to the Linux
   Foundation's Agentic AI Foundation (Dec 2025) is the model we intend to follow.

Until trigger 3, this repository is the spec's interim home, and `marrow`'s
maintainers are its interim stewards.

## Conformance authority

"ARI-conformant" is not granted by us as a favor — it is **earned by passing the
[conformance kit](ari-conformance/)** and claimed per
[ARI §10.4](ARI-SPEC.md#104-claiming-conformance). We maintain the kit and the
[conformance registry](CONFORMANCE.md); we do not gatekeep who may implement the
spec.

## Code of conduct

Participation is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Amending this document

Changes to governance follow the same RFC process as spec changes, so the rules
for changing the rules are themselves on the record.
