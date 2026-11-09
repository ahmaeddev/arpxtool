#!/usr/bin/env python3
"""Regression tests for the dex-integrity guards in arpxtool.py.

Run:  python3 test_dex_integrity.py        (exit 0 = everything still holds)

What it locks down:
  * a code_item must keep its exact length when a method body is stubbed,
    otherwise ART rejects the whole dex at load time and the app dies at
    launch with ClassNotFoundException (the classes10.dex failure);
  * dex_validate() must catch a shortened insns_size, a dropped tries_size,
    non-zero section padding and a stale header;
  * the archive-level audit must surface a rejected dex through apk_lint()
    and install_check(), so it can never reach a signed build unnoticed.
"""
import hashlib
import struct
import os
import sys
import zipfile
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import arpxtool as A

FAILS = []


def check(name, cond, extra=""):
    print(("  ok   " if cond else "  FAIL ") + name + ("" if cond else "  " + str(extra)))
    if not cond:
        FAILS.append(name)


# ── dex builders ────────────────────────────────────────────────────────────
def code_item(insns_size, tries=0):
    out = struct.pack("<HHHHII", 1, 0, 1, tries, 0, insns_size) + b"\x0e\x00" * insns_size
    if tries:
        if insns_size & 1:
            out += b"\x00\x00"
        out += struct.pack("<IHH", 0, insns_size, 0) * tries
        out += b"\x01" + b"\x01\x00\x00"          # 1 handler: size 1, type 0, addr 0
    return out


def seal(buf, map_off):
    buf = bytearray(buf)
    struct.pack_into("<I", buf, 0x20, len(buf))
    struct.pack_into("<I", buf, 0x24, 0x70)
    struct.pack_into("<I", buf, 0x28, 0x12345678)
    struct.pack_into("<I", buf, 0x34, map_off)
    buf[12:32] = hashlib.sha1(bytes(buf[32:])).digest()
    struct.pack_into("<I", buf, 8, zlib.adler32(bytes(buf[12:])) & 0xFFFFFFFF)
    return bytes(buf)


def build(items, map_off=None, pad=b"\x00"):
    body = b"".join(items)
    off = 0x70
    if map_off is None:
        map_off = off + len(body)
    buf = bytearray(b"dex\n035\x00" + b"\x00" * (off - 8) + body)
    while len(buf) < map_off:
        buf += pad
    entries = [(0, 0x0000, 1), (off, 0x2001, len(items)), (map_off, 0x1000, 1)]
    buf += struct.pack("<I", len(entries))
    for o, t, c in entries:
        buf += struct.pack("<HHII", t, 0, c, o)
    return seal(buf, map_off)


