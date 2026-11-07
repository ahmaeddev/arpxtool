# ARPXTOOL compared with seven other tools

How each tool defeats TLS verification, what it costs you, and where it stops.

Facts for tools 1–4 come from reading their source. Tools 5–7 are described at
the level their public documentation supports.

---

## The table

| # | Tool | Method | Root | Flutter / Dart | Engine coverage | Self-verifies |
|---|---|---|---|---|---|---|
| 1 | **NVISO `disable-flutter-tls-verification`** | Frida script, `Interceptor.replace` on every pattern match | **Yes** — frida-server, or a gadget in a repacked APK | Yes | Patterns for arm/arm64/x86/x64 | Warns on multiple matches |
| 2 | **reFlutter** | Replaces `libflutter.so` with a prebuilt patched engine keyed by engine hash | No | Yes | Only builds published in its release table | No |
| 3 | **Flutter-Unpinner** | Byte signature + fixed patch bytes | No | Yes | 3 armv7 · 2 armv8 · 1 x86_64 | Refuses >1 match |
| 4 | **ApkPatcher** (TechnoIndian) | APKEditor/apktool + radare2 `wao ret0/ret1`, text NSC with `overridePins`, regex smali | No | Yes | First architecture found only | No |
| 5 | **objection** | Frida runtime instrumentation, `android sslpinning disable` | **Yes** (or gadget) | Partial — Java layer only | n/a | n/a |
| 6 | **apk-mitm** | Node.js: manifest + injected NSC + smali pinning removal | No | **No** — Dart untouched | n/a | Limited |
| 7 | **Frida gadget / server** | Runtime hooking | Server: yes · gadget: no | Yes, with a Flutter-aware script | Depends on the script | n/a |

---

## Scoring

0 = missing, 5 = best in class. Scores reflect **TLS interception on a Flutter
app without root**, which is the problem this tool exists for.

| Dimension | ARPXTOOL | NVISO | reFlutter | Unpinner | ApkPatcher | objection | apk-mitf | Frida |
|---|---|---|---|---|---|---|---|---|
| Works without root | **5** | 1 | 5 | 5 | 5 | 1 | 5 | 1 |
| Covers Dart/Flutter traffic | **5** | 5 | 5 | 5 | 4 | 2 | 0 | 4 |
| Engine build coverage | **5** | 4 | 4 | 2 | 3 | 0 | 0 | 3 |
| Correct success value per function | **5** | 5 | 5 | 3 | 2 | 2 | 0 | 3 |
| Verifies its own patch | **5** | 3 | 0 | 3 | 0 | 0 | 2 | 0 |
| Automatic setup (no manual download) | **5** | 2 | 4 | 2 | 2 | 2 | 5 | 1 |
| Keeps classes apktool loses | **5** | 3 | 3 | 3 | 1 | 4 | 2 | 4 |
| Works on an installed app | 1 | **5** | 2 | 2 | 2 | **5** | 2 | **5** |
| Snapshot dump / analysis | 1 | 1 | **5** | 3 | 1 | 3 | 1 | 3 |
| Setup simplicity on Termux | 4 | 2 | 4 | 3 | 3 | 2 | 4 | 1 |
| **Total /50** | **41** | 31 | 37 | 31 | 23 | 22 | 21 | 24 |

Read this honestly: ARPXTOOL wins on *interception that can be proven* and on
never losing classes, and it loses badly on the one thing the Frida tools do
better — working against an app that is already installed, without repacking.

---

## Where ARPXTOOL is genuinely different

**It patches in-archive and proves it.** After signing, the output is reopened
and every patch site is confirmed present. Two rounds of "the app looks the same
before and after" ended when this check was added: the engine patch was being
written to a decoded tree that the surgery path then discarded.

**Every engine, not the first one.** ApkPatcher patches the first architecture it
finds in `arm64-v8a, armeabi-v7a, armeabi, x86_64`. On a 32-bit device with a
multi-ABI APK, the ABI that actually runs can stay unpatched. ARPXTOOL patches
every `lib/<abi>/libflutter.so` and checks the ELF machine of any replacement.

**Per-function success values.** A single stub returning `1` is wrong for
`ssl_verify_peer_cert`, where success is `0`. Of 36 real engines, 34 match that
function.

**A table validated on 36 engines**, one site per file, no misses — the same
rule NVISO's verifier enforces.

**It falls back instead of failing.** When no signature matches a new build, it
reads the engine build id, looks it up in reFlutter's table and downloads the
patched engine for that exact build — automatically, cached, ABI-checked.

**DEX surgery under a length invariant.** apktool 2.12.1 drops a class on a JVM
float bug; a tree rebuild would ship an app missing that class. The surgery path
edits the original DEX and validates the result structurally before signing.

---

## Where the others are better

- **NVISO** works on an installed app without repacking, and retries until the
  engine is loaded.
- **reFlutter** also dumps the Dart snapshot and offers a patch mode; its engine
  table is the source ARPXTOOL uses for unknown builds.
- **apk-mitm** covers React Native and Cordova with one command.
- **objection** needs no repack when root is available and covers Java pinning
  broadly.

## What none of them solve

Pinning written in Dart — `badCertificateCallback`, a SHA-256 compare in
`libapp.so` — survives every tool in this table. Once the engine accepts the
proxy certificate, that is the next wall.
