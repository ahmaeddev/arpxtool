# Changelog

Everything below happened on real files. Each fix names the symptom that forced
it, because that is the only reason to trust it.

---

## v55.1 — GATEKEEPER · 2026-11-10

### New

**Flutter engine support that does not give up**

- `verify_flutter_engines.py` — a standalone probe, no imports from the tool, so
  it can cross-check the tool's own answer.
- Signature table validated on **36 real engines**: 36/36 matched, exactly one
  site per file, correct function and success value per match.
- **Symbol-table fallback** — an unstripped engine is patched by name, no pattern
  needed.
- **Automatic prebuilt engine** — when a build is newer than every published
  signature, the tool reads the engine build id, looks it up in reFlutter's
  table, downloads the matching patched engine (cached a week, ABI-checked) and
  swaps it in. `--flutter-engine` still overrides by hand.

**Beyond TLS**

- **RASP bypass** — 45 detection methods (root, emulator, Frida, Xposed,
  debugger, mock location, tamper, su binary) patched to return false, and the
  "is everything fine" ones to return true. Wired into `security`, `full`,
  `signature`, `ssl` modes **and** the surgery path, plus `--bypass-protection`.
- **Certificate pin map** — every `sha256/…` pin in the payload, with the host it
  belongs to and the class that declares it, printed before you touch the app.
- **Play licence removal** — LVL and PairIP: `allowAccess` → true,
  `connectToLicensingService` / `retryOrThrow` → void.
- **dex2c / VMP census** — counts `ACC_NATIVE` methods per class and reads JNI
  exports (`Java_*`, `JNI_OnLoad`, `RegisterNatives`) to say where the code
  actually lives, and lists every patch target that turned out to be native.

**Reporting**

- `--report-bundle` writes `<name>.report.json`, `<name>.report.md` and
  `<name>.report.zip` (with the session log) next to the output — one file to
  attach when something goes wrong.

**Feedback instead of silence**

- Surgery prints a line per dex (classes, hits, seconds) and every 2000 packed
  entries, so a long build never looks frozen.

### Fixed

| Symptom | Cause | Fix |
|---|---|---|
| Crash at launch: `Non-zero padding bc before section of type 8193` | `dex_patch_code` shrank `insns_size` | stub + `nop` tail, item length preserved, checked before/after |
| Second crash: `List too large for insns size` | same, via tries | `tries_size` / `debug_info_off` untouched |
| Crash: `certificates element missing src attribute` | AXML generated from scratch | edit the app's own compiled config in place |
| Engine patch never matched a real build | `compile_pattern` compiled `?3` to a contiguous range | explicit value set per nibble |
| 34 of 36 engines got the wrong success value | one stub for every signature | per-function value: `0` / `1` |
| "The app is the same before and after" | edits written to a tree the surgery path discarded | every edit re-applied inside the signed archive, then verified |
| `! 1 patch site(s) unconfirmed` | engine patch never reached the output | `patch_native_in_apk()` |
| Build died at the end: `[Errno 18] Cross-device link` | `os.replace()` across filesystems on Termux | copy + unlink fallback |
| Manifest fields printed as `?` | aapt2 stores attribute names as resource ids | resource map parsed, attributes matched by id |
| `java.vendor` counted as a host | regex accepted any dotted string | two dots + real TLD |
| Tool appeared frozen on a 169 MB, 7-dex app | `find_class()` linear scan, once per target | `class_map()` built once — **48× faster** (measured) |
| Surgery skipped native targets silently | `code_off == 0` just `continue` | collected and reported as `native target(s)` |
| RASP list ignored on large apps | wired into `security` mode but not into surgery | armed in `sigmap` |
| `mkdtemp(prefix=…)` broke in the obfuscated build | `prefix` renamed as a parameter | stdlib keyword names are never renamed |

---

## v55.0 — GATEKEEPER · first public build

- static analysis: manifest, permissions, exported components, native surface,
  frameworks, hardening, packers
- DEX surgery with a length invariant and a structural audit before signing
- network-security-config edited in place (`user` anchor, `overridePins`, pins
  dropped, cleartext forced)
- Java trust layer: trust managers, hostname verifiers, OkHttp pinner,
  conscrypt, chain cleaners — stub chosen from the method's return type
- signing (v1/v2/v3) and verification of every patch site in the output
- install diagnosis that prints `unavailable` instead of a value it never read
