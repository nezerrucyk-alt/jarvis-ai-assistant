# Code signing and build verification

## Current status

JARVIS builds are **not code-signed** yet. That means:

- Windows SmartScreen may show «Windows protected your PC»;
- macOS Gatekeeper may say the app is damaged or from an unidentified developer;
- Linux does not require a signature, but your distribution may still warn.

This is not hidden on the website. Until a certificate exists, every release
ships `SHA256SUMS.txt` and GitHub build provenance, so you can verify that the
file was produced by this repository's release workflow and was not modified.

## Option 1 — verify SHA256 (all platforms)

1. Download the build and `SHA256SUMS.txt` from the same release.
2. Run the command for your system in the folder with both files.

Windows (PowerShell):

```powershell
Get-FileHash .\JARVIS-Windows.exe -Algorithm SHA256
Get-Content .\SHA256SUMS.txt
```

macOS:

```bash
shasum -a 256 JARVIS-macOS.zip
cat SHA256SUMS.txt
```

Linux:

```bash
sha256sum JARVIS-Linux.tar.gz
cat SHA256SUMS.txt
```

The hash must match exactly. If it does not, delete the file and download it
again from the official releases page.

## Option 2 — verify GitHub attestation (recommended)

The release workflow uses `actions/attest-build-provenance`, which records
which workflow, commit and repository produced each artifact.

Install the GitHub CLI, then run:

```bash
gh attestation verify JARVIS-Windows.exe --repo nezerrucyk-alt/jarvis-ai-assistant
```

Replace the filename with the artifact you downloaded. A successful check
prints the workflow, the commit SHA and the repository. This proves the file
came from the official CI run — it does not prove that the code is bug-free.

## Option 3 — build from source

If you do not trust prebuilt binaries, build them yourself:

```bash
git clone https://github.com/nezerrucyk-alt/jarvis-ai-assistant.git
cd jarvis-ai-assistant
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed --name JARVIS --icon assets/jarvis.ico --add-data "assets;assets" jarvis.py
```

On macOS/Linux replace `;` with `:` in `--add-data` and use `--windowed` for
the `.app` bundle. The result is your own local build, so no third-party
signature is involved.

## Windows SmartScreen

If you verified the hash and still want to run the build:

1. Click «More info».
2. Click «Run anyway».

Do not disable SmartScreen globally and do not add blanket exclusions. If the
hash does not match, stop.

## macOS Gatekeeper

Right-click `JARVIS.app` → **Open** → **Open** again. If macOS still blocks it:

```bash
xattr -dr com.apple.quarantine /Applications/JARVIS.app
open /Applications/JARVIS.app
```

Only do this after verifying the SHA256 or the attestation.

## Linux

Make the binary executable and run it:

```bash
chmod +x JARVIS
./JARVIS
```

Some distributions need `libportaudio2`, `libasound2` and X11/XWayland.

## The signing plan

The project plans to apply for the
[SignPath.io](https://signpath.io/) free code-signing program for open-source
projects. If approved:

- Windows builds will be signed with a real certificate and SmartScreen
  reputation will improve over time;
- the release workflow will sign artifacts before publishing;
- this page will be updated with the certificate details and verification
  commands;
- older unsigned releases will stay available for transparency.

There is no paid certificate and no SignPath application has been submitted
yet. The roadmap marks this honestly as «in progress»; do not treat the plan
as a guarantee.

## What signing does and does not prove

A valid signature proves that the binary was signed by the certificate owner
and was not modified after signing. It does **not** prove that the code has no
bugs or that the project is trustworthy by itself. Hashes, attestations, open
source and reproducible builds are complementary signals — use them together.
