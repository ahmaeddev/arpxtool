#!/usr/bin/env python3
"""CLI level tests — they exercise the shipped build, not its internals.

    python3 tests/test_cli.py [app.apk]

The optional apk is only used for the engine probe test.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "arpxtool_pro.py")
PROBE = os.path.join(ROOT, "verify_flutter_engines.py")

FAILS = []


def check(label, cond, detail=""):
    print(("  ok   " if cond else "  FAIL ") + label + ("" if cond else "  " + str(detail)))
    if not cond:
        FAILS.append(label)


def run(args, timeout=180):
    p = subprocess.run([sys.executable] + args, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout + p.stderr


def main():
    print("self check")
    rc, out = run([TOOL, "--self-check"])
    ticks = out.count("✓")
    crosses = out.count("✗")
    check("exit code is 0", rc == 0, rc)
    check("34 checks pass", ticks == 34, "%d ticks" % ticks)
    check("no failing check", crosses == 0, crosses)

    print("cli surface")
    rc, out = run([TOOL, "--help"])
    check("help exits 0", rc == 0, rc)
    for flag in ("--flutter-engine", "--remove-license", "-m", "-i"):
        check("help mentions %s" % flag, flag in out)

    print("engine probe")
    rc, out = run([PROBE])
    check("probe without arguments prints usage", rc == 2, rc)

    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        rc, out = run([PROBE, sys.argv[1]], timeout=300)
        check("probe runs on the apk", rc in (0, 1), rc)
        print(out.strip()[-400:])

    print()
    if FAILS:
        print("%d test(s) failed" % len(FAILS))
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
