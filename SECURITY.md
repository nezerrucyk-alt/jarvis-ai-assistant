# Security policy

## Supported versions

| Version | Supported |
| --- | --- |
| 2.2.x | yes |
| 2.1.x | security fixes only |
| older | no |

The latest release is always listed on the
[releases page](https://github.com/nezerrucyk-alt/jarvis-ai-assistant/releases/latest).

## Reporting a vulnerability

Please **do not open a public issue** for security problems.

Use GitHub's private vulnerability reporting:

1. Open <https://github.com/nezerrucyk-alt/jarvis-ai-assistant/security/advisories/new>.
2. Describe the problem, the affected version and the steps to reproduce.
3. Add logs or a proof of concept if you have them, but remove API keys,
   tokens and personal data first.

If private reporting is unavailable, open a minimal public issue asking for a
private contact channel — without technical details.

## What to expect

- Acknowledgement within 3 business days.
- A first assessment within 7 days.
- A fix or a mitigation plan before any public disclosure.
- Credit in the advisory unless you ask to stay anonymous.

## Scope

In scope:

- the desktop application in this repository;
- the website in `website/`;
- GitHub Actions workflows and release artifacts;
- the plugin loader and the Android bridge.

Out of scope:

- vulnerabilities in third-party AI providers or their APIs;
- issues that require an already compromised machine or a leaked API key;
- social engineering;
- denial of service caused by intentionally huge local files.

## API keys and local data

JARVIS has no backend. API keys, chats, memory and settings are stored locally
in the Jarvis data folder:

- Windows: `%APPDATA%\Jarvis`
- macOS: `~/Library/Application Support/Jarvis`
- Linux: `~/.local/share/Jarvis` (or `$XDG_DATA_HOME/Jarvis`)

Keys are sent only to the provider you selected. Do not paste keys into issues,
screenshots or reviews. If a key was exposed, revoke it in the provider
dashboard and generate a new one.

## Plugins are trusted code

Plugins run inside the application process with the same permissions as JARVIS.
There is no sandbox yet. Install plugins only from sources you trust and read
the code before putting it into the `plugins` folder. A restricted subprocess
sandbox is on the roadmap.

## Verifying a build

Every release publishes `SHA256SUMS.txt` and GitHub build provenance. See
[`docs/CODE_SIGNING.md`](docs/CODE_SIGNING.md) for exact commands. The binaries
are currently **not** code-signed, so Windows SmartScreen and macOS Gatekeeper
may warn. Hashes and attestations are the honest alternative until an OSS
signing certificate is approved.

## Dependency hygiene

- Dependabot checks pip and GitHub Actions weekly.
- The test workflow runs `pip-audit` against `requirements.txt`.
- `requirements.txt` pins minimum versions; review the diff before upgrading.
