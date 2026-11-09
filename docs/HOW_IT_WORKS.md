# How ARPXTOOL works

This is the engineering log of the decisions behind the tool, written from the
failures that produced them. Everything below was verified on real files, not
assumed.

---

## 1. Two build paths, and why edits were being lost

The tool can rebuild an APK two ways:

- **tree rebuild** — apktool decodes everything, the tree is edited, apktool builds it back;
- **dex surgery** — no java, no apktool, no aapt2: the original DEX files are edited in place inside the archive.

The first version applied manifest and native edits to the decoded tree, then
silently switched to surgery whenever apktool failed to disassemble a class —
and the tree edits died with the tree. The output looked patched and was byte
for byte the original app on the native side.

**Rule now:** every edit that matters is re-applied *inside the archive that
will be signed*, not to a tree that may be discarded. DEX, manifest,
`libflutter.so` and the network-security-config each have an in-archive pass,
and verification counts the patch sites found in the final file.

---

## 2. DEX surgery: the length invariant

`dex_patch_code` used to shrink `insns_size` when replacing a method body. ART
rejects that in two different ways, both seen on a real device:

```
Non-zero padding bc before section of type 8193
List too large for insns size
```

**Invariant:** the item length never changes. The stub is written at the start
of the instruction stream and the rest of the old body is filled with `nop`;
`tries_size` and `debug_info_off` are left untouched. `dex_code_item_end` is
measured before and after, and a patch that moves it is refused.

Every DEX is then walked structurally before signing: header, map list, string
and type tables, class data, code items. A build that fails the walk is not
signed. The walk is advisory where the spec allows odd alignment — a `code_item`
at 2 mod 4 with an odd `insns_size` and no tries is legal, and an earlier
version wrongly rejected it.

---

## 3. The stub must match the method's return type

Patching `checkServerTrusted` with `return-void` is a verify error when that
method is declared to return `Ljava/util/List;` — ART rejects the method and the
caller throws at the first call. The stub is now chosen from the method's own
prototype, read from `proto_ids`:

| return type | stub |
|---|---|
| `V` | `return-void` |
| `Z` | `const/4 v0, #1 ; return v0` |
| `I S B C F` | `const/4 v0, #0 ; return v0` |
| `J D` | `const-wide/16 v0, #0 ; return-wide v0` |
| reference / array | `const/4 v0, #0 ; return-object v0` |

---

## 4. Network security config: edit, never generate

Building an AXML from scratch crashed the app on launch:

```
certificates element missing src attribute
```

Android's `XmlConfigSource` is stricter than aapt. The fix is to edit the app's
own compiled config in place: clone the existing `<certificates>` element,
append `"user"` to the string pool, drop `pin-set` and `domain-config`, and add
`overridePins="true"` to the user anchor — that attribute is what makes a pinned
app accept a user CA at all. `base-config` has `cleartextTrafficPermitted`
forced to `true` so plain HTTP is not silently blocked.

---

## 5. Flutter: signatures, and the wildcard bug

The engine ships its own BoringSSL, so no Java patch and no trust-store change
reaches Dart traffic. The engine has to be patched.

Patterns are byte signatures with nibble wildcards. `compile_pattern` turned
`?3` into a contiguous range `0x03–0x13` instead of `{0x03, 0x13, …, 0xF3}` —
so the pattern that matches `ssl_crypto_x509_session_verify_cert_chain` never
matched a single real engine. Fixed, then validated against 36 real
`libflutter.so` builds (arm, arm64, x86, x64): 36/36 matched, exactly one site
per file, and the two functions are distinguished with their own success values
(`0` for `ssl_verify_peer_cert`, `1` for the chain verifier).

A single return value for every match was wrong for 34 of those 36 engines.

---

## 6. When the engine is not in the table

Newer engines (Dart 3.13+, Flutter 3.47) match no published signature. The tool
then:

1. reads the engine build id and Dart version out of `libflutter.so`;
2. fetches reFlutter's engine table (cached for a week);
3. downloads the prebuilt patched engine for that exact build id and ABI;
4. replaces it inside the archive, after checking the ELF machine matches.

Nothing is guessed: an unknown build id produces a clear message, not a wrong
patch.

---

## 7. Small things that cost hours

- `os.replace()` from `$TMPDIR` to `/storage/emulated/0` raises `EXDEV` on
  Termux and killed a finished build at the last step. All moves now fall back
  to copy + unlink.
- The ASCII banner wrapped on a phone terminal and mangled the header; it is a
  compact box now.
- The manifest reader matched attributes by name, but aapt2 stores them as
  resource ids — `versionCode`, `minSdkVersion` and friends came out as `?`.
  The resource map is parsed now and attributes are matched by id as well.
- `host issuers` matched any dotted lowercase string, so `java.vendor` counted
  as a host. It now requires two dots and a real TLD.

---

## Verification

```bash
python3 arpxtool.py --self-check      # 34 checks
```

A success marker is only printed for something that was actually verified. When
a check cannot run, the tool says so instead of printing a tick.
