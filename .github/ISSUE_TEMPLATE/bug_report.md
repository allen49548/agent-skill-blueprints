---
name: Bug report
about: Something does not work as documented
title: "[bug] "
labels: bug
assignees: ''
---

**Version**
Output of `python3 -c "import sys; sys.path.insert(0,'.'); from skillkit import __version__; print(__version__)"` or the `VERSION` file.

**Environment**
- Python version:
- OS:
- Package: `document-intake-ledger` / `message-to-workbook-sync` / `scheduled-digest-publisher` / `verified-batch-calculation` / shared runtime / build

**Command**
```
python3 run.py ...
```

**Expected**
What the documentation or capability matrix says should happen.

**Actual**
What happened instead. Paste the relevant part of `run.log` (JSON lines) and the run summary, with identifiers redacted.

**Reproduction**
Minimal steps, ideally using only `examples/demo_input.json`.

**Checklist**
- [ ] I read [docs/capability-matrix.md](../../docs/capability-matrix.md) and the feature is marked Implemented
- [ ] I ran `python3 run.py doctor`
- [ ] I removed tokens, account/chat identifiers, real names and absolute paths from pasted output
