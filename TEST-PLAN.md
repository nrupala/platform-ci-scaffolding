# Test plan — platform-ci-scaffolding

## Scope

This repo is reusable GitHub Actions scaffolding: a reusable build+test workflow
(matrix: Ubuntu, Windows, macOS), two copy-in templates, and one worked example.
The "product" is workflow behaviour, so the test evidence is a real execution of
the reusable workflow on all three operating systems — not a unit suite. Out of
scope: the correctness of any caller repo's own build/test commands.

## Suites

| Suite | Covers | Run it | Runs in CI |
|---|---|---|---|
| Self-test (reusable workflow) | Calls `.github/workflows/reusable-build-test.yml` with trivial build/test commands (`echo BUILD_OK && uname -a`, `echo TEST_OK`) on `ubuntu-latest`, `windows-latest`, and `macos-15`; every leg must complete green | Dispatch from the Actions tab: **Self-test (reusable workflow) → Run workflow** (dispatch-only by design — hosted minutes, macOS at a 10x multiplier, are a real budget; see README) | It is itself a workflow; evidence: run **42154594890** (2026-11-05), completed/success on all three OS legs |

## CI gates

- A change to the reusable workflow is proven by a fresh green Self-test dispatch
  before merge (per CONTRIBUTING).
- CodeQL (`actions` language) runs on push, pull request, and weekly over the
  workflow definitions themselves.

## Cadence

- On demand (dispatch): Self-test after any change to the reusable workflow.
- Every push / pull request / weekly: CodeQL.
- Every release candidate: the release-readiness run (checker + evidence reads),
  per the house Release-Readiness Standard.

## Coverage bar

No numeric floor; new functionality lands with tests per CONTRIBUTING — for this
repo that means a Self-test leg or template proof that exercises it for real.
