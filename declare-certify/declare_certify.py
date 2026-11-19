#!/usr/bin/env python3
"""declare_certify.py — declare -> certify for release pipelines.

The pattern: a release is *declared* before anything ships and
*certified* after the pipeline's own proof legs complete, and the
record of those two acts travels with the pipeline (in GitHub Actions:
as a workflow artifact between jobs). A release whose declaration is
still OPEN is not certified, and a guard step fails the workflow so it
cannot be published.

Contract:
- `declare` writes a declaration record (state OPEN) naming the target,
  version, base, and the gate-verdict file that authorises the release.
  Declare refuses to open if the gate-verdict file is not on disk —
  no verdict, no release.
- `certify` closes the record (state CLOSED) with an evidence file's
  path + sha256. Certify refuses without evidence on disk, and refuses
  to close twice.
- `check` exits 2 while any matching declaration is OPEN.

Records live in ./.declare-certify/<id>.json (override the directory
with the DECLARE_CERTIFY_DIR environment variable).

Usage:
  declare_certify.py declare --target T --version V --base B \
      --gate-verdict FILE [--id ID]
  declare_certify.py certify --id ID --evidence FILE [--note TEXT]
  declare_certify.py check [--id ID]
  declare_certify.py --self-test

Exit codes: 0 ok - 2 refused / open declaration found - 1 usage error.
Stdlib only. No network. Never deploys anything itself.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid

DEFAULT_DIR = os.path.join(os.getcwd(), ".declare-certify")


def state_dir():
    return os.environ.get("DECLARE_CERTIFY_DIR", DEFAULT_DIR)


def record_path(decl_id):
    return os.path.join(state_dir(), f"{decl_id}.json")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_record(decl_id):
    p = record_path(decl_id)
    if not os.path.isfile(p):
        return None
    with open(p) as f:
        return json.load(f)


def save_record(rec):
    os.makedirs(state_dir(), exist_ok=True)
    tmp = record_path(rec["id"]) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(rec, f, indent=2)
    os.replace(tmp, record_path(rec["id"]))


def cmd_declare(args):
    if not os.path.isfile(args.gate_verdict):
        print(f"REFUSED: gate verdict file not found: {args.gate_verdict}")
        return 2
    decl_id = args.id or (
        f"{args.target}-{args.version}-{time.strftime('%Y%m%dT%H%M%S')}"
        f"-{uuid.uuid4().hex[:6]}")
    if load_record(decl_id) is not None:
        print(f"REFUSED: declaration already exists: {decl_id}")
        return 2
    rec = {
        "id": decl_id,
        "target": args.target,
        "version": args.version,
        "base": args.base,
        "gate_verdict_file": os.path.abspath(args.gate_verdict),
        "gate_verdict_sha256": sha256_file(args.gate_verdict),
        "declared_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "state": "OPEN",
    }
    save_record(rec)
    print(f"DECLARED {decl_id} (state OPEN) -> {record_path(decl_id)}")
    return 0


def cmd_certify(args):
    rec = load_record(args.id)
    if rec is None:
        print(f"REFUSED: no such declaration: {args.id}")
        return 2
    if rec["state"] != "OPEN":
        print(f"REFUSED: declaration {args.id} is already {rec['state']}")
        return 2
    if not os.path.isfile(args.evidence):
        print(f"REFUSED: evidence file not found: {args.evidence} "
              f"(certification requires evidence on disk)")
        return 2
    rec["state"] = "CLOSED"
    rec["certified_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    rec["evidence_file"] = os.path.abspath(args.evidence)
    rec["evidence_sha256"] = sha256_file(args.evidence)
    if args.note:
        rec["certify_note"] = args.note
    save_record(rec)
    print(f"CERTIFIED {args.id} (state CLOSED, evidence sha256 "
          f"{rec['evidence_sha256'][:12]}...)")
    return 0


def cmd_check(args):
    if args.id:
        rec = load_record(args.id)
        if rec is None:
            print(f"UNKNOWN declaration: {args.id}")
            return 2
        print(f"{args.id}: {rec['state']}")
        return 0 if rec["state"] == "CLOSED" else 2
    d = state_dir()
    open_recs = []
    if os.path.isdir(d):
        for name in sorted(os.listdir(d)):
            if name.endswith(".json"):
                with open(os.path.join(d, name)) as f:
                    rec = json.load(f)
                if rec.get("state") == "OPEN":
                    open_recs.append(rec["id"])
    if open_recs:
        print("OPEN declarations (uncertified deploys = findings):")
        for oid in open_recs:
            print(f"  {oid}")
        return 2
    print("no OPEN declarations")
    return 0


def self_test():
    ok = True

    def check(name, cond):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL'}: {name}")
        ok = ok and cond

    me = os.path.abspath(__file__)
    with tempfile.TemporaryDirectory() as td:
        env = dict(os.environ, DECLARE_CERTIFY_DIR=td)

        def cli(*a):
            return subprocess.run([sys.executable, me, *a],
                                  capture_output=True, text=True, env=env)

        verdict = os.path.join(td, "verdict.md")
        with open(verdict, "w") as f:
            f.write("gate verdict: PASS WITH FINDINGS\n")
        evidence = os.path.join(td, "evidence.txt")
        with open(evidence, "w") as f:
            f.write("live proof: e2e 16/16, https 302\n")

        p = cli("declare", "--target", "widget", "--version", "1.2.3",
                "--base", "abc123", "--gate-verdict", verdict,
                "--id", "test-1")
        check("declare writes an OPEN record", p.returncode == 0
              and os.path.isfile(os.path.join(td, "test-1.json")))
        p = cli("declare", "--target", "widget", "--version", "1.2.3",
                "--base", "abc123", "--gate-verdict",
                os.path.join(td, "missing.md"), "--id", "test-2")
        check("declare refuses a missing gate verdict", p.returncode == 2)
        p = cli("check", "--id", "test-1")
        check("check flags the OPEN declaration (exit 2)",
              p.returncode == 2)
        p = cli("certify", "--id", "test-1", "--evidence",
                os.path.join(td, "nope.txt"))
        check("certify refuses missing evidence", p.returncode == 2)
        p = cli("certify", "--id", "test-1", "--evidence", evidence,
                "--note", "self-test")
        check("certify closes with evidence on disk", p.returncode == 0)
        with open(os.path.join(td, "test-1.json")) as f:
            rec = json.load(f)
        check("record carries evidence sha256",
              rec["state"] == "CLOSED"
              and rec["evidence_sha256"] == sha256_file(evidence))
        p = cli("certify", "--id", "test-1", "--evidence", evidence)
        check("double certify is refused", p.returncode == 2)
        p = cli("check", "--id", "test-1")
        check("check passes once CLOSED (exit 0)", p.returncode == 0)
        p = cli("check")
        check("check finds no OPEN declarations", p.returncode == 0)
    print("SELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--self-test", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    d = sub.add_parser("declare")
    d.add_argument("--target", required=True)
    d.add_argument("--version", required=True)
    d.add_argument("--base", required=True)
    d.add_argument("--gate-verdict", required=True)
    d.add_argument("--id")
    c = sub.add_parser("certify")
    c.add_argument("--id", required=True)
    c.add_argument("--evidence", required=True)
    c.add_argument("--note")
    k = sub.add_parser("check")
    k.add_argument("--id")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if args.cmd == "declare":
        return cmd_declare(args)
    if args.cmd == "certify":
        return cmd_certify(args)
    if args.cmd == "check":
        return cmd_check(args)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
