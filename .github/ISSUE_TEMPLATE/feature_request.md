---
name: Feature request
about: Propose a new capability, adapter or mechanism
title: "[feature] "
labels: enhancement
assignees: ''
---

**Problem**
What are you trying to do that the current runtime cannot?

**Proposed change**
Which layer does it touch? Shared runtime / a profile / an adapter / docs / build.

**Status today**
Check [docs/capability-matrix.md](../../docs/capability-matrix.md). Is this currently Target design, Contract only, or genuinely absent?

**Alternatives considered**
Could this be done with an existing adapter or a config change instead of code?

**Tests**
Which invariant would you add to `tests/`? A row should not move to Implemented without a test.

**Compatibility**
Does this change `config.example.json`, `wizard` or `engine` structures? All four packages must keep identical structures.
