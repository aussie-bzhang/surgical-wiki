# git-crypt Setup Guide for SurgicalWiki Pro (Windows)

## 1. Install git-crypt

Option A (Scoop -- recommended):
  scoop install git-crypt

Option B (manual):
  Download git-crypt-0.7.0-x86_64.exe from
    https://github.com/AGWA/git-crypt/releases
  Rename to git-crypt.exe and add to PATH.

## 2. Initialise in the repo

  cd L:\medical\surgical-wiki
  git init
  git-crypt init

## 3. Check .gitattributes (already created by setup script)

  cat .gitattributes

## 4. Export your encryption key -- KEEP THIS SAFE

  git-crypt export-key L:\medical\surgical-wiki-PRIVATE.key

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
