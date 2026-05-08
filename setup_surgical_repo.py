"""
setup_surgical_repo.py
======================
One-shot repo scaffold for SurgicalWiki Pro.

Run ONCE from repo root (L:\\medical\\surgical-wiki):
  python setup_surgical_repo.py

What it creates:
  .gitattributes          -- git-crypt encryption rules
  .gitignore              -- sensible Python / Windows / Obsidian ignores
  docs/git_crypt_setup.md -- step-by-step git-crypt guide for Windows
  docs/ci_workflow.yml    -- GitHub Actions Prolog verification workflow
  LICENSE                 -- proprietary licence (Bailing Zhang, 2026)
  vault/_meta/            -- meta directory for prolog_report.json
  rules/                  -- Prolog KB directory (if missing)
  pipeline/               -- Python pipeline directory (if missing)

Then prints the 11-step git + git-crypt commands to run.
"""

import os
import sys
from pathlib import Path

# ----------------------------------------------------------------
# CONFIGURATION  -- edit if your layout differs
# ----------------------------------------------------------------
REPO_ROOT   = Path(r"L:\医疗健康\surgical-wiki")
KEY_PATH    = r"L:\医疗健康\surgical-wiki-PRIVATE.key"
GITHUB_URL  = "https://github.com/aussie-bzhang/surgical-wiki.git"
AUTHOR      = "Bailing Zhang"
YEAR        = "2026"

# ----------------------------------------------------------------
# FILE TEMPLATES
# ----------------------------------------------------------------

GITATTRIBUTES = """\
# git-crypt: encrypt sensitive synthesis reports and Prolog KB
vault/synthesis/**          filter=git-crypt diff=git-crypt
vault/_meta/**              filter=git-crypt diff=git-crypt
rules/**                    filter=git-crypt diff=git-crypt
pipeline/**                 filter=git-crypt diff=git-crypt

# Plain text -- not encrypted (structure only)
vault/*.md                  text eol=lf
*.gitattributes             text eol=lf
README.md                   text eol=lf
LICENSE                     text eol=lf
"""

GITIGNORE = """\
# Python
__pycache__/
*.py[cod]
*.pyo
*.egg-info/
dist/
build/
.env
venv/
env/

# Obsidian workspace (local only)
.obsidian/workspace.json
.obsidian/workspace-mobile.json

# Windows
Thumbs.db
desktop.ini
*.lnk

# Reports (regenerated on CI)
vault/_meta/prolog_report.json

# Sensitive key files -- NEVER commit
*.key
*.aes
"""

LICENSE_TEXT = """\
SurgicalWiki Pro -- Proprietary Licence
Copyright (c) {year} {author}. All rights reserved.

This repository and its contents (the "Software") are the exclusive
intellectual property of {author}.

GRANT OF ACCESS
You may access this repository solely if you have been granted explicit
written permission by the copyright holder.

RESTRICTIONS
You may NOT:
  (a) copy, distribute, or sublicense the Software or any portion thereof;
  (b) use the Software for commercial purposes without prior written consent;
  (c) reverse-engineer, decompile, or disassemble the Software;
  (d) re-identify any de-identified patient data contained herein.

CLINICAL DISCLAIMER
This Software is an educational tool only. It does not constitute medical
advice and must not be used as the sole basis for any clinical decision.
All clinical decisions remain the responsibility of the licensed practitioner.

TERMINATION
Access rights terminate immediately upon breach of any provision above.

For licensing enquiries contact the copyright holder directly.
""".format(year=YEAR, author=AUTHOR)

GIT_CRYPT_GUIDE = """\
# git-crypt Setup Guide for SurgicalWiki Pro (Windows)

## 1. Install git-crypt

Option A (Scoop -- recommended):
  scoop install git-crypt

Option B (manual):
  Download git-crypt-0.7.0-x86_64.exe from
    https://github.com/AGWA/git-crypt/releases
  Rename to git-crypt.exe and add to PATH.

## 2. Initialise in the repo

  cd L:\\medical\\surgical-wiki
  git init
  git-crypt init

## 3. Check .gitattributes (already created by setup script)

  cat .gitattributes

## 4. Export your encryption key -- KEEP THIS SAFE

  git-crypt export-key L:\\medical\\surgical-wiki-PRIVATE.key

Store this key in a secure location (password manager, encrypted drive).
NEVER commit the .key file to git.

## 5. Add files and make initial commit

  git add .
  git commit -m "Initial commit: SurgicalWiki Pro v1.0"

## 6. Create a PRIVATE repo on GitHub

  https://github.com/new
  Name: surgical-wiki
  Visibility: Private

## 7. Push

  git remote add origin https://github.com/aussie-bzhang/surgical-wiki.git
  git push -u origin main

## 8. Grant access to an authorized collaborator (e.g. your son)

  a. GitHub -> Settings -> Collaborators -> Add people
  b. Send the .key file via a secure channel (encrypted email, Signal, etc.)
  c. Collaborator runs:
       git clone https://github.com/aussie-bzhang/surgical-wiki.git
       cd surgical-wiki
       git-crypt unlock /path/to/surgical-wiki-PRIVATE.key

## What happens without the key?

Encrypted files (rules/, pipeline/, vault/synthesis/, vault/_meta/) appear
as random binary data -- unreadable without the key.
Unencrypted files (README.md, vault/*.md case pages, docs/) remain visible.
"""

