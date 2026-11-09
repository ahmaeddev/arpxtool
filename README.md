# ARPXTOOL

<p align="center">
  <img src="assets/logo.png" alt="ARPXTOOL" width="100%">
</p>

<p align="center">
  <b>Android reverse-engineering toolkit for Termux — decompile, inspect, patch, repack and sign APK files without root and without Frida.</b>
</p>

<p align="center">
  <code>v55.1 · GATEKEEPER</code> · <code>python 3.12</code> · <code>termux</code> · <code>no root</code>
</p>

---

## Why it exists

Intercepting a modern Android app is not one problem, it is four: the platform
trust store, the app's own network-security-config, the Java pinning layer, and
— for Flutter — a BoringSSL compiled inside `libflutter.so` that ignores all
three. Most tools solve one of them and claim the rest.

ARPXTOOL solves all four in the APK itself, and then **re-opens the signed
output to prove every patch is actually there**. It never prints a success
marker for something it did not verify.

<p align="center">
  <img src="assets/terminal.svg" alt="real build output" width="92%">
</p>

## What it does

| Capability | Detail |
|---|---|
| **Static analysis** | manifest, permissions, exported components, native surface, framework inventory, hardening and packer markers, behavioural signals |
| **DEX surgery** | patches methods in the original DEX files under a strict length invariant, so classes apktool fails to disassemble are never lost |
| **Trust layer** | rewrites the app's own network-security-config in place: `user` anchor added, `overridePins="true"`, `pin-set` and `domain-config` removed, cleartext forced |
| **Java pinning** | neutralises trust managers, hostname verifiers, OkHttp `CertificatePinner`, conscrypt and chain cleaners — chosen by signature shape, with a stub that matches each method's real return type |
| **Flutter engine** | signature-based `libflutter.so` patching validated on 36 real engine builds, with the correct success value per BoringSSL function |
| **Unknown engines** | reads the engine build id, fetches the matching prebuilt patched engine automatically, ABI-checked, cached |
| **Integrity** | every DEX is structurally validated before signing; a build that would not launch is refused instead of shipped |
| **RASP bypass** | root, emulator, Frida, Xposed, debugger, mock-location and tamper checks — 45 method names, each patched with a stub that matches its own return type |
| **Pin map** | lists every `sha256/…` pin found in the payload with the host it belongs to and the class that declares it, before you touch the app |
| **Protection analysis** | counts `ACC_NATIVE` methods per class and reads JNI exports (`Java_*`, `JNI_OnLoad`, `RegisterNatives`) to tell you when the code you want to patch lives in a `.so` — dex2c / VMP territory |
| **Build report** | `--report-bundle` writes a sendable zip: JSON + Markdown + the session log, next to the output |
| **Verification** | archive, signature schemes, patch sites, install diagnosis — with `unavailable` instead of fake values |

## Install

```bash
pkg update -y && pkg install -y git
git clone https://github.com/ahmaeddev/arpxtool.git
cd arpxtool
bash install.sh
```

The installer checks python, java, apktool, zipalign, apksigner, keytool, free
space and network, installs only what is missing, then runs the 34 internal
checks and tells you the truth about what it found.

## Usage

```bash
arpxtool -i app.apk                          # full analysis + patch + sign
arpxtool -i app.apk -m ssl                   # TLS neutralisation only
arpxtool -i app.apk -m signature --remove-license
arpxtool -i app.apk -m fast                  # manifest + netsec, never smali
arpxtool -i app.apk -m surgery               # no java, no apktool, no aapt2
arpxtool -i app.apk -m native --flutter-engine ./libflutter_arm.so
arpxtool -i app.apk -m full --report-bundle    # build + sendable report zip
arpxtool -i app.apk -m security --bypass-protection   # root / emulator / frida / tamper
arpxtool --self-check                        # 34 internal checks
```

Modes: `detect · fast · full · inspect · native · re · security · signature · ssl · surgery · unpack · verify`

## Results, measured

