# ARPXTOOL

Android reverse-engineering toolkit for Termux: decompile, inspect, patch, repack and sign APK files — with no root and no Frida server.

**v55.0 · GATEKEEPER**

---

## What it does

- **Static analysis** — manifest, permissions, exported components, native surface, frameworks, hardening and packer markers.
- **Bytecode patching** — direct DEX surgery that keeps the original class files, so classes that apktool fails to disassemble are never lost.
- **TLS interception support** — rewrites the app's own network-security-config in place (`user` anchor + `overridePins`), patches the Java trust/pinning layer, and patches the Flutter engine so Dart traffic becomes interceptable.
- **Flutter engine patching** — signature-based patching validated against 36 real `libflutter.so` builds, plus automatic download of a prebuilt patched engine (reFlutter) keyed by the engine build id when no signature matches.
- **Integrity guards** — every DEX is structurally validated before signing; a build that would not launch is refused instead of shipped.
- **Verification** — after signing it re-checks the archive, confirms every patch site is present in the output, and reports honestly instead of printing a fake success line.

## Install (Termux)

```bash
pkg update -y && pkg install -y python git openjdk-17
git clone https://github.com/ahmaeddev/arpxtool.git
cd arpxtool
bash install.sh
```

## Usage

```bash
arpxtool -i app.apk                 # full analysis + patch + sign
arpxtool -i app.apk -m ssl          # TLS neutralisation only
arpxtool -i app.apk -m signature --remove-license
arpxtool -i app.apk -m fast         # manifest + netsec only, never smali
arpxtool --self-check               # 34 internal checks
```

Key flags: `-m` mode, `-o` output, `--flutter-engine` (drop-in engine), `--remove-license`, `--targets` (custom patch table), `--no-net` (offline).

## Verify a Flutter engine

```bash
python3 verify_flutter_engines.py "app.apk"
```

Prints, per engine, the architecture, the matched BoringSSL function, the offset and the success value — or says plainly that the build is not in the table.

## Tests

```bash
python3 test_dex_integrity.py
python3 test_netsec.py
python3 test_flutter_patch.py
```

## Notes

- `arpxtool_pro.py` is the distributed build: every identifier except methods and stdlib keyword names is renamed, comments and docstrings removed. Regenerate after editing with `python3 obfuscate.py arpxtool.py arpxtool_pro.py`.
- The tool never prints a success marker for something it did not verify.

---

## بالعربية

أداة لهندسة تطبيقات أندرويد عكسيًا من Termux: فكّ، فحص، ترقيع، إعادة بناء، وتوقيع — بلا روت وبلا Frida.

أبرز ما فيها: ترقيع الديكس مباشرة مع الحفاظ على الأصناف الأصلية، إعادة كتابة إعداد أمان الشبكة داخل الأرشيف، ترقيع محرّك Flutter بالبصمات مع تنزيل محرّك مُرقّع تلقائيًا عند غياب البصمة، والتحقق من كل خطوة قبل التوقيع حتى لا يُطبع نجاح وهمي.

```bash
arpxtool -i app.apk -m ssl
```

## Disclaimer

Use only on applications you own or are explicitly authorised to test. Intercepting traffic you do not own is illegal in most jurisdictions.

## License

MIT
