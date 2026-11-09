#!/usr/bin/env python3
"""Test the signature-based flutter patch: correct stub value per function."""
import struct
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import arpxtool as A

FAILS = []


def check(name, cond, extra=""):
    print(("  ok   " if cond else "  FAIL ") + name + ("" if cond else "  " + str(extra)))
    if not cond:
        FAILS.append(name)


def elf64(machine, body, body_off=0x200):
    """Minimal ELF64 little-endian with `body` at body_off."""
    size = body_off + len(body)
    hdr = bytearray(0x40)
    hdr[0:4] = b"\x7fELF"
    hdr[4] = 2
    hdr[5] = 1
    hdr[6] = 1
    struct.pack_into("<H", hdr, 16, 3)
    struct.pack_into("<H", hdr, 18, machine)
    struct.pack_into("<I", hdr, 20, 1)
    struct.pack_into("<Q", hdr, 32, 0x40)       # e_phoff
    struct.pack_into("<H", hdr, 52, 0x40)
    struct.pack_into("<H", hdr, 54, 0x38)
    struct.pack_into("<H", hdr, 56, 1)
    ph = struct.pack("<IIQQQQQQ", 1, 5, body_off, 0, 0, size, size, 0x1000)
    out = bytes(hdr) + ph
    out += b"\x00" * (body_off - len(out))
    return out + body


def elf32(machine, body, body_off=0x100):
    """Minimal ELF32 little-endian with `body` at body_off, one PT_LOAD."""
    size = body_off + len(body)
    hdr = bytearray(0x34)
    hdr[0:4] = b"\x7fELF"
    hdr[4] = 1                       # 32 bit
    hdr[5] = 1                       # little endian
    hdr[6] = 1
    struct.pack_into("<H", hdr, 16, 3)          # ET_DYN
    struct.pack_into("<H", hdr, 18, machine)
    struct.pack_into("<I", hdr, 20, 1)
    struct.pack_into("<I", hdr, 28, 0x34)       # e_phoff
    struct.pack_into("<H", hdr, 40, 0x34)       # e_ehsize
    struct.pack_into("<H", hdr, 42, 0x20)       # e_phentsize
    struct.pack_into("<H", hdr, 44, 1)          # e_phnum
    ph = struct.pack("<IIIIIIII", 1, body_off, 0, 0, size, size, 5, 0x1000)
    out = bytes(hdr) + ph
    out += b"\x00" * (body_off - len(out))
    return out + body


def concretise(pattern):
    """Turn a signature string into bytes, filling wildcard nibbles with 0."""
    out = b""
    for tok in pattern.split():
        hi = "0" if tok[0] in ".?" else tok[0]
        lo = "0" if tok[1] in ".?" else tok[1]
        out += bytes([int(hi + lo, 16)])
    return out


ARM_PEER = concretise(A.PATTERNS["arm"][0])
A64_CHAIN = concretise([p for p in A.PATTERNS["aarch64"] if "FF .3 01 D1" in p][0])
A64_PEER = concretise(A.PATTERNS["aarch64"][1])

print("patch_stub")
check("arm ok-value is 0", A.patch_stub("arm", 0) == bytes.fromhex("0020 7047".replace(" ", "")))
check("arm verified is 1", A.patch_stub("arm", 1) == bytes.fromhex("0120 7047".replace(" ", "")))
check("aarch64 ok-value is 0", A.patch_stub("aarch64", 0) == bytes.fromhex("000080d2c0035fd6"))
check("aarch64 verified is 1", A.patch_stub("aarch64", 1) == bytes.fromhex("200080d2c0035fd6"))

print("pattern_info")
check("peer-cert patterns default to 0",
      A.pattern_info(A.PATTERNS["arm"][0]) == (0, A.SSL_VERIFY_PEER_CERT))
chain_pat = [p for p in A.PATTERNS["aarch64"] if "FF .3 01 D1" in p]
check("chain pattern is marked 1", chain_pat and A.pattern_info(chain_pat[0]) == (1, A.SSL_VERIFY_CHAIN),
      chain_pat[:1])

print("patch_shared_object · arm")
path = "/tmp/libflutter_arm.so"
open(path, "wb").write(elf32(40, ARM_PEER))
res = A.patch_shared_object(path, "armeabi-v7a")
check("signature found and patched", res.hits and not res.error, res.error)
check("name recorded", res.names and res.names[0][1] == A.SSL_VERIFY_PEER_CERT, res.names)
check("returns 0, not 1", res.names and res.names[0][2] == 0, res.names)
data = open(path, "rb").read()
off = res.hits[0]
check("stub written is movs r0,#0", data[off:off + 4] == bytes.fromhex("00207047"), data[off:off + 4].hex())
check("backup kept", os.path.exists(path + ".arpbak"))
res2 = A.patch_shared_object(path, "armeabi-v7a")
check("second run reports already patched", res2.already == 1 and not res2.hits, (res2.already, res2.hits, res2.error))

