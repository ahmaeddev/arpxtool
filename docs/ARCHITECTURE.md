# Architecture

A deep walk through the tool: what each stage does, which invariant it protects,
and why it is built this way. Function names are the real ones in
`arpxtool.py`.

```
        ┌────────────┐
 apk ──▶│  INTAKE    │──▶ merged.apk  (+ hash, entry audit)
        └────────────┘
              │
        ┌────────────┐
        │  DECODE    │──▶ tree/src  (+ classes_lost counter)
        └────────────┘
              │
        ┌────────────┐
        │  PLAN      │──▶ which stages run, which targets, which guards
        └────────────┘
              │
   ┌──────────┴──────────┬───────────┬────────────┐
 DEX surgery          manifest     netsec      native
 (length rule)        (flags)      (anchors)   (engine)
   └──────────┬──────────┴───────────┴────────────┘
              │
        ┌────────────┐        ┌────────────┐
        │  REBUILD   │───────▶│    SIGN    │──▶ apk
        └────────────┘        └────────────┘
                                     │
                              ┌────────────┐
                              │  VERIFY    │  patch sites, schemes, install
                              └────────────┘
```

---

## 1. Two build paths, one output

`decode_tree()` returns the decoded tree **and** `classes_lost`. If apktool lost
even one class, a tree rebuild would silently ship an APK missing that class, so
the build switches to `surgery_pipeline()` — no java, no apktool, no aapt2: the
original DEX files, the binary manifest and the native libraries are edited
directly inside the archive.

The consequence that shapes the whole design: **anything applied to the tree is
lost on the surgery path.** Every edit that matters therefore has an in-archive
pass:

| Edit | Tree pass | In-archive pass |
|---|---|---|
| DEX methods | smali → rebuild | `dex_surgery_apk()` |
| Manifest flags | text manifest | `manifest_edit()` |
| Network config | `res/xml/*.xml` | `inject_netsec()` |
| `libflutter.so` | `patch_shared_object()` | `patch_native_in_apk()` |

`pipe.records` collects every patch site; `VERIFY` re-opens the signed output and
counts them. A site that is in the records but not in the file is reported as
`unconfirmed` — that line is what ended two rounds of "the app looks the same
before and after".

---

## 2. DEX surgery

### The invariant

A `code_item` is `header(16) + insns(2·insns_size) + tries + handlers`. ART
validates the size of that stream against the section that follows it. Shrinking
it produces:

```
Non-zero padding bc before section of type 8193
List too large for insns size
```

So `dex_patch_code()` never changes the item length:

1. encode the stub (`const/4 v0,#1 ; return v0`, `return-void`, …);
2. write it at the start of the instruction stream;
3. fill the remaining units with `nop` (`0x0000`);
4. leave `tries_size`, `try_off` and `debug_info_off` untouched.

`dex_code_item_end()` is measured before and after; a patch that moves it is
refused. `dex_stub_ok()` re-reads the stream and checks the stub is there and the
tail is nop.

### The stub follows the return type

`DexIndex.stub_kind()` reads `method_id → proto_id → return_type_idx →
type_name` and picks:

| descriptor | stub |
|---|---|
| `V` | `return-void` |
| `Z` | `const/4 v0, #1 ; return v0` |
| `I S B C F` | `const/4 v0, #0 ; return v0` |
| `J D` | `const-wide/16 v0, #0 ; return-wide v0` |
| reference / array | `const/4 v0, #0 ; return-object v0` |

Writing `return-void` into a method declared to return `Ljava/util/List;` is a
verify error: ART rejects the method and the caller throws on first call. The
return type decides the stub, never the method name.

### Structural audit

`dex_audit_apk()` walks header → map list → string/type/proto/method/class
tables → class data → code items. Failures are `bad`; things the spec allows but
look odd (a `code_item` at 2 mod 4 with an odd `insns_size` and no tries) are
`warn`. Only `bad` blocks signing.

