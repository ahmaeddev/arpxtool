# Comparison with well-known tools

Twelve tools, grouped by what they actually are. A decompiler and a proxy are
not worse than a repackaging toolkit — they solve different problems, and
scoring them on one axis would be dishonest. So this page has three parts:

1. **what each tool is for** — the honest category map;
2. **a scoped score** — only for tools that attempt TLS interception on a
   Flutter app *without root*, which is the problem ARPXTOOL exists for;
3. **a capability matrix** — what each one can and cannot do.

Facts for the tools marked ✎ come from reading their source. The rest are
described at the level their public documentation supports.

---

## 1. What each tool is for

| Tool | Category | One line |
|---|---|---|
| **ARPXTOOL** ✎ | repackaging toolkit | patches the APK itself: DEX, manifest, netsec, Flutter engine, then signs and verifies |
| **Frida** | runtime instrumentation | injects JavaScript into a running process; the framework everything else builds on |
| **objection** | runtime instrumentation | Frida wrapper with ready-made commands, `android sslpinning disable` among them |
| **RMS — Runtime Mobile Security** | runtime instrumentation | web UI over Frida for hooking and exploring a live app |
| **apk-mitm** ✎ | repackaging | Node.js: rewrites the manifest, injects a network-security-config, strips pinning from smali |
| **reFlutter** ✎ | repackaging | swaps `libflutter.so` for a prebuilt patched engine, and dumps the Dart snapshot |
| **NVISO disable-flutter-tls** ✎ | Frida script | scans the engine in memory and replaces the verify function |
| **Flutter-Unpinner** ✎ | repackaging | byte signature + fixed patch bytes for `libflutter.so` |
| **ApkPatcher** (TechnoIndian) ✎ | repackaging | APKEditor/apktool + radare2, text NSC with `overridePins`, regex smali rules |
| **apktool** | build tool | decodes resources and smali, rebuilds them; no patching logic, no signing |
| **jadx** | decompiler | DEX → Java, searchable; read-only |
| **MobSF** | analysis framework | automated static + dynamic report over an APK; uses Frida for the dynamic half |
| **mitmproxy / HTTP Toolkit** | proxy | the interception endpoint itself; needs the app to trust its CA |

---

## 2. Scoped score — no-root TLS interception on a Flutter app

Nine dimensions, 0 = missing, 5 = best in class. Only tools that attempt this
job are scored; jadx, apktool, MobSF and mitmproxy are in the matrix below
instead, because intercepting is not their job.

| Dimension | ARPXTOOL | reFlutter | NVISO | Unpinner | Frida+gadget | ApkPatcher | objection | apk-mitm |
|---|---|---|---|---|---|---|---|---|
| Works without root | **5** | 5 | 1 | 5 | 3 | 5 | 1 | 5 |
| Covers Dart/Flutter traffic | **5** | 5 | 5 | 5 | 4 | 4 | 2 | 0 |
| Engine build coverage | **5** | 4 | 4 | 2 | 3 | 3 | 0 | 0 |
| Correct value per BoringSSL function | **5** | 5 | 5 | 3 | 3 | 2 | 2 | 0 |
| Verifies its own patch | **5** | 0 | 3 | 3 | 0 | 0 | 0 | 2 |
| Automatic setup | **5** | 4 | 2 | 2 | 1 | 2 | 2 | **5** |
| Keeps classes apktool loses | **5** | 3 | 3 | 3 | 4 | 1 | 4 | 2 |
| Works on an installed app | 1 | 2 | **5** | 2 | **5** | 2 | **5** | 2 |
| Snapshot dump / analysis | 1 | **5** | 1 | 3 | 3 | 1 | 3 | 1 |
| **Total /45** | **37** | 33 | 29 | 28 | 26 | 20 | 19 | 17 |

Read this honestly: ARPXTOOL wins on *interception that can be proven* and on
never losing classes; it loses clearly on the one thing the Frida tools do
better — working against an app that is **already installed**, with no repack.

---

## 3. Capability matrix

`●` full · `◐` partial · `○` none

| Tool | Static analysis | DEX patch | Manifest + netsec | Sign | Flutter engine | Runtime hook | Report | No root |
|---|---|---|---|---|---|---|---|---|
| **ARPXTOOL** | ● | ● | ● | ● | ● | ○ | ● | ● |
| Frida | ○ | ○ | ○ | ○ | ◐ | ● | ○ | ○ |
| objection | ○ | ○ | ○ | ○ | ◐ | ● | ○ | ○ |
| RMS | ◐ | ○ | ○ | ○ | ◐ | ● | ◐ | ○ |
| apk-mitm | ○ | ● | ● | ◐ | ○ | ○ | ○ | ● |
| reFlutter | ○ | ○ | ○ | ○ | ● | ○ | ○ | ● |
| NVISO | ○ | ○ | ○ | ○ | ● | ● | ○ | ○ |
| Flutter-Unpinner | ○ | ○ | ○ | ◐ | ● | ○ | ○ | ● |
| ApkPatcher | ◐ | ● | ● | ● | ● | ○ | ○ | ● |
| apktool | ○ | ◐ | ◐ | ○ | ○ | ○ | ○ | ● |
| jadx | ● | ○ | ○ | ○ | ○ | ○ | ◐ | ● |
| MobSF | ● | ○ | ○ | ○ | ○ | ◐ | ● | ● |
| mitmproxy | ○ | ○ | ○ | ○ | ○ | ○ | ◐ | ● |

---

## 4. Where ARPXTOOL is genuinely different

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
function and 2 match the chain verifier.

**A table validated on 36 engines**, one site per file, no misses — the same rule
NVISO's own verifier enforces.

**It falls back instead of failing.** When no signature matches a new build
(Dart 3.13+, Flutter 3.47), it reads the engine build id, looks it up in
reFlutter's table and downloads the patched engine for that exact build —
automatically, cached, ABI-checked.

**DEX surgery under a length invariant.** apktool 2.12.1 drops a class on a JVM
float bug; a tree rebuild would ship an app missing that class. The surgery path
edits the original DEX and validates the result structurally before signing.

---

## 5. Where the others are better — plainly

- **Frida / objection / RMS** work on a *running* app with no repack, and can
  hook anything at runtime, including Dart, with the right script. If root is
  available, they are faster than any repackaging tool.
- **reFlutter** also dumps the Dart snapshot and has a patch mode; its engine
  table is the source ARPXTOOL uses for unknown builds.
- **apk-mitm** covers React Native and Cordova with one command and needs no
  configuration at all.
- **MobSF** gives a full security report in one upload — different job, done
  better than anything here.
- **jadx** remains the best way to *read* an app.
- **mitmproxy / HTTP Toolkit** are where the traffic actually lands; every tool
  above exists to make their job possible.

## 6. What none of them solve

Pinning written in Dart — `badCertificateCallback`, a SHA-256 compare inside
`libapp.so` — survives every tool in this table. Once the engine accepts the
proxy certificate, that is the next wall, and it needs Dart-level analysis
rather than an engine patch.
