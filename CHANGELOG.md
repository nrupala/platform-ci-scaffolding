# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `SECURITY.md` (private vulnerability reporting route) and `CONTRIBUTING.md`.
- CodeQL workflow analysing the repo's GitHub Actions workflows.
- `TEST-PLAN.md` documenting the self-test as this repo's test evidence.

## [1.0.0] - 2026-11-05

Tagged `v1` — the first public release of the scaffolding kit.

### Added
- Reusable build+test workflow (`.github/workflows/reusable-build-test.yml`):
  one `workflow_call` runs a caller's build and test commands across
  `ubuntu-latest`, `windows-latest`, and `macos-15`, with optional setup
  command, Go setup, and working-directory inputs.
- Copy-in templates: `templates/multi-platform-ci.yml` (the same three-OS
  matrix as an owned workflow) and `templates/macos-e2e-proof.yml`
  (dispatch-only end-to-end proof on a real Apple Silicon runner).
- `examples/aishell-macos-e2e.yml` — the proven instance the kit was distilled
  from, kept verbatim as the reference implementation.
- Self-test workflow (dispatch-only) that proves the reusable workflow on all
  three OS legs — first run 42154594890, completed/success on every leg.
- README with the hard-won runner lessons (macos-15 is the working Apple
  Silicon label; macOS/Windows proofs stay on GitHub-hosted runners; proof
  workflows stay dispatch-only; assert per step and upload transcripts).
