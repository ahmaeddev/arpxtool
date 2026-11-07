#!/usr/bin/env python3
"""Check whether a libflutter.so (or an APK) can be TLS-patched, and how.

    python3 verify_flutter_engines.py app.apk
    python3 verify_flutter_engines.py lib/armeabi-v7a/libflutter.so

For every engine it prints the architecture, which BoringSSL function matched,
the file offset and the value the stub returns — or says plainly that the build
is not covered. Nothing is modified: this is a dry run.

Self contained on purpose: it shares no code with the tool, so it can be used
to cross-check the tool's own result.
"""
import os
import re
import struct
import sys
import zipfile

# the four validated signatures (nibble wildcards: 'F' = high nibble wildcard,
# '.' = any nibble). One site per engine, checked against 36 real builds.
PATTERNS = {
    "arm64-v8a": [
        ("F. 0F 1C F8 F. 5. 01 A9 F. 5. 02 A9 F. .. 03 A9 .. .. .. .. 68 1A 40 F9", 0, "ssl_verify_peer_cert"),
        ("FF 43 01 D1 FE 67 01 A9 F8 5F 02 A9 F6 57 03 A9 F4 4F 04 A9 13 00 40 F9", 0, "ssl_verify_peer_cert"),
        ("FF 43 01 D1 FE 67 01 A9 .. .. 06 94 .. 7. 06 94 68 1A 40 F9 15 15 41 F9", 1, "ssl_crypto_x509_session_verify_cert_chain"),
    ],
    "armeabi-v7a": [
        ("2D E9 F. 4. D0 F8 00 80 81 46 D8 F8 18 00 D0 F8", 0, "ssl_verify_peer_cert"),
    ],
    "x86_64": [
        ("55 41 57 41 56 41 55 41 54 53 50 49 89 FE 48 8B 1F 48 8B 43 30 4C 8B B8 D0 01 00 00", 0, "ssl_verify_peer_cert"),
        ("55 41 57 41 56 41 55 41 54 53 48 83 EC 18 49 89 FF 48 8B 1F 48 8B 43 30 4C 8B A0 28 02 00 00", 0, "ssl_verify_peer_cert"),
        ("55 41 57 41 56 41 55 41 54 53 48 83 EC 38 C6 02 50 48 8B AF .. 00 00 00 48 85 ED 74", 1, "ssl_crypto_x509_session_verify_cert_chain"),
    ],
}

STUB = {"armeabi-v7a": b"\x00\x20\x70\x47", "arm64-v8a": b"\x00\x00\x80\xd2\xc0\x03\x5f\xd6"}


def compile_pattern(text):
    parts = []
    for tok in text.split():
        if tok == "..":
            parts.append(b".")
            continue
        hi, lo = tok[0], tok[1]
        hs = b"." if hi == "F" else re.escape(hi.encode())
        ls = b"." if lo == "." else re.escape(lo.encode())
        parts.append(hs + ls)
    return re.compile(b"".join(parts), re.DOTALL)


def elf_abi(data):
    if len(data) < 20 or data[:4] != b"\x7fELF":
        return None
    bits = 64 if data[4] == 2 else 32
    machine = struct.unpack_from("<H", data, 18)[0]
    if machine == 40 and bits == 32:
        return "armeabi-v7a"
    if machine == 183 and bits == 64:
        return "arm64-v8a"
    if machine == 62 and bits == 64:
        return "x86_64"
    if machine == 3 and bits == 32:
        return "x86"
    return None


def probe(data, abi):
    """[(offset, function, ret)] or [] when no signature matches."""
    hits = []
    for text, ret, name in PATTERNS.get(abi, []):
        for m in compile_pattern(text).finditer(data):
            hits.append((m.start(), name, ret))
    seen, out = set(), []
    for off, name, ret in sorted(hits):
        if off in seen:
            continue
        seen.add(off)
        out.append((off, name, ret))
    return out


def engines(target):
    p = target
    if os.path.isfile(p) and p.lower().endswith((".apk", ".apks", ".xapk")):
        found = []
        with zipfile.ZipFile(p) as z:
            for name in z.namelist():
                if name.endswith("/libflutter.so"):
                    found.append((name, z.read(name)))
        return found
    if os.path.isfile(p):
        return [(p, open(p, "rb").read())]
    found = []
    for root, _dirs, files in os.walk(p):
        for f in files:
            if f == "libflutter.so":
                full = os.path.join(root, f)
                found.append((full, open(full, "rb").read()))
    return found


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    found = engines(sys.argv[1])
    if not found:
        print("no libflutter.so found in", sys.argv[1])
        return 3
    bad = 0
    for label, data in found:
        abi = elf_abi(data)
        if not abi:
            print("%-46s ?  unknown elf machine" % label)
            bad += 1
            continue
        if abi not in PATTERNS:
            print("%-46s ✗  no signature table for %s" % (label, abi))
            bad += 1
            continue
        hits = probe(data, abi)
        if not hits:
            print("%-46s ✗  no signature match · this engine build is not covered" % label)
            bad += 1
            continue
        for off, name, ret in hits:
            print("%-46s ✓  %-42s 0x%-8x returns %d" % (label, name, off, ret))
        if len(hits) > 1:
            print("%-46s !  %d sites matched · the tool would refuse this engine"
                  % ("", len(hits)))
            bad += 1
    print()
    if bad:
        print("%d engine(s) could not be matched" % bad)
        return 1
    print("all engines matched · exactly one site each")
    return 0


if __name__ == "__main__":
    sys.exit(main())