---

## 3. Manifest

Two readers exist because two problems exist:

- `axml_manifest()` — binary AXML. Attributes are matched by **name** and, when
  aapt2 stored them as resource ids only, by **id** through the resource map
  (`versionCode 0x0101021b`, `minSdkVersion 0x0101020c`, …). Package name falls
  back to a scan of the whole string pool, then to a UTF-8/UTF-16 scan of the
  raw bytes.
- `manifest_edit()` — writes flags back into the binary manifest: `debuggable`,
  `usesCleartextTraffic`, `networkSecurityConfig`, `extractNativeLibs`.

`show_manifest_truth()` prints `unavailable` rather than a value it could not
read.

---

## 4. Network security config

`inject_netsec()` **edits** the app's own compiled config; it never builds one
from scratch — a generated AXML is rejected at runtime with
`certificates element missing src attribute`.

Steps, all in-place on the AXML chunk list:

1. find `res/xml/network_security_config.xml` through the manifest reference;
2. clone the existing `<certificates>` element;
3. append `"user"` and `"overridePins"` to the string pool;
4. point the clone at `user`, set `overridePins="true"` (new attribute record,
   `attributeCount` and chunk size updated);
5. drop `domain-config` (and with it every `pin-set`);
6. force `cleartextTrafficPermitted="true"` on `base-config`.

`overridePins` is the part that matters: it tells Android to ignore the app's
pins for connections validated by that anchor. Without it a pinned app refuses
the proxy certificate even when the CA is trusted.

---

## 5. Native: the Flutter engine

`patch_shared_object()` resolves a patch site in three steps:

1. **signature** — `PATTERNS[arch]`, byte patterns with nibble wildcards,
   compiled by `compile_pattern()`. The primary table holds only patterns
   validated on the 36-engine corpus; `PATTERNS_EXTRA` is tried only if the
   primary misses, so a file can never match two different signatures.
2. **symbol table** — `elf_symbol_offsets()` reads `.dynsym`/`.symtab`; an
   unstripped engine needs no pattern at all.
3. **prebuilt engine** — `auto_patched_engine()` reads the engine build id from
   `libflutter.so`, looks it up in reFlutter's `enginehash.csv` (cached a week),
   downloads the matching patched engine, checks the ELF machine, replaces it.

Success values: `ssl_verify_peer_cert` returns `0` on success,
`ssl_crypto_x509_session_verify_cert_chain` returns `1`. Of 36 real engines, 34
match the first and 2 the second — one shared value is wrong for most of them.

`patch_native_in_apk()` applies the same logic to the archive itself, because
the tree copy dies on the surgery path.

---

## 6. Build and sign

- `do_zipalign()` aligns to 4 bytes; the aligned file is moved with
  `move_file()`, which falls back to copy + unlink when `$TMPDIR` and
  `/storage/emulated/0` are different filesystems (`EXDEV`).
- `signer_plan()` prefers `apksigner` (v1+v2+v3), falls back to a keystore
  generated on first use, then to `jarsigner` with a loud warning.
- Every DEX is audited before signing; a build with a `bad` finding is not
  signed.

## 7. Verification

`install_check()` returns `(issues, cert_facts, manifest)`:

- archive: `resources.arsc` present, uncompressed, 4-byte aligned;
- DEX: structural audit;
- signature: block consistency, schemes present;
- manifest: package, sdk range, `extractNativeLibs`, netsec reference.

`show_install_check()` prints `unavailable` for anything it could not read and
never a tick it did not verify.

---

## 8. Why the code is shaped this way

Three rules run through everything:

1. **Verify or stay silent.** No success marker without a re-read of the output.
2. **Never change a length in a binary format you do not fully own.** DEX items,
   AXML chunks, ELF sections — all patched in place, never resized unless the
   format allows it.
3. **One source of truth per edit.** A patch lives in the file that gets signed,
   not in a tree that might be thrown away.
