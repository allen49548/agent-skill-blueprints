# Publishing: Complete Repository Creation Commands

Run these commands in order. They create a local git repository in the generated workspace directory, associate it with a new empty remote repository, make the first commit and push it.

The local directory is named `open-source-skills`; the remote repository is named `agent-skill-blueprints`. Git does not require them to match. If you prefer them identical, rename the directory before step 2 and adjust the path.

**Published state (2026-11-15):** steps 5-10 have already been run, and version 0.2.0 has been released. The repository is live at `git@github.com:allen49548/agent-skill-blueprints.git` (public). Use the 'Subsequent releases' section for new changes. The earlier steps document how it was created so the procedure is reproducible.

Review each command before running it, and replace `GITHUB_OWNER`, `COPYRIGHT_HOLDER` and `LOCAL_REPO` with your own values. The LICENSE placeholder has been resolved; adjust the holder if you fork the project.

## 0. Set the placeholders

```bash
export GITHUB_OWNER="your-github-username"
export REPO_NAME="agent-skill-blueprints"
export COPYRIGHT_HOLDER="Your Name Or Organization"
export LOCAL_REPO="<PATH_TO_GENERATED_DIRECTORY>"
```

## 1. One-time git identity

Skip if already configured.

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
git config --global init.defaultBranch main
```

## 2. Enter the generated repository root

```bash
cd "$LOCAL_REPO"
pwd
find . -type f -not -path './.git/*' | sort
```

## 3. Fill the license placeholder

Use a literal replacement so names containing shell or regex metacharacters are safe, and so the same command works on macOS and Linux:

```bash
python3 - <<'PY'
import os, pathlib
holder = os.environ["COPYRIGHT_HOLDER"]
p = pathlib.Path("LICENSE")
text = p.read_text()
assert "<COPYRIGHT_HOLDER>" in text, "placeholder already replaced"
p.write_text(text.replace("<COPYRIGHT_HOLDER>", holder))
PY
```

Verify:

```bash
grep -n "Copyright" LICENSE
```

## 4. Privacy pre-flight (must print CLEAN before continuing)

Check for vendor identifiers, local machine paths, tokens and credentials:

```bash
grep -rInE '(oc_[a-f0-9]{16,}|ou_[a-f0-9]{16,}|ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|/Users/|/home/|C:\\Users\\|BEGIN [A-Z ]*PRIVATE KEY)' \
  --exclude-dir=.git --exclude=PUBLISHING.md . || echo "CLEAN: no identifiers, paths or credentials"
```

Check that all prose except the Chinese READMEs is ASCII-only English:

```bash
python3 - <<'PY'
import pathlib
bad = []
for p in pathlib.Path('.').rglob('*'):
    if not p.is_file() or '.git' in p.parts or p.name == 'README.md':
        continue
    for i, line in enumerate(p.read_text(errors='replace').splitlines(), 1):
        if any(ord(c) > 127 for c in line):
            bad.append((str(p), i))
print('CLEAN: ASCII only (README exempt)' if not bad else 'NON-ASCII FOUND: ' + repr(bad[:20]))
PY
```

Check that no untracked local config or state would be staged:

```bash
find . -name 'config.json' -o -name '.env' -o -name '*.sqlite' -o -name '*.xlsx'
```

If any check reports a hit, fix it before step 5. Note that `config.example.json` is a template with placeholders and is safe to publish; `config.json` is not.

## 5. Initialize the local repository

```bash
git init -b main
git status --short
```

## 6. Create the empty remote repository

GitHub does not create a repository on first push. Choose one option.

**Option A - GitHub CLI (recommended)**

```bash
gh auth status || gh auth login
gh repo create "${GITHUB_OWNER}/${REPO_NAME}" \
  --public \
  --description "Four project-independent, English-only capability blueprints for agent skills"
```

**Option B - Web UI**

Open `https://github.com/new`, set the repository name to `agent-skill-blueprints`, choose public or private, and **do not** tick README, .gitignore or License. An empty repository avoids a non-fast-forward conflict on the first push.

## 7. Associate the remote

SSH (matches the key-based workflow used by the original skill repositories):

```bash
ssh -T git@github.com
git remote add origin "git@github.com:${GITHUB_OWNER}/${REPO_NAME}.git"
git remote -v
```

HTTPS alternative, if SSH is unavailable:

```bash
git remote add origin "https://github.com/${GITHUB_OWNER}/${REPO_NAME}.git"
```

If `origin` already exists because of a previous attempt:

```bash
git remote set-url origin "git@github.com:${GITHUB_OWNER}/${REPO_NAME}.git"
```

## 8. Stage explicitly

Do not use `git add -A`. Stage only the intended documentation paths.

```bash
git add README.md LICENSE .gitignore CONTRIBUTING.md PUBLISHING.md
git add CHANGELOG.md SECURITY.md VERSION build.py
git add docs/ tools/ tests/ .github/ skillkit/
git add skills/scheduled-digest-publisher/
git add skills/verified-batch-calculation/
git add skills/message-to-workbook-sync/
git add skills/document-intake-ledger/
git status --short
```

Review the staged file list. It should contain only Markdown, JSON examples and dotfiles. Re-run the step 4 checks against the staged content if anything unexpected appears:

```bash
git diff --cached --stat
```

## 9. First commit

```bash
git commit -m "docs: initial release of four capability-level agent skill blueprints"
git log --oneline -1
```

## 10. First push

```bash
git push -u origin main
```

If the remote was created with a README or license and the push is rejected as non-fast-forward, do not force-push over someone else's history. Either delete and recreate the empty remote, or integrate deliberately:

```bash
git pull --rebase origin main
git push -u origin main
```

## 11. Verify

```bash
git status -sb
git remote show origin
gh repo view "${GITHUB_OWNER}/${REPO_NAME}" --web
```

Expected state: branch `main` tracks `origin/main`, working tree clean, and the remote contains the root docs plus four skill packages.

## Subsequent releases

```bash
cd "$LOCAL_REPO"
git status --short
git add <explicit-paths-only>
git commit -m "docs: <what changed and why>"
git push
```

## Notes

- This is a single monorepo by design. The original author-side toolkit enforced one repository per skill; that convention is intentionally not applied here.
- The generated directory is a copy. The four original skills were left untouched, so their scheduled automations, absolute paths and embedded identifiers continue to work.
- If those original repositories are ever made public, their current `SKILL.md` files contain real identifiers and must be sanitized first. Some already have identifiers in commit history; removing them from the current version does not remove them from history.
