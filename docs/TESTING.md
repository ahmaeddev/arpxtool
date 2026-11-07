# Testing report

Everything in this file was measured, not estimated. The failures are listed
first, because they are the reason the tool behaves the way it does.

**Environment:** Xiaomi M2006C3LG · Android 11 (SDK 30) · armv8l 32-bit ·
Termux · **no root** · no Frida server.

---

## 1. Regression log — nine real defects, found and fixed

| # | Symptom | Root cause | Fix |
|---|---|---|---|
| 1 | App crashed at launch: `Non-zero padding bc before section of type 8193` | `dex_patch_code` shrank `insns_size` | stub + `nop` tail, item length preserved |
| 2 | Second crash: `List too large for insns size` | same, via tries | `tries_size` / `debug_info_off` untouched, length checked before/after |
| 3 | Crash: `certificates element missing src attribute` | AXML generated from scratch, rejected by `XmlConfigSource` | edit the app's own compiled config in place |
| 4 | Flutter patch never matched any real engine | `compile_pattern` compiled `?3` to a contiguous range `0x03–0x13` instead of `{0x03,0x13,…,0xF3}` | explicit value set per nibble |
| 5 | 34 of 36 engines patched with the wrong success value | one stub (`return 1`) for every signature | per-signature return value: `0` for `ssl_verify_peer_cert`, `1` for the chain verifier |
| 6 | "The app is the same before and after" | native/manifest edits written to a decoded tree that the surgery path discarded | every edit re-applied inside the archive that gets signed, then verified in the output |
| 7 | Build died at the last step: `[Errno 18] Cross-device link` | `os.replace()` from `$TMPDIR` to `/storage/emulated/0` | copy + unlink fallback |
| 8 | Manifest fields showed `?` in install diagnosis | aapt2 stores attribute names as resource ids | resource map parsed, attributes matched by id |
| 9 | `host issuers` listed `java.vendor` as a host | regex accepted any dotted lowercase string | two dots + real TLD required |

---

## 2. Flutter engine validation

Corpus: **36 real `libflutter.so` builds** (arm, arm64, x86, x64) from
NVISO's `libflutter_samples`, run against the signature table.

| Metric | Result |
|---|---|
| Engines matched | **36 / 36** |
| Misses | 0 |
| Engines with more than one match site | 0 |
| `ssl_verify_peer_cert` (returns 0) | 34 engines |
| `ssl_crypto_x509_session_verify_cert_chain` (returns 1) | 2 engines |
| Stub written on arm | `00 20 70 47` |
| Stub written on arm64 | `00 00 80 d2 c0 03 5f d6` |
| Second run on a patched engine | reports exactly one `already patched` |

Cross-checks: NVISO's own `verify.py` reports 50 OK / 0 NOK on the same corpus
and treats more than one match per file as a failure — the table here obeys the
same rule.

A newer engine (Dart 3.13.5, Flutter 3.47.7, build `deb2874…`) matched **none**
of the published signatures — NVISO's arm pattern and all three of
Flutter-Unpinner's armv7 signatures were tested against it. That is the case the
automatic prebuilt-engine path exists for.

---

## 3. Unit and structural tests

```
test_dex_integrity.py   ALL PASS
test_netsec.py          ALL PASS
test_flutter_patch.py   ALL PASS
arpxtool --self-check   34 / 34
```

`test_dex_integrity.py` covers: the length invariant, `code_item` alignment
rules (an odd `insns_size` with no tries legitimately ends at 2 mod 4), stub
acceptance vs. a drifted stream, the structural audit on a broken archive, the
stub chosen from the method's return type (`V`, `Z`, `Ljava/util/List;`, `J`),
and host attribution from `const-string`.

`test_netsec.py` covers: the clone of `<certificates>`, the `user` anchor added,
`overridePins="true"` present, `cleartextTrafficPermitted` forced on, `pin-set`
and `domain-config` removed, and an archive with no config reported honestly as
`absent`.

`test_flutter_patch.py` covers: pattern compilation with nibble wildcards, one
site per engine, the correct return value per function, patching an engine
inside an archive (4 bytes changed, size preserved, second pass sees it as
already patched), and symbol-table lookup on an unstripped engine.

---

## 4. Real build, measured on the device

Target: `My Ooredoo 1.5.19` (`.apks` bundle, 40,790 classes, 29 permissions,
15 exported components), Flutter + OkHttp + CleverTap.

| Stage | Time |
|---|---|
| INTAKE (bundle merge, 8,880 lines) | 93.54 s |
| DECODE (apktool 2.12.1, 40,773 smali files) | 101.40 s |
| MANIFEST | 7.11 s |
| BINARY PATCH | 0.66 s |
| **total** | **620.06 s** |

What the build did:

- 29 methods rewritten across 3 DEX files (trust managers, hostname verifiers,
  OkHttp pinner, conscrypt verifier);
- network-security-config rewritten in the archive, 560 → 616 bytes, the app's
  own encoding kept, `user` CA added, `domain-config` and `pin-set` removed;
- `libflutter.so` patched in the archive: `ssl_verify_peer_cert @0x5283e8 ·
  returns 0`, confirmed by verification afterwards;
- 8 DEX files passed the structural audit;
- signature verified v2 + v3.

Result: **`apis.ooredoo.dz` became interceptable**. That is the first time in
this project that traffic was actually captured rather than claimed.

Second target, `Djezzy-Companion-1.0.apk` (pure Flutter, 1,231 smali files, no
Java networking at all): no signature matched, the tool printed the engine
build id, downloaded the matching prebuilt patched engine, replaced it in the
archive and reported the new SHA-1 — the ABI check refused to touch the other
architectures.

---

## 5. What is still not covered

- Pinning implemented inside Dart (`badCertificateCallback`, a SHA-256 compare
  in `libapp.so`) survives every technique here. It needs Dart-level analysis,
  not an engine patch.
- SDKs that build their own trust store from `/system/etc/security/cacerts`
  ignore the network-security-config entirely; the tool reports them but does
  not patch them.
- PairIP-protected apps that verify the archive CRC are not handled.
