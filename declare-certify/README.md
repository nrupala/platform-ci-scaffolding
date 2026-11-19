# Declare → Certify for release workflows

A release pipeline pattern: **declare** the release before anything
ships, **certify** it after the pipeline's own proof legs, and let the
record travel between jobs as a workflow artifact. A job that publishes
or tags the release guards on the record — while the declaration is
still OPEN, the guard fails and the release cannot be published.

Born from a simple failure shape: the deploy finished, certification
was somebody's next manual step, and it silently didn't happen. A step
built into the pipeline cannot be forgotten, because the pipeline does
not complete without it.

## The pieces

| Path | What it is |
|---|---|
| `declare_certify.py` | The shared module (stdlib-only Python, no network). `declare` / `certify` / `check` subcommands; `--self-test` proves its own contract. |
| `declare/action.yml` | Composite action for the gate job: runs `declare` and uploads the record as an artifact. Refuses when the gate-verdict file is missing. |
| `certify/action.yml` | Composite action for the certification job: downloads the record, runs `certify` against an evidence file, verifies it reads CLOSED, uploads the closed record as an artifact. |
| `guard/action.yml` | Composite action for the publish job: downloads a record artifact and fails the job while the declaration is OPEN. |
| `self-test.sh` | Local proof of the whole chain across two simulated runners (see below). |

## The job chain

```yaml
jobs:
  declare:                       # the gate job
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Write the gate verdict
        run: ./scripts/gate.sh > gate-verdict.md   # your gate; its file authorises the release
      - uses: nrupala/platform-ci-scaffolding/declare-certify/declare@v1
        with:
          target: my-product
          version: ${{ github.ref_name }}
          base: ${{ github.sha }}
          gate-verdict: gate-verdict.md

  build:                         # your existing build jobs
    needs: declare
    # ... build as usual; write an evidence file (hashes, proof log)
    # and upload it with the build artifacts.

  certify:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4   # fetch the build evidence
        with: { name: build-artifacts }
      - uses: nrupala/platform-ci-scaffolding/declare-certify/certify@v1
        with:
          declaration-id: my-product-${{ github.ref_name }}
          evidence: release-evidence.txt

  publish:                       # the job that tags / uploads the release
    needs: certify
    runs-on: ubuntu-latest
    steps:
      - uses: nrupala/platform-ci-scaffolding/declare-certify/guard@v1
        with:
          declaration-id: my-product-${{ github.ref_name }}
      # ... publish steps; unreachable while the declaration is OPEN.
```

The declaration id defaults to `<target>-<version>` in the declare
action; pass the same id to certify and guard.

## Prove it locally

```bash
bash declare-certify/self-test.sh
```

The script runs the module's own self-test, then simulates two runners
with two store directories: declare in the first, the record carried by
copy (what the artifact steps do), the guard failing on the OPEN
record, certify closing it against evidence, and the guard passing.
Exit 0 means the whole chain behaved. The repo's
`Self-test (declare-certify)` workflow runs the same script on a
GitHub runner (dispatch-only).

## Contract details

- Declare refuses a missing gate-verdict file — no verdict, no release.
- Certify refuses missing evidence and refuses to close twice; the
  record stores the evidence path + SHA-256.
- `check --id <id>` exits 2 while the declaration is OPEN, 0 once
  CLOSED. That exit code is the whole guard.
- Records are plain JSON in a store directory (`DECLARE_CERTIFY_DIR`
  overrides the `./.declare-certify` default); the artifact steps move
  that directory's record between jobs.
