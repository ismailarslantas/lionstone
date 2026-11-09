# Security policy

Lionstone runs on your computer and edits your own media. Nothing is uploaded, there is no
telemetry and no account. This page says what we protect, how to report a problem and how
to check that a release really comes from this repository.

## Supported versions

| Version | Security fixes |
|---|---|
| 1.0.x | ✅ |
| < 1.0 | ❌ (please upgrade; older releases were retired when 1.0.0 shipped) |

## Reporting a vulnerability

Please report privately through GitHub: **Security → Report a vulnerability**
([private advisory](https://github.com/ismailarslantas/lionstone/security/advisories/new)).
Do not open a public issue.

* We reply within **3 working days** and agree a fix date with you.
* Critical issues (code execution, path traversal, credential exposure) get a fix or a
  mitigation within **14 days**, then a GitHub Security Advisory and a CVE when it applies.
* We credit reporters in the advisory unless you prefer to stay anonymous.
* Good-faith research that respects users' data and stops at a proof of concept is welcome,
  and we will not take legal action over it.

## What Lionstone does on the network

| When | What | Protection |
|---|---|---|
| Transcription (opt-in, `lionstone[whisper]`) | downloads a Whisper model once | from the model publisher over HTTPS |
| Motion FX person matte (`lionstone[vision]`) | downloads `u2netp.onnx` (4.6 MB) once from the rembg GitHub release | **pinned SHA-256**; a file that does not match is deleted and refused |
| LLM features you enable with your own API key | calls that provider | your key stays in your environment, never written to plans or logs |

Media, transcripts, plans and mattes stay on your disk (mattes in your user config folder).

## How we handle untrusted input

Lionstone opens media files you give it with FFmpeg. Keep FFmpeg up to date: most media
parser bugs are fixed there.

* FFmpeg runs as a separate process with an argument list (no shell). User text (titles,
  captions, effect text) is written to files and passed with `textfile=`, never pasted into a
  filtergraph; drawtext expansion is off for effect text.
* Temporary files go to private per-process folders (`mkdtemp`, mode 0700) and are removed
  when Lionstone exits.
* Effect parameters are typed and range-checked; unknown parameters and invalid values are
  rejected, never guessed.
* The OpenMontage integration calls the `lionstone` command as a separate process; no code
  from either project is loaded into the other.

## Supply chain

* **CodeQL code scanning** (GitHub default setup: Python, JavaScript/TypeScript and Actions) on every push and pull request.
* **OpenSSF Scorecard** weekly, results in the Security tab and the README badge.
* **Dependabot** for Python, npm (Remotion) and GitHub Actions.
* GitHub Actions are **pinned to commit SHAs** and run with **read-only tokens** by default.
* Releases are built by GitHub Actions from a tag, with **SHA256SUMS** and a **build
  provenance attestation** (SLSA, signed with Sigstore).

### Verify a release

```bash
# download the wheel and SHA256SUMS from the release page, then:
sha256sum -c SHA256SUMS --ignore-missing
gh attestation verify lionstone-1.0.0-py3-none-any.whl --repo ismailarslantas/lionstone
```

A file that fails either check did not come from this repository: do not install it.
