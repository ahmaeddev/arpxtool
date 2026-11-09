#!/usr/bin/env python3
"""End-to-end test of the in-archive network-security-config injection."""
import struct
import sys
import zipfile
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import arpxtool as A


def manifest(ref=True):
    """Binary manifest with android:networkSecurityConfig on <application>."""
    strings = []

    def intern(s):
        if s not in strings:
            strings.append(s)
        return strings.index(s)

    body = bytearray()
    # <manifest package="chat.agent.ah">
    attrs = struct.pack("<IIIHBBI", 0xFFFFFFFF, intern("package"), intern("chat.agent.ah"),
                        8, 0, 0x03, intern("chat.agent.ah"))
    ext = struct.pack("<IIHHHHHH", 0xFFFFFFFF, intern("manifest"), 20, 20, 1, 0, 0, 0)
    body += struct.pack("<HHIII", 0x0102, 16, 16 + len(ext) + len(attrs), 1, 0xFFFFFFFF) + ext + attrs
    # <application android:networkSecurityConfig="@xml/network_security_config">
    if ref:
        val = struct.pack("<IIIHBBI", 0xFFFFFFFF, intern("networkSecurityConfig"),
                          intern("@xml/network_security_config"), 8, 0, 0x01, 0x7F130001)
    else:
        val = struct.pack("<IIIHBBI", 0xFFFFFFFF, intern("networkSecurityConfig"),
                          intern("@xml/network_security_config"), 8, 0, 0x03,
                          intern("@xml/network_security_config"))
    ext = struct.pack("<IIHHHHHH", 0xFFFFFFFF, intern("application"), 20, 20, 1, 0, 0, 0)
    body += struct.pack("<HHIII", 0x0102, 16, 16 + len(ext) + len(val), 1, 0xFFFFFFFF) + ext + val
    for tag in ("application", "manifest"):
        body += struct.pack("<HHIIIII", 0x0103, 16, 24, 1, 0xFFFFFFFF, 0xFFFFFFFF, intern(tag))
    pool = A.build_string_pool(strings)
    return struct.pack("<HHI", 0x0003, 8, 8 + len(pool) + len(body)) + pool + bytes(body)


def nsc_with_pinset():
    nodes = [("start", "network-security-config", []),
             ("start", "base-config", [("cleartextTrafficPermitted", 0x12, 0)]),
             ("start", "trust-anchors", []),
             ("start", "certificates", [("src", 0x03, "system")]),
             ("end", "certificates", []),
             ("end", "trust-anchors", []),
             ("end", "base-config", []),
             ("start", "domain-config", []),
             ("start", "pin-set", [("expiration", 0x03, "2027-01-01")]),
             ("start", "pin", [("digest", 0x03, "SHA-256")]),
             ("end", "pin", []),
             ("end", "pin-set", []),
             ("end", "domain-config", []),
             ("end", "network-security-config", [])]
    return A._axml_document(nodes)


def build_apk(path, ref=True, with_nsc=True):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("AndroidManifest.xml", manifest(ref))
        if with_nsc:
            zi = zipfile.ZipInfo("res/xml/network_security_config.xml")
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, nsc_with_pinset())
        z.writestr("classes.dex", b"dex\n035\x00" + b"\x00" * 100)


FAILS = []


def check(name, cond, extra=""):
    print(("  ok   " if cond else "  FAIL ") + name + ("" if cond else "  " + str(extra)))
    if not cond:
        FAILS.append(name)


print("manifest_attr_raw")
m = manifest(True)
check("reference attribute returns the raw string",
      A.manifest_attr_raw(m, "application", "networkSecurityConfig") == "@xml/network_security_config",
      A.manifest_attr_raw(m, "application", "networkSecurityConfig"))

print("inject_netsec · rewrites the app's own config")
for label, ref, with_nsc in (("reference", True, True), ("string", False, True), ("no-nsc", True, False)):
    path = "/tmp/netsec_%s.apk" % label
    build_apk(path, ref=ref, with_nsc=with_nsc)
    entry = A.nsc_entry(path)
    status, detail = A.inject_netsec(path)
    print("   %-10s entry=%r status=%s\n              %s" % (label, entry, status, detail))
    if label == "no-nsc":
        check("missing config is reported", status == "absent" and entry is None)
        continue
    check("%s · entry found" % label, entry == "res/xml/network_security_config.xml")
    check("%s · rewritten" % label, status == "replaced", status)
    with zipfile.ZipFile(path) as z:
        blob = z.read("res/xml/network_security_config.xml")
    x = A.Axml(blob)
    check("%s · still parses" % label, x.valid, x.elements[:3])
    check("%s · root intact" % label, x.elements[:1] == ["network-security-config"], x.elements)
    check("%s · pin-set removed" % label, "pin-set" not in x.elements, x.elements)
    check("%s · domain-config removed" % label, "domain-config" not in x.elements, x.elements)
    check("%s · system anchor kept" % label,
          any(a[2] == "src" and a[3] == "system" for a in x.attrs), x.attrs)
    check("%s · user anchor added" % label,
          any(a[2] == "src" and a[3] == "user" for a in x.attrs), x.attrs)
    check("%s · two certificates elements" % label, x.elements.count("certificates") == 2, x.elements)
    check("%s · user anchor overrides pins" % label,
          any(a[2] == "overridePins" and a[3] == "true" for a in x.attrs), x.attrs)
    check("%s · cleartext forced on" % label,
          any(a[1] == "base-config" and a[2] == "cleartextTrafficPermitted" and a[3] == "true"
              for a in x.attrs), x.attrs)
    os.unlink(path)

print()
print("FAILED: %d" % len(FAILS) if FAILS else "ALL PASS")
sys.exit(1 if FAILS else 0)
