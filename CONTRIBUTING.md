# Contributing

These packages are runnable capability skills with a shared runtime and per-package configuration. A good contribution makes a capability clearer or more reusable; a bad one quietly reintroduces a specific project or breaks the "clone and run" guarantee.

## Non-negotiable rules

1. **Code in English, READMEs in Chinese.** Identifiers, concepts, `SKILL.md`, `DESIGN.md`, `docs/`, config keys and inline comments stay English. All five `README.md` files are user-facing Chinese. `tools/check_repo.py` enforces both directions. Do not add localized trigger phrases to `SKILL.md` frontmatter.
2. **Capability-level naming.** Package slugs, config keys and concept names describe the mechanism. Domain nouns may appear only in illustrative use cases, never in identifiers.
3. **No project-specific vocabulary.** Do not introduce brands, product names, organization names, human roles, store names, team names or industry jargon into concepts or identifiers. `feishu` and `wecom` are allowed only as config option values.
4. **No real identifiers.** Chat identifiers, account identifiers, absolute home-directory paths, real personal names, real amounts, tokens and API keys are forbidden anywhere in the repository. Use `<PLACEHOLDER>` or an environment variable reference.
5. **Configuration over constants.** Any value that varies between deployments lives in `config.json`, generated from `config.example.json`. Document every field in `config.schema.md`.
6. **Invariants stay documented.** If you change a pipeline, update the invariants in the package `DESIGN.md` and the glossary in `docs/vocabulary.md`.
7. **One capability per package.** Do not merge packages or add a second unrelated capability.
8. **Runtime is standard library only.** `engine.py` must not import third-party packages or vendor SDKs. Built-in adapters work with zero credentials; real platform connectors are registered, never hardcoded.
9. **Onboarding choices are config, not prose.** Any new platform, group, message source, output mode, notification template or schedule preset belongs in `docs/onboarding-contract.md` and in the shared `wizard` section of every package. All four `wizard` structures must stay identical.
10. **One runtime, one source.** Never copy `skillkit/engine.py` into a skill directory. `run.py` stays a shim; standalone copies are produced by `build.py` into gitignored `dist/`.

## Adding a new package

1. Create `skills/<capability-slug>/` with `SKILL.md`, `README.md`, `DESIGN.md`, `config.example.json`, `config.schema.md`, `profile.json`, the standard `run.py` shim and `examples/demo_input.json`.
2. Add a row to the catalog in the root `README.md`, including a "do NOT reach for it when" case.
3. Add the old-to-new mapping and removed vocabulary to `docs/abstraction-map.md`.
4. Introduce any new canonical term in `docs/vocabulary.md` first, then use it consistently.
5. Update the repository layout tree in the root `README.md` and the applicability matrix in `docs/onboarding-contract.md`.
6. Verify `python3 run.py demo`, `setup --yes`, `doctor` and `run` all succeed in the new package.

## `SKILL.md` frontmatter

Keep frontmatter minimal and valid:

```yaml
---
name: <capability-slug>
description: <English description of the mechanism, when to use it, and what it explicitly does not do>
agent_created: true
---
```

The description must be trigger-oriented (what a user would ask for) and must state the boundary. Avoid enumerating a long keyword list; a capability description generalizes better.

## Pull request checklist

- [ ] All five READMEs are Chinese; all other docs, identifiers and comments are English.
- [ ] No real names, identifiers, paths, amounts or credentials.
- [ ] `config.example.json` parses and the `engine` section works with zero credentials; `config.schema.md` documents every field.
- [ ] `profile.json` declares defaults, applicable wizard steps and invariants.
- [ ] `DESIGN.md` lists invariants, extension points and a failure matrix.
- [ ] `README.md` lists both applicable and non-applicable scenarios and the four quick-start commands.
- [ ] `python3 -m unittest discover -s tests -v` passes; new behaviour has a test.
- [ ] `python3 tools/check_repo.py` passes.
- [ ] `python3 build.py --check` passes.
- [ ] `docs/capability-matrix.md` and `CHANGELOG.md` reflect any status change.
- [ ] Privacy pre-flight from `PUBLISHING.md` passes.
- [ ] Root catalog, abstraction map and onboarding contract are updated where needed.
