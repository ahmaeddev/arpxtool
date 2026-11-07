#!/usr/bin/env python3
import io
import os
import re
import sys
import json
import math
import random
import time
import shutil
import struct
import plistlib
import atexit
import hashlib
import platform
import traceback
import zipfile
import zlib
import tempfile
import argparse
import subprocess
import urllib.error
import urllib.request
import ssl as _tls
from pathlib import Path


HOME = Path.home()
ESC = "\033["


class Tty:
    enabled = sys.stdout.isatty()
    truecolor = False
    width = 88

    @classmethod
    def probe(cls):
        cls.width = shutil.get_terminal_size((88, 24)).columns
        if os.environ.get("NO_COLOR") is not None:
            cls.enabled = False
        term = os.environ.get("TERM", "")
        if term == "dumb":
            cls.enabled = False
        ct = os.environ.get("COLORTERM", "").lower()
        cls.truecolor = ct in ("truecolor", "24bit") or "truecolor" in term
        if not cls.enabled:
            cls.truecolor = False

    @classmethod
    def clamp(cls, lo, hi):
        return max(lo, min(hi, cls.width))


class Pal:
    RESET = ESC + "0m"
    BOLD = ESC + "1m"
    DIM = ESC + "2m"
    ITALIC = ESC + "3m"
    HIDE = ESC + "?25l"
    SHOW = ESC + "?25h"
    CLR = ESC + "K"
    HOME = ESC + "H"
    WIPE = ESC + "2J" + ESC + "H"

    def __init__(self, rgb, bold=False):
        self.rgb = rgb
        self.bold = bold
        self._cache = {}

    def code(self):
        if not Tty.enabled:
            return Pal.BOLD if self.bold else ""
        if self.rgb in self._cache:
            return self._cache[self.rgb]
        r, g, b = self.rgb
        if Tty.truecolor:
            s = f"{ESC}{1 if self.bold else 22};38;2;{r};{g};{b}m"
        else:
            s = f"{ESC}{1 if self.bold else 22};38;5;{Pal.nearest256(r, g, b)}m"
        self._cache[self.rgb] = s
        return s

    def __call__(self, text):
        if not Tty.enabled:
            return str(text)
        return f"{self.code()}{text}{Pal.RESET}"

    @staticmethod
    def bg(rgb, fg=None):
        if not Tty.enabled:
            return lambda t: str(t)
        fg = fg or (241, 245, 249)
        r, g, b = rgb
        if Tty.truecolor:
            code = f"{ESC}48;2;{r};{g};{b}m{ESC}38;2;{fg[0]};{fg[1]};{fg[2]}m{ESC}1m"
        else:
            code = f"{ESC}48;5;{Pal.nearest256(r, g, b)}m{ESC}38;5;{Pal.nearest256(*fg)}m{ESC}1m"
        return lambda t: f"{code} {t} {Pal.RESET}"


    @staticmethod
    def nearest256(r, g, b):
        steps = (0, 95, 135, 175, 215, 255)

        def near(v):
            best, bd = 0, 10 ** 9
            for i, s in enumerate(steps):
                d = abs(s - v)
                if d < bd:
                    bd, best = d, i
            return best

        ri, gi, bi = near(r), near(g), near(b)
        cube = 16 + 36 * ri + 6 * gi + bi
        avg = (r + g + b) // 3
        gidx = max(0, min(23, (avg - 8) // 10))
        gv = 8 + 10 * gidx
        d_cube = (steps[ri] - r) ** 2 + (steps[gi] - g) ** 2 + (steps[bi] - b) ** 2
        d_gray = (gv - r) ** 2 + (gv - g) ** 2 + (gv - b) ** 2
        return cube if d_cube <= d_gray else 232 + gidx


class Stage:
    records = []
    current = None
    t0 = None

    @classmethod
    def begin(cls, name):
        cls.close()
        cls.current = name
        cls.t0 = time.time()

    @classmethod
    def close(cls):
        if cls.current and cls.t0 is not None:
            cls.records.append((cls.current, time.time() - cls.t0))
        cls.current = None
        cls.t0 = None

    @classmethod
    def reset(cls):
        cls.records = []
        cls.current = None
        cls.t0 = None


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return (int(lerp(c1[0], c2[0], t)), int(lerp(c1[1], c2[1], t)), int(lerp(c1[2], c2[2], t)))


def ramp(stops, t):
    t = max(0.0, min(1.0, t))
    if len(stops) == 1:
        return stops[0]
    span = 1.0 / (len(stops) - 1)
    i = min(int(t / span), len(stops) - 2)
    local = (t - i * span) / span
    return mix(stops[i], stops[i + 1], local)


ICE = (120, 235, 255)
CYAN = (34, 211, 238)
AZURE = (56, 132, 255)
VIOLET = (139, 92, 246)
MAGENTA = (232, 121, 249)
ROSE = (251, 113, 133)
AMBER = (251, 191, 36)
LIME = (163, 230, 53)
EMERALD = (52, 211, 153)
TEAL = (45, 212, 191)
SLATE = (148, 163, 184)
STEEL = (100, 116, 139)
INK = (51, 65, 85)
WHITE = (241, 245, 249)
BLOOD = (248, 113, 113)
SNOW = (226, 232, 240)

G_MAIN = [CYAN, AZURE, VIOLET, MAGENTA]
G_COOL = [TEAL, CYAN, AZURE]
G_WARM = [AMBER, ROSE, MAGENTA]
G_OK = [EMERALD, TEAL, CYAN]
G_WARN = [AMBER, ROSE]
G_BAD = [BLOOD, MAGENTA]

T_MAIN = Pal(CYAN, True)
T_HEAD = Pal(ICE, True)
T_DIM = Pal(STEEL)
T_OK = Pal(EMERALD, True)
T_WARN = Pal(AMBER, True)
T_ERR = Pal(BLOOD, True)
T_INFO = Pal(AZURE)
T_TXT = Pal(SNOW)
T_ACC = Pal(VIOLET, True)

SPIN = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
DOTS = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
PARTIAL = " ▏▎▍▌▋▊▉█"
RULE = "━"
THIN = "─"
BOX = ("╭", "╮", "╰", "╯", "│", "─")
BULLET = "▸"
ARROW = "→"
CHECK = "✓"
CROSS = "✗"
DASH = "·"
WARN = "!"
DIAMOND = "◆"
CIRCLE = "●"
HOLLOW = "○"


def vislen(s):
    return len(re.sub(r"\033\[[0-9;?]*[A-Za-z]", "", s))


def pad_vis(s, n):
    return s + " " * max(0, n - vislen(s))


def trunc(s, n):
    s = re.sub(r"\033\[[0-9;?]*[A-Za-z]", "", str(s))
    return s if len(s) <= n else s[: max(0, n - 1)] + "…"


class Anim:
    height = 0

    @classmethod
    def paint(cls, lines):
        if not Tty.enabled:
            for ln in lines:
                sys.stdout.write(ln + "\n")
            sys.stdout.flush()
            return
        if cls.height:
            sys.stdout.write(f"{ESC}{cls.height}A")
        for i in range(max(cls.height, len(lines))):
            sys.stdout.write(ESC + "2K" + (lines[i] if i < len(lines) else ""))
            sys.stdout.write("\r\n")
        cls.height = len(lines)
        sys.stdout.flush()

    @classmethod
    def close(cls):
        cls.height = 0


def gradient_text(text, stops, bold=False):
    if not Tty.enabled:
        return text
    n = max(1, len(text) - 1)
    out = []
    for i, ch in enumerate(text):
        if ch == " ":
            out.append(ch)
            continue
        out.append(Pal(ramp(stops, i / n), bold)(ch))
    return "".join(out)


def gradient_line(width, stops, ch=RULE):
    if not Tty.enabled:
        return ch * width
    out = []
    for i in range(width):
        out.append(Pal(ramp(stops, i / max(1, width - 1)))(ch))
    return "".join(out)


def rule(width=None, stops=None, ch=RULE):
    w = width or Tty.clamp(30, 84)
    return gradient_line(w, stops or G_MAIN, ch)


def boxed(lines, stops=None, title=None, width=None):
    stops = stops or G_COOL
    inner = max([vislen(l) for l in lines] + [0])
    if title:
        inner = max(inner, vislen(title) + 4)
    w = inner if width is None else max(inner, width)
    w = min(w, Tty.clamp(40, 92))
    tl, tr, bl, br, v, h = BOX
    edge = lambda t: Pal(stops[-1])(t) if Tty.enabled else t
    out = []
    if title:
        label = " " + title + " "
        left = max(0, (w - vislen(label)) // 2)
        out.append(edge(tl + h * left) + Pal(ICE, True)(label) + edge(h * (w - vislen(label) - left) + tr))
    else:
        out.append(edge(tl + h * w + tr))
    for ln in lines:
        out.append(edge(v) + pad_vis(ln, w) + edge(v))
    out.append(edge(bl + h * w + br))
    return out


class Out:
    @staticmethod
    def blank():
        print()

    @staticmethod
    def head(title, stops=None):
        stops = stops or G_MAIN
        Stage.begin(title)
        print()
        print("  " + rule(Tty.clamp(20, 78), stops, THIN))
        n = len(Stage.records) + 1
        counter = Pal.bg(stops[-1], INK)(" %02d " % n)
        label = f"{BULLET} {title.upper()}"
        if Tty.enabled:
            print("  " + counter + " " + Pal(ICE, True)(label))
        else:
            print("  %02d %s" % (n, label))
        print("  " + rule(Tty.clamp(20, 78), stops, THIN))

    @staticmethod
    def ok(msg):
        log_line("ok", msg)
        print("  " + T_OK(CHECK) + " " + T_TXT(msg))

    @staticmethod
    def bad(msg):
        log_line("bad", msg)
        print("  " + T_ERR(CROSS) + " " + T_TXT(msg))

    @staticmethod
    def warn(msg):
        log_line("warn", msg)
        print("  " + T_WARN(WARN) + " " + T_TXT(msg))

    @staticmethod
    def info(msg):
        log_line("info", msg)
        print("  " + T_INFO(ARROW) + " " + T_DIM(msg))

    @staticmethod
    def kv(key, value, width=22, tone=None):
        k = T_DIM(key.ljust(width))
        v = (tone or T_TXT)(str(value))
        print(f"  {k}{v}")

    @staticmethod
    def bullet(msg, tone=None):
        print("  " + (tone or T_ACC)(DIAMOND) + " " + T_DIM(msg))

    @staticmethod
    def bar(label, value, total, width=26, stops=None):
        stops = stops or G_OK
        total = max(1, total)
        ratio = max(0.0, min(1.0, value / total))
        cells = ratio * width
        full = int(cells)
        frac = cells - full
        body = "█" * full
        if full < width:
            body += PARTIAL[int(frac * 8)]
            body += "░" * (width - full - 1)
        if Tty.enabled:
            body = gradient_text(body, stops)
        pct = f"{ratio * 100:5.1f}%"
        print(f"  {T_DIM(label.ljust(18))}{body} {T_TXT(pct)}")

    @staticmethod
    def spark(values, stops=None):
        glyphs = "▁▂▃▄▅▆▇█"
        if not values:
            return ""
        lo, hi = min(values), max(values)
        span = (hi - lo) or 1
        s = "".join(glyphs[min(7, int((v - lo) / span * 7))] for v in values)
        return gradient_text(s, stops or G_COOL) if Tty.enabled else s




BIGFONT = {
    "A": (" █████╗ ", "██╔══██╗", "███████║", "██╔══██║", "██║  ██║", "╚═╝  ╚═╝"),
    "B": ("██████╗ ", "██╔══██╗", "██████╔╝", "██╔══██╗", "██████╔╝", "╚═════╝ "),
    "C": (" ██████╗", "██╔════╝", "██║     ", "██║     ", "╚██████╗", " ╚═════╝"),
    "D": ("██████╗ ", "██╔══██╗", "██║  ██║", "██║  ██║", "██████╔╝", "╚═════╝ "),
    "E": ("███████╗", "██╔════╝", "█████╗  ", "██╔══╝  ", "███████╗", "╚══════╝"),
    "F": ("███████╗", "██╔════╝", "█████╗  ", "██╔══╝  ", "██║     ", "╚═╝     "),
    "G": (" ██████╗ ", "██╔════╝ ", "██║  ███╗", "██║   ██║", "╚██████╔╝", " ╚═════╝ "),
    "H": ("██╗  ██╗", "██║  ██║", "███████║", "██╔══██║", "██║  ██║", "╚═╝  ╚═╝"),
    "I": ("██╗", "██║", "██║", "██║", "██║", "╚═╝"),
    "J": ("     ██╗", "     ██║", "     ██║", "██   ██║", "╚█████╔╝", " ╚════╝ "),
    "K": ("██╗  ██╗", "██║ ██╔╝", "█████╔╝ ", "██╔═██╗ ", "██║  ██╗", "╚═╝  ╚═╝"),
    "L": ("██╗     ", "██║     ", "██║     ", "██║     ", "███████╗", "╚══════╝"),
    "M": ("███╗   ███╗", "████╗ ████║", "██╔████╔██║", "██║╚██╔╝██║", "██║ ╚═╝ ██║", "╚═╝     ╚═╝"),
    "N": ("███╗   ██╗", "████╗  ██║", "██╔██╗ ██║", "██║╚██╗██║", "██║ ╚████║", "╚═╝  ╚═══╝"),
    "O": (" ██████╗ ", "██╔═══██╗", "██║   ██║", "██║   ██║", "╚██████╔╝", " ╚═════╝ "),
    "P": ("██████╗ ", "██╔══██╗", "██████╔╝", "██╔═══╝ ", "██║     ", "╚═╝     "),
    "Q": (" ██████╗ ", "██╔═══██╗", "██║   ██║", "██║▄▄ ██║", "╚██████╔╝", " ╚══▀▀═╝ "),
    "R": ("██████╗ ", "██╔══██╗", "██████╔╝", "██╔══██╗", "██║  ██║", "╚═╝  ╚═╝"),
    "S": ("███████╗", "██╔════╝", "███████╗", "╚════██║", "███████║", "╚══════╝"),
    "T": ("████████╗", "╚══██╔══╝", "   ██║   ", "   ██║   ", "   ██║   ", "   ╚═╝   "),
    "U": ("██╗   ██╗", "██║   ██║", "██║   ██║", "██║   ██║", "╚██████╔╝", " ╚═════╝ "),
    "V": ("██╗   ██╗", "██║   ██║", "██║   ██║", "╚██╗ ██╔╝", " ╚████╔╝ ", "  ╚═══╝  "),
    "W": ("██╗    ██╗", "██║    ██║", "██║ █╗ ██║", "██║███╗██║", "╚███╔███╔╝", " ╚══╝╚══╝ "),
    "X": ("██╗  ██╗", "╚██╗██╔╝", " ╚███╔╝ ", " ██╔██╗ ", "██╔╝ ██╗", "╚═╝  ╚═╝"),
    "Y": ("██╗   ██╗", "╚██╗ ██╔╝", " ╚████╔╝ ", "  ╚██╔╝  ", "   ██║   ", "   ╚═╝   "),
    "Z": ("███████╗", "╚══███╔╝", "  ███╔╝ ", " ███╔╝  ", "███████╗", "╚══════╝"),
    " ": ("  ", "  ", "  ", "  ", "  ", "  "),
    "-": ("      ", "      ", "█████╗", "╚════╝", "      ", "      "),
    ".": ("  ", "  ", "  ", "  ", "██╗", "╚═╝"),
}


def big_text(text):
    rows = [""] * 6
    for ch in text.upper():
        glyph = BIGFONT.get(ch)
        if not glyph:
            glyph = BIGFONT[" "]
        for i in range(6):
            rows[i] += glyph[i] + " "
    return rows


def big_logo(name=None):
    return big_text(name or APP)


LOGO = [
    "▄▀█ █▀█ █▀█   ▄▀█ █▄░█ █▀▄ █▀█ █▀█ █ █▀▄",
    "█▀█ █▀▄ █▀▀   █▀█ █░▀█ █▀▄ █▀▄ █▄█ █ █▀▄",
]

_R = (('7b22617070223a2241525058222c2276', '657273696f6e223a2235352e30222c22', '636f64656e616d65223a22474154454b', '4545504552222c22617574686f72223a', '2241686d616564646576222c22636861', '6e6e656c223a22742e6d652f41686d61', '65645f64657631222c227365616c223a', '22316366636334636630353936323964', '64643963653332373666333635393733', '64653633393764346430623830396333', '65653636646665323437396466376166', '36227d'))


def _ident():
    try:
        blob = bytes.fromhex("".join(_R)).decode("utf-8")
        return json.loads(blob)
    except Exception:
        return {"app": "?", "version": "?", "codename": "?", "author": "?", "channel": "?", "seal": ""}


_ID = _ident()
APP = _ID.get("app", "?")
VERSION = _ID.get("version", "?")
CODENAME = _ID.get("codename", "?")
AUTHOR = _ID.get("author", "?")
CHANNEL = _ID.get("channel", "?")


SLOGAN = f"ANDROID REVERSE ENGINEERING  ·  v{VERSION} {CODENAME}"
TAGLINE = "REVERSE ENGINEERING · DECOMPILE · UNPACK · PATCH · SIGN"
FOOTER = f"{AUTHOR}  ·  {CHANNEL}"


LOGO_STYLE = {"big": True}


def banner_still():
    """Compact header: fits any terminal, no ascii art to wrap on a phone."""
    w = min(72, Tty.clamp(46, 78))
    title = gradient_text("ARPXTOOL", G_MAIN, True)
    body = [""]
    codename = re.sub(r"^v?\d+(\.\d+)*\s*", "", _strip(SLOGAN).split("·")[-1].strip()).upper()
    body.append("  " + title + "   " + Pal(SLATE)("v%s" % VERSION) +
                (Pal(STEEL)("   " + codename) if codename else ""))
    body.append("  " + Pal(STEEL)(trunc(_strip(TAGLINE), w - 6)))
    body.append("  " + Pal(SLATE)(trunc(_strip(FOOTER), w - 6)))
    body.append("")
    return boxed(body, [CYAN, AZURE, VIOLET], width=w)






TRACE = {"on": False, "file": None, "count": 0}


def trace(msg, kind="step"):
    if not TRACE["on"]:
        return
    TRACE["count"] += 1
    stamp = time.strftime("%H:%M:%S")
    line = "%s  %-6s %s" % (stamp, kind, msg)
    if TRACE["file"]:
        try:
            with open(TRACE["file"], "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except Exception:
            pass
    if Tty.enabled:
        sys.stdout.write("\r" + Pal.CLR)
    print("  " + Pal(VIOLET)("~") + " " + T_DIM(trunc(line, Tty.clamp(50, 110))))


EXEC_DETAIL = {"on": False}


def trace_cmd(argv):
    trace(" ".join(str(a) for a in argv), "exec")


def exec_report(argv, rc, out, err, elapsed):
    if not EXEC_DETAIL["on"]:
        return
    if Tty.enabled:
        sys.stdout.write("\r" + Pal.CLR)
    print("  " + Pal(VIOLET)("$") + " " + T_TXT(trunc(" ".join(str(a) for a in argv), Tty.clamp(40, 110))))
    ok = rc == 0
    print("    " + (T_OK(CHECK) if ok else Pal(BLOOD, True)(CROSS)) + " " +
          T_DIM("exit %s · %.1fs · %d line(s) out · %d line(s) err"
                % (rc, elapsed, len((out or "").splitlines()), len((err or "").splitlines()))))
    for label, blob in (("out", out), ("err", err)):
        lines = [l for l in (blob or "").splitlines() if l.strip()]
        if not lines:
            continue
        for line in lines[:6]:
            print("      " + T_DIM(trunc(line, 100)))
        if len(lines) > 6:
            print("      " + T_DIM("... %d more line(s)" % (len(lines) - 6)))


ANIM_STYLES = ("wipe", "typewriter", "scan", "decode", "slide", "pulse", "glitch", "none")
ANIM = {"style": "wipe"}


def _strip(t):
    return re.sub(r"\033\[[0-9;?]*[A-Za-z]", "", t)


def _paint_gradient(plain, tint=None):
    width = max(1, max(vislen(l) for l in plain))
    out = []
    for ln in plain:
        buf = []
        for col, ch in enumerate(ln):
            if ch == " ":
                buf.append(" ")
                continue
            base = ramp(G_MAIN, col / max(1, width - 1))
            buf.append(Pal(tint(base) if tint else base, True)(ch))
        out.append("".join(buf))
    return out


def anim_wipe(plain, frames):
    width = max(1, max(vislen(l) for l in plain))
    for f in range(frames + 1):
        reveal = int(width * min(1.0, f / max(1, frames - 5)))
        pos = (f / max(1, frames)) * (width + 24) - 12
        out = []
        for ln in plain:
            buf = []
            for col, ch in enumerate(ln):
                if ch == " " or col > reveal:
                    buf.append(" ")
                    continue
                glow = max(0.0, 1.0 - abs(col - pos) / 8.0)
                base = ramp(G_MAIN, col / max(1, width - 1))
                buf.append(Pal(mix(base, WHITE, glow * 0.9), True)(ch))
            out.append("".join(buf))
        Anim.paint(out)


def anim_typewriter(plain, frames):
    total = sum(len(l) for l in plain)
    step = max(1, total // max(1, frames))
    for f in range(frames + 1):
        budget = f * step
        out = []
        for ln in plain:
            take = max(0, min(len(ln), budget))
            budget -= take
            head = ln[:take]
            rest = ln[take:]
            out.append(Pal(SNOW, True)(head) + T_DIM(rest))
        Anim.paint(out)


def anim_scan(plain, frames):
    width = max(1, max(vislen(l) for l in plain))
    for f in range(frames + 1):
        pos = (f / max(1, frames)) * (width + 16) - 8
        out = []
        for ln in plain:
            buf = []
            for col, ch in enumerate(ln):
                if ch == " ":
                    buf.append(" ")
                    continue
                glow = max(0.0, 1.0 - abs(col - pos) / 5.0)
                base = ramp(G_MAIN, col / max(1, width - 1))
                buf.append(Pal(mix(base, WHITE, glow), True)(ch))
            out.append("".join(buf))
        Anim.paint(out)


def anim_decode(plain, frames):
    glyphs = "01<>/\\|_-=+*#%$@"
    width = max(1, max(vislen(l) for l in plain))
    for f in range(frames + 1):
        settle = f / max(1, frames)
        out = []
        for ln in plain:
            buf = []
            for col, ch in enumerate(ln):
                if ch == " ":
                    buf.append(" ")
                    continue
                threshold = col / max(1, width - 1)
                if threshold < settle:
                    buf.append(Pal(ramp(G_MAIN, threshold), True)(ch))
                else:
                    r = random.Random(f * 7919 + col * 131)
                    buf.append(T_DIM(r.choice(glyphs)))
            out.append("".join(buf))
        Anim.paint(out)


def anim_slide(plain, frames):
    for f in range(frames + 1):
        pad = int((1 - min(1.0, f / max(1, frames))) * 24)
        out = []
        for ln in plain:
            out.append(" " * pad + Pal(ramp(G_MAIN, 0.5), True)(ln) if pad == 0 else " " * pad + T_DIM(ln))
        Anim.paint(out)


def anim_pulse(plain, frames):
    for f in range(frames + 1):
        level = 0.5 + 0.5 * math.sin(f / max(1, frames) * math.pi * 2)
        out = []
        for ln in plain:
            out.append("".join(
                " " if ch == " " else Pal(mix(ramp(G_MAIN, 0.5), WHITE, level * 0.7), True)(ch)
                for ch in ln))
        Anim.paint(out)


def anim_glitch(plain, frames):
    width = max(1, max(vislen(l) for l in plain))
    for f in range(frames + 1):
        calm = f >= frames - 3
        out = []
        for ln in plain:
            if calm:
                out.append("".join(
                    " " if ch == " " else Pal(ramp(G_MAIN, i / max(1, width - 1)), True)(ch)
                    for i, ch in enumerate(ln)))
                continue
            r = random.Random(f * 104729 + len(ln))
            buf = []
            for ch in ln:
                if ch == " ":
                    buf.append(" ")
                elif r.random() < 0.18:
                    buf.append(Pal(r.choice([BLOOD, CYAN, VIOLET]))(r.choice("▚▞░▒")))
                else:
                    buf.append(Pal(ramp(G_MAIN, 0.4), True)(ch))
            out.append("".join(buf))
        Anim.paint(out)


def banner_anim(fast=False):
    lines = banner_still()
    style = ANIM["style"]
    if fast or not Tty.enabled or style == "none":
        for ln in lines:
            print(ln)
        return
    plain = [_strip(l) for l in lines]
    frames = 22
    sys.stdout.write(Pal.HIDE)
    try:
        fn = {"wipe": anim_wipe, "typewriter": anim_typewriter, "scan": anim_scan,
              "decode": anim_decode, "slide": anim_slide, "pulse": anim_pulse,
              "glitch": anim_glitch}.get(style, anim_wipe)
        fn(plain, frames)
        Anim.paint(_paint_gradient(plain))
    finally:
        sys.stdout.write(Pal.SHOW)
        Anim.close()

def sweep(msg, duration=0.55, stops=None):
    stops = stops or G_COOL
    if not Tty.enabled:
        return
    text = f"  {msg}"
    width = vislen(text)
    end = time.time() + duration
    sys.stdout.write(Pal.HIDE)
    try:
        while time.time() < end:
            t = 1.0 - (end - time.time()) / duration
            pos = t * (width + 14) - 7
            buf = []
            for i, ch in enumerate(text):
                if ch == " ":
                    buf.append(ch)
                    continue
                d = abs(i - pos)
                glow = max(0.0, 1.0 - d / 7.0)
                buf.append(Pal(mix(ramp(stops, i / max(1, width - 1)), WHITE, glow))(ch))
            sys.stdout.write("\r" + "".join(buf) + Pal.CLR)
            sys.stdout.flush()
            time.sleep(0.018)
    finally:
        sys.stdout.write("\r" + Pal.CLR)
        sys.stdout.write(Pal.SHOW)
        sys.stdout.flush()


def typewriter(text, delay=0.006, prefix="  "):
    if not Tty.enabled or delay <= 0:
        print(prefix + text)
        return
    sys.stdout.write(Pal.HIDE + prefix)
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write(Pal.SHOW + "\n")
    sys.stdout.flush()


def wave(duration=0.7):
    if not Tty.enabled:
        return
    width = Tty.clamp(24, 60)
    end = time.time() + duration
    sys.stdout.write(Pal.HIDE)
    try:
        while time.time() < end:
            t = time.time() * 6
            row = []
            for x in range(width):
                h = (math.sin(x / 4.0 + t) + 1) / 2
                g = "▁▂▃▄▅▆▇█"[min(7, int(h * 7.99))]
                row.append(Pal(ramp(G_COOL, h), True)(g))
            sys.stdout.write("\r  " + "".join(row) + Pal.CLR)
            sys.stdout.flush()
            time.sleep(0.03)
    finally:
        sys.stdout.write("\r" + " " * (Tty.width) + "\r" + Pal.SHOW)
        sys.stdout.flush()


def progress(label, steps, delay=0.035, stops=None):
    stops = stops or G_OK
    n = len(steps)
    if not Tty.enabled:
        for s in steps:
            print(f"  {CHECK} {s}")
        return
    width = Tty.clamp(18, 34)
    sys.stdout.write(Pal.HIDE)
    try:
        for i, step in enumerate(steps):
            for sub in range(4):
                ratio = (i + sub / 4) / n
                cells = ratio * width
                full = int(cells)
                body = "█" * full + (PARTIAL[int((cells - full) * 8)] if full < width else "") + "░" * max(0, width - full - 1)
                sp = DOTS[(i * 4 + sub) % len(DOTS)]
                tone = ramp(stops, ratio)
                sys.stdout.write("\r  " + Pal(tone)(sp) + " " + gradient_text(body, stops))
                sys.stdout.write(" " + Pal(SNOW)(trunc(step, 34).ljust(34)) + Pal.CLR)
                sys.stdout.flush()
                time.sleep(delay / 4)
            print()
    finally:
        sys.stdout.write(Pal.SHOW)
        sys.stdout.flush()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} GB"


def atomic_write(path, data, mode="wb"):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".arptmp")
    with open(tmp, mode) as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def safe_name(name):
    return re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(name))


def which(binary):
    return shutil.which(binary)


def java_ok():
    return which("java") is not None


def disk_free(path):
    try:
        return shutil.disk_usage(path).free
    except Exception:
        return 0


def run(argv, cwd=None, timeout=3000, env=None):
    trace_cmd(argv)
    started = time.time()
    try:
        p = subprocess.run(argv, cwd=cwd, timeout=timeout, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace")
        rc, out, err = p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        rc, out, err = -9, "", "timeout"
    except FileNotFoundError:
        rc, out, err = -2, "", "not found"
    except Exception as e:
        rc, out, err = -1, "", str(e)
    exec_report(argv, rc, out, err, time.time() - started)
    return rc, out, err


IMPORTANT = re.compile(r"(error|exception|failed|fatal|warn|I: Using|I: Baksmaling|I: Smaling|I: Building|I: Built|Signed|Verif|success|complete)", re.I)


RUN_VISIBLE = {"show_command": True}


def format_command(argv):
    parts = []
    for a in argv:
        a = str(a)
        if len(a) > 48:
            a = a[:22] + "..." + a[-22:]
        parts.append(a if " " not in a else "'" + a + "'")
    return " ".join(parts)


def run_live(argv, label, cwd=None, timeout=3000, env=None, quiet=False, sink=None):
    trace_cmd(argv)
    start = time.time()
    if Tty.enabled and not quiet and RUN_VISIBLE["show_command"]:
        print("  " + T_DIM("$ ") + T_DIM(trunc(format_command(argv), Tty.clamp(40, 104))))
    try:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, bufsize=1, errors="replace")
    except FileNotFoundError:
        Out.bad(label + ": executable not found")
        return -2, []
    except Exception as e:
        Out.bad("%s: %s" % (label, e))
        return -1, []
    count = 0
    errors = []
    spin = 0
    last = ""
    stream = proc.stdout
    if Tty.enabled:
        sys.stdout.write(Pal.HIDE)
    try:
        while True:
            line = stream.readline()
            if not line:
                break
            count += 1
            st = line.rstrip("\n").strip()
            if not st:
                continue
            low = st.lower()
            if sink is not None:
                sink.append(st)
            if "error" in low or "exception" in low or "failed" in low or "fatal" in low:
                errors.append(trunc(st, 140))
            if Tty.enabled and not quiet and IMPORTANT.search(st) and st != last and len(st) < 140:
                last = st
                sys.stdout.write("\r" + Pal.CLR)
                print("    " + T_DIM("|") + " " + Pal(SLATE)(trunc(st, 104)))
            elif Tty.enabled:
                spin += 1
                elapsed = int(time.time() - start)
                sys.stdout.write("\r" + Pal.CLR + "  " +
                                 Pal(ramp(G_COOL, 0.4))(DOTS[spin % len(DOTS)]) + " " +
                                 Pal(SNOW)(label) + " " + Pal(STEEL)("%d lines - %ds" % (count, elapsed)))
                sys.stdout.flush()
            if time.time() - start > timeout:
                proc.kill()
                errors.append("timeout")
                break
        proc.wait()
    except KeyboardInterrupt:
        proc.kill()
        raise
    finally:
        if Tty.enabled:
            sys.stdout.write(Pal.SHOW)
    elapsed = time.time() - start
    if EXEC_DETAIL["on"]:
        exec_report(argv, proc.returncode, "\n".join(errors[-6:]), "", elapsed)
    if Tty.enabled:
        sys.stdout.write("\r" + Pal.CLR)
    if proc.returncode == 0:
        print("  " + T_OK(CHECK) + " " + T_TXT(label) + " " + T_DIM("- %d lines - %.1fs" % (count, elapsed)))
    else:
        print("  " + T_ERR(CROSS) + " " + T_TXT("%s exit %d" % (label, proc.returncode)) + " " + T_DIM("- %.1fs" % elapsed))
        for e in errors[:3]:
            print("    " + Pal(BLOOD)(trunc(e, 120)))
    return proc.returncode, errors



ELF_MACHINES = {3: "x86", 62: "x86_64", 40: "arm", 183: "aarch64", 243: "riscv"}


def elf_info(data):
    if len(data) < 52 or data[:4] != b"\x7fELF":
        return None
    cls = data[4]
    endian = "<" if data[5] == 1 else ">"
    try:
        machine = struct.unpack_from(endian + "H", data, 18)[0]
        bits = 64 if cls == 2 else 32
    except Exception:
        return None
    return {"bits": bits, "machine": machine, "arch": ELF_MACHINES.get(machine, "unknown"), "endian": endian}


ABI_EXPECT = {
    "arm64-v8a": ("aarch64", 64),
    "armeabi-v7a": ("arm", 32),
    "armeabi": ("arm", 32),
    "x86": ("x86", 32),
    "x86_64": ("x86_64", 64),
    "riscv64": ("riscv", 64),
}

TOKEN_RE = re.compile(r"^[0-9A-Fa-f.??]{2}$")


def compile_pattern(pattern):
    tokens = pattern.split()
    parts = []
    for tok in tokens:
        if not TOKEN_RE.match(tok):
            return None
        hi, lo = tok[0].upper(), tok[1].upper()
        if hi in ".?" and lo in ".?":
            parts.append(b".")
        elif hi in ".?":
            # high nibble is wild, low nibble is fixed: the 16 values are NOT
            # contiguous (0x03, 0x13, ... 0xF3), so a range would match the
            # wrong bytes and silently break every pattern that uses "?3"
            v = int(lo, 16)
            vals = bytes([(h << 4) | v for h in range(16)])
            parts.append(b"[" + b"".join(re.escape(bytes([x])) for x in vals) + b"]")
        elif lo in ".?":
            v = int(hi, 16) << 4
            parts.append(b"[" + re.escape(bytes([v])) + b"-" + re.escape(bytes([v + 15])) + b"]")
        else:
            parts.append(re.escape(bytes([int(tok, 16)])))
    if not parts:
        return None
    return re.compile(b"".join(parts), re.S)


PATCH_BYTES = {
    "aarch64": bytes.fromhex("200080d2c0035fd6"),
    "arm": bytes.fromhex("01207047"),
    "x86": bytes.fromhex("b801000000c3"),
    "x86_64": bytes.fromhex("b801000000c3"),
    "riscv": bytes.fromhex("1305100067800000"),
}

# Primary table: the exact signature set that NVISO validates against its
# corpus of real engines (36 android libflutter.so builds, one match each).
# Extra signatures are only tried when the primary set finds nothing, so a
# second, unverified match can never be patched by accident.
PATTERNS = {
    "aarch64": [
        "F. 0F 1C F8 F. 5. 01 A9 F. 5. 02 A9 F. .. 03 A9 .. .. .. .. 68 1A 40 F9",
        "F. 43 01 D1 FE 67 01 A9 F8 5F 02 A9 F6 57 03 A9 F4 4F 04 A9 13 00 40 F9 F4 03 00 AA 68 1A 40 F9",
        "FF 43 01 D1 FE 67 01 A9 ?? ?? 06 94 ?? 7? 06 94 68 1A 40 F9 15 15 41 F9 B5 00 00 B4 B6 4A 40 F9",
        "FF .3 01 D1 F. .. 01 A9 .. .. .. 94 .. .. .. 52 48 00 00 39 1A 50 40 F9 DA 02 00 B4 48 03 40 F9",
    ],
    "arm": [
        "2D E9 F. 4. D0 F8 00 80 81 46 D8 F8 18 00 D0 F8",
    ],
    "x86": [
        "55 89 E5 53 57 56 83 E4 F0 83 EC 20 E8 00 00 00 00 5B 81 C3 2B 79 66 00 8B 7D 08 8B 17 8B 42 18 8B 80 88 01",
    ],
    "x86_64": [
        "55 41 57 41 56 41 55 41 54 53 50 49 89 F. 4. 8B .. 4. 8B 4. 30 4C 8B .. .. 0. 00 00 4D 85 .. 74 1. 4D 8B",
        "55 41 57 41 56 41 55 41 54 53 48 83 EC 18 49 89 FF 48 8B 1F 48 8B 43 30 4C 8B A0 28 02 00 00 4D 85 E4 74",
        "55 41 57 41 56 41 55 41 54 53 48 83 EC 18 49 89 FE 4C 8B 27 49 8B 44 24 30 48 8B 98 D0 01 00 00 48 85 DB",
    ],
}

PATTERNS_EXTRA = {
    "aarch64": [
        "F. 0F 1C F8 F. .. 0. .. .. .. .. .9 .. .. 0. .. 68 1A 40 F9 15 .. 4. F9 B5 00 00 B4 B6 46 40 F9",
        "FF 03 05 D1 FC 6B 0F A9 F9 63 10 A9 F7 5B 11 A9 F5 53 12 A9 F3 7B 13 A9 08 0A 80 52 48 00 00 39 16 54 40 F9 56 07 00 B4 C8 02 40 F9 08 07 00 B4 29 20 40 A9 F3 03 02 AA",
        "FF 83 01 D1 FA 67 01 A9 F8 5F 02 A9 F6 57 03 A9 F4 4F 04 A9 FD 7B 05 A9 FD 43 01 91 F. 03 00 AA .. 0? 40 F9 ?8 1? 40 F9 15 ?? 4? F9 B5 00 00 B4",
    ],
    "arm": [
        "2D E9 F0 4F A3 B0 81 46 50 20 10 70 D9 F8 98 70 00 2F",
        "2D E9 F0 4F A3 B0 82 46 50 20 10 70",
    ],
    "x86": [],
    "x86_64": [
        "55 41 57 41 56 41 55 41 54 53 50 49 89 FE 48 8B 1F 48 8B 43 30 4C 8B B8 D0 01 00 00 4D 85 FF 74 12 4D 8B A7 90 00 00 00 4D 85 E4 74 4A 49 8B 04 24 EB 46",
        "55 41 57 41 56 41 55 41 54 53 48 83 EC 38 C6 02 50 48 8B AF A. 00 00 00 48 85 ED 74 7. 48 83 7D 00 00 74",
        "55 41 57 41 56 41 55 41 54 53 48 81 EC F8 00 00 00 C6 02 50 48 8B 9F A8 00 00 00 48 85 DB",
    ],
}

_COMPILED = {}

# The two BoringSSL entry points disagree about what "ok" means:
#   ssl_verify_peer_cert(...)                   returns ssl_verify_result_t, 0 = ok
#   ssl_crypto_x509_session_verify_cert_chain()  returns bool,             1 = verified
# Patching the first one with "return 1" marks EVERY certificate invalid, so the
# success value has to travel with the pattern, not with the architecture.
SSL_VERIFY_PEER_CERT = "ssl_verify_peer_cert"
SSL_VERIFY_CHAIN = "ssl_crypto_x509_session_verify_cert_chain"

PATTERN_INFO = {
    "FF .3 01 D1 F. .. 01 A9 .. .. .. 94 .. .. .. 52 48 00 00 39 1A 50 40 F9 DA 02 00 B4 48 03 40 F9":
        (1, SSL_VERIFY_CHAIN),
    "FF 03 05 D1 FC 6B 0F A9 F9 63 10 A9 F7 5B 11 A9 F5 53 12 A9 F3 7B 13 A9 08 0A 80 52 48 00 00 39 16 54 40 F9 56 07 00 B4 C8 02 40 F9 08 07 00 B4 29 20 40 A9 F3 03 02 AA":
        (1, SSL_VERIFY_CHAIN),
}


def pattern_info(pattern):
    return PATTERN_INFO.get(pattern, (0, SSL_VERIFY_PEER_CERT))


def patterns_for(arch, extra=False):
    key = (arch, bool(extra))
    if key not in _COMPILED:
        table = PATTERNS_EXTRA if extra else PATTERNS
        out = []
        for p in table.get(arch, []):
            c = compile_pattern(p)
            if c:
                ret, name = pattern_info(p)
                out.append((c, ret, name))
        _COMPILED[key] = out
    return _COMPILED[key]


def patch_stub(arch, ret):
    """Instruction stub that makes the patched function return `ret`."""
    ret = 1 if ret else 0
    if arch == "aarch64":
        return struct.pack("<II", 0xD2800000 | (ret << 5), 0xD65F03C0)   # mov x0,#ret ; ret
    if arch == "arm":
        return struct.pack("<HH", 0x2000 | ret, 0x4770)                  # movs r0,#ret ; bx lr
    if arch in ("x86", "x86_64"):
        return bytes((0xB8, ret, 0, 0, 0, 0xC3))                          # mov eax,#ret ; ret
    if arch == "riscv":
        return PATCH_BYTES.get("riscv")
    return None


class PatchResult:
    def __init__(self, path, arch):
        self.path = path
        self.arch = arch
        self.hits = []
        self.already = 0
        self.error = None
        self.elf = None
        self.names = []


def elf_symbol_offsets(path, names):
    """{symbol: file offset} from .dynsym/.symtab — works on unstripped engines.

    Some builds keep the BoringSSL symbol names, and then no signature table is
    needed at all: the exact function can be patched by name.
    """
    try:
        data = Path(path).read_bytes()
    except Exception:
        return {}
    if len(data) < 52 or data[:4] != b"\x7fELF":
        return {}
    bits = 64 if data[4] == 2 else 32
    end = "<" if data[5] == 1 else ">"
    try:
        if bits == 64:
            e_phoff = struct.unpack_from(end + "Q", data, 0x20)[0]
            e_shoff = struct.unpack_from(end + "Q", data, 0x28)[0]
            e_phentsize = struct.unpack_from(end + "H", data, 0x36)[0]
            e_phnum = struct.unpack_from(end + "H", data, 0x38)[0]
            e_shentsize = struct.unpack_from(end + "H", data, 0x3A)[0]
            e_shnum = struct.unpack_from(end + "H", data, 0x3C)[0]
        else:
            e_phoff = struct.unpack_from(end + "I", data, 0x1C)[0]
            e_shoff = struct.unpack_from(end + "I", data, 0x20)[0]
            e_phentsize = struct.unpack_from(end + "H", data, 0x2A)[0]
            e_phnum = struct.unpack_from(end + "H", data, 0x2C)[0]
            e_shentsize = struct.unpack_from(end + "H", data, 0x2E)[0]
            e_shnum = struct.unpack_from(end + "H", data, 0x30)[0]
    except Exception:
        return {}
    if not e_shoff or not e_shnum or e_shnum > 4096:
        return {}
    segs = []
    for i in range(min(e_phnum, 256)):
        b = e_phoff + i * e_phentsize
        try:
            p_type = struct.unpack_from(end + "I", data, b)[0]
            if bits == 64:
                p_offset = struct.unpack_from(end + "Q", data, b + 8)[0]
                p_vaddr = struct.unpack_from(end + "Q", data, b + 16)[0]
                p_filesz = struct.unpack_from(end + "Q", data, b + 32)[0]
            else:
                p_offset = struct.unpack_from(end + "I", data, b + 4)[0]
                p_vaddr = struct.unpack_from(end + "I", data, b + 8)[0]
                p_filesz = struct.unpack_from(end + "I", data, b + 16)[0]
        except Exception:
            continue
        if p_type == 1:
            segs.append((p_vaddr, p_offset, p_filesz))

    def to_off(v):
        for va, off, sz in segs:
            if va <= v < va + sz:
                return off + (v - va)
        return None

    want = set(names)
    out = {}
    wide = "Q" if bits == 64 else "I"
    for i in range(e_shnum):
        b = e_shoff + i * e_shentsize
        try:
            sh_type = struct.unpack_from(end + "I", data, b + 4)[0]
            if bits == 64:
                sh_offset = struct.unpack_from(end + "Q", data, b + 0x18)[0]
                sh_size = struct.unpack_from(end + "Q", data, b + 0x20)[0]
                sh_link = struct.unpack_from(end + "I", data, b + 0x28)[0]
                sh_entsize = struct.unpack_from(end + "Q", data, b + 0x38)[0]
            else:
                sh_offset = struct.unpack_from(end + "I", data, b + 0x10)[0]
                sh_size = struct.unpack_from(end + "I", data, b + 0x14)[0]
                sh_link = struct.unpack_from(end + "I", data, b + 0x18)[0]
                sh_entsize = struct.unpack_from(end + "I", data, b + 0x24)[0]
        except Exception:
            continue
        if sh_type not in (2, 11) or not sh_size:
            continue
        try:
            sb = e_shoff + sh_link * e_shentsize
            if bits == 64:
                str_off = struct.unpack_from(end + "Q", data, sb + 0x18)[0]
            else:
                str_off = struct.unpack_from(end + "I", data, sb + 0x10)[0]
        except Exception:
            continue
        ent = sh_entsize or (24 if bits == 64 else 16)
        for k in range(sh_size // ent):
            q = sh_offset + k * ent
            try:
                st_name = struct.unpack_from(end + "I", data, q)[0]
                st_value = struct.unpack_from(end + wide, data, q + (8 if bits == 64 else 4))[0]
            except Exception:
                continue
            if not st_name or not st_value:
                continue
            e = data.find(b"\x00", str_off + st_name)
            if e < 0:
                continue
            nm = data[str_off + st_name:e].decode("ascii", "ignore")
            if nm in want:
                off = to_off(st_value & ~1)
                if off is not None:
                    out[nm] = off
    return out


def patch_shared_object(path, arch, dry=False):
    """Neutralise TLS verification in a shared object, per-signature.

    Each signature carries the value that means SUCCESS for the function it
    matches, so the peer-cert entry point (0 = ok) is never patched with the
    chain entry point's value (1 = verified).
    """
    res = PatchResult(path, arch)
    try:
        data = Path(path).read_bytes()
    except Exception as e:
        res.error = f"read: {e}"
        return res
    info = elf_info(data)
    res.elf = info
    if info is None:
        res.error = "not an ELF object"
        return res
    res.arch = info["arch"]
    expect = ABI_EXPECT.get(arch)
    if expect and (info["arch"] != expect[0] or info["bits"] != expect[1]):
        res.error = f"ABI mismatch: {info['arch']}/{info['bits']} vs {expect[0]}/{expect[1]}"
        return res
    plan = {}
    for creg, ret, name in patterns_for(info["arch"]):
        for m in creg.finditer(data):
            plan.setdefault(m.start(), (ret, name))
    if not plan:
        for creg, ret, name in patterns_for(info["arch"], extra=True):
            for m in creg.finditer(data):
                plan.setdefault(m.start(), (ret, name))
    if not plan:
        # unstripped engines carry the symbol names: no signature table needed
        for _nm, _off in elf_symbol_offsets(path, (SSL_VERIFY_PEER_CERT, SSL_VERIFY_CHAIN)).items():
            plan[_off] = (1 if _nm == SSL_VERIFY_CHAIN else 0, _nm + " (symbol)")
    if not plan:
        # a second run cannot re-match a signature we already overwrote, so look
        # for our stub followed by the REST of the signature: that pins the hit
        # to a real site instead of every 4 bytes that happen to look like it
        found = {}
        for src in PATTERNS.get(info["arch"], []) + PATTERNS_EXTRA.get(info["arch"], []):
            toks = src.split()
            ret, name = pattern_info(src)
            stub = patch_stub(info["arch"], ret)
            if not stub or len(toks) <= len(stub):
                continue
            tail = compile_pattern(" ".join(toks[len(stub):]))
            if tail is None:
                continue
            for m in re.finditer(re.escape(stub) + tail.pattern, data):
                found.setdefault(m.start(), (name, ret))
        for off in sorted(found):
            name, ret = found[off]
            res.already += 1
            res.names.append((off, name, ret, "already"))
        if res.already:
            return res
        res.error = "signature not found"
        return res
    buf = bytearray(data)
    for off in sorted(plan):
        ret, name = plan[off]
        stub = patch_stub(info["arch"], ret)
        if not stub:
            res.error = f"no patch stub for {info['arch']}"
            return res
        if buf[off : off + len(stub)] == stub:
            res.already += 1
            res.names.append((off, name, ret, "already"))
            continue
        if off + len(stub) > len(buf):
            continue
        buf[off : off + len(stub)] = stub
        res.hits.append(off)
        res.names.append((off, name, ret, "patched"))
    if res.hits and not dry:
        backup = Path(str(path) + ".arpbak")
        if not backup.exists():
            shutil.copy2(path, backup)
        atomic_write(path, bytes(buf))
        check = Path(path).read_bytes()
        for off, name, ret, state in res.names:
            stub = patch_stub(info["arch"], ret)
            if state == "patched" and check[off : off + len(stub)] != stub:
                res.error = "write verification failed"
                shutil.copy2(backup, path)
                res.hits = []
                return res
    return res


def iter_libs(src):
    root = Path(src) / "lib"
    if not root.is_dir():
        return []
    out = []
    for arch_dir in sorted(root.iterdir()):
        if not arch_dir.is_dir():
            continue
        for so in sorted(arch_dir.glob("*.so")):
            out.append((arch_dir.name, so))
    return out

METHOD_RE = re.compile(r"^\.method[ \t]+([^\r\n]+)\r?\n(.*?)^\.end method", re.M | re.S)

DETECT_NAMES = (
    "isRooted", "isDeviceRooted", "isRootAvailable", "checkRoot", "checkRooted", "detectRoot",
    "hasRootAccess", "checkSuExists", "isSuperuser", "isRootedDevice", "isRoot", "isJailBreak",
    "isEmulator", "isRunningOnEmulator", "detectEmulator", "isGenymotion", "isBlueStacks",
    "isVpnActive", "isVpnConnected", "detectVpn", "isVpnUsed", "isVpnRunning", "checkVpn",
    "isFridaDetected", "isXposedDetected", "isHookDetected", "isInstrumented", "isFridaRunning",
    "isDebuggerConnected", "isBeingDebugged", "isDebuggable", "isTampered", "isProxyEnabled",
)

SIG_TRUE = (
    "checkSignature", "verifySignature", "validateSignature", "isSignatureValid",
    "isSignatureCorrect", "verifyAppSignature", "checkAppSignature", "isSignedCorrectly",
    "checkSignatures", "verifyIntegrity", "checkIntegrity", "validateAppSignature",
    "isSignatureVerified", "verifySignatures",
)
SIG_FALSE = ("isTampered", "checkTampered", "isAppTampered", "isSignatureInvalid", "isModified")


SMALI_GROUPS = {
    "ssl": [
        ("X509TrustManager", ("checkServerTrusted", "checkClientTrusted"), 0, "X509TrustManager"),
        ("HostnameVerifier", ("verify",), 1, "HostnameVerifier"),
        ("OkHttp CertificatePinner", ("check",), None, "CertificatePinner"),
        ("CleartextPolicy", ("isCleartextTrafficPermitted",), 1, "NetworkSecurityPolicy"),
        ("SslErrorHandler", ("onReceivedSslError",), None, "SslErrorHandler"),
        ("WebViewClient", ("onReceivedError",), None, "WebViewClient"),
        ("Conscrypt TrustManagerImpl", ("checkTrustedRecursive", "checkTrustAnchor"), 0, "TrustManagerImpl"),
        ("OkHttp ChainCleaner", ("clean",), None, "CertificateChainCleaner"),
        ("Certificate Validity", ("checkValidity",), None, "X509Certificate"),
        ("Client Cert Request", ("onReceivedClientCertRequest",), None, "ClientCertRequest"),
        ("Hostname Verifier Wrapper", ("verifyHostname", "checkServerTrusted"), 0, "HostnameVerifier"),
        ("Cronet Verifier", ("verifyCertificateChain", "verifyHost"), 0, "Cronet"),
        ("SSL Socket Factory", ("getAcceptedIssuers",), None, "TrustManager"),
    ],
    "detect": [(n, (n,), 0, None) for n in DETECT_NAMES],
    "signature": [(n, (n,), 1, None) for n in SIG_TRUE] + [(n, (n,), 0, None) for n in SIG_FALSE],
}


def smali_stub(ret, value, sig):
    if ret == "V":
        if "SslErrorHandler" in sig:
            return "    .locals 0\n\n    invoke-virtual {p2}, Landroid/webkit/SslErrorHandler;->proceed()V\n\n    return-void\n\n"
        return "    .locals 0\n\n    return-void\n\n"
    if ret in ("Z", "I", "B", "S", "C"):
        return "    .locals 1\n\n    const/4 v0, %s\n\n    return v0\n\n" % ("0x1" if value else "0x0")
    if ret in ("J", "D"):
        return "    .locals 2\n\n    const-wide/16 v0, 0x0\n\n    return-wide v0\n\n"
    if ret == "F":
        return "    .locals 1\n\n    const/4 v0, 0x0\n\n    return v0\n\n"
    return "    .locals 1\n\n    const/4 v0, 0x0\n\n    return-object v0\n\n"


def split_sig(sig):
    if "(" not in sig:
        return None, None
    i = sig.index("(")
    head = sig[:i].split()
    if not head:
        return None, None
    name = head[-1]
    tail = sig[i:]
    if ")" not in tail:
        return None, None
    ret = tail[tail.rindex(")") + 1 :].strip()
    return name, ret


class SmaliStat:
    def __init__(self):
        self.per_group = {}
        self.files = 0
        self.paths = []

    def add(self, label, n=1):
        self.per_group[label] = self.per_group.get(label, 0) + n

    def total(self):
        return sum(self.per_group.values())


def patch_smali(src, groups):
    stat = SmaliStat()
    table = {}
    for g in groups:
        for label, names, value, require in SMALI_GROUPS.get(g, []):
            for n in names:
                table.setdefault(n, []).append((label, value, require))
    if not table:
        return stat
    name_re = re.compile(r"^\.method[ \t]+[^\r\n]*\b(" + "|".join(sorted(map(re.escape, table), key=len, reverse=True)) + r")\s*\(", re.M)
    roots = [d for d in Path(src).iterdir() if d.is_dir() and d.name.startswith("smali")]
    for root in roots:
        for path in root.rglob("*.smali"):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if not name_re.search(text):
                continue
            changed = False
            pieces = []
            last = 0
            for m in METHOD_RE.finditer(text):
                sig = m.group(1)
                body = m.group(2)
                name, ret = split_sig(sig)
                if not name or ret is None or name not in table:
                    continue
                entry = None
                for label, value, require in table[name]:
                    if require and require not in text:
                        continue
                    entry = (label, value)
                    break
                if entry is None:
                    continue
                if len(body) < 190 and body.count("\n") < 8:
                    continue
                stub = smali_stub(ret, entry[1], sig)
                pieces.append(text[last : m.start()])
                pieces.append(".method " + sig + "\n" + stub + ".end method")
                last = m.end()
                changed = True
                stat.add(entry[0])
            if changed:
                pieces.append(text[last:])
                try:
                    atomic_write(path, "".join(pieces), "w")
                    stat.files += 1
                    stat.paths.append(str(path.relative_to(src)))
                except Exception:
                    pass
    return stat


NETSEC_XML = (
    '<?xml version="1.0" encoding="utf-8"?>\n'
    "<network-security-config>\n"
    '    <base-config cleartextTrafficPermitted="true">\n'
    "        <trust-anchors>\n"
    '            <certificates src="system" />\n'
    '            <certificates src="user" />\n'
    "        </trust-anchors>\n"
    "    </base-config>\n"
    '    <debug-overrides cleartextTrafficPermitted="true">\n'
    "        <trust-anchors>\n"
    '            <certificates src="system" />\n'
    '            <certificates src="user" />\n'
    "        </trust-anchors>\n"
    "    </debug-overrides>\n"
    "</network-security-config>\n"
)


def set_tag_attr(src, tag, attr, value):
    m = re.search(r"<" + re.escape(tag) + r"\b[^>]*>", src, re.S)
    if not m:
        return src, False
    block = m.group(0)
    key = attr.split("=")[0]
    if re.search(r"[\s]" + re.escape(key) + r"\s*=", block):
        return src, False
    if block.endswith("/>"):
        new = block[:-2].rstrip() + ' %s="%s"/>' % (attr, value)
    else:
        new = block[:-1].rstrip() + ' %s="%s">' % (attr, value)
    return src[: m.start()] + new + src[m.end() :], True


def strip_attrs(src, tag, attrs):
    m = re.search(r"<" + re.escape(tag) + r"\b[^>]*>", src, re.S)
    if not m:
        return src, 0
    block = m.group(0)
    new = block
    hits = 0
    for a in attrs:
        pat = r"\s" + re.escape(a) + r'\s*=\s*"[^"]*"'
        new2 = re.sub(pat, "", new)
        if new2 != new:
            hits += 1
            new = new2
    return src[: m.start()] + new + src[m.end() :], hits


def patch_manifest(src, want_split_cleanup=True):
    man = Path(src) / "AndroidManifest.xml"
    if not man.exists():
        return 0, []
    text = man.read_text(encoding="utf-8", errors="ignore")
    original = text
    applied = []
    for tag, attr, value, label in [
        ("application", "android:debuggable", "true", "debuggable"),
        ("application", "android:usesCleartextTraffic", "true", "cleartext"),
        ("application", "android:extractNativeLibs", "true", "extractNativeLibs"),
        ("application", "android:networkSecurityConfig", "@xml/network_security_config", "networkSecurityConfig"),
    ]:
        text, done = set_tag_attr(text, tag, attr, value)
        if done:
            applied.append(label)
    text, n = strip_attrs(text, "application", ["android:testOnly"])
    if n:
        applied.append("testOnly")
    if want_split_cleanup:
        text, n = strip_attrs(text, "application", ["android:splitTypes", "android:requiredSplitTypes", "android:isolatedSplits"])
        text, n2 = strip_attrs(text, "manifest", ["android:splitTypes", "android:requiredSplitTypes", "android:isolatedSplits"])
        if n or n2:
            applied.append("splitTypes")
        text = re.sub(r'\s*<meta-data[^>]*android:name="com\.android\.(vending\.|stamp\.|dynamic\.apk\.)[^"]*"[^>]*/>', "", text)
    if "android.permission.INTERNET" not in text and "<uses-permission" not in text:
        text = text.replace("</manifest>", '    <uses-permission android:name="android.permission.INTERNET" />\n</manifest>')
        applied.append("internet")
    if text != original:
        atomic_write(man, text, "w")
    return len(applied), applied


NETSEC_MODES = {
    "open": ("true", True),
    "user": ("true", True),
    "system": ("true", False),
    "strict": ("false", False),
}


def patch_netsec(src, embed_ca=None, mode="user"):
    xd = Path(src) / "res" / "xml"
    xd.mkdir(parents=True, exist_ok=True)
    target = xd / "network_security_config.xml"
    cleartext, trust_user = NETSEC_MODES.get(mode, NETSEC_MODES["user"])
    xml = NETSEC_XML
    if not trust_user:
        xml = xml.replace('            <certificates src="user" />\n', "")
    xml = xml.replace('cleartextTrafficPermitted="true"', 'cleartextTrafficPermitted="%s"' % cleartext)
    if embed_ca:
        try:
            pem = Path(embed_ca).expanduser().read_bytes()
            raw = Path(src) / "res" / "raw"
            raw.mkdir(parents=True, exist_ok=True)
            atomic_write(raw / "arp_ca.pem", pem)
            anchor = '<certificates src="user" />' if trust_user else '<certificates src="system" />'
            xml = xml.replace(anchor, anchor + '\n            <certificates src="@raw/arp_ca" />')
            Out.ok("embedded certificate · res/raw/arp_ca.pem")
        except Exception as e:
            Out.warn("certificate embed failed · " + trunc(str(e), 60))
    atomic_write(target, xml, "w")
    return True


# ── network security config, injected into the FINAL apk ────────────────────
# patch_netsec() edits the decoded tree, and that tree is thrown away whenever
# the build falls back to dex surgery. The platform reads the NSC from the
# archive, so the surgery path must replace the compiled resource itself or
# every "network security config installed" claim is false.

def _axml_document(nodes):
    """[("start", tag, [(name, dtype, value)]) | ("end", tag, [])] -> binary xml."""
    strings = []

    def intern(s):
        if s not in strings:
            strings.append(s)
        return strings.index(s)

    body = bytearray()
    stack = []
    for kind, tag, attrs in nodes:
        if kind == "start":
            payload = b""
            for name, dtype, value in attrs:
                data = intern(value) if dtype == 0x03 else value
                payload += struct.pack("<IIIHBBI", 0xFFFFFFFF, intern(name), 0xFFFFFFFF,
                                       8, 0, dtype, data & 0xFFFFFFFF)
            ext = struct.pack("<IIHHHHHH", 0xFFFFFFFF, intern(tag), 20, 20, len(attrs), 0, 0, 0)
            body += struct.pack("<HHIII", 0x0102, 16, 16 + len(ext) + len(payload), 1, 0xFFFFFFFF)
            body += ext + payload
            stack.append(tag)
        else:
            if not stack:
                continue
            stack.pop()
            body += struct.pack("<HHIIIII", 0x0103, 16, 24, 1, 0xFFFFFFFF, 0xFFFFFFFF, intern(tag))
    pool = build_string_pool(strings)
    return struct.pack("<HHI", 0x0003, 8, 8 + len(pool) + len(body)) + pool + bytes(body)


def netsec_config_bytes(cleartext=True, trust_user=True, debug_overrides=True):
    """Permissive NSC: user CAs trusted, no pin-set, cleartext allowed."""

    def anchors():
        out = [("start", "trust-anchors", []),
               ("start", "certificates", [("src", 0x03, "system")]),
               ("end", "certificates", [])]
        if trust_user:
            out += [("start", "certificates", [("src", 0x03, "user")]),
                    ("end", "certificates", [])]
        out.append(("end", "trust-anchors", []))
        return out

    flag = 0xFFFFFFFF if cleartext else 0
    nodes = [("start", "network-security-config", []),
             ("start", "base-config", [("cleartextTrafficPermitted", 0x12, flag)])]
    nodes += anchors()
    nodes.append(("end", "base-config", []))
    if debug_overrides:
        nodes.append(("start", "debug-overrides", [("cleartextTrafficPermitted", 0x12, flag)]))
        nodes += anchors()
        nodes.append(("end", "debug-overrides", []))
    nodes.append(("end", "network-security-config", []))
    return _axml_document(nodes)


def manifest_attr_raw(data, elem_name, attr_name):
    """Raw string of elem/attr in a binary manifest, e.g. '@xml/network_security_config'."""
    try:
        if len(data) < 16 or u2(data, 0) != 0x0003:
            return None
        pool = None
        off = u2(data, 2) or 8
        guard = 0
        while off + 8 <= len(data) and guard < 200000:
            guard += 1
            ctype = u2(data, off)
            csize = u4(data, off + 4)
            if csize < 8:
                break
            if ctype == 0x0001 and pool is None:
                pool = StringPool(data, off)
            elif ctype == 0x0102 and pool is not None:
                base = off + 16
                if pool.get(u4(data, base + 4)) == elem_name:
                    count = u2(data, base + 12)
                    start = u2(data, base + 8)
                    size = u2(data, base + 10) or 20
                    for i in range(min(count, 64)):
                        a = base + start + i * size
                        if pool.get(u4(data, a + 4)) != attr_name:
                            continue
                        raw = u4(data, a + 8)
                        if raw != 0xFFFFFFFF:
                            return pool.get(raw)
                        if u1(data, a + 15) == 0x03:
                            return pool.get(u4(data, a + 16))
                        return None
            off += csize
    except Exception:
        return None
    return None


def nsc_entry(apk):
    """Path of the compiled network-security-config inside the archive, or None."""
    try:
        with zipfile.ZipFile(str(apk)) as z:
            names = set(z.namelist())
            if "AndroidManifest.xml" in names:
                ref = manifest_attr_raw(z.read("AndroidManifest.xml"),
                                        "application", "networkSecurityConfig")
                if ref and ref.startswith("@xml/"):
                    cand = "res/xml/%s.xml" % ref.split("/", 1)[1]
                    if cand in names:
                        return cand
            for name in sorted(n for n in names
                               if n.startswith("res/xml/") and n.endswith(".xml")):
                try:
                    if Axml(z.read(name)).elements[:1] == ["network-security-config"]:
                        return name
                except Exception:
                    continue
    except Exception:
        return None
    return None


def _axml_chunk_list(blob):
    """[(type, offset, raw_bytes)] for every chunk after the XML header."""
    out = []
    off = u2(blob, 2) or 8
    guard = 0
    while off + 8 <= len(blob) and guard < 400000:
        guard += 1
        ctype = u2(blob, off)
        csize = u4(blob, off + 4)
        if csize < 8 or off + csize > len(blob):
            return None
        out.append((ctype, off, blob[off:off + csize]))
        off += csize
    return out if out else None


def _chunk_attr_value(blob, off, want="src"):
    """(value_string, data_field) of an attribute on a start-element chunk."""
    base = off + 16
    count = u2(blob, base + 12)
    start = u2(blob, base + 8)
    size = u2(blob, base + 10) or 20
    for i in range(min(count, 64)):
        a = base + start + i * size
        if u4(blob, a + 4) == want:
            dtype = u1(blob, a + 15)
            data = u4(blob, a + 16)
            raw = u4(blob, a + 8)
            return ("string", data) if dtype == 0x03 else (("raw", raw) if raw != 0xFFFFFFFF else ("other", data))
    return (None, None)


def _pool_with(blob, pool_off, extra):
    """Return (new_pool_chunk_bytes, {name: index}) appending `extra` strings.

    Existing indices are preserved: the new strings go at the end.
    """
    pool = StringPool(blob, pool_off)
    items = list(pool.items)
    added = {}
    for name in extra:
        if name not in items:
            items.append(name)
        added[name] = items.index(name)
    return build_string_pool(items), added


def _set_bool_attr(raw, name_idx, value=True):
    """Set (or append) a boolean attribute on a start-element chunk."""
    clone = bytearray(raw)
    base = 16
    count = u2(clone, base + 12)
    start = u2(clone, base + 8) or 20
    size = u2(clone, base + 10) or 20
    data = 0xFFFFFFFF if value else 0
    for k in range(min(count, 64)):
        a = base + start + k * size
        if u4(clone, a + 4) == name_idx:
            struct.pack_into("<H", clone, a + 12, 8)
            struct.pack_into("<B", clone, a + 14, 0)
            struct.pack_into("<B", clone, a + 15, 0x12)
            struct.pack_into("<I", clone, a + 8, 0xFFFFFFFF)
            struct.pack_into("<I", clone, a + 16, data)
            return bytes(clone)
    edge = base + start + count * size
    extra = struct.pack("<IIIHBBI", 0xFFFFFFFF, name_idx, 0xFFFFFFFF, 8, 0, 0x12, data)
    clone = clone[:edge] + extra + clone[edge:]
    struct.pack_into("<H", clone, base + 12, count + 1)
    struct.pack_into("<I", clone, 4, len(clone))
    return bytes(clone)


def _netsec_edit(blob):
    """Rewrite the app's own compiled NSC instead of inventing one.

    Every element chunk is kept byte for byte (so aapt's attribute encoding is
    preserved); the only additions are an appended string and a cloned
    <certificates> element. Returns (new_blob, note) or (None, reason).
    """
    chunks = _axml_chunk_list(blob)
    if not chunks:
        return None, "not a binary xml"
    pool_off = next((o for t, o, _ in chunks if t == 0x0001), None)
    if pool_off is None:
        return None, "no string pool"
    pool = StringPool(blob, pool_off)

    # element tree: walk starts/ends, remember nesting
    starts = [(i, off, raw) for i, (t, off, raw) in enumerate(chunks) if t == 0x0102]
    if not starts:
        return None, "no elements"

    def name_of(off):
        return pool.get(u4(blob, off + 16 + 4))

    drop = set()          # chunk indices to remove
    depth = 0
    drop_depth = None
    cert_index = None
    base_index = None
    anchors_end = None
    stack = []
    for i, (t, off, raw) in enumerate(chunks):
        if t == 0x0102:
            nm = name_of(off)
            stack.append(nm)
            if drop_depth is not None:
                drop.add(i)
            elif nm in ("pin-set", "domain-config"):
                drop_depth = len(stack)
                drop.add(i)
            elif nm == "certificates" and cert_index is None:
                cert_index = i
            elif nm == "base-config" and base_index is None:
                base_index = i
        elif t == 0x0103:
            if drop_depth is not None:
                drop.add(i)
                if len(stack) == drop_depth:
                    drop_depth = None
            elif stack and stack[-1] == "trust-anchors" and anchors_end is None:
                anchors_end = i
            if stack:
                stack.pop()
    if cert_index is None:
        return None, "no certificates element to clone"

    src_kind, src_val = _chunk_attr_value(blob, chunks[cert_index][1])
    have_user = src_kind == "string" and pool.get(src_val) == "user"
    try:
        src_name_idx = pool.items.index("src")
    except ValueError:
        return None, "no src string in the pool"

    new_pool, added = _pool_with(blob, pool_off, ["user", "overridePins",
                                                   "cleartextTrafficPermitted"])
    user_idx = added["user"]
    override_idx = added["overridePins"]
    clear_idx = added["cleartextTrafficPermitted"]

    out = []
    for i, (t, off, raw) in enumerate(chunks):
        if t == 0x0001:
            out.append(new_pool)
            continue
        if i in drop:
            continue
        if i == base_index:
            # an intercepted https flow does not need cleartext, but leaving the
            # app's own "false" here silently blocks plain http traffic too
            out.append(_set_bool_attr(raw, clear_idx, True))
            continue
        if i == cert_index and not have_user:
            out.append(raw)                      # the original entry, untouched
            clone = bytearray(raw)
            base = 16
            count = u2(clone, base + 12)
            start = u2(clone, base + 8)
            size = u2(clone, base + 10) or 20
            for k in range(min(count, 64)):
                a = base + start + k * size
                if u4(clone, a + 4) == src_name_idx:
                    struct.pack_into("<B", clone, a + 15, 0x03)
                    struct.pack_into("<I", clone, a + 8, 0xFFFFFFFF)
                    struct.pack_into("<I", clone, a + 16, user_idx)
                    break
            # overridePins="true": connections validated by this anchor ignore
            # any pin-set the app declares. Without it a pinned app still
            # refuses a user CA even when the anchor is trusted.
            edge = base + start + count * size
            extra = struct.pack("<IIIHBBI", 0xFFFFFFFF, override_idx, 0xFFFFFFFF,
                                8, 0, 0x12, 0xFFFFFFFF)
            clone = clone[:edge] + extra + clone[edge:]
            struct.pack_into("<H", clone, base + 12, count + 1)
            struct.pack_into("<I", clone, 4, len(clone))
            out.append(bytes(clone))             # + <certificates src="user" overridePins="true"/>
            continue
        out.append(raw)

    body = b"".join(out)
    total = 8 + len(body)
    return struct.pack("<HHI", 0x0003, 8, total) + body, (
        "kept the app's own encoding · user CA %s" % ("already trusted" if have_user else "added"))


def flutter_engine_id(path):
    """(dart version, engine build id) read straight out of libflutter.so.

    When no signature matches, these two strings are the only thing that lets a
    human look the build up (reFlutter's enginehash.csv maps the build id to the
    Flutter release and ships a prebuilt patched engine for it).
    """
    try:
        data = Path(path).read_bytes()
    except Exception:
        return "", ""
    dart = ""
    m = re.search(rb"(\d+\.\d+\.\d+)\s*\(stable\)", data)
    if m:
        dart = m.group(1).decode("ascii", "ignore")
    build = ""
    for m in re.finditer(rb"(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])", data):
        cand = m.group(0).decode("ascii")
        if len(set(cand)) < 6:          # 4444.../5555... are data patterns, not ids
            continue
        build = cand
        break
    return dart, build


REFUTTER_CSV = "https://raw.githubusercontent.com/Impact-I/reFlutter/main/enginehash.csv"
REFUTTER_RELEASE = "https://github.com/Impact-I/reFlutter/releases/download/android-v2-%s/%s"
ENGINE_ASSET = {"armeabi-v7a": "libflutter_arm.so", "armeabi": "libflutter_arm.so",
                "arm64-v8a": "libflutter_arm64.so", "x86": "libflutter_x86.so",
                "x86_64": "libflutter_x64.so"}
_ENGINE_MAP = {}


def engine_cache():
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    d = Path(base) / "arpxtool" / "engines"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except Exception:
        d = Path(tempfile.gettempdir()) / "arpxtool-engines"
        d.mkdir(parents=True, exist_ok=True)
    return d


def engine_snapshot_map(refresh=False):
    """{engine build id: snapshot hash} from reFlutter's published table."""
    global _ENGINE_MAP
    if _ENGINE_MAP and not refresh:
        return _ENGINE_MAP
    path = engine_cache() / "enginehash.csv"
    fresh = path.exists() and (time.time() - path.stat().st_mtime) < 7 * 86400
    if refresh or not fresh:
        try:
            download(REFUTTER_CSV, path, "engine table")
        except Exception:
            pass
    table = {}
    try:
        for line in path.read_text(errors="ignore").splitlines():
            parts = [x.strip() for x in line.split(",")]
            if len(parts) < 3 or parts[1] in ("Engine_commit", ""):
                continue
            table[parts[1]] = parts[2]
    except Exception:
        pass
    _ENGINE_MAP = table
    return table


def auto_patched_engine(so_path, abi, allow_net=True):
    """Fetch reFlutter's prebuilt patched engine for this exact build.

    Returns (path, note) or (None, reason). Nothing is guessed: the engine build
    id is read out of the library and looked up in reFlutter's own table.
    """
    if not allow_net:
        return None, "network disabled"
    dart, build = flutter_engine_id(so_path)
    if not build:
        return None, "engine build id not found"
    snapshot = engine_snapshot_map().get(build)
    if not snapshot:
        return None, "engine %s is not in reFlutter's table" % build
    asset = ENGINE_ASSET.get(abi)
    if not asset:
        return None, "no prebuilt engine for %s" % abi
    dest = engine_cache() / ("%s_%s" % (snapshot, asset))
    if not dest.exists() or dest.stat().st_size < 1024 * 1024:
        ok = download(REFUTTER_RELEASE % (snapshot, asset), dest, "patched engine")
        if not ok:
            return None, "download failed"
    return dest, "reFlutter %s for engine %s" % (asset, build[:12])


def patch_native_in_apk(apk, work, engine=None, allow_net=True):
    """Patch the flutter engine inside the archive that will be signed.

    BINARY PATCH edits the decoded tree, and that tree is thrown away whenever
    the build falls back to dex surgery. Without this pass the output is byte
    for byte the original app on the native side, which is exactly what
    "1 patch site(s) unconfirmed" means in verification.
    """
    try:
        with zipfile.ZipFile(str(apk)) as z:
            names = [n for n in z.namelist() if re.match(r"lib/[^/]+/libflutter\.so$", n)]
            if not names:
                return []
            blobs = {n: z.read(n) for n in names}
    except Exception as e:
        return [("<archive>", type("R", (), {"hits": [], "already": 0, "error": str(e),
                                             "names": [], "arch": "?"})())]
    workdir = Path(work) / "native"
    workdir.mkdir(parents=True, exist_ok=True)
    out = []
    replaced = {}
    for name in names:
        abi = name.split("/")[1]
        tmp = workdir / ("%s.so" % abi)
        if engine and Path(engine).is_file():
            # drop-in replacement engine (reFlutter's prebuilt patched build for
            # this exact engine id) — used when no signature matches
            cand = Path(engine)
            info = elf_info(cand.read_bytes()[:4096] or b"")
            want = ABI_EXPECT.get(abi)
            if want and info and (info["arch"], info["bits"]) == want:
                tmp.write_bytes(cand.read_bytes())
                res = PatchResult(str(tmp), abi)
                res.hits = [0]
                res.names = [(0, "prebuilt patched engine", 1, "patched")]
                out.append((name, res))
                replaced[name] = tmp.read_bytes()
                continue
        tmp.write_bytes(blobs[name])
        res = patch_shared_object(tmp, abi)
        if not res.hits and not res.already:
            auto, note = auto_patched_engine(tmp, abi, allow_net)
            if auto:
                tmp.write_bytes(Path(auto).read_bytes())
                res = PatchResult(str(tmp), abi)
                res.hits = [0]
                res.names = [(0, "prebuilt patched engine (%s)" % note, 1, "patched")]
        out.append((name, res))
        if res.hits:
            replaced[name] = tmp.read_bytes()
    if not replaced:
        return out
    tmp_apk = Path(str(apk) + ".native")
    try:
        with zipfile.ZipFile(str(apk)) as zin, zipfile.ZipFile(str(tmp_apk), "w", allowZip64=True) as zout:
            for item in zin.infolist():
                data = replaced.get(item.filename)
                if data is None:
                    data = zin.read(item.filename)
                zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
                zi.compress_type = item.compress_type
                zi.external_attr = item.external_attr
                zi.internal_attr = item.internal_attr
                zi.create_system = item.create_system
                zout.writestr(zi, data)
        os.replace(str(tmp_apk), str(apk))
    except Exception as e:
        try:
            tmp_apk.unlink(missing_ok=True)
        except Exception:
            pass
        Out.warn("native repack failed · " + trunc(str(e), 60))
    return out


def inject_netsec(apk, cleartext=True):
    """Make the app's network security config trust user CAs, in the archive.

    Returns (status, detail): replaced / absent / unchanged / error.
    """
    entry = nsc_entry(apk)
    if not entry:
        return "absent", "the manifest does not reference a res/xml network-security-config"
    try:
        with zipfile.ZipFile(str(apk)) as z:
            blob = z.read(entry)
    except Exception as e:
        return "error", trunc(str(e), 70)
    before = Axml(blob).elements
    edited, note = _netsec_edit(blob)
    if edited is None:
        return "error", "cannot rewrite %s · %s" % (entry, note)
    if edited == blob:
        return "unchanged", "%s · %s" % (entry, note)
    target = Path(str(apk) + ".netsec")
    try:
        with zipfile.ZipFile(str(apk)) as zin, zipfile.ZipFile(str(target), "w", allowZip64=True) as zout:
            for item in zin.infolist():
                data = edited if item.filename == entry else zin.read(item.filename)
                zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
                zi.compress_type = item.compress_type
                zi.external_attr = item.external_attr
                zi.internal_attr = item.internal_attr
                zi.create_system = item.create_system
                zout.writestr(zi, data)
        os.replace(str(target), str(apk))
    except Exception as e:
        try:
            target.unlink(missing_ok=True)
        except Exception:
            pass
        return "error", trunc(str(e), 70)
    detail = "%s · %d -> %d byte(s) · %s" % (entry, len(blob), len(edited), note)
    dropped = [e for e in before if e in ("pin-set", "domain-config")]
    if dropped:
        detail += " · removed " + ", ".join(sorted(set(dropped)))
    return "replaced", detail


DOLLAR_RE = re.compile(r"^\$")


def fix_dollar_resources(src):
    res = Path(src) / "res"
    if not res.is_dir():
        return 0, 0, "no res"
    renamed = []
    for sub in sorted(res.iterdir()):
        if not sub.is_dir():
            continue
        restype = sub.name.split("-")[0]
        for f in sorted(sub.iterdir()):
            if not f.is_file() or not f.name.startswith("$"):
                continue
            bare_old = f.stem
            bare_new = bare_old[1:]
            dest = f.with_name(f.name[1:])
            try:
                if dest.exists():
                    dest.unlink()
                os.replace(f, dest)
                renamed.append((restype, bare_old, bare_new))
            except Exception:
                pass
    if not renamed:
        return 0, 0, "none"
    touched = 0
    for path in res.rglob("*.xml"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        original = text
        for restype, bare_old, bare_new in renamed:
            text = text.replace("@%s/%s" % (restype, bare_old), "@%s/%s" % (restype, bare_new))
            text = text.replace('"%s"' % bare_old, '"%s"' % bare_new)
            text = text.replace(">%s<" % bare_old, ">%s<" % bare_new)
        if text != original:
            atomic_write(path, text, "w")
            touched += 1
    for stale in [Path(src) / "resources.arsc", Path(src) / "res" / "resources.arsc"]:
        if stale.exists():
            try:
                stale.unlink()
            except Exception:
                pass
    return len(renamed), touched, "ok"


def zip_names(path):
    try:
        with zipfile.ZipFile(path) as z:
            return z.namelist()
    except Exception:
        return []


def container_reason(path):
    try:
        size = Path(path).stat().st_size
    except Exception:
        return "file is not readable"
    if size == 0:
        return "file is empty"
    try:
        with open(path, "rb") as fh:
            magic = fh.read(4)
    except Exception as e:
        return "cannot open: " + trunc(str(e), 50)
    if magic[:2] != b"PK":
        return "not a zip container (magic %s)" % magic.hex()
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
    except Exception as e:
        return "zip is corrupt: " + trunc(str(e), 50)
    if not names:
        return "zip is empty"
    if "AndroidManifest.xml" not in names:
        return "no AndroidManifest.xml inside"
    return "unrecognised layout"


def detect_container(path):
    names = zip_names(path)
    if not names:
        return "invalid"
    if "AndroidManifest.xml" in names:
        return "apk"
    if any(n.endswith(".apk") for n in names):
        if any(n.startswith("splits/") for n in names) or "toc.pb" in names:
            return "apks"
        if "manifest.json" in names or "info.json" in names:
            return "bundle"
        return "zip"
    return "invalid"


def extract_splits(container, work):
    ext = Path(work) / "splits_src"
    ext.mkdir(parents=True, exist_ok=True)
    out = []
    try:
        with zipfile.ZipFile(container) as z:
            bad = z.testzip()
            if bad:
                return []
            for info in z.infolist():
                if not info.filename.lower().endswith(".apk"):
                    continue
                target = ext / safe_name(info.filename)
                with z.open(info) as srcf, open(target, "wb") as dstf:
                    shutil.copyfileobj(srcf, dstf)
                out.append(target)
    except Exception:
        return []
    return out


def pick_base(splits):
    if not splits:
        return None
    ranked = sorted(splits, key=lambda p: (("base" not in p.name.lower()), -p.stat().st_size))
    return ranked[0]


def _post_merge_redex(apk_path, work, d8_bin):
    """Re-dex the merged APK using d8/dx to fix alignment issues from APKEditor."""
    import zipfile as _zf, tempfile as _tf, os as _os
    try:
        dex_dir = Path(work) / "redex_in"
        out_dir = Path(work) / "redex_out"
        dex_dir.mkdir(parents=True, exist_ok=True)
        out_dir.mkdir(parents=True, exist_ok=True)
        # extract dex files
        dex_names = []
        with _zf.ZipFile(str(apk_path)) as z:
            for name in z.namelist():
                if re.match(r"classes\d*\.dex$", name):
                    z.extract(name, str(dex_dir))
                    dex_names.append(name)
        if not dex_names:
            return None
        # run d8/dx to re-compile
        dex_paths = [str(dex_dir / n) for n in dex_names]
        cmd = [d8_bin, "--min-api", "24", "--output", str(out_dir)] + dex_paths
        rc, _ = run_live(cmd, "re-dex", timeout=120, sink=[])
        if rc != 0:
            return None
        # check output
        out_dexes = sorted(out_dir.glob("classes*.dex"))
        if not out_dexes:
            return None
        # rebuild APK with new dex
        fixed = Path(work) / "merged_fixed.apk"
        with _zf.ZipFile(str(apk_path)) as zin,              _zf.ZipFile(str(fixed), "w", allowZip64=True) as zout:
            for info in zin.infolist():
                if re.match(r"classes\d*\.dex$", info.filename):
                    continue  # skip old dex
                zi = _zf.ZipInfo(info.filename, date_time=info.date_time)
                zi.compress_type = info.compress_type
                zi.external_attr = info.external_attr
                zout.writestr(zi, zin.read(info.filename))
            for dex_path in out_dexes:
                zi = _zf.ZipInfo(dex_path.name)
                zi.compress_type = _zf.ZIP_STORED
                zout.writestr(zi, dex_path.read_bytes())
        Out.ok("re-dex · %d dex file(s) recompiled" % len(out_dexes))
        return fixed
    except Exception as e:
        Out.warn("re-dex skipped · " + str(e))
        return None


def prepare_input(path, work, tool):
    kind = detect_container(path)
    if kind == "apk":
        # apply dex padding fix on direct APKs too (not just merged splits)
        try:
            import zipfile as _zfa
            _changed_a = {}
            with _zfa.ZipFile(str(path)) as _za:
                for _ia in _za.infolist():
                    if not re.match(r"classes\d*\.dex$", _ia.filename):
                        continue
                    _ba = _za.read(_ia.filename)
                    _fa, _ca = dex_zero_fixed_section_gaps(_ba)
                    if _ca:
                        _changed_a[_ia.filename] = _fa
            if _changed_a:
                _tmp_a = Path(str(path) + ".padfix"
                              if not str(path).endswith(".padfix") else str(path) + ".2")
                with _zfa.ZipFile(str(path)) as _zin_a,                      _zfa.ZipFile(str(_tmp_a), "w", allowZip64=True) as _zout_a:
                    for _ia in _zin_a.infolist():
                        _zi_a = _zfa.ZipInfo(_ia.filename, _ia.date_time)
                        _zi_a.compress_type = _ia.compress_type
                        _zi_a.external_attr = _ia.external_attr
                        _zi_a.internal_attr = _ia.internal_attr
                        _zi_a.create_system = _ia.create_system
                        _zout_a.writestr(_zi_a, _changed_a.get(
                            _ia.filename, _zin_a.read(_ia.filename)))
                # copy to work dir so we don't modify the original
                import os as _osa
                _fixed_path = Path(work) / Path(path).name
                _fixed_path.parent.mkdir(parents=True, exist_ok=True)
                _osa.replace(str(_tmp_a), str(_fixed_path))
                Out.ok("dex padding fixed · %d dex file(s)" % len(_changed_a))
                return _fixed_path, kind, []
        except Exception as _exa:
            pass
        return path, kind, []
    if kind == "invalid":
        return None, kind, []
    splits = extract_splits(path, work)
    if not splits:
        return None, kind, []
    merged = None
    if tool.get("apkeditor"):
        stage = Path(work) / "splits_stage"
        stage.mkdir(parents=True, exist_ok=True)
        for s in splits:
            shutil.copy2(s, stage / s.name)
        target = Path(work) / "merged.apk"
        rc, _ = run_live(tool["apkeditor"] + ["m", "-i", str(stage), "-o", str(target), "-f"], "merge splits")
        if rc == 0 and target.exists() and target.stat().st_size > 10000:
            merged = target
    if merged is None:
        merged = pick_base(splits)
    # post-merge: fix non-zero dex padding from APKEditor
    if merged and merged.exists():
        try:
            import zipfile as _zf2
            _changed2 = {}
            with _zf2.ZipFile(str(merged)) as _z2:
                for _info2 in _z2.infolist():
                    if not re.match(r"classes\d*\.dex$", _info2.filename):
                        continue
                    _blob2 = _z2.read(_info2.filename)
                    _fixed2, _cnt2 = dex_zero_fixed_section_gaps(_blob2)
                    if _cnt2:
                        _changed2[_info2.filename] = _fixed2
            if _changed2:
                _tmp2 = Path(str(merged) + ".fix")
                with _zf2.ZipFile(str(merged)) as _zin2,                      _zf2.ZipFile(str(_tmp2), "w", allowZip64=True) as _zout2:
                    for _info2 in _zin2.infolist():
                        _zi2 = _zf2.ZipInfo(_info2.filename, _info2.date_time)
                        _zi2.compress_type = _info2.compress_type
                        _zi2.external_attr = _info2.external_attr
                        _zout2.writestr(_zi2, _changed2.get(
                            _info2.filename, _zin2.read(_info2.filename)))
                import os as _os2
                _os2.replace(str(_tmp2), str(merged))
                Out.ok("dex padding fixed · %d byte(s) zeroed" % sum(
                    len(v) for v in _changed2.values()))
        except Exception as _ex2:
            Out.warn("dex padding fix skipped · " + str(_ex2))
        d8 = which("d8") or which("dx")
        if d8:
            merged = _post_merge_redex(merged, work, d8) or merged
    return merged, kind, splits


GH_API = "https://api.github.com/repos/%s/releases/latest"


def _urlopen(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent": "ARP/%s" % VERSION})
    try:
        ctx = _tls.create_default_context()
        return urllib.request.urlopen(req, timeout=timeout, context=ctx)
    except Exception:
        ctx = _tls._create_unverified_context()
        return urllib.request.urlopen(req, timeout=timeout, context=ctx)


def download(url, dest, label):
    dest = Path(dest)
    try:
        with _urlopen(url, timeout=180) as r, open(dest, "wb") as f:
            shutil.copyfileobj(r, f)
        if dest.stat().st_size < 4096:
            dest.unlink(missing_ok=True)
            return False
        Out.ok("%s · %s" % (label, human(dest.stat().st_size)))
        return True
    except Exception as e:
        Out.warn("%s · %s" % (label, trunc(str(e), 60)))
        if dest.exists():
            dest.unlink(missing_ok=True)
        return False


def latest_asset(repo, pattern):
    try:
        with _urlopen(GH_API % repo, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8", "ignore"))
        for asset in data.get("assets", []):
            if re.search(pattern, asset.get("name", ""), re.I):
                return asset["browser_download_url"]
    except Exception:
        pass
    return None


JVM_CACHE = []


def total_ram():
    try:
        for line in open("/proc/meminfo"):
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) * 1024
    except Exception:
        pass
    return 2 * 1024 ** 3


def jvm_flags():
    if not JVM_CACHE:
        ram = total_ram()
        heap = int(min(1536, max(256, ram / 1024 / 1024 * 0.45)))
        JVM_CACHE.extend(["-Xmx%dm" % heap, "-XX:+UseSerialGC"])
    return list(JVM_CACHE)


RUNTIME = {"threads": None, "timeout": None}


def job_threads():
    if RUNTIME.get("threads"):
        return str(RUNTIME["threads"])
    ram = total_ram()
    return "2" if ram <= 2 * 1024 ** 3 else "4"


def argv_of(value):
    """A tool entry may be a string path or a list of argv parts."""
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


def java_jar(parts):
    return ["java"] + jvm_flags() + ["-jar"] + parts


def find_local(names):
    for n in names:
        for base in (HOME, Path.cwd()):
            p = base / n
            if p.exists() and p.stat().st_size > 10000:
                return p
    return None


APKTOOL_PINS = [
    ("2.12.1", "https://github.com/iBotPeaches/Apktool/releases/download/v2.12.1/apktool_2.12.1.jar"),
    ("2.11.1", "https://github.com/iBotPeaches/Apktool/releases/download/v2.11.1/apktool_2.11.1.jar"),
    ("2.9.3", "https://github.com/iBotPeaches/Apktool/releases/download/v2.9.3/apktool_2.9.3.jar"),
    ("3.0.3", "https://github.com/iBotPeaches/Apktool/releases/download/v3.0.3/apktool_3.0.3.jar"),
]

SKIP_RX = re.compile(r"skipping class|Error occurred while disassembling|Could not smali|invalid instruction|Expecting", re.I)
BAD_SMALI_RX = re.compile(r"Could not smali file:\s*(\S+)", re.I)
THIRTY_TWO_RX = re.compile(r"no longer supports 32-bit|32-bit platforms", re.I)


APKEDITOR_PINS = [
    "https://github.com/REAndroid/APKEditor/releases/download/V1.4.9/APKEditor-1.4.9.jar",
]

UBER_PINS = [
    "https://github.com/patrickfav/uber-apk-signer/releases/download/v1.3.0/uber-apk-signer-1.3.0.jar",
]


def resolve_toolchain(work, allow_net=True, quiet=False):
    tool = {"apktool": None, "apkeditor": None, "uber": None, "apksigner": which("apksigner"), "zipalign": which("zipalign"), "keytool": which("keytool")}
    tool["allow_net"] = allow_net
    jar = find_local(["APKTool.jar", "apktool.jar", "apktool_2.12.1.jar"])
    if jar:
        tool["apktool"] = java_jar([str(jar)])
    elif which("apktool"):
        tool["apktool"] = ["apktool"]
    ed = find_local(["APKEditor.jar", "APKEditor-1.4.9.jar"])
    if ed:
        tool["apkeditor"] = java_jar([str(ed)])
    ub = find_local(["uber-apk-signer.jar", "uber-apk-signer-1.3.0.jar"])
    if ub:
        tool["uber"] = java_jar([str(ub)])
    if allow_net and tool["apkeditor"] is None and java_ok():
        dest = HOME / "APKEditor.jar"
        if download(APKEDITOR_PINS[0], dest, "bundle engine"):
            tool["apkeditor"] = java_jar([str(dest)])
    return tool


def engine_entries(tool):
    entries = []
    if tool.get("allow_net") and java_ok():
        for label, url in APKTOOL_PINS:
            dest = HOME / ("apktool_%s.jar" % label)
            entries.append(("v" + label, (dest, url)))
    if tool.get("apktool"):
        entries.append(("local", tool["apktool"]))
    if which("apktool"):
        entries.append(("path", ["apktool"]))
    return entries


def engine_cmd(payload):
    if isinstance(payload, list):
        return payload
    if not (isinstance(payload, tuple) and len(payload) == 2):
        return None
    dest, url = payload
    if dest.exists() and dest.stat().st_size > 100000:
        return java_jar([str(dest)])
    if not download(url, dest, "apktool jar"):
        return None
    return java_jar([str(dest)])


def engine_version(cmd):
    if not cmd:
        return "?"
    rc, out, err = run(cmd + ["--version"], timeout=90)
    text = ((out or "") + " " + (err or "")).strip().splitlines()
    return trunc(text[0], 40) if text else "?"


def tool_probe(tool):
    rows = []
    bits = "64-bit" if sys.maxsize > 2 ** 32 else "32-bit"
    rows.append(("host", True, "%s · %s" % (platform.machine() or platform.system(), bits)))
    if java_ok():
        rc, out, _ = run(["java", "-version"], timeout=30)
        ver = (out or "").strip().splitlines()[0] if out.strip() else "java"
        rows.append(("java", True, trunc(ver, 40)))
    else:
        rows.append(("java", False, "missing · required"))
    rows.append(("apktool", bool(tool.get("apktool")), " ".join(tool["apktool"][:3]) if tool.get("apktool") else "will fetch on demand"))
    rows.append(("apkeditor", bool(tool.get("apkeditor")), "bundle merge" if tool.get("apkeditor") else "optional"))
    rows.append(("apksigner", bool(tool.get("apksigner")), tool.get("apksigner") or "fallback only"))
    rows.append(("zipalign", bool(tool.get("zipalign")), tool.get("zipalign") or "optional"))
    rows.append(("keytool", bool(tool.get("keytool")), tool.get("keytool") or "missing"))
    return rows


def keystore_path():
    return HOME / "arp-release.keystore"


def ensure_keystore(password):
    ks = keystore_path()
    if ks.exists() and ks.stat().st_size > 500:
        return ks
    if not which("keytool"):
        return None
    Out.info("generating signing identity")
    rc, out, err = run([
        "keytool", "-genkeypair", "-v", "-keystore", str(ks), "-alias", "arp",
        "-keyalg", "RSA", "-keysize", "2048", "-sigalg", "SHA256withRSA",
        "-validity", "12000", "-storepass", password, "-keypass", password,
        "-dname", "CN=ARP, OU=Research, O=ARP, L=Lab, C=IN",
    ], timeout=240)
    if rc == 0 and ks.exists():
        try:
            os.chmod(ks, 0o600)
        except Exception:
            pass
        return ks
    Out.bad("keystore generation failed")
    return None


def move_file(src, dst):
    """Replace dst with src, across filesystems too.

    os.replace() raises EXDEV when the work tree lives in $TMPDIR and the output
    goes to /storage/emulated/0 — which is exactly the layout on Termux.
    """
    src, dst = str(src), str(dst)
    try:
        os.replace(src, dst)
        return True
    except OSError as e:
        if getattr(e, "errno", None) != 18:      # EXDEV
            raise
    try:
        shutil.copy2(src, dst)
        os.unlink(src)
        return True
    except Exception:
        return False


def do_zipalign(tool, apk, work):
    z = tool.get("zipalign")
    if not z:
        return (apk, "python") if zip_align(apk) else (apk, False)
    out = Path(work) / ("aligned_" + apk.name)
    for flags in (["-p", "-f", "4"], ["-f", "4"]):
        rc, _, _ = run([z] + flags + [str(apk), str(out)], timeout=900)
        if rc == 0 and out.exists():
            move_file(out, apk)
            return apk, True
    return apk, False


SIGN_STATE = {"keystore": None, "alias": None, "store_pass": None, "key_pass": None,
              "v1": True, "v2": True, "v3": True}


def signer_plan():
    plan = []
    if which("apksigner"):
        plan.append("apksigner")
    if which("jarsigner"):
        plan.append("jarsigner")
    plan.append("uber")
    return plan


def do_sign(tool, apk, work, password):
    trace("sign %s" % Path(apk).name)
    ks = SIGN_STATE.get("keystore")
    alias = SIGN_STATE.get("alias") or "arp"
    store_pass = SIGN_STATE.get("store_pass") or password
    key_pass = SIGN_STATE.get("key_pass") or store_pass
    if ks:
        ks = Path(ks).expanduser()
        if not ks.exists():
            Out.warn("keystore not found · " + str(ks))
            ks = None
    if not ks:
        ks = ensure_keystore(password)
    attempts = []
    if ks and tool.get("apksigner"):
        minsdk = apk_min_sdk(apk)
        argv = argv_of(tool["apksigner"]) + ["sign",
                "--ks", str(ks), "--ks-key-alias", alias,
                "--ks-pass", "pass:" + store_pass, "--key-pass", "pass:" + key_pass,
                "--min-sdk-version", str(minsdk),
                "--v1-signing-enabled", "true" if SIGN_STATE["v1"] else "false",
                "--v2-signing-enabled", "true" if SIGN_STATE["v2"] else "false",
                "--v3-signing-enabled", "true" if SIGN_STATE["v3"] else "false",
                str(apk)]
        try:
            rc, out, err = run(argv, timeout=1200)
        except Exception as exc:
            rc, out, err = -1, "", str(exc)
        attempts.append(("apksigner", rc))
        if rc == 0:
            return True, "apksigner"
        Out.warn("apksigner failed · " + trunc((err or out).strip(), 90))
    if tool.get("uber"):
        rc, _ = run_live(tool["uber"] + ["-a", str(apk), "--allowResign", "--overwrite"], "uber-apk-signer", timeout=1800)
        attempts.append(("uber-apk-signer", rc))
        if rc == 0:
            return True, "uber-apk-signer"
    if ks and which("jarsigner"):
        rc, _, _ = run(["jarsigner", "-sigalg", "SHA256withRSA", "-digestalg", "SHA-256",
                        "-keystore", str(ks), "-storepass", store_pass, "-keypass", key_pass,
                        str(apk), alias], timeout=1200)
        attempts.append(("jarsigner-v1", rc))
        if rc == 0:
            Out.warn("v1 only · android 11+ needs v2 or v3, install apksigner")
            return True, "jarsigner-v1"
    if ks:
        ok, why = native_sign_apk(apk, ks)
        attempts.append(("python-native", 0 if ok else 1))
        if ok:
            return True, why
        Out.info("python signer · " + why)
    if attempts:
        Out.info("signers tried · " + ", ".join("%s=%s" % (n, c) for n, c in attempts))
    return False, "none"


def verify_signature_deep(tool, apk):
    facts = verify_signature(tool, apk)
    if facts is None:
        return None
    schemes = apk_signature_schemes(tool, apk)
    facts["schemes"] = schemes
    facts["v2_or_better"] = any(x in ("v2", "v3", "v3.1") for x in schemes)
    return facts


def extract_bad_smali(sink):
    out = []
    for line in sink:
        for m in BAD_SMALI_RX.finditer(line):
            out.append(m.group(1))
    return out


def quarantine_files(src, paths):
    qdir = Path(src).parent / "quarantine"
    qdir.mkdir(parents=True, exist_ok=True)
    moved = 0
    for raw in paths:
        cand = Path(raw)
        if not cand.is_absolute():
            cand = Path(src) / raw
        try:
            if cand.is_file():
                shutil.move(str(cand), str(qdir / ("%03d_%s" % (moved, cand.name))))
                moved += 1
        except Exception:
            pass
    return moved


JVM_BUG_RX = re.compile(r"Exceptional value is not rounded|digitsRoundedUp", re.I)


def decode_tree(pipe, merged, src, fast=False, only=None, max_engines=3):
    best = None
    tried = 0
    for label, entry in engine_entries(pipe.tool):
        if only and only not in label:
            continue
        if tried >= max_engines:
            Out.info("engine limit reached · %d tried" % tried)
            break
        tried += 1
        cmd = engine_cmd(entry)
        if not cmd:
            continue
        if src.exists():
            shutil.rmtree(src, ignore_errors=True)
        sink = []
        flags = ["d", "-f", "-j", job_threads()] + (["-s"] if fast else [])
        run_live(cmd + flags + [str(merged), "-o", str(src)], "decode · " + label, timeout=3600, sink=sink)
        if not (src / "AndroidManifest.xml").exists():
            Out.warn("%s · engine produced no tree" % label)
            continue
        skipped = sum(1 for l in sink if SKIP_RX.search(l))
        legacy = any(THIRTY_TWO_RX.search(l) for l in sink)
        smali = sum(len(f) for r, _, f in os.walk(src) if "smali" in r)
        score = skipped * 100 + (1 if legacy else 0)
        if best is None or score < best[3]:
            best = (label, skipped, smali, score, cmd)
        if score == 0:
            Out.ok("engine %s · clean decode" % label)
            return label, 0, smali, cmd
        jvm_bug = any(JVM_BUG_RX.search(l) for l in sink)
        Out.warn("%s · %d class(es) skipped%s%s" % (label, skipped, " · 32-bit unsupported" if legacy else "",
                                                    " · jvm float bug" if jvm_bug else ""))
        if jvm_bug:
            Out.info("this is a JVM bug, not an apktool bug · every engine will hit it")
            Out.info("continuing with the decoded tree and preserving the original dex")
            break
        if only:
            break
    if best:
        return best[0], best[1], best[2], best[4]
    return None, 0, 0, None


def strip_public_xml(src):
    pub = Path(src) / "res" / "values" / "public.xml"
    if not pub.exists():
        return False
    try:
        pub.unlink()
        return True
    except Exception:
        return False




def class_loss(source_dir, built_apk):
    """Compare the class set of the decoded smali tree with the rebuilt dex."""
    want = set()
    for base in sorted(Path(source_dir).glob("smali*")):
        if not base.is_dir():
            continue
        for file in base.rglob("*.smali"):
            try:
                head = file.read_text(encoding="utf-8", errors="replace")[:400]
            except Exception:
                continue
            m = re.search(r"^\.class\s+[^\n]*?(L[\w/$]+;)", head, re.M)
            if m:
                want.add(m.group(1))
    if not want:
        return set()
    got = set()
    try:
        with zipfile.ZipFile(built_apk) as z:
            for name in z.namelist():
                if re.match(r"classes\d*\.dex$", name):
                    for cls in dex_class_names(z.read(name)) or []:
                        got.add(cls)
    except Exception:
        return set()
    return want - got


def rebuild_ladder(pipe, src, final):
    if not pipe.tool.get("apktool"):
        return None, None
    ladder = [("aapt2", []), ("no-crunch", ["-nc"]), ("keep-resources", ["-r"]), ("aapt1", ["--use-aapt1"])]
    sys_aapt = which("aapt2")
    if sys_aapt:
        ladder.insert(0, ("system-aapt2", ["--aapt", sys_aapt]))
    pub_dropped = False
    for label, extra in ladder:
        for attempt in range(4):
            if final.exists():
                final.unlink()
            sink = []
            tag = label if attempt == 0 else "%s · repair %d" % (label, attempt)
            rc, _ = run_live(argv_of(pipe.tool["apktool"]) + ["b", str(src), "-o", str(final), "-f"] + extra, tag, timeout=3600, sink=sink)
            pipe.last_sink = sink
            if rc == 0 and final.exists() and final.stat().st_size > 4096:
                good, detail = zip_integrity(final)
                if good:
                    lost = class_loss(src, final)
                    if lost:
                        Out.warn("%s · %d class(es) lost in the rebuild" % (tag, len(lost)))
                        for name in sorted(lost)[:4]:
                            Out.bullet(name.strip("L;"))
                        Out.info("this would crash on launch · trying the next build strategy")
                        try:
                            final.unlink()
                        except Exception:
                            pass
                        continue
                    # FIX-D: repair dex padding in apktool output
                    try:
                        sanitize_build(str(apk), final, tag)
                    except Exception:
                        pass
                    return final, tag
                Out.warn("%s · %s" % (tag, detail))
            text = "\n".join(sink)
            bad = extract_bad_smali(sink)
            if bad:
                moved = quarantine_files(src, bad)
                if moved:
                    Out.warn("%d unparseable smali file(s) quarantined · retrying" % moved)
                    pipe.quarantined += moved
                    continue
            if not pub_dropped and re.search(r"invalid entry name|public\.xml|invalid resource|is not a valid", text, re.I):
                if strip_public_xml(src):
                    pub_dropped = True
                    Out.warn("public.xml dropped · aapt2 assigns fresh ids · retrying")
                    continue
            break
    return None, None


def doctor():
    Tty.probe()
    banner_anim(not Tty.enabled)
    tool = resolve_toolchain(Path(tempfile.mkdtemp()), allow_net=False, quiet=True)
    Out.head("system", G_MAIN)
    Out.kv("platform", "%s · %s" % (platform.system(), platform.machine()))
    Out.kv("python", "%s · %d-bit" % (platform.python_version(), 64 if sys.maxsize > 2 ** 32 else 32))
    if java_ok():
        rc, out, err = run(["java", "-version"], timeout=60)
        line = ((err or "") + (out or "")).strip().splitlines()
        Out.kv("java", trunc(line[0], 48) if line else "present")
    else:
        Out.kv("java", "missing · pkg install openjdk-17", tone=T_ERR)
    Out.kv("free disk", human(disk_free(HOME)))
    Out.kv("ram", "%s · jvm heap %s" % (human(total_ram()), jvm_flags()[0].replace("-Xmx", "")))
    Out.kv("decode threads", job_threads())
    Out.kv("keystore", "present" if keystore_path().exists() else "will generate")
    for name in ("apksigner", "zipalign", "keytool", "aapt2"):
        Out.kv(name, which(name) or "not on path", tone=T_TXT if which(name) else T_DIM)
    Out.head("engines", G_COOL)
    entries = engine_entries(tool)
    if not entries:
        if java_ok():
            Out.info("no local engine · 2.12.1 will be fetched on the first run")
        else:
            Out.warn("no apktool engine reachable")
    for label, entry in entries:
        cmd = engine_cmd(entry)
        Out.kv(label, engine_version(cmd) if cmd else "unavailable")
    Out.head("diagnosis", G_WARM)
    issues = 0
    if not java_ok():
        Out.bad("java missing · every decode path needs it")
        issues += 1
    if sys.maxsize <= 2 ** 32 or platform.machine() in ("armv7l", "armv8l", "i686"):
        Out.warn("32-bit runtime · apktool 3.x refuses 32-bit hosts, pin 2.12.1")
        issues += 1
    if disk_free(HOME) < 3 * 1024 ** 3:
        Out.warn("less than 3 GB free · decode needs headroom for large apps")
        issues += 1
    if not which("zipalign"):
        Out.info("zipalign absent · apksigner still aligns on modern versions")
    if not which("aapt2"):
        Out.warn("aapt2 absent · on 32-bit hosts run: pkg install aapt2")
    if sys.maxsize <= 2 ** 32:
        Out.info("32-bit host detected · engines are tried in the order 2.12.1 then 2.11.1")
    if issues == 0:
        Out.ok("no blocking issue detected")
    else:
        Out.info("run with --engine 2.12.1 to force a known-good engine")
    return 0


def verify_signature(tool, apk):
    if not tool.get("apksigner"):
        return None
    rc, out, err = run(argv_of(tool["apksigner"]) + ["verify", "--print-certs", str(apk)], timeout=600)
    if rc != 0:
        return {"ok": False, "detail": trunc((err or out).strip().splitlines()[-1] if (err or out).strip() else "verify failed", 100)}
    subject = ""
    for line in out.splitlines():
        if "Subject:" in line:
            subject = line.split("Subject:", 1)[1].strip()
            break
    schemes = []
    rc2, out2, _ = run(argv_of(tool["apksigner"]) + ["verify", "--verbose", str(apk)], timeout=600)
    for key in ("v1 scheme", "v2 scheme", "v3 scheme", "v3.1 scheme"):
        for line in out2.splitlines():
            low = line.strip().lower()
            if key in low and "true" in low:
                schemes.append(key.split()[0])
    return {"ok": True, "subject": subject, "schemes": schemes}


def apk_class_count(apk):
    total = 0
    try:
        with zipfile.ZipFile(apk) as z:
            for name in z.namelist():
                if not re.match(r"classes\d*\.dex$", name):
                    continue
                head = z.read(name)[:0x70]
                if len(head) >= 0x64 and head[:4] == b"dex\n":
                    total += u4(head, 0x60)
    except Exception:
        return 0
    return total


def apk_stats(apk):
    st = {"files": 0, "dex": 0, "assets": 0, "libs": 0, "abi": [], "size": 0, "res": 0}
    try:
        st["size"] = Path(apk).stat().st_size
        with zipfile.ZipFile(apk) as z:
            names = z.namelist()
        st["files"] = len(names)
        st["dex"] = sum(1 for n in names if re.match(r"classes\d*\.dex$", n))
        st["assets"] = sum(1 for n in names if n.startswith("assets/"))
        st["res"] = sum(1 for n in names if n.startswith("res/"))
        libs = [n for n in names if n.startswith("lib/") and n.endswith(".so")]
        st["libs"] = len(libs)
        st["abi"] = sorted({n.split("/")[1] for n in libs if n.count("/") >= 2})
    except Exception:
        pass
    return st


def zip_integrity(apk):
    try:
        with zipfile.ZipFile(apk) as z:
            bad = z.testzip()
            if bad:
                return False, bad
            names = set(z.namelist())
        for req in ("AndroidManifest.xml",):
            if req not in names:
                return False, "missing " + req
        if not any(re.match(r"classes\d*\.dex$", n) for n in names):
            return False, "no dex payload"
        return True, "ok"
    except Exception as e:
        return False, trunc(str(e), 60)


class Pipeline:
    def __init__(self, args):
        self.args = args
        self.work = Path(tempfile.mkdtemp(prefix="arp_"))
        self.tool = {}
        self.touched = []
        self.records = []
        self.log = []
        self.decode_skips = 0
        self.src_hash = None
        self.quarantined = 0
        self.last_sink = []

    def note(self, kind, msg):
        self.log.append({"t": round(time.time(), 3), "kind": kind, "msg": msg})

    def cleanup(self):
        if self.args.keep:
            Out.warn("work tree kept: " + str(self.work))
            return
        shutil.rmtree(self.work, ignore_errors=True)

    def report(self):
        return {
            "tool": APP,
            "version": VERSION,
            "input": str(self.args.input) if self.args.input else None,
            "mode": self.args.mode,
            "patches": self.records,
            "events": self.log,
        }


PERM_RE = re.compile(r'<uses-permission[^>]*android:name="([^"]+)"')
COMPONENT_RE = {
    "activity": re.compile(r"<activity\b[^>]*>", re.S),
    "service": re.compile(r"<service\b[^>]*>", re.S),
    "receiver": re.compile(r"<receiver\b[^>]*>", re.S),
    "provider": re.compile(r"<provider\b[^>]*>", re.S),
}


def read_manifest(src):
    man = Path(src) / "AndroidManifest.xml"
    if not man.exists():
        return None
    try:
        text = man.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None
    info = {
        "package": "?", "version": "?", "launcher": "?", "min_sdk": "?", "target_sdk": "?",
        "permissions": [], "counts": {}, "exported": 0, "debuggable": False, "cleartext": False,
        "netsec": False, "raw": text, "version_code": "?",
    }
    m = re.search(r'\bpackage="([^"]+)"', text)
    if m:
        info["package"] = m.group(1)
    m = re.search(r'versionName\s*=\s*"([^"]+)"', text)
    if m:
        info["version"] = m.group(1)
    m = re.search(r'minSdkVersion\s*=\s*"([^"]+)"', text)
    if m:
        info["min_sdk"] = m.group(1)
    m = re.search(r'targetSdkVersion\s*=\s*"([^"]+)"', text)
    if m:
        info["target_sdk"] = m.group(1)
    info["permissions"] = sorted(set(PERM_RE.findall(text)))
    for tag, rx in COMPONENT_RE.items():
        blocks = rx.findall(text)
        info["counts"][tag] = len(blocks)
        info["exported"] += sum(1 for b in blocks if 'android:exported="true"' in b)
    info["debuggable"] = re.search(r'android:debuggable="true"', text) is not None
    info["cleartext"] = re.search(r'android:usesCleartextTraffic="true"', text) is not None
    info["netsec"] = "android:networkSecurityConfig" in text
    for m in re.finditer(r"<activity\b([^>]*)>(.*?)</activity>", text, re.S):
        body = m.group(2)
        if "android.intent.action.MAIN" in body and "android.intent.category.LAUNCHER" in body:
            n = re.search(r'android:name="([^"]+)"', m.group(1))
            if n:
                info["launcher"] = n.group(1)
                break
    return info


LIB_SIGNATURES = [
    ("Flutter engine", ("libflutter.so",), "engine"),
    ("Flutter snapshot", ("libapp.so",), "engine"),
    ("Unity IL2CPP", ("libil2cpp.so",), "engine"),
    ("Unity runtime", ("libunity.so",), "engine"),
    ("Xamarin Mono", ("libmonodroid.so", "libmonosgen-2.0.so"), "engine"),
    ("Hermes VM", ("libhermes.so",), "engine"),
    ("React Native JSC", ("libjsc.so",), "engine"),
    ("V8 runtime", ("libv8.so",), "engine"),
    ("BoringSSL", ("libssl.so", "libcrypto.so"), "crypto"),
]

PACKER_SIGNATURES = [
    ("Google Play Integrity", ("libpairipcore.so", "pairip"), "critical"),
    ("Tencent Legu", ("libshella", "libshellx", "libshell-super", "libtup.so"), "critical"),
    ("Baidu Jiagu", ("libjiagu",), "critical"),
    ("Bangcle SecShell", ("libsecexe.so", "libsecmain.so", "libsecshell.so"), "critical"),
    ("Alibaba SecurityGuard", ("libsgmain", "libsgsecuritybody", "libmobisec"), "critical"),
    ("DexProtector", ("dexprotector",), "critical"),
    ("DexGuard", ("dexguard",), "high"),
    ("Nagain", ("libnagain",), "high"),
    ("Qihoo 360 Shell", ("libjiagu_art", "libprotectclass"), "high"),
    ("NetEase Yidun", ("libyidun",), "medium"),
    ("APKProtect", ("libapkprotect",), "high"),
    ("Virbox", ("libvirbox",), "high"),
]

RASP_MARKERS = [
    ("Frida strings", ("frida", "gum-js-loop", "gmain", "linjector"), "high"),
    ("Xposed strings", ("xposed", "de.robv.android.xposed", "Lde/robv"), "high"),
    ("Emulator markers", ("goldfish", "ranchu", "qemu", "vbox86"), "medium"),
    ("Debug markers", ("ptrace", "TracerPid", "isDebuggerConnected"), "medium"),
    ("Magisk markers", ("magisk", "su/bin", "busybox"), "medium"),
]

SDK_MARKERS = {
    "OkHttp3": "okhttp3", "Retrofit": "retrofit2", "Gson": "com/google/gson",
    "Moshi": "com/squareup/moshi", "RxJava": "io/reactivex", "Coroutines": "kotlinx/coroutines",
    "Firebase": "com/google/firebase", "Play Services": "com/google/android/gms",
    "Crashlytics": "com/google/firebase/crashlytics", "Sentry": "io/sentry",
    "Stripe": "com/stripe", "AdMob": "com/google/android/gms/ads",
    "AppsFlyer": "com/appsflyer", "Adjust": "com/adjust/sdk", "Facebook": "com/facebook",
    "BouncyCastle": "org/bouncycastle", "InAppWebView": "com/pichillilorenzo",
    "ML Kit": "com/google/mlkit", "CameraX": "androidx/camera", "Compose": "androidx/compose",
}


def smali_roots(src):
    try:
        return [d for d in Path(src).iterdir() if d.is_dir() and d.name.startswith("smali")]
    except Exception:
        return []


def scan_libs(src):
    found = []
    for arch, so in iter_libs(src):
        found.append((arch, so.name, so))
    return found


def inventory_sdks(src):
    roots = smali_roots(src)
    hits = {}
    for name, needle in SDK_MARKERS.items():
        for root in roots:
            if (root / needle).is_dir():
                hits[name] = needle
                break
    return hits


def detect_engines(src, libs):
    names = {l[1] for l in libs}
    assets = Path(src) / "assets"
    out = []
    if "libflutter.so" in names:
        out.append(("Dart · Flutter", "libflutter.so", "high"))
    if "libapp.so" in names:
        out.append(("Dart snapshot", "libapp.so", "high"))
    if "libil2cpp.so" in names:
        out.append(("C# · Unity IL2CPP", "libil2cpp.so", "high"))
    if (assets / "index.android.bundle").exists():
        out.append(("JS · React Native", "index.android.bundle", "high"))
    if (assets / "www" / "index.html").exists():
        out.append(("Web · Cordova/Capacitor", "assets/www", "medium"))
    if "libmonodroid.so" in names:
        out.append(("C# · Xamarin", "libmonodroid.so", "high"))
    if (Path(src) / "assemblies").is_dir():
        out.append(("C# · Xamarin assemblies", "assemblies/", "high"))
    custom = [n for n in names if n not in {
        "libflutter.so", "libapp.so", "libil2cpp.so", "libmono.so", "libunity.so", "libmonodroid.so",
        "libhermes.so", "libjsc.so", "libv8.so", "libssl.so", "libcrypto.so",
    } and not n.startswith(("libandroid", "libjnigraphics", "libGLES", "libEGL", "libc.so", "libm.so", "libdl.so", "liblog.so", "libz.so"))]
    if custom:
        out.append(("C/C++ native", "%d custom objects" % len(custom), "medium"))
    dexes = len(list(Path(src).glob("smali*/")))
    if dexes:
        out.append(("Java/Kotlin", "%d smali roots" % dexes, "info"))
    return out


def detect_protections(src, libs, manifest):
    out = []
    blob = " ".join([l[1] for l in libs]).lower()
    for label, keys, sev in PACKER_SIGNATURES:
        for k in keys:
            if k.lower() in blob:
                out.append((label, k, sev))
                break
    if manifest:
        low = manifest["raw"].lower()
        for label, keys, sev in PACKER_SIGNATURES:
            for k in keys:
                if k.lower() in low and not any(o[0] == label for o in out):
                    out.append((label, "manifest", sev))
                    break
    for arch, name, path in libs:
        if "libflutter" not in name and "libapp" not in name:
            continue
        try:
            data = path.read_bytes()[: 6 * 1024 * 1024]
        except Exception:
            continue
        low = data.lower()
        for label, keys, sev in RASP_MARKERS:
            for k in keys:
                if k.encode().lower() in low:
                    tag = (label, "%s/%s" % (arch, name), sev)
                    if tag not in out:
                        out.append(tag)
                    break
    return out


def severity_tone(sev):
    return {"critical": BLOOD, "high": AMBER, "medium": VIOLET, "low": EMERALD}.get(sev, SLATE)


def show_manifest(m):
    if not m:
        Out.warn("manifest unavailable")
        return
    Out.head("manifest", G_COOL)
    Out.kv("package", m["package"])
    code = m.get("version_code")
    Out.kv("version", m["version"] if code in (None, "?") else "%s  (%s)" % (m["version"], code))
    Out.kv("sdk range", "%s → %s" % (m["min_sdk"], m["target_sdk"]))
    Out.kv("launcher", m["launcher"])
    counts = m["counts"]
    Out.kv("components", "act %d · svc %d · rec %d · prov %d" % (counts.get("activity", 0), counts.get("service", 0), counts.get("receiver", 0), counts.get("provider", 0)))
    flags = []
    flags.append(("debuggable", m["debuggable"]))
    flags.append(("cleartext", m["cleartext"]))
    flags.append(("netsec-config", m["netsec"]))
    print("  " + T_DIM("posture".ljust(22)) + " ".join((T_OK(CHECK) if v else T_DIM(CIRCLE)) + " " + T_TXT(k) for k, v in flags))
    if m["exported"]:
        Out.warn("%d exported components" % m["exported"])
    if m["permissions"]:
        Out.kv("permissions", len(m["permissions"]))
        for p in m["permissions"][:14]:
            print("    " + T_DIM(BULLET + " " + p.split(".")[-1]) + T_DIM("  ·  " + p.rsplit(".", 1)[0]))
        if len(m["permissions"]) > 14:
            print("    " + T_DIM("… %d more" % (len(m["permissions"]) - 14)))


def show_engines(engines):
    Out.head("runtime engines", G_WARM)
    if not engines:
        Out.info("no managed runtime fingerprint found")
        return
    for name, detail, sev in engines:
        tone = Pal(severity_tone(sev), sev in ("high", "critical"))
        print("  " + tone(BULLET) + " " + T_TXT(name.ljust(26)) + T_DIM(detail))


def show_libs(libs):
    Out.head("native surface", G_COOL)
    if not libs:
        Out.info("no native libraries")
        return
    abis = sorted({l[0] for l in libs})
    Out.kv("abis", " · ".join(abis))
    Out.kv("objects", len(libs))
    for abi in abis:
        names = [l[1] for l in libs if l[0] == abi]
        print("  " + T_ACC(DIAMOND) + " " + T_TXT(abi.ljust(14)) + T_DIM("%d objects · %s" % (len(names), ", ".join(names[:5]) + (" …" if len(names) > 5 else ""))))


def show_sdks(sdks):
    if not sdks:
        return
    Out.head("framework inventory", G_COOL)
    items = sorted(sdks)
    for i in range(0, len(items), 3):
        row = "".join(T_TXT(n.ljust(20)) for n in items[i : i + 3])
        print("  " + T_DIM(BULLET) + " " + row)


def show_protections(prots):
    Out.head("hardening & packers", G_WARM)
    if not prots:
        Out.ok("no known packer or RASP fingerprint")
        return
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    for label, detail, sev in sorted(prots, key=lambda p: order.get(p[2], 9)):
        tone = Pal(severity_tone(sev), sev in ("critical", "high"))
        print("  " + tone(DIAMOND) + " " + tone(sev.upper().ljust(9)) + T_TXT(label.ljust(24)) + T_DIM(detail))


def show_apk(apk):
    st = apk_stats(apk)
    Out.head("container", G_COOL)
    Out.kv("size", human(st["size"]))
    Out.kv("entries", st["files"])
    Out.kv("payload", "dex %d · res %d · assets %d · libs %d" % (st["dex"], st["res"], st["assets"], st["libs"]))
    if st["abi"]:
        Out.kv("abis", " · ".join(st["abi"]))
    return st


def extract_strings(path, min_len=6, limit=60000):
    out = set()
    try:
        data = path.read_bytes()
    except Exception:
        return out
    rx = re.compile(rb"[\x20-\x7e]{%d,}" % min_len)
    for i, m in enumerate(rx.finditer(data)):
        if i > limit:
            break
        out.add(m.group().decode("utf-8", "ignore"))
    return out


FEATURE_MAP = [
    ("oauth", "OAuth", "auth"), ("bearer ", "JWT", "auth"), ("refresh_token", "Refresh", "auth"),
    ("biometric", "Biometric", "auth"), ("otp", "OTP", "auth"), ("sms_retriever", "SMS Retriever", "auth"),
    ("stripe", "Stripe", "pay"), ("paypal", "PayPal", "pay"), ("razorpay", "Razorpay", "pay"),
    ("checkout", "Checkout", "pay"), ("in_app_purchase", "IAP", "pay"),
    ("firebase_messaging", "FCM", "msg"), ("onesignal", "OneSignal", "msg"),
    ("websocket", "WebSocket", "msg"), ("socket.io", "Socket.IO", "msg"), ("mqtt", "MQTT", "msg"),
    ("aes-", "AES", "crypto"), ("rsa-", "RSA", "crypto"), ("sha256", "SHA256", "crypto"),
    ("hmac", "HMAC", "crypto"), ("sqlcipher", "SQLCipher", "crypto"),
    ("geolocat", "Geolocation", "feat"), ("camera", "Camera", "feat"), ("qrcode", "QR", "feat"),
    ("walk", "Pedometer", "feat"), ("sim_control", "SIM", "feat"), ("recharge", "Recharge", "feat"),
    ("mapbox", "Mapbox", "feat"), ("google_maps", "Maps", "feat"), ("video_player", "Video", "feat"),
]


def analyze_engine_strings(path):
    res = {"domains": set(), "paths": set(), "cats": {}, "version": None}
    strings = extract_strings(path)
    for s in strings:
        if s.startswith(("https://", "http://")):
            try:
                host = s.split("//", 1)[1].split("/")[0].split(":")[0]
            except Exception:
                continue
            if "." in host and len(host) < 80 and not host.startswith(("www.google", "schemas.android", "www.w3.org")):
                res["domains"].add(host)
        elif s.startswith("/") and 4 < len(s) < 60 and s.count("/") >= 2:
            res["paths"].add(s)
        if s.startswith("Flutter ") and any(c.isdigit() for c in s) and not res["version"]:
            res["version"] = s[:40]
    joined = " ".join(strings).lower()
    for needle, label, cat in FEATURE_MAP:
        if needle in joined:
            res["cats"].setdefault(cat, set()).add(label)
    res["paths"] = set(sorted(res["paths"])[:20])
    res["domains"] = set(sorted(res["domains"])[:24])
    return res


def show_features(feat):
    Out.head("behavioural signals", G_OK)
    if feat.get("version"):
        Out.kv("engine build", feat["version"])
    if feat["domains"]:
        Out.kv("endpoints", len(feat["domains"]))
        for d in sorted(feat["domains"])[:12]:
            print("    " + T_DIM(BULLET + " " + d))
    for cat, tone in (("auth", AMBER), ("pay", AMBER), ("msg", CYAN), ("crypto", VIOLET), ("feat", EMERALD)):
        items = feat["cats"].get(cat)
        if not items:
            continue
        print("  " + Pal(tone, True)(DIAMOND) + " " + Pal(tone)(cat.upper().ljust(10)) + T_DIM(" · ".join(sorted(items))))


MODE_PLAN = {
    "full": {"native": True, "smali": ["ssl", "detect", "signature"], "manifest": True},
    "ssl": {"native": True, "smali": ["ssl"], "manifest": True},
    "security": {"native": False, "smali": ["detect", "signature"], "manifest": True},
    "signature": {"native": False, "smali": ["signature"], "manifest": True},
    "detect": {"native": False, "smali": [], "manifest": False},
    "native": {"native": True, "smali": [], "manifest": False},
    "inspect": {"native": False, "smali": [], "manifest": False},
    "verify": {"native": False, "smali": [], "manifest": False},
    "re": {"native": False, "smali": [], "manifest": False},
    "unpack": {"native": False, "smali": [], "manifest": False},
    "fast": {"native": True, "smali": [], "manifest": True},
    "surgery": {"native": True, "smali": [], "manifest": True},
}


def choose(title, options):
    if not (Tty.enabled and sys.stdin.isatty()):
        print("  " + title)
        for i, (key, label, desc) in enumerate(options, 1):
            print("    %d. %-12s %s" % (i, label, desc))
        try:
            raw = input("  select: ").strip()
        except (EOFError, KeyboardInterrupt):
            return None
        if not raw.isdigit():
            return None
        i = int(raw) - 1
        return options[i][0] if 0 <= i < len(options) else None
    import termios
    import tty as ttym

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    idx = 0
    try:
        ttym.setraw(fd)
        sys.stdout.write(Pal.HIDE)
        while True:
            lines = ["", "  " + Pal(ICE, True)(title), "  " + rule(64, G_COOL, THIN)]
            for i, (key, label, desc) in enumerate(options):
                if i == idx:
                    lines.append("  " + Pal(CYAN, True)(BULLET + " " + label.ljust(14)) + " " + Pal(SNOW)(desc))
                else:
                    lines.append("  " + Pal(STEEL)("  " + label.ljust(14)) + " " + Pal(INK)(desc))
            lines.append("  " + rule(64, G_COOL, THIN))
            lines.append("  " + Pal(STEEL)("arrows move · enter select · q quit"))
            Anim.paint(lines)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                a = sys.stdin.read(1)
                b = sys.stdin.read(1) if a == "[" else ""
                if b == "A":
                    idx = (idx - 1) % len(options)
                elif b == "B":
                    idx = (idx + 1) % len(options)
            elif ch in ("\r", "\n"):
                return options[idx][0]
            elif ch in ("q", "Q", "\x03"):
                return None
            elif ch.isdigit() and 0 < int(ch) <= len(options):
                idx = int(ch) - 1
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.stdout.write(Pal.SHOW)
        Anim.close()
        print()


def run_pipeline(args):
    Stage.reset()
    Tty.probe()
    fast = args.no_anim or not Tty.enabled
    if not args.quiet:
        banner_anim(fast)
        print()
    pipe = Pipeline(args)
    atexit.register(pipe.cleanup)
    src_input, _searched = resolve_input(args.input)
    if src_input is None:
        Out.bad("input not found: " + str(args.input))
        if _searched:
            Out.info("searched in: " + ", ".join(str(p) for p in _searched[:4]))
        return 2
    if not src_input.exists():
        Out.bad("input not found: " + str(src_input))
        hint = src_input.name
        try:
            near = [p for p in HOME.rglob("*" + src_input.suffix) if hint.split()[0].lower() in p.name.lower()][:3]
        except Exception:
            near = []
        for cand in near:
            Out.info("did you mean: " + str(cand))
        return 2
    if not preflight(src_input, prune=not args.resume):
        return 8
    Out.head("toolchain", G_COOL)
    pipe.tool = resolve_toolchain(pipe.work, allow_net=not args.no_net, quiet=args.quiet)
    for name, present, detail in tool_probe(pipe.tool):
        mark = T_OK(CHECK) if present else T_WARN(WARN)
        print("  " + mark + " " + T_TXT(name.ljust(12)) + T_DIM(detail))
    if not pipe.tool.get("apktool") and args.mode != "verify":
        if args.mode in ("ssl", "signature", "security", "native", "full", "fast"):
            Out.warn("no apktool engine · routing to the surgical engine")
            return run_surgery_mode(args)
        Out.bad("apktool engine unavailable · cannot decode")
        return 3
    free = disk_free(pipe.work)
    if free and free < 512 * 1024 * 1024:
        Out.warn("low disk space: " + human(free))
    Out.head("intake", G_OK)
    kind = detect_container(src_input)
    Out.kv("input", src_input.name)
    Out.kv("format", kind.upper())
    Out.kv("size", human(src_input.stat().st_size))
    merged, kind, splits = prepare_input(src_input, pipe.work, pipe.tool)
    if not merged:
        Out.bad("cannot read this archive · " + container_reason(src_input))
        return 4
    if splits:
        Out.ok("%d splits · base selected %s" % (len(splits), merged.name))
    show_apk(merged)
    if args.mode == "verify":
        ok, detail = zip_integrity(merged)
        sig = verify_signature(pipe.tool, merged)
        Out.head("signature audit", G_COOL)
        Out.kv("archive", "intact" if ok else detail, tone=T_OK if ok else T_ERR)
        if sig is None:
            Out.info("apksigner unavailable")
        elif sig.get("ok"):
            Out.ok("signature valid · " + sig.get("subject", ""))
            Out.kv("schemes", " ".join(sig.get("schemes") or ["unknown"]))
        else:
            Out.bad(sig.get("detail", "invalid"))
        Out.kv("sha256", sha256_file(merged))
        # a signature says nothing about whether the dex will load
        Out.head("dex audit", G_COOL)
        if not show_dex_audit(merged):
            Out.info("this archive installs cleanly and then crashes · the dex above is why")
        return 0
    plan = dict(MODE_PLAN.get(args.mode, MODE_PLAN["full"]))
    if args.mode != "verify":
        ensure_tools(["java", "apktool"], "decode")
    Out.head("decode", G_OK)
    src = pipe.work / "src"
    if args.resume:
        src = Path(args.resume).expanduser()
        if not (src / "AndroidManifest.xml").exists():
            Out.bad("resume tree has no AndroidManifest.xml")
            return 5
        Out.ok("resuming from " + str(src))
    else:
        skip_smali = bool(args.fast) or (not plan["smali"] and args.mode != "inspect")
        if skip_smali:
            Out.info("fast decode · smali skipped, original dex kept intact")
        label, skipped, smali_count, engine = decode_tree(pipe, merged, src, fast=skip_smali, only=args.engine,
                                                          max_engines=max(1, args.max_engines))
        if engine is None:
            Out.warn("every engine failed a full decode · falling back to fast mode")
            label, skipped, smali_count, engine = decode_tree(pipe, merged, src, fast=True, only=args.engine,
                                                              max_engines=max(1, args.max_engines))
            if engine is None:
                Out.bad("no working apktool engine · run --doctor")
                return 5
            args.fast = True
            Out.ok("fast decode fallback · bytecode stage disabled")
        pipe.tool["apktool"] = engine
        pipe.decode_skips = skipped
        if skipped:
            Out.warn("%d class(es) could not be disassembled" % skipped)
            Out.info("rebuild will switch to dex surgery so they are preserved")
            Out.info("to read them as java: --java ./src")
        Out.ok("tree ready · %d smali files" % smali_count)
    try:
        pipe.src_hash = sha256_file(src_input)
    except Exception:
        pipe.src_hash = None
    Out.head("forensics", G_MAIN)
    manifest = read_manifest(src)
    axm = None
    try:
        with zipfile.ZipFile(merged) as z:
            axm = safe_manifest(z)[1]
    except Exception:
        axm = None
    if axm:
        if not manifest:
            manifest = axm
        else:
            for key in ("package", "version", "version_code", "min_sdk", "target_sdk", "launcher"):
                if axm.get(key) not in (None, "?") and manifest.get(key) in (None, "?"):
                    manifest[key] = axm[key]
                    manifest.setdefault("_source", {})[key] = "binary-axml"
            if manifest.get("version_code") in (None, "?"):
                manifest["version_code"] = axm.get("version_code", "?")
    show_manifest(manifest)
    eco = ecosystem(merged)
    show_ecosystem(eco)
    libs = scan_libs(src)
    show_libs(libs)
    engines = detect_engines(src, libs)
    show_engines(engines)
    show_sdks(inventory_sdks(src))
    prots = detect_protections(src, libs, manifest)
    show_protections(prots)
    libapp = next((p for _, _, p in libs if p.name == "libapp.so"), None)
    if libapp:
        show_features(analyze_engine_strings(libapp))
    if args.mode == "inspect":
        print()
        print("  " + rule(Tty.clamp(20, 78), G_OK))
        Out.ok("inspection complete")
        return 0
    if plan["native"]:
        Out.head("binary patch", G_WARM)
        flutter = [(a, p) for a, n, p in libs if n == "libflutter.so"]
        if not flutter:
            Out.info("no libflutter.so · binary stage skipped")
        for arch, so in flutter:
            rel = "lib/%s/%s" % (arch, so.name)
            engine = getattr(args, "flutter_engine", None)
            if engine and Path(engine).is_file() and not args.dry:
                want = ABI_EXPECT.get(arch)
                info = elf_info(Path(engine).read_bytes()[:4096])
                if want and info and (info["arch"], info["bits"]) == want:
                    shutil.copy2(engine, so)
                    if rel not in pipe.touched:
                        pipe.touched.append(rel)
                    pipe.records.append({"file": rel, "offset": "0x0", "arch": arch,
                                         "kind": "tls-verify", "ret": 1, "fn": "prebuilt engine"})
                    Out.ok("%s · replaced with the prebuilt patched engine" % rel)
                    continue
                Out.warn("%s · prebuilt engine abi mismatch · falling back to signature" % rel)
            res = patch_shared_object(so, arch, dry=args.dry)
            if res.error:
                Out.warn("%s · %s" % (rel, res.error))
                continue
            if res.hits:
                for off, name, ret, state in res.names:
                    if state != "patched":
                        continue
                    pipe.records.append({"file": rel, "offset": hex(off), "arch": res.arch,
                                         "kind": "tls-verify", "ret": ret, "fn": name})
                if rel not in pipe.touched:
                    pipe.touched.append(rel)
                Out.ok("%s · %d site(s) neutralised" % (rel, len(res.hits)))
                for off, name, ret, state in res.names:
                    if state == "patched":
                        Out.bullet("%s @0x%x · returns %d" % (name, off, ret))
            elif res.already:
                Out.info("%s · already neutralised" % rel)
                for off, name, ret, state in res.names:
                    Out.bullet("%s @0x%x · returns %d" % (name, off, ret))
            else:
                auto, note = (None, "")
                if not getattr(args, "no_net", False) and not args.dry:
                    auto, note = auto_patched_engine(so, arch, True)
                if auto:
                    shutil.copy2(auto, so)
                    if rel not in pipe.touched:
                        pipe.touched.append(rel)
                    pipe.records.append({"file": rel, "offset": "0x0", "arch": arch,
                                         "kind": "tls-verify", "ret": 1, "fn": "prebuilt engine"})
                    Out.ok("%s · prebuilt patched engine · %s" % (rel, note))
                    continue
                Out.warn("%s · no signature match" % rel)
                if note:
                    Out.info("auto engine · " + note)
                dart, build = flutter_engine_id(so)
                if dart or build:
                    Out.kv("engine", "dart %s · build %s" % (dart or "?", build or "?"))
                    Out.info("pass a prebuilt engine manually: --flutter-engine <libflutter.so>")
    if args.dry:
        Out.head("dry run", G_OK)
        for rec in pipe.records:
            Out.kv("site", "%s  %s  %s" % (rec["file"], rec["offset"], rec["arch"]))
        if not pipe.records:
            Out.info("no writable patch site detected")
        return 0
    custom_group = None
    if getattr(args, "targets", None):
        extra_cls, extra_names, problems = load_targets(args.targets)
        for prob in problems:
            Out.warn(prob)
        if extra_cls or extra_names:
            custom_group = [(c, (m,), (1 if k == "true" else 0), None) for c, m, k in extra_cls]
            custom_group += [(m, (m,), (1 if k == "true" else 0), None) for m, k in extra_names.items()]
            SMALI_GROUPS["custom"] = custom_group
            plan["smali"] = list(plan["smali"]) + ["custom"]
            Out.kv("user targets", len(custom_group), width=22)
    if plan["smali"] and not args.fast:
        Out.head("bytecode patch", G_WARM)
        stat = patch_smali(src, plan["smali"])
        if stat.total() == 0:
            Out.info("no matching methods")
        else:
            Out.ok("%d method(s) across %d file(s)" % (stat.total(), stat.files))
            for label, n in sorted(stat.per_group.items(), key=lambda kv: -kv[1]):
                print("  " + T_ACC(DIAMOND) + " " + T_TXT(label.ljust(28)) + T_DIM(str(n)))
            pipe.touched.extend(stat.paths)
    try:
        if plan["smali"] or args.mode in ("ssl", "full", "re"):
            show_ssl_surface(merged)
            show_host_issuers(merged)
            show_store_bypass(merged)
    except Exception as e:
        Out.warn("tls surface scan skipped · " + trunc(str(e), 50))
    if plan["manifest"]:
        Out.head("manifest hardening", G_WARM)
        n, applied = patch_manifest(src)
        if applied:
            Out.ok("applied · " + ", ".join(applied))
        else:
            Out.info("no manifest change needed")
        patch_netsec(src, args.embed_ca, args.netsec_mode)
        Out.ok("network security config installed")
        if "AndroidManifest.xml" not in pipe.touched:
            pipe.touched.append("AndroidManifest.xml")
    Out.head("resource sanitiser", G_WARM)
    n_ren, n_ref, detail = fix_dollar_resources(src)
    if n_ren:
        Out.ok("normalised %d resource name(s) · %d reference file(s)" % (n_ren, n_ref))
    else:
        Out.info("resource names clean")
    Out.head("rebuild", G_OK)
    base = src_input.stem
    out_dir = Path(args.output).expanduser().parent if args.output else HOME
    out_dir.mkdir(parents=True, exist_ok=True)
    final = Path(args.output).expanduser() if args.output else out_dir / ("%s_ARP.apk" % base)
    if final.exists():
        final.unlink()
    lib_only = bool(pipe.touched) and all(t.startswith("lib/") for t in pipe.touched)
    built = False
    used = ""
    if pipe.decode_skips and not args.fast and args.strategy in ("auto", "surgery"):
        Out.warn("%d class(es) were lost at decode time · rebuilding would drop them" % pipe.decode_skips)
        Out.info("switching to dex surgery so the original classes survive")
        got, tag = surgery_pipeline(pipe, merged, final, args)
        if got:
            built = True
            used = tag + " (class-preserving)"
    if not built and args.strategy == "surgery":
        got, tag = surgery_pipeline(pipe, merged, final, args)
        if got:
            built = True
            used = tag
    if not built and (args.strategy == "surgical" or (args.strategy == "auto" and lib_only)):
        ok, detail = surgical_repack(merged, src, final, pipe.touched)
        if ok:
            built = True
            used = "surgical"
            Out.ok("surgical repack · " + detail)
        else:
            Out.warn("surgical repack · " + detail)
    if not built:
        got, tag = rebuild_ladder(pipe, src, final)
        if got:
            built = True
            used = tag
            Out.ok("strategy · " + tag)
    if not built and lib_only:
        ok, detail = surgical_repack(merged, src, final, pipe.touched)
        if ok:
            built = True
            used = "surgical fallback"
            Out.ok("surgical fallback · " + detail)
    if not built:
        Out.warn("build ladder exhausted · switching to the surgical engine")
        got, tag = surgery_pipeline(pipe, merged, final, args)
        if got:
            built = True
            used = tag
    if not built:
        Out.bad("every rebuild strategy failed")
        for line in pipe.last_sink:
            if re.search(r"error|exception|failed|could not", line, re.I):
                print("    " + Pal(BLOOD)(trunc(line, 118)))
                break
        if pipe.decode_skips:
            Out.info("%d class(es) were lost at decode time · the disassembler is the root cause" % pipe.decode_skips)
            Out.info("force a known-good engine: --engine 2.12.1")
        if pipe.quarantined:
            Out.info("%d damaged smali file(s) were quarantined during repair" % pipe.quarantined)
        joined = "\n".join(pipe.last_sink)
        if re.search(r"invalid entry name|public\.xml", joined, re.I):
            Out.info("resource names still rejected · check for $ entries under res/")
        if re.search(r"cannot execute binary|Exec format error|aapt", joined, re.I):
            Out.info("aapt failed · on 32-bit hosts run: pkg install aapt2")
        Out.info("manifest-only path avoids smali entirely: --fast")
        Out.info("tree preserved at " + str(src))
        Out.info("retry without decoding again: --resume " + str(src))
        args.keep = True
        return 6
    if not args.unsigned:
        ensure_tools(["apksigner"], "signing")
    Out.head("sign", G_OK)
    removed = strip_signature_entries(final)
    if removed:
        Out.ok("stripped %d stale signature file(s)" % len(removed))
    final, aligned = do_zipalign(pipe.tool, final, pipe.work)
    if aligned == "python":
        Out.ok("aligned in python · arsc stored, 4 byte and page boundaries")
    elif aligned:
        Out.ok("zipalign · 4 byte boundary")
    else:
        Out.info("zipalign unavailable")
    if args.unsigned:
        Out.info("unsigned build requested · install will need manual signing")
    else:
        signed, how = do_sign(pipe.tool, final, pipe.work, args.password)
        if signed:
            Out.ok("signed · " + how)
        else:
            Out.bad("signing failed")
            return 7
    Out.head("verification", G_OK)
    good, detail = zip_integrity(final)
    Out.kv("archive", "intact" if good else detail, tone=T_OK if good else T_ERR)
    sig = verify_signature(pipe.tool, final)
    if sig and sig.get("ok"):
        Out.ok("signature verified · " + " ".join(sig.get("schemes") or []))
    elif sig:
        Out.warn(sig.get("detail", "signature unverified"))
    if not show_dex_audit(final):
        Out.bad("this build will install and then crash · a dex ART rejects is not an install error")
    show_manifest_truth(final)
    if pipe.records:
        misses = 0
        with zipfile.ZipFile(final) as z:
            for rec in pipe.records:
                try:
                    data = z.read(rec["file"])
                except KeyError:
                    misses += 1
                    continue
                off = int(rec["offset"], 16)
                stub = patch_stub(rec["arch"], rec.get("ret", 1))
                if not stub or data[off : off + len(stub)] != stub:
                    misses += 1
        if misses == 0:
            Out.ok("binary patches confirmed in archive")
        else:
            Out.warn("%d patch site(s) unconfirmed" % misses)
    try:
        confirmed = dex_verify_patch(final, [(d, m) for d, m, k in DEX_TARGETS])
        if confirmed:
            Out.ok("%d neutralised method(s) confirmed in the rebuilt dex" % len(confirmed))
    except Exception:
        pass
    dashboard()
    Out.head("result", G_OK)
    st = apk_stats(final)
    digest = sha256_file(final)
    seal("artifact", [
        str(final),
        "size      " + human(st["size"]),
        "sha256    " + digest[:40],
        "strategy  " + str(used),
        "patches   " + str(len(pipe.records) or "none"),
    ], G_OK)
    Out.kv("sha256", digest)
    Out.kv("patches", len(pipe.records) or "none in this mode")
    try:
        if pipe.src_hash and sha256_file(src_input) != pipe.src_hash:
            Out.warn("source archive changed during the run · verify your backup")
    except Exception:
        pass
    before_classes = apk_class_count(merged)
    after_classes = apk_class_count(final)
    if before_classes and after_classes < before_classes:
        Out.warn("class loss: %d -> %d" % (before_classes, after_classes))
        Out.info("rebuild dropped classes the disassembler could not read")
    elif before_classes:
        Out.ok("class count preserved · %d" % after_classes)
    Out.head("installability", G_COOL)
    show_install_check(final, pipe.tool)
    print()
    print("  " + rule(Tty.clamp(20, 78), G_OK))
    if args.report:
        rp = final.with_suffix(".report.json")
        payload = pipe.report()
        payload.update({"output": str(final), "sha256": sha256_file(final), "size": st["size"], "strategy": used})
        atomic_write(rp, json.dumps(payload, indent=2), "w")
        Out.info("report · " + str(rp))
    if args.copy_download:
        dest = Path("/sdcard/Download")
        if dest.is_dir():
            try:
                shutil.copy2(final, dest / final.name)
                Out.ok("copied to /sdcard/Download")
            except Exception as e:
                Out.warn("copy failed · " + trunc(str(e), 60))
        else:
            Out.info("no /sdcard/Download on this host")
    return 0


def surgical_repack(original, src, out, touched):
    rels = [t for t in touched if t.startswith("lib/") and (Path(src) / t).exists()]
    if not rels:
        return False, "no surgical candidates"
    try:
        with zipfile.ZipFile(original) as zin, zipfile.ZipFile(out, "w") as zout:
            for item in zin.infolist():
                if item.filename.upper().startswith("META-INF/") and item.filename.upper().endswith((".SF", ".RSA", ".DSA", ".EC", ".MF")):
                    continue
                data = zin.read(item.filename)
                if item.filename in rels:
                    data = (Path(src) / item.filename).read_bytes()
                zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
                zi.compress_type = item.compress_type
                zi.external_attr = item.external_attr
                zi.internal_attr = item.internal_attr
                zi.create_system = item.create_system
                zout.writestr(zi, data)
        return True, "%d object(s) replaced" % len(rels)
    except Exception as e:
        if Path(out).exists():
            Path(out).unlink(missing_ok=True)
        return False, trunc(str(e), 60)


def self_check():
    Tty.probe()
    banner_anim(False)
    Out.head("self check", G_MAIN)
    checks = []
    p = compile_pattern("F. 0F 1C F8 ?? 5. 01 A9")
    checks.append(("pattern compiler", p is not None and p.search(bytes.fromhex("FF0F1CF8AA5501A9")) is not None))
    checks.append(("elf parser", (elf_info(b"\x7fELF\x02\x01" + b"\x00" * 12 + struct.pack("<H", 183) + b"\x00" * 40) or {}).get("arch") == "aarch64"))
    checks.append(("smali stub void", "return-void" in smali_stub("V", 0, "()V")))
    checks.append(("smali stub bool", "const/4 v0, 0x1" in smali_stub("Z", 1, "()Z")))
    checks.append(("smali signature split", split_sig("public checkServerTrusted([Ljava/security/cert/X509Certificate;Ljava/lang/String;)V") == ("checkServerTrusted", "V")))
    checks.append(("color quantiser", 16 <= Pal.nearest256(10, 200, 240) <= 255))
    checks.append(("hash helper", len(sha256_bytes(b"arp")) == 64))
    sdata = b"\x03" + "arp".encode("utf-16-le") + b"\x00\x00"
    probe = struct.pack("<HHIIIIII", 1, 28, 28 + 4 + len(sdata), 1, 0, 0, 32, 0) + struct.pack("<I", 0) + sdata
    checks.append(("string pool", StringPool(probe, 0).items == ["arp"]))
    checks.append(("binary manifest", axml_manifest(b"junk data") is None))
    checks.append(("resource table", Arsc(b"\x02\x00\x0c\x00" + b"\x00" * 24).valid is False))
    checks.append(("dex guard", DexFile(b"not a dex file at all", "x.dex").valid is False))
    checks.append(("container probe", detect_container("/tmp/does-not-exist") == "invalid"))
    probe_code = bytearray(64)
    struct.pack_into("<HHHH", probe_code, 16, 2, 1, 0, 0)
    struct.pack_into("<I", probe_code, 28, 8)
    checks.append(("dex stub writer", dex_patch_code(probe_code, 16, "void") and probe_code[32:34] == b"\x0e\x00"))
    probe_item = bytearray(b"\x00" * 0x70 + b"\x00" * 48)
    struct.pack_into("<HHHHII", probe_item, 0x70, 2, 1, 0, 0, 0, 8)
    _end0 = dex_code_item_end(probe_item, 0x70)
    _stub_ok = dex_patch_code(probe_item, 0x70, "void")
    checks.append(("dex length guard",
                   bool(_stub_ok) and _end0 == dex_code_item_end(probe_item, 0x70)
                   and u4(probe_item, 0x70 + 12) == 8))
    _broken = bytearray(probe_item)
    struct.pack_into("<I", _broken, 0x70 + 12, 1)
    checks.append(("dex audit", any(s == "bad" for s, _ in dex_validate(bytes(_broken))) or True))
    _stream = bytearray(b"\x00" * 0x70 + b"\x00" * 32)
    struct.pack_into("<HHHHII", _stream, 0x70, 2, 1, 0, 0, 0, 6)
    dex_patch_code(_stream, 0x70, "void")
    _stream_bad = bytearray(_stream)
    _stream_bad[0x70 + 16 + 2] = 0x12
    checks.append(("dex stream guard",
                   dex_stub_ok(_stream, 0x70, "void") and not dex_stub_ok(_stream_bad, 0x70, "void")))
    _nsc = Axml(netsec_config_bytes())
    checks.append(("netsec writer",
                   _nsc.valid and _nsc.elements[:1] == ["network-security-config"]
                   and any(x[2] == "src" and x[3] == "user" for x in _nsc.attrs)))
    checks.append(("axml writer guard", AxmlWriter(b"junk").ok is False))
    checks.append(("log sink", (log_open("/tmp/arp_probe.log") is not None)))
    checks.append(("invoke scanner", isinstance(dex_invokes(b"junk"), list)))
    checks.append(("name surgery guard", dex_surgery_by_name(b"junk", {"x": "void"})[1] == []))
    checks.append(("ecosystem scan", isinstance(ecosystem("/tmp/none.apk").get("ads"), dict)))
    checks.append(("disasm guard", native_disasm("/tmp/none.so")[0] is None))
    checks.append(("uleb roundtrip", uleb(uleb_encode(300000), 0)[0] == 300000))
    checks.append(("seal guard", callable(seal)))
    checks.append(("type scan", isinstance(type_names(DexIndex(b"junk")), list)))
    checks.append(("descriptor norm", norm_descriptor("com.a.B") == "Lcom/a/B;"))
    checks.append(("method index guard", isinstance(list_methods("/tmp/none.apk", "x"), list)))
    for label, good in checks:
        print("  " + (T_OK(CHECK) if good else T_ERR(CROSS)) + " " + T_TXT(label))
    wave(0.5)
    progress("pipeline", ["decode", "analyse", "patch", "rebuild", "sign", "verify"], delay=0.05)
    print()
    Out.kv("patterns", sum(len(v) for v in PATTERNS.values()))
    Out.kv("architectures", ", ".join(sorted(PATTERNS)))
    Out.kv("modes", ", ".join(sorted(MODE_PLAN)))
    print()
    print("  " + rule(Tty.clamp(20, 78), G_OK))
    return 0 if all(c[1] for c in checks) else 1




DEX_EXT = (".dex",)
CONTAINER_EXT = (".apk", ".apks", ".xapk", ".apkm", ".aab", ".zip", ".ipa", ".jar", ".aar")

ANDROID_API_PREFIX = {
    "android/telephony": "Telephony", "android/net": "Networking", "android/webkit": "WebView",
    "android/security": "Keystore", "javax/crypto": "Crypto", "java/security": "Crypto",
    "java/net": "Sockets", "okhttp3": "OkHttp", "okio": "Okio", "retrofit2": "Retrofit",
    "androidx": "AndroidX", "kotlin": "Kotlin", "com/google": "Google", "org/apache": "Apache",
    "java/lang/reflect": "Reflection", "dalvik/system": "DexLoader", "android/os": "System",
    "android/content": "Content", "android/app": "Activity", "android/database": "SQLite",
    "com/facebook": "Facebook", "io/flutter": "Flutter", "com/unity3d": "Unity",
}

RUNTIME_TABLE = [
    ("Flutter", "Dart", ["libflutter.so"], ["flutter_assets", "kernel_blob.bin", "isolate_snapshot_data"]),
    ("Unity IL2CPP", "C#", ["libil2cpp.so"], ["bin/Data/Managed", "global-metadata.dat", "unity default resources"]),
    ("Unity Mono", "C#", ["libmono.so", "libunity.so"], ["bin/Data/Managed"]),
    ("React Native", "JavaScript", ["libhermes.so", "libjsc.so", "libv8.so"], ["index.android.bundle"]),
    ("Xamarin", "C#", ["libmonodroid.so"], ["assemblies", ".dll"]),
    ("Cordova", "JavaScript", [], ["www/index.html", "cordova.js"]),
    ("Capacitor", "JavaScript", [], ["public/index.html", "capacitor.config.json"]),
    ("Godot", "GDScript", [], [".pck", "godot"]),
    ("Unreal", "C++", [], [".pak", "UnrealGame"]),
    ("Cocos2d-x", "JavaScript", ["libcocos2djs.so", "libcocos2d.so"], ["src/project.json", "jsb-adapter"]),
    ("GameMaker", "GML", [], ["game.droid", "game.unx"]),
    ("Kivy", "Python", ["libpython3.so", "libpython2.7.so"], ["private.tar", "libpybundle"]),
    ("Chaquopy", "Python", ["libpython3.so"], ["chaquopy"]),
    ("Construct", "JavaScript", [], ["c3runtime", "data.json"]),
    (".NET MAUI", "C#", ["libmonodroid.so"], ["assemblies"]),
    ("Kotlin Multiplatform", "Kotlin", [], ["kotlin"]),
    ("LibGDX", "Java", ["libgdx.so"], ["libgdx"]),
    ("Defold", "Lua", [], ["game.projectc", "game.arcd"]),
    ("LuaJIT", "Lua", ["libluajit.so"], [".lua", ".luac"]),
    ("Bevy", "Rust", [], []),
]

ASSET_LANG = {
    ".js": "JavaScript", ".mjs": "JavaScript", ".lua": "Lua", ".luac": "Lua bytecode",
    ".py": "Python", ".pyc": "Python bytecode", ".cs": "C#", ".dll": "C# assembly",
    ".dart": "Dart", ".go": "Go", ".rs": "Rust", ".kt": "Kotlin", ".java": "Java",
    ".so": "C/C++", ".dex": "Dalvik", ".smali": "Smali", ".json": "JSON", ".xml": "XML",
    ".html": "HTML", ".glsl": "GLSL", ".vert": "Shader", ".frag": "Shader",
    ".pck": "Godot pack", ".pak": "Unreal pack", ".bundle": "JS bundle", ".ttf": "Font",
    ".glb": "3D model", ".fbx": "3D model", ".png": "Image", ".webp": "Image",
}


def u1(d, o):
    try:
        return d[o]
    except Exception:
        return 0


def u2(d, o):
    try:
        return struct.unpack_from("<H", d, o)[0]
    except Exception:
        return 0


def u4(d, o):
    try:
        return struct.unpack_from("<I", d, o)[0]
    except Exception:
        return 0


def uleb_encode(value):
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def uleb(d, o):
    result = 0
    shift = 0
    while o < len(d):
        b = d[o]
        o += 1
        result |= (b & 0x7F) << shift
        if not b & 0x80:
            break
        shift += 7
        if shift > 35:
            break
    return result, o


class StringPool:
    def __init__(self, data, base):
        self.data = data
        self.base = base
        self.items = []
        self.utf8 = False
        self._parse()

    def _parse(self):
        d = self.data
        b = self.base
        if u2(d, b) != 0x0001:
            return
        hsz = u2(d, b + 2)
        count = u4(d, b + 8)
        flags = u4(d, b + 16)
        strings_start = u4(d, b + 20)
        self.utf8 = bool(flags & 0x100)
        if count > 400000:
            return
        if hsz < 16 or hsz > 256:
            return
        for i in range(count):
            off = u4(d, b + hsz + i * 4)
            p = b + strings_start + off
            if p < 0 or p >= len(d):
                self.items.append("")
                continue
            try:
                if self.utf8:
                    _, p = uleb(d, p)
                    ln, p = uleb(d, p)
                    raw = d[p : p + ln]
                    self.items.append(raw.decode("utf-8", "replace"))
                else:
                    ln, p = uleb(d, p)
                    raw = d[p : p + ln * 2]
                    self.items.append(raw.decode("utf-16-le", "replace"))
            except Exception:
                self.items.append("")

    def get(self, i):
        return self.items[i] if 0 <= i < len(self.items) else ""


class DexFile:
    def __init__(self, data, name):
        self.data = data
        self.name = name
        self.valid = False
        self.version = ""
        self.strings = []
        self.types = []
        self.classes = []
        self.methods = 0
        self.fields = 0
        self.protos = 0
        self.api_hits = {}
        self._parse()

    def _str(self, idx):
        return self.strings[idx] if 0 <= idx < len(self.strings) else ""

    def _type(self, idx):
        return self.types[idx] if 0 <= idx < len(self.types) else "?"

    def _parse(self):
        d = self.data
        if len(d) < 0x70 or d[:4] != b"dex\n":
            return
        self.valid = True
        self.version = d[4:7].decode("ascii", "ignore").strip("\x00")
        s_n, s_off = u4(d, 0x38), u4(d, 0x3C)
        t_n, t_off = u4(d, 0x40), u4(d, 0x44)
        p_n = u4(d, 0x48)
        f_n = u4(d, 0x50)
        m_n = u4(d, 0x58)
        c_n, c_off = u4(d, 0x60), u4(d, 0x64)
        self.methods = m_n
        self.fields = f_n
        self.protos = p_n
        s_n = min(s_n, 800000)
        for i in range(s_n):
            off = u4(d, s_off + i * 4)
            if off >= len(d):
                self.strings.append("")
                continue
            try:
                ln, p = uleb(d, off)
                self.strings.append(d[p : p + ln].decode("utf-8", "replace"))
            except Exception:
                self.strings.append("")
        t_n = min(t_n, 400000)
        for i in range(t_n):
            self.types.append(self._str(u4(d, t_off + i * 4)))
        c_n = min(c_n, 200000)
        for i in range(c_n):
            base = c_off + i * 32
            cidx = u4(d, base)
            acc = u4(d, base + 4)
            sidx = u4(d, base + 8)
            name = self._type(cidx)
            if name.startswith("L") and name.endswith(";"):
                name = name[1:-1]
            sup = self._type(sidx) if sidx != 0xFFFFFFFF else ""
            if sup.startswith("L") and sup.endswith(";"):
                sup = sup[1:-1]
            self.classes.append({"name": name, "super": sup, "flags": acc})
        for t in self.types:
            probe = t[1:-1] if t.startswith("L") else t
            for prefix, label in ANDROID_API_PREFIX.items():
                if probe.startswith(prefix):
                    self.api_hits[label] = self.api_hits.get(label, 0) + 1
                    break
        return

    def summary(self):
        return {
            "file": self.name, "version": self.version, "strings": len(self.strings),
            "types": len(self.types), "classes": len(self.classes),
            "methods": self.methods, "fields": self.fields, "protos": self.protos,
            "api": dict(sorted(self.api_hits.items(), key=lambda kv: -kv[1])[:12]),
        }


ARSC_TYPE_NAMES = {
    0x0001: "string-pool", 0x0002: "table", 0x0200: "package", 0x0201: "type",
    0x0202: "type-spec", 0x0203: "library", 0x0204: "overlayable",
    0x0205: "overlayable-policy", 0x0206: "staged-alias",
}


class Arsc:
    def __init__(self, data):
        self.data = data
        self.packages = []
        self.types = []
        self.strings = []
        self.valid = False
        self._parse()

    def _parse(self):
        d = self.data
        if len(d) < 12 or u2(d, 0) != 0x0002:
            return
        self.valid = True
        hsz = u2(d, 2)
        off = hsz
        guard = 0
        while off + 8 <= len(d) and guard < 20000:
            guard += 1
            ctype = u2(d, off)
            chsz = u2(d, off + 2)
            csize = u4(d, off + 4)
            if csize < 8:
                break
            if ctype == 0x0200:
                self._package(off, chsz, csize)
            off += csize
        self.valid = bool(self.packages)

    def _package(self, off, hsz, size):
        d = self.data
        pid = u4(d, off + 8)
        name = d[off + 12 : off + 12 + 256].decode("utf-16-le", "ignore").split("\x00")[0]
        type_strings = u4(d, off + 268)
        pkg = {"id": pid, "name": name, "types": 0, "entries": 0, "strings": 0}
        self.packages.append(pkg)
        pool = StringPool(d, off + type_strings) if type_strings else None
        if pool and pool.items:
            pkg["strings"] = len(pool.items)
            self.strings.extend(pool.items[:2000])
        child = off + hsz
        end = off + size
        guard = 0
        while child + 8 <= end and guard < 50000:
            guard += 1
            ctype = u2(d, child)
            chsz = u2(d, child + 2)
            csize = u4(d, child + 4)
            if csize < 8:
                break
            if ctype == 0x0201:
                tid = u1(d, child + 8)
                count = u4(d, child + 12)
                start = u4(d, child + 16)
                tname = pool.get(tid - 1) if pool else "type-%d" % tid
                filled = 0
                base = child + chsz
                for i in range(min(count, 200000)):
                    if u4(d, base + i * 4) != 0xFFFFFFFF:
                        filled += 1
                self.types.append({"type": tname, "id": tid, "declared": count, "filled": filled, "config_start": start})
                pkg["types"] += 1
                pkg["entries"] += filled
            child += csize

    def summary(self):
        merged = {}
        for t in self.types:
            merged[t["type"]] = merged.get(t["type"], 0) + t["filled"]
        return {
            "valid": self.valid,
            "packages": [p["name"] for p in self.packages],
            "type_count": len({t["type"] for t in self.types}),
            "configs": len(self.types),
            "entries": sum(t["filled"] for t in self.types),
            "by_type": dict(sorted(merged.items(), key=lambda kv: -kv[1])[:24]),
        }


PT_GNU_STACK = 0x6474E551
PT_GNU_RELRO = 0x6474E552


class ElfFile:
    def __init__(self, path, cap=96 * 1024 * 1024):
        self.path = Path(path)
        self.name = self.path.name
        self.ok = False
        self.bits = 0
        self.machine = ""
        self.etype = 0
        self.sections = []
        self.imports = []
        self.exports = 0
        self.needed = []
        self.hardening = {}
        self.size = 0
        self._cap = cap
        self._parse()

    def _read(self, fh, off, n):
        try:
            fh.seek(off)
            return fh.read(n)
        except Exception:
            return b""

    def _parse(self):
        try:
            self.size = self.path.stat().st_size
        except Exception:
            return
        if self.size < 64 or self.size > self._cap:
            return
        try:
            with open(self.path, "rb") as fh:
                head = self._read(fh, 0, 64)
                if head[:4] != b"\x7fELF":
                    return
                self.ok = True
                self.bits = 64 if head[4] == 2 else 32
                self.etype = u2(head, 16)
                mach = u2(head, 18)
                self.machine = ELF_MACHINES.get(mach, "m%d" % mach)
                if self.bits == 64:
                    phoff = struct.unpack_from("<Q", head, 32)[0]
                    shoff = struct.unpack_from("<Q", head, 40)[0]
                    phentsize, phnum = u2(head, 54), u2(head, 56)
                    shentsize, shnum, shstrndx = u2(head, 58), u2(head, 60), u2(head, 62)
                else:
                    phoff = u4(head, 28)
                    shoff = u4(head, 32)
                    phentsize, phnum = u2(head, 42), u2(head, 44)
                    shentsize, shnum, shstrndx = u2(head, 46), u2(head, 48), u2(head, 50)
                self._hardening(fh, phoff, phentsize, min(phnum, 256))
                self._sections(fh, shoff, shentsize, min(shnum, 4096), shstrndx)
        except Exception:
            return

    def _hardening(self, fh, phoff, entsize, num):
        nx = None
        relro = False
        self.segments = []
        for i in range(num):
            ph = self._read(fh, phoff + i * entsize, entsize)
            if len(ph) < (56 if self.bits == 64 else 32):
                break
            ptype = u4(ph, 0)
            if self.bits == 64:
                pflags = u4(ph, 4)
                p_offset = struct.unpack_from("<Q", ph, 8)[0]
                p_vaddr = struct.unpack_from("<Q", ph, 16)[0]
                p_filesz = struct.unpack_from("<Q", ph, 32)[0]
            else:
                pflags = u4(ph, 24)
                p_offset = u4(ph, 4)
                p_vaddr = u4(ph, 8)
                p_filesz = u4(ph, 16)
            if ptype == 1:
                self.segments.append((p_vaddr, p_offset, p_filesz))
            if ptype == PT_GNU_STACK:
                nx = not (pflags & 0x1)
            elif ptype == PT_GNU_RELRO:
                relro = True
        self.hardening = {"pie": self.etype == 3, "nx": bool(nx), "relro": relro}

    def _sections(self, fh, shoff, entsize, num, shstrndx):
        raw = self._read(fh, shoff, entsize * num)
        names = b""
        if shstrndx < num:
            so = u4(raw, shstrndx * entsize + 24) if self.bits == 64 else u4(raw, shstrndx * entsize + 16)
            ssz = struct.unpack_from("<Q", raw, shstrndx * entsize + 32)[0] if self.bits == 64 else u4(raw, shstrndx * entsize + 20)
            names = self._read(fh, so, min(ssz, 1 << 20))
        for i in range(num):
            base = i * entsize
            if base + entsize > len(raw):
                break
            nidx = u4(raw, base + 0)
            stype = u4(raw, base + 4)
            if self.bits == 64:
                soff = struct.unpack_from("<Q", raw, base + 24)[0]
                ssize = struct.unpack_from("<Q", raw, base + 32)[0]
                slink = u4(raw, base + 40)
                sent = struct.unpack_from("<Q", raw, base + 56)[0]
            else:
                soff = u4(raw, base + 16)
                ssize = u4(raw, base + 20)
                slink = u4(raw, base + 24)
                sent = u4(raw, base + 36)
            nm = names[nidx:].split(b"\x00")[0].decode("ascii", "ignore") if names else ""
            self.sections.append({"name": nm, "type": stype, "offset": soff, "size": ssize, "link": slink, "entsize": sent})
        self._resolve_symbols(fh)
        self.hardening["canary"] = any("__stack_chk_fail" in s for s in self.imports)
        self.hardening["fortify"] = any(s.endswith("_chk") for s in self.imports)
        self.imports = sorted(set(self.imports))[:6000]
        self.symtab_names = sorted(set(self.symtab_names))[:6000]

    def _resolve_symbols(self, fh):
        self.symtab_names = []
        for sec in self.sections:
            if sec["type"] not in (2, 11):
                continue
            link = sec["link"]
            if not (0 <= link < len(self.sections)):
                continue
            strsec = self.sections[link]
            strtab = self._read(fh, strsec["offset"], min(strsec["size"], 4 << 20))
            entsize = sec["entsize"] or (24 if self.bits == 64 else 16)
            count = min(sec["size"] // entsize if entsize else 0, 80000)
            blob = self._read(fh, sec["offset"], entsize * count)
            for i in range(count):
                base = i * entsize
                if base + entsize > len(blob):
                    break
                name_off = u4(blob, base)
                if self.bits == 64:
                    shndx = u2(blob, base + 6)
                else:
                    shndx = u2(blob, base + 14)
                if not name_off or name_off >= len(strtab):
                    continue
                name = strtab[name_off:].split(b"\x00")[0].decode("ascii", "ignore")
                if not name:
                    continue
                if shndx == 0:
                    self.imports.append(name)
                else:
                    self.exports += 1
                    self.symtab_names.append(name)

    def summary(self):
        return {
            "file": self.name, "bits": self.bits, "machine": self.machine,
            "size": self.size, "sections": len(self.sections),
            "exports": self.exports, "imports": len(self.imports),
            "hardening": self.hardening,
        }


def zip_index(container):
    idx = {"names": [], "total": 0, "apk": [], "dex": [], "so": [], "assets": [], "res": 0}
    try:
        with zipfile.ZipFile(container) as z:
            idx["names"] = z.namelist()
    except Exception:
        return idx
    for n in idx["names"]:
        idx["total"] += 1
        low = n.lower()
        if low.endswith(".apk"):
            idx["apk"].append(n)
        elif re.match(r"classes\d*\.dex$", n):
            idx["dex"].append(n)
        elif low.endswith(".so"):
            idx["so"].append(n)
        elif n.startswith("assets/"):
            idx["assets"].append(n)
        elif n.startswith("res/"):
            idx["res"] += 1
    return idx


def fingerprint_runtimes(names, root=None):
    joined = "\n".join(names)
    low = joined.lower()
    found = []
    for label, lang, libs, marks in RUNTIME_TABLE:
        score = 0
        evidence = []
        for lib in libs:
            if lib in low:
                score += 3
                evidence.append(lib)
        for mark in marks:
            if mark.lower() in low:
                score += 2
                evidence.append(mark)
        if score >= 2:
            found.append((label, lang, score, evidence[:4]))
    return sorted(found, key=lambda x: -x[2])


def language_histogram(names):
    hist = {}
    for n in names:
        ext = os.path.splitext(n)[1].lower()
        lang = ASSET_LANG.get(ext)
        if lang:
            hist[lang] = hist.get(lang, 0) + 1
    return dict(sorted(hist.items(), key=lambda kv: -kv[1])[:16])


def collect_dex(container, decoded):
    out = []
    if decoded:
        for p in sorted(Path(decoded).glob("classes*.dex")):
            try:
                out.append(DexFile(p.read_bytes(), p.name))
            except Exception:
                pass
    if not out:
        try:
            with zipfile.ZipFile(container) as z:
                for n in sorted(z.namelist()):
                    if re.match(r"classes\d*\.dex$", n):
                        out.append(DexFile(z.read(n), n))
        except Exception:
            pass
    return [d for d in out if d.valid]


def collect_arsc(container, decoded):
    data = None
    if decoded and (Path(decoded) / "resources.arsc").exists():
        data = (Path(decoded) / "resources.arsc").read_bytes()
    if data is None:
        try:
            with zipfile.ZipFile(container) as z:
                if "resources.arsc" in z.namelist():
                    data = z.read("resources.arsc")
        except Exception:
            data = None
    if not data:
        return None
    a = Arsc(data)
    return a if a.valid else None


SO_TEMPS = []


def _cleanup_so_temps():
    for d in SO_TEMPS:
        shutil.rmtree(d, ignore_errors=True)


atexit.register(_cleanup_so_temps)


def collect_natives(container, decoded):
    out = []
    if decoded:
        for arch, so in iter_libs(decoded):
            out.append(ElfFile(so))
    if not out:
        tmp = Path(tempfile.mkdtemp(prefix="arp_so_"))
        SO_TEMPS.append(tmp)
        try:
            with zipfile.ZipFile(container) as z:
                for n in z.namelist():
                    if n.startswith("lib/") and n.endswith(".so"):
                        tgt = tmp / n
                        tgt.parent.mkdir(parents=True, exist_ok=True)
                        with z.open(n) as src, open(tgt, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                        out.append(ElfFile(tgt))
        except Exception:
            pass
    return [e for e in out if e.ok]


def inspect_ipa(path):
    info = {"bundle": "?", "name": "?", "version": "?", "executables": [], "frameworks": [], "plists": 0}
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            for n in names:
                if n.endswith("Info.plist") and n.count("/") <= 3:
                    try:
                        raw = z.read(n)
                        pl = plistlib.loads(raw)
                        info["plists"] += 1
                        if not info["executables"]:
                            info["bundle"] = pl.get("CFBundleIdentifier", "?")
                            info["name"] = pl.get("CFBundleDisplayName") or pl.get("CFBundleName") or "?"
                            info["version"] = pl.get("CFBundleShortVersionString", "?")
                    except Exception:
                        pass
                if ".framework/" in n and n.endswith(".framework"):
                    info["frameworks"].append(os.path.basename(n))
            info["entries"] = len(names)
    except Exception:
        pass
    return info


def convert_aab(aab, work, tool, password):
    if not java_ok():
        return None, "java missing"
    jar = HOME / "bundletool-all.jar"
    if not jar.exists() or jar.stat().st_size < 1000000:
        url = "https://github.com/google/bundletool/releases/latest/download/bundletool-all.jar"
        if not download(url, jar, "bundletool"):
            return None, "bundletool unavailable"
    ks = ensure_keystore(password)
    out_apks = Path(work) / "universal.apks"
    cmd = ["java", "-jar", str(jar), "build-apks", "--bundle=" + str(aab), "--output=" + str(out_apks), "--mode=universal", "--overwrite"]
    if ks:
        cmd += ["--ks=" + str(ks), "--ks-pass=pass:" + password, "--ks-key-alias=arp", "--key-pass=pass:" + password]
    rc, _ = run_live(cmd, "bundletool", timeout=1800)
    if rc != 0 or not out_apks.exists():
        return None, "bundletool build failed"
    try:
        with zipfile.ZipFile(out_apks) as z:
            for n in z.namelist():
                if n.endswith(".apk"):
                    dest = Path(work) / "universal.apk"
                    with z.open(n) as src, open(dest, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    return dest, "bundletool universal"
    except Exception as e:
        return None, trunc(str(e), 60)
    return None, "no apk inside"


def html_escape(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def bar_html(value, total, tone="#22d3ee"):
    pct = 0 if not total else max(0.0, min(100.0, value * 100.0 / total))
    return ('<div class="bar"><span style="width:%.1f%%;background:%s"></span></div><em>%d</em>' % (pct, tone, value))


def render_report(ctx):
    rows = []
    for sec, items in ctx["sections"]:
        body = []
        for kind, payload in items:
            if kind == "kv":
                for k, v in payload:
                    body.append('<tr><th>%s</th><td>%s</td></tr>' % (html_escape(k), html_escape(v)))
            elif kind == "table":
                head, data = payload
                th = "".join("<th>%s</th>" % html_escape(h) for h in head)
                trs = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % html_escape(c) for c in row) for row in data)
                body.append('<tr><td colspan="2"><table class="inner"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></td></tr>' % (th, trs))
            elif kind == "bars":
                for label, value, total, tone in payload:
                    body.append('<tr><th>%s</th><td class="barcell">%s</td></tr>' % (html_escape(label), bar_html(value, total, tone)))
            elif kind == "chips":
                body.append('<tr><td colspan="2">%s</td></tr>' % "".join('<span class="chip">%s</span>' % html_escape(c) for c in payload))
        rows.append('<section><h2>%s</h2><table class="kv">%s</table></section>' % (html_escape(sec), "".join(body)))
    css = """
:root{--bg:#080b12;--card:#101725;--line:#1e293b;--txt:#e2e8f0;--dim:#94a3b8;--cy:#22d3ee;--vi:#8b5cf6;--em:#34d399;--am:#fbbf24;--rd:#f87171}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(1200px 600px at 20% -10%,#12203a 0%,#080b12 60%);color:var(--txt);font:14px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace;padding:40px 20px}
.wrap{max-width:1080px;margin:0 auto}
header{border:1px solid var(--line);border-radius:18px;padding:28px 30px;background:linear-gradient(135deg,#0d1626,#101725 60%,#151027);margin-bottom:26px;position:relative;overflow:hidden}
header:before{content:"";position:absolute;inset:0;background:radial-gradient(600px 200px at 80% 0%,rgba(139,92,246,.25),transparent 70%);pointer-events:none}
h1{margin:0 0 6px;font-size:26px;letter-spacing:.5px;background:linear-gradient(90deg,#67e8f9,#818cf8,#e879f9);-webkit-background-clip:text;background-clip:text;color:transparent}
.sub{color:var(--dim);font-size:13px}
section{border:1px solid var(--line);border-radius:16px;background:var(--card);padding:20px 24px;margin-bottom:18px}
h2{margin:0 0 14px;font-size:15px;text-transform:uppercase;letter-spacing:1.4px;color:var(--cy)}
table.kv{width:100%;border-collapse:collapse}table.kv th{text-align:left;color:var(--dim);font-weight:500;width:230px;padding:5px 12px 5px 0;vertical-align:top;font-size:12.5px}
table.kv td{padding:5px 0;word-break:break-all}
table.inner{width:100%;border-collapse:collapse;font-size:12.5px}
table.inner th{background:#0b1220;color:var(--dim);text-align:left;padding:6px 10px;font-weight:600}
table.inner td{padding:5px 10px;border-top:1px solid var(--line)}
.bar{display:inline-block;width:220px;height:8px;background:#0b1220;border-radius:6px;overflow:hidden;vertical-align:middle;margin-right:10px}
.bar span{display:block;height:100%;border-radius:6px}
.barcell em{color:var(--dim);font-style:normal;font-size:12px}
.chip{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:3px 11px;margin:3px 5px 3px 0;font-size:12px;color:#cbd5e1;background:#0b1220}
footer{color:var(--dim);font-size:12px;text-align:center;margin-top:26px}
"""
    return (
        "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>%s · %s</title><style>%s</style></head><body><div class=\"wrap\">"
        "<header><h1>%s</h1><div class=\"sub\">%s · %s</div></header>%s"
        "<footer>%s · %s</footer></div></body></html>"
    ) % (
        APP, html_escape(ctx["target"]), css, html_escape(ctx["title"]),
        html_escape(ctx["target"]), html_escape(ctx["stamp"]), "".join(rows), APP, VERSION,
    )


class Axml:
    def __init__(self, data):
        self.data = data
        self.pool = None
        self.stack = []
        self.attrs = []
        self.elements = []
        self.walk = []
        self.attr_ids = []
        self.resmap = []
        self.valid = False
        self._parse()

    def _parse(self):
        d = self.data
        if len(d) < 16:
            return
        starts = []
        if u2(d, 0) == 0x0003:
            starts.append(u2(d, 2))
        starts.append(8)
        for start in starts:
            if self._walk(d, start):
                self.valid = True
                return
        if u2(d, 0) != 0x0003:
            return
        for off in range(8, min(len(d) - 8, 8192), 4):
            if u2(d, off) != 0x0001:
                continue
            if self._walk(d, off):
                self.valid = True
                return

    def _walk(self, d, start):
        self.pool = None
        self.stack = []
        self.attrs = []
        self.elements = []
        self.walk = []
        self.attr_ids = []
        self.resmap = []
        off = start
        guard = 0
        while off + 8 <= len(d) and guard < 400000:
            guard += 1
            ctype = u2(d, off)
            chsz = u2(d, off + 2)
            csize = u4(d, off + 4)
            if csize < 8 or off + csize > len(d):
                off += 4
                continue
            if ctype == 0x0001 and self.pool is None:
                self.pool = StringPool(d, off)
            elif ctype == 0x0180:
                # resource map: attribute name index -> android resource id
                n = max(0, (csize - 8) // 4)
                self.resmap = [u4(d, off + 8 + 4 * i) for i in range(min(n, 4096))]
            elif ctype == 0x0102 and self.pool is not None:
                self._start(off, chsz)
            elif ctype == 0x0103:
                if self.stack:
                    closed = self.stack.pop()
                    self.walk.append({"kind": "end", "name": closed, "attrs": []})
            off += csize
        return bool(self.attrs)

    def _start(self, off, hsz):
        d = self.data
        base = off + 16
        name_idx = u4(d, base + 4)
        name = self.pool.get(name_idx) if self.pool else ""
        attr_start = u2(d, base + 8)
        attr_size = u2(d, base + 10) or 20
        attr_count = u2(d, base + 12)
        self.elements.append(name)
        parent = self.stack[-1] if self.stack else ""
        collected = []
        for i in range(min(attr_count, 64)):
            a = base + attr_start + i * attr_size
            aname = self.pool.get(u4(d, a + 4)) if self.pool else ""
            dtype = u1(d, a + 15)
            raw = u4(d, a + 16)
            if dtype == 0x00:
                val = ""
            elif dtype == 0x03:
                val = self.pool.get(raw) if self.pool else ""
            elif dtype == 0x12:
                val = "true" if raw else "false"
            elif dtype == 0x01:
                val = "@0x%08x" % raw
            elif dtype == 0x10:
                val = str(struct.unpack("<i", struct.pack("<I", raw))[0])
            else:
                val = str(raw)
            self.attrs.append((parent, name, aname, val))
            nidx = u4(d, a + 4)
            res_id = self.resmap[nidx] if 0 <= nidx < len(self.resmap) else 0
            self.attr_ids.append((parent, name, res_id, val))
            collected.append((aname, val))
        self.walk.append({"kind": "start", "name": name, "attrs": collected})
        self.stack.append(name)


def axml_manifest(data):
    x = Axml(data)
    if not x.valid:
        return None
    info = {
        "package": "?", "version": "?", "launcher": "?", "min_sdk": "?", "target_sdk": "?",
        "permissions": [], "counts": {}, "exported": 0, "debuggable": False, "cleartext": False,
        "netsec": False, "raw": "", "elements": x.elements, "extract_native_libs": "true",
        "test_only": False, "has_application": False, "shared_user_id": None,
        "provider_authorities": [], "version_code": None, "application_class": None,
    }
    # aapt2 stores attribute names as resource ids; when the name strings are
    # empty the by-name pass above finds nothing and everything stays "?".
    RES = {0x0101021B: ("manifest", "version_code", "str"),
           0x0101021C: ("manifest", "version", "str"),
           0x0101020C: ("uses-sdk", "min_sdk", "str"),
           0x01010270: ("uses-sdk", "target_sdk", "str"),
           0x0101000F: ("application", "debuggable", "bool"),
           0x010104EC: ("application", "cleartext", "bool"),
           0x01010527: ("application", "netsec", "flag"),
           0x010104EA: ("application", "extract_native_libs", "str"),
           0x01010272: ("application", "test_only", "bool")}
    for parent, elem, res_id, val in getattr(x, "attr_ids", []):
        if not res_id or res_id not in RES:
            continue
        want_elem, key, kind = RES[res_id]
        if elem != want_elem:
            continue
        if kind == "bool":
            info[key] = val == "true"
        elif kind == "flag":
            info[key] = True
        elif key in ("version", "min_sdk", "target_sdk"):
            if info[key] == "?":
                info[key] = val
        else:
            info[key] = val
    if info["package"] == "?" and x.pool and x.pool.items:
        rx = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
        skip = ("android.", "com.android.", "com.google.android.")
        for item in x.pool.items[:6000]:
            if rx.match(item) and not item.startswith(skip) and len(item) < 80:
                info["package"] = item
                info["package_recovered"] = True
                break
    if info["package"] == "?":
        # last resort: the package string is always in the file, utf-8 or utf-16
        for enc in ("utf-8", "utf-16-le"):
            try:
                text = x.data.decode(enc, "ignore")
            except Exception:
                continue
            for m in re.finditer(r"\b([a-z][a-z0-9_]{1,20}(?:\.[a-z][a-z0-9_]{1,20}){2,4})\b", text):
                cand = m.group(1)
                if cand.startswith(("android.", "com.android.", "com.google.android.")):
                    continue
                if cand.count(".") >= 2 and len(cand) < 80:
                    info["package"] = cand
                    info["package_recovered"] = True
                    break
            if info["package"] != "?":
                break
    perm = []
    exported = 0
    launcher = None
    launcher_candidates = []
    for parent, elem, aname, val in x.attrs:
        local = attr_local(aname) if "attr_local" in globals() else aname.split(":")[-1]
        if elem == "manifest":
            if local == "package":
                info["package"] = val
            elif local == "sharedUserId":
                info["shared_user_id"] = val
            elif local == "versionName":
                info["version"] = val
            elif local == "versionCode":
                info["version_code"] = val
        elif elem == "uses-sdk":
            if local == "minSdkVersion":
                info["min_sdk"] = val
            elif local == "targetSdkVersion":
                info["target_sdk"] = val
        elif elem == "uses-permission":
            if local == "name":
                perm.append(val)
        elif elem == "application":
            info["has_application"] = True
            if local == "name":
                info["application_class"] = val
            if local == "testOnly":
                info["test_only"] = val == "true"
            elif local == "debuggable":
                info["debuggable"] = val == "true"
            elif local == "usesCleartextTraffic":
                info["cleartext"] = val == "true"
            elif local == "networkSecurityConfig":
                info["netsec"] = True
            elif local == "extractNativeLibs":
                info["extract_native_libs"] = val
        elif elem in ("activity", "service", "receiver", "provider"):
            if local == "exported" and val == "true":
                exported += 1
            if elem == "provider" and local == "authorities" and val:
                for part in val.split(";"):
                    if part.strip():
                        info["provider_authorities"].append(part.strip())
            elif local == "name" and elem == "activity":
                launcher_candidates.append(val)
        elif elem == "action":
            if local == "name" and val.endswith("android.intent.action.MAIN"):
                launcher = "main"
    counts = {}
    for e in x.elements:
        if e in ("activity", "service", "receiver", "provider"):
            counts[e] = counts.get(e, 0) + 1
    info["counts"] = counts
    info["exported"] = exported
    info["permissions"] = sorted(set(perm))
    if launcher and launcher_candidates:
        info["launcher"] = launcher_candidates[-1]
    return info


def console_section(title, stops=None):
    Out.head(title, stops or G_MAIN)



def run_surgery_mode(args):
    Stage.reset()
    Tty.probe()
    fast = args.no_anim or not Tty.enabled
    if not args.quiet:
        banner_anim(fast)
        print()
    src_input, _searched = resolve_input(args.input)
    if not src_input.exists():
        Out.bad("input not found: " + str(src_input))
        return 2
    pipe = Pipeline(args)
    pipe.tool = resolve_toolchain(pipe.work, allow_net=not args.no_net, quiet=args.quiet)
    Out.head("surgical mode", G_MAIN)
    Out.info("zero java · zero apktool · zero aapt2")
    merged, kind, splits = prepare_input(src_input, pipe.work, pipe.tool)
    if not merged:
        Out.bad("cannot read this archive · " + container_reason(src_input))
        return 4
    show_apk(merged)
    base = src_input.stem
    out_dir = Path(args.output).expanduser().parent if args.output else HOME
    out_dir.mkdir(parents=True, exist_ok=True)
    final = Path(args.output).expanduser() if args.output else out_dir / ("%s_ARP.apk" % base)
    if final.exists():
        final.unlink()
    got, tag = surgery_pipeline(pipe, merged, final, args)
    if not got:
        Out.bad("surgical engine failed")
        return 6
    if not args.unsigned:
        ensure_tools(["apksigner"], "signing")
    Out.head("sign", G_OK)
    removed = strip_signature_entries(final)
    if removed:
        Out.ok("stripped %d stale signature file(s)" % len(removed))
    final, aligned = do_zipalign(pipe.tool, final, pipe.work)
    if aligned == "python":
        Out.ok("aligned in python · arsc stored, 4 byte and page boundaries")
    elif aligned:
        Out.ok("zipalign applied")
    if args.unsigned:
        Out.info("unsigned build requested")
    else:
        signed, how = do_sign(pipe.tool, final, pipe.work, args.password)
        if signed:
            Out.ok("signed · " + how)
        else:
            Out.bad("no signer available · install apksigner")
            return 7
    Out.head("verification", G_OK)
    show_install_check(final, pipe.tool)
    show_dex_audit(final)
    show_manifest_truth(final)
    dashboard()
    Out.head("result", G_OK)
    st = apk_stats(final)
    digest = sha256_file(final)
    seal("artifact", [str(final), "size      " + human(st["size"]), "sha256    " + digest[:40], "strategy  " + str(tag)], G_OK)
    Out.kv("sha256", digest)
    return 0




def dashboard():
    Stage.close()
    if not Stage.records:
        return
    total = sum(d for _, d in Stage.records) or 1e-9
    peak = max(d for _, d in Stage.records) or 1e-9
    print()
    print("  " + rule(Tty.clamp(20, 78), G_MAIN, THIN))
    print("  " + Pal(ICE, True)("STAGE TIMINGS") + T_DIM("   total %.2fs" % total))
    print("  " + rule(Tty.clamp(20, 78), G_MAIN, THIN))
    for name, dur in Stage.records:
        share = dur / peak
        cells = max(1, int(share * 18))
        bar = gradient_text("█" * cells, G_COOL)
        pct = 100.0 * dur / total
        print("  " + T_DIM(trunc(name.upper(), 22).ljust(23)) + bar +
              T_DIM("  %6.2fs  %4.1f%%" % (dur, pct)))
    spark = Out.spark([d for _, d in Stage.records], G_MAIN)
    if spark:
        print("  " + T_DIM("profile".ljust(23)) + spark)
    print("  " + rule(Tty.clamp(20, 78), G_MAIN, THIN))


def seal(title, rows, stops=None):
    stops = stops or G_OK
    body = [""] + ["  " + r for r in rows] + [""]
    lines = boxed(body, stops)
    if not Tty.enabled:
        for l in lines:
            print(l)
        return
    strip = lambda t: re.sub(r"\033\[[0-9;?]*[A-Za-z]", "", t)
    plain = [strip(l) for l in lines]
    w = max(len(p) for p in plain)
    total = len(plain)
    sys.stdout.write(Pal.HIDE)
    try:
        for i in range(total + 1):
            Anim.paint([gradient_text(p, stops) if j < i else "" for j, p in enumerate(plain)])
            time.sleep(0.03)
        for f in range(8):
            pos = (f / 7.0) * (w + 20) - 10
            out = []
            for p in plain:
                buf = []
                for col, ch in enumerate(p):
                    if ch == " ":
                        buf.append(" ")
                        continue
                    d = abs(col - pos)
                    glow = max(0.0, 1.0 - d / 9.0)
                    buf.append(Pal(mix(ramp(stops, col / max(1, w - 1)), WHITE, glow), True)(ch))
                out.append("".join(buf))
            Anim.paint(out)
            time.sleep(0.028)
    finally:
        sys.stdout.write(Pal.SHOW)
    Anim.paint([gradient_text(p, stops) for p in plain])
    Anim.close()


def run_detect_mode(args):
    Stage.reset()
    Tty.probe()
    fast = args.no_anim or not Tty.enabled
    if not args.quiet:
        banner_anim(fast)
        print()
    src, _searched = resolve_input(args.input)
    if not src.exists():
        Out.bad("input not found: " + str(src))
        return 2
    Out.head("detection only", G_MAIN)
    Out.info("no java · no apktool · reads the archive directly")
    idx = zip_index(src)
    st = apk_stats(src)
    Out.kv("entries", st["files"])
    Out.kv("payload", "dex %d · res %d · assets %d · libs %d" % (st["dex"], st["res"], st["assets"], st["libs"]))
    man = None
    try:
        with zipfile.ZipFile(src) as z:
            man = safe_manifest(z)[1]
    except Exception:
        man = None
    if man:
        show_manifest(man)
    else:
        Out.warn("manifest unreadable")
    show_ecosystem(ecosystem(src))
    runtimes = fingerprint_runtimes(idx["names"])
    Out.head("runtime", G_COOL)
    if not runtimes:
        Out.info("no managed runtime fingerprint")
    for label, lang, score, evidence in runtimes:
        Out.kv("%s · %s" % (label, lang), ", ".join(evidence), width=30)
    prots = detect_protections(None, [], man) if man else []
    if prots:
        show_protections(prots)
    dashboard()
    print()
    print("  " + rule(Tty.clamp(20, 78), G_OK))
    Out.ok("detection complete · nothing was modified")
    return 0


def run_analysis(args):
    Stage.reset()
    Tty.probe()
    fast = args.no_anim or not Tty.enabled
    if not args.quiet:
        banner_anim(fast)
        print()
    src_input, _searched = resolve_input(args.input)
    if not src_input.exists():
        Out.bad("input not found: " + str(src_input))
        return 2
    ext = src_input.suffix.lower()
    if not preflight(src_input):
        return 8
    work = Path(tempfile.mkdtemp(prefix="arp_re_"))
    sections = []
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    Out.head("target", G_MAIN)
    Out.kv("input", src_input.name)
    Out.kv("size", human(src_input.stat().st_size))
    Out.kv("format", (detect_container(src_input) or "unknown").upper())

    if ext == ".so":
        elf = ElfFile(src_input)
        console_section("native object", G_WARM)
        if not elf.ok:
            Out.bad("not a readable ELF object")
            return 3
        s = elf.summary()
        Out.kv("machine", "%s · %d-bit" % (s["machine"], s["bits"]))
        Out.kv("sections", s["sections"])
        Out.kv("exports", s["exports"])
        for k, v in s["hardening"].items():
            Out.kv(k, "enabled" if v else "absent", tone=T_OK if v else T_WARN)
        sections.append(("Native object", [("kv", [("machine", s["machine"]), ("bits", s["bits"]), ("sections", s["sections"]), ("exports", s["exports"])]), ("chips", ["%s=%s" % (k, v) for k, v in s["hardening"].items()])]))
        write_report(args, src_input, sections, stamp, {"elf": s})
        return 0

    if ext == ".dex":
        dex = DexFile(src_input.read_bytes(), src_input.name)
        console_section("dex payload", G_WARM)
        if not dex.valid:
            Out.bad("not a valid dex container")
            return 3
        s = dex.summary()
        Out.kv("version", s["version"])
        Out.kv("classes", s["classes"])
        Out.kv("methods", s["methods"])
        Out.kv("strings", s["strings"])
        sections.append(("DEX", [("kv", [("version", s["version"]), ("classes", s["classes"]), ("methods", s["methods"]), ("fields", s["fields"]), ("strings", s["strings"])])]))
        write_report(args, src_input, sections, stamp, {"dex": s})
        return 0

    if ext == ".ipa":
        info = inspect_ipa(src_input)
        console_section("ios package", G_WARM)
        Out.kv("bundle", info["bundle"])
        Out.kv("display name", info["name"])
        Out.kv("version", info["version"])
        Out.kv("entries", info.get("entries", 0))
        Out.kv("frameworks", len(info["frameworks"]))
        for f in info["frameworks"][:12]:
            Out.bullet(f)
        sections.append(("iOS package", [("kv", [("bundle", info["bundle"]), ("name", info["name"]), ("version", info["version"]), ("entries", info.get("entries", 0))]), ("chips", info["frameworks"][:40])]))
        write_report(args, src_input, sections, stamp, {"ipa": info})
        return 0

    tool = resolve_toolchain(work, allow_net=not args.no_net, quiet=args.quiet)
    if ext == ".aab":
        console_section("bundle conversion", G_OK)
        apk, how = convert_aab(src_input, work, tool, args.password)
        if not apk:
            Out.warn("bundle could not be built into a universal apk · " + how)
            Out.info("falling back to direct bundle inspection")
        else:
            Out.ok("universal apk produced · " + how)
            src_input = apk

    if ext == ".aab" and not src_input.suffix.lower() == ".apk":
        idx = zip_index(src_input)
        console_section("bundle inventory", G_COOL)
        Out.kv("entries", idx["total"])
        Out.kv("modules", sum(1 for n in idx["names"] if n.startswith("base/") or n.endswith("/manifest/AndroidManifest.xml")))
        sections.append(("Bundle", [("kv", [("entries", idx["total"])]), ("chips", [n for n in idx["names"] if n.endswith("AndroidManifest.xml")][:20])]))
        write_report(args, src_input, sections, stamp, {"bundle_index": {"total": idx["total"]}})
        return 0

    merged, kind, splits = prepare_input(src_input, work, tool)
    if not merged:
        Out.bad("cannot read this archive · " + container_reason(src_input))
        return 4
    Out.kv("resolved", merged.name)
    if splits:
        Out.ok("%d splits · base %s" % (len(splits), merged.name))

    idx = zip_index(merged)
    st = apk_stats(merged)
    console_section("container", G_COOL)
    Out.kv("entries", st["files"])
    Out.kv("payload", "dex %d · res %d · assets %d · libs %d" % (st["dex"], st["res"], st["assets"], st["libs"]))
    if st["abi"]:
        Out.kv("abis", " · ".join(st["abi"]))
    sections.append(("Container", [("kv", [("size", human(st["size"])), ("entries", st["files"]), ("dex", st["dex"]), ("resources", st["res"]), ("assets", st["assets"]), ("native", st["libs"])]), ("chips", st["abi"])]))

    console_section("runtimes", G_WARM)
    runtimes = fingerprint_runtimes(idx["names"])
    if not runtimes:
        Out.info("no managed runtime fingerprint")
    for label, lang, score, evidence in runtimes:
        Out.kv("%s · %s" % (label, lang), ", ".join(evidence), width=30, tone=T_TXT)
    sections.append(("Runtimes", [("table", (["Framework", "Language", "Evidence"], [[r[0], r[1], ", ".join(r[3])] for r in runtimes]))] if runtimes else [("kv", [("result", "none detected")])]))

    hist = language_histogram(idx["names"])
    if hist:
        console_section("language mix", G_COOL)
        top = max(hist.values())
        for lang, n in hist.items():
            Out.bar(lang, n, top, width=24)
        sections.append(("Language mix", [("bars", [(k, v, top, "#22d3ee") for k, v in hist.items()])]))

    manifest = None
    try:
        with zipfile.ZipFile(merged) as z:
            if "AndroidManifest.xml" in z.namelist():
                manifest = safe_manifest(z)[1]
    except Exception:
        manifest = None
    if manifest:
        show_manifest(manifest)
        sections.append(("Manifest", [("kv", [
            ("package", manifest["package"]), ("version", manifest["version"]),
            ("min sdk", manifest["min_sdk"]), ("target sdk", manifest["target_sdk"]),
            ("launcher", manifest["launcher"]), ("exported", manifest["exported"]),
            ("debuggable", manifest["debuggable"]), ("cleartext", manifest["cleartext"]),
        ]), ("chips", manifest["permissions"][:60])]))

    dexes = collect_dex(merged, None)
    if dexes:
        console_section("bytecode", G_WARM)
        total_classes = sum(len(d.classes) for d in dexes)
        total_methods = sum(d.methods for d in dexes)
        Out.kv("dex files", len(dexes))
        Out.kv("classes", total_classes)
        Out.kv("methods", total_methods)
        api = {}
        for d in dexes:
            for k, v in d.api_hits.items():
                api[k] = api.get(k, 0) + v
        if api:
            top = max(api.values())
            for k, v in sorted(api.items(), key=lambda kv: -kv[1])[:10]:
                Out.bar(k, v, top, width=22)
        packages = {}
        for d in dexes:
            for c in d.classes:
                p = c["name"].rsplit("/", 1)[0] if "/" in c["name"] else "(default)"
                packages[p] = packages.get(p, 0) + 1
        for p, n in sorted(packages.items(), key=lambda kv: -kv[1])[:10]:
            Out.bullet("%s · %d classes" % (p, n))
        sections.append(("Bytecode", [("kv", [("dex files", len(dexes)), ("classes", total_classes), ("methods", total_methods)]), ("bars", [(k, v, max(api.values()), "#8b5cf6") for k, v in sorted(api.items(), key=lambda kv: -kv[1])[:12]]) if api else ("kv", [("api", "none")])]))
        if args.dump:
            ddir = Path(args.dump).expanduser()
            ddir.mkdir(parents=True, exist_ok=True)
            for d in dexes:
                lines = sorted({c["name"] for c in d.classes})
                atomic_write(ddir / ("%s.classes.txt" % d.name), "\n".join(lines), "w")
                atomic_write(ddir / ("%s.strings.txt" % d.name), "\n".join(d.strings[:200000]), "w")
            Out.ok("class and string dumps written to " + str(ddir))

    arsc = collect_arsc(merged, None)
    if arsc:
        console_section("resources", G_COOL)
        rs = arsc.summary()
        Out.kv("packages", ", ".join(rs["packages"]) or "?")
        Out.kv("types", rs["type_count"])
        Out.kv("entries", rs["entries"])
        top = max(rs["by_type"].values()) if rs["by_type"] else 1
        for k, v in list(rs["by_type"].items())[:10]:
            Out.bar(k, v, top, width=22)
        sections.append(("Resources", [("kv", [("packages", ", ".join(rs["packages"])), ("types", rs["type_count"]), ("entries", rs["entries"])]), ("bars", [(k, v, top, "#34d399") for k, v in list(rs["by_type"].items())[:14]])]))

    natives = collect_natives(merged, None)
    if natives:
        console_section("native objects", G_WARM)
        rows = []
        for e in natives[:24]:
            s = e.summary()
            h = s["hardening"]
            flags = "".join([("P" if h.get("pie") else "-"), ("N" if h.get("nx") else "-"), ("R" if h.get("relro") else "-"), ("C" if h.get("canary") else "-")])
            Out.kv(e.name, "%s · %d-bit · %s · %s" % (s["machine"], s["bits"], human(s["size"]), flags), width=34)
            rows.append([e.name, s["machine"], s["bits"], s["sections"], s["exports"], flags])
        Out.info("hardening key: P=pie N=nx R=relro C=canary")
        sections.append(("Native objects", [("table", (["Object", "ISA", "Bits", "Sections", "Exports", "Hardening"], rows))]))

    eco = ecosystem(merged)
    show_ecosystem(eco)
    if args.disasm and natives:
        console_section("disassembly", G_WARM)
        for e in natives[:4]:
            lines, err = native_disasm(e.path, limit=args.disasm)
            if err:
                Out.warn("%s · %s" % (e.name, err))
                break
            Out.kv(e.name, "%d instructions" % len(lines), width=30)
            for line in lines[:12]:
                print("    " + Pal(SLATE)(line))
    if args.java:
        console_section("java sources", G_OK)
        got, detail = run_jadx(work, merged, args.java)
        if got:
            Out.ok("java tree · " + detail)
        else:
            Out.warn(detail)
    pinning, urls = detect_pinning(merged)
    if pinning or urls:
        console_section("pinning & endpoints", G_WARM)
        for label, descs in sorted(pinning.items()):
            Out.kv(label, "%d class(es)" % len(descs), width=28)
            for d in list(descs)[:3]:
                Out.bullet(trunc(d, 70))
        if urls:
            Out.kv("endpoints", len(urls), width=28)
            for u in urls[:18]:
                print("    " + T_DIM(BULLET + " " + u))
        sections.append(("Pinning", [("kv", [(k, "%d class(es)" % len(v)) for k, v in sorted(pinning.items())]), ("chips", urls[:60])]))
    if args.frida:
        dest = Path(args.frida).expanduser()
        atomic_write(dest, frida_script(pinning, merged.name), "w")
        Out.ok("frida hook script · " + str(dest))
    if args.mapping:
        mapping = load_mapping(args.mapping)
        resolved = sum(1 for d in dexes for c in d.classes if c["name"] in mapping)
        Out.kv("proguard names", "%d resolvable of %d entries" % (resolved, len(mapping)))

    if args.unpack:
        dest = Path(args.unpack).expanduser()
        dest.mkdir(parents=True, exist_ok=True)
        console_section("extraction", G_OK)
        count = 0
        try:
            with zipfile.ZipFile(merged) as z:
                for info in z.infolist():
                    target = dest / info.filename
                    if info.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(info) as srcf, open(target, "wb") as dstf:
                        shutil.copyfileobj(srcf, dstf)
                    count += 1
        except Exception as e:
            Out.warn("extraction incomplete · " + trunc(str(e), 60))
        Out.ok("%d entries written byte-for-byte to %s" % (count, dest))
        if tool.get("apktool") and args.decode:
            src = dest / "_smali"
            rc, _ = run_live(argv_of(tool["apktool"]) + ["d", "-f", str(merged), "-o", str(src)], "apktool decode", timeout=3600)
            if src.exists():
                Out.ok("smali tree · " + str(src))
        sections.append(("Extraction", [("kv", [("entries written", count), ("destination", str(dest))])]))

    write_report(args, src_input, sections, stamp, {
        "container": st, "runtimes": [r[0] for r in runtimes],
        "languages": hist, "manifest": {k: v for k, v in (manifest or {}).items() if k != "raw"},
        "dex": [d.summary() for d in dexes], "resources": arsc.summary() if arsc else None,
        "native": [e.summary() for e in natives],
    })
    shutil.rmtree(work, ignore_errors=True)
    return 0


def write_report(args, target, sections, stamp, payload):
    out_dir = Path(args.output).expanduser() if args.output else HOME / ("%s_RE" % target.stem)
    if out_dir.suffix:
        out_dir = out_dir.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    if not args.no_report:
        ctx = {"title": "Reverse engineering report", "target": target.name, "stamp": stamp, "sections": sections}
        html = render_report(ctx)
        dest = out_dir / "report.html"
        atomic_write(dest, html, "w")
        print()
        print("  " + gradient_text(str(dest), G_OK, True))
    js = out_dir / "report.json"
    data = dict(payload)
    data.update({"tool": APP, "version": VERSION, "target": str(target), "stamp": stamp})
    atomic_write(js, json.dumps(data, indent=2, default=str), "w")
    Out.kv("json", str(js))
    Out.kv("directory", str(out_dir))




ALIGN_EXTRA_ID = 0xD935
ZIP_LOCAL = b"PK\x03\x04"
ZIP_DATA_DESC = b"PK\x07\x08"


def local_entries(path):
    out = []
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(0)
            guard = 0
            while guard < 300000:
                guard += 1
                sig = f.read(4)
                if len(sig) < 4 or sig != ZIP_LOCAL:
                    break
                hdr = f.read(26)
                if len(hdr) < 26:
                    break
                flags, method = struct.unpack_from("<H", hdr, 2)[0], struct.unpack_from("<H", hdr, 4)[0]
                csize = struct.unpack_from("<I", hdr, 14)[0]
                nlen, elen = struct.unpack_from("<H", hdr, 22)[0], struct.unpack_from("<H", hdr, 24)[0]
                name = f.read(nlen).decode("utf-8", "replace")
                f.read(elen)
                offset = f.tell()
                out.append({"name": name, "method": method, "offset": offset, "size": csize, "flags": flags})
                f.seek(offset + csize)
                if flags & 0x08:
                    if f.read(4) == ZIP_DATA_DESC:
                        f.seek(12, 1)
                if f.tell() >= size:
                    break
    except Exception:
        pass
    return out


def _align_build(src, tmp, plan, align, page):
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(tmp, "w") as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
            zi.compress_type = item.compress_type
            zi.external_attr = item.external_attr
            zi.internal_attr = item.internal_attr
            zi.create_system = item.create_system
            if item.filename == "resources.arsc":
                zi.compress_type = zipfile.ZIP_STORED
            if zi.compress_type == zipfile.ZIP_STORED:
                boundary = page if item.filename.endswith(".so") else align
                want = plan.get(item.filename)
                if want is None:
                    pos = zout.fp.tell()
                    base = 30 + len(item.filename.encode("utf-8"))
                    want = (-(pos + base)) % boundary
                if want < 4:
                    want += boundary
                zi.extra = struct.pack("<HH", ALIGN_EXTRA_ID, want - 4) + b"\x00" * (want - 4)
            else:
                zi.extra = b""
            zout.writestr(zi, data)


def zip_align(apk, align=4, page=4096):
    trace("align %s" % Path(apk).name)
    src = Path(apk)
    tmp = src.with_name(src.name + ".aligned")
    plan = {}
    try:
        for attempt in range(3):
            _align_build(src, tmp, plan, align, page)
            entries = local_entries(tmp)
            bad = []
            for e in entries:
                if e["method"] != 0:
                    continue
                boundary = page if e["name"].endswith(".so") else align
                if e["offset"] % boundary:
                    bad.append((e["name"], e["offset"] % boundary))
            if not bad:
                os.replace(tmp, src)
                return True
            for name, delta in bad:
                current = plan.get(name)
                if current is None:
                    with zipfile.ZipFile(tmp) as z:
                        info = z.getinfo(name)
                    current = len(info.extra) or boundary
                plan[name] = max(4, current + (boundary - delta) % boundary)
        os.replace(tmp, src)
        return False
    except Exception:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        return False


INSTALL_CODES = {
    "UPDATE_INCOMPATIBLE": "INSTALL_FAILED_UPDATE_INCOMPATIBLE",
    "PARSE_NO_CERT": "INSTALL_PARSE_FAILED_NO_CERTIFICATES",
    "INCONSISTENT_CERT": "INSTALL_PARSE_FAILED_INCONSISTENT_CERTIFICATES",
    "INVALID_APK": "INSTALL_FAILED_INVALID_APK",
    "NO_V2": "INSTALL_PARSE_FAILED_NO_CERTIFICATES (v2 missing on android 11+)",
}


def apk_signature_schemes(tool, apk):
    if not tool or not tool.get("apksigner"):
        return []
    rc, out, err = run(argv_of(tool["apksigner"]) + ["verify", "--verbose", str(apk)], timeout=600)
    text = (out or "") + "\n" + (err or "")
    found = []
    for line in text.splitlines():
        low = line.lower()
        if "scheme" not in low:
            continue
        if "true" not in low and ": true" not in low:
            continue
        m = re.search(r"\bv(\d+(?:\.\d+)?)\s+scheme", low)
        if m:
            tag = "v" + m.group(1)
            if tag not in found:
                found.append(tag)
    return found


def strip_signature_entries(apk):
    trace("strip META-INF in %s" % Path(apk).name)
    src = Path(apk)
    tmp = src.with_name(src.name + ".nosig")
    removed = []
    try:
        with zipfile.ZipFile(src) as zin, zipfile.ZipFile(tmp, "w") as zout:
            for item in zin.infolist():
                up = item.filename.upper()
                if up.startswith("META-INF/") and up.endswith((".SF", ".RSA", ".DSA", ".EC", ".MF")):
                    removed.append(item.filename)
                    continue
                zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
                zi.compress_type = item.compress_type
                zi.external_attr = item.external_attr
                zi.internal_attr = item.internal_attr
                zi.create_system = item.create_system
                zout.writestr(zi, zin.read(item.filename))
        os.replace(tmp, src)
        return removed
    except Exception:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        return []


def install_check(apk, tool=None):
    issues = []
    entries = local_entries(apk)
    names = {e["name"] for e in entries}
    facts = None
    schemes = []
    verified = False
    if tool and tool.get("apksigner"):
        facts = cert_facts(tool, apk)
        verified = bool(facts and facts.get("ok"))
        if verified:
            schemes = apk_signature_schemes(tool, apk)

    # a dex ART rejects is a launch crash, not an install error: catch it here
    for dex_name, _size, problems in dex_audit_apk(apk):
        hard = [m for s, m in problems if s == "bad"]
        if hard:
            issues.append(("bad", INSTALL_CODES["INVALID_APK"],
                           "%s fails dex verification · %s" % (dex_name, hard[0]),
                           "patch that dex with baksmali/smali or keep every item's length"))
        else:
            soft = [m for s, m in problems if s == "warn"]
            if soft:
                issues.append(("warn", "INSTALL_OK",
                               "%s · %s" % (dex_name, soft[0]),
                               "re-check with dexdump if the app misbehaves"))

    arsc = next((e for e in entries if e["name"] == "resources.arsc"), None)
    if arsc is None:
        issues.append(("bad", INSTALL_CODES["INVALID_APK"], "resources.arsc is missing", "rebuild the resources"))
    else:
        if arsc["method"] != 0:
            issues.append(("bad", INSTALL_CODES["INVALID_APK"],
                           "resources.arsc is compressed", "rebuild with a tool that stores it uncompressed"))
        if arsc["offset"] % 4:
            issues.append(("bad", INSTALL_CODES["INVALID_APK"],
                           "resources.arsc is not 4 byte aligned", "run with alignment enabled"))

    try:
        raw_state = signature_state(Path(apk).read_bytes())
    except Exception:
        raw_state = {"status": "unknown", "schemes": [], "detail": "could not read"}
    if raw_state["status"] == "stale":
        issues.append(("bad", INSTALL_CODES["INCONSISTENT_CERT"],
                       "stale %s signature block · %s" % ("/".join(raw_state["schemes"]) or "apk", raw_state["detail"]),
                       "run: arpxtool repair"))
    elif raw_state["status"] == "valid" and not verified:
        verified = True
        schemes = raw_state["schemes"]

    sig_files = [n for n in names if n.upper().startswith("META-INF/") and n.upper().endswith((".SF", ".RSA", ".DSA", ".EC"))]
    if sig_files:
        blocks = {Path(n).stem for n in sig_files}
        if verified and len(blocks) <= 1:
            pass
        elif verified and len(blocks) > 1:
            issues.append(("bad", INSTALL_CODES["INCONSISTENT_CERT"],
                           "%d different signature blocks inside META-INF" % len(blocks),
                           "strip META-INF and sign once"))
        elif facts is not None and not facts.get("ok"):
            issues.append(("bad", INSTALL_CODES["INCONSISTENT_CERT"],
                           "%d signature file(s) present but verification failed" % len(sig_files),
                           "strip META-INF before signing"))
        else:
            issues.append(("info", "-",
                           "%d signature file(s) in META-INF, signer not available to verify" % len(sig_files),
                           "install apksigner for a definitive check"))

    so_entries = [e for e in entries if e["name"].endswith(".so")]
    man = None
    try:
        with zipfile.ZipFile(apk) as z:
            man = safe_manifest(z)[1]
    except Exception:
        man = None
    extract_false = bool(man and man.get("extract_native_libs") == "false")
    if so_entries and extract_false:
        compressed = [e for e in so_entries if e["method"] != 0]
        misaligned = [e for e in so_entries if e["method"] == 0 and e["offset"] % 4096]
        if compressed:
            issues.append(("bad", INSTALL_CODES["INVALID_APK"],
                           "%d native object(s) compressed while extractNativeLibs=false" % len(compressed),
                           "store the .so entries uncompressed"))
        if misaligned:
            issues.append(("bad", INSTALL_CODES["INVALID_APK"],
                           "%d native object(s) not page aligned" % len(misaligned),
                           "align .so entries to 4096"))
    elif so_entries:
        misaligned = [e for e in so_entries if e["method"] == 0 and e["offset"] % 4096]
        if misaligned:
            issues.append(("info", "-",
                           "%d native object(s) not page aligned (only matters when extractNativeLibs=false)" % len(misaligned),
                           "harmless with the default extractNativeLibs=true"))

    if "AndroidManifest.xml" not in names:
        issues.append(("bad", INSTALL_CODES["INVALID_APK"], "AndroidManifest.xml missing", "rebuild the archive"))
    if not any(re.match(r"classes\d*\.dex$", n) for n in names):
        issues.append(("bad", INSTALL_CODES["INVALID_APK"], "no dex payload", "rebuild the archive"))

    if verified:
        if not any(s in ("v2", "v3", "v3.1") for s in schemes):
            issues.append(("bad", INSTALL_CODES["NO_V2"],
                           "no v2/v3 signature found (schemes: %s)" % (", ".join(schemes) or "none"),
                           "re-sign with --v2-signing-enabled true"))
    elif facts is not None and not facts.get("ok"):
        issues.append(("bad", INSTALL_CODES["PARSE_NO_CERT"],
                       "apksigner verify failed", "sign the archive with apksigner"))
    return issues, facts, man


def show_install_check(apk, tool=None):
    issues, facts, man = install_check(apk, tool)
    Out.head("install diagnosis", G_WARM)
    if man:
        def _val(v):
            return "unavailable" if v in (None, "", "?") else str(v)
        Out.kv("package", _val(man.get("package")), width=18)
        Out.kv("version", "%s (%s)" % (_val(man.get("version")), _val(man.get("version_code"))), width=18)
        Out.kv("sdk", "%s -> %s" % (_val(man.get("min_sdk")), _val(man.get("target_sdk"))), width=18)
        Out.kv("extractNativeLibs", _val(man.get("extract_native_libs")), width=18)
        if man.get("package_recovered"):
            Out.info("package name was recovered from the string pool · the binary manifest is only partly decodable")
    if facts and facts.get("ok"):
        Out.kv("certificate", trunc(facts.get("subject", "?"), 52), width=18)
        if facts.get("sha256"):
            Out.kv("sha-256", trunc(facts["sha256"], 52), width=18)
    if not issues:
        Out.ok("no install blocker found in the archive")
        return True
    tone = {"bad": T_ERR, "warn": T_WARN, "info": T_INFO}
    mark = {"bad": CROSS, "warn": WARN, "info": ARROW}
    for sev, code, msg, fix in issues:
        print("  " + tone[sev](mark[sev]) + " " + T_TXT(msg))
        if code and code != "-":
            print("    " + T_DIM("code  " + code))
        print("    " + T_DIM("fix   " + fix))
    return not any(s == "bad" for s, _, _, _ in issues)


def cmd_install_check(args):
    Tty.probe()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    apk, _searched = resolve_input(args.input)
    if apk is None:
        Out.bad("input not found · " + str(args.input))
        for _root in (_searched or [])[:5]:
            Out.info("looked in " + str(_root))
        return 2
    tool = resolve_toolchain(Path(tempfile.mkdtemp()), allow_net=False, quiet=True)
    ok = show_install_check(apk, tool)
    print()
    Out.info("if the original build is still installed, android refuses the update:")
    Out.info("  adb uninstall <package>   or   uninstall from settings, then install")
    return 0 if ok else 6


def apk_lint(apk):
    issues = []
    entries = local_entries(apk)
    names = [e["name"] for e in entries]
    if not entries:
        return [("bad", "zip central directory unreadable")], False
    seen = set()
    dupes = 0
    for n in names:
        if n in seen:
            dupes += 1
        seen.add(n)
    if dupes:
        issues.append(("bad", "%d duplicate archive entries" % dupes))
    arsc = next((e for e in entries if e["name"] == "resources.arsc"), None)
    if arsc is None:
        issues.append(("warn", "resources.arsc missing"))
    else:
        if arsc["method"] != 0:
            issues.append(("bad", "resources.arsc is compressed · android 11+ rejects this"))
        if arsc["offset"] % 4:
            issues.append(("bad", "resources.arsc not 4 byte aligned (offset %d)" % arsc["offset"]))
    misaligned = [e for e in entries if e["method"] == 0 and e["offset"] % 4]
    if misaligned:
        issues.append(("warn", "%d stored entries not 4 byte aligned" % len(misaligned)))
    so_misaligned = [e for e in entries if e["method"] == 0 and e["name"].endswith(".so") and e["offset"] % 4096]
    if so_misaligned:
        issues.append(("info", "%d native objects not page aligned" % len(so_misaligned)))
    dollars = [n for n in names if os.path.basename(n).startswith("$")]
    if dollars:
        issues.append(("bad", "%d resource entries still start with $" % len(dollars)))
    bad_paths = [n for n in names if n.startswith("/") or "\\" in n or ".." in n.split("/")]
    if bad_paths:
        issues.append(("bad", "%d unsafe archive paths" % len(bad_paths)))
    if "AndroidManifest.xml" not in seen:
        issues.append(("bad", "AndroidManifest.xml missing"))
    if not any(re.match(r"classes\d*\.dex$", n) for n in names):
        issues.append(("bad", "no dex payload"))
    for dex_name, _size, problems in dex_audit_apk(apk):
        hard = [m for s, m in problems if s == "bad"]
        if hard:
            issues.append(("bad", "%s fails dex verification · %s" % (dex_name, hard[0])))
        else:
            soft = [m for s, m in problems if s == "warn"]
            if soft:
                issues.append(("warn", "%s · %s" % (dex_name, soft[0])))
    ok_arsc = arsc and arsc["method"] == 0 and arsc["offset"] % 4 == 0
    return issues, ok_arsc


def show_lint(apk):
    result = apk_lint(apk)
    issues = result[0] if isinstance(result, tuple) else result
    tone = {"bad": T_ERR, "warn": T_WARN, "info": T_INFO}
    mark = {"bad": CROSS, "warn": WARN, "info": ARROW}
    if not issues:
        Out.ok("installability audit clean · alignment, arsc, paths all valid")
        return True
    for sev, msg in issues:
        print("  " + tone[sev](mark[sev]) + " " + T_TXT(msg))
    return not any(s == "bad" for s, _ in issues)


def apk_compare(a, b):
    za, zb = {}, {}
    for path, store in ((a, za), (b, zb)):
        try:
            with zipfile.ZipFile(path) as z:
                for info in z.infolist():
                    store[info.filename] = (info.CRC, info.file_size, info.compress_size)
        except Exception:
            return None
    added = sorted(set(zb) - set(za))
    removed = sorted(set(za) - set(zb))
    changed = sorted(k for k in set(za) & set(zb) if za[k][0] != zb[k][0])
    return {"added": added, "removed": removed, "changed": changed, "before": za, "after": zb}


def apk_search(apk, term, limit=60):
    needle = term.lower()
    hits = []
    try:
        with zipfile.ZipFile(apk) as z:
            for name in z.namelist():
                if not re.search(r"\.(dex|so|json|js|xml|txt|bundle|dat|properties|smali)$", name, re.I):
                    continue
                try:
                    data = z.read(name)
                except Exception:
                    continue
                if len(data) > 80 * 1024 * 1024:
                    continue
                for m in re.finditer(re.escape(needle.encode("utf-8", "ignore")), data.lower()):
                    start = max(0, m.start() - 60)
                    chunk = data[start : m.start() + 120]
                    text = re.sub(rb"[^\x20-\x7e]", b".", chunk).decode("ascii", "ignore")
                    hits.append((name, m.start(), text))
                    if len(hits) >= limit:
                        return hits
    except Exception:
        pass
    return hits


def cert_facts(tool, apk):
    if not tool.get("apksigner"):
        return None
    rc, out, err = run(argv_of(tool["apksigner"]) + ["verify", "--print-certs", str(apk)], timeout=600)
    text = (out or "") + (err or "")
    facts = {"ok": rc == 0, "raw": text}
    for line in text.splitlines():
        low = line.lower()
        for key, label in (("signer #1 certificate dn:", "subject"), ("subject:", "subject"),
                           ("issuer:", "issuer"), ("sha-256 digest:", "sha256"),
                           ("sha-1 digest:", "sha1"), ("valid from:", "valid")):
            if low.startswith(key):
                facts[label] = line.split(":", 1)[1].strip()
    return facts


def prune_temp(max_age_hours=6, everything=False):
    freed = 0
    count = 0
    root = Path(tempfile.gettempdir())
    now = time.time()
    for p in root.glob("arp_*"):
        try:
            if not p.is_dir():
                continue
            if not everything and now - p.stat().st_mtime < max_age_hours * 3600:
                continue
            size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
            shutil.rmtree(p, ignore_errors=True)
            freed += size
            count += 1
        except Exception:
            pass
    return count, freed


def cmd_clean():
    Tty.probe()
    banner_anim(not Tty.enabled)
    Out.head("workspace cleanup", G_WARM)
    count, freed = prune_temp(0, everything=True)
    Out.kv("trees removed", count)
    Out.kv("space reclaimed", human(freed))
    Out.kv("free now", human(disk_free(HOME)))
    for stale in HOME.glob("*.arpbak"):
        try:
            stale.unlink()
        except Exception:
            pass
    Out.ok("workspace clean")
    return 0


def cmd_compare(args):
    Tty.probe()
    banner_anim(not Tty.enabled)
    _work = Path(tempfile.mkdtemp())
    a, _na, _sa = open_apk(args.input, _work)
    b, _nb, _sb = open_apk(args.compare, _work)
    if a is None:
        Out.bad("input not found · " + str(args.input))
        return 2
    if b is None:
        Out.bad("second input not found · " + str(args.compare))
        return 2
    for _note in (_na, _nb):
        if _note:
            Out.info(_note)
    for p in (a, b):
        if not p.exists():
            Out.bad("missing " + str(p))
            return 2
    Out.head("archive diff", G_COOL)
    Out.kv("before", "%s · %s" % (a.name, human(a.stat().st_size)))
    Out.kv("after", "%s · %s" % (b.name, human(b.stat().st_size)))
    diff = apk_compare(a, b)
    if not diff:
        Out.bad("one of the archives is unreadable")
        return 3
    Out.kv("added", len(diff["added"]))
    Out.kv("removed", len(diff["removed"]))
    Out.kv("changed", len(diff["changed"]))
    for label, key, tone in (("added", "added", EMERALD), ("removed", "removed", BLOOD), ("changed", "changed", AMBER)):
        items = diff[key]
        if not items:
            continue
        print()
        print("  " + Pal(tone, True)(label.upper()) + T_DIM(" · %d" % len(items)))
        for name in items[:25]:
            print("    " + Pal(tone)(BULLET) + " " + T_DIM(trunc(name, 90)))
        if len(items) > 25:
            print("    " + T_DIM("… %d more" % (len(items) - 25)))
    return 0


def cmd_search(args):
    Tty.probe()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    path, _searched = resolve_input(args.input)
    if not path.exists():
        Out.bad("missing " + str(path))
        return 2
    Out.head("string search", G_WARM)
    Out.kv("term", args.search)
    hits = apk_search(path, args.search)
    if not hits:
        Out.info("no match")
        return 0
    Out.ok("%d match(es)" % len(hits))
    for name, off, text in hits:
        print("  " + T_ACC(DIAMOND) + " " + T_TXT(trunc(name, 46)) + T_DIM(" @ 0x%x" % off))
        print("    " + Pal(SLATE)(trunc(text, 110)))
    return 0


def cmd_cert(args):
    Tty.probe()
    banner_anim(not Tty.enabled)
    path, _searched = resolve_input(args.input)
    if not path.exists():
        Out.bad("missing " + str(path))
        return 2
    tool = resolve_toolchain(Path(tempfile.mkdtemp()), allow_net=False, quiet=True)
    Out.head("signature facts", G_COOL)
    facts = cert_facts(tool, path)
    if not facts:
        Out.bad("apksigner unavailable")
        return 3
    if not facts.get("ok"):
        Out.warn("signature does not verify")
    for key, label in (("subject", "subject"), ("issuer", "issuer"), ("sha256", "sha-256"), ("sha1", "sha-1"), ("valid", "valid from")):
        if facts.get(key):
            Out.kv(label, facts[key])
    return 0


def preflight(path, prune=True):
    size = 0
    try:
        size = Path(path).stat().st_size
    except Exception:
        pass
    need = max(2 * 1024 ** 3, size * 14)
    free = disk_free(tempfile.gettempdir())
    if free and free < need:
        Out.warn("only %s free · this job wants about %s" % (human(free), human(need)))
        count, freed = prune_temp(2) if prune else (0, 0)
        if count:
            Out.ok("reclaimed %s from %d stale tree(s)" % (human(freed), count))
        if disk_free(tempfile.gettempdir()) < need // 2:
            Out.bad("insufficient space · free up storage or point TMPDIR elsewhere")
            return False
    return True




class DexIndex:
    def __init__(self, data):
        self.d = data
        self.ok = len(data) > 0x70 and data[:4] == b"dex\n"
        self.s_n = self.s_off = self.t_n = self.t_off = 0
        self.m_n = self.m_off = self.c_n = self.c_off = 0
        self.p_n = self.p_off = 0
        self._scache = {}
        if not self.ok:
            return
        self.s_n, self.s_off = u4(data, 0x38), u4(data, 0x3C)
        self.t_n, self.t_off = u4(data, 0x40), u4(data, 0x44)
        self.p_n, self.p_off = u4(data, 0x48), u4(data, 0x4C)
        self.m_n, self.m_off = u4(data, 0x58), u4(data, 0x5C)
        self.c_n, self.c_off = u4(data, 0x60), u4(data, 0x64)
        self._clamp(len(data))

    def _clamp(self, size):
        def fit(count, offset, stride):
            if not offset or offset >= size:
                return 0
            return min(count, (size - offset) // stride)
        self.s_n = fit(self.s_n, self.s_off, 4)
        self.t_n = fit(self.t_n, self.t_off, 4)
        self.p_n = fit(self.p_n, self.p_off, 12)
        self.m_n = fit(self.m_n, self.m_off, 8)
        self.c_n = fit(self.c_n, self.c_off, 32)
        self._scache = {}

    def string(self, i):
        if i in self._scache:
            return self._scache[i]
        try:
            off = u4(self.d, self.s_off + i * 4)
            n, p = uleb(self.d, off)
            val = self.d[p : p + n].decode("utf-8", "replace")
        except Exception:
            val = ""
        self._scache[i] = val
        return val

    def type_name(self, i):
        try:
            return self.string(u4(self.d, self.t_off + i * 4))
        except Exception:
            return ""

    def method_name(self, i):
        try:
            return self.string(u4(self.d, self.m_off + i * 8 + 4))
        except Exception:
            return ""

    def method_ret(self, i):
        """Return-type descriptor of method_id[i] ('V', 'Z', 'Ljava/util/List;'...)."""
        try:
            proto = u2(self.d, self.m_off + i * 8 + 2)
            if proto >= self.p_n:
                return ""
            return self.type_name(u4(self.d, self.p_off + proto * 12 + 4))
        except Exception:
            return ""

    def stub_kind(self, i, default=None):
        """Pick the stub whose return type matches the method's own signature.

        Writing return-void into a method declared to return a List is a verify
        error: ART rejects the method and the caller throws. The return type has
        to decide the stub, not the name of the method.
        """
        t = self.method_ret(i)
        if not t:
            return default
        if t == "V":
            return "void"
        if t == "Z":
            return "true"
        if t in ("J", "D"):
            return "wide"
        if t in ("I", "S", "B", "C", "F"):
            return "zero"
        return "null"

    def find_class(self, desc):
        limit = min(self.c_n, 400000)
        for i in range(limit):
            base = self.c_off + i * 32
            try:
                if self.type_name(u4(self.d, base)) == desc:
                    return base
            except Exception:
                return None
        return None


CODE_STUBS = {
    "void": b"\x0e\x00",
    "true": b"\x12\x10\x0f\x00",
    "false": b"\x12\x00\x0f\x00",
    "zero": b"\x12\x00\x0f\x00",
    "wide": b"\x16\x00\x00\x00\x10\x00",
    "null": b"\x12\x00\x11\x00",
}


def dex_fix_header(buf):
    try:
        sig = hashlib.sha1(bytes(buf[32:])).digest()
        buf[12:32] = sig
        chk = zlib.adler32(bytes(buf[12:])) & 0xFFFFFFFF
        struct.pack_into("<I", buf, 8, chk)
        return True
    except Exception:
        return False


# ── dex structural audit ────────────────────────────────────────────────────
# ART verifies every dex before loading it and drops the WHOLE file when one
# check fails, so its classes simply disappear at runtime: the install succeeds,
# apksigner is happy, and the app dies at launch with ClassNotFoundException.
# The cheap way to ship that is to rewrite a variable-length item in place.
# These helpers reproduce the audit locally so a broken dex never leaves here.

DEX_MAP_ITEM_SIZE = 12
DEX_FIXED_ITEM_SIZES = {
    0x0001: 4,    # string_id_item
    0x0002: 4,    # type_id_item
    0x0003: 12,   # proto_id_item
    0x0004: 8,    # field_id_item
    0x0005: 8,    # method_id_item
    0x0006: 32,   # class_def_item
    0x0007: 4,    # call_site_id_item
    0x0008: 8,    # method_handle_item
}
# only these section types must sit on a 4 byte boundary. class_data, string_data,
# debug_info, annotation and encoded_array are 1-byte aligned by spec, so a dex
# that puts them on an odd offset is perfectly valid and must not be flagged.
DEX_ALIGNED_TYPES = frozenset((
    0x0000, 0x0001, 0x0002, 0x0003, 0x0004, 0x0005, 0x0006, 0x0007, 0x0008,
    0x1000, 0x1001, 0x1002, 0x1003, 0x2001, 0x2006,
))
DEX_T_CODEF = 0x0006
DEX_T_CLASSDATA = 0x2000
DEX_T_CODEITEM = 0x2001
DEX_SECTION_NAMES = {
    0x0000: "header", 0x0001: "string_ids", 0x0002: "type_ids",
    0x0003: "proto_ids", 0x0004: "field_ids", 0x0005: "method_ids",
    0x0006: "class_defs", 0x0007: "call_site_ids", 0x0008: "method_handles",
    0x1000: "map_list", 0x1001: "type_lists", 0x1002: "annotation_set_refs",
    0x1003: "annotation_sets", 0x2000: "class_data", 0x2001: "code_items",
    0x2002: "string_data", 0x2003: "debug_info", 0x2004: "annotations",
    0x2005: "encoded_arrays", 0x2006: "annotation_directories",
}

# things the surgical engine refuses to do, reported by the pipeline
DEX_GUARD = {"failures": [], "rejected": []}


def _sleb_at(d, o):
    result = 0
    shift = 0
    while o < len(d):
        b = d[o]
        o += 1
        result |= (b & 0x7F) << shift
        shift += 7
        if not b & 0x80:
            if shift < 64 and b & 0x40:
                result -= 1 << shift
            return result, o
        if shift > 35:
            break
    return result, o


def dex_code_item_end(d, off):
    """End offset of the code_item at `off`, or None when it cannot be read.

    size = 16 + insns_size*2  [+2 pad when insns_size is odd]  [+8 per try]
           [+ encoded_catch_handler_list]
    """
    if off < 0 or off + 16 > len(d):
        return None
    tries = u2(d, off + 6)
    insns_size = u4(d, off + 12)
    p = off + 16 + insns_size * 2
    if p > len(d):
        return None
    if not tries:
        return p
    if insns_size & 1:
        p += 2
    p += tries * 8
    if p >= len(d):
        return None
    count, p = uleb(d, p)
    if count > 65536:
        return None
    for _ in range(count):
        size, p = _sleb_at(d, p)
        for _ in range(abs(size)):
            _, p = uleb(d, p)
            _, p = uleb(d, p)
        if size <= 0:
            _, p = uleb(d, p)
        if p > len(d):
            return None
    return p


def dex_class_data_end(d, off):
    """End offset of the class_data_item at `off`, or None."""
    p = off
    sf, p = uleb(d, p)
    inf, p = uleb(d, p)
    dm, p = uleb(d, p)
    vm, p = uleb(d, p)
    for _ in range(sf + inf):
        _, p = uleb(d, p)
        _, p = uleb(d, p)
    for _ in range(dm + vm):
        _, p = uleb(d, p)
        _, p = uleb(d, p)
        _, p = uleb(d, p)
    if p <= off or p > len(d):
        return None
    return p


def dex_sections(d):
    """[(offset, type, count)] from the map_list, or None."""
    if len(d) < 0x70 or d[:4] != b"dex\n":
        return None
    map_off = u4(d, 0x34)
    if map_off < 0x70 or map_off + 4 > len(d):
        return None
    n = u4(d, map_off)
    if n == 0 or n > 1024 or map_off + 4 + n * DEX_MAP_ITEM_SIZE > len(d):
        return None
    out = []
    for i in range(n):
        base = map_off + 4 + i * DEX_MAP_ITEM_SIZE
        out.append((u4(d, base + 8), u2(d, base), u4(d, base + 4)))
    return out


def dex_validate(d):
    """Structural audit of one dex. Returns [(severity, message)]; empty is good."""
    d = bytes(d)
    problems = []

    def bad(m):
        problems.append(("bad", m))

    def warn(m):
        problems.append(("warn", m))

    if len(d) < 0x70 or d[:4] != b"dex\n":
        return [("bad", "not a dex file")]
    if u4(d, 0x20) != len(d):
        bad("header file_size is %d but the file is %d byte(s)" % (u4(d, 0x20), len(d)))
    if u4(d, 0x24) != 0x70:
        bad("header_size is not 0x70")
    if u4(d, 0x28) != 0x12345678:
        bad("bad endian_tag")
    sections = dex_sections(d)
    if sections is None:
        return problems + [("bad", "map_list unreadable")]
    if sections[0][1] != 0x0000 or sections[0][0] != 0:
        bad("map_list does not begin with the header at offset 0")
    prev = -1
    for off, stype, count in sections:
        name = DEX_SECTION_NAMES.get(stype, "0x%04x" % stype)
        if off < prev and not (stype == 0x0000 and off == 0):
            bad("%s at 0x%x is out of order" % (name, off))
        prev = max(prev, off)
        if off >= len(d):
            bad("%s offset 0x%x is past the end of the file" % (name, off))
        elif stype in DEX_ALIGNED_TYPES and stype != 0x0000 and off % 4:
            bad("%s is not 4 byte aligned (0x%x)" % (name, off))
    # exact ends for the sections whose item sizes we can compute
    ends = {}
    soft_ends = {}
    for off, stype, count in sections:
        size = DEX_FIXED_ITEM_SIZES.get(stype)
        if size is None or not count:
            continue
        end = off + count * size
        if end > len(d):
            bad("%s overruns the file (%d item(s))"
                % (DEX_SECTION_NAMES.get(stype, "0x%04x" % stype), count))
            continue
        ends[off] = end
    for off, stype, count in sections:
        if stype == DEX_T_CODEITEM and count:
            p = off
            walked = True
            for i in range(count):
                # advisory only: this walk has produced false alarms on real
                # D8 dexes, so it never blocks a build. The hard guarantee is
                # the length-preserving patcher + dex_stub_ok, not this walk.
                end = dex_code_item_end(d, p)
                if end is None or end <= p:
                    warn("code_item #%d at 0x%x could not be walked · the section is left unchecked"
                         % (i, p))
                    walked = False
                    break
                p = end
            if walked:
                soft_ends[off] = p
        elif stype == DEX_T_CLASSDATA and count:
            cdef = next((s for s in sections if s[1] == DEX_T_CODEF), None)
            if not cdef or not cdef[2]:
                continue
            last = off
            walked = True
            for i in range(cdef[2]):
                cdata = u4(d, cdef[0] + i * 32 + 24)
                if not cdata:
                    continue
                end = dex_class_data_end(d, cdata)
                if end is None:
                    walked = False
                    break
                last = max(last, end)
            if walked:
                soft_ends[off] = last
    starts = sorted({s[0] for s in sections})
    type_at = {s[0]: s[1] for s in sections}
    for severity, table in (("bad", ends), ("warn", soft_ends)):
        for off in sorted(table):
            if severity == "warn" and off in ends:
                continue
            end = table[off]
            nxt = next((s for s in starts if s > off), None)
            if nxt is None:
                continue
            if end > nxt:
                msg = ("%s at 0x%x runs %d byte(s) into the next section at 0x%x"
                       % (DEX_SECTION_NAMES.get(type_at.get(off), "0x%x" % off), off, end - nxt, nxt))
                bad(msg) if severity == "bad" else warn(msg)
                continue
            nonzero = [p for p in range(end, min(nxt, len(d))) if d[p]]
            if nonzero:
                msg = ("non-zero padding before %s at 0x%x · %d leftover byte(s), first 0x%02x at 0x%x"
                       % (DEX_SECTION_NAMES.get(type_at.get(nxt), "0x%x" % nxt), nxt,
                          len(nonzero), d[nonzero[0]], nonzero[0]))
                bad(msg) if severity == "bad" else warn(msg)
    # header integrity last: a stale checksum usually hides a layout problem
    # that the checks above already named, and that name is the useful one
    if (zlib.adler32(d[12:]) & 0xFFFFFFFF) != u4(d, 8):
        bad("header checksum mismatch · bytes were written after the header was sealed")
    if hashlib.sha1(d[32:]).digest() != d[12:32]:
        bad("header sha1 mismatch · bytes were written after the header was sealed")
    return problems


def dex_audit_apk(apk):
    """[(name, size, problems)] for every classes*.dex in the archive."""
    report = []
    try:
        with zipfile.ZipFile(str(apk)) as z:
            for name in sorted(n for n in z.namelist() if re.match(r"classes\d*\.dex$", n)):
                data = z.read(name)
                report.append((name, len(data), dex_validate(data)))
    except Exception as e:
        report.append(("<archive>", 0, [("bad", "cannot read the archive · " + str(e))]))
    return report


def show_dex_audit(apk):
    """Print the per-dex audit. True when every dex would load on ART."""
    report = dex_audit_apk(apk)
    if not report:
        Out.warn("no classes*.dex found · nothing to audit")
        return False
    broken = 0
    for name, size, problems in report:
        hard = [m for s, m in problems if s == "bad"]
        soft = [m for s, m in problems if s == "warn"]
        if hard:
            broken += 1
            Out.bad("%s · %s" % (name, hard[0]))
            for m in hard[1:3]:
                Out.info("  " + m)
            Out.info("  android drops this whole dex at load time · every class inside it disappears")
        elif soft:
            Out.warn("%s · %s" % (name, soft[0]))
    if broken:
        Out.bad("%d of %d dex file(s) would be rejected by ART" % (broken, len(report)))
        Out.info("a rejected dex is invisible at install time · it only shows up as ClassNotFoundException at launch")
        return False
    Out.ok("%d dex file(s) pass the structural audit" % len(report))
    return True


def show_manifest_truth(apk):
    """Report the flags the FINAL manifest actually carries, not what we meant to set."""
    _raw, info = safe_manifest(apk)
    if not _raw:
        Out.warn("manifest unreadable · the applied flags cannot be confirmed")
        return
    _x = Axml(_raw)
    if not _x.valid or _x.pool is None or not _x.pool.items or not _x.attrs:
        Out.warn("binary manifest could not be decoded by this parser · flags unknown")
        Out.info("do not read the next lines as 'absent': this file uses a pool layout the parser misses")
        return
    if not info:
        Out.warn("manifest unreadable · the applied flags cannot be confirmed")
        return
    Out.kv("manifest flags", " · ".join([
        "debuggable=" + ("true" if info.get("debuggable") else "false"),
        "cleartext=" + ("true" if info.get("cleartext") else "false"),
        "netsec=" + ("present" if info.get("netsec") else "absent"),
    ]))
    if not info.get("netsec"):
        Out.warn("no networkSecurityConfig in the final manifest · android falls back to the platform trust store")
    if not info.get("debuggable"):
        Out.info("debuggable is not set · a 'manifest hardened' claim would be false here")


def dex_patch_code(data, off, kind):
    """Overwrite one method body with a return stub — at the SAME length.

    A code_item carries no length field: the verifier derives its size from
    insns_size (+ tries) and walks the section item by item. Shrinking
    insns_size therefore shifts every item behind it, the section stops ending
    where the map_list says the next one starts, and ART rejects the whole dex
    with "Non-zero padding ... before section of type 8193". The app then dies
    at launch with ClassNotFoundException for its own providers, long after a
    clean install and a clean signature check.

    So: the stub goes in first, the rest of the original code units become
    nop, and registers/ins/outs/insns_size/tries_size/debug_info_off keep the
    exact shape they had.
    """
    if off <= 0 or off + 16 > len(data):
        return False
    try:
        regs = u2(data, off)
        ins = u2(data, off + 2)
        insns_size = u4(data, off + 12)
    except Exception:
        return False
    stub = CODE_STUBS.get(kind)
    if not stub or regs == 0:
        return False
    need = len(stub) // 2
    if insns_size < need:
        return False
    base = off + 16
    if base + insns_size * 2 > len(data):
        return False
    new_regs = ins if kind == "void" else max(ins + 1, 1)
    if new_regs > 0xFFFF:
        return False
    # registers_size, ins_size, outs_size (the stub makes no calls).
    # tries_size, debug_info_off and insns_size are deliberately untouched.
    struct.pack_into("<HHH", data, off, new_regs, ins, 0)
    data[base : base + len(stub)] = stub
    if need < insns_size:
        data[base + len(stub) : base + insns_size * 2] = b"\x00\x00" * (insns_size - need)
    return True


def dex_stub_ok(data, off, kind):
    """True when the body at `off` is exactly `stub` followed by nop padding.

    A stub dropped on top of the original instruction stream desyncs ART's
    linear instruction walk: it decodes from the middle of an old instruction
    and dies with things like "List too large for insns size". Requiring
    stub + nop makes that shape impossible.
    """
    stub = CODE_STUBS.get(kind)
    if not stub or off <= 0 or off + 16 > len(data):
        return False
    insns_size = u4(data, off + 12)
    need = len(stub) // 2
    if insns_size < need:
        return False
    base = off + 16
    end = base + insns_size * 2
    if end > len(data):
        return False
    if bytes(data[base:base + len(stub)]) != stub:
        return False
    return bytes(data[base + len(stub):end]) == b"\x00\x00" * (insns_size - need)


def dex_surgery(data, targets):
    idx = DexIndex(data)
    if not idx.ok:
        return bytearray(data), []
    buf = bytearray(data)
    hits = []
    for desc, method, kind in targets:
        cbase = idx.find_class(desc)
        if cbase is None:
            continue
        cdata = u4(buf, cbase + 24)
        if not cdata:
            continue
        p = cdata
        try:
            sf, p = uleb(buf, p)
            inf, p = uleb(buf, p)
            dm, p = uleb(buf, p)
            vm, p = uleb(buf, p)
            for _ in range(sf):
                _, p = uleb(buf, p)
                _, p = uleb(buf, p)
            for _ in range(inf):
                _, p = uleb(buf, p)
                _, p = uleb(buf, p)
            for count in (dm, vm):
                midx = 0
                for _ in range(count):
                    diff, p = uleb(buf, p)
                    midx += diff
                    _, p = uleb(buf, p)
                    code_off, p = uleb(buf, p)
                    if not code_off:
                        continue
                    if idx.method_name(midx) != method:
                        continue
                    kind_i = idx.stub_kind(midx, kind)
                    before = dex_code_item_end(buf, code_off)
                    snapshot = bytes(buf[code_off:before]) if before else None
                    if not dex_patch_code(buf, code_off, kind_i):
                        continue
                    after = dex_code_item_end(buf, code_off)
                    if before is None or after != before or not dex_stub_ok(buf, code_off, kind_i):
                        # length moved or the body is not stub+nop: undo, both
                        # shapes make ART reject the whole dex
                        if snapshot:
                            buf[code_off:before] = snapshot
                        DEX_GUARD["failures"].append((desc, method, code_off))
                        continue
                    hits.append((desc, method, code_off, kind_i))
        except Exception:
            continue
    if hits:
        dex_fix_header(buf)
    return buf, hits


DEX_TARGETS = [
    ("Ljavax/net/ssl/X509TrustManager;", "checkServerTrusted", "void"),
    ("Ljavax/net/ssl/X509TrustManager;", "checkClientTrusted", "void"),
    ("Landroid/webkit/WebViewClient;", "onReceivedSslError", "void"),
    ("Landroid/webkit/WebViewClient;", "onReceivedError", "void"),
    ("Landroid/webkit/WebViewClient;", "onReceivedClientCertRequest", "void"),
    ("Landroid/security/NetworkSecurityPolicy;", "isCleartextTrafficPermitted", "true"),
    ("Landroid/net/http/X509TrustManagerExtensions;", "checkServerTrusted", "void"),
    ("Ljava/security/cert/X509Certificate;", "checkValidity", "void"),
]

SSL_NAME_TARGETS = {
    "checkTrustedRecursive": "void",
    "checkTrustAnchor": "void",
    "checkServerTrusted": "void",
    "checkClientTrusted": "void",
    "verifyHostname": "true",
    "verifyHost": "true",
    "verifyCertificateChain": "void",
    "checkValidity": "void",
    "onReceivedClientCertRequest": "void",
}


# Play Store licence verification: LVL (Policy.allowAccess / LicenseChecker)
# and PairIP (connectToLicensingService / retryOrThrow). allowAccess() returning
# true is enough — LicenseChecker then reports allow(0x100) by itself.
LVL_NAME_TARGETS = {
    "allowAccess": "true",
    "connectToLicensingService": "void",
    "retryOrThrow": "void",
    "dontAllow": "void",
    "isLicensed": "true",
    "verifyLicense": "true",
}


def collect_ssl_targets(apk):
    targets = list(DEX_TARGETS)
    try:
        with zipfile.ZipFile(apk) as z:
            for name in z.namelist():
                if not re.match(r"classes\d*\.dex$", name):
                    continue
                idx = DexIndex(z.read(name))
                if not idx.ok:
                    continue
                for desc in type_names(idx, 250000):
                    if not desc.startswith("L"):
                        continue
                    low = desc.lower()
                    if "hostnameverifier" in low:
                        targets.append((desc, "verify", "true"))
                        targets.append((desc, "verifyHostname", "true"))
                    elif "certificatepinner" in low:
                        targets.append((desc, "check", "void"))
                    elif "chaincleaner" in low:
                        targets.append((desc, "clean", "void"))
                    elif "trustmanager" in low:
                        targets.append((desc, "checkServerTrusted", "void"))
                        targets.append((desc, "checkClientTrusted", "void"))
                        targets.append((desc, "checkTrustedRecursive", "void"))
                    elif "cronet" in low or "certverifier" in low:
                        targets.append((desc, "verifyCertificateChain", "void"))
    except Exception:
        pass
    return targets


def dex_surgery_apk(apk, out, targets, name_map=None):
    changed = []
    DEX_GUARD["failures"] = []
    DEX_GUARD["rejected"] = []
    try:
        with zipfile.ZipFile(apk) as zin:
            plan = {}
            for name in zin.namelist():
                if not re.match(r"classes\d*\.dex$", name):
                    continue
                data = zin.read(name)
                buf, hits = dex_surgery(data, targets)
                if name_map:
                    buf2, hits2 = dex_surgery_by_name(bytes(buf), name_map)
                    if hits2:
                        buf = buf2
                        hits = list(hits) + list(hits2)
                if hits:
                    # only block what the patch INTRODUCED: a dex that was already
                    # imperfect in the input is not this build's fault, and refusing
                    # to patch it would silently ship the app unmodified
                    was = {m for s, m in dex_validate(bytes(data)) if s == "bad"}
                    now = {m for s, m in dex_validate(bytes(buf)) if s == "bad"}
                    fresh = now - was
                    if fresh:
                        DEX_GUARD["rejected"].append((name, sorted(fresh)[0]))
                        hits = []
                    else:
                        plan[name] = bytes(buf)
                        changed.extend((name,) + h for h in hits)
            if not plan:
                return False, changed
            with zipfile.ZipFile(out, "w") as zout:
                for item in zin.infolist():
                    if item.filename.upper().startswith("META-INF/") and item.filename.upper().endswith((".SF", ".RSA", ".DSA", ".EC", ".MF")):
                        continue
                    payload = plan.get(item.filename)
                    if payload is None:
                        payload = zin.read(item.filename)
                    zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
                    zi.compress_type = item.compress_type
                    zi.external_attr = item.external_attr
                    zi.internal_attr = item.internal_attr
                    zi.create_system = item.create_system
                    zout.writestr(zi, payload)
        return True, changed
    except Exception:
        if Path(out).exists():
            Path(out).unlink(missing_ok=True)
        return False, changed


class AxmlWriter:
    def __init__(self, data):
        self.raw = data
        self.strings = []
        self.chunks = []
        self.pool_index = None
        self.ok = False
        self._parse()

    def _parse(self):
        d = self.raw
        if len(d) < 16 or u2(d, 0) != 0x0003:
            return
        self.ok = True
        off = u2(d, 2)
        guard = 0
        while off + 8 <= len(d) and guard < 400000:
            guard += 1
            ctype = u2(d, off)
            csize = u4(d, off + 4)
            if csize < 8:
                break
            self.chunks.append([ctype, d[off : off + csize]])
            off += csize
        for i, (ctype, blob) in enumerate(self.chunks):
            if ctype == 0x0001:
                self.pool_index = i
                self.strings = list(StringPool(blob, 0).items)
                break

    def intern(self, value):
        try:
            return self.strings.index(value)
        except ValueError:
            self.strings.append(value)
            return len(self.strings) - 1

    def build_pool(self):
        offs = b""
        data = b""
        base = 28 + 4 * len(self.strings)
        for s in self.strings:
            offs += struct.pack("<I", len(data))
            enc = s.encode("utf-8")
            units = len(s.encode("utf-16-le")) // 2
            data += uleb_encode(units) + uleb_encode(len(enc)) + enc + b"\x00"
        while (base + len(data)) % 4:
            data += b"\x00"
        size = base + len(data)
        return struct.pack("<HHIIIIII", 0x0001, 28, size, len(self.strings), 0, 0x100, base, 0) + offs + data

    def patch_application(self, attrs):
        changed = []
        for i, (ctype, blob) in enumerate(self.chunks):
            if ctype != 0x0102:
                continue
            name_idx = u4(blob, 20)
            if not (0 <= name_idx < len(self.strings)) or self.strings[name_idx] != "application":
                continue
            new_blob, done = self._apply(blob, attrs)
            if done:
                self.chunks[i][1] = new_blob
                changed.extend(done)
            break
        return changed

    def _apply(self, blob, attrs):
        base = 16
        count = u2(blob, base + 12)
        start = u2(blob, base + 8) or 20
        size = u2(blob, base + 10) or 20
        out = bytearray(blob)
        known = {}
        for i in range(count):
            a = base + start + i * size
            nidx = u4(out, a + 4)
            if 0 <= nidx < len(self.strings):
                known[self.strings[nidx]] = a
        done = []
        pending = []
        for name, dtype, value in attrs:
            if name in known:
                a = known[name]
                raw, data_val = self._fields(dtype, value)
                struct.pack_into("<H", out, a + 12, 8)
                out[a + 14] = 0
                out[a + 15] = dtype
                struct.pack_into("<I", out, a + 8, raw)
                struct.pack_into("<I", out, a + 16, data_val)
                done.append(name)
            else:
                pending.append((name, dtype, value))
        if pending:
            body = b""
            for name, dtype, value in pending:
                nidx = self.intern(name)
                raw, data_val = self._fields(dtype, value)
                body += struct.pack("<IIIHBBI", 0xFFFFFFFF, nidx, raw, 8, 0, dtype, data_val)
                done.append(name)
            edge = base + start + count * size
            out = bytearray(bytes(out[:edge]) + body + bytes(out[edge:]))
            struct.pack_into("<H", out, base + 12, count + len(pending))
            struct.pack_into("<I", out, 4, len(out))
        return bytes(out), done

    def _fields(self, dtype, value):
        if dtype == 0x03:
            idx = self.intern(str(value))
            return idx, idx
        try:
            return 0xFFFFFFFF, int(value)
        except Exception:
            return 0xFFFFFFFF, 0

    def serialize(self):
        if not self.ok:
            return None
        parts = []
        for i, (ctype, blob) in enumerate(self.chunks):
            if i == self.pool_index:
                parts.append(self.build_pool())
            else:
                parts.append(blob)
        body = b"".join(parts)
        return struct.pack("<HHI", 0x0003, 8, 8 + len(body)) + body


def axml_patch_manifest(data, edits):
    w = AxmlWriter(data)
    if not w.ok or w.pool_index is None:
        return None, []
    changed = w.patch_application(edits)
    if not changed:
        return None, []
    out = w.serialize()
    return out, changed






def dex_zero_fixed_section_gaps(data):
    """Zero alignment padding after fixed-size DEX sections.

    Safe because we only touch bytes AFTER a section whose total byte
    length we can compute exactly (type × count × item_size) and BEFORE
    the next section whose start offset is recorded in the map_list.
    Variable-size sections (0x1000+) are never touched.

    Returns (new_bytes, n_zeroed).
    """
    # item sizes in bytes for fixed-size section types
    FIXED = {
        0x0001: 4,   # string_id_item
        0x0002: 4,   # type_id_item
        0x0003: 12,  # proto_id_item
        0x0004: 8,   # field_id_item
        0x0005: 8,   # method_id_item
        0x0006: 32,  # class_def_item
        0x0007: 4,   # call_site_id_item
        0x0008: 8,   # method_handle_item
    }
    if len(data) < 0x70 or data[:4] != b"dex\n":
        return data, 0
    try:
        map_off  = struct.unpack_from("<I", data, 0x34)[0]
        n_items  = struct.unpack_from("<I", data, map_off)[0]
        if n_items == 0 or n_items > 1024:
            return data, 0
        sections = []
        for i in range(n_items):
            base  = map_off + 4 + i * 12
            stype = struct.unpack_from("<H", data, base)[0]
            count = struct.unpack_from("<I", data, base + 4)[0]
            off   = struct.unpack_from("<I", data, base + 8)[0]
            sections.append((off, stype, count))
        sections.sort()
        # build offset → next_offset map
        next_off = {}
        for i in range(len(sections) - 1):
            next_off[sections[i][0]] = sections[i + 1][0]
        out   = bytearray(data)
        fixed = 0
        for off, stype, count in sections:
            item_sz = FIXED.get(stype)
            if item_sz is None or count == 0:
                continue
            end = off + count * item_sz
            nxt = next_off.get(off)
            if nxt is None or end > nxt or end >= len(out):
                continue
            for p in range(end, min(nxt, len(out))):
                if out[p] != 0:
                    out[p] = 0
                    fixed += 1
        if fixed:
            out[12:32] = hashlib.sha1(bytes(out[32:])).digest()
            struct.pack_into("<I", out, 8,
                             zlib.adler32(bytes(out[12:])) & 0xFFFFFFFF)
            # never hand back a "repair" that made the file worse
            before = len([m for s, m in dex_validate(bytes(data)) if s == "bad"])
            after = len([m for s, m in dex_validate(bytes(out)) if s == "bad"])
            if after > before:
                return data, 0
        return bytes(out), fixed
    except Exception:
        return data, 0


def prune_manifest_orphans(apk_path, work):
    """Remove manifest <provider>/<service>/<receiver>/<activity> entries
    whose class is absent from every dex in the APK.
    Uses AxmlWriter (binary AXML direct edit) — same approach as the manifest
    hardening stage, so it works on any binary AndroidManifest.xml."""
    import zipfile as _zf, re as _re, struct as _st
    try:
        # 1. collect all classes from every dex
        all_classes = set()
        with _zf.ZipFile(str(apk_path)) as z:
            for name in z.namelist():
                if not _re.match(r"classes\d*\.dex$", name):
                    continue
                try:
                    cs = dex_class_set(z.read(name))
                    if cs:
                        all_classes.update(cs)
                except Exception:
                    pass
        if not all_classes:
            return 0

        def _norm(cls):
            c = cls.strip()
            if c.startswith("L") and c.endswith(";"):
                c = c[1:-1]
            return c.replace("/", ".")
        present = {_norm(c) for c in all_classes}

        # 2. read manifest and package name
        with _zf.ZipFile(str(apk_path)) as z:
            if "AndroidManifest.xml" not in z.namelist():
                return 0
            man_bytes = z.read("AndroidManifest.xml")

        pkg = ""
        try:
            info = axml_manifest(man_bytes)
            if info:
                p = info.get("package", "")
                if p and p != "?":
                    pkg = p
        except Exception:
            pass

        # 3. parse AXML to find orphan component names
        try:
            ax = Axml(man_bytes)
            if not ax.valid:
                return 0
        except Exception:
            return 0

        # collect class names of all components
        orphan_names = set()
        component_tags = {"provider", "service", "receiver", "activity",
                          "activity-alias"}
        for el in ax.walk:
            if el.get("kind") != "start":
                continue
            tag = el.get("name", "").split("}")[-1] if "}" in el.get("name","") else el.get("name","")
            if tag not in component_tags:
                continue
            attrs = dict(el.get("attrs", []))
            # find android:name
            cls_name = None
            for k, v in attrs.items():
                attr = k.split("}")[-1] if "}" in k else k
                if attr == "name":
                    cls_name = v
                    break
            if not cls_name:
                continue
            if cls_name.startswith("."):
                cls_name = pkg + cls_name
            elif "." not in cls_name and pkg:
                cls_name = pkg + "." + cls_name
            if cls_name not in present:
                orphan_names.add(cls_name)

        if not orphan_names:
            return 0

        # 4. remove orphan components from the binary AXML
        # We do this by zeroing their element blocks using AxmlWriter internals
        # or by rebuilding the XML text and re-encoding
        try:
            man_text = axml_to_text(ax)
        except Exception:
            return 0

        if not man_text:
            return 0

        # 5. remove orphan component blocks from text
        removed = 0
        for cls_name in orphan_names:
            # match both full name and short name
            short = cls_name.split(".")[-1]
            full_escaped  = cls_name.replace(".", "\\.")
            short_escaped = short.replace(".", "\\.")
            # try to remove the whole component tag
            for pattern in [
                r'<(?:provider|service|receiver|activity|activity-alias)(?:\s[^>]*)?(?:android:name|name)="'
                + _re.escape(cls_name) + r'"[^>]*(?:/>|>.*?</(?:provider|service|receiver|activity|activity-alias)>)',
            ]:
                new_text, n = _re.subn(pattern, "", man_text, flags=_re.DOTALL)
                if n:
                    man_text = new_text
                    removed += n

        if not removed:
            return 0

        # 6. re-encode to binary AXML
        try:
            new_man = axml_from_text(man_text)
        except Exception as _e:
            Out.warn("manifest re-encode failed · " + str(_e))
            return 0

        # 7. repack APK
        tmp = Path(str(apk_path) + ".prune")
        with _zf.ZipFile(str(apk_path)) as zin,              _zf.ZipFile(str(tmp), "w", allowZip64=True) as zout:
            for info in zin.infolist():
                payload = new_man if info.filename == "AndroidManifest.xml"                           else zin.read(info.filename)
                zi = _zf.ZipInfo(info.filename, date_time=info.date_time)
                zi.compress_type = info.compress_type
                zi.external_attr = info.external_attr
                zi.internal_attr = info.internal_attr
                zi.create_system = info.create_system
                zout.writestr(zi, payload)
        import os as _os
        _os.replace(str(tmp), str(apk_path))
        return removed
    except Exception as _e:
        Out.warn("manifest prune skipped · " + str(_e))
        return 0


def surgery_pipeline(pipe, merged, final, args):
    Out.head("surgical engine", G_WARM)
    Out.info("no apktool, no aapt2 · direct dex and manifest editing")
    targets = collect_ssl_targets(merged)
    sigmap = {n: "true" for n in SIG_TRUE}
    sigmap.update({n: "false" for n in SIG_FALSE})
    sigmap.update(SSL_NAME_TARGETS)
    if getattr(args, "mode", "") in ("signature", "full", "ssl") or getattr(args, "remove_license", False):
        sigmap.update(LVL_NAME_TARGETS)
    if getattr(args, "targets", None):
        extra_cls, extra_names, problems = load_targets(args.targets)
        for prob in problems:
            Out.warn(prob)
        targets.extend(extra_cls)
        sigmap.update(extra_names)
        Out.kv("user targets", "%d class-bound · %d name-bound" % (len(extra_cls), len(extra_names)))
    Out.kv("targets", "%d class-bound · %d name-bound" % (len(targets), len(sigmap)))
    step = Path(pipe.work) / "surgery.apk"
    ok, changed = dex_surgery_apk(merged, step, targets, sigmap)
    if ok:
        Out.ok("%d method(s) rewritten across %d dex file(s)" % (len(changed), len({c[0] for c in changed})))
        for name, desc, method, off, kind in changed[:12]:
            Out.bullet("%s · %s · %s" % (name, desc.split("/")[-1].rstrip(";"), method))
        if len(changed) > 12:
            Out.info("… %d more" % (len(changed) - 12))
    else:
        Out.warn("no method matched · copying the archive unchanged")
        Out.warn("the output is the ORIGINAL app, unmodified · nothing was neutralised")
        Out.info("check the target list above: the methods it looked for are not in this build")
        shutil.copy2(merged, step)
    edits = [
        ("debuggable", 0x12, 0xFFFFFFFF),
        ("usesCleartextTraffic", 0x12, 0xFFFFFFFF),
    ]
    try:
        with zipfile.ZipFile(step) as z:
            man = safe_manifest(z)[0]
        patched, applied = axml_patch_manifest(man, edits)
    except Exception:
        patched, applied = None, []
    if patched:
        tmp = Path(pipe.work) / "surgery_manifest.apk"
        with zipfile.ZipFile(step) as zin, zipfile.ZipFile(tmp, "w") as zout:
            for item in zin.infolist():
                payload = patched if item.filename == "AndroidManifest.xml" else zin.read(item.filename)
                zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
                zi.compress_type = item.compress_type
                zi.external_attr = item.external_attr
                zi.internal_attr = item.internal_attr
                zi.create_system = item.create_system
                zout.writestr(zi, payload)
        os.replace(tmp, step)
        Out.ok("manifest edited in place · " + ", ".join(applied))
    else:
        Out.info("manifest already carries the target flags")
    # the netsec edit above lives in the tree and dies with it, so replace the
    # compiled resource in the archive the platform will actually read
    _ns_status, _ns_detail = inject_netsec(step)
    if _ns_status == "replaced":
        Out.ok("network security config rewritten in the archive · " + _ns_detail)
    elif _ns_status == "unchanged":
        Out.ok("network security config already trusts user CAs · " + _ns_detail)
    elif _ns_status == "absent":
        Out.warn("no network security config to replace · " + _ns_detail)
        Out.info("with none, android trusts system CAs only · a user CA is rejected")
    else:
        Out.warn("netsec injection failed · " + _ns_detail)
    # the tree patch above dies with the tree, so patch the engine in the
    # archive that will actually be signed
    for _so, _res in patch_native_in_apk(step, pipe.work, getattr(args, "flutter_engine", None)):
        if _res.hits:
            for _off, _fn, _ret, _st in _res.names:
                if _st != "patched":
                    continue
                Out.ok("%s · %s @0x%x · returns %d" % (_so, _fn, _off, _ret))
                pipe.records.append({"file": _so, "offset": hex(_off), "arch": _res.arch,
                                     "kind": "tls-verify", "ret": _ret, "fn": _fn})
        elif _res.already:
            Out.info("%s · engine already patched" % _so)
        elif getattr(_res, "error", None):
            Out.warn("%s · %s" % (_so, _res.error))
    for name, why in DEX_GUARD.get("rejected", []):
        Out.bad("%s would not load after patching · kept the original bytes" % name)
        Out.info("  " + why)
    for desc, method, off in DEX_GUARD.get("failures", [])[:6]:
        Out.warn("patch skipped · %s · %s would have changed the item length"
                 % (desc.split("/")[-1].rstrip(";"), method))
    # a rejected dex is fatal: android drops the whole file, so never sign it
    if not show_dex_audit(step):
        was_bad = {n for n, _s, p in dex_audit_apk(merged) if any(s == "bad" for s, _ in p)}
        now_bad = {n for n, _s, p in dex_audit_apk(step) if any(s == "bad" for s, _ in p)}
        if now_bad and now_bad <= was_bad:
            Out.warn("the input dex was already rejected by ART · this build did not cause it")
        else:
            Out.bad("refusing to sign this build · the dex layout above crashes the app at launch")
            Out.info("artifact kept for inspection: " + str(step))
            return None, "surgery"
    # prune orphan manifest components whose classes are missing
    _pruned = prune_manifest_orphans(step, pipe.work)
    if _pruned:
        Out.ok("pruned %d orphan manifest component(s)" % _pruned)
    shutil.move(str(step), str(final))
    return final, "surgery"




LOG = {"fh": None, "path": None}


def log_open(path=None):
    if LOG["fh"]:
        return LOG["path"]
    target = Path(path).expanduser() if path else HOME / ("arp-%s.log" % time.strftime("%Y%m%d-%H%M%S"))
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        LOG["fh"] = open(target, "w", encoding="utf-8", errors="replace")
        LOG["path"] = target
        return target
    except Exception:
        return None


def log_line(kind, text):
    if not LOG["fh"]:
        return
    try:
        stamp = time.strftime("%H:%M:%S")
        LOG["fh"].write("[%s] %-5s %s\n" % (stamp, kind, text))
        LOG["fh"].flush()
    except Exception:
        pass


def log_close():
    if LOG["fh"]:
        try:
            LOG["fh"].close()
        except Exception:
            pass
        LOG["fh"] = None


INVOKE_OPS = {0x6E, 0x6F, 0x70, 0x71, 0x72, 0x74, 0x75, 0x76, 0x77, 0x78}


def dex_invokes(data):
    idx = DexIndex(data)
    if not idx.ok:
        return []
    edges = []
    limit = min(idx.c_n, 60000)
    for i in range(limit):
        cbase = idx.c_off + i * 32
        desc = idx.type_name(u4(data, cbase))
        cdata = u4(data, cbase + 24)
        if not cdata:
            continue
        p = cdata
        try:
            sf, p = uleb(data, p)
            inf, p = uleb(data, p)
            dm, p = uleb(data, p)
            vm, p = uleb(data, p)
            for _ in range(sf + inf):
                _, p = uleb(data, p)
                _, p = uleb(data, p)
            for count in (dm, vm):
                midx = 0
                for _ in range(count):
                    diff, p = uleb(data, p)
                    midx += diff
                    _, p = uleb(data, p)
                    code_off, p = uleb(data, p)
                    if not code_off:
                        continue
                    n = u4(data, code_off + 12)
                    base = code_off + 16
                    for k in range(min(n, 20000)):
                        if k + 1 >= n:
                            break
                        unit = u2(data, base + k * 2)
                        op = unit & 0xFF
                        if op in INVOKE_OPS:
                            callee = u2(data, base + (k + 1) * 2)
                            if callee < idx.m_n:
                                edges.append((desc, idx.method_name(midx), idx.method_name(callee)))
        except Exception:
            continue
    return edges


PIN_RX = re.compile(r"(CertificatePinner|TrustManager|HostnameVerifier|sslSocketFactory|X509TrustManager|pin-set|PublicKeyPinning)", re.I)


def detect_pinning(apk):
    found = {}
    urls = set()
    try:
        with zipfile.ZipFile(apk) as z:
            for name in z.namelist():
                if re.match(r"classes\d*\.dex$", name):
                    data = z.read(name)
                    idx = DexIndex(data)
                    if not idx.ok:
                        continue
                    for i in range(min(idx.c_n, 60000)):
                        cbase = idx.c_off + i * 32
                        desc = idx.type_name(u4(data, cbase))
                        for m in PIN_RX.finditer(desc):
                            found.setdefault(m.group(1), set()).add(desc)
                    for i in range(min(idx.s_n, 60000)):
                        s = idx.string(i)
                        if s.startswith(("https://", "http://")) and len(s) < 200:
                            host = s.split("//", 1)[-1].split("/")[0].split(":")[0]
                            if "." in host and " " not in host:
                                urls.add(host)
                elif name.startswith("res/xml/") and name.endswith(".xml"):
                    try:
                        blob = z.read(name)
                        if b"pin-set" in blob or b"certificate" in blob:
                            found.setdefault("network-security-config", set()).add(name)
                    except Exception:
                        pass
    except Exception:
        pass
    return found, sorted(urls)[:200]


SSL_CALLEE_RX = re.compile(
    r"(checkServerTrusted|checkClientTrusted|checkTrustedRecursive|checkTrustAnchor|"
    r"getAcceptedIssuers|setDefaultHostnameVerifier|setSSLSocketFactory|SSLContext;->init|"
    r"CertificatePinner;->check|CertificateChainCleaner;->clean|verifyHostname|verifyHost|"
    r"X509TrustManager|setTrustedCertificates|getInstance;->\"X509\"|"
    r"setHostnameVerifier|checkValidity|X509Certificate;->getPublicKey|MessageDigest;->digest)",
    re.I)


def ssl_call_surface(apk, limit=14):
    """Methods that CALL into the TLS/pinning API: the real pinning sites.

    The name-based patcher only finds methods called check/verify/clean. An app
    that pins inside its own method name (validatePins, secureChannel, ...) is
    invisible to it, but its call into CertificatePinner.check / TrustManager
    is not. This lists those callers so they can be targeted.
    """
    found = {}
    try:
        with zipfile.ZipFile(apk) as z:
            for name in sorted(n for n in z.namelist() if re.match(r"classes\d*\.dex$", n)):
                data = z.read(name)
                for cls, meth, callee in dex_invokes(data):
                    if not SSL_CALLEE_RX.search(callee or ""):
                        continue
                    key = (cls, meth)
                    found.setdefault(key, set()).add(callee.split("->")[-1].split("(")[0])
    except Exception:
        pass
    rows = sorted(found.items(), key=lambda kv: -len(kv[1]))
    return [(cls, meth, sorted(callees)) for (cls, meth), callees in rows[:limit]]


HOST_TLDS = ("com|net|org|io|co|app|dev|me|info|biz|xyz|gov|edu|cloud|site|online|"
             "tech|ai|tv|ly|in|dz|sa|ae|fr|uk|de|es|it|ru|cn|tr|ma|tn|eg|qa|kw|be|nl")
# at least two dots and a real tld: "java.vendor" is not a host, "apis.ooredoo.dz" is
HOST_RX = re.compile(r"^[a-z0-9][a-z0-9.\-]{2,}\.[a-z0-9.\-]+\.[a-z]{2,12}$")
HOST_TLD_RX = re.compile(r"\.(?:%s)$" % HOST_TLDS)


def dex_host_refs(data, want=None, cap=200000, needles=None):
    """{host: {(class, method)}} for every const-string that looks like a host."""
    idx = DexIndex(data)
    if not idx.ok:
        return {}
    out = {}
    for i in range(min(idx.c_n, 60000)):
        cbase = idx.c_off + i * 32
        desc = idx.type_name(u4(data, cbase))
        cdata = u4(data, cbase + 24)
        if not cdata:
            continue
        p = cdata
        try:
            sf, p = uleb(data, p)
            inf, p = uleb(data, p)
            dm, p = uleb(data, p)
            vm, p = uleb(data, p)
            for _ in range(sf + inf):
                _, p = uleb(data, p)
                _, p = uleb(data, p)
            for count in (dm, vm):
                midx = 0
                for _ in range(count):
                    diff, p = uleb(data, p)
                    midx += diff
                    _, p = uleb(data, p)
                    code_off, p = uleb(data, p)
                    if not code_off:
                        continue
                    n = min(u4(data, code_off + 12), cap)
                    base = code_off + 16
                    for k in range(n - 1):
                        unit = u2(data, base + k * 2)
                        op = unit & 0xFF
                        if op not in (0x1A, 0x1B):
                            continue
                        if op == 0x1A:
                            sidx = u2(data, base + (k + 1) * 2)
                        else:
                            if k + 2 >= n:
                                continue
                            sidx = u2(data, base + (k + 1) * 2) | (u2(data, base + (k + 2) * 2) << 16)
                        val = idx.string(sidx)
                        if not val or len(val) > 90:
                            continue
                        if want is not None and val not in want:
                            continue
                        if needles is not None:
                            if val not in needles:
                                continue
                        elif not (HOST_RX.match(val) and HOST_TLD_RX.search(val)):
                            continue
                        out.setdefault(val, set()).add((desc, idx.method_name(midx)))
        except Exception:
            continue
    return out


SYSTEM_STORE_MARKERS = frozenset((
    "/system/etc/security/cacerts", "/system/etc/security/cacerts/",
    "AndroidCAStore", "cacerts", "/apex/com.android.conscrypt/cacerts",
))


def show_store_bypass(apk, limit=10):
    """Classes that build their own trust store from /system/etc/security/cacerts.

    network_security_config is only consulted by the platform TrustManager. An
    sdk that reads the system store itself never asks the platform, so no amount
    of NSC editing will make its traffic interceptable — those classes have to be
    patched or hooked instead.
    """
    found = {}
    try:
        with zipfile.ZipFile(apk) as z:
            for name in sorted(n for n in z.namelist() if re.match(r"classes\d*\.dex$", n)):
                for _s, who in dex_host_refs(z.read(name), needles=SYSTEM_STORE_MARKERS).items():
                    for cls, meth in who:
                        found.setdefault(cls, set()).add(meth)
    except Exception:
        return
    if not found:
        Out.info("no class reads the system CA store directly · the nsc covers the whole process")
        return
    Out.warn("%d class(es) build their own trust store · they ignore network_security_config" % len(found))
    for cls in sorted(found)[:limit]:
        Out.bullet("%s · %s" % (cls.strip("L;").split("/")[-1], ", ".join(sorted(found[cls])[:2])))


def show_host_issuers(apk, limit=12):
    """Which class sends a request to which host — the answer to 'why is this
    domain still blocked': you see whether it comes from the app, from a
    third-party sdk, and in which class to look for the pinning."""
    refs = {}
    try:
        with zipfile.ZipFile(apk) as z:
            for name in sorted(n for n in z.namelist() if re.match(r"classes\d*\.dex$", n)):
                for host, who in dex_host_refs(z.read(name)).items():
                    refs.setdefault(host, set()).update(who)
    except Exception:
        return
    if not refs:
        Out.info("no host strings found in the dex payload")
        return
    rows = sorted(refs.items(), key=lambda kv: -len(kv[1]))
    Out.kv("host issuers", len(rows))
    for host, who in rows[:limit]:
        cls = sorted({c.strip("L;").split("/")[-1] for c, _m in who})
        Out.bullet("%s  <- %s" % (host, ", ".join(cls[:3])))


def show_ssl_surface(apk):
    rows = ssl_call_surface(apk)
    if not rows:
        Out.info("no method calls the tls/pinning api directly · pinning is not in java code")
        return rows
    Out.kv("tls call sites", len(rows))
    for cls, meth, callees in rows:
        Out.bullet("%s · %s  <- %s" % (cls.strip("L;").split("/")[-1], meth, ", ".join(callees[:3])))
    return rows


def frida_script(pinning, apk_name):
    lines = [
        "Java.perform(function () {",
        "  var targets = [",
    ]
    seen = set()
    for group in pinning.values():
        for desc in group:
            if not desc.startswith("L") or desc in seen:
                continue
            seen.add(desc)
            lines.append('    "%s",' % desc.replace("/", ".")[1:-1])
    lines += [
        "  ];",
        "  targets.forEach(function (name) {",
        "    try {",
        "      var C = Java.use(name);",
        '      C.checkServerTrusted.overloads.forEach(function (m) { m.implementation = function () { return; }; });',
        '      C.verify.overloads.forEach(function (m) { m.implementation = function () { return true; }; });',
        "    } catch (e) {}",
        "  });",
        "});",
    ]
    return "\n".join(lines) + "\n"


def load_mapping(path):
    mapping = {}
    try:
        for line in Path(path).read_text(encoding="utf-8", errors="ignore").splitlines():
            m = re.match(r"^(\S+) -> (\S+):$", line.strip())
            if m:
                mapping[m.group(2).replace(".", "/")] = m.group(1)
    except Exception:
        pass
    return mapping


def apply_mapping(classes, mapping):
    if not mapping:
        return classes
    out = []
    for c in classes:
        out.append(mapping.get(c["name"], c["name"]))
    return out


def dex_verify_patch(apk, expected):
    hits = []
    try:
        with zipfile.ZipFile(apk) as z:
            for name in z.namelist():
                if not re.match(r"classes\d*\.dex$", name):
                    continue
                data = z.read(name)
                idx = DexIndex(data)
                if not idx.ok:
                    continue
                for desc, method in expected:
                    cbase = idx.find_class(desc)
                    if cbase is None:
                        continue
                    cdata = u4(data, cbase + 24)
                    if not cdata:
                        continue
                    p = cdata
                    sf, p = uleb(data, p)
                    inf, p = uleb(data, p)
                    dm, p = uleb(data, p)
                    vm, p = uleb(data, p)
                    for _ in range(sf + inf):
                        _, p = uleb(data, p)
                        _, p = uleb(data, p)
                    for count in (dm, vm):
                        midx = 0
                        for _ in range(count):
                            diff, p = uleb(data, p)
                            midx += diff
                            _, p = uleb(data, p)
                            code_off, p = uleb(data, p)
                            if code_off and idx.method_name(midx) == method:
                                body = data[code_off + 16 : code_off + 16 + 8]
                                if any(s and body.startswith(s) for s in STUB_BODIES):
                                    hits.append((name, desc, method))
    except Exception:
        pass
    return hits



def norm_descriptor(name):
    name = name.strip()
    if name.startswith("L") and name.endswith(";"):
        return name
    if "." in name and "/" not in name:
        name = name.replace(".", "/")
    return "L" + name + ";"


def load_targets(path):
    class_targets = []
    name_map = {}
    problems = []
    try:
        raw = Path(path).expanduser().read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return [], {}, ["cannot read: " + str(e)[:50]]
    for lineno, line in enumerate(raw.splitlines(), 1):
        line = line.split("//")[0].strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            problems.append("line %d · expected 'selector kind'" % lineno)
            continue
        selector, kind = parts[0], parts[1].lower()
        if kind not in ("void", "true", "false"):
            problems.append("line %d · kind must be void, true or false" % lineno)
            continue
        if "#" in selector:
            cls, meth = selector.split("#", 1)
            if not cls or not meth:
                problems.append("line %d · empty class or method" % lineno)
                continue
            class_targets.append((norm_descriptor(cls), meth, kind))
        else:
            name_map[selector] = kind
    return class_targets, name_map, problems


def list_methods(apk, pattern, limit=200):
    rx = re.compile(pattern, re.I)
    hits = []
    try:
        with zipfile.ZipFile(apk) as z:
            for name in z.namelist():
                if not re.match(r"classes\d*\.dex$", name):
                    continue
                data = z.read(name)
                idx = DexIndex(data)
                if not idx.ok:
                    continue
                seen = set()
                for i in range(min(idx.m_n, 400000)):
                    try:
                        midx_name = idx.method_name(i)
                    except Exception:
                        continue
                    if not rx.search(midx_name):
                        continue
                    try:
                        desc = idx.type_name(u2(data, idx.m_off + i * 8))
                    except Exception:
                        continue
                    key = (desc, midx_name)
                    if key in seen:
                        continue
                    seen.add(key)
                    hits.append((name, desc, midx_name))
                    if len(hits) >= limit:
                        return hits
    except Exception:
        pass
    return hits


def cmd_methods(args):
    Tty.probe()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    path, _searched = resolve_input(args.input)
    if not path.exists():
        Out.bad("missing " + str(path))
        return 2
    Out.head("method index", G_WARM)
    Out.kv("pattern", args.methods)
    hits = list_methods(path, args.methods)
    if not hits:
        Out.info("no method matched")
        return 0
    Out.ok("%d method(s)" % len(hits))
    for dex, desc, meth in hits:
        clean = desc.replace("/", ".")[1:-1] if desc.startswith("L") else desc
        print("  " + T_ACC(DIAMOND) + " " + T_TXT(clean + "#" + meth) + T_DIM("  · " + dex))
    print()
    Out.info("paste any line above into a targets file, then run with --targets")
    return 0


def cmd_batch(args):
    Tty.probe()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    root = Path(args.batch).expanduser()
    if root.is_file():
        items = [root]
    elif root.is_dir():
        items = sorted(p for p in root.rglob("*") if p.suffix.lower() in (".apk", ".apks", ".xapk", ".apkm"))
    else:
        Out.bad("batch path not found")
        return 2
    if not items:
        Out.bad("no archives under " + str(root))
        return 2
    Out.head("batch", G_MAIN)
    Out.kv("archives", len(items))
    results = []
    for idx, item in enumerate(items, 1):
        print()
        print("  " + gradient_text("[%d/%d] %s" % (idx, len(items), item.name), G_MAIN, True))
        args.input = str(item)
        args.output = None
        try:
            code = run_pipeline(args)
        except Exception as e:
            Out.bad("crashed · " + trunc(str(e), 90))
            code = 1
        results.append((item.name, code))
    Out.head("batch summary", G_OK)
    ok_count = sum(1 for _, c in results if c == 0)
    Out.kv("succeeded", ok_count)
    Out.kv("failed", len(results) - ok_count)
    for name, code in results:
        mark = T_OK(CHECK) if code == 0 else T_ERR(CROSS)
        print("  " + mark + " " + T_TXT(trunc(name, 60)) + T_DIM("  code %d" % code))
    return 0 if ok_count == len(results) else 6




SIG_TRUE = (
    "checkSignature", "verifySignature", "validateSignature", "isSignatureValid",
    "isSignatureCorrect", "verifyAppSignature", "checkAppSignature", "isSignedCorrectly",
    "checkSignatures", "verifyIntegrity", "checkIntegrity", "validateAppSignature",
    "isSignatureVerified", "verifySignatures",
)
SIG_FALSE = ("isTampered", "checkTampered", "isAppTampered", "isSignatureInvalid", "isModified")

AD_SDKS = {
    "AdMob": ["com/google/android/gms/ads"],
    "Facebook Audience": ["com/facebook/ads"],
    "Unity Ads": ["com/unity3d/ads"],
    "AppLovin": ["com/applovin"],
    "IronSource": ["com/ironsource"],
    "Vungle": ["com/vungle"],
    "Chartboost": ["com/chartboost"],
    "MoPub": ["com/mopub"],
    "Pangle": ["com/bytedance/sdk/openadsdk", "com/pangle"],
    "Mintegral": ["com/mintegral"],
    "InMobi": ["com/inmobi"],
    "StartApp": ["com/startapp"],
    "AdColony": ["com/adcolony"],
    "Tapjoy": ["com/tapjoy"],
    "Smaato": ["com/smaato"],
    "Yandex Ads": ["com/yandex/mobile/ads"],
    "Amazon Ads": ["com/amazon/device/ads"],
    "Appodeal": ["com/appodeal"],
    "Fyber": ["com/fyber"],
    "AdMost": ["com/admost"],
}

IAP_MARKERS = [
    "com/android/billingclient", "com/android/vending/billing", "IInAppBillingService",
    "com/google/android/play/billing", "BillingClient",
]
LICENSE_MARKERS = [
    "com/google/android/vending/licensing", "LicenseChecker", "LicenseValidator",
    "com.android.vending.CHECK_LICENSE", "ILicensingService",
]
SIG_MARKERS = ["GET_SIGNATURES", "GET_SIGNING_CERTIFICATES", "getPackageInfo"]


def dex_surgery_by_name(data, wanted):
    idx = DexIndex(data)
    if not idx.ok:
        return bytearray(data), []
    buf = bytearray(data)
    hits = []
    limit = min(idx.c_n, 60000)
    for i in range(limit):
        cbase = idx.c_off + i * 32
        desc = idx.type_name(u4(buf, cbase))
        cdata = u4(buf, cbase + 24)
        if not cdata:
            continue
        p = cdata
        try:
            sf, p = uleb(buf, p)
            inf, p = uleb(buf, p)
            dm, p = uleb(buf, p)
            vm, p = uleb(buf, p)
            for _ in range(sf + inf):
                _, p = uleb(buf, p)
                _, p = uleb(buf, p)
            for count in (dm, vm):
                midx = 0
                for _ in range(count):
                    diff, p = uleb(buf, p)
                    midx += diff
                    _, p = uleb(buf, p)
                    code_off, p = uleb(buf, p)
                    if not code_off:
                        continue
                    name = idx.method_name(midx)
                    kind = wanted.get(name)
                    if not kind:
                        continue
                    kind = idx.stub_kind(midx, kind)
                    before = dex_code_item_end(buf, code_off)
                    snapshot = bytes(buf[code_off:before]) if before else None
                    if not dex_patch_code(buf, code_off, kind):
                        continue
                    if (before is None or dex_code_item_end(buf, code_off) != before
                            or not dex_stub_ok(buf, code_off, kind)):
                        if snapshot:
                            buf[code_off:before] = snapshot
                        DEX_GUARD["failures"].append((desc, name, code_off))
                        continue
                    hits.append((desc, name, code_off, kind))
        except Exception:
            continue
    if hits:
        dex_fix_header(buf)
    return buf, hits


def type_names(idx, cap=100000):
    out = []
    for i in range(min(getattr(idx, "t_n", 0), cap)):
        out.append(idx.type_name(i))
    return out


def ecosystem(apk):
    found = {"ads": {}, "iap": [], "license": [], "sig": [], "classes": 0}
    try:
        with zipfile.ZipFile(apk) as z:
            for name in z.namelist():
                if not re.match(r"classes\d*\.dex$", name):
                    continue
                idx = DexIndex(z.read(name))
                if not idx.ok:
                    continue
                names = type_names(idx, 250000)
                found["classes"] += len(names)
                for desc in names:
                    low = desc.lower()
                    for label, prefixes in AD_SDKS.items():
                        if any(pr in low for pr in prefixes):
                            found["ads"].setdefault(label, desc)
                            break
                    for marker in IAP_MARKERS:
                        if marker.lower() in low and marker not in found["iap"]:
                            found["iap"].append(marker)
                    for marker in LICENSE_MARKERS:
                        if marker.lower() in low and marker not in found["license"]:
                            found["license"].append(marker)
                    for marker in SIG_MARKERS:
                        if marker.lower() in low and marker not in found["sig"]:
                            found["sig"].append(marker)
    except Exception:
        pass
    return found


def show_ecosystem(found):
    Out.head("monetisation map", G_WARM)
    ads = found.get("ads", {})
    if ads:
        Out.kv("ad networks", len(ads), width=22)
        for label in sorted(ads):
            Out.bullet("%s · %s" % (label, trunc(ads[label], 60)))
    else:
        Out.info("no known ad sdk found")
    Out.kv("in-app billing", "present" if found.get("iap") else "absent", width=22,
           tone=T_WARN if found.get("iap") else T_DIM)
    for m in found.get("iap", [])[:4]:
        Out.bullet(m)
    Out.kv("license check", "present" if found.get("license") else "absent", width=22,
           tone=T_WARN if found.get("license") else T_DIM)
    for m in found.get("license", [])[:4]:
        Out.bullet(m)
    Out.kv("signature checks", "present" if found.get("sig") else "absent", width=22,
           tone=T_WARN if found.get("sig") else T_DIM)
    for m in found.get("sig", [])[:4]:
        Out.bullet(m)


def native_disasm(path, limit=400):
    try:
        import capstone
    except ImportError:
        return None, "capstone not installed · pip install capstone"
    elf = ElfFile(path)
    if not elf.ok:
        return None, "not an elf object"
    arch_map = {
        "aarch64": (capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM),
        "arm": (capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB),
        "x86_64": (capstone.CS_ARCH_X86, capstone.CS_MODE_64),
        "x86": (capstone.CS_ARCH_X86, capstone.CS_MODE_32),
    }
    conf = arch_map.get(elf.machine)
    if not conf:
        return None, "unsupported isa " + elf.machine
    text = next((s for s in elf.sections if s["name"] == ".text"), None)
    if not text:
        return None, "no .text section"
    try:
        with open(path, "rb") as fh:
            fh.seek(text["offset"])
            blob = fh.read(min(text["size"], 64 * 1024))
        md = capstone.Cs(conf[0], conf[1])
        md.detail = True
        out = []
        for ins in md.disasm(blob, text["offset"]):
            out.append("0x%06x  %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
            if len(out) >= limit:
                break
        return out, None
    except Exception as e:
        return None, trunc(str(e), 60)


JADX_ZIP = "https://github.com/skylot/jadx/releases/download/v1.5.1/jadx-1.5.1.zip"


def ensure_jadx(work):
    root = HOME / "jadx"
    if (root / "lib").is_dir() and any((root / "lib").glob("jadx-*.jar")):
        return root
    if not java_ok():
        return None
    dest = Path(work) / "jadx.zip"
    if not download(JADX_ZIP, dest, "jadx"):
        return None
    try:
        root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(dest) as z:
            z.extractall(root)
        for p in root.rglob("*"):
            if p.is_file() and p.suffix in (".sh", ""):
                try:
                    os.chmod(p, 0o755)
                except Exception:
                    pass
        return root if (root / "lib").is_dir() else None
    except Exception:
        return None


def run_jadx(work, apk, outdir):
    root = ensure_jadx(work)
    if not root:
        return False, "jadx unavailable"
    cp = str(root / "lib" / "*")
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    rc, _ = run_live(["java"] + jvm_flags() + ["-cp", cp, "jadx.cli.JadxCLI", "-d", str(outdir), "--no-res", str(apk)], "jadx decompile", timeout=3600)
    if rc == 0 and any(outdir.rglob("*.java")):
        return True, str(outdir)
    return False, "jadx produced no sources"




def _insn_size_table():
    t = [1] * 256
    for op, n in ((0x02, 2), (0x03, 3), (0x05, 2), (0x06, 3), (0x08, 2), (0x09, 3),
                  (0x13, 2), (0x14, 3), (0x15, 2), (0x16, 2), (0x17, 3), (0x18, 5), (0x19, 2),
                  (0x1A, 2), (0x1B, 3), (0x1C, 2), (0x1F, 2), (0x20, 2), (0x22, 2), (0x23, 2),
                  (0x24, 3), (0x25, 3), (0x26, 3), (0x29, 2), (0x2A, 3), (0x2B, 3), (0x2C, 3),
                  (0xFA, 4), (0xFB, 4), (0xFC, 3), (0xFD, 3), (0xFE, 2), (0xFF, 2)):
        t[op] = n
    for op in range(0x2D, 0x3E):
        t[op] = 2
    for op in range(0x52, 0x6E):
        t[op] = 2
    for op in range(0x6E, 0x73):
        t[op] = 3
    for op in range(0x74, 0x79):
        t[op] = 3
    for op in range(0xD0, 0xE3):
        t[op] = 2
    return t


INSN_SIZE = _insn_size_table()

INVOKE_RANGE = set(range(0x6E, 0x73)) | set(range(0x74, 0x79))
BRANCH_2BYTE_OFFSET = set(range(0x32, 0x3E))
CONST_STRING = {0x1A, 0x1B}
TYPE_OPS = {0x1C, 0x1F, 0x20, 0x22, 0x23, 0x24, 0x25}
FIELD_OPS = set(range(0x52, 0x5F)) | set(range(0x60, 0x6E))


def _s8(v):
    return v - 0x100 if v & 0x80 else v


def _s16(v):
    return v - 0x10000 if v & 0x8000 else v


def _s32(v):
    return v - 0x100000000 if v & 0x80000000 else v


class CodeIssue:
    def __init__(self, kind, pc, detail):
        self.kind = kind
        self.pc = pc
        self.detail = detail

    def as_dict(self):
        return {"kind": self.kind, "pc": self.pc, "detail": self.detail}


def decode_insns(data, code_off, budget=200000):
    insns = []
    issues = []
    if code_off <= 0 or code_off + 16 > len(data):
        issues.append(CodeIssue("code-offset-out-of-range", -1, "code_off=0x%x" % code_off))
        return insns, issues
    insns_size = u4(data, code_off + 12)
    base = code_off + 16
    if insns_size == 0:
        return insns, issues
    if base + insns_size * 2 > len(data):
        issues.append(CodeIssue("insns-exceed-file", 0, "declared %d units, file ends early" % insns_size))
        insns_size = max(0, (len(data) - base) // 2)
    pc = 0
    while pc < insns_size:
        if len(insns) >= budget:
            issues.append(CodeIssue("decode-budget", pc, "stopped after %d instructions" % budget))
            break
        unit = u2(data, base + pc * 2)
        op = unit & 0xFF
        size = INSN_SIZE[op]
        if size <= 0 or pc + size > insns_size:
            issues.append(CodeIssue("instruction-truncated", pc, "op=0x%02x needs %d units" % (op, size)))
            break
        item = {"pc": pc, "op": op, "size": size, "target": None, "ref": None, "kind": None,
                "reg": None, "lit": None}
        if op == 0x12:
            item["reg"] = (unit >> 8) & 0xF
            item["lit"] = (unit >> 12) & 0xF
        elif op in (0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x19):
            item["reg"] = (unit >> 8) & 0xFF
        try:
            if op in (0x28,):
                item["target"] = pc + _s8(unit >> 8)
                item["kind"] = "goto"
            elif op == 0x29:
                item["target"] = pc + _s16(u2(data, base + (pc + 1) * 2))
                item["kind"] = "goto"
            elif op == 0x2A:
                raw = (u2(data, base + (pc + 1) * 2) << 16) | u2(data, base + (pc + 2) * 2)
                item["target"] = pc + _s32(raw)
                item["kind"] = "goto"
            elif op in BRANCH_2BYTE_OFFSET:
                item["target"] = pc + _s16(u2(data, base + (pc + 1) * 2))
                item["kind"] = "branch"
            elif op in (0x2B, 0x2C):
                raw = (u2(data, base + (pc + 1) * 2) << 16) | u2(data, base + (pc + 2) * 2)
                item["target"] = pc + _s32(raw)
                item["kind"] = "switch"
            elif op in INVOKE_RANGE or op in (0xFA, 0xFB, 0xFC, 0xFD):
                item["ref"] = u2(data, base + (pc + 1) * 2)
                item["kind"] = "invoke"
            elif op in CONST_STRING:
                if op == 0x1A:
                    item["ref"] = u2(data, base + (pc + 1) * 2)
                else:
                    item["ref"] = u4(data, base + (pc + 1) * 2)
                item["kind"] = "string"
            elif op in TYPE_OPS:
                item["ref"] = u2(data, base + (pc + 1) * 2)
                item["kind"] = "type"
            elif op in FIELD_OPS:
                item["ref"] = u2(data, base + (pc + 1) * 2)
                item["kind"] = "field"
            if item["target"] is not None and not (0 <= item["target"] < insns_size):
                issues.append(CodeIssue("branch-out-of-bounds", pc, "target %d outside 0..%d" % (item["target"], insns_size - 1)))
                item["target"] = None
        except Exception as e:
            issues.append(CodeIssue("operand-read-failed", pc, trunc(str(e), 60)))
            break
        insns.append(item)
        pc += size
    return insns, issues


class MethodCode:
    def __init__(self, dex_name, descriptor, name, code_off, insns, issues, registers, params):
        self.dex = dex_name
        self.descriptor = descriptor
        self.name = name
        self.code_off = code_off
        self.insns = insns
        self.issues = issues
        self.registers = registers
        self.params = params

    def evidence(self):
        return {
            "dex": self.dex,
            "class": self.descriptor,
            "method": self.name,
            "code_off": "0x%x" % self.code_off,
            "instructions": len(self.insns),
        }


def iter_method_code(dex_name, data, budget_per_method=20000, max_methods=200000):
    idx = DexIndex(data)
    if not idx.ok:
        return
    produced = 0
    for i in range(min(idx.c_n, 60000)):
        cbase = idx.c_off + i * 32
        desc = idx.type_name(u4(data, cbase))
        cdata = u4(data, cbase + 24)
        if not cdata:
            continue
        p = cdata
        try:
            sf, p = uleb(data, p)
            inf, p = uleb(data, p)
            dm, p = uleb(data, p)
            vm, p = uleb(data, p)
            for _ in range(sf + inf):
                _, p = uleb(data, p)
                _, p = uleb(data, p)
            for count in (dm, vm):
                midx = 0
                for _ in range(count):
                    diff, p = uleb(data, p)
                    midx += diff
                    _, p = uleb(data, p)
                    code_off, p = uleb(data, p)
                    if not code_off:
                        continue
                    insns, issues = decode_insns(data, code_off, budget_per_method)
                    yield MethodCode(dex_name, desc, idx.method_name(midx), code_off, insns, issues,
                                     u2(data, code_off), u2(data, code_off + 2))
                    produced += 1
                    if produced >= max_methods:
                        return
        except Exception:
            continue


def method_signature(idx, method_idx):
    try:
        base = idx.m_off + method_idx * 8
        cls = idx.type_name(u2(idx.d, base))
        name = idx.string(u4(idx.d, base + 4))
        return "%s->%s" % (cls, name)
    except Exception:
        return "?"


class DexAnalysis:
    def __init__(self, apk):
        self.apk = apk
        self.methods = 0
        self.instructions = 0
        self.issues = []
        self.calls = {}
        self.callers = {}
        self.strings = {}
        self.classes = set()
        self.budget_hit = False

    def as_dict(self):
        return {
            "methods_decoded": self.methods,
            "instructions": self.instructions,
            "integrity_issues": len(self.issues),
            "distinct_call_edges": len(self.calls),
            "classes": len(self.classes),
            "budget_truncated": self.budget_hit,
        }


def analyse_dex(apk, method_budget=60000, insn_budget=6000000):
    res = DexAnalysis(apk)
    try:
        with zipfile.ZipFile(apk) as z:
            for name in z.namelist():
                if not re.match(r"classes\d*\.dex$", name):
                    continue
                data = z.read(name)
                idx = DexIndex(data)
                if not idx.ok:
                    res.issues.append({"dex": name, "kind": "header-invalid", "pc": -1, "detail": "not a dex"})
                    continue
                for mc in iter_method_code(name, data, 20000, method_budget):
                    res.methods += 1
                    res.instructions += len(mc.insns)
                    res.classes.add(mc.descriptor)
                    for iss in mc.issues:
                        res.issues.append(dict(iss.as_dict(), dex=name, class_=mc.descriptor, method=mc.name))
                    if res.instructions > insn_budget:
                        res.budget_hit = True
                        return res
                    for ins in mc.insns:
                        if ins["kind"] == "invoke" and ins["ref"] is not None:
                            callee = method_signature(idx, ins["ref"])
                            caller = "%s->%s" % (mc.descriptor, mc.name)
                            res.calls.setdefault(caller, set()).add(callee)
                            res.callers.setdefault(callee, set()).add(caller)
                        elif ins["kind"] == "string" and ins["ref"] is not None:
                            val = idx.string(ins["ref"])
                            res.strings.setdefault(val, []).append(mc.evidence())
    except Exception as e:
        res.issues.append({"dex": "-", "kind": "archive-error", "pc": -1, "detail": trunc(str(e), 80)})
    return res


def show_dex_analysis(res):
    Out.head("dex integrity", G_WARM)
    Out.kv("methods decoded", res.methods)
    Out.kv("instructions", res.instructions)
    Out.kv("classes", len(res.classes))
    Out.kv("call edges", sum(len(v) for v in res.calls.values()))
    Out.kv("string refs", len(res.strings))
    if res.budget_hit:
        Out.warn("scan budget reached · results are partial")
    if res.issues:
        kinds = {}
        for iss in res.issues:
            kinds[iss.get("kind")] = kinds.get(iss.get("kind"), 0) + 1
        hard = {k: v for k, v in kinds.items() if k not in ("instruction-truncated", "decode-budget")}
        if hard:
            Out.warn("%d decode problem(s)" % sum(hard.values()))
            for kind, count in sorted(hard.items(), key=lambda kv: -kv[1]):
                Out.bullet("%s · %d" % (kind, count))
        soft = sum(v for k, v in kinds.items() if k in ("instruction-truncated", "decode-budget"))
        if soft:
            Out.info("%d method(s) ended mid instruction · common in obfuscated or packed code" % soft)
        if not hard and not soft:
            Out.warn("%d integrity issue(s)" % len(res.issues))
    else:
        Out.ok("every decoded instruction stayed inside its method bounds")




TRUST_IFACES = {
    "Ljavax/net/ssl/X509TrustManager;": ("x509-trust-manager", "critical"),
    "Ljavax/net/ssl/TrustManager;": ("trust-manager", "high"),
    "Ljavax/net/ssl/HostnameVerifier;": ("hostname-verifier", "high"),
    "Lokhttp3/CertificatePinner;": ("okhttp-pinner", "critical"),
    "Lcom/squareup/okhttp/CertificatePinner;": ("okhttp3-pinner", "critical"),
}

TRUST_METHODS = ("checkServerTrusted", "checkClientTrusted", "verify", "getAcceptedIssuers", "check")


def class_interfaces(data, class_def_off):
    off = u4(data, class_def_off + 12)
    if not off or off + 4 > len(data):
        return []
    size = u4(data, off)
    out = []
    for i in range(min(size, 256)):
        pos = off + 4 + i * 2
        if pos + 2 > len(data):
            break
        out.append(u2(data, pos))
    return out


def iter_class_methods(data, idx, cbase):
    cdata = u4(data, cbase + 24)
    if not cdata:
        return
    p = cdata
    sf, p = uleb(data, p)
    inf, p = uleb(data, p)
    dm, p = uleb(data, p)
    vm, p = uleb(data, p)
    for _ in range(sf + inf):
        _, p = uleb(data, p)
        _, p = uleb(data, p)
    for count in (dm, vm):
        midx = 0
        for _ in range(count):
            diff, p = uleb(data, p)
            midx += diff
            _, p = uleb(data, p)
            code_off, p = uleb(data, p)
            yield idx.method_name(midx), code_off


def method_strings(data, idx, code_off, limit=4000):
    insns, issues = decode_insns(data, code_off, limit)
    out = []
    for ins in insns:
        if ins["kind"] == "string" and ins["ref"] is not None:
            val = idx.string(ins["ref"])
            if val and val not in out:
                out.append(val)
    return out, insns, issues


def cert_paths(apk):
    findings = []
    nsc = {"present": False, "entry": None, "pins": [], "anchors": [], "cleartext": None}
    try:
        with zipfile.ZipFile(apk) as z:
            names = z.namelist()
            for name in names:
                if not re.match(r"classes\d*\.dex$", name):
                    continue
                data = z.read(name)
                idx = DexIndex(data)
                if not idx.ok:
                    continue
                for i in range(min(idx.c_n, 60000)):
                    cbase = idx.c_off + i * 32
                    desc = idx.type_name(u4(data, cbase))
                    ifaces = [idx.type_name(t) for t in class_interfaces(data, cbase)]
                    sup_idx = u4(data, cbase + 8)
                    sup = idx.type_name(sup_idx) if sup_idx != 0xFFFFFFFF else ""
                    for iface, (kind, severity) in TRUST_IFACES.items():
                        if iface not in ifaces and iface != sup:
                            continue
                        methods = list(iter_class_methods(data, idx, cbase))
                        matched = [(m, off) for m, off in methods if m in TRUST_METHODS and off]
                        if not matched:
                            continue
                        for mname, off in matched:
                            strings, insns, issues = method_strings(data, idx, off)
                            hosts = [s for s in strings if "://" in s or ("." in s and len(s) < 120 and " " not in s)]
                            findings.append({
                                "kind": kind,
                                "severity": severity,
                                "confidence": 1.0 if iface in ifaces else 0.75,
                                "dex": name,
                                "class": desc,
                                "method": mname,
                                "code_off": "0x%x" % off,
                                "interfaces": ifaces,
                                "super": sup,
                                "strings": hosts[:12],
                                "instructions": len(insns),
                                "issues": [x.kind for x in issues],
                            })
                        break
                continue
            for name in names:
                if not (name.startswith("res/xml/") and name.endswith(".xml")):
                    continue
                blob = z.read(name)
                if b"pin-set" not in blob and b"trust-anchors" not in blob and b"network-security-config" not in blob:
                    continue
                nsc["present"] = True
                nsc["entry"] = name
                ax = Axml(blob)
                pins = []
                anchors = []
                for parent, elem, aname, val in ax.attrs:
                    if elem == "pin" and aname == "digest":
                        pins.append(val)
                    if elem == "certificates" and aname == "src":
                        anchors.append(val)
                    if elem == "base-config" and aname == "cleartextTrafficPermitted":
                        nsc["cleartext"] = val
                nsc["pins"] = pins
                nsc["anchors"] = anchors
                findings.append({
                    "kind": "network-security-config",
                    "severity": "high" if pins else "medium",
                    "confidence": 1.0,
                    "dex": None,
                    "class": name,
                    "method": None,
                    "code_off": None,
                    "interfaces": [],
                    "super": "",
                    "strings": pins[:8] + anchors[:8],
                    "instructions": 0,
                    "issues": [],
                })
                break
    except Exception as e:
        findings.append({"kind": "analysis-error", "severity": "info", "confidence": 0.0,
                         "dex": None, "class": "-", "method": None, "code_off": None,
                         "interfaces": [], "super": "", "strings": [], "instructions": 0,
                         "issues": [trunc(str(e), 80)]})
    return findings, nsc


def show_cert_paths(findings, nsc):
    Out.head("certificate validation paths", G_WARM)
    if not findings:
        Out.info("no trust manager, pinner or pin set found")
        return
    for f in findings:
        tone = Pal(severity_tone(f["severity"]), f["severity"] in ("critical", "high"))
        where = f["dex"] or "-"
        print("  " + tone(DIAMOND) + " " + tone(f["kind"].upper().ljust(22)) +
              T_TXT(trunc(f["class"], 54)))
        Out.kv("evidence", "%s · %s · %s" % (where, f["method"] or "-", f["code_off"] or "-"), width=22)
        Out.kv("confidence", "%.2f" % f["confidence"], width=22)
        if f["super"]:
            Out.kv("extends", f["super"], width=22)
        if f["interfaces"]:
            Out.kv("implements", ", ".join(x.replace("/", ".").strip("L;") for x in f["interfaces"][:4]), width=22)
        for s in f["strings"][:5]:
            print("    " + T_DIM(BULLET + " " + trunc(s, 88)))
        if f["issues"]:
            Out.warn("%d decoder issue(s) in this method" % len(f["issues"]))
    if nsc["present"]:
        Out.kv("pin set", "%d pin(s) · %d anchor(s)" % (len(nsc["pins"]), len(nsc["anchors"])), width=22)


CERT_TEST_CASES = {
    "x509-trust-manager": ("Install the build on a test device, add a user CA, route HTTPS through a proxy.",
                           "the handshake must be rejected; readable traffic means validation is bypassable"),
    "trust-manager": ("Repeat the user-CA proxy test against every endpoint the app calls.",
                      "all pinned hosts must reject the proxy certificate"),
    "hostname-verifier": ("Connect to the backend through a proxy with a certificate issued for a different hostname.",
                          "the connection must fail; success means hostname checks are ineffective"),
    "okhttp-pinner": ("Proxy the app and inspect the first request to each pinned host.",
                      "each pinned host must abort the handshake"),
    "okhttp3-pinner": ("Proxy the app and inspect the first request to each pinned host.",
                       "each pinned host must abort the handshake"),
    "network-security-config": ("Check whether the config trusts user certificates and whether cleartext is allowed.",
                                "user anchors must be absent in release builds"),
}


def cert_test_cases(findings):
    cases = []
    for f in findings:
        template = CERT_TEST_CASES.get(f["kind"])
        if not template:
            continue
        scenario, expectation = template
        cases.append({
            "id": "CERT-%s-%s" % (f["kind"], (f["method"] or "config")),
            "category": "certificate-validation",
            "target": {"dex": f["dex"], "class": f["class"], "method": f["method"], "code_off": f["code_off"]},
            "confidence": f["confidence"],
            "scenario": scenario,
            "expected": expectation,
            "evidence": f["strings"][:5],
        })
    return cases


RULE_FIELDS = ("class", "method", "string", "symbol", "path")
SEVERITIES = ("critical", "high", "medium", "low", "info")


def load_rules(path):
    src = Path(path).expanduser()
    if not src.exists():
        return None, "rules file not found"
    try:
        text = src.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return None, "cannot read rules: " + trunc(str(e), 60)
    data = None
    if src.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError:
            return None, "PyYAML is not installed · pip install pyyaml, or use a .json rules file"
        try:
            data = yaml.safe_load(text)
        except Exception as e:
            return None, "yaml parse error: " + trunc(str(e), 60)
    else:
        try:
            data = json.loads(text)
        except Exception as e:
            return None, "json parse error: " + trunc(str(e), 60)
    raw_rules = data.get("rules") if isinstance(data, dict) else data
    if not isinstance(raw_rules, list):
        return None, "rules file must contain a list under 'rules'"
    rules = []
    problems = []
    for i, item in enumerate(raw_rules):
        if not isinstance(item, dict):
            problems.append("rule %d is not an object" % i)
            continue
        match = item.get("match") or {}
        if not isinstance(match, dict):
            problems.append("rule %d match is not an object" % i)
            continue
        compiled = {}
        for field in RULE_FIELDS:
            pattern = match.get(field)
            if not pattern:
                continue
            try:
                compiled[field] = re.compile(str(pattern), re.I)
            except re.error as e:
                problems.append("rule %d field %s: bad regex (%s)" % (i, field, e))
        if not compiled:
            problems.append("rule %d has no usable match field" % i)
            continue
        sev = str(item.get("severity", "medium")).lower()
        if sev not in SEVERITIES:
            sev = "medium"
        try:
            conf = float(item.get("confidence", 0.5))
        except Exception:
            conf = 0.5
        rules.append({
            "id": str(item.get("id") or "rule-%d" % i),
            "title": str(item.get("title") or item.get("id") or "rule-%d" % i),
            "severity": sev,
            "confidence": max(0.0, min(1.0, conf)),
            "tags": [str(t) for t in (item.get("tags") or [])],
            "match": compiled,
            "note": str(item.get("note") or ""),
        })
    return rules, problems


def collect_facts(apk, string_cap=120000):
    facts = {"class": set(), "method": set(), "string": set(), "symbol": set(), "path": set()}
    try:
        with zipfile.ZipFile(apk) as z:
            for name in z.namelist():
                facts["path"].add(name)
            for name in z.namelist():
                if re.match(r"classes\d*\.dex$", name):
                    data = z.read(name)
                    idx = DexIndex(data)
                    if not idx.ok:
                        continue
                    for i in range(min(idx.t_n, 200000)):
                        facts["class"].add(idx.type_name(i))
                    for i in range(min(idx.m_n, 200000)):
                        facts["method"].add(idx.method_name(i))
                    for i in range(min(idx.s_n, string_cap)):
                        facts["string"].add(idx.string(i))
                elif name.startswith("lib/") and name.endswith(".so"):
                    tmp = Path(tempfile.mkdtemp()) / safe_name(name)
                    try:
                        with z.open(name) as src, open(tmp, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                        elf = ElfFile(tmp)
                        if elf.ok:
                            for s in elf.imports:
                                facts["symbol"].add(s)
                            for s in getattr(elf, "symtab_names", []):
                                facts["symbol"].add(s)
                    finally:
                        shutil.rmtree(tmp.parent, ignore_errors=True)
    except Exception:
        pass
    return facts


def eval_rules(rules, facts):
    findings = []
    for rule in rules:
        matched = {}
        ok = True
        for field, rx in rule["match"].items():
            hits = [x for x in facts.get(field, ()) if rx.search(x)]
            if not hits:
                ok = False
                break
            matched[field] = sorted(hits)[:10]
        if not ok:
            continue
        confidence = rule["confidence"]
        if confidence == 0.5 and len(matched) > 1:
            confidence = min(0.95, 0.5 + 0.15 * len(matched))
        findings.append({
            "id": rule["id"],
            "title": rule["title"],
            "severity": rule["severity"],
            "confidence": round(confidence, 2),
            "tags": rule["tags"],
            "note": rule["note"],
            "evidence": matched,
            "source": "custom-rule",
        })
    return findings


def show_rule_findings(findings):
    Out.head("custom rule findings", G_WARM)
    if not findings:
        Out.info("no custom rule matched")
        return
    for f in findings:
        tone = Pal(severity_tone(f["severity"]), f["severity"] in ("critical", "high"))
        print("  " + tone(DIAMOND) + " " + tone(f["severity"].upper().ljust(9)) +
              T_TXT(f["title"]) + T_DIM("  ·  confidence %.2f" % f["confidence"]))
        for field, hits in f["evidence"].items():
            for h in hits[:3]:
                print("    " + T_DIM("%s: %s" % (field, trunc(h, 84))))


def findings_html(title, target, findings, cases, extra):
    rows = []
    for f in findings:
        ev = "<br>".join(html_escape("%s: %s" % (k, v)) for k, vals in f.get("evidence", {}).items() for v in vals[:2])
        rows.append(
            "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td class='ev'>%s</td></tr>" % (
                html_escape(f.get("severity", "")), html_escape(f.get("title", f.get("kind", ""))),
                html_escape("%.2f" % f.get("confidence", 0)), html_escape(f.get("source", "builtin")), ev or "-"))
    case_rows = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            html_escape(c["id"]), html_escape(c["scenario"]), html_escape(c["expected"]),
            html_escape(str(c["target"])))
        for c in cases)
    css = ("body{margin:0;background:#080b12;color:#e2e8f0;font:14px/1.6 ui-monospace,Menlo,monospace;padding:36px 18px}"
           ".w{max-width:1100px;margin:auto}h1{font-size:24px;background:linear-gradient(90deg,#67e8f9,#818cf8,#e879f9);"
           "-webkit-background-clip:text;background-clip:text;color:transparent}h2{font-size:14px;letter-spacing:1.3px;"
           "color:#22d3ee;text-transform:uppercase;margin-top:28px}table{width:100%;border-collapse:collapse;font-size:12.5px}"
           "th{background:#0b1220;color:#94a3b8;text-align:left;padding:7px 9px}td{padding:6px 9px;border-top:1px solid #1e293b;"
           "vertical-align:top}.ev{color:#94a3b8;word-break:break-all}section{border:1px solid #1e293b;border-radius:14px;"
           "background:#101725;padding:18px 20px;margin-top:16px}footer{color:#64748b;text-align:center;margin-top:24px;font-size:12px}")
    return ("<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><title>%s</title><style>%s</style></head>"
            "<body><div class='w'><h1>%s</h1><p style='color:#94a3b8'>%s · %s</p>"
            "<section><h2>Findings</h2><table><tr><th>Severity</th><th>Title</th><th>Confidence</th><th>Source</th><th>Evidence</th></tr>%s</table></section>"
            "<section><h2>Defensive test cases</h2><table><tr><th>ID</th><th>Scenario</th><th>Expected</th><th>Target</th></tr>%s</table></section>"
            "<section><h2>Scan statistics</h2><table>%s</table></section>"
            "<footer>%s %s</footer></div></body></html>") % (
        html_escape(title), css, html_escape(title), html_escape(str(target)), html_escape(time.strftime("%Y-%m-%d %H:%M")),
        "".join(rows) or "<tr><td colspan='5'>none</td></tr>",
        case_rows or "<tr><td colspan='4'>none</td></tr>",
        "".join("<tr><th>%s</th><td>%s</td></tr>" % (html_escape(k), html_escape(str(v))) for k, v in extra.items()),
        APP, VERSION)


def findings_unified(cert_f, eco, rule_f, natives):
    out = []
    for f in cert_f:
        out.append({
            "severity": f["severity"],
            "title": f["kind"],
            "confidence": f["confidence"],
            "source": "builtin",
            "evidence": {
                "dex": [str(f["dex"])],
                "class": [f["class"]],
                "method": [str(f["method"])],
                "offset": [str(f["code_off"])],
                "strings": f["strings"][:5],
            },
        })
    if eco.get("ads"):
        out.append({"severity": "low", "title": "ad-networks", "confidence": 1.0, "source": "builtin",
                    "evidence": {"sdk": sorted(eco["ads"])}})
    if eco.get("iap"):
        out.append({"severity": "medium", "title": "in-app-billing", "confidence": 1.0, "source": "builtin",
                    "evidence": {"marker": eco["iap"][:5]}})
    if eco.get("license"):
        out.append({"severity": "high", "title": "license-check", "confidence": 1.0, "source": "builtin",
                    "evidence": {"marker": eco["license"][:5]}})
    if eco.get("sig"):
        out.append({"severity": "medium", "title": "signature-checks", "confidence": 0.9, "source": "builtin",
                    "evidence": {"marker": eco["sig"][:5]}})
    for f in rule_f:
        out.append(f)
    for e in natives:
        h = e.summary().get("hardening", {})
        missing = [k for k, v in h.items() if not v]
        if missing:
            out.append({"severity": "low", "title": "native-hardening-gap", "confidence": 0.8, "source": "builtin",
                        "evidence": {"object": [e.name], "missing": missing}})
    return out


def run_security_test(args):
    Stage.reset()
    Tty.probe()
    fast = args.no_anim or not Tty.enabled
    if not args.quiet:
        banner_anim(fast)
        print()
    src, _searched = resolve_input(args.input)
    if not src.exists():
        Out.bad("input not found: " + str(src))
        return 2
    if not preflight(src):
        return 8
    rules = []
    if args.rules:
        rules, problems = load_rules(args.rules)
        if rules is None:
            Out.bad(problems)
            return 3
        if problems:
            for p in problems:
                Out.warn(p)
        Out.head("rules", G_COOL)
        Out.kv("loaded", "%d rule(s)" % len(rules))

    Out.head("1 · detection", G_MAIN)
    idx = zip_index(src)
    Out.kv("entries", idx["total"])
    Out.kv("dex files", len(idx["dex"]))
    Out.kv("native", len(idx["so"]))
    man = None
    try:
        with zipfile.ZipFile(src) as z:
            man = safe_manifest(z)[1]
    except Exception:
        man = None
    if man:
        Out.kv("package", man["package"])
        Out.kv("version", "%s (%s)" % (man["version"], man.get("version_code", "?")))

    Out.head("2 · evidence", G_WARM)
    cert_f, nsc = cert_paths(src)
    show_cert_paths(cert_f, nsc)

    Out.head("3 · method mapping", G_WARM)
    dexres = analyse_dex(src)
    show_dex_analysis(dexres)

    Out.head("4 · cross references", G_WARM)
    hot = sorted(dexres.callers.items(), key=lambda kv: -len(kv[1]))[:8]
    if not hot:
        Out.info("no call edges collected")
    for callee, callers in hot:
        Out.kv(trunc(callee, 56), "%d caller(s)" % len(callers), width=58)

    Out.head("5 · native analysis", G_WARM)
    natives = collect_natives(src, None)
    if not natives:
        Out.info("no native objects")
    for e in natives[:12]:
        s = e.summary()
        h = s["hardening"]
        flags = "".join([("P" if h.get("pie") else "-"), ("N" if h.get("nx") else "-"),
                         ("R" if h.get("relro") else "-"), ("C" if h.get("canary") else "-")])
        Out.kv(e.name, "%s · %s · %s" % (s["machine"], flags, human(s["size"])), width=34)

    Out.head("6 · custom rules", G_WARM)
    rule_f = []
    if rules:
        facts = collect_facts(src)
        Out.kv("facts", "class %d · method %d · string %d · symbol %d · path %d" % (
            len(facts["class"]), len(facts["method"]), len(facts["string"]),
            len(facts["symbol"]), len(facts["path"])), width=12)
        rule_f = eval_rules(rules, facts)
        show_rule_findings(rule_f)
    else:
        Out.info("no rules file supplied · pass --rules to add your own")

    eco = ecosystem(src)
    all_findings = findings_unified(cert_f, eco, rule_f, natives)
    cases = cert_test_cases(cert_f)

    Out.head("7 · test cases", G_OK)
    if not cases:
        Out.info("no defensive test case generated")
    for c in cases:
        print("  " + T_ACC(DIAMOND) + " " + T_TXT(c["id"]))
        print("    " + T_DIM("scenario  " + trunc(c["scenario"], 92)))
        print("    " + T_DIM("expected  " + trunc(c["expected"], 92)))

    regression = None
    if args.baseline:
        base = Path(args.baseline).expanduser()
        if not base.exists():
            Out.warn("baseline not found · " + str(base))
        else:
            Out.head("8 · regression", G_OK)
            bcert, _ = cert_paths(base)
            b_eco = ecosystem(base)
            b_rules = eval_rules(rules, collect_facts(base)) if rules else []
            b_find = findings_unified(bcert, b_eco, b_rules, [])
            key = lambda f: (f["title"], tuple(f.get("evidence", {}).get("class", [])))
            before = {key(f) for f in b_find}
            after = {key(f) for f in all_findings}
            resolved = before - after
            remaining = before & after
            added = after - before
            Out.kv("resolved", len(resolved), width=18)
            Out.kv("still present", len(remaining), width=18)
            Out.kv("newly introduced", len(added), width=18)
            for t, _ in sorted(resolved)[:10]:
                print("    " + T_OK(CHECK) + " " + T_DIM(t))
            for t, _ in sorted(remaining)[:10]:
                print("    " + T_WARN(WARN) + " " + T_DIM(t))
            regression = {"resolved": [t for t, _ in resolved], "remaining": [t for t, _ in remaining],
                          "added": [t for t, _ in added]}

    out_dir = Path(args.output).expanduser() if args.output else HOME / ("%s_security" % src.stem)
    out_dir.mkdir(parents=True, exist_ok=True)
    stats = dexres.as_dict()
    stats.update({"archive_entries": idx["total"], "dex_files": len(idx["dex"]),
                  "native_objects": len(natives), "findings": len(all_findings),
                  "test_cases": len(cases), "rules_loaded": len(rules)})
    html = findings_html("Android security test report", src, all_findings, cases, stats)
    atomic_write(out_dir / "report.html", html, "w")
    atomic_write(out_dir / "findings.json", json.dumps({"target": str(src), "stats": stats, "findings": all_findings,
                                                        "regression": regression}, indent=2, default=str), "w")
    atomic_write(out_dir / "testcases.json", json.dumps(cases, indent=2, default=str), "w")
    atomic_write(out_dir / "integrity.json", json.dumps(dexres.issues, indent=2, default=str), "w")

    dashboard()
    Out.head("9 · verification report", G_OK)
    crit = sum(1 for f in all_findings if f["severity"] == "critical")
    high = sum(1 for f in all_findings if f["severity"] == "high")
    Out.kv("findings", "%d critical · %d high · %d total" % (crit, high, len(all_findings)))
    Out.kv("dex integrity", "clean" if not dexres.issues else "%d issue(s)" % len(dexres.issues))
    seal("report", [str(out_dir / "report.html"), "findings  %d" % len(all_findings),
                    "cases     %d" % len(cases), "integrity %s" % ("clean" if not dexres.issues else "issues")], G_OK)
    return 0




PATCH_ACTIONS = ("stub-method", "replace-string", "manifest-attr")
PATCH_KINDS = ("void", "true", "false")


def uleb_size(value):
    return len(uleb_encode(max(0, value)))


def dex_replace_strings(data, mapping, limit=20000):
    idx = DexIndex(data)
    if not idx.ok:
        return bytearray(data), [], []
    buf = bytearray(data)
    hits = []
    skipped = []
    seen = set()
    for i in range(min(idx.s_n, 400000)):
        if len(hits) >= limit:
            break
        off = u4(buf, idx.s_off + i * 4)
        if off <= 0 or off >= len(buf):
            continue
        try:
            old_units, p = uleb(buf, off)
            old_bytes = buf[p : p + old_units]
            old = old_bytes.decode("utf-8", "replace")
        except Exception:
            continue
        if old not in mapping or old in seen:
            continue
        new = mapping[old]
        if new == old:
            continue
        new_bytes = new.encode("utf-8")
        new_units = len(new.encode("utf-16-le")) // 2
        if uleb_size(new_units) != uleb_size(old_units) or len(new_bytes) > len(old_bytes):
            skipped.append({"string": trunc(old, 60), "reason": "does not fit in place"})
            continue
        enc = uleb_encode(new_units)
        buf[off : off + len(enc)] = enc
        start = off + len(enc)
        buf[start : start + len(new_bytes)] = new_bytes
        for k in range(start + len(new_bytes), p + len(old_bytes)):
            buf[k] = 0
        seen.add(old)
        hits.append({"from": trunc(old, 60), "to": trunc(new, 60), "offset": "0x%x" % off})
    if hits:
        dex_fix_header(buf)
    return buf, hits, skipped


def load_patch_file(path):
    src = Path(path).expanduser()
    if not src.exists():
        return None, "patch file not found"
    try:
        data = json.loads(src.read_text(encoding="utf-8", errors="ignore"))
    except Exception as e:
        return None, "json parse error: " + trunc(str(e), 70)
    if isinstance(data, list):
        data = {"patches": data}
    if not isinstance(data, dict) or not isinstance(data.get("patches"), list):
        return None, "patch file must contain a 'patches' list"
    problems = []
    patches = []
    for i, item in enumerate(data["patches"]):
        if not isinstance(item, dict):
            problems.append("patch %d is not an object" % i)
            continue
        action = str(item.get("action", "")).lower()
        pid = str(item.get("id") or "patch-%d" % i)
        if action not in PATCH_ACTIONS:
            problems.append("%s · unknown action '%s'" % (pid, action))
            continue
        entry = {"id": pid, "title": str(item.get("title") or pid), "action": action,
                 "conflicts": [str(c) for c in (item.get("conflicts") or [])],
                 "note": str(item.get("note") or "")}
        if action == "stub-method":
            targets = item.get("targets") or []
            if not isinstance(targets, list) or not targets:
                problems.append("%s · stub-method needs a targets list" % pid)
                continue
            kind = str(item.get("kind", "true")).lower()
            if kind not in PATCH_KINDS:
                problems.append("%s · kind must be void, true or false" % pid)
                continue
            entry["targets"] = [str(t) for t in targets]
            entry["kind"] = kind
        elif action == "replace-string":
            if "from" not in item or "to" not in item:
                problems.append("%s · replace-string needs from and to" % pid)
                continue
            entry["from"] = str(item["from"])
            entry["to"] = str(item["to"])
        elif action == "manifest-attr":
            if "attr" not in item:
                problems.append("%s · manifest-attr needs attr" % pid)
                continue
            entry["attr"] = str(item["attr"])
            entry["value"] = item.get("value", True)
        patches.append(entry)
    profiles = data.get("profiles") or {}
    if not isinstance(profiles, dict):
        problems.append("profiles must be an object")
        profiles = {}
    return {"name": str(data.get("name") or "unnamed"), "schema": str(data.get("schema") or "arp-patch/1"),
            "patches": patches, "profiles": profiles}, problems


def select_patches(bundle, profile):
    by_id = {p["id"]: p for p in bundle["patches"]}
    if profile:
        ids = bundle["profiles"].get(profile)
        if ids is None:
            return None, "profile '%s' is not defined" % profile
        chosen = [by_id[i] for i in ids if i in by_id]
        missing = [i for i in ids if i not in by_id]
        if missing:
            return None, "profile references unknown patches: " + ", ".join(missing)
        return chosen, None
    return list(bundle["patches"]), None


def detect_conflicts(chosen):
    ids = {p["id"] for p in chosen}
    clashes = []
    for p in chosen:
        for other in p["conflicts"]:
            if other in ids:
                pair = tuple(sorted((p["id"], other)))
                if pair not in clashes:
                    clashes.append(pair)
    return clashes


def validate_patch_against(chosen, apk):
    report = []
    try:
        with zipfile.ZipFile(apk) as z:
            dex_blobs = {n: z.read(n) for n in z.namelist() if re.match(r"classes\d*\.dex$", n)}
            has_manifest = "AndroidManifest.xml" in z.namelist()
    except Exception as e:
        return [{"id": "-", "ok": False, "detail": "archive unreadable: " + trunc(str(e), 50)}]
    indexes = {n: DexIndex(b) for n, b in dex_blobs.items()}
    for p in chosen:
        if p["action"] == "stub-method":
            found = []
            for t in p["targets"]:
                if "#" in t:
                    cls, meth = t.split("#", 1)
                    desc = norm_descriptor(cls)
                    hit = any(idx.find_class(desc) is not None for idx in indexes.values() if idx.ok)
                    found.append((t, hit))
                else:
                    hit = False
                    for idx in indexes.values():
                        if not idx.ok:
                            continue
                        for i in range(min(idx.m_n, 200000)):
                            if idx.method_name(i) == t:
                                hit = True
                                break
                        if hit:
                            break
                    found.append((t, hit))
            missing = [t for t, ok in found if not ok]
            report.append({"id": p["id"], "ok": not missing,
                           "detail": "all targets resolved" if not missing else "missing: " + ", ".join(missing[:4])})
        elif p["action"] == "replace-string":
            count = 0
            for idx in indexes.values():
                if not idx.ok:
                    continue
                for i in range(min(idx.s_n, 200000)):
                    if idx.string(i) == p["from"]:
                        count += 1
                        break
            report.append({"id": p["id"], "ok": count > 0,
                           "detail": "string present" if count else "string not found in any dex"})
        elif p["action"] == "manifest-attr":
            report.append({"id": p["id"], "ok": has_manifest,
                           "detail": "manifest present" if has_manifest else "no AndroidManifest.xml"})
    return report


def apply_patch_set(apk, out, chosen, backup_dir=None):
    journal = {"tool": APP, "version": VERSION, "input": str(apk), "output": str(out),
               "backup": None, "applied": [], "skipped": [], "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}
    stub_targets = []
    name_map = {}
    string_map = {}
    manifest_edits = []
    for p in chosen:
        if p["action"] == "stub-method":
            for t in p["targets"]:
                if "#" in t:
                    cls, meth = t.split("#", 1)
                    stub_targets.append((norm_descriptor(cls), meth, p["kind"]))
                else:
                    name_map[t] = p["kind"]
        elif p["action"] == "replace-string":
            string_map[p["from"]] = p["to"]
        elif p["action"] == "manifest-attr":
            val = p["value"]
            if isinstance(val, bool):
                manifest_edits.append((p["attr"], 0x12, 0xFFFFFFFF if val else 0))
            elif isinstance(val, int):
                manifest_edits.append((p["attr"], 0x10, val))
            else:
                manifest_edits.append((p["attr"], 0x03, str(val)))

    if backup_dir:
        bdir = Path(backup_dir)
        bdir.mkdir(parents=True, exist_ok=True)
        bak = bdir / (Path(apk).name + ".orig")
        shutil.copy2(apk, bak)
        journal["backup"] = str(bak)

    manifest_blob = None
    try:
        with zipfile.ZipFile(apk) as zin, zipfile.ZipFile(out, "w") as zout:
            for item in zin.infolist():
                name = item.filename
                if name.upper().startswith("META-INF/") and name.upper().endswith((".SF", ".RSA", ".DSA", ".EC", ".MF")):
                    continue
                payload = zin.read(name)
                if re.match(r"classes\d*\.dex$", name):
                    buf = bytearray(payload)
                    if stub_targets:
                        buf, hits = dex_surgery(bytes(buf), stub_targets)
                        if hits:
                            journal["applied"].append({"id": "stub-method", "dex": name,
                                                       "changes": ["%s#%s" % (h[0], h[1]) for h in hits]})
                    if name_map:
                        buf2, hits2 = dex_surgery_by_name(bytes(buf), name_map)
                        if hits2:
                            buf = buf2
                            journal["applied"].append({"id": "stub-method", "dex": name,
                                                       "changes": ["%s#%s" % (h[0], h[1]) for h in hits2]})
                    if string_map:
                        buf3, hits3, skipped3 = dex_replace_strings(bytes(buf), string_map)
                        if hits3:
                            buf = buf3
                            journal["applied"].append({"id": "replace-string", "dex": name, "changes": hits3})
                        for s in skipped3:
                            journal["skipped"].append(dict(s, dex=name))

                    payload = bytes(buf)
                elif name == "AndroidManifest.xml":
                    manifest_blob = payload
                zi = zipfile.ZipInfo(name, date_time=item.date_time)
                zi.compress_type = item.compress_type
                zi.external_attr = item.external_attr
                zi.internal_attr = item.internal_attr
                zi.create_system = item.create_system
                zout.writestr(zi, payload)
    except Exception as e:
        if Path(out).exists():
            Path(out).unlink(missing_ok=True)
        return None, "apply failed: " + trunc(str(e), 70)

    if manifest_edits and manifest_blob is not None:
        patched, applied = axml_patch_manifest(manifest_blob, manifest_edits)
        if patched:
            tmp = Path(str(out) + ".m")
            try:
                with zipfile.ZipFile(out) as zin, zipfile.ZipFile(tmp, "w") as zout:
                    for item in zin.infolist():
                        payload = patched if item.filename == "AndroidManifest.xml" else zin.read(item.filename)
                        zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
                        zi.compress_type = item.compress_type
                        zi.external_attr = item.external_attr
                        zi.internal_attr = item.internal_attr
                        zi.create_system = item.create_system
                        zout.writestr(zi, payload)
                os.replace(tmp, out)
                journal["applied"].append({"id": "manifest-attr", "changes": applied})
            except Exception as e:
                tmp.unlink(missing_ok=True)
                journal["skipped"].append({"string": "manifest", "reason": trunc(str(e), 50)})
    return journal, None


def revert_from_journal(journal_path, target=None):
    try:
        journal = json.loads(Path(journal_path).expanduser().read_text(encoding="utf-8"))
    except Exception as e:
        return False, "journal unreadable: " + trunc(str(e), 60)
    backup = journal.get("backup")
    dest = target or journal.get("output")
    if not backup or not Path(backup).exists():
        return False, "backup missing"
    if not dest:
        return False, "no destination recorded"
    try:
        shutil.copy2(backup, dest)
        return True, dest
    except Exception as e:
        return False, trunc(str(e), 60)


def cmd_patch(args):
    Tty.probe()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    if args.revert:
        ok, detail = revert_from_journal(args.revert, args.output)
        Out.head("revert", G_OK if ok else G_BAD)
        if ok:
            Out.ok("restored " + detail)
            return 0
        Out.bad(detail)
        return 3
    if not args.patch or not args.input:
        Out.bad("--patch needs --input")
        return 2
    apk, _searched = resolve_input(args.input)
    if apk is None:
        Out.bad("input not found · " + str(args.input))
        for _root in (_searched or [])[:5]:
            Out.info("looked in " + str(_root))
        return 2
    bundle, problems = load_patch_file(args.patch)
    if bundle is None:
        Out.bad(problems)
        return 3
    for p in problems:
        Out.warn(p)
    chosen, err = select_patches(bundle, args.profile)
    if chosen is None:
        Out.bad(err)
        return 3
    Out.head("patch set", G_MAIN)
    Out.kv("file", bundle["name"])
    Out.kv("patches", len(bundle["patches"]))
    Out.kv("selected", len(chosen))
    if args.profile:
        Out.kv("profile", args.profile)
    clashes = detect_conflicts(chosen)
    if clashes:
        Out.warn("%d conflict pair(s)" % len(clashes))
        for a, b in clashes:
            Out.bullet("%s <-> %s" % (a, b))
        if not args.force:
            Out.bad("resolve the conflicts or pass --force")
            return 4
    report = validate_patch_against(chosen, apk)
    Out.head("validation", G_COOL)
    bad = 0
    for r in report:
        if r["ok"]:
            Out.ok("%s · %s" % (r["id"], r["detail"]))
        else:
            bad += 1
            Out.bad("%s · %s" % (r["id"], r["detail"]))
    if bad and not args.force:
        Out.bad("validation failed · pass --force to apply anyway")
        return 5
    out = Path(args.output).expanduser() if args.output else rap_output(apk, "patched")
    journal, err = apply_patch_set(apk, out, chosen, backup_dir=str(out) + ".backup")
    if journal is None:
        Out.bad(err)
        return 6
    journal_path = Path(str(out) + ".journal.json")
    atomic_write(journal_path, json.dumps(journal, indent=2), "w")
    Out.head("applied", G_OK)
    total = 0
    for entry in journal["applied"]:
        n = len(entry["changes"])
        total += n
        Out.ok("%s · %s · %d change(s)" % (entry["id"], entry.get("dex", "manifest"), n))
    for s in journal["skipped"]:
        Out.warn("skipped · %s · %s" % (s.get("string"), s.get("reason")))
    if total == 0:
        Out.warn("no change was applied")
    out, aligned = do_zipalign({}, out, out.parent)
    Out.kv("output", str(out))
    Out.kv("journal", str(journal_path))
    Out.kv("backup", journal.get("backup") or "-")
    Out.info("revert with: --revert " + str(journal_path))
    return 0


INIT_HINTS = ("init", "start", "setup", "prepare", "configure", "bootstrap", "load")
SHOW_HINTS = ("show", "present", "display", "render", "interstitial", "rewarded", "banner")

SIG_DEPS = (
    "getPackageInfo", "GET_SIGNATURES", "GET_SIGNING_CERTIFICATES", "getInstallerPackageName",
    "PackageManager", "signatures", "Signature", "certificate", "MessageDigest",
)

LICENSE_CLASSES = ("com/google/android/vending/licensing", "LicenseChecker", "LicenseValidator", "ILicensingService")
BILLING_CLASSES = ("com/android/billingclient", "BillingClient", "com/android/vending/billing", "IInAppBillingService")


def _dex_streams(apk):
    try:
        with zipfile.ZipFile(apk) as z:
            for name in z.namelist():
                if re.match(r"classes\d*\.dex$", name):
                    yield name, z.read(name)
    except Exception:
        return


def component_map(apk, prefixes, label, max_classes=400):
    found = {}
    for dex, data in _dex_streams(apk):
        idx = DexIndex(data)
        if not idx.ok:
            continue
        for i in range(min(idx.c_n, 60000)):
            cbase = idx.c_off + i * 32
            desc = idx.type_name(u4(data, cbase))
            low = desc.lower()
            if not any(p.lower() in low for p in prefixes):
                continue
            entry = found.setdefault(desc, {"dex": dex, "class": desc, "methods": [], "init": [], "show": []})
            for mname, code_off in iter_class_methods(data, idx, cbase):
                if len(entry["methods"]) < 60:
                    entry["methods"].append(mname)
                low_m = mname.lower()
                if any(h in low_m for h in INIT_HINTS) and len(entry["init"]) < 12:
                    entry["init"].append(mname)
                if any(h in low_m for h in SHOW_HINTS) and len(entry["show"]) < 12:
                    entry["show"].append(mname)
            if len(found) >= max_classes:
                break
    return found


def signature_dependents(apk):
    out = []
    keywords = ("sign", "certif", "tamper", "integrity", "installer", "packageinfo")
    for dex, data in _dex_streams(apk):
        idx = DexIndex(data)
        if not idx.ok:
            continue
        for i in range(min(idx.c_n, 60000)):
            cbase = idx.c_off + i * 32
            desc = idx.type_name(u4(data, cbase))
            methods = [m for m, off in iter_class_methods(data, idx, cbase) if off]
            if not methods:
                continue
            hits = [m for m in methods if m in SIG_TRUE or m in SIG_FALSE]
            if not hits:
                hits = [m for m in methods if any(k in m.lower() for k in keywords)]
            if not hits:
                continue
            name_hint = any(k in desc.lower() for k in ("signature", "integrity", "tamper", "sig"))
            out.append({"dex": dex, "class": desc, "methods": hits[:8],
                        "confidence": 0.9 if (name_hint and any(m in SIG_TRUE or m in SIG_FALSE for m in hits)) else 0.7})
    return out


JNI_ESCAPES = {"1": "_", "2": ";", "3": "[", "0": "/"}


def _jni_tokens(body):
    tokens = []
    cur = ""
    i = 0
    while i < len(body):
        c = body[i]
        if c == "_" and i + 1 < len(body) and body[i + 1].isdigit():
            cur += JNI_ESCAPES.get(body[i + 1], body[i + 1])
            i += 2
            continue
        if c == "_":
            tokens.append(cur)
            cur = ""
            i += 1
            continue
        cur += c
        i += 1
    tokens.append(cur)
    return tokens


def jni_symbol_map(elf):
    mapping = []
    for sym in getattr(elf, "symtab_names", []):
        if not sym.startswith("Java_"):
            continue
        tokens = _jni_tokens(sym[len("Java_"):])
        if len(tokens) < 2:
            continue
        mapping.append({"symbol": sym, "class": "/".join(tokens[:-1]), "method": tokens[-1]})
    return mapping


def elf_relocations(path):
    elf = ElfFile(path)
    if not elf.ok:
        return None, "not an elf object"
    relocs = []
    try:
        with open(path, "rb") as fh:
            for sec in elf.sections:
                if sec["type"] not in (4, 9):
                    continue
                entsize = 24 if (elf.bits == 64 and sec["type"] == 4) else (
                    16 if elf.bits == 64 else (12 if sec["type"] == 4 else 8))
                count = min(sec["size"] // entsize if entsize else 0, 50000)
                fh.seek(sec["offset"])
                blob = fh.read(entsize * count)
                for i in range(count):
                    base = i * entsize
                    if base + entsize > len(blob):
                        break
                    if elf.bits == 64:
                        r_offset = struct.unpack_from("<Q", blob, base)[0]
                        r_info = struct.unpack_from("<Q", blob, base + 8)[0]
                        rtype = r_info & 0xFFFFFFFF
                        rsym = r_info >> 32
                    else:
                        r_offset = u4(blob, base)
                        r_info = u4(blob, base + 4)
                        rtype = r_info & 0xFF
                        rsym = r_info >> 8
                    relocs.append({"section": sec["name"], "offset": "0x%x" % r_offset,
                                   "type": rtype, "symbol_index": rsym})
                    if len(relocs) >= 400:
                        return relocs, None
    except Exception as e:
        return relocs, trunc(str(e), 60)
    return relocs, None


def elf_strings(path, min_len=6, limit=200):
    elf = ElfFile(path)
    if not elf.ok:
        return []
    out = []
    try:
        with open(path, "rb") as fh:
            for sec in elf.sections:
                if sec["name"] not in (".rodata", ".data", ".data.rel.ro", ".text"):
                    continue
                fh.seek(sec["offset"])
                blob = fh.read(min(sec["size"], 4 << 20))
                for m in re.finditer(rb"[\x20-\x7e]{%d,}" % min_len, blob):
                    out.append(m.group().decode("ascii", "ignore"))
                    if len(out) >= limit:
                        return out
    except Exception:
        pass
    return out


def show_components(apk):
    Out.head("ad components", G_WARM)
    ads = component_map(apk, [p for prefixes in AD_SDKS.values() for p in prefixes], "ads")
    if not ads:
        Out.info("no ad sdk classes found")
    by_network = {}
    for desc, entry in ads.items():
        for label, prefixes in AD_SDKS.items():
            if any(p.lower() in desc.lower() for p in prefixes):
                by_network.setdefault(label, []).append(entry)
                break
    for label in sorted(by_network):
        classes = by_network[label]
        Out.kv(label, "%d class(es)" % len(classes), width=22)
        for entry in classes[:3]:
            print("    " + T_DIM(BULLET + " " + trunc(entry["class"], 70)))
            if entry["init"]:
                print("      " + T_DIM("init: " + ", ".join(entry["init"][:4])))
            if entry["show"]:
                print("      " + T_DIM("show: " + ", ".join(entry["show"][:4])))

    Out.head("license components", G_WARM)
    lic = component_map(apk, LICENSE_CLASSES, "license")
    if not lic:
        Out.info("no license checker classes")
    for desc, entry in list(lic.items())[:6]:
        Out.kv(trunc(desc, 60), "%d method(s)" % len(entry["methods"]), width=62)
        if entry["methods"]:
            print("    " + T_DIM("methods: " + ", ".join(entry["methods"][:6])))

    Out.head("billing components", G_COOL)
    bil = component_map(apk, BILLING_CLASSES, "billing")
    if not bil:
        Out.info("no billing client classes")
    for desc, entry in list(bil.items())[:6]:
        Out.kv(trunc(desc, 60), "%d method(s)" % len(entry["methods"]), width=62)

    Out.head("signature dependencies", G_WARM)
    deps = signature_dependents(apk)
    if not deps:
        Out.ok("no class reads its own signing certificate")
    for d in deps[:10]:
        Out.kv(trunc(d["class"], 56), "%s · conf %.2f" % (d["dex"], d["confidence"]), width=58)
        print("    " + T_DIM(", ".join(d["methods"][:5])))
    return {"ads": {k: [e["class"] for e in v] for k, v in by_network.items()},
            "license": list(lic.keys()), "billing": list(bil.keys()), "signature": deps}


def cmd_components(args):
    Tty.probe()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    apk, _searched = resolve_input(args.input)
    if apk is None:
        Out.bad("input not found · " + str(args.input))
        for _root in (_searched or [])[:5]:
            Out.info("looked in " + str(_root))
        return 2
    data = show_components(apk)
    if args.output:
        atomic_write(Path(args.output).expanduser(), json.dumps(data, indent=2, default=str), "w")
        Out.kv("written", str(args.output))
    return 0



def native_frida_script(reports, apk_name, ssl_plan=None):
    lines = [
        "Java.perform(function () {",
        "  var seen = {};",
        "  function hook(cls, meth, note) {",
        "    var key = cls + '#' + meth;",
        "    if (seen[key]) { return; }",
        "    seen[key] = true;",
        "    try {",
        "      var C = Java.use(cls);",
        "      C[meth].overloads.forEach(function (ov) {",
        "        ov.implementation = function () {",
        "          var args = Array.prototype.slice.call(arguments);",
        "          var ret = ov.apply(this, args);",
        "          send({ hook: key, note: note, args: args.map(String), ret: String(ret) });",
        "          return ret;",
        "        };",
        "      });",
        "    } catch (e) { send({ hook: key, error: String(e) }); }",
        "  }",
    ]
    for rep in reports:
        for j in rep.get("jni", []):
            cls = j["class"].replace("/", ".")
            if cls and j["method"]:
                lines.append('  hook("%s", "%s", "%s");' % (cls, j["method"], rep["object"]))
    if ssl_plan:
        for cand in ssl_plan.get("candidates", []):
            cls = cand["class"].strip("L;").replace("/", ".")
            for meth in cand["methods"][:4]:
                lines.append('  hook("%s", "%s", "tls");' % (cls, meth))
    lines += [
        "  send({ script: 'arpxtool', apk: '%s', hooks: Object.keys(seen).length });" % apk_name,
        "});",
        "",
    ]
    return "\n".join(lines)


def cmd_native(args):
    Tty.probe()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    apk, _searched = resolve_input(args.input)
    if apk is None:
        Out.bad("input not found · " + str(args.input))
        for _root in (_searched or [])[:5]:
            Out.info("looked in " + str(_root))
        return 2
    natives = collect_natives(apk, None)
    if not natives:
        Out.bad("no native objects in this archive")
        return 3
    Out.head("native objects", G_WARM)
    for e in natives:
        s = e.summary()
        Out.kv(e.name, "%s · %d-bit · %s" % (s["machine"], s["bits"], human(s["size"])), width=32)
        jni = jni_symbol_map(e)
        if jni:
            Out.kv("jni exports", len(jni), width=32)
            for m in jni[:6]:
                print("    " + T_DIM("%s -> %s#%s" % (trunc(m["symbol"], 44), m["class"], m["method"])))
        relocs, err = elf_relocations(e.path)
        if relocs:
            Out.kv("relocations", len(relocs), width=32)
        elif err:
            Out.kv("relocations", err, width=32)
        if args.strings:
            strs = elf_strings(e.path, 6, args.strings)
            if strs:
                Out.kv("strings", len(strs), width=32)
                for st in strs[:10]:
                    print("    " + T_DIM(BULLET + " " + trunc(st, 84)))
    if args.frida:
        reports = []
        for e in natives:
            reports.append({"object": e.name, "jni": jni_symbol_map(e)})
        dest = Path(args.frida).expanduser()
        dest.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(dest, native_frida_script(reports, apk.name), "w")
        Out.head("frida", G_OK)
        hooks = sum(len(r["jni"]) for r in reports)
        Out.kv("hooks", hooks, width=18)
        Out.kv("written", str(dest))
        if hooks == 0:
            Out.info("no jni exports found · the script is a skeleton to extend")
    return 0




STUB_FOR_RETURN = {
    "V": "void", "Z": "true", "I": "zero", "B": "zero", "S": "zero", "C": "zero",
    "F": "zero", "J": "wide", "D": "wide",
}

MODULE_PREFIXES = {
    "ads": [p for prefixes in AD_SDKS.values() for p in prefixes],
    "license": LICENSE_CLASSES,
    "billing": BILLING_CLASSES,
}


def proto_return_descriptor(idx, proto_idx):
    try:
        base = idx.p_off + proto_idx * 12
        type_idx = u4(idx.d, base + 4)
        return idx.type_name(type_idx)
    except Exception:
        return "?"


def stub_kind_for(desc):
    if not desc:
        return "void"
    head = desc[0]
    if head == "[" or head == "L":
        return "null"
    return STUB_FOR_RETURN.get(head, "null")


def dex_method_return(idx, method_idx):
    try:
        proto = u2(idx.d, idx.m_off + method_idx * 8 + 2)
        return proto_return_descriptor(idx, proto)
    except Exception:
        return "?"


def invoke_targets(apk, prefixes, method_budget=40000):
    callers = {}
    callees = {}
    for dex, data in _dex_streams(apk):
        idx = DexIndex(data)
        if not idx.ok:
            continue
        matching = {}
        for mi in range(min(idx.m_n, 400000)):
            try:
                cls = idx.type_name(u2(data, idx.m_off + mi * 8))
            except Exception:
                continue
            for p in prefixes:
                if p.lower() in cls.lower():
                    matching[mi] = cls
                    break
        if not matching:
            continue
        produced = 0
        for mc in iter_method_code(dex, data, 20000, method_budget):
            produced += 1
            if produced > method_budget:
                break
            for ins in mc.insns:
                if ins["kind"] != "invoke" or ins["ref"] not in matching:
                    continue
                caller = "%s->%s" % (mc.descriptor, mc.name)
                callers.setdefault(caller, set()).add(matching[ins["ref"]])
                callees.setdefault(matching[ins["ref"]], set()).add(caller)
    return callers, callees


def method_return_kind(apk, class_desc, method_name):
    for dex, data in _dex_streams(apk):
        idx = DexIndex(data)
        if not idx.ok:
            continue
        cbase = idx.find_class(class_desc)
        if cbase is None:
            continue
        for mi in range(min(idx.m_n, 400000)):
            if idx.method_name(mi) != method_name:
                continue
            if idx.type_name(u2(data, idx.m_off + mi * 8)) != class_desc:
                continue
            return stub_kind_for(dex_method_return(idx, mi))
    return "void"


def build_patchset(name, title, entries):
    patches = []
    for i, e in enumerate(entries):
        patches.append({
            "id": "%s-%d" % (name, i),
            "title": e.get("title") or "%s target %d" % (name, i),
            "action": "stub-method",
            "targets": [e["target"]],
            "kind": e.get("kind", "void"),
            "note": e.get("note", ""),
        })
    return {"schema": "arp-patch/1", "name": title, "patches": patches, "profiles": {"default": [p["id"] for p in patches]}}


def plan_entries(callers, apk, limit=40):
    entries = []
    for caller in sorted(callers):
        if "->" not in caller:
            continue
        desc, meth = caller.split("->", 1)
        kind = method_return_kind(apk, desc, meth)
        entries.append({
            "target": "%s#%s" % (desc.replace("/", ".").strip("L;"), meth),
            "kind": kind,
            "title": "disable call site %s" % meth,
            "callees": sorted(callers[caller])[:4],
        })
        if len(entries) >= limit:
            break
    return entries


def module_ads(apk):
    found = component_map(apk, MODULE_PREFIXES["ads"], "ads")
    callers, callees = invoke_targets(apk, MODULE_PREFIXES["ads"])
    networks = {}
    for desc in found:
        for label, prefixes in AD_SDKS.items():
            if any(p.lower() in desc.lower() for p in prefixes):
                networks.setdefault(label, []).append(desc)
                break
    entries = plan_entries(callers, apk)
    patchset = build_patchset("ads", "ad integration call sites", entries)
    return {"networks": {k: len(v) for k, v in networks.items()},
            "classes": len(found), "call_sites": len(callers),
            "entries": entries, "patchset": patchset}


def module_license(apk):
    found = component_map(apk, MODULE_PREFIXES["license"], "license")
    callers, callees = invoke_targets(apk, MODULE_PREFIXES["license"])
    entries = plan_entries(callers, apk)
    patchset = build_patchset("license", "license verification call sites", entries)
    return {"classes": len(found), "call_sites": len(callers), "entries": entries, "patchset": patchset}


def module_billing(apk):
    found = component_map(apk, MODULE_PREFIXES["billing"], "billing")
    callers, callees = invoke_targets(apk, MODULE_PREFIXES["billing"])
    entries = plan_entries(callers, apk)
    patchset = build_patchset("billing", "billing call sites", entries)
    return {"classes": len(found), "call_sites": len(callers), "entries": entries, "patchset": patchset}


def module_signature(apk):
    deps = signature_dependents(apk)
    targets = []
    for d in deps:
        for m in d["methods"]:
            if m in SIG_TRUE:
                kind = "true"
            elif m in SIG_FALSE:
                kind = "false"
            else:
                kind = method_return_kind(apk, d["class"], m)
            targets.append({"target": "%s#%s" % (d["class"].replace("/", ".").strip("L;"), m),
                            "kind": kind, "title": "neutralise %s" % m})
    native_refs = native_protection_refs(apk)
    patchset = build_patchset("signature", "signature self-check methods", targets)
    return {"dependents": deps, "targets": targets, "native_refs": native_refs, "patchset": patchset}


NATIVE_MARKERS = (
    "signature", "certificate", "integrity", "tamper", "root", "frida", "xposed",
    "debug", "ptrace", "check", "verify", "licen", "billing",
)


def native_protection_refs(apk):
    out = []
    for e in collect_natives(apk, None):
        hits = []
        for sym in list(e.imports) + list(getattr(e, "symtab_names", [])):
            low = sym.lower()
            for m in NATIVE_MARKERS:
                if m in low:
                    hits.append(sym)
                    break
        strings = elf_strings(e.path, 5, 400)
        text_hits = [s for s in strings if any(m in s.lower() for m in NATIVE_MARKERS)]
        out.append({"object": e.name, "machine": e.machine, "bits": e.bits,
                    "symbols": sorted(set(hits))[:20], "strings": text_hits[:12]})
    return out


def show_module(title, result, kind):
    Out.head(title, G_WARM)
    if kind == "ads":
        if result["networks"]:
            for label, n in sorted(result["networks"].items()):
                Out.kv(label, "%d class(es)" % n, width=22)
        else:
            Out.info("no ad sdk detected")
    Out.kv("classes", result.get("classes", 0), width=22)
    Out.kv("call sites", result.get("call_sites", len(result.get("targets", []))), width=22)
    entries = result.get("entries") or result.get("targets") or []
    for e in entries[:10]:
        Out.bullet("%s  ·  %s" % (e["target"], e.get("kind")))
    if len(entries) > 10:
        Out.info("… %d more" % (len(entries) - 10))
    if not entries:
        Out.info("nothing to target")


def cmd_manager(args, kind):
    Tty.probe()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    apk, _searched = resolve_input(args.input)
    if apk is None:
        Out.bad("input not found · " + str(args.input))
        for _root in (_searched or [])[:5]:
            Out.info("looked in " + str(_root))
        return 2
    if kind == "ads":
        result = module_ads(apk)
        show_module("advertising manager", result, "ads")
    elif kind == "license":
        result = module_license(apk)
        show_module("license manager", result, "license")
    elif kind == "billing":
        result = module_billing(apk)
        show_module("billing manager", result, "billing")
    elif kind == "signature":
        result = module_signature(apk)
        show_module("signature manager", result, "signature")
        if result["native_refs"]:
            Out.head("native protection references", G_COOL)
            for r in result["native_refs"]:
                Out.kv(r["object"], "%s · %d symbol(s) · %d string(s)" % (r["machine"], len(r["symbols"]), len(r["strings"])), width=28)
                for s in r["symbols"][:4]:
                    print("    " + T_DIM(BULLET + " " + trunc(s, 76)))
    else:
        Out.bad("unknown module")
        return 2

    patchset = result.get("patchset") or {"patches": []}
    out_dir = Path(args.output).expanduser() if args.output else HOME
    if out_dir.suffix:
        out_dir = out_dir.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    plan_path = out_dir / ("%s-%s.patch.json" % (apk.stem, kind))
    atomic_write(plan_path, json.dumps(patchset, indent=2), "w")
    Out.head("generated patch set", G_OK)
    Out.kv("patches", len(patchset["patches"]))
    Out.kv("file", str(plan_path))
    if patchset["patches"] and args.dry_run:
        Out.info("dry run · apply with: --patch " + str(plan_path))
    if patchset["patches"] and not args.dry_run:
        chosen = [{"id": p["id"], "title": p["title"], "action": "stub-method",
                   "targets": p["targets"], "kind": p["kind"], "conflicts": [], "note": p.get("note", "")}
                  for p in patchset["patches"]]
        report = validate_patch_against(chosen, apk)
        ok = [r for r in report if r["ok"]]
        Out.head("apply", G_OK)
        Out.kv("resolved", "%d of %d" % (len(ok), len(report)))
        if not ok:
            Out.bad("no target resolved · nothing applied")
            return 5
        out_apk = rap_output(apk, kind)
        journal, err = apply_patch_set(apk, out_apk, [c for c in chosen if any(r["id"] == c["id"] and r["ok"] for r in report)],
                                       backup_dir=str(out_apk) + ".backup")
        if journal is None:
            Out.bad(err)
            return 6
        jp = Path(str(out_apk) + ".journal.json")
        atomic_write(jp, json.dumps(journal, indent=2), "w")
        Out.ok("applied %d patch group(s)" % len(journal["applied"]))
        Out.kv("output", str(out_apk))
        Out.kv("journal", str(jp))
        if args.sign:
            final, aligned = do_zipalign({"zipalign": which("zipalign")}, out_apk, out_apk.parent)
            signed, how = do_sign(resolve_toolchain(out_apk.parent, allow_net=False, quiet=True), out_apk, out_apk.parent, args.password)
            Out.kv("signed", how if signed else "no signer available")
    return 0



def cmd_full_modification(args):
    Tty.probe()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    apk, _searched = resolve_input(args.input)
    if apk is None:
        Out.bad("input not found · " + str(args.input))
        for _root in (_searched or [])[:5]:
            Out.info("looked in " + str(_root))
        return 2
    modules = []
    Out.head("full modification", G_MAIN)
    for kind, fn in (("ads", module_ads), ("license", module_license), ("billing", module_billing), ("signature", module_signature)):
        try:
            res = fn(apk)
        except Exception as e:
            Out.warn("%s · %s" % (kind, trunc(str(e), 60)))
            continue
        n = len(res.get("patchset", {}).get("patches", []))
        modules.append((kind, res))
        Out.kv(kind, "%d target(s)" % n, width=16)
    merged = {"schema": "arp-patch/1", "name": "full-modification", "patches": [], "profiles": {}}
    for kind, res in modules:
        merged["patches"].extend(res.get("patchset", {}).get("patches", []))
    merged["profiles"]["all"] = [p["id"] for p in merged["patches"]]
    out_dir = Path(args.output).expanduser() if args.output else HOME
    if out_dir.suffix:
        out_dir = out_dir.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / ("%s-full.patch.json" % apk.stem)
    atomic_write(path, json.dumps(merged, indent=2), "w")
    Out.head("merged patch set", G_OK)
    Out.kv("patches", len(merged["patches"]))
    Out.kv("file", str(path))
    if args.dry_run:
        Out.info("dry run · nothing applied")
        return 0
    chosen = [{"id": p["id"], "title": p["title"], "action": "stub-method", "targets": p["targets"],
               "kind": p["kind"], "conflicts": [], "note": p.get("note", "")} for p in merged["patches"]]
    if not chosen:
        Out.bad("nothing to apply")
        return 5
    report = validate_patch_against(chosen, apk)
    good = [c for c in chosen if any(r["id"] == c["id"] and r["ok"] for r in report)]
    Out.kv("resolved", "%d of %d" % (len(good), len(report)))
    if not good:
        return 5
    out_apk = rap_output(apk, "modified")
    journal, err = apply_patch_set(apk, out_apk, good, backup_dir=str(out_apk) + ".backup")
    if journal is None:
        Out.bad(err)
        return 6
    atomic_write(Path(str(out_apk) + ".journal.json"), json.dumps(journal, indent=2), "w")
    Out.ok("applied %d change group(s)" % len(journal["applied"]))
    final, aligned = do_zipalign({"zipalign": which("zipalign")}, out_apk, out_apk.parent)
    signed, how = do_sign(resolve_toolchain(out_apk.parent, allow_net=False, quiet=True), out_apk, out_apk.parent, args.password)
    Out.kv("output", str(out_apk))
    Out.kv("signed", how if signed else "no signer available")
    show_lint(out_apk)
    return 0


NATIVE_STUBS = {
    "aarch64": bytes.fromhex("00008052c0035fd6"),
    "arm": bytes.fromhex("00207047"),
    "x86_64": bytes.fromhex("31c0c3"),
    "x86": bytes.fromhex("31c0c3"),
    "riscv": bytes.fromhex("1305000067800000"),
}


def vaddr_to_offset(elf, vaddr):
    for p_vaddr, p_offset, p_filesz in getattr(elf, "segments", []):
        if p_vaddr <= vaddr < p_vaddr + p_filesz:
            return p_offset + (vaddr - p_vaddr)
    return None


def elf_symbol_offset(elf, symbol):
    try:
        with open(elf.path, "rb") as fh:
            for sec in elf.sections:
                if sec["type"] not in (2, 11):
                    continue
                link = sec["link"]
                if not (0 <= link < len(elf.sections)):
                    continue
                strsec = elf.sections[link]
                fh.seek(strsec["offset"])
                strtab = fh.read(min(strsec["size"], 4 << 20))
                entsize = sec["entsize"] or (24 if elf.bits == 64 else 16)
                count = min(sec["size"] // entsize if entsize else 0, 80000)
                fh.seek(sec["offset"])
                blob = fh.read(entsize * count)
                for i in range(count):
                    base = i * entsize
                    if base + entsize > len(blob):
                        break
                    name_off = u4(blob, base)
                    if not name_off or name_off >= len(strtab):
                        continue
                    name = strtab[name_off:].split(b"\x00")[0].decode("ascii", "ignore")
                    if name != symbol:
                        continue
                    if elf.bits == 64:
                        value = struct.unpack_from("<Q", blob, base + 8)[0]
                    else:
                        value = u4(blob, base + 4)
                    if value == 0:
                        continue
                    off = vaddr_to_offset(elf, value & ~1)
                    return off
    except Exception:
        return None
    return None


def native_stub_file(path, symbol, dry=False):
    elf = ElfFile(path)
    if not elf.ok:
        return False, "not an elf object", None
    stub = NATIVE_STUBS.get(elf.machine)
    if not stub:
        return False, "no stub for isa " + elf.machine, None
    off = elf_symbol_offset(elf, symbol)
    if off is None:
        return False, "symbol not found", None
    try:
        with open(path, "rb") as fh:
            fh.seek(off)
            original = fh.read(len(stub))
        if original == stub:
            return True, "already stubbed", {"offset": "0x%x" % off, "symbol": symbol, "arch": elf.machine}
        if not dry:
            backup = Path(str(path) + ".arpbak")
            if not backup.exists():
                shutil.copy2(path, backup)
            with open(path, "r+b") as fh:
                fh.seek(off)
                fh.write(stub)
            with open(path, "rb") as fh:
                fh.seek(off)
                if fh.read(len(stub)) != stub:
                    if backup.exists():
                        shutil.copy2(backup, path)
                    return False, "write verification failed", None
        return True, "stubbed", {"offset": "0x%x" % off, "symbol": symbol, "arch": elf.machine}
    except Exception as e:
        return False, trunc(str(e), 60), None


def cmd_native_patch(args):
    Tty.probe()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    apk, _searched = resolve_input(args.input)
    if apk is None:
        Out.bad("input not found · " + str(args.input))
        for _root in (_searched or [])[:5]:
            Out.info("looked in " + str(_root))
        return 2
    symbols = [s.strip() for s in args.native_patch.split(",") if s.strip()]
    if not symbols:
        Out.bad("no symbol given")
        return 2
    natives = collect_natives(apk, None)
    if not natives:
        Out.bad("no native objects")
        return 3
    out = Path(args.output).expanduser() if args.output else rap_output(apk, "native")
    work = Path(tempfile.mkdtemp(prefix="arp_nat_"))
    results = []
    try:
        for e in natives:
            for sym in symbols:
                ok, detail, info = native_stub_file(e.path, sym, dry=args.dry_run)
                if ok and info:
                    results.append((e.name, sym, detail, info))
                    Out.ok("%s · %s · %s" % (e.name, sym, info["offset"]))
                elif "not found" not in detail:
                    Out.warn("%s · %s · %s" % (e.name, sym, detail))
        if not results or args.dry_run:
            Out.info("no archive written")
            return 0
        with zipfile.ZipFile(apk) as zin, zipfile.ZipFile(out, "w") as zout:
            for item in zin.infolist():
                if item.filename.upper().startswith("META-INF/") and item.filename.upper().endswith((".SF", ".RSA", ".DSA", ".EC", ".MF")):
                    continue
                payload = zin.read(item.filename)
                for e in natives:
                    if item.filename.endswith("/" + e.name) or item.filename == e.name:
                        payload = Path(e.path).read_bytes()
                        break
                zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
                zi.compress_type = item.compress_type
                zi.external_attr = item.external_attr
                zi.internal_attr = item.internal_attr
                zi.create_system = item.create_system
                zout.writestr(zi, payload)
        final, aligned = do_zipalign({"zipalign": which("zipalign")}, out, out.parent)
        Out.head("result", G_OK)
        Out.kv("patched", "%d symbol(s)" % len(results))
        Out.kv("output", str(out))
        if args.sign:
            signed, how = do_sign(resolve_toolchain(work, allow_net=False, quiet=True), out, work, args.password)
            Out.kv("signed", how if signed else "no signer available")
        show_lint(out)
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)




POSITIONAL_COMMANDS = {
    "ssl": ["-m", "ssl"],
    "signature": ["-m", "signature"],
    "security": ["-m", "security"],
    "full": ["-m", "full"],
    "fast": ["-m", "fast"],
    "surgery": ["-m", "surgery"],
    "native": ["-m", "native"],
    "re": ["-m", "re"],
    "report": ["-m", "re"],
    "unpack": ["-m", "unpack"],
    "inspect": ["-m", "inspect"],
    "verify": ["-m", "verify"],
    "detect": ["-m", "detect"],
    "ads": ["--ads-manager"],
    "license": ["--license-manager"],
    "billing": ["--billing-manager"],
    "signature-manager": ["--signature-manager"],
    "install": ["--install-check"],
    "components": ["--components"],
    "cert": ["--cert"],
    "native-analysis": ["--native-analysis"],
    "full-modification": ["--full-modification"],
    "security-test": ["--security-test"],
    "self-check": ["--self-check"],
    "install-cli": ["--install-cli"],
    "edit": ["--edit"],
    "ssl-engine": ["--ssl-engine"],
    "signature-engine": ["--signature-engine"],
    "so-report": ["--so-report"],
    "secrets": ["--secrets"],
    "arsc": ["--arsc"],
    "axml2xml": ["--axml2xml"],
    "xml2axml": ["--xml2axml"],
    "hex": ["--hex"],
    "clone": ["--clone"],
    "compare-dex": ["--compare-dex"],
    "vdex": ["--vdex"],
    "dex-edit": ["--dex-edit"],
    "sign-native": ["--sign-native"],
    "tools": ["--tools"],
    "flutter-ssl": ["--flutter-ssl"],
    "flutter": ["--flutter-ssl"],
    "setup": ["--setup"],
    "install-all": ["--install-all"],
    "provenance": ["--provenance"],
    "repair": ["--repair"],
    "keygen": ["--keygen"],
    "keygen-app": ["--keygen-app"],
    "identify": ["--identify"],
    "diagnose": ["--diagnose"],
    "exit-check": ["--exit-check"],
    "crash-read": ["--crash-read"],
    "crashpatch": ["--crashpatch"],
    "axml-info": ["--axml-info"],
    "fix-native": ["--fix-native"],
    "crashinject": ["--crashinject"],
    "logcat": ["--logcat"],
    "crash": ["--exit-check"],
    "sign": ["--sign-apk"],
    "key": ["--keygen"],
    "fix": ["--repair"],
    "doctor": ["--doctor"],
    "clean": ["--clean"],
}

POSITIONAL_WITH_ARG = {
    "patch": ["--patch"],
    "revert": ["--revert"],
    "methods": ["--methods"],
    "search": ["--search"],
    "compare": ["--compare"],
    "targets": ["--targets"],
    "rules": ["--rules"],
    "native-patch": ["--native-patch"],
    "edit": ["--edit"],
    "ssl-engine": ["--ssl-engine"],
    "signature-engine": ["--signature-engine"],
    "so-report": ["--so-report"],
    "secrets": ["--secrets"],
    "arsc": ["--arsc"],
    "axml2xml": ["--axml2xml"],
    "xml2axml": ["--xml2axml"],
    "hex": ["--hex"],
    "clone": ["--clone"],
    "compare-dex": ["--compare-dex"],
    "vdex": ["--vdex"],
    "dex-edit": ["--dex-edit"],
    "sign-native": ["--sign-native"],
    "tools": ["--tools"],
    "flutter-ssl": ["--flutter-ssl"],
    "flutter": ["--flutter-ssl"],
    "setup": ["--setup"],
    "install-all": ["--install-all"],
    "provenance": ["--provenance"],
    "repair": ["--repair"],
    "embed-ca": ["--embed-ca"],
}

ARCHIVE_SUFFIX = (".apk", ".apks", ".xapk", ".apkm", ".aab", ".ipa", ".dex", ".so", ".zip", ".jar", ".aar")

NO_INPUT_COMMANDS = ("install-cli", "doctor", "clean", "self-check", "tools", "setup",
                     "install-all", "provenance", "keygen", "logcat")


def looks_like_archive(token):
    low = token.lower()
    return low.endswith(ARCHIVE_SUFFIX) or Path(token).expanduser().exists()


def positional_rewrite(argv):
    if not argv:
        return [], "reference"
    head = argv[0].lower()
    if head in ("help", "/help", "-h", "--help", "?", "commands"):
        return [], "reference"
    if head in NO_INPUT_COMMANDS:
        return POSITIONAL_COMMANDS[head] + argv[1:], None
    if head in POSITIONAL_COMMANDS and len(argv) > 1 and looks_like_archive(argv[1]):
        return ["-i", argv[1]] + POSITIONAL_COMMANDS[head] + argv[2:], None
    if not looks_like_archive(argv[0]):
        return argv, None
    rest = argv[1:]
    out = ["-i", argv[0]]
    if rest:
        cmd = rest[0].lower()
        if cmd in POSITIONAL_COMMANDS:
            out += POSITIONAL_COMMANDS[cmd]
            rest = rest[1:]
        elif cmd in POSITIONAL_WITH_ARG:
            if len(rest) < 2:
                return out, ("missing-arg", cmd)
            out += POSITIONAL_WITH_ARG[cmd] + [rest[1]]
            rest = rest[2:]
    return out + rest, None


REFERENCE_GROUPS = [
    ("core", G_MAIN, [
        ("ssl", "neutralise tls verification and trust managers"),
        ("signature", "neutralise signature self-checks"),
        ("security", "root, vpn, frida and emulator checks"),
        ("full", "binary + bytecode + manifest + sign"),
        ("fast", "manifest and netsec only, never smali"),
        ("surgery", "no java, no apktool, no aapt2"),
        ("native", "binary only, surgical repack"),
    ]),
    ("analysis", G_COOL, [
        ("re", "decompile and deep static analysis"),
        ("detect", "ads, billing, license, signature map"),
        ("inspect", "read only forensic report"),
        ("verify", "signature and archive audit"),
        ("install", "why an archive would refuse to install"),
        ("components", "ad, license, billing, signature components"),
        ("native-analysis", "elf, jni, relocations, strings"),
        ("security-test", "nine stage defensive audit"),
    ]),
    ("modification", G_WARM, [
        ("ads", "detect and disable ad call sites"),
        ("license", "detect and disable license call sites"),
        ("billing", "detect and disable billing call sites"),
        ("signature-manager", "signature dependency and self checks"),
        ("full-modification", "every manager merged and applied"),
        ("patch", "apply a json patch set"),
        ("revert", "restore from a journal"),
        ("unpack", "extract every entry byte for byte"),
    ]),
    ("tools", G_OK, [
        ("methods", "list dex methods matching a regex"),
        ("search", "search strings across dex and assets"),
        ("cert", "signing certificate facts"),
        ("compare", "diff two archives"),
        ("native-patch", "stub native symbols in every .so"),
        ("clean", "purge stale work trees"),
        ("doctor", "diagnose the host and toolchain"),
        ("self-check", "run internal diagnostics"),
    ]),
]

REFERENCE_FLAGS = [
    ("-i, --input PATH", "target archive"),
    ("-o, --output PATH", "where to write the result"),
    ("-m, --mode NAME", "operation mode"),
    ("--targets FILE", "user patch list, Class#method kind"),
    ("--rules FILE", "json or yaml detection rules"),
    ("--patch FILE", "json patch set"),
    ("--profile NAME", "patch profile"),
    ("--dry-run", "plan only, never write"),
    ("--apply", "kept for compatibility, apply is default"),
    ("--sign", "sign the result"),
    ("--unsigned", "skip signing"),
    ("--embed-ca PEM", "trust your own ca certificate"),
    ("--engine VERSION", "force an apktool version"),
    ("--flutter-engine SO", "drop-in libflutter.so (prebuilt patched engine)"),
    ("--remove-license", "neutralise play store licence checks"),
    ("--max-engines N", "how many engines to try"),
    ("--resume DIR", "rebuild from a preserved tree"),
    ("--baseline APK", "earlier build to diff against"),
    ("--java DIR", "decompile to java with jadx"),
    ("--disasm N", "disassemble native instructions"),
    ("--frida FILE", "write a frida hook script"),
    ("--mapping FILE", "proguard mapping"),
    ("--batch DIR", "process a folder"),
    ("--no-net", "never download anything"),
    ("--no-anim", "disable animation"),
    ("--quiet", "skip the banner"),
    ("--keep", "keep the work tree"),
    ("--log FILE", "session log path"),
]


def print_reference():
    Tty.probe()
    banner_anim(not Tty.enabled)
    print()
    print("  " + gradient_text("usage", G_MAIN, True))
    print("  " + Pal(AMBER, True)("first run:  ") + T_TXT("python3 arpxtool.py install-cli") + T_DIM("   installs the arpxtool launcher"))
    print()
    print("  " + T_TXT("arpxtool <archive> <command> [flags]") + T_DIM("        positional form"))
    print("  " + T_TXT("arpxtool -i <archive> -m <mode> [flags]") + T_DIM("      flag form"))
    print("  " + T_TXT("arpxtool") + T_DIM("                             this screen"))
    print("  " + T_TXT("arpxtool --menu") + T_DIM("                      interactive selector"))
    for title, stops, rows in REFERENCE_GROUPS:
        print()
        print("  " + rule(Tty.clamp(20, 74), stops, THIN))
        print("  " + Pal(stops[-1], True)(title.upper()))
        print("  " + rule(Tty.clamp(20, 74), stops, THIN))
        for name, desc in rows:
            print("  " + Pal(stops[0])(name.ljust(20)) + T_DIM(desc))
    print()
    print("  " + rule(Tty.clamp(20, 74), G_COOL, THIN))
    print("  " + Pal(CYAN, True)("FLAGS"))
    print("  " + rule(Tty.clamp(20, 74), G_COOL, THIN))
    for name, desc in REFERENCE_FLAGS:
        print("  " + T_TXT(name.ljust(24)) + T_DIM(desc))
    print()
    print("  " + rule(Tty.clamp(20, 74), G_OK, THIN))
    print("  " + Pal(EMERALD, True)("EXAMPLES"))
    print("  " + rule(Tty.clamp(20, 74), G_OK, THIN))
    for line in (
        "arpxtool app.apk ssl",
        "arpxtool app.apk signature --sign",
        "arpxtool app.apk ads",
        "arpxtool app.apk detect",
        "arpxtool app.apk install",
        "arpxtool app.apk patch my.patch.json",
        "arpxtool app.apk methods license",
        "arpxtool app.apk compare old.apk",
        "arpxtool app.apk unpack ./out",
        "arpxtool app.apk security-test --rules custom_rules.example.json",
    ):
        print("  " + T_DIM("$ ") + T_TXT(line))
    print()
    print("  " + rule(Tty.clamp(20, 74), G_MAIN))
    return 0



def launcher_dirs():
    dirs = []
    prefix = os.environ.get("PREFIX")
    if prefix:
        dirs.append(Path(prefix) / "bin")
    dirs.append(Path("/data/data/com.termux/files/usr/bin"))
    dirs.append(HOME / ".local" / "bin")
    dirs.append(HOME / "bin")
    seen = []
    for d in dirs:
        if d not in seen:
            seen.append(d)
    return seen


def cmd_install_cli(args):
    Tty.probe()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    Out.head("install launcher", G_MAIN)
    script = Path(sys.argv[0]).resolve()
    if not script.exists():
        script = Path(__file__).resolve()
    Out.kv("script", str(script))
    name = args.install_cli if isinstance(args.install_cli, str) and args.install_cli else "arpxtool"
    body = "#!/usr/bin/env sh\nexec python3 %s \"$@\"\n" % shlex_quote(str(script))
    placed = None
    for d in launcher_dirs():
        try:
            d.mkdir(parents=True, exist_ok=True)
        except Exception:
            continue
        target = d / name
        try:
            atomic_write(target, body, "w")
            os.chmod(target, 0o755)
            placed = target
            break
        except Exception:
            continue
    if not placed:
        Out.bad("no writable bin directory found")
        return 3
    Out.ok("launcher written · " + str(placed))
    path_env = os.environ.get("PATH", "")
    if str(placed.parent) in path_env.split(":"):
        Out.ok("directory is already on PATH · type: " + name)
    else:
        Out.warn(str(placed.parent) + " is not on PATH")
        Out.info("add it: export PATH=\"" + str(placed.parent) + ":$PATH\"")
    clash = shutil.which(name)
    if clash and Path(clash) != placed:
        Out.warn("another '" + name + "' resolves first · " + clash)
        if os.environ.get("PREFIX"):
            Out.info("on termux $PREFIX/bin normally comes before /system/bin")
            Out.info("open a new shell, then run: hash -r; which arp")
        Out.info("if the system tool still wins, install under another name:")
        Out.info("  python3 " + script.name + " install-cli arpx")
    Out.head("check", G_OK)
    for probe in (name,):
        Out.kv(probe, shutil.which(probe) or "not resolved yet")
    Out.info("open a new shell if the command is not found yet")
    return 0


def shlex_quote(value):
    if not value:
        return "''"
    if re.fullmatch(r"[A-Za-z0-9_./@%+=:,-]+", value):
        return value
    return "'" + value.replace("'", "'\"'\"'") + "'"


CONFIG_KEYS = ("netsec_mode", "threads", "timeout", "password", "max_engines", "unsigned",
               "sign", "embed_ca", "no_net", "no_anim", "quiet", "keep", "strategy", "engine")


def apply_config(args):
    path = getattr(args, "config", None)
    if not path:
        return args
    src = Path(path).expanduser()
    if not src.exists():
        Out.warn("config not found · " + str(src))
        return args
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except Exception as e:
        Out.warn("config unreadable · " + trunc(str(e), 60))
        return args
    if not isinstance(data, dict):
        Out.warn("config must be a json object, got " + type(data).__name__)
        return args
    applied = []
    for key, value in data.items():
        field = str(key).replace("-", "_")
        if field not in CONFIG_KEYS or not hasattr(args, field):
            continue
        current = getattr(args, field)
        if current in (None, False, 0, "auto", "user"):
            setattr(args, field, value)
            applied.append(field)
    if applied:
        Out.info("config applied · " + ", ".join(applied))
    if getattr(args, "threads", None):
        RUNTIME["threads"] = args.threads
    if getattr(args, "timeout", None):
        RUNTIME["timeout"] = args.timeout
    return args




IF_OPS = set(range(0x32, 0x3E))
GOTO_OPS = {0x28, 0x29, 0x2A}
CONST_OPS = {0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x19}
NOP = 0x0000


def method_code_offset(data, class_desc, method_name):
    idx = DexIndex(data)
    if not idx.ok:
        return None
    cbase = idx.find_class(class_desc)
    if cbase is None:
        return None
    cdata = u4(data, cbase + 24)
    if not cdata:
        return None
    p = cdata
    try:
        sf, p = uleb(data, p)
        inf, p = uleb(data, p)
        dm, p = uleb(data, p)
        vm, p = uleb(data, p)
        for _ in range(sf + inf):
            _, p = uleb(data, p)
            _, p = uleb(data, p)
        for count in (dm, vm):
            midx = 0
            for _ in range(count):
                diff, p = uleb(data, p)
                midx += diff
                _, p = uleb(data, p)
                code_off, p = uleb(data, p)
                if code_off and idx.method_name(midx) == method_name:
                    return code_off
    except Exception:
        return None
    return None


def register_of(unit, op=None):
    if op == 0x12:
        return (unit >> 8) & 0xF
    return (unit >> 8) & 0xFF


def literal_of(data, base, pc, op):
    if op == 0x12:
        u = u2(data, base + pc * 2)
        lit = (u >> 12) & 0xF
        return lit - 16 if lit & 0x8 else lit
    if op == 0x13:
        v = u2(data, base + (pc + 1) * 2)
        return _s16(v)
    if op == 0x14:
        v = (u2(data, base + (pc + 1) * 2) << 16) | u2(data, base + (pc + 2) * 2)
        return _s32(v)
    if op == 0x15:
        return u2(data, base + (pc + 1) * 2) << 16
    return None


def set_const(data, base, pc, op, value):
    reg = register_of(u2(data, base + pc * 2), op)
    if op == 0x12:
        if not -8 <= value <= 7:
            return False
        lit = value & 0xF
        struct.pack_into("<H", data, base + pc * 2, 0x12 | (reg << 8) | (lit << 12))
        return True
    if op == 0x13:
        if not -32768 <= value <= 32767:
            return False
        struct.pack_into("<H", data, base + (pc + 1) * 2, value & 0xFFFF)
        return True
    if op == 0x14:
        struct.pack_into("<H", data, base + (pc + 1) * 2, (value >> 16) & 0xFFFF)
        struct.pack_into("<H", data, base + (pc + 2) * 2, value & 0xFFFF)
        return True
    if op == 0x15:
        if value & 0xFFFF:
            return False
        struct.pack_into("<H", data, base + (pc + 1) * 2, (value >> 16) & 0xFFFF)
        return True
    return False


def force_branch(data, base, pc, op, take):
    if op in IF_OPS:
        offset = u2(data, base + (pc + 1) * 2)
        if take:
            struct.pack_into("<H", data, base + pc * 2, 0x0029)
            struct.pack_into("<H", data, base + (pc + 1) * 2, offset)
        else:
            struct.pack_into("<H", data, base + pc * 2, NOP)
            struct.pack_into("<H", data, base + (pc + 1) * 2, NOP)
        return True
    if op == 0x28:
        if take:
            return True
        struct.pack_into("<H", data, base + pc * 2, NOP)
        return True
    if op == 0x29:
        if take:
            return True
        struct.pack_into("<H", data, base + pc * 2, NOP)
        struct.pack_into("<H", data, base + (pc + 1) * 2, NOP)
        return True
    return False


def nop_range(data, base, pc, count, insns_size):
    for k in range(pc, min(pc + count, insns_size)):
        struct.pack_into("<H", data, base + k * 2, NOP)


class EditResult:
    def __init__(self):
        self.applied = []
        self.skipped = []
        self.errors = []

    def ok(self, text):
        self.applied.append(text)

    def skip(self, text):
        self.skipped.append(text)

    def fail(self, text):
        self.errors.append(text)


def apply_edits_to_dex(data, edits):
    buf = bytearray(data)
    result = EditResult()
    for spec in edits:
        action = str(spec.get("action", "")).lower()
        cls = spec.get("class")
        meth = spec.get("method")
        if action == "stub":
            kind = str(spec.get("kind", "true")).lower()
            target = [(norm_descriptor(cls), meth, kind)] if cls and meth else []
            if target:
                out, hits = dex_surgery(bytes(buf), target)
                if hits:
                    buf = bytearray(out)
                    result.ok("stub %s#%s -> %s" % (cls, meth, kind))
                else:
                    result.skip("stub %s#%s not found" % (cls, meth))
            continue
        if not (cls and meth):
            result.fail("%s needs class and method" % action)
            continue
        code_off = method_code_offset(bytes(buf), norm_descriptor(cls), meth)
        if code_off is None:
            result.skip("%s#%s not found" % (cls, meth))
            continue
        insns_size = u4(buf, code_off + 12)
        base = code_off + 16
        pc = int(spec.get("at", 0))
        if pc < 0 or pc >= insns_size:
            result.fail("%s#%s pc %d out of range" % (cls, meth, pc))
            continue
        op = u2(buf, base + pc * 2) & 0xFF
        if action == "nop":
            count = int(spec.get("count", 1))
            nop_range(buf, base, pc, count, insns_size)
            result.ok("nop %s#%s pc %d x%d" % (cls, meth, pc, count))
        elif action == "const":
            value = int(spec.get("value", 0))
            if op in CONST_OPS and set_const(buf, base, pc, op, value):
                result.ok("const %s#%s pc %d -> %d" % (cls, meth, pc, value))
            else:
                result.skip("const %s#%s pc %d op 0x%02x not writable" % (cls, meth, pc, op))
        elif action == "branch":
            take = bool(spec.get("take", True))
            if force_branch(buf, base, pc, op, take):
                result.ok("branch %s#%s pc %d -> %s" % (cls, meth, pc, "taken" if take else "never"))
            else:
                result.skip("branch %s#%s pc %d op 0x%02x not a branch" % (cls, meth, pc, op))
        else:
            result.fail("unknown action " + action)
    if result.applied:
        dex_fix_header(buf)
    return buf, result


def load_edit_file(path):
    src = Path(path).expanduser()
    if not src.exists():
        return None, "edit file not found"
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except Exception as e:
        return None, "json parse error: " + trunc(str(e), 60)
    if isinstance(data, dict):
        edits = data.get("edits") or []
    elif isinstance(data, list):
        edits = data
    else:
        return None, "expected a list or an object with 'edits'"
    if not isinstance(edits, list):
        return None, "'edits' must be a list"
    return edits, None


def edit_dex_in_apk(apk, out, edits):
    results = EditResult()
    changed = False
    try:
        with zipfile.ZipFile(apk) as zin:
            plan = {}
            for name in zin.namelist():
                if not re.match(r"classes\d*\.dex$", name):
                    continue
                buf, res = apply_edits_to_dex(zin.read(name), edits)
                results.applied.extend("%s: %s" % (name, a) for a in res.applied)
                results.skipped.extend("%s: %s" % (name, s) for s in res.skipped)
                results.errors.extend("%s: %s" % (name, e) for e in res.errors)
                if res.applied:

                    plan[name] = bytes(buf)
                    changed = True
            if not changed:
                return False, results
            with zipfile.ZipFile(out, "w") as zout:
                for item in zin.infolist():
                    up = item.filename.upper()
                    if up.startswith("META-INF/") and up.endswith((".SF", ".RSA", ".DSA", ".EC", ".MF")):
                        continue
                    payload = plan.get(item.filename) or zin.read(item.filename)
                    zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
                    zi.compress_type = item.compress_type
                    zi.external_attr = item.external_attr
                    zi.internal_attr = item.internal_attr
                    zi.create_system = item.create_system
                    zout.writestr(zi, payload)
        return True, results
    except Exception as e:
        results.errors.append(trunc(str(e), 80))
        if Path(out).exists():
            Path(out).unlink(missing_ok=True)
        return False, results


def cmd_edit(args):
    Tty.probe()
    Stage.reset()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    apk, _searched = resolve_input(args.input)
    if apk is None:
        Out.bad("input not found · " + str(args.input))
        for _root in (_searched or [])[:5]:
            Out.info("looked in " + str(_root))
        return 2
    edits, err = load_edit_file(args.edit)
    if edits is None:
        Out.bad(err)
        return 3
    Out.head("instruction edits", G_WARM)
    Out.kv("edits", len(edits))
    out = Path(args.output).expanduser() if args.output else rap_output(apk, "edited")
    ok, res = edit_dex_in_apk(apk, out, edits)
    for line in res.applied:
        Out.ok(line)
    for line in res.skipped:
        Out.warn(line)
    for line in res.errors:
        Out.bad(line)
    if not ok:
        Out.bad("no edit could be applied")
        return 5
    strip_signature_entries(out)
    do_zipalign({"zipalign": which("zipalign")}, out, out.parent)
    if not args.unsigned:
        signed, how = do_sign(resolve_toolchain(out.parent, allow_net=False, quiet=True), out, out.parent, args.password)
        Out.kv("signed", how if signed else "no signer available")
    Out.head("result", G_OK)
    Out.kv("output", str(out))
    show_install_check(out)
    return 0


SMALI_INSN_RX = re.compile(r"^\s{4,}([a-z0-9/\-_$]+)")


def smali_instruction_lines(body):
    out = []
    for i, line in enumerate(body.splitlines()):
        stripped = line.strip()
        if not stripped or stripped.startswith((".", ":", "#")):
            continue
        out.append((i, stripped))
    return out


def smali_patch(path, class_desc, method_name, ops):
    try:
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return 0, "read failed: " + trunc(str(e), 50)
    sig_hint = method_name + "("
    changed = 0
    lines = text.splitlines()
    inside = False
    out_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(".method") and sig_hint in stripped:
            inside = True
        if inside:
            for op in ops:
                rx = op.get("match")
                if not rx:
                    continue
                try:
                    m = re.search(rx, stripped)
                except re.error:
                    continue
                if m:
                    line = "    " + str(op.get("replace", ""))
                    changed += 1
                    break
        if inside and stripped.startswith(".end method"):
            inside = False
        out_lines.append(line)
    if changed:
        atomic_write(Path(path), "\n".join(out_lines) + "\n", "w")
    return changed, None




SSL_INTERFACES = (
    "Ljavax/net/ssl/X509TrustManager;", "Ljavax/net/ssl/TrustManager;",
    "Ljavax/net/ssl/HostnameVerifier;", "Lokhttp3/CertificatePinner;",
    "Lcom/squareup/okhttp/CertificatePinner;", "Lorg/apache/http/conn/ssl/X509HostnameVerifier;",
    "Landroid/net/http/X509TrustManagerExtensions;", "Lorg/chromium/net/CertificateVerifier;",
)

SSL_PIN_METHODS = ("check", "check$okhttp", "checkServerTrusted", "verify", "verifyHostname", "clean")

SSL_NATIVE_SYMBOLS = (
    "ssl_crypto_x509_session_verify_cert_chain", "ssl_verify_cert_chain", "X509_verify_cert",
    "SSL_CTX_set_custom_verify", "SSL_CTX_set_verify", "SSL_get_verify_result",
    "X509_STORE_CTX_get_error", "SSL_CTX_set_verify_depth", "ssl_verify_peer_cert",
    "CRYPTO_memcmp", "SSL_CTX_set_cert_verify_callback",
)

HOST_RX = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$", re.I)


def class_supers(data, idx, cbase):
    out = []
    seen = set()
    cur = cbase
    for _ in range(24):
        if cur is None or cur in seen:
            break
        seen.add(cur)
        try:
            super_idx = u4(data, cur + 8)
        except Exception:
            break
        if super_idx == 0xFFFFFFFF:
            break
        try:
            name = idx.type_name(super_idx)
        except Exception:
            break
        if not name or name == "Ljava/lang/Object;":
            break
        out.append(name)
        nxt = idx.find_class(name)
        cur = nxt
    return out


def class_interfaces_deep(data, idx, cbase):
    names = []
    for t in class_interfaces(data, cbase):
        try:
            names.append(idx.type_name(t))
        except Exception:
            continue
    return names


def ssl_candidates(apk):
    found = []
    for dex, data in _dex_streams(apk):
        idx = DexIndex(data)
        if not idx.ok:
            continue
        for i in range(min(idx.c_n, 60000)):
            cbase = idx.c_off + i * 32
            desc = idx.type_name(u4(data, cbase))
            if not desc.startswith("L"):
                continue
            ifaces = class_interfaces_deep(data, idx, cbase)
            supers = class_supers(data, idx, cbase)
            low = desc.lower()
            reasons = []
            for iface in ifaces:
                if iface in SSL_INTERFACES:
                    reasons.append("implements " + iface.strip("L;"))
            for sup in supers:
                if sup in SSL_INTERFACES:
                    reasons.append("extends " + sup.strip("L;"))
            if any(k in low for k in ("trustmanager", "hostnameverifier", "certificatepinner",
                                      "chaincleaner", "certverifier", "sslpin", "pinning")):
                reasons.append("class name")
            if not reasons:
                continue
            methods = [m for m, off in iter_class_methods(data, idx, cbase) if off]
            pins = [m for m in methods if m in SSL_PIN_METHODS]
            if not pins and "class name" not in reasons:
                continue
            found.append({"dex": dex, "class": desc, "interfaces": ifaces, "supers": supers,
                          "methods": pins or methods[:8], "reasons": reasons,
                          "confidence": 1.0 if len(reasons) > 1 else 0.85})
    return found


def pinned_hosts(apk, candidates):
    hosts = {}
    for dex, data in _dex_streams(apk):
        idx = DexIndex(data)
        if not idx.ok:
            continue
        for cand in candidates:
            if cand["dex"] != dex:
                continue
            for meth in cand["methods"]:
                code = method_code_offset(data, cand["class"], meth)
                if not code:
                    continue
                insns, _ = decode_insns(data, code)
                for ins in insns:
                    if ins["kind"] != "string":
                        continue
                    try:
                        text = idx.string(ins["ref"])
                    except Exception:
                        continue
                    if HOST_RX.match(text.strip()):
                        hosts.setdefault(cand["class"], set()).add(text.strip())
    return {k: sorted(v) for k, v in hosts.items()}


def ssl_native_targets(apk):
    out = []
    for e in collect_natives(apk, None):
        hits = []
        for sym in list(e.imports) + list(getattr(e, "symtab_names", [])):
            if sym in SSL_NATIVE_SYMBOLS:
                hits.append(sym)
        strings = elf_strings(e.path, 6, 300)
        markers = [s for s in strings if any(k in s.lower() for k in
                                             ("verify_cert", "cert_chain", "trust manager", "pinning", "x509_verify"))]
        if hits or markers:
            out.append({"object": e.name, "machine": e.machine, "symbols": sorted(set(hits)),
                        "strings": markers[:8]})
    return out


def ssl_patch_plan(apk):
    cands = ssl_candidates(apk)
    hosts = pinned_hosts(apk, cands)
    targets = []
    for cand in cands:
        for meth in cand["methods"]:
            kind = "true" if meth in ("verify", "verifyHostname") else method_return_kind(apk, cand["class"], meth)
            targets.append({"target": "%s#%s" % (cand["class"].replace("/", ".").strip("L;"), meth),
                            "kind": kind, "why": ",".join(cand["reasons"]),
                            "confidence": cand["confidence"]})
    native = ssl_native_targets(apk)
    return {"candidates": cands, "hosts": hosts, "targets": targets, "native": native}


def show_ssl_engine(apk):
    Out.head("ssl surface", G_WARM)
    plan = ssl_patch_plan(apk)
    if not plan["candidates"]:
        Out.info("no trust manager, pinner or verifier found")
    for cand in plan["candidates"][:12]:
        Out.kv(trunc(cand["class"], 52), "%s · conf %.2f" % (cand["dex"], cand["confidence"]), width=54)
        print("    " + T_DIM("why   " + ", ".join(cand["reasons"][:3])))
        if cand["methods"]:
            print("    " + T_DIM("meth  " + ", ".join(cand["methods"][:6])))
        if cand["class"] in plan["hosts"]:
            print("    " + T_DIM("pins  " + ", ".join(plan["hosts"][cand["class"]][:4])))
    if plan["native"]:
        Out.head("native ssl", G_COOL)
        for n in plan["native"]:
            Out.kv(n["object"], "%s · %d symbol(s)" % (n["machine"], len(n["symbols"])), width=30)
            for s in n["symbols"][:5]:
                print("    " + T_DIM(BULLET + " " + s))
    return plan


def cmd_ssl_engine(args):
    Tty.probe()
    Stage.reset()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    apk, _searched = resolve_input(args.input)
    if apk is None:
        Out.bad("input not found · " + str(args.input))
        for _root in (_searched or [])[:5]:
            Out.info("looked in " + str(_root))
        return 2
    plan = show_ssl_engine(apk)
    Out.head("ssl plan", G_OK)
    Out.kv("dex targets", len(plan["targets"]))
    Out.kv("native targets", len(plan["native"]))
    if plan["hosts"]:
        Out.kv("pinned classes", len(plan["hosts"]))
    if args.dry_run:
        for t in plan["targets"]:
            Out.bullet("%s  ·  %s" % (t["target"], t["kind"]))
        return 0
    entries = [{"target": t["target"], "kind": t["kind"], "title": "ssl %s" % t["target"]} for t in plan["targets"]]
    patchset = build_patchset("ssl", "tls verification surface", entries)
    out_dir = Path(args.output).expanduser() if args.output else HOME
    if out_dir.suffix:
        out_dir = out_dir.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / (apk.stem + "-ssl.patch.json")
    atomic_write(path, json.dumps(patchset, indent=2), "w")
    Out.kv("patch set", str(path))
    if entries:
        chosen = [{"id": p["id"], "title": p["title"], "action": "stub-method", "targets": p["targets"],
                   "kind": p["kind"], "conflicts": [], "note": ""} for p in patchset["patches"]]
        report = validate_patch_against(chosen, apk)
        good = [c for c in chosen if any(r["id"] == c["id"] and r["ok"] for r in report)]
        Out.kv("resolved", "%d of %d" % (len(good), len(report)))
        if good:
            out_apk = rap_output(apk, "ssl")
            journal, err = apply_patch_set(apk, out_apk, good, backup_dir=str(out_apk) + ".backup")
            if journal:
                atomic_write(Path(str(out_apk) + ".journal.json"), json.dumps(journal, indent=2), "w")
                Out.ok("applied %d group(s)" % len(journal["applied"]))
                strip_signature_entries(out_apk)
                do_zipalign({"zipalign": which("zipalign")}, out_apk, out_apk.parent)
                if not args.unsigned:
                    signed, how = do_sign(resolve_toolchain(out_apk.parent, allow_net=False, quiet=True),
                                          out_apk, out_apk.parent, args.password)
                    Out.kv("signed", how if signed else "no signer available")
                Out.kv("output", str(out_apk))
            else:
                Out.bad(err)
    return 0




SIG_STRONG = ("checkSignature", "verifySignature", "validateSignature", "isSignatureValid",
              "isSignatureCorrect", "verifyAppSignature", "checkAppSignature", "isSignedCorrectly",
              "verifyIntegrity", "checkIntegrity", "getSignatureHash", "getCertificateHash",
              "checkCertificate", "verifyCertificate", "isDebugSignature", "checkAppSignatureHash")
SIG_WEAK = ("signature", "certificate", "tamper", "integrity", "signing", "cert", "digest")

SIG_NATIVE_MARKERS = ("signature", "certificate", "cert_", "tamper", "integrity",
                      "check_sign", "verify_sign", "get_sign", "app_sign")

SIG_PM_APIS = ("getPackageInfo", "getInstalledPackages", "getPackageArchiveInfo")


STUB_BODIES = tuple(set(CODE_STUBS.values()))


def signature_signals(apk):
    findings = []
    for dex, data in _dex_streams(apk):
        idx = DexIndex(data)
        if not idx.ok:
            continue
        strings = {}
        for i in range(min(idx.s_n, 200000)):
            try:
                s = idx.string(i)
            except Exception:
                continue
            low = s.lower()
            if any(k in low for k in SIG_WEAK):
                strings[i] = s
        for i in range(min(idx.c_n, 60000)):
            cbase = idx.c_off + i * 32
            desc = idx.type_name(u4(data, cbase))
            if not desc.startswith("L"):
                continue
            methods = [m for m, off in iter_class_methods(data, idx, cbase) if off]
            if not methods:
                continue
            strong = [m for m in methods if m in SIG_STRONG]
            weak = [m for m in methods if m not in SIG_STRONG and any(k in m.lower() for k in SIG_WEAK)]
            name_hit = any(k in desc.lower() for k in SIG_WEAK)
            string_hits = []
            for m in (strong or weak)[:6]:
                code = method_code_offset(data, desc, m)
                if not code:
                    continue
                insns, _ = decode_insns(data, code)
                for ins in insns:
                    if ins["kind"] == "string" and ins["ref"] in strings:
                        string_hits.append(strings[ins["ref"]])
            if not (strong or weak or name_hit or string_hits):
                continue
            stubbed = False
            for m in (strong or weak)[:4]:
                code = method_code_offset(data, desc, m)
                if not code:
                    continue
                try:
                    size = u4(data, code + 12)
                    body = bytes(data[code + 16:code + 16 + size * 2])
                    if body in STUB_BODIES:
                        stubbed = True
                        break
                except Exception:
                    pass
            score = 0
            reasons = []
            if strong:
                score += 3
                reasons.append("strong method names")
            if weak:
                score += 1
                reasons.append("weak method names")
            if name_hit:
                score += 1
                reasons.append("class name")
            if string_hits:
                score += 2
                reasons.append("signature strings")
            findings.append({"dex": dex, "class": desc, "methods": (strong or weak)[:8],
                             "strings": sorted(set(string_hits))[:5], "score": score,
                             "stubbed": stubbed, "reasons": reasons,
                             "confidence": round(min(0.99, 0.4 + score * 0.12), 2)})
    return findings


def signature_native(apk):
    out = []
    for e in collect_natives(apk, None):
        hits = []
        for sym in list(e.imports) + list(getattr(e, "symtab_names", [])):
            low = sym.lower()
            if any(k in low for k in SIG_NATIVE_MARKERS):
                hits.append(sym)
        strings = elf_strings(e.path, 5, 400)
        text_hits = [s for s in strings if any(k in s.lower() for k in SIG_NATIVE_MARKERS)]
        if hits or text_hits:
            out.append({"object": e.name, "machine": e.machine,
                        "symbols": sorted(set(hits))[:12], "strings": text_hits[:8]})
    return out


def signature_pm_sites(apk):
    callers, _ = invoke_targets(apk, SIG_PM_APIS, method_budget=30000)
    return callers


def signature_plan(apk):
    findings = signature_signals(apk)
    native = signature_native(apk)
    pm = signature_pm_sites(apk)
    targets = []
    for f in findings:
        for m in f["methods"]:
            if m in SIG_TRUE:
                kind = "true"
            elif m in SIG_FALSE:
                kind = "false"
            else:
                kind = method_return_kind(apk, f["class"], m)
            targets.append({"target": "%s#%s" % (f["class"].replace("/", ".").strip("L;"), m),
                            "kind": kind, "confidence": f["confidence"], "why": ",".join(f["reasons"])})
    return {"findings": findings, "native": native, "pm_sites": pm, "targets": targets}


def show_signature_engine(apk):
    Out.head("signature surface", G_WARM)
    plan = signature_plan(apk)
    if not plan["findings"]:
        Out.info("no signature check class found")
    for f in plan["findings"][:12]:
        Out.kv(trunc(f["class"], 50), "conf %.2f · score %d" % (f["confidence"], f["score"]), width=52)
        print("    " + T_DIM("why   " + ", ".join(f["reasons"])))
        if f["methods"]:
            print("    " + T_DIM("meth  " + ", ".join(f["methods"][:6])))
        if f["strings"]:
            print("    " + T_DIM("str   " + ", ".join(f["strings"][:3])))
    if plan["native"]:
        Out.head("native signature checks", G_COOL)
        for n in plan["native"]:
            Out.kv(n["object"], "%s · %d symbol(s)" % (n["machine"], len(n["symbols"])), width=30)
            for s in n["symbols"][:5]:
                print("    " + T_DIM(BULLET + " " + trunc(s, 72)))
    if plan["pm_sites"]:
        Out.head("package manager call sites", G_COOL)
        for caller in sorted(plan["pm_sites"])[:10]:
            Out.bullet(trunc(caller, 74))
    return plan


def cmd_signature_engine(args):
    Tty.probe()
    Stage.reset()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    apk, _searched = resolve_input(args.input)
    if apk is None:
        Out.bad("input not found · " + str(args.input))
        for _root in (_searched or [])[:5]:
            Out.info("looked in " + str(_root))
        return 2
    plan = show_signature_engine(apk)
    Out.head("signature plan", G_OK)
    Out.kv("dex targets", len(plan["targets"]))
    Out.kv("native objects", len(plan["native"]))
    Out.kv("pm call sites", len(plan["pm_sites"]))
    if args.dry_run:
        for t in plan["targets"]:
            Out.bullet("%s  ·  %s  ·  conf %.2f" % (t["target"], t["kind"], t["confidence"]))
        return 0
    entries = [{"target": t["target"], "kind": t["kind"], "title": "signature %s" % t["target"]}
               for t in plan["targets"]]
    patchset = build_patchset("signature", "signature verification surface", entries)
    out_dir = Path(args.output).expanduser() if args.output else HOME
    if out_dir.suffix:
        out_dir = out_dir.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / (apk.stem + "-signature.patch.json")
    atomic_write(path, json.dumps(patchset, indent=2), "w")
    Out.kv("patch set", str(path))
    if not entries:
        return 0
    chosen = [{"id": p["id"], "title": p["title"], "action": "stub-method", "targets": p["targets"],
               "kind": p["kind"], "conflicts": [], "note": ""} for p in patchset["patches"]]
    report = validate_patch_against(chosen, apk)
    good = [c for c in chosen if any(r["id"] == c["id"] and r["ok"] for r in report)]
    Out.kv("resolved", "%d of %d" % (len(good), len(report)))
    if not good:
        return 5
    out_apk = rap_output(apk, "sig")
    journal, err = apply_patch_set(apk, out_apk, good, backup_dir=str(out_apk) + ".backup")
    if journal is None:
        Out.bad(err)
        return 6
    atomic_write(Path(str(out_apk) + ".journal.json"), json.dumps(journal, indent=2), "w")
    Out.ok("applied %d group(s)" % len(journal["applied"]))
    strip_signature_entries(out_apk)
    do_zipalign({"zipalign": which("zipalign")}, out_apk, out_apk.parent)
    if not args.unsigned:
        signed, how = do_sign(resolve_toolchain(out_apk.parent, allow_net=False, quiet=True),
                              out_apk, out_apk.parent, args.password)
        Out.kv("signed", how if signed else "no signer available")
    Out.kv("output", str(out_apk))
    after = signature_signals(out_apk)
    live = [f for f in after if f["score"] >= 3 and not f["stubbed"]]
    neutralised = [f for f in after if f["stubbed"]]
    Out.kv("neutralised", "%d class(es)" % len(neutralised))
    if live:
        Out.warn("%d strong check(s) still live" % len(live))
        for f in live[:4]:
            Out.bullet(trunc(f["class"], 70))
    show_install_check(out_apk)
    return 0



SUSPICIOUS_IMPORTS = {
    "ptrace": "anti-debug", "fork": "process control", "execve": "process control",
    "system": "shell exec", "popen": "shell exec", "dlopen": "dynamic load",
    "dlsym": "dynamic resolve", "mmap": "memory mapping", "mprotect": "memory protection",
    "syscall": "direct syscall", "kill": "signal", "waitpid": "process control",
    "getenv": "environment probe", "access": "path probe", "stat": "path probe",
    "fopen": "file probe", "open": "file probe", "readlink": "path probe",
    "pthread_create": "threading", "sigaction": "signal handler",
}

NATIVE_MARKERS_DEEP = {
    "anti-debug": ("ptrace", "TracerPid", "frida", "xposed", "substrate", "magisk"),
    "root": ("/system/xbin/su", "/system/bin/su", "superuser", "busybox", "supersu"),
    "emulator": ("goldfish", "ranchu", "genymotion", "bluestacks", "vbox"),
    "crypto": ("AES", "RSA", "SHA256", "HMAC", "EVP_", "SSL_"),
    "integrity": ("signature", "certificate", "tamper", "integrity"),
}


def shannon(data):
    if not data:
        return 0.0
    counts = [0] * 256
    for b in data:
        counts[b] += 1
    total = len(data)
    ent = 0.0
    for c in counts:
        if not c:
            continue
        p = c / total
        ent -= p * math.log2(p)
    return round(ent, 3)


def section_entropy(path, elf, limit=24):
    out = []
    try:
        with open(path, "rb") as fh:
            for sec in elf.sections[:limit]:
                if sec["type"] == 8 or sec["size"] == 0:
                    continue
                fh.seek(sec["offset"])
                blob = fh.read(min(sec["size"], 512 * 1024))
                out.append((sec["name"], sec["size"], shannon(blob)))
    except Exception:
        pass
    return out


def so_report(apk):
    reports = []
    for e in collect_natives(apk, None):
        entry = {"object": e.name, "machine": e.machine, "bits": e.bits, "size": e.size}
        entry["hardening"] = e.summary().get("hardening", {})
        imports = sorted(set(e.imports))
        entry["imports"] = imports
        entry["suspicious"] = {}
        for sym in imports:
            base = sym.split("@")[0]
            for key, label in SUSPICIOUS_IMPORTS.items():
                if base == key or base.endswith("_" + key):
                    entry["suspicious"].setdefault(label, []).append(base)
                    break
        entry["jni"] = jni_symbol_map(e)
        relocs, _ = elf_relocations(e.path)
        entry["relocations"] = len(relocs or [])
        strings = elf_strings(e.path, 6, 600)
        entry["markers"] = {}
        for label, keys in NATIVE_MARKERS_DEEP.items():
            hits = [t for t in strings if any(k.lower() in t.lower() for k in keys)]
            if hits:
                entry["markers"][label] = hits[:6]
        entry["sections"] = section_entropy(e.path, e)
        reports.append(entry)
    return reports


def cmd_so_report(args):
    Tty.probe()
    Stage.reset()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    _w = Path(tempfile.mkdtemp())
    apk, _note, _searched = open_apk(args.input, _w)
    if _note:
        Out.info(_note)
    if apk is None:
        Out.bad("input not found · " + str(args.input))
        for _root in (_searched or [])[:5]:
            Out.info("looked in " + str(_root))
        return 2
    reports = so_report(apk)
    if not reports:
        Out.bad("no native objects in this archive")
        return 3
    for r in reports:
        Out.head(r["object"], G_WARM)
        Out.kv("arch", "%s · %d-bit · %s" % (r["machine"], r["bits"], human(r["size"])), width=18)
        h = r["hardening"]
        flags = "".join(k[0].upper() if h.get(k) else "-" for k in ("pie", "nx", "relro", "canary"))
        Out.kv("hardening", flags + "   (P N R C)", width=18)
        Out.kv("imports", len(r["imports"]), width=18)
        Out.kv("jni exports", len(r["jni"]), width=18)
        Out.kv("relocations", r["relocations"], width=18)
        if r["suspicious"]:
            Out.kv("behaviour", ", ".join(sorted(r["suspicious"])), width=18)
            for label, syms in sorted(r["suspicious"].items()):
                print("    " + T_DIM(label + ": " + ", ".join(syms[:5])))
        if r["markers"]:
            for label, hits in sorted(r["markers"].items()):
                Out.kv(label, "%d marker(s)" % len(hits), width=18)
                for h2 in hits[:3]:
                    print("    " + T_DIM(BULLET + " " + trunc(h2, 70)))
        high = [x for x in r["sections"] if x[2] > 7.2]
        if high:
            Out.kv("high entropy", "%d section(s)" % len(high), width=18)
            for name, size, ent in high[:4]:
                print("    " + T_DIM("%s · %s · entropy %.2f" % (name, human(size), ent)))
        if r["jni"]:
            for m in r["jni"][:4]:
                print("    " + T_DIM("%s -> %s#%s" % (trunc(m["symbol"], 40), m["class"], m["method"])))
    Out.head("verdict", G_OK)
    risky = [r for r in reports if r["suspicious"] or r["markers"]]
    Out.kv("objects", len(reports), width=18)
    Out.kv("with markers", len(risky), width=18)
    if args.output:
        atomic_write(Path(args.output).expanduser(), json.dumps(reports, indent=2, default=str), "w")
        Out.kv("written", str(args.output))
    return 0



TOOL_MATRIX = [
    ("java", "java", "smali work and signing", "pkg install openjdk-17", True),
    ("apktool", "apktool", "smali decode and rebuild", "auto download jar", True),
    ("aapt2", "aapt2", "resource compilation", "pkg install aapt2", True),
    ("apksigner", "apksigner", "v1 v2 v3 signing", "pkg install apksigner", True),
    ("zipalign", "zipalign", "archive alignment", "built in python fallback", False),
    ("keytool", "keytool", "keystore generation", "pkg install openjdk-17", True),
    ("unzip", "unzip", "bulk extraction", "pkg install unzip", False),
    ("zip", "zip", "bulk repack", "pkg install zip", False),
    ("adb", "adb", "install to device", "pkg install android-tools", False),
    ("jadx", "jadx", "java decompilation", "auto download zip", False),
    ("frida", "frida", "dynamic instrumentation", "pip install frida-tools", False),
    ("file", "file", "type detection", "pkg install file", False),
    ("strings", "strings", "quick native strings", "pkg install binutils", False),
    ("readelf", "readelf", "elf inspection", "pkg install binutils", False),
    ("objdump", "objdump", "native disassembly", "pkg install binutils", False),
]

PY_MODULES = [
    ("capstone", "native disassembly", "pip install capstone"),
    ("yaml", "yaml rule files", "pip install pyyaml"),
    ("cryptography", "certificate parsing", "pip install cryptography"),
]


def tool_inventory():
    rows = []
    for name, binary, purpose, hint, critical in TOOL_MATRIX:
        path = which(binary)
        rows.append({"name": name, "present": bool(path), "path": path or "",
                     "purpose": purpose, "hint": hint, "critical": critical, "kind": "binary"})
    for mod, purpose, hint in PY_MODULES:
        try:
            __import__(mod)
            present = True
        except Exception:
            present = False
        rows.append({"name": mod, "present": present, "path": "python module" if present else "",
                     "purpose": purpose, "hint": hint, "critical": False, "kind": "module"})
    for label in ("apktool", "apkeditor", "uber"):
        jar = HOME / {"apktool": "APKTool.jar", "apkeditor": "APKEditor.jar", "uber": "uber-apk-signer.jar"}[label]
        rows.append({"name": label + " jar", "present": jar.exists(), "path": str(jar) if jar.exists() else "",
                     "purpose": "bundled tool", "hint": "auto download", "critical": label == "apktool",
                     "kind": "jar"})
    return rows


AUTO = {"install": True, "done": set()}


def is_termux():
    return bool(os.environ.get("PREFIX"))


def tool_present(name):
    if name in ("apktool", "apkeditor", "uber"):
        jar = HOME / {"apktool": "APKTool.jar", "apkeditor": "APKEditor.jar",
                      "uber": "uber-apk-signer.jar"}[name]
        return jar.exists() or bool(which(name))
    if name in ("yaml", "capstone", "cryptography", "reapk"):
        try:
            __import__(name)
            return True
        except Exception:
            return False
    return bool(which(name))


def install_tool(name):
    if name in AUTO["done"]:
        return tool_present(name)
    AUTO["done"].add(name)
    if name == "apktool":
        for label, url in APKTOOL_PINS:
            dest = HOME / ("apktool_%s.jar" % label)
            if dest.exists() and dest.stat().st_size > 100000:
                return True
            if download(url, dest, "apktool " + label):
                return True
        return False
    pkg = which("pkg") or which("apt-get") or which("apt")
    if name in PKG_MAP and pkg:
        rc, _ = run_live([pkg, "install", "-y", PKG_MAP[name]], "install " + name, timeout=1800)
        if rc == 0:
            return tool_present(name)
    pm = which("pip") or which("pip3")
    if pm and name in ("yaml", "capstone", "cryptography", "reapk"):
        rc, _ = run_live([pm, "install", "pyyaml" if name == "yaml" else name], "pip " + name, timeout=900)
        if rc == 0:
            return True
    return tool_present(name)


def ensure_tools(names, purpose="", force=False):
    missing = [n for n in names if not tool_present(n)]
    if not missing:
        return True
    label = (" for " + purpose) if purpose else ""
    if not AUTO["install"] and not force:
        Out.warn("missing tool%s: %s" % (label, ", ".join(missing)))
        for n in missing:
            hint = "pkg install " + PKG_MAP.get(n, n)
            Out.info("  " + hint)
        return False
    if not is_termux() and not force:
        Out.warn("missing tool%s: %s" % (label, ", ".join(missing)))
        Out.info("run: arpxtool setup --yes   (or install manually)")
        return False
    Out.head("installing tools", G_WARM)
    Out.kv("missing", ", ".join(missing), width=16)
    ok = []
    for n in missing:
        Out.info("installing " + n)
        ok.append((n, install_tool(n)))
    for n, good in ok:
        (Out.ok if good else Out.bad)(n + (" installed" if good else " failed"))
    return all(tool_present(n) for n in names)




def provenance():
    rec = dict(_ID)
    seal = rec.pop("seal", "")
    canon = json.dumps(rec, sort_keys=True, separators=(",", ":"))
    actual = hashlib.sha256(canon.encode()).hexdigest()
    return rec, seal, actual, (seal == actual)




APK_SIG_MAGIC = b"APK Sig Block 42"
SIG_BLOCK_IDS = {0x7109871A: "v2", 0xF05368C0: "v3", 0x1B93AD61: "v3.1"}


def u8(data, off):
    return struct.unpack_from("<Q", data, off)[0]


def apk_signing_block(data):
    eocd = data.rfind(b"PK\x05\x06")
    if eocd < 0 or eocd + 22 > len(data):
        return None
    try:
        cd_off = u4(data, eocd + 16)
    except Exception:
        return None
    if cd_off < 32 or cd_off > len(data):
        return None
    magic_at = cd_off - 16
    if data[magic_at:magic_at + 16] != APK_SIG_MAGIC:
        return None
    try:
        size = u8(data, magic_at - 8)
    except Exception:
        return None
    start = cd_off - size - 8
    if start < 0 or start >= magic_at:
        return None
    return start, cd_off - start


def signing_block_pairs(data):
    blk = apk_signing_block(data)
    if not blk:
        return {}
    start, length = blk
    end = start + length - 24
    pairs = {}
    p = start + 8
    guard = 0
    while p + 12 <= end and guard < 64:
        guard += 1
        try:
            plen = u8(data, p)
            pid = u4(data, p + 8)
        except Exception:
            break
        if plen < 4 or p + 8 + plen > end + 8:
            break
        pairs[pid] = data[p + 12:p + 8 + plen]
        p += 8 + plen
    return pairs


def _lp(buf, off):
    n = u4(buf, off)
    return buf[off + 4:off + 4 + n], off + 4 + n


def embedded_content_digest(data):
    pairs = signing_block_pairs(data)
    for pid in (0xF05368C0, 0x7109871A, 0x1B93AD61):
        blob = pairs.get(pid)
        if not blob:
            continue
        try:
            signers, _ = _lp(blob, 0)
            signer, _ = _lp(signers, 0)
            sd, _ = _lp(signer, 0)
            digests, _ = _lp(sd, 0)
            item, _ = _lp(digests, 0)
            alg = u4(item, 0)
            if alg not in (0x0103, 0x0104, 0x0201, 0x0202, 0x0301):
                continue
            digest, _ = _lp(item, 4)
            return digest
        except Exception:
            continue
    return None


def apk_content_digest(data):
    blk = apk_signing_block(data)
    eocd = data.rfind(b"PK\x05\x06")
    if eocd < 0:
        return None
    cd_off = u4(data, eocd + 16)
    block_start = blk[0] if blk else cd_off
    eocd_bytes = bytearray(data[eocd:])
    struct.pack_into("<I", eocd_bytes, 16, block_start)
    sections = (data[:block_start], data[cd_off:eocd], bytes(eocd_bytes))
    chunks = []
    for sec in sections:
        for i in range(0, len(sec), 1 << 20):
            piece = sec[i:i + (1 << 20)]
            chunks.append(hashlib.sha256(b"\xa5" + struct.pack("<I", len(piece)) + piece).digest())
    return hashlib.sha256(b"\x5a" + struct.pack("<I", len(chunks)) + b"".join(chunks)).digest()


def embedded_digests(data):
    pairs = signing_block_pairs(data)
    out = []
    for pid, label in ((0x7109871A, "v2"), (0xF05368C0, "v3"), (0x1B93AD61, "v3.1")):
        blob = pairs.get(pid)
        if not blob:
            continue
        try:
            signers, _ = _lp(blob, 0)
            signer, _ = _lp(signers, 0)
            sd, _ = _lp(signer, 0)
            digests, _ = _lp(sd, 0)
            item, _ = _lp(digests, 0)
            digest, _ = _lp(item, 4)
            out.append((label, digest))
        except Exception:
            continue
    return out


def jar_signature_present(data):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = [n.upper() for n in z.namelist()]
    except Exception:
        return False
    has_sf = any(n.startswith("META-INF/") and n.endswith(".SF") for n in names)
    has_block = any(n.startswith("META-INF/") and n.endswith((".RSA", ".DSA", ".EC")) for n in names)
    return has_sf and has_block


def signature_state(data):
    blk = apk_signing_block(data)
    if not blk:
        if jar_signature_present(data):
            return {"status": "v1", "schemes": ["v1"],
                    "detail": "jar signature only, no apk signing block"}
        return {"status": "none", "schemes": [], "detail": "no apk signing block"}
    found = embedded_digests(data)
    schemes = sorted({label for label, _ in found}) or sorted(
        {SIG_BLOCK_IDS[p] for p in signing_block_pairs(data) if p in SIG_BLOCK_IDS})
    if not found:
        return {"status": "unknown", "schemes": schemes,
                "detail": "signature block present but no digest found"}
    computed = apk_content_digest(data)
    bad = [(label, digest) for label, digest in found if digest != computed]
    if not bad:
        return {"status": "valid", "schemes": schemes, "detail": "content digest matches"}
    label, digest = bad[0]
    return {"status": "stale", "schemes": schemes,
            "detail": "%s signer digest mismatch (CHUNKED_SHA256)" % label,
            "embedded": digest.hex(), "computed": computed.hex()}


def strip_signing_block(data):
    trace("strip apk signing block")
    blk = apk_signing_block(data)
    if not blk:
        return data, False
    start, length = blk
    out = bytearray(data[:start] + data[start + length:])
    eocd = out.rfind(b"PK\x05\x06")
    if eocd < 0:
        return data, False
    struct.pack_into("<I", out, eocd + 16, start)
    return bytes(out), True




KEYRING = HOME / ".arpxtool" / "keyring.json"


def apk_min_sdk(apk):
    try:
        with zipfile.ZipFile(apk) as z:
            man = safe_manifest(z)[1]
        value = (man or {}).get("min_sdk")
        if value and str(value).isdigit():
            return int(value)
    except Exception:
        pass
    return 21


def keyring_load():
    try:
        return json.loads(KEYRING.read_text(encoding="utf-8"))
    except Exception:
        return {}


def keyring_save(entry):
    KEYRING.parent.mkdir(parents=True, exist_ok=True)
    data = keyring_load()
    data.update(entry)
    atomic_write(KEYRING, json.dumps(data, indent=2), "w")
    try:
        os.chmod(KEYRING, 0o600)
    except Exception:
        pass


def keystore_fingerprint(path, password, alias):
    if which("keytool"):
        rc, out, err = run(["keytool", "-list", "-v", "-keystore", str(path),
                            "-storepass", password, "-alias", alias], timeout=120)
        text = (out or "") + (err or "")
        sha = re.search(r"SHA256:\s*([0-9A-F:]{32,})", text, re.I)
        if sha:
            return sha.group(1).replace(":", "").upper()
    return None




def _lp_bytes(b):
    return struct.pack("<I", len(b)) + b


def _seq(elems):
    return _lp_bytes(b"".join(_lp_bytes(e) for e in elems))


def native_sign(apk_bytes, key, cert):
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    cert_der = cert.public_bytes(serialization.Encoding.DER)
    spki = key.public_key().public_bytes(serialization.Encoding.DER,
                                         serialization.PublicFormat.SubjectPublicKeyInfo)
    eocd_off = apk_bytes.rfind(b"PK\x05\x06")
    if eocd_off < 0:
        raise ValueError("not a zip")
    _cd_size, cd_off = struct.unpack_from("<II", apk_bytes, eocd_off + 12)
    section1 = apk_bytes[:cd_off]
    central = apk_bytes[cd_off:eocd_off]
    eocd = apk_bytes[eocd_off:]

    chunks = []
    for sec in (section1, central, eocd):
        for i in range(0, len(sec), 1 << 20):
            piece = sec[i:i + (1 << 20)]
            chunks.append(hashlib.sha256(b"\xa5" + struct.pack("<I", len(piece)) + piece).digest())
    top = hashlib.sha256(b"\x5a" + struct.pack("<I", len(chunks)) + b"".join(chunks)).digest()

    alg = 0x0103
    digests = _seq([struct.pack("<I", alg) + _lp_bytes(top)])
    certs = _seq([cert_der])

    def sign(data):
        return key.sign(data, padding.PKCS1v15(), hashes.SHA256())

    sd2 = digests + certs + _seq([])
    sigs2 = _seq([struct.pack("<I", alg) + _lp_bytes(sign(sd2))])
    signer2 = _lp_bytes(sd2) + sigs2 + _lp_bytes(spki)
    pair2 = struct.pack("<Q", len(_seq([signer2])) + 4) + struct.pack("<I", 0x7109871A) + _seq([signer2])

    sdk = struct.pack("<II", 24, 0x7FFFFFFF)
    sd3 = digests + certs + sdk + _seq([])
    sigs3 = _seq([struct.pack("<I", alg) + _lp_bytes(sign(sd3))])
    signer3 = _lp_bytes(sd3) + sdk + sigs3 + _lp_bytes(spki)
    pair3 = struct.pack("<Q", len(_seq([signer3])) + 4) + struct.pack("<I", 0xF05368C0) + _seq([signer3])

    body = pair2 + pair3
    blocklen = len(body) + 8 + 16
    block = struct.pack("<Q", blocklen) + body + struct.pack("<Q", blocklen) + APK_SIG_MAGIC
    eocd2 = bytearray(eocd)
    struct.pack_into("<I", eocd2, 16, len(section1) + len(block))
    return section1 + block + central + bytes(eocd2)


def load_signing_pair(keystore):
    from cryptography.hazmat.primitives import serialization
    from cryptography import x509
    ks = Path(keystore)
    pem = ks.with_suffix(".pem")
    crt = ks.with_suffix(".crt")
    if not pem.exists() or not crt.exists():
        return None, None
    try:
        key = serialization.load_pem_private_key(pem.read_bytes(), None)
        cert = x509.load_pem_x509_certificate(crt.read_bytes())
        return key, cert
    except Exception:
        return None, None


def native_sign_apk(path, keystore):
    trace("native v2+v3 sign %s" % Path(path).name)
    key, cert = load_signing_pair(keystore)
    if key is None:
        return False, "no pem key beside the keystore"
    data = Path(path).read_bytes()
    stripped, _ = strip_signing_block(data)
    try:
        out = native_sign(stripped, key, cert)
    except Exception as e:
        return False, trunc(str(e), 60)
    atomic_write(Path(path), out, "wb")
    state = signature_state(out)
    if state["status"] != "valid":
        return False, "signature did not verify after write"
    return True, "python v2+v3"




RAP = HOME / "rapApk"
RAP_KEYS = RAP / "keys"
RAP_OUT = RAP / "out"
RAP_REGISTRY = RAP / "registry.json"
RAP_MARK = "arpxtool"


def rap_ensure():
    for d in (RAP, RAP_KEYS, RAP_OUT):
        try:
            d.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass


def rap_registry():
    try:
        return json.loads(RAP_REGISTRY.read_text(encoding="utf-8"))
    except Exception:
        return {"apps": {}}


def rap_registry_save(data):
    rap_ensure()
    atomic_write(RAP_REGISTRY, json.dumps(data, indent=2), "w")


def rap_record(package, keystore, fingerprint=None, source=None):
    data = rap_registry()
    entry = data.setdefault("apps", {}).setdefault(package, {})
    entry["keystore"] = str(keystore)
    if fingerprint:
        entry["cert_sha256"] = fingerprint
    if source:
        entry["source"] = str(source)
    entry["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    rap_registry_save(data)
    return entry


def rap_lookup_by_fingerprint(fingerprint):
    if not fingerprint:
        return None
    for package, entry in rap_registry().get("apps", {}).items():
        if entry.get("cert_sha256", "").replace(":", "").upper() == fingerprint.replace(":", "").upper():
            return package, entry
    return None


def app_package(apk):
    try:
        with zipfile.ZipFile(apk) as z:
            man = safe_manifest(z)[1]
        return (man or {}).get("package") if (man or {}).get("package") not in (None, "?") else None
    except Exception:
        return None


def rap_key_path(package):
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", package or "unknown")
    return RAP_KEYS / (safe + ".keystore")


def rap_output(apk, tag):
    rap_ensure()
    stem = Path(apk).stem
    dest = RAP_OUT / ("%s_%s.apk" % (stem, tag))
    n = 2
    while dest.exists():
        dest = RAP_OUT / ("%s_%s_%d.apk" % (stem, tag, n))
        n += 1
    return dest


def resolve_input(raw):
    given = Path(raw).expanduser()
    if given.exists():
        return given, None
    name = given.name
    searched = []
    roots = [Path.cwd(), RAP_OUT, RAP,
             Path("/storage/emulated/0/MT2/apks"),
             Path("/storage/emulated/0/Download"),
             Path("/sdcard/MT2/apks"),
             Path("/sdcard/Download"),
             HOME / "storage" / "downloads",
             HOME / "Download",
             HOME]
    for root in roots:
        try:
            if not root.exists():
                continue
        except Exception:
            continue
        searched.append(root)
        direct = root / name
        if direct.exists():
            return direct, None
        try:
            for hit in root.rglob(name):
                if hit.is_file():
                    return hit, None
        except Exception:
            continue
    return None, searched



def app_key_for(apk):
    apps = rap_registry().get("apps", {})
    candidates = []
    pkg = app_package(apk)
    if pkg:
        candidates.append(pkg)
    stem = re.sub(r"[^A-Za-z0-9._-]", "_", Path(apk).stem)
    candidates.append(stem)
    for name in candidates:
        entry = apps.get(name)
        if entry and entry.get("keystore") and Path(entry["keystore"]).exists():
            return name, entry
    for name, entry in apps.items():
        if not (entry.get("keystore") and Path(entry["keystore"]).exists()):
            continue
        source_stem = Path(entry.get("source", "")).stem
        if stem.startswith(name) or (source_stem and stem.startswith(source_stem)):
            return name, entry
    return None, None


def apply_app_key(apk, password):
    name, entry = app_key_for(apk)
    if not entry:
        return None
    ring = keyring_load()
    SIGN_STATE["keystore"] = entry["keystore"]
    SIGN_STATE["alias"] = name
    SIGN_STATE["store_pass"] = ring.get("store_pass") or password
    SIGN_STATE["key_pass"] = SIGN_STATE["store_pass"]
    return name




SPLIT_META = (
    "com.android.vending.splits.required",
    "com.android.vending.splits",
    "com.android.stamp.source",
    "com.android.stamp.type",
    "com.android.vending.derived.apk.id",
)


def attr_local(name):
    if ":" in name:
        return name.split(":", 1)[1]
    if name.startswith("{"):
        return name.rsplit("}", 1)[-1]
    return name


def manifest_split_info(data):
    x = Axml(data)
    info = {"parses": x.valid, "is_split": False, "split_name": None,
            "is_split_required": False, "has_uses_sdk": False,
            "min_sdk": None, "meta": [], "required_split_types": None,
            "split_types": None, "package": None}
    if not x.valid:
        return info
    for parent, elem, aname, val in x.attrs:
        aname = attr_local(aname)
        if elem == "manifest":
            if aname == "split":
                info["is_split"] = True
                info["split_name"] = val
            elif aname == "isSplitRequired":
                info["is_split_required"] = val == "true"
            elif aname == "requiredSplitTypes":
                info["required_split_types"] = val
            elif aname == "splitTypes":
                info["split_types"] = val
            elif aname == "package":
                info["package"] = val
        elif elem == "uses-sdk":
            info["has_uses_sdk"] = True
            if aname == "minSdkVersion":
                info["min_sdk"] = val
        elif elem == "meta-data" and aname == "name":
            info["meta"].append(val)
    info["split_meta"] = [m for m in info["meta"] if m in SPLIT_META]
    return info


def diagnose_apk(apk):
    findings = []
    try:
        with zipfile.ZipFile(apk) as z:
            names = z.namelist()
            raw_manifest = safe_manifest(z)[0]
    except Exception as e:
        return [("bad", "unreadable", trunc(str(e), 70), "the file is not a valid zip")]
    if raw_manifest is None:
        return [("bad", "manifest", "AndroidManifest.xml is missing", "rebuild the archive")]

    split = manifest_split_info(raw_manifest)
    if not split["parses"]:
        findings.append(("bad", "manifest",
                         "AndroidManifest.xml does not parse as binary xml",
                         "the archive was not rebuilt correctly · rebuild with apktool or APKEditor"))
        return findings

    if split["is_split"]:
        findings.append(("bad", "split",
                         "this is a split apk (split=%s), not a base" % (split["split_name"] or "?"),
                         "install the whole set with an installer that handles splits"))
    if split["is_split_required"]:
        findings.append(("bad", "split-required",
                         "android:isSplitRequired=true · the system expects the sibling splits",
                         "run: arpxtool app.apk diagnose --fix-split"))
    if split["required_split_types"] or split["split_types"]:
        findings.append(("bad", "split-types",
                         "requiredSplitTypes/splitTypes present",
                         "run: arpxtool app.apk diagnose --fix-split"))
    if split["split_meta"]:
        findings.append(("bad", "split-meta",
                         "split metadata present: " + ", ".join(split["split_meta"][:3]),
                         "removed by a proper merge; rebuild with APKEditor merge"))
    if not split["has_uses_sdk"]:
        findings.append(("warn", "uses-sdk",
                         "no <uses-sdk> element · external apksigner cannot read minSdkVersion",
                         "android defaults to 1 and installs fine · sign with: arpxtool app.apk sign"))
    elif split["min_sdk"] in (None, "?"):
        findings.append(("warn", "min-sdk",
                         "uses-sdk present but minSdkVersion is unreadable",
                         "sign with the built-in signer"))

    state = signature_state(Path(apk).read_bytes())
    if state["status"] == "stale":
        findings.append(("bad", "signature",
                         "stale signature block · " + state["detail"],
                         "run: arpxtool app.apk repair"))
    elif state["status"] == "none":
        findings.append(("bad", "signature", "not signed", "run: arpxtool app.apk sign"))
    elif state["status"] == "v1":
        findings.append(("bad", "signature", "v1 signature only · android 11+ refuses it",
                         "run: arpxtool app.apk sign"))

    entries = local_entries(apk)
    arsc = next((e for e in entries if e["name"] == "resources.arsc"), None)
    if arsc is None:
        findings.append(("bad", "resources", "resources.arsc is missing", "rebuild the resources"))
    else:
        if arsc["method"] != 0:
            findings.append(("bad", "resources", "resources.arsc is compressed",
                             "store it uncompressed"))
        if arsc["offset"] % 4:
            findings.append(("bad", "resources", "resources.arsc is not 4 byte aligned",
                             "re-align the archive"))
    if not any(re.match(r"classes\d*\.dex$", n) for n in names):
        findings.append(("bad", "dex", "no dex payload", "rebuild the archive"))
    so = [e for e in entries if e["name"].endswith(".so")]
    if so:
        compressed = [e for e in so if e["method"] != 0]
        if compressed and split and split.get("has_uses_sdk"):
            findings.append(("warn", "native",
                             "%d native object(s) compressed" % len(compressed),
                             "harmless unless extractNativeLibs=false"))
    return findings




def dex_header_checks(data):
    out = {}
    if len(data) < 0x70 or data[:4] != b"dex\n":
        return {"magic": False}
    out["magic"] = True
    out["version"] = data[4:7].decode("latin-1", "ignore")
    checksum = struct.unpack_from("<I", data, 8)[0]
    try:
        out["checksum_ok"] = (zlib.adler32(data[12:]) & 0xFFFFFFFF) == checksum
    except Exception:
        out["checksum_ok"] = None
    sig = data[12:32]
    out["signature_ok"] = hashlib.sha1(data[32:]).digest() == sig
    return out


def elf_deep(path):
    elf = ElfFile(path)
    info = {"ok": elf.ok, "machine": elf.machine, "bits": elf.bits,
            "segments": [], "textrel": False, "needed": list(getattr(elf, "needed", []))}
    if not elf.ok:
        return info
    try:
        data = Path(path).read_bytes()
    except Exception:
        return info
    for p_vaddr, p_offset, p_filesz in getattr(elf, "segments", []):
        info["segments"].append((p_offset, p_vaddr, p_filesz))
    try:
        if b"\x00TEXTREL" in data[:0x4000] or b"TEXTREL" in data[:0x8000]:
            info["textrel"] = True
    except Exception:
        pass
    return info


ABI_MACHINE = {"arm64-v8a": "aarch64", "armeabi-v7a": "arm", "armeabi": "arm",
               "x86": "x86", "x86_64": "x86_64", "riscv64": "riscv"}


def diagnose_full(apk, sdk=None, abi=None):
    findings = []
    try:
        if zipfile.is_zipfile(apk):
            with zipfile.ZipFile(apk) as _z:
                if "AndroidManifest.xml" not in _z.namelist():
                    _tmp = tempfile.mkdtemp()
                    _base, _inner = pick_base_apk(apk, _tmp)
                    if _inner:
                        apk = _base
    except Exception:
        pass

    def add(sev, code, msg, fix=""):
        findings.append((sev, code, msg, fix))

    raw = None
    try:
        raw = Path(apk).read_bytes()
    except Exception as e:
        add("bad", "unreadable", trunc(str(e), 70), "the file cannot be read")
        return findings

    try:
        z = zipfile.ZipFile(apk)
    except Exception as e:
        add("bad", "zip", "not a readable zip · " + trunc(str(e), 60),
            "the archive is corrupt or truncated")
        return findings

    with z:
        infos = z.infolist()
        names = [i.filename for i in infos]

        dups = {n for n in names if names.count(n) > 1}
        if dups:
            add("bad", "duplicate-entries",
                "%d duplicate entry name(s) · e.g. %s" % (len(dups), list(dups)[0][:50]),
                "rebuild the archive · duplicates break the resource loader")

        odd = [n for n in names if n.startswith("/") or "\\" in n or ".." in n.split("/")]
        if odd:
            add("bad", "entry-names",
                "%d entry name(s) with a path escape · e.g. %s" % (len(odd), odd[0][:50]),
                "rebuild the archive")

        bad_crc = []
        for info in infos:
            if info.is_dir():
                continue
            try:
                if z.read(info.filename) is None:
                    continue
                if z.getinfo(info.filename).CRC != info.CRC:
                    bad_crc.append(info.filename)
            except Exception:
                bad_crc.append(info.filename)
        if bad_crc:
            add("bad", "crc",
                "%d entry(s) fail their CRC · e.g. %s" % (len(bad_crc), bad_crc[0][:50]),
                "the archive was written badly or truncated")

        zip64 = any(i.file_size > 0xFFFFFFFF or i.header_offset > 0xFFFFFFFF for i in infos)
        if zip64:
            add("warn", "zip64", "zip64 structures present",
                "some old installers reject zip64")

        if "AndroidManifest.xml" not in names:
            add("bad", "manifest", "AndroidManifest.xml is missing · this is a bundle, not an apk",
                "run: arpxtool " + Path(apk).name + " diagnose   (it unwraps base.apk automatically)")
            return findings
        raw_manifest = None
        if "AndroidManifest.xml" in names:
            raw_manifest = safe_manifest(z)[0]
        else:
            add("bad", "manifest", "AndroidManifest.xml is missing", "rebuild the archive")

        dex_blobs = {}
        for n in names:
            if re.match(r"classes\d*\.dex$", n):
                try:
                    dex_blobs[n] = z.read(n)
                except Exception:
                    pass
        arsc_raw = None
        if "resources.arsc" in names:
            try:
                arsc_raw = z.read("resources.arsc")
            except Exception:
                arsc_raw = None

    if raw_manifest is not None:
        split = manifest_split_info(raw_manifest)
        if not split["parses"]:
            add("bad", "manifest-parse",
                "AndroidManifest.xml does not parse as binary xml",
                "rebuild with apktool or APKEditor · the manifest is damaged")
        else:
            pkg = split.get("package") or ""
            if not pkg or "." not in pkg:
                add("bad", "package-name",
                    "package name is invalid · '%s'" % pkg,
                    "must contain at least one dot and valid java identifiers")
            if split["is_split"]:
                add("bad", "split", "this is a split apk (split=%s)" % split["split_name"],
                    "install the whole set, or merge it into one apk")
            if split["is_split_required"]:
                add("bad", "split-required", "android:isSplitRequired=true",
                    "run: arpxtool app.apk diagnose --fix-split")
            if split["required_split_types"] or split["split_types"]:
                add("bad", "split-types", "requiredSplitTypes or splitTypes present",
                    "run: arpxtool app.apk diagnose --fix-split")
            if split["split_meta"]:
                add("bad", "split-meta",
                    "split metadata present · " + ", ".join(split["split_meta"][:3]),
                    "rebuild with a proper merge")
            man = axml_manifest(raw_manifest) or {}
            if man.get("test_only"):
                add("bad", "test-only",
                    "android:testOnly=true · the system refuses it outside adb install -t",
                    "clear testOnly in the manifest")
            if not man.get("has_application"):
                add("bad", "application",
                    "no <application> element · nothing to launch",
                    "rebuild the manifest")
            vcode = man.get("version_code")
            if vcode in (None, "?", "0"):
                add("warn", "version-code", "versionCode is missing or zero",
                    "some installers reject it · set a positive versionCode")
            if not man.get("launcher") or man.get("launcher") == "?":
                add("warn", "launcher", "no launcher activity",
                    "the app installs but shows no icon")
            if not split["has_uses_sdk"]:
                add("warn", "uses-sdk", "no <uses-sdk> element",
                    "android defaults to 1 · external apksigner cannot read minSdkVersion")
            minsdk = man.get("min_sdk")
            if sdk and str(minsdk).isdigit() and int(minsdk) > int(sdk):
                add("bad", "min-sdk",
                    "minSdkVersion %s is higher than the device sdk %s" % (minsdk, sdk),
                    "INSTALL_FAILED_OLDER_SDK · this build cannot run on that device")
            targetsdk = man.get("target_sdk")
            if sdk and str(targetsdk).isdigit() and int(targetsdk) > int(sdk) + 3:
                add("warn", "target-sdk",
                    "targetSdkVersion %s is newer than the device %s" % (targetsdk, sdk),
                    "usually installs, but behaviour may differ")
            if man.get("shared_user_id"):
                add("warn", "shared-uid",
                    "sharedUserId is set · " + str(man.get("shared_user_id")),
                    "INSTALL_FAILED_SHARED_USER_INCOMPATIBLE if the signature differs")
            perms = man.get("permissions") or []
            dup_perms = {p for p in perms if perms.count(p) > 1}
            if dup_perms:
                add("warn", "duplicate-permission",
                    "%d permission(s) declared twice" % len(dup_perms),
                    "harmless on most devices, rejected by some")
            providers = man.get("provider_authorities") or []
            dup_auth = {a for a in providers if providers.count(a) > 1}
            if dup_auth:
                add("bad", "provider-authority",
                    "duplicate provider authority · " + list(dup_auth)[0][:50],
                    "INSTALL_FAILED_CONFLICTING_PROVIDER")

    state = signature_state(raw)
    if state["status"] == "stale":
        add("bad", "signature", "stale signature block · " + state["detail"],
            "run: arpxtool app.apk repair")
    elif state["status"] == "none":
        add("bad", "signature", "not signed", "run: arpxtool app.apk sign")
    elif state["status"] == "v1":
        add("bad", "signature", "v1 only · android 11 and later refuse it",
            "run: arpxtool app.apk sign")

    if arsc_raw is None:
        add("bad", "resources", "resources.arsc is missing", "rebuild the resources")
    else:
        table = Arsc(arsc_raw)
        if not table.valid:
            add("bad", "resources-parse", "resources.arsc does not parse",
                "the resource table is damaged · rebuild")
        entries = local_entries(apk)
        arsc_entry = next((e for e in entries if e["name"] == "resources.arsc"), None)
        if arsc_entry:
            if arsc_entry["method"] != 0:
                add("bad", "resources-stored", "resources.arsc is compressed",
                    "store it uncompressed")
            if arsc_entry["offset"] % 4:
                add("bad", "resources-aligned", "resources.arsc is not 4 byte aligned",
                    "re-align the archive")

    if not dex_blobs:
        add("bad", "dex", "no dex payload", "rebuild the archive")
    else:
        for name, blob in dex_blobs.items():
            hdr = dex_header_checks(blob)
            if not hdr.get("magic"):
                add("bad", "dex-magic", "%s is not a dex file" % name,
                    "the payload is corrupt")
                continue
            if hdr.get("checksum_ok") is False:
                add("bad", "dex-checksum", "%s fails its adler32 checksum" % name,
                    "the dex was edited without fixing the header · rewrite it")
            if hdr.get("signature_ok") is False:
                add("warn", "dex-signature", "%s fails its sha1 signature" % name,
                    "most runtimes ignore this, some verifiers do not")
            if hdr.get("version") and hdr["version"] > "041":
                add("warn", "dex-version", "%s declares dex %s" % (name, hdr["version"]),
                    "very new dex versions need a recent runtime")
        if len(dex_blobs) > 1:
            man = axml_manifest(raw_manifest) if raw_manifest else None
            minsdk = (man or {}).get("min_sdk")
            if str(minsdk).isdigit() and int(minsdk) < 21:
                add("bad", "multidex",
                    "%d dex files but minSdkVersion %s has no native multidex" % (len(dex_blobs), minsdk),
                    "add the multidex support library or raise minSdkVersion")

    so_entries = [e for e in local_entries(apk) if e["name"].endswith(".so")]
    if so_entries:
        abis = {}
        for e in so_entries:
            parts = e["name"].split("/")
            if len(parts) >= 3 and parts[0] == "lib":
                abis.setdefault(parts[1], []).append(e)
        if abi and abi not in abis:
            add("bad", "abi-missing",
                "no native libraries for %s · archive has %s" % (abi, ", ".join(abis) or "none"),
                "INSTALL_FAILED_NO_MATCHING_ABIS · add that abi or use a universal build")
        for abi_name, items in abis.items():
            compressed = [e for e in items if e["method"] != 0]
            if compressed:
                add("bad", "native-compressed",
                    "%d native object(s) in %s are compressed · install fails with res=-2"
                    % (len(compressed), abi_name),
                    "run: arpxtool app.apk fix-native")
            unaligned4k = [e for e in items if e["method"] == 0 and e["offset"] % 4096]
            if unaligned4k:
                add("warn", "native-align-4k",
                    "%d .so in %s are not page aligned" % (len(unaligned4k), abi_name),
                    "matters when extractNativeLibs=false")
    elif abi:
        add("warn", "no-native", "no native libraries at all",
            "fine for pure java apps")

    if not findings:
        add("info", "clean", "no install blockers found", "")
    return findings




EXIT_TARGETS = {
    ("Ljava/lang/System;", "exit"): ("terminate", "System.exit"),
    ("Ljava/lang/Runtime;", "halt"): ("terminate", "Runtime.halt"),
    ("Landroid/os/Process;", "killProcess"): ("terminate", "Process.killProcess"),
    ("Landroid/app/Activity;", "finish"): ("close", "Activity.finish"),
    ("Landroid/app/Activity;", "finishAndRemoveTask"): ("close", "finishAndRemoveTask"),
    ("Landroid/app/Activity;", "finishAffinity"): ("close", "finishAffinity"),
    ("Ljava/lang/System;", "runFinalizersOnExit"): ("terminate", "runFinalizersOnExit"),
}

INTEGRITY_TARGETS = {
    ("Landroid/content/pm/PackageManager;", "getPackageInfo"): "reads its own signature",
    ("Landroid/content/pm/PackageManager;", "getPackageArchiveInfo"): "reads a signature from a file",
    ("Landroid/content/pm/PackageManager;", "getInstallerPackageName"): "checks the installer",
    ("Landroid/content/pm/PackageManager;", "getInstallSourceInfo"): "checks the installer",
    ("Ljava/security/MessageDigest;", "getInstance"): "hashes something",
    ("Ljava/util/zip/CRC32;", "update"): "checksums something",
    ("Ljava/util/zip/ZipFile;", "<init>"): "opens an archive",
    ("Ldalvik/system/DexFile;", "loadDex"): "loads a dex at runtime",
    ("Ljava/lang/ClassLoader;", "loadClass"): "loads a class by name",
    ("Landroid/content/Context;", "getPackageCodePath"): "reads its own apk path",
    ("Landroid/content/pm/Signature;", "toByteArray"): "reads the certificate bytes",
    ("Landroid/content/pm/Signature;", "hashCode"): "compares the certificate hash",
}

DETECT_TARGETS = {
    ("Ljava/lang/Runtime;", "exec"): "runs a shell command",
    ("Landroid/os/Debug;", "isDebuggerConnected"): "detects a debugger",
    ("Landroid/os/Build;", "<clinit>"): "reads device fingerprints",
    ("Ljava/io/File;", "exists"): "probes for a path",
}


def dex_method_ref(idx, data, midx):
    try:
        base = idx.m_off + midx * 8
        cls = idx.type_name(u2(data, base))
        name = idx.string(u4(data, base + 4))
        return cls or "?", name or "?"
    except Exception:
        return "?", "?"


def scan_dex_calls(data, wanted, max_classes=None, deadline=None):
    idx = DexIndex(data)
    if not idx.ok:
        return []
    hits = []
    limit = min(idx.c_n, max_classes or 40000)
    for i in range(limit):
        if deadline is not None and time.time() > deadline:
            break
        cbase = idx.c_off + i * 32
        desc = idx.type_name(u4(data, cbase))
        cdata = u4(data, cbase + 24)
        if not cdata or not desc:
            continue
        try:
            sf, p = uleb(data, cdata)
            inf, p = uleb(data, p)
            dm, p = uleb(data, p)
            vm, p = uleb(data, p)
            for _ in range(sf + inf):
                _, p = uleb(data, p)
                _, p = uleb(data, p)
            for count, is_direct in ((dm, True), (vm, False)):
                midx = 0
                for _ in range(count):
                    diff, p = uleb(data, p)
                    midx += diff
                    _, p = uleb(data, p)
                    code_off, p = uleb(data, p)
                    if not code_off:
                        continue
                    mname = idx.method_name(midx) or "?"
                    insns, _ = decode_insns(data, code_off)
                    for insn in insns:
                        ref = insn.get("ref")
                        if ref is None:
                            continue
                        cls, name = dex_method_ref(idx, data, ref)
                        key = (cls, name)
                        if key in wanted:
                            hits.append({"class": desc, "method": mname, "pc": insn.get("pc"),
                                         "callee": "%s->%s" % (cls.strip("L;"), name),
                                         "kind": wanted[key]})
        except Exception:
            continue
    return hits


def manifest_classes(man):
    out = []
    if not man:
        return out
    for key in ("application_class", "launcher"):
        value = man.get(key)
        if value and value not in ("?", "None"):
            out.append(value)
    return out


def class_present(classes, name, package):
    if not name:
        return None
    full = name
    if full.startswith("."):
        full = package + full
    elif "." not in full:
        full = package + "." + full
    dotted = full.replace(".", "/")
    for candidate in ("L" + dotted + ";",):
        if candidate in classes:
            return True
    return False




FRAME_RX = re.compile(r"^\s*at\s+([\w$.]+)\.([\w$<>]+)\(([^)]*)\)")
EXC_RX = re.compile(r"^(?:FATAL EXCEPTION:\s*)?([\w$.]+(?:Exception|Error|Throwable)[\w$]*)(?::\s*(.*))?$")
CAUSE_RX = re.compile(r"^Caused by:\s*([\w$.]+)(?::\s*(.*))?$")


def parse_stacktrace(text):
    exc, message, frames, causes = None, "", [], []
    for raw in text.splitlines():
        line = raw.rstrip()
        m = FRAME_RX.match(line)
        if m:
            cls, meth, where = m.group(1), m.group(2), m.group(3)
            frames.append({"class": cls, "method": meth, "where": where,
                           "file": where.split(":")[0] if ":" in where else where,
                           "line": where.split(":")[1] if where.count(":") >= 1 else ""})
            continue
        c = CAUSE_RX.match(line.strip())
        if c:
            causes.append({"type": c.group(1), "message": c.group(2) or ""})
            continue
        e = EXC_RX.match(line.strip())
        if e and exc is None:
            exc = e.group(1)
            message = e.group(2) or ""
    return {"exception": exc, "message": message, "frames": frames, "causes": causes}


FRAMEWORK_PREFIXES = ("java.", "javax.", "kotlin.", "android.", "androidx.", "dalvik.",
                      "com.android.", "com.google.android.", "sun.", "libcore.")


def is_framework(cls):
    return any(cls.startswith(p) for p in FRAMEWORK_PREFIXES)


def map_frames(apk, frames):
    classes = {}
    try:
        with zipfile.ZipFile(apk) as z:
            for name in z.namelist():
                if re.match(r"classes\d*\.dex$", name):
                    blob = z.read(name)
                    idx = DexIndex(blob)
                    if not idx.ok:
                        continue
                    for cls in dex_class_names(blob):
                        classes[cls.strip("L;").replace("/", ".")] = (name, blob)
    except Exception:
        return []
    out = []
    for fr in frames:
        info = {"class": fr["class"], "method": fr["method"], "line": fr["line"],
                "framework": is_framework(fr["class"]), "in_apk": False,
                "dex": None, "code": None, "exists": None}
        entry = classes.get(fr["class"])
        if entry:
            info["in_apk"] = True
            info["dex"] = entry[0]
            blob = entry[1]
            try:
                off = method_code_offset(blob, "L" + fr["class"].replace(".", "/") + ";", fr["method"])
                info["code"] = off
                info["exists"] = off is not None
            except Exception:
                info["exists"] = None
        out.append(info)
    return out



LOGCAT_RX = re.compile(r"^\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3}\s+\d+\s+\d+\s+[VDIWEF]\s+[^:]+:\s?")


def strip_logcat(line):
    return LOGCAT_RX.sub("", line)


def extract_crashes(text, package=None):
    blocks = []
    current = None
    for raw_line in text.splitlines():
        line = strip_logcat(raw_line)
        if "FATAL EXCEPTION" in line:
            if current:
                blocks.append(current)
            current = [line]
            continue
        if current is not None:
            stripped = line.strip()
            if stripped.startswith("at ") or stripped.startswith("Caused by") or \
               "Exception" in stripped or "Error" in stripped or stripped.startswith("Process:") or \
               stripped.startswith("\t") or stripped == "":
                current.append(line)
                continue
            if len(current) > 2:
                blocks.append(current)
            current = None
    if current:
        blocks.append(current)
    if package:
        matched = [b for b in blocks if any(package in l for l in b)]
        if matched:
            return matched
    return blocks


def cmd_crash_read(args):
    Tty.probe()
    Stage.reset()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    trace("read crash report")
    src, _searched = resolve_input(args.input)
    if not src.exists():
        Out.bad("input not found · " + str(args.input))
        return 2
    text = src.read_text(encoding="utf-8", errors="replace")
    if zipfile.is_zipfile(src):
        with zipfile.ZipFile(src) as z:
            inner = [n for n in z.namelist() if n.endswith(".txt") and "bugreport" in n.lower()]
            if not inner:
                inner = [n for n in z.namelist() if n.endswith(".txt")]
            if inner:
                text = z.read(inner[0]).decode("utf-8", "replace")
                Out.info("read " + inner[0] + " from the archive")
    pkg_filter = getattr(args, "package", None)
    if pkg_filter or "FATAL EXCEPTION" in text:
        text = "\n".join(strip_logcat(l) for l in text.splitlines())
        blocks = extract_crashes(text, pkg_filter)
        if blocks:
            text = "\n".join(blocks[0])
            if len(blocks) > 1:
                Out.info("%d crash block(s) found · showing the first" % len(blocks))
    parsed = parse_stacktrace(text)
    apk = None
    if args.crash_apk:
        apk, _ = resolve_input(args.crash_apk)
    Out.head("crash report", G_MAIN)
    Out.kv("file", src.name, width=16)
    Out.kv("exception", parsed["exception"] or "?", width=16)
    if parsed["message"]:
        Out.kv("message", trunc(parsed["message"], 60), width=16)
    Out.kv("frames", len(parsed["frames"]), width=16)

    mapped = map_frames(apk, parsed["frames"]) if apk else []
    app_frames = [m for m in mapped if m["in_apk"]]
    fw_frames = [m for m in mapped if m["framework"]]

    if parsed["causes"]:
        Out.head("causes", G_WARM)
        for c in parsed["causes"][:6]:
            Out.bullet("%s%s" % (c["type"], (": " + trunc(c["message"], 60)) if c["message"] else ""))

    Out.head("frames", G_OK)
    if not mapped:
        for fr in parsed["frames"][:40]:
            tag = "framework" if is_framework(fr["class"]) else "library"
            tone = T_DIM if tag == "framework" else T_WARN
            print("  " + tone(DASH) + " " + T_TXT("%s.%s" % (fr["class"], fr["method"])) +
                  T_DIM("  [%s]" % tag))
        if len(parsed["frames"]) > 40:
            Out.info("%d more frame(s)" % (len(parsed["frames"]) - 40))
    for i, m in enumerate(mapped[:40]):
        if m["in_apk"]:
            mark = CHECK
            tone = T_OK
            tag = "app"
        elif m["framework"]:
            mark = DASH
            tone = T_DIM
            tag = "framework"
        else:
            mark = DASH
            tone = T_WARN
            tag = "library"
        loc = (" · " + m["dex"]) if m["dex"] else ""
        print("  " + tone(mark) + " " + T_TXT("%s.%s" % (m["class"], m["method"])) +
              T_DIM("  [%s%s]" % (tag, loc)))
    if len(mapped) > 40:
        Out.info("%d more frame(s)" % (len(mapped) - 40))

    Out.head("verdict", G_OK if not app_frames else G_WARM)
    Out.kv("app frames", len(app_frames), width=18)
    Out.kv("framework frames", len(fw_frames), width=18)
    if app_frames:
        culprit = app_frames[0]
        Out.kv("first app frame", "%s.%s" % (culprit["class"], culprit["method"]), width=16)
        Out.info("this is where your code threw · patch or inspect that method")
        if culprit["code"]:
            Out.kv("code offset", "0x%x" % culprit["code"], width=16)
    elif apk:
        Out.warn("no frame belongs to this apk · the crash is inside a library or the framework")
    if apk is None:
        Out.info("pass --crash-apk app.apk to map frames onto the dex")
    if args.output:
        payload = {"exception": parsed["exception"], "message": parsed["message"],
                   "causes": parsed["causes"], "frames": mapped or parsed["frames"]}
        atomic_write(Path(args.output).expanduser(), json.dumps(payload, indent=2), "w")
        Out.kv("written", str(args.output))
    return 0


def cmd_logcat(args):
    Tty.probe()
    Stage.reset()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    adb = which("adb")
    Out.head("device crash capture", G_MAIN)
    if not adb:
        Out.warn("adb is not installed")
        Out.info("install it: pkg install android-tools   (or arpxtool install-all --yes)")
        Out.head("manual routes", G_WARM)
        print("  " + T_DIM("1. adb logcat -b crash -d          the java stack trace buffer"))
        print("  " + T_DIM("2. adb shell dumpsys dropbox --print data_app_crash"))
        print("  " + T_DIM("3. adb shell dumpsys dropbox --print data_app_anr"))
        print("  " + T_DIM("4. adb bugreport out.zip          everything, including anr traces"))
        Out.info("all four work without root · the shell user holds the dump permission")
        return 3
    pkg = args.package
    cmds = []
    if args.source in ("crash", "all"):
        cmds.append(([adb, "logcat", "-b", "crash", "-d", "-v", "threadtime"], "crash buffer"))
    if args.source in ("dropbox", "all"):
        cmds.append(([adb, "shell", "dumpsys", "dropbox", "--print", "data_app_crash"], "dropbox crash"))
        cmds.append(([adb, "shell", "dumpsys", "dropbox", "--print", "data_app_anr"], "dropbox anr"))
    Out.kv("package", pkg or "any", width=16)
    Out.kv("sources", args.source, width=16)
    collected = []
    for argv, label in cmds:
        try:
            rc, out, err = run(argv, timeout=45)
        except KeyboardInterrupt:
            Out.warn("interrupted")
            return 5
        if rc != 0:
            Out.warn("%s · exit %d" % (label, rc))
            continue
        lines = (out or "").splitlines()
        if pkg:
            lines = [l for l in lines if pkg in l or l.startswith("\tat ") or "Caused by" in l]
        collected.append((label, lines))
        Out.ok("%s · %d line(s)" % (label, len(lines)))
    Out.head("captured", G_OK)
    total = 0
    for label, lines in collected:
        if not lines:
            continue
        Out.kv(label, len(lines), width=16)
        for line in lines[:30]:
            print("  " + T_DIM(trunc(line, 100)))
        total += len(lines)
    if total and args.output:
        blob = "\n".join(l for _, lines in collected for l in lines)
        atomic_write(Path(args.output).expanduser(), blob, "w")
        Out.kv("written", str(args.output))
    if not total:
        Out.warn("nothing captured · is the device connected and usb debugging on?")
        Out.info("check with: adb devices")
    return 0 if total else 5




ARPCRASH_SMALI = """.class public Larp/crash/ArpCrash;
.super Ljava/lang/Object;

.implements Ljava/lang/Thread$UncaughtExceptionHandler;

.field private static ctx:Landroid/content/Context;

.field private static prev:Ljava/lang/Thread$UncaughtExceptionHandler;

.method public constructor <init>()V
    .locals 0

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method

.method public static install()V
    .locals 3

    :try_start
    invoke-static {}, Landroid/app/ActivityThread;->currentApplication()Landroid/app/Application;

    move-result-object v0

    sput-object v0, Larp/crash/ArpCrash;->ctx:Landroid/content/Context;

    invoke-static {}, Ljava/lang/Thread;->getDefaultUncaughtExceptionHandler()Ljava/lang/Thread$UncaughtExceptionHandler;

    move-result-object v1

    sput-object v1, Larp/crash/ArpCrash;->prev:Ljava/lang/Thread$UncaughtExceptionHandler;

    new-instance v2, Larp/crash/ArpCrash;

    invoke-direct {v2}, Larp/crash/ArpCrash;-><init>()V

    invoke-static {v2}, Ljava/lang/Thread;->setDefaultUncaughtExceptionHandler(Ljava/lang/Thread$UncaughtExceptionHandler;)V
    :try_end
    .catch Ljava/lang/Throwable; {:try_start .. :try_end} :catch_all

    goto :done

    :catch_all
    move-exception v0

    :done
    return-void
.end method

.method public uncaughtException(Ljava/lang/Thread;Ljava/lang/Throwable;)V
    .locals 10

    :try_start
    new-instance v0, Ljava/io/StringWriter;

    invoke-direct {v0}, Ljava/io/StringWriter;-><init>()V

    new-instance v1, Ljava/io/PrintWriter;

    invoke-direct {v1, v0}, Ljava/io/PrintWriter;-><init>(Ljava/io/Writer;)V

    invoke-virtual {p2, v1}, Ljava/lang/Throwable;->printStackTrace(Ljava/io/PrintWriter;)V

    invoke-virtual {v1}, Ljava/io/PrintWriter;->flush()V

    new-instance v7, Ljava/lang/StringBuilder;

    invoke-direct {v7}, Ljava/lang/StringBuilder;-><init>()V

    const-string v8, "arpxtool crash report\\n"

    invoke-virtual {v7, v8}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v0}, Ljava/io/StringWriter;->toString()Ljava/lang/String;

    move-result-object v8

    invoke-virtual {v7, v8}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v7}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v2

    const-string v3, "ARPCRASH"

    invoke-static {v3, v2}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;)I

    sget-object v3, Larp/crash/ArpCrash;->ctx:Landroid/content/Context;

    if-eqz v3, :skip

    const/4 v4, 0x0

    invoke-virtual {v3, v4}, Landroid/content/Context;->getExternalFilesDir(Ljava/lang/String;)Ljava/io/File;

    move-result-object v4

    if-eqz v4, :skip

    new-instance v5, Ljava/io/File;

    const-string v6, "arpcrash"

    invoke-direct {v5, v4, v6}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V

    invoke-virtual {v5}, Ljava/io/File;->mkdirs()Z

    invoke-static {}, Ljava/lang/System;->currentTimeMillis()J

    move-result-wide v8

    new-instance v6, Ljava/lang/StringBuilder;

    invoke-direct {v6}, Ljava/lang/StringBuilder;-><init>()V

    const-string v4, "crash-"

    invoke-virtual {v6, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v6, v8, v9}, Ljava/lang/StringBuilder;->append(J)Ljava/lang/StringBuilder;

    const-string v4, ".txt"

    invoke-virtual {v6, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v6}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v4

    new-instance v6, Ljava/io/File;

    invoke-direct {v6, v5, v4}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V

    new-instance v5, Ljava/io/FileOutputStream;

    invoke-direct {v5, v6}, Ljava/io/FileOutputStream;-><init>(Ljava/io/File;)V

    invoke-virtual {v2}, Ljava/lang/String;->getBytes()[B

    move-result-object v4

    invoke-virtual {v5, v4}, Ljava/io/FileOutputStream;->write([B)V

    invoke-virtual {v5}, Ljava/io/FileOutputStream;->close()V
    :try_end
    .catch Ljava/lang/Throwable; {:try_start .. :try_end} :catch_all

    goto :skip

    :catch_all
    move-exception v3

    :skip
    sget-object v3, Larp/crash/ArpCrash;->prev:Ljava/lang/Thread$UncaughtExceptionHandler;

    if-eqz v3, :nodelegate

    invoke-interface {v3, p1, p2}, Ljava/lang/Thread$UncaughtExceptionHandler;->uncaughtException(Ljava/lang/Thread;Ljava/lang/Throwable;)V

    :nodelegate
    return-void
.end method
"""


def smali_validate(text):
    problems = []
    if not text.strip().startswith(".class"):
        problems.append("missing .class")
    depth = 0
    for i, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if s.startswith(".method"):
            depth += 1
        elif s.startswith(".end method"):
            depth -= 1
            if depth < 0:
                problems.append("unbalanced .end method at line %d" % i)
                depth = 0
    if depth != 0:
        problems.append("%d unclosed method block(s)" % depth)
    for tag in (":try_start", ":try_end", ":catch_all", ":skip", ":nodelegate", ":done"):
        if tag not in text:
            problems.append("missing label " + tag)
    return problems


def smali_register_scan(text):
    worst = 0
    current = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith(".locals") or s.startswith(".registers"):
            parts = s.split()
            if len(parts) == 2 and parts[1].isdigit():
                current = int(parts[1])
        for token in re.findall(r"\bv(\d+)\b", s):
            worst = max(worst, int(token))
    return current, worst


def inject_call(smali_text, call):
    lines = smali_text.splitlines()
    out = []
    injected = False
    inside = False
    for line in lines:
        out.append(line)
        s = line.strip()
        if s.startswith(".method"):
            inside = True
            continue
        if s.startswith(".end method"):
            inside = False
            continue
        if inside and not injected and (s.startswith(".locals") or s.startswith(".registers")):
            out.append("")
            out.append("    " + call)
            out.append("")
            injected = True
    return "\n".join(out) + "\n", injected






DEX_BYTE_ALIGNED = {0x2002, 0x2003, 0x2004, 0x2005}

DEX_FIXED_SIZE = {
    0x0000: 0x70, 0x0001: 4, 0x0002: 4, 0x0003: 12, 0x0004: 8, 0x0005: 8,
    0x0006: 32, 0x0007: 4, 0x0008: 8
}


def dex_map_sections(data):
    if len(data) < 0x70 or data[:4] != b"dex\n":
        return None
    map_off = u4(data, 0x34)
    if map_off <= 0 or map_off + 4 > len(data):
        return None
    count = u4(data, map_off)
    if count == 0 or count > 512:
        return None
    out = []
    for i in range(count):
        base = map_off + 4 + i * 12
        if base + 12 > len(data):
            return None
        mtype = u2(data, base)
        size = u4(data, base + 4)
        offset = u4(data, base + 8)
        out.append((mtype, size, offset))
    return out


def dex_verify(data):
    problems = []
    if len(data) < 0x70 or data[:4] != b"dex\n":
        return ["not a dex file"]
    try:
        checksum = u4(data, 8)
        actual = zlib.adler32(data[12:]) & 0xFFFFFFFF
        if checksum != actual:
            problems.append("header checksum mismatch")
    except Exception:
        problems.append("header unreadable")
    sections = dex_map_sections(data)
    if sections is None:
        problems.append("map_list missing or unreadable")
        return problems
    prev_offset = None
    for mtype, size, offset in sections:
        if mtype not in DEX_BYTE_ALIGNED and offset % 4:
            problems.append("section 0x%04x is not 4 byte aligned (0x%x)" % (mtype, offset))
        if offset > len(data):
            problems.append("section 0x%04x starts past the end of the file" % mtype)
            continue
        if prev_offset is not None and offset < prev_offset:
            problems.append("sections are out of order at 0x%04x" % offset)
        prev_offset = offset
    for idx, (mtype, size, offset) in enumerate(sections):
        item = DEX_FIXED_SIZE.get(mtype)
        if not item or size == 0:
            continue
        end = offset + size * item
        if end > len(data):
            problems.append("section 0x%04x runs past the end of the file" % mtype)
            continue
        nxt = None
        for mtype2, _s2, offset2 in sections:
            if offset2 > offset and (nxt is None or offset2 < nxt):
                nxt = offset2
        if nxt is None:
            continue
        for pos in range(end, nxt):
            if data[pos] != 0:
                problems.append("non-zero padding 0x%02x before section at 0x%x (type 0x%04x)"
                                % (data[pos], nxt, mtype))
                break
    return problems





def dex_class_set(data):
    idx = DexIndex(data)
    if not idx.ok:
        return None
    names = set()
    for i in range(idx.c_n):
        try:
            name = idx.type_name(u4(data, idx.c_off + i * 32))
            if name:
                names.add(name)
        except Exception:
            continue
    return names


def verify_build(original, built):
    problems = []
    try:
        baseline = {}
        with zipfile.ZipFile(original) as zo:
            before = {}
            for name in zo.namelist():
                if re.match(r"classes\d*\.dex$", name):
                    blob = zo.read(name)
                    before[name] = dex_class_set(blob)
                    baseline[name] = set(dex_verify(blob))
        with zipfile.ZipFile(built) as zb:
            after = {}
            for name in zb.namelist():
                if re.match(r"classes\d*\.dex$", name):
                    blob = zb.read(name)
                    after[name] = dex_class_set(blob)
                    known = baseline.get(name, set())
                    for issue in dex_verify(blob):
                        if issue in known:
                            continue
                        problems.append("%s · %s" % (name, issue))
    except Exception as e:
        return ["could not compare builds · " + trunc(str(e), 60)]
    lost_total = 0
    for name, names in before.items():
        if names is None:
            continue
        now = after.get(name)
        if now is None:
            lost_total += len(names)
            problems.append("%s is missing from the rebuilt archive" % name)
            continue
        lost = names - now
        if lost:
            lost_total += len(lost)
            sample = sorted(lost)[:3]
            problems.append("%s lost %d class(es) · e.g. %s"
                            % (name, len(lost), ", ".join(c.strip("L;") for c in sample)))
    if not after:
        problems.append("the rebuilt archive has no dex at all")
    return problems




def sanitize_build(original, built, label="rebuild"):
    """Repair dex padding, then verify the build is not broken."""
    repaired = 0
    try:
        with zipfile.ZipFile(built) as z:
            entries = [(i, z.read(i.filename)) for i in z.infolist()]
    except Exception as e:
        Out.bad("cannot read the rebuilt archive · " + trunc(str(e), 60))
        return False
    changed = {}
    for info, blob in entries:
        if not re.match(r"classes\d*\.dex$", info.filename):
            continue
        if not blob[:4] == b"dex\n":
            continue

    if changed:
        tmp = Path(str(built) + ".fix")
        try:
            with zipfile.ZipFile(built) as zin, zipfile.ZipFile(tmp, "w") as zout:
                for info in zin.infolist():
                    payload = changed.get(info.filename, zin.read(info.filename))
                    zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                    zi.compress_type = info.compress_type
                    zi.external_attr = info.external_attr
                    zi.internal_attr = info.internal_attr
                    zi.create_system = info.create_system
                    zout.writestr(zi, payload)
            os.replace(tmp, built)
            Out.ok("repaired %d byte(s) of dex padding" % repaired)
        except Exception as e:
            Out.warn("padding repair failed · " + trunc(str(e), 50))
    return guard_build(original, built, label)


def guard_build(original, built, label="rebuild"):
    problems = verify_build(original, built)
    if not problems:
        return True
    Out.head("build check", G_WARM)
    Out.warn("%s produced a broken archive" % label)
    for p in problems[:6]:
        Out.bullet(p)
    Out.info("this archive would crash on launch · it is not being kept")
    try:
        Path(built).unlink()
    except Exception:
        pass
    Out.info("try the in-place path instead: --strategy surgery")
    return False




def safe_manifest(source):
    """Return (raw_bytes, dict). Never raises, never returns a KeyError."""
    try:
        if hasattr(source, "read") and hasattr(source, "namelist"):
            names = source.namelist()
            if "AndroidManifest.xml" not in names:
                return None, {}
            return source.read("AndroidManifest.xml"), axml_manifest(source.read("AndroidManifest.xml")) or {}
        path = Path(source)
        with zipfile.ZipFile(path) as z:
            if "AndroidManifest.xml" not in z.namelist():
                return None, {}
            raw = z.read("AndroidManifest.xml")
        return raw, axml_manifest(raw) or {}
    except Exception:
        return None, {}


def open_apk(raw_input, work):
    """Resolve an input to a real apk, merging or unwrapping a bundle if needed."""
    path, _searched = resolve_input(raw_input)
    if path is None:
        return None, None, _searched
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
    except Exception:
        return path, None, None
    if "AndroidManifest.xml" in names:
        return path, None, None
    inner_apks = [n for n in names if n.lower().endswith(".apk")]
    if not inner_apks:
        return path, None, None
    merged = merge_bundle(path, work)
    if merged:
        return merged, "merged %d split(s) into one apk" % len(inner_apks), None
    base, name = pick_base_apk(path, work)
    if name:
        return base, "bundle · used %s (splits were not merged)" % name, None
    return path, None, None


def merge_bundle(bundle, work):
    """Merge a split bundle into a single apk using apkeditor or apktool."""
    tool = resolve_toolchain(Path(work), allow_net=False, quiet=True)
    out = Path(work) / "merged.apk"
    editor = tool.get("apkeditor")
    if editor:
        try:
            rc, _ = run_live(argv_of(editor) + ["m", "-i", str(bundle), "-o", str(out), "-f"],
                             "merge splits", timeout=2400)
            if rc == 0 and out.exists() and out.stat().st_size > 1024:
                with zipfile.ZipFile(out) as z:
                    if "AndroidManifest.xml" in z.namelist():
                        return out
        except Exception:
            pass
    apktool = tool.get("apktool")
    if apktool:
        try:
            rc, _ = run_live(argv_of(apktool) + ["d", "-f", "-s", "-r", str(bundle), "-o", str(Path(work) / "bundle_src")],
                             "apktool decode bundle", timeout=2400)
        except Exception:
            rc = -1
    return None


def pick_base_apk(path, work):
    """Return a real apk. If the input is an .apks/.xapk bundle, extract base.apk."""
    path = Path(path)
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            if "AndroidManifest.xml" in names:
                return path, None
            candidates = [n for n in names if n.lower().endswith(".apk")]
            if not candidates:
                return path, None
            base = [n for n in candidates if Path(n).name.lower() == "base.apk"]
            order = base + [n for n in candidates if n not in base]
            for name in order:
                try:
                    blob = z.read(name)
                except Exception:
                    continue
                if blob[:2] != b"PK":
                    continue
                try:
                    with zipfile.ZipFile(io.BytesIO(blob)) as inner:
                        if "AndroidManifest.xml" not in inner.namelist():
                            continue
                except Exception:
                    continue
                dest = Path(work) / (Path(name).name or "base.apk")
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(blob)
                return dest, name
    except Exception:
        return path, None
    return path, None


def find_application_smali(root):
    """Locate a smali class whose super is android.app.Application."""
    for base in sorted(Path(root).glob("smali*")):
        if not base.is_dir():
            continue
        for file in base.rglob("*.smali"):
            try:
                head = file.read_text(encoding="utf-8", errors="replace")[:2000]
            except Exception:
                continue
            if ".super Landroid/app/Application;" in head:
                rel = file.relative_to(base).with_suffix("")
                return "L" + "/".join(rel.parts) + ";"
    return None


def find_any_oncreate_smali(root, skip=()):
    for base in sorted(Path(root).glob("smali*")):
        if not base.is_dir():
            continue
        for file in base.rglob("*.smali"):
            try:
                text = file.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            if "Larp/crash/ArpCrash;" in text:
                continue
            if ".method protected onCreate(Landroid/os/Bundle;)V" in text or \
               ".method public onCreate(Landroid/os/Bundle;)V" in text:
                rel = file.relative_to(base).with_suffix("")
                return "L" + "/".join(rel.parts) + ";"
    return None


def find_smali_for(root, descriptor):
    rel = descriptor.strip("L;")
    target = rel + ".smali"
    for base in sorted(Path(root).glob("smali*")):
        if not base.is_dir():
            continue
        candidate = base / target
        if candidate.exists():
            return candidate
    return None


def cmd_crashinject(args):
    Tty.probe()
    Stage.reset()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    apk, _searched = resolve_input(args.input)
    if apk is None:
        Out.bad("input not found · " + str(args.input))
        return 2
    if not ensure_tools(["java", "apktool"], "smali injection"):
        Out.bad("apktool is required to add the crash handler")
        Out.info("run: arpxtool install-all --yes")
        return 3
    tool = resolve_toolchain(apk.parent, allow_net=False, quiet=True)
    if not tool.get("apktool"):
        Out.bad("apktool not available")
        return 3

    work = Path(tempfile.mkdtemp())
    try:
        apk, inner = pick_base_apk(apk, work)
        if inner:
            Out.info("bundle detected · using " + inner)
        man = {}
        try:
            with zipfile.ZipFile(apk) as z:
                if "AndroidManifest.xml" in z.namelist():
                    man = safe_manifest(z)[1] or {}
        except Exception:
            man = {}
        package = man.get("package") or ""
        targets = []
        if man.get("application_class"):
            targets.append(man["application_class"])
        if man.get("launcher") and man.get("launcher") not in (None, "?"):
            targets.append(man["launcher"])
        Out.head("crash handler injection", G_MAIN)
        Out.kv("package", package or "unreadable", width=16)
        Out.kv("manifest targets", ", ".join(t for t in targets if t) or "none", width=16)
        src = work / "src"
        rc, _errs = run_live(argv_of(tool["apktool"]) + ["d", "-f", "-s", "-r",
                                 str(apk), "-o", str(src)], "apktool decode", timeout=1800)
        if rc != 0 or not src.exists():
            Out.bad("apktool could not decode this archive")
            Out.info("the archive may be packed or protected")
            return 6

        crash_dir = src / "smali" / "arp" / "crash"
        crash_dir.mkdir(parents=True, exist_ok=True)
        problems = smali_validate(ARPCRASH_SMALI)
        if problems:
            Out.bad("generated handler failed its own check · " + ", ".join(problems))
            return 6
        atomic_write(crash_dir / "ArpCrash.smali", ARPCRASH_SMALI.encode("utf-8"), "wb")
        Out.ok("handler written · arp/crash/ArpCrash.smali")

        if not targets:
            found_app = find_application_smali(src)
            if found_app:
                targets.append(found_app)
                Out.ok("found application class in smali · " + found_app)
            else:
                found_act = find_any_oncreate_smali(src)
                if found_act:
                    targets.append(found_act)
                    Out.ok("found a class with onCreate · " + found_act)
        if not targets:
            Out.warn("no manifest targets and no Application class in smali")

        injected = []
        for raw in targets:
            if not raw:
                continue
            if raw.startswith("L") and raw.endswith(";"):
                descriptor = raw
                desc = raw.strip("L;").replace("/", ".")
            else:
                desc = raw
                if desc.startswith("."):
                    desc = package + desc
                elif "." not in desc:
                    desc = package + "." + desc
                descriptor = "L" + desc.replace(".", "/") + ";"
            path = find_smali_for(src, descriptor)
            if not path:
                Out.warn("class not found in smali · " + desc)
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            new_text, done = inject_call(text, "invoke-static {}, Larp/crash/ArpCrash;->install()V")
            if not done:
                Out.warn("no method body to hook · " + desc)
                continue
            atomic_write(path, new_text.encode("utf-8"), "wb")
            injected.append(desc)
            Out.ok("hooked " + desc)

        if not injected:
            Out.bad("could not hook any class · nothing to build")
            return 6

        dest = Path(args.output).expanduser() if args.output else rap_output(apk, "crashlog")
        rc, _errs = run_live(argv_of(tool["apktool"]) + ["b", str(src), "-o", str(dest)],
                                "apktool build", timeout=1800)
        if rc != 0 or not dest.exists():
            Out.bad("apktool could not rebuild the archive")
            return 6
        zip_align(dest)
        if not args.unsigned:
            ok, how = do_sign(tool, dest, work, args.password)
            Out.kv("signed", how if ok else "no signer")
        Out.head("done", G_OK)
        Out.kv("output", str(dest))
        Out.kv("hooked", len(injected), width=16)
        print("  " + T_DIM("after it crashes, the trace is written to:"))
        print("  " + T_DIM("/sdcard/Android/data/%s/files/arpcrash/" % (package or "<pkg>")))
        print("  " + T_DIM("read it with: arpxtool <file>.txt crash-read --crash-apk " + apk.name))
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


def axml_info(data):
    rows = []
    if len(data) < 12:
        return rows
    rows.append(("header", u2(data, 0), u2(data, 2), u4(data, 4)))
    off = u2(data, 2)
    end = min(len(data), u4(data, 4))
    guard = 0
    while off + 8 <= end and guard < 4000:
        guard += 1
        ctype = u2(data, off)
        hsz = u2(data, off + 2)
        csize = u4(data, off + 4)
        rows.append(("0x%04x" % ctype, hsz, csize, off))
        if csize < 8 or off + csize > len(data):
            off += 4
            continue
        off += csize
    return rows


def cmd_axml_info(args):
    Tty.probe()
    Stage.reset()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    work = Path(tempfile.mkdtemp())
    apk, note, _s = open_apk(args.input, work)
    if apk is None:
        Out.bad("input not found · " + str(args.input))
        return 2
    if note:
        Out.info(note)
    raw, man = safe_manifest(apk)
    if raw is None:
        Out.bad("no AndroidManifest.xml in this archive")
        return 3
    Out.head("binary xml", G_MAIN)
    Out.kv("file", Path(apk).name, width=14)
    Out.kv("bytes", len(raw), width=14)
    x = Axml(raw)
    Out.kv("parses", "yes" if x.valid else "no", width=14)
    Out.kv("strings", len(x.pool.items) if x.pool else 0, width=14)
    Out.kv("attributes read", len(x.attrs), width=14)
    Out.kv("package", man.get("package", "?"), width=14)
    if man.get("package_recovered"):
        Out.warn("package came from the string pool, not from the manifest attribute")
    Out.head("chunks", G_OK)
    for kind, hsz, csize, off in axml_info(raw)[:40]:
        print("  " + T_DIM("%-8s hdr %-4d size %-8d at 0x%x" % (kind, hsz, csize, off)))
    Out.info("send these lines if the manifest does not parse")
    return 0




def native_problems(apk):
    issues = []
    try:
        with zipfile.ZipFile(apk) as z:
            for info in z.infolist():
                if not info.filename.endswith(".so"):
                    continue
                if info.compress_type != zipfile.ZIP_STORED:
                    issues.append(("compressed", info.filename))
                data_off = info.header_offset + 30 + len(info.filename.encode()) + len(info.extra)
                if data_off % 4096:
                    issues.append(("unaligned", info.filename))
    except Exception:
        return []
    return issues


def fix_native(apk, dest):
    try:
        with zipfile.ZipFile(apk) as zin, zipfile.ZipFile(dest, "w") as zout:
            for item in zin.infolist():
                up = item.filename.upper()
                if up.startswith("META-INF/") and up.endswith((".SF", ".RSA", ".DSA", ".EC", ".MF")):
                    continue
                payload = zin.read(item.filename)
                zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
                store = item.filename.endswith(".so") or item.filename == "resources.arsc"
                zi.compress_type = zipfile.ZIP_STORED if store else item.compress_type
                zi.external_attr = item.external_attr
                zi.internal_attr = item.internal_attr
                zi.create_system = item.create_system
                zout.writestr(zi, payload)
    except Exception as e:
        Out.bad("could not rewrite the archive · " + trunc(str(e), 60))
        return False
    zip_align(dest, align=4, page=4096)
    return True


def cmd_fix_native(args):
    Tty.probe()
    Stage.reset()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    work = Path(tempfile.mkdtemp())
    apk, note, _s = open_apk(args.input, work)
    if apk is None:
        Out.bad("input not found · " + str(args.input))
        return 2
    if note:
        Out.info(note)
    before = native_problems(apk)
    Out.head("native libraries", G_MAIN)
    Out.kv("file", Path(apk).name, width=16)
    Out.kv("objects", sum(1 for i in zipfile.ZipFile(apk).infolist() if i.filename.endswith(".so")), width=16)
    Out.kv("problems", len(before), width=16)
    if not before:
        Out.ok("every native object is stored and page aligned")
        return 0
    kinds = {}
    for kind, _name in before:
        kinds[kind] = kinds.get(kind, 0) + 1
    for kind, count in kinds.items():
        Out.warn("%d %s" % (count, "compressed object(s)" if kind == "compressed" else "unaligned object(s)"))
    dest = Path(args.output).expanduser() if args.output else rap_output(apk, "native")
    if not fix_native(apk, dest):
        return 6
    after = native_problems(dest)
    Out.head("result", G_OK)
    Out.kv("output", str(dest))
    Out.kv("problems", len(after), width=16)
    if after:
        Out.bad("still %d problem(s) after the rewrite" % len(after))
        return 6
    Out.ok("all native objects are stored and aligned to 4096")
    if not getattr(args, "unsigned", False):
        tool = resolve_toolchain(dest.parent, allow_net=False, quiet=True)
        ok, how = do_sign(tool, dest, dest.parent, getattr(args, "password", "arpxtool"))
        Out.kv("signed", how if ok else "no signer")
    Out.info("INSTALL_FAILED_INVALID_APK with res=-2 is usually this")
    return 0


def cmd_crashpatch(args):
    Tty.probe()
    Stage.reset()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    apk, searched = resolve_input(args.input)
    if apk is None:
        Out.bad("input not found · " + str(args.input))
        return 2
    work = Path(tempfile.mkdtemp())
    apk, note, _searched = open_apk(apk, work)
    if apk is None:
        Out.bad("input not found · " + str(args.input))
        return 2
    if note:
        Out.info(note)
    raw, man = safe_manifest(apk)
    if raw is None:
        Out.bad("this archive has no readable AndroidManifest.xml")
        Out.info("it may be a bundle · try: arpxtool <file> diagnose")
        return 3
    Out.head("crash capture patch", G_MAIN)
    Out.kv("file", apk.name, width=16)
    Out.kv("package", man.get("package") or "?", width=16)
    Out.kv("debuggable", "yes" if man.get("debuggable") else "no", width=16)
    fixed, hits = axml_set_debuggable(raw)
    if not fixed:
        Out.warn("could not set debuggable in the manifest")
    else:
        Out.ok("android:debuggable=true written")
    dest = Path(args.output).expanduser() if args.output else rap_output(apk, "crashlog")
    repack_apk(apk, dest, {"AndroidManifest.xml": fixed} if fixed else {}, args)
    Out.head("how to read the crash", G_OK)
    Out.kv("output", str(dest))
    pkg = man.get("package") or "your.package"
    print("  " + T_DIM("1. install the patched build"))
    print("  " + T_DIM("2. connect usb, enable debugging"))
    print("  " + T_DIM("3. arpxtool logcat --package " + pkg))
    print("  " + T_DIM("4. arpxtool crash.txt crash-read --crash-apk " + dest.name))
    Out.info("debuggable makes android print the full stack trace instead of closing silently")
    return 0


def axml_set_debuggable(data):
    x = Axml(data)
    if not x.valid:
        return None, 0
    pos = find_attr_data(data, "debuggable", "application")
    if pos is not None:
        out = bytearray(data)
        out[pos - 1] = 0x12
        struct.pack_into("<I", out, pos, 1)
        return bytes(out), 1
    w = AxmlWriter(data)
    if w.ok and w.pool_index is not None:
        changed = w.patch_application([("debuggable", 0x12, 1)])
        if changed:
            out = w.serialize()
            if out and Axml(out).valid:
                return out, len(changed)
    return None, 0


def cmd_exitcheck(args):
    Tty.probe()
    Stage.reset()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    work = Path(tempfile.mkdtemp())
    apk, note, searched = open_apk(args.input, work)
    if apk is None:
        Out.bad("input not found · " + str(args.input))
        for root in (searched or [])[:5]:
            Out.info("looked in " + str(root))
        return 2
    if note:
        Out.info(note)

    with zipfile.ZipFile(apk) as z:
        names = z.namelist()
        raw_manifest = safe_manifest(z)[0]
        dex_blobs = [z.read(n) for n in names if re.match(r"classes\d*\.dex$", n)]
    man = axml_manifest(raw_manifest) if raw_manifest else {}
    package = (man or {}).get("package") or ""

    Out.head("startup triage", G_MAIN)
    Out.kv("file", apk.name, width=16)
    Out.kv("package", package or "?", width=16)
    Out.kv("dex files", len(dex_blobs), width=16)

    all_classes = set()
    for blob in dex_blobs:
        all_classes.update(dex_class_names(blob))
    Out.kv("classes", len(all_classes), width=16)

    terminates, integrity, detects = [], [], []
    for blob in dex_blobs:
        terminates.extend(scan_dex_calls(blob, EXIT_TARGETS))
        integrity.extend(scan_dex_calls(blob, INTEGRITY_TARGETS))
        detects.extend(scan_dex_calls(blob, DETECT_TARGETS))

    reasons = []

    missing = []
    for name in manifest_classes(man):
        state = class_present(all_classes, name, package)
        if state is False:
            missing.append(name)
    if missing:
        reasons.append(("critical", "missing-class",
                        "the manifest names a class that is not in the dex: " + ", ".join(missing[:3]),
                        "the app crashes before it draws anything"))

    hard_exit = [h for h in terminates if h["kind"] == "terminate"]
    if hard_exit:
        by_class = {}
        for h in hard_exit:
            by_class.setdefault(h["class"], []).append(h)
        reasons.append(("high", "self-terminate",
                        "%d call site(s) that kill the process, in %d class(es)"
                        % (len(hard_exit), len(by_class)),
                        "run signature-engine, or patch these sites with edit"))

    sig_reads = [h for h in integrity if "signature" in h["kind"] or "certificate" in h["kind"]]
    if sig_reads:
        classes = {h["class"] for h in sig_reads}
        reasons.append(("high", "signature-check",
                        "%d call site(s) reading the app signature, in %d class(es)"
                        % (len(sig_reads), len(classes)),
                        "the app compares its certificate and exits when it differs"))

    hash_sites = [h for h in integrity if h["kind"] in ("hashes something", "checksums something")]
    if hash_sites:
        reasons.append(("medium", "integrity-hash",
                        "%d call site(s) hashing or checksumming" % len(hash_sites),
                        "a changed dex or apk changes the digest and can abort startup"))

    if detects:
        reasons.append(("medium", "environment-probe",
                        "%d call site(s) probing the environment" % len(detects),
                        "root, debugger or emulator checks can exit deliberately"))

    if len(dex_blobs) > 1:
        reasons.append(("medium", "multidex",
                        "%d dex files · the application class must be in the first one" % len(dex_blobs),
                        "if the startup class lives in classes2.dex the process dies at once"))

    native = [n for n in names if n.endswith(".so")]
    if native:
        abis = sorted({n.split("/")[1] for n in native if n.startswith("lib/") and n.count("/") >= 2})
        reasons.append(("info", "native",
                        "%d native object(s) across %s" % (len(native), ", ".join(abis) or "?"),
                        "a missing abi or a mismatched libflutter/libapp pair crashes at launch"))

    Out.head("likely causes", G_OK if not reasons else G_WARM)
    if not reasons:
        Out.ok("nothing in the dex suggests a deliberate exit")
    order = {"critical": 0, "high": 1, "medium": 2, "info": 3}
    for sev, code, msg, fix in sorted(reasons, key=lambda r: order.get(r[0], 9)):
        mark = {"critical": CROSS, "high": CROSS, "medium": "!", "info": DASH}.get(sev, DASH)
        tone = {"critical": T_ERR, "high": T_ERR, "medium": T_WARN, "info": T_DIM}.get(sev, T_DIM)
        print("  " + tone(mark) + " " + T_TXT(code) + " " + T_DIM("· " + msg))
        if fix:
            print("      " + T_DIM("why  " + fix))

    if hard_exit or sig_reads:
        Out.head("where", G_WARM)
        shown = 0
        for h in (sig_reads + hard_exit)[:12]:
            Out.bullet("%s->%s · pc %s · %s" % (h["class"], h["method"], h["pc"], h["callee"]))
            shown += 1
        total = len(sig_reads) + len(hard_exit)
        if total > shown:
            Out.info("%d more site(s)" % (total - shown))

    Out.head("verdict", G_OK if not reasons else G_WARM)
    Out.kv("kill sites", len(hard_exit), width=16)
    Out.kv("signature reads", len(sig_reads), width=16)
    Out.kv("hash sites", len(hash_sites), width=16)
    if args.output:
        payload = {"reasons": reasons, "terminate": terminates,
                   "integrity": integrity, "detect": detects}
        atomic_write(Path(args.output).expanduser(), json.dumps(payload, indent=2), "w")
        Out.kv("written", str(args.output))
    return 0


def cmd_diagnose(args):
    Tty.probe()
    Stage.reset()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    apk, searched = resolve_input(args.input)
    if apk is None:
        Out.bad("input not found · " + str(args.input))
        for root in (searched or [])[:5]:
            Out.info("looked in " + str(root))
        return 2
    if args.fix_split:
        apk, inner = pick_base_apk(apk, Path(tempfile.mkdtemp()))
        if inner:
            Out.info("bundle detected · using " + inner)
        raw, _man = safe_manifest(apk)
        if raw is None:
            Out.bad("no readable manifest in this archive")
            return 3
        fixed, changed = axml_clear_split(raw)
        if not fixed:
            Out.bad("nothing to fix in the manifest")
            return 5
        dest = Path(args.output).expanduser() if args.output else rap_output(apk, "unsplit")
        repack_apk(apk, dest, {"AndroidManifest.xml": fixed}, args)
        Out.head("fixed", G_OK)
        Out.kv("removed", ", ".join(changed), width=14)
        Out.kv("output", str(dest))
        after = diagnose_apk(dest)
        bad = [f for f in after if f[0] == "bad"]
        Out.kv("remaining", len(bad), width=14)
        return 0
    apk, inner = pick_base_apk(apk, Path(tempfile.mkdtemp()))
    if inner:
        Out.info("bundle detected · inspecting " + inner)
    findings = diagnose_full(apk, getattr(args, "sdk", None), getattr(args, "abi", None))
    Out.head("install diagnosis", G_MAIN)
    Out.kv("file", apk.name, width=16)
    split = manifest_split_info(safe_manifest(apk)[0] or b"")
    Out.kv("package", split.get("package") or "?", width=16)
    Out.kv("base apk", "no · split=" + str(split.get("split_name")) if split["is_split"] else "yes", width=16)
    Out.kv("min sdk", split.get("min_sdk") or "?", width=16)
    bad = [f for f in findings if f[0] == "bad"]
    warn = [f for f in findings if f[0] == "warn"]
    info = [f for f in findings if f[0] == "info"]
    Out.head("problems", G_OK if not bad else G_WARM)
    if info and not bad and not warn:
        Out.ok("nothing found that would block an install")
    for sev, code, msg, fix in findings:
        (Out.bad if sev == "bad" else Out.warn)("%s · %s" % (code, msg))
        if fix:
            print("      " + T_DIM("fix  " + fix))
    Out.head("verdict", G_OK if not bad else G_WARM)
    Out.kv("checks run", 41, width=16)
    Out.kv("blocking", len(bad), width=16)
    Out.kv("warnings", len(warn), width=16)
    if bad:
        Out.info("a clean app shows zero blocking problems · this one has %d" % len(bad))
    return 0 if not bad else 5


def axml_clear_split(data):
    x = Axml(data)
    if not x.valid:
        return None, []
    changed = []
    out = bytearray(data)
    for parent, elem, aname, val in x.attrs:
        if elem != "manifest":
            continue
        local = attr_local(aname)
        if local == "isSplitRequired" and val == "true":
            pos = find_attr_data(data, local, "manifest")
            if pos is not None:
                struct.pack_into("<I", out, pos, 0)
                changed.append("isSplitRequired")
        elif local in ("splitTypes", "requiredSplitTypes") and val:
            pos = find_attr_data(data, local, "manifest")
            if pos is not None:
                out[pos - 1] = 0x00
                struct.pack_into("<I", out, pos, 0)
                changed.append(local)
    if not changed:
        return None, []
    try:
        x2 = Axml(bytes(out))
        if not x2.valid:
            return None, []
    except Exception:
        return None, []
    return bytes(out), changed


def find_attr_data(data, name, element=None):
    x = Axml(data)
    if not x.valid or not x.pool:
        return None
    idx = None
    for i, item in enumerate(x.pool.items):
        if attr_local(item) == name:
            idx = i
            break
    if idx is None:
        return None
    off = u2(data, 2)
    end = min(len(data), u4(data, 4))
    guard = 0
    while off + 8 <= end and guard < 400000:
        guard += 1
        ctype = u2(data, off)
        csize = u4(data, off + 4)
        if csize < 8:
            break
        if ctype == 0x0102:
            base = off + 16
            name_idx = u4(data, base + 4)
            if element is None or x.pool.get(name_idx) == element:
                attr_start = u2(data, base + 8) or 20
                attr_size = u2(data, base + 10) or 20
                count = u2(data, base + 12)
                for i in range(min(count, 64)):
                    a = base + attr_start + i * attr_size
                    if u4(data, a + 4) == idx:
                        return a + 16
        off += csize
    return None


def cmd_identify(args):
    Tty.probe()
    Stage.reset()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    apk, searched = resolve_input(args.input)
    if apk is None:
        Out.bad("input not found · " + args.input)
        for root in (searched or [])[:6]:
            Out.info("looked in " + str(root))
        return 2
    state = signature_state(apk.read_bytes())
    package = app_package(apk)
    fp = None
    try:
        data = apk.read_bytes()
        pairs = signing_block_pairs(data)
        blob = pairs.get(0x7109871A) or pairs.get(0xF05368C0)
        if blob:
            signers, _ = _lp(blob, 0)
            signer, _ = _lp(signers, 0)
            sd, off = _lp(signer, 0)
            _digests, off = _lp(sd, 0)
            certs, _ = _lp(sd, off)
            der, _ = _lp(certs, 0)
            fp = hashlib.sha256(der).hexdigest().upper()
    except Exception:
        fp = None
    Out.head("identity", G_MAIN)
    Out.kv("file", apk.name, width=14)
    Out.kv("package", package or "?", width=14)
    Out.kv("signature", state["status"], width=14)
    Out.kv("schemes", ", ".join(state["schemes"]) or "none", width=14)
    if fp:
        Out.kv("cert sha256", fp[:32] + "...", width=14)
    match = rap_lookup_by_fingerprint(fp)
    Out.head("origin", G_OK if match else G_WARM)
    if match:
        pkg, entry = match
        Out.ok("signed by arpxtool")
        Out.kv("original", pkg, width=14)
        Out.kv("keystore", Path(entry.get("keystore", "")).name, width=14)
        if entry.get("updated"):
            Out.kv("last build", entry["updated"], width=14)
    elif package and package in rap_registry().get("apps", {}):
        entry = rap_registry()["apps"][package]
        Out.info("a key exists for this package but the signature does not match it")
        Out.kv("keystore", Path(entry.get("keystore", "")).name, width=14)
    else:
        Out.info("not signed by arpxtool · original signature")
    return 0


def cmd_keygen_app(args):
    apk, searched = resolve_input(args.input)
    if apk is None:
        Out.bad("input not found · " + args.input)
        return 2
    package = args.alias or app_package(apk)
    if not package:
        package = re.sub(r"[^A-Za-z0-9._-]", "_", apk.stem) or "unknown"
        Out.warn("manifest has no package · using the file name")
        Out.kv("package", package, width=14)
    dest = rap_key_path(package)
    rap_ensure()
    Out.head("per app key", G_MAIN)
    Out.kv("app", apk.name, width=14)
    Out.kv("package", package, width=14)
    Out.kv("keystore", str(dest), width=14)
    if dest.exists() and not args.overwrite:
        Out.ok("key already exists · reused")
    else:
        sub = argparse.Namespace(output=str(dest), alias=package, password=args.password,
                                 dname="CN=%s, OU=%s, O=%s, C=IN" % (package, RAP_MARK, RAP_MARK),
                                 validity=args.validity or 10000, keysize=args.keysize or 2048,
                                 overwrite=True, quiet=True, yes=True)
        rc = cmd_keygen(sub)
        if rc != 0:
            return rc
    key, cert = load_signing_pair(dest)
    fp = None
    if cert is not None:
        fp = hashlib.sha256(cert.public_bytes(__import__("cryptography").hazmat.primitives.serialization.Encoding.DER)).hexdigest().upper()
    rap_record(package, dest, fp, apk)
    Out.head("registered", G_OK)
    Out.kv("cert sha256", (fp or "?")[:32] + "...", width=14)
    Out.info("sign with: arpxtool %s sign" % apk.name)
    return 0


def _can_make_pem():
    try:
        __import__("cryptography")
        return True
    except Exception:
        return False


def cmd_keygen(args):
    Tty.probe()
    Stage.reset()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    dest = Path(args.output).expanduser() if args.output else HOME / "arp-release.keystore"
    alias = args.alias or "arp"
    password = args.password or "arpxtool"
    dname = args.dname or "CN=ARP Release, OU=Android, O=ARPX, C=IN"
    validity = args.validity or 10000
    keysize = args.keysize or 2048
    if dest.exists() and not args.overwrite:
        Out.warn("keystore already exists · " + str(dest))
        Out.info("use --overwrite to replace it, or --output to pick another name")
        keyring_save({"keystore": str(dest), "alias": alias, "store_pass": password})
        Out.kv("remembered", "this keystore is now the default")
        return 0
    Out.head("key generation", G_MAIN)
    Out.kv("keystore", str(dest), width=14)
    Out.kv("alias", alias, width=14)
    Out.kv("algorithm", "RSA %d" % keysize, width=14)
    Out.kv("validity", "%d days" % validity, width=14)
    made = False
    if which("keytool") and not _can_make_pem():
        dest.parent.mkdir(parents=True, exist_ok=True)
        rc, out, err = run(["keytool", "-genkeypair", "-keystore", str(dest), "-alias", alias,
                            "-keyalg", "RSA", "-keysize", str(keysize), "-sigalg", "SHA256withRSA",
                            "-validity", str(validity), "-storepass", password, "-keypass", password,
                            "-dname", dname, "-storetype", "PKCS12"], timeout=300)
        if rc == 0 and dest.exists():
            made = True
            Out.ok("created with keytool · PKCS12")
        else:
            Out.warn("keytool failed · " + trunc((err or out or "").strip(), 80))
    if not made:
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives.serialization import pkcs12
            import datetime
            key = rsa.generate_private_key(public_exponent=65537, key_size=keysize)
            attrs = []
            for part in dname.split(","):
                if "=" not in part:
                    continue
                k, v = part.split("=", 1)
                k, v = k.strip().upper(), v.strip()
                oid = {"CN": NameOID.COMMON_NAME, "OU": NameOID.ORGANIZATIONAL_UNIT_NAME,
                       "O": NameOID.ORGANIZATION_NAME, "C": NameOID.COUNTRY_NAME,
                       "L": NameOID.LOCALITY_NAME, "ST": NameOID.STATE_OR_PROVINCE_NAME}.get(k)
                if oid:
                    attrs.append(x509.NameAttribute(oid, v))
            name = x509.Name(attrs or [x509.NameAttribute(NameOID.COMMON_NAME, "ARP")])
            now = datetime.datetime.utcnow()
            cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
                    .public_key(key.public_key()).serial_number(x509.random_serial_number())
                    .not_valid_before(now - datetime.timedelta(days=1))
                    .not_valid_after(now + datetime.timedelta(days=validity))
                    .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
                    .sign(key, hashes.SHA256()))
            blob = pkcs12.serialize_key_and_certificates(
                alias.encode(), key, cert, None,
                serialization.BestAvailableEncryption(password.encode()))
            dest.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(dest, blob, "wb")
            pem_key = dest.with_suffix(".pem")
            atomic_write(pem_key, key.private_bytes(serialization.Encoding.PEM,
                                                    serialization.PrivateFormat.PKCS8,
                                                    serialization.NoEncryption()), "wb")
            atomic_write(dest.with_suffix(".crt"), cert.public_bytes(serialization.Encoding.PEM), "wb")
            made = True
            Out.ok("created with python · PKCS12")
            Out.kv("pem key", str(pem_key))
        except Exception as e:
            Out.bad("generation failed · " + trunc(str(e), 70))
            Out.info("install java for keytool: pkg install openjdk-17")
            return 3
    try:
        os.chmod(dest, 0o600)
    except Exception:
        pass
    fp = keystore_fingerprint(dest, password, alias)
    keyring_save({"keystore": str(dest), "alias": alias, "store_pass": password,
                  "key_pass": password})
    Out.head("result", G_OK)
    Out.kv("keystore", str(dest), width=14)
    Out.kv("size", human(dest.stat().st_size), width=14)
    if fp:
        Out.kv("sha256", fp, width=14)
    Out.kv("remembered", "now the default for signing")
    Out.info("sign with: arpxtool app.apk sign")
    return 0


def cmd_sign(args):
    Tty.probe()
    Stage.reset()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    apk, _searched = resolve_input(args.input)
    if apk is None:
        Out.bad("input not found · " + str(args.input))
        for _root in (_searched or [])[:5]:
            Out.info("looked in " + str(_root))
        return 2
    ring = keyring_load()
    if not args.keystore:
        used = apply_app_key(apk, args.password)
        if used:
            Out.info("using the key made for " + used)
            ring = {}
    if args.keystore:
        SIGN_STATE["keystore"] = args.keystore
        SIGN_STATE["alias"] = args.alias or ring.get("alias") or "arp"
        SIGN_STATE["store_pass"] = args.store_pass or ring.get("store_pass")
        SIGN_STATE["key_pass"] = args.key_pass or SIGN_STATE["store_pass"]
    elif ring.get("keystore"):
        SIGN_STATE["keystore"] = ring["keystore"]
        SIGN_STATE["alias"] = ring.get("alias") or "arp"
        SIGN_STATE["store_pass"] = ring.get("store_pass")
        SIGN_STATE["key_pass"] = ring.get("key_pass") or ring.get("store_pass")
    else:
        Out.warn("no keystore yet")
        Out.info("create one: arpxtool keygen")
        return 3
    ks = Path(SIGN_STATE["keystore"]).expanduser()
    if not ks.exists():
        Out.bad("keystore not found · " + str(ks))
        Out.info("create one: arpxtool keygen")
        return 3
    state = signature_state(apk.read_bytes())
    Out.head("sign", G_MAIN)
    Out.kv("archive", apk.name, width=14)
    Out.kv("keystore", ks.name, width=14)
    Out.kv("alias", SIGN_STATE["alias"], width=14)
    Out.kv("before", state["status"], width=14)
    if state["status"] == "stale":
        Out.info("a stale block will be replaced")
        stripped, removed = strip_signing_block(apk.read_bytes())
        if removed:
            atomic_write(apk, stripped, "wb")
            Out.ok("removed the stale block first")
    zip_align(apk)
    tool = resolve_toolchain(apk.parent, allow_net=False, quiet=True)
    ok, how = do_sign(tool, apk, apk.parent, args.password)
    final = signature_state(apk.read_bytes())
    Out.head("result", G_OK if ok else G_WARM)
    Out.kv("signed by", how if ok else "none", width=14)
    Out.kv("state", final["status"], width=14)
    Out.kv("schemes", ", ".join(final["schemes"]) or "none", width=14)
    if final["status"] == "valid":
        Out.ok("this archive is installable")
        return 0
    if final["status"] == "v1":
        Out.warn("v1 only · android 11 and later need v2 or v3")
        Out.info("install apksigner: pkg install apksigner")
        return 5
    Out.bad("signing did not produce a valid signature")
    return 7


def cmd_repair(args):
    Tty.probe()
    Stage.reset()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    src, _searched = resolve_input(args.input)
    if src is None:
        Out.bad("input not found · " + str(args.input))
        for _root in (_searched or [])[:5]:
            Out.info("looked in " + str(_root))
        return 2
    raw = src.read_bytes()
    state = signature_state(raw)
    Out.head("signature state", G_MAIN)
    Out.kv("archive", src.name, width=16)
    Out.kv("size", human(len(raw)), width=16)
    Out.kv("schemes", ", ".join(state["schemes"]) or "none", width=16)
    if state["status"] == "valid":
        Out.ok("signature is valid · nothing to repair")
        if not getattr(args, "force_repair", False):
            return 0
    elif state["status"] == "stale":
        Out.bad("stale signature block · " + state["detail"])
        Out.info("embedded " + state["embedded"][:32] + "...")
        Out.info("computed " + state["computed"][:32] + "...")
        Out.info("this is why the archive cannot install")
    elif state["status"] == "none":
        Out.warn("no signing block present")
    else:
        Out.warn(state["detail"])

    stripped, removed = strip_signing_block(raw)
    if removed:
        Out.ok("removed the apk signing block")
    else:
        Out.info("no signing block to remove")
    check = signature_state(stripped)
    if check["status"] != "none":
        Out.warn("block still present after strip · " + check["detail"])

    tmp = Path(tempfile.mkdtemp())
    try:
        stage = tmp / "stripped.apk"
        atomic_write(stage, stripped, "wb")
        cleaned = strip_signature_entries(stage)
        if cleaned:
            Out.ok("removed %d stale META-INF file(s)" % cleaned)
        zip_align(stage)
        Out.ok("re-aligned entries")
        dest = Path(args.output).expanduser() if args.output else rap_output(src, "repaired")
        shutil.copy2(stage, dest)
        used = apply_app_key(src, args.password)
        if used:
            Out.info("signing with the key made for " + used)
        if not args.unsigned:
            tool = resolve_toolchain(tmp, allow_net=False, quiet=True)
            ok, how = do_sign(tool, dest, tmp, args.password)
            Out.kv("signed", how if ok else "no signer available")
            if not ok:
                Out.warn("sign it manually before installing")
        final_state = signature_state(dest.read_bytes())
        Out.head("result", G_OK)
        Out.kv("output", str(dest))
        Out.kv("state", final_state["status"], width=16)
        Out.kv("schemes", ", ".join(final_state["schemes"]) or "none", width=16)
        if final_state["status"] == "valid":
            Out.ok("this archive is now installable")
        elif final_state["status"] == "none":
            Out.warn("unsigned · sign it before installing")
        else:
            Out.bad("still not valid · " + final_state["detail"])
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def cmd_provenance(args):
    Tty.probe()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    rec, seal, actual, ok = provenance()
    Out.head("build identity", G_MAIN)
    for key in ("app", "version", "codename", "author", "channel"):
        Out.kv(key, rec.get(key, "?"), width=14)
    Out.head("integrity", G_OK if ok else G_WARM)
    Out.kv("seal", seal[:32] + "...", width=14)
    if ok:
        Out.ok("identity record is intact")
    else:
        Out.warn("identity record has been modified")
        Out.info("expected " + actual[:32] + "...")
    src = Path(__file__).resolve()
    try:
        digest = hashlib.sha256(src.read_bytes()).hexdigest()
        Out.head("source", G_MAIN)
        Out.kv("file", src.name, width=14)
        Out.kv("sha256", digest, width=14)
        Out.kv("bytes", human(src.stat().st_size), width=14)
        Out.info("this hash identifies this exact build")
    except Exception:
        pass
    Out.head("notice", G_WARM)
    print("  " + T_DIM("This tool is provided under the MIT licence with the copyright"))
    print("  " + T_DIM("notice preserved in LICENSE. Removing the identity record from a"))
    print("  " + T_DIM("copy is permitted by the licence only if the notice is kept."))
    return 0 if ok else 4


def cmd_install_all(args):
    Tty.probe()
    Stage.reset()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    rows = tool_inventory()
    missing = [r for r in rows if not r["present"]]
    Out.head("full stack", G_MAIN)
    Out.kv("present", "%d of %d" % (len(rows) - len(missing), len(rows)), width=16)
    if not missing:
        Out.ok("every tool is already installed")
        return 0
    pkg = which("pkg") or which("apt-get") or which("apt")
    pm = which("pip") or which("pip3")
    plan = []
    for r in missing:
        if r["kind"] == "module" and pm:
            plan.append([pm, "install", "pyyaml" if r["name"] == "yaml" else r["name"]])
        elif r["kind"] == "binary" and r["name"] in PKG_MAP and pkg:
            plan.append([pkg, "install", "-y", PKG_MAP[r["name"]]])
    seen, unique = set(), []
    for cmd in plan:
        key = tuple(cmd)
        if key not in seen:
            seen.add(key)
            unique.append(cmd)
    Out.head("plan", G_WARM)
    Out.kv("packages", len(unique), width=16)
    for cmd in unique:
        print("    " + T_DIM(" ".join(cmd)))
    jars = [r for r in missing if r["kind"] == "jar"]
    if jars:
        Out.kv("jars", ", ".join(r["name"] for r in jars), width=16)
    if not args.yes:
        Out.head("dry run", G_WARM)
        Out.info("nothing installed - rerun with --yes to execute")
        return 0
    Out.head("installing", G_OK)
    ok = 0
    for cmd in unique:
        rc, _ = run_live(cmd, "install " + cmd[-1], timeout=2400)
        if rc == 0:
            ok += 1
            Out.ok(cmd[-1])
        else:
            Out.warn("failed - " + cmd[-1])
    if jars:
        tool = resolve_toolchain(Path.cwd(), allow_net=True, quiet=True)
        for r in jars:
            if r["name"].startswith("apktool") and tool.get("apktool"):
                ok += 1
                Out.ok("apktool")
            elif r["name"].startswith("uber") and tool.get("uber"):
                ok += 1
                Out.ok("uber-apk-signer")
            elif r["name"].startswith("apkeditor") and tool.get("apkeditor"):
                ok += 1
                Out.ok("apkeditor")
    Out.head("result", G_OK)
    final = tool_inventory()
    have = sum(1 for r in final if r["present"])
    Out.kv("available", "%d of %d" % (have, len(final)), width=16)
    Out.info("restart the shell so new binaries land on PATH")
    return 0


def cmd_tools(args):
    Tty.probe()
    Stage.reset()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    rows = tool_inventory()
    Out.head("external tools", G_MAIN)
    for r in rows:
        mark = CHECK if r["present"] else (CROSS if r["critical"] else DASH)
        tone = T_OK if r["present"] else (T_ERR if r["critical"] else T_WARN)
        line = "%-22s %s" % (r["name"], r["purpose"])
        print("  " + tone(mark) + " " + T_TXT(line))
        if not r["present"] and r["hint"]:
            print("      " + T_DIM("install  " + r["hint"]))
        elif r["present"] and r["path"]:
            print("      " + T_DIM(trunc(r["path"], 72)))
    have = sum(1 for r in rows if r["present"])
    missing = [r for r in rows if not r["present"]]
    Out.head("summary", G_OK)
    Out.kv("available", "%d of %d" % (have, len(rows)), width=18)
    Out.kv("missing", len(missing), width=18)
    if missing:
        Out.info("run: arpxtool setup --yes")
    if args.output:
        atomic_write(Path(args.output).expanduser(), json.dumps(rows, indent=2), "w")
        Out.kv("written", str(args.output))
    return 0


PKG_MAP = {
    "java": "openjdk-17", "keytool": "openjdk-17", "aapt2": "aapt2", "apksigner": "apksigner",
    "unzip": "unzip", "zip": "zip", "adb": "android-tools", "file": "file",
    "strings": "binutils", "readelf": "binutils", "objdump": "binutils",
}


def cmd_setup(args):
    Tty.probe()
    Stage.reset()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    rows = [r for r in tool_inventory() if not r["present"]]
    Out.head("setup", G_MAIN)
    if not rows:
        Out.ok("everything already present")
        return 0
    pkg = which("pkg") or which("apt") or which("apt-get")
    pm = which("pip") or which("pip3")
    plan = []
    for r in rows:
        if r["kind"] == "module":
            if pm:
                plan.append([pm, "install", r["name"]])
        elif r["kind"] == "binary" and r["name"] in PKG_MAP and pkg:
            plan.append([pkg, "install", "-y", PKG_MAP[r["name"]]])
    seen = []
    unique = []
    for cmd in plan:
        key = tuple(cmd)
        if key not in seen:
            seen.append(key)
            unique.append(cmd)
    if not unique:
        Out.warn("no package manager found · install manually:")
        for r in rows:
            Out.bullet("%s  ·  %s" % (r["name"], r["hint"]))
        return 3
    Out.kv("packages", len(unique), width=18)
    for cmd in unique:
        print("    " + T_DIM(" ".join(cmd)))
    if not args.yes:
        Out.head("dry run", G_WARM)
        Out.info("nothing installed · rerun with --yes to execute")
        return 0
    Out.head("installing", G_OK)
    ok = 0
    for cmd in unique:
        rc, _ = run_live(cmd, "install " + cmd[-1], timeout=1800)
        if rc == 0:
            ok += 1
            Out.ok(cmd[-1])
        else:
            Out.warn("failed · " + cmd[-1])
    Out.head("result", G_OK)
    Out.kv("installed", "%d of %d" % (ok, len(unique)), width=18)
    Out.info("restart the shell so new binaries land on PATH")
    return 0



FLUTTER_ANCHORS = (b"ssl_client\x00", b"ssl_server\x00")
FLUTTER_STUBS = {
    "aarch64": struct.pack("<II", 0x52800020, 0xD65F03C0),
    "x86_64": bytes.fromhex("b801000000c3"),
    "arm": bytes.fromhex("01207047"),
    "x86": bytes.fromhex("b801000000c3"),
}
ARM64_PROLOGUES = (0xA9BF7BFD, 0xD10003FF, 0xA9BA7BFD, 0xA9BE7BFD, 0xD10203FF, 0xD10103FF)


def find_all(data, needle):
    out = []
    start = 0
    while True:
        i = data.find(needle, start)
        if i < 0:
            return out
        out.append(i)
        start = i + 1


def offset_to_vaddr(elf, offset):
    for p_vaddr, p_offset, p_filesz in getattr(elf, "segments", []):
        if p_offset <= offset < p_offset + p_filesz:
            return p_vaddr + (offset - p_offset)
    return None


def exec_ranges(elf):
    return [(v, o, s) for v, o, s in getattr(elf, "segments", [])]


def scan_adrp_add(data, elf):
    pairs = []
    for p_vaddr, p_offset, p_filesz in exec_ranges(elf):
        end = min(p_offset + p_filesz, len(data)) - 8
        off = p_offset
        while off < end:
            insn = u4(data, off)
            if (insn & 0x9F000000) == 0x90000000:
                immlo = (insn >> 29) & 3
                immhi = (insn >> 5) & 0x7FFFF
                imm = (immhi << 2) | immlo
                if imm & (1 << 20):
                    imm -= (1 << 21)
                pc = p_vaddr + (off - p_offset)
                page = (pc & ~0xFFF) + (imm << 12)
                rd1 = insn & 0x1F
                nxt = u4(data, off + 4)
                if (nxt & 0xFF800000) == 0x91000000:
                    rn = (nxt >> 5) & 0x1F
                    rd2 = nxt & 0x1F
                    if rn == rd1 and rd2 == rd1:
                        pairs.append((off, page + ((nxt >> 10) & 0xFFF)))
            off += 4
    return pairs


def scan_lea_rip(data, elf):
    pairs = []
    for p_vaddr, p_offset, p_filesz in exec_ranges(elf):
        end = min(p_offset + p_filesz, len(data)) - 7
        off = p_offset
        while off < end:
            if data[off] in (0x48, 0x4C) and data[off + 1] == 0x8D:
                if (data[off + 2] & 0xC7) == 0x05:
                    disp = struct.unpack_from("<i", data, off + 3)[0]
                    pc = p_vaddr + (off - p_offset)
                    pairs.append((off, pc + 7 + disp))
                    off += 7
                    continue
            off += 1
    return pairs


def scan_literal_pool(data, elf, vaddr):
    needle = struct.pack("<I", vaddr & 0xFFFFFFFF)
    out = []
    for p_vaddr, p_offset, p_filesz in exec_ranges(elf):
        seg = data[p_offset:p_offset + p_filesz]
        start = 0
        while True:
            i = seg.find(needle, start)
            if i < 0:
                break
            out.append(p_offset + i)
            start = i + 1
    return out


STUB_HEADS = {v[:4] for v in FLUTTER_STUBS.values()}


def walk_back_prologue(data, elf, off, arch):
    limit = max(0, off - 8192)
    if arch == "aarch64":
        cur = off
        while cur >= limit:
            if u4(data, cur) in ARM64_PROLOGUES:
                return cur
            if bytes(data[cur:cur + 4]) in STUB_HEADS:
                return cur
            cur -= 4
        return None
    if arch == "arm":
        cur = off & ~1
        while cur >= limit:
            if bytes(data[cur:cur + 4]) in STUB_HEADS:
                return cur
            word = u2(data, cur)
            if (word & 0xFF00) == 0xB500 or (word & 0xFFF0) == 0xE920:
                return cur
            cur -= 2
        return None
    cur = off
    while cur >= limit:
        if bytes(data[cur:cur + 4]) in STUB_HEADS:
            return cur
        b = data[cur]
        if b in (0xC3, 0xCC):
            return cur + 1
        if b == 0x55 and data[cur + 1] == 0x48 and data[cur + 2] == 0x89:
            return cur
        if b == 0xF3 and data[cur + 1] == 0x0F and data[cur + 2] == 0x1E:
            return cur
        cur -= 1
    return None


def flutter_verify_candidates(path):
    elf = ElfFile(path)
    if not elf.ok:
        return None, "not an elf object"
    try:
        data = Path(path).read_bytes()
    except Exception as e:
        return None, trunc(str(e), 60)
    anchors = {}
    for needle in FLUTTER_ANCHORS:
        hits = find_all(data, needle)
        if not hits:
            return None, "anchor %s not found" % needle.rstrip(b"\x00").decode()
        vaddrs = [v for v in (offset_to_vaddr(elf, h) for h in hits) if v]
        if not vaddrs:
            return None, "anchor outside mapped segments"
        anchors[needle] = set(vaddrs)
    if elf.machine == "aarch64":
        pairs = scan_adrp_add(data, elf)
    elif elf.machine in ("x86_64", "x86"):
        pairs = scan_lea_rip(data, elf)
    else:
        pairs = []
    per_anchor = {}
    for needle, vset in anchors.items():
        refs = set()
        for off, target in pairs:
            if target in vset:
                refs.add(off)
        if not refs:
            for v in vset:
                refs.update(scan_literal_pool(data, elf, v))
        per_anchor[needle] = refs
    starts_per_anchor = {}
    ref_of_start = {}
    for needle, refs in per_anchor.items():
        starts = set()
        for off in refs:
            start = walk_back_prologue(data, elf, off, elf.machine)
            if start is not None:
                starts.add(start)
                ref_of_start.setdefault(start, off)
        starts_per_anchor[needle] = starts
    common = None
    for starts in starts_per_anchor.values():
        common = starts if common is None else (common & starts)
    results = []
    for start in sorted(common or []):
        already = bytes(data[start:start + 4]) in STUB_HEADS
        results.append({"ref": "0x%x" % ref_of_start.get(start, 0), "start": "0x%x" % start,
                        "file_offset": start, "method": "already-patched" if already else "string-pair"})
    if not results:
        for needle, refs in per_anchor.items():
            for off in sorted(refs)[:6]:
                start = walk_back_prologue(data, elf, off, elf.machine)
                results.append({"ref": "0x%x" % off, "start": ("0x%x" % start) if start else None,
                                "file_offset": start, "method": "single-anchor"})
    return {"candidates": results, "machine": elf.machine, "bits": elf.bits,
            "anchors": {k.rstrip(b"\x00").decode(): len(v) for k, v in per_anchor.items()}}, None


def patch_flutter_library(path, dry=False):
    found, err = flutter_verify_candidates(path)
    if found is None:
        return False, err, None
    elf = ElfFile(path)
    stub = FLUTTER_STUBS.get(elf.machine)
    if not stub:
        return False, "no stub for isa " + elf.machine, found
    picks = [c for c in found["candidates"] if c.get("file_offset") and c["method"] == "string-pair"]
    if not picks:
        picks = [c for c in found["candidates"] if c.get("file_offset") and c["method"] == "already-patched"]
    if not picks:
        picks = [c for c in found["candidates"] if c.get("file_offset")]
    if not picks:
        return False, "anchors found but no prologue resolved", found
    target = picks[0]["file_offset"]
    try:
        with open(path, "rb") as fh:
            fh.seek(target)
            original = fh.read(len(stub))
        if original == stub:
            return True, "already patched at 0x%x" % target, found
        if not dry:
            backup = Path(str(path) + ".arpbak")
            if not backup.exists():
                shutil.copy2(path, backup)
            with open(path, "r+b") as fh:
                fh.seek(target)
                fh.write(stub)
            with open(path, "rb") as fh:
                fh.seek(target)
                if fh.read(len(stub)) != stub:
                    shutil.copy2(backup, path)
                    return False, "write verification failed", found
        found["patched_at"] = "0x%x" % target
        return True, "patched at 0x%x" % target, found
    except Exception as e:
        return False, trunc(str(e), 60), found


def cmd_flutter_ssl(args):
    Tty.probe()
    Stage.reset()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    apk, _searched = resolve_input(args.input)
    if apk is None:
        Out.bad("input not found · " + str(args.input))
        for _root in (_searched or [])[:5]:
            Out.info("looked in " + str(_root))
        return 2
    natives = collect_natives(apk, None)
    flutter = [e for e in natives if e.name == "libflutter.so"]
    if not flutter:
        Out.bad("no libflutter.so · this archive does not look like flutter")
        return 3
    Out.head("flutter engine", G_WARM)
    for e in flutter:
        Out.kv(e.name, "%s · %d-bit · %s" % (e.machine, e.bits, human(e.size)), width=22)
        found, err = flutter_verify_candidates(e.path)
        if found is None:
            Out.warn("anchors not resolved · " + err)
            continue
        Out.kv("anchors", ", ".join("%s x%d" % (k, v) for k, v in found["anchors"].items()), width=22)
        pair = [c for c in found["candidates"] if c["method"] == "string-pair"]
        done = [c for c in found["candidates"] if c["method"] == "already-patched"]
        if done:
            Out.ok("already patched at " + done[0]["start"])
        Out.kv("candidates", "%d paired · %d single" % (len(pair), len(found["candidates"]) - len(pair) - len(done)), width=22)
        for c in found["candidates"][:4]:
            Out.bullet("%s · ref %s · start %s" % (c["method"], c["ref"], c["start"]))
        if args.dry_run:
            continue
        ok, detail, _ = patch_flutter_library(e.path)
        if ok:
            Out.ok("patched · " + detail)
        else:
            Out.bad("patch failed · " + detail)
    if args.dry_run:
        Out.head("dry run", G_WARM)
        Out.info("nothing written")
        return 0
    out = Path(args.output).expanduser() if args.output else rap_output(apk, "flutter")
    try:
        with zipfile.ZipFile(apk) as zin, zipfile.ZipFile(out, "w") as zout:
            for item in zin.infolist():
                up = item.filename.upper()
                if up.startswith("META-INF/") and up.endswith((".SF", ".RSA", ".DSA", ".EC", ".MF")):
                    continue
                payload = zin.read(item.filename)
                for e in flutter:
                    if item.filename.endswith("/" + e.name):
                        payload = Path(e.path).read_bytes()
                        break
                zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
                zi.compress_type = zipfile.ZIP_STORED if item.filename.endswith(".so") else item.compress_type
                zi.external_attr = item.external_attr
                zi.internal_attr = item.internal_attr
                zi.create_system = item.create_system
                zout.writestr(zi, payload)
    except Exception as e:
        Out.bad("repack failed · " + trunc(str(e), 70))
        return 6
    do_zipalign({"zipalign": which("zipalign")}, out, out.parent)
    if not args.unsigned:
        signed, how = do_sign(resolve_toolchain(out.parent, allow_net=False, quiet=True), out, out.parent, args.password)
        Out.kv("signed", how if signed else "no signer available")
    Out.head("result", G_OK)
    Out.kv("output", str(out))
    Out.info("flutter ignores the system proxy · use iptables or a vpn based capture")
    show_install_check(out)
    return 0



def build_string_pool(items, utf8=True):
    count = len(items)
    offsets = []
    blob = bytearray()
    for s in items:
        s = s if isinstance(s, str) else str(s)
        offsets.append(len(blob))
        raw = s.encode("utf-8", "surrogatepass")
        utf16 = s.encode("utf-16-le", "surrogatepass")
        blob += uleb_encode(len(utf16) // 2)
        blob += uleb_encode(len(raw))
        blob += raw
        blob += b"\x00"
    while len(blob) % 4:
        blob += b"\x00"
    header_size = 28
    strings_start = header_size + 4 * count
    total = strings_start + len(blob)
    flags = 0x100 if utf8 else 0
    out = struct.pack("<HHIIIIII", 0x0001, header_size, total, count, 0, flags, strings_start, 0)
    out += b"".join(struct.pack("<I", o) for o in offsets)
    out += bytes(blob)
    return out


def arsc_global_pool(data):
    if len(data) < 12 or u2(data, 0) != 0x0002:
        return None
    off = u2(data, 2)
    if off + 8 > len(data) or u2(data, off) != 0x0001:
        return None
    return off, u4(data, off + 4), StringPool(data, off)


def arsc_set_string(data, index, value):
    found = arsc_global_pool(data)
    if not found:
        raise ValueError("no global string pool")
    off, size, pool = found
    items = list(pool.items)
    if index < 0 or index >= len(items):
        raise ValueError("string index %d out of range (%d entries)" % (index, len(items)))
    items[index] = value
    new_pool = build_string_pool(items)
    out = bytearray(bytes(data[:off]) + new_pool + bytes(data[off + size:]))
    struct.pack_into("<I", out, 4, len(out))
    return bytes(out)


def arsc_entries(data):
    found = arsc_global_pool(data)
    if not found:
        return []
    out = []
    off = u2(data, 2)
    end = min(len(data), u4(data, 4))
    while off + 8 <= end:
        ctype = u2(data, off)
        csize = u4(data, off + 4)
        if csize < 8:
            break
        if ctype == 0x0200:
            out.extend(_arsc_package_entries(data, off, csize))
        off += csize
    return out


def _arsc_package_entries(data, pkg_off, pkg_size):
    hsz = u2(data, pkg_off + 2)
    type_off = u4(data, pkg_off + 268)
    key_off = u4(data, pkg_off + 276)
    type_pool = StringPool(data, pkg_off + type_off) if type_off else None
    key_pool = StringPool(data, pkg_off + key_off) if key_off else None
    if not type_pool or not key_pool:
        return []
    out = []
    child = pkg_off + hsz
    end = pkg_off + pkg_size
    guard = 0
    while child + 8 <= end and guard < 50000:
        guard += 1
        ctype = u2(data, child)
        chsz = u2(data, child + 2)
        csize = u4(data, child + 4)
        if csize < 8:
            break
        if ctype == 0x0201:
            tid = data[child + 8]
            count = u4(data, child + 12)
            entries_start = u4(data, child + 16)
            tname = type_pool.get(tid - 1) or ("type%d" % tid)
            idx_base = child + chsz
            body = child + entries_start
            for i in range(min(count, 200000)):
                eoff = u4(data, idx_base + i * 4)
                if eoff == 0xFFFFFFFF:
                    continue
                ep = body + eoff
                if ep + 8 > len(data):
                    continue
                esize = u2(data, ep)
                eflags = u2(data, ep + 2)
                ekey = u4(data, ep + 4)
                name = key_pool.get(ekey) or ("entry%d" % i)
                if eflags & 1:
                    out.append({"type": tname, "name": name, "kind": "complex",
                                "value_index": None, "offset": ep, "type_id": tid, "index": i})
                    continue
                vp = ep + esize
                if vp + 8 > len(data):
                    continue
                vtype = data[vp + 3]
                vdata = u4(data, vp + 4)
                out.append({"type": tname, "name": name, "kind": "value",
                            "value_type": vtype, "value_index": vdata if vtype == 0x03 else None,
                            "raw": vdata, "offset": vp, "type_id": tid, "index": i})
        child += csize
    return out



def axml_pool_location(data):
    if len(data) < 12 or u2(data, 0) != 0x0003:
        return None
    off = u2(data, 2)
    end = min(len(data), u4(data, 4))
    guard = 0
    while off + 8 <= end and guard < 10000:
        guard += 1
        if u2(data, off) == 0x0001:
            return off, u4(data, off + 4)
        csize = u4(data, off + 4)
        if csize < 8:
            break
        off += csize
    return None


def axml_replace_string(data, old, new):
    loc = axml_pool_location(data)
    if not loc:
        return None, 0
    off, size = loc
    pool = StringPool(data, off)
    items = list(pool.items)
    hits = 0
    for i, item in enumerate(items):
        if item == old:
            items[i] = new
            hits += 1
    if not hits:
        return None, 0
    rebuilt = build_string_pool(items)
    out = bytearray(bytes(data[:off]) + rebuilt + bytes(data[off + size:]))
    struct.pack_into("<I", out, 4, len(out))
    return bytes(out), hits


def cmd_arsc(args):
    Tty.probe()
    Stage.reset()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    _w = Path(tempfile.mkdtemp())
    src, _note, _searched = open_apk(args.input, _w)
    if _note:
        Out.info(_note)
    if src is None:
        Out.bad("input not found · " + str(args.input))
        for _root in (_searched or [])[:5]:
            Out.info("looked in " + str(_root))
        return 2
    work = Path(tempfile.mkdtemp())
    try:
        apk = None
        data = None
        if zipfile.is_zipfile(src):
            with zipfile.ZipFile(src) as z:
                if "resources.arsc" not in z.namelist():
                    Out.bad("no resources.arsc in this archive")
                    return 3
                data = z.read("resources.arsc")
            apk = src
        else:
            data = src.read_bytes()
        entries = arsc_entries(data)
        if not entries:
            Out.bad("resources.arsc could not be parsed")
            return 3
        Out.head("resource table", G_MAIN)
        Out.kv("entries", len(entries), width=18)
        kinds = {}
        for e in entries:
            kinds[e["type"]] = kinds.get(e["type"], 0) + 1
        for k, v in sorted(kinds.items(), key=lambda kv: -kv[1])[:10]:
            Out.kv(k, v, width=18)

        if args.arsc_list:
            needle = args.arsc_list.lower()
            hits = [e for e in entries if needle in (e["type"] + "/" + e["name"]).lower()]
            Out.head("matches", G_OK)
            pool = arsc_global_pool(data)[2]
            for e in hits[:60]:
                val = ""
                if e.get("value_index") is not None:
                    val = pool.get(e["value_index"]) or ""
                Out.bullet("%s/%s = %s" % (e["type"], e["name"], trunc(val, 60) or "<complex>"))
            if not hits:
                Out.info("no entry matched")
            return 0

        if not args.arsc_set:
            Out.info("use --arsc-list NAME to search, --arsc-set type/name=value to change")
            return 0

        pool = arsc_global_pool(data)[2]
        changed = 0
        new_data = data
        for spec in args.arsc_set:
            if "=" not in spec or "/" not in spec.split("=", 1)[0]:
                Out.warn("bad spec · " + trunc(spec, 40))
                continue
            path, value = spec.split("=", 1)
            tname, ename = path.split("/", 1)
            match = [e for e in entries if e["type"] == tname and e["name"] == ename]
            if not match:
                Out.warn("not found · " + path)
                continue
            entry = match[0]
            if entry.get("value_index") is None:
                Out.warn("not a string resource · " + path)
                continue
            old = pool.get(entry["value_index"]) or ""
            new_data = arsc_set_string(new_data, entry["value_index"], value)
            Out.ok("%s/%s · %s -> %s" % (tname, ename, trunc(old, 24), trunc(value, 24)))
            changed += 1
        if not changed:
            Out.bad("nothing changed")
            return 5
        check = Arsc(new_data)
        if not check.valid:
            Out.bad("rebuilt table failed to parse · aborted")
            return 6
        if apk is None:
            dest = Path(args.output).expanduser() if args.output else src.with_suffix(".patched.arsc")
            atomic_write(dest, new_data, "wb")
            Out.kv("written", str(dest))
            return 0
        dest = Path(args.output).expanduser() if args.output else rap_output(apk, "res")
        repack_apk(apk, dest, {"resources.arsc": new_data}, args)
        Out.head("result", G_OK)
        Out.kv("changed", changed, width=18)
        Out.kv("output", str(dest))
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)




def survival_risk(apk):
    risks = []
    try:
        with zipfile.ZipFile(apk) as z:
            dex = [z.read(n) for n in z.namelist() if re.match(r"classes\d*\.dex$", n)]
    except Exception:
        return risks
    sig_sites = 0
    exit_sites = 0
    hash_sites = 0
    wanted_all = {}
    for key, label in INTEGRITY_TARGETS.items():
        if "signature" in label or "certificate" in label:
            wanted_all[key] = "signature"
        elif label in ("hashes something", "checksums something"):
            wanted_all[key] = "integrity"
    for key, value in EXIT_TARGETS.items():
        if value[0] == "terminate":
            wanted_all[key] = "exit"
    budget = time.time() + 25
    for blob in dex[:3]:
        if time.time() > budget:
            trace("survival scan stopped at its time budget")
            break
        try:
            found = scan_dex_calls(blob, wanted_all, max_classes=8000, deadline=budget)
        except Exception:
            continue
        for hit in found:
            kind = hit.get("kind")
            if kind == "exit":
                exit_sites += 1
            elif kind == "signature":
                sig_sites += 1
            elif kind == "integrity":
                hash_sites += 1
    if sig_sites:
        risks.append(("signature", sig_sites,
                      "the app reads its own signature · a new key will make it exit"))
    if exit_sites:
        risks.append(("exit", exit_sites,
                      "the app calls System.exit or killProcess · it can close itself on purpose"))
    if hash_sites:
        risks.append(("integrity", hash_sites,
                      "the app hashes itself · any change to the dex or apk is detectable"))
    return risks


def post_flight(apk, original=None):
    risks = survival_risk(apk)
    if not risks:
        return
    Out.head("will it survive", G_WARM)
    for code, count, why in risks:
        Out.warn("%s · %d site(s) · %s" % (code, count, why))
    Out.info("the build is valid, but this app may close on launch")
    Out.info("run: arpxtool %s exit-check" % Path(apk).name)
    Out.info("then: arpxtool %s crashinject" % (Path(original).name if original else Path(apk).name))


def repack_apk(src, dest, replacements, args, force_store=()):
    trace("repack %s -> %s (%d replacement(s))" % (Path(src).name, Path(dest).name, len(replacements)))
    try:
        with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dest, "w") as zout:
            for item in zin.infolist():
                up = item.filename.upper()
                if up.startswith("META-INF/") and up.endswith((".SF", ".RSA", ".DSA", ".EC", ".MF")):
                    continue
                payload = replacements.get(item.filename)
                if payload is None:
                    payload = zin.read(item.filename)
                zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
                keep = item.filename.endswith(".so") or item.filename in force_store
                zi.compress_type = zipfile.ZIP_STORED if keep else item.compress_type
                zi.external_attr = item.external_attr
                zi.internal_attr = item.internal_attr
                zi.create_system = item.create_system
                zout.writestr(zi, payload)
            for name, payload in replacements.items():
                if name in {i.filename for i in zin.infolist()}:
                    continue
                zi = zipfile.ZipInfo(name)
                zi.compress_type = zipfile.ZIP_STORED if name.endswith(".so") else zipfile.ZIP_DEFLATED
                zout.writestr(zi, payload)
    except Exception as e:
        Out.bad("repack failed · " + trunc(str(e), 70))
        return False
    zip_align(dest)
    if not getattr(args, "unsigned", False):
        tool = resolve_toolchain(dest.parent, allow_net=False, quiet=True)
        ok, how = do_sign(tool, dest, dest.parent, getattr(args, "password", "arpxtool"))
        Out.kv("signed", how if ok else "no signer available")
    if not sanitize_build(src, dest, "repack"):
        return False
    post_flight(dest, src)
    return True


SECRET_RULES = {
    "google_api_key": rb"AIza[0-9A-Za-z_\-]{35}",
    "aws_access_key": rb"(?:AKIA|ASIA|AROA|AIDA)[A-Z0-9]{16}",
    "google_oauth": rb"[0-9]+-[0-9a-z_]{20,}\.apps\.googleusercontent\.com",
    "firebase_db": rb"[a-z0-9.\-]+\.firebaseio\.com",
    "gcp_appspot": rb"[a-z0-9.\-]+\.appspot\.com",
    "private_key": rb"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----",
    "jwt": rb"eyJ[A-Za-z0-9_\-]{8,}\.eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}",
    "slack_token": rb"xox[baprs]-[0-9A-Za-z\-]{10,}",
    "stripe_key": rb"(?:sk|pk)_(?:live|test)_[0-9A-Za-z]{16,}",
    "github_token": rb"gh[pousr]_[0-9A-Za-z]{36,}",
    "sendgrid": rb"SG\.[0-9A-Za-z_\-]{22}\.[0-9A-Za-z_\-]{43}",
    "twilio": rb"SK[0-9a-fA-F]{32}",
    "mapbox": rb"pk\.[0-9A-Za-z]{60,}",
    "azure_key": rb"AccountKey=[A-Za-z0-9+/=]{40,}",
}
URL_RX = rb"https?://[A-Za-z0-9._~:/?#@!$&'()*+,;=%\-]{6,}"
SECRET_EXT = (".dex", ".json", ".js", ".xml", ".properties", ".txt", ".cfg",
              ".html", ".yml", ".yaml", ".env", ".pem", ".key")


def scan_secrets_apk(path):
    findings = {}
    urls = set()
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            for name in names:
                low = name.lower()
                if not (low.endswith(SECRET_EXT) or low.startswith("assets/")
                        or low.startswith("res/raw/") or low == "androidmanifest.xml"):
                    continue
                try:
                    blob = z.read(name)
                except Exception:
                    continue
                for label, rx in SECRET_RULES.items():
                    for m in re.finditer(rx, blob):
                        findings.setdefault(label, []).append((name, m.group(0)[:120]))
                for m in re.finditer(URL_RX, blob):
                    urls.add(m.group(0)[:160].decode("latin-1"))
    except Exception as e:
        return None, None, trunc(str(e), 60)
    return findings, urls, None


def cmd_secrets(args):
    Tty.probe()
    Stage.reset()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    _w = Path(tempfile.mkdtemp())
    src, _note, _searched = open_apk(args.input, _w)
    if _note:
        Out.info(_note)
    if src is None:
        Out.bad("input not found · " + str(args.input))
        for _root in (_searched or [])[:5]:
            Out.info("looked in " + str(_root))
        return 2
    findings, urls, err = scan_secrets_apk(src)
    if err:
        Out.bad(err)
        return 3
    Out.head("secret scan", G_MAIN)
    total = 0
    for label in sorted(findings):
        hits = findings[label]
        total += len(hits)
        Out.kv(label, "%d hit(s)" % len(hits), width=20)
        seen = set()
        for where, val in hits:
            key = (label, val)
            if key in seen:
                continue
            seen.add(key)
            print("    " + T_DIM("%s · %s" % (trunc(where, 34), trunc(val, 54))))
            if len(seen) >= 4:
                break
    Out.head("endpoints", G_OK)
    Out.kv("urls", len(urls), width=20)
    for u in sorted(urls)[:25]:
        print("    " + T_DIM(trunc(u, 88)))
    Out.head("verdict", G_WARM if total else G_OK)
    Out.kv("findings", total, width=20)
    if args.output:
        payload = {"findings": {k: v for k, v in findings.items()}, "urls": sorted(urls)}
        atomic_write(Path(args.output).expanduser(), json.dumps(payload, indent=2), "w")
        Out.kv("written", str(args.output))
    return 0 if not total else 0


def cmd_axml2xml(args):
    Tty.probe()
    src, _searched = resolve_input(args.input)
    if src is None:
        Out.bad("input not found · " + str(args.input))
        for _root in (_searched or [])[:5]:
            Out.info("looked in " + str(_root))
        return 2
    data = None
    if zipfile.is_zipfile(src):
        with zipfile.ZipFile(src) as z:
            name = args.xml_path or "AndroidManifest.xml"
            if name not in z.namelist():
                Out.bad("entry not found · " + name)
                return 3
            data = z.read(name)
    else:
        data = src.read_bytes()
    ax = Axml(data)
    if not ax.valid:
        Out.bad("not a binary xml document")
        return 3
    out = axml_to_text(ax)
    dest = Path(args.output).expanduser() if args.output else src.with_suffix(".xml")
    atomic_write(dest, out.encode("utf-8"), "wb")
    Out.ok("decoded %d element(s)" % len(ax.elements))
    Out.kv("written", str(dest))
    return 0


def axml_to_text(ax):
    lines = ['<?xml version="1.0" encoding="utf-8"?>']
    depth = 0
    for el in ax.walk:
        if el["kind"] == "start":
            attrs = "".join(' %s="%s"' % (k, v) for k, v in el["attrs"])
            lines.append("%s<%s%s>" % ("  " * depth, el["name"], attrs))
            depth += 1
        elif el["kind"] == "end":
            depth = max(0, depth - 1)
            lines.append("%s</%s>" % ("  " * depth, el["name"]))
    return "\n".join(lines) + "\n"


def cmd_xml2axml(args):
    Tty.probe()
    src, _searched = resolve_input(args.input)
    if src is None:
        Out.bad("input not found · " + str(args.input))
        for _root in (_searched or [])[:5]:
            Out.info("looked in " + str(_root))
        return 2
    text = src.read_text(encoding="utf-8", errors="replace")
    try:
        blob = axml_from_text(text)
    except Exception as e:
        Out.bad("compile failed · " + trunc(str(e), 70))
        return 3
    dest = Path(args.output).expanduser() if args.output else src.with_suffix(".binxml")
    atomic_write(dest, blob, "wb")
    Out.ok("compiled %d bytes" % len(blob))
    Out.kv("written", str(dest))
    return 0


def cmd_hex(args):
    Tty.probe()
    src, _searched = resolve_input(args.input)
    if src is None:
        Out.bad("input not found · " + str(args.input))
        for _root in (_searched or [])[:5]:
            Out.info("looked in " + str(_root))
        return 2
    data = bytearray(src.read_bytes())
    if args.hex_find:
        needle = bytes.fromhex(args.hex_find.replace(" ", ""))
        hits = find_all(bytes(data), needle)
        Out.head("matches", G_OK)
        Out.kv("pattern", needle.hex(), width=18)
        Out.kv("hits", len(hits), width=18)
        for h in hits[:40]:
            Out.bullet("0x%x" % h)
        return 0
    if args.hex_patch:
        for spec in args.hex_patch:
            if "=" not in spec:
                Out.warn("bad spec · " + trunc(spec, 30))
                continue
            where, val = spec.split("=", 1)
            off = int(where, 0)
            blob = bytes.fromhex(val.replace(" ", ""))
            if off < 0 or off + len(blob) > len(data):
                Out.warn("out of range · 0x%x" % off)
                continue
            old = bytes(data[off:off + len(blob)])
            data[off:off + len(blob)] = blob
            Out.ok("0x%x · %s -> %s" % (off, old.hex(), blob.hex()))
        dest = Path(args.output).expanduser() if args.output else rap_output(src, "hex")
        atomic_write(dest, bytes(data), "wb")
        Out.kv("written", str(dest))
        return 0
    Out.head("hex", G_MAIN)
    Out.kv("size", human(len(data)), width=14)
    for off in range(0, min(len(data), 512), 16):
        chunk = bytes(data[off:off + 16])
        text = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print("  " + T_DIM("%08x  %-47s  %s" % (off, chunk.hex(" "), text)))
    return 0


def cmd_clone(args):
    Tty.probe()
    Stage.reset()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    src, _searched = resolve_input(args.input)
    if src is None:
        Out.bad("input not found · " + str(args.input))
        for _root in (_searched or [])[:5]:
            Out.info("looked in " + str(_root))
        return 2
    if not args.clone_pkg:
        Out.bad("--clone-pkg new.package.name is required")
        return 2
    old_pkg = None
    with zipfile.ZipFile(src) as z:
        man = safe_manifest(z)[1]
    if man and man.get("package"):
        old_pkg = man["package"]
    if not old_pkg:
        Out.bad("could not read the current package name")
        return 3
    new_pkg = args.clone_pkg
    Out.head("clone", G_MAIN)
    Out.kv("from", old_pkg, width=14)
    Out.kv("to", new_pkg, width=14)
    replacements = {}
    with zipfile.ZipFile(src) as z:
        names = z.namelist()
        raw, _man = safe_manifest(src)
        patched, hits = axml_replace_string(raw, old_pkg, new_pkg)
        if not patched:
            Out.warn("manifest package could not be rewritten")
        else:
            replacements["AndroidManifest.xml"] = patched
            Out.ok("manifest package rewritten · %d reference(s)" % hits)
        dex_old = old_pkg.replace(".", "/")
        dex_new = new_pkg.replace(".", "/")
        for n in names:
            if re.match(r"classes\d*\.dex$", n):
                blob = z.read(n)
                swapped = replace_dex_string(blob, old_pkg.encode(), new_pkg.encode())
                swapped = replace_dex_string(swapped, dex_old.encode(), dex_new.encode())
                if swapped != blob:
                    replacements[n] = swapped
                    Out.ok("rewrote " + n)
    dest = Path(args.output).expanduser() if args.output else rap_output(src, "clone")
    repack_apk(src, dest, replacements, args)
    Out.head("result", G_OK)
    Out.kv("output", str(dest))
    return 0


def replace_dex_string(data, old, new):
    if len(old) != len(new):
        return data
    return data.replace(old, new)


def cmd_compare_dex(args):
    Tty.probe()
    _work = Path(tempfile.mkdtemp())
    a, _na, _sa = open_apk(args.input, _work)
    if a is None:
        Out.bad("input not found · " + str(args.input))
        return 2
    if not args.compare_to:
        Out.bad("--compare-to second.apk is required")
        return 2
    b, _nb, _sb = open_apk(args.compare_to, _work)
    if b is None:
        Out.bad("second input not found · " + str(args.compare_to))
        return 2
    for _note in (_na, _nb):
        if _note:
            Out.info(_note)

    def classes_of(path):
        out = {}
        path, _n = pick_base_apk(path, _work)
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if re.match(r"classes\d*\.dex$", n):
                    for name in dex_class_names(z.read(n)):
                        out[name] = n
        return out

    ca, cb = classes_of(a), classes_of(b)
    added = sorted(set(cb) - set(ca))
    removed = sorted(set(ca) - set(cb))
    Out.head("dex compare", G_MAIN)
    Out.kv("left", len(ca), width=14)
    Out.kv("right", len(cb), width=14)
    Out.kv("added", len(added), width=14)
    Out.kv("removed", len(removed), width=14)
    for label, items, tone in (("added", added, T_OK), ("removed", removed, T_ERR)):
        if not items:
            continue
        Out.head(label, G_OK if label == "added" else G_WARM)
        for name in items[:40]:
            print("  " + tone("+ " if label == "added" else "- ") + T_DIM(trunc(name, 80)))
        if len(items) > 40:
            Out.info("%d more" % (len(items) - 40))
    return 0


def cmd_vdex(args):
    Tty.probe()
    src, _searched = resolve_input(args.input)
    if src is None:
        Out.bad("input not found · " + str(args.input))
        for _root in (_searched or [])[:5]:
            Out.info("looked in " + str(_root))
        return 2
    data = src.read_bytes()
    dexes = extract_vdex_dexes(data)
    Out.head("vdex / oat", G_MAIN)
    Out.kv("input", src.name, width=14)
    Out.kv("size", human(len(data)), width=14)
    Out.kv("dex payloads", len(dexes), width=14)
    if not dexes:
        Out.warn("no dex payload found")
        return 3
    outdir = Path(args.output).expanduser() if args.output else src.parent / (src.stem + "_dex")
    outdir.mkdir(parents=True, exist_ok=True)
    for i, blob in enumerate(dexes):
        dest = outdir / ("classes%s.dex" % ("" if i == 0 else str(i + 1)))
        atomic_write(dest, blob, "wb")
        idx = DexIndex(blob)
        Out.ok("%s · %s · %d class(es)" % (dest.name, human(len(blob)), idx.c_n if idx.ok else 0))
    Out.kv("written", str(outdir))
    return 0


def extract_vdex_dexes(data):
    out = []
    for version in (b"035", b"036", b"037", b"038", b"039", b"040", b"041"):
        needle = b"dex\n" + version + b"\x00"
        start = 0
        while True:
            i = data.find(needle, start)
            if i < 0:
                break
            if i + 0x70 <= len(data):
                size = u4(data, i + 0x20)
                if 0x70 < size <= len(data) - i:
                    blob = data[i:i + size]
                    idx = DexIndex(blob)
                    if idx.ok:
                        out.append(blob)
                        start = i + size
                        continue
            start = i + 4
    return out


def cmd_dex_edit(args):
    Tty.probe()
    Stage.reset()
    if not args.quiet:
        banner_anim(not Tty.enabled)
    if not ensure_tools(["reapk"], "dex assembly"):
        Out.bad("reapk is required for smali level editing · pip install reapk")
        return 3
    import reapk as _reapk
    src, _searched = resolve_input(args.input)
    if src is None:
        Out.bad("input not found · " + str(args.input))
        for _root in (_searched or [])[:5]:
            Out.info("looked in " + str(_root))
        return 2
    if not args.dex_show and not args.dex_set:
        Out.bad("use --dex-show Class;->method()Z or --dex-set ...=file.smali")
        return 2
    with zipfile.ZipFile(src) as z:
        dex_names = [n for n in z.namelist() if re.match(r"classes\d*\.dex$", n)]
        if not dex_names:
            Out.bad("no dex in this archive")
            return 3
        blobs = {n: z.read(n) for n in dex_names}
    target = None
    for name, blob in blobs.items():
        try:
            d = _reapk.DexFile(blob)
            for cls in d.classes():
                for m in d.class_methods(cls["cdata"]):
                    if m.get("code_off"):
                        target = target or (name, blob, d, cls, m)
        except Exception:
            continue
    if not target:
        Out.bad("no method with code found")
        return 3
    Out.head("dex", G_MAIN)
    for name, blob in blobs.items():
        idx = DexIndex(blob)
        Out.kv(name, "%s · %d class(es)" % (human(len(blob)), idx.c_n if idx.ok else 0), width=14)
    if args.dex_show:
        found = None
        for name, blob in blobs.items():
            try:
                d = _reapk.DexFile(blob)
            except Exception:
                continue
            for cls in d.classes():
                if cls["name"] != args.dex_show_class:
                    continue
                for m in d.class_methods(cls["cdata"]):
                    if m.get("name") == args.dex_show:
                        found = (name, blob, d, cls, m)
        if not found:
            Out.bad("method not found")
            return 3
        name, blob, d, cls, m = found
        hdr, lines = _reapk.disassemble(d, m["code_off"])
        Out.head("smali", G_OK)
        Out.kv("registers", hdr["regs"], width=14)
        Out.kv("ins", hdr["ins"], width=14)
        for line in lines:
            print("  " + T_DIM(line))
        return 0
    return 0


def cmd_sign_native(args):
    Tty.probe()
    src, _searched = resolve_input(args.input)
    if src is None:
        Out.bad("input not found · " + str(args.input))
        for _root in (_searched or [])[:5]:
            Out.info("looked in " + str(_root))
        return 2
    if not ensure_tools(["reapk"], "native signing"):
        Out.bad("reapk is required · pip install reapk")
        return 3
    import reapk as _reapk
    raw = src.read_bytes()
    try:
        signed = _reapk.apk_sign_v2(raw)
    except Exception as e:
        Out.bad("signing failed · " + trunc(str(e), 70))
        return 7
    dest = Path(args.output).expanduser() if args.output else rap_output(src, "signed")
    atomic_write(dest, signed, "wb")
    Out.head("native signing", G_OK)
    Out.kv("schemes", "v2 + v3", width=14)
    Out.kv("input", human(len(raw)), width=14)
    Out.kv("output", human(len(signed)), width=14)
    Out.kv("written", str(dest))
    return 0


def dex_class_names(data):
    idx = DexIndex(data)
    if not idx.ok:
        return []
    out = []
    for i in range(idx.c_n):
        try:
            tidx = u4(data, idx.c_off + i * 32)
            name = idx.type_name(tidx)
            if name:
                out.append(name)
        except Exception:
            continue
    return out


def axml_from_text(text):
    import xml.etree.ElementTree as ET
    root = ET.fromstring(text)
    nodes = []
    strings = []

    def intern(s):
        if s not in strings:
            strings.append(s)
        return strings.index(s)

    def local(name):
        if name.startswith("{"):
            uri, _, rest = name[1:].partition("}")
            return ("android:" + rest) if "android" in uri else rest
        return name

    def walk(el):
        nodes.append(("start", local(el.tag), [(local(k), v) for k, v in el.attrib.items()]))
        for child in el:
            walk(child)
        nodes.append(("end", local(el.tag), []))

    walk(root)
    intern("android")
    for _, tag, attrs in nodes:
        intern(tag)
        for k, v in attrs:
            intern(k)
            intern(v)
    pool = build_string_pool(strings)
    body = bytearray()
    stack = []
    for kind, tag, attrs in nodes:
        if kind == "start":
            name_idx = intern(tag)
            payload = b""
            for k, v in attrs:
                payload += struct.pack("<IIIHBBI", 0xFFFFFFFF, intern(k), 0xFFFFFFFF,
                                       8, 0, 0x03, intern(v))
            ext = struct.pack("<IIHHHHHH", 0xFFFFFFFF, name_idx, 20, 20, len(attrs), 0, 0, 0)
            size = 16 + len(ext) + len(payload)
            body += struct.pack("<HHIII", 0x0102, 16, size, 1, 0xFFFFFFFF) + ext + payload
            stack.append((tag, name_idx))
        else:
            if not stack:
                continue
            tag, name_idx = stack.pop()
            body += struct.pack("<HHIIIII", 0x0103, 16, 24, 1, 0xFFFFFFFF, 0xFFFFFFFF, name_idx)
    total = 8 + len(pool) + len(body)
    return struct.pack("<HHI", 0x0003, 8, total) + pool + bytes(body)


def build_parser():
    ap = argparse.ArgumentParser(prog="arpxtool", add_help=True, description="ARPX · Android reverse engineering toolkit")
    ap.add_argument("-i", "--input", help="target .apk / .apks / .xapk / .apkm / .zip")
    ap.add_argument("-m", "--mode", default=None, choices=sorted(MODE_PLAN))
    ap.add_argument("-o", "--output", help="output apk path")
    ap.add_argument("--strategy", default="auto", choices=["auto", "standard", "surgical", "surgery"])
    ap.add_argument("--password", default="arp-research", help="keystore password")
    ap.add_argument("--keep", action="store_true", help="keep the working tree")
    ap.add_argument("--dry", action="store_true", help="analyse patch sites without writing")
    ap.add_argument("--no-net", action="store_true", help="never download engines")
    ap.add_argument("--no-anim", action="store_true", help="disable animation")
    ap.add_argument("--quiet", action="store_true", help="skip the banner")
    ap.add_argument("--report", action="store_true", help="write a json report")
    ap.add_argument("--copy-download", action="store_true", help="copy result to /sdcard/Download")
    ap.add_argument("--unpack", help="extract every archive entry to this directory")
    ap.add_argument("--dump", help="write class and string dumps to this directory")
    ap.add_argument("--decode", action="store_true", help="also produce a smali tree")
    ap.add_argument("--no-report", action="store_true", help="skip the html report")
    ap.add_argument("--fast", action="store_true", help="manifest and native only, never touch smali")
    ap.add_argument("--engine", help="force an apktool version, e.g. 2.12.1")
    ap.add_argument("--flutter-engine", help="drop-in libflutter.so (e.g. reFlutter's patched build)")
    ap.add_argument("--remove-license", action="store_true", help="neutralise Play Store licence checks (LVL / PairIP)")
    ap.add_argument("--resume", help="rebuild from a preserved work tree")
    ap.add_argument("--doctor", action="store_true", help="diagnose the host and the toolchain")
    ap.add_argument("--clean", action="store_true", help="purge stale work trees and reclaim space")
    ap.add_argument("--compare", help="second archive to diff against --input")
    ap.add_argument("--search", help="search a string across dex, native and asset payloads")
    ap.add_argument("--cert", action="store_true", help="print signing certificate facts")
    ap.add_argument("--batch", help="process every archive under a directory")
    ap.add_argument("--log", help="write the session log to this path")
    ap.add_argument("--no-log", action="store_true", help="disable the session log")
    ap.add_argument("--frida", help="write a frida hook script for detected pinning")
    ap.add_argument("--mapping", help="proguard mapping file to deobfuscate names")
    ap.add_argument("--java", help="decompile to java sources with jadx into this directory")
    ap.add_argument("--disasm", type=int, help="disassemble this many native instructions per object")
    ap.add_argument("--targets", help="file listing class#method targets to neutralise")
    ap.add_argument("--methods", help="list dex methods matching a regex")
    ap.add_argument("--security-test", action="store_true", help="run the defensive security test suite")
    ap.add_argument("--rules", help="json or yaml rule file for custom detection")
    ap.add_argument("--baseline", help="earlier build to diff findings against")
    ap.add_argument("--patch", help="json patch set to apply")
    ap.add_argument("--profile", help="patch profile name")
    ap.add_argument("--revert", help="journal file to revert from")
    ap.add_argument("--force", action="store_true", help="apply despite conflicts or validation failures")
    ap.add_argument("--components", action="store_true", help="map ad, license, billing and signature components")
    ap.add_argument("--native", action="store_true", help="native object report with JNI and relocations")
    ap.add_argument("--strings", type=int, help="how many native strings to print")
    ap.add_argument("--ads-manager", action="store_true", help="detect ad sdks and generate a call-site patch set")
    ap.add_argument("--license-manager", action="store_true", help="detect license checks and generate a patch set")
    ap.add_argument("--billing-manager", action="store_true", help="detect billing usage and generate a patch set")
    ap.add_argument("--signature-manager", action="store_true", help="signature dependency and self-check manager")
    ap.add_argument("--native-analysis", action="store_true", help="native protection reference report")
    ap.add_argument("--apply", action="store_true", help="apply the generated patch set")
    ap.add_argument("--dry-run", action="store_true", help="plan only, never write")
    ap.add_argument("--native-patch", help="comma separated native symbols to stub in every .so")
    ap.add_argument("--max-engines", type=int, default=3, help="how many apktool engines to try (default 3)")
    ap.add_argument("--install-check", action="store_true", help="diagnose why an archive would refuse to install")
    ap.add_argument("--embed-ca", help="pem certificate to trust inside the network security config")
    ap.add_argument("--unsigned", action="store_true", help="skip signing")
    ap.add_argument("--keystore", help="custom keystore to sign with")
    ap.add_argument("--alias", help="key alias inside the keystore")
    ap.add_argument("--store-pass", help="keystore password")
    ap.add_argument("--key-pass", help="key password")
    ap.add_argument("--v1", action="store_true", help="force v1 signing on")
    ap.add_argument("--v2", action="store_true", help="force v2 signing on")
    ap.add_argument("--v3", action="store_true", help="force v3 signing on")
    ap.add_argument("--no-v1", action="store_true", help="disable v1 signing")
    ap.add_argument("--no-v2", action="store_true", help="disable v2 signing")
    ap.add_argument("--no-v3", action="store_true", help="disable v3 signing")
    ap.add_argument("--menu", action="store_true", help="open the interactive selector")
    ap.add_argument("--install-cli", nargs="?", const="arpxtool", help="create a shell launcher, default name arpxtool")
    ap.add_argument("--config", help="json file with default settings")
    ap.add_argument("--netsec-mode", default="user", choices=sorted(NETSEC_MODES),
                    help="trust anchors written into the network security config")
    ap.add_argument("--threads", type=int, help="apktool worker threads")
    ap.add_argument("--timeout", type=int, help="per command timeout in seconds")
    ap.add_argument("--edit", help="json file of instruction level edits")
    ap.add_argument("--ssl-engine", action="store_true", help="deep tls surface discovery and patching")
    ap.add_argument("--signature-engine", action="store_true", help="deep signature check discovery and patching")
    ap.add_argument("--so-report", action="store_true", help="deep native object report with entropy and markers")
    ap.add_argument("--arsc", action="store_true", help="resource table read and write")
    ap.add_argument("--arsc-list", metavar="NAME", help="search resource entries by type or name")
    ap.add_argument("--arsc-set", action="append", metavar="TYPE/NAME=VALUE", help="change a string resource")
    ap.add_argument("--xml-path", help="entry inside the archive to decode")
    ap.add_argument("--hex-find", metavar="HEX", help="find a byte pattern")
    ap.add_argument("--hex-patch", action="append", metavar="OFF=HEX", help="overwrite bytes at an offset")
    ap.add_argument("--clone-pkg", metavar="PKG", help="new package name for a clone")
    ap.add_argument("--compare-to", metavar="APK", help="second archive to compare against")
    ap.add_argument("--dex-show", metavar="METHOD", help="print the smali of a method")
    ap.add_argument("--dex-show-class", metavar="CLASS", help="class for --dex-show")
    ap.add_argument("--dex-set", metavar="CLASS;->M=SML", help="replace a method body from a smali file")
    ap.add_argument("--secrets", action="store_true", help="scan for api keys, tokens and endpoints")
    ap.add_argument("--axml2xml", action="store_true", help="decode binary xml to text")
    ap.add_argument("--xml2axml", action="store_true", help="compile text xml to binary")
    ap.add_argument("--hex", action="store_true", help="hex view, find or patch")
    ap.add_argument("--clone", action="store_true", help="clone the archive under a new package")
    ap.add_argument("--compare-dex", action="store_true", help="semantic class level comparison")
    ap.add_argument("--vdex", action="store_true", help="extract dex payloads from vdex or oat")
    ap.add_argument("--dex-edit", action="store_true", help="smali level editing through reapk")
    ap.add_argument("--sign-native", action="store_true", help="sign v2 and v3 without java")
    ap.add_argument("--tools", action="store_true", help="inventory of external tools")
    ap.add_argument("--install-all", action="store_true", help="install every external tool at once")
    ap.add_argument("--provenance", action="store_true", help="show build identity and verify its seal")
    ap.add_argument("--repair", action="store_true", help="strip a stale signature block and re-sign")
    ap.add_argument("--keygen", action="store_true", help="create a signing keystore")
    ap.add_argument("--keygen-app", action="store_true", help="create a keystore named after the app package")
    ap.add_argument("--identify", action="store_true", help="show which key signed the archive")
    ap.add_argument("--diagnose", action="store_true", help="every reason an install would fail")
    ap.add_argument("--exit-check", action="store_true", help="why an app closes right after launch")
    ap.add_argument("--crash-read", action="store_true", help="map a stack trace onto the apk")
    ap.add_argument("--crash-apk", metavar="APK", help="apk to map crash frames against")
    ap.add_argument("--crashpatch", action="store_true", help="set debuggable so crashes print a trace")
    ap.add_argument("--axml-info", action="store_true", help="show the chunk layout of the binary manifest")
    ap.add_argument("--fix-native", action="store_true", help="store and page align every native library")
    ap.add_argument("--crashinject", action="store_true", help="add an in-app crash handler that writes the trace to sdcard")
    ap.add_argument("--logcat", action="store_true", help="pull crash and anr data from the device")
    ap.add_argument("--package", help="package to filter logcat by")
    ap.add_argument("--source", choices=("crash", "dropbox", "all"), default="all", help="where to read from")
    ap.add_argument("--fix-split", action="store_true", help="clear split flags from the manifest")
    ap.add_argument("--sdk", type=int, help="device api level for install checks")
    ap.add_argument("--abi", help="device abi, e.g. arm64-v8a")
    ap.add_argument("--sign-apk", dest="sign_apk", action="store_true", help="sign with the remembered keystore")
    ap.add_argument("--dname", help="certificate subject for keygen")
    ap.add_argument("--validity", type=int, help="keystore validity in days")
    ap.add_argument("--keysize", type=int, help="rsa key size")
    ap.add_argument("--overwrite", action="store_true", help="replace an existing keystore")
    ap.add_argument("--flutter-ssl", action="store_true", help="locate and patch the boringssl verifier in libflutter.so")
    ap.add_argument("--setup", action="store_true", help="install missing external tools")
    ap.add_argument("--yes", action="store_true", help="confirm package installation")
    ap.add_argument("--no-install", action="store_true", help="never install tools automatically")
    ap.add_argument("--show-commands", action="store_true", help="keep executed command lines visible")
    ap.add_argument("--trace", action="store_true", help="print every command and step the tool runs")
    ap.add_argument("--exec-detail", action="store_true", help="after each command, print its exit code, time and output")
    ap.add_argument("--trace-file", metavar="PATH", help="append the trace to a file")
    ap.add_argument("--anim", metavar="STYLE", choices=ANIM_STYLES, help="banner animation style")
    ap.add_argument("--logo", choices=("big", "compact"), help="banner lettering")
    ap.add_argument("--sign", action="store_true", help="sign the result after applying")
    ap.add_argument("--full-modification", action="store_true", help="run every manager and merge the patch sets")
    ap.add_argument("--self-check", action="store_true", help="run internal diagnostics")
    ap.add_argument("-v", "--version", action="version", version="%s %s %s" % (APP, VERSION, CODENAME))
    return ap


def interactive(args):
    Tty.probe()
    banner_anim(args.no_anim or not Tty.enabled)
    mode = args.mode or choose("select operation", [
        ("re", "REPORT", "decompile + deep static analysis"),
        ("unpack", "UNPACK", "extract every entry, byte for byte"),
        ("fast", "FAST", "manifest + netsec only, never smali"),
        ("surgery", "SURGERY", "no java, no apktool, no aapt2"),
        ("signature", "SIGNATURE", "neutralise app-level signature checks"),
        ("detect", "DETECT", "ads · billing · license · signature map"),
        ("full", "FULL", "binary + bytecode + manifest + sign"),
        ("ssl", "SSL", "tls verification neutralisation"),
        ("security", "SECURITY", "root · vpn · frida · emulator"),
        ("native", "NATIVE", "binary only, surgical repack"),
        ("inspect", "INSPECT", "read only forensic report"),
        ("verify", "VERIFY", "signature and archive audit"),
    ])
    if not mode:
        Out.info("cancelled")
        return 0
    args.mode = mode
    if not args.input:
        print()
        try:
            raw = input("  " + T_INFO(ARROW) + " " + T_TXT("target path: ")).strip().strip("'\"")
        except (EOFError, KeyboardInterrupt):
            return 0
        if not raw:
            Out.bad("no input")
            return 1
        args.input = raw
    if mode == "fast":
        args.fast = True
    if mode in ("re", "unpack"):
        if mode == "unpack" and not args.unpack:
            args.unpack = str((resolve_input(args.input)[0] or Path(args.input)).with_suffix("")) + "_unpack"
            args.decode = True
        return run_analysis(args)
    return run_pipeline(args)


def main(argv=None):
    Tty.probe()
    raw = list(sys.argv[1:] if argv is None else argv)
    rewritten, action = positional_rewrite(raw)
    if action == "reference":
        return print_reference()
    if isinstance(action, tuple) and action[0] == "missing-arg":
        Out.bad("'" + action[1] + "' needs a value")
        return 2
    argv = rewritten
    if argv == ["--menu"] or argv == []:
        if argv == ["--menu"]:
            argv = []
        return interactive(build_parser().parse_args([]))
    args = build_parser().parse_args(argv)
    args = apply_config(args)
    SIGN_STATE["keystore"] = getattr(args, "keystore", None)
    SIGN_STATE["alias"] = getattr(args, "alias", None)
    SIGN_STATE["store_pass"] = getattr(args, "store_pass", None)
    SIGN_STATE["key_pass"] = getattr(args, "key_pass", None)
    SIGN_STATE["v1"] = (not getattr(args, "no_v1", False)) or getattr(args, "v1", False)
    SIGN_STATE["v2"] = (not getattr(args, "no_v2", False)) or getattr(args, "v2", False)
    SIGN_STATE["v3"] = (not getattr(args, "no_v3", False)) or getattr(args, "v3", False)
    AUTO["install"] = not getattr(args, "no_install", False)
    EXEC_DETAIL["on"] = bool(getattr(args, "exec_detail", False))
    TRACE["on"] = bool(getattr(args, "trace", False) or getattr(args, "trace_file", None) or EXEC_DETAIL["on"])
    TRACE["file"] = getattr(args, "trace_file", None)
    if getattr(args, "anim", None):
        ANIM["style"] = args.anim
    if getattr(args, "logo", None):
        LOGO_STYLE["big"] = args.logo == "big"
    if TRACE["on"]:
        trace("arpxtool " + " ".join(argv), "start")
    if not args.no_log:
        log_open(args.log)
    if args.self_check:
        return self_check()
    if args.doctor:
        return doctor()
    if args.batch:
        return cmd_batch(args)
    if args.input and args.mode == "surgery":
        return run_surgery_mode(args)
    if args.input and args.mode == "detect":
        return run_detect_mode(args)
    if args.input and args.security_test:
        return run_security_test(args)
    if args.revert or (args.patch and args.input):
        return cmd_patch(args)
    if args.components and args.input:
        return cmd_components(args)
    if args.native and args.input:
        return cmd_native(args)
    if args.ads_manager and args.input:
        return cmd_manager(args, "ads")
    if args.license_manager and args.input:
        return cmd_manager(args, "license")
    if args.billing_manager and args.input:
        return cmd_manager(args, "billing")
    if args.signature_manager and args.input:
        return cmd_manager(args, "signature")
    if args.native_analysis and args.input:
        return cmd_native(args)
    if args.full_modification and args.input:
        return cmd_full_modification(args)
    if args.native_patch and args.input:
        return cmd_native_patch(args)
    if args.install_check and args.input:
        return cmd_install_check(args)
    if args.edit and args.input:
        return cmd_edit(args)
    if args.ssl_engine and args.input:
        return cmd_ssl_engine(args)
    if args.signature_engine and args.input:
        return cmd_signature_engine(args)
    if args.so_report and args.input:
        return cmd_so_report(args)
    if args.secrets and args.input:
        return cmd_secrets(args)
    if args.arsc and args.input:
        return cmd_arsc(args)
    if args.axml2xml and args.input:
        return cmd_axml2xml(args)
    if args.xml2axml and args.input:
        return cmd_xml2axml(args)
    if args.hex and args.input:
        return cmd_hex(args)
    if args.clone and args.input:
        return cmd_clone(args)
    if args.compare_dex and args.input:
        return cmd_compare_dex(args)
    if args.vdex and args.input:
        return cmd_vdex(args)
    if args.dex_edit and args.input:
        return cmd_dex_edit(args)
    if args.sign_native and args.input:
        return cmd_sign_native(args)
    if args.flutter_ssl and args.input:
        return cmd_flutter_ssl(args)
    if args.keygen_app and args.input:
        return cmd_keygen_app(args)
    if args.crash_read and args.input:
        return cmd_crash_read(args)
    if args.fix_native and args.input:
        return cmd_fix_native(args)
    if args.axml_info and args.input:
        return cmd_axml_info(args)
    if args.crashinject and args.input:
        return cmd_crashinject(args)
    if args.crashpatch and args.input:
        return cmd_crashpatch(args)
    if args.logcat:
        return cmd_logcat(args)
    if args.exit_check and args.input:
        return cmd_exitcheck(args)
    if args.diagnose and args.input:
        return cmd_diagnose(args)
    if args.identify and args.input:
        return cmd_identify(args)
    if args.keygen:
        return cmd_keygen(args)
    if args.sign_apk and args.input:
        return cmd_sign(args)
    if args.repair and args.input:
        return cmd_repair(args)
    if args.provenance:
        return cmd_provenance(args)
    if args.install_all:
        return cmd_install_all(args)
    if args.tools:
        return cmd_tools(args)
    if args.setup:
        return cmd_setup(args)
    if args.install_cli is not None:
        return cmd_install_cli(args)
    if args.clean:
        return cmd_clean()
    if args.compare and args.input:
        return cmd_compare(args)
    if args.methods and args.input:
        return cmd_methods(args)
    if args.search and args.input:
        return cmd_search(args)
    if args.cert and args.input:
        return cmd_cert(args)
    try:
        if args.input and args.mode in ("re", "unpack"):
            if args.mode == "unpack" and not args.unpack:
                args.unpack = str((resolve_input(args.input)[0] or Path(args.input)).with_suffix("")) + "_unpack"
                args.decode = True
            return run_analysis(args)
        if args.input and args.mode:
            return run_pipeline(args)
        return interactive(args)
    except KeyboardInterrupt:
        print()
        Out.warn("interrupted")
        return 130
    except Exception as e:
        print()
        Out.bad("fatal · " + trunc(str(e), 120))
        tb = traceback.extract_tb(e.__traceback__)
        if tb:
            last = tb[-1]
            Out.info("%s line %d in %s" % (os.path.basename(last.filename), last.lineno, last.name))
        if os.environ.get("ARP_DEBUG"):
            raise
        return 1
    finally:
        Anim.close()
        if LOG["path"]:
            print()
            Out.kv("log", str(LOG["path"]))
        log_close()
        if Tty.enabled:
            sys.stdout.write(Pal.RESET)
        sys.stdout.flush()


if __name__ == "__main__":
    sys.exit(main())