| Test | Result |
|---|---|
| Flutter engines matched (36 real builds) | **36 / 36**, exactly one site each |
| Function split | 34 `ssl_verify_peer_cert` (returns 0) · 2 chain verifier (returns 1) |
| Unit suites (`dex`, `netsec`, `flutter`) | **ALL PASS** |
| Internal checks | **34 / 34** |
| Real build on device | 620 s · 29 methods rewritten · engine patched in-archive · **traffic intercepted** |
| Large multi-dex app (169 MB, 7 dex) | class lookup rebuilt: **48x faster**, surgery now reports progress per dex |

Full numbers, the regression log of nine real defects, and what is still not
covered: **[docs/TESTING.md](docs/TESTING.md)**

## Pipeline

<p align="center">
  <img src="assets/architecture.svg" alt="pipeline" width="100%">
</p>

Every stage writes into the archive that gets signed — never into a tree that
may be discarded. Deep dive, stage by stage, with the invariants each one
protects: **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**

## Comparison with twelve well-known tools

<p align="center">
  <img src="assets/comparison.svg" alt="comparison" width="88%">
</p>


Frida · objection · RMS · apk-mitm · reFlutter · NVISO · Flutter-Unpinner ·
ApkPatcher · apktool · jadx · MobSF · mitmproxy — grouped by what each one is
actually for, then scored only on the job they share, with a capability matrix
for the rest: **[docs/COMPARISON.md](docs/COMPARISON.md)**

Short version: **37/45** for ARPXTOOL on no-root Flutter interception, ahead of
reFlutter (33), NVISO (29) and Flutter-Unpinner (28). It loses clearly on one
thing — the Frida tools work on an app that is **already installed**, without
repacking.

## Documentation

| File | What is inside |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | every stage, every invariant, the real function names |
| [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) | the engineering log, written from the failures that produced each decision |
| [docs/TESTING.md](docs/TESTING.md) | measured report: 36 engines, 9 fixed defects, real build timings |
| [docs/COMPARISON.md](docs/COMPARISON.md) | twelve tools: categories, scoped score, capability matrix |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | every new feature and every fixed defect, with the symptom that forced it |

## Verify a Flutter engine yourself

Self-contained — it shares no code with the tool, so it can cross-check it:

```bash
python3 verify_flutter_engines.py "app.apk"
```

```
lib/armeabi-v7a/libflutter.so   ✓  ssl_verify_peer_cert   0x5283e8   returns 0
```

## Tests

```bash
python3 tests/test_cli.py             # self-check, cli surface, engine probe
python3 tests/test_dex_integrity.py   # length invariant, alignment, stubs, census, pins
python3 tests/test_netsec.py          # the network-security-config edit
python3 tests/test_flutter_patch.py   # signature table, symbol table, in-archive patch
```

All four print `ALL PASS` on a clean tree.

## Repository layout

```
arpxtool.py                the tool — readable source, ~15k lines
verify_flutter_engines.py  standalone engine probe (no imports from the tool)
install.sh                 Termux installer
tests/                     four suites: cli, dex, netsec, flutter
assets/                    logo, pipeline, comparison, terminal
docs/ARCHITECTURE.md       stage by stage, with invariants
docs/HOW_IT_WORKS.md       engineering log
docs/COMPARISON.md         seven-tool comparison with scores
docs/TESTING.md            measured test report + regression log
```

## Notes

- The shipped source is the readable one. No obfuscation: what the tool does is
  in the code, and the docs explain why each part exists.
- The tool refuses to sign a build it cannot verify.

## Disclaimer

Use only on applications you own or are explicitly authorised to test.
Intercepting traffic you do not own is illegal in most jurisdictions.

## License

**GNU General Public License v3.0** — see [LICENSE](LICENSE).

In plain words: you may use it, study it, modify it and even sell what you build
with it, but if you distribute a modified version, its source must be published
under the same license. A closed-source fork is not allowed. There is no
warranty of any kind.

```
ARPXTOOL — android reverse-engineering toolkit for termux
Copyright (C) 2026 Ahmaeddev <t.me/Ahmaed_dev1>
```