def main():
    good = build([code_item(4, tries=1), code_item(4, tries=1)])
    map_off = 0xB8

    print("dex_validate")
    check("clean code_item section passes", A.dex_validate(good) == [], A.dex_validate(good))

    shortened = bytearray(good)
    struct.pack_into("<I", shortened, 0x70 + 12, 1)        # insns_size 4 -> 1
    shortened = seal(shortened, map_off)
    p = A.dex_validate(shortened)
    check("shortened insns_size is reported",
          any(sev in ("bad", "warn") for sev, _ in p), p)
    print("     ->", p[0][1][:90] if p else "nothing")

    dropped = bytearray(good)
    struct.pack_into("<H", dropped, 0x70 + 6, 0)           # tries_size 1 -> 0
    p = A.dex_validate(seal(dropped, map_off))
    check("dropped tries_size is reported", any(sev in ("bad", "warn") for sev, _ in p), p)

    padded = build([code_item(4, tries=1), code_item(4, tries=1)], map_off=0x70 + 72 + 4, pad=b"\xbc")
    p = A.dex_validate(padded)
    check("non-zero padding is reported",
          any("non-zero padding" in m for _s, m in p), p)

    stale = bytearray(good)
    stale[0x40] ^= 0xFF
    p = A.dex_validate(bytes(stale))
    check("stale header is caught",
          any("checksum" in m or "sha1" in m for s, m in p), p)

    print("dex_code_item_end")
    item = code_item(5, tries=2)
    check("walk with tries and an odd insns_size",
          A.dex_code_item_end(b"\x00" * 0x70 + item, 0x70) == 0x70 + len(item))

    print("dex_patch_code keeps every item's shape")
    for kind, units in (("void", 1), ("true", 2), ("null", 2)):
        buf = bytearray(b"\x00" * 0x70 + code_item(6, tries=1))
        off = 0x70
        end_before = A.dex_code_item_end(buf, off)
        insns_before, tries_before = A.u4(buf, off + 12), A.u2(buf, off + 6)
        ok = A.dex_patch_code(buf, off, kind)
        check("%s · stub applied" % kind, ok)
        check("%s · item length unchanged" % kind, A.dex_code_item_end(buf, off) == end_before)
        check("%s · insns_size unchanged" % kind, A.u4(buf, off + 12) == insns_before)
        check("%s · tries_size unchanged" % kind, A.u2(buf, off + 6) == tries_before)
        check("%s · stub in place" % kind,
              bytes(buf[off + 16:off + 16 + units * 2]) == A.CODE_STUBS[kind])
        check("%s · tail filled with nop" % kind,
              bytes(buf[off + 16 + units * 2:off + 16 + insns_before * 2])
              == b"\x00\x00" * (insns_before - units))

    print("stub kind follows the method's return type")
    def uleb(n):
        out = bytearray()
        while True:
            b = n & 0x7F
            n >>= 7
            out.append(b | 0x80 if n else b)
            if not n:
                return bytes(out)

    def mini_dex(strings, types, protos, methods):
        n_s, n_t, n_p, n_m = len(strings), len(types), len(protos), len(methods)
        s_off, t_off = 0x70, 0x70 + 4 * n_s
        p_off, m_off = t_off + 4 * n_t, t_off + 4 * n_t + 12 * n_p
        d_off = m_off + 8 * n_m
        data, offs = bytearray(), []
        for st in strings:
            offs.append(d_off + len(data))
            data += uleb(len(st)) + st.encode() + b"\x00"
        buf = bytearray(d_off + len(data))
        buf[0:8] = b"dex\n035\x00"
        struct.pack_into("<I", buf, 0x20, len(buf))
        struct.pack_into("<I", buf, 0x24, 0x70)
        struct.pack_into("<I", buf, 0x28, 0x12345678)
        struct.pack_into("<I", buf, 0x38, n_s); struct.pack_into("<I", buf, 0x3C, s_off)
        struct.pack_into("<I", buf, 0x40, n_t); struct.pack_into("<I", buf, 0x44, t_off)
        struct.pack_into("<I", buf, 0x48, n_p); struct.pack_into("<I", buf, 0x4C, p_off)
        struct.pack_into("<I", buf, 0x58, n_m); struct.pack_into("<I", buf, 0x5C, m_off)
        for i, o in enumerate(offs):
            struct.pack_into("<I", buf, s_off + 4 * i, o)
        for i, si in enumerate(types):
            struct.pack_into("<I", buf, t_off + 4 * i, si)
        for i, (sh, ret, par) in enumerate(protos):
            struct.pack_into("<III", buf, p_off + 12 * i, sh, ret, par)
        for i, (cls, pr, name) in enumerate(methods):
            struct.pack_into("<HHI", buf, m_off + 8 * i, cls, pr, name)
        buf[d_off:] = data
        return bytes(buf)

    md = mini_dex(["V", "Z", "Ljava/util/List;", "checkServerTrusted", "J"],
                  [0, 1, 2, 4],
                  [(0, 0, 0), (1, 1, 0), (2, 2, 0), (4, 3, 0)],
                  [(0, 0, 3), (0, 1, 3), (0, 2, 3), (0, 3, 3)])
    idx = A.DexIndex(md)
    check("dex index reads protos", idx.ok and idx.p_n == 4)
    check("void method -> return-void", idx.stub_kind(0) == "void", idx.stub_kind(0))
    check("boolean method -> return true", idx.stub_kind(1) == "true", idx.stub_kind(1))
    check("List method -> return null (never return-void)", idx.stub_kind(2) == "null", idx.stub_kind(2))
    check("long method -> wide stub", idx.stub_kind(3) == "wide", idx.stub_kind(3))
    check("unknown method falls back to the requested kind", idx.stub_kind(99, "void") == "void")

    print("host issuers")
    def host_dex():
        st = ["LTest;", "a", "graph.facebook.com", "V"]
        n_s = len(st)
        s_off = 0x70; t_off = s_off + 4 * n_s; p_off = t_off + 8
        m_off = p_off + 12; c_off = m_off + 8; cd_off = c_off + 32
        code_off = (cd_off + 4 + 1 + 1 + 2 + 3) & ~3
        cd = bytes([0, 0, 1, 0]) + uleb(0) + uleb(1) + uleb(code_off)
        code = struct.pack("<HHHHII", 1, 0, 0, 0, 0, 3) + struct.pack("<HHH", 0x001A, 2, 0x000E)
        d_off = code_off + len(code)
        data = bytearray(); offs = []
        for x in st:
            offs.append(d_off + len(data)); data += uleb(len(x)) + x.encode() + b"\x00"
        buf = bytearray(d_off + len(data)); buf[0:8] = b"dex\n035\x00"
        struct.pack_into("<I", buf, 0x20, len(buf)); struct.pack_into("<I", buf, 0x24, 0x70)
        struct.pack_into("<I", buf, 0x28, 0x12345678)
        struct.pack_into("<I", buf, 0x38, n_s); struct.pack_into("<I", buf, 0x3C, s_off)
        struct.pack_into("<I", buf, 0x40, 2); struct.pack_into("<I", buf, 0x44, t_off)
        struct.pack_into("<I", buf, 0x48, 1); struct.pack_into("<I", buf, 0x4C, p_off)
        struct.pack_into("<I", buf, 0x58, 1); struct.pack_into("<I", buf, 0x5C, m_off)
        struct.pack_into("<I", buf, 0x60, 1); struct.pack_into("<I", buf, 0x64, c_off)
        for i, o in enumerate(offs):
            struct.pack_into("<I", buf, s_off + 4 * i, o)
        struct.pack_into("<I", buf, t_off, 0); struct.pack_into("<I", buf, t_off + 4, 3)
        struct.pack_into("<III", buf, p_off, 3, 1, 0)
        struct.pack_into("<HHI", buf, m_off, 0, 0, 1)
        struct.pack_into("<IIIIIIII", buf, c_off, 0, 1, 0, 0, 0, 0, cd_off, 0)
        buf[cd_off:cd_off + len(cd)] = cd
        buf[code_off:code_off + len(code)] = code
        buf[d_off:] = data
        return bytes(buf)

    hd = host_dex()
    refs = A.dex_host_refs(hd)
    check("const-string host is attributed to its class",
          refs.get("graph.facebook.com") == {("LTest;", "a")}, refs)
    check("host regex accepts sdk domains",
          bool(A.HOST_RX.match("firebase-settings.crashlytics.com")))
    check("exact-needle mode matches a literal string",
          A.dex_host_refs(hd, needles={"graph.facebook.com"}).get("graph.facebook.com")
          == {("LTest;", "a")})
    check("exact-needle mode ignores other strings",
          A.dex_host_refs(hd, needles={"/system/etc/security/cacerts"}) == {})

    print("native protection census")
    def native_dex(n_native, n_normal):
        st = ["LTest;", "a", "b", "V"]
        n_s = len(st)
        s_off = 0x70; t_off = s_off + 4 * n_s; p_off = t_off + 4
        m_off = p_off + 12; n_m = n_native + n_normal
        c_off = m_off + 8 * n_m; cd_off = c_off + 32
        head = bytes([0, 0, n_m, 0]) + uleb(0) + uleb(1)
        tail = b"".join(uleb(0) + uleb(0x101 if i < n_native else 1) + uleb(0)
                        for i in range(1, n_m))
        code_off = (cd_off + len(head) + 2 + len(tail) + 3) & ~3
        cd = head + uleb(code_off) + tail
        code = struct.pack("<HHHHII", 1, 0, 0, 0, 0, 2) + struct.pack("<HH", 0x000E, 0)
        d_off = code_off + len(code)
        data = bytearray(); offs = []
        for x in st:
            offs.append(d_off + len(data)); data += uleb(len(x)) + x.encode() + b"\x00"
        buf = bytearray(d_off + len(data)); buf[0:8] = b"dex\n035\x00"
        struct.pack_into("<I", buf, 0x20, len(buf)); struct.pack_into("<I", buf, 0x24, 0x70)
        struct.pack_into("<I", buf, 0x28, 0x12345678)
        struct.pack_into("<I", buf, 0x38, n_s); struct.pack_into("<I", buf, 0x3C, s_off)
        struct.pack_into("<I", buf, 0x40, 1); struct.pack_into("<I", buf, 0x44, t_off)
        struct.pack_into("<I", buf, 0x48, 1); struct.pack_into("<I", buf, 0x4C, p_off)
        struct.pack_into("<I", buf, 0x58, n_m); struct.pack_into("<I", buf, 0x5C, m_off)
        struct.pack_into("<I", buf, 0x60, 1); struct.pack_into("<I", buf, 0x64, c_off)
        for i, o in enumerate(offs):
            struct.pack_into("<I", buf, s_off + 4 * i, o)
        struct.pack_into("<I", buf, t_off, 0)
        struct.pack_into("<III", buf, p_off, 2, 1, 0)
        for i in range(n_m):
            struct.pack_into("<HHI", buf, m_off + 8 * i, 0, 0, 1)
        struct.pack_into("<IIIIIIII", buf, c_off, 0, 1, 0, 0, 0, 0, cd_off, 0)
        buf[cd_off:cd_off + len(cd)] = cd
        buf[code_off:code_off + len(code)] = code
        buf[d_off:] = data
        return bytes(buf)

    nd = native_dex(3, 5)
    census = A.dex_native_census(nd)
    check("census counts every method", census["methods"] == 8, census)
    check("census counts ACC_NATIVE", census["native"] == 2, census)
    check("census names the class", census["by_class"].get("LTest;") == 2, census)
    clean = A.dex_native_census(native_dex(0, 5))
    check("a clean dex reports zero native", clean["native"] == 0, clean)

    print("certificate pin map")
    def pin_dex(host, pin):
        st = ["LTest;", "a", host, pin, "V"]
        n_s = len(st)
        s_off = 0x70; t_off = s_off + 4 * n_s; p_off = t_off + 4
        m_off = p_off + 12; c_off = m_off + 8; cd_off = c_off + 32
        insns = struct.pack("<HHH", 0x001A, 2, 0x001A) + struct.pack("<HH", 3, 0x000E)
        code_off = (cd_off + 4 + 1 + 1 + 2 + 3) & ~3
        cd = bytes([0, 0, 1, 0]) + uleb(0) + uleb(1) + uleb(code_off)
        code = struct.pack("<HHHHII", 1, 0, 0, 0, 0, 5) + insns
        d_off = code_off + len(code)
        data = bytearray(); offs = []
        for x in st:
            offs.append(d_off + len(data)); data += uleb(len(x)) + x.encode() + b"\x00"
        buf = bytearray(d_off + len(data)); buf[0:8] = b"dex\n035\x00"
        struct.pack_into("<I", buf, 0x20, len(buf)); struct.pack_into("<I", buf, 0x24, 0x70)
        struct.pack_into("<I", buf, 0x28, 0x12345678)
        struct.pack_into("<I", buf, 0x38, n_s); struct.pack_into("<I", buf, 0x3C, s_off)
        struct.pack_into("<I", buf, 0x40, 1); struct.pack_into("<I", buf, 0x44, t_off)
        struct.pack_into("<I", buf, 0x48, 1); struct.pack_into("<I", buf, 0x4C, p_off)
        struct.pack_into("<I", buf, 0x58, 1); struct.pack_into("<I", buf, 0x5C, m_off)
        struct.pack_into("<I", buf, 0x60, 1); struct.pack_into("<I", buf, 0x64, c_off)
        for i, o in enumerate(offs):
            struct.pack_into("<I", buf, s_off + 4 * i, o)
        struct.pack_into("<I", buf, t_off, 0)
        struct.pack_into("<III", buf, p_off, 4, 4, 0)
        struct.pack_into("<HHI", buf, m_off, 0, 0, 1)
        struct.pack_into("<IIIIIIII", buf, c_off, 0, 1, 0, 0, 0, 0, cd_off, 0)
        buf[cd_off:cd_off + len(cd)] = cd
        buf[code_off:code_off + len(code)] = code
        buf[d_off:] = data
        return bytes(buf)

    PIN = "sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    pm = A.dex_pin_map(pin_dex("graph.facebook.com", PIN))
    check("pin map finds the pinned host", pm.get("LTest;", ([], []))[0] == ["graph.facebook.com"], pm)
    check("pin map returns the pin value", pm.get("LTest;", ([], []))[1] == [PIN], pm)
    check("pin regex rejects short values", not A.PIN_VALUE_RX.match("sha256/abc"))

    print("alignment rules")
    def map_dex(entries, size):
        buf = bytearray(b"dex\n035\x00" + b"\x00" * (size - 8))
        buf += struct.pack("<I", len(entries))
        for o, t, c in entries:
            buf += struct.pack("<HHII", t, 0, c, o)
        return seal(buf, entries[-1][0])

    odd = map_dex([(0, 0x0000, 1), (0x71, 0x2002, 1), (0x80, 0x1000, 1)], 0x80)
    p_odd = A.dex_validate(odd)
    check("1-byte aligned string_data at an odd offset is legal",
          not any(s == "bad" for s, _ in p_odd), p_odd)

    # an item with an odd insns_size and no tries ends at 2 mod 4; the next
    # code_item therefore starts there too, and that is legal
    body = code_item(3) + code_item(2)
    walk = bytearray(b"dex\n035\x00" + b"\x00" * (0x70 - 8) + body)
    while len(walk) % 4:
        walk += b"\x00"
    map_at = len(walk)
    walk += struct.pack("<I", 3)
    for o, t, c in ((0, 0x0000, 1), (0x70, 0x2001, 2), (map_at, 0x1000, 1)):
        walk += struct.pack("<HHII", t, 0, c, o)
    walk = seal(walk, map_at)
    p_walk = A.dex_validate(walk)
    check("code_item at 2 mod 4 (odd insns_size, no tries) is legal",
          not any(s == "bad" for s, _ in p_walk), p_walk)

    drift = bytearray(walk)
    struct.pack_into("<I", drift, 0x70 + 12, 1)     # shorten the first item
    drift = seal(drift, map_at)
    p_drift = A.dex_validate(drift)
    check("a drifted code_item section is still reported",
          any("padding" in m or "drift" in m for _s, m in p_drift), p_drift)
    print("     ->", p_drift[0][1][:90] if p_drift else "nothing")

    print("dex_stub_ok")
    buf = bytearray(b"\x00" * 0x70 + code_item(6, tries=1))
    A.dex_patch_code(buf, 0x70, "void")
    check("stub + nop tail accepted", A.dex_stub_ok(buf, 0x70, "void"))
    leftover = bytearray(buf)
    leftover[0x70 + 16 + 2] = 0x12          # the old bug: original stream left behind
    check("stub over the old stream rejected", not A.dex_stub_ok(leftover, 0x70, "void"))

    print("archive level")
    # a gap after a FIXED section is the hard, unambiguous fault
    broken = bytearray(b"dex\n035\x00" + b"\x00" * (0x70 - 8) + b"\x00" * 32 + b"\xbc" * 4)
    broken += struct.pack("<I", 3)
    for o, t, c in ((0, 0x0000, 1), (0x70, 0x0006, 1), (0x94, 0x1000, 1)):
        broken += struct.pack("<HHII", t, 0, c, o)
    broken = seal(broken, 0x94)
    for label, dexes, want in (("clean", {"classes.dex": good}, False),
                               ("broken", {"classes.dex": good, "classes10.dex": bytes(broken)}, True)):
        path = Path("/tmp/arp_%s.apk" % label)
        with zipfile.ZipFile(str(path), "w") as z:
            z.writestr(zipfile.ZipInfo("AndroidManifest.xml"), b"\x00" * 64)
            for n, d in dexes.items():
                zi = zipfile.ZipInfo(n)
                zi.compress_type = zipfile.ZIP_STORED
                z.writestr(zi, d)
        bad = not A.show_dex_audit(path)
        issues, _ok = A.apk_lint(path)
        lint_hit = any("dex verification" in m for _s, m in issues)
        ic, _facts, _man = A.install_check(path, None)
        install_hit = any("dex verification" in m for _s, _c, m, _f in ic)
        check("%s archive · audit verdict" % label, bad == want, bad)
        check("%s archive · apk_lint reports it" % label, lint_hit == want, issues)
        check("%s archive · install_check blocks it" % label, install_hit == want)
        path.unlink()

    print()
    if FAILS:
        print("FAILED: %d" % len(FAILS))
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
