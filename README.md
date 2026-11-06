# Platform CI Scaffolding

Reusable GitHub Actions scaffolding for proving our software actually runs on
**Windows, macOS, and Linux** — not just that it compiles. Born from the
aishell certification round (2026-11-05), where a GitHub-hosted macOS runner
provided a genuine Apple Silicon execution proof for a product whose owner has
no Mac hardware and no Apple Developer licence.

## What's here

| Path | What it is |
|---|---|
| `.github/workflows/reusable-build-test.yml` | A **reusable workflow** (`workflow_call`) any of our repos can invoke: build + test across `ubuntu-latest`, `windows-latest`, and `macos-15` in one matrix call. |
| `templates/multi-platform-ci.yml` | A copy-in CI workflow for repos that prefer to own their file: same three-OS matrix on push/PR. |
| `templates/macos-e2e-proof.yml` | A copy-in, **manually dispatched** end-to-end proof for macOS: builds natively on a real Apple Silicon runner, runs your repo's `scripts/macos-e2e.sh`, and uploads the session logs as an artifact. |
| `examples/aishell-macos-e2e.yml` | The proven instance this kit was distilled from — aishell's live workflow, kept verbatim as the reference implementation (it also lives on aishell's `main`). |

## Use the reusable workflow (no copying)

In any repo, add a caller workflow:

```yaml
name: Platform tests
on: [push, workflow_dispatch]
jobs:
  platform:
    uses: nrupala/platform-ci-scaffolding/.github/workflows/reusable-build-test.yml@v1
    with:
      setup-command: ""                 # optional, runs first on every OS
      build-command: "go build ./..."   # your build, bash syntax
      test-command: "go test ./..."     # your tests, bash syntax
      # go-version: "1.23"              # optional: set up Go first
      # working-directory: "."          # optional
```

Commands run under `bash` on every OS (Git Bash on Windows). Keep them
portable, or move OS-specific logic into a script in your repo and call that.

## Use the macOS E2E proof template

1. Copy `templates/macos-e2e-proof.yml` to your repo's `.github/workflows/`.
2. Set the three `env` values at the top (`DEPS_COMMAND`, `BUILD_COMMAND`,
   and where your E2E script writes logs).
3. Give your repo a `scripts/macos-e2e.sh` that runs the real product
   end-to-end and writes transcripts into `e2e-logs/`. Every leg should
   assert, not just run — a step that cannot fail is not a proof.
4. Run it from the Actions tab (it is dispatch-only, so it never burns
   minutes uninvited).

## Hard-won lessons (read before editing)

- **`macos-14` jobs are cancelled ~1 second after creation on this account**
  (no steps, no logs). `macos-13` only queues. **`macos-15` is the working
  label** — it is a real Apple Silicon (arm64) runner. Verified 2026-11-05
  with a probe workflow across four labels.
- **macOS and Windows proofs must stay on GitHub-hosted runners.** The
  fleet's standing rule sends feasible PR checks to the self-hosted Aetheris
  runner to save hosted minutes, but release/deploy workflows and required
  macOS/Windows jobs stay hosted — there is no self-hosted Mac, and that is
  the entire point of this kit.
- **Keep proof workflows dispatch-only** unless a branch push is the test.
  A macOS E2E run with a real model download takes ~15 minutes; don't let
  every push trigger one.
- **Assert per step, upload transcripts always.** Split the E2E into named
  steps with `if: always()` on the later ones, so one failure doesn't hide
  the evidence of the legs that never ran, and upload the logs as an
  artifact even on failure.
- **Downloading an Actions artifact through the API:** the artifact-zip
  endpoint answers with a redirect to a signed URL; the signed URL rejects
  requests that still carry your API authorization header (Azure 401).
  Follow the redirect *without* the auth header.
- **Hosted minutes are a real budget** on this account (the macOS multiplier
  is 10x). Proofs are occasional and deliberate, not per-commit.

## Provenance

- Distilled from `nrupala/aishell` (`.github/workflows/macos-e2e.yml`,
  merged 2026-11-05, PR #4), which certified aishell v1.0.3 on a real
  Apple Silicon runner: full run green, including macOS `sandbox-exec`
  denying a confirmed write live. Gate pack:
  `~/workspace/aishell-release-prep/GATE-PACK-2026-11-05.md` (fleet-local).

## Licence

Apache-2.0, © 2351485 ALBERTA INC. Use it in every repo we own.