CI_WORKFLOW = """\
# .github/workflows/prolog_verify.yml
# Runs on every push to main -- verifies Prolog KB
name: Prolog KB Verification

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install SWI-Prolog
        run: |
          sudo apt-get update -qq
          sudo apt-get install -y swi-prolog

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Run Prolog KB verifier
        run: python pipeline/surgical_prolog_verifier.py --swipl swipl

      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: prolog-kb-report
          path: vault/_meta/prolog_report.json
"""

# ----------------------------------------------------------------
# SCAFFOLD RUNNER
# ----------------------------------------------------------------

DIRS_TO_CREATE = [
    "rules",
    "pipeline",
    "vault/_meta",
    "vault/synthesis",
    "docs",
    ".github/workflows",
]

FILES_TO_CREATE = {
    ".gitattributes":                    GITATTRIBUTES,
    ".gitignore":                        GITIGNORE,
    "LICENSE":                           LICENSE_TEXT,
    "docs/git_crypt_setup.md":           GIT_CRYPT_GUIDE,
    "docs/ci_workflow.yml":              CI_WORKFLOW,
}


def run():
    if not REPO_ROOT.exists():
        print("[ERROR] Repo root not found: " + str(REPO_ROOT))
        print("  Create the directory first or edit REPO_ROOT in this script.")
        sys.exit(1)

    os.chdir(REPO_ROOT)
    print("=" * 60)
    print("  SurgicalWiki Pro -- Repo Scaffold")
    print("  Root: " + str(REPO_ROOT))
    print("=" * 60)

    # Create directories
    for d in DIRS_TO_CREATE:
        path = REPO_ROOT / d
        path.mkdir(parents=True, exist_ok=True)
        # Touch a .gitkeep so git tracks the empty dir
        keep = path / ".gitkeep"
        if not keep.exists():
            keep.touch()
        print("  [DIR]  " + d)

    # Write files (skip if already exist to avoid overwriting)
    for rel_path, content in FILES_TO_CREATE.items():
        target = REPO_ROOT / rel_path
        if target.exists():
            print("  [SKIP] " + rel_path + " (already exists)")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as fh:
                fh.write(content)
            print("  [OK]   " + rel_path)

    # Copy CI workflow to correct location
    ci_src  = REPO_ROOT / "docs" / "ci_workflow.yml"
    ci_dest = REPO_ROOT / ".github" / "workflows" / "prolog_verify.yml"
    if not ci_dest.exists() and ci_src.exists():
        import shutil
        shutil.copy(ci_src, ci_dest)
        print("  [OK]   .github/workflows/prolog_verify.yml")

    print("")
    print("=" * 60)
    print("  SCAFFOLD COMPLETE")
    print("=" * 60)
    print("")
    print("  Next: run these commands IN ORDER")
    print("")
    print("  Step 1 : cd " + str(REPO_ROOT))
    print("  Step 2 : git init")
    print("  Step 3 : git-crypt init")
    print("  Step 4 : git-crypt export-key " + KEY_PATH)
    print("           *** BACK UP THIS KEY FILE IMMEDIATELY ***")
    print("  Step 5 : git add .")
    print('  Step 6 : git commit -m "Initial commit: SurgicalWiki Pro v1.0"')
    print("  Step 7 : Create PRIVATE repo at https://github.com/new")
    print("           Name it: surgical-wiki")
    print("  Step 8 : git remote add origin " + GITHUB_URL)
    print("  Step 9 : git push -u origin main")
    print("  Step 10: Add collaborator in GitHub -> Settings -> Collaborators")
    print("  Step 11: Send the .key file securely to your son")
    print("")
    print("  See docs/git_crypt_setup.md for full details.")
    print("=" * 60)


if __name__ == "__main__":
    run()
