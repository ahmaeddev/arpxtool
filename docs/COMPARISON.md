# ARPXTOOL compared with seven other tools

The comparison below is about **how each tool defeats TLS verification**, not
about features in general. Facts for the first four were read from their source
code; the last three are described at the level their public documentation
supports.

| # | Tool | Approach | Root needed | Flutter / Dart traffic | Engine coverage | Verifies its own patch |
|---|---|---|---|---|---|---|
| 1 | **NVISO `disable-flutter-tls-verification`** | Frida script: scans `r-x` ranges, `Interceptor.replace` on every pattern match | Yes — frida-server, or a gadget in a repacked APK | Yes, by design | Pattern table for arm/arm64/x86/x64 | Warns on multiple matches |
| 2 | **reFlutter** (`impact-i`) | Replaces `libflutter.so` with a prebuilt patched engine keyed by engine hash | No | Yes | Only builds published in its release table | No |
| 3 | **Flutter-Unpinner** (`alexsantee`) | Byte signature + fixed patch bytes (`01207047` for armv7) | No | Yes | 3 armv7 signatures, 2 armv8, 1 x86_64 | Refuses more than one match |
| 4 | **ApkPatcher** (`TechnoIndian`) | APKEditor/apktool + radare2 `wao ret0/ret1`; text NSC with `overridePins`; regex smali rules | No | Yes | Patches only the first architecture found | No |
| 5 | **objection** (`sensepost`) | Frida-based runtime instrumentation, `android sslpinning disable` | Yes (or gadget) | Partial — Java layer only | n/a | n/a |
| 6 | **apk-mitm** (`shroudedcode`) | Node.js: rewrites the manifest, injects a network-security-config, removes pinning from smali | No | No — Dart traffic is untouched | n/a | Limited |
| 7 | **Frida gadget / frida-server** | Runtime hooking, no repack (server) or a repack with the gadget | Server: yes · gadget: no | Yes, with a Flutter-aware script | Depends on the script | n/a |

## Where ARPXTOOL differs

**It patches in-archive, and it proves it.** After signing, the tool re-opens the
output and confirms every patch site is present. Two rounds of "the app looks the
same before and after" ended when this check was added — the engine patch was
being written to a decoded tree that the surgery path then threw away.

**Every engine, not the first one.** ApkPatcher patches the first architecture it
finds in `arm64-v8a, armeabi-v7a, armeabi, x86_64`; on a 32-bit device with a
multi-ABI APK the ABI that actually runs can stay unpatched. ARPXTOOL patches
every `lib/<abi>/libflutter.so` in the archive and checks the ELF machine of any
replacement engine.

**Per-function success values.** A single stub returning `1` is wrong for
`ssl_verify_peer_cert`, where success is `0`. Of 36 real engines, 34 match that
function and 2 match the chain verifier — one value for both is wrong for most
of them.

**Signature table validated on 36 engines.** Patterns are checked against real
`libflutter.so` builds, one site per file, no misses. A nibble-wildcard bug
(`?3` compiled to a contiguous range) had silently disabled one of the four
arm64 patterns.

**It falls back to a prebuilt engine instead of failing.** When no signature
matches a new build (Dart 3.13+, Flutter 3.47), the tool reads the engine build
id, looks it up in reFlutter's table and downloads the patched engine for that
exact build — automatically, cached, ABI-checked.

**DEX surgery keeps classes apktool loses.** apktool 2.12.1 drops a class on a
JVM float-formatting bug; a tree rebuild would ship an app missing that class.
The surgery path edits the original DEX instead, under a strict length
invariant, and validates the result structurally before signing.

**No root, no Frida, no server.** Everything happens in the APK. Tools 1, 5 and
7 need a Frida server (root) or a gadget; 2 and 3 need a build-specific engine
that may not exist for a new app.

## Where the others are better

- **NVISO** works on an already-installed app without repacking, and its Frida
  script retries until the engine is loaded — useful when repacking is not an
  option.
- **reFlutter** also dumps the Dart snapshot and offers a patch mode, which
  ARPXTOOL does not do.
- **apk-mitm** handles the whole Node.js ecosystem case (React Native, Cordova)
  with a single command.
- **objection** needs no repack at all when root is available, and covers Java
  pinning broadly.

## What none of them solve

Pinning written inside Dart (`badCertificateCallback`, a SHA-256 comparison in
`libapp.so`) survives every tool in this table. Once the engine accepts the
proxy certificate, that is the next wall — and it needs Dart-level analysis, not
an engine patch.
