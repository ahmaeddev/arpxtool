#!/usr/bin/env python3
"""Generate the SVG artwork used by the README (no external deps)."""
import os
from pathlib import Path

BG = "#0b1017"
PANEL = "#111a24"
LINE = "#1e2b39"
TXT = "#c9d6e2"
DIM = "#6b7f93"
CYAN = "#22d3ee"
VIOLET = "#a78bfa"
GREEN = "#34d399"
AMBER = "#fbbf24"
RED = "#f87171"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

OUT = Path(__file__).resolve().parent / "assets"


def head(w, h, title):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
        'role="img" aria-label="%s">\n'
        '<defs>'
        '<linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="%s"/><stop offset="0.5" stop-color="%s"/>'
        '<stop offset="1" stop-color="%s"/></linearGradient>'
        '<linearGradient id="bar" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>'
        '<filter id="soft"><feGaussianBlur stdDeviation="18"/></filter>'
        '</defs>'
        '<rect width="%d" height="%d" fill="%s"/>\n'
        % (w, h, w, h, title, CYAN, VIOLET, GREEN, CYAN, VIOLET, w, h, BG)
    )


def text(x, y, s, size=14, fill=TXT, weight="400", font=MONO, anchor="start", extra=""):
    s = (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    return ('<text x="%d" y="%d" font-family="%s" font-size="%d" fill="%s" '
            'font-weight="%s" text-anchor="%s" %s>%s</text>\n'
            % (x, y, font, size, fill, weight, anchor, extra, s))


def banner():
    w, h = 1280, 330
    s = head(w, h, "ARPXTOOL banner")
    s += '<ellipse cx="240" cy="40" rx="320" ry="150" fill="%s" opacity="0.16" filter="url(#soft)"/>\n' % CYAN
    s += '<ellipse cx="1060" cy="300" rx="300" ry="140" fill="%s" opacity="0.16" filter="url(#soft)"/>\n' % VIOLET
    s += text(72, 108, "ARPXTOOL", 62, "url(#g)", "700", extra='letter-spacing="2"')
    s += text(74, 152, "android reverse-engineering toolkit for termux", 20, DIM)
    s += '<rect x="74" y="176" width="196" height="30" rx="15" fill="%s" opacity="0.16"/>\n' % CYAN
    s += text(94, 196, "v55.0 · GATEKEEPER", 13, CYAN, "600")
    s += '<rect x="284" y="176" width="150" height="30" rx="15" fill="%s" opacity="0.16"/>\n' % GREEN
    s += text(304, 196, "no root · no frida", 13, GREEN, "600")
    stats = [("36/36", "flutter engines"), ("34/34", "self checks"), ("4", "patch layers"), ("620s", "real build")]
    x = 74
    for big, small in stats:
        s += text(x, 268, big, 30, TXT, "700")
        s += text(x, 292, small, 12, DIM)
        x += 200
    s += '<line x1="74" y1="228" x2="1206" y2="228" stroke="%s"/>\n' % LINE
    return s + "</svg>\n"


def architecture():
    w, h = 1280, 780
    s = head(w, h, "ARPXTOOL pipeline")

    def box(x, y, bw, bh, title, lines, accent=CYAN):
        o = '<rect x="%d" y="%d" width="%d" height="%d" rx="12" fill="%s" stroke="%s" stroke-width="1.5"/>\n' % (
            x, y, bw, bh, PANEL, accent)
        o += '<rect x="%d" y="%d" width="4" height="%d" rx="2" fill="%s"/>\n' % (x, y + 10, bh - 20, accent)
        o += text(x + 18, y + 28, title, 15, accent, "700")
        for i, ln in enumerate(lines):
            o += text(x + 18, y + 52 + i * 18, ln, 12, DIM)
        return o

    def arrow(x1, y1, x2, y2, color=LINE):
        return ('<path d="M%d %d L%d %d" stroke="%s" stroke-width="2" marker-end="url(#a)"/>\n'
                % (x1, y1, x2, y2, color))

    s += ('<defs><marker id="a" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" '
          'orient="auto"><path d="M0 0 L10 5 L0 10 z" fill="%s"/></marker></defs>\n' % DIM)

    s += text(60, 60, "pipeline", 22, TXT, "700")
    s += text(60, 84, "every stage writes into the archive that gets signed — never into a tree that may be discarded", 13, DIM)

    s += box(60, 120, 260, 96, "1 · INTAKE", ["merge .apks/.xapk", "zip audit, entry list", "input hash"])
    s += box(360, 120, 260, 96, "2 · DECODE", ["apktool 2.12.1", "class loss counted", "-> surgery if any"])
    s += box(660, 120, 260, 96, "3 · ANALYSE", ["manifest · netsec", "native surface", "frameworks · hardening"])
    s += box(960, 120, 260, 96, "4 · PLAN", ["mode -> stages", "targets collected", "guards armed"], VIOLET)

    s += box(60, 280, 300, 120, "5a · DEX SURGERY", ["length invariant", "stub by return type", "structural audit"], GREEN)
    s += box(390, 280, 260, 120, "5b · MANIFEST", ["flags set", "netsec reference", "prune orphans"], GREEN)
    s += box(680, 280, 260, 120, "5c · NETSEC", ["clone <certificates>", "+ user · overridePins", "pin-set removed"], GREEN)
    s += box(970, 280, 250, 120, "5d · NATIVE", ["signature table", "or symbol table", "or prebuilt engine"], GREEN)

    s += box(300, 460, 300, 110, "6 · REBUILD", ["tree build when clean", "surgery when classes lost", "in-archive re-apply"], CYAN)
    s += box(680, 460, 300, 110, "7 · SIGN", ["zipalign 4-byte", "apksigner v1/v2/v3", "cross-device safe move"], CYAN)
    s += box(480, 620, 340, 110, "8 · VERIFY", ["archive · schemes", "patch sites confirmed", "install diagnosis"], AMBER)

    s += arrow(320, 168, 356, 168) + arrow(620, 168, 656, 168) + arrow(920, 168, 956, 168)
    s += arrow(1090, 216, 1090, 276)
    s += arrow(210, 216, 210, 276) + arrow(520, 216, 520, 276) + arrow(810, 216, 810, 276)
    s += arrow(210, 400, 400, 456) + arrow(520, 400, 500, 456)
    s += arrow(810, 400, 760, 456) + arrow(1090, 400, 900, 456)
    s += arrow(600, 570, 620, 616)

    s += text(60, 748, "a stage that cannot verify its own result prints nothing — the tool never fakes a success line", 12, DIM)
    return s + "</svg>\n"


def comparison():
    w, h = 1120, 600
    rows = [("ARPXTOOL", 41, CYAN), ("reFlutter", 37, VIOLET), ("NVISO", 31, DIM),
            ("Flutter-Unpinner", 31, DIM), ("Frida gadget", 24, DIM), ("ApkPatcher", 23, DIM),
            ("objection", 22, DIM), ("apk-mitf", 21, DIM)]
    s = head(w, h, "comparison chart")
    s += text(60, 56, "no-root flutter interception · score / 50", 20, TXT, "700")
    s += text(60, 80, "nine dimensions: root, dart coverage, engine coverage, return values, verification, automation, class retention, live app, dump", 11, DIM)
    top, bh, gap = 120, 34, 20
    maxv = 50
    for i, (name, val, color) in enumerate(rows):
        y = top + i * (bh + gap)
        s += text(60, y + 23, name, 14, TXT if val > 30 else DIM, "600" if val > 30 else "400")
        x0 = 260
        bw = int((w - x0 - 120) * val / maxv)
        s += '<rect x="%d" y="%d" width="%d" height="%d" rx="8" fill="%s" opacity="0.10"/>\n' % (x0, y, w - x0 - 120, bh, LINE)
        s += '<rect x="%d" y="%d" width="%d" height="%d" rx="8" fill="url(#bar)" opacity="%s"/>\n' % (
            x0, y, bw, bh, "1" if color == CYAN else "0.45")
        s += text(x0 + bw + 14, y + 23, str(val), 15, color, "700")
    s += text(60, h - 26, "scores are relative to this problem, not to general features", 11, DIM)
    return s + "</svg>\n"


def terminal():
    w, h = 1180, 700
    s = head(w, h, "terminal output")
    s += '<rect x="40" y="36" width="%d" height="%d" rx="12" fill="#0a0e14" stroke="%s"/>\n' % (w - 80, h - 80, LINE)
    s += '<rect x="40" y="36" width="%d" height="34" rx="12" fill="%s"/>\n' % (w - 80, PANEL)
    for i, c in enumerate((RED, AMBER, GREEN)):
        s += '<circle cx="%d" cy="53" r="6" fill="%s"/>\n' % (66 + i * 20, c)
    s += text(160, 58, "arpxtool -i My Ooredoo_1.5.19.apks -m ssl", 13, DIM)

    lines = [
        ("  ARPXTOOL   v55.0   GATEKEEPER", TXT, "700"),
        ("", DIM, "400"),
        ("  13 · BINARY PATCH", CYAN, "700"),
        ("  [ok] lib/armeabi-v7a/libflutter.so · 1 site(s) neutralised", GREEN, "400"),
        ("  [**] ssl_verify_peer_cert @0x5283e8 · returns 0", TXT, "400"),
        ("", DIM, "400"),
        ("  18 · SURGICAL ENGINE", CYAN, "700"),
        ("  [ok] 29 method(s) rewritten across 3 dex file(s)", GREEN, "400"),
        ("  [ok] network security config rewritten · 560 -> 616 byte(s) · user CA added", GREEN, "400"),
        ("  [ok] lib/armeabi-v7a/libflutter.so · ssl_verify_peer_cert @0x5283e8 · returns 0", GREEN, "400"),
        ("  [ok] 8 dex file(s) pass the structural audit", GREEN, "400"),
        ("", DIM, "400"),
        ("  20 · VERIFICATION", CYAN, "700"),
        ("  [ok] archive intact", GREEN, "400"),
        ("  [ok] signature verified · v2 v3", GREEN, "400"),
        ("  [ok] binary patches confirmed in archive", GREEN, "400"),
        ("", DIM, "400"),
        ("  STAGE TIMINGS   total 620.06s", TXT, "700"),
        ("  INTAKE 93.54s · DECODE 101.40s · MANIFEST 7.11s · BINARY 0.66s", DIM, "400"),
    ]
    y = 110
    for ln, color, weight in lines:
        s += text(80, y, ln, 13, color, weight)
        y += 26
    s += '<rect x="70" y="%d" width="10" height="16" fill="%s" opacity="0.9"/>\n' % (y - 12, CYAN)
    return s + "</svg>\n"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in (("banner.svg", banner), ("architecture.svg", architecture),
                     ("comparison.svg", comparison), ("terminal.svg", terminal)):
        (OUT / name).write_text(fn(), encoding="utf-8")
        print("wrote assets/%s" % name)


if __name__ == "__main__":
    main()