print("patch_shared_object · aarch64 chain")
path = "/tmp/libflutter_a64.so"
open(path, "wb").write(elf64(183, A64_CHAIN))
res = A.patch_shared_object(path, "arm64-v8a")
check("chain signature patched", res.hits and not res.error, res.error)
check("chain returns 1", res.names and res.names[0][2] == 1, res.names)
data = open(path, "rb").read()
check("stub written is mov w0,#1",
      data[res.hits[0]:res.hits[0] + 8] == bytes.fromhex("200080d2c0035fd6"), data[res.hits[0]:res.hits[0] + 8].hex())

print("patch_native_in_apk")
import zipfile as _zf
_apk = "/tmp/arp_flutter_test.apk"
_so = elf32(40, ARM_PEER)
with _zf.ZipFile(_apk, "w") as z:
    z.writestr("AndroidManifest.xml", b"\x00" * 64)
    zi = _zf.ZipInfo("lib/armeabi-v7a/libflutter.so")
    zi.compress_type = _zf.ZIP_DEFLATED
    z.writestr(zi, _so)
_before = _zf.ZipFile(_apk).read("lib/armeabi-v7a/libflutter.so")
_out = A.patch_native_in_apk(_apk, "/tmp/arp_flutter_work")
_after = _zf.ZipFile(_apk).read("lib/armeabi-v7a/libflutter.so")
check("engine inside the apk is patched", _out and _out[0][1].hits, _out)
check("only the stub bytes changed", sum(1 for x, y in zip(_before, _after) if x != y) == 4)
check("archive size preserved", len(_before) == len(_after))
_out2 = A.patch_native_in_apk(_apk, "/tmp/arp_flutter_work")
check("second pass sees it as already patched", _out2 and _out2[0][1].already == 1)
os.unlink(_apk)

print("elf_symbol_offsets")
import struct as _st
_code_off = 0x100
_code = ARM_PEER + b"\x00" * 16
_strtab = b"\x00ssl_verify_peer_cert\x00"
_str_off, _sym_off, _sh_off = 0x140, 0x180, 0x1A0
_symtab = (_st.pack("<IIIBBH", 0, 0, 0, 0, 0, 0)
           + _st.pack("<IIIBBH", 1, _code_off, 0, 0x12, 0, 1))
_sh = bytearray(b"\x00" * 40)
_sh += _st.pack("<IIIIIIIIII", 0, 3, 0, 0, _str_off, len(_strtab), 0, 0, 1, 0)
_sh += _st.pack("<IIIIIIIIII", 0, 11, 0, 0, _sym_off, len(_symtab), 1, 1, 4, 16)
_size = _sh_off + len(_sh)
_buf = bytearray(_size)
_buf[0:4] = b"\x7fELF"; _buf[4] = 1; _buf[5] = 1; _buf[6] = 1
_st.pack_into("<H", _buf, 16, 3); _st.pack_into("<H", _buf, 18, 40); _st.pack_into("<I", _buf, 20, 1)
_st.pack_into("<I", _buf, 28, 0x34); _st.pack_into("<H", _buf, 40, 0x34)
_st.pack_into("<H", _buf, 42, 0x20); _st.pack_into("<H", _buf, 44, 1)
_st.pack_into("<I", _buf, 32, _sh_off); _st.pack_into("<H", _buf, 46, 40); _st.pack_into("<H", _buf, 48, 3)
_buf[0x34:0x34 + 32] = _st.pack("<IIIIIIII", 1, _code_off, _code_off, _code_off, _size, _size, 5, 0x1000)
_buf[_code_off:_code_off + len(_code)] = _code
_buf[_str_off:_str_off + len(_strtab)] = _strtab
_buf[_sym_off:_sym_off + len(_symtab)] = _symtab
_buf[_sh_off:_sh_off + len(_sh)] = _sh
_sym = "/tmp/arp_sym.so"
open(_sym, "wb").write(bytes(_buf))
_syms = A.elf_symbol_offsets(_sym, ("ssl_verify_peer_cert",))
check("symbol table resolves the function", _syms.get("ssl_verify_peer_cert") == _code_off, _syms)
_sres = A.patch_shared_object(_sym, "armeabi-v7a")
check("unstripped engine patched by symbol", _sres.hits == [_code_off], (_sres.hits, _sres.error))
os.unlink(_sym)

print("patch_shared_object · unknown build")
path = "/tmp/libflutter_none.so"
open(path, "wb").write(elf32(40, b"\x00" * 64))
res = A.patch_shared_object(path, "armeabi-v7a")
check("no signature is a clean miss", res.error == "signature not found" and not res.hits, res.error)

for f in ("/tmp/libflutter_arm.so", "/tmp/libflutter_arm.so.arpbak",
          "/tmp/libflutter_a64.so", "/tmp/libflutter_a64.so.arpbak", "/tmp/libflutter_none.so"):
    try:
        os.unlink(f)
    except OSError:
        pass

print()
print("FAILED: %d" % len(FAILS) if FAILS else "ALL PASS")
sys.exit(1 if FAILS else 0)
