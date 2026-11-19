#!/usr/bin/env bash
# Self-test for the declare-certify actions: simulates the GitHub Actions
# job chain locally with the real declare_certify.py.
#
# Two separate store directories stand in for two separate runners
# (the gate job and the certification job); the declaration record is
# carried between them by a plain copy, exactly what the artifact
# upload/download steps in the actions do.
#
# Proves the three behaviours the actions exist for:
#   1. declare opens a record in the gate job and the record travels.
#   2. certify (in a later job) closes it against evidence on disk.
#   3. the guard fails the job while the declaration is OPEN, so a
#      publish/tag step that needs the guard can never run uncertified.
# Plus the fail-closed refusals: no gate verdict -> no declaration;
# no evidence -> no certification; no double certification.
#
# Usage: bash declare-certify/self-test.sh   (exit 0 = all pass)
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
DC="python3 $HERE/declare_certify.py"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
JOB_A="$WORK/job-a"   # the gate job's runner
JOB_B="$WORK/job-b"   # the certification job's runner
mkdir -p "$JOB_A" "$JOB_B"
FAILURES=0

expect() { # expect <label> <wanted-exit> <actual-exit>
  if [ "$2" -eq "$3" ]; then
    echo "PASS: $1"
  else
    echo "FAIL: $1 (wanted exit $2, got $3)"
    FAILURES=$((FAILURES + 1))
  fi
}

echo "gate verdict: PASS (self-test fixture)" > "$WORK/verdict.md"
echo "release proof: binaries built, hashes recorded" > "$WORK/evidence.txt"

# The module's own self-test first.
$DC --self-test > /dev/null 2>&1
expect "module self-test" 0 $?

# 1. Gate job: declare refuses without a gate verdict on disk.
DECLARE_CERTIFY_DIR="$JOB_A" $DC declare --target widget --version v1.0.0 \
  --base abc123 --gate-verdict "$WORK/missing.md" --id widget-v1.0.0 > /dev/null 2>&1
expect "declare refuses a missing gate verdict" 2 $?

# 1b. Gate job: declare opens the record.
DECLARE_CERTIFY_DIR="$JOB_A" $DC declare --target widget --version v1.0.0 \
  --base abc123 --gate-verdict "$WORK/verdict.md" --id widget-v1.0.0 > /dev/null 2>&1
expect "declare opens an OPEN record" 0 $?
[ -f "$JOB_A/widget-v1.0.0.json" ]
expect "record exists in the gate job's store" 0 $?

# Artifact carry: gate job -> certification job (upload/download in CI).
cp "$JOB_A/widget-v1.0.0.json" "$JOB_B/widget-v1.0.0.json"

# 3. Guard before certification: the publish job would fail here.
DECLARE_CERTIFY_DIR="$JOB_B" $DC check --id widget-v1.0.0 > /dev/null 2>&1
expect "guard blocks while the declaration is OPEN" 2 $?

# 2. Certification job: certify refuses without evidence on disk.
DECLARE_CERTIFY_DIR="$JOB_B" $DC certify --id widget-v1.0.0 \
  --evidence "$WORK/nope.txt" > /dev/null 2>&1
expect "certify refuses missing evidence" 2 $?

# 2b. Certify closes the record against the evidence.
DECLARE_CERTIFY_DIR="$JOB_B" $DC certify --id widget-v1.0.0 \
  --evidence "$WORK/evidence.txt" --note "self-test chain" > /dev/null 2>&1
expect "certify closes the declaration" 0 $?

# 2c. The closed record carries the evidence hash.
python3 - "$JOB_B/widget-v1.0.0.json" "$WORK/evidence.txt" <<'PYEOF'
import hashlib, json, sys
rec = json.load(open(sys.argv[1]))
want = hashlib.sha256(open(sys.argv[2], "rb").read()).hexdigest()
sys.exit(0 if rec["state"] == "CLOSED" and rec["evidence_sha256"] == want else 1)
PYEOF
expect "closed record carries the evidence sha256" 0 $?

# 2d. No double certification.
DECLARE_CERTIFY_DIR="$JOB_B" $DC certify --id widget-v1.0.0 \
  --evidence "$WORK/evidence.txt" > /dev/null 2>&1
expect "double certify is refused" 2 $?

# 3b. Guard after certification: the publish job may proceed.
DECLARE_CERTIFY_DIR="$JOB_B" $DC check --id widget-v1.0.0 > /dev/null 2>&1
expect "guard passes once the declaration is CLOSED" 0 $?

if [ "$FAILURES" -eq 0 ]; then
  echo "SELF-TEST: PASS (declare -> artifact carry -> guard -> certify chain)"
  exit 0
fi
echo "SELF-TEST: FAIL ($FAILURES failing checks)"
exit 1
